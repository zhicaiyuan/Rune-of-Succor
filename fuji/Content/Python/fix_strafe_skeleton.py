# -*- coding: utf-8 -*-
"""
Fix skeleton mismatch for strafe locomotion.
Strategy A: IK retarget Sword loops -> Characters Mannequin, rebuild BS, patch ABP.
Strategy B: mark skeletons compatible + rebuild BS with Characters skeleton using source anims.
Strategy C: point character/ABP at Sword skeleton mesh path if A/B fail for samples.
"""

from __future__ import annotations

import unreal

OUT_DIR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
RETARGET_DIR = f"{OUT_DIR}/Retargeted"
BS_NAME = "BS_WalkRun_Locomotion"
BS_PATH = f"{OUT_DIR}/{BS_NAME}"
ABP_PATH = f"{OUT_DIR}/ABP_StrafeLocomotion"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IMC_DEFAULT = "/Game/Input/IMC_Default"
IA_SPRINT = "/Game/Input/Actions/IA_Sprint"

TARGET_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
TARGET_SK = "/Game/Characters/Mannequins/Meshes/SK_Mannequin"
SOURCE_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
SOURCE_SK_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SK_Mannequin"
IK_RETARGETER = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/NewIKRetargeter"

SRC_IDLE = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"
SRC_WALK = {
    0.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Loop_F_0_Seq",
    -45.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/02_Walk_F_L_45/Walk_Loop_F_L_45_Seq",
    45.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/03_Walk_F_R_45/Walk_Loop_F_R_45_Seq",
    -90.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/04_Walk_F_L_90/Walk_Loop_F_L_90_Seq",
    90.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/05_Walk_F_R_90/Walk_Loop_F_R_90_Seq",
    180.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq",
    -180.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq",
    -135.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/07_Walk_B_L_45/Walk_Loop_B_L_45_Seq",
    135.0: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/08_Walk_B_R_45/Walk_Loop_B_R_45_Seq",
    -157.5: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/09_Walk_B_L_90/Walk_Loop_B_L_90_Seq",
    157.5: "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/10_Walk_B_R_90/Walk_Loop_B_R_90_Seq",
}
SRC_RUN = {
    0.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Loop_F_0_Seq",
    -45.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/02_Run_F_L_45/Run_Loop_F_L_45_Seq",
    45.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/03_Run_F_R_45/Run_Loop_F_R_45_Seq",
    -90.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/04_Run_F_L_90/Run_Loop_F_L_90_Seq",
    90.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/05_Run_F_R_90/Run_Loop_F_R_90_Seq",
    180.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq",
    -180.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq",
    -135.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/07_Run_B_L_45/Run_Loop_B_L_45_Seq",
    135.0: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/08_Run_B_R_45/Run_Loop_B_R_45_Seq",
    -157.5: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/09_Run_B_L_90/Run_Loop_B_L_90_Seq",
    157.5: "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/10_Run_B_R_90/Run_Loop_B_R_90_Seq",
}


def log(msg: str) -> None:
    unreal.log(f"[FixStrafe] {msg}")


def ensure_dir(path: str) -> None:
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def load(path: str):
    a = unreal.EditorAssetLibrary.load_asset(path)
    if not a:
        raise RuntimeError(f"Missing: {path}")
    return a


def unique_src():
    out, seen = [], set()
    for p in [SRC_IDLE, *SRC_WALK.values(), *SRC_RUN.values()]:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def skeleton_of_mesh(path: str):
    mesh = load(path)
    if isinstance(mesh, unreal.SkeletalMesh):
        return mesh.get_editor_property("skeleton")
    if isinstance(mesh, unreal.Skeleton):
        return mesh
    raise RuntimeError(path)


def skeleton_of_anim(path: str):
    return load(path).get_editor_property("skeleton")


