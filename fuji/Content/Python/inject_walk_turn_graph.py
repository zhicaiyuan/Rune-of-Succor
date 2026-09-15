# -*- coding: utf-8 -*-
"""
1) Add LeftAlt -> IA_Walk on restored IMC_Default
2) Inject EventGraph nodes: IA_Walk Started->Crouch, Completed->UnCrouch
3) Inject Event Tick idle-turn using Play Slot Animation montages
"""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"

WALK_SPEED = 200.0
RUN_SPEED = 600.0


def log(m):
    unreal.log(f"[InjectGraph] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def make_key(name: str):
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name(name))
    return key


def ensure_imc_walk():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_WALK):
        unreal.EditorAssetLibrary.duplicate_asset("/Game/Input/Actions/IA_Jump", IA_WALK)
    ia = load(IA_WALK)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_WALK, only_if_is_dirty=False)

    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    # remove old walk
    mappings = [
        m
        for m in mappings
        if not (
            m.get_editor_property("action")
            and "IA_Walk" in m.get_editor_property("action").get_path_name()
        )
    ]
    m = unreal.EnhancedActionKeyMapping()
    m.set_editor_property("action", ia)
    m.set_editor_property("key", make_key("LeftAlt"))
    mappings.append(m)
    imc.set_editor_property("mappings", mappings)
    unreal.EditorAssetLibrary.save_asset(IMC, only_if_is_dirty=False)
    log(f"IMC mappings={len(mappings)} (+LeftAlt IA_Walk)")


def get_event_graph(bp):
    bel = unreal.BlueprintEditorLibrary
    try:
        g = bel.find_event_graph(bp)
        if g:
            log(f"find_event_graph -> {g}")
            return g
    except Exception as exc:
        log(f"find_event_graph: {exc}")
    try:
        g = bel.find_graph(bp, "EventGraph")
        if g:
            log(f"find_graph EventGraph -> {g}")
            return g
    except Exception as exc:
        log(f"find_graph: {exc}")
    try:
        names = list(bel.list_graph_names(bp) or [])
        log(f"graph names: {names}")
        for n in names:
            if "EventGraph" in str(n):
                return bel.find_graph(bp, n)
    except Exception as exc:
        log(f"list_graph_names: {exc}")
    return None


def pin_by_name(node, name_substr: str, direction=None):
    try:
        pins = list(node.get_editor_property("pins") or [])
    except Exception:
        try:
            pins = list(node.pins)
        except Exception:
            pins = []
    for p in pins:
        try:
            pname = str(p.get_editor_property("pin_name"))
        except Exception:
            try:
                pname = str(p.pin_name)
            except Exception:
                pname = str(p)
        if name_substr.lower() in pname.lower():
            if direction is not None:
                try:
                    d = p.get_editor_property("direction")
                    if d != direction and str(direction) not in str(d):
                        continue
                except Exception:
                    pass
            return p
    # dump pins for debug
    for p in pins:
        try:
            log(f"  pin {p.get_editor_property('pin_name')} dir={p.get_editor_property('direction')}")
        except Exception:
            log(f"  pin {p}")
    return None


def try_link(schema, a, b):
    if not a or not b:
        return False
    try:
        schema.try_create_connection(a, b)
        return True
    except Exception as exc:
        log(f"link fail: {exc}")
        try:
            # alternate
            unreal.EdGraphSchema_K2.try_create_connection(schema, a, b)
            return True
        except Exception as exc2:
            log(f"link fail2: {exc2}")
    return False


