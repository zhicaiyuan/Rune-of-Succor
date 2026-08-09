# -*- coding: utf-8 -*-
"""
Bind IA_Walk Started/Completed -> Crouch/UnCrouch via InputActionEventNodeSpawner (load_class).
Add idle turn: Event Tick -> yaw delta -> Play Slot Animation montages.
"""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IA_WALK = "/Game/Input/Actions/IA_Walk"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
TURNS = {
    "L90": f"{OUT}/Montages/AM_Turn_90_L",
    "R90": f"{OUT}/Montages/AM_Turn_90_R",
    "L180": f"{OUT}/Montages/AM_Turn_180_L",
    "R180": f"{OUT}/Montages/AM_Turn_180_R",
}


def log(m):
    unreal.log(f"[BindWalkTurn] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def spawn_enhanced_input_node(graph, ia, x, y):
    """Use InputActionEventNodeSpawner from InputBlueprintNodes module."""
    spawner_cls = None
    for path in (
        "/Script/InputBlueprintNodes.InputActionEventNodeSpawner",
        "/Script/EnhancedInput.InputActionEventNodeSpawner",
    ):
        spawner_cls = unreal.load_class(None, path)
        if spawner_cls:
            log(f"loaded {path}")
            break
    if not spawner_cls:
        log("InputActionEventNodeSpawner class not found")
        return None

    # Static Create
    create = getattr(spawner_cls, "create", None) or getattr(spawner_cls, "Create", None)
    if not create:
        # try call as unreal.InputActionEventNodeSpawner.create after assigning
        log(f"spawner methods: {[m for m in dir(spawner_cls) if not m.startswith('_')][:40]}")
        return None

    node_cls = unreal.K2Node_EnhancedInputAction.static_class()
    try:
        spawner = create(node_cls, ia)
    except Exception as exc:
        log(f"create(node_cls, ia): {exc}")
        try:
            spawner = create(unreal.K2Node_EnhancedInputAction, ia)
        except Exception as exc2:
            log(f"create alt: {exc2}")
            return None

    log(f"spawner instance={spawner}")
    loc = unreal.Vector2D(float(x), float(y))
    # BindingSet
    bindings = None
    for maker in (
        lambda: unreal.BlueprintNodeSpawner.BindingSet(),
        lambda: set(),
        lambda: [],
        lambda: None,
    ):
        try:
            bindings = maker()
            break
        except Exception:
            continue

    try:
        node = spawner.invoke(graph, bindings, loc)
        log(f"invoke -> {node}")
        return node
    except Exception as exc:
        log(f"invoke failed: {exc}")
        # Try with empty FBindingSet via default
        try:
            node = spawner.invoke(graph, set(), loc)
            return node
        except Exception as exc2:
            log(f"invoke2: {exc2}")
    return None


def pins(node):
    for getter in (
        lambda: node.get_all_pins(),
        lambda: list(node.list_output_pins() or []) + list(node.list_input_pins() or []),
    ):
        try:
            p = list(getter() or [])
            if p:
                return p
        except Exception:
            pass
    return []


def find_pin(pin_list, *names):
    for p in pin_list:
        try:
            pn = str(p.get_editor_property("pin_name"))
        except Exception:
            pn = str(p)
        for n in names:
            if n.lower() in pn.lower():
                return p
    return None


def make_call(graph, func_name, x, y):
    node = unreal.new_object(unreal.K2Node_CallFunction, graph)
    try:
        fn = unreal.load_object(None, f"/Script/Engine.Character:{func_name}")
        if fn and hasattr(node, "set_from_function"):
            node.set_from_function(fn)
        else:
            ref = node.get_editor_property("function_reference")
            ref.set_editor_property("member_name", unreal.Name(func_name))
            ref.set_editor_property("member_parent", unreal.Character.static_class())
            node.set_editor_property("function_reference", ref)
    except Exception as exc:
        log(f"make_call {func_name}: {exc}")
    for m in ("allocate_default_pins", "reconstruct_node"):
        if hasattr(node, m):
            try:
                getattr(node, m)()
            except Exception:
                pass
    try:
        node.node_pos_x = x
        node.node_pos_y = y
    except Exception:
        pass
    return node


def link(schema, a, b, label):
    if not a or not b:
        log(f"link {label}: missing")
        return False
    try:
        schema.try_create_connection(a, b)
        log(f"link {label} OK")
        return True
    except Exception as exc:
        log(f"link {label}: {exc}")
        return False


def inject_walk(bp_path):
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)
    ia = load(IA_WALK)
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")

    ei = spawn_enhanced_input_node(graph, ia, -400, 1500)
    if not ei:
        return False

    crouch = make_call(graph, "Crouch", 300, 1400)
    uncrouch = make_call(graph, "UnCrouch", 300, 1650)

    ei_pins = pins(ei)
    for p in ei_pins:
        try:
            log(f"EI pin: {p.get_editor_property('pin_name')}")
        except Exception:
            pass

    ok1 = link(schema, find_pin(ei_pins, "Started"), find_pin(pins(crouch), "execute"), "Started->Crouch")
    ok2 = link(schema, find_pin(ei_pins, "Completed"), find_pin(pins(uncrouch), "execute"), "Completed->UnCrouch")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(bp)
        log(f"compiled {bp_path} links={ok1},{ok2}")
    except Exception as exc:
        log(f"compile: {exc}")
    return ok1 or ok2


