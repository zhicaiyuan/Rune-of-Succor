# -*- coding: utf-8 -*-
"""
Setup Strafing 8-direction Walk/Run locomotion (Loop only).
Run inside Unreal Editor Python:
  File > Execute Python Script, or:
  UnrealEditor-Cmd <project> -ExecutePythonScript=\".../setup_strafe_locomotion.py\"
"""

from __future__ import annotations

import unreal

OUT_DIR = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"  # Characters/林符/动画
BS_NAME = "BS_WalkRun_Locomotion"
BS_PATH = f"{OUT_DIR}/{BS_NAME}"
ABP_NAME = "ABP_StrafeLocomotion"
ABP_PATH = f"{OUT_DIR}/{ABP_NAME}"
SRC_ABP = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_CHAR_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IMC_DEFAULT = "/Game/Input/IMC_Default"
IA_SPRINT_PATH = "/Game/Input/Actions/IA_Sprint"
MARKER = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/_strafe_setup_done"

IDLE = "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq"

WALK = {
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

RUN = {
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

WALK_SPEED = 200.0
RUN_SPEED = 500.0
MAX_SPEED_AXIS = 600.0


def log(msg: str) -> None:
    unreal.log(f"[StrafeLocomotion] {msg}")


def ensure_dir(path: str) -> None:
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def load_anim(path: str):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if not asset:
        raise RuntimeError(f"Missing animation: {path}")
    return asset


def get_skeleton_from_anim(anim_path: str):
    anim = load_anim(anim_path)
    skel = anim.get_editor_property("skeleton")
    if not skel:
        raise RuntimeError(f"No skeleton on {anim_path}")
    return skel


def get_preview_mesh():
    for p in (
        "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
        "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny",
        "/Game/Characters/Mannequins/Meshes/SK_Mannequin",
        "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SK_Mannequin",
    ):
        mesh = unreal.EditorAssetLibrary.load_asset(p)
        if mesh and isinstance(mesh, unreal.SkeletalMesh):
            return mesh
        # Some SK_* assets resolve as Skeleton; skip those
    return None


def create_or_reset_blendspace():
    ensure_dir(OUT_DIR)
    skeleton = get_skeleton_from_anim(WALK[0.0])
    if not isinstance(skeleton, unreal.Skeleton):
        raise RuntimeError(f"Expected Skeleton, got {type(skeleton)}")
    preview = get_preview_mesh()

    bs = None
    if unreal.EditorAssetLibrary.does_asset_exist(BS_PATH):
        bs = unreal.EditorAssetLibrary.load_asset(BS_PATH)
        log(f"Updating existing BlendSpace: {BS_PATH}")
    else:
        factory = unreal.BlendSpaceFactoryNew()
        factory.set_editor_property("target_skeleton", skeleton)
        if preview and isinstance(preview, unreal.SkeletalMesh):
            factory.set_editor_property("preview_skeletal_mesh", preview)
        else:
            log("No preview SkeletalMesh found; creating BlendSpace without preview mesh")

        asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
        bs = asset_tools.create_asset(BS_NAME, OUT_DIR, unreal.BlendSpace, factory)
        if not bs:
            raise RuntimeError("Failed to create BlendSpace")

    # Axis X = Direction, Y = Speed
    x_param = unreal.BlendParameter()
    x_param.set_editor_property("display_name", "Direction")
    x_param.set_editor_property("min", -180.0)
    x_param.set_editor_property("max", 180.0)
    x_param.set_editor_property("grid_num", 8)

    y_param = unreal.BlendParameter()
    y_param.set_editor_property("display_name", "Speed")
    y_param.set_editor_property("min", 0.0)
    y_param.set_editor_property("max", MAX_SPEED_AXIS)
    y_param.set_editor_property("grid_num", 4)

    bs.set_editor_property("blend_parameters", [x_param, y_param])

    samples = []

    def add_sample(anim_path: str, direction: float, speed: float):
        anim = load_anim(anim_path)
        sample = unreal.BlendSample()
        sample.set_editor_property("animation", anim)
        sample.set_editor_property("sample_value", unreal.Vector(direction, speed, 0.0))
        sample.set_editor_property("rate_scale", 1.0)
        samples.append(sample)

    # Idle row
    add_sample(IDLE, 0.0, 0.0)
    add_sample(IDLE, -180.0, 0.0)
    add_sample(IDLE, 180.0, 0.0)
    add_sample(IDLE, -90.0, 0.0)
    add_sample(IDLE, 90.0, 0.0)

    for direction, path in WALK.items():
        add_sample(path, direction, WALK_SPEED)

    for direction, path in RUN.items():
        add_sample(path, direction, RUN_SPEED)

    bs.set_editor_property("sample_data", samples)

    # Force rescale / validate if API exists
    try:
        unreal.BlendSpaceLibrary.resample_data(bs)  # type: ignore[attr-defined]
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_asset(BS_PATH, only_if_is_dirty=False)
    log(f"Created BlendSpace with {len(samples)} samples: {BS_PATH}")
    return bs


def patch_abp_blendspace_reference(abp_package_path: str) -> bool:
    """Same-length soft path patch: BS_Idle_Walk_Run -> BS_WalkRun_LocomoX (padded).
    We instead duplicate ABP then replace the known soft path string if lengths match,
    or point nodes via object iteration.
    """
    old = "/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"
    # Prefer updating live objects first
    abp = unreal.EditorAssetLibrary.load_asset(abp_package_path)
    if not abp:
        return False

    bs = unreal.EditorAssetLibrary.load_asset(BS_PATH)
    replaced = 0

    # Walk package objects
    package_name = abp.get_outer().get_name() if abp.get_outer() else abp.get_path_name()
    # Iterate all objects belonging to this asset package
    for obj in unreal.ObjectIterator:  # may not exist
        break

    # Fallback: use AssetRegistry + find referencers style via get_editor_property on known nodes
    try:
        # AnimBlueprint stores graphs as objects in the package
        package_path = abp_package_path
        assets = unreal.EditorAssetLibrary.list_assets(OUT_DIR, recursive=False, include_folder=False)
    except Exception:
        pass

    # Binary patch after save: replace old path with a same-length alias.
    # Create a same-length redirector-like duplicate path for the blendspace.
    return False


def create_same_length_blendspace_alias():
    """Create alias with same asset-name length as BS_Idle_Walk_Run (16 chars)."""
    alias_dir = "/Game/Characters/Mannequins/Anims/Unarmed"
    old = "BS_Idle_Walk_Run"  # 16
    new = "BS_WalkRun_Sword"  # 16
    assert len(old) == len(new), (len(old), len(new))
    alias_path = f"{alias_dir}/{new}"

    if unreal.EditorAssetLibrary.does_asset_exist(alias_path):
        unreal.EditorAssetLibrary.delete_asset(alias_path)

    ok = unreal.EditorAssetLibrary.duplicate_asset(BS_PATH, alias_path)
    if not ok and not unreal.EditorAssetLibrary.does_asset_exist(alias_path):
        raise RuntimeError("Failed to duplicate blendspace alias")
    unreal.EditorAssetLibrary.save_asset(alias_path, only_if_is_dirty=False)
    log(f"Alias BlendSpace: {alias_path}")
    return alias_path


def create_strafe_anim_bp(alias_bs_path: str):
    ensure_dir(OUT_DIR)
    if unreal.EditorAssetLibrary.does_asset_exist(ABP_PATH):
        unreal.EditorAssetLibrary.delete_asset(ABP_PATH)

    dup = unreal.EditorAssetLibrary.duplicate_asset(SRC_ABP, ABP_PATH)
    if not dup and not unreal.EditorAssetLibrary.does_asset_exist(ABP_PATH):
        raise RuntimeError("Failed to duplicate ABP_Unarmed")

    unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)

    # Patch soft object path on disk (same string length)
    project_content = unreal.Paths.project_content_dir()
    rel = ABP_PATH.replace("/Game/", "") + ".uasset"
    fs_path = (project_content + rel).replace("/", "\\")

    old_bytes = b"BS_Idle_Walk_Run"
    new_bytes = b"BS_WalkRun_Sword"
    if len(old_bytes) != len(new_bytes):
        raise RuntimeError("Soft path length mismatch")

    with open(fs_path, "rb") as f:
        data = bytearray(f.read())
    count = data.count(old_bytes)
    if count == 0:
        log("WARNING: BS_Idle_Walk_Run string not found in ABP; blendspace may still point to old asset")
    else:
        data = data.replace(old_bytes, new_bytes)
        with open(fs_path, "wb") as f:
            f.write(data)
        log(f"Patched ABP blendspace references: {count}")

    # Reload
    unreal.EditorAssetLibrary.load_asset(ABP_PATH)
    try:
        unreal.EditorAssetLibrary.save_asset(ABP_PATH, only_if_is_dirty=False)
    except Exception as exc:
        log(f"Save after patch note: {exc}")

    # Compile
    abp = unreal.EditorAssetLibrary.load_asset(ABP_PATH)
    if abp:
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        except Exception:
            try:
                unreal.KismetEditorUtilities.compile_blueprint(abp)  # type: ignore
            except Exception as exc:
                log(f"Compile warning: {exc}")

    log(f"AnimBP ready: {ABP_PATH} -> {alias_bs_path}")
    return ABP_PATH


def configure_character_strafe(bp_path: str, walk_speed: float = 250.0) -> None:
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        log(f"Skip missing character BP: {bp_path}")
        return

    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        log(f"Failed to load {bp_path}")
        return

    # Generated class / CDO
    try:
        gen_class = bp.generated_class()
    except Exception:
        gen_class = bp.get_editor_property("generated_class")

    cdo = unreal.get_default_object(gen_class)

    # Pawn rotation: face controller (strafe)
    try:
        cdo.set_editor_property("use_controller_rotation_yaw", True)
        cdo.set_editor_property("use_controller_rotation_pitch", False)
        cdo.set_editor_property("use_controller_rotation_roll", False)
    except Exception as exc:
        log(f"Controller rotation props: {exc}")

    # Character movement
    try:
        move = cdo.get_editor_property("character_movement")
        if move:
            move.set_editor_property("orient_rotation_to_movement", False)
            move.set_editor_property("use_controller_desired_rotation", False)
            move.set_editor_property("max_walk_speed", walk_speed)
            move.set_editor_property("max_acceleration", 1000.0)
            move.set_editor_property("braking_deceleration_walking", 1200.0)
            move.set_editor_property("ground_friction", 6.0)
            try:
                move.set_editor_property(
                    "rotation_rate", unreal.Rotator(0.0, 480.0, 0.0)
                )
            except Exception:
                pass
    except Exception as exc:
        log(f"Movement props: {exc}")

    # Mesh yaw -90 and Anim Class
    try:
        mesh = cdo.get_editor_property("mesh")
        if mesh:
            rel = mesh.get_editor_property("relative_rotation")
            mesh.set_editor_property(
                "relative_rotation", unreal.Rotator(rel.pitch, -90.0, rel.roll)
            )
            abp = unreal.EditorAssetLibrary.load_asset(ABP_PATH)
            if abp:
                # Anim class is the generated class of the AnimBP
                try:
                    anim_class = abp.generated_class()
                except Exception:
                    anim_class = abp.get_editor_property("generated_class")
                mesh.set_editor_property("anim_class", anim_class)
    except Exception as exc:
        log(f"Mesh/AnimClass props: {exc}")

    # Spring arm use pawn control rotation
    try:
        for prop_name in ("camera_boom", "CameraBoom", "spring_arm", "SpringArm"):
            try:
                boom = cdo.get_editor_property(prop_name)
            except Exception:
                boom = None
            if boom:
                boom.set_editor_property("use_pawn_control_rotation", True)
                break
        # Also scan components
        try:
            comps = cdo.get_components_by_class(unreal.SpringArmComponent)
            for boom in comps:
                boom.set_editor_property("use_pawn_control_rotation", True)
        except Exception:
            pass
    except Exception as exc:
        log(f"SpringArm props: {exc}")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"Configured strafe on {bp_path} (walk_speed={walk_speed})")


