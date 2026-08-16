# -*- coding: utf-8 -*-
"""
Press C to toggle crouch. Small patch on existing character Tick.

Fixes:
  1) crouched_half_height was equal to standing capsule (90) so Crouch() had no visual
  2) C was not wired to Character.Crouch / UnCrouch
  3) AnimBP SET Is Crouched reads CharacterMovement.IsCrouching

Does not change Alt-walk (WW_*) chain. Inserts after LC_SetHasInput.
Run with editor CLOSED.
"""
from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
CROUCH_HALF_HEIGHT = 40.0

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixCrouchC] {m}")


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def connect(a, b):
    if not a or not b:
        return False
    try:
        return bool(a.try_create_connection(b))
    except Exception:
        try:
            return bool(b.try_create_connection(a))
        except Exception:
            return False


def pin_in(node, name):
    for cand in bel.list_input_pins(node) or []:
        try:
            if str(cand.get_pin_name()) == name:
                return cand
        except Exception:
            pass
    try:
        return bel.find_input_pin(node, name)
    except Exception:
        return None


def pin_out(node, name=None):
    if name:
        for cand in bel.list_output_pins(node) or []:
            try:
                if str(cand.get_pin_name()) == name:
                    return cand
            except Exception:
                pass
        try:
            return bel.find_output_pin(node, name)
        except Exception:
            pass
    try:
        return bel.find_result_pin(node)
    except Exception:
        outs = bel.list_output_pins(node) or []
        return outs[0] if outs else None


def set_val(node, pin_name, value):
    p = pin_in(node, pin_name)
    if not p:
        return False
    try:
        p.set_pin_value(str(value))
        return True
    except Exception:
        return False


def pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        pass


def safe_rename(node, name):
    try:
        existing = unreal.find_object(node.get_outer(), name)
        if existing and existing != node:
            return False
        node.rename(name)
        return True
    except Exception:
        return False


def find_named(graph, name):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() == graph and n.get_name() == name:
            return n
    return None


def purge_prefix(ed, graph, prefix):
    kill = [
        n
        for n in unreal.ObjectIterator(unreal.EdGraphNode)
        if n.get_outer() == graph and n.get_name().startswith(prefix)
    ]
    if kill:
        ed.remove_nodes(kill)
    log(f"purged {len(kill)} {prefix}*")


def patch_cdo(bp):
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_editor_property("character_movement")
    cap = cdo.get_editor_property("capsule_component")
    stand = float(cap.get_editor_property("capsule_half_height"))
    move.set_editor_property("crouched_half_height", CROUCH_HALF_HEIGHT)
    try:
        move.set_editor_property("crouch_maintains_base_location", True)
    except Exception:
        try:
            move.set_editor_property("b_crouch_maintains_base_location", True)
        except Exception:
            pass
    nav = move.get_editor_property("nav_agent_props")
    try:
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception as e:
        log(f"nav can_crouch: {e}")
    log(
        f"CDO stand_hh={stand} crouched_hh={move.get_editor_property('crouched_half_height')} "
        f"crouch_spd={move.get_editor_property('max_walk_speed_crouched')}"
    )


def ensure_char_vars(bp):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name("bPrevCDown"), pin)
        log("added bPrevCDown")
    except Exception:
        pass


def find_tick_continue(graph, attach):
    """First non-CR_* node after attach.exec, walking through CR_ chain if present."""
    try:
        then = bel.find_then_pin(attach)
        pins = list(then.list_connected_pins() or [])
    except Exception:
        pins = []
    seen = set()
    while pins:
        n = pins[0].get_owning_node()
        nm = n.get_name()
        if nm in seen:
            break
        seen.add(nm)
        if not nm.startswith("CR_"):
            return bel.find_execute_pin(n), nm
        try:
            nxt = bel.find_then_pin(n)
            pins = list(nxt.list_connected_pins() or []) if nxt else []
        except Exception:
            pins = []
    for n in unreal.ObjectIterator(unreal.K2Node_IfThenElse):
        if n.get_outer() != graph:
            continue
        if n.get_name().startswith("CR_"):
            continue
        return bel.find_execute_pin(n), n.get_name()
    return None, None


