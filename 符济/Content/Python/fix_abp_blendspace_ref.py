# -*- coding: utf-8 -*-
"""Force ABP_StrafeLocomotion BlendSpacePlayer to use BS_WalkRun_Locomotion / BS_WalkRun_Sword."""

import unreal

ABP_PATH = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
BS_PATH = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/BS_WalkRun_Locomotion"
ALIAS_PATH = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[FixABP] {m}")


def run():
    bs = unreal.EditorAssetLibrary.load_asset(BS_PATH)
    alias = unreal.EditorAssetLibrary.load_asset(ALIAS_PATH)
    if not bs and not alias:
        raise RuntimeError("No blendspace found")
    target_bs = bs or alias

    # Ensure alias mirrors BS
    if bs:
        if unreal.EditorAssetLibrary.does_asset_exist(ALIAS_PATH):
            unreal.EditorAssetLibrary.delete_asset(ALIAS_PATH)
        unreal.EditorAssetLibrary.duplicate_asset(BS_PATH, ALIAS_PATH)
        alias = unreal.EditorAssetLibrary.load_asset(ALIAS_PATH)
        unreal.EditorAssetLibrary.save_asset(ALIAS_PATH, only_if_is_dirty=False)

    # Prefer alias for same-skeleton folder as original ABP content
    use_bs = alias or target_bs
    log(f"Target BS: {use_bs.get_path_name()}")
    log(f"BS skeleton: {use_bs.get_editor_property('skeleton')}")

    abp = unreal.EditorAssetLibrary.load_asset(ABP_PATH)
    if not abp:
        raise RuntimeError("ABP missing")

    replaced = 0
    node_classes = []
    for name in (
        "AnimGraphNode_BlendSpacePlayer",
        "AnimGraphNode_BlendSpaceEvaluator",
        "AnimGraphNode_RotationOffsetBlendSpace",
    ):
        cls = getattr(unreal, name, None)
        if cls:
            node_classes.append(cls)

    for cls in node_classes:
        try:
            iterator = unreal.ObjectIterator(cls)
        except Exception as exc:
            log(f"ObjectIterator({cls}) failed: {exc}")
            continue
        for obj in iterator:
            try:
                path = obj.get_path_name()
            except Exception:
                continue
            if "ABP_StrafeLocomotion" not in path:
                continue
            for prop in ("blend_space", "BlendSpace"):
                try:
                    old = obj.get_editor_property(prop)
                    obj.set_editor_property(prop, use_bs)
                    replaced += 1
                    log(f"Set {obj.get_class().get_name()}.{prop}: {old} -> {use_bs.get_name()}")
                    break
                except Exception:
                    continue

    log(f"Nodes updated: {replaced}")

    # Soft reference scan via asset registry dependencies won't mutate; compile+save
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)

    # Binary safety net AFTER save, do not compile again
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP_PATH.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = bytearray(f.read())
    if b"BS_Idle_Walk_Run" in data:
        data = data.replace(b"BS_Idle_Walk_Run", b"BS_WalkRun_Sword")
        with open(fs, "wb") as f:
            f.write(data)
        log("Post-save binary patch applied")
    with open(fs, "rb") as f:
        d = f.read()
    log(f"Final: Sword={b'BS_WalkRun_Sword' in d} Idle={b'BS_Idle_Walk_Run' in d}")

    # Ensure character still points at ABP
    bp = unreal.EditorAssetLibrary.load_asset(CHAR_BP)
    if bp:
        try:
            gen = bp.generated_class()
            cdo = unreal.get_default_object(gen)
            mesh = cdo.get_editor_property("mesh")
            mesh.set_editor_property("anim_class", abp.generated_class())
            cdo.set_editor_property("use_controller_rotation_yaw", True)
            move = cdo.get_editor_property("character_movement")
            move.set_editor_property("orient_rotation_to_movement", False)
            move.set_editor_property("max_walk_speed", 250.0)
            unreal.EditorAssetLibrary.save_asset(CHAR_BP, only_if_is_dirty=False)
            log("Character refreshed")
        except Exception as exc:
            log(f"char: {exc}")

    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