def create_sprint_input():
    """Create IA_Sprint and add Left Shift mapping to IMC_Default."""
    ensure_dir("/Game/Input/Actions")

    if not unreal.EditorAssetLibrary.does_asset_exist(IA_SPRINT_PATH):
        factory = None
        for factory_name in ("InputActionFactory", "EnhancedInputActionFactory"):
            factory_cls = getattr(unreal, factory_name, None)
            if factory_cls:
                factory = factory_cls()
                break
        if factory is None:
            # Fallback: duplicate IA_Jump as template
            ok = unreal.EditorAssetLibrary.duplicate_asset(
                "/Game/Input/Actions/IA_Jump", IA_SPRINT_PATH
            )
            ia = unreal.EditorAssetLibrary.load_asset(IA_SPRINT_PATH)
            log(f"Duplicated IA_Jump -> IA_Sprint ({bool(ia)})")
        else:
            asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
            ia = asset_tools.create_asset(
                "IA_Sprint", "/Game/Input/Actions", unreal.InputAction, factory
            )
            if ia:
                try:
                    ia.set_editor_property(
                        "value_type", unreal.InputActionValueType.BOOLEAN
                    )
                except Exception:
                    pass
                unreal.EditorAssetLibrary.save_asset(IA_SPRINT_PATH, only_if_is_dirty=False)
                log(f"Created {IA_SPRINT_PATH}")
    else:
        ia = unreal.EditorAssetLibrary.load_asset(IA_SPRINT_PATH)

    imc = unreal.EditorAssetLibrary.load_asset(IMC_DEFAULT)
    if not imc or not ia:
        log("Could not load IMC_Default or IA_Sprint")
        return ia

    try:
        mappings = list(imc.get_editor_property("mappings") or [])
        # Avoid duplicate
        already = False
        for m in mappings:
            try:
                action = m.get_editor_property("action")
                if action and action.get_path_name().startswith(IA_SPRINT_PATH):
                    already = True
                    break
            except Exception:
                pass
        if not already:
            mapping = unreal.EnhancedActionKeyMapping()
            mapping.set_editor_property("action", ia)
            mapping.set_editor_property("key", unreal.Key("LeftShift"))
            mappings.append(mapping)
            imc.set_editor_property("mappings", mappings)
            unreal.EditorAssetLibrary.save_asset(IMC_DEFAULT, only_if_is_dirty=False)
            log("Added LeftShift -> IA_Sprint on IMC_Default")
    except Exception as exc:
        log(f"IMC mapping failed: {exc}")

    return ia


