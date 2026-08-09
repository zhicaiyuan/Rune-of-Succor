# -*- coding: utf-8 -*-
"""Verify ordinary locomotion setup; add Mouse2D look; ensure character/ABP/BS/turn assets."""

from __future__ import annotations

import unreal

IMC = "/Game/Input/IMC_Default"
IA_LOOK = "/Game/Input/Actions/IA_Look"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
IKR = f"{OUT}/IK/IKR_SwordToCharacters"


def log(m):
    unreal.log(f"[VerifyFinish] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def make_key(name: str):
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name(name))
    return key


def ensure_mouse_look():
    imc = load(IMC)
    dkm = imc.get_editor_property("default_key_mappings")
    mappings = list(dkm.get_editor_property("mappings") or [])
    has_mouse = False
    for m in mappings:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = str(k.get_editor_property("key_name")) if k else ""
        if a and "IA_Look" in a.get_path_name() and "Mouse" in kn:
            has_mouse = True
    if not has_mouse:
        ia = load(IA_LOOK)
        m = unreal.EnhancedActionKeyMapping()
        m.set_editor_property("action", ia)
        m.set_editor_property("key", make_key("Mouse2D"))
        # Copy negate Y modifier from gamepad look if present
        for src in mappings:
            sa = src.get_editor_property("action")
            if sa and "IA_Look" in sa.get_path_name():
                try:
                    mods = list(src.get_editor_property("modifiers") or [])
                    m.set_editor_property("modifiers", mods)
                except Exception:
                    pass
                break
        mappings.append(m)
        dkm.set_editor_property("mappings", mappings)
        imc.set_editor_property("default_key_mappings", dkm)
        unreal.EditorAssetLibrary.save_asset(IMC, only_if_is_dirty=False)
        log("added Mouse2D -> IA_Look")
    else:
        log("Mouse look already present")


def ensure_character():
    bp = load(CHAR_BP)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("max_walk_speed", 600.0)
    move.set_editor_property("max_walk_speed_crouched", 200.0)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("braking_deceleration_walking", 1000.0)
    move.set_editor_property("ground_friction", 5.0)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=360.0, roll=0.0))
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        mesh.set_editor_property("anim_class", load(ABP).generated_class())
    for name in ("camera_boom", "CameraBoom"):
        try:
            boom = cdo.get_editor_property(name)
            if boom:
                boom.set_editor_property("use_pawn_control_rotation", True)
        except Exception:
            pass
    unreal.EditorAssetLibrary.save_asset(CHAR_BP, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    r = mesh.get_editor_property("relative_rotation")
    log(
        f"char speed={move.get_editor_property('max_walk_speed')} "
        f"accel={move.get_editor_property('max_acceleration')} "
        f"desiredRot={move.get_editor_property('use_controller_desired_rotation')} "
        f"mesh=P{r.pitch}Y{r.yaw} "
        f"anim={mesh.get_editor_property('anim_class')}"
    )


def verify_assets():
    checks = {
        "IKR": IKR,
        "BS": BS,
        "ABP": ABP,
        "Idle_RTG": f"{OUT}/SwordRTG/Idle_Seq_RTG",
        "Walk_RTG": f"{OUT}/SwordRTG/Walk_Loop_F_0_Seq_RTG",
        "Run_RTG": f"{OUT}/SwordRTG/Run_Loop_F_0_Seq_RTG",
        "Turn90L_RTG": f"{OUT}/SwordRTG/Turn_90_L_Seq_RTG",
        "Turn90R_RTG": f"{OUT}/SwordRTG/Turn_90_R_Seq_RTG",
        "Turn180L_RTG": f"{OUT}/SwordRTG/Turn_180_L_Seq_RTG",
        "Turn180R_RTG": f"{OUT}/SwordRTG/Turn_180_R_Seq_RTG",
        "AM_Turn90L": f"{OUT}/Montages/AM_Turn_90_L",
        "IA_Walk": "/Game/Input/Actions/IA_Walk",
    }
    ok = True
    for name, path in checks.items():
        exists = unreal.EditorAssetLibrary.does_asset_exist(path)
        log(f"{'OK' if exists else 'MISS'} {name}: {path}")
        ok = ok and exists

    # BS samples
    bs = load(BS)
    samples = list(bs.get_editor_property("sample_data") or [])
    log(f"BS samples={len(samples)}")
    if samples:
        a0 = samples[0].get_editor_property("animation")
        log(f"BS sample0={a0.get_path_name() if a0 else None}")

    # IMC walk
    imc = load(IMC)
    dkm = imc.get_editor_property("default_key_mappings")
    mappings = list(dkm.get_editor_property("mappings") or [])
    walk = [m for m in mappings if m.get_editor_property("action") and "IA_Walk" in m.get_editor_property("action").get_path_name()]
    log(f"IMC total={len(mappings)} walk_maps={len(walk)}")
    return ok


def run():
    log("start")
    ensure_mouse_look()
    ensure_character()
    ok = verify_assets()
    log("ALL OK" if ok else "SOME MISSING")
    log(
        "Controls: WASD 8-dir, mouse look, hold LeftAlt=walk(~200 via input scale), "
        "release=run accel to 600. Body faces camera (desired rot). "
        "Turn montages on DefaultSlot; body turns via RotationRate toward look."
    )
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
