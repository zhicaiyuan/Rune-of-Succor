# -*- coding: utf-8 -*-
import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ProbeTick] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
graph = ed.get_graph()

for n in unreal.ObjectIterator(unreal.K2Node_Event):
    if n.get_outer() != graph:
        continue
    title = str(bel.get_node_title(n))
    if "Tick" in title or "ReceiveTick" in n.get_name():
        then = bel.find_then_pin(n)
        linked = [p.get_owning_node().get_name() for p in (then.list_connected_pins() or [])]
        log(f"Tick {n.get_name()} then -> {linked}")

for prefix in ("LC_", "WW_", "SW_", "TO_", "YL_"):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if n.get_name().startswith(prefix):
            then = bel.find_then_pin(n) if hasattr(n, "find_then_pin") else None
            try:
                then = bel.find_then_pin(n)
            except Exception:
                then = None
            outs = []
            if then:
                outs = [p.get_owning_node().get_name() for p in (then.list_connected_pins() or [])]
            log(f"{n.get_name()} then -> {outs}")

# count TO nodes
to_nodes = [n.get_name() for n in unreal.ObjectIterator(unreal.EdGraphNode) if n.get_outer() == graph and n.get_name().startswith("TO_")]
log(f"TO count={len(to_nodes)} names={to_nodes[:20]}")
