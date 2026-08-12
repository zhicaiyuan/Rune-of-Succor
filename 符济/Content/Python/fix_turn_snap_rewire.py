# -*- coding: utf-8 -*-
"""
Rebuild Character turn-end snap (TO_*), chained after LC_SetHasInput.

Attach exec after existing tick chain; use Mesh member get (same as SW_Mesh).
SNAP_YAW_OFFSET=0 — mesh RelativeYaw -90 is visual only; +90 caused facing camera.
"""
from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
SNAP_YAW_OFFSET = 0.0
ATTACH_AFTER = "LC_SetHasInput"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[SnapRewire] {m}")


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


def must(node, label):
    if not node:
        raise RuntimeError(f"failed to create {label}")
    return node


def find_attach(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if n.get_outer() == graph and n.get_name() == ATTACH_AFTER:
            return bel.find_then_pin(n), n
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
            return bel.find_then_pin(n), n
    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if tick:
        return bel.find_then_pin(tick), tick
    return None, None


def purge_to_nodes(ed, graph):
    kill = [
        n
        for n in unreal.ObjectIterator(unreal.EdGraphNode)
        if n.get_outer() == graph and n.get_name().startswith("TO_")
    ]
    if kill:
        ed.remove_nodes(kill)
    log(f"purged {len(kill)} TO_* nodes")


def ensure_char_vars(bp):
    for name, kind in (("bPrevInTurn", "bool"), ("TurnSnapYaw", "real")):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(kind if kind != "real" else "double"))
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception:
            pass