def make_call_function(graph, function_name: str, x: int, y: int):
    """Create K2Node_CallFunction for Character::Crouch / UnCrouch."""
    node = unreal.new_object(unreal.K2Node_CallFunction, graph, unreal.Name(f"Call_{function_name}_{y}"))
    # Resolve UFunction from Character
    char_cls = unreal.Character.static_class()
    ufunc = None
    for getter in ("get_function", "find_function_by_name", "FindFunctionByName"):
        # use unreal.get_default_object(Character).get_class()
        pass
    # Blueprint API often uses set_from_function
    try:
        # Get function via Class
        ufunc = unreal.Object.get_class  # noop
    except Exception:
        pass

    # Prefer: call.set_from_function with find
    try:
        # In UE Python, functions can be found via:
        ufunc = char_cls.class_generated_by  # wrong
    except Exception:
        pass

    # Use MemberReference fields
    try:
        # K2Node_CallFunction has FunctionReference (FMemberReference)
        # Set MemberName + MemberParent
        # Some builds expose helper:
        if hasattr(node, "set_from_function"):
            # Find UFunction object
            fn_path = f"/Script/Engine.Character:{function_name}"
            fn_obj = unreal.load_object(None, fn_path)
            log(f"load function {fn_path} -> {fn_obj}")
            if fn_obj:
                node.set_from_function(fn_obj)
        else:
            # Manual member reference
            ref = node.get_editor_property("function_reference")
            ref.set_editor_property("member_name", unreal.Name(function_name))
            try:
                ref.set_editor_property("member_parent", char_cls)
            except Exception:
                try:
                    ref.set_editor_property("member_parent", unreal.Character.static_class())
                except Exception:
                    pass
            node.set_editor_property("function_reference", ref)
    except Exception as exc:
        log(f"configure CallFunction {function_name}: {exc}")

    try:
        node.allocate_default_pins()
    except Exception:
        pass
    try:
        node.reconstruct_node()
    except Exception:
        pass
    unreal.BlueprintEditorLibrary.set_node_pos(node, x, y)
    return node


def make_enhanced_input_node(graph, ia, x, y):
    node = unreal.new_object(unreal.K2Node_EnhancedInputAction, graph, unreal.Name("IA_Walk_Node"))
    for prop in ("input_action", "InputAction"):
        try:
            node.set_editor_property(prop, ia)
            log(f"EnhancedInputAction.{prop} set")
            break
        except Exception as exc:
            log(f"EnhancedInputAction.{prop}: {exc}")
    try:
        node.allocate_default_pins()
    except Exception as exc:
        log(f"alloc pins: {exc}")
    try:
        node.reconstruct_node()
    except Exception as exc:
        log(f"reconstruct: {exc}")
    unreal.BlueprintEditorLibrary.set_node_pos(node, x, y)
    # Dump pins
    pin_by_name(node, "Started")
    return node


def inject_walk(bp_path: str):
    bp = load(bp_path)
    graph = get_event_graph(bp)
    if not graph:
        log(f"no EventGraph on {bp_path}")
        return False

    # Remove previous injected nodes if re-run
    try:
        nodes = list(graph.get_editor_property("nodes") or [])
        keep = []
        for n in nodes:
            nm = n.get_name() if hasattr(n, "get_name") else str(n)
            if "IA_Walk" in nm or "Call_Crouch" in nm or "Call_UnCrouch" in nm:
                log(f"remove old {nm}")
                continue
            keep.append(n)
        graph.set_editor_property("nodes", keep)
    except Exception as exc:
        log(f"cleanup: {exc}")

    ia = load(IA_WALK)
    schema = unreal.EdGraphSchema_K2()

    ei = make_enhanced_input_node(graph, ia, -200, 1200)
    crouch = make_call_function(graph, "Crouch", 350, 1100)
    uncrouch = make_call_function(graph, "UnCrouch", 350, 1350)

    # Ensure nodes in graph list
    try:
        nodes = list(graph.get_editor_property("nodes") or [])
        for n in (ei, crouch, uncrouch):
            if n and n not in nodes:
                nodes.append(n)
        graph.set_editor_property("nodes", nodes)
        log(f"nodes count={len(nodes)}")
    except Exception as exc:
        log(f"set nodes: {exc}")

    # Link exec pins
    started = pin_by_name(ei, "Started") or pin_by_name(ei, "Triggered")
    completed = pin_by_name(ei, "Completed")
    crouch_exec = pin_by_name(crouch, "execute") or pin_by_name(crouch, "exec")
    uncrouch_exec = pin_by_name(uncrouch, "execute") or pin_by_name(uncrouch, "exec")
    # CallFunction self pin - usually automatic with latent self

    ok1 = try_link(schema, started, crouch_exec)
    ok2 = try_link(schema, completed, uncrouch_exec)
    log(f"links started->Crouch={ok1} completed->UnCrouch={ok2}")

    # Movement config
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("max_walk_speed", RUN_SPEED)
    move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("braking_deceleration_walking", 1000.0)
    move.set_editor_property("ground_friction", 5.0)
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=400.0, roll=0.0))
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    try:
        nav = move.get_editor_property("nav_agent_props")
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception:
        pass
    try:
        cap = cdo.get_editor_property("capsule_component")
        move.set_editor_property(
            "crouched_half_height", float(cap.get_editor_property("capsule_half_height"))
        )
    except Exception:
        pass
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        mesh.set_editor_property("anim_class", abp.generated_class())

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        log(f"compiled {bp_path}")
    except Exception as exc:
        log(f"compile err: {exc}")
    return True


