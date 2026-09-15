# -*- coding: utf-8 -*-
"""Recreate BS_WalkRun_Locomotion on Characters Mannequin skeleton and re-bind ABP."""

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
BS_PATH = f"{OUT}/BS_WalkRun_Locomotion"
ALIAS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
ABP = f"{OUT}/ABP_StrafeLocomotion"
CHAR_MESH_SK = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
CHAR_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
SWORD_SK = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SK_Mannequin"

IDLE = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"
WALKS = [
    (0.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Loop_F_0_Seq"),
    (-45.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/02_Walk_F_L_45/Walk_Loop_F_L_45_Seq"),
    (45.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/03_Walk_F_R_45/Walk_Loop_F_R_45_Seq"),
    (-90.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/04_Walk_F_L_90/Walk_Loop_F_L_90_Seq"),
    (90.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/05_Walk_F_R_90/Walk_Loop_F_R_90_Seq"),
    (180.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq"),
    (-180.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq"),
    (-135.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/07_Walk_B_L_45/Walk_Loop_B_L_45_Seq"),
    (135.0, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/08_Walk_B_R_45/Walk_Loop_B_R_45_Seq"),
    (-157.5, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/09_Walk_B_L_90/Walk_Loop_B_L_90_Seq"),
    (157.5, "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/10_Walk_B_R_90/Walk_Loop_B_R_90_Seq"),
]
RUNS = [
    (0.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Loop_F_0_Seq"),
    (-45.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/02_Run_F_L_45/Run_Loop_F_L_45_Seq"),
    (45.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/03_Run_F_R_45/Run_Loop_F_R_45_Seq"),
    (-90.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/04_Run_F_L_90/Run_Loop_F_L_90_Seq"),
    (90.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/05_Run_F_R_90/Run_Loop_F_R_90_Seq"),
    (180.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq"),
    (-180.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq"),
    (-135.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/07_Run_B_L_45/Run_Loop_B_L_45_Seq"),
    (135.0, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/08_Run_B_R_45/Run_Loop_B_R_45_Seq"),
    (-157.5, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/09_Run_B_L_90/Run_Loop_B_L_90_Seq"),
    (157.5, "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/10_Run_B_R_90/Run_Loop_B_R_90_Seq"),
]


def log(m):
    unreal.log(f"[FixBS] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(p)
    return a


def run():
    char_sk_mesh = load(CHAR_MESH_SK)
    char_skel = char_sk_mesh.get_editor_property("skeleton") if isinstance(char_sk_mesh, unreal.SkeletalMesh) else char_sk_mesh
    sword_sk_mesh = load(SWORD_SK)
    sword_skel = sword_sk_mesh.get_editor_property("skeleton") if isinstance(sword_sk_mesh, unreal.SkeletalMesh) else sword_sk_mesh
    preview = unreal.EditorAssetLibrary.load_asset(CHAR_MESH)
    if not isinstance(preview, unreal.SkeletalMesh):
        preview = char_sk_mesh if isinstance(char_sk_mesh, unreal.SkeletalMesh) else None

    # Compatible both ways
    for sk, other in ((char_skel, sword_skel), (sword_skel, char_skel)):
        try:
            arr = list(sk.get_editor_property("compatible_skeletons") or [])
            if other not in arr:
                arr.append(other)
                sk.set_editor_property("compatible_skeletons", arr)
                log(f"compatible ok {sk.get_name()}")
        except Exception as exc:
            log(f"compatible fail: {exc}")

    # Force remove old BS (and redirector leftovers)
    for path in (BS_PATH, ALIAS):
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            ok = unreal.EditorAssetLibrary.delete_asset(path)
            log(f"delete {path}: {ok}")

    unreal.EditorAssetLibrary.make_directory(OUT)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", char_skel)
    if isinstance(preview, unreal.SkeletalMesh):
        factory.set_editor_property("preview_skeletal_mesh", preview)

    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BS_WalkRun_Locomotion", OUT, unreal.BlendSpace, factory
    )
    if not bs:
        raise RuntimeError("create BS failed")

    sk_now = bs.get_editor_property("skeleton")
    log(f"Created BS skeleton NOW: {sk_now.get_path_name() if sk_now else None}")
    if "Characters/Mannequins" not in sk_now.get_path_name():
        raise RuntimeError(f"BS skeleton wrong: {sk_now.get_path_name()}")

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

    samples = []

    def add(path, direction, speed):
        anim = load(path)
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)

    for d in (0.0, -90.0, 90.0, 180.0, -180.0):
        add(IDLE, d, 0.0)
    for d, p in WALKS:
        add(p, d, 200.0)
    for d, p in RUNS:
        add(p, d, 500.0)

    bs.set_editor_property("sample_data", samples)
    unreal.EditorAssetLibrary.save_loaded_asset(bs)
    unreal.EditorAssetLibrary.save_asset(BS_PATH, only_if_is_dirty=False)

    sk_now = bs.get_editor_property("skeleton")
    log(f"After samples skeleton: {sk_now.get_path_name()}")
    log(f"Sample count: {len(bs.get_editor_property('sample_data'))}")

    # Alias in Mannequins folder (same name length as BS_Idle_Walk_Run)
    unreal.EditorAssetLibrary.duplicate_asset(BS_PATH, ALIAS)
    unreal.EditorAssetLibrary.save_asset(ALIAS, only_if_is_dirty=False)
    alias_bs = load(ALIAS)
    log(f"Alias skeleton: {alias_bs.get_editor_property('skeleton').get_path_name()}")

    # Patch ABP only on disk — no compile after
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    # Save ABP first if loaded dirty
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    with open(fs, "rb") as f:
        data = bytearray(f.read())
    n = data.count(b"BS_Idle_Walk_Run")
    n2 = data.count(b"BS_WalkRun_Sword")
    if n:
        data = data.replace(b"BS_Idle_Walk_Run", b"BS_WalkRun_Sword")
        with open(fs, "wb") as f:
            f.write(data)
    with open(fs, "rb") as f:
        d = f.read()
    log(f"ABP patch replaced Idle->{n}, final Sword={b'BS_WalkRun_Sword' in d} Idle={b'BS_Idle_Walk_Run' in d} (prevSword={n2})")

    log("DONE — reopen project. In ABP list should show BS_WalkRun_Locomotion / BS_WalkRun_Sword")


if __name__ == "__main__":
    run()
else:
    run()
