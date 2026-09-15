# -*- coding: utf-8 -*-
"""Rebuild/update BS_WalkRun_Sword from already-retargeted SwordRTG clips, enable strafe ABP."""

from __future__ import annotations

import unreal

RETARGET_DIR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
ABP_STRAFE = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"

SRC_IDLE = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"
SRC_WALKS = [
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Loop_F_0_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/02_Walk_F_L_45/Walk_Loop_F_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/03_Walk_F_R_45/Walk_Loop_F_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/04_Walk_F_L_90/Walk_Loop_F_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/05_Walk_F_R_90/Walk_Loop_F_R_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/07_Walk_B_L_45/Walk_Loop_B_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/08_Walk_B_R_45/Walk_Loop_B_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/09_Walk_B_L_90/Walk_Loop_B_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/10_Walk_B_R_90/Walk_Loop_B_R_90_Seq",
]
SRC_RUNS = [
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Loop_F_0_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/02_Run_F_L_45/Run_Loop_F_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/03_Run_F_R_45/Run_Loop_F_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/04_Run_F_L_90/Run_Loop_F_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/05_Run_F_R_90/Run_Loop_F_R_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/07_Run_B_L_45/Run_Loop_B_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/08_Run_B_R_45/Run_Loop_B_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/09_Run_B_L_90/Run_Loop_B_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/10_Run_B_R_90/Run_Loop_B_R_90_Seq",
]


def log(m):
    unreal.log(f"[RebuildBS] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def rtg_path(src: str) -> str:
    name = src.split("/")[-1]
    return f"{RETARGET_DIR}/{name}_RTG"


def force_recreate_bs(skel, mesh):
    # Rename old aside, then create fresh
    old = ALIAS_BS
    trash = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword_OLD"
    if unreal.EditorAssetLibrary.does_asset_exist(old):
        if unreal.EditorAssetLibrary.does_asset_exist(trash):
            unreal.EditorAssetLibrary.delete_asset(trash)
        ok = unreal.EditorAssetLibrary.rename_asset(old, trash)
        log(f"rename old BS -> OLD: {ok}")
        if unreal.EditorAssetLibrary.does_asset_exist(trash):
            unreal.EditorAssetLibrary.delete_asset(trash)
            log("deleted OLD")

    # Fix redirectors in folder
    try:
        unreal.EditorAssetLibrary.fix_up_redirectors("/Game/Characters/Mannequins/Anims/Unarmed")
    except Exception as exc:
        log(f"fixup: {exc}")

    if unreal.EditorAssetLibrary.does_asset_exist(old):
        log("old BS still exists after rename/delete; will update in place")
        return load(old)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", skel)
    factory.set_editor_property("preview_skeletal_mesh", mesh)
    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BS_WalkRun_Sword",
        "/Game/Characters/Mannequins/Anims/Unarmed",
        unreal.BlendSpace,
        factory,
    )
    if not bs:
        raise RuntimeError("create_asset BS failed")
    return bs


def update_bs_samples(bs):
    x = unreal.BlendParameter()
    x.set_editor_property("display_name", "Direction")
    x.set_editor_property("min", -180.0)
    x.set_editor_property("max", 180.0)
    x.set_editor_property("grid_num", 8)
    y = unreal.BlendParameter()
    y.set_editor_property("display_name", "Speed")
    y.set_editor_property("min", 0.0)
    y.set_editor_property("max", 600.0)
    y.set_editor_property("grid_num", 4)
    bs.set_editor_property("blend_parameters", [x, y])

    dirs = [0.0, -45.0, 45.0, -90.0, 90.0, 180.0, -135.0, 135.0, -157.5, 157.5]
    pairs = [
        (SRC_IDLE, 0.0, 0.0),
        (SRC_IDLE, -90.0, 0.0),
        (SRC_IDLE, 90.0, 0.0),
        (SRC_IDLE, 180.0, 0.0),
        (SRC_IDLE, -180.0, 0.0),
    ]
    for p, d in zip(SRC_WALKS, dirs):
        pairs.append((p, d, 200.0))
    pairs.append((SRC_WALKS[5], -180.0, 200.0))
    for p, d in zip(SRC_RUNS, dirs):
        pairs.append((p, d, 500.0))
    pairs.append((SRC_RUNS[5], -180.0, 500.0))

    samples = []
    for src, direction, speed in pairs:
        path = rtg_path(src)
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log(f"missing RTG {path}")
            continue
        anim = load(path)
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)

    bs.set_editor_property("sample_data", samples)
    unreal.EditorAssetLibrary.save_asset(ALIAS_BS, only_if_is_dirty=False)
    log(f"samples set: {len(samples)}")
    return len(samples)


def fix_character(bp_path: str):
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    cdo.set_editor_property("use_controller_rotation_yaw", True)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    move = cdo.get_editor_property("character_movement")
    if move:
        move.set_editor_property("orient_rotation_to_movement", False)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("max_walk_speed", 250.0)

    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))

    abp = load(ABP_STRAFE)
    try:
        anim_class = abp.generated_class()
    except Exception:
        anim_class = abp.get_editor_property("generated_class")
    mesh.set_editor_property("anim_class", anim_class)

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"{bp_path} AnimClass=ABP_StrafeLocomotion mesh=(0,-90,0)")


def run():
    log("start")
    mesh = load(TGT_MESH)
    skel = mesh.get_editor_property("skeleton")

    # Prefer in-place update if exists, else recreate
    if unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS):
        bs = load(ALIAS_BS)
        log("updating existing BS in place")
    else:
        bs = force_recreate_bs(skel, mesh)

    n = update_bs_samples(bs)
    if n < 20:
        raise RuntimeError(f"too few samples: {n}")

    # Verify first sample skeleton
    sd = bs.get_editor_property("sample_data")
    if sd:
        anim0 = sd[0].get_editor_property("animation")
        log(f"sample0={anim0.get_path_name() if anim0 else None}")

    fix_character(CHAR_BP)
    if unreal.EditorAssetLibrary.does_asset_exist(COMBAT_BP):
        fix_character(COMBAT_BP)
    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
