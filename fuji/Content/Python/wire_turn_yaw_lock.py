# -*- coding: utf-8 -*-
"""
Turn yaw lock (anim-only during play):

  Capsule stays on HoldYaw while SM turn anim twists the mesh.
  When latch ends: SetActorRotation once to TargetYaw, Orient ON.

Gates:
  - 原地: grounded + speed < STATIONARY_SPEED + Abs>=60
  - 折返跑: grounded + moving + Abs>=180 threshold (135)
    TargetYaw = InputYaw + RUN_PIVOT_YAW_OFFSET (fixes Mesh/-90 facing)
  - Air: cancel lock, Orient ON
  - Interrupt: |InputYaw-TargetYaw| >= INTERRUPT_ANGLE

Syncs bTurnYawLocked -> AnimBP.
Does not change AnimBP animation assets.
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
LOCK_TIME_90 = 0.55
LOCK_TIME_180 = 0.85
INPUT_EPS = 0.1
TURN_ANGLE_90 = 60.0
TURN_ANGLE_180 = 135.0
INTERRUPT_ANGLE = 45.0
STATIONARY_SPEED = 40.0
# Mesh RelativeYaw is -90; run pivot often needs +90 so capsule matches visual intent.
# If still wrong the other way, set to -90.0
RUN_PIVOT_YAW_OFFSET = 90.0

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[YawLock] {m}")


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


def pin_in(node, *names):
    pins = bel.list_input_pins(node) or []
    for name in names:
        for cand in pins:
            try:
                if str(cand.get_pin_name()) == name:
                    return cand
            except Exception:
                pass
        try:
            p = bel.find_input_pin(node, name)
            if p:
                return p
        except Exception:
            pass
    return None


def pin_out(node, *names):
    pins = bel.list_output_pins(node) or []
    if names:
        for name in names:
            for cand in pins:
                try:
                    if str(cand.get_pin_name()) == name:
                        return cand
                except Exception:
                    pass
            try:
                p = bel.find_output_pin(node, name)
                if p:
                    return p
            except Exception:
                pass
    try:
        r = bel.find_result_pin(node)
        if r:
            return r
    except Exception:
        pass
    return pins[0] if pins else None


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


def make_set_orient(ed, name, x, y):
    n = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName"
    )
    safe_rename(n, name)
    pos(n, x, y)
    set_val(n, "PropertyName", "bOrientRotationToMovement")
    return n


def make_set_rot(ed, name, x, y):
    n = ed.add_call_function_node("/Script/Engine.Actor:K2_SetActorRotation")
    safe_rename(n, name)
    pos(n, x, y)
    set_val(n, "bTeleportPhysics", "false")
    return n


def ensure_abp_locked_var():
    abp = load(ABP)
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(abp, unreal.Name("bTurnYawLocked"), pin)
        log("ABP add bTurnYawLocked")
    except Exception as e:
        log(f"ABP add bTurnYawLocked: {e}")
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    try:
        cdo = unreal.get_default_object(abp.generated_class())
        cdo.set_editor_property("bTurnYawLocked", False)
    except Exception:
        pass
    save(ABP)


def ensure_vars(bp):
    for name, kind in (
        ("TurnYawLockTime", "real"),
        ("TurnYawLockDuration", "real"),
        ("TurnTargetYaw", "real"),
        ("TurnHoldYaw", "real"),
        ("bTurnYawLocked", "bool"),
    ):
        try:
            if kind == "bool":
                pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            else:
                try:
                    pin = bel.get_basic_type_by_name(unreal.Name("real"))
                except Exception:
                    pin = bel.get_basic_type_by_name(unreal.Name("double"))
            bel.add_member_variable(bp, unreal.Name(name), pin)
            log(f"add {name}")
        except Exception as e:
            log(f"add {name}: {e}")
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    for n, v in (
        ("TurnYawLockTime", 0.0),
        ("TurnYawLockDuration", 0.55),
        ("TurnTargetYaw", 0.0),
        ("TurnHoldYaw", 0.0),
        ("bTurnYawLocked", False),
    ):
        try:
            cdo.set_editor_property(n, v)
        except Exception:
            pass
    try:
        move = cdo.get_editor_property("character_movement")
        move.set_editor_property("orient_rotation_to_movement", True)
    except Exception:
        pass
    save(CHAR)


def purge_yl(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_IfThenElse,
        unreal.K2Node_PromotableOperator,
        unreal.EdGraphNode_Comment,
        unreal.K2Node_ExecutionSequence,
        unreal.K2Node_CallArrayFunction,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("YL_") or name.startswith("YL_DEL_") or "YawLock" in title:
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
            n.rename(f"YL_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")


def find_attach(graph):
    for name in ("LC_SetHasInput", "WW_SetSpd", "SW_SetProp", "WW_SetBool"):
        for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
            try:
                if n.get_outer() == graph and n.get_name() == name:
                    log(f"attach after {name}")
                    return bel.find_then_pin(n), n
            except Exception:
                pass
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
                log("attach after Tick")
                return bel.find_then_pin(n), n
        except Exception:
            pass
    return None, None


def run():
    log("start")
    ensure_abp_locked_var()
    bp = load(CHAR)
    ensure_vars(bp)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    attach, _ = find_attach(graph)
    if not attach:
        raise RuntimeError("no attach pin")

    old = list(attach.list_connected_pins() or [])
    keep_old = []
    old_names = []
    for p in old:
        try:
            nm = p.get_owning_node().get_name()
            old_names.append(nm)
            if nm.startswith("YL_") or nm.startswith("YL_DEL_"):
                continue
            keep_old.append(p)
        except Exception:
            pass
    log(f"old then -> {old_names} keep={len(keep_old)}")
    attach.break_pin_links()
    purge_yl(ed, graph)

    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
                tick = n
                break
        except Exception:
            pass

    # --- sync bTurnYawLocked to AnimBP ---
    sync_mesh = ed.add_get_member_variable_node("Mesh")
    safe_rename(sync_mesh, "YL_SyncMesh")
    pos(sync_mesh, -200, 2400)

    sync_anim = ed.add_call_function_node(
        "/Script/Engine.SkeletalMeshComponent:GetAnimInstance"
    )
    safe_rename(sync_anim, "YL_SyncAnim")
    pos(sync_anim, 50, 2400)

    sync_lit = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralName"
    )
    safe_rename(sync_lit, "YL_SyncName")
    pos(sync_lit, 50, 2520)
    if not set_val(sync_lit, "Value", "bTurnYawLocked"):
        set_val(sync_lit, "value", "bTurnYawLocked")

    sync_get = ed.add_get_member_variable_node("bTurnYawLocked")
    safe_rename(sync_get, "YL_SyncGet")
    pos(sync_get, 50, 2620)

    sync_prop = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName"
    )
    safe_rename(sync_prop, "YL_SyncProp")
    pos(sync_prop, 300, 2400)
    set_val(sync_prop, "PropertyName", "bTurnYawLocked")

    # --- input / facing ---
    get_pend = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetPendingMovementInputVector"
    )
    safe_rename(get_pend, "YL_Pend")
    pos(get_pend, -200, 2800)

    get_last = ed.add_call_function_node(
        "/Script/Engine.Pawn:GetLastMovementInputVector"
    )
    safe_rename(get_last, "YL_Last")
    pos(get_last, -200, 2930)

    add_v = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_VectorVector")
    safe_rename(add_v, "YL_AddIn")
    pos(add_v, 50, 2860)

    vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSizeXY")
    if not vsize:
        vsize = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(vsize, "YL_VSize")
    pos(vsize, 280, 2750)

    gt_in = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
    safe_rename(gt_in, "YL_HasIn")
    pos(gt_in, 500, 2750)
    set_val(gt_in, "B", str(INPUT_EPS))

    brk = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector")
    safe_rename(brk, "YL_BrkIn")
    pos(brk, 280, 2900)

    atan = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2")
    safe_rename(atan, "YL_InputYaw")
    pos(atan, 500, 2900)

    get_rot = ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation")
    safe_rename(get_rot, "YL_GetRot")
    pos(get_rot, 50, 3100)

    brk_rot = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakRotator")
    safe_rename(brk_rot, "YL_BrkRot")
    pos(brk_rot, 280, 3100)

    sub_yaw = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"
    )
    if not sub_yaw:
        sub_yaw = ed.add_call_function_node(
            "/Script/Engine.KismetMathLibrary:Subtract_FloatFloat"
        )
    safe_rename(sub_yaw, "YL_SubYaw")
    pos(sub_yaw, 500, 3050)

    norm = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm, "YL_Norm")
    pos(norm, 720, 3050)

    abs_d = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs")
    if not abs_d:
        abs_d = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs_Double")
    if not abs_d:
        abs_d = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs_Float")
    safe_rename(abs_d, "YL_Abs")
    pos(abs_d, 920, 3050)

    gt_turn = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(gt_turn, "YL_GtTurn")
    pos(gt_turn, 1120, 3050)
    set_val(gt_turn, "B", str(TURN_ANGLE_90))

    and_want = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_want, "YL_AndWant")
    pos(and_want, 1320, 2900)

    # grounded
    is_grounded = None
    for path in (
        "/Script/Engine.CharacterMovementComponent:IsMovingOnGround",
        "/Script/Engine.NavMovementComponent:IsMovingOnGround",
    ):
        is_grounded = ed.add_call_function_node(path)
        if is_grounded:
            log(f"ground: {path}")
            break
    if not is_grounded:
        raise RuntimeError("IsMovingOnGround missing")
    safe_rename(is_grounded, "YL_OnGround")
    pos(is_grounded, 1120, 2780)

    not_grounded = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_grounded, "YL_NotGround")
    pos(not_grounded, 1320, 2780)

    # stationary
    get_vel = ed.add_call_function_node("/Script/Engine.Actor:GetVelocity")
    safe_rename(get_vel, "YL_GetVel")
    pos(get_vel, 920, 2680)

    spd = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSizeXY")
    if not spd:
        spd = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:VSize")
    safe_rename(spd, "YL_SpdXY")
    pos(spd, 1120, 2680)

    gt_moving = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Greater_FloatFloat"
    )
    safe_rename(gt_moving, "YL_GtMoving")
    pos(gt_moving, 1320, 2680)
    set_val(gt_moving, "B", str(STATIONARY_SPEED))

    not_moving = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_moving, "YL_NotMoving")
    pos(not_moving, 1520, 2680)

    gt_180 = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(gt_180, "YL_Gt180")
    pos(gt_180, 1120, 3200)
    set_val(gt_180, "B", str(TURN_ANGLE_180))

    # start if: grounded && ( (stationary && want60) || (moving && want180) )
    and_want_180 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_want_180, "YL_AndWant180")
    pos(and_want_180, 1520, 3000)

    and_idle_start = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_idle_start, "YL_AndIdleStart")
    pos(and_idle_start, 1720, 2880)

    or_start = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_start, "YL_OrStart")
    pos(or_start, 1920, 2940)

    and_want_gnd = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_want_gnd, "YL_AndWantGnd")
    pos(and_want_gnd, 2120, 2900)

    # TargetYaw: moving pivot -> InputYaw + OFFSET; idle -> InputYaw
    lit_off = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralDouble"
    )
    if not lit_off:
        lit_off = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary:MakeLiteralFloat"
        )
    safe_rename(lit_off, "YL_LitOff")
    pos(lit_off, 500, 3350)
    set_val(lit_off, "Value", str(RUN_PIVOT_YAW_OFFSET))

    add_off = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Add_DoubleDouble"
    )
    if not add_off:
        add_off = ed.add_call_function_node(
            "/Script/Engine.KismetMathLibrary:Add_FloatFloat"
        )
    safe_rename(add_off, "YL_AddOff")
    pos(add_off, 720, 3300)

    norm_off = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm_off, "YL_NormOff")
    pos(norm_off, 920, 3300)

    sel_tgt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    safe_rename(sel_tgt, "YL_SelTgt")
    pos(sel_tgt, 1120, 3300)

    sel_lock = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    safe_rename(sel_lock, "YL_SelLock")
    pos(sel_lock, 1320, 3200)

    lit_90 = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralDouble"
    )
    if not lit_90:
        lit_90 = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary:MakeLiteralFloat"
        )
    safe_rename(lit_90, "YL_Lit90")
    pos(lit_90, 920, 3300)
    set_val(lit_90, "Value", str(LOCK_TIME_90))

    lit_180 = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralDouble"
    )
    if not lit_180:
        lit_180 = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary:MakeLiteralFloat"
        )
    safe_rename(lit_180, "YL_Lit180")
    pos(lit_180, 920, 3420)
    set_val(lit_180, "Value", str(LOCK_TIME_180))

    get_locked = ed.add_get_member_variable_node("bTurnYawLocked")
    safe_rename(get_locked, "YL_GetLocked")
    pos(get_locked, 1320, 2550)

    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    safe_rename(get_cmc, "YL_CMC")
    pos(get_cmc, 50, 2550)

    lit_name = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralName"
    )
    safe_rename(lit_name, "YL_LitName")
    pos(lit_name, 280, 2550)
    if not set_val(lit_name, "Value", "bOrientRotationToMovement"):
        set_val(lit_name, "value", "bOrientRotationToMovement")

    lit_f = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralBool"
    )
    safe_rename(lit_f, "YL_LitF")
    pos(lit_f, 500, 2550)
    set_val(lit_f, "Value", "false")

    lit_t = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralBool"
    )
    safe_rename(lit_t, "YL_LitT")
    pos(lit_t, 500, 2650)
    set_val(lit_t, "Value", "true")

    lit_zero = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralDouble"
    )
    if not lit_zero:
        lit_zero = ed.add_call_function_node(
            "/Script/Engine.KismetSystemLibrary:MakeLiteralFloat"
        )
    safe_rename(lit_zero, "YL_LitZero")
    pos(lit_zero, 500, 2720)
    set_val(lit_zero, "Value", "0.0")

    get_hold = ed.add_get_member_variable_node("TurnHoldYaw")
    safe_rename(get_hold, "YL_GetHold")
    pos(get_hold, 2000, 2500)

    get_target = ed.add_get_member_variable_node("TurnTargetYaw")
    safe_rename(get_target, "YL_GetTarget")
    pos(get_target, 2000, 2580)

    get_lock_t = ed.add_get_member_variable_node("TurnYawLockTime")
    safe_rename(get_lock_t, "YL_GetLockT")
    pos(get_lock_t, 2000, 2660)

    # branches
    br_air = ed.add_branch_node()
    safe_rename(br_air, "YL_BrAir")
    pos(br_air, 1600, 2850)

    br_locked = ed.add_branch_node()
    safe_rename(br_locked, "YL_BrLocked")
    pos(br_locked, 1850, 3000)

    br_it = ed.add_branch_node()
    safe_rename(br_it, "YL_BrIT")
    pos(br_it, 2200, 2850)

    br_remain = ed.add_branch_node()
    safe_rename(br_remain, "YL_BrRemain")
    pos(br_remain, 3200, 3000)

    br_want = ed.add_branch_node()
    safe_rename(br_want, "YL_BrWant")
    pos(br_want, 1850, 3300)

    # air cancel
    set_locked_air = ed.add_set_member_variable_node("bTurnYawLocked")
    safe_rename(set_locked_air, "YL_SetLockedAir")
    pos(set_locked_air, 1850, 3500)

    zero_lock_air = ed.add_set_member_variable_node("TurnYawLockTime")
    safe_rename(zero_lock_air, "YL_ZeroLockAir")
    pos(zero_lock_air, 2050, 3500)

    set_orient_air = make_set_orient(ed, "YL_OrientAir", 2250, 3500)

    # interrupt: |Input-Target| >= 45
    sub_it = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"
    )
    if not sub_it:
        sub_it = ed.add_call_function_node(
            "/Script/Engine.KismetMathLibrary:Subtract_FloatFloat"
        )
    safe_rename(sub_it, "YL_SubIT")
    pos(sub_it, 2000, 2300)

    norm_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm_it, "YL_NormIT")
    pos(norm_it, 2200, 2300)

    abs_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs")
    if not abs_it:
        abs_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs_Double")
    if not abs_it:
        abs_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Abs_Float")
    safe_rename(abs_it, "YL_AbsIT")
    pos(abs_it, 2400, 2300)

    gt_it = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat"
    )
    safe_rename(gt_it, "YL_GtIT")
    pos(gt_it, 2600, 2300)
    set_val(gt_it, "B", str(INTERRUPT_ANGLE))

    and_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_it, "YL_AndIT")
    pos(and_it, 2800, 2300)

    make_it = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
    safe_rename(make_it, "YL_MakeIT")
    pos(make_it, 3000, 2200)

    set_rot_it = make_set_rot(ed, "YL_SetRotIT", 3200, 2200)

    set_locked_it = ed.add_set_member_variable_node("bTurnYawLocked")
    safe_rename(set_locked_it, "YL_SetLockedIT")
    pos(set_locked_it, 3400, 2200)

    zero_lock_it = ed.add_set_member_variable_node("TurnYawLockTime")
    safe_rename(zero_lock_it, "YL_ZeroLockIT")
    pos(zero_lock_it, 3600, 2200)

    set_orient_it = make_set_orient(ed, "YL_OrientIT", 3800, 2200)

    # locked continue: freeze HoldYaw (anim-only), countdown
    set_orient_off_l = make_set_orient(ed, "YL_OrientOffL", 2400, 2700)

    make_hold = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
    safe_rename(make_hold, "YL_MakeHold")
    pos(make_hold, 2600, 2550)

    set_rot_hold = make_set_rot(ed, "YL_SetRotHold", 2800, 2550)

    sub_dt = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Subtract_DoubleDouble"
    )
    if not sub_dt:
        sub_dt = ed.add_call_function_node(
            "/Script/Engine.KismetMathLibrary:Subtract_FloatFloat"
        )
    safe_rename(sub_dt, "YL_SubDT")
    pos(sub_dt, 2800, 2750)

    max0 = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:FMax")
    safe_rename(max0, "YL_Max0")
    pos(max0, 3000, 2750)
    set_val(max0, "B", "0.0")

    set_lock_dec = ed.add_set_member_variable_node("TurnYawLockTime")
    safe_rename(set_lock_dec, "YL_SetLockDec")
    pos(set_lock_dec, 3200, 2750)

    gt_remain = ed.add_call_function_node(
        "/Script/Engine.KismetMathLibrary:Greater_FloatFloat"
    )
    safe_rename(gt_remain, "YL_GtRemain")
    pos(gt_remain, 3400, 2750)
    set_val(gt_remain, "B", "0.0")

    # finish: apply Target once
    make_tgt = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
    safe_rename(make_tgt, "YL_MakeTgt")
    pos(make_tgt, 3400, 2950)

    set_rot_tgt = make_set_rot(ed, "YL_SetRotTgt", 3600, 2950)

    set_locked_f = ed.add_set_member_variable_node("bTurnYawLocked")
    safe_rename(set_locked_f, "YL_SetLockedF")
    pos(set_locked_f, 3800, 2950)

    set_orient_on = make_set_orient(ed, "YL_OrientOn", 4000, 2950)

    # start
    set_hold = ed.add_set_member_variable_node("TurnHoldYaw")
    safe_rename(set_hold, "YL_SetHold")
    pos(set_hold, 2100, 3200)

    set_target = ed.add_set_member_variable_node("TurnTargetYaw")
    safe_rename(set_target, "YL_SetTarget")
    pos(set_target, 2300, 3200)

    set_dur = ed.add_set_member_variable_node("TurnYawLockDuration")
    safe_rename(set_dur, "YL_SetDur")
    pos(set_dur, 2500, 3200)

    set_lock_start = ed.add_set_member_variable_node("TurnYawLockTime")
    safe_rename(set_lock_start, "YL_SetLockStart")
    pos(set_lock_start, 2700, 3200)

    set_locked_t = ed.add_set_member_variable_node("bTurnYawLocked")
    safe_rename(set_locked_t, "YL_SetLockedT")
    pos(set_locked_t, 2900, 3200)

    set_orient_off_s = make_set_orient(ed, "YL_OrientOffS", 3100, 3200)

    set_orient_idle = make_set_orient(ed, "YL_OrientIdle", 2100, 3450)

    links = []

    # data
    links.append(("pend->add", connect(pin_out(get_pend, "ReturnValue"), pin_in(add_v, "A"))))
    links.append(("last->add", connect(pin_out(get_last, "ReturnValue"), pin_in(add_v, "B"))))
    links.append(("add->size", connect(pin_out(add_v, "ReturnValue"), pin_in(vsize, "A"))))
    links.append(("size->gt", connect(pin_out(vsize, "ReturnValue"), pin_in(gt_in, "A"))))
    links.append(
        ("add->brk", connect(pin_out(add_v, "ReturnValue"), pin_in(brk, "InVec", "A")))
    )
    links.append(("Y->atan", connect(pin_out(brk, "Y"), pin_in(atan, "Y", "A"))))
    links.append(("X->atan", connect(pin_out(brk, "X"), pin_in(atan, "X", "B"))))
    links.append(
        (
            "rot->brk",
            connect(pin_out(get_rot, "ReturnValue"), pin_in(brk_rot, "InRot", "A")),
        )
    )
    links.append(("iy->sub", connect(pin_out(atan, "ReturnValue"), pin_in(sub_yaw, "A"))))
    links.append(("ay->sub", connect(pin_out(brk_rot, "Yaw"), pin_in(sub_yaw, "B"))))
    links.append(
        (
            "sub->norm",
            connect(pin_out(sub_yaw, "ReturnValue"), pin_in(norm, "Angle", "A")),
        )
    )
    links.append(("norm->abs", connect(pin_out(norm, "ReturnValue"), pin_in(abs_d, "A"))))
    links.append(("abs->gt", connect(pin_out(abs_d, "ReturnValue"), pin_in(gt_turn, "A"))))
    links.append(
        ("has->and", connect(pin_out(gt_in, "ReturnValue"), pin_in(and_want, "A")))
    )
    links.append(
        ("gt->and", connect(pin_out(gt_turn, "ReturnValue"), pin_in(and_want, "B")))
    )

    gself = bel.find_self_pin(is_grounded) or pin_in(is_grounded, "self")
    links.append(("cmc->gnd", connect(pin_out(get_cmc), gself)))
    links.append(
        (
            "gnd->ng",
            connect(pin_out(is_grounded, "ReturnValue"), pin_in(not_grounded, "A")),
        )
    )
    links.append(
        ("vel->spd", connect(pin_out(get_vel, "ReturnValue"), pin_in(spd, "A")))
    )
    links.append(
        ("spd->gtm", connect(pin_out(spd, "ReturnValue"), pin_in(gt_moving, "A")))
    )
    links.append(
        (
            "gtm->nm",
            connect(pin_out(gt_moving, "ReturnValue"), pin_in(not_moving, "A")),
        )
    )
    links.append(("abs->180", connect(pin_out(abs_d, "ReturnValue"), pin_in(gt_180, "A"))))
    # want180 = hasInput AND Abs>=135
    links.append(
        ("has->w180", connect(pin_out(gt_in, "ReturnValue"), pin_in(and_want_180, "A")))
    )
    links.append(
        ("g180->w180", connect(pin_out(gt_180, "ReturnValue"), pin_in(and_want_180, "B")))
    )
    # idle start = stationary AND want60
    links.append(
        (
            "nm->idle",
            connect(pin_out(not_moving, "ReturnValue"), pin_in(and_idle_start, "A")),
        )
    )
    links.append(
        (
            "want->idle",
            connect(pin_out(and_want, "ReturnValue"), pin_in(and_idle_start, "B")),
        )
    )
    # or_start = idle_start OR want180
    links.append(
        (
            "idle->or",
            connect(pin_out(and_idle_start, "ReturnValue"), pin_in(or_start, "A")),
        )
    )
    links.append(
        (
            "w180->or",
            connect(pin_out(and_want_180, "ReturnValue"), pin_in(or_start, "B")),
        )
    )
    # want_gnd = grounded AND or_start
    links.append(
        (
            "gnd->wg",
            connect(pin_out(is_grounded, "ReturnValue"), pin_in(and_want_gnd, "A")),
        )
    )
    links.append(
        (
            "or->wg",
            connect(pin_out(or_start, "ReturnValue"), pin_in(and_want_gnd, "B")),
        )
    )
    # target yaw select: moving ? Normalize(Input+OFFSET) : Input
    links.append(
        ("iy->addo", connect(pin_out(atan, "ReturnValue"), pin_in(add_off, "A")))
    )
    links.append(
        ("off->addo", connect(pin_out(lit_off, "ReturnValue"), pin_in(add_off, "B")))
    )
    links.append(
        (
            "addo->noff",
            connect(pin_out(add_off, "ReturnValue"), pin_in(norm_off, "Angle", "A")),
        )
    )
    links.append(
        (
            "noff->selA",
            connect(pin_out(norm_off, "ReturnValue"), pin_in(sel_tgt, "A")),
        )
    )
    links.append(
        ("iy->selB", connect(pin_out(atan, "ReturnValue"), pin_in(sel_tgt, "B")))
    )
    links.append(
        (
            "mov->sel",
            connect(pin_out(gt_moving, "ReturnValue"), pin_in(sel_tgt, "bPickA")),
        )
    )
    links.append(
        ("lit180->selA", connect(pin_out(lit_180, "ReturnValue"), pin_in(sel_lock, "A")))
    )
    links.append(
        ("lit90->selB", connect(pin_out(lit_90, "ReturnValue"), pin_in(sel_lock, "B")))
    )
    links.append(
        ("gt180->sel", connect(pin_out(gt_180, "ReturnValue"), pin_in(sel_lock, "bPickA")))
    )

    # exec: attach -> sync -> air
    links.append(("att->sync", connect(attach, bel.find_execute_pin(sync_prop))))
    links.append(
        (
            "mesh->anim",
            connect(
                pin_out(sync_mesh),
                bel.find_self_pin(sync_anim) or pin_in(sync_anim, "self"),
            ),
        )
    )
    links.append(
        (
            "anim->obj",
            connect(pin_out(sync_anim, "ReturnValue"), pin_in(sync_prop, "Object")),
        )
    )
    links.append(
        (
            "lit->prop",
            connect(pin_out(sync_lit, "ReturnValue"), pin_in(sync_prop, "PropertyName")),
        )
    )
    links.append(("get->val", connect(pin_out(sync_get), pin_in(sync_prop, "Value"))))
    set_val(sync_prop, "PropertyName", "bTurnYawLocked")

    links.append(
        ("sync->air", connect(bel.find_then_pin(sync_prop), bel.find_execute_pin(br_air)))
    )
    links.append(
        (
            "ng->air",
            connect(pin_out(not_grounded, "ReturnValue"), bel.find_condition_pin(br_air)),
        )
    )

    # AIR cancel
    links.append(
        (
            "airT->lk",
            connect(bel.find_then_pin(br_air), bel.find_execute_pin(set_locked_air)),
        )
    )
    links.append(
        (
            "f->lkair",
            connect(
                pin_out(lit_f, "ReturnValue"), pin_in(set_locked_air, "bTurnYawLocked")
            ),
        )
    )
    links.append(
        (
            "lkair->z",
            connect(bel.find_then_pin(set_locked_air), bel.find_execute_pin(zero_lock_air)),
        )
    )
    links.append(
        (
            "0->zair",
            connect(
                pin_out(lit_zero, "ReturnValue"),
                pin_in(zero_lock_air, "TurnYawLockTime"),
            ),
        )
    )
    links.append(
        (
            "zair->or",
            connect(bel.find_then_pin(zero_lock_air), bel.find_execute_pin(set_orient_air)),
        )
    )
    links.append(
        ("cmc->orair", connect(pin_out(get_cmc), pin_in(set_orient_air, "Object")))
    )
    links.append(
        (
            "name->orair",
            connect(
                pin_out(lit_name, "ReturnValue"), pin_in(set_orient_air, "PropertyName")
            ),
        )
    )
    links.append(
        (
            "t->orair",
            connect(pin_out(lit_t, "ReturnValue"), pin_in(set_orient_air, "Value")),
        )
    )
    set_val(set_orient_air, "PropertyName", "bOrientRotationToMovement")

    links.append(
        (
            "airE->brL",
            connect(bel.find_else_pin(br_air), bel.find_execute_pin(br_locked)),
        )
    )
    links.append(
        ("lk->brL", connect(pin_out(get_locked), bel.find_condition_pin(br_locked)))
    )

    # LOCKED -> interrupt check
    links.append(
        ("LT->brit", connect(bel.find_then_pin(br_locked), bel.find_execute_pin(br_it)))
    )
    # compare corrected facing yaw vs stored target (not raw Input vs Target+90)
    links.append(
        ("selt->sit", connect(pin_out(sel_tgt, "ReturnValue"), pin_in(sub_it, "A")))
    )
    links.append(("tgt->sit", connect(pin_out(get_target), pin_in(sub_it, "B"))))
    links.append(
        (
            "sit->nit",
            connect(pin_out(sub_it, "ReturnValue"), pin_in(norm_it, "Angle", "A")),
        )
    )
    links.append(
        ("nit->ait", connect(pin_out(norm_it, "ReturnValue"), pin_in(abs_it, "A")))
    )
    links.append(
        ("ait->git", connect(pin_out(abs_it, "ReturnValue"), pin_in(gt_it, "A")))
    )
    links.append(
        ("has->andit", connect(pin_out(gt_in, "ReturnValue"), pin_in(and_it, "A")))
    )
    links.append(
        ("git->andit", connect(pin_out(gt_it, "ReturnValue"), pin_in(and_it, "B")))
    )
    links.append(
        (
            "andit->brit",
            connect(pin_out(and_it, "ReturnValue"), bel.find_condition_pin(br_it)),
        )
    )

    # interrupt TRUE
    links.append(
        (
            "ITT->srot",
            connect(bel.find_then_pin(br_it), bel.find_execute_pin(set_rot_it)),
        )
    )
    links.append(
        ("p->mit", connect(pin_out(brk_rot, "Pitch"), pin_in(make_it, "Pitch", "A")))
    )
    # interrupt face same corrected target yaw
    links.append(
        (
            "selt->mit",
            connect(pin_out(sel_tgt, "ReturnValue"), pin_in(make_it, "Yaw", "B")),
        )
    )
    links.append(
        ("r->mit", connect(pin_out(brk_rot, "Roll"), pin_in(make_it, "Roll", "C")))
    )
    links.append(
        (
            "mit->srot",
            connect(pin_out(make_it, "ReturnValue"), pin_in(set_rot_it, "NewRotation")),
        )
    )
    links.append(
        (
            "srotit->lk",
            connect(bel.find_then_pin(set_rot_it), bel.find_execute_pin(set_locked_it)),
        )
    )
    links.append(
        (
            "f->lkit",
            connect(
                pin_out(lit_f, "ReturnValue"), pin_in(set_locked_it, "bTurnYawLocked")
            ),
        )
    )
    links.append(
        (
            "lkit->z",
            connect(bel.find_then_pin(set_locked_it), bel.find_execute_pin(zero_lock_it)),
        )
    )
    links.append(
        (
            "0->zit",
            connect(
                pin_out(lit_zero, "ReturnValue"),
                pin_in(zero_lock_it, "TurnYawLockTime"),
            ),
        )
    )
    links.append(
        (
            "zit->or",
            connect(bel.find_then_pin(zero_lock_it), bel.find_execute_pin(set_orient_it)),
        )
    )
    links.append(
        ("cmc->orit", connect(pin_out(get_cmc), pin_in(set_orient_it, "Object")))
    )
    links.append(
        (
            "name->orit",
            connect(
                pin_out(lit_name, "ReturnValue"), pin_in(set_orient_it, "PropertyName")
            ),
        )
    )
    links.append(
        ("t->orit", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_orient_it, "Value")))
    )
    set_val(set_orient_it, "PropertyName", "bOrientRotationToMovement")

    # interrupt FALSE: freeze hold + countdown (anim rotates visually)
    links.append(
        (
            "ITE->off",
            connect(bel.find_else_pin(br_it), bel.find_execute_pin(set_orient_off_l)),
        )
    )
    links.append(
        ("cmc->offL", connect(pin_out(get_cmc), pin_in(set_orient_off_l, "Object")))
    )
    links.append(
        (
            "name->offL",
            connect(
                pin_out(lit_name, "ReturnValue"), pin_in(set_orient_off_l, "PropertyName")
            ),
        )
    )
    links.append(
        ("f->offL", connect(pin_out(lit_f, "ReturnValue"), pin_in(set_orient_off_l, "Value")))
    )
    set_val(set_orient_off_l, "PropertyName", "bOrientRotationToMovement")

    links.append(
        (
            "offL->hold",
            connect(bel.find_then_pin(set_orient_off_l), bel.find_execute_pin(set_rot_hold)),
        )
    )
    links.append(
        ("p->mhold", connect(pin_out(brk_rot, "Pitch"), pin_in(make_hold, "Pitch", "A")))
    )
    links.append(
        ("hold->mhold", connect(pin_out(get_hold), pin_in(make_hold, "Yaw", "B")))
    )
    links.append(
        ("r->mhold", connect(pin_out(brk_rot, "Roll"), pin_in(make_hold, "Roll", "C")))
    )
    links.append(
        (
            "mhold->srot",
            connect(pin_out(make_hold, "ReturnValue"), pin_in(set_rot_hold, "NewRotation")),
        )
    )
    links.append(
        (
            "sroth->dec",
            connect(bel.find_then_pin(set_rot_hold), bel.find_execute_pin(set_lock_dec)),
        )
    )
    links.append(("lt->subA", connect(pin_out(get_lock_t), pin_in(sub_dt, "A"))))
    if tick:
        ds = None
        for p in bel.list_output_pins(tick) or []:
            if str(p.get_pin_name()) in ("DeltaSeconds", "Delta Time", "DeltaTimeX"):
                ds = p
                break
        if ds:
            links.append(("dt->subB", connect(ds, pin_in(sub_dt, "B"))))
        else:
            set_val(sub_dt, "B", "0.016")
    else:
        set_val(sub_dt, "B", "0.016")
    links.append(("sub->max", connect(pin_out(sub_dt, "ReturnValue"), pin_in(max0, "A"))))
    links.append(
        (
            "max->dec",
            connect(pin_out(max0, "ReturnValue"), pin_in(set_lock_dec, "TurnYawLockTime")),
        )
    )
    links.append(
        (
            "dec->brR",
            connect(bel.find_then_pin(set_lock_dec), bel.find_execute_pin(br_remain)),
        )
    )
    links.append(
        ("max->gtR", connect(pin_out(max0, "ReturnValue"), pin_in(gt_remain, "A")))
    )
    links.append(
        (
            "gtR->brR",
            connect(pin_out(gt_remain, "ReturnValue"), bel.find_condition_pin(br_remain)),
        )
    )

    # remain FALSE -> apply target (anim done)
    links.append(
        (
            "RF->tgt",
            connect(bel.find_else_pin(br_remain), bel.find_execute_pin(set_rot_tgt)),
        )
    )
    links.append(
        ("p->mtgt", connect(pin_out(brk_rot, "Pitch"), pin_in(make_tgt, "Pitch", "A")))
    )
    links.append(
        ("tgt->mtgt", connect(pin_out(get_target), pin_in(make_tgt, "Yaw", "B")))
    )
    links.append(
        ("r->mtgt", connect(pin_out(brk_rot, "Roll"), pin_in(make_tgt, "Roll", "C")))
    )
    links.append(
        (
            "mtgt->srott",
            connect(pin_out(make_tgt, "ReturnValue"), pin_in(set_rot_tgt, "NewRotation")),
        )
    )
    links.append(
        (
            "srott->lkf",
            connect(bel.find_then_pin(set_rot_tgt), bel.find_execute_pin(set_locked_f)),
        )
    )
    links.append(
        (
            "f->lkf",
            connect(pin_out(lit_f, "ReturnValue"), pin_in(set_locked_f, "bTurnYawLocked")),
        )
    )
    links.append(
        (
            "lkf->on",
            connect(bel.find_then_pin(set_locked_f), bel.find_execute_pin(set_orient_on)),
        )
    )
    links.append(("cmc->on", connect(pin_out(get_cmc), pin_in(set_orient_on, "Object"))))
    links.append(
        (
            "name->on",
            connect(pin_out(lit_name, "ReturnValue"), pin_in(set_orient_on, "PropertyName")),
        )
    )
    links.append(
        ("t->on", connect(pin_out(lit_t, "ReturnValue"), pin_in(set_orient_on, "Value")))
    )
    set_val(set_orient_on, "PropertyName", "bOrientRotationToMovement")

    # NOT locked -> start if 原地 wants turn
    links.append(
        (
            "LE->bw",
            connect(bel.find_else_pin(br_locked), bel.find_execute_pin(br_want)),
        )
    )
    links.append(
        (
            "want->bw",
            connect(pin_out(and_want_gnd, "ReturnValue"), bel.find_condition_pin(br_want)),
        )
    )
    links.append(
        (
            "WT->hold",
            connect(bel.find_then_pin(br_want), bel.find_execute_pin(set_hold)),
        )
    )
    links.append(
        ("ay->hold", connect(pin_out(brk_rot, "Yaw"), pin_in(set_hold, "TurnHoldYaw")))
    )
    links.append(
        (
            "hold->tgt",
            connect(bel.find_then_pin(set_hold), bel.find_execute_pin(set_target)),
        )
    )
    links.append(
        (
            "selt->tgt",
            connect(
                pin_out(sel_tgt, "ReturnValue"), pin_in(set_target, "TurnTargetYaw")
            ),
        )
    )
    links.append(
        (
            "tgt->dur",
            connect(bel.find_then_pin(set_target), bel.find_execute_pin(set_dur)),
        )
    )
    links.append(
        (
            "sel->dur",
            connect(
                pin_out(sel_lock, "ReturnValue"),
                pin_in(set_dur, "TurnYawLockDuration"),
            ),
        )
    )
    links.append(
        (
            "dur->lks",
            connect(bel.find_then_pin(set_dur), bel.find_execute_pin(set_lock_start)),
        )
    )
    links.append(
        (
            "sel->lks",
            connect(
                pin_out(sel_lock, "ReturnValue"),
                pin_in(set_lock_start, "TurnYawLockTime"),
            ),
        )
    )
    links.append(
        (
            "lks->lkt",
            connect(bel.find_then_pin(set_lock_start), bel.find_execute_pin(set_locked_t)),
        )
    )
    links.append(
        (
            "t->lkt",
            connect(pin_out(lit_t, "ReturnValue"), pin_in(set_locked_t, "bTurnYawLocked")),
        )
    )
    links.append(
        (
            "lkt->offs",
            connect(bel.find_then_pin(set_locked_t), bel.find_execute_pin(set_orient_off_s)),
        )
    )
    links.append(
        ("cmc->offs", connect(pin_out(get_cmc), pin_in(set_orient_off_s, "Object")))
    )
    links.append(
        (
            "name->offs",
            connect(
                pin_out(lit_name, "ReturnValue"), pin_in(set_orient_off_s, "PropertyName")
            ),
        )
    )
    links.append(
        (
            "f->offs",
            connect(pin_out(lit_f, "ReturnValue"), pin_in(set_orient_off_s, "Value")),
        )
    )
    set_val(set_orient_off_s, "PropertyName", "bOrientRotationToMovement")

    links.append(
        (
            "WE->idle",
            connect(bel.find_else_pin(br_want), bel.find_execute_pin(set_orient_idle)),
        )
    )
    links.append(
        ("cmc->idle", connect(pin_out(get_cmc), pin_in(set_orient_idle, "Object")))
    )
    links.append(
        (
            "name->idle",
            connect(
                pin_out(lit_name, "ReturnValue"), pin_in(set_orient_idle, "PropertyName")
            ),
        )
    )
    links.append(
        (
            "t->idle",
            connect(pin_out(lit_t, "ReturnValue"), pin_in(set_orient_idle, "Value")),
        )
    )
    set_val(set_orient_idle, "PropertyName", "bOrientRotationToMovement")

    join_src = [
        bel.find_then_pin(set_orient_air),
        bel.find_then_pin(set_orient_it),
        bel.find_then_pin(br_remain),
        bel.find_then_pin(set_orient_on),
        bel.find_then_pin(set_orient_off_s),
        bel.find_then_pin(set_orient_idle),
    ]
    if keep_old:
        for i, jp in enumerate(join_src):
            links.append((f"join{i}->old", connect(jp, keep_old[0])))
        log("reattach old keep")

    try:
        ed.add_comment_node(
            "YawLock v9: 原地 + 折返跑(180)\n"
            "During: freeze HoldYaw + Orient OFF\n"
            "End: apply TargetYaw\n"
            f"Run pivot TargetYaw = InputYaw{RUN_PIVOT_YAW_OFFSET:+.0f}\n"
            f"(flip RUN_PIVOT_YAW_OFFSET to -90 if still wrong)",
            unreal.IntPoint(-250, 2280),
        )
    except Exception:
        pass

    fail = []
    for n, ok in links:
        log(f"link {n}: {ok}")
        if not ok:
            fail.append(n)

    set_val(gt_in, "B", str(INPUT_EPS))
    set_val(gt_turn, "B", str(TURN_ANGLE_90))
    set_val(gt_180, "B", str(TURN_ANGLE_180))
    set_val(gt_it, "B", str(INTERRUPT_ANGLE))
    set_val(gt_moving, "B", str(STATIONARY_SPEED))
    set_val(lit_off, "Value", str(RUN_PIVOT_YAW_OFFSET))
    set_val(lit_90, "Value", str(LOCK_TIME_90))
    set_val(lit_180, "Value", str(LOCK_TIME_180))

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    save(CHAR)
    log(f"done fails={fail}")


if __name__ == "__main__":
    run()
else:
    run()
