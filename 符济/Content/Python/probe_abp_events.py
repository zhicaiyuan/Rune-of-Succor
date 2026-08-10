# -*- coding: utf-8 -*-
from __future__ import annotations
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ProbeEvt] {m}")


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    # list all graphs
    try:
        for g in bel.list_graphs(abp) or []:
            log(f"graph: {g.get_name()} path={g.get_path_name()}")
    except Exception as e:
        log(f"list_graphs: {e}")

    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()
    log(f"editor graph={graph.get_path_name()}")

    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if "ABP_StrafeLocomotion" not in n.get_path_name():
                continue
            title = str(bel.get_node_title(n))
            outer = n.get_outer().get_name() if n.get_outer() else "?"
            pins = [str(p.get_pin_name()) for p in (bel.list_all_pins(n) or [])]
            # dump all editor props we can
            props = []
            for prop in (
                "event_reference",
                "EventReference",
                "bOverrideFunction",
                "bInternalEvent",
                "custom_function_name",
                "CustomFunctionName",
            ):
                try:
                    props.append(f"{prop}={n.get_editor_property(prop)}")
                except Exception as e:
                    props.append(f"{prop}:ERR")
            # FunctionReference export
            try:
                fr = n.get_editor_property("EventReference")
                props.append(f"ER.export={fr.export_text()}")
            except Exception:
                pass
            log(f"EVENT name={n.get_name()} outer={outer} title={title}")
            log(f"  pins={pins}")
            log(f"  {props}")
        except Exception as e:
            log(f"err: {e}")

    # Also CustomEvent
    for n in unreal.ObjectIterator(unreal.K2Node_CustomEvent):
        try:
            if "ABP_StrafeLocomotion" not in n.get_path_name():
                continue
            log(f"CUSTOM {n.get_name()} title={bel.get_node_title(n)}")
        except Exception:
            pass

    # compile messages
    try:
        bel.compile_blueprint(abp)
        log("compile done")
    except Exception as e:
        log(f"compile: {e}")


if __name__ == "__main__":
    run()
else:
    run()