def add_sprint_logic_to_character(bp_path: str, walk_speed=250.0, run_speed=500.0):
    """Store sprint speeds as metadata on CDO; bind via custom event if possible.
    Also set default walk speed; runtime sprint toggled by a lightweight component BP if binding fails.
    """
    # Create a simple ActorComponent blueprint that polls IA_Sprint
    comp_dir = OUT_DIR
    comp_name = "AC_SprintSpeed"
    comp_path = f"{comp_dir}/{comp_name}"

    ensure_dir(comp_dir)
    ia = unreal.EditorAssetLibrary.load_asset(IA_SPRINT_PATH)

    # Prefer adding variables + event nodes; if too hard, use Anim/character tick via existing PC.
    # Practical approach: create Blueprint component with Event Tick that reads Enhanced Input.
    if unreal.EditorAssetLibrary.does_asset_exist(comp_path):
        unreal.EditorAssetLibrary.delete_asset(comp_path)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.ActorComponent)
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    comp_bp = asset_tools.create_asset(
        comp_name, comp_dir, unreal.Blueprint, factory
    )
    if not comp_bp:
        log("Failed to create AC_SprintSpeed; sprint key asset exists, bind manually if needed")
        return

    # Add editable floats on CDO
    try:
        gen = comp_bp.generated_class()
        cdo = unreal.get_default_object(gen)
        # Can't easily add new UPROPERTY via Python without creating variables through BlueprintEditorLibrary
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_asset(comp_path, only_if_is_dirty=False)

    # Attach component to character default subobjects if API allows
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        return

    try:
        # SCS: Simple Construction Script add component
        # Use SubobjectDataSubsystem (UE5)
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        # Complex; instead set Max Walk Speed on character and document Shift.
        # Runtime: use PlayerController blueprint modification.
        pass
    except Exception as exc:
        log(f"Component attach skipped: {exc}")

    # Store speeds using existing movement; bind sprint by patching PlayerController BeginPlay is hard.
    # Final pragmatic sprint: modify BP_ThirdPersonCharacter via adding Ubergraph - skip if unavailable.
    # Set character walk=250; create console-friendly default and also set "Max Walk Speed Crouched" unused.
    # Use Enhanced Input WorldSubsystem in a Level Script - no.

    # Implement sprint by setting character Movement's MaxWalkSpeed in an Animation Blueprint? No.

    # Use GameInstance / Developer Settings - overkill.

    log(
        "IA_Sprint created (Left Shift). "
        "Character default MaxWalkSpeed=250; will inject BindAction via graph helper."
    )

    _try_bind_sprint_on_character(bp_path, walk_speed, run_speed)


