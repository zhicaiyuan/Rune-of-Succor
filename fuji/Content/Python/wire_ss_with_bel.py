# -*- coding: utf-8 -*-
"""
Start/Stop locomotion via UE 5.8 BlueprintGraphEditor APIs:
Character Event Tick edge-detect -> PlayAnimMontage (DefaultSlot).
Also keeps BS / FootIK / montage soft refs.
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
BS_GRAPH = f"{OUT}/BS_SwordStrafe2D"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
RTG = f"{OUT}/SwordRTG"

MONTAGES = {
    "SS_WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "SS_WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "SS_RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "SS_RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[SSBel] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def pos(ed_or_bel, node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        try:
            node.node_pos_x = int(x)
            node.node_pos_y = int(y)
        except Exception:
            pass


def connect(a, b):
    if not a or not b:
        return False
    try:
        if hasattr(a, "try_create_connection"):
            return bool(a.try_create_connection(b))
    except Exception as exc:
        log(f"connect a->b: {exc}")
    try:
        if hasattr(b, "try_create_connection"):
            return bool(b.try_create_connection(a))
    except Exception as exc:
        log(f"connect b->a: {exc}")
    return False


def pin_in(node, name):
    try:
        p = bel.find_input_pin(node, name)
        if p and hasattr(p, "get_pin_name") and str(p.get_pin_name()) == name:
            return p
        # some returns are fuzzy — verify
        if p and hasattr(p, "get_pin_name"):
            if str(p.get_pin_name()) == name:
                return p
        # fallback scan
        for cand in bel.list_input_pins(node) or []:
            if str(cand.get_pin_name()) == name:
                return cand
        return p
    except Exception:
        return None


def pin_out(node, name=None):
    if name:
        try:
            p = bel.find_output_pin(node, name)
            if p and str(p.get_pin_name()) == name:
                return p
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
        log(f"no pin {pin_name} on {node.get_name()}")
        return
    try:
        p.set_pin_value(str(value))
        log(f"set {node.get_name()}.{pin_name}={value}")
    except Exception as exc:
        log(f"set_pin_value: {exc}")


def ensure_vars(bp):
    for name in MONTAGES:
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception as exc:
            log(f"var {name}: {exc}")
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name("SS_WasMoving"), pin)
    except Exception as exc:
        log(f"SS_WasMoving: {exc}")
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    for prop, path in MONTAGES.items():
        try:
            cdo.set_editor_property(prop, load(path))
            log(f"CDO {prop}")
        except Exception as exc:
            log(f"CDO {prop}: {exc}")


def fix_abp():
    abp = load(ABP)
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_Slot):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("slot_name", unreal.Name("DefaultSlot"))
                obj.set_editor_property(outer, node)
                log("Slot=DefaultSlot")
            except Exception:
                pass
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_ControlRig):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("alpha", 0.0)
                obj.set_editor_property(outer, node)
                log("FootIK=0")
            except Exception:
                pass
    for name in list(MONTAGES) + ["SS_WasMoving", "SS_bWantsWalk"]:
        try:
            if name == "SS_WasMoving" or name == "SS_bWantsWalk":
                pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            else:
                pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    cdo = unreal.get_default_object(abp.generated_class())
    for prop, path in MONTAGES.items():
        try:
            cdo.set_editor_property(prop, load(path))
        except Exception:
            pass
    save(ABP)
    bp = load(CHAR)
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", abp.generated_class())
    save(CHAR)


def purge_driver_nodes(ed, graph):
    """Remove prior Start/Stop driver nodes (titles / SS_ vars / orphaned probe calls)."""
    kill = []
    markers = (
        "PlayAnimMontage",
        "GetVelocity",
        "Vector Length",
        "float > float",
        "float <= float",
        "NOT Boolean",
        "MakeLiteralBool",
        "获得SS_",
        "设置SS_",
        "获得CharacterMovement",
        "获得MaxWalkSpeed",
        "SS_Comment",
    )
    classes = (
        unreal.K2Node_CallFunction,
        unreal.K2Node_IfThenElse,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
    )
    for cls in classes:
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                title = str(bel.get_node_title(n))
                name = n.get_name()
                if "Tick" in title:
                    continue
                hit = any(m in title for m in markers) or name.startswith("SS_") or "SS_" in title
                # Always clear branches / SS variable nodes / PlayAnimMontage in EventGraph
                if cls is unreal.K2Node_IfThenElse:
                    hit = True
                if cls is unreal.K2Node_CallFunction and "PlayAnimMontage" in title:
                    hit = True
                if cls in (unreal.K2Node_VariableGet, unreal.K2Node_VariableSet) and "SS_" in title:
                    hit = True
                if hit:
                    kill.append(n)
            except Exception:
                continue
    # unique
    seen = set()
    uniq = []
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    kill = uniq
    if kill:
        try:
            ed.remove_nodes(kill)
            log(f"removed {len(kill)} old nodes via editor")
        except Exception as exc:
            log(f"remove_nodes: {exc}")
        for n in kill:
            try:
                # Force-destroy leftovers ObjectIterator may still see
                if hasattr(graph, "remove_node"):
                    graph.remove_node(n)
            except Exception:
                try:
                    n.destroy()
                except Exception:
                    pass
    # Hard pass: any remaining PlayAnimMontage in this EventGraph
    leftovers = []
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if n.get_outer() == graph and "PlayAnimMontage" in str(bel.get_node_title(n)):
                leftovers.append(n)
        except Exception:
            continue
    if leftovers:
        try:
            ed.remove_nodes(leftovers)
        except Exception:
            pass
        for n in leftovers:
            try:
                graph.remove_node(n)
            except Exception:
                pass
        log(f"hard-purged PlayAnimMontage leftovers={len(leftovers)}")


def fill_sm_states():
    """Best-effort: create AnimationStateGraph + SequencePlayer under Start/Stop states."""
    abp = load(ABP)
    sm = None
    idle = loco = None
    for n in unreal.ObjectIterator(unreal.AnimStateNode):
        p = n.get_path_name()
        if "StateMachine_0.Locomotion" not in p:
            continue
        sm = n.get_outer()
        if n.get_name() == "AnimStateNode_1":
            idle = n
        elif n.get_name() == "AnimStateNode_2":
            loco = n
    if not sm:
        log("SM not found")
        return
    ag_cls = getattr(unreal, "AnimationStateGraph", None)
    wanted = {
        "WalkStart": f"{RTG}/Walk_Start_F_0_Seq_RTG",
        "RunStart": f"{RTG}/Run_Start_F_0_Seq_RTG",
        "WalkStop": f"{RTG}/Walk_Stop_F_0_Seq_RTG",
        "RunStop": f"{RTG}/Run_Stop_F_0_Seq_RTG",
    }
    created = {}
    for i, (name, path) in enumerate(wanted.items()):
        state = None
        for n in unreal.ObjectIterator(unreal.AnimStateNode):
            if n.get_outer() == sm and n.get_name() == name:
                state = n
                break
        if not state:
            state = unreal.new_object(unreal.AnimStateNode, sm, unreal.Name(name))
            pos(None, state, 600, -100 + i * 160)
        bound = None
        if ag_cls:
            for g in unreal.ObjectIterator(ag_cls):
                if g.get_outer() == state:
                    bound = g
                    break
            if not bound:
                try:
                    bound = unreal.new_object(ag_cls, state, unreal.Name(name))
                except Exception as exc:
                    log(f"bound {name}: {exc}")
        if not bound:
            continue
        # Sequence player
        sp = None
        for cand in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
            if cand.get_outer() == bound:
                sp = cand
                break
        if not sp:
            sp = unreal.new_object(unreal.AnimGraphNode_SequencePlayer, bound, unreal.Name("SP"))
        try:
            node = sp.get_editor_property("node")
            node.set_editor_property("sequence", load(path))
            try:
                node.set_editor_property("loop_animation", False)
            except Exception:
                pass
            sp.set_editor_property("node", node)
            log(f"SM {name} <- {path}")
        except Exception as exc:
            log(f"SM seq {name}: {exc}")
        # StateResult
        rcls = getattr(unreal, "AnimGraphNode_StateResult", None)
        if rcls:
            has = False
            for r in unreal.ObjectIterator(rcls):
                if r.get_outer() == bound:
                    has = True
                    break
            if not has:
                unreal.new_object(rcls, bound, unreal.Name("Result"))
        created[name] = state
        # Auto transition Start/Stop completion
        if name.endswith("Start") and loco:
            t = unreal.new_object(unreal.AnimStateTransitionNode, sm, unreal.Name(f"{name}_to_Loco"))
            try:
                t.set_editor_property("automatic_rule_based_on_sequence_player_in_state", True)
            except Exception:
                try:
                    t.set_editor_property("bAutomaticRuleBasedOnSequencePlayerInState", True)
                except Exception:
                    pass
        if name.endswith("Stop") and idle:
            t = unreal.new_object(unreal.AnimStateTransitionNode, sm, unreal.Name(f"{name}_to_Idle"))
            try:
                t.set_editor_property("automatic_rule_based_on_sequence_player_in_state", True)
            except Exception:
                try:
                    t.set_editor_property("bAutomaticRuleBasedOnSequencePlayerInState", True)
                except Exception:
                    pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    save(ABP)
    log(f"SM states created={list(created)}")


def wire_driver(bp):
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()
    log(f"editor graph={graph.get_path_name()}")
    purge_driver_nodes(ed, graph)

    # Tick
    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
                tick = n
                break
        except Exception:
            continue
    if not tick:
        tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(-1600, 1600))
    pos(ed, tick, -1600, 1600)

    # Nodes
    get_vel = ed.add_call_function_node("/Script/Engine.Actor:GetVelocity")
    vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    gt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    le = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:LessEqual_FloatFloat")
    not_was = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    lit_t = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    lit_f = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    get_max = ed.add_get_member_variable_node(
        "MaxWalkSpeed", "/Script/Engine.CharacterMovementComponent"
    )

    br_mv = ed.add_branch_node()
    br_start = ed.add_branch_node()
    br_stop = ed.add_branch_node()
    br_w1 = ed.add_branch_node()
    br_w2 = ed.add_branch_node()

    play_ws = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    play_rs = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    play_wst = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
    play_rst = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")

    get_was = ed.add_get_member_variable_node("SS_WasMoving")
    # Separate Set nodes per play path (exec pins are single-connection)
    set_ws = ed.add_set_member_variable_node("SS_WasMoving")
    set_rs = ed.add_set_member_variable_node("SS_WasMoving")
    set_wst = ed.add_set_member_variable_node("SS_WasMoving")
    set_rst = ed.add_set_member_variable_node("SS_WasMoving")
    m_ws = ed.add_get_member_variable_node("SS_WalkStart")
    m_rs = ed.add_get_member_variable_node("SS_RunStart")
    m_wst = ed.add_get_member_variable_node("SS_WalkStop")
    m_rst = ed.add_get_member_variable_node("SS_RunStop")

    layout = [
        (get_vel, -1300, 1600),
        (vsize, -1050, 1500),
        (gt, -800, 1500),
        (get_cmc, -1300, 1850),
        (get_max, -1050, 1850),
        (le, -800, 1850),
        (not_was, -550, 1400),
        (get_was, -800, 1350),
        (br_mv, -550, 1600),
        (br_start, -250, 1450),
        (br_stop, -250, 1750),
        (br_w1, 50, 1400),
        (br_w2, 50, 1750),
        (play_ws, 350, 1350),
        (play_rs, 350, 1500),
        (play_wst, 350, 1700),
        (play_rst, 350, 1850),
        (m_ws, 200, 1280),
        (m_rs, 200, 1500),
        (m_wst, 200, 1700),
        (m_rst, 200, 1850),
        (lit_t, 550, 1400),
        (lit_f, 550, 1750),
        (set_ws, 750, 1350),
        (set_rs, 750, 1500),
        (set_wst, 750, 1700),
        (set_rst, 750, 1850),
    ]
    for n, x, y in layout:
        pos(ed, n, x, y)

    set_val(gt, "B", "15.0")
    set_val(le, "B", "300.0")
    set_val(lit_t, "Value", "true")
    set_val(lit_f, "Value", "false")

    links = []
    # GetVelocity / VSize / compares are pure — exec goes Tick -> Branch only
    links.append(("tick->br", connect(bel.find_then_pin(tick), bel.find_execute_pin(br_mv))))

    # data: vel -> vsize -> gt
    links.append(("vel->vsize", connect(pin_out(get_vel, "ReturnValue"), pin_in(vsize, "A"))))
    links.append(("vsize->gt", connect(pin_out(vsize, "ReturnValue"), pin_in(gt, "A"))))
    links.append(("gt->br", connect(pin_out(gt, "ReturnValue"), bel.find_condition_pin(br_mv))))

    # MaxWalkSpeed: CMC get -> MaxWalkSpeed target
    self_max = bel.find_self_pin(get_max) or pin_in(get_max, "self")
    links.append(("cmc->max", connect(pin_out(get_cmc), self_max)))
    if not links[-1][1]:
        try:
            ips = list(bel.list_input_pins(get_max) or [])
            if ips:
                links.append(("cmc->max0", connect(pin_out(get_cmc), ips[0])))
        except Exception:
            pass
    links.append(("max->le", connect(pin_out(get_max), pin_in(le, "A"))))

    # START edge
    links.append(("brT->start", connect(bel.find_then_pin(br_mv), bel.find_execute_pin(br_start))))
    links.append(("was->not", connect(pin_out(get_was), pin_in(not_was, "A"))))
    links.append(("not->start", connect(pin_out(not_was, "ReturnValue"), bel.find_condition_pin(br_start))))
    links.append(("startT->w1", connect(bel.find_then_pin(br_start), bel.find_execute_pin(br_w1))))
    links.append(("le->w1", connect(pin_out(le, "ReturnValue"), bel.find_condition_pin(br_w1))))
    links.append(("w1T->pws", connect(bel.find_then_pin(br_w1), bel.find_execute_pin(play_ws))))
    links.append(("w1E->prs", connect(bel.find_else_pin(br_w1), bel.find_execute_pin(play_rs))))
    links.append(("pws->set", connect(bel.find_then_pin(play_ws), bel.find_execute_pin(set_ws))))
    links.append(("prs->set", connect(bel.find_then_pin(play_rs), bel.find_execute_pin(set_rs))))
    links.append(("true->set_ws", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_ws, "SS_WasMoving"))))
    links.append(("true->set_rs", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_rs, "SS_WasMoving"))))

    # STOP edge
    links.append(("brE->stop", connect(bel.find_else_pin(br_mv), bel.find_execute_pin(br_stop))))
    links.append(("was->stop", connect(pin_out(get_was), bel.find_condition_pin(br_stop))))
    links.append(("stopT->w2", connect(bel.find_then_pin(br_stop), bel.find_execute_pin(br_w2))))
    links.append(("le->w2", connect(pin_out(le, "ReturnValue"), bel.find_condition_pin(br_w2))))
    links.append(("w2T->pwst", connect(bel.find_then_pin(br_w2), bel.find_execute_pin(play_wst))))
    links.append(("w2E->prst", connect(bel.find_else_pin(br_w2), bel.find_execute_pin(play_rst))))
    links.append(("pwst->set", connect(bel.find_then_pin(play_wst), bel.find_execute_pin(set_wst))))
    links.append(("prst->set", connect(bel.find_then_pin(play_rst), bel.find_execute_pin(set_rst))))
    links.append(("false->set_wst", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_wst, "SS_WasMoving"))))
    links.append(("false->set_rst", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_rst, "SS_WasMoving"))))

    # montages
    for getter, player in (
        (m_ws, play_ws),
        (m_rs, play_rs),
        (m_wst, play_wst),
        (m_rst, play_rst),
    ):
        links.append(
            (
                f"m->{player.get_name()}",
                connect(pin_out(getter), pin_in(player, "AnimMontage")),
            )
        )

    for name, ok in links:
        log(f"link {name}: {ok}")

    try:
        c = ed.add_comment_node(
            "START/STOP: Tick edge-detect PlayAnimMontage -> DefaultSlot\n"
            "Walk if MaxWalkSpeed<=300 else Run"
        )
        pos(ed, c, -1600, 1200)
    except Exception as exc:
        log(f"comment: {exc}")

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as exc:
        log(f"compile: {exc}")
    save(CHAR)
    return True


def verify():
    bp = load(CHAR)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    live = set()
    try:
        for n in ed.list_all_nodes() or []:
            live.add(n.get_path_name())
    except Exception:
        pass
    plays = 0
    linked_plays = 0
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if "PlayAnimMontage" not in str(bel.get_node_title(n)):
                continue
            if "BP_ThirdPersonCharacter:EventGraph" not in n.get_path_name():
                continue
            if live and n.get_path_name() not in live:
                continue
            plays += 1
            p = pin_in(n, "AnimMontage")
            linked = list(p.list_connected_pins()) if p else []
            if linked:
                linked_plays += 1
            log(f"PlayAnimMontage {n.get_name()} links={len(linked)}")
        except Exception:
            continue
    log(f"verify PlayAnimMontage live={plays} linked={linked_plays}")
    for prop, path in MONTAGES.items():
        log(f"verify asset {prop}: {unreal.EditorAssetLibrary.does_asset_exist(path)}")
    # BS
    if unreal.EditorAssetLibrary.does_asset_exist(BS_GRAPH):
        bs = load(BS_GRAPH)
        try:
            n = len(bs.get_editor_property("sample_data") or [])
        except Exception:
            n = -1
        log(f"verify BS samples={n}")


def run():
    log("start")
    for p in MONTAGES.values():
        log(f"exists {p}: {unreal.EditorAssetLibrary.does_asset_exist(p)}")
    bp = load(CHAR)
    ensure_vars(bp)
    fix_abp()
    try:
        fill_sm_states()
    except Exception as exc:
        log(f"fill_sm: {exc}")
    wire_driver(bp)
    verify()
    content = unreal.Paths.project_content_dir()
    with open(content + "Python/START_STOP_VERIFY.txt", "w", encoding="utf-8") as f:
        f.write(
            "Lvl_ThirdPerson Start/Stop check:\n"
            "1) No Alt + W: Run Start montage -> Run loop\n"
            "2) Release W: Run Stop -> Idle\n"
            "3) Alt + W: Walk Start -> Walk loop\n"
            "4) Release W: Walk Stop -> Idle\n"
            "5) Mouse look still drives camera boom\n"
            "\nRuntime path: Character Tick edge-detect -> PlayAnimMontage -> ABP DefaultSlot\n"
            "SM Start/Stop states may also exist (BoundGraph filled); transitions may need hand-link.\n"
        )
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