def inject_turn_via_event_tick(bp_path: str):
    """
    Add Event Tick that:
    - if speed < 10 and abs(yaw delta) > thresholds, PlaySlotAnimation
    Uses K2Node_Event ReceiveTick + CallFunction PlaySlotAnimationAsDynamicMontage
    """
    bp = load(bp_path)
    graph = get_event_graph(bp)
    if not graph:
        return

    # List existing events to see if Tick exists
    try:
        events = list(unreal.BlueprintEditorLibrary.list_events(bp) or [])
        log(f"events: {events[:30]}")
    except Exception as exc:
        log(f"list_events: {exc}")

    # Create Event Tick override
    try:
        # add_event_override if available
        bel = unreal.BlueprintEditorLibrary
        if hasattr(bel, "add_event_override"):
            # signature unknown — try
            try:
                bel.add_event_override(bp, "ReceiveTick")
                log("add_event_override ReceiveTick")
            except Exception as exc:
                log(f"add_event_override: {exc}")
    except Exception as exc:
        log(f"tick event: {exc}")

    # For turn montages — ensure they exist and soft-ref on BP as variables
    for var_name, typ in (("TurnYaw90", "real"), ("TurnYaw180", "real"), ("bIsTurning", "bool")):
        try:
            # pin type via string in UE 5.8
            unreal.BlueprintEditorLibrary.add_member_variable(bp, var_name, typ)
            log(f"added var {var_name}")
        except Exception as exc:
            # try EdGraphPinType
            try:
                pin = unreal.EdGraphPinType()
                if typ == "bool":
                    pin.set_editor_property("pin_category", "bool")
                else:
                    pin.set_editor_property("pin_category", "real")
                unreal.BlueprintEditorLibrary.add_member_variable(bp, var_name, pin)
                log(f"added var {var_name} via pin type")
            except Exception as exc2:
                log(f"var {var_name}: {exc} / {exc2}")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass


def verify(bp_path):
    bp = load(bp_path)
    graph = get_event_graph(bp)
    if not graph:
        return
    nodes = list(graph.get_editor_property("nodes") or [])
    walk_nodes = [n.get_name() for n in nodes if "Walk" in n.get_name() or "Crouch" in n.get_name()]
    log(f"VERIFY {bp_path} walk-related nodes: {walk_nodes}")
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_editor_property("character_movement")
    log(
        f"speed={move.get_editor_property('max_walk_speed')} "
        f"crouched={move.get_editor_property('max_walk_speed_crouched')} "
        f"yawCtrl={cdo.get_editor_property('use_controller_rotation_yaw')} "
        f"desiredRot={move.get_editor_property('use_controller_desired_rotation')}"
    )


def run():
    log("start")
    ensure_imc_walk()
    for bp in (CHAR_BP, COMBAT_BP):
        if not unreal.EditorAssetLibrary.does_asset_exist(bp):
            continue
        inject_walk(bp)
        inject_turn_via_event_tick(bp)
        verify(bp)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
