# -*- coding: utf-8 -*-
"""
Classic third-person:
- Camera (SpringArm) follows mouse / control rotation — NOT actor yaw
- Character faces movement (OrientRotationToMovement)
- UseControllerRotationYaw = False so looking around doesn't spin the body with the camera lock
"""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[TPSCam] {m}")


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
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)

    # Body does NOT lock to controller yaw
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)

    move = cdo.get_editor_property("character_movement")
    if move:
        # Face walk direction (classic TPS)
        move.set_editor_property("orient_rotation_to_movement", True)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=500.0, roll=0.0))
        move.set_editor_property("max_walk_speed", 600.0)
        move.set_editor_property("max_acceleration", 800.0)
        move.set_editor_property("braking_deceleration_walking", 1000.0)
        move.set_editor_property("ground_friction", 5.0)
        log(f"{bp_path} OrientToMovement=True UseControllerYaw=False")

    mesh = cdo.get_editor_property("mesh")
    if mesh:
        mesh.set_editor_property(
            "relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0)
        )
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
        if unreal.EditorAssetLibrary.does_asset_exist(ABP):
            abp = load(ABP)
            mesh.set_editor_property("anim_class", abp.generated_class())
            log(f"{bp_path} AnimClass=ABP_StrafeLocomotion")

    # SpringArm: follow control rotation (mouse), inherit yaw from controller not actor
    fixed_boom = False
    for name in ("camera_boom", "CameraBoom", "spring_arm", "SpringArm"):
        try:
            boom = cdo.get_editor_property(name)
        except Exception:
            boom = None
        if boom:
            boom.set_editor_property("use_pawn_control_rotation", True)
            try:
                boom.set_editor_property("inherit_pitch", True)
                boom.set_editor_property("inherit_yaw", True)
                boom.set_editor_property("inherit_roll", False)
            except Exception:
                pass
            fixed_boom = True
            log(f"{bp_path} {name} UsePawnControlRotation=True")
            break

    try:
        for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
            boom.set_editor_property("use_pawn_control_rotation", True)
            try:
                boom.set_editor_property("inherit_pitch", True)
                boom.set_editor_property("inherit_yaw", True)
                boom.set_editor_property("inherit_roll", False)
            except Exception:
                pass
            fixed_boom = True
            log(f"{bp_path} CDO SpringArm UsePawnControlRotation=True")
    except Exception as exc:
        log(f"boom scan: {exc}")

    # Camera itself should NOT use pawn control rotation (boom handles it)
    try:
        for cam in cdo.get_components_by_class(unreal.CameraComponent):
            cam.set_editor_property("use_pawn_control_rotation", False)
    except Exception:
        pass

    # SCS templates (blueprint components)
    try:
        scs = bp.get_editor_property("simple_construction_script")
    except Exception:
        scs = None
    if scs:
        try:
            nodes = scs.get_all_nodes()
        except Exception:
            try:
                nodes = scs.get_editor_property("all_nodes")
            except Exception:
                nodes = []
        for node in nodes or []:
            try:
                tmpl = node.get_editor_property("component_template")
            except Exception:
                tmpl = None
            if not tmpl:
                continue
            if isinstance(tmpl, unreal.SpringArmComponent):
                tmpl.set_editor_property("use_pawn_control_rotation", True)
                try:
                    tmpl.set_editor_property("inherit_pitch", True)
                    tmpl.set_editor_property("inherit_yaw", True)
                    tmpl.set_editor_property("inherit_roll", False)
                except Exception:
                    pass
                fixed_boom = True
                log(f"{bp_path} SCS SpringArm fixed")
            elif isinstance(tmpl, unreal.CameraComponent):
                tmpl.set_editor_property("use_pawn_control_rotation", False)

    # SubobjectDataSubsystem pass
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
        for h in handles or []:
            try:
                obj = subsystem.get_object_for_handle(h)
            except Exception:
                try:
                    obj = h.get_object()
                except Exception:
                    obj = None
            if isinstance(obj, unreal.SpringArmComponent):
                obj.set_editor_property("use_pawn_control_rotation", True)
                fixed_boom = True
                log(f"{bp_path} subobject SpringArm fixed")
            elif isinstance(obj, unreal.CameraComponent):
                obj.set_editor_property("use_pawn_control_rotation", False)
    except Exception as exc:
        log(f"subobject: {exc}")

    if not fixed_boom:
        log(f"WARNING: SpringArm not found on {bp_path}")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass

    # Verify
    yaw = cdo.get_editor_property("use_controller_rotation_yaw")
    orient = move.get_editor_property("orient_rotation_to_movement") if move else None
    desired = move.get_editor_property("use_controller_desired_rotation") if move else None
    log(f"VERIFY {bp_path} yawCtrl={yaw} orientMove={orient} desiredRot={desired}")


def run():
    log("start")
    for p in BPS:
        fix_bp(p)
    log("done — classic TPS: mouse aims camera, body faces WASD")


if __name__ == "__main__":
    run()
else:
    run()
