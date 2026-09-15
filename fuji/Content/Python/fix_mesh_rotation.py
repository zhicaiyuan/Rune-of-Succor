# -*- coding: utf-8 -*-
"""
Fix lying mesh: Unreal Python Rotator positional args are (roll, pitch, yaw),
NOT (pitch, yaw, roll). Previous scripts set Pitch=-90 by mistake.
Correct mannequin mesh: Pitch=0, Yaw=-90, Roll=0.
"""

from __future__ import annotations

import unreal

BPS = [
    "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter",
    "/Game/Variant_Combat/Blueprints/BP_CombatCharacter",
]


def log(m):
    unreal.log(f"[FixMeshRot] {m}")


def run():
    for bp_path in BPS:
        if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
            log(f"skip {bp_path}")
            continue
        bp = unreal.EditorAssetLibrary.load_asset(bp_path)
        try:
            gen = bp.generated_class()
        except Exception:
            gen = bp.get_editor_property("generated_class")
        cdo = unreal.get_default_object(gen)
        mesh = cdo.get_editor_property("mesh")
        before = mesh.get_editor_property("relative_rotation")
        log(f"{bp_path} BEFORE P={before.pitch} Y={before.yaw} R={before.roll}")

        # Named args — never use positional Rotator for this
        upright = unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0)
        mesh.set_editor_property("relative_rotation", upright)
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))

        after = mesh.get_editor_property("relative_rotation")
        log(f"{bp_path} AFTER  P={after.pitch} Y={after.yaw} R={after.roll}")

        unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        except Exception:
            pass

    log("DONE — mesh should stand. If anim still weird, next fix is IK retargeter.")


if __name__ == "__main__":
    run()
else:
    run()
