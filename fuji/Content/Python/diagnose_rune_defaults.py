# -*- coding: utf-8 -*-
"""Read-only dump of the values that control rune candidate selection."""

from pathlib import Path
import unreal


COMPONENT = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BPC_\u753b\u7b26\u7cfb\u7edf"
REPORT = Path(__file__).with_name("diagnose_rune_defaults_report.txt")
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
LINES = []


def emit(message):
    line = str(message)
    LINES.append(line)
    unreal.log(f"[RuneDefaults] {line}")


def title(node):
    try:
        return str(BEL.get_node_title(node))
    except Exception:
        return node.get_name()


def describe_graph(bp, graph_name):
    editor = BGE.get_graph_editor_by_name(bp, graph_name)
    if not editor:
        emit(f"missing_graph={graph_name}")
        return

    graph = editor.get_graph()
    nodes = [
        node
        for node in unreal.ObjectIterator(unreal.EdGraphNode)
        if node.get_outer() == graph
    ]
    emit(f"graph={graph_name} nodes={len(nodes)}")
    interesting_titles = {
        "Set \u6700\u4f73\u5206\u6570",
        "Set \u548c",
        "For Loop",
        "Equal (Integer)",
        "float < float",
        "AND Boolean",
        "\u6bd4\u5206",
        "Get \u7b14\u753b\u6570",
        "Length",
        "IsValid",
        "计算画符特征距离",
    }
    for node in nodes:
        node_title = title(node)
        if node_title not in interesting_titles:
            continue
        emit(f"node={node.get_name()} title={node_title}")
        for graph_pin in BEL.list_all_pins(node) or []:
            try:
                linked = [
                    f"{item.get_owning_node().get_name()}.{item.get_pin_name()}"
                    for item in graph_pin.list_connected_pins() or []
                ]
                emit(
                    f"  pin={graph_pin.get_pin_name()} "
                    f"value={graph_pin.get_pin_value()!r} linked={linked}"
                )
            except Exception as exc:
                emit(f"  pin_error={exc}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(COMPONENT)
    if not bp:
        raise RuntimeError("rune component is missing")

    default = unreal.get_default_object(bp.generated_class())
    for property_name in ("\u6700\u4f73\u5206\u6570", "\u5f53\u524d\u7279\u5f81", "\u7b26\u5e93"):
        try:
            value = default.get_editor_property(property_name)
            emit(f"cdo.{property_name}={value}")
        except Exception as exc:
            emit(f"cdo.{property_name}.error={exc}")

    describe_graph(bp, "EventGraph")
    describe_graph(bp, "\u6bd4\u5206")
    REPORT.write_text("\n".join(LINES), encoding="utf-8")


main()