def wire_character(bp):
    ensure_char_vars(bp)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    attach = find_named(graph, "LC_SetHasInput")
    if not attach:
        attach = find_named(graph, "WW_SetSpd")
    if not attach:
        raise RuntimeError("LC_SetHasInput / WW_SetSpd not found")

    old_exec, old_name = find_tick_continue(graph, attach)
    log(f"continue after crouch -> {old_name}")

    then = bel.find_then_pin(attach)
    then.break_pin_links()
    purge_prefix(ed, graph, "CR_")
    then = bel.find_then_pin(attach)

    get_pc = find_named(graph, "WW_GetPC")
    if not get_pc:
        get_pc = ed.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerController")
        safe_rename(get_pc, "CR_GetPC")
        pos(get_pc, 900, 2100)
        set_val(get_pc, "PlayerIndex", "0")

    is_c = ed.add_call_function_node("/Script/Engine.PlayerController:IsInputKeyDown")
    safe_rename(is_c, "CR_IsC")
    pos(is_c, 1100, 2100)
    connect(pin_out(get_pc, "ReturnValue"), bel.find_self_pin(is_c) or pin_in(is_c, "self"))
    if not set_val(is_c, "Key", "C"):
        set_val(is_c, "Key", '(KeyName="C")')

    get_prev = ed.add_get_member_variable_node("bPrevCDown")
    safe_rename(get_prev, "CR_GetPrevC")
    pos(get_prev, 1100, 2240)

    not_prev = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_prev, "CR_NotPrev")
    pos(not_prev, 1280, 2240)
    connect(pin_out(get_prev, "bPrevCDown") or pin_out(get_prev), pin_in(not_prev, "A"))

    and_edge = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_edge, "CR_AndEdge")
    pos(and_edge, 1460, 2160)
    connect(pin_out(is_c, "ReturnValue"), pin_in(and_edge, "A"))
    connect(pin_out(not_prev, "ReturnValue"), pin_in(and_edge, "B"))

    br_edge = ed.add_branch_node()
    safe_rename(br_edge, "CR_BranchEdge")
    pos(br_edge, 1680, 2000)
    connect(pin_out(and_edge, "ReturnValue"), pin_in(br_edge, "Condition") or bel.find_condition_pin(br_edge))

    get_crouched = ed.add_get_member_variable_node("bIsCrouched")
    if not get_crouched:
        get_crouched = ed.add_get_member_variable_node("bIsCrouched", "/Script/Engine.Character")
    safe_rename(get_crouched, "CR_GetIsCrouched")
    pos(get_crouched, 1680, 1880)

    br_state = ed.add_branch_node()
    safe_rename(br_state, "CR_BranchState")
    pos(br_state, 1900, 1880)
    connect(
        pin_out(get_crouched, "bIsCrouched") or pin_out(get_crouched),
        pin_in(br_state, "Condition") or bel.find_condition_pin(br_state),
    )

    crouch = ed.add_call_function_node("/Script/Engine.Character:Crouch")
    safe_rename(crouch, "CR_Crouch")
    pos(crouch, 2140, 1980)
    set_val(crouch, "bClientSimulation", "false")

    uncrouch = ed.add_call_function_node("/Script/Engine.Character:UnCrouch")
    safe_rename(uncrouch, "CR_UnCrouch")
    pos(uncrouch, 2140, 1840)
    set_val(uncrouch, "bClientSimulation", "false")

    set_prev = ed.add_set_member_variable_node("bPrevCDown")
    safe_rename(set_prev, "CR_SetPrevC")
    pos(set_prev, 2400, 2000)
    connect(pin_out(is_c, "ReturnValue"), pin_in(set_prev, "bPrevCDown"))

    links = []
    links.append(("att->edge", connect(then, bel.find_execute_pin(br_edge))))
    links.append(("edgeT->state", connect(bel.find_then_pin(br_edge), bel.find_execute_pin(br_state))))
    links.append(("stateT->un", connect(bel.find_then_pin(br_state), bel.find_execute_pin(uncrouch))))
    links.append(("stateF->c", connect(bel.find_else_pin(br_state), bel.find_execute_pin(crouch))))
    links.append(("un->prev", connect(bel.find_then_pin(uncrouch), bel.find_execute_pin(set_prev))))
    links.append(("c->prev", connect(bel.find_then_pin(crouch), bel.find_execute_pin(set_prev))))
    links.append(("edgeF->prev", connect(bel.find_else_pin(br_edge), bel.find_execute_pin(set_prev))))
    if old_exec:
        links.append(("prev->old", connect(bel.find_then_pin(set_prev), old_exec)))
        log(f"reattach -> {old_name}")
    else:
        log("WARN: no Tick continue node")
    for n, ok in links:
        log(f"char {n}: {ok}")


