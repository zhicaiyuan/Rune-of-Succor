# -*- coding: utf-8 -*-
"""
Reliable Alt walk (no GetInputActionValue — protected in UE 5.8 Python):
  Tick -> Set bWantsWalk(LeftAlt OR CapsLock)
       -> Set MaxWalkSpeed(SelectFloat A=200 B=600)
       -> Start/Stop branch

IMC also maps LeftAlt + CapsLock -> IA_Walk for completeness.
CapsLock backup: editor PIE often eats Left Alt.
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
    unreal.log(f"[FixAlt] {m}")


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
        log(f"no pin {pin_name} on {node.get_name()}")
        return False
    try:
        p.set_pin_value(str(value))
        log(f"set {node.get_name()}.{pin_name}={value}")
        return True
    except Exception as exc:
        log(f"set_val {pin_name}: {exc}")
        return False


def pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        pass


def make_key(name: str):
    k = unreal.Key()
    try:
        k.import_text(name)
        return k
    except Exception as exc:
        log(f"import_text {name}: {exc}")
    try:
        k.set_editor_property("key_name", unreal.Name(name))
        return k
    except Exception as exc:
        log(f"key_name {name}: {exc}")
    return None


def ensure_imc_keys():
    imc = load(IMC)
    ia = load(IA_WALK)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    save(IA_WALK)

    dkm = imc.get_editor_property("default_key_mappings")
    mappings = list(dkm.get_editor_property("mappings") or [])

    def is_walk(m):
        try:
            a = m.get_editor_property("action")
            return a and "IA_Walk" in a.get_path_name()
        except Exception:
            return False

    kept = [m for m in mappings if not is_walk(m)]
    for key_str in ("LeftAlt", "CapsLock"):
        k = make_key(key_str)
        if not k:
            continue
        m = unreal.EnhancedActionKeyMapping()
        m.set_editor_property("action", ia)
        m.set_editor_property("key", k)
        kept.append(m)
        log(f"IMC add IA_Walk <- {key_str}")

    dkm.set_editor_property("mappings", kept)
    imc.set_editor_property("default_key_mappings", dkm)
    for key_str in ("LeftAlt", "CapsLock"):
        k = make_key(key_str)
        if k:
            try:
                imc.map_key(ia, k)
            except Exception:
                pass
    save(IMC)
    text = imc.get_editor_property("default_key_mappings").export_text()
    log(f"IMC LeftAlt={('LeftAlt' in text)} CapsLock={('CapsLock' in text)}")


def safe_rename(node, name):
    """Rename only if free — never crash on name collision."""
    try:
        outer = node.get_outer()
        existing = unreal.find_object(outer, name)
        if existing and existing != node:
            return False
        node.rename(name)
        return True
    except Exception as exc:
        log(f"rename {name} skipped: {exc}")
        return False


def purge_ww(ed, graph):
    kill = []
    for cls_name in (
        "K2Node_CallFunction",
        "K2Node_VariableGet",
        "K2Node_VariableSet",
        "K2Node_GetInputActionValue",
        "K2Node_ExecutionSequence",
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
                if (
                    name.startswith("WW_")
                    or "Alt Walk" in title
                    or "WALK: bWantsWalk" in title
                    or "IsInputKeyDown" in title
                    or "Select Float" in title
                    or "Boolean OR" in title
                    or "Make Literal Int" in title
                ):
                    # Only kill walk-driver helpers near our chain; avoid wiping unrelated SelectFloat.
                    if name.startswith("WW_") or "WALK:" in title or "Alt Walk" in title:
                        kill.append(n)
                    elif "IsInputKeyDown" in title or "Make Literal Int" in title:
                        kill.append(n)
            except Exception:
                continue
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() != graph:
                continue
            if "bWantsWalk" in str(bel.get_node_title(n)) or "Max Walk Speed" in str(bel.get_node_title(n)):
                # only if previously named WW_ or orphaned from walk driver
                if n.get_name().startswith("WW_") or "bWantsWalk" in str(bel.get_node_title(n)):
                    kill.append(n)
        except Exception:
            pass
    if not kill:
        log("purge: nothing")
        return
    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    # Rename away first so new nodes can reuse WW_* names safely
    for i, n in enumerate(uniq):
        try:
            n.rename(f"WW_DEL_{i}")
        except Exception:
            pass
    ed.remove_nodes(uniq)
    log(f"purged {len(uniq)}")


def find_ss_target(graph, tick_then_old):
    # Prefer WW_SetSpd.then consumer (before purge)
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
                tp = bel.find_then_pin(n)
                linked = list(tp.list_connected_pins() or [])
                if linked:
                    log(f"SS via WW_SetSpd.then -> {linked[0].get_owning_node().get_name()}")
                    return linked[0]
        except Exception:
            pass
    # Any IfThenElse that looks like Start/Stop (SS_*)
    for n in unreal.ObjectIterator(unreal.K2Node_IfThenElse):
        try:
            if n.get_outer() != graph:
                continue
            # prefer branch near SS vars
            name = n.get_name()
            log(f"SS fallback IfThenElse {name}")
            return bel.find_execute_pin(n)
        except Exception:
            pass
    if tick_then_old:
        # if old wasn't WW_*, keep it
        for p in tick_then_old:
            try:
                on = p.get_owning_node()
                if not on.get_name().startswith("WW_"):
                    log(f"SS keep old Tick target {on.get_name()}")
                    return p
            except Exception:
                pass
    return None


def ensure_var(bp):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name(BOOL_NAME), pin)
    except Exception:
        pass
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
    save(CHAR)


def wire(bp):
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if not tick:
        tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(-1600, 1600))
    pos(tick, -1600, 1600)

    then = bel.find_then_pin(tick)
    old = list(then.list_connected_pins() or [])
    log(f"Tick targets was {[p.get_owning_node().get_name() for p in old]}")

    # Capture SS IfThenElse by name BEFORE purge (pins go stale)
    ss_if_name = None
    ss_pin = find_ss_target(graph, old)
    if ss_pin:
        try:
            ss_if_name = ss_pin.get_owning_node().get_name()
            log(f"SS node name={ss_if_name}")
        except Exception:
            pass

    then.break_pin_links()
    purge_ww(ed, graph)

    # GetPlayerController(0) — safe_rename avoids fatal rename collision
    get_pc = ed.add_call_function_node("/Script/Engine.GameplayStatics:GetPlayerController")
    safe_rename(get_pc, "WW_GetPC")
    pos(get_pc, -1350, 2200)
    lit_idx = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:MakeLiteralInt")
    safe_rename(lit_idx, "WW_LitIdx")
    pos(lit_idx, -1550, 2200)
    set_val(lit_idx, "Value", "0")
    connect(pin_out(lit_idx, "ReturnValue"), pin_in(get_pc, "PlayerIndex"))

    def make_is_down(key_name, x, y, tag):
        n = ed.add_call_function_node("/Script/Engine.PlayerController:IsInputKeyDown")
        safe_rename(n, tag)
        pos(n, x, y)
        connect(pin_out(get_pc, "ReturnValue"), bel.find_self_pin(n) or pin_in(n, "self"))
        ok = set_val(n, "Key", key_name)
        if not ok:
            set_val(n, "Key", f'(KeyName="{key_name}")')
        p = pin_in(n, "Key")
        try:
            log(f"{tag}.Key={p.get_pin_value() if p else None}")
        except Exception:
            pass
        return n

    is_alt = make_is_down("LeftAlt", -1100, 2200, "WW_IsAlt")
    is_caps = make_is_down("CapsLock", -1100, 2350, "WW_IsCaps")

    or_bool = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_bool, "WW_Or")
    pos(or_bool, -900, 2250)
    connect(pin_out(is_alt, "ReturnValue"), pin_in(or_bool, "A"))
    connect(pin_out(is_caps, "ReturnValue"), pin_in(or_bool, "B"))
    bool_src = pin_out(or_bool, "ReturnValue")
    log("bool = LeftAlt OR CapsLock")

    set_bool = ed.add_set_member_variable_node(BOOL_NAME)
    safe_rename(set_bool, "WW_SetBool")
    pos(set_bool, -550, 2100)

    get_bool = ed.add_get_member_variable_node(BOOL_NAME)
    safe_rename(get_bool, "WW_GetBool")
    pos(get_bool, -550, 1900)

    get_cmc = ed.add_get_member_variable_node("CharacterMovement")
    safe_rename(get_cmc, "WW_CMC")
    pos(get_cmc, -350, 2250)

    set_spd = ed.add_set_member_variable_node(
        "MaxWalkSpeed", "/Script/Engine.CharacterMovementComponent"
    )
    safe_rename(set_spd, "WW_SetSpd")
    pos(set_spd, -100, 2100)

    select_f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:SelectFloat")
    safe_rename(select_f, "WW_Select")
    pos(select_f, -350, 2100)
    set_val(select_f, "A", str(WALK_SPEED))
    set_val(select_f, "B", str(RUN_SPEED))

    links = []
    links.append(("tick->setBool", connect(bel.find_then_pin(tick), bel.find_execute_pin(set_bool))))
    links.append(("bool->set", connect(bool_src, pin_in(set_bool, BOOL_NAME))))
    links.append(("setBool->setSpd", connect(bel.find_then_pin(set_bool), bel.find_execute_pin(set_spd))))
    links.append(("getBool->pick", connect(pin_out(get_bool), pin_in(select_f, "bPickA"))))
    links.append(("cmc->self", connect(pin_out(get_cmc), bel.find_self_pin(set_spd) or pin_in(set_spd, "self"))))
    links.append(("sel->spd", connect(pin_out(select_f, "ReturnValue"), pin_in(set_spd, "MaxWalkSpeed"))))

    # Reattach Start/Stop
    ss_exec = None
    if ss_if_name:
        for n in unreal.ObjectIterator(unreal.K2Node_IfThenElse):
            if n.get_outer() == graph and n.get_name() == ss_if_name:
                ss_exec = bel.find_execute_pin(n)
                break
    if not ss_exec:
        for n in unreal.ObjectIterator(unreal.K2Node_IfThenElse):
            if n.get_outer() == graph:
                ss_exec = bel.find_execute_pin(n)
                log(f"reattach first IfThenElse {n.get_name()}")
                break
    if ss_exec:
        links.append(("setSpd->ss", connect(bel.find_then_pin(set_spd), ss_exec)))
    else:
        log("WARN: no Start/Stop IfThenElse to reattach")

    try:
        ed.add_comment_node(
            "WALK: bWantsWalk = LeftAlt OR CapsLock\n"
            f"MaxWalkSpeed = {int(WALK_SPEED)} if true else {int(RUN_SPEED)}\n"
            "PIE tip: CapsLock if Alt is eaten by editor",
            unreal.IntPoint(-1400, 1800),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    for pname in ("A", "B", "bPickA"):
        p = pin_in(select_f, pname)
        try:
            log(f"Select.{pname} val={p.get_pin_value()} links={len(list(p.list_connected_pins() or []))}")
        except Exception:
            pass

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as exc:
        log(f"compile: {exc}")
    save(CHAR)


def run():
    log("start")
    ensure_imc_keys()
    bp = load(CHAR)
    ensure_var(bp)
    wire(bp)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
