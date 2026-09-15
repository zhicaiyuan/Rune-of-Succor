# -*- coding: utf-8 -*-
"""
Finalize ordinary locomotion:
- Append LeftAlt->IA_Walk to intact IMC (do not wipe)
- Inject EventGraph IA_Walk -> Crouch/UnCrouch
- Configure character speeds / strafe / mesh
- Wire ABP turn soft refs; disable Foot IK alpha if possible
"""

from __future__ import annotations

import unreal

IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
IA_JUMP = "/Game/Input/Actions/IA_Jump"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
ALIAS_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"


def log(m):
    unreal.log(f"[FinalizeLoco] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def make_key(name: str):
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name(name))
    return key


def ensure_ia_walk():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_WALK):
        unreal.EditorAssetLibrary.duplicate_asset(IA_JUMP, IA_WALK)
    ia = load(IA_WALK)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_WALK, only_if_is_dirty=False)
    return ia


def append_walk_to_imc():
    ia = ensure_ia_walk()
    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    log(f"IMC before append: {len(mappings)}")
    for m in mappings:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = None
        try:
            kn = k.get_editor_property("key_name")
        except Exception:
            kn = str(k)
        log(f"  {kn} -> {a.get_name() if a else None}")

    # Remove only IA_Walk entries
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
    log(f"IMC after append: {len(mappings)}")


def get_schema():
    for path in (
        "/Script/BlueprintGraph.Default__EdGraphSchema_K2",
        "/Script/BlueprintGraph.EdGraphSchema_K2",
    ):
        try:
            obj = unreal.load_object(None, path)
            if obj:
                log(f"schema object {path} -> {obj}")
                return obj
        except Exception:
            pass
    cls = unreal.load_class(None, "/Script/BlueprintGraph.EdGraphSchema_K2")
    if cls:
        try:
            return unreal.get_default_object(cls)
        except Exception as exc:
            log(f"schema CDO: {exc}")
    return None


def configure_character(bp_path: str):
    bp = load(bp_path)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)

    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass

    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("max_walk_speed", 600.0)
    move.set_editor_property("max_walk_speed_crouched", 200.0)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("braking_deceleration_walking", 1000.0)
    move.set_editor_property("ground_friction", 5.0)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=400.0, roll=0.0))
    try:
        nav = move.get_editor_property("nav_agent_props")
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception as exc:
        log(f"nav crouch: {exc}")
    try:
        cap = cdo.get_editor_property("capsule_component")
        move.set_editor_property(
            "crouched_half_height", float(cap.get_editor_property("capsule_half_height"))
        )
    except Exception as exc:
        log(f"capsule hh: {exc}")

    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        mesh.set_editor_property("anim_class", abp.generated_class())

    for name in ("camera_boom", "CameraBoom"):
        try:
            boom = cdo.get_editor_property(name)
            if boom:
                boom.set_editor_property("use_pawn_control_rotation", True)
        except Exception:
            pass

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"configured {bp_path}")


def _dump_pins(node):
    pins = []
    for getter in (
        lambda: node.get_all_pins(),
        lambda: node.pins,
        lambda: node.get_editor_property("pins"),
    ):
        try:
            pins = list(getter() or [])
            if pins:
                break
        except Exception:
            continue
    for p in pins:
        try:
            log(f"  pin name={p.get_editor_property('pin_name')} dir={p.get_editor_property('direction')} id={p.pin_id if hasattr(p,'pin_id') else ''}")
        except Exception:
            try:
                log(f"  pin {p}")
            except Exception:
                pass
    return pins


def _find_pin(pins, *needles):
    for p in pins:
        try:
            name = str(p.get_editor_property("pin_name"))
        except Exception:
            name = str(p)
        lname = name.lower()
        for n in needles:
            if n.lower() in lname:
                return p
    return None


