# -*- coding: utf-8 -*-
"""升级现有画符蓝图：稳定采样特征，并加入圆、叉模板。"""

from __future__ import annotations

import math
import unreal


COMPONENT = "/Game/蓝图/玩家/BPC_画符系统"
TEMPLATE_DIR = "/Game/UI/画符界面/符纸类型"
VERTICAL = f"{TEMPLATE_DIR}/符_竖"
HORIZONTAL = f"{TEMPLATE_DIR}/符_横"
CIRCLE = f"{TEMPLATE_DIR}/符_圆"
CROSS = f"{TEMPLATE_DIR}/符_叉"
LIGHTNING = f"{TEMPLATE_DIR}/符_闪电"
SPIRAL = f"{TEMPLATE_DIR}/符_螺旋"
GRID_SIZE = 6
STRUCTURAL_SAMPLE_COUNT = 32
DIRECTNESS_WEIGHT = 0.35
NET_TURNING_WEIGHT = 0.35
TURN_CONSISTENCY_WEIGHT = 0.25
PATH_LENGTH_WEIGHT = 0.15

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(message):
    unreal.log(f"[RuneUpgrade] {message}")


def pin(node, name):
    for candidate in bel.list_all_pins(node) or []:
        try:
            if str(candidate.get_pin_name()) == name:
                return candidate
        except Exception:
            pass
    return None


def connect(source, target):
    if not source or not target:
        return False
    try:
        return bool(source.try_create_connection(target))
    except Exception:
        try:
            return bool(target.try_create_connection(source))
        except Exception:
            return False


def set_pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(x, y))
    except Exception:
        pass


def node_title(node):
    try:
        return str(bel.get_node_title(node))
    except Exception:
        return node.get_name()


def linked_pins(graph_pin):
    return list(graph_pin.list_connected_pins() or []) if graph_pin else []


def is_linked_to_node(graph_pin, node):
    return any(item.get_owning_node() == node for item in linked_pins(graph_pin))


def break_links(graph_pin):
    if not graph_pin:
        return
    if hasattr(graph_pin, "break_all_pin_links"):
        graph_pin.break_all_pin_links()
    elif hasattr(graph_pin, "break_pin_links"):
        graph_pin.break_pin_links()
    else:
        raise RuntimeError(f"引脚不支持断开连接: {graph_pin}")


