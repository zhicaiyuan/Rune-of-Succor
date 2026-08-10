# -*- coding: utf-8 -*-
from __future__ import annotations
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[Chain] {m}")


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    # find Update
    upd = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == graph and "BlueprintUpdateAnimation" in str(bel.get_node_title(n)).replace(" ", ""):
            upd = n
            break
    if not upd:
        log("NO UPDATE")
        return

    # walk exec chain
    node = upd
    seen = set()
    for i in range(30):
        if id(node) in seen:
            break
        seen.add(id(node))
        then = bel.find_then_pin(node)
        if not then:
            log(f"{i}: {node.get_name()} title={bel.get_node_title(node)} (no then)")
            break
        linked = list(then.list_connected_pins() or [])
        names = []
        for p in linked:
            try:
                names.append(f"{p.get_owning_node().get_name()}/{bel.get_node_title(p.get_owning_node())}")
            except Exception:
                pass
        log(f"{i}: {node.get_name()} | {bel.get_node_title(node)} -> {names}")
        if not linked:
            break
        node = linked[0].get_owning_node()

    try:
        bel.compile_blueprint(abp)
        log("compile OK — check for dup errors above")
    except Exception as e:
        log(f"compile: {e}")


if __name__ == "__main__":
    run()
else:
    run()
