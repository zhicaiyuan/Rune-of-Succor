# -*- coding: utf-8 -*-
"""
Replace broken PrevMoveDir(vector) storage with PrevMoveYaw(float) + bHasPrevMoveDir.
Rewire angle math to yaw delta. Does not touch state machine.
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[TurnYaw] {m}")


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


def find_tv(graph, name):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() == graph and n.get_name() == name:
                return n
        except Exception:
            pass
    return None


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    # add float/bool storage
    for name, kind in (("PrevMoveYaw", "real"), ("bHasPrevMoveDir", "bool")):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(kind if kind != "real" else "real"))
            if kind == "real":
                try:
                    pin = bel.get_basic_type_by_name(unreal.Name("real"))
                except Exception:
                    pin = bel.get_basic_type_by_name(unreal.Name("double"))
            else:
                pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            bel.add_member_variable(abp, unreal.Name(name), pin)
            log(f"add {name}")
        except Exception as e:
            log(f"add {name}: {e}")
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    cdo = unreal.get_default_object(abp.generated_class())
    try:
        cdo.set_editor_property("PrevMoveYaw", 0.0)
        cdo.set_editor_property("bHasPrevMoveDir", False)
    except Exception:
        pass

    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    # Existing nodes we keep for input / flags
    brk = find_tv(graph, "TV_Break")
    sel = find_tv(graph, "TV_SelDelta")
    and_valid = find_tv(graph, "TV_AndValid")
    gt_in = find_tv(graph, "TV_HasInput")
    set_delta = find_tv(graph, "TV_SetDelta")
    set_prev_curr = find_tv(graph, "TV_SetPrevCurr")  # will repurpose or bypass
    set_prev_zero = find_tv(graph, "TV_SetPrevZero")

    # New: CurrYaw = DegAtan2(Y, X) from break of input
    atan_curr = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2")
    safe_rename(atan_curr, "TV_CurrYaw")
    pos(atan_curr, -280, 1250)

    get_prev_yaw = ed.add_get_member_variable_node("PrevMoveYaw")
    safe_rename(get_prev_yaw, "TV_GetPrevYaw")
    pos(get_prev_yaw, -280, 1350)

    sub = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble")
    if not sub:
        sub = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_FloatFloat")
    safe_rename(sub, "TV_SubYaw")
    pos(sub, 0, 1300)

    norm_axis = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm_axis, "TV_NormAxis")
    pos(norm_axis, 220, 1300)

    get_has_prev = ed.add_get_member_variable_node("bHasPrevMoveDir")
    safe_rename(get_has_prev, "TV_GetHasPrev")
    pos(get_has_prev, 0, 1450)

    # Replace and_valid B input: use bHasPrevMoveDir instead of Prev vector size
    # Break old hprev->and link by connecting get_has_prev to and_valid.B
    if and_valid and get_has_prev:
        bpin = pin_in(and_valid, "B")
        if bpin:
            try:
                bpin.break_pin_links()
            except Exception:
                pass
        ok = connect(pin_out(get_has_prev), pin_in(and_valid, "B"))
        log(f"hasPrev -> and_valid.B: {ok}")

    # Curr yaw from Break X/Y (TV_Break is break of AddInput)
    if brk:
        ok1 = connect(pin_out(brk, "Y"), pin_in(atan_curr, "Y") or pin_in(atan_curr, "A"))
        ok2 = connect(pin_out(brk, "X"), pin_in(atan_curr, "X") or pin_in(atan_curr, "B"))
        log(f"break->atan Y:{ok1} X:{ok2}")

    # Delta = NormalizeAxis(Curr - Prev)
    ok = connect(pin_out(atan_curr, "ReturnValue"), pin_in(sub, "A"))
    log(f"curr->subA: {ok}")
    ok = connect(pin_out(get_prev_yaw), pin_in(sub, "B"))
    log(f"prev->subB: {ok}")
    ok = connect(pin_out(sub, "ReturnValue"), pin_in(norm_axis, "A"))
    log(f"sub->norm: {ok}")

    # Feed SelectFloat A from NormalizeAxis instead of old Atan2(cross)
    if sel:
        apin = pin_in(sel, "A")
        if apin:
            try:
                apin.break_pin_links()
            except Exception:
                pass
        ok = connect(pin_out(norm_axis, "ReturnValue"), apin)
        log(f"norm->sel.A: {ok}")

    # Set PrevMoveYaw / bHasPrevMoveDir on true path instead of PrevMoveDir
    set_yaw = ed.add_set_member_variable_node("PrevMoveYaw")
    safe_rename(set_yaw, "TV_SetPrevYaw")
    pos(set_yaw, 2650, 820)

    set_has_t = ed.add_set_member_variable_node("bHasPrevMoveDir")
    safe_rename(set_has_t, "TV_SetHasPrevT")
    pos(set_has_t, 2900, 820)

    set_has_f = ed.add_set_member_variable_node("bHasPrevMoveDir")
    safe_rename(set_has_f, "TV_SetHasPrevF")
    pos(set_has_f, 1400, 1250)

    lit_t = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    safe_rename(lit_t, "TV_LitT")
    pos(lit_t, 1200, 1250)
    set_val(lit_t, "Value", "true")

    lit_f = find_tv(graph, "TV_LitF")

    set_t180 = find_tv(graph, "TV_SetT180")
    old_seq = None
    for n in unreal.ObjectIterator(unreal.K2Node_ExecutionSequence):
        if n.get_outer() == graph and n.get_name() == "K2Node_ExecutionSequence_0":
            old_seq = n
            break

    # TRUE path: after SetT180, go SetPrevYaw -> SetHasPrevT -> OldSeq
    # (bypass broken SetPrevCurr)
    if set_t180:
        then = bel.find_then_pin(set_t180)
        # may currently go to SetPrevCurr
        then.break_pin_links()
        log(f"T180->SetYaw: {connect(then, bel.find_execute_pin(set_yaw))}")
        log(f"yaw val: {connect(pin_out(atan_curr, 'ReturnValue'), pin_in(set_yaw, 'PrevMoveYaw'))}")
        log(f"SetYaw->HasT: {connect(bel.find_then_pin(set_yaw), bel.find_execute_pin(set_has_t))}")
        log(f"true->HasT: {connect(pin_out(lit_t, 'ReturnValue'), pin_in(set_has_t, 'bHasPrevMoveDir'))}")
        if old_seq:
            # remove SetPrevCurr from old_seq exec if present
            log(f"HasT->Old: {connect(bel.find_then_pin(set_has_t), bel.find_execute_pin(old_seq))}")

    # FALSE path: after SetPrevZero (or from Br else), set bHasPrev=false
    # Insert SetHasPrevF at start of false path: Br else -> SetHasPrevF -> SetPrevZero/Clr...
    br = find_tv(graph, "TV_BrInput")
    if br and set_has_f and lit_f:
        else_pin = bel.find_else_pin(br)
        old_else = list(else_pin.list_connected_pins() or [])
        else_pin.break_pin_links()
        log(f"BrE->HasF: {connect(else_pin, bel.find_execute_pin(set_has_f))}")
        log(f"false->HasF: {connect(pin_out(lit_f, 'ReturnValue'), pin_in(set_has_f, 'bHasPrevMoveDir'))}")
        if old_else:
            log(f"HasF->oldElse: {connect(bel.find_then_pin(set_has_f), old_else[0])}")

    # If SetPrevCurr still linked to OldSeq, break it (replaced by SetHasPrevT)
    if set_prev_curr:
        try:
            bel.find_then_pin(set_prev_curr).break_pin_links()
            log("broke SetPrevCurr.then")
        except Exception:
            pass

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)

    # update readme
    text = """ABP turn variables (WASD direction change — NOT mouse)

