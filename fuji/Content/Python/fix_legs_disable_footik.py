# -*- coding: utf-8 -*-
"""
Legs look unbound / twisted often because ABP_Unarmed's Foot IK Control Rig
fights retargeted Sword clips. Disable Foot IK alpha and verify IK retarget chains.
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
IKR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/IK/IKR_SwordToCharacters"
IK_CHAR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/IK/IK_Characters_Manny"
CHA2 = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/Cha_2_IKRig"
IDLE = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Idle_Seq_RTG"
WALK = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Walk_Loop_F_0_Seq_RTG"


def log(m):
    unreal.log(f"[FixLegs] {m}")


def disable_foot_ik(abp) -> int:
    n = 0
    cls = getattr(unreal, "AnimGraphNode_ControlRig", None)
    if not cls:
        log("no AnimGraphNode_ControlRig")
        return 0
    for obj in unreal.ObjectIterator(cls):
        try:
            path = obj.get_path_name()
        except Exception:
            continue
        if "ABP_StrafeLocomotion" not in path:
            continue
        log(f"ControlRig node {obj.get_name()} path={path}")

        # Inspect control rig asset
        for prop in ("control_rig_class", "ControlRigClass", "control_rig_asset", "ControlRigAsset"):
            try:
                v = obj.get_editor_property(prop)
                log(f"  {prop}={v}")
            except Exception:
                pass

        # Nested AnimNode_ControlRig
        for outer in ("node", "Node", None):
            target = obj
            if outer:
                try:
                    target = obj.get_editor_property(outer)
                except Exception:
                    continue
            if not target:
                continue
            for prop, val in (
                ("alpha", 0.0),
                ("Alpha", 0.0),
                ("lod_threshold", 0),
                ("LODThreshold", 0),
            ):
                try:
                    old = target.get_editor_property(prop)
                    target.set_editor_property(prop, val)
                    if outer:
                        try:
                            obj.set_editor_property(outer, target)
                        except Exception:
                            pass
                    log(f"  set {outer or 'self'}.{prop}: {old} -> {val}")
                    n += 1
                except Exception:
                    pass

            # Also try alpha_bool / alpha_input_type to constant 0
            for prop, val in (
                ("alpha_input_type", getattr(unreal.EAnimAlphaInputType, "Float", None) or 0),
                ("b_alpha_bool_enabled", False),
            ):
                try:
                    target.set_editor_property(prop, val)
                    if outer:
                        try:
                            obj.set_editor_property(outer, target)
                        except Exception:
                            pass
                    log(f"  set {prop}={val}")
                except Exception:
                    pass
    return n


def inspect_ik_retargeter():
    if not unreal.EditorAssetLibrary.does_asset_exist(IKR):
        log(f"missing IKR {IKR}")
        return
    ikr = unreal.EditorAssetLibrary.load_asset(IKR)
    log(f"IKR={ikr.get_path_name()}")
    for prop in (
        "source_ik_rig_asset",
        "target_ik_rig_asset",
        "SourceIKRigAsset",
        "TargetIKRigAsset",
    ):
        try:
            v = ikr.get_editor_property(prop)
            log(f"  {prop}={v.get_path_name() if v else None}")
        except Exception as exc:
            log(f"  {prop}: {exc}")

    # Try to list chain mapping
    for prop in ("chain_mapping", "ChainMapping", "retarget_chain_settings", "RetargetChainSettings"):
        try:
            v = ikr.get_editor_property(prop)
            log(f"  {prop} type={type(v)} len={len(v) if v is not None and hasattr(v,'__len__') else 'n/a'}")
            if v:
                for i, item in enumerate(list(v)[:40]):
                    try:
                        d = item.to_tuple() if hasattr(item, "to_tuple") else None
                    except Exception:
                        d = None
                    # dump editor props
                    bits = []
                    for ap in dir(item):
                        if ap.startswith("_"):
                            continue
                        if ap.startswith("get_") or ap in (
                            "source_chain",
                            "target_chain",
                            "SourceChain",
                            "TargetChain",
                            "chain_name",
                            "enabled",
                        ):
                            try:
                                if hasattr(item, ap) and callable(getattr(item, ap)):
                                    continue
                            except Exception:
                                pass
                    for ap in (
                        "source_chain",
                        "target_chain",
                        "SourceChain",
                        "TargetChain",
                        "enabled",
                        "EnableFK",
                        "EnableIK",
                        "source_chain_name",
                        "target_chain_name",
                    ):
                        try:
                            bits.append(f"{ap}={item.get_editor_property(ap)}")
                        except Exception:
                            pass
                    log(f"    [{i}] {bits or d or item}")
            break
        except Exception as exc:
            log(f"  {prop}: {exc}")

    # Controller ops if available
    ctrl_cls = getattr(unreal, "IKRetargeterController", None)
    if ctrl_cls:
        try:
            ctrl = ctrl_cls.get_controller(ikr)
            log(f"controller={ctrl}")
            for meth in (
                "get_retarget_chain_settings",
                "get_all_chain_settings",
                "get_chain_mapping",
                "get_retarget_chains",
            ):
                if hasattr(ctrl, meth):
                    try:
                        r = getattr(ctrl, meth)()
                        log(f"  ctrl.{meth} => {r}")
                    except Exception as exc:
                        try:
                            r = getattr(ctrl, meth)(ikr)
                            log(f"  ctrl.{meth}(ikr) => {r}")
                        except Exception as exc2:
                            log(f"  ctrl.{meth} ERR {exc} / {exc2}")
        except Exception as exc:
            log(f"controller: {exc}")


def inspect_anims():
    for p in (IDLE, WALK):
        if not unreal.EditorAssetLibrary.does_asset_exist(p):
            log(f"missing {p}")
            continue
        a = unreal.EditorAssetLibrary.load_asset(p)
        sk = a.get_editor_property("skeleton")
        log(f"{a.get_name()} skeleton={sk.get_path_name() if sk else None}")
        try:
            log(f"  num_frames={a.get_editor_property('number_of_sampled_frames') if hasattr(a,'get_editor_property') else '?'}")
        except Exception:
            pass
        try:
            log(f"  rate_scale={a.get_editor_property('rate_scale')}")
            log(f"  additive={a.get_editor_property('additive_anim_type')}")
        except Exception:
            pass


def ensure_fbik_on_target_ikrig():
    """Make sure target IK Rig has leg/foot chains for retarget."""
    if not unreal.EditorAssetLibrary.does_asset_exist(IK_CHAR):
        log("IK_Characters_Manny missing")
        return
    ik = unreal.EditorAssetLibrary.load_asset(IK_CHAR)
    ctrl_cls = getattr(unreal, "IKRigController", None)
    if not ctrl_cls:
        log("no IKRigController")
        return
    try:
        ctrl = ctrl_cls.get_controller(ik)
    except Exception as exc:
        log(f"IKRigController: {exc}")
        return
    log(f"IKRigController={ctrl}")
    for meth in ("get_retarget_chains", "get_ik_rig_goals", "get_solver_array"):
        if hasattr(ctrl, meth):
            try:
                result = getattr(ctrl, meth)()
                log(f"  {meth}={result}")
            except Exception as exc:
                log(f"  {meth}: {exc}")
    # Apply auto retarget definition again if available
    for meth in (
        "apply_auto_generated_retarget_definition",
        "auto_generate_retarget_definition",
        "generate_retarget_definition",
    ):
        if hasattr(ctrl, meth):
            try:
                getattr(ctrl, meth)()
                log(f"ran {meth}")
            except Exception as exc:
                try:
                    getattr(ctrl, meth)(True)
                    log(f"ran {meth}(True)")
                except Exception as exc2:
                    log(f"{meth}: {exc} / {exc2}")
    unreal.EditorAssetLibrary.save_asset(IK_CHAR, only_if_is_dirty=False)


def run():
    log("start")
    inspect_anims()
    inspect_ik_retargeter()
    ensure_fbik_on_target_ikrig()

    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    n = disable_foot_ik(abp)
    log(f"foot ik tweaks={n}")
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)

    # Binary check
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = f.read()
    log(f"VERIFY still has FootIK asset ref={b'CR_Mannequin_FootIK' in data} (node may remain with alpha=0)")
    log("done — Foot IK disabled; if legs still wrong, need re-retarget with better chain mapping")


if __name__ == "__main__":
    run()
else:
    run()
