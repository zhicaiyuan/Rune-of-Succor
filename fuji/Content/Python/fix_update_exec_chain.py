# -*- coding: utf-8 -*-
"""
SI_SetStop.then was wrongly linked to a VariableGet.
Reconnect: Update -> SI_SetStop -> ExecutionSequence (original loco updates).
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixChain] {m}")


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


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    set_stop = None
    seq = None
    upd = None
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() != graph:
                continue
            name = n.get_name()
            title = str(bel.get_node_title(n))
            if name == "SI_SetStop":
                set_stop = n
            if name == "K2Node_ExecutionSequence_0" or title in ("序列", "Sequence"):
                seq = n
                log(f"seq={name} title={title}")
                for p in bel.list_all_pins(n) or []:
                    links = []
                    for lp in p.list_connected_pins() or []:
                        try:
                            links.append(lp.get_owning_node().get_name())
                        except Exception:
                            pass
                    log(f"  pin {p.get_pin_name()} -> {links}")
            if "BlueprintUpdateAnimation" in title.replace(" ", ""):
                upd = n
        except Exception:
            pass

    if not set_stop:
        log("NO SI_SetStop")
        return
    if not seq:
        # find any sequence in EventGraph
        for n in unreal.ObjectIterator(unreal.K2Node_ExecutionSequence):
            if n.get_outer() == graph:
                seq = n
                log(f"fallback seq {n.get_name()}")
                break

    # Break bad then from SI_SetStop
    then = bel.find_then_pin(set_stop)
    old = []
    for p in then.list_connected_pins() or []:
        try:
            old.append(p.get_owning_node().get_name())
        except Exception:
            pass
    log(f"SI_SetStop.then was -> {old}")
    then.break_pin_links()

    if seq:
        # Sequence execute pin
        exec_pin = bel.find_execute_pin(seq)
        ok = connect(then, exec_pin)
        log(f"SI_SetStop -> Sequence: {ok}")
        # dump sequence outs again
        for p in bel.list_output_pins(seq) or []:
            links = [lp.get_owning_node().get_name() for lp in (p.list_connected_pins() or [])]
            log(f"  seq out {p.get_pin_name()} -> {links}")
    else:
        log("WARN: no Sequence found — original update chain may be missing")

    # Ensure Update -> SI_SetStop
    if upd:
        ut = bel.find_then_pin(upd)
        targets = [p.get_owning_node().get_name() for p in (ut.list_connected_pins() or [])]
        log(f"Update.then -> {targets}")
        if "SI_SetStop" not in targets:
            ut.break_pin_links()
            ok = connect(ut, bel.find_execute_pin(set_stop))
            log(f"rewire Update->SI_SetStop: {ok}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
