# -*- coding: utf-8 -*-
"""
Rebuild turn vars: angle between Actor facing and move-input direction.

Keeps SM-facing names:
  MoveYawDelta, AbsMoveYawDelta, bTurnLeft, bWantsTurn90, bWantsTurn180
  TurnAngle90 (60), TurnAngle180 (135)

Does NOT modify state machine.
Preserves: SI_SetStop -> (turn compute) -> K2Node_ExecutionSequence_0
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
INPUT_EPS = 0.1

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[TurnFace] {m}")


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
    except Exception as e:
        log(f"set_val {pin_name}: {e}")
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
        try:
            if n.get_outer() == graph and n.get_name() == name:
                return n
        except Exception:
            pass
    return None


def ensure_vars(abp):
    specs = [
        ("MoveYawDelta", "real"),
        ("AbsMoveYawDelta", "real"),
        ("bTurnLeft", "bool"),
        ("bWantsTurn90", "bool"),
        ("bWantsTurn180", "bool"),
        ("TurnAngle90", "real"),
        ("TurnAngle180", "real"),
        ("ActorYaw", "real"),
        ("InputYaw", "real"),
    ]
    for name, kind in specs:
        try:
            if kind == "bool":
                pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            else:
                try:
                    pin = bel.get_basic_type_by_name(unreal.Name("real"))
                except Exception:
                    pin = bel.get_basic_type_by_name(unreal.Name("double"))
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    cdo = unreal.get_default_object(abp.generated_class())
    for n, v in (
        ("TurnAngle90", 60.0),
        ("TurnAngle180", 135.0),
        ("MoveYawDelta", 0.0),
        ("AbsMoveYawDelta", 0.0),
        ("bTurnLeft", False),
        ("bWantsTurn90", False),
        ("bWantsTurn180", False),
    ):
        try:
            cdo.set_editor_property(n, v)
        except Exception:
            pass


def purge_tv(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_IfThenElse,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
        unreal.K2Node_ExecutionSequence,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("TV_") or name.startswith("TV_DEL_") or "Turn vars" in title or "TurnFace" in title:
                    # never delete the original loco sequence
                    if name == "K2Node_ExecutionSequence_0":
                        continue
                    kill.append(n)
            except Exception:
                pass
    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    for i, n in enumerate(uniq):
        try:
            n.rename(f"TV_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")


def run():
    log("start — facing vs input")
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ensure_vars(abp)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    si = find_named(graph, "SI_SetStop")
    old_seq = find_named(graph, "K2Node_ExecutionSequence_0")
    try_get = find_named(graph, "SI_TryGet")
    if not si:
        raise RuntimeError("SI_SetStop missing")
    if not old_seq:
        raise RuntimeError("K2Node_ExecutionSequence_0 missing")

    # Remember attach
    si_then = bel.find_then_pin(si)
    si_then.break_pin_links()

    purge_tv(ed, graph)

    if not try_get:
        try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
        safe_rename(try_get, "SI_TryGet")
        pos(try_get, -1400, -200)
    pawn = pin_out(try_get, "ReturnValue")

    # --- input vector ---
    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "TV_GetPending")
    pos(get_pending, -1100, 700)
    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "TV_GetLast")
    pos(get_last, -1100, 840)

    add_v = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    safe_rename(add_v, "TV_AddInput")
    pos(add_v, -850, 760)

    vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSizeXY")
    if not vsize:
        vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(vsize, "TV_VSizeXY")
    pos(vsize, -620, 720)

    gt_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_in, "TV_HasInput")
    pos(gt_in, -400, 720)
    set_val(gt_in, "B", str(INPUT_EPS))

    brk = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector")
    safe_rename(brk, "TV_BreakIn")
    pos(brk, -620, 880)

    input_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2")
    safe_rename(input_yaw, "TV_InputYaw")
    pos(input_yaw, -400, 880)

    # --- actor yaw ---
    get_rot = ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation")
    safe_rename(get_rot, "TV_GetActorRot")
    pos(get_rot, -1100, 1000)

    brk_rot = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakRotator")
    safe_rename(brk_rot, "TV_BreakRot")
    pos(brk_rot, -850, 1000)

    # Delta = NormalizeAxis(InputYaw - ActorYaw)
    sub = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble")
    if not sub:
        sub = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Subtract_FloatFloat")
    safe_rename(sub, "TV_SubYaw")
    pos(sub, -150, 880)

    norm = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm, "TV_NormAxis")
    pos(norm, 80, 880)

    # Select delta: has input ? norm : 0
    sel = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    safe_rename(sel, "TV_SelDelta")
    pos(sel, 300, 800)
    set_val(sel, "B", "0.0")

    abs_f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs")
    safe_rename(abs_f, "TV_Abs")
    pos(abs_f, 520, 800)

    get_th90 = ed.add_get_member_variable_node("TurnAngle90")
    safe_rename(get_th90, "TV_GetTh90")
    pos(get_th90, 520, 960)
    get_th180 = ed.add_get_member_variable_node("TurnAngle180")
    safe_rename(get_th180, "TV_GetTh180")
    pos(get_th180, 520, 1040)

    ge90 = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(ge90, "TV_Ge90")
    pos(ge90, 740, 860)
    ge180 = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(ge180, "TV_Ge180")
    pos(ge180, 740, 980)
    lt180 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    safe_rename(lt180, "TV_Lt180")
    pos(lt180, 740, 920)

    and90 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and90, "TV_And90")
    pos(and90, 960, 880)

    # final flags also require has input
    and90f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and90f, "TV_And90F")
    pos(and90f, 1160, 860)
    and180f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and180f, "TV_And180F")
    pos(and180f, 1160, 980)

    lt0 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    safe_rename(lt0, "TV_Lt0")
    pos(lt0, 520, 700)
    set_val(lt0, "B", "0.0")

    and_left = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_left, "TV_AndLeft")
    pos(and_left, 740, 700)

    # Branch + sets
    br = ed.add_branch_node()
    safe_rename(br, "TV_BrInput")
    pos(br, 300, 600)

    set_delta = ed.add_set_member_variable_node("MoveYawDelta")
    safe_rename(set_delta, "TV_SetDelta")
    pos(set_delta, 1400, 560)
    set_abs = ed.add_set_member_variable_node("AbsMoveYawDelta")
    safe_rename(set_abs, "TV_SetAbs")
    pos(set_abs, 1650, 560)
    set_left = ed.add_set_member_variable_node("bTurnLeft")
    safe_rename(set_left, "TV_SetLeft")
    pos(set_left, 1900, 560)
    set_t90 = ed.add_set_member_variable_node("bWantsTurn90")
    safe_rename(set_t90, "TV_SetT90")
    pos(set_t90, 2150, 560)
    set_t180 = ed.add_set_member_variable_node("bWantsTurn180")
    safe_rename(set_t180, "TV_SetT180")
    pos(set_t180, 2400, 560)

    set_actor_yaw = ed.add_set_member_variable_node("ActorYaw")
    safe_rename(set_actor_yaw, "TV_SetActorYaw")
    pos(set_actor_yaw, 1400, 720)
    set_input_yaw = ed.add_set_member_variable_node("InputYaw")
    safe_rename(set_input_yaw, "TV_SetInputYaw")
    pos(set_input_yaw, 1650, 720)

    # clear path
    lit_f = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    safe_rename(lit_f, "TV_LitF")
    pos(lit_f, 1400, 900)
    set_val(lit_f, "Value", "false")
    lit_0 = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralDouble")
    if not lit_0:
        lit_0 = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralFloat")
    safe_rename(lit_0, "TV_Lit0")
    pos(lit_0, 1400, 980)
    set_val(lit_0, "Value", "0.0")

    clr_t90 = ed.add_set_member_variable_node("bWantsTurn90")
    safe_rename(clr_t90, "TV_ClrT90")
    pos(clr_t90, 1650, 900)
    clr_t180 = ed.add_set_member_variable_node("bWantsTurn180")
    safe_rename(clr_t180, "TV_ClrT180")
    pos(clr_t180, 1900, 900)
    clr_delta = ed.add_set_member_variable_node("MoveYawDelta")
    safe_rename(clr_delta, "TV_ClrDelta")
    pos(clr_delta, 2150, 900)
    clr_abs = ed.add_set_member_variable_node("AbsMoveYawDelta")
    safe_rename(clr_abs, "TV_ClrAbs")
    pos(clr_abs, 2400, 900)

    links = []
    # data
    links.append(("p->pend", connect(pawn, bel.find_self_pin(get_pending) or pin_in(get_pending, "self"))))
    links.append(("p->last", connect(pawn, bel.find_self_pin(get_last) or pin_in(get_last, "self"))))
    links.append(("p->rot", connect(pawn, bel.find_self_pin(get_rot) or pin_in(get_rot, "self"))))
    links.append(("pend->add", connect(pin_out(get_pending, "ReturnValue"), pin_in(add_v, "A"))))
    links.append(("last->add", connect(pin_out(get_last, "ReturnValue"), pin_in(add_v, "B"))))
    links.append(("add->size", connect(pin_out(add_v, "ReturnValue"), pin_in(vsize, "A"))))
    links.append(("size->gt", connect(pin_out(vsize, "ReturnValue"), pin_in(gt_in, "A"))))
    links.append(("add->brk", connect(pin_out(add_v, "ReturnValue"), pin_in(brk, "InVec") or pin_in(brk, "A"))))
    links.append(("Y->atan", connect(pin_out(brk, "Y"), pin_in(input_yaw, "Y") or pin_in(input_yaw, "A"))))
    links.append(("X->atan", connect(pin_out(brk, "X"), pin_in(input_yaw, "X") or pin_in(input_yaw, "B"))))
    links.append(("rot->brk", connect(pin_out(get_rot, "ReturnValue"), pin_in(brk_rot, "InRot") or pin_in(brk_rot, "A"))))
    # Input - Actor
    links.append(("in->subA", connect(pin_out(input_yaw, "ReturnValue"), pin_in(sub, "A"))))
    links.append(("yaw->subB", connect(pin_out(brk_rot, "Yaw"), pin_in(sub, "B"))))
    links.append(("sub->norm", connect(pin_out(sub, "ReturnValue"), pin_in(norm, "Angle"))))
    links.append(("norm->selA", connect(pin_out(norm, "ReturnValue"), pin_in(sel, "A"))))
    links.append(("has->sel", connect(pin_out(gt_in, "ReturnValue"), pin_in(sel, "bPickA"))))
    links.append(("sel->abs", connect(pin_out(sel, "ReturnValue"), pin_in(abs_f, "A"))))

    links.append(("abs->ge90", connect(pin_out(abs_f, "ReturnValue"), pin_in(ge90, "A"))))
    links.append(("th90->ge90", connect(pin_out(get_th90), pin_in(ge90, "B"))))
    links.append(("abs->ge180", connect(pin_out(abs_f, "ReturnValue"), pin_in(ge180, "A"))))
    links.append(("th180->ge180", connect(pin_out(get_th180), pin_in(ge180, "B"))))
    links.append(("abs->lt180", connect(pin_out(abs_f, "ReturnValue"), pin_in(lt180, "A"))))
    links.append(("th180->lt180", connect(pin_out(get_th180), pin_in(lt180, "B"))))
    links.append(("ge90->and90", connect(pin_out(ge90, "ReturnValue"), pin_in(and90, "A"))))
    links.append(("lt180->and90", connect(pin_out(lt180, "ReturnValue"), pin_in(and90, "B"))))
    links.append(("and90->f", connect(pin_out(and90, "ReturnValue"), pin_in(and90f, "A"))))
    links.append(("has->f90", connect(pin_out(gt_in, "ReturnValue"), pin_in(and90f, "B"))))
    links.append(("ge180->f180", connect(pin_out(ge180, "ReturnValue"), pin_in(and180f, "A"))))
    links.append(("has->f180", connect(pin_out(gt_in, "ReturnValue"), pin_in(and180f, "B"))))
    links.append(("sel->lt0", connect(pin_out(sel, "ReturnValue"), pin_in(lt0, "A"))))
    links.append(("lt0->left", connect(pin_out(lt0, "ReturnValue"), pin_in(and_left, "A"))))
    links.append(("has->left", connect(pin_out(gt_in, "ReturnValue"), pin_in(and_left, "B"))))

    # exec: SI -> Br; both ends -> OldSeq
    links.append(("SI->Br", connect(si_then, bel.find_execute_pin(br))))
    links.append(("has->Br", connect(pin_out(gt_in, "ReturnValue"), bel.find_condition_pin(br))))

    # TRUE
    links.append(("T->delta", connect(bel.find_then_pin(br), bel.find_execute_pin(set_delta))))
    links.append(("sel->delta", connect(pin_out(sel, "ReturnValue"), pin_in(set_delta, "MoveYawDelta"))))
    links.append(("d->abs", connect(bel.find_then_pin(set_delta), bel.find_execute_pin(set_abs))))
    links.append(("absv->s", connect(pin_out(abs_f, "ReturnValue"), pin_in(set_abs, "AbsMoveYawDelta"))))
    links.append(("a->left", connect(bel.find_then_pin(set_abs), bel.find_execute_pin(set_left))))
    links.append(("leftv->s", connect(pin_out(and_left, "ReturnValue"), pin_in(set_left, "bTurnLeft"))))
    links.append(("l->t90", connect(bel.find_then_pin(set_left), bel.find_execute_pin(set_t90))))
    links.append(("t90v->s", connect(pin_out(and90f, "ReturnValue"), pin_in(set_t90, "bWantsTurn90"))))
    links.append(("t90->t180", connect(bel.find_then_pin(set_t90), bel.find_execute_pin(set_t180))))
    links.append(("t180v->s", connect(pin_out(and180f, "ReturnValue"), pin_in(set_t180, "bWantsTurn180"))))
    # debug yaw sets then old
    links.append(("t180->ay", connect(bel.find_then_pin(set_t180), bel.find_execute_pin(set_actor_yaw))))
    links.append(("yaw->ay", connect(pin_out(brk_rot, "Yaw"), pin_in(set_actor_yaw, "ActorYaw"))))
    links.append(("ay->iy", connect(bel.find_then_pin(set_actor_yaw), bel.find_execute_pin(set_input_yaw))))
    links.append(("in->iy", connect(pin_out(input_yaw, "ReturnValue"), pin_in(set_input_yaw, "InputYaw"))))
    links.append(("iy->old", connect(bel.find_then_pin(set_input_yaw), bel.find_execute_pin(old_seq))))

    # FALSE clear -> old
    links.append(("E->c90", connect(bel.find_else_pin(br), bel.find_execute_pin(clr_t90))))
    links.append(("f->c90", connect(pin_out(lit_f, "ReturnValue"), pin_in(clr_t90, "bWantsTurn90"))))
    links.append(("c90->c180", connect(bel.find_then_pin(clr_t90), bel.find_execute_pin(clr_t180))))
    links.append(("f->c180", connect(pin_out(lit_f, "ReturnValue"), pin_in(clr_t180, "bWantsTurn180"))))
    links.append(("c180->cd", connect(bel.find_then_pin(clr_t180), bel.find_execute_pin(clr_delta))))
    links.append(("0->cd", connect(pin_out(lit_0, "ReturnValue"), pin_in(clr_delta, "MoveYawDelta"))))
    links.append(("cd->ca", connect(bel.find_then_pin(clr_delta), bel.find_execute_pin(clr_abs))))
    links.append(("0->ca", connect(pin_out(lit_0, "ReturnValue"), pin_in(clr_abs, "AbsMoveYawDelta"))))
    links.append(("ca->old", connect(bel.find_then_pin(clr_abs), bel.find_execute_pin(old_seq))))

    try:
        ed.add_comment_node(
            "TurnFace: MoveYawDelta = InputYaw - ActorYaw\n"
            "bWantsTurn90/180 while |delta| large (stays true until aligned)\n"
            "SM: Walk/Run -> Turn* using these bools",
            unreal.IntPoint(-1100, 560),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    # verify critical
    for n, pname in ((gt_in, "B"), (sel, "B"), (norm, "Angle")):
        p = pin_in(n, pname)
        try:
            log(f"{n.get_name()}.{pname} val={p.get_pin_value() if p else None} "
                f"links={len(list(p.list_connected_pins() or [])) if p else 0}")
        except Exception:
            pass

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)

    readme = """Turn variables — Actor facing vs move input

