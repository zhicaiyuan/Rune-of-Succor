# -*- coding: utf-8 -*-
"""
Start/Stop by WASD input (not velocity):
  hasInput = |PendingMoveInput| OR |LastMoveInput| > 0.1
  Start when hasInput rises, Stop when hasInput falls.
  Walk/Run still by MaxWalkSpeed <= 300 (Alt walk).

Keeps WW_* Alt-walk chain: Tick -> WW_SetBool -> WW_SetSpd -> SS driver.
Also sets bHasMoveInput for AnimBP state-machine rules.
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
MONTAGES = {
    "SS_WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "SS_WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "SS_RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "SS_RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}
INPUT_EPS = 0.1
WALK_MAX = 300.0

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[SSInput] {m}")


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
        log(f"set {node.get_name()}.{pin_name}={value}")
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


def ensure_vars(bp):
    for name in MONTAGES:
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception:
            pass
    for name in ("SS_WasMoving", "bHasMoveInput"):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    for prop, path in MONTAGES.items():
        try:
            cdo.set_editor_property(prop, load(path))
        except Exception:
            pass
    for bname in ("SS_WasMoving", "bHasMoveInput"):
        try:
            cdo.set_editor_property(bname, False)
        except Exception:
            pass
    save(CHAR)


def collect_exec_cluster(start_pin):
    """BFS along exec pins from start_pin's owning node."""
    if not start_pin:
        return []
    try:
        start = start_pin.get_owning_node()
    except Exception:
        return []
    seen = set()
    out = []
    stack = [start]
    while stack:
        n = stack.pop()
        i = id(n)
        if i in seen:
            continue
        seen.add(i)
        # never delete Alt-walk helpers
        try:
            if n.get_name().startswith("WW_"):
                continue
        except Exception:
            pass
        out.append(n)
        for pn in bel.list_all_pins(n) or []:
            try:
                # follow exec outs
                d = str(pn.direction)
                if "Output" in d or d.endswith("EGPD_Output"):
                    for linked in pn.list_connected_pins() or []:
                        on = linked.get_owning_node()
                        if on and not on.get_name().startswith("WW_"):
                            stack.append(on)
            except Exception:
                pass
    return out


def collect_pure_deps(exec_nodes, graph):
    """Also kill pure nodes feeding the SS cluster (GetVelocity, compares, montage gets)."""
    kill = list(exec_nodes)
    titles_kill = (
        "GetVelocity",
        "GetLastMovementInputVector",
        "GetPendingMovementInputVector",
        "Vector Length",
        "float > float",
        "float <= float",
        "NOT Boolean",
        "OR Boolean",
        "MakeLiteralBool",
        "PlayAnimMontage",
        "获得SS_",
        "设置SS_",
        "获得bHasMoveInput",
        "设置bHasMoveInput",
        "获得MaxWalkSpeed",
    )
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
                if n.get_name().startswith("WW_"):
                    continue
                title = str(bel.get_node_title(n))
                name = n.get_name()
                if name.startswith("SS_") or any(t in title for t in titles_kill):
                    kill.append(n)
                if "START/STOP" in title or "WASD input" in title:
                    kill.append(n)
                # CharacterMovement get only if NOT WW and used for MaxWalkSpeed in SS
                if "获得CharacterMovement" in title or "Get CharacterMovement" in title:
                    if not name.startswith("WW_"):
                        kill.append(n)
            except Exception:
                pass
    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    return uniq


def find_attach_pin(graph):
    """Prefer WW_SetSpd.then; else Tick.then (skipping WW)."""
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
                tp = bel.find_then_pin(n)
                log("attach after WW_SetSpd")
                return tp
        except Exception:
            pass
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
                log("attach after Tick (no WW_SetSpd)")
                return bel.find_then_pin(n)
        except Exception:
            pass
    return None


def purge_ss(ed, graph, attach_pin):
    old_targets = []
    if attach_pin:
        old_targets = list(attach_pin.list_connected_pins() or [])
        # If attach is WW_SetSpd, only purge cluster from its then target
        cluster = []
        for p in old_targets:
            cluster.extend(collect_exec_cluster(p))
        kill = collect_pure_deps(cluster, graph)
    else:
        kill = collect_pure_deps([], graph)

    # Also kill orphaned PlayAnimMontage / SS vars
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if n.get_outer() == graph and "PlayAnimMontage" in str(bel.get_node_title(n)):
                if not n.get_name().startswith("WW_"):
                    kill.append(n)
        except Exception:
            pass

    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen and not n.get_name().startswith("WW_"):
            seen.add(i)
            uniq.append(n)

    if attach_pin:
        attach_pin.break_pin_links()

    for i, n in enumerate(uniq):
        try:
            n.rename(f"SS_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)} SS nodes")
    else:
        log("purge: nothing")