def stable_features(strokes, grid_size=GRID_SIZE):
    points = [point for stroke in strokes if len(stroke) >= 2 for point in stroke]
    min_x = min(point[0] for point in points)
    max_x = max(point[0] for point in points)
    min_y = min(point[1] for point in points)
    max_y = max(point[1] for point in points)
    long_edge = max(max_x - min_x, max_y - min_y)
    counts = [0.0] * (grid_size * grid_size)
    total = 0

    def add(point):
        nonlocal total
        x = min(grid_size - 1, max(0, math.floor(point[0] * grid_size)))
        y = min(grid_size - 1, max(0, math.floor(point[1] * grid_size)))
        counts[y * grid_size + x] += 1.0
        total += 1

    for stroke in strokes:
        if len(stroke) < 2:
            continue
        normalized = [
            ((point[0] - min_x) / long_edge, (point[1] - min_y) / long_edge)
            for point in stroke
        ]
        for start, end in zip(normalized, normalized[1:]):
            length = math.dist(start, end)
            steps = max(1, math.ceil(length * grid_size * 6.0))
            for step in range(steps):
                alpha = step / steps
                add(
                    (
                        start[0] + (end[0] - start[0]) * alpha,
                        start[1] + (end[1] - start[1]) * alpha,
                    )
                )
        add(normalized[-1])
    features = [value / total for value in counts]

    def resample_stroke(stroke):
        normalized = [
            ((point[0] - min_x) / long_edge, (point[1] - min_y) / long_edge)
            for point in stroke
        ]
        points = []
        for point in normalized:
            if not points or math.dist(points[-1], point) ** 2 > 1.0e-8:
                points.append(point)
        if len(points) < 2:
            return []

        distances = [0.0]
        for start, end in zip(points, points[1:]):
            distances.append(distances[-1] + math.dist(start, end))
        total_length = distances[-1]
        if total_length <= 1.0e-8:
            return []

        result = []
        segment_index = 1
        for sample_index in range(STRUCTURAL_SAMPLE_COUNT):
            target_distance = total_length * sample_index / (STRUCTURAL_SAMPLE_COUNT - 1)
            while (
                segment_index < len(distances) - 1
                and distances[segment_index] < target_distance
            ):
                segment_index += 1
            segment_start = distances[segment_index - 1]
            segment_length = distances[segment_index] - segment_start
            alpha = (
                (target_distance - segment_start) / segment_length
                if segment_length > 1.0e-8
                else 0.0
            )
            start = points[segment_index - 1]
            end = points[segment_index]
            result.append(
                (
                    start[0] + (end[0] - start[0]) * alpha,
                    start[1] + (end[1] - start[1]) * alpha,
                )
            )

        smoothed = list(result)
        for index in range(1, len(result) - 1):
            previous = result[index - 1]
            current = result[index]
            following = result[index + 1]
            smoothed[index] = (
                (previous[0] + current[0] * 2.0 + following[0]) * 0.25,
                (previous[1] + current[1] * 2.0 + following[1]) * 0.25,
            )
        return smoothed

    total_length = 0.0
    endpoint_distance = 0.0
    total_signed_turning = 0.0
    total_absolute_turning = 0.0
    for stroke in strokes:
        points = resample_stroke(stroke)
        if len(points) < 2:
            continue
        endpoint_distance += math.dist(points[0], points[-1])
        previous_direction = None
        for start, end in zip(points, points[1:]):
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            segment_length = math.hypot(dx, dy)
            if segment_length <= 1.0e-8:
                continue
            total_length += segment_length
            direction = (dx / segment_length, dy / segment_length)
            if previous_direction is not None:
                cross = previous_direction[0] * direction[1] - previous_direction[1] * direction[0]
                dot = previous_direction[0] * direction[0] + previous_direction[1] * direction[1]
                angle = math.atan2(cross, dot)
                total_signed_turning += angle
                total_absolute_turning += abs(angle)
            previous_direction = direction

    directness = endpoint_distance / total_length if total_length > 1.0e-8 else 0.0
    net_turning = min(1.0, abs(total_signed_turning) / (4.0 * math.pi))
    turn_consistency = (
        min(1.0, abs(total_signed_turning) / total_absolute_turning)
        if total_absolute_turning > 1.0e-8
        else 0.0
    )
    normalized_path_length = min(1.0, total_length / 4.0)
    features.extend(
        [
            directness * DIRECTNESS_WEIGHT,
            net_turning * NET_TURNING_WEIGHT,
            turn_consistency * TURN_CONSISTENCY_WEIGHT,
            normalized_path_length * PATH_LENGTH_WEIGHT,
        ]
    )
    return features


def canonical_circle():
    return [[
        (
            0.5 + 0.5 * math.cos(-math.pi / 2 + index * 2 * math.pi / 96),
            0.5 + 0.5 * math.sin(-math.pi / 2 + index * 2 * math.pi / 96),
        )
        for index in range(97)
    ]]


def canonical_spiral():
    """一笔两圈的阿基米德螺旋；绘制方向不会影响占用特征。"""
    point_count = 128
    return [[
        (
            0.5 + (0.08 + 0.40 * index / point_count)
            * math.cos(-math.pi / 2 + index * 4 * math.pi / point_count),
            0.5 + (0.08 + 0.40 * index / point_count)
            * math.sin(-math.pi / 2 + index * 4 * math.pi / point_count),
        )
        for index in range(point_count + 1)
    ]]


