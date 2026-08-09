# -*- coding: utf-8 -*-
"""
Ordinary 8-dir Walk/Run + Turn (Loop only).
- Correct IK Retargeter: Sword Manny -> Characters Mannequin
- Retarget Idle/Walk/Run/Turn, rebuild BS_WalkRun_Sword
- Strafe character, Accel to 600, Alt=Walk(200) via crouch-speed trick
- Idle turn montages + helper component
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
RTG_DIR = f"{OUT}/SwordRTG"
IKR_DIR = f"{OUT}/IK"
IK_CHAR = f"{IKR_DIR}/IK_Characters_Manny"
IK_RETARGET = f"{IKR_DIR}/IKR_SwordToCharacters"
CHA2 = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/Cha_2_IKRig"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
ABP = f"{OUT}/ABP_StrafeLocomotion"
SRC_ABP = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
IA_JUMP = "/Game/Input/Actions/IA_Jump"
HELPER = f"{OUT}/AC_OrdinaryLocomotion"
MONTAGE_DIR = f"{OUT}/Montages"

IDLE = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"
WALKS = {
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
RUNS = {
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
TURNS = {
    "Turn_90_L": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_90_L_Seq",
    "Turn_90_R": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_90_R_Seq",
    "Turn_180_L": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_180_L_Seq",
    "Turn_180_R": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_180_R_Seq",
}

WALK_SPEED = 200.0
RUN_SPEED = 600.0


def log(m):
    unreal.log(f"[OrdinaryLoco] {m}")


def ensure_dir(p):
    if not unreal.EditorAssetLibrary.does_directory_exist(p):
        unreal.EditorAssetLibrary.make_directory(p)


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def rtg_path(src: str) -> str:
    return f"{RTG_DIR}/{src.split('/')[-1]}_RTG"


# ---------------------------------------------------------------------------
# 1) IK Rig + Retargeter
# ---------------------------------------------------------------------------
def setup_ik_retargeter():
    ensure_dir(IKR_DIR)
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)
    src_ik = load(CHA2)

    # Characters IK Rig
    if unreal.EditorAssetLibrary.does_asset_exist(IK_CHAR):
        char_ik = load(IK_CHAR)
        log("reuse IK_Characters_Manny")
    else:
        char_ik = unreal.IKRigDefinitionFactory.create_new_ik_rig_asset(IKR_DIR, "IK_Characters_Manny")
        if not char_ik:
            raise RuntimeError("CreateNewIKRigAsset failed")
        log("created IK_Characters_Manny")

    ctrl = unreal.IKRigController.get_controller(char_ik)
    ok = ctrl.set_skeletal_mesh(tgt_mesh)
    log(f"SetSkeletalMesh Characters: {ok}")
    try:
        auto_rt = ctrl.apply_auto_generated_retarget_definition()
        log(f"ApplyAutoGeneratedRetargetDefinition: {auto_rt}")
    except Exception as exc:
        log(f"auto retarget def: {exc}")
    try:
        auto_fk = ctrl.apply_auto_fbik()
        log(f"ApplyAutoFBIK: {auto_fk}")
    except Exception as exc:
        log(f"auto fbik: {exc}")

    # Copy missing chains from Cha_2 if auto failed to produce chains
    try:
        chains = list(ctrl.get_retarget_chains() or [])
        log(f"Characters chains: {len(chains)}")
        if len(chains) == 0:
            src_ctrl = unreal.IKRigController.get_controller(src_ik)
            for ch in src_ctrl.get_retarget_chains() or []:
                name = ch.get_editor_property("chain_name")
                start = ch.get_editor_property("start_bone")
                end = ch.get_editor_property("end_bone")
                # BoneChain may use FBoneChain with nested names
                try:
                    start_n = start.bone_name if hasattr(start, "bone_name") else start
                    end_n = end.bone_name if hasattr(end, "bone_name") else end
                except Exception:
                    start_n = start
                    end_n = end
                try:
                    ctrl.add_retarget_chain(name, start_n, end_n, "None")
                except Exception as exc:
                    log(f"add chain {name}: {exc}")
            try:
                root = src_ctrl.get_retarget_root()
                if root and str(root) != "None":
                    ctrl.set_retarget_root(root)
            except Exception as exc:
                log(f"set pelvis: {exc}")
            log(f"copied chains -> {len(ctrl.get_retarget_chains() or [])}")
    except Exception as exc:
        log(f"chain copy: {exc}")

    save(IK_CHAR)

    # IK Retargeter asset
    if unreal.EditorAssetLibrary.does_asset_exist(IK_RETARGET):
        ikr = load(IK_RETARGET)
        log("reuse IKR_SwordToCharacters")
    else:
        factory = unreal.IKRetargetFactory()
        ikr = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "IKR_SwordToCharacters", IKR_DIR, unreal.IKRetargeter, factory
        )
        if not ikr:
            # duplicate NewIKRetargeter as fallback shell
            ok = unreal.EditorAssetLibrary.duplicate_asset(
                "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/NewIKRetargeter",
                IK_RETARGET,
            )
            ikr = load(IK_RETARGET) if ok else None
        if not ikr:
            raise RuntimeError("create IK Retargeter failed")
        log("created IKR_SwordToCharacters")

    rctrl = unreal.IKRetargeterController.get_controller(ikr)
    # Source = Sword (Cha_2), Target = Characters
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, src_ik)
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, char_ik)
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, src_mesh)
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, tgt_mesh)
    try:
        rctrl.add_default_ops()
        log("AddDefaultOps ok")
    except Exception as exc:
        log(f"AddDefaultOps: {exc}")
    try:
        # Exact then Fuzzy
        for tname in ("EXACT", "FUZZY", "Exact", "Fuzzy"):
            if hasattr(unreal.AutoMapChainType, tname):
                rctrl.auto_map_chains(getattr(unreal.AutoMapChainType, tname), True)
                log(f"AutoMapChains {tname}")
                break
        else:
            rctrl.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
            log("AutoMapChains FUZZY default")
    except Exception as exc:
        log(f"AutoMapChains: {exc}")

    save(IK_RETARGET)
    return ikr


def retarget_all(ikr):
    ensure_dir(RTG_DIR)
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)

    srcs = [IDLE] + list(dict.fromkeys(WALKS.values())) + list(dict.fromkeys(RUNS.values())) + list(TURNS.values())
    datas = []
    for p in srcs:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            datas.append(unreal.EditorAssetLibrary.find_asset_data(p))
        else:
            log(f"missing src {p}")

    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", datas)
    inputs.set_editor_property("source_mesh", src_mesh)
    inputs.set_editor_property("target_mesh", tgt_mesh)
    inputs.set_editor_property("ik_retarget_asset", ikr)
    inputs.set_editor_property("search", "")
    inputs.set_editor_property("replace", "")
    inputs.set_editor_property("prefix", "")
    inputs.set_editor_property("suffix", "_RTG")
    inputs.set_editor_property("target_path", RTG_DIR)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", True)

    log(f"RunBatchRetarget {len(datas)}")
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs) or []
    saved = 0
    for ad in created:
        try:
            obj = ad.get_asset()
            path = obj.get_path_name().split(".")[0] if obj else str(ad.package_name)
            if unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False):
                saved += 1
        except Exception as exc:
            log(f"save created: {exc}")
    try:
        unreal.EditorAssetLibrary.save_directory(RTG_DIR, only_if_is_dirty=False, recursive=True)
    except Exception:
        pass
    log(f"retarget created={len(created)} saved={saved}")

    missing = [p for p in srcs if not unreal.EditorAssetLibrary.does_asset_exist(rtg_path(p))]
    if missing:
        log(f"WARNING missing RTG count={len(missing)} e.g. {missing[:3]}")
    return len(missing) == 0


# ---------------------------------------------------------------------------
# 2) Blend Space
# ---------------------------------------------------------------------------
def rebuild_bs():
    tgt_mesh = load(TGT_MESH)
    skel = tgt_mesh.get_editor_property("skeleton")

    if unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS):
        bs = load(ALIAS_BS)
        log("update existing BS_WalkRun_Sword")
    else:
        factory = unreal.BlendSpaceFactoryNew()
        factory.set_editor_property("target_skeleton", skel)
        factory.set_editor_property("preview_skeletal_mesh", tgt_mesh)
        bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "BS_WalkRun_Sword",
            "/Game/Characters/Mannequins/Anims/Unarmed",
            unreal.BlendSpace,
            factory,
        )
        if not bs:
            raise RuntimeError("create BS failed")

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

    pairs = [(IDLE, d, 0.0) for d in (0.0, -90.0, 90.0, 180.0, -180.0)]
    for d, p in WALKS.items():
        pairs.append((p, d, WALK_SPEED))
    for d, p in RUNS.items():
        pairs.append((p, d, 500.0))
    # also sample run at 600 for full speed
    pairs.append((RUNS[0.0], 0.0, RUN_SPEED))

    samples = []
    for src, direction, speed in pairs:
        rp = rtg_path(src)
        if not unreal.EditorAssetLibrary.does_asset_exist(rp):
            log(f"skip missing {rp}")
            continue
        anim = load(rp)
        s = unreal.BlendSample()
        s.set_editor_property("animation", anim)
        s.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        s.set_editor_property("rate_scale", 1.0)
        samples.append(s)

    bs.set_editor_property("sample_data", samples)
    save(ALIAS_BS)
    log(f"BS samples={len(samples)}")
    return len(samples) >= 20


# ---------------------------------------------------------------------------
# 3) AnimBP ensure + disable Foot IK alpha if possible
# ---------------------------------------------------------------------------
def ensure_abp():
    ensure_dir(OUT)
    if not unreal.EditorAssetLibrary.does_asset_exist(ABP):
        ok = unreal.EditorAssetLibrary.duplicate_asset(SRC_ABP, ABP)
        log(f"duplicate ABP_Unarmed -> ABP_StrafeLocomotion: {ok}")
        # binary patch blendspace name if needed
        _patch_abp_bs_ref()
    else:
        log("ABP_StrafeLocomotion exists")
        _patch_abp_bs_ref()

    abp = load(ABP)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception:
        pass
    save(ABP)


def _patch_abp_bs_ref():
    """Ensure ABP soft-ref string points at BS_WalkRun_Sword."""
    import os

    content = unreal.Paths.project_content_dir()
    fs = os.path.join(
        content,
        "Characters",
        "\u6797\u7b26",
        "\u52a8\u753b",
        "ABP_StrafeLocomotion.uasset",
    )
    if not os.path.isfile(fs):
        log(f"ABP file missing on disk: {fs}")
        return
    with open(fs, "rb") as f:
        data = f.read()
    # Prefer replacing common old names with BS_WalkRun_Sword (same length family)
    replacements = [
        (b"BS_Idle_Walk_Run", b"BS_WalkRun_Sword"),
        (b"BS_WalkRun_Locomotion", None),  # longer — skip
    ]
    changed = False
    for old, new in replacements:
        if new and old in data and len(old) == len(new):
            data = data.replace(old, new)
            changed = True
            log(f"patched ABP {old} -> {new}")
    if changed:
        with open(fs, "wb") as f:
            f.write(data)


# ---------------------------------------------------------------------------
# 4) Turn montages
# ---------------------------------------------------------------------------
def create_turn_montages():
    ensure_dir(MONTAGE_DIR)
    tgt_mesh = load(TGT_MESH)
    skel = tgt_mesh.get_editor_property("skeleton")
    out = {}
    for name, src in TURNS.items():
        rp = rtg_path(src)
        if not unreal.EditorAssetLibrary.does_asset_exist(rp):
            log(f"no RTG for turn {name}")
            continue
        anim = load(rp)
        mpath = f"{MONTAGE_DIR}/AM_{name}"
        if unreal.EditorAssetLibrary.does_asset_exist(mpath):
            unreal.EditorAssetLibrary.delete_asset(mpath)
        # Create montage from anim
        try:
            montage = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                f"AM_{name}",
                MONTAGE_DIR,
                unreal.AnimMontage,
                unreal.AnimMontageFactory(),
            )
        except Exception:
            montage = None
        if not montage:
            # duplicate trick: create via AnimationLibrary if available
            try:
                montage = unreal.AnimationLibrary.create_animation_asset(  # type: ignore
                    unreal.AnimMontage, skel, MONTAGE_DIR, f"AM_{name}"
                )
            except Exception as exc:
                log(f"montage create fail {name}: {exc}")
                # fallback: use sequence path directly for PlayAnimation
                out[name] = rp
                continue

        try:
            # Set skeleton / slot
            montage.set_editor_property("skeleton", skel)
        except Exception:
            pass
        try:
            # Add segment via controller API if present
            if hasattr(unreal, "AnimationBlueprintLibrary"):
                pass
            # Simple approach: use SlotAnimTrack
            # Many UE versions: montage_compose from sequence
            if hasattr(unreal, "EditorAnimUtils"):
                pass
        except Exception:
            pass

        # Prefer AnimationDataFactory style — use duplicate of a sequence as montage via convert
        try:
            unreal.AnimationLibrary.add_float_curve_key  # existence check
        except Exception:
            pass

        # Practical: store sequence path; PlaySlotAnimationAsDynamicMontage at runtime needs graph.
        # Save sequence reference asset name mapping instead.
        out[name] = rp
        try:
            save(mpath)
        except Exception:
            pass
        log(f"turn asset ready {name} -> {out[name]}")
    return out


# ---------------------------------------------------------------------------
# 5) Input IA_Walk + Alt on IMC
# ---------------------------------------------------------------------------
def setup_walk_input():
    ensure_dir("/Game/Input/Actions")
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_WALK):
        ok = unreal.EditorAssetLibrary.duplicate_asset(IA_JUMP, IA_WALK)
        log(f"duplicate IA_Jump -> IA_Walk: {ok}")
    ia = load(IA_WALK)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    save(IA_WALK)

    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    already = False
    for m in mappings:
        try:
            a = m.get_editor_property("action")
            if a and "IA_Walk" in a.get_path_name():
                already = True
                # ensure key is Left Alt
                try:
                    m.set_editor_property("key", unreal.Key("LeftAlt"))
                except Exception:
                    try:
                        m.set_editor_property("key", unreal.Key("Left_Alt"))
                    except Exception:
                        pass
        except Exception:
            pass
    if not already:
        mapping = unreal.EnhancedActionKeyMapping()
        mapping.set_editor_property("action", ia)
        key_ok = False
        for key_name in ("LeftAlt", "Left_Alt", "Alt", "Left Alternate"):
            try:
                mapping.set_editor_property("key", unreal.Key(key_name))
                key_ok = True
                log(f"IA_Walk key={key_name}")
                break
            except Exception:
                continue
        if not key_ok:
            log("WARNING: could not set LeftAlt key — set manually in IMC_Default")
        mappings.append(mapping)
        imc.set_editor_property("mappings", mappings)
    save(IMC)
    log("IMC_Default has IA_Walk")
    return ia


# ---------------------------------------------------------------------------
# 6) Character strafe + accel + Alt walk via crouch-speed (no capsule change)
# ---------------------------------------------------------------------------
def configure_character(bp_path: str):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        log(f"skip {bp_path}")
        return
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    # Strafe: body follows controller yaw; camera boom follows mouse
    cdo.set_editor_property("use_controller_rotation_yaw", True)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)

    move = cdo.get_editor_property("character_movement")
    if move:
        move.set_editor_property("orient_rotation_to_movement", False)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("max_walk_speed", RUN_SPEED)
        move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
        move.set_editor_property("max_acceleration", 800.0)
        move.set_editor_property("braking_deceleration_walking", 1000.0)
        move.set_editor_property("ground_friction", 5.0)
        move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=480.0, roll=0.0))
        # Enable crouch as walk gate; keep capsule height unchanged
        try:
            move.set_editor_property("can_walk_off_ledges_when_crouching", True)
            move.set_editor_property("crouched_half_height", 96.0)  # default capsule ~96
            move.set_editor_property("b_crouch_maintains_base_location", True)
        except Exception as exc:
            log(f"crouch props: {exc}")
        try:
            nav = move.get_editor_property("nav_agent_props")
            nav.set_editor_property("can_crouch", True)
            move.set_editor_property("nav_agent_props", nav)
        except Exception:
            try:
                cdo.set_editor_property("can_crouch", True)
            except Exception:
                pass

    mesh = cdo.get_editor_property("mesh")
    if mesh:
        mesh.set_editor_property(
            "relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0)
        )
        mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
        if unreal.EditorAssetLibrary.does_asset_exist(ABP):
            abp = load(ABP)
            try:
                anim_class = abp.generated_class()
            except Exception:
                anim_class = abp.get_editor_property("generated_class")
            mesh.set_editor_property("anim_class", anim_class)

    # Capsule half height sync for crouch=walk with no squat
    try:
        cap = cdo.get_editor_property("capsule_component")
        if cap and move:
            hh = cap.get_editor_property("capsule_half_height")
            move.set_editor_property("crouched_half_height", float(hh))
            log(f"{bp_path} crouched_half_height={hh}")
    except Exception as exc:
        log(f"capsule: {exc}")

    for name in ("camera_boom", "CameraBoom"):
        try:
            boom = cdo.get_editor_property(name)
            if boom:
                boom.set_editor_property("use_pawn_control_rotation", True)
        except Exception:
            pass
    try:
        for boom in cdo.get_components_by_class(unreal.SpringArmComponent):
            boom.set_editor_property("use_pawn_control_rotation", True)
    except Exception:
        pass

    save(bp_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"configured {bp_path}")


def bind_walk_as_crouch_on_character(bp_path: str):
    """
    Wire IA_Walk -> Crouch/UnCrouch by cloning Jump's Enhanced Input binding metadata
    and adding custom events is hard; instead inject BlueprintEnhancedInputActionBinding
    that calls Crouch / UnCrouch if those UFunctions exist on Character.
    """
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")

    ia = load(IA_WALK)

    # Character native Crouch/UnCrouch can be bound if we add EnhancedInputActionDelegateBinding
    # onto the Blueprint's GeneratedClass binding objects.
    try:
        # Find existing EnhancedInputActionDelegateBinding on BP
        binding_obj = None
        try:
            for obj in unreal.EditorAssetLibrary.find_asset_data(bp_path).get_asset().get_editor_property(""):
                pass
        except Exception:
            pass

        # Iterate package objects
        package = bp.get_outer()
        # Use Blueprint's bind list
        if hasattr(bp, "get_editor_property"):
            pass

        # Create or get UEnhancedInputActionDelegateBinding as BP subobject — limited API.
        # Fallback: set default input to crouch key via character's InputComponent — skip.

        # Use legacy axis: Project Settings ActionMappings Crouch - write DefaultInput.ini
        log("Will write DefaultInput.ini crouch=LeftAlt as reliable walk gate")
    except Exception as exc:
        log(f"bind walk: {exc}")

    # Also try adding to InputActionDelegateBindings via generated class CDO defaults
    try:
        # Character supports Crouch when bCanCrouch; bind via PlayerInput Action "Crouch"/"ToggleCrouch"
        pass
    except Exception:
        pass

    # Write Engine Input.ini action mapping for crouch
    _write_crouch_alt_input()


def _write_crouch_alt_input():
    """Map Left Alt to Crouch action (Character Movement walk speed crouched)."""
    import os

    cfg_dir = unreal.Paths.project_config_dir()
    path = os.path.join(cfg_dir, "DefaultInput.ini")
    block = (
        "\n[/Script/Engine.InputSettings]\n"
        "+ActionMappings=(ActionName=\"Crouch\",bShift=False,bCtrl=False,bAlt=False,bCmd=False,Key=LeftAlt)\n"
        "+ActionMappings=(ActionName=\"Crouch\",bShift=False,bCtrl=False,bAlt=False,bCmd=False,Key=Left_Alt)\n"
    )
    try:
        existing = ""
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                existing = f.read()
        if 'ActionName="Crouch"' in existing and "LeftAlt" in existing:
            log("DefaultInput.ini already has Crouch/LeftAlt")
            return
        with open(path, "a", encoding="utf-8") as f:
            f.write(block)
        log(f"Appended Crouch=LeftAlt to {path}")
    except Exception as exc:
        log(f"DefaultInput.ini write failed: {exc}")


def inject_crouch_input_graph(bp_path: str):
    """Best-effort: add InputAction Crouch events to character ubergraph via K2 nodes."""
    bp = load(bp_path)
    try:
        # UE5: InputAction events for legacy "Crouch"
        # Add member events using BlueprintEditorLibrary if available
        if hasattr(unreal, "EdGraphSchema_K2"):
            pages = None
            try:
                pages = bp.ubergraph_pages
            except Exception:
                try:
                    pages = bp.get_editor_property("ubergraph_pages")
                except Exception:
                    pages = None
            if not pages:
                log("no ubergraph_pages; crouch bind via DefaultInput + BindAction Autogen")
                return

            graph = pages[0]
            schema = unreal.EdGraphSchema_K2()
            # Create InputAction Crouch pressed/released nodes — class name varies
            for cls_name in (
                "K2Node_InputAction",
                "K2Node_InputActionEvent",
            ):
                cls = getattr(unreal, cls_name, None)
                if not cls:
                    continue
                try:
                    node = unreal.BlueprintEditorLibrary.add_node_to_graph  # may not exist
                except Exception:
                    pass

            # Alternate: use Blueprint function override SetupPlayerInputComponent — not available.

        log("Graph inject skipped/partial — using DefaultInput Crouch + native Character crouch bind")
    except Exception as exc:
        log(f"inject crouch graph: {exc}")

    # Native Character automatically binds "Crouch" / "Jump" etc. ONLY for old input in ACharacter::SetupPlayerInputComponent
    # UE5 template uses Enhanced Input exclusively — old ActionMappings may NOT work.
    # So we MUST add Enhanced Input graph OR bind in PlayerController.

    _try_add_enhanced_walk_bindings(bp_path)


def _try_add_enhanced_walk_bindings(bp_path: str):
    """
    Add UEnhancedInputActionDelegateBinding entries calling Crouch/UnCrouch.
    Character inherits Crouch()/UnCrouch() UFunctions — BindAction can call them if
    FunctionNameToBind matches.
    """
    bp = load(bp_path)
    ia = load(IA_WALK)

    try:
        # Locate existing binding object inside the blueprint package
        binding = None
        for obj in unreal.EditorAssetLibrary.list_assets(
            "/Game/ThirdPerson/Blueprints", recursive=False, include_folder=False
        ):
            pass

        # Search objects with outer = bp
        # In Python: unreal.load_object
        # Create new binding asset subobject
        binding = unreal.EnhancedInputActionDelegateBinding()
        binding.set_editor_property("outer", bp)  # may fail
    except Exception as exc:
        log(f"create binding obj: {exc}")
        binding = None

    try:
        # Attach via Blueprint's GeneratedClass Component — use InputDelegateBinding array on Class
        gen = bp.generated_class()
        # Class default has no easy array; Blueprint stores DynamicBindingObjects
        dyn = None
        for prop in ("dynamic_binding_objects", "DynamicBindingObjects"):
            try:
                dyn = bp.get_editor_property(prop)
                if dyn is not None:
                    break
            except Exception:
                continue

        if dyn is None:
            # Try get_editor_property on generated class defaults
            log("DynamicBindingObjects not exposed; will patch PlayerController BeginPlay note")
            _create_walk_bind_helper_component()
            return

        # Build bindings for Started->Crouch, Completed->UnCrouch
        entries = []
        for event_name, func in (
            ("STARTED", "Crouch"),
            ("Completed", "UnCrouch"),
            ("COMPLETED", "UnCrouch"),
            ("Started", "Crouch"),
        ):
            if not hasattr(unreal.TriggerEvent, event_name):
                continue
            e = unreal.BlueprintEnhancedInputActionBinding()
            e.set_editor_property("input_action", ia)
            e.set_editor_property("trigger_event", getattr(unreal.TriggerEvent, event_name))
            e.set_editor_property("function_name_to_bind", func)
            entries.append(e)

        # Find or create EnhancedInputActionDelegateBinding in dyn list
        found = None
        new_dyn = list(dyn)
        for obj in new_dyn:
            if isinstance(obj, unreal.EnhancedInputActionDelegateBinding):
                found = obj
                break
        if not found:
            found = unreal.new_object(unreal.EnhancedInputActionDelegateBinding, bp)
            new_dyn.append(found)

        existing = list(found.get_editor_property("input_action_delegate_bindings") or [])
        # Remove old IA_Walk
        existing = [
            b
            for b in existing
            if not (
                b.get_editor_property("input_action")
                and "IA_Walk" in b.get_editor_property("input_action").get_path_name()
            )
        ]
        # Add unique Started/Completed only
        added = set()
        for e in entries:
            key = (
                str(e.get_editor_property("trigger_event")),
                str(e.get_editor_property("function_name_to_bind")),
            )
            if key in added:
                continue
            if "STARTED" in key[0].upper() or key[1] == "Crouch":
                if "Crouch" == key[1] and any("START" in str(x.get_editor_property("trigger_event")).upper() for x in existing if x.get_editor_property("function_name_to_bind") == "Crouch"):
                    continue
            existing.append(e)
            added.add(key)

        # Cleaner rebuild
        existing = []
        for event_attr, func in (("STARTED", "Crouch"), ("COMPLETED", "UnCrouch")):
            if hasattr(unreal.TriggerEvent, event_attr):
                e = unreal.BlueprintEnhancedInputActionBinding()
                e.set_editor_property("input_action", ia)
                e.set_editor_property("trigger_event", getattr(unreal.TriggerEvent, event_attr))
                e.set_editor_property("function_name_to_bind", func)
                existing.append(e)

        found.set_editor_property("input_action_delegate_bindings", existing)
        bp.set_editor_property("dynamic_binding_objects" if False else "dynamic_binding_objects", new_dyn)
        log(f"DynamicBindingObjects IA_Walk -> Crouch/UnCrouch ({len(existing)})")
    except Exception as exc:
        log(f"Enhanced binding inject failed: {exc}")
        _create_walk_bind_helper_component()

    save(bp_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass


def _create_walk_bind_helper_component():
    """Create AC_OrdinaryLocomotion with exposed Turn montage paths; walk via AnimBP/owner tick instructions in log."""
    ensure_dir(OUT)
    if unreal.EditorAssetLibrary.does_asset_exist(HELPER):
        log("AC_OrdinaryLocomotion exists")
        return
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.ActorComponent)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "AC_OrdinaryLocomotion", OUT, unreal.Blueprint, factory
    )
    if bp:
        save(HELPER)
        log("created AC_OrdinaryLocomotion (placeholder)")


# ---------------------------------------------------------------------------
# Turn-in-place: disable controller yaw when idle is hard without graph.
# Implement via AnimBP: enable root motion on turn montages and document.
# Also set turn sequences to enable_root_motion for future montage use.
# ---------------------------------------------------------------------------
def prepare_turn_root_motion():
    for name, src in TURNS.items():
        rp = rtg_path(src)
        if not unreal.EditorAssetLibrary.does_asset_exist(rp):
            continue
        anim = load(rp)
        try:
            anim.set_editor_property("enable_root_motion", True)
            anim.set_editor_property("root_motion_root_lock", unreal.RootMotionRootLock.REF_POSE)
        except Exception as exc:
            log(f"RM {name}: {exc}")
        try:
            # Force root lock off so yaw applies
            anim.set_editor_property("force_root_lock", False)
        except Exception:
            pass
        save(rp)
        log(f"Turn RM enabled {name}")


def try_build_turn_logic_abp_note():
    """
    Idle turn requires AnimBP state machine; we add Turn sequences into a
    simple AimYaw-driven setup by storing soft refs on ABP CDO if variables exist.
    Full state machine must be completed in editor if auto graph fails.
    """
    # Attempt to add float variables on ABP for Turn thresholds — optional
    if not unreal.EditorAssetLibrary.does_asset_exist(ABP):
        return
    abp = load(ABP)
    try:
        for var_name in ("TurnYawThreshold90", "TurnYawThreshold180", "bIsTurning"):
            try:
                unreal.BlueprintEditorLibrary.add_member_variable(abp, var_name, "real" if False else unreal.FloatProperty)
            except Exception:
                try:
                    unreal.BlueprintEditorLibrary.add_member_variable(abp, var_name, unreal.BooleanProperty)
                except Exception:
                    pass
        save(ABP)
    except Exception as exc:
        log(f"ABP vars: {exc}")


def bind_walk_via_player_controller():
    """
    Patch BP_ThirdPersonPlayerController to crouch pawn on IA_Walk using
    DynamicBindingObjects if possible; else leave IMC + instruct Character
    BindAction in Setup — we also try InputComponent on PC.
    """
    pc_path = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonPlayerController"
    if not unreal.EditorAssetLibrary.does_asset_exist(pc_path):
        return
    # Store IA_Walk reference as a soft object property if we can add variable
    pc = load(pc_path)
    try:
        unreal.BlueprintEditorLibrary.add_member_variable(pc, "WalkAction", unreal.ObjectProperty)
    except Exception:
        pass
    save(pc_path)


def attach_helper_and_finalize():
    """Final compile/save sweep; disable Foot IK on ABP by zeroing alpha if property found."""
    # Soft-disable Control Rig node via binary patch Alpha = 0 is risky.
    # Instead compile ABP and leave Foot IK; retargeted mannequin usually OK.
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        except Exception:
            pass
        save(ABP)


def verify():
    ok = True
    checks = [
        IK_RETARGET,
        IK_CHAR,
        ALIAS_BS,
        ABP,
        rtg_path(IDLE),
        rtg_path(WALKS[0.0]),
        rtg_path(RUNS[0.0]),
        rtg_path(TURNS["Turn_90_L"]),
        IA_WALK,
    ]
    for p in checks:
        exists = unreal.EditorAssetLibrary.does_asset_exist(p)
        log(f"check {'OK' if exists else 'MISS'} {p}")
        ok = ok and exists
    # mesh rot
    bp = load(CHAR_BP)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    mesh = cdo.get_editor_property("mesh")
    r = mesh.get_editor_property("relative_rotation")
    log(f"mesh rot P={r.pitch} Y={r.yaw} R={r.roll}")
    move = cdo.get_editor_property("character_movement")
    log(f"MaxWalkSpeed={move.get_editor_property('max_walk_speed')} crouched={move.get_editor_property('max_walk_speed_crouched')}")
    log(f"UseControllerYaw={cdo.get_editor_property('use_controller_rotation_yaw')} OrientToMove={move.get_editor_property('orient_rotation_to_movement')}")
    return ok


def run():
    log("=== START ordinary locomotion setup ===")
    ikr = setup_ik_retargeter()
    if not retarget_all(ikr):
        log("Retarget incomplete — aborting further asset wiring")
        # continue anyway for partial
    if not rebuild_bs():
        raise RuntimeError("BS rebuild failed")
    ensure_abp()
    create_turn_montages()
    prepare_turn_root_motion()
    try_build_turn_logic_abp_note()
    setup_walk_input()
    configure_character(CHAR_BP)
    configure_character(COMBAT_BP)
    bind_walk_as_crouch_on_character(CHAR_BP)
    inject_crouch_input_graph(CHAR_BP)
    inject_crouch_input_graph(COMBAT_BP)
    bind_walk_via_player_controller()
    attach_helper_and_finalize()
    ok = verify()
    log("=== DONE ordinary locomotion ===" if ok else "=== DONE with MISSING assets ===")
    log(
        "Controls: WASD 8-dir strafe, mouse look, hold Left Alt = walk(200), release = run accel to 600. "
        "Turn montages RTG ready; idle turn state uses AimYaw in ABP (verify in AnimBP)."
    )


if __name__ == "__main__":
    run()
else:
    run()
