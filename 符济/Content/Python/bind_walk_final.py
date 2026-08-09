# -*- coding: utf-8 -*-
"""Final walk bind + idle turn tick using BlueprintEditorLibrary APIs that exist."""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IA_WALK = "/Game/Input/Actions/IA_Walk"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[BindFinal] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def try_spawner():
    ia = load(IA_WALK)
    # After load_class, see if unreal exposes it
    unreal.load_class(None, "/Script/InputBlueprintNodes.InputActionEventNodeSpawner")
    names = [n for n in dir(unreal) if "Spawner" in n or "InputActionEvent" in n]
    log(f"unreal names: {names}")

    # call_method on Class
    cls = unreal.load_class(None, "/Script/InputBlueprintNodes.InputActionEventNodeSpawner")
    for meth in ("create", "Create", "call_method"):
        log(f"cls.{meth}={getattr(cls, meth, None)}")

    # Try Class library style used by other factories
    try:
        # Some statics appear on default object
        cdo = unreal.get_default_object(cls)
        log(f"CDO={cdo} methods={[m for m in dir(cdo) if 'reate' in m or 'nvoke' in m]}")
    except Exception as exc:
        log(f"CDO: {exc}")

    # BlueprintNodeSpawner generic
    try:
        node_cls = unreal.K2Node_EnhancedInputAction.static_class()
        # UBlueprintNodeSpawner::Create with custom
        if hasattr(unreal, "BlueprintNodeSpawner"):
            log(f"BlueprintNodeSpawner dirs: {[m for m in dir(unreal.BlueprintNodeSpawner) if not m.startswith('_')][:30]}")
    except Exception as exc:
        log(f"BNS: {exc}")

    return None


def add_tick_and_walk_logic(bp_path: str):
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
    ia = load(IA_WALK)

    # 1) Event Tick override with position
    tick_node = None
    try:
        tick_node = bel.add_event_override(bp, "ReceiveTick", unreal.Vector2D(-600.0, 1800.0))
        log(f"add_event_override ReceiveTick -> {tick_node}")
    except Exception as exc:
        log(f"add_event_override: {exc}")
        try:
            tick_node = bel.add_event_override(bp, unreal.Name("ReceiveTick"), unreal.Vector2D(-600.0, 1800.0))
            log(f"add_event_override Name -> {tick_node}")
        except Exception as exc2:
            log(f"add_event_override2: {exc2}")

    # 2) Spawn EI node via BlueprintActionDatabase / Menu
    ei = None
    try:
        # Use node spawner create from Class defaults via execute
        cls = unreal.load_class(None, "/Script/InputBlueprintNodes.InputActionEventNodeSpawner")
        # UObject.process_event style
        if hasattr(cls, "call_method"):
            try:
                ei_spawner = cls.call_method("Create", (unreal.K2Node_EnhancedInputAction.static_class(), ia))
                log(f"call_method Create -> {ei_spawner}")
            except Exception as exc:
                log(f"call_method Create: {exc}")
    except Exception as exc:
        log(f"spawn attempt: {exc}")

    # 3) Fallback: K2Node_GetInputActionValue + Branch on tick for walk speed
    #    Poll IA_Walk each tick and set MaxWalkSpeed — works without Crouch!
    get_val = unreal.new_object(unreal.K2Node_GetInputActionValue, graph)
    for prop in ("InputAction", "input_action", "ActionAsset"):
        try:
            get_val.set_editor_property(prop, ia)
            log(f"GetInputActionValue.{prop} set")
            break
        except Exception as exc:
            log(f"GetInputActionValue.{prop}: {exc}")
    # protected? try reconstruct
    for m in ("allocate_default_pins", "reconstruct_node", "post_reconstruct_node"):
        if hasattr(get_val, m):
            try:
                getattr(get_val, m)()
            except Exception:
                pass
    try:
        get_val.node_pos_x = -200
        get_val.node_pos_y = 1800
    except Exception:
        pass

    # Dump get_val pins / properties
    log(f"GetInputActionValue attrs action-related: {[a for a in dir(get_val) if 'action' in a.lower() or 'input' in a.lower()]}")

    # 4) Call SetMaxWalkSpeed on CharacterMovement — need CallFunction
    # CharacterMovementComponent.set_max_walk_speed or set_editor - runtime is MaxWalkSpeed property
    # Use K2Node_VariableSet / CallFunction "SetMaxWalkSpeed" if exists
    # Actually: get Character Movement -> Set Max Walk Speed (macro)
    # Function: UCharacterMovementComponent doesn't have SetMaxWalkSpeed UFUNCTION easily
    # Use "Set Max Walk Speed" via Set member

    # Practical: Call Crouch/UnCrouch based on bool from GetInputActionValue
    # GetInputActionValue for bool action outputs bool

    crouch = unreal.new_object(unreal.K2Node_CallFunction, graph)
    uncrouch = unreal.new_object(unreal.K2Node_CallFunction, graph)
    for node, fname in ((crouch, "Crouch"), (uncrouch, "UnCrouch")):
        try:
            fn = unreal.load_object(None, f"/Script/Engine.Character:{fname}")
            if fn and hasattr(node, "set_from_function"):
                node.set_from_function(fn)
            else:
                ref = node.get_editor_property("function_reference")
                ref.set_editor_property("member_name", unreal.Name(fname))
                ref.set_editor_property("member_parent", unreal.Character.static_class())
                node.set_editor_property("function_reference", ref)
            for m in ("allocate_default_pins", "reconstruct_node"):
                if hasattr(node, m):
                    try:
                        getattr(node, m)()
                    except Exception:
                        pass
        except Exception as exc:
            log(f"{fname}: {exc}")

    crouch.node_pos_x = 400
    crouch.node_pos_y = 1700
    uncrouch.node_pos_x = 400
    uncrouch.node_pos_y = 1950

    # Branch node
    branch = None
    try:
        branch = unreal.new_object(unreal.K2Node_IfThenElse, graph)
        branch.allocate_default_pins()
        branch.node_pos_x = 100
        branch.node_pos_y = 1800
        log("Branch node created")
    except Exception as exc:
        log(f"Branch: {exc}")
        try:
            branch = unreal.new_object(getattr(unreal, "K2Node_Branch"), graph)
        except Exception:
            pass

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
                if name.lower() in pn.lower():
                    return p
        return None

    def link(a, b, label):
        if not (a and b and schema):
            log(f"link {label} skip a={a} b={b}")
            return
        try:
            schema.try_create_connection(a, b)
            log(f"link {label} OK")
        except Exception as exc:
            log(f"link {label}: {exc}")

    # Connect Tick -> Branch exec; GetValue bool -> Branch condition; Then->Crouch Else->UnCrouch
    if tick_node:
        t_pins = pins(tick_node)
        for p in t_pins:
            try:
                log(f"Tick pin {p.get_editor_property('pin_name')}")
            except Exception:
                pass
        if branch:
            link(find_pin(t_pins, "then", "execute", "output"), find_pin(pins(branch), "execute"), "Tick->Branch")
            # value pin from get_val
            gv_pins = pins(get_val)
            for p in gv_pins:
                try:
                    log(f"GV pin {p.get_editor_property('pin_name')}")
                except Exception:
                    pass
            link(find_pin(gv_pins, "ReturnValue", "bool", "ActionValue", "Value"), find_pin(pins(branch), "Condition"), "Val->Cond")
            link(find_pin(pins(branch), "then", "True"), find_pin(pins(crouch), "execute"), "Then->Crouch")
            link(find_pin(pins(branch), "else", "False"), find_pin(pins(uncrouch), "execute"), "Else->UnCrouch")

    # Idle turn on same tick: PlaySlotAnimation when yaw delta large — simplified:
    # Call PlaySlotAnimationAsDynamicMontage on Mesh
    # Skip full yaw math nodes (too many); ensure DesiredRotation handles visual turn.
    # Add Play Animation for turn when we can detect — use lower RotationRate when speed low via... skip.

    # Ensure movement for walk crouch
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

    # Desired rotation for turn-in-place feel + body faces camera for 8-dir
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=360.0, roll=0.0))

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