VARIABLES (use these in SM)
---------------------------
bWantsTurn90      bool   Abs angle in [TurnAngle90, TurnAngle180)
bWantsTurn180     bool   Abs angle >= TurnAngle180
bTurnLeft         bool   True = turn left (MoveYawDelta < 0). Swap L/R if mirrored.
MoveYawDelta      float  Signed degrees (-180..180) from previous move dir to current
AbsMoveYawDelta   float  Absolute MoveYawDelta
TurnAngle90       float  Default 60
TurnAngle180      float  Default 135

INTERNAL (usually ignore in SM)
-------------------------------
PrevMoveYaw       float  Last move-input yaw
bHasPrevMoveDir   bool   Had move input last frame
PrevMoveDir       vector UNUSED (broken type) — ignore

STATE MACHINE
-------------
Loop -> Turn180L : bWantsTurn180 AND bTurnLeft
Loop -> Turn180R : bWantsTurn180 AND NOT bTurnLeft
Loop -> Turn90L  : bWantsTurn90 AND bTurnLeft
Loop -> Turn90R  : bWantsTurn90 AND NOT bTurnLeft
Turn* -> Loop    : Automatic Rule (sequence end)
Turn* -> Stop    : bStopInput (optional)

Examples: A then D ~180; A then S ~90. Mouse look does not affect these.
"""
    path = unreal.Paths.project_content_dir() + "Python/TURN_VARS_README.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    log("readme updated")
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