TEMPLATES = {
    HORIZONTAL: {
        "strokes": [[(0.0, 0.0), (1.0, 0.0)]],
        "stroke_count": 1,
        "skill": "横线",
        "tolerance": 0.35,
        "min_aspect": 2.5,
        "max_aspect": 1000.0,
    },
    VERTICAL: {
        "strokes": [[(0.0, 0.0), (0.0, 1.0)]],
        "stroke_count": 1,
        "skill": "竖线",
        "tolerance": 0.35,
        "min_aspect": 0.0,
        "max_aspect": 0.4,
    },
    CIRCLE: {
        "strokes": canonical_circle(),
        "stroke_count": 1,
        "skill": "圆",
        "tolerance": 0.35,
        "min_aspect": 0.60,
        "max_aspect": 1.67,
    },
    CROSS: {
        "strokes": [[(0.0, 0.0), (1.0, 1.0)], [(1.0, 0.0), (0.0, 1.0)]],
        "stroke_count": 2,
        "skill": "叉",
        "tolerance": 0.35,
        "min_aspect": 0.60,
        "max_aspect": 1.67,
    },
    LIGHTNING: {
        "strokes": [[(0.68, 0.0), (0.24, 0.44), (0.60, 0.44), (0.18, 1.0)]],
        "stroke_count": 1,
        "skill": "闪电",
        "tolerance": 0.35,
        "min_aspect": 0.25,
        "max_aspect": 0.90,
    },
    SPIRAL: {
        "strokes": canonical_spiral(),
        "stroke_count": 1,
        "skill": "螺旋",
        "tolerance": 0.35,
        "min_aspect": 0.60,
        "max_aspect": 1.67,
    },
}


def find_property_name(obj, display_name):
    """蓝图变量有时带 GUID 后缀，通过导出文本找到真实属性名。"""
    try:
        obj.get_editor_property(display_name)
        return display_name
    except Exception:
        pass

    # UE Python 不公开 FProperty 迭代器，call_method 可通过对象反射访问常规变量。
    # 当前工程中的中文蓝图变量通常就是显示名；这里保留明确错误，防止静默写错。
    raise RuntimeError(f"{obj.get_path_name()} 找不到属性 {display_name}")


def set_template_values(asset, spec):
    values = {
        "特征": stable_features(spec["strokes"]),
        "笔画数": spec["stroke_count"],
        "容差": spec["tolerance"],
        "技能标识": unreal.Name(spec["skill"]),
        "最小宽高比": spec["min_aspect"],
        "最大宽高比": spec["max_aspect"],
    }
    for property_name, value in values.items():
        property_name = find_property_name(asset, property_name)
        asset.set_editor_property(property_name, value)
    unreal.EditorAssetLibrary.save_loaded_asset(asset)
    log(
        f"模板 {asset.get_name()}: 笔画={spec['stroke_count']} "
        f"特征={len(values['特征'])} 容差={spec['tolerance']}"
    )


def ensure_templates():
    for path in (CIRCLE, CROSS, LIGHTNING, SPIRAL):
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            if not unreal.EditorAssetLibrary.duplicate_asset(VERTICAL, path):
                raise RuntimeError(f"创建模板失败: {path}")

    assets = []
    for path, spec in TEMPLATES.items():
        asset = unreal.EditorAssetLibrary.load_asset(path)
        if not asset:
            raise RuntimeError(f"加载模板失败: {path}")
        set_template_values(asset, spec)
        assets.append(asset)
    return assets


def replace_feature_graph(bp):
    editor = BGE.get_graph_editor_by_name(bp, "算特征")
    if not editor:
        raise RuntimeError("找不到算特征图")
    graph = editor.get_graph()
    nodes = [
        node
        for node in unreal.ObjectIterator(unreal.EdGraphNode)
        if node.get_outer() == graph
    ]
    entries = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)]
    results = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionResult)]
    if len(entries) != 1 or not results:
        raise RuntimeError(f"算特征入口/出口异常: entry={len(entries)} result={len(results)}")

    entry = entries[0]
    result = results[-1]
    removable = [node for node in nodes if node not in (entry, result)] + results[:-1]
    if removable:
        editor.remove_nodes(removable)

    call = editor.add_call_function_node(
        "/Script/RuneofSuccor.RuneRecognitionLibrary:ExtractRuneFeatures"
    )
    if not call:
        raise RuntimeError("无法创建稳定特征提取节点")
    set_pos(entry, -600, 0)
    set_pos(call, -200, 0)
    set_pos(result, 350, 0)

    required = [
        (pin(entry, "then"), pin(call, "execute"), "执行入口"),
        (pin(entry, "笔画"), pin(call, "Strokes"), "笔画数据"),
        (pin(call, "then"), pin(result, "execute"), "执行出口"),
        (pin(call, "Features"), pin(result, "特征"), "特征结果"),
        (pin(call, "AspectRatio"), pin(result, "宽高比"), "宽高比"),
    ]
    for source, target, label in required:
        if not connect(source, target):
            names = [str(p.get_pin_name()) for p in (bel.list_all_pins(call) or [])]
            raise RuntimeError(f"连接{label}失败，识别节点引脚={names}")

    grid_pin = pin(call, "GridSize")
    if grid_pin:
        try:
            grid_pin.set_default_value(str(GRID_SIZE))
        except Exception:
            pass
    log(f"算特征已替换，移除旧节点 {len(removable)} 个")


