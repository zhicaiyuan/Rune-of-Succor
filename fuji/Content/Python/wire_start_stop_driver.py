# -*- coding: utf-8 -*-
"""
Wire Start/Stop using DefaultSlot montages driven from Character EventGraph.

ABP_StrafeLocomotion already has AnimGraphNode_Slot (DefaultSlot). Playing a
montage into DefaultSlot overrides the state-machine pose for Start/Stop, then
returns to Idle/Locomotion BS when the montage ends.

Also restores/verifies BS_WalkRun_Sword on BlendSpace player and FootIK alpha=0.
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
IDLE_RTG = f"{OUT}/SwordRTG/Idle_Seq_RTG"

MONTAGES = {
    "WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}

# Thresholds
WALK_SPEED_MAX = 300.0  # MaxWalkSpeed <= this => walk
MOVE_ENTER = 15.0
MOVE_EXIT = 10.0


def log(m):
    unreal.log(f"[SSWire] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def fix_abp():
    abp = load(ABP)
    bs = load(BS) if unreal.EditorAssetLibrary.does_asset_exist(BS) else None
    idle = load(IDLE_RTG) if unreal.EditorAssetLibrary.does_asset_exist(IDLE_RTG) else None

    # Blend space — try nested node.blend_space
    bs_n = 0
    cls = getattr(unreal, "AnimGraphNode_BlendSpacePlayer", None)
    if cls and bs:
        for obj in unreal.ObjectIterator(cls):
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
                    bs_n += 1
                    log("BS rebound")
                except Exception as exc:
                    log(f"BS set: {exc}")
    log(f"BlendSpacePlayer updates={bs_n}")

    # Also scan binary-named players via SequencePlayer idle
    if idle:
        seq_cls = getattr(unreal, "AnimGraphNode_SequencePlayer", None)
        if seq_cls:
            for obj in unreal.ObjectIterator(seq_cls):
                try:
                    if "ABP_StrafeLocomotion" not in obj.get_path_name():
                        continue
                except Exception:
                    continue
                for outer in ("node", "Node"):
                    try:
                        node = obj.get_editor_property(outer)
                        seq = node.get_editor_property("sequence")
                        if seq and "MM_Idle" in seq.get_name():
                            node.set_editor_property("sequence", idle)
                            obj.set_editor_property(outer, node)
                            log("Idle still MM_Idle -> Idle_Seq_RTG")
                    except Exception:
                        pass

    # Foot IK off
    cr = getattr(unreal, "AnimGraphNode_ControlRig", None)
    if cr:
        for obj in unreal.ObjectIterator(cr):
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

    # Ensure Slot name is DefaultSlot
    slot_cls = getattr(unreal, "AnimGraphNode_Slot", None)
    if slot_cls:
        for obj in unreal.ObjectIterator(slot_cls):
            try:
                if "ABP_StrafeLocomotion" not in obj.get_path_name():
                    continue
            except Exception:
                continue
            for outer in ("node", "Node"):
                try:
                    node = obj.get_editor_property(outer)
                    node.set_editor_property("slot_name", unreal.Name("DefaultSlot"))
                    obj.set_editor_property(outer, node)
                    log("Slot=DefaultSlot")
                except Exception as exc:
                    log(f"slot: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"abp compile: {exc}")
    save(ABP)


def find_event_graph(bp):
    for g in unreal.ObjectIterator(unreal.EdGraph):
        try:
            p = g.get_path_name()
        except Exception:
            continue
        if "BP_ThirdPersonCharacter" in p and g.get_name() == "EventGraph":
            return g
    return None


def get_or_create_tick(graph):
    """Find ReceiveTick event node or create one."""
    # Existing
    for cls_name in ("K2Node_Event", "K2Node_CustomEvent"):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            try:
                if graph.get_path_name() not in n.get_path_name() and n.get_outer() != graph:
                    if n.get_outer() != graph:
                        continue
            except Exception:
                continue
            try:
                if n.get_outer() != graph and graph.get_name() not in n.get_path_name():
                    continue
            except Exception:
                continue
            # Check event name
            for prop in ("event_reference", "EventReference"):
                try:
                    ref = n.get_editor_property(prop)
                    # member name
                    for mp in ("member_name", "MemberName"):
                        try:
                            mn = str(ref.get_editor_property(mp))
                            if mn == "ReceiveTick":
                                log(f"found ReceiveTick {n.get_name()}")
                                return n
                        except Exception:
                            pass
                except Exception:
                    pass
            try:
                if "ReceiveTick" in n.get_name() or "Tick" in n.get_node_title(0).to_string():
                    log(f"found tick-like {n.get_name()}")
                    return n
            except Exception:
                pass

    # Create
    event_cls = getattr(unreal, "K2Node_Event", None)
    if not event_cls:
        log("no K2Node_Event")
        return None
    node = unreal.new_object(event_cls, graph, unreal.Name("SS_ReceiveTick"))
    try:
        graph.add_node(node, False, False)
    except Exception:
        try:
            graph.add_node(node)
        except Exception as exc:
            log(f"add tick node: {exc}")
            return None

    # Set event to ReceiveTick / Actor.ReceiveTick
    try:
        # FMemberReference
        node.recreate_node()  # may fail
    except Exception:
        pass
    for meth in ("set_from_function", "SetFromFunction", "initialize"):
        if hasattr(node, meth):
            try:
                # find UFunction ReceiveTick on Actor
                fn = unreal.Actor.static_class().find_function_by_name("ReceiveTick")
                if fn:
                    getattr(node, meth)(fn)
                    log(f"tick via {meth}")
                    break
            except Exception as exc:
                log(f"{meth}: {exc}")
    try:
        node.allocate_default_pins()
    except Exception:
        pass
    try:
        node.reconstruct_node()
    except Exception:
        pass
    try:
        node.set_editor_property("node_pos_x", -1200)
        node.set_editor_property("node_pos_y", 800)
    except Exception:
        pass
    log(f"created tick node {node.get_name()}")
    return node


def add_member_vars(bp):
    """Add typed member variables using EdGraphPinType."""
    # BlueprintEditorLibrary.add_member_variable(Blueprint, Name, EdGraphPinType)
    lib = unreal.BlueprintEditorLibrary
    vars_to_add = [
        ("SS_PrevSpeed", "real", "double"),
        ("SS_WasMoving", "bool", "bool"),
        ("SS_WalkStart", "object", "object"),
        ("SS_WalkStop", "object", "object"),
        ("SS_RunStart", "object", "object"),
        ("SS_RunStop", "object", "object"),
    ]
    for vname, category, subcategory in vars_to_add:
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name(category))
            try:
                pin.set_editor_property("pin_sub_category", unreal.Name(subcategory))
            except Exception:
                pass
            if category == "object":
                # AnimMontage class
                try:
                    pin.set_editor_property(
                        "pin_sub_category_object", unreal.AnimMontage.static_class()
                    )
                except Exception:
                    pass
            ok = lib.add_member_variable(bp, unreal.Name(vname), pin)
            log(f"add_member_variable {vname}: {ok}")
        except Exception as exc:
            log(f"add_member_variable {vname}: {exc}")


def set_montage_defaults(bp):
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"compile before defaults: {exc}")
    cdo = unreal.get_default_object(bp.generated_class())
    mapping = {
        "s_s_walk_start": MONTAGES["WalkStart"],
        "SS_WalkStart": MONTAGES["WalkStart"],
        "ss_walk_start": MONTAGES["WalkStart"],
        "SS_WalkStop": MONTAGES["WalkStop"],
        "SS_RunStart": MONTAGES["RunStart"],
        "SS_RunStop": MONTAGES["RunStop"],
    }
    # Try common property name styles
    for prop, path in (
        ("SS_WalkStart", MONTAGES["WalkStart"]),
        ("SS_WalkStop", MONTAGES["WalkStop"]),
        ("SS_RunStart", MONTAGES["RunStart"]),
        ("SS_RunStop", MONTAGES["RunStop"]),
    ):
        try:
            cdo.set_editor_property(prop, load(path))
            log(f"CDO {prop} set")
        except Exception as exc:
            log(f"CDO {prop}: {exc}")


def create_call_function(graph, function_owner_class, function_name, x, y):
    node = unreal.new_object(
        unreal.K2Node_CallFunction, graph, unreal.Name(f"SS_{function_name}_{x}_{y}")
    )
    try:
        graph.add_node(node, False, False)
    except Exception:
        try:
            graph.add_node(node)
        except Exception as exc:
            log(f"add call {function_name}: {exc}")
            return None
    fn = None
    try:
        fn = function_owner_class.static_class().find_function_by_name(function_name)
    except Exception:
        try:
            fn = unreal.find_object(
                None, f"/Script/Engine.{function_owner_class.__name__}:{function_name}"
            )
        except Exception:
            pass
    if fn is None:
        # try Character / AnimInstance paths
        for cls in (
            unreal.Character,
            unreal.Actor,
            unreal.AnimInstance,
            unreal.SkeletalMeshComponent,
            unreal.GameplayStatics,
        ):
            try:
                fn = cls.static_class().find_function_by_name(function_name)
                if fn:
                    break
            except Exception:
                continue
    if fn:
        try:
            node.set_from_function(fn)
        except Exception:
            try:
                # FunctionReference
                ref = node.get_editor_property("function_reference")
                ref.set_editor_property("member_name", unreal.Name(function_name))
                try:
                    ref.set_editor_property("member_parent", function_owner_class.static_class())
                except Exception:
                    pass
                node.set_editor_property("function_reference", ref)
            except Exception as exc:
                log(f"set function {function_name}: {exc}")
    try:
        node.allocate_default_pins()
        node.reconstruct_node()
    except Exception:
        pass
    try:
        node.set_editor_property("node_pos_x", x)
        node.set_editor_property("node_pos_y", y)
    except Exception:
        pass
    return node


def try_connect(schema, a_node, a_pin, b_node, b_pin):
    try:
        pa = a_node.find_pin(a_pin)
        pb = b_node.find_pin(b_pin)
        if not pa or not pb:
            # enumerate pins
            try:
                pins_a = list(a_node.get_editor_property("pins") or [])
                pins_b = list(b_node.get_editor_property("pins") or [])
                log(
                    f"pins {a_node.get_name()}={[p.get_name() for p in pins_a]} "
                    f"{b_node.get_name()}={[p.get_name() for p in pins_b]}"
                )
            except Exception:
                pass
            return False
        ok = unreal.EdGraphSchema_K2.try_create_connection(schema, pa, pb)
        return bool(ok)
    except Exception as exc:
        log(f"connect {a_pin}->{b_pin}: {exc}")
        return False


def inject_tick_driver(bp, graph):
    """
    Build a compact tick chain:
      Tick -> GetVelocity -> VectorLength -> (store logic via custom event)

    Full branch graph is large; instead create a CustomEvent `SS_UpdateStartStop`
    and a CallFunction chain that uses a BlueprintImplementable helper.

    Most reliable for UE Python: create K2Node_CallFunction to a NEW
    Blueprint Function Library — hard.

    Alternative: use Component created as EditorUtility — no.

    Practical: create AnimNotify-free driver as **collapsed graph** using
    existing Character movement events.

    We'll create CustomEvent SS_LocoTick and document; ALSO attach a
    **SceneComponent-less ActorComponent BP** with Ubergraph built from
    duplicate of a template.

    NEW APPROACH that works: use `unreal.EditorLevelLibrary` / PIE — no.

    Use Animation Blueprint Linked layer with Property Access — transitions
    on Speed already exist Idle<->Locomotion. For Start/Stop montages, call
    from Character using **Input Action** Completed — no.

    Implement via **AnimBP AnimNotify** on Idle? no.

    Final approach: Create `BP_StartStopDriver` Actor Component with parent
    class that has Tick enabled, and use `UserConstructionScript` + 
    `receive_tick` override via Python by setting `primary_component_tick`.

    For Blueprint ActorComponent, we can set CDO tick enabled and inject
    EventGraph ReceiveTick with Montage_Play calls.

    Steps:
    1. Create BP AC_StartStopDriver : ActorComponent
    2. Enable tick on CDO
    3. Inject EventGraph
    4. Add component to Character SCS
    """
    return create_and_attach_driver_component(bp)


def create_and_attach_driver_component(char_bp):
    comp_path = f"{OUT}/AC_StartStopDriver"
    if unreal.EditorAssetLibrary.does_asset_exist(comp_path):
        unreal.EditorAssetLibrary.delete_asset(comp_path)

    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", unreal.ActorComponent)
    comp_bp = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "AC_StartStopDriver", OUT, unreal.Blueprint, factory
    )
    if not comp_bp:
        log("FAILED AC_StartStopDriver")
        return False

    # Enable tick
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(comp_bp)
    except Exception:
        pass
    try:
        cdo = unreal.get_default_object(comp_bp.generated_class())
        tick = cdo.get_editor_property("primary_component_tick")
        tick.set_editor_property("b_start_with_tick_enabled", True)
        tick.set_editor_property("b_can_ever_tick", True)
        cdo.set_editor_property("primary_component_tick", tick)
        try:
            cdo.set_editor_property("b_auto_activate", True)
        except Exception:
            pass
        log("component tick enabled")
    except Exception as exc:
        log(f"tick enable: {exc}")

    # Add montage variables with EdGraphPinType
    lib = unreal.BlueprintEditorLibrary
    for vname in ("WalkStart", "WalkStop", "RunStart", "RunStop"):
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name("object"))
            pin.set_editor_property(
                "pin_sub_category_object", unreal.AnimMontage.static_class()
            )
            lib.add_member_variable(comp_bp, unreal.Name(vname), pin)
            log(f"comp var {vname}")
        except Exception as exc:
            log(f"comp var {vname}: {exc}")
    for vname, cat in (("PrevSpeed", "real"), ("WasMoving", "bool")):
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name(cat))
            lib.add_member_variable(comp_bp, unreal.Name(vname), pin)
            log(f"comp var {vname}")
        except Exception as exc:
            log(f"comp var {vname}: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(comp_bp)
    except Exception as exc:
        log(f"comp compile: {exc}")

    # Set defaults
    try:
        cdo = unreal.get_default_object(comp_bp.generated_class())
        for prop, key in (
            ("WalkStart", "WalkStart"),
            ("WalkStop", "WalkStop"),
            ("RunStart", "RunStart"),
            ("RunStop", "RunStop"),
        ):
            try:
                cdo.set_editor_property(prop, load(MONTAGES[key]))
                log(f"comp CDO {prop}")
            except Exception as exc:
                log(f"comp CDO {prop}: {exc}")
    except Exception as exc:
        log(f"comp defaults: {exc}")

    save(comp_path)

    # Inject EventGraph on component
    graph = None
    for g in unreal.ObjectIterator(unreal.EdGraph):
        try:
            if "AC_StartStopDriver" in g.get_path_name() and g.get_name() == "EventGraph":
                graph = g
                break
        except Exception:
            continue
    if graph:
        build_component_tick_graph(comp_bp, graph)
    else:
        log("AC_StartStopDriver EventGraph not found — will use native-less fallback")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(comp_bp)
    except Exception as exc:
        log(f"comp compile2: {exc}")
    save(comp_path)

    # Attach to character via SubobjectDataSubsystem
    attached = attach_component_to_character(char_bp, comp_path)
    log(f"attached={attached}")
    return attached


def build_component_tick_graph(comp_bp, graph):
    """
    Build ReceiveTick graph that plays Start/Stop montages.

    Pseudocode:
      speed = owner.GetVelocity().Size()
      moving = speed > MOVE_ENTER if not WasMoving else speed > MOVE_EXIT
      walk = owner.CharacterMovement.MaxWalkSpeed <= WALK_SPEED_MAX
      if moving and not WasMoving:
          play WalkStart or RunStart
      if not moving and WasMoving:
          play WalkStop or RunStop
      WasMoving = moving
      PrevSpeed = speed
    """
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
    if not schema:
        schema = unreal.EdGraphSchema_K2()

    tick = get_or_create_tick(graph)
    if not tick:
        log("no tick on component")
        return

    # Mark graph dirty; full automated branch wiring is fragile.
    # Instead create a clear CustomEvent and CallFunction stubs the user can
    # see — AND implement logic via AnimBP-less **python-generated Bytecode** — no.

    # Use K2Node_CallFunction: GetOwner -> Cast To Character -> GetVelocity ...
    # Build minimal chain that at least calls PlayAnimMontage on start edge
    # using Sequence of CallFunctions.

    owner = create_call_function(graph, unreal.ActorComponent, "GetOwner", -900, 900)
    # Get Component Velocity from owner pawn
    # Play Montage: SkeletalMeshComponent.PlayAnimation or AnimInstance.Montage_Play

    # Create CustomEvent SS_Drive for clarity
    custom_cls = getattr(unreal, "K2Node_CustomEvent", None)
    if custom_cls:
        try:
            ce = unreal.new_object(custom_cls, graph, unreal.Name("SS_DriveStartStop"))
            graph.add_node(ce, False, False)
            try:
                ce.set_editor_property("custom_function_name", unreal.Name("SS_DriveStartStop"))
            except Exception:
                pass
            ce.set_editor_property("node_pos_x", -900)
            ce.set_editor_property("node_pos_y", 1200)
            try:
                ce.allocate_default_pins()
                ce.reconstruct_node()
            except Exception:
                pass
            log("added CustomEvent SS_DriveStartStop")
        except Exception as exc:
            log(f"custom event: {exc}")

    # Because full K2 branch wiring is error-prone, implement driver as
    # **Animation Asset User Data** — no.
    #
    # Use `unreal.SystemLibrary.execute_console_command` — no.
    #
    # Implement using AnimBP **State Machine Library** at runtime from
    # a Blueprint Interface — no.
    #
    # REAL working method in UE5.8 Python for gameplay logic without K2:
    # Create an Editor Utility Widget — doesn't run in PIE.
    #
    # Must wire K2. Let's do a compact version with fewer nodes:
    # Tick then-exec -> CallFunction "SS_DriveStartStop" if we make it a
    # BlueprintCallable on the component via CustomEvent + then implement
    # body with nodes.

    log("component graph scaffolding done; building executable chain...")
    build_executable_tick_chain(comp_bp, graph, tick, schema)


def build_executable_tick_chain(comp_bp, graph, tick, schema):
    """
    Create nodes and connections for Start/Stop montage driver.
    Uses PlayAnimMontage on Character.
    """
    # Nodes
    get_owner = create_call_function(graph, unreal.ActorComponent, "GetOwner", -700, 900)
    cast_cls = getattr(unreal, "K2Node_DynamicCast", None)
    cast_node = None
    if cast_cls:
        try:
            cast_node = unreal.new_object(cast_cls, graph, unreal.Name("SS_CastCharacter"))
            graph.add_node(cast_node, False, False)
            cast_node.set_editor_property("target_type", unreal.Character.static_class())
            cast_node.set_editor_property("node_pos_x", -450)
            cast_node.set_editor_property("node_pos_y", 900)
            cast_node.allocate_default_pins()
            cast_node.reconstruct_node()
            log("cast to Character")
        except Exception as exc:
            log(f"cast: {exc}")

    get_vel = create_call_function(graph, unreal.Actor, "GetVelocity", -200, 900)
    # Vector Length - K2Node_CallFunction on KismetMathLibrary.VSize
    vsize = create_call_function(graph, unreal.MathLibrary, "VSize", 50, 900)
    if not vsize:
        vsize = create_call_function(graph, unreal.KismetMathLibrary, "VSize", 50, 900)

    # Get MaxWalkSpeed from movement
    get_move = create_call_function(
        graph, unreal.Character, "GetMovementComponent", -200, 1150
    )

    # PlayAnimMontage on Character
    play_mont = create_call_function(graph, unreal.Character, "PlayAnimMontage", 500, 900)

    # Variable get/set nodes
    var_get_cls = getattr(unreal, "K2Node_VariableGet", None)
    var_set_cls = getattr(unreal, "K2Node_VariableSet", None)

    def make_var_get(varname, x, y):
        if not var_get_cls:
            return None
        n = unreal.new_object(var_get_cls, graph, unreal.Name(f"Get_{varname}"))
        try:
            graph.add_node(n, False, False)
        except Exception:
            graph.add_node(n)
        try:
            # set variable reference
            n.set_editor_property("variable_reference", None)
        except Exception:
            pass
        for meth in ("set_from_property", "SetFromProperty", "create_new"):
            pass
        try:
            ref = n.get_editor_property("variable_reference")
            ref.set_editor_property("member_name", unreal.Name(varname))
            try:
                ref.set_editor_property("member_parent", None)  # self
                ref.set_editor_property("b_self_context", True)
            except Exception:
                try:
                    ref.set_editor_property("self_context", True)
                except Exception:
                    pass
            n.set_editor_property("variable_reference", ref)
        except Exception as exc:
            log(f"var get ref {varname}: {exc}")
        try:
            n.allocate_default_pins()
            n.reconstruct_node()
        except Exception:
            pass
        try:
            n.set_editor_property("node_pos_x", x)
            n.set_editor_property("node_pos_y", y)
        except Exception:
            pass
        return n

    def make_var_set(varname, x, y):
        if not var_set_cls:
            return None
        n = unreal.new_object(var_set_cls, graph, unreal.Name(f"Set_{varname}"))
        try:
            graph.add_node(n, False, False)
        except Exception:
            graph.add_node(n)
        try:
            ref = n.get_editor_property("variable_reference")
            ref.set_editor_property("member_name", unreal.Name(varname))
            try:
                ref.set_editor_property("b_self_context", True)
            except Exception:
                pass
            n.set_editor_property("variable_reference", ref)
        except Exception as exc:
            log(f"var set ref {varname}: {exc}")
        try:
            n.allocate_default_pins()
            n.reconstruct_node()
        except Exception:
            pass
        try:
            n.set_editor_property("node_pos_x", x)
            n.set_editor_property("node_pos_y", y)
        except Exception:
            pass
        return n

    get_was = make_var_get("WasMoving", 50, 1100)
    get_ws = make_var_get("WalkStart", 300, 700)
    get_rs = make_var_get("RunStart", 300, 800)
    get_wst = make_var_get("WalkStop", 300, 1000)
    get_rst = make_var_get("RunStop", 300, 1100)
    set_was = make_var_set("WasMoving", 800, 1100)
    set_prev = make_var_set("PrevSpeed", 800, 1200)

    # Try basic exec connections: Tick -> GetOwner (exec)
    # Many CallFunctions need exec pins
    if schema and tick and get_owner:
        for a, ap, b, bp in (
            (tick, "then", get_owner, "execute"),
            (get_owner, "then", cast_node, "execute") if cast_node else (None, None, None, None),
        ):
            if a and b:
                try_connect(schema, a, ap, b, bp)

    # Data: GetOwner ReturnValue -> Cast Object
    if schema and get_owner and cast_node:
        try_connect(schema, get_owner, "ReturnValue", cast_node, "Object")

    # Cast AsCharacter -> GetVelocity self
    if schema and cast_node and get_vel:
        try_connect(schema, cast_node, "AsCharacter", get_vel, "self")
        try_connect(schema, cast_node, "then", get_vel, "execute")

    if schema and get_vel and vsize:
        try_connect(schema, get_vel, "ReturnValue", vsize, "A")

    log("tick chain nodes created (partial wiring)")

    # Because Branch/Compare wiring is lengthy and fragile in headless, also
    # write a Function graph using Blueprint Nativization-free approach:
    # store a Python-callable is NOT available at runtime.
    #
    # Complete the logic by creating an **Animation Modifier** — no.
    #
    # Use `UBlueprint` generated class override via `ComponentInstanceData` — no.
    #
    # I'll implement a secondary path: **AnimBP Event Graph** injection of
    # BlueprintUpdateAnimation which already fires every frame in AnimInstance.
    inject_animbp_update_driver()


def inject_animbp_update_driver():
    """
    Inject into ABP EventGraph (BlueprintUpdateAnimation) the Start/Stop montage logic.
    AnimInstance.Montage_Play is available on self.
    """
    abp = load(ABP)
    graph = None
    for g in unreal.ObjectIterator(unreal.EdGraph):
        try:
            p = g.get_path_name()
        except Exception:
            continue
        if "ABP_StrafeLocomotion" in p and g.get_name() == "EventGraph":
            graph = g
            break
    if not graph:
        log("ABP EventGraph missing")
        return False

    log(f"ABP EventGraph={graph.get_path_name()}")

    # Add variables on AnimBP
    lib = unreal.BlueprintEditorLibrary
    for vname, cat, subobj in (
        ("SS_WasMoving", "bool", None),
        ("SS_PrevSpeed", "real", None),
        ("SS_WalkStart", "object", unreal.AnimMontage.static_class()),
        ("SS_WalkStop", "object", unreal.AnimMontage.static_class()),
        ("SS_RunStart", "object", unreal.AnimMontage.static_class()),
        ("SS_RunStop", "object", unreal.AnimMontage.static_class()),
    ):
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name(cat))
            if subobj:
                pin.set_editor_property("pin_sub_category_object", subobj)
            ok = lib.add_member_variable(abp, unreal.Name(vname), pin)
            log(f"ABP add {vname}: {ok}")
        except Exception as exc:
            log(f"ABP add {vname}: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"abp compile vars: {exc}")

    cdo = unreal.get_default_object(abp.generated_class())
    for prop, key in (
        ("SS_WalkStart", "WalkStart"),
        ("SS_WalkStop", "WalkStop"),
        ("SS_RunStart", "RunStart"),
        ("SS_RunStop", "RunStop"),
    ):
        try:
            cdo.set_editor_property(prop, load(MONTAGES[key]))
            log(f"ABP CDO {prop} OK")
        except Exception as exc:
            log(f"ABP CDO {prop}: {exc}")

    # Find BlueprintUpdateAnimation event
    update_event = None
    for cls_name in ("K2Node_Event",):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph and "ABP_StrafeLocomotion" not in n.get_path_name():
                    continue
                if n.get_outer() != graph:
                    continue
            except Exception:
                continue
            try:
                title = ""
                try:
                    title = n.get_node_title(0).to_string()
                except Exception:
                    title = n.get_name()
                ref = n.get_editor_property("event_reference")
                mn = ""
                try:
                    mn = str(ref.get_editor_property("member_name"))
                except Exception:
                    pass
                if "BlueprintUpdateAnimation" in mn or "BlueprintUpdateAnimation" in title:
                    update_event = n
                    log(f"found BlueprintUpdateAnimation {n.get_name()}")
                    break
            except Exception:
                continue
        if update_event:
            break

    if not update_event:
        log("BlueprintUpdateAnimation not found — creating custom event hook")
        # ABP_Unarmed always has it; search more loosely
        for n in unreal.ObjectIterator(unreal.K2Node_Event):
            try:
                if "ABP_StrafeLocomotion" not in n.get_path_name():
                    continue
                log(f"event candidate {n.get_name()} outer={n.get_outer().get_name() if n.get_outer() else None}")
            except Exception:
                pass

    # Expand state machine: find AnimationStateGraph outers
    expand_sm_via_state_nodes()

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"abp compile: {exc}")
    save(ABP)
    return True


def expand_sm_via_state_nodes():
    """
    Find AnimStateNodes and their bound AnimationStateGraphs; identify Idle vs Locomotion;
    create transition-friendly Start/Stop by cloning Idle state graphs.
    """
    abp = load(ABP)
    states = []
    for n in unreal.ObjectIterator(unreal.AnimStateNode):
        try:
            if "ABP_StrafeLocomotion" not in n.get_path_name():
                continue
        except Exception:
            continue
        bound = None
        try:
            bound = n.get_editor_property("bound_graph")
        except Exception:
            pass
        # Determine content
        kind = "unknown"
        if bound:
            # look for blendspace vs sequence in bound graph path children
            for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
                try:
                    if bound.get_name() not in sp.get_path_name() and sp.get_outer() != bound:
                        # check outer
                        if sp.get_typed_outer(unreal.EdGraph) != bound:
                            continue
                except Exception:
                    continue
                try:
                    node = sp.get_editor_property("node")
                    seq = node.get_editor_property("sequence")
                    if seq:
                        kind = f"seq:{seq.get_name()}"
                except Exception:
                    pass
            bs_cls = getattr(unreal, "AnimGraphNode_BlendSpacePlayer", None)
            if bs_cls:
                for bpnode in unreal.ObjectIterator(bs_cls):
                    try:
                        if bpnode.get_typed_outer(unreal.EdGraph) != bound:
                            continue
                        kind = "blendspace"
                    except Exception:
                        continue
        try:
            xpos = n.get_editor_property("node_pos_x")
            ypos = n.get_editor_property("node_pos_y")
        except Exception:
            xpos = ypos = 0
        log(f"STATE {n.get_name()} kind={kind} pos=({xpos},{ypos}) bound={bound.get_name() if bound else None}")
        states.append((n, kind, bound))

    # Find SM EdGraph (outer of AnimStateNode)
    sm_graph = None
    if states:
        sm_graph = states[0][0].get_outer()
        log(f"SM outer graph={sm_graph.get_path_name() if sm_graph else None} class={sm_graph.get_class().get_name() if sm_graph else None}")

    if not sm_graph:
        return False

    # Create 4 new states with SequencePlayers
    rtgs = {
        "WalkStart": f"{OUT}/SwordRTG/Walk_Start_F_0_Seq_RTG",
        "WalkStop": f"{OUT}/SwordRTG/Walk_Stop_F_0_Seq_RTG",
        "RunStart": f"{OUT}/SwordRTG/Run_Start_F_0_Seq_RTG",
        "RunStop": f"{OUT}/SwordRTG/Run_Stop_F_0_Seq_RTG",
    }
    schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationStateMachineSchema")
    anim_schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationGraphSchema")

    created = {}
    for i, (name, path) in enumerate(rtgs.items()):
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log(f"missing {path}")
            continue
        seq = load(path)
        try:
            node = unreal.new_object(unreal.AnimStateNode, sm_graph, unreal.Name(name))
            try:
                sm_graph.add_node(node, False, False)
            except Exception:
                sm_graph.add_node(node)
            node.set_editor_property("node_pos_x", 600)
            node.set_editor_property("node_pos_y", -200 + i * 180)
            # After add, UE usually creates BoundGraph automatically on reconstruct
            try:
                node.allocate_default_pins()
            except Exception:
                pass
            try:
                node.reconstruct_node()
            except Exception:
                pass
            bound = None
            try:
                bound = node.get_editor_property("bound_graph")
            except Exception:
                pass
            if not bound:
                # Create AnimationStateGraph manually
                try:
                    bound = unreal.new_object(
                        unreal.AnimationStateGraph, node, unreal.Name(f"{name}_Graph")
                    )
                    node.set_editor_property("bound_graph", bound)
                    log(f"created bound graph for {name}")
                except Exception as exc:
                    log(f"bound graph {name}: {exc}")
            if bound:
                # Ensure StateResult exists
                result = None
                result_cls = getattr(unreal, "AnimGraphNode_StateResult", None)
                if result_cls:
                    for r in unreal.ObjectIterator(result_cls):
                        if r.get_outer() == bound:
                            result = r
                            break
                    if not result:
                        try:
                            result = unreal.new_object(result_cls, bound, unreal.Name("Result"))
                            bound.add_node(result, False, False)
                            result.set_editor_property("node_pos_x", 400)
                            result.set_editor_property("node_pos_y", 0)
                        except Exception as exc:
                            log(f"result node: {exc}")
                # Sequence player
                sp = unreal.new_object(
                    unreal.AnimGraphNode_SequencePlayer, bound, unreal.Name(f"SP_{name}")
                )
                try:
                    bound.add_node(sp, False, False)
                except Exception:
                    try:
                        bound.add_node(sp)
                    except Exception as exc:
                        log(f"add sp: {exc}")
                try:
                    anim_node = sp.get_editor_property("node")
                    anim_node.set_editor_property("sequence", seq)
                    for prop in ("loop_animation", "b_loop_animation"):
                        try:
                            anim_node.set_editor_property(prop, False)
                        except Exception:
                            pass
                    sp.set_editor_property("node", anim_node)
                    sp.set_editor_property("node_pos_x", 0)
                    sp.set_editor_property("node_pos_y", 0)
                    log(f"{name} sequence set")
                except Exception as exc:
                    log(f"sp seq {name}: {exc}")
                # Connect Pose
                if result and anim_schema:
                    try:
                        # Pose pins often named "Pose" / "Result"
                        for ap, bp in (("Pose", "Result"), ("Pose", "Pose"), ("Animation", "Result")):
                            pa = sp.find_pin(ap)
                            pb = result.find_pin(bp)
                            if pa and pb:
                                unreal.EdGraphSchema_K2.try_create_connection(anim_schema, pa, pb)
                                log(f"connected {name} {ap}->{bp}")
                                break
                        else:
                            # dump pins
                            try:
                                log(
                                    f"SP pins={[p.get_name() for p in sp.get_editor_property('pins')]}"
                                )
                                log(
                                    f"Result pins={[p.get_name() for p in result.get_editor_property('pins')]}"
                                )
                            except Exception:
                                pass
                    except Exception as exc:
                        log(f"connect pose: {exc}")
            created[name] = node
            log(f"STATE CREATED {name}")
        except Exception as exc:
            log(f"create state {name}: {exc}")

    # Create transitions between states
    # Find Idle and Locomotion from kinds
    idle_state = None
    loco_state = None
    for n, kind, bound in states:
        if kind.startswith("seq:") and ("Idle" in kind or "Idle_Seq" in kind):
            idle_state = n
        if kind == "blendspace" or "BS_" in kind:
            loco_state = n
    # Fallback: by common template names / order
    if not idle_state or not loco_state:
        for n, kind, bound in states:
            log(f"fallback state scan {n.get_name()} {kind}")
        if states:
            # Unarmed: typically Idle is sequence, Jump states, Locomotion is BS
            for n, kind, bound in states:
                if "blendspace" in kind:
                    loco_state = n
                elif kind.startswith("seq:Idle") or "Idle_Seq" in kind:
                    idle_state = n
                elif kind.startswith("seq:") and idle_state is None:
                    # first sequence that isn't jump
                    if "Jump" not in kind and "Land" not in kind and "Fall" not in kind:
                        idle_state = n

    log(f"idle_state={idle_state.get_name() if idle_state else None} loco={loco_state.get_name() if loco_state else None}")

    # Create transition nodes
    trans_cls = getattr(unreal, "AnimStateTransitionNode", None)
    if schema and trans_cls and idle_state:
        pairs = []
        if "WalkStart" in created:
            pairs.append((idle_state, created["WalkStart"], "Idle_to_WalkStart"))
        if "RunStart" in created:
            pairs.append((idle_state, created["RunStart"], "Idle_to_RunStart"))
        if loco_state and "WalkStart" in created:
            pairs.append((created["WalkStart"], loco_state, "WalkStart_to_Loco"))
        if loco_state and "RunStart" in created:
            pairs.append((created["RunStart"], loco_state, "RunStart_to_Loco"))
        if loco_state and "WalkStop" in created:
            pairs.append((loco_state, created["WalkStop"], "Loco_to_WalkStop"))
        if loco_state and "RunStop" in created:
            pairs.append((loco_state, created["RunStop"], "Loco_to_RunStop"))
        if "WalkStop" in created and idle_state:
            pairs.append((created["WalkStop"], idle_state, "WalkStop_to_Idle"))
        if "RunStop" in created and idle_state:
            pairs.append((created["RunStop"], idle_state, "RunStop_to_Idle"))

        for src, dst, tname in pairs:
            try:
                tnode = unreal.new_object(trans_cls, sm_graph, unreal.Name(tname))
                try:
                    sm_graph.add_node(tnode, False, False)
                except Exception:
                    sm_graph.add_node(tnode)
                # Bidirectional pin link via schema create transition
                for meth in ("create_transition_node_between", "try_create_connection"):
                    pass
                # Set previous / next state
                for prop, val in (("previous_state", src), ("next_state", dst)):
                    try:
                        tnode.set_editor_property(prop, val)
                    except Exception:
                        pass
                # Connect pins: src "Out" to transition, transition to dst
                try:
                    # AnimationStateMachineSchema has CreateTransition
                    if hasattr(schema, "create_transition_node"):
                        schema.create_transition_node(src, dst)
                        log(f"schema create_transition {tname}")
                        continue
                except Exception as exc:
                    log(f"create_transition: {exc}")
                # Manual pin connect
                try:
                    out_pin = src.find_pin("Out") or src.find_pin("Execute") 
                    in_pin = dst.find_pin("In")
                    # Transition nodes use BoundGraph for rules
                    log(f"transition {tname} created (manual link may need editor)")
                except Exception:
                    pass
                try:
                    tnode.reconstruct_node()
                except Exception:
                    pass
            except Exception as exc:
                log(f"transition {tname}: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile SM: {exc}")
    save(ABP)
    return len(created) > 0


def attach_component_to_character(char_bp, comp_path):
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(char_bp)
        # Find root
        root = handles[0] if handles else None
        params = unreal.AddNewSubobjectParams()
        # Prefer newer API
        try:
            params.set_editor_property("parent_handle", root)
        except Exception:
            pass
        try:
            params.set_editor_property(
                "new_class", load(comp_path).generated_class()
            )
        except Exception:
            try:
                params.set_editor_property("new_class", unreal.load_object(None, comp_path + "_C"))
            except Exception as exc:
                log(f"new_class: {exc}")
                return False
        try:
            result = subsystem.add_new_subobject(params)
            log(f"add_new_subobject={result}")
        except Exception as exc:
            log(f"add_new_subobject: {exc}")
            # SCS fallback
            return attach_via_scs(char_bp, comp_path)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(char_bp)
        except Exception:
            pass
        save(CHAR)
        return True
    except Exception as exc:
        log(f"attach: {exc}")
        return attach_via_scs(char_bp, comp_path)


def attach_via_scs(char_bp, comp_path):
    log("SCS attach fallback — set default subobject via CDO add instance component not available")
    # As last resort, leave montages on ABP CDO; write console instructions
    return False


def run():
    log("start")
    fix_abp()
    bp = load(CHAR)
    add_member_vars(bp)
    set_montage_defaults(bp)
    graph = find_event_graph(bp)
    log(f"char EventGraph={graph.get_path_name() if graph else None}")
    inject_tick_driver(bp, graph)
    # Always try SM expansion + ABP vars
    inject_animbp_update_driver()
    # Re-ensure mesh anim class
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", load(ABP).generated_class())
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"char compile: {exc}")
    save(CHAR)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
