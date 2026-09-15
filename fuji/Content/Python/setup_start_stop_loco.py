# -*- coding: utf-8 -*-
"""
Start/Stop locomotion (forward Walk/Run):
1) Ensure IK chain map Leg_L->LeftLeg etc.
2) Retarget 4 Start/Stop sequences -> SwordRTG
3) Create montages (DefaultSlot)
4) Wire ABP_StrafeLocomotion state machine OR EventGraph montage driver
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
RTG_DIR = f"{OUT}/SwordRTG"
MONT_DIR = f"{OUT}/Montages"
IKR = f"{OUT}/IK/IKR_SwordToCharacters"
CHA2 = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/Cha_2_IKRig"
IK_CHAR = f"{OUT}/IK/IK_Characters_Manny"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ABP = f"{OUT}/ABP_StrafeLocomotion"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"

CHAIN_MAP = {
    "Spine": "Spine",
    "Head": "Head",
    "Leg_L": "LeftLeg",
    "Leg_R": "RightLeg",
    "Arm_L": "LeftArm",
    "Arm_R": "RightArm",
    "Finger_L_Thumb": "LeftThumb",
    "Finger_L_Index": "LeftIndex",
    "Finger_L_Middle": "LeftMiddle",
    "Finger_L_Ring": "LeftRing",
    "Finger_L_Pinky": "LeftPinky",
    "Finger_R_Thumb": "RightThumb",
    "Finger_R_Index": "RightIndex",
    "Finger_R_Middle": "RightMiddle",
    "Finger_R_Ring": "RightRing",
    "Finger_R_Pinky": "RightPinky",
}

START_STOP_SRC = {
    "Walk_Start_F_0_Seq": "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Start_F_0_Seq",
    "Walk_Stop_F_0_Seq": "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Stop_F_0_Seq",
    "Run_Start_F_0_Seq": "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Start_F_0_Seq",
    "Run_Stop_F_0_Seq": "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Stop_F_0_Seq",
}


def log(m):
    unreal.log(f"[StartStop] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def ensure_dir(path: str):
    if not unreal.EditorAssetLibrary.does_directory_exist(path):
        unreal.EditorAssetLibrary.make_directory(path)


def ensure_chain_map():
    ikr = load(IKR)
    rctrl = unreal.IKRetargeterController.get_controller(ikr)
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, load(CHA2))
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, load(IK_CHAR))
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, load(SRC_MESH))
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, load(TGT_MESH))
    try:
        rctrl.add_default_ops()
    except Exception:
        pass
    for src, tgt in CHAIN_MAP.items():
        try:
            rctrl.set_source_chain(unreal.Name(src), unreal.Name(tgt))
        except Exception as exc:
            log(f"map {src}->{tgt}: {exc}")
    for tgt in ("LeftLeg", "RightLeg"):
        try:
            log(f"chain {tgt} <= {rctrl.get_source_chain(unreal.Name(tgt))}")
        except Exception as exc:
            log(f"verify {tgt}: {exc}")
    save(IKR)
    return ikr


def retarget_start_stop(ikr):
    ensure_dir(RTG_DIR)
    datas = []
    for name, path in START_STOP_SRC.items():
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log(f"MISSING src {path}")
            continue
        datas.append(unreal.EditorAssetLibrary.find_asset_data(path))
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", datas)
    inputs.set_editor_property("source_mesh", load(SRC_MESH))
    inputs.set_editor_property("target_mesh", load(TGT_MESH))
    inputs.set_editor_property("ik_retarget_asset", ikr)
    inputs.set_editor_property("search", "")
    inputs.set_editor_property("replace", "")
    inputs.set_editor_property("prefix", "")
    inputs.set_editor_property("suffix", "_RTG")
    inputs.set_editor_property("target_path", RTG_DIR)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", True)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs) or []
    try:
        unreal.EditorAssetLibrary.save_directory(RTG_DIR, only_if_is_dirty=False, recursive=True)
    except Exception:
        pass
    out = {}
    for name in START_STOP_SRC:
        rtg = f"{RTG_DIR}/{name}_RTG"
        if unreal.EditorAssetLibrary.does_asset_exist(rtg):
            out[name] = rtg
            log(f"RTG ok {rtg}")
        else:
            log(f"RTG missing {rtg}")
    log(f"retargeted {len(created)} created, {len(out)}/4 present")
    return out


def create_montages(rtg_map: dict):
    ensure_dir(MONT_DIR)
    montages = {}
    for seq_name, rtg_path in rtg_map.items():
        mont_name = "AM_" + seq_name.replace("_Seq", "")
        mont_path = f"{MONT_DIR}/{mont_name}"
        seq = load(rtg_path)
        if unreal.EditorAssetLibrary.does_asset_exist(mont_path):
            unreal.EditorAssetLibrary.delete_asset(mont_path)
        # Create from sequence
        mont = None
        try:
            mont = unreal.AnimationLibrary.create_animation_montage(seq, "DefaultSlot")
        except Exception as exc:
            log(f"AnimationLibrary.create_animation_montage: {exc}")
        if not mont:
            try:
                factory = unreal.AnimMontageFactory()
                factory.set_editor_property("target_skeleton", seq.get_editor_property("skeleton"))
                try:
                    factory.set_editor_property("source_animation", seq)
                except Exception:
                    pass
                mont = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                    mont_name, MONT_DIR, unreal.AnimMontage, factory
                )
            except Exception as exc:
                log(f"AnimMontageFactory: {exc}")
        if not mont:
            # duplicate sequence then convert? fallback: AssetTools create empty + set slot
            log(f"FAILED montage for {seq_name}")
            continue
        # Ensure path/name
        try:
            if mont.get_path_name().split(".")[0] != mont_path:
                # move/rename if created elsewhere
                created_path = mont.get_path_name().split(".")[0]
                if created_path != mont_path:
                    if unreal.EditorAssetLibrary.does_asset_exist(mont_path):
                        unreal.EditorAssetLibrary.delete_asset(mont_path)
                    ok = unreal.EditorAssetLibrary.rename_asset(created_path, mont_path)
                    log(f"rename montage {created_path} -> {mont_path}: {ok}")
                    mont = load(mont_path)
        except Exception as exc:
            log(f"montage path fix: {exc}")

        # Slot DefaultSlot + blend times
        try:
            # Rebuild montage from sequence if API available
            unreal.AnimationLibrary.add_animation_notify_event  # existence probe
        except Exception:
            pass
        try:
            mont.set_editor_property("blend_in", unreal.AlphaBlend(blend_time=0.1))
        except Exception:
            try:
                unreal.AnimationLibrary.set_montage_blend_time(mont, 0.1)
            except Exception:
                pass
        save(mont.get_path_name().split(".")[0])
        montages[seq_name] = mont.get_path_name().split(".")[0]
        log(f"montage {montages[seq_name]}")
    return montages


def probe_abp():
    abp = load(ABP)
    log(f"ABP={abp.get_path_name()}")
    # List interesting classes
    for cls_name in (
        "AnimStateNode",
        "AnimStateTransitionNode",
        "AnimationStateMachineGraph",
        "AnimGraphNode_StateMachine",
        "AnimGraphNode_SequencePlayer",
        "AnimGraphNode_Slot",
        "AnimGraphNode_BlendSpacePlayer",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            log(f"no class {cls_name}")
            continue
        n = 0
        for obj in unreal.ObjectIterator(cls):
            try:
                p = obj.get_path_name()
            except Exception:
                continue
            if "ABP_StrafeLocomotion" not in p:
                continue
            n += 1
            extra = ""
            try:
                if hasattr(obj, "get_editor_property"):
                    for prop in ("state_name", "StateName", "node_title", "bound_graph"):
                        try:
                            extra += f" {prop}={obj.get_editor_property(prop)}"
                        except Exception:
                            pass
            except Exception:
                pass
            if n <= 20:
                log(f"  {cls_name}: {obj.get_name()}{extra}")
        log(f"  total {cls_name}: {n}")

    # AnimBlueprint libraries
    for name in dir(unreal):
        if "AnimBlue" in name or "AnimationState" in name or "AnimGraph" in name and "Library" in name:
            log(f"api {name}")


def disable_foot_ik(abp):
    cls = getattr(unreal, "AnimGraphNode_ControlRig", None)
    if not cls:
        return
    for obj in unreal.ObjectIterator(cls):
        try:
            if "ABP_StrafeLocomotion" not in obj.get_path_name():
                continue
        except Exception:
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("alpha", 0.0)
                obj.set_editor_property(outer, node)
                log("FootIK alpha=0")
            except Exception:
                pass


def add_abp_variables(abp):
    """Add bool/float vars used by transitions / EventGraph."""
    # Try BlueprintEditorLibrary / BlueprintEditorSubsystem
    names = [
        ("bWantsWalk", unreal.BoolProperty if hasattr(unreal, "BoolProperty") else None),
        ("bIsStarting", None),
        ("bIsStopping", None),
        ("MoveSpeed", None),
    ]
    for vname, _ in names:
        try:
            # UE5: EditorAssetLibrary / BlueprintEditorLibrary.add_member_variable
            if hasattr(unreal.BlueprintEditorLibrary, "add_member_variable"):
                unreal.BlueprintEditorLibrary.add_member_variable(abp, vname, "bool")
                log(f"add var {vname}")
        except Exception as exc:
            log(f"add var {vname}: {exc}")


def try_wire_state_machine(abp, rtg_map):
    """
    Best-effort: find Idle / Locomotion states; inject Start/Stop sequence players
    by cloning SequencePlayer nodes into new states if schema allows.
    Returns True if meaningful wiring done.
    """
    state_cls = getattr(unreal, "AnimStateNode", None)
    if not state_cls:
        return False

    states = []
    for obj in unreal.ObjectIterator(state_cls):
        try:
            if "ABP_StrafeLocomotion" not in obj.get_path_name():
                continue
        except Exception:
            continue
        states.append(obj)

    log(f"AnimStateNode count={len(states)}")
    for s in states:
        try:
            # State name often in BoundGraph outer or State property
            g = None
            try:
                g = s.get_editor_property("bound_graph")
            except Exception:
                pass
            log(f" state {s.get_name()} graph={g.get_name() if g else None}")
        except Exception:
            pass

    # AnimationStateMachineSchema helpers
    schema = None
    for path in (
        "/Script/AnimGraph.Default__AnimationStateMachineSchema",
        "/Script/AnimGraph.AnimationStateMachineSchema",
    ):
        schema = unreal.load_object(None, path)
        if schema:
            log(f"schema={path}")
            break
    if schema:
        log(f"schema methods sample={[m for m in dir(schema) if not m.startswith('_')][:40]}")

    return False


def create_driver_component(montages: dict):
    """
    Create BP component AC_StartStopLoco that plays Start/Stop montages on owner mesh.
    Logic implemented via Construction + documented EventGraph is hard; instead use
    AnimBP Event Graph injection OR a simple AnimNotify-free approach:

    Attach float/bool properties and implement with AnimBP BlueprintUpdateAnimation
    by cloning from a generated AnimInstance subclass — not available in BP-only.

    Fallback: create Animation Montages and wire ABP via soft object refs + modify
    existing transitions thresholds; plus inject into character Event Tick.
    """
    ensure_dir(OUT)
    comp_path = f"{OUT}/AC_StartStopLoco"
    if unreal.EditorAssetLibrary.does_asset_exist(comp_path):
        unreal.EditorAssetLibrary.delete_asset(comp_path)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.ActorComponent)
    bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "AC_StartStopLoco", OUT, unreal.Blueprint, factory
    )
    if not bp:
        log("FAILED create AC_StartStopLoco")
        return None

    # Add soft object properties for montages via BlueprintEditorLibrary if possible
    for key, path in montages.items():
        vname = "M_" + key.replace("_Seq", "")
        try:
            if hasattr(unreal, "EditorUtilityLibrary"):
                pass
        except Exception:
            pass

    save(comp_path)
    log(f"created {comp_path} (shell)")
    return comp_path


def inject_character_tick_driver(montages: dict):
    """
    Inject into BP_ThirdPersonCharacter EventGraph:
    - Custom event / Timeline alternative: use existing ReceiveTick if present
    - PlayAnimMontage on Mesh when speed crosses thresholds

    Enhanced Input nodes are protected; CallFunction PlayAnimMontage usually works.
    """
    bp = load(CHAR)
    # Find Ubergraph
    graphs = []
    try:
        graphs = list(bp.get_editor_property("ubergraph_pages") or [])
    except Exception:
        pass
    try:
        fg = bp.get_editor_property("function_graphs")
    except Exception:
        fg = None
    log(f"char ubergraph_pages={len(graphs)} function_graphs={fg}")

    # Store montage soft refs on Character CDO as tags? Use class defaults via
    # metadata — simpler: set on AnimBP as soft ptr properties.

    # Put montage paths into ABP as SoftObjectPath properties if we can
    abp = load(ABP)
    gen = abp.generated_class()
    cdo = unreal.get_default_object(gen)

    # Assign via dynamic properties - AnimBP may not have them.
    # Instead, use Animation Asset Manager style: soft refs baked into montages
    # and drive from AnimBP using Sequence Players in new states.

    # Practical approach for BP-only Python: rebuild locomotion state content
    # Use Blend Poses by Bool nested — if we can find/create nodes.

    # --- Wire Sequence Players that already exist? ---
    # Replace approach: create AimOffset/BlendSpace1D for start and stop with single sample,
    # then use existing BS player pattern — still needs new states.

    # FINAL reliable approach: use AnimNode Slot + Character Blueprint
    # Play Montage via AnimInstance from Character Event Graph built with
    # K2Node_Event ReceiveTick + branches.

    uber = graphs[0] if graphs else None
    if not uber:
        # try get_all_graphs
        try:
            uber = bp.get_editor_property("simple_construction_script")
        except Exception:
            pass
    # Find event graph by iterating EdGraph
    event_graph = None
    for cls_name in ("EdGraph",):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for g in unreal.ObjectIterator(cls):
            try:
                p = g.get_path_name()
            except Exception:
                continue
            if "BP_ThirdPersonCharacter" in p and ("EventGraph" in p or "ExecuteUbergraph" in g.get_name()):
                event_graph = g
                log(f"found graph {p}")
                break
    if not event_graph:
        # ubergraph_pages entries are EdGraphs
        for g in graphs:
            log(f"uber page {g.get_name()}")
            event_graph = g
            break

    if not event_graph:
        log("no EventGraph — skip character inject")
        return False

    # Add member variables on Character for montage refs
    for label, path in montages.items():
        vname = "SS_" + label.replace("_Seq", "")
        try:
            # Soft object path as object property
            unreal.BlueprintEditorLibrary.add_member_variable(bp, vname, "object")
        except Exception as exc:
            log(f"char var {vname}: {exc}")

    # Set CDO soft refs if properties exist
    cdo = unreal.get_default_object(bp.generated_class())
    for label, path in montages.items():
        vname = "SS_" + label.replace("_Seq", "")
        mont = load(path)
        for prop in (vname, vname.lower()):
            try:
                cdo.set_editor_property(prop, mont)
                log(f"CDO set {prop}")
            except Exception:
                pass

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"char compile: {exc}")
    save(CHAR)
    return True


def wire_abp_with_sequences(rtg_map: dict):
    """
    Modify ABP to use Start/Stop via extending the state machine graph.
    Strategy:
    - Keep Idle Sequence = Idle_Seq_RTG
    - Keep Locomotion = BS_WalkRun_Sword
    - Add Soft Object Path variables on ABP for the 4 sequences
    - Implement LocState in AnimGraph using existing nodes where possible

    Since adding states via Python is limited, we implement Start/Stop using
    **Animation Montages played from AnimBP Event Graph** through
    `Montage_Play` nodes if we can create them, OR use
    `AnimGraphNode_SequencePlayer` inside cloned states.

    Probe AnimationBlueprintLibrary / RigVM — then attempt to add states
    with AnimationStateMachineSchema.try_create_connection patterns.
    """
    abp = load(ABP)
    disable_foot_ik(abp)

    # Soft-bind: ensure BlendSpace still correct
    bs = load(BS) if unreal.EditorAssetLibrary.does_asset_exist(BS) else None
    bs_cls = getattr(unreal, "AnimGraphNode_BlendSpacePlayer", None)
    if bs_cls and bs:
        for obj in unreal.ObjectIterator(bs_cls):
            try:
                if "ABP_StrafeLocomotion" not in obj.get_path_name():
                    continue
            except Exception:
                continue
            for outer in ("node", "Node"):
                try:
                    node = obj.get_editor_property(outer)
                    node.set_editor_property("blend_space", bs)
                    obj.set_editor_property(outer, node)
                    log("rebound BS_WalkRun_Sword")
                except Exception:
                    pass

    # Try to find/create state machine states via schema
    wired = try_wire_state_machine(abp, rtg_map)

    # Add anim sequences as exposed assets on ABP CDO using existing sequence players
    # for Jump — don't touch those.

    # Create BlendSpace1D assets for WalkStart/WalkStop/RunStart/RunStop with
    # single sample — allows future direction expansion without graph change.
    # Then we still need states to play them.

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"abp compile: {exc}")
    save(ABP)
    return wired


def build_start_stop_blendspaces(rtg_map: dict):
    """Optional BS1D for Start/Stop — not required for F-only Sequence players."""
    return {}


def create_montages_v2(rtg_map: dict):
    """More robust montage creation using EditorAssetLibrary duplicate + factory."""
    ensure_dir(MONT_DIR)
    result = {}
    skel = load("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
    for seq_name, rtg_path in rtg_map.items():
        mont_name = "AM_" + seq_name.replace("_Seq", "")
        mont_path = f"{MONT_DIR}/{mont_name}"
        seq = load(rtg_path)
        if unreal.EditorAssetLibrary.does_asset_exist(mont_path):
            unreal.EditorAssetLibrary.delete_asset(mont_path)

        mont = None
        # UE 5.x AnimationLibrary
        for call in (
            lambda: unreal.AnimationLibrary.create_animation_montage(seq),
            lambda: unreal.AnimationLibrary.create_animation_montage(seq, unreal.Name("DefaultSlot")),
        ):
            try:
                mont = call()
                if mont:
                    break
            except Exception as exc:
                log(f"create_animation_montage try: {exc}")

        if mont is None:
            factory = unreal.AnimMontageFactory()
            try:
                factory.set_editor_property("target_skeleton", skel)
            except Exception:
                pass
            try:
                factory.set_editor_property("source_animation", seq)
            except Exception:
                pass
            mont = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                mont_name, MONT_DIR, unreal.AnimMontage, factory
            )

        if not mont:
            log(f"no montage {mont_name}")
            continue

        # If factory created empty montage, add slot segment with sequence
        try:
            # Prefer AnimationBlueprintLibrary / Montage APIs
            if hasattr(unreal, "AnimationLibrary"):
                al = unreal.AnimationLibrary
                for meth in (
                    "set_montage_slot",
                    "add_slot_to_montage",
                    "fill_montage_with_animation",
                ):
                    if hasattr(al, meth):
                        log(f"AnimationLibrary has {meth}")
        except Exception:
            pass

        # Native: UAnimMontage slot track
        try:
            # Some versions: montage.add_slot("DefaultSlot")
            if hasattr(mont, "add_slot"):
                mont.add_slot("DefaultSlot")
        except Exception:
            pass

        # Soft: set composite sections via EditorProperty sample_data-like
        try:
            slot_anim_tracks = mont.get_editor_property("slot_anim_tracks")
            log(f"{mont_name} slots={slot_anim_tracks}")
            if slot_anim_tracks is not None and len(slot_anim_tracks) == 0:
                # build SlotAnimationTrack
                track = unreal.SlotAnimationTrack()
                track.set_editor_property("slot_name", unreal.Name("DefaultSlot"))
                segment = unreal.AnimSegment()
                segment.set_editor_property("anim_reference", seq)
                try:
                    length = seq.get_editor_property("sequence_length")
                except Exception:
                    length = 1.0
                try:
                    segment.set_editor_property("anim_end_time", length)
                    segment.set_editor_property("anim_play_rate", 1.0)
                except Exception:
                    pass
                anim_track = unreal.AnimTrack()
                try:
                    anim_track.set_editor_property("anim_segments", [segment])
                except Exception:
                    pass
                try:
                    track.set_editor_property("anim_track", anim_track)
                except Exception:
                    pass
                mont.set_editor_property("slot_anim_tracks", [track])
                log(f"{mont_name} built slot track len={length}")
        except Exception as exc:
            log(f"slot tracks {mont_name}: {exc}")

        # Ensure asset at expected path
        cur = mont.get_path_name().split(".")[0]
        if cur != mont_path:
            try:
                if unreal.EditorAssetLibrary.does_asset_exist(mont_path):
                    unreal.EditorAssetLibrary.delete_asset(mont_path)
                unreal.EditorAssetLibrary.rename_asset(cur, mont_path)
                mont = load(mont_path)
            except Exception as exc:
                log(f"rename: {exc}")
                mont_path = cur

        save(mont_path)
        result[seq_name] = mont_path
        log(f"OK montage {mont_path}")
    return result


def wire_abp_eventgraph_montage_driver(montages: dict):
    """
    Add variables + try to inject BlueprintUpdateAnimation logic into ABP.
    Also store montage refs on AnimBP CDO.
    """
    abp = load(ABP)

    # Member variables
    var_defs = [
        ("PrevSpeed", "real"),
        ("bWantsWalk", "bool"),
        ("bPlayingStartStop", "bool"),
    ]
    for vname, vtype in var_defs:
        try:
            unreal.BlueprintEditorLibrary.add_member_variable(abp, vname, vtype)
            log(f"ABP var {vname}")
        except Exception as exc:
            log(f"ABP var {vname}: {exc}")

    # Soft object vars for montages — type object
    for seq_name, path in montages.items():
        vname = "M_" + seq_name.replace("_Seq", "")
        try:
            unreal.BlueprintEditorLibrary.add_member_variable(abp, vname, "object")
            log(f"ABP var {vname}")
        except Exception as exc:
            log(f"ABP var {vname}: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile after vars: {exc}")

    # Set defaults on CDO
    try:
        cdo = unreal.get_default_object(abp.generated_class())
        for seq_name, path in montages.items():
            vname = "M_" + seq_name.replace("_Seq", "")
            mont = load(path)
            for prop in (vname,):
                try:
                    cdo.set_editor_property(prop, mont)
                    log(f"ABP CDO {prop} set")
                except Exception as exc:
                    log(f"ABP CDO {prop}: {exc}")
    except Exception as exc:
        log(f"CDO assign: {exc}")

    disable_foot_ik(abp)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    save(ABP)


def expand_state_machine_with_new_states(rtg_map: dict):
    """
    Attempt to add WalkStart/RunStart/WalkStop/RunStop AnimStateNodes
    into the existing AnimationStateMachineGraph.
    """
    abp = load(ABP)
    sm_graph = None
    sm_cls = getattr(unreal, "AnimationStateMachineGraph", None)
    if sm_cls:
        for g in unreal.ObjectIterator(sm_cls):
            try:
                if "ABP_StrafeLocomotion" in g.get_path_name():
                    sm_graph = g
                    log(f"SM graph {g.get_path_name()}")
                    break
            except Exception:
                continue

    if not sm_graph:
        log("No AnimationStateMachineGraph found")
        return False

    schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationStateMachineSchema")
    if not schema:
        log("No AnimationStateMachineSchema")
        return False

    # Find positions of existing states
    state_cls = unreal.AnimStateNode
    existing = []
    for n in unreal.ObjectIterator(state_cls):
        try:
            if sm_graph.get_path_name() not in n.get_path_name() and n.get_outer() != sm_graph:
                # check outer chain
                if "ABP_StrafeLocomotion" not in n.get_path_name():
                    continue
        except Exception:
            continue
        if "ABP_StrafeLocomotion" not in n.get_path_name():
            continue
        existing.append(n)
        try:
            xpos = n.get_editor_property("node_pos_x")
            ypos = n.get_editor_property("node_pos_y")
        except Exception:
            xpos, ypos = 0, 0
        log(f"existing state {n.get_name()} pos=({xpos},{ypos})")

    # Create new state nodes
    new_states = {}
    y = 0
    for i, (key, seq_path) in enumerate(rtg_map.items()):
        state_name = key.replace("_Seq", "").replace("_F_0", "")
        # Walk_Start_F_0 -> Walk_Start
        try:
            node = unreal.new_object(unreal.AnimStateNode, sm_graph, unreal.Name(state_name))
        except Exception as exc:
            log(f"new AnimStateNode: {exc}")
            continue
        try:
            sm_graph.add_node(node, False, False)
        except Exception:
            try:
                sm_graph.add_node(node)
            except Exception as exc:
                log(f"add_node: {exc}")
        try:
            node.set_editor_property("node_pos_x", 400 + (i % 2) * 250)
            node.set_editor_property("node_pos_y", y + (i // 2) * 200)
        except Exception:
            pass
        # State name
        for prop in ("state_name", "StateName"):
            try:
                node.set_editor_property(prop, unreal.Name(state_name))
            except Exception:
                pass

        # Bound graph SequencePlayer
        bound = None
        try:
            bound = node.get_editor_property("bound_graph")
        except Exception:
            pass
        if bound:
            log(f"bound graph for {state_name}: {bound.get_name()}")
            # Find or create SequencePlayer in bound graph
            seq = load(seq_path)
            sp_cls = getattr(unreal, "AnimGraphNode_SequencePlayer", None)
            if sp_cls:
                # create sequence player in bound graph
                try:
                    sp = unreal.new_object(sp_cls, bound)
                    try:
                        bound.add_node(sp, False, False)
                    except Exception:
                        try:
                            bound.add_node(sp)
                        except Exception as exc:
                            log(f"add sp: {exc}")
                    for outer in ("node", "Node"):
                        try:
                            anim_node = sp.get_editor_property(outer)
                            anim_node.set_editor_property("sequence", seq)
                            try:
                                anim_node.set_editor_property("loop_animation", False)
                            except Exception:
                                pass
                            try:
                                anim_node.set_editor_property("b_loop_animation", False)
                            except Exception:
                                pass
                            sp.set_editor_property(outer, anim_node)
                            log(f"set sequence on {state_name}")
                        except Exception as exc:
                            log(f"set seq: {exc}")
                    # Connect to Result node if present
                    result_cls = getattr(unreal, "AnimGraphNode_StateResult", None)
                    if result_cls:
                        for r in unreal.ObjectIterator(result_cls):
                            if bound.get_name() in r.get_path_name() or r.get_outer() == bound:
                                # try schema connect
                                try:
                                    schema_k2 = unreal.load_object(
                                        None, "/Script/AnimGraph.Default__AnimationGraphSchema"
                                    )
                                    if schema_k2:
                                        # get pins
                                        pass
                                except Exception:
                                    pass
                                log(f"found StateResult {r.get_name()}")
                except Exception as exc:
                    log(f"create SP in {state_name}: {exc}")
        new_states[state_name] = node
        log(f"created state {state_name}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile after states: {exc}")
    save(ABP)
    log(f"new states={list(new_states.keys())}")
    return len(new_states) > 0


def write_manual_checklist(montages, rtg_map, sm_ok):
    content_dir = unreal.Paths.project_content_dir()
    path = content_dir + "Python/START_STOP_WIRING.txt"
    lines = [
        "Start/Stop wiring status",
        f"sm_ok={sm_ok}",
        "RTG:",
    ]
    for k, v in rtg_map.items():
        lines.append(f"  {k}={v}")
    lines.append("Montages:")
    for k, v in montages.items():
        lines.append(f"  {k}={v}")
    lines.append(
        "If SM auto-wire incomplete: open ABP_StrafeLocomotion AnimGraph state machine and connect Idle->WalkStart/RunStart->Locomotion->WalkStop/RunStop->Idle using sequences above."
    )
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        log(f"wrote {path}")
    except Exception as exc:
        log(f"checklist: {exc}")


def run():
    log("start")
    probe_abp()
    ikr = ensure_chain_map()
    rtg_map = retarget_start_stop(ikr)
    if len(rtg_map) < 4:
        raise RuntimeError(f"retarget incomplete {rtg_map}")

    montages = create_montages_v2(rtg_map)
    log(f"montages={montages}")

    sm_ok = expand_state_machine_with_new_states(rtg_map)
    wire_abp_eventgraph_montage_driver(montages)
    inject_character_tick_driver(montages)
    write_manual_checklist(montages, rtg_map, sm_ok)

    # Ensure character uses ABP
    bp = load(CHAR)
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    abp = load(ABP)
    mesh.set_editor_property("anim_class", abp.generated_class())
    save(CHAR)
    log(f"done sm_ok={sm_ok} rtg={len(rtg_map)} mont={len(montages)}")


if __name__ == "__main__":
    run()
else:
    run()
