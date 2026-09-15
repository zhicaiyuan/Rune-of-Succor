# -*- coding: utf-8 -*-
import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def walk_from(node, depth=0, seen=None):
    if seen is None:
        seen = set()
    if node.get_name() in seen or depth > 30:
        return
    seen.add(node.get_name())
    try:
        then = bel.find_then_pin(node)
    except Exception:
        return
    if not then:
        return
    for p in then.list_connected_pins() or []:
        n = p.get_owning_node()
        unreal.log(f"{'  '*depth}{node.get_name()} -> {n.get_name()}")
        walk_from(n, depth + 1, seen)


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
graph = ed.get_graph()

for n in unreal.ObjectIterator(unreal.K2Node_Event):
    if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
        unreal.log(f"[Walk] from {n.get_name()}")
        walk_from(n)

for n in unreal.ObjectIterator(unreal.EdGraphNode):
    if n.get_outer() != graph:
        continue
    if n.get_name() == "K2Node_IfThenElse_2":
        unreal.log(f"[Walk] from IfThenElse_2")
        walk_from(n)