def run():
    bp = load(CHAR)
    ensure_char_vars(bp)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()
    purge_to_nodes(ed, graph)

    attach, attach_node = find_attach(graph)
    if not attach:
        raise RuntimeError(f"attach pin not found ({ATTACH_AFTER})")
    log(f"attach after {attach_node.get_name()}")

    get_mesh = must(ed.add_get_member_variable_node("Mesh"), "Mesh")
    safe_rename(get_mesh, "TO_Mesh")
    pos(get_mesh, 3200, 1200)

    get_anim = must(
        ed.add_call_function_node("/Script/Engine.SkeletalMeshComponent:GetAnimInstance"),
        "GetAnimInstance",
    )
    safe_rename(get_anim, "TO_GetAnim")
    pos(get_anim, 3400, 1200)

    get_state = must(
        ed.add_call_function_node("/Script/Engine.AnimInstance:GetCurrentStateName"),
        "GetCurrentStateName",
    )
    safe_rename(get_state, "TO_GetState")
    pos(get_state, 3620, 1200)
    set_val(get_state, "MachineIndex", "0")

    contains_turn = must(
        ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains"),
        "ContainsTurn",
    )
    safe_rename(contains_turn, "TO_HasTurn")
    pos(contains_turn, 3840, 1180)
    set_val(contains_turn, "Substring", "Turn")

    contains_run = must(
        ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Contains"),
        "ContainsRunTurn",
    )
    safe_rename(contains_run, "TO_HasRunTurn")
    pos(contains_run, 3840, 1260)
    set_val(contains_run, "Substring", "RunTurn")

    or_turn = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR"), "OrTurn")
    safe_rename(or_turn, "TO_OrTurn")
    pos(or_turn, 4060, 1220)

    get_move = must(
        ed.add_call_function_node(
            "/Script/Engine.CharacterMovementComponent:GetLastUpdateVelocity"
        ),
        "GetLastUpdateVelocity",
    )
    safe_rename(get_move, "TO_GetVel")
    pos(get_move, 3840, 1400)

    brk = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector"), "BreakVector")
    safe_rename(brk, "TO_Brk")
    pos(brk, 3840, 1400)

    atan = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2"), "DegAtan2")
    safe_rename(atan, "TO_Atan")
    pos(atan, 4060, 1400)

    add_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if not add_yaw:
        add_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    add_yaw = must(add_yaw, "Add")
    safe_rename(add_yaw, "TO_OffAdd")
    pos(add_yaw, 4180, 1360)
    set_val(add_yaw, "B", str(SNAP_YAW_OFFSET))

    norm_yaw = must(
        ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis"), "NormalizeAxis"
    )
    safe_rename(norm_yaw, "TO_OffNorm")
    pos(norm_yaw, 4360, 1360)

    get_rot = must(
        ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation"),
        "GetActorRotation",
    )
    safe_rename(get_rot, "TO_GetRot")
    pos(get_rot, 4060, 1500)

    brk_rot = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakRotator"), "BreakRotator")
    safe_rename(brk_rot, "TO_BrkRot")
    pos(brk_rot, 4280, 1500)

    make_rot = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator"), "MakeRotator")
    safe_rename(make_rot, "TO_MakeRot")
    pos(make_rot, 4500, 1420)

    set_rot = must(ed.add_call_function_node("/Script/Engine.Actor:K2_SetActorRotation"), "SetActorRotation")
    safe_rename(set_rot, "TO_SetRot")
    pos(set_rot, 4720, 1420)

    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    if not get_cmc:
        get_cmc = ed.add_call_function_node("/Script/Engine.Character:GetCharacterMovement")
    get_cmc = must(get_cmc, "CharacterMovement")
    safe_rename(get_cmc, "TO_GetCMC")
    pos(get_cmc, 3620, 1100)

    set_orient_off = must(
        ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName"),
        "SetOrientOff",
    )
    safe_rename(set_orient_off, "TO_SetOrientOff")
    pos(set_orient_off, 4500, 1100)
    set_val(set_orient_off, "PropertyName", "bOrientRotationToMovement")
    set_val(set_orient_off, "Value", "false")

    set_orient_on = must(
        ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName"),
        "SetOrientOn",
    )
    safe_rename(set_orient_on, "TO_SetOrientOn")
    pos(set_orient_on, 4500, 1260)
    set_val(set_orient_on, "PropertyName", "bOrientRotationToMovement")
    set_val(set_orient_on, "Value", "true")

    get_prev = ed.add_get_member_variable_node("bPrevInTurn")
    get_prev = must(get_prev, "GetPrev")
    safe_rename(get_prev, "TO_GetPrev")
    pos(get_prev, 3840, 1100)

    set_prev = ed.add_set_member_variable_node("bPrevInTurn")
    set_prev = must(set_prev, "SetPrev")
    safe_rename(set_prev, "TO_SetPrev")
    pos(set_prev, 4940, 1200)

    branch_in = must(ed.add_branch_node(), "BranchIn")
    safe_rename(branch_in, "TO_BranchIn")
    pos(branch_in, 3840, 1200)

    not_in_turn = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool"), "Not")
    safe_rename(not_in_turn, "TO_NotInTurn")
    pos(not_in_turn, 4060, 1080)

    and_end = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND"), "And")
    safe_rename(and_end, "TO_AndEnd")
    pos(and_end, 4280, 1080)

    branch_end = must(ed.add_branch_node(), "BranchEnd")
    safe_rename(branch_end, "TO_BranchEnd")
    pos(branch_end, 4500, 1200)

    lit_f = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool"), "NotF")
    safe_rename(lit_f, "TO_LitF")
    pos(lit_f, 4280, 1140)

    lit_t = must(ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool"), "NotT")
    safe_rename(lit_t, "TO_LitT")
    pos(lit_t, 4280, 1180)

    # self refs for pawn calls
    self_mesh = pin_out(get_mesh)
    self_pawn = None
    try:
        self_pawn = bel.find_self_pin(get_move) or pin_in(get_move, "self")
    except Exception:
        self_pawn = pin_in(get_move, "self")

    links = []
    links.append(("mesh->anim", connect(self_mesh, bel.find_self_pin(get_anim) or pin_in(get_anim, "self"))))
    links.append(("anim->state", connect(pin_out(get_anim, "ReturnValue"), bel.find_self_pin(get_state) or pin_in(get_state, "self"))))
    links.append(("state->ct", connect(pin_out(get_state, "ReturnValue"), pin_in(contains_turn, "SearchIn"))))
    links.append(("state->cr", connect(pin_out(get_state, "ReturnValue"), pin_in(contains_run, "SearchIn"))))
    links.append(("ct->or", connect(pin_out(contains_turn, "ReturnValue"), pin_in(or_turn, "A"))))
    links.append(("cr->or", connect(pin_out(contains_run, "ReturnValue"), pin_in(or_turn, "B"))))
    links.append(("cmc->vel", connect(pin_out(get_cmc), bel.find_self_pin(get_move) or pin_in(get_move, "self"))))
    links.append(("vel->brk", connect(pin_out(get_move, "ReturnValue"), pin_in(brk, "InVec"))))
    links.append(("brkY->atan", connect(pin_out(brk, "Y"), pin_in(atan, "Y"))))
    links.append(("brkX->atan", connect(pin_out(brk, "X"), pin_in(atan, "X"))))
    links.append(("atan->add", connect(pin_out(atan, "ReturnValue"), pin_in(add_yaw, "A"))))
    links.append(
        (
            "add->norm",
            connect(pin_out(add_yaw, "ReturnValue"), pin_in(norm_yaw, "Angle") or pin_in(norm_yaw, "A")),
        )
    )
    links.append(
        (
            "norm->yaw",
            connect(
                pin_out(norm_yaw, "ReturnValue"),
                pin_in(make_rot, "Yaw") or pin_in(make_rot, "Y"),
            ),
        )
    )
    links.append(("cmc->rotSelf", connect(pin_out(get_cmc), bel.find_self_pin(get_rot) or pin_in(get_rot, "self"))))
    links.append(("rot->brk", connect(pin_out(get_rot, "ReturnValue"), pin_in(brk_rot, "InRot"))))
    links.append(("pitch", connect(pin_out(brk_rot, "Pitch"), pin_in(make_rot, "Pitch"))))
    links.append(("roll", connect(pin_out(brk_rot, "Roll"), pin_in(make_rot, "Roll"))))
    links.append(("mk->set", connect(pin_out(make_rot, "ReturnValue"), pin_in(set_rot, "NewRotation"))))

    links.append(("inTurn->brIn", connect(pin_out(or_turn, "ReturnValue"), pin_in(branch_in, "Condition"))))
    links.append(("cmc->offObj", connect(pin_out(get_cmc), pin_in(set_orient_off, "Object"))))
    links.append(("cmc->onObj", connect(pin_out(get_cmc), pin_in(set_orient_on, "Object"))))

    links.append(("inTurn->notEnd", connect(pin_out(or_turn, "ReturnValue"), pin_in(not_in_turn, "A"))))
    links.append(("prev->and", connect(pin_out(get_prev, "bPrevInTurn"), pin_in(and_end, "A"))))
    links.append(("not->and", connect(pin_out(not_in_turn, "ReturnValue"), pin_in(and_end, "B"))))
    links.append(("and->brEnd", connect(pin_out(and_end, "ReturnValue"), pin_in(branch_end, "Condition"))))
    links.append(("inTurn->prev", connect(pin_out(or_turn, "ReturnValue"), pin_in(set_prev, "bPrevInTurn"))))

    try:
        schema = unreal.EdGraphSchema_K2()
        self_node = schema.create_node(unreal.K2Node_Self.static_class(), graph)
        safe_rename(self_node, "TO_Self")
        pos(self_node, 3000, 1300)
        self_pin = bel.find_self_pin(self_node) or pin_out(self_node)
        for node in (get_rot, set_rot):
            sp = bel.find_self_pin(node) or pin_in(node, "self")
            links.append((f"self->{node.get_name()}", connect(self_pin, sp)))
    except Exception as e:
        log(f"self node warn: {e}")

    links.append(("attach->brIn", connect(attach, bel.find_execute_pin(branch_in))))
    links.append(("brInT->off", connect(bel.find_then_pin(branch_in), bel.find_execute_pin(set_orient_off))))
    links.append(("brInF->on", connect(bel.find_else_pin(branch_in), bel.find_execute_pin(set_orient_on))))
    links.append(("off->end", connect(bel.find_then_pin(set_orient_off), bel.find_execute_pin(branch_end))))
    links.append(("on->end", connect(bel.find_then_pin(set_orient_on), bel.find_execute_pin(branch_end))))
    links.append(("endT->snap", connect(bel.find_then_pin(branch_end), bel.find_execute_pin(set_rot))))
    links.append(("snap->prev", connect(bel.find_then_pin(set_rot), bel.find_execute_pin(set_prev))))
    links.append(("endF->prev", connect(bel.find_else_pin(branch_end), bel.find_execute_pin(set_prev))))

    for name, ok in links:
        log(f"link {name}: {ok}")

    try:
        gen = bp.generated_class()
        cdo = unreal.get_default_object(gen)
        move = cdo.get_editor_property("character_movement")
        cdo.set_editor_property("use_controller_rotation_yaw", False)
        move.set_editor_property("use_controller_desired_rotation", False)
        move.set_editor_property("orient_rotation_to_movement", True)
    except Exception as e:
        log(f"CDO warn: {e}")

    save(CHAR)
    log("DONE — saved without compile; open BP and Compile. offset=0; anim Import Rotation 0,0,0")


if __name__ == "__main__":
    run()
