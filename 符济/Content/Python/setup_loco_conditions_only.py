# -*- coding: utf-8 -*-
"""
NO MONTAGES for Start/Stop.

Keep only condition vars for the user to wire in AnimBP state machine:
  Character (updated every Tick, after Alt-walk speed):
    - bWantsWalk     (Alt held)
    - bHasMoveInput  (WASD / move input present)
  AnimBP copies the same two bools each Update.

User owns all Start/Stop sequences + transition graphs.
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
INPUT_EPS = 0.1

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[LocoCond] {m}")


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


def ensure_bool(bp, name):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name(name), pin)
    except Exception:
        pass


def purge_montage_ss(ed, graph):
    """Remove ALL Start/Stop montage driver nodes. Never touch WW_* Alt-walk."""
    kill = []
    markers = (
        "PlayAnimMontage",
        "GetVelocity",
        "GetLastMovementInputVector",
        "GetPendingMovementInputVector",
        "获得SS_",
        "设置SS_",
        "获得bHasMoveInput",
        "设置bHasMoveInput",
        "START/STOP",
        "WASD input",
        "NO MONTAGES",
        "Loco conditions",
    )
    name_prefixes = ("SS_", "SS_DEL_")

    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_IfThenElse,
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
                if name.startswith("WW_"):
                    continue
                title = str(bel.get_node_title(n))
                hit = name.startswith(name_prefixes) or any(m in title for m in markers)
                # Kill leftover IfThenElse only if previously named SS_ or linked from SS
                if cls is unreal.K2Node_IfThenElse and name.startswith("SS_"):
                    hit = True
                if cls is unreal.K2Node_IfThenElse and name.startswith("K2Node_IfThenElse"):
                    # only remove if in SS cluster: connected from old SS / PlayAnim path
                    # safer: skip generic IfThenElse that aren't SS_*
                    pass
                if hit:
                    kill.append(n)
            except Exception:
                continue

    # Any PlayAnimMontage left in this EventGraph
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if n.get_outer() != graph:
                continue
            if n.get_name().startswith("WW_"):
                continue
            if "PlayAnimMontage" in str(bel.get_node_title(n)):
                kill.append(n)
        except Exception:
            pass

    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)

    # Detach WW_SetSpd.then before delete
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
                bel.find_then_pin(n).break_pin_links()
        except Exception:
            pass

    for i, n in enumerate(uniq):
        try:
            n.rename(f"SS_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"removed {len(uniq)} montage/SS nodes")
    else:
        log("no montage/SS nodes")


def find_attach(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
                log("attach after WW_SetSpd")
                return bel.find_then_pin(n)
        except Exception:
            pass
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
                log("attach after Tick")
                return bel.find_then_pin(n)
        except Exception:
            pass
    return None


def wire_char_input_flag(bp):
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()
    purge_montage_ss(ed, graph)

    attach = find_attach(graph)
    if not attach:
        raise RuntimeError("no attach pin")

    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "LC_GetPending")
    pos(get_pending, -200, 2100)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "LC_GetLast")
    pos(get_last, -200, 2220)

    v_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_p, "LC_VPending")
    pos(v_p, 50, 2100)
    v_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(v_l, "LC_VLast")
    pos(v_l, 50, 2220)

    gt_p = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_p, "LC_GtP")
    pos(gt_p, 280, 2100)
    set_val(gt_p, "B", str(INPUT_EPS))
    gt_l = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_l, "LC_GtL")
    pos(gt_l, 280, 2220)
    set_val(gt_l, "B", str(INPUT_EPS))

    or_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_in, "LC_OrInput")
    pos(or_in, 520, 2160)

    set_has = ed.add_set_member_variable_node("bHasMoveInput")
    safe_rename(set_has, "LC_SetHasInput")
    pos(set_has, 760, 2160)

    links = []
    links.append(("att->set", connect(attach, bel.find_execute_pin(set_has))))
    links.append(("p->v", connect(pin_out(get_pending, "ReturnValue"), pin_in(v_p, "A"))))
    links.append(("l->v", connect(pin_out(get_last, "ReturnValue"), pin_in(v_l, "A"))))
    links.append(("vp->gt", connect(pin_out(v_p, "ReturnValue"), pin_in(gt_p, "A"))))
    links.append(("vl->gt", connect(pin_out(v_l, "ReturnValue"), pin_in(gt_l, "A"))))
    links.append(("gtp->or", connect(pin_out(gt_p, "ReturnValue"), pin_in(or_in, "A"))))
    links.append(("gtl->or", connect(pin_out(gt_l, "ReturnValue"), pin_in(or_in, "B"))))
    links.append(("or->set", connect(pin_out(or_in, "ReturnValue"), pin_in(set_has, "bHasMoveInput"))))

    try:
        ed.add_comment_node(
            "Loco conditions ONLY (no montages)\n"
            "bWantsWalk  = Alt held (WW_* above)\n"
            "bHasMoveInput = WASD / move input\n"
            "Use these in AnimBP state machine transitions",
            unreal.IntPoint(-250, 1950),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"char link {n}: {ok}")

    try:
        bel.compile_blueprint(bp)
        log("char compile OK")
    except Exception as e:
        log(f"char compile: {e}")
    save(CHAR)


def purge_abp_sync(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_DynamicCast,
        unreal.K2Node_IfThenElse,
        unreal.EdGraphNode_Comment,
        unreal.K2Node_Event,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("LC_") or "Loco conditions" in title or "copy bHasMoveInput" in title:
                    # don't delete BlueprintUpdateAnimation event itself if not LC_
                    if cls is unreal.K2Node_Event and "Blueprint Update Animation" in title:
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
            n.rename(f"LC_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"abp purged {len(uniq)}")


def wire_abp_copy(abp):
    """Event BlueprintUpdateAnimation -> copy bHasMoveInput / bWantsWalk from Character."""
    ensure_bool(abp, "bHasMoveInput")
    ensure_bool(abp, "bWantsWalk")
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass

    # Prefer EventGraph
    ed = None
    for gname in ("EventGraph", "AnimGraph"):
        try:
            ed = BGE.get_graph_editor_by_name(abp, gname)
            if ed and gname == "EventGraph":
                break
        except Exception:
            ed = None
    if not ed:
        log("no ABP EventGraph editor — vars created only")
        save(ABP)
        return

    graph = ed.get_graph()
    purge_abp_sync(ed, graph)

    # Find or add BlueprintUpdateAnimation
    upd = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Blueprint Update Animation" in str(bel.get_node_title(n)):
                upd = n
                break
        except Exception:
            pass
    if not upd:
        try:
            upd = bel.add_event_override(
                abp, "BlueprintUpdateAnimation", unreal.IntPoint(-1200, 0)
            )
        except Exception as e:
            log(f"add Update event: {e}")
            # try Receive
            try:
                upd = bel.add_event_override(
                    abp, "BlueprintUpdateAnimation", unreal.IntPoint(-1200, 0)
                )
            except Exception:
                pass
    if not upd:
        log("WARN: could not create BlueprintUpdateAnimation — set ABP vars manually")
        save(ABP)
        return
    pos(upd, -1200, 200)
    then = bel.find_then_pin(upd)
    # Don't break existing update chain — insert at front
    old = list(then.list_connected_pins() or [])
    then.break_pin_links()

    try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
    safe_rename(try_get, "LC_TryGet")
    pos(try_get, -1000, 400)

    # Cast to BP_ThirdPersonCharacter
    cast_node = None
    try:
        char_cls = load(CHAR).generated_class()
        cast_node = ed.add_cast_node(char_cls) if hasattr(ed, "add_cast_node") else None
    except Exception as e:
        log(f"add_cast_node: {e}")
    if not cast_node:
        # Dynamic cast via new_object
        try:
            cls = unreal.K2Node_DynamicCast
            cast_node = unreal.new_object(cls, graph, unreal.Name("LC_CastChar"))
            cast_node.set_editor_property("target_type", load(CHAR).generated_class())
            for m in ("allocate_default_pins", "reconstruct_node"):
                if hasattr(cast_node, m):
                    try:
                        getattr(cast_node, m)()
                    except Exception:
                        pass
        except Exception as e:
            log(f"DynamicCast: {e}")

    if cast_node:
        safe_rename(cast_node, "LC_CastChar")
        pos(cast_node, -750, 250)

    set_has = ed.add_set_member_variable_node("bHasMoveInput")
    safe_rename(set_has, "LC_SetHas")
    pos(set_has, -350, 200)
    set_walk = ed.add_set_member_variable_node("bWantsWalk")
    safe_rename(set_walk, "LC_SetWalk")
    pos(set_walk, -100, 200)

    # Gets from cast result — use Character variable gets with self from cast
    # Simpler: call get on cast output via member get nodes with Target
    get_has = None
    get_walk = None
    try:
        # Variable gets of character properties need cast as self — use "get member" with path
        get_has = ed.add_get_member_variable_node(
            "bHasMoveInput", load(CHAR).generated_class().get_path_name()
        )
    except Exception:
        try:
            get_has = ed.add_get_member_variable_node("bHasMoveInput")
        except Exception as e:
            log(f"get_has: {e}")
    try:
        get_walk = ed.add_get_member_variable_node(
            "bWantsWalk", load(CHAR).generated_class().get_path_name()
        )
    except Exception:
        try:
            get_walk = ed.add_get_member_variable_node("bWantsWalk")
        except Exception as e:
            log(f"get_walk: {e}")

    if get_has:
        safe_rename(get_has, "LC_GetHas")
        pos(get_has, -550, 400)
    if get_walk:
        safe_rename(get_walk, "LC_GetWalk")
        pos(get_walk, -550, 500)

    links = []
    links.append(("upd->cast", connect(then, bel.find_execute_pin(cast_node) if cast_node else bel.find_execute_pin(set_has))))
    if cast_node:
        links.append(("pawn->cast", connect(pin_out(try_get, "ReturnValue"), pin_in(cast_node, "Object") or pin_in(cast_node, "object"))))
        # cast success -> set_has -> set_walk -> old
        succ = bel.find_then_pin(cast_node) or pin_out(cast_node, "then")
        links.append(("cast->setHas", connect(succ, bel.find_execute_pin(set_has))))
        # cast As BP -> self of gets
        as_pin = pin_out(cast_node, "AsBP Third Person Character")
        if not as_pin:
            for p in bel.list_output_pins(cast_node) or []:
                nm = str(p.get_pin_name())
                if nm.lower().startswith("as") or "Third" in nm or "Character" in nm:
                    as_pin = p
                    break
        if as_pin and get_has:
            links.append(("as->getHas", connect(as_pin, bel.find_self_pin(get_has) or pin_in(get_has, "self") or pin_in(get_has, "Target"))))
        if as_pin and get_walk:
            links.append(("as->getWalk", connect(as_pin, bel.find_self_pin(get_walk) or pin_in(get_walk, "self") or pin_in(get_walk, "Target"))))

    if get_has:
        links.append(("getHas->set", connect(pin_out(get_has), pin_in(set_has, "bHasMoveInput"))))
    if get_walk:
        links.append(("getWalk->set", connect(pin_out(get_walk), pin_in(set_walk, "bWantsWalk"))))
    links.append(("setHas->setWalk", connect(bel.find_then_pin(set_has), bel.find_execute_pin(set_walk))))

    # reattach previous update consumers
    if old:
        links.append(("setWalk->old", connect(bel.find_then_pin(set_walk), old[0])))

    try:
        ed.add_comment_node(
            "Loco conditions copy (no montages)\n"
            "bHasMoveInput / bWantsWalk <- Character\n"
            "Use in SM transition rules",
            unreal.IntPoint(-1200, 50),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"abp link {n}: {ok}")

    try:
        bel.compile_blueprint(abp)
        log("abp compile OK")
    except Exception as e:
        log(f"abp compile: {e}")
    save(ABP)


def write_rules():
    text = """ABP_StrafeLocomotion — conditions ONLY (NO montages)

