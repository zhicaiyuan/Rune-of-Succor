# -*- coding: utf-8 -*-
"""Resolve CameraBoom via SubobjectDataBlueprintFunctionLibrary and force TPS camera."""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[BoomLib] {m}")


def fix_character_movement(cdo):
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    move = cdo.get_editor_property("character_movement")
    if move:
        move.set_editor_property("orient_rotation_to_movement", True)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=500.0, roll=0.0))
        move.set_editor_property("max_walk_speed", 600.0)
        move.set_editor_property("max_acceleration", 800.0)
        move.set_editor_property("braking_deceleration_walking", 1000.0)
        move.set_editor_property("ground_friction", 5.0)
    mesh = cdo.get_editor_property("mesh")
    if mesh:
        mesh.set_editor_property(
            "relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0)
        )
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
        if unreal.EditorAssetLibrary.does_asset_exist(ABP):
            abp = unreal.EditorAssetLibrary.load_asset(ABP)
            mesh.set_editor_property("anim_class", abp.generated_class())


def resolve_object(lib, data, bp):
    for meth, args in (
        ("get_object", (data,)),
        ("get_object_for_blueprint", (data, bp)),
        ("get_associated_object", (data,)),
    ):
        try:
            obj = getattr(lib, meth)(*args)
            if obj:
                return obj, meth
        except Exception as exc:
            log(f"  {meth}: {exc}")
    return None, None


def fix_bp(bp_path: str):
    log(f"==== {bp_path}")
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    fix_character_movement(cdo)

    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)

    boom_ok = False
    cam_ok = False
    for h in handles:
        data = None
        try:
            data = lib.get_data(h)
        except Exception:
            try:
                data = subsystem.k2_find_subobject_data_from_handle(h)
            except Exception:
                continue
        if not data:
            continue

        # variable / display name
        vname = None
        dname = None
        for meth in ("get_variable_name", "get_display_name"):
            try:
                val = getattr(lib, meth)(data)
                if meth.endswith("variable_name"):
                    vname = str(val)
                else:
                    dname = str(val)
            except Exception as exc:
                log(f"  name via data.{meth}: {exc}")

        obj, via = resolve_object(lib, data, bp)
        if not obj:
            log(f"  no object vname={vname} dname={dname}")
            continue

        cls = obj.get_class().get_name()
        name = obj.get_name()
        log(f"  obj via={via} name={name} cls={cls} vname={vname} dname={dname}")

        if isinstance(obj, unreal.SpringArmComponent) or "SpringArm" in cls:
            obj.set_editor_property("use_pawn_control_rotation", True)
            try:
                obj.set_editor_property("inherit_pitch", True)
                obj.set_editor_property("inherit_yaw", True)
                obj.set_editor_property("inherit_roll", False)
            except Exception:
                pass
            v = obj.get_editor_property("use_pawn_control_rotation")
            log(f"  BOOM UsePawnControlRotation={v}")
            boom_ok = True
        elif isinstance(obj, unreal.CameraComponent) or cls == "CameraComponent":
            obj.set_editor_property("use_pawn_control_rotation", False)
            v = obj.get_editor_property("use_pawn_control_rotation")
            log(f"  CAM UsePawnControlRotation={v}")
            cam_ok = True

    log(
        f"VERIFY yaw={cdo.get_editor_property('use_controller_rotation_yaw')} "
        f"orient={cdo.get_editor_property('character_movement').get_editor_property('orient_rotation_to_movement')} "
        f"desired={cdo.get_editor_property('character_movement').get_editor_property('use_controller_desired_rotation')} "
        f"boom={boom_ok} cam={cam_ok}"
    )

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)


def run():
    log("start")
    for p in BPS:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            fix_bp(p)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