def make_compatible(a, b):
    """Add each skeleton to the other's compatible list if property exists."""
    for sk, other in ((a, b), (b, a)):
        if not sk or not other:
            continue
        for prop in ("compatible_skeletons", "CompatibleSkeletons"):
            try:
                arr = list(sk.get_editor_property(prop) or [])
                if other not in arr:
                    arr.append(other)
                    sk.set_editor_property(prop, arr)
                    log(f"Compatible: {sk.get_name()} <-> {other.get_name()} via {prop}")
                break
            except Exception:
                continue


def asset_data_list(paths):
    datas = []
    for p in paths:
        try:
            ad = unreal.EditorAssetLibrary.find_asset_data(p)
            if ad:
                datas.append(ad)
                continue
        except Exception:
            pass
        try:
            datas.append(unreal.AssetData(p))
        except Exception as exc:
            log(f"AssetData fail {p}: {exc}")
    return datas


def try_ik_retarget(src_paths):
    ensure_dir(RETARGET_DIR)
    result = {}
    ikr = unreal.EditorAssetLibrary.load_asset(IK_RETARGETER)
    src_mesh = unreal.EditorAssetLibrary.load_asset(SOURCE_MESH) or unreal.EditorAssetLibrary.load_asset(SOURCE_SK_MESH)
    tgt_mesh = unreal.EditorAssetLibrary.load_asset(TARGET_MESH) or unreal.EditorAssetLibrary.load_asset(TARGET_SK)
    if not (ikr and src_mesh and tgt_mesh):
        log("IK retarget prerequisites missing")
        return result

    datas = asset_data_list(src_paths)
    log(f"IK retargeting {len(datas)} assets...")

    try:
        # UE5.8 typical signature uses Array[AssetData]
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            datas,
            src_mesh,
            tgt_mesh,
            ikr,
            "",
            "",
            "_RTG",
            RETARGET_DIR,
        )
    except Exception as exc1:
        log(f"IK call1 failed: {exc1}")
        try:
            unreal.IKRetargetBatchOperation.duplicate_and_retarget(
                assets_to_retarget=datas,
                source_mesh=src_mesh,
                target_mesh=tgt_mesh,
                ik_retargeter_asset=ikr,
                search="",
                replace="",
                prefix="",
                suffix="_RTG",
                output_path=RETARGET_DIR,
            )
        except Exception as exc2:
            log(f"IK call2 failed: {exc2}")
            try:
                # Another common kw set
                unreal.IKRetargetBatchOperation.duplicate_and_retarget(
                    assets_to_retarget=datas,
                    source_mesh=src_mesh,
                    target_mesh=tgt_mesh,
                    retarget_asset=ikr,
                    export_path=RETARGET_DIR,
                    search_prefix="",
                    replace_prefix="",
                    suffix="_RTG",
                )
            except Exception as exc3:
                log(f"IK call3 failed: {exc3}")
                return result

    for src in src_paths:
        name = src.split("/")[-1]
        for cand in (f"{RETARGET_DIR}/{name}_RTG", f"{RETARGET_DIR}/{name}"):
            if unreal.EditorAssetLibrary.does_asset_exist(cand):
                result[src] = cand
                break
    log(f"IK produced {len(result)}/{len(src_paths)}")
    return result


def rebuild_bs(anim_map: dict, use_characters_skeleton: bool):
    ensure_dir(OUT_DIR)
    if use_characters_skeleton:
        skel = skeleton_of_mesh(TARGET_MESH if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH) else TARGET_SK)
        preview = unreal.EditorAssetLibrary.load_asset(TARGET_MESH) or unreal.EditorAssetLibrary.load_asset(TARGET_SK)
    else:
        skel = skeleton_of_anim(SRC_IDLE)
        preview = unreal.EditorAssetLibrary.load_asset(SOURCE_MESH) or unreal.EditorAssetLibrary.load_asset(SOURCE_SK_MESH)

    if unreal.EditorAssetLibrary.does_asset_exist(BS_PATH):
        # Recreate cleanly
        unreal.EditorAssetLibrary.delete_asset(BS_PATH)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", skel)
    if isinstance(preview, unreal.SkeletalMesh):
        factory.set_editor_property("preview_skeletal_mesh", preview)

    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        BS_NAME, OUT_DIR, unreal.BlendSpace, factory
    )
    if not bs:
        # try load if delete failed unattended
        bs = unreal.EditorAssetLibrary.load_asset(BS_PATH)
    if not bs:
        raise RuntimeError("Cannot create/load BlendSpace")

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

    def add(src, direction, speed):
        path = anim_map.get(src, src)
        anim = load(path)
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)

    try:
        for d in (0.0, -90.0, 90.0, -180.0, 180.0):
            add(SRC_IDLE, d, 0.0)
        for d, src in SRC_WALK.items():
            add(src, d, 200.0)
        for d, src in SRC_RUN.items():
            add(src, d, 500.0)
        bs.set_editor_property("sample_data", samples)
    except Exception as exc:
        log(f"Adding samples failed: {exc}")
        raise

    unreal.EditorAssetLibrary.save_asset(BS_PATH, only_if_is_dirty=False)
    log(f"BS saved skeleton={skel.get_path_name()} samples={len(samples)}")
    return skel


