# -*- coding: utf-8 -*-
"""Replace ABP_StrafeLocomotion Idle SequencePlayer MM_Idle -> Idle_Seq_RTG."""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
IDLE_RTG = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Idle_Seq_RTG"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"


def log(m):
    unreal.log(f"[FixIdle] {m}")


def set_nested_blendspace(node, bs) -> bool:
    """BlendSpacePlayer stores asset inside nested AnimNode struct."""
    for outer in ("node", "Node"):
        try:
            anim_node = node.get_editor_property(outer)
        except Exception:
            continue
        if not anim_node:
            continue
        for prop in ("blend_space", "BlendSpace"):
            try:
                old = anim_node.get_editor_property(prop)
                anim_node.set_editor_property(prop, bs)
                # write back if needed
                try:
                    node.set_editor_property(outer, anim_node)
                except Exception:
                    pass
                log(f"BS player {node.get_name()}: {old} -> {bs.get_name()}")
                return True
            except Exception:
                continue
    # flat props
    for prop in ("blend_space", "BlendSpace"):
        try:
            old = node.get_editor_property(prop)
            node.set_editor_property(prop, bs)
            log(f"BS flat {node.get_name()}: {old} -> {bs.get_name()}")
            return True
        except Exception:
            continue
    return False


def set_nested_sequence(node, seq) -> bool:
    for outer in ("node", "Node"):
        try:
            anim_node = node.get_editor_property(outer)
        except Exception:
            continue
        if not anim_node:
            continue
        for prop in ("sequence", "Sequence"):
            try:
                old = anim_node.get_editor_property(prop)
                anim_node.set_editor_property(prop, seq)
                try:
                    node.set_editor_property(outer, anim_node)
                except Exception:
                    pass
                log(
                    f"Seq {node.get_name()}: "
                    f"{old.get_name() if old else None} -> {seq.get_name()}"
                )
                return True
            except Exception:
                continue
    for prop in ("sequence", "Sequence"):
        try:
            old = node.get_editor_property(prop)
            node.set_editor_property(prop, seq)
            log(
                f"Seq flat {node.get_name()}: "
                f"{old.get_name() if old else None} -> {seq.get_name()}"
            )
            return True
        except Exception:
            continue
    return False


def get_sequence_from_node(node):
    for outer in ("node", "Node", None):
        obj = node
        if outer:
            try:
                obj = node.get_editor_property(outer)
            except Exception:
                continue
        if not obj:
            continue
        for prop in ("sequence", "Sequence"):
            try:
                return obj.get_editor_property(prop)
            except Exception:
                continue
    return None


def run():
    log("start")
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    idle = unreal.EditorAssetLibrary.load_asset(IDLE_RTG)
    bs = unreal.EditorAssetLibrary.load_asset(BS)
    if not abp or not idle:
        raise RuntimeError("ABP or Idle_Seq_RTG missing")

    replaced = 0
    seq_cls = getattr(unreal, "AnimGraphNode_SequencePlayer", None)
    if seq_cls:
        for obj in unreal.ObjectIterator(seq_cls):
            try:
                path = obj.get_path_name()
            except Exception:
                continue
            if "ABP_StrafeLocomotion" not in path:
                continue
            seq = get_sequence_from_node(obj)
            sname = seq.get_name() if seq else ""
            log(f"found SeqPlayer {obj.get_name()} -> {seq.get_path_name() if seq else None}")
            # Replace idle only (keep jump/land for now)
            if seq and ("MM_Idle" in sname or sname == "MM_Idle" or "Idle" == sname):
                if set_nested_sequence(obj, idle):
                    replaced += 1
            elif seq and "MM_Idle" in seq.get_path_name():
                if set_nested_sequence(obj, idle):
                    replaced += 1

    # Ensure BlendSpacePlayer still points at BS_WalkRun_Sword
    bs_ok = 0
    bs_cls = getattr(unreal, "AnimGraphNode_BlendSpacePlayer", None)
    if bs_cls and bs:
        for obj in unreal.ObjectIterator(bs_cls):
            try:
                path = obj.get_path_name()
            except Exception:
                continue
            if "ABP_StrafeLocomotion" not in path:
                continue
            if set_nested_blendspace(obj, bs):
                bs_ok += 1

    log(f"Idle replaced={replaced}, BS rebound={bs_ok}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)

    # Verify soft refs
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = f.read()
    log(
        f"VERIFY Idle_Seq_RTG={b'Idle_Seq_RTG' in data} "
        f"MM_Idle={b'MM_Idle' in data} "
        f"BS_WalkRun_Sword={b'BS_WalkRun_Sword' in data}"
    )
    log("done — standing uses Sword Idle_Seq_RTG; move still uses BS_WalkRun_Sword")


if __name__ == "__main__":
    run()
else:
    run()