def replace_score_graph(bp):
    """Replace the old 16-element Blueprint scorer with the native dynamic scorer."""
    editor = BGE.get_graph_editor_by_name(bp, "比分")
    if not editor:
        raise RuntimeError("找不到比分图")
    graph = editor.get_graph()
    nodes = [
        node
        for node in unreal.ObjectIterator(unreal.EdGraphNode)
        if node.get_outer() == graph
    ]
    entries = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionEntry)]
    results = [node for node in nodes if isinstance(node, unreal.K2Node_FunctionResult)]
    if len(entries) != 1 or not results:
        raise RuntimeError(f"比分入口/出口异常: entry={len(entries)} result={len(results)}")

    entry = entries[0]
    result = results[0]
    removable = [node for node in nodes if node not in (entry, result)]
    if removable:
        editor.remove_nodes(removable)

    call = editor.add_call_function_node(
        "/Script/RuneofSuccor.RuneRecognitionLibrary:ScoreRuneFeatures"
    )
    if not call:
        raise RuntimeError("无法创建原生特征距离节点")

    set_pos(entry, -550, 0)
    set_pos(call, -100, 120)
    set_pos(result, 350, 0)
    required = [
        (pin(entry, "then"), pin(result, "execute"), "执行连接"),
        (pin(entry, "A"), pin(call, "A"), "特征 A"),
        (pin(entry, "B"), pin(call, "B"), "特征 B"),
        (pin(call, "ReturnValue"), pin(result, "分数"), "距离结果"),
    ]
    for source, target, label in required:
        if not connect(source, target):
            names = [str(item.get_pin_name()) for item in (bel.list_all_pins(call) or [])]
            raise RuntimeError(f"连接{label}失败，评分节点引脚={names}")
    log(f"比分已替换为动态长度评分，移除旧节点 {len(removable)} 个")


def update_library(bp, templates):
    default = unreal.get_default_object(bp.generated_class())
    property_name = find_property_name(default, "符库")
    current = list(default.get_editor_property(property_name) or [])
    by_path = {item.get_path_name().split(".")[0]: item for item in current if item}
    for item in templates:
        by_path[item.get_path_name().split(".")[0]] = item
    ordered = [
        by_path[path]
        for path in (HORIZONTAL, VERTICAL, CIRCLE, CROSS, LIGHTNING, SPIRAL)
        if path in by_path
    ]
    ordered.extend(
        item
        for path, item in by_path.items()
        if path not in (HORIZONTAL, VERTICAL, CIRCLE, CROSS, LIGHTNING, SPIRAL)
    )
    default.set_editor_property(property_name, ordered)
    log(f"符库已更新: {[item.get_name() for item in ordered]}")


