# -*- coding: utf-8 -*-
"""Force SpringArm UsePawnControlRotation on character BPs (SCS + CDO)."""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]


def log(m):
    unreal.log(f"[FixBoom] {m}")


def fix_object(obj, label: str):
    if not obj:
        return
    try:
        if isinstance(obj, unreal.SpringArmComponent):
            obj.set_editor_property("use_pawn_control_rotation", True)
            obj.set_editor_property("inherit_pitch", True)
            obj.set_editor_property("inherit_yaw", True)
            obj.set_editor_property("inherit_roll", False)
            log(f"{label}: SpringArm UsePawnControlRotation=True")
        elif isinstance(obj, unreal.CameraComponent):
            obj.set_editor_property("use_pawn_control_rotation", False)
            log(f"{label}: Camera UsePawnControlRotation=False")
    except Exception as exc:
        log(f"{label} err: {exc}")


def walk_scs(bp):
    try:
        scs = bp.get_editor_property("simple_construction_script")
    except Exception:
        return
    if not scs:
        return
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
        if tmpl:
            fix_object(tmpl, f"SCS.{tmpl.get_name()}")


def run():
    for bp_path in BPS:
        if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
            continue
        bp = unreal.EditorAssetLibrary.load_asset(bp_path)
        walk_scs(bp)

        try:
            gen = bp.generated_class()
        except Exception:
            gen = bp.get_editor_property("generated_class")
        cdo = unreal.get_default_object(gen)

        # CDO components
        try:
            for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
                fix_object(boom, f"CDO.{boom.get_name()}")
        except Exception as exc:
            log(f"CDO boom: {exc}")

        # Also try common property names
        for name in ("camera_boom", "CameraBoom", "spring_arm", "SpringArm"):
            try:
                boom = cdo.get_editor_property(name)
                fix_object(boom, f"prop.{name}")
            except Exception:
                pass

        # Movement/camera ownership again
        cdo.set_editor_property("use_controller_rotation_yaw", False)
        move = cdo.get_editor_property("character_movement")
        if move:
            move.set_editor_property("orient_rotation_to_movement", True)

        unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        except Exception:
            pass
        log(f"saved {bp_path}")
    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