def ensure_abp(skel):
    src_abp = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
    if not unreal.EditorAssetLibrary.does_asset_exist(ABP_PATH):
        unreal.EditorAssetLibrary.duplicate_asset(src_abp, ABP_PATH)
        unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)

    # Alias for same-length patch
    alias = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
    if unreal.EditorAssetLibrary.does_asset_exist(alias):
        unreal.EditorAssetLibrary.delete_asset(alias)
    unreal.EditorAssetLibrary.duplicate_asset(BS_PATH, alias)
    unreal.EditorAssetLibrary.save_asset(alias, only_if_is_dirty=False)

    # Soft-path patch after save/compile
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP_PATH.replace("/Game/", "") + ".uasset").replace("/", "\\")

    def patch():
        with open(fs, "rb") as f:
            data = bytearray(f.read())
        n = data.count(b"BS_Idle_Walk_Run")
        if n:
            data = data.replace(b"BS_Idle_Walk_Run", b"BS_WalkRun_Sword")
            with open(fs, "wb") as f:
                f.write(data)
        with open(fs, "rb") as f:
            d = f.read()
        log(f"ABP patch: changed={n}, hasSword={b'BS_WalkRun_Sword' in d}, hasIdle={b'BS_Idle_Walk_Run' in d}")

    unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)
    patch()
    abp = load(ABP_PATH)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)
    patch()


def configure_character(bp_path: str, mesh_path: str | None = None):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        return
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    try:
        cdo.set_editor_property("use_controller_rotation_yaw", True)
        cdo.set_editor_property("use_controller_rotation_pitch", False)
        cdo.set_editor_property("use_controller_rotation_roll", False)
    except Exception:
        pass

    try:
        move = cdo.get_editor_property("character_movement")
        if move:
            move.set_editor_property("orient_rotation_to_movement", False)
            move.set_editor_property("use_controller_desired_rotation", False)
            move.set_editor_property("max_walk_speed", 250.0)
            move.set_editor_property("max_acceleration", 1000.0)
            move.set_editor_property("braking_deceleration_walking", 1200.0)
            move.set_editor_property("ground_friction", 6.0)
    except Exception:
        pass

    try:
        mesh = cdo.get_editor_property("mesh")
        if mesh:
            rel = mesh.get_editor_property("relative_rotation")
            mesh.set_editor_property("relative_rotation", unreal.Rotator(rel.pitch, -90.0, rel.roll))
            if mesh_path:
                sm = unreal.EditorAssetLibrary.load_asset(mesh_path)
                if isinstance(sm, unreal.SkeletalMesh):
                    mesh.set_editor_property("skeletal_mesh_asset", sm)
            abp = load(ABP_PATH)
            try:
                anim_class = abp.generated_class()
            except Exception:
                anim_class = abp.get_editor_property("generated_class")
            mesh.set_editor_property("anim_class", anim_class)
    except Exception as exc:
        log(f"char mesh: {exc}")

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
    log(f"Configured {bp_path}")


