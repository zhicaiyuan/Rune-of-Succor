# -*- coding: utf-8 -*-
"""
1) Classic third-person camera: mouse aims camera; character faces movement
   (NOT strafe / camera locked to body yaw).
2) Use stock ABP_Unarmed for clean upright locomotion until Sword IK retarget
   is done with a correct retargeter (current NewIKRetargeter is UE4->Sword).
"""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]
ABP_UNARMED = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"


def log(m):
    unreal.log(f"[FixCamAnim] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def fix_bp(bp_path: str):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        log(f"skip {bp_path}")
        return
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    # Body faces movement; yaw not glued to controller/camera
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)

    move = cdo.get_editor_property("character_movement")
    if move:
        move.set_editor_property("orient_rotation_to_movement", True)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=500.0, roll=0.0))
        move.set_editor_property("max_walk_speed", 500.0)
        log(f"{bp_path} OrientToMovement=True UseControllerYaw=False")

    mesh = cdo.get_editor_property("mesh")
    if mesh:
        mesh.set_editor_property(
            "relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0)
        )
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
        abp = load(ABP_UNARMED)
        try:
            anim_class = abp.generated_class()
        except Exception:
            anim_class = abp.get_editor_property("generated_class")
        mesh.set_editor_property("anim_class", anim_class)
        log(f"{bp_path} AnimClass=ABP_Unarmed")

    # Camera follows mouse (control rotation), not actor facing
    try:
        for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
            boom.set_editor_property("use_pawn_control_rotation", True)
            boom.set_editor_property("inherit_pitch", True)
            boom.set_editor_property("inherit_yaw", True)
            boom.set_editor_property("inherit_roll", False)
            log(f"{bp_path} SpringArm UsePawnControlRotation=True")
    except Exception as exc:
        log(f"boom: {exc}")

    try:
        for cam in cdo.get_components_by_class(unreal.CameraComponent):
            cam.set_editor_property("use_pawn_control_rotation", False)
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass


def run():
    log("start")
    for p in BPS:
        fix_bp(p)
    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
