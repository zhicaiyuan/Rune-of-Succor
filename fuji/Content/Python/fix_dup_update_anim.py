# -*- coding: utf-8 -*-
"""
Remove duplicate 事件BlueprintUpdateAnimation; keep original; wire bStopInput on it.
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
BOOL_NAME = "bStopInput"
INPUT_EPS = 0.1

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixDup] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


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


def is_update_event(n):
    try:
        title = str(bel.get_node_title(n)).replace(" ", "")
        # 事件BlueprintUpdateAnimation (UE CN, no spaces)
        return "BlueprintUpdateAnimation" in title
    except Exception:
        return False


def purge_si(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableSet,
        unreal.K2Node_VariableGet,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("SI_") or name.startswith("SI_DEL_") or "StopInput" in title:
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
        log(f"purged SI {len(uniq)}")


def wire_stop_on(ed, graph, upd):
    then = bel.find_then_pin(upd)
    old = list(then.list_connected_pins() or [])
    then.break_pin_links()

    try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
    safe_rename(try_get, "SI_TryGet")
    pos(try_get, -1400, 400)

    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "SI_GetPending")
    pos(get_pending, -1150, 360)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "SI_GetLast")
    pos(get_last, -1150, 500)

    v_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_p, "SI_VPending")
    pos(v_p, -900, 360)
    v_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_l, "SI_VLast")
    pos(v_l, -900, 500)

    gt_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_p, "SI_GtP")
    pos(gt_p, -650, 360)
    set_val(gt_p, "B", str(INPUT_EPS))
    gt_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_l, "SI_GtL")
    pos(gt_l, -650, 500)
    set_val(gt_l, "B", str(INPUT_EPS))

    or_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_in, "SI_OrHasInput")
    pos(or_in, -430, 420)

    not_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_in, "SI_Not")
    pos(not_in, -230, 420)

    set_stop = ed.add_set_member_variable_node(BOOL_NAME)
    safe_rename(set_stop, "SI_SetStop")
    pos(set_stop, 0, 280)

    links = []
    links.append(("upd->set", connect(then, bel.find_execute_pin(set_stop))))
    pawn_out = pin_out(try_get, "ReturnValue")
    links.append(("pawn->pend", connect(pawn_out, bel.find_self_pin(get_pending) or pin_in(get_pending, "self"))))
    links.append(("pawn->last", connect(pawn_out, bel.find_self_pin(get_last) or pin_in(get_last, "self"))))
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
                if on and not str(on.get_name()).startswith("SI_"):
                    links.append(("set->old", connect(bel.find_then_pin(set_stop), p)))
                    log(f"reattach old -> {on.get_name()}")
                    break
            except Exception:
                pass

    try:
        ed.add_comment_node(
            "bStopInput = TRUE when NO WASD\nSM Stop transition: bStopInput",
            unreal.IntPoint(-1400, 200),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")


def run():
    log("start")
    abp = load(ABP)
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(abp, unreal.Name(BOOL_NAME), pin)
    except Exception:
        pass

    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    updates = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and is_update_event(n):
                updates.append(n)
                log(f"Update: {n.get_name()} title={bel.get_node_title(n)}")
        except Exception:
            pass

    if not updates:
        raise RuntimeError("no BlueprintUpdateAnimation found")

    # Keep K2Node_Event_0 if present, else first
    keep = None
    for u in updates:
        if u.get_name() == "K2Node_Event_0":
            keep = u
            break
    if keep is None:
        keep = updates[0]
    drop = [u for u in updates if u != keep]
    log(f"KEEP {keep.get_name()}, drop {[d.get_name() for d in drop]}")

    for u in drop:
        try:
            bel.find_then_pin(u).break_pin_links()
        except Exception:
            pass

    purge_si(ed, graph)

    if drop:
        for i, u in enumerate(drop):
            try:
                u.rename(f"DUP_UPDATE_DEL_{i}")
            except Exception:
                pass
        ed.remove_nodes(drop)
        log(f"removed {len(drop)} duplicates")

    wire_stop_on(ed, graph, keep)

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")

    left = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and is_update_event(n):
                left.append(n.get_name())
        except Exception:
            pass
    log(f"Update count after={len(left)} {left}")
    if len(left) != 1:
        log("WARN: still not exactly one Update event")
    save(ABP)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
