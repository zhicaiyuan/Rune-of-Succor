# -*- coding: utf-8 -*-
"""
Restore Alt-walk exec chain on BP_ThirdPersonCharacter.

Expected:
  Tick -> WW_SetBool -> SW_SetProp -> WW_SetSpd -> LC_SetHasInput -> (tail) -> ...

If Tick was rewired to IfThenElse / turn snap directly, WW_SetBool never runs.
"""
from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixTickChain] {m}")


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


def find_node(graph, name_prefix=None, exact=None):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        nm = n.get_name()
        if exact and nm == exact:
            return n
        if name_prefix and nm.startswith(name_prefix):
            return n
    return None


def exec_tail(node):
    """Follow single exec 'then' chain to last node."""
    cur = node
    seen = set()
    while cur and cur.get_name() not in seen:
        seen.add(cur.get_name())
        try:
            then = bel.find_then_pin(cur)
        except Exception:
            break
        if not then:
            break
        nxt = list(then.list_connected_pins() or [])
        if not nxt:
            return cur
        cur = nxt[0].get_owning_node()
    return cur


def run():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if not tick:
        raise RuntimeError("ReceiveTick not found")

    ww = find_node(graph, exact="WW_SetBool")
    if not ww:
        ww = find_node(graph, name_prefix="WW_SetBool")
    if not ww:
        raise RuntimeError("WW_SetBool not found — run fix_alt_walk.py first")

    tick_then = bel.find_then_pin(tick)
    old_targets = list(tick_then.list_connected_pins() or [])
    old_names = [p.get_owning_node().get_name() for p in old_targets]
    log(f"Tick.then was -> {old_names}")

    ww_exec = bel.find_execute_pin(ww)
    ww_incoming = list(ww_exec.list_connected_pins() or []) if ww_exec else []
    log(f"WW_SetBool.execute incoming={[p.get_owning_node().get_name() for p in ww_incoming]}")

    # Tick must drive WW_SetBool
    if not ww_incoming or ww_incoming[0].get_owning_node() != tick:
        tick_then.break_pin_links()
        ok = connect(tick_then, ww_exec)
        log(f"Tick -> WW_SetBool: {ok}")

    tail = exec_tail(ww)
    log(f"chain tail={tail.get_name()}")

    # Reattach former Tick targets after tail (e.g. IfThenElse Start/Stop)
    tail_then = bel.find_then_pin(tail)
    for p in old_targets:
        node = p.get_owning_node()
        if node.get_name().startswith("WW_"):
            continue
        # skip if already connected
        existing = list(tail_then.list_connected_pins() or [])
        if any(e.get_owning_node() == node for e in existing):
            log(f"tail already -> {node.get_name()}")
            continue
        ok = connect(tail_then, bel.find_execute_pin(node))
        log(f"tail -> {node.get_name()}: {ok}")

    try:
        bel.compile_blueprint(bp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
    log("DONE — Alt walk: Tick -> WW_SetBool -> ... Hold LeftAlt in PIE (CapsLock if editor eats Alt)")


if __name__ == "__main__":
    run()