AnimBP variables (copied from Character each Update):
  bHasMoveInput  = player holding WASD / move input
  bWantsWalk     = holding Alt (walk ~200); false = run ~600

Suggested state machine transitions (you plug sequences yourself):

  Idle -> WalkStart:     bHasMoveInput AND bWantsWalk
  Idle -> RunStart:      bHasMoveInput AND NOT bWantsWalk
  WalkStart -> WalkLoop: Automatic (sequence nearly done)
  RunStart  -> RunLoop:  Automatic (sequence nearly done)
  WalkLoop -> WalkStop:  NOT bHasMoveInput AND bWantsWalk
  RunLoop  -> RunStop:   NOT bHasMoveInput AND NOT bWantsWalk
  WalkStop / RunStop -> Idle: Automatic (sequence nearly done)

Interrupt while stopping:
  WalkStop -> WalkStart: bHasMoveInput AND bWantsWalk
  RunStop  -> RunStart:  bHasMoveInput AND NOT bWantsWalk

Do NOT use Speed≈0 for Stop (feels late).
Do NOT PlayAnimMontage for Start/Stop — state machine sequences only.
"""
    path = unreal.Paths.project_content_dir() + "Python/START_STOP_TRANSITION_RULES.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    log("wrote START_STOP_TRANSITION_RULES.txt")


def run():
    log("start — strip montages, keep conditions")
    bp = load(CHAR)
    ensure_bool(bp, "bWantsWalk")
    ensure_bool(bp, "bHasMoveInput")
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    for n in ("bWantsWalk", "bHasMoveInput"):
        try:
            cdo.set_editor_property(n, False)
        except Exception:
            pass
    save(CHAR)

    wire_char_input_flag(bp)

    abp = load(ABP)
    wire_abp_copy(abp)
    write_rules()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