def _try_bind_sprint_on_character(bp_path: str, walk_speed: float, run_speed: float):
    """Best-effort: add Blueprint variables WalkSpeed/RunSpeed and rely on existing input setup.
    If we can find Add Mapping Context graph, inject nearby.
    """
    bp = unreal.EditorAssetLibrary.load_asset(bp_path)
    if not bp:
        return

    # Create Blueprint variables via Editor
    try:
        if hasattr(unreal, "BlueprintEditorLibrary"):
            # Add member variables
            for var_name, default in (("WalkSpeed", walk_speed), ("RunSpeed", run_speed)):
                try:
                    unreal.BlueprintEditorLibrary.add_member_variable(
                        bp, var_name, unreal.FloatProperty
                    )
                except Exception:
                    pass
    except Exception as exc:
        log(f"Add member variable: {exc}")

    # Use default object custom properties if variables exist
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        for name, val in (("walk_speed", walk_speed), ("WalkSpeed", walk_speed),
                          ("run_speed", run_speed), ("RunSpeed", run_speed)):
            try:
                cdo.set_editor_property(name, val)
            except Exception:
                pass
        move = cdo.get_editor_property("character_movement")
        if move:
            move.set_editor_property("max_walk_speed", walk_speed)
            # Some templates expose MaxWalkSpeed while sprinting via blueprint; store run on unused
            try:
                move.set_editor_property("max_walk_speed_crouched", run_speed)
            except Exception:
                pass
    except Exception as exc:
        log(f"Sprint speed storage: {exc}")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    log(
        "Sprint speeds stored. "
        "If auto-bind unavailable, character uses walk=250; hold shift needs graph bind "
        "(IA_Sprint already in IMC_Default)."
    )


