# -*- coding: utf-8 -*-
"""Spawn EI node via InputActionEventNodeSpawner instance + WeakActionPtr; wire Crouch."""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IA_WALK = "/Game/Input/Actions/IA_Walk"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[Spawn2] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def pins(n):
    try:
        return list(n.get_all_pins() or [])
    except Exception:
        return []


def find_pin(ps, *names):
    for p in ps:
        try:
            pn = str(p.get_editor_property("pin_name"))
        except Exception:
            continue
        for name in names:
            if name.lower() == pn.lower() or name.lower() in pn.lower():
                return p
    return None


def inject(bp_path: str):
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)
    ia = load(IA_WALK)
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")

    cls = unreal.load_class(None, "/Script/InputBlueprintNodes.InputActionEventNodeSpawner")
    spawner = unreal.new_object(cls)
    log(f"spawner={spawner}")

    # Try set action on spawner
    for prop in ("weak_action_ptr", "WeakActionPtr", "action", "Action", "input_action", "InputAction"):
        try:
            spawner.set_editor_property(prop, ia)
            log(f"spawner.{prop} set OK")
        except Exception as exc:
            log(f"spawner.{prop}: {exc}")

    # Also try set_editor_properties dict
    try:
        spawner.set_editor_properties({"weak_action_ptr": ia})
        log("set_editor_properties weak_action_ptr")
    except Exception as exc:
        log(f"set_editor_properties: {exc}")

    loc_candidates = [
        unreal.Vector2D(-400.0, 1600.0),
        (-400.0, 1600.0),
        unreal.Vector(-400.0, 1600.0, 0.0),
    ]
    node = None
    for loc in loc_candidates:
        for bindings in (set(), [], None):
            try:
                node = spawner.invoke(graph, bindings, loc)
                if node:
                    log(f"invoke OK loc={loc} bindings={bindings} -> {node}")
                    break
            except Exception as exc:
                log(f"invoke fail loc={type(loc)} bind={type(bindings)}: {exc}")
        if node:
            break

    if not node:
        # Try parent BlueprintNodeSpawner.invoke after setting node class
        log("invoke failed — trying K2Node_EnhancedInputActionEvent directly")
        try:
            node = unreal.new_object(unreal.K2Node_EnhancedInputActionEvent, graph)
            for prop in ("InputAction", "input_action"):
                try:
                    node.set_editor_property(prop, ia)
                    log(f"EventNode.{prop} OK")
                except Exception as exc:
                    log(f"EventNode.{prop}: {exc}")
            # Custom function name Crouch for Started-like behavior — events have one function
            for prop in ("custom_function_name", "CustomFunctionName", "function_name", "EventReference"):
                try:
                    node.set_editor_property(prop, unreal.Name("Crouch"))
                    log(f"EventNode.{prop}=Crouch")
                except Exception as exc:
                    log(f"EventNode.{prop}: {exc}")
            for m in ("allocate_default_pins", "reconstruct_node", "post_place_node"):
                if hasattr(node, m):
                    try:
                        getattr(node, m)()
                        log(f"EventNode.{m} OK")
                    except Exception as exc:
                        log(f"EventNode.{m}: {exc}")
        except Exception as exc:
            log(f"EventNode create: {exc}")

    if not node:
        log("FAILED to create input node")
        return False

    for p in pins(node):
        try:
            log(f"node pin: {p.get_editor_property('pin_name')}")
        except Exception:
            pass

    # Call Crouch / UnCrouch via set_from_function
    def make_call(fname, y):
        n = unreal.new_object(unreal.K2Node_CallFunction, graph)
        fn = unreal.load_object(None, f"/Script/Engine.Character:{fname}")
        log(f"UFunction {fname}={fn}")
        if fn and hasattr(n, "set_from_function"):
            try:
                n.set_from_function(fn)
                log(f"set_from_function {fname} OK")
            except Exception as exc:
                log(f"set_from_function: {exc}")
        for m in ("allocate_default_pins", "reconstruct_node"):
            if hasattr(n, m):
                try:
                    getattr(n, m)()
                except Exception:
                    pass
        try:
            bel.set_node_pos(n, unreal.Vector2D(350.0, float(y)))
        except Exception:
            try:
                bel.set_node_pos(n, (350, y))
            except Exception as exc:
                log(f"set_node_pos: {exc}")
        return n

    crouch = make_call("Crouch", 1500)
    uncrouch = make_call("UnCrouch", 1750)

    def link(a, b, label):
        if not a or not b:
            log(f"link {label} missing")
            return
        try:
            schema.try_create_connection(a, b)
            log(f"link {label} OK")
        except Exception as exc:
            log(f"link {label}: {exc}")

    np = pins(node)
    # Enhanced Input Action node has Started/Completed; Event node has then/exec
    link(find_pin(np, "Started", "Pressed", "then"), find_pin(pins(crouch), "execute"), "start->crouch")
    link(find_pin(np, "Completed", "Released"), find_pin(pins(uncrouch), "execute"), "complete->uncrouch")

    # Movement
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("max_walk_speed", 600.0)
    move.set_editor_property("max_walk_speed_crouched", 200.0)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("orient_rotation_to_movement", False)
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
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        mesh.set_editor_property("anim_class", load(ABP).generated_class())

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(bp)
        log(f"compiled {bp_path}")
    except Exception as exc:
        log(f"compile: {exc}")
    return True


def add_turn_to_idle_abp():
    """Replace Idle sequence in ABP Idle state with logic — if Idle uses MM_Idle, leave it.
    Add turn montages playable via DefaultSlot by ensuring Slot name.
    Create a simple Aim Offset-like: use Turn sequences as additive — skip.
    Wire: use Locomotion Idle state; character DesiredRotation provides turn.
    Additionally set ABP to use turn anims as SequencePlayers in new state via AnimationLibrary — N/A.
    """
    abp = load(ABP)
    # Ensure Slot on montages
    for name in ("AM_Turn_90_L", "AM_Turn_90_R", "AM_Turn_180_L", "AM_Turn_180_R"):
        path = f"/Game/Characters/\u6797\u7b26/\u52a8\u753b/Montages/{name}"
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            continue
        m = load(path)
        try:
            tracks = list(m.get_editor_property("slot_anim_tracks") or [])
            if tracks:
                tracks[0].set_editor_property("slot_name", "DefaultSlot")
                m.set_editor_property("slot_anim_tracks", tracks)
                unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
                log(f"slot ok {name}")
        except Exception as exc:
            log(f"slot {name}: {exc}")
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception:
        pass


def run():
    log("start")
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            inject(bp)
    add_turn_to_idle_abp()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