FORMULA
  InputYaw  = direction of WASD move input (world XY)
  ActorYaw  = character actor rotation yaw
  MoveYawDelta = NormalizeAxis(InputYaw - ActorYaw)
  AbsMoveYawDelta = |MoveYawDelta|

  bWantsTurn180 = hasInput AND Abs >= TurnAngle180   (default 135)
  bWantsTurn90  = hasInput AND Abs >= TurnAngle90 AND Abs < TurnAngle180  (60..135)
  bTurnLeft     = hasInput AND MoveYawDelta < 0

WHY BETTER
  Old: previous input vs current input (1-frame pulse, easy to miss)
  New: body facing vs wanted move dir — stays true until character turns enough

SM (you wire)
  Walk/Run -> Turn180L : bWantsTurn180 AND bTurnLeft
  Walk/Run -> Turn180R : bWantsTurn180 AND NOT bTurnLeft
  Walk/Run -> Turn90L  : bWantsTurn90 AND bTurnLeft
  Walk/Run -> Turn90R  : bWantsTurn90 AND NOT bTurnLeft
  Turn* -> Walk/Run    : Automatic Rule (sequence end)

DEBUG (optional watch in PIE)
  ActorYaw, InputYaw, MoveYawDelta, AbsMoveYawDelta, bWantsTurn180

Tune: TurnAngle90 / TurnAngle180 on AnimBP defaults.
"""
    path = unreal.Paths.project_content_dir() + "Python/TURN_VARS_README.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(readme)
    log("done")


if __name__ == "__main__":
    run()
