# -*- coding: utf-8 -*-
"""
IK-retarget Sword Sequence2 Idle/Walk/Run loops onto Characters Mannequin,
SAVE them, rebuild BS_WalkRun_Sword, switch to ABP_StrafeLocomotion.
"""

from __future__ import annotations

import unreal

RETARGET_DIR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
ABP_STRAFE = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
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
    unreal.log(f"[SwordRTG] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def ensure_dir(path: str):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def package_path_from_asset_data(ad) -> str:
    # /Game/.../Name.Name -> /Game/.../Name
    try:
        obj = ad.get_asset()
        if obj:
            return obj.get_path_name().split(".")[0]
    except Exception:
        pass
    try:
        pkg = str(ad.package_name)
        return pkg
    except Exception:
        return ""


def retarget_all() -> dict:
    ikr = load(IK_RETARGETER)
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)
    ensure_dir(RETARGET_DIR)

    srcs = [SRC_IDLE] + SRC_WALKS + SRC_RUNS
    datas = [unreal.EditorAssetLibrary.find_asset_data(p) for p in srcs if unreal.EditorAssetLibrary.does_asset_exist(p)]

    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", datas)
    inputs.set_editor_property("source_mesh", src_mesh)
    inputs.set_editor_property("target_mesh", tgt_mesh)
    inputs.set_editor_property("ik_retarget_asset", ikr)
    inputs.set_editor_property("search", "")
    inputs.set_editor_property("replace", "")
    inputs.set_editor_property("prefix", "")
    inputs.set_editor_property("suffix", "_RTG")
    inputs.set_editor_property("target_path", RETARGET_DIR)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", True)
    inputs.set_editor_property("retain_additive_flags", True)

    log(f"RunBatchRetarget count={len(datas)} -> {RETARGET_DIR}")
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs) or []
    log(f"created assets: {len(created)}")

    saved = 0
    created_paths = []
    for ad in created:
        path = package_path_from_asset_data(ad)
        if not path:
            continue
        created_paths.append(path)
        ok = unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
        saved += 1 if ok else 0
        log(f"  save {path}: {ok}")

    # Also save directory recursively
    try:
        unreal.EditorAssetLibrary.save_directory(RETARGET_DIR, only_if_is_dirty=False, recursive=True)
        log("save_directory done")
    except Exception as exc:
        log(f"save_directory: {exc}")

    log(f"saved {saved}/{len(created)}")

    # Map by source basename
    anim_map = {}
    for p in srcs:
        name = p.split("/")[-1]
        cand = f"{RETARGET_DIR}/{name}_RTG"
        if unreal.EditorAssetLibrary.does_asset_exist(cand):
            anim_map[p] = cand
            continue
        # match against created list
        for cp in created_paths:
            if cp.endswith(f"/{name}_RTG") or cp.split("/")[-1].startswith(f"{name}_RTG"):
                anim_map[p] = cp
                break
    log(f"mapped {len(anim_map)}/{len(srcs)}")
    return anim_map


def update_bs(anim_map: dict) -> int:
    tgt_mesh = load(TGT_MESH)
    if not unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS):
        factory = unreal.BlendSpaceFactoryNew()
        factory.set_editor_property("target_skeleton", tgt_mesh.get_editor_property("skeleton"))
        factory.set_editor_property("preview_skeletal_mesh", tgt_mesh)
        bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BS_WalkRun_Sword",
            "/Game/Characters/Mannequins/Anims/Unarmed",
            unreal.BlendSpace,
            factory,
        )
        if not bs:
            raise RuntimeError("create BS failed")
    else:
        bs = load(ALIAS_BS)

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
        if src not in anim_map:
            log(f"skip unmapped {src}")
            continue
        anim = load(anim_map[src])
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)

    bs.set_editor_property("sample_data", samples)
    unreal.EditorAssetLibrary.save_asset(ALIAS_BS, only_if_is_dirty=False)
    log(f"BS samples={len(samples)}")
    if samples:
        a0 = samples[0].get_editor_property("animation")
        log(f"sample0={a0.get_path_name() if a0 else None}")
    return len(samples)


def fix_character(bp_path: str):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        return
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
    # Rotator positional = (roll, pitch, yaw). Always use named args.
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
    log(f"{bp_path} -> ABP_StrafeLocomotion")


def run():
    log("start")
    anim_map = retarget_all()
    needed = len([SRC_IDLE] + SRC_WALKS + SRC_RUNS)
    if len(anim_map) < needed:
        raise RuntimeError(f"retarget incomplete {len(anim_map)}/{needed}")

    n = update_bs(anim_map)
    if n < 20:
        raise RuntimeError(f"BS samples too few: {n}")

    fix_character(CHAR_BP)
    fix_character(COMBAT_BP)
    log("DONE")


if __name__ == "__main__":
    run()
else:
    run()