def fix_sprint():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_SPRINT):
        unreal.EditorAssetLibrary.duplicate_asset("/Game/Input/Actions/IA_Jump", IA_SPRINT)
    ia = load(IA_SPRINT)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_SPRINT, only_if_is_dirty=False)

    imc = load(IMC_DEFAULT)
    mappings = list(imc.get_editor_property("mappings") or [])
    kept = []
    for m in mappings:
        try:
            a = m.get_editor_property("action")
            if a and "IA_Sprint" in a.get_path_name():
                continue
        except Exception:
            pass
        kept.append(m)

    # Clone Jump mapping template
    jump_m = None
    for m in kept:
        try:
            a = m.get_editor_property("action")
            if a and "IA_Jump" in a.get_path_name():
                jump_m = m
                break
        except Exception:
            pass

    try:
        m = unreal.EnhancedActionKeyMapping()
        m.set_editor_property("action", ia)
        if jump_m:
            # start from jump key then set LeftShift
            try:
                m.set_editor_property("key", jump_m.get_editor_property("key"))
            except Exception:
                pass
        try:
            m.set_editor_property("key", unreal.Key("LeftShift"))
        except Exception as exc:
            log(f"LeftShift key set failed ({exc}); sprint action still added — rebind in editor if needed")
        kept.append(m)
        imc.set_editor_property("mappings", kept)
        unreal.EditorAssetLibrary.save_asset(IMC_DEFAULT, only_if_is_dirty=False)
        log("IMC sprint mapping saved")
    except Exception as exc:
        log(f"IMC sprint failed: {exc}")


def run():
    log("Start...")
    src_paths = unique_src()
    char_skel = skeleton_of_mesh(TARGET_MESH if unreal.EditorAssetLibrary.does_asset_exist(TARGET_MESH) else TARGET_SK)
    sword_skel = skeleton_of_anim(SRC_IDLE)
    log(f"Char skel: {char_skel.get_path_name()}")
    log(f"Sword skel: {sword_skel.get_path_name()}")
    make_compatible(char_skel, sword_skel)
    unreal.EditorAssetLibrary.save_asset(char_skel.get_path_name().split(".")[0], only_if_is_dirty=False)
    try:
        unreal.EditorAssetLibrary.save_asset(sword_skel.get_path_name().split(".")[0], only_if_is_dirty=False)
    except Exception:
        pass

    anim_map = try_ik_retarget(src_paths)
    use_char = len(anim_map) == len(src_paths)

    if not use_char:
        log("IK incomplete — building BS on Sword skeleton (will also retarget ABP usage via alias + character mesh if needed)")
        anim_map = {p: p for p in src_paths}
        skel = rebuild_bs(anim_map, use_characters_skeleton=False)
        # For ABP (Characters skeleton) to accept this BS, they must be compatible.
        # Additionally create Characters-skeleton BS if compatible allows samples.
        try:
            make_compatible(char_skel, sword_skel)
            rebuild_bs(anim_map, use_characters_skeleton=True)
            use_char = True
            log("Characters-skeleton BS built using compatible sword anims")
        except Exception as exc:
            log(f"Characters BS with compatible anims failed: {exc}")
            # Keep sword BS; switch character mesh to sword mannequin so runtime matches
            ensure_abp(skel)
            configure_character(CHAR_BP, SOURCE_MESH)
            configure_character(COMBAT_BP, SOURCE_MESH)
            fix_sprint()
            log("DONE (Sword skeleton path). Open ABP — if list still empty, use BS_WalkRun_Sword after assigning Sword skeleton, or use character with Sword mesh.")
            return
    else:
        rebuild_bs(anim_map, use_characters_skeleton=True)

    ensure_abp(char_skel)
    configure_character(CHAR_BP, None)
    configure_character(COMBAT_BP, None)
    fix_sprint()

    try:
        unreal.EditorAssetLibrary.save_directory(OUT_DIR, only_if_is_dirty=False, recursive=True)
    except Exception:
        pass
    log("DONE. In ABP_StrafeLocomotion pick BS_WalkRun_Locomotion or BS_WalkRun_Sword.")


if __name__ == "__main__":
    run()
else:
    run()
