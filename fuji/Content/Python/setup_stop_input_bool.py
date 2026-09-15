# -*- coding: utf-8 -*-
"""
AnimBP only: bool bStopInput for state machine.
  bStopInput = true  when player has NO WASD / move input
  bStopInput = false when holding move input

Computed from Pawn GetPending/LastMovementInputVector (no Character cast, no montages).
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
INPUT_EPS = 0.1
BOOL_NAME = "bStopInput"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[StopInput] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(p)
    return a


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
    except Exception as e:
        log(f"set_val: {e}")
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


def ensure_bool(bp, name):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name(name), pin)
        log(f"add var {name}")
    except Exception as e:
        log(f"var {name}: {e}")


def purge_si(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("SI_") or "bStopInput" in title and name.startswith("SI_"):
                    kill.append(n)
                if "StopInput condition" in title or name.startswith("SI_DEL_"):
                    kill.append(n)
                if name.startswith("LC_") or name.startswith("LC_DEL_"):
                    kill.append(n)
            except Exception:
                pass
    # also SI sets of bStopInput
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name().startswith("SI_"):
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
            n.rename(f"SI_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")


def find_or_add_update(abp, ed, graph):
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() != graph:
                continue
            title = str(bel.get_node_title(n))
            if "Blueprint Update Animation" in title or "更新动画" in title:
                log(f"found Update: {n.get_name()} ({title})")
                return n
        except Exception:
            pass
    try:
        n = bel.add_event_override(
            abp, "BlueprintUpdateAnimation", unreal.IntPoint(-1600, -200)
        )
        log(f"added Update: {n}")
        return n
    except Exception as e:
        log(f"add_event_override: {e}")
    return None


def run():
    log("start")
    abp = load(ABP)
    ensure_bool(abp, BOOL_NAME)
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass

    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()
    purge_si(ed, graph)

    upd = find_or_add_update(abp, ed, graph)
    if not upd:
        raise RuntimeError("no BlueprintUpdateAnimation")
    pos(upd, -1600, -200)

    then = bel.find_then_pin(upd)
    old = list(then.list_connected_pins() or [])
    then.break_pin_links()

    try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
    safe_rename(try_get, "SI_TryGet")
    pos(try_get, -1350, 0)

    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "SI_GetPending")
    pos(get_pending, -1100, -40)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "SI_GetLast")
    pos(get_last, -1100, 100)

    v_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_p, "SI_VPending")
    pos(v_p, -850, -40)
    v_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_l, "SI_VLast")
    pos(v_l, -850, 100)

    gt_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_p, "SI_GtP")
    pos(gt_p, -600, -40)
    set_val(gt_p, "B", str(INPUT_EPS))
    gt_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_l, "SI_GtL")
    pos(gt_l, -600, 100)
    set_val(gt_l, "B", str(INPUT_EPS))

    or_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_in, "SI_OrHasInput")
    pos(or_in, -380, 30)

    not_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_in, "SI_Not")
    pos(not_in, -180, 30)

    set_stop = ed.add_set_member_variable_node(BOOL_NAME)
    safe_rename(set_stop, "SI_SetStop")
    pos(set_stop, 50, -80)

    links = []
    # exec: Update -> Set bStopInput -> previous chain
    links.append(("upd->set", connect(then, bel.find_execute_pin(set_stop))))

    # self pins for pawn functions
    pawn_out = pin_out(try_get, "ReturnValue")
    links.append(
        (
            "pawn->pend",
            connect(pawn_out, bel.find_self_pin(get_pending) or pin_in(get_pending, "self")),
        )
    )
    links.append(
        (
            "pawn->last",
            connect(pawn_out, bel.find_self_pin(get_last) or pin_in(get_last, "self")),
        )
    )

    links.append(("pend->v", connect(pin_out(get_pending, "ReturnValue"), pin_in(v_p, "A"))))
    links.append(("last->v", connect(pin_out(get_last, "ReturnValue"), pin_in(v_l, "A"))))
    links.append(("vp->gt", connect(pin_out(v_p, "ReturnValue"), pin_in(gt_p, "A"))))
    links.append(("vl->gt", connect(pin_out(v_l, "ReturnValue"), pin_in(gt_l, "A"))))
    links.append(("gtp->or", connect(pin_out(gt_p, "ReturnValue"), pin_in(or_in, "A"))))
    links.append(("gtl->or", connect(pin_out(gt_l, "ReturnValue"), pin_in(or_in, "B"))))
    links.append(("or->not", connect(pin_out(or_in, "ReturnValue"), pin_in(not_in, "A"))))
    links.append(("not->set", connect(pin_out(not_in, "ReturnValue"), pin_in(set_stop, BOOL_NAME))))

    if old:
        for p in old:
            try:
                on = p.get_owning_node()
                if on and not on.get_name().startswith("SI_"):
                    links.append(("set->old", connect(bel.find_then_pin(set_stop), p)))
                    break
            except Exception:
                pass

    try:
        ed.add_comment_node(
            "StopInput condition (for SM)\n"
            "bStopInput = TRUE when NO WASD/move input\n"
            "Locomotion -> Stop: bStopInput\n"
            "Idle -> Start: NOT bStopInput",
            unreal.IntPoint(-1600, -400),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    save(ABP)

    cdo = unreal.get_default_object(abp.generated_class())
    try:
        cdo.set_editor_property(BOOL_NAME, True)
        log(f"CDO {BOOL_NAME}=True (idle default)")
    except Exception as e:
        log(f"CDO: {e}")
    save(ABP)
    log("done — SM use: bStopInput")


if __name__ == "__main__":
    run()
else:
    run()
