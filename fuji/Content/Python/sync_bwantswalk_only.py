# -*- coding: utf-8 -*-
"""
ONLY sync Character.bWantsWalk -> AnimInstance.bWantsWalk each Tick.
Does NOT touch AnimBP state machine / AnimGraph / transitions.

Uses KismetSystemLibrary.SetBoolPropertyByName (no Cast needed).
Inserts after WW_SetBool in BP_ThirdPersonCharacter EventGraph.
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
PROP = "bWantsWalk"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[SyncWalk] {m}")


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


def purge_sync_only(ed, graph):
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.EdGraphNode_Comment,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("SW_") or "sync bWantsWalk" in title.lower() or "Sync bWantsWalk" in title:
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
            n.rename(f"SW_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged old sync nodes {len(uniq)}")


def find_ww_setbool(graph):
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() != graph:
                continue
            if n.get_name() == "WW_SetBool":
                return n
            if "bWantsWalk" in str(bel.get_node_title(n)) and n.get_name().startswith("WW_"):
                return n
        except Exception:
            pass
    # any set bWantsWalk
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() == graph and "bWantsWalk" in str(bel.get_node_title(n)):
                return n
        except Exception:
            pass
    return None


def run():
    log("start — sync only, no SM changes")
    bp = load(CHAR)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    set_bool = find_ww_setbool(graph)
    if not set_bool:
        raise RuntimeError("WW_SetBool / Set bWantsWalk not found on Character")
    log(f"found setter {set_bool.get_name()} title={bel.get_node_title(set_bool)}")

    then = bel.find_then_pin(set_bool)
    old_targets = list(then.list_connected_pins() or [])
    old_names = []
    for p in old_targets:
        try:
            old_names.append(p.get_owning_node().get_name())
        except Exception:
            pass
    log(f"WW_SetBool.then was -> {old_names}")

    purge_sync_only(ed, graph)

    # Re-get then after purge (shouldn't affect WW_)
    then = bel.find_then_pin(set_bool)
    old_targets = list(then.list_connected_pins() or [])
    then.break_pin_links()

    # Mesh
    get_mesh = ed.add_get_member_variable_node("Mesh")
    safe_rename(get_mesh, "SW_Mesh")
    pos(get_mesh, -200, 2480)

    # GetAnimInstance on SkeletalMeshComponent
    get_anim = ed.add_call_function_node(
        "/Script/Engine.SkeletalMeshComponent:GetAnimInstance"
    )
    safe_rename(get_anim, "SW_GetAnim")
    pos(get_anim, 50, 2480)

    # SetBoolPropertyByName(Object, PropertyName, Value)
    set_prop = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:SetBoolPropertyByName"
    )
    safe_rename(set_prop, "SW_SetProp")
    pos(set_prop, 350, 2350)

    # Property name literal
    lit_name = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:MakeLiteralName"
    )
    safe_rename(lit_name, "SW_LitName")
    pos(lit_name, 50, 2620)
    # pin may be Value or Value
    if not set_val(lit_name, "Value", PROP):
        set_val(lit_name, "value", PROP)

    # Get bWantsWalk for value (or use Output_Get from set_bool)
    get_walk = ed.add_get_member_variable_node(PROP)
    safe_rename(get_walk, "SW_GetWalk")
    pos(get_walk, 50, 2750)

    links = []
    links.append(("setBool->setProp", connect(then, bel.find_execute_pin(set_prop))))
    links.append(
        (
            "mesh->self",
            connect(pin_out(get_mesh), bel.find_self_pin(get_anim) or pin_in(get_anim, "self")),
        )
    )
    links.append(
        (
            "anim->obj",
            connect(pin_out(get_anim, "ReturnValue"), pin_in(set_prop, "Object")),
        )
    )
    links.append(
        (
            "name->prop",
            connect(pin_out(lit_name, "ReturnValue"), pin_in(set_prop, "PropertyName")),
        )
    )
    # Value: prefer Output_Get from set_bool if present
    out_get = pin_out(set_bool, "Output_Get") or pin_out(set_bool, PROP)
    if out_get:
        links.append(("setOut->val", connect(out_get, pin_in(set_prop, "Value"))))
    else:
        links.append(("get->val", connect(pin_out(get_walk), pin_in(set_prop, "Value"))))

    # Fallback property name via pin default if literal fails
    if not pin_out(lit_name, "ReturnValue") or not any(n == "name->prop" and ok for n, ok in []):
        set_val(set_prop, "PropertyName", PROP)

    # Also try set PropertyName pin directly
    set_val(set_prop, "PropertyName", PROP)

    # Reattach previous then chain after sync
    if old_targets:
        ok = connect(bel.find_then_pin(set_prop), old_targets[0])
        links.append(("setProp->old", ok))
        log(f"reattach -> {old_names[0] if old_names else '?'}: {ok}")
    else:
        # try WW_SetSpd
        for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
            try:
                if n.get_outer() == graph and n.get_name() == "WW_SetSpd":
                    ok = connect(bel.find_then_pin(set_prop), bel.find_execute_pin(n))
                    links.append(("setProp->SetSpd", ok))
                    break
            except Exception:
                pass

    try:
        ed.add_comment_node(
            "Sync bWantsWalk -> AnimInstance (SM untouched)",
            unreal.IntPoint(-250, 2280),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    # verify PropertyName pin
    p = pin_in(set_prop, "PropertyName")
    try:
        log(f"PropertyName val={p.get_pin_value() if p else None}")
    except Exception:
        pass

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    save(CHAR)
    log("done — Character pushes bWantsWalk to AnimBP each Tick; SM not modified")


if __name__ == "__main__":
    run()
else:
    run()
