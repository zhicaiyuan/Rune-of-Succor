# -*- coding: utf-8 -*-
"""
Add WASD-direction turn variables on ABP_StrafeLocomotion + compute in Update.
Does NOT modify state machine / AnimGraph states / transitions.

Variables:
  MoveYawDelta      float   signed degrees PrevMoveDir -> CurrMoveDir (-180..180)
  AbsMoveYawDelta   float   abs(MoveYawDelta)
  bTurnLeft         bool    MoveYawDelta < 0
  bWantsTurn90      bool    edge: Abs in [TurnAngle90, TurnAngle180)
  bWantsTurn180     bool    edge: Abs >= TurnAngle180
  PrevMoveDir       vector  last stable move dir (XY)
  TurnAngle90       float   default 60
  TurnAngle180      float   default 135
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
INPUT_EPS = 0.1

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[TurnVar] {m}")


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


def add_var(bp, name, kind):
    """kind: bool | float | vector"""
    try:
        if kind == "bool":
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        elif kind == "float":
            # double/real in UE5
            try:
                pin = bel.get_basic_type_by_name(unreal.Name("real"))
            except Exception:
                pin = bel.get_basic_type_by_name(unreal.Name("double"))
        elif kind == "vector":
            pin = bel.get_basic_type_by_name(unreal.Name("vector"))
        else:
            return
        bel.add_member_variable(bp, unreal.Name(name), pin)
        log(f"add {name} ({kind})")
    except Exception as e:
        log(f"add {name}: {e}")


def ensure_vars(bp):
    add_var(bp, "MoveYawDelta", "float")
    add_var(bp, "AbsMoveYawDelta", "float")
    add_var(bp, "bTurnLeft", "bool")
    add_var(bp, "bWantsTurn90", "bool")
    add_var(bp, "bWantsTurn180", "bool")
    add_var(bp, "PrevMoveDir", "vector")
    add_var(bp, "TurnAngle90", "float")
    add_var(bp, "TurnAngle180", "float")
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    for name, val in (
        ("MoveYawDelta", 0.0),
        ("AbsMoveYawDelta", 0.0),
        ("TurnAngle90", 60.0),
        ("TurnAngle180", 135.0),
        ("bTurnLeft", False),
        ("bWantsTurn90", False),
        ("bWantsTurn180", False),
    ):
        try:
            cdo.set_editor_property(name, val)
        except Exception:
            pass
    try:
        cdo.set_editor_property("PrevMoveDir", unreal.Vector(0, 0, 0))
    except Exception:
        pass
    save(ABP)


def purge_tv(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_IfThenElse,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
        unreal.K2Node_MacroInstance,
        unreal.K2Node_ExecutionSequence,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("TV_") or name.startswith("TV_DEL_") or "Turn vars" in title:
                    kill.append(n)
            except Exception:
                pass
    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    # If we remove a Sequence that was only for TV, careful — only TV_ prefixed
    for i, n in enumerate(uniq):
        try:
            n.rename(f"TV_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")


def find_update(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "BlueprintUpdateAnimation" in str(
                bel.get_node_title(n)
            ).replace(" ", ""):
                return n
        except Exception:
            pass
    return None


def find_si_setstop(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name() == "SI_SetStop":
                return n
        except Exception:
            pass
    return None


def wire_compute(abp):
    """
    Insert after SI_SetStop (or Update):
      compute move-dir yaw delta -> set turn vars -> previous chain

    Pure math graph is large; use a compact Custom Event? No — keep in Update.

    Practical compact approach via fewer nodes:
      GetPending/Last input -> Make Vector XY -> VSizeXY
      Branch has input
      Normalize -> get PrevMoveDir
      Dot / Cross Z for signed angle via DegAtan2
      Set floats/bools
      Set PrevMoveDir = Curr when Abs < 45 OR no prev; on turn edge also set Prev=Curr after flags (pulse)

    UE nodes:
      - GetLastMovementInputVector / GetPendingMovementInputVector on Pawn
      - Greater (size)
      - Boolean OR
      - Vector_Normal2D or Normalize + set Z=0
      - Dot_VectorVector, Cross_VectorVector, BreakVector Z, DegAtan2
      - Abs, GreaterEqual for thresholds
    """
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()
    purge_tv(ed, graph)

    # Attach after SI_SetStop if present, else after Update
    attach_node = find_si_setstop(graph)
    upd = find_update(graph)
    if attach_node:
        attach_pin = bel.find_then_pin(attach_node)
        log("attach after SI_SetStop")
    elif upd:
        attach_pin = bel.find_then_pin(upd)
        log("attach after Update")
    else:
        raise RuntimeError("no Update / SI_SetStop")

    old = list(attach_pin.list_connected_pins() or [])
    old_names = []
    for p in old:
        try:
            old_names.append(p.get_owning_node().get_name())
        except Exception:
            pass
    log(f"old then -> {old_names}")
    attach_pin.break_pin_links()

    # --- Sequence: then0 = turn compute chain end sets, then1 = old ---
    # Simpler: linear exec of sets, then reconnect old.

    # Reuse SI_TryGet if exists
    try_get = None
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if n.get_outer() == graph and n.get_name() == "SI_TryGet":
                try_get = n
                break
        except Exception:
            pass
    if not try_get:
        try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
        safe_rename(try_get, "TV_TryGet")
        pos(try_get, -1400, 800)
    else:
        log("reuse SI_TryGet")

    get_pending = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pending, "TV_GetPending")
    pos(get_pending, -1150, 760)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "TV_GetLast")
    pos(get_last, -1150, 900)

    # Add vectors pending+last for robustness
    add_v = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    safe_rename(add_v, "TV_AddInput")
    pos(add_v, -900, 820)

    # Vector length XY
    vsize_xy = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSizeXY")
    if not vsize_xy:
        vsize_xy = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
        safe_rename(vsize_xy, "TV_VSize")
    else:
        safe_rename(vsize_xy, "TV_VSizeXY")
    pos(vsize_xy, -680, 780)

    gt_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_in, "TV_HasInput")
    pos(gt_in, -480, 780)
    set_val(gt_in, "B", str(INPUT_EPS))

    # Normal2D
    norm2d = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Normal2D")
    # Normal2D takes FVector2D — might need Conv. Use Vector_NormalUnsafe + set Z=0 instead.
    if not norm2d:
        log("no Normal2D")
    # Use: MakeVector(X,Y,0) from break, then Normal
    brk = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector")
    safe_rename(brk, "TV_Break")
    pos(brk, -680, 920)

    make_flat = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    safe_rename(make_flat, "TV_MakeFlat")
    pos(make_flat, -480, 920)
    set_val(make_flat, "Z", "0.0")

    normal = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Normal")
    safe_rename(normal, "TV_Normal")
    pos(normal, -280, 920)
    set_val(normal, "Tolerance", "0.0001")

    get_prev = ed.add_get_member_variable_node("PrevMoveDir")
    safe_rename(get_prev, "TV_GetPrev")
    pos(get_prev, -280, 1080)

    vsize_prev = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSizeXY")
    if not vsize_prev:
        vsize_prev = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(vsize_prev, "TV_PrevSize")
    pos(vsize_prev, -80, 1080)

    gt_prev = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_prev, "TV_HasPrev")
    pos(gt_prev, 120, 1080)
    set_val(gt_prev, "B", str(INPUT_EPS))

    # Signed angle: DegAtan2(Cross.Z, Dot)
    dot = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Dot_VectorVector")
    safe_rename(dot, "TV_Dot")
    pos(dot, -80, 920)

    cross = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Cross_VectorVector")
    safe_rename(cross, "TV_Cross")
    pos(cross, -80, 1000)

    brk_c = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector")
    safe_rename(brk_c, "TV_BreakCross")
    pos(brk_c, 120, 1000)

    atan2 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2")
    safe_rename(atan2, "TV_Atan2")
    pos(atan2, 320, 960)

    abs_f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs")
    safe_rename(abs_f, "TV_Abs")
    pos(abs_f, 520, 960)

    get_th90 = ed.add_get_member_variable_node("TurnAngle90")
    safe_rename(get_th90, "TV_GetTh90")
    pos(get_th90, 520, 1100)
    get_th180 = ed.add_get_member_variable_node("TurnAngle180")
    safe_rename(get_th180, "TV_GetTh180")
    pos(get_th180, 520, 1180)

    ge_90 = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(ge_90, "TV_Ge90")
    pos(ge_90, 720, 1000)

    ge_180 = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(ge_180, "TV_Ge180")
    pos(ge_180, 720, 1120)

    lt_180 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    safe_rename(lt_180, "TV_Lt180")
    pos(lt_180, 720, 1040)

    and_90 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_90, "TV_And90")
    pos(and_90, 920, 1000)

    # both valid for turn
    and_valid = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_valid, "TV_AndValid")
    pos(and_valid, 320, 780)

    and_90b = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_90b, "TV_And90Final")
    pos(and_90b, 1120, 1000)

    and_180b = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_180b, "TV_And180Final")
    pos(and_180b, 1120, 1120)

    lt_zero = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
    safe_rename(lt_zero, "TV_Lt0")
    pos(lt_zero, 520, 880)
    set_val(lt_zero, "B", "0.0")

    and_left = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_left, "TV_AndLeft")
    pos(and_left, 720, 880)

    # select delta: if has prev+input use atan else 0
    sel_delta = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    safe_rename(sel_delta, "TV_SelDelta")
    pos(sel_delta, 520, 780)
    set_val(sel_delta, "B", "0.0")

    # Branch: has input -> update prev logic via two set paths
    br = ed.add_branch_node()
    safe_rename(br, "TV_BrInput")
    pos(br, 200, 700)

    # Sets
    set_delta = ed.add_set_member_variable_node("MoveYawDelta")
    safe_rename(set_delta, "TV_SetDelta")
    pos(set_delta, 1400, 700)

    set_abs = ed.add_set_member_variable_node("AbsMoveYawDelta")
    safe_rename(set_abs, "TV_SetAbs")
    pos(set_abs, 1650, 700)

    set_left = ed.add_set_member_variable_node("bTurnLeft")
    safe_rename(set_left, "TV_SetLeft")
    pos(set_left, 1900, 700)

    set_t90 = ed.add_set_member_variable_node("bWantsTurn90")
    safe_rename(set_t90, "TV_SetT90")
    pos(set_t90, 2150, 700)

    set_t180 = ed.add_set_member_variable_node("bWantsTurn180")
    safe_rename(set_t180, "TV_SetT180")
    pos(set_t180, 2400, 700)

    set_prev_curr = ed.add_set_member_variable_node("PrevMoveDir")
    safe_rename(set_prev_curr, "TV_SetPrevCurr")
    pos(set_prev_curr, 2650, 700)

    set_prev_zero = ed.add_set_member_variable_node("PrevMoveDir")
    safe_rename(set_prev_zero, "TV_SetPrevZero")
    pos(set_prev_zero, 1400, 900)

    # clear turn flags on no input
    set_t90_f = ed.add_set_member_variable_node("bWantsTurn90")
    safe_rename(set_t90_f, "TV_ClrT90")
    pos(set_t90_f, 1650, 900)
    set_t180_f = ed.add_set_member_variable_node("bWantsTurn180")
    safe_rename(set_t180_f, "TV_ClrT180")
    pos(set_t180_f, 1900, 900)
    set_delta_0 = ed.add_set_member_variable_node("MoveYawDelta")
    safe_rename(set_delta_0, "TV_ClrDelta")
    pos(set_delta_0, 2150, 900)
    set_abs_0 = ed.add_set_member_variable_node("AbsMoveYawDelta")
    safe_rename(set_abs_0, "TV_ClrAbs")
    pos(set_abs_0, 2400, 900)

    lit_f = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralBool")
    safe_rename(lit_f, "TV_LitF")
    pos(lit_f, 1400, 1050)
    set_val(lit_f, "Value", "false")

    lit_0 = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralFloat")
    # MakeLiteralDouble in UE5?
    if not lit_0:
        lit_0 = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralDouble")
    safe_rename(lit_0, "TV_Lit0")
    pos(lit_0, 1400, 1120)
    set_val(lit_0, "Value", "0.0")

    # zero vector for clear prev — MakeVector 0,0,0
    zero_v = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeVector")
    safe_rename(zero_v, "TV_ZeroV")
    pos(zero_v, 1200, 900)
    set_val(zero_v, "X", "0.0")
    set_val(zero_v, "Y", "0.0")
    set_val(zero_v, "Z", "0.0")

    links = []
    # exec: attach -> Sequence(then0=Branch turn sets, then1=old chain)
    seq = None
    try:
        if hasattr(ed, "add_sequence_node"):
            seq = ed.add_sequence_node()
        else:
            seq = unreal.new_object(unreal.K2Node_ExecutionSequence, graph, unreal.Name("TV_Seq"))
            for m in ("allocate_default_pins", "reconstruct_node"):
                if hasattr(seq, m):
                    try:
                        getattr(seq, m)()
                    except Exception:
                        pass
        safe_rename(seq, "TV_Seq")
        pos(seq, 0, 700)
    except Exception as e:
        log(f"seq create: {e}")
        seq = None

    links.append(("has->br", connect(pin_out(gt_in, "ReturnValue"), bel.find_condition_pin(br))))
    if seq:
        links.append(("att->seq", connect(attach_pin, bel.find_execute_pin(seq))))
        t0 = pin_out(seq, "then_0")
        links.append(("seq0->br", connect(t0, bel.find_execute_pin(br))))
        t1 = pin_out(seq, "then_1")
        if old and t1:
            links.append(("seq1->old", connect(t1, old[0])))
            log(f"seq1 -> {old_names[0] if old_names else '?'}")
        elif old:
            log("WARN: no then_1 — will join from branch ends")
    else:
        links.append(("att->br", connect(attach_pin, bel.find_execute_pin(br))))

    # data: pawn inputs
    pawn = pin_out(try_get, "ReturnValue")
    links.append(("pawn->pend", connect(pawn, bel.find_self_pin(get_pending) or pin_in(get_pending, "self"))))
    links.append(("pawn->last", connect(pawn, bel.find_self_pin(get_last) or pin_in(get_last, "self"))))
    links.append(("pend->add", connect(pin_out(get_pending, "ReturnValue"), pin_in(add_v, "A"))))
    links.append(("last->add", connect(pin_out(get_last, "ReturnValue"), pin_in(add_v, "B"))))
    links.append(("add->size", connect(pin_out(add_v, "ReturnValue"), pin_in(vsize_xy, "A"))))
    links.append(("size->gt", connect(pin_out(vsize_xy, "ReturnValue"), pin_in(gt_in, "A"))))

    links.append(("add->brk", connect(pin_out(add_v, "ReturnValue"), pin_in(brk, "InVec") or pin_in(brk, "A"))))
    links.append(("x->make", connect(pin_out(brk, "X"), pin_in(make_flat, "X"))))
    links.append(("y->make", connect(pin_out(brk, "Y"), pin_in(make_flat, "Y"))))
    links.append(("flat->n", connect(pin_out(make_flat, "ReturnValue"), pin_in(normal, "A"))))

    curr = pin_out(normal, "ReturnValue")
    links.append(("prev->psize", connect(pin_out(get_prev), pin_in(vsize_prev, "A"))))
    links.append(("psize->gt", connect(pin_out(vsize_prev, "ReturnValue"), pin_in(gt_prev, "A"))))
    links.append(("has->and", connect(pin_out(gt_in, "ReturnValue"), pin_in(and_valid, "A"))))
    links.append(("hprev->and", connect(pin_out(gt_prev, "ReturnValue"), pin_in(and_valid, "B"))))

    links.append(("prev->dotA", connect(pin_out(get_prev), pin_in(dot, "A"))))
    links.append(("curr->dotB", connect(curr, pin_in(dot, "B"))))
    links.append(("prev->crossA", connect(pin_out(get_prev), pin_in(cross, "A"))))
    links.append(("curr->crossB", connect(curr, pin_in(cross, "B"))))
    links.append(("cross->brk", connect(pin_out(cross, "ReturnValue"), pin_in(brk_c, "InVec") or pin_in(brk_c, "A"))))
    # DegAtan2(Y, X) = Atan2(Cross.Z, Dot)
    links.append(("z->atanY", connect(pin_out(brk_c, "Z"), pin_in(atan2, "Y") or pin_in(atan2, "A"))))
    links.append(("dot->atanX", connect(pin_out(dot, "ReturnValue"), pin_in(atan2, "X") or pin_in(atan2, "B"))))

    links.append(("atan->selA", connect(pin_out(atan2, "ReturnValue"), pin_in(sel_delta, "A"))))
    links.append(("valid->sel", connect(pin_out(and_valid, "ReturnValue"), pin_in(sel_delta, "bPickA"))))
    links.append(("sel->abs", connect(pin_out(sel_delta, "ReturnValue"), pin_in(abs_f, "A"))))

    links.append(("abs->ge90A", connect(pin_out(abs_f, "ReturnValue"), pin_in(ge_90, "A"))))
    links.append(("th90->ge90B", connect(pin_out(get_th90), pin_in(ge_90, "B"))))
    links.append(("abs->ge180A", connect(pin_out(abs_f, "ReturnValue"), pin_in(ge_180, "A"))))
    links.append(("th180->ge180B", connect(pin_out(get_th180), pin_in(ge_180, "B"))))
    links.append(("abs->lt180A", connect(pin_out(abs_f, "ReturnValue"), pin_in(lt_180, "A"))))
    links.append(("th180->lt180B", connect(pin_out(get_th180), pin_in(lt_180, "B"))))
    links.append(("ge90->and90", connect(pin_out(ge_90, "ReturnValue"), pin_in(and_90, "A"))))
    links.append(("lt180->and90", connect(pin_out(lt_180, "ReturnValue"), pin_in(and_90, "B"))))
    links.append(("and90->f", connect(pin_out(and_90, "ReturnValue"), pin_in(and_90b, "A"))))
    links.append(("valid->f90", connect(pin_out(and_valid, "ReturnValue"), pin_in(and_90b, "B"))))
    links.append(("ge180->f180", connect(pin_out(ge_180, "ReturnValue"), pin_in(and_180b, "A"))))
    links.append(("valid->f180", connect(pin_out(and_valid, "ReturnValue"), pin_in(and_180b, "B"))))

    links.append(("sel->lt0", connect(pin_out(sel_delta, "ReturnValue"), pin_in(lt_zero, "A"))))
    links.append(("lt0->left", connect(pin_out(lt_zero, "ReturnValue"), pin_in(and_left, "A"))))
    links.append(("valid->left", connect(pin_out(and_valid, "ReturnValue"), pin_in(and_left, "B"))))

    # TRUE path: set all then Prev=Curr (pulse: flags true one eval when angle big, prev updates same frame so next frame 0 — 
    # WAIT: if we always set Prev=Curr, turn flags only true when Prev was old. Same frame: flags from old Prev vs Curr, then Prev=Curr. Good pulse.
    links.append(("brT->delta", connect(bel.find_then_pin(br), bel.find_execute_pin(set_delta))))
    links.append(("sel->delta", connect(pin_out(sel_delta, "ReturnValue"), pin_in(set_delta, "MoveYawDelta"))))
    links.append(("delta->abs", connect(bel.find_then_pin(set_delta), bel.find_execute_pin(set_abs))))
    links.append(("absv->set", connect(pin_out(abs_f, "ReturnValue"), pin_in(set_abs, "AbsMoveYawDelta"))))
    links.append(("abs->left", connect(bel.find_then_pin(set_abs), bel.find_execute_pin(set_left))))
    links.append(("leftv->set", connect(pin_out(and_left, "ReturnValue"), pin_in(set_left, "bTurnLeft"))))
    links.append(("left->t90", connect(bel.find_then_pin(set_left), bel.find_execute_pin(set_t90))))
    links.append(("t90v->set", connect(pin_out(and_90b, "ReturnValue"), pin_in(set_t90, "bWantsTurn90"))))
    links.append(("t90->t180", connect(bel.find_then_pin(set_t90), bel.find_execute_pin(set_t180))))
    links.append(("t180v->set", connect(pin_out(and_180b, "ReturnValue"), pin_in(set_t180, "bWantsTurn180"))))
    links.append(("t180->prev", connect(bel.find_then_pin(set_t180), bel.find_execute_pin(set_prev_curr))))
    links.append(("curr->prev", connect(curr, pin_in(set_prev_curr, "PrevMoveDir"))))

    # FALSE path: clear
    links.append(("brE->p0", connect(bel.find_else_pin(br), bel.find_execute_pin(set_prev_zero))))
    links.append(("zero->prev", connect(pin_out(zero_v, "ReturnValue"), pin_in(set_prev_zero, "PrevMoveDir"))))
    links.append(("p0->c90", connect(bel.find_then_pin(set_prev_zero), bel.find_execute_pin(set_t90_f))))
    links.append(("f->c90", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_t90_f, "bWantsTurn90"))))
    links.append(("c90->c180", connect(bel.find_then_pin(set_t90_f), bel.find_execute_pin(set_t180_f))))
    links.append(("f->c180", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_t180_f, "bWantsTurn180"))))
    links.append(("c180->cd", connect(bel.find_then_pin(set_t180_f), bel.find_execute_pin(set_delta_0))))
    links.append(("0->cd", connect(pin_out(lit_0, "ReturnValue"), pin_in(set_delta_0, "MoveYawDelta"))))
    links.append(("cd->ca", connect(bel.find_then_pin(set_delta_0), bel.find_execute_pin(set_abs_0))))
    links.append(("0->ca", connect(pin_out(lit_0, "ReturnValue"), pin_in(set_abs_0, "AbsMoveYawDelta"))))

    # Branch ends intentionally open: Sequence.then1 continues old Update chain same frame.
    if not seq and old:
        links.append(("prev->old", connect(bel.find_then_pin(set_prev_curr), old[0])))
        links.append(("abs0->old", connect(bel.find_then_pin(set_abs_0), old[0])))

    try:
        ed.add_comment_node(
            "Turn vars (WASD dir change, no mouse)\n"
            "bWantsTurn90 / bWantsTurn180 / bTurnLeft\n"
            "MoveYawDelta / AbsMoveYawDelta\n"
            "SM not modified — wire transitions yourself",
            unreal.IntPoint(-1400, 600),
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


def write_readme():
    text = """ABP turn variables (WASD direction change — NOT mouse)