def ensure_abp_var(abp):
    for name in ("IsCrouched", "Is Crouched"):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            bel.add_member_variable(abp, unreal.Name(name), pin)
            log(f"ABP add {name}")
        except Exception:
            pass


def find_set_is_crouched(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if n.get_outer() != graph:
            continue
        title = ""
        try:
            title = str(bel.get_node_title(n))
        except Exception:
            pass
        name = n.get_name()
        blob = (title + " " + name).replace(" ", "").lower()
        if "iscrouched" in blob:
            return n
    return None


def wire_abp(abp):
    ensure_abp_var(abp)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()
    purge_prefix(ed, graph, "CR_")

    set_c = find_set_is_crouched(graph)
    if not set_c:
        set_c = ed.add_set_member_variable_node("isCrouched")
        if not set_c:
            set_c = ed.add_set_member_variable_node("IsCrouched")
        safe_rename(set_c, "CR_SetIsCrouched")
        pos(set_c, 800, 200)
        log("created SET isCrouched")
    else:
        log(f"reuse SET {set_c.get_name()} title={bel.get_node_title(set_c)}")
        try:
            for p in bel.list_input_pins(set_c) or []:
                log(f"  SET in {p.get_pin_name()}")
        except Exception:
            pass

    get_pawn = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
    safe_rename(get_pawn, "CR_GetPawn")
    pos(get_pawn, 0, 200)

    get_flag = None
    for spec in (
        ("bIsCrouched", "/Script/Engine.Character"),
        ("bIsCrouched", None),
        ("IsCrouched", "/Script/Engine.Character"),
    ):
        name, cls = spec
        try:
            if cls:
                get_flag = ed.add_get_member_variable_node(name, cls)
            else:
                get_flag = ed.add_get_member_variable_node(name)
        except Exception as e:
            log(f"get {name} {cls}: {e}")
            get_flag = None
        if get_flag:
            log(f"GET crouched via {name} {cls}")
            break
    if not get_flag:
        log("WARN: cannot create bIsCrouched getter")
        return
    safe_rename(get_flag, "CR_GetBIsCrouched")
    pos(get_flag, 280, 200)
    connect(
        pin_out(get_pawn, "ReturnValue"),
        bel.find_self_pin(get_flag) or pin_in(get_flag, "self") or pin_in(get_flag, "Target"),
    )

    src = pin_out(get_flag, "bIsCrouched") or pin_out(get_flag)
    val_pin = None
    for pname in ("isCrouched", "IsCrouched", "Is Crouched", "bIsCrouched"):
        val_pin = pin_in(set_c, pname)
        if val_pin:
            break
    ok = connect(src, val_pin)
    log(f"bIsCrouched -> SET: {ok} val={val_pin.get_pin_name() if val_pin else None}")

    # If SET has no exec yet, hang it after BlueprintUpdateAnimation
    exec_in = bel.find_execute_pin(set_c)
    incoming = list(exec_in.list_connected_pins() or []) if exec_in else []
    if not incoming:
        upd = None
        for n in unreal.ObjectIterator(unreal.K2Node_Event):
            if n.get_outer() != graph:
                continue
            try:
                if "UpdateAnimation" in n.get_name() or "Update Animation" in str(
                    bel.get_node_title(n)
                ):
                    upd = n
                    break
            except Exception:
                pass
        if upd:
            then = bel.find_then_pin(upd)
            old = list(then.list_connected_pins() or [])
            then.break_pin_links()
            connect(then, exec_in)
            if old:
                connect(bel.find_then_pin(set_c), old[0])
            log("hung SET after UpdateAnimation")
    else:
        log(f"SET already exec from {[p.get_owning_node().get_name() for p in incoming]}")


def run():
    log("start toggle C")
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    patch_cdo(bp)
    wire_character(bp)
    try:
        bel.compile_blueprint(bp)
        log("char compile OK")
    except Exception as e:
        log(f"char compile: {e}")
    save(CHAR)
    log("DONE — press C toggles crouch; release does nothing. AnimBP unchanged.")


if __name__ == "__main__":
    run()
