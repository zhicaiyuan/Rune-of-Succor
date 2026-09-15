# -*- coding: utf-8 -*-
"""Create BS_WalkRun_Sword on Characters skeleton (ABP already references this name)."""

import unreal

ALIAS_DIR = "/Game/Characters/Mannequins/Anims/Unarmed"
ALIAS_NAME = "BS_WalkRun_Sword"
ALIAS = f"{ALIAS_DIR}/{ALIAS_NAME}"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
BS2_NAME = "BS_SwordStrafe2D"
BS2 = f"{OUT}/{BS2_NAME}"

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
    unreal.log(f"[FixBS2] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(p)
    return a


def force_delete(path: str):
    for _ in range(3):
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            return True
        unreal.EditorAssetLibrary.delete_asset(path)
    # redirector?
    return not unreal.EditorAssetLibrary.does_asset_exist(path)


def fill_bs(bs):
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
    return len(samples)


def create_bs(name, directory, char_skel, preview):
    force_delete(f"{directory}/{name}")
    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", char_skel)
    if isinstance(preview, unreal.SkeletalMesh):
        factory.set_editor_property("preview_skeletal_mesh", preview)
    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        name, directory, unreal.BlendSpace, factory
    )
    if not bs:
        # Fallback unique name
        alt = name + "_New"
        bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            alt, directory, unreal.BlendSpace, factory
        )
        log(f"Created alt name {alt}")
    return bs


def run():
    char_obj = load(CHAR_MESH_SK)
    char_skel = char_obj.get_editor_property("skeleton") if isinstance(char_obj, unreal.SkeletalMesh) else char_obj
    sword_obj = load(SWORD_SK)
    sword_skel = sword_obj.get_editor_property("skeleton") if isinstance(sword_obj, unreal.SkeletalMesh) else sword_obj
    preview = unreal.EditorAssetLibrary.load_asset(CHAR_MESH)
    if not isinstance(preview, unreal.SkeletalMesh):
        preview = char_obj if isinstance(char_obj, unreal.SkeletalMesh) else None

    for sk, other in ((char_skel, sword_skel), (sword_skel, char_skel)):
        try:
            arr = list(sk.get_editor_property("compatible_skeletons") or [])
            if other not in arr:
                arr.append(other)
                sk.set_editor_property("compatible_skeletons", arr)
        except Exception as exc:
            log(f"compat: {exc}")

    # Primary: alias path ABP already uses
    force_delete(ALIAS)
    bs = create_bs(ALIAS_NAME, ALIAS_DIR, char_skel, preview)
    if not bs:
        raise RuntimeError("Failed to create alias BS")
    sk = bs.get_editor_property("skeleton")
    log(f"ALIAS skeleton={sk.get_path_name()}")
    if "Characters/Mannequins" not in sk.get_path_name():
        raise RuntimeError("Alias BS not on Characters skeleton")
    n = fill_bs(bs)
    unreal.EditorAssetLibrary.save_asset(bs.get_path_name().split(".")[0], only_if_is_dirty=False)
    log(f"ALIAS samples={n} path={bs.get_path_name()}")

    # Also create convenient copy under 林符/动画 with new name
    unreal.EditorAssetLibrary.make_directory(OUT)
    force_delete(BS2)
    bs2 = create_bs(BS2_NAME, OUT, char_skel, preview)
    if bs2:
        fill_bs(bs2)
        unreal.EditorAssetLibrary.save_asset(BS2, only_if_is_dirty=False)
        log(f"Also created {BS2} skeleton={bs2.get_editor_property('skeleton').get_path_name()}")

    # Confirm ABP still points to BS_WalkRun_Sword
    content = unreal.Paths.project_content_dir()
    abp_fs = (content + "Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion.uasset").replace("/", "\\")
    with open(abp_fs, "rb") as f:
        d = f.read()
    if b"BS_WalkRun_Sword" not in d:
        data = bytearray(d)
        if b"BS_Idle_Walk_Run" in data:
            data = data.replace(b"BS_Idle_Walk_Run", b"BS_WalkRun_Sword")
            with open(abp_fs, "wb") as f:
                f.write(data)
            log("Re-patched ABP to BS_WalkRun_Sword")
        else:
            log("WARNING: ABP does not reference BS_WalkRun_Sword")
    else:
        log("ABP already references BS_WalkRun_Sword")

    log("DONE. Open ABP_StrafeLocomotion — Blend Space list should include BS_WalkRun_Sword")


if __name__ == "__main__":
    run()
else:
    run()
