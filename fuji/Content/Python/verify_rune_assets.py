# -*- coding: utf-8 -*-
"""验证画符蓝图与模板的持久化状态。"""

import math
from pathlib import Path
import unreal


COMPONENT = "/Game/蓝图/玩家/BPC_画符系统"
TEMPLATES = [
    "/Game/UI/画符界面/符纸类型/符_横",
    "/Game/UI/画符界面/符纸类型/符_竖",
    "/Game/UI/画符界面/符纸类型/符_圆",
    "/Game/UI/画符界面/符纸类型/符_叉",
    "/Game/UI/画符界面/符纸类型/符_闪电",
    "/Game/UI/画符界面/符纸类型/符_螺旋",
]
REPORT = Path(__file__).with_name("verify_rune_assets_report.txt")
REPORT_LINES = []


def log(message):
    REPORT_LINES.append(str(message))
    unreal.log(f"[RuneVerify] {message}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(COMPONENT)
    if not bp:
        raise RuntimeError("画符组件不存在")

    generated_class = bp.generated_class()
    default = unreal.get_default_object(generated_class)
    library = list(default.get_editor_property("符库") or [])
    log(f"component_class={generated_class.get_path_name()}")
    log(f"component_default={default.get_path_name()}")
    log(f"library_count={len(library)} library={[item.get_path_name() if item else None for item in library]}")
    if len(library) < len(TEMPLATES):
        raise RuntimeError(f"符库数量不足: {len(library)} < {len(TEMPLATES)}")

    for path in TEMPLATES:
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            raise RuntimeError(f"缺少模板: {path}")
        features = list(asset.get_editor_property("特征") or [])
        grid_total = sum(float(value) for value in features[:36])
        finite = all(math.isfinite(float(value)) for value in features)
        if len(features) != 40 or not finite or abs(grid_total - 1.0) > 0.001:
            raise RuntimeError(
                f"模板特征无效: {path}, count={len(features)}, grid_sum={grid_total}, finite={finite}"
            )
        log(
            f"template={asset.get_name()} strokes={asset.get_editor_property('笔画数')} "
            f"features={len(features)} grid_sum={grid_total:.6f} finite={finite} "
            f"tolerance={asset.get_editor_property('容差')} "
            f"aspect=[{asset.get_editor_property('最小宽高比')}, {asset.get_editor_property('最大宽高比')}]"
        )

    editor = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "算特征")
    if not editor:
        raise RuntimeError("算特征图不存在")
    graph = editor.get_graph()
    nodes = [
        node
        for node in unreal.ObjectIterator(unreal.EdGraphNode)
        if node.get_outer() == graph
    ]
    for node in nodes:
        try:
            title = unreal.BlueprintEditorLibrary.get_node_title(node)
        except Exception:
            title = node.get_name()
        pins = []
        for pin in unreal.BlueprintEditorLibrary.list_all_pins(node) or []:
            try:
                links = [str(item.get_pin_name()) for item in pin.list_connected_pins() or []]
                pins.append(f"{pin.get_pin_name()}->{links}")
            except Exception:
                pass
        log(f"feature_node={node.get_class().get_name()} title={title} pins={pins}")

    REPORT.write_text("\n".join(REPORT_LINES), encoding="utf-8")


main()
