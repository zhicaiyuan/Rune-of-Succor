# -*- coding: utf-8 -*-
"""
Hold Left Alt -> bWantsWalk=True -> MaxWalkSpeed=200
Release        -> bWantsWalk=False -> MaxWalkSpeed=600

Single Tick exec chain (does not break Start/Stop):
  Tick -> Set bWantsWalk(IsInputKeyDown LeftAlt)
       -> Set MaxWalkSpeed(SelectFloat 200/600)
       -> previous Tick consumer (Start/Stop branch)
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"

WALK_SPEED = 200.0
RUN_SPEED = 600.0
BOOL_NAME = "bWantsWalk"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[AltWalk] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
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
        except Exception as exc:
            log(f"connect: {exc}")
            return False


def pin_in(node, name):
    try:
        for cand in bel.list_input_pins(node) or []:
            if str(cand.get_pin_name()) == name:
                return cand
        return bel.find_input_pin(node, name)
    except Exception:
        return None


def pin_out(node, name=None):
    try:
        if name:
            for cand in bel.list_output_pins(node) or []:
                if str(cand.get_pin_name()) == name:
                    return cand
            p = bel.find_output_pin(node, name)
            if p:
                return p
        return bel.find_result_pin(node)
    except Exception:
        outs = bel.list_output_pins(node) or []
        return outs[0] if outs else None


def set_val(node, pin_name, value):
    p = pin_in(node, pin_name)
    if not p:
        log(f"no pin {pin_name} on {node.get_name()}")
        return False
    try:
        p.set_pin_value(str(value))
        log(f"default {node.get_name()}.{pin_name}={value}")
        return True
    except Exception as exc:
        log(f"set_val: {exc}")
        return False


def pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        try:
            node.node_pos_x = int(x)
            node.node_pos_y = int(y)
        except Exception:
            pass


def make_key_left_alt():
    try:
        return unreal.Key(key_name=unreal.Name("LeftAlt"))
    except Exception:
        pass
    try:
        k = unreal.Key()
        k.set_editor_property("key_name", unreal.Name("LeftAlt"))
        return k
    except Exception as exc:
        log(f"make_key: {exc}")
        return None


def ensure_imc():
    imc = load(IMC)
    ia = load(IA_WALK)
    key = make_key_left_alt()
    if key is None:
        return False
    try:
        m = imc.map_key(ia, key)
        log(f"map_key LeftAlt->IA_Walk => {m}")
        save(IMC)
        return True
    except Exception as exc:
        log(f"map_key: {exc}")
        return False


def ensure_vars(bp):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        log(f"add {BOOL_NAME}: {bel.add_member_variable(bp, unreal.Name(BOOL_NAME), pin)}")
    except Exception as exc:
        log(f"add bool: {exc}")
    try:
        bel.compile_blueprint(bp)
    except Exception:
        pass
    cdo = unreal.get_default_object(bp.generated_class())
    try:
        cdo.set_editor_property(BOOL_NAME, False)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("max_walk_speed", RUN_SPEED)
    try:
        move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
    except Exception:
        pass
    save(CHAR)


def purge_ww(ed, graph):
    kill = []
    for cls_name in (
        "K2Node_CallFunction",
        "K2Node_VariableGet",
        "K2Node_VariableSet",
        "K2Node_IfThenElse",
        "K2Node_ExecutionSequence",
        "K2Node_GetInputActionValue",
        "EdGraphNode_Comment",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("WW_") or "Alt Walk" in title:
                    kill.append(n)
            except Exception:
                continue
    if not kill:
        return
    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    try:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")
    except Exception as exc:
        log(f"purge: {exc}")


def wire(bp):
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

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
    pos(tick, -1600, 1600)

    then_pin = bel.find_then_pin(tick)
    old_targets = []
    try:
        old_targets = list(then_pin.list_connected_pins() or [])
        # If previous broken run left Tick unconnected, try find SS branch by title
        then_pin.break_pin_links()
        log(f"Tick.then targets={len(old_targets)}")
    except Exception as exc:
        log(f"break: {exc}")

    if not old_targets:
        # recover SS branch: first IfThenElse near SS or any branch with Speed compare upstream
        for n in unreal.ObjectIterator(unreal.K2Node_IfThenElse):
            try:
                if n.get_outer() != graph:
                    continue
                # Prefer one that looks like moving branch — take first without inputs? 
                # Use node with exec pin free / named path
                old_targets = [bel.find_execute_pin(n)]
                log(f"recovered branch {n.get_name()}")
                break
            except Exception:
                continue

    purge_ww(ed, graph)

    # Nodes
    get_pc = ed.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerController")
    is_down = ed.add_call_function_node("/Script/Engine.PlayerController:IsInputKeyDown")
    set_bool = ed.add_set_member_variable_node(BOOL_NAME)
    get_bool = ed.add_get_member_variable_node(BOOL_NAME)
    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    set_spd = ed.add_set_member_variable_node(
        "MaxWalkSpeed", "/Script/Engine.CharacterMovementComponent"
    )
    select_f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    lit_w = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralFloat")
    lit_r = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralFloat")
    lit_idx = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralInt")

    # Tag by renaming via duplicate names — set node name isn't easy; use positions in WW band
    for n, name in (
        (get_pc, "WW_GetPC"),
        (is_down, "WW_IsDown"),
        (set_bool, "WW_SetBool"),
        (get_bool, "WW_GetBool"),
        (get_cmc, "WW_CMC"),
        (set_spd, "WW_SetSpd"),
        (select_f, "WW_Select"),
        (lit_w, "WW_LitW"),
        (lit_r, "WW_LitR"),
        (lit_idx, "WW_LitIdx"),
    ):
        try:
            n.rename(name)
        except Exception:
            pass

    pos(get_pc, -1350, 2050)
    pos(is_down, -1100, 2050)
    pos(set_bool, -850, 2100)
    pos(get_bool, -850, 1900)
    pos(lit_w, -850, 2300)
    pos(lit_r, -850, 2450)
    pos(select_f, -600, 2300)
    pos(get_cmc, -600, 2100)
    pos(set_spd, -350, 2100)
    pos(lit_idx, -1350, 2200)

    set_val(lit_w, "Value", str(WALK_SPEED))
    set_val(lit_r, "Value", str(RUN_SPEED))
    set_val(lit_idx, "Value", "0")

    # GetPlayerController PlayerIndex = 0
    connect(pin_out(lit_idx, "ReturnValue"), pin_in(get_pc, "PlayerIndex"))

    # IsInputKeyDown: self=PC, Key=LeftAlt
    connect(pin_out(get_pc, "ReturnValue"), bel.find_self_pin(is_down) or pin_in(is_down, "self"))
    # Set Key default on pin
    key_pin = pin_in(is_down, "Key")
    if key_pin:
        try:
            key_pin.set_pin_value("LeftAlt")
            log("IsInputKeyDown.Key=LeftAlt")
        except Exception as exc:
            log(f"Key pin: {exc}")

    links = []
    # Tick -> SetBool -> SetSpeed -> old
    links.append(("tick->setBool", connect(bel.find_then_pin(tick), bel.find_execute_pin(set_bool))))
    links.append(("isDown->bool", connect(pin_out(is_down, "ReturnValue"), pin_in(set_bool, BOOL_NAME))))
    links.append(("setBool->setSpd", connect(bel.find_then_pin(set_bool), bel.find_execute_pin(set_spd))))

    # SelectFloat(A=walk, B=run, bPickA=bWantsWalk) — check pin names
    # In KismetMathLibrary SelectFloat(float A, float B, bool bPickA)
    links.append(("litW->A", connect(pin_out(lit_w, "ReturnValue"), pin_in(select_f, "A"))))
    links.append(("litR->B", connect(pin_out(lit_r, "ReturnValue"), pin_in(select_f, "B"))))
    links.append(("bool->pick", connect(pin_out(get_bool), pin_in(select_f, "bPickA"))))
    # some versions use PickA
    if not links[-1][1]:
        links.append(("bool->PickA", connect(pin_out(get_bool), pin_in(select_f, "PickA"))))

    links.append(("cmc->self", connect(pin_out(get_cmc), bel.find_self_pin(set_spd) or pin_in(set_spd, "self"))))
    links.append(("sel->spd", connect(pin_out(select_f, "ReturnValue"), pin_in(set_spd, "MaxWalkSpeed"))))

    if old_targets:
        links.append(("setSpd->old", connect(bel.find_then_pin(set_spd), old_targets[0])))
    else:
        log("WARN: no old Tick target — Start/Stop may need re-wire")

    try:
        ed.add_comment_node(
            f"Alt Walk: LeftAlt -> {BOOL_NAME} -> MaxWalkSpeed "
            f"{int(WALK_SPEED)} / {int(RUN_SPEED)}",
            unreal.IntPoint(-1400, 1850),
        )
    except Exception:
        pass

    for name, ok in links:
        log(f"link {name}: {ok}")

    # Dump select / is_down pins for debug
    for n in (select_f, is_down, set_bool, set_spd):
        try:
            pins = [str(p.get_pin_name()) for p in (bel.list_all_pins(n) or [])]
            log(f"pins {n.get_name()} title={bel.get_node_title(n)}: {pins}")
        except Exception:
            pass

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as exc:
        log(f"compile: {exc}")
    save(CHAR)


def verify(bp):
    names = [str(n) for n in (bel.list_member_variable_names(bp) or [])]
    log(f"VERIFY {BOOL_NAME}={BOOL_NAME in names}")
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_editor_property("character_movement")
    log(f"VERIFY MaxWalkSpeed={move.get_editor_property('max_walk_speed')}")
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = ed.get_graph()
    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == g and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if tick:
        then = bel.find_then_pin(tick)
        log(f"VERIFY Tick.then links={len(list(then.list_connected_pins() or []))}")


def run():
    log("start")
    ensure_imc()
    bp = load(CHAR)
    ensure_vars(bp)
    wire(bp)
    verify(bp)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