def wire(bp):
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()
    attach = find_attach_pin(graph)
    if not attach:
        raise RuntimeError("no Tick/WW_SetSpd attach pin")

    purge_ss(ed, graph, attach)

    # --- input size ---
    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "SS_GetPending")
    pos(get_pending, -1300, 1600)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "SS_GetLast")
    pos(get_last, -1300, 1720)

    v_pending = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_pending, "SS_VPending")
    pos(v_pending, -1050, 1600)

    v_last = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_last, "SS_VLast")
    pos(v_last, -1050, 1720)

    gt_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_p, "SS_GtPending")
    pos(gt_p, -800, 1600)
    set_val(gt_p, "B", str(INPUT_EPS))

    gt_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_l, "SS_GtLast")
    pos(gt_l, -800, 1720)
    set_val(gt_l, "B", str(INPUT_EPS))

    or_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_in, "SS_OrInput")
    pos(or_in, -600, 1660)

    # walk/run
    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    safe_rename(get_cmc, "SS_CMC")
    pos(get_cmc, -1300, 1900)
    get_max = ed.add_get_member_variable_node(
        "MaxWalkSpeed", "/Script/Engine.CharacterMovementComponent"
    )
    safe_rename(get_max, "SS_MaxSpd")
    pos(get_max, -1050, 1900)
    le = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    safe_rename(le, "SS_IsWalk")
    pos(le, -800, 1900)
    set_val(le, "B", str(WALK_MAX))

    not_was = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_was, "SS_NotWas")
    pos(not_was, -400, 1500)

    lit_t = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    safe_rename(lit_t, "SS_LitT")
    pos(lit_t, 550, 1400)
    set_val(lit_t, "Value", "true")

    lit_f = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    safe_rename(lit_f, "SS_LitF")
    pos(lit_f, 550, 1750)
    set_val(lit_f, "Value", "false")

    set_has = ed.add_set_member_variable_node("bHasMoveInput")
    safe_rename(set_has, "SS_SetHasInput")
    pos(set_has, -400, 1660)

    br_mv = ed.add_branch_node()
    safe_rename(br_mv, "SS_BrHasInput")
    pos(br_mv, -150, 1660)

    br_start = ed.add_branch_node()
    safe_rename(br_start, "SS_BrStart")
    pos(br_start, 80, 1500)

    br_stop = ed.add_branch_node()
    safe_rename(br_stop, "SS_BrStop")
    pos(br_stop, 80, 1800)

    br_w1 = ed.add_branch_node()
    safe_rename(br_w1, "SS_BrWalkStart")
    pos(br_w1, 320, 1450)

    br_w2 = ed.add_branch_node()
    safe_rename(br_w2, "SS_BrWalkStop")
    pos(br_w2, 320, 1800)

    play_ws = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    safe_rename(play_ws, "SS_PlayWalkStart")
    pos(play_ws, 600, 1350)
    play_rs = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    safe_rename(play_rs, "SS_PlayRunStart")
    pos(play_rs, 600, 1520)
    play_wst = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    safe_rename(play_wst, "SS_PlayWalkStop")
    pos(play_wst, 600, 1720)
    play_rst = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    safe_rename(play_rst, "SS_PlayRunStop")
    pos(play_rst, 600, 1880)

    get_was = ed.add_get_member_variable_node("SS_WasMoving")
    safe_rename(get_was, "SS_GetWas")
    pos(get_was, -400, 1400)

    set_ws = ed.add_set_member_variable_node("SS_WasMoving")
    safe_rename(set_ws, "SS_SetWas_WS")
    pos(set_ws, 900, 1350)
    set_rs = ed.add_set_member_variable_node("SS_WasMoving")
    safe_rename(set_rs, "SS_SetWas_RS")
    pos(set_rs, 900, 1520)
    set_wst = ed.add_set_member_variable_node("SS_WasMoving")
    safe_rename(set_wst, "SS_SetWas_WST")
    pos(set_wst, 900, 1720)
    set_rst = ed.add_set_member_variable_node("SS_WasMoving")
    safe_rename(set_rst, "SS_SetWas_RST")
    pos(set_rst, 900, 1880)

    m_ws = ed.add_get_member_variable_node("SS_WalkStart")
    m_rs = ed.add_get_member_variable_node("SS_RunStart")
    m_wst = ed.add_get_member_variable_node("SS_WalkStop")
    m_rst = ed.add_get_member_variable_node("SS_RunStop")
    pos(m_ws, 450, 1280)
    pos(m_rs, 450, 1520)
    pos(m_wst, 450, 1720)
    pos(m_rst, 450, 1880)

    links = []
    # data: pending/last input
    links.append(("pend->v", connect(pin_out(get_pending, "ReturnValue"), pin_in(v_pending, "A"))))
    links.append(("last->v", connect(pin_out(get_last, "ReturnValue"), pin_in(v_last, "A"))))
    links.append(("vp->gt", connect(pin_out(v_pending, "ReturnValue"), pin_in(gt_p, "A"))))
    links.append(("vl->gt", connect(pin_out(v_last, "ReturnValue"), pin_in(gt_l, "A"))))
    links.append(("gtp->or", connect(pin_out(gt_p, "ReturnValue"), pin_in(or_in, "A"))))
    links.append(("gtl->or", connect(pin_out(gt_l, "ReturnValue"), pin_in(or_in, "B"))))

    # MaxWalkSpeed
    links.append(
        ("cmc->max", connect(pin_out(get_cmc), bel.find_self_pin(get_max) or pin_in(get_max, "self")))
    )
    links.append(("max->le", connect(pin_out(get_max), pin_in(le, "A"))))

    # exec: attach -> set bHasMoveInput -> branch
    links.append(("attach->setHas", connect(attach, bel.find_execute_pin(set_has))))
    links.append(("or->has", connect(pin_out(or_in, "ReturnValue"), pin_in(set_has, "bHasMoveInput"))))
    links.append(("setHas->br", connect(bel.find_then_pin(set_has), bel.find_execute_pin(br_mv))))
    links.append(("or->brCond", connect(pin_out(or_in, "ReturnValue"), bel.find_condition_pin(br_mv))))

    # START edge: has input && !was
    links.append(("brT->start", connect(bel.find_then_pin(br_mv), bel.find_execute_pin(br_start))))
    links.append(("was->not", connect(pin_out(get_was), pin_in(not_was, "A"))))
    links.append(("not->start", connect(pin_out(not_was, "ReturnValue"), bel.find_condition_pin(br_start))))
    links.append(("startT->w1", connect(bel.find_then_pin(br_start), bel.find_execute_pin(br_w1))))
    links.append(("le->w1", connect(pin_out(le, "ReturnValue"), bel.find_condition_pin(br_w1))))
    links.append(("w1T->pws", connect(bel.find_then_pin(br_w1), bel.find_execute_pin(play_ws))))
    links.append(("w1E->prs", connect(bel.find_else_pin(br_w1), bel.find_execute_pin(play_rs))))
    links.append(("pws->set", connect(bel.find_then_pin(play_ws), bel.find_execute_pin(set_ws))))
    links.append(("prs->set", connect(bel.find_then_pin(play_rs), bel.find_execute_pin(set_rs))))
    links.append(("true->ws", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_ws, "SS_WasMoving"))))
    links.append(("true->rs", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_rs, "SS_WasMoving"))))

    # STOP edge: no input && was
    links.append(("brE->stop", connect(bel.find_else_pin(br_mv), bel.find_execute_pin(br_stop))))
    links.append(("was->stop", connect(pin_out(get_was), bel.find_condition_pin(br_stop))))
    links.append(("stopT->w2", connect(bel.find_then_pin(br_stop), bel.find_execute_pin(br_w2))))
    links.append(("le->w2", connect(pin_out(le, "ReturnValue"), bel.find_condition_pin(br_w2))))
    links.append(("w2T->pwst", connect(bel.find_then_pin(br_w2), bel.find_execute_pin(play_wst))))
    links.append(("w2E->prst", connect(bel.find_else_pin(br_w2), bel.find_execute_pin(play_rst))))
    links.append(("pwst->set", connect(bel.find_then_pin(play_wst), bel.find_execute_pin(set_wst))))
    links.append(("prst->set", connect(bel.find_then_pin(play_rst), bel.find_execute_pin(set_rst))))
    links.append(("false->wst", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_wst, "SS_WasMoving"))))
    links.append(("false->rst", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_rst, "SS_WasMoving"))))

    for getter, player in (
        (m_ws, play_ws),
        (m_rs, play_rs),
        (m_wst, play_wst),
        (m_rst, play_rst),
    ):
        links.append((f"m->{player.get_name()}", connect(pin_out(getter), pin_in(player, "AnimMontage"))))

    try:
        ed.add_comment_node(
            "START/STOP by WASD input (not Speed)\n"
            "hasInput = Pending OR Last move input > 0.1\n"
            "Stop plays on release; Walk if MaxWalkSpeed<=300\n"
            "bHasMoveInput exposed for AnimBP SM rules",
            unreal.IntPoint(-1400, 1450),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    save(CHAR)


def run():
    log("start")
    bp = load(CHAR)
    ensure_vars(bp)
    wire(bp)
    # update rules text for SM users
    try:
        rules = (
            "ABP_StrafeLocomotion Start/Stop — use INPUT not Speed for Stop:\n\n"
            "Copy from character each Update:\n"
            "  bHasMoveInput, bWantsWalk (or MaxWalkSpeed)\n\n"
            "Idle -> WalkStart:  bHasMoveInput AND bWantsWalk\n"
            "Idle -> RunStart:   bHasMoveInput AND NOT bWantsWalk\n"
            "WalkStart/RunStart -> Locomotion: Automatic (sequence end)\n"
            "Locomotion -> WalkStop: NOT bHasMoveInput AND bWantsWalk\n"
            "Locomotion -> RunStop:  NOT bHasMoveInput AND NOT bWantsWalk\n"
            "WalkStop/RunStop -> Idle: Automatic (sequence end)\n"
            "During Stop, if bHasMoveInput again -> back to Start (interrupt)\n"
        )
        path = unreal.Paths.project_content_dir() + "Python/START_STOP_TRANSITION_RULES.txt"
        with open(path, "w", encoding="utf-8") as f:
            f.write(rules)
        log("updated START_STOP_TRANSITION_RULES.txt")
    except Exception as e:
        log(f"rules file: {e}")
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
