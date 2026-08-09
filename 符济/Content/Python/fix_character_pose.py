# -*- coding: utf-8 -*-
"""
Fix character lying on ground:
1) Reset Mesh RelativeRotation to (0, -90, 0)
2) Keep strafe movement settings
3) Prefer ABP_Unarmed first (stable stand). Optionally keep Strafe ABP if mesh matches.
4) Try IK retarget Sword loops -> Characters skeleton and rebuild BS_WalkRun_Sword
"""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
ABP_UNARMED = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
ABP_STRAFE = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
RETARGET_DIR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/Retargeted"
IK_RETARGETER = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/NewIKRetargeter"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
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
    unreal.log(f"[FixPose] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def fix_character(bp_path: str, use_unarmed: bool = True):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        log(f"skip {bp_path}")
        return
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    # Strafe movement (keep)
    try:
        cdo.set_editor_property("use_controller_rotation_yaw", True)
        cdo.set_editor_property("use_controller_rotation_pitch", False)
        cdo.set_editor_property("use_controller_rotation_roll", False)
        move = cdo.get_editor_property("character_movement")
        if move:
            move.set_editor_property("orient_rotation_to_movement", False)
            move.set_editor_property("use_controller_desired_rotation", False)
            move.set_editor_property("max_walk_speed", 250.0)
            move.set_editor_property("max_acceleration", 1000.0)
            move.set_editor_property("braking_deceleration_walking", 1200.0)
    except Exception as exc:
        log(f"move: {exc}")

    mesh = cdo.get_editor_property("mesh")
    if mesh:
        # Critical: mannequin must be Yaw -90, Pitch/Roll 0 — lying usually means Pitch±90
        # Rotator positional = (roll, pitch, yaw). Always use named args.
        mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
        log(f"{bp_path} mesh rot set to P0 Y-90 R0, loc z=-90")

        # Ensure Quinn/Manny characters mesh (not null)
        if not mesh.get_editor_property("skeletal_mesh_asset"):
            sm = unreal.EditorAssetLibrary.load_asset(
                "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"
            )
            if sm:
                mesh.set_editor_property("skeletal_mesh_asset", sm)

        abp_path = ABP_UNARMED if use_unarmed else ABP_STRAFE
        if unreal.EditorAssetLibrary.does_asset_exist(abp_path):
            abp = load(abp_path)
            try:
                anim_class = abp.generated_class()
            except Exception:
                anim_class = abp.get_editor_property("generated_class")
            mesh.set_editor_property("anim_class", anim_class)
            log(f"{bp_path} AnimClass -> {abp_path}")

    try:
        for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
            boom.set_editor_property("use_pawn_control_rotation", True)
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"fixed {bp_path}")


def try_retarget_and_rebuild_bs() -> bool:
    """Return True if retargeted anims ready and BS rebuilt."""
    ikr = unreal.EditorAssetLibrary.load_asset(IK_RETARGETER)
    src_mesh = unreal.EditorAssetLibrary.load_asset(SRC_MESH)
    tgt_mesh = unreal.EditorAssetLibrary.load_asset(TGT_MESH)
    if not (ikr and src_mesh and tgt_mesh):
        log("IK retarget assets missing")
        return False

    if not unreal.EditorAssetLibrary.does_directory_exist(RETARGET_DIR):
        unreal.EditorAssetLibrary.make_directory(RETARGET_DIR)

    srcs = [SRC_IDLE] + SRC_WALKS + SRC_RUNS
    datas = []
    for p in srcs:
        try:
            datas.append(unreal.EditorAssetLibrary.find_asset_data(p))
        except Exception:
            pass
    if not datas:
        return False

    try:
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            datas, src_mesh, tgt_mesh, ikr, "", "", "_RTG", RETARGET_DIR
        )
    except Exception as exc:
        log(f"IK retarget failed: {exc}")
        return False

    # Map results
    anim_map = {}
    for p in srcs:
        name = p.split("/")[-1]
        cand = f"{RETARGET_DIR}/{name}_RTG"
        if unreal.EditorAssetLibrary.does_asset_exist(cand):
            anim_map[p] = cand
    log(f"retargeted {len(anim_map)}/{len(srcs)}")
    if len(anim_map) < len(srcs):
        return False

    # Rebuild alias BS on Characters skeleton with retargeted clips
    char_skel = tgt_mesh.get_editor_property("skeleton")
    if unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS):
        unreal.EditorAssetLibrary.delete_asset(ALIAS_BS)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", char_skel)
    factory.set_editor_property("preview_skeletal_mesh", tgt_mesh)
    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BS_WalkRun_Sword",
        "/Game/Characters/Mannequins/Anims/Unarmed",
        unreal.BlendSpace,
        factory,
    )
    if not bs:
        log("create BS failed")
        return False

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

    walk_dirs = [0, -45, 45, -90, 90, 180, -180, -135, 135, -157.5, 157.5]
    # SRC_WALKS order matches walk_dirs used previously (10 unique + duplicate 180)
    # Rebuild with explicit pairs:
    pairs = [(SRC_IDLE, 0.0, 0.0), (SRC_IDLE, -90.0, 0.0), (SRC_IDLE, 90.0, 0.0),
             (SRC_IDLE, 180.0, 0.0), (SRC_IDLE, -180.0, 0.0)]
    wdirs = [0.0, -45.0, 45.0, -90.0, 90.0, 180.0, -135.0, 135.0, -157.5, 157.5]
    # SRC_WALKS has 10 items including both 180 entries in old map; use first 10 with:
    wdirs_full = [0.0, -45.0, 45.0, -90.0, 90.0, 180.0, -135.0, 135.0, -157.5, 157.5]
    # Actually SRC_WALKS list order:
    # F0, FL45, FR45, FL90, FR90, B180, BL45, BR45, BL90, BR90
    wdirs_full = [0.0, -45.0, 45.0, -90.0, 90.0, 180.0, -135.0, 135.0, -157.5, 157.5]
    for p, d in zip(SRC_WALKS, wdirs_full):
        pairs.append((p, d, 200.0))
    pairs.append((SRC_WALKS[5], -180.0, 200.0))  # B180 also at -180
    for p, d in zip(SRC_RUNS, wdirs_full):
        pairs.append((p, d, 500.0))
    pairs.append((SRC_RUNS[5], -180.0, 500.0))

    samples = []
    for src, direction, speed in pairs:
        anim = load(anim_map[src])
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)
    bs.set_editor_property("sample_data", samples)
    unreal.EditorAssetLibrary.save_asset(ALIAS_BS, only_if_is_dirty=False)
    log(f"BS rebuilt with retargeted anims, samples={len(samples)}")
    return True


def run():
    log("Start pose fix...")
    # Immediate: stand upright with stock ABP (known good)
    fix_character(CHAR_BP, use_unarmed=True)
    fix_character(COMBAT_BP, use_unarmed=True)

    # Try proper sword retarget for later; if success, switch strafe ABP back
    ok = try_retarget_and_rebuild_bs()
    if ok:
        # Point strafe ABP is already on BS_WalkRun_Sword; switch characters to strafe ABP
        fix_character(CHAR_BP, use_unarmed=False)
        fix_character(COMBAT_BP, use_unarmed=False)
        log("DONE with retargeted Sword anims + strafe ABP")
    else:
        log("DONE with ABP_Unarmed (standing). Sword anims still need editor IK Retarget — see chat.")
        log("Character should no longer lie on the ground.")


if __name__ == "__main__":
    run()
else:
    run()