def fix_result_guard(bp):
    """把容差判断放进候选循环，避免最佳符为空时纯节点仍提前读取属性。"""
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    if not editor:
        raise RuntimeError("找不到 EventGraph")
    graph = editor.get_graph()
    nodes = [
        node
        for node in unreal.ObjectIterator(unreal.EdGraphNode)
        if node.get_outer() == graph
    ]

    is_valid = next((node for node in nodes if node_title(node) == "IsValid"), None)
    if is_valid:
        valid_output = pin(is_valid, "ReturnValue")
        already_guarded = any(
            isinstance(item.get_owning_node(), unreal.K2Node_IfThenElse)
            and str(item.get_pin_name()) == "Condition"
            for item in linked_pins(valid_output)
        )
        if already_guarded:
            log("识别结果空引用保护已经生效，跳过重复改线")
            return

    tolerance_get = next((node for node in nodes if node_title(node) == "Get 容差"), None)
    max_aspect_get = next((node for node in nodes if node_title(node) == "Get 最大宽高比"), None)
    if not is_valid or not tolerance_get or not max_aspect_get:
        raise RuntimeError("识别结果保护所需节点不完整")

    score_vs_tolerance = next(
        (
            node
            for node in nodes
            if node_title(node) == "float < float"
            and is_linked_to_node(pin(node, "B"), tolerance_get)
        ),
        None,
    )
    score_vs_best = next(
        (
            node
            for node in nodes
            if node_title(node) == "float < float"
            and any(node_title(item.get_owning_node()) == "Get 最佳分数" for item in linked_pins(pin(node, "B")))
        ),
        None,
    )
    if not score_vs_tolerance or not score_vs_best:
        raise RuntimeError("找不到分数比较节点")

    and_node = next(
        (
            node
            for node in nodes
            if node_title(node) == "AND Boolean"
            and is_linked_to_node(pin(node, "B"), score_vs_tolerance)
        ),
        None,
    )
    if not and_node:
        raise RuntimeError("找不到最终 AND 节点")

    valid_output = pin(is_valid, "ReturnValue")
    and_output = pin(and_node, "ReturnValue")
    score_best_output = pin(score_vs_best, "ReturnValue")
    final_branch = next(
        (
            item.get_owning_node()
            for item in linked_pins(valid_output)
            if isinstance(item.get_owning_node(), unreal.K2Node_IfThenElse)
        ),
        None,
    )
    loop_branch = next(
        (
            item.get_owning_node()
            for item in linked_pins(and_output)
            if isinstance(item.get_owning_node(), unreal.K2Node_IfThenElse)
        ),
        None,
    )

    # 未修复版本中，最终分支接 AND，循环分支接“分数 < 最佳分数”。
    if not final_branch:
        final_branch = next(
            (
                item.get_owning_node()
                for item in linked_pins(and_output)
                if isinstance(item.get_owning_node(), unreal.K2Node_IfThenElse)
            ),
            None,
        )
    if not loop_branch or loop_branch == final_branch:
        loop_branch = next(
            (
                item.get_owning_node()
                for item in linked_pins(score_best_output)
                if isinstance(item.get_owning_node(), unreal.K2Node_IfThenElse)
            ),
            None,
        )
    if not final_branch or not loop_branch or final_branch == loop_branch:
        raise RuntimeError("无法区分最终分支和候选分支")

    candidate_links = linked_pins(pin(max_aspect_get, "self"))
    if not candidate_links:
        raise RuntimeError("找不到当前候选符引用")
    candidate_pin = candidate_links[0]
    score_links = linked_pins(pin(score_vs_best, "A"))
    if not score_links:
        raise RuntimeError("找不到当前候选分数")
    current_score_pin = score_links[0]

    # 候选必须同时满足：比当前最佳分数小，并且低于该候选自己的容差。
    break_links(pin(and_node, "A"))
    connect(score_best_output, pin(and_node, "A"))
    break_links(pin(score_vs_tolerance, "A"))
    connect(current_score_pin, pin(score_vs_tolerance, "A"))
    break_links(pin(tolerance_get, "self"))
    connect(candidate_pin, pin(tolerance_get, "self"))
    break_links(pin(loop_branch, "Condition"))
    connect(and_output, pin(loop_branch, "Condition"))

    # 循环结束后只检查引用是否有效，空引用不会再触发属性读取错误。
    break_links(pin(final_branch, "Condition"))
    connect(valid_output, pin(final_branch, "Condition"))
    log("已修复最佳符为空时的容差读取，并将容差筛选前移到候选循环")


def main():
    templates = ensure_templates()
    bp = unreal.EditorAssetLibrary.load_asset(COMPONENT)
    if not bp:
        raise RuntimeError("加载 BPC_画符系统 失败")
    replace_feature_graph(bp)
    replace_score_graph(bp)
    update_library(bp, templates)
    fix_result_guard(bp)
    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp)
    unreal.EditorAssetLibrary.save_asset(COMPONENT, only_if_is_dirty=False)
    log("升级完成")


main()