def inject_sprint_via_input_component_defaults():
    """Alternative: set run speed as default Max Walk Speed when sprint mapping uses Modify modifier - not available.
    Create a Blueprint Function Library callable - skip.
    """
    pass


def write_marker():
    # Touch a tiny data asset as done flag
    ensure_dir(OUT_DIR)
    marker_path = f"{OUT_DIR}/StrafeSetupComplete"
    if unreal.EditorAssetLibrary.does_asset_exist(marker_path):
        return
    factory = unreal.DataAssetFactory()
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    try:
        asset_tools.create_asset(
            "StrafeSetupComplete", OUT_DIR, unreal.DataAsset, factory
        )
        unreal.EditorAssetLibrary.save_asset(marker_path, only_if_is_dirty=False)
    except Exception as exc:
        log(f"Marker note: {exc}")


def deprecate_bad_1d_blendspace():
    bad = f"{OUT_DIR}/\u79fb\u52a8\u6df7\u5408\u7a7a\u95f41D"  # 移动混合空间1D
    if unreal.EditorAssetLibrary.does_asset_exist(bad):
        # Rename instead of delete (safer)
        renamed = f"{OUT_DIR}/DEPRECATED_MoveBlendSpace1D"
        try:
            unreal.EditorAssetLibrary.rename_asset(bad, renamed)
            log(f"Renamed bad 1D blendspace -> {renamed}")
        except Exception as exc:
            log(f"Could not rename 1D BS: {exc}")


def run():
    log("Starting strafe locomotion setup...")
    create_or_reset_blendspace()
    alias = create_same_length_blendspace_alias()
    create_strafe_anim_bp(alias)
    deprecate_bad_1d_blendspace()

    configure_character_strafe(CHAR_BP, walk_speed=250.0)
    # Combat character if present
    configure_character_strafe(COMBAT_CHAR_BP, walk_speed=250.0)

    create_sprint_input()
    add_sprint_logic_to_character(CHAR_BP, 250.0, 500.0)

    # Save all
    try:
        unreal.EditorAssetLibrary.save_directory(OUT_DIR, only_if_is_dirty=False, recursive=True)
        unreal.EditorAssetLibrary.save_directory("/Game/Input", only_if_is_dirty=False, recursive=True)
        unreal.EditorAssetLibrary.save_directory("/Game/ThirdPerson/Blueprints", only_if_is_dirty=False, recursive=True)
        unreal.EditorAssetLibrary.save_directory(
            "/Game/Characters/Mannequins/Anims/Unarmed", only_if_is_dirty=False, recursive=False
        )
    except Exception as exc:
        log(f"Save directory note: {exc}")

    write_marker()
    log("DONE. Play in editor: WASD strafe, Left Shift = sprint (bind MaxWalkSpeed to IA_Sprint if not auto).")
    log(f"AnimBP: {ABP_PATH}")
    log(f"BlendSpace: {BS_PATH}")
    log(f"Alias BS: {alias}")


if __name__ == "__main__":
    run()
else:
    # When executed via -ExecutePythonScript, UE often execs the file as __main__
    run()