def inject_walk_graph(bp_path: str):
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)
    if not graph:
        log("no event graph")
        return
    log(f"EventGraph={graph.get_path_name()}")

    ia = load(IA_WALK)
    schema = get_schema()

    # Create Enhanced Input Action node
    ei = unreal.new_object(unreal.K2Node_EnhancedInputAction, graph)
    try:
        ei.set_editor_property("input_action", ia)
    except Exception as exc:
        log(f"set input_action: {exc}")
        try:
            ei.input_action = ia
        except Exception as exc2:
            log(f"attr input_action: {exc2}")
    for fn in ("allocate_default_pins", "reconstruct_node", "reallocate_pins_during_reconstruction"):
        if hasattr(ei, fn):
            try:
                getattr(ei, fn)()
                log(f"ei.{fn} ok")
            except Exception as exc:
                log(f"ei.{fn}: {exc}")
    bel.set_node_pos(ei, -300, 1400)
    ei_pins = _dump_pins(ei)

    # Create Crouch / UnCrouch call nodes via CallFunction
    def make_call(func_name, y):
        node = unreal.new_object(unreal.K2Node_CallFunction, graph)
        configured = False
        # Try load UFunction
        for path in (
            f"/Script/Engine.Character:{func_name}",
            f"/Script/Engine.Character.{func_name}",
        ):
            try:
                fn = unreal.load_object(None, path)
                if fn and hasattr(node, "set_from_function"):
                    node.set_from_function(fn)
                    configured = True
                    log(f"set_from_function {path}")
                    break
            except Exception as exc:
                log(f"load fn {path}: {exc}")
        if not configured:
            try:
                ref = node.get_editor_property("function_reference")
                ref.set_editor_property("member_name", unreal.Name(func_name))
                ref.set_editor_property("member_parent", unreal.Character.static_class())
                node.set_editor_property("function_reference", ref)
                configured = True
                log(f"function_reference {func_name}")
            except Exception as exc:
                log(f"function_reference fail: {exc}")
        for fn in ("allocate_default_pins", "reconstruct_node"):
            if hasattr(node, fn):
                try:
                    getattr(node, fn)()
                except Exception:
                    pass
        bel.set_node_pos(node, 400, y)
        return node

    crouch = make_call("Crouch", 1300)
    uncrouch = make_call("UnCrouch", 1550)
    crouch_pins = _dump_pins(crouch)
    uncrouch_pins = _dump_pins(uncrouch)

    # Connect
    started = _find_pin(ei_pins, "Started", "Triggered")
    completed = _find_pin(ei_pins, "Completed")
    c_exec = _find_pin(crouch_pins, "execute", "exec")
    u_exec = _find_pin(uncrouch_pins, "execute", "exec")

    def link(a, b, label):
        if not a or not b:
            log(f"link {label}: missing pin")
            return
        if not schema:
            log(f"link {label}: no schema")
            return
        for meth in ("try_create_connection", "create_connection", "TryCreateConnection"):
            if hasattr(schema, meth):
                try:
                    getattr(schema, meth)(a, b)
                    log(f"link {label} via {meth} OK")
                    return
                except Exception as exc:
                    log(f"link {label} {meth}: {exc}")
        # Graph helper
        try:
            graph.create_connection(a, b)
            log(f"link {label} via graph.create_connection OK")
        except Exception as exc:
            log(f"link {label} graph: {exc}")

    link(started, c_exec, "Started->Crouch")
    link(completed, u_exec, "Completed->UnCrouch")

    # Notify graph changed
    try:
        graph.notify_graph_changed()
    except Exception:
        pass

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(bp)
        log(f"compiled {bp_path}")
    except Exception as exc:
        log(f"compile: {exc}")


def setup_abp_turn():
    """Prepare ABP for turn: confirm BS ref, list graphs, add vars for turn anims."""
    if not unreal.EditorAssetLibrary.does_asset_exist(ABP):
        log("ABP missing")
        return
    abp = load(ABP)
    bel = unreal.BlueprintEditorLibrary
    try:
        names = list(bel.list_graph_names(abp) or [])
        log(f"ABP graphs: {names}")
    except Exception as exc:
        log(f"ABP graphs: {exc}")

    # Ensure BS asset exists
    log(f"BS exists={unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS)}")

    # Add float thresholds for turn (for manual AnimBP wiring if needed)
    for name, cat in (("TurnAngle90", "real"), ("TurnAngle180", "real")):
        try:
            pin = unreal.EdGraphPinType()
            pin.set_editor_property("pin_category", unreal.Name(cat))
            bel.add_member_variable(abp, name, pin)
            log(f"ABP var {name}")
        except Exception as exc:
            log(f"ABP var {name}: {exc}")

    # Soft-disable Foot IK Control Rig by setting AnimNode alpha — binary risky.
    # Instead note it remains; retargeted mannequin should stand.

    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass


def verify_all():
    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    log(f"VERIFY IMC count={len(mappings)}")
    has_walk = False
    for m in mappings:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = k.get_editor_property("key_name") if k else None
        an = a.get_name() if a else None
        log(f"  {kn} -> {an}")
        if an == "IA_Walk":
            has_walk = True

    bp = load(CHAR_BP)
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_editor_property("character_movement")
    mesh = cdo.get_editor_property("mesh")
    r = mesh.get_editor_property("relative_rotation")
    log(
        f"VERIFY char speed={move.get_editor_property('max_walk_speed')} "
        f"crouchSpeed={move.get_editor_property('max_walk_speed_crouched')} "
        f"accel={move.get_editor_property('max_acceleration')} "
        f"mesh=P{r.pitch}Y{r.yaw}R{r.roll} "
        f"anim={mesh.get_editor_property('anim_class')} "
        f"desiredRot={move.get_editor_property('use_controller_desired_rotation')}"
    )
    log(f"VERIFY has IA_Walk={has_walk} BS={unreal.EditorAssetLibrary.does_asset_exist(ALIAS_BS)} ABP={unreal.EditorAssetLibrary.does_asset_exist(ABP)}")
    # RTG turns
    for t in ("Turn_90_L_Seq_RTG", "Turn_90_R_Seq_RTG", "Turn_180_L_Seq_RTG", "Turn_180_R_Seq_RTG"):
        p = f"{OUT}/SwordRTG/{t}"
        log(f"VERIFY turn {t}={unreal.EditorAssetLibrary.does_asset_exist(p)}")


def run():
    log("start")
    append_walk_to_imc()
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            configure_character(bp)
            inject_walk_graph(bp)
    setup_abp_turn()
    verify_all()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
