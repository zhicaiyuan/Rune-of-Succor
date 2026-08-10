# -*- coding: utf-8 -*-
"""
Classic TPS camera + body:
- UseControllerRotationYaw = False (looking does not spin pawn)
- OrientRotationToMovement = True (body faces WASD)
- UseControllerDesiredRotation = False
- SpringArm UsePawnControlRotation = True (boom follows mouse/control rot)
Dump every SCS/subobject along the way so we can see CameraBoom.
"""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[TPSv2] {m}")


def fix_boom_like(obj, label: str) -> bool:
    if not obj:
        return False
    name = ""
    try:
        name = str(obj.get_name())
    except Exception:
        pass
    cls = ""
    try:
        cls = str(obj.get_class().get_name())
    except Exception:
        cls = type(obj).__name__

    is_arm = isinstance(obj, unreal.SpringArmComponent) or (
        "SpringArm" in cls or "CameraBoom" in name
    )
    is_cam = isinstance(obj, unreal.CameraComponent) or (
        "CameraComponent" in cls and "Spring" not in cls
    )

    log(f"  see {label} name={name} cls={cls}")

    fixed = False
    if is_arm:
        for prop, val in (
            ("use_pawn_control_rotation", True),
            ("b_use_pawn_control_rotation", True),
            ("inherit_pitch", True),
            ("inherit_yaw", True),
            ("inherit_roll", False),
        ):
            try:
                obj.set_editor_property(prop, val)
                fixed = True
            except Exception:
                pass
        try:
            v = obj.get_editor_property("use_pawn_control_rotation")
            log(f"  FIXED boom {label} UsePawnControlRotation={v}")
        except Exception as exc:
            log(f"  boom set ok? {exc}")
    elif is_cam:
        try:
            obj.set_editor_property("use_pawn_control_rotation", False)
            log(f"  FIXED cam {label} UsePawnControlRotation=False")
            fixed = True
        except Exception:
            pass
    return fixed


def dump_and_fix_scs(bp) -> bool:
    found = False
    try:
        scs = bp.get_editor_property("simple_construction_script")
    except Exception as exc:
        log(f"no SCS: {exc}")
        return False
    if not scs:
        log("SCS is None")
        return False

    nodes = []
    for getter in ("get_all_nodes",):
        try:
            nodes = list(getattr(scs, getter)())
            break
        except Exception:
            pass
    if not nodes:
        for prop in ("all_nodes", "root_nodes"):
            try:
                nodes = list(scs.get_editor_property(prop) or [])
                if nodes:
                    break
            except Exception:
                pass

    log(f"SCS nodes={len(nodes)}")
    for node in nodes:
        tmpl = None
        for prop in ("component_template", "ComponentTemplate"):
            try:
                tmpl = node.get_editor_property(prop)
                if tmpl:
                    break
            except Exception:
                pass
        if tmpl and fix_boom_like(tmpl, "SCS"):
            found = True
        # Some UE versions expose variable name on node
        try:
            vname = node.get_variable_name()
            log(f"  node var={vname}")
        except Exception:
            pass
    return found


def dump_and_fix_subobjects(bp) -> bool:
    found = False
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    except Exception as exc:
        log(f"no SubobjectDataSubsystem: {exc}")
        return False

    handles = None
    for meth in (
        "k2_gather_subobject_data_for_blueprint",
        "gather_subobject_data_for_blueprint",
        "k2_gather_subobject_data_for_instance",
    ):
        try:
            handles = getattr(subsystem, meth)(bp)
            if handles is not None:
                log(f"subobjects via {meth}: {len(handles)}")
                break
        except Exception as exc:
            log(f"{meth}: {exc}")

    if not handles:
        return False

    for h in handles:
        obj = None
        for getter in (
            lambda: subsystem.k2_find_subobject_data_from_handle(h),
            lambda: subsystem.get_data_for_handle(h),
            lambda: subsystem.get_object_for_handle(h),
            lambda: h.get_object() if hasattr(h, "get_object") else None,
        ):
            try:
                obj = getter()
                if obj:
                    break
            except Exception:
                continue
        # handle may itself be SubobjectData
        if obj is not None and not isinstance(
            obj, (unreal.ActorComponent, unreal.Object)
        ):
            for prop in ("object", "Object", "component_template"):
                try:
                    cand = obj.get_editor_property(prop)
                    if cand:
                        obj = cand
                        break
                except Exception:
                    pass
        if fix_boom_like(obj, "SubObj"):
            found = True
    return found


def fix_cdo(bp) -> bool:
    found = False
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)

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

    # Export all editor properties that look like components
    try:
        for prop in cdo.get_editor_property("root_component").get_children_components(True):
            if fix_boom_like(prop, "CDO.child"):
                found = True
    except Exception as exc:
        log(f"children: {exc}")

    try:
        for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
            if fix_boom_like(boom, "CDO.class"):
                found = True
    except Exception as exc:
        log(f"by_class: {exc}")

    for name in (
        "camera_boom",
        "CameraBoom",
        "spring_arm",
        "SpringArm",
        "follow_camera",
        "FollowCamera",
    ):
        try:
            obj = cdo.get_editor_property(name)
            if fix_boom_like(obj, f"CDO.{name}"):
                found = True
        except Exception as exc:
            log(f"prop {name}: {exc}")

    # Reflect via dir / get_editor_property list
    try:
        for attr in dir(cdo):
            if "camera" in attr.lower() or "boom" in attr.lower() or "spring" in attr.lower():
                try:
                    obj = getattr(cdo, attr)
                    if isinstance(obj, unreal.ActorComponent):
                        if fix_boom_like(obj, f"dir.{attr}"):
                            found = True
                except Exception:
                    pass
    except Exception:
        pass

    log(
        f"VERIFY yawCtrl={cdo.get_editor_property('use_controller_rotation_yaw')} "
        f"orient={move.get_editor_property('orient_rotation_to_movement') if move else None} "
        f"desired={move.get_editor_property('use_controller_desired_rotation') if move else None}"
    )
    return found


def fix_bp(bp_path: str):
    log(f"==== {bp_path}")
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        log("missing")
        return
    found = False
    found = dump_and_fix_scs(bp) or found
    found = dump_and_fix_subobjects(bp) or found
    found = fix_cdo(bp) or found
    if not found:
        log("WARNING: never touched a SpringArm — relying on default template boom")
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    log(f"saved found_boom={found}")


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