Computed each BlueprintUpdateAnimation from Pawn move input XY.

VARIABLES
---------
MoveYawDelta     float   Signed angle (degrees) from PrevMoveDir to current move input. -180..180
AbsMoveYawDelta  float   Absolute value of MoveYawDelta
bTurnLeft        bool    True when MoveYawDelta < 0 (left turn). If anim side is wrong, swap L/R states.
bWantsTurn90     bool    True this frame when Abs in [TurnAngle90, TurnAngle180) and had a previous dir
bWantsTurn180    bool    True this frame when Abs >= TurnAngle180 and had a previous dir
PrevMoveDir      vector  Last move direction (XY). Cleared when no WASD. (usually no need in SM)
TurnAngle90      float   Default 60 — start counting as 90-turn
TurnAngle180     float   Default 135 — count as 180-turn

HOW THE PULSE WORKS
-------------------
When you switch A->D etc., flags are true for the evaluation where the direction
changed; PrevMoveDir then becomes the new direction so flags go false next frame.
SM transitions usually catch a one-frame true. If not, briefly hold input or lower thresholds.

STATE MACHINE (you wire)
------------------------
From Walk/Run Loop (example):
  -> Turn180L : bWantsTurn180 AND bTurnLeft
  -> Turn180R : bWantsTurn180 AND NOT bTurnLeft
  -> Turn90L  : bWantsTurn90  AND bTurnLeft
  -> Turn90R  : bWantsTurn90  AND NOT bTurnLeft

Turn* -> Loop : Automatic Rule (sequence end)
Turn* -> Stop : bStopInput (optional interrupt)

Do NOT use these for mouse look. Mouse does not change move input direction.

EXAMPLES
--------
A then D  ~180  -> bWantsTurn180
A then S  ~90   -> bWantsTurn90
"""
    path = unreal.Paths.project_content_dir() + "Python/TURN_VARS_README.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    log("wrote TURN_VARS_README.txt")


def run():
    log("start")
    abp = load(ABP)
    ensure_vars(abp)
    wire_compute(abp)
    write_readme()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