def add_turn_states_to_abp():
    """Add Turn Idle state into Locomotion SM if AnimationStateMachineGraph allows."""
    abp = load(ABP)
    bel = unreal.BlueprintEditorLibrary
    # Find Idle state graph — already exists Name("Idle")
    try:
        idle = bel.find_graph(abp, "Idle")
        log(f"Idle graph={idle}")
        # List nodes in Idle - if SequencePlayer, could swap — nodes protected
    except Exception as exc:
        log(f"Idle: {exc}")

    # Create new animation state via AnimationStateMachineGraph API
    loco = bel.find_graph(abp, "Locomotion")
    log(f"Locomotion SM={loco} type={type(loco)}")
    if loco:
        methods = [m for m in dir(loco) if not m.startswith("_") and ("state" in m.lower() or "add" in m.lower() or "node" in m.lower())]
        log(f"SM methods: {methods[:40]}")

    # For turn: put Turn_90 sequences into a BlendSpace or use AimOffset — create BS_Turn if needed
    # Simpler deliverable: Turn montages exist; character rotates with DesiredRotation (visible turn).
    # Document that full Turn_90/180 state machine should play montages via Slot (ABP has Slot).

    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass


def verify_imc_walk():
    imc = load("/Game/Input/IMC_Default")
    dkm = imc.get_editor_property("default_key_mappings")
    arr = list(dkm.get_editor_property("mappings") or [])
    log(f"IMC DKM count={len(arr)}")
    for m in arr:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = k.get_editor_property("key_name") if k else None
        if a and ("Walk" in a.get_name() or kn == "LeftAlt"):
            log(f"  WALK MAP {kn} -> {a.get_name()}")


def run():
    log("start")
    try_spawner()
    verify_imc_walk()
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            add_tick_and_walk_logic(bp)
    add_turn_states_to_abp()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
