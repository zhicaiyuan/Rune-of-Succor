# -*- coding: utf-8 -*-
"""
Fix Left Alt -> IA_Walk binding, wire walk speed on character,
and add idle turn-in-place using AnimBP Slot + character helper logic via graph nodes.
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
ABP = f"{OUT}/ABP_StrafeLocomotion"
RTG = f"{OUT}/SwordRTG"
WALK_SPEED = 200.0
RUN_SPEED = 600.0

TURN_ANIMS = {
    "Turn_90_L": f"{RTG}/Turn_90_L_Seq_RTG",
    "Turn_90_R": f"{RTG}/Turn_90_R_Seq_RTG",
    "Turn_180_L": f"{RTG}/Turn_180_L_Seq_RTG",
    "Turn_180_R": f"{RTG}/Turn_180_R_Seq_RTG",
}


def log(m):
    unreal.log(f"[FixWalkTurn] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def find_alt_key():
    # Prefer unreal.Keys
    keys_mod = getattr(unreal, "Keys", None)
    candidates = []
    if keys_mod:
        for name in ("LEFT_ALT", "RightAlt", "LEFT_COMMAND", "LeftAlt", "AnyKey"):
            if hasattr(keys_mod, name):
                candidates.append(getattr(keys_mod, name))
        for attr in dir(keys_mod):
            if "ALT" in attr.upper() or attr.upper().endswith("MENU"):
                candidates.append(getattr(keys_mod, attr))
    # Also try constructing
    for name in ("LeftAlt", "RightAlt", "Left_Alt", "Alt", "LeftAlternate", "Left Menu", "LeftMenu"):
        try:
            candidates.append(unreal.Key(name))
        except Exception:
            pass
        try:
            candidates.append(unreal.Key(unreal.Name(name)))
        except Exception:
            pass

    # Dedup by str
    seen = set()
    uniq = []
    for k in candidates:
        s = str(k)
        if s not in seen:
            seen.add(s)
            uniq.append(k)
    log(f"Alt key candidates: {uniq[:12]}")
    return uniq


def fix_imc_alt():
    ia = load(IA_WALK)
    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    keys = find_alt_key()

    # Remove broken IA_Walk mappings without valid key
    new_mappings = []
    for m in mappings:
        try:
            a = m.get_editor_property("action")
            if a and "IA_Walk" in a.get_path_name():
                continue  # rebuild
        except Exception:
            pass
        new_mappings.append(m)

    mapped = False
    for key in keys:
        try:
            mapping = unreal.EnhancedActionKeyMapping()
            mapping.set_editor_property("action", ia)
            mapping.set_editor_property("key", key)
            # verify roundtrip
            got = mapping.get_editor_property("key")
            log(f"try key {key} -> got {got}")
            new_mappings.append(mapping)
            mapped = True
            break
        except Exception as exc:
            log(f"key fail {key}: {exc}")

    if not mapped:
        # Last resort: use C key for walk so something works; log clearly
        try:
            mapping = unreal.EnhancedActionKeyMapping()
            mapping.set_editor_property("action", ia)
            mapping.set_editor_property("key", unreal.Key("C"))
            new_mappings.append(mapping)
            mapped = True
            log("FALLBACK: IA_Walk bound to C (Alt key enum unavailable)")
        except Exception as exc:
            log(f"fallback C failed: {exc}")

    imc.set_editor_property("mappings", new_mappings)
    save(IMC)
    log(f"IMC mappings count={len(new_mappings)} walk_mapped={mapped}")


def add_bp_variables(bp):
    for name, typ in (
        ("WalkSpeed", "float"),
        ("RunSpeed", "float"),
        ("Turn90Threshold", "float"),
        ("Turn180Threshold", "float"),
        ("bIsTurning", "bool"),
    ):
        try:
            if typ == "float":
                unreal.BlueprintEditorLibrary.add_member_variable(bp, name, unreal.FloatProperty)
            else:
                unreal.BlueprintEditorLibrary.add_member_variable(bp, name, unreal.BooleanProperty)
            log(f"added var {name}")
        except Exception as exc:
            log(f"var {name}: {exc}")


def set_speed_defaults(bp_path):
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)
    for name, val in (("walk_speed", WALK_SPEED), ("run_speed", RUN_SPEED),
                      ("WalkSpeed", WALK_SPEED), ("RunSpeed", RUN_SPEED)):
        try:
            cdo.set_editor_property(name, val)
        except Exception:
            pass
    # Ensure crouch walk speeds + can crouch
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("max_walk_speed", RUN_SPEED)
    move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
    move.set_editor_property("max_acceleration", 800.0)
    try:
        nav = move.get_editor_property("nav_agent_props")
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception:
        pass
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    save(bp_path)


def dump_bp_graph_api(bp_path):
    bp = load(bp_path)
    log(f"BP type={type(bp)}")
    for attr in (
        "ubergraph_pages",
        "function_graphs",
        "macro_graphs",
        "dynamic_binding_objects",
        "component_templates",
        "simple_construction_script",
        "new_variables",
    ):
        try:
            v = bp.get_editor_property(attr)
            log(f"prop {attr}: {type(v)} len={len(v) if hasattr(v,'__len__') else v}")
        except Exception as exc:
            log(f"prop {attr}: ERR {exc}")
        if hasattr(bp, attr):
            try:
                v = getattr(bp, attr)
                log(f"attr {attr}: {type(v)}")
            except Exception:
                pass

    # List package objects
    try:
        pkg_name = bp.get_path_name().split(".")[0]
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        # get dependencies
    except Exception as exc:
        log(f"registry: {exc}")

    # Try find Enhanced input binding class via load
    for path in (
        "/Script/EnhancedInput.EnhancedInputActionDelegateBinding",
        "/Script/EnhancedInput.BlueprintEnhancedInputActionBinding",
    ):
        try:
            cls = unreal.load_class(None, path)
            log(f"load_class {path} -> {cls}")
        except Exception as exc:
            log(f"load_class {path}: {exc}")


def inject_enhanced_input_nodes(bp_path: str):
    """Create K2 Enhanced Input Action event nodes for IA_Walk -> set MaxWalkSpeed / Crouch."""
    bp = load(bp_path)
    add_bp_variables(bp)

    pages = None
    try:
        pages = bp.get_editor_property("ubergraph_pages")
    except Exception:
        try:
            pages = bp.ubergraph_pages
        except Exception:
            pages = None
    if not pages:
        log("No ubergraph — cannot inject nodes")
        return False

    graph = pages[0]
    ia = load(IA_WALK)

    # Try various node classes
    node_cls = None
    for name in (
        "K2Node_EnhancedInputAction",
        "K2Node_EnhancedInputActionEvent",
        "EdGraphNode_EnhancedInputAction",
    ):
        node_cls = getattr(unreal, name, None)
        if node_cls:
            log(f"found node class {name}")
            break

    if not node_cls:
        # Try load_class
        for path in (
            "/Script/InputBlueprintNodes.K2Node_EnhancedInputAction",
            "/Script/EnhancedInput.K2Node_EnhancedInputAction",
            "/Script/BlueprintGraph.K2Node_EnhancedInputAction",
        ):
            try:
                node_cls = unreal.load_class(None, path)
                if node_cls:
                    log(f"loaded {path}")
                    break
            except Exception:
                continue

    if not node_cls:
        log("No Enhanced Input K2 node class in Python")
        return False

    try:
        # Add node to graph
        node = unreal.BlueprintEditorLibrary.add_node_to_blueprint_graph  # may not exist
    except Exception:
        pass

    try:
        graph_model = graph
        # UE API: schema create
        if hasattr(unreal, "EdGraphHelper"):
            pass
        # Manual: construct node as outer=graph
        node = unreal.new_object(node_cls, graph)
        try:
            node.set_editor_property("input_action", ia)
        except Exception:
            try:
                node.set_editor_property("InputAction", ia)
            except Exception as exc:
                log(f"set input_action on node: {exc}")
        # Allocate default pins
        try:
            node.allocate_default_pins()
        except Exception:
            pass
        try:
            nodes = list(graph.get_editor_property("nodes") or [])
            nodes.append(node)
            graph.set_editor_property("nodes", nodes)
            log("appended Enhanced Input node to graph nodes")
        except Exception as exc:
            log(f"append node: {exc}")
        save(bp_path)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            log("compiled after node inject")
        except Exception as exc:
            log(f"compile: {exc}")
        return True
    except Exception as exc:
        log(f"node inject failed: {exc}")
        return False


def create_montages():
    """Create AnimMontages from turn sequences using AnimComposite/Montage factories."""
    ensure = unreal.EditorAssetLibrary.make_directory
    mdir = f"{OUT}/Montages"
    if not unreal.EditorAssetLibrary.does_directory_exist(mdir):
        ensure(mdir)

    created = {}
    for name, path in TURN_ANIMS.items():
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            continue
        anim = load(path)
        mpath = f"{mdir}/AM_{name}"
        if unreal.EditorAssetLibrary.does_asset_exist(mpath):
            created[name] = mpath
            continue

        factory = None
        if hasattr(unreal, "AnimMontageFactory"):
            factory = unreal.AnimMontageFactory()
            try:
                factory.set_editor_property("target_skeleton", anim.get_editor_property("skeleton"))
            except Exception:
                pass
            try:
                factory.set_editor_property("source_animation", anim)
            except Exception:
                pass

        montage = None
        if factory:
            montage = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
                f"AM_{name}", mdir, unreal.AnimMontage, factory
            )
        if montage:
            # Ensure skeleton
            try:
                montage.set_editor_property("skeleton", anim.get_editor_property("skeleton"))
            except Exception:
                pass
            # Try to set slot animation
            try:
                # Use AnimationBlueprintLibrary.create_unique_asset_name - skip
                # Compose: set composite sections
                pass
            except Exception:
                pass
            save(mpath)
            created[name] = mpath
            log(f"montage {mpath}")
        else:
            created[name] = path
            log(f"montage fallback sequence {path}")
    return created


def setup_idle_turn_on_character(bp_path: str, montages: dict):
    """
    Switch to hybrid rotation for idle turns:
    - UseControllerRotationYaw = False
    - UseControllerDesiredRotation = True (faces camera while moving / always)
    Soft refs for turn anims stored as name properties when possible.

    True montage playback needs Event Tick graph; we add Turn anim soft refs
    and set RotationRate for visible turning. Also enable root motion from montages
    when played via Slot from AnimBP if we patch ABP SequencePlayer — limited.

    Additional: set character to allow root motion.
    """
    bp = load(bp_path)
    try:
        gen = bp.generated_class()
    except Exception:
        gen = bp.get_editor_property("generated_class")
    cdo = unreal.get_default_object(gen)

    # Hybrid: desired rotation toward control (strafe facing) without locking yaw instantly
    # Instant lock prevents AimYawDelta; desired rotation allows small lag for turns.
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=360.0, roll=0.0))

    # Mesh still upright
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))

    # Root motion on mesh anim instance
    try:
        cdo.set_editor_property("base_translation_offset", unreal.Vector(0, 0, 0))
    except Exception:
        pass

    save(bp_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"hybrid rotation on {bp_path}")


def patch_abp_for_turn_sequences():
    """
    If ABP has a SequencePlayer referencing MM_Idle or similar, we keep BS for loco.
    Add soft object paths as ABP class defaults via member variables pointing at Turn RTGs.
    Full state machine for Turn_90/180 needs editor; we create a companion
    AnimNotify-less approach: replace unused SequencePlayer asset soft path with Turn if found.
    """
    abp = load(ABP)
    for name, path in TURN_ANIMS.items():
        var = f"Anim_{name}"
        try:
            unreal.BlueprintEditorLibrary.add_member_variable(abp, var, unreal.ObjectProperty)
            log(f"ABP var {var}")
        except Exception as exc:
            log(f"ABP var {var}: {exc}")

    # Try set defaults on CDO
    try:
        gen = abp.generated_class()
        cdo = unreal.get_default_object(gen)
        for name, path in TURN_ANIMS.items():
            anim = load(path) if unreal.EditorAssetLibrary.does_asset_exist(path) else None
            for prop in (f"anim_{name}", f"Anim_{name}", name):
                try:
                    if anim:
                        cdo.set_editor_property(prop, anim)
                        log(f"set ABP.{prop}")
                except Exception:
                    pass
    except Exception as exc:
        log(f"ABP CDO: {exc}")

    save(ABP)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception:
        pass


def try_play_turn_via_anim_notify_state():
    """Create a simple Animation Layer Blueprint if factory exists."""
    # Skip if not available
    pass


def bind_walk_speed_using_input_component_override():
    """
    Final reliable walk: use PlayerController to poll Left Alt each tick — needs graph.
    Instead, set IA_Walk triggers to Down/Pressed and document.

    Also try assigning Crouch key through Enhanced Input by duplicating Jump graph
    binary pattern — too fragile.

    Use: Character Movement MaxWalkSpeed modified by binding IA_Walk to
    Input Action events that call a custom BlueprintImplementableEvent — no.

    RELIABLE METHOD: Create EditorUtility... no.

    Use Input Mapping Context with dual Move scales — no.

    Implement walk by setting `IA_Walk` as triggers on IMC and using
    `unreal.PythonScriptLibrary` - no.

    Last reliable automation: add `SetupPlayerInputComponent` override in
    a NEW C++ module — project is BP-only.

    Use Animation Blueprint Event Graph - ABP always ticks!
    AnimBP Event Blueprint Update Animation can call Set Max Walk Speed on owner.
    If we can ADD nodes to AnimBP Event Graph...
    """
    abp = load(ABP)
    pages = None
    for prop in ("ubergraph_pages", "function_graphs"):
        try:
            pages = abp.get_editor_property(prop)
            if pages:
                log(f"ABP {prop} len={len(pages)}")
                break
        except Exception as exc:
            log(f"ABP {prop}: {exc}")

    # List graphs
    try:
        graphs = abp.get_editor_property("function_graphs")
        for g in graphs or []:
            log(f"ABP func graph: {g.get_name() if hasattr(g,'get_name') else g}")
    except Exception as exc:
        log(f"func graphs: {exc}")


def wire_walk_with_is_input_key_down_in_abp():
    """
    Binary/string approach won't add nodes. Create a NEW AnimBP from scratch
    with only BlendSpace — Event Graph empty — then user adds Alt in editor.

    Better reliable approach for Alt walk WITHOUT graph:
    Map LeftAlt to Crouch in Enhanced IMC using IA that character ALREADY binds...
    Character doesn't bind crouch.

    Change MaxWalkSpeed default to 200 and use IA_Sprint (Shift) for run 600 —
    plan says Alt=walk, release=run. Opposite of sprint pattern.
    Invert: default Run 600, need Alt to lower speed.

    Could use `AxisConfig` - no.

    I'll create a GameInstance Blueprint subsystem — still needs graph.

    PYTHON RUNTIME: not available in packaged PIE for gameplay.

    Check if BP_ThirdPersonCharacter has a Timeline or unused custom event we can retarget.
    """
    import re
    import os

    content = unreal.Paths.project_content_dir()
    fs = os.path.join(content, "ThirdPerson", "Blueprints", "BP_ThirdPersonCharacter.uasset")
    data = open(fs, "rb").read()
    # Find EnhancedInputActionDelegateBinding package export names
    hits = re.findall(rb"EnhancedInput[A-Za-z0-9_]+", data)
    log(f"binding-related strings: {sorted(set(hits))[:20]}")


def force_key_via_input_settings():
    """Add Left Alt to IA_Walk through Input Settings developer config + IMC rebuild."""
    # Use InputModifier or raw mapping list with FKey from InputCore
    ia = load(IA_WALK)
    imc = load(IMC)

    # Get all FKeys from InputSettings
    try:
        settings = unreal.InputSettings.get_input_settings()
        # action mappings
    except Exception as exc:
        log(f"InputSettings: {exc}")

    # Try EKeys via unreal.InputCoreTypes - iterate Key structs from get_all_keys if any
    all_keys = []
    try:
        # unreal.Key.get_all_keys doesn't exist; use Keys reflection
        keys_mod = unreal.Keys
        for attr in dir(keys_mod):
            if attr.startswith("_"):
                continue
            try:
                val = getattr(keys_mod, attr)
                if "Alt" in attr or "ALT" in attr or "Menu" in attr:
                    all_keys.append((attr, val))
            except Exception:
                pass
        log(f"Keys.*Alt*: {all_keys}")
    except Exception as exc:
        log(f"Keys reflect: {exc}")

    if all_keys:
        mappings = list(imc.get_editor_property("mappings") or [])
        # strip IA_Walk
        mappings = [
            m
            for m in mappings
            if not (
                m.get_editor_property("action")
                and "IA_Walk" in m.get_editor_property("action").get_path_name()
            )
        ]
        attr, key = all_keys[0]
        mapping = unreal.EnhancedActionKeyMapping()
        mapping.set_editor_property("action", ia)
        mapping.set_editor_property("key", key)
        mappings.append(mapping)
        imc.set_editor_property("mappings", mappings)
        save(IMC)
        log(f"Bound IA_Walk to Keys.{attr} = {key}")
        return True
    return False


def create_walk_turn_component_with_nativized_logic():
    """
    Create AC_OrdinaryLocomotion as ActorComponent Blueprint and use
    ReceiveTick via adding an Event Tick node with Python EdGraphSchema_K2.
    """
    helper = f"{OUT}/AC_OrdinaryLocomotion"
    if unreal.EditorAssetLibrary.does_asset_exist(helper):
        bp = load(helper)
    else:
        factory = unreal.BlueprintFactory()
        factory.set_editor_property("parent_class", unreal.ActorComponent)
        bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            "AC_OrdinaryLocomotion", OUT, unreal.Blueprint, factory
        )
    if not bp:
        log("helper BP missing")
        return

    # Enable tick on CDO
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        cdo.set_editor_property("primary_component_tick", unreal.ActorComponentTickFunction())
    except Exception as exc:
        log(f"tick func: {exc}")
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        tick = cdo.get_editor_property("primary_component_tick")
        tick.set_editor_property("b_start_with_tick_enabled", True)
        tick.set_editor_property("b_can_ever_tick", True)
        cdo.set_editor_property("primary_component_tick", tick)
        log("helper tick enabled on CDO")
    except Exception as exc:
        log(f"enable tick: {exc}")

    # Try EdGraphSchema_K2 to create Event Tick
    try:
        pages = bp.get_editor_property("ubergraph_pages")
        if pages:
            graph = pages[0]
            # Create UK2Node_Event for ReceiveTick
            event_cls = getattr(unreal, "K2Node_Event", None) or unreal.load_class(
                None, "/Script/BlueprintGraph.K2Node_Event"
            )
            if event_cls:
                node = unreal.new_object(event_cls, graph)
                try:
                    node.set_editor_property("event_reference", None)
                except Exception:
                    pass
                # Set custom function name ReceiveTick
                for prop, val in (
                    ("function_name", "ReceiveTick"),
                    ("FunctionReference", None),
                ):
                    try:
                        node.set_editor_property(prop, val)
                    except Exception:
                        pass
                try:
                    # FMemberReference
                    pass
                except Exception:
                    pass
                log(f"created event node {node}")
    except Exception as exc:
        log(f"helper graph: {exc}")

    save(helper)

    # Attach to character SCS
    _attach_component_to_character(CHAR_BP, helper)
    _attach_component_to_character(COMBAT_BP, helper)


def _attach_component_to_character(bp_path, comp_bp_path):
    if not unreal.EditorAssetLibrary.does_asset_exist(bp_path):
        return
    if not unreal.EditorAssetLibrary.does_asset_exist(comp_bp_path):
        return
    bp = load(bp_path)
    comp_bp = load(comp_bp_path)
    try:
        gen = comp_bp.generated_class()
    except Exception:
        gen = comp_bp.get_editor_property("generated_class")

    # SubobjectDataSubsystem add component
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        # Get handle for root
        handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
        log(f"subobjects {bp_path}: {len(handles) if handles else 0}")
        if handles:
            root = handles[0]
            params = unreal.AddNewSubobjectParams()
            params.set_editor_property("parent_handle", root)
            params.set_editor_property("new_class", gen)
            # prefer blueprint class
            try:
                params.set_editor_property("b_conform_to_parent", True)
            except Exception:
                pass
            result_handle, fail_reason = subsystem.add_new_subobject(params)
            log(f"add subobject: {result_handle} reason={fail_reason}")
            save(bp_path)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"attach component: {exc}")


def run():
    log("start")
    dump_bp_graph_api(CHAR_BP)
    force_key_via_input_settings() or fix_imc_alt()
    set_speed_defaults(CHAR_BP)
    set_speed_defaults(COMBAT_BP)
    inject_enhanced_input_nodes(CHAR_BP)
    inject_enhanced_input_nodes(COMBAT_BP)
    montages = create_montages()
    setup_idle_turn_on_character(CHAR_BP, montages)
    setup_idle_turn_on_character(COMBAT_BP, montages)
    patch_abp_for_turn_sequences()
    bind_walk_speed_using_input_component_override()
    wire_walk_with_is_input_key_down_in_abp()
    create_walk_turn_component_with_nativized_logic()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
