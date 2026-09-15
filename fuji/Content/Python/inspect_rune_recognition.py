# -*- coding: utf-8 -*-
"""只读导出画符蓝图的图、节点、引脚和变量，便于定位识别逻辑。"""

from __future__ import annotations

import unreal


ASSETS = [
    "/Game/蓝图/玩家/BPC_画符系统",
    "/Game/UI/画符界面/WBP_画符界面",
    "/Game/UI/画符界面/F笔画",
    "/Game/UI/画符界面/符纸类型/DA_符",
    "/Game/UI/画符界面/符纸类型/符_横",
    "/Game/UI/画符界面/符纸类型/符_竖",
]

bel = unreal.BlueprintEditorLibrary


def log(message):
    unreal.log(f"[RuneInspect] {message}")


def prop(obj, name, fallback="<n/a>"):
    try:
        return obj.get_editor_property(name)
    except Exception:
        return fallback


def pin_text(pin):
    try:
        name = str(pin.get_pin_name())
    except Exception:
        name = str(prop(pin, "pin_name"))
    direction = str(prop(pin, "direction"))
    default = str(prop(pin, "default_value", ""))
    try:
        linked = [
            f"{p.get_owning_node().get_name()}.{p.get_pin_name()}"
            for p in (pin.list_connected_pins() or [])
        ]
    except Exception:
        linked = []
    return f"{direction} {name} default={default!r} -> {linked}"


def inspect_blueprint(asset):
    log(f"BLUEPRINT {asset.get_path_name()} class={asset.get_class().get_name()}")
    for key in ("parent_class", "new_variables", "implemented_interfaces"):
        value = prop(asset, key)
        log(f"  {key}={value}")

    try:
        default = unreal.get_default_object(asset.generated_class())
        log(f"  default_object={default}")
        for key in (
            "符库",
            "网格大小",
            "录制模式",
            "当前特征",
            "最佳分数",
        ):
            value = prop(default, key)
            if value != "<n/a>":
                log(f"  default.{key}={value}")
    except Exception as exc:
        log(f"  default_object error={exc}")

    graphs = []
    for graph in unreal.ObjectIterator(unreal.EdGraph):
        try:
            if asset.get_name() in graph.get_path_name():
                graphs.append(graph)
        except Exception:
            pass

    seen = set()
    for graph in graphs:
        path = graph.get_path_name()
        if path in seen:
            continue
        seen.add(path)
        log(f"GRAPH {path}")
        nodes = []
        for node in unreal.ObjectIterator(unreal.EdGraphNode):
            try:
                if node.get_outer() == graph:
                    nodes.append(node)
            except Exception:
                pass
        nodes.sort(key=lambda n: (int(prop(n, "node_pos_y", 0)), int(prop(n, "node_pos_x", 0))))
        for node in nodes:
            try:
                title = str(bel.get_node_title(node))
            except Exception:
                try:
                    title = node.get_node_title(0).to_string()
                except Exception:
                    title = "<untitled>"
            log(
                f" NODE {node.get_name()} class={node.get_class().get_name()} "
                f"pos=({prop(node, 'node_pos_x', 0)},{prop(node, 'node_pos_y', 0)}) title={title!r}"
            )
            try:
                pins = bel.list_all_pins(node) or []
            except Exception:
                pins = prop(node, "pins", [])
            for pin in pins:
                log(f"   PIN {pin_text(pin)}")


def main():
    for path in ASSETS:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            log(f"MISSING {path}")
            continue
        log(f"ASSET {path} object={asset} class={asset.get_class().get_name()}")
        if asset.get_class().get_name() in ("Blueprint", "WidgetBlueprint"):
            inspect_blueprint(asset)
        else:
            log(f"  dir={[name for name in dir(asset) if not name.startswith('_')]}")
            for key in (
                "row_struct",
                "sample_points",
                "points",
                "strokes",
                "stroke_count",
                "rune_name",
                "name",
                "特征",
                "笔画数",
                "容差",
                "技能标识",
                "最大宽高比",
                "最小宽高比",
            ):
                value = prop(asset, key)
                if value != "<n/a>":
                    log(f"  {key}={value}")


main()
