# -*- coding: utf-8 -*-
"""Diagnose why character still lies on ground."""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP_STRAFE = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
ABP_UNARMED = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
IDLE_RTG = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Idle_Seq_RTG"
IDLE_SRC = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"
WALK_RTG = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Walk_Loop_F_0_Seq_RTG"
CHAR_SKEL = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
SWORD_SKEL = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SK_Mannequin"
IKR = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/NewIKRetargeter"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
QUINN = "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"


def log(m):
    unreal.log(f"[DiagLie] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def dump_rotator(r):
    try:
        return f"P={r.pitch:.2f} Y={r.yaw:.2f} R={r.roll:.2f}"
    except Exception:
        return str(r)


def dump_vec(v):
    try:
        return f"X={v.x:.2f} Y={v.y:.2f} Z={v.z:.2f}"
    except Exception:
        return str(v)


def anim_info(path):
    a = load(path)
    if not a:
        log(f"ANIM missing {path}")
        return
    skel = a.get_editor_property("skeleton")
    log(f"ANIM {path}")
    log(f"  skeleton={skel.get_path_name() if skel else None}")
    try:
        log(f"  additive={a.get_editor_property('additive_anim_type')}")
    except Exception:
        pass
    try:
        log(f"  root_motion={a.get_editor_property('enable_root_motion')}")
    except Exception:
        pass
    try:
        log(f"  force_root_lock={a.get_editor_property('force_root_lock')}")
    except Exception:
        pass
    # bone track names sample
    try:
        names = a.get_animation_track_names()
        log(f"  tracks={len(names)} first={list(names)[:8]}")
    except Exception as exc:
        log(f"  tracks err: {exc}")


def run():
    log("==== character ====")
    bp = load(CHAR_BP)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    mesh = cdo.get_editor_property("mesh")
    log(f"mesh rot {dump_rotator(mesh.get_editor_property('relative_rotation'))}")
    log(f"mesh loc {dump_vec(mesh.get_editor_property('relative_location'))}")
    sm = mesh.get_editor_property("skeletal_mesh_asset")
    log(f"skeletal_mesh={sm.get_path_name() if sm else None}")
    if sm:
        log(f"  mesh.skeleton={sm.get_editor_property('skeleton').get_path_name()}")
    anim_class = mesh.get_editor_property("anim_class")
    log(f"anim_class={anim_class}")
    try:
        log(f"anim_class path={anim_class.get_path_name()}")
    except Exception:
        pass

    log("==== ABP ====")
    for p in [ABP_STRAFE, ABP_UNARMED]:
        abp = load(p)
        if not abp:
            log(f"missing {p}")
            continue
        log(f"ABP {p} class={abp.generated_class()}")
        try:
            skel = abp.get_editor_property("target_skeleton")
            log(f"  target_skeleton={skel.get_path_name() if skel else None}")
        except Exception as exc:
            log(f"  target_skeleton err {exc}")

    log("==== BS ====")
    bs = load(ALIAS_BS)
    if bs:
        skel = bs.get_editor_property("skeleton")
        log(f"BS skeleton={skel.get_path_name() if skel else None}")
        samples = bs.get_editor_property("sample_data") or []
        log(f"BS samples={len(samples)}")
        for i, s in enumerate(list(samples)[:5]):
            anim = s.get_editor_property("animation")
            val = s.get_editor_property("sample_value")
            log(f"  [{i}] {dump_vec(val)} -> {anim.get_path_name() if anim else None}")
            if anim:
                ask = anim.get_editor_property("skeleton")
                log(f"       animskel={ask.get_path_name() if ask else None}")

    log("==== anims ====")
    anim_info(IDLE_SRC)
    anim_info(IDLE_RTG)
    anim_info(WALK_RTG)

    log("==== IK Retargeter ====")
    ikr = load(IKR)
    if ikr:
        log(f"IKR={ikr.get_path_name()}")
        for prop in [
            "source_ik_rig_asset",
            "target_ik_rig_asset",
            "source_preview_mesh",
            "target_preview_mesh",
        ]:
            try:
                v = ikr.get_editor_property(prop)
                log(f"  {prop}={v.get_path_name() if v else None}")
            except Exception as exc:
                log(f"  {prop} err {exc}")

    log("==== meshes ====")
    for p in [SRC_MESH, TGT_MESH, QUINN]:
        m = load(p)
        if not m:
            log(f"missing {p}")
            continue
        sk = m.get_editor_property("skeleton")
        log(f"{p} skel={sk.get_path_name() if sk else None}")

    # Check if Idle_RTG bone transforms look upright by sampling root/pelvis at t=0
    try:
        anim = load(IDLE_RTG)
        if anim:
            # Get ref pose / compressed data via controller if available
            log(f"Idle_RTG num_frames={anim.get_number_of_sampled_keys()}")
            log(f"Idle_RTG length={anim.get_play_length()}")
    except Exception as exc:
        log(f"idle frame err {exc}")

    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