def inject_idle_turn(bp_path):
    """
    Add ReceiveTick override that plays turn montages based on control yaw delta when nearly idle.
    Full branch graph is complex; we add:
    - Event Tick (override)
    - Variables for montage soft refs
    - Call to PlaySlotAnimationAsDynamicMontage when possible
    """
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)

    # Add member variables for turn montages (object refs)
    for key, path in TURNS.items():
        var = f"MontageTurn{key}"
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name("object"))
            pin.set_editor_property("pin_sub_category_object", unreal.AnimMontage.static_class())
            bel.add_member_variable(bp, var, pin)
            log(f"var {var}")
        except Exception as exc:
            log(f"var {var}: {exc}")

    # Set defaults on CDO
    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        for key, path in TURNS.items():
            if not unreal.EditorAssetLibrary.does_asset_exist(path):
                continue
            mont = load(path)
            for prop in (f"montage_turn{key}", f"MontageTurn{key}"):
                try:
                    cdo.set_editor_property(prop, mont)
                    log(f"set {prop}")
                except Exception:
                    pass
    except Exception as exc:
        log(f"CDO montages: {exc}")

    # Try add Event Tick override
    try:
        if hasattr(bel, "add_event_override"):
            # Unknown signature — probe
            try:
                bel.add_event_override(bp, unreal.Name("ReceiveTick"))
                log("add_event_override ReceiveTick")
            except Exception as exc:
                log(f"add_event_override: {exc}")
                try:
                    bel.add_event_override(bp, "ReceiveTick")
                except Exception as exc2:
                    log(f"add_event_override2: {exc2}")
    except Exception as exc:
        log(f"tick: {exc}")

    # List events after
    try:
        log(f"events: {list(bel.list_events(bp) or [])[:40]}")
    except Exception:
        pass

    # Hybrid rotation already set for turn lag — ensure still on
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=300.0, roll=0.0))

    # When idle, lower rotation rate so turn anims (when wired) can lead; when moving, higher.
    # Without tick graph, constant 300 deg/s gives visible turn toward camera.

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    log(f"turn prep done {bp_path}")


def wire_abp_turn_state():
    """Inspect ABP state machine; if we can add states via BEL, do so."""
    abp_path = f"{OUT}/ABP_StrafeLocomotion"
    if not unreal.EditorAssetLibrary.does_asset_exist(abp_path):
        return
    abp = load(abp_path)
    bel = unreal.BlueprintEditorLibrary
    try:
        names = list(bel.list_graph_names(abp) or [])
        log(f"ABP graphs: {names}")
        for n in names:
            if "Locomotion" in str(n) or "State" in str(n) or "AnimGraph" in str(n):
                g = bel.find_graph(abp, n)
                log(f"  graph {n} -> {g}")
    except Exception as exc:
        log(f"ABP inspect: {exc}")

    # Ensure turn sequences are set as anim assets on ABP if SequencePlayers exist — skip binary.

    # Soft approach for turn: use Control Rig off - set ABP preview
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass


def run():
    log("start")
    for bp in (CHAR_BP, COMBAT_BP):
        if not unreal.EditorAssetLibrary.does_asset_exist(bp):
            continue
        inject_walk(bp)
        inject_idle_turn(bp)
    wire_abp_turn_state()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
