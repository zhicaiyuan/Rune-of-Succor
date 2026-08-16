# -*- coding: utf-8 -*-
import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ProbeCrouch] {m}")


def dump(bp, gname):
    ed = BGE.get_graph_editor_by_name(bp, gname)
    g = ed.get_graph()
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != g:
            continue
        title = str(bel.get_node_title(n))
        name = n.get_name()
        low = (title + " " + name).lower()
        if any(
            k in low
            for k in (
                "crouch",
                "pawn owner",
                "iscrouch",
                "keydown",
                "ww_getpc",
                "lc_sethasinput",
            )
        ):
            then = []
            try:
                tp = bel.find_then_pin(n)
                if tp:
                    then = [p.get_owning_node().get_name() for p in (tp.list_connected_pins() or [])]
            except Exception:
                pass
            log(f"{gname} {name} title={title} then={then}")


dump(unreal.EditorAssetLibrary.load_asset(CHAR), "EventGraph")
dump(unreal.EditorAssetLibrary.load_asset(ABP), "EventGraph")
