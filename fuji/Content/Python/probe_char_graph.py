# -*- coding: utf-8 -*-
"""Probe BP_ThirdPersonCharacter EventGraph for Move/Tick nodes to hook Start/Stop."""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeChar] {m}")


def run():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    graph = None
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if "BP_ThirdPersonCharacter" in g.get_path_name() and g.get_name() == "EventGraph":
            graph = g
            break
    log(f"graph={graph}")
    # All K2 nodes in this graph
    count = 0
    for cls_name in (
        "K2Node_Event",
        "K2Node_CustomEvent",
        "K2Node_CallFunction",
        "K2Node_VariableGet",
        "K2Node_VariableSet",
        "K2Node_IfThenElse",
        "K2Node_EnhancedInputAction",
        "K2Node_InputAction",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
            except Exception:
                continue
            count += 1
            extra = ""
            try:
                title = n.get_node_title(0).to_string()
                extra += f" title={title}"
            except Exception:
                pass
            try:
                if hasattr(n, "get_editor_property"):
                    for prop in ("function_reference", "event_reference", "variable_reference"):
                        try:
                            ref = n.get_editor_property(prop)
                            mn = ref.get_editor_property("member_name")
                            extra += f" {prop}.member={mn}"
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                pins = [p.get_name() for p in (n.get_editor_property("pins") or [])]
                extra += f" pins={pins[:12]}"
            except Exception:
                pass
            log(f"{cls_name}: {n.get_name()}{extra}")
    log(f"total={count}")

    # BlueprintEditorLibrary graph helpers
    bel = unreal.BlueprintEditorLibrary
    log(f"BEL methods with graph/node: {[m for m in dir(bel) if any(k in m.lower() for k in ('node','graph','pin','connect','comment','tick'))]}")


if __name__ == "__main__":
    run()
else:
    run()
