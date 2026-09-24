# -*- coding: utf-8 -*-
"""一次选定处决动画并缓存目标，避免瞬移后重读空的重叠数组。"""

import unreal


PATH = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BP_ThirdPersonCharacter"
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚：{node.get_name()}.{name}")


def connected(source, target):
    return any(item.get_owning_node().get_name() == target.get_owning_node().get_name()
               and str(item.get_pin_name()) == str(target.get_pin_name())
               for item in source.list_connected_pins() or [])


def wire(source, target, label):
    if connected(source, target):
        return
    target.break_pin_links()
    try:
        ok = bool(source.try_create_connection(target))
    except Exception:
        ok = bool(target.try_create_connection(source))
    if not ok or not connected(source, target):
        raise RuntimeError(f"无法连接：{label}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(PATH)
    if not bp:
        raise RuntimeError("找不到玩家蓝图")
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = editor.get_graph()
    nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
             if node.get_outer() == graph}

    loop = nodes["K2Node_MacroInstance_1"]
    target_branch = nodes["K2Node_IfThenElse_6"]
    message = nodes["K2Node_Message_0"]
    old_pair = nodes["K2Node_CallFunction_116"]
    warp = nodes["K2Node_CallFunction_51"]
    montage = nodes["K2Node_PlayMontage_2"]
    montage_array = nodes["K2Node_VariableGet_42"]
    if str(BEL.get_node_title(old_pair)) != "Prepare Execution Pair":
        raise RuntimeError("处决准备节点与预期不符")

    pair = editor.add_call_function_node("/Script/RuneofSuccor.CombatFeelLibrary:PrepareExecutionPair")
    if not pair:
        raise RuntimeError("无法创建新版处决准备节点")
    try:
        BEL.set_node_pos(pair, unreal.IntPoint(1660, 2640))
    except Exception:
        pass
    for name in ("ExecutionMontages", "WarpTargetComponent", "PreparedTarget",
                 "SelectedMontage", "AnimationIndex", "WarpTargetName", "ReturnValue"):
        pin(pair, name)

    success = nodes.get("ExecutionPreparedBranch")
    if not success:
        success = editor.add_branch_node()
        if not success:
            raise RuntimeError("无法添加处决成功分支")
        success.rename("ExecutionPreparedBranch")
        try:
            BEL.set_node_pos(success, unreal.IntPoint(1890, 2640))
        except Exception:
            pass

    wire(pin(montage_array, "处决动画数组"), pin(pair, "ExecutionMontages"), "动画数组 → 一次选择")
    wire(pin(loop, "Array Element"), pin(pair, "Target"), "重叠目标 → 处决准备")
    wire(pin(target_branch, "then"), pin(pair, "execute"), "目标有效 → 处决准备")
    wire(pin(pair, "then"), pin(success, "execute"), "准备完成 → 成功检查")
    wire(pin(pair, "ReturnValue"), pin(success, "Condition"), "准备结果 → 成功检查")
    wire(pin(success, "then"), pin(message, "execute"), "成功 → 敌人处决动画")
    wire(pin(pair, "PreparedTarget"), pin(message, "self"), "缓存目标 → 敌人处决动画")
    wire(pin(pair, "AnimationIndex"), pin(message, "随机动画数"), "单次索引 → 敌人动画")
    wire(pin(message, "then"), pin(warp, "execute"), "敌人动画 → Motion Warping")
    wire(pin(pair, "WarpTargetComponent"), pin(warp, "WarpTarget_Component"), "缓存组件 → WarpTarget")
    wire(pin(pair, "WarpTargetName"), pin(warp, "WarpTarget_Name"), "蒙太奇名称 → WarpTarget")
    wire(pin(pair, "WarpLocation"), pin(warp, "WarpTarget_Location"), "位置 → WarpTarget")
    wire(pin(pair, "WarpRotation"), pin(warp, "WarpTarget_Rotation"), "朝向 → WarpTarget")
    wire(pin(warp, "then"), pin(montage, "execute"), "WarpTarget → 玩家动画")
    wire(pin(pair, "SelectedMontage"), pin(montage, "MontageToPlay"), "同一动画 → 玩家蒙太奇")

    editor.remove_nodes([old_pair])

    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("玩家蓝图保存失败")
    unreal.log("[ExecutionStable] Selected one montage and cached target before teleport")


main()
