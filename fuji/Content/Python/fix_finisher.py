# -*- coding: utf-8 -*-
"""修正处决同步朝向，并让第三下每段剑追踪各触发一次命中。"""

import unreal


BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
PLAYER = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BP_ThirdPersonCharacter"
ATTACK = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BPC_\u653b\u51fb\u7cfb\u7edf"


def node_map(bp):
    graph = BGE.get_graph_editor_by_name(bp, "EventGraph").get_graph()
    return {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
            if node.get_outer() == graph}


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚：{node.get_name()}.{name}")


def linked(source, target):
    return any(other.get_owning_node().get_name() == target.get_owning_node().get_name()
               and str(other.get_pin_name()) == str(target.get_pin_name())
               for other in source.list_connected_pins() or [])


def main():
    player = unreal.EditorAssetLibrary.load_asset(PLAYER)
    attack = unreal.EditorAssetLibrary.load_asset(ATTACK)
    if not player or not attack:
        raise RuntimeError("玩家或攻击系统蓝图不存在")

    player_nodes = node_map(player)
    warp = player_nodes.get("K2Node_CallFunction_51")
    if not warp or str(BEL.get_node_title(warp)) != "AddOrUpdateWarpTarget":
        raise RuntimeError("处决 WarpTarget 节点与预期不符")
    rotation_offset = pin(warp, "WarpTarget_RotationOffset")
    rotation_offset.set_pin_value("0.000000,0.000000,0.000000")
    if any(abs(float(value.strip())) > 0.001
           for value in str(rotation_offset.get_pin_value()).split(",")):
        raise RuntimeError(f"处决旋转偏移未写入：{rotation_offset.get_pin_value()}")

    attack_nodes = node_map(attack)
    gate = attack_nodes.get("K2Node_MacroInstance_1")
    stop_trace = attack_nodes.get("K2Node_CallFunction_19")
    if not gate or not stop_trace or str(BEL.get_node_title(stop_trace)) != "Clear and Invalidate Timer by Handle":
        raise RuntimeError("剑追踪收尾节点与预期不符")
    reset_input = pin(gate, "Reset")
    trace_stopped = pin(stop_trace, "then")
    if not linked(trace_stopped, reset_input):
        reset_input.break_pin_links()
        if not trace_stopped.try_create_connection(reset_input):
            raise RuntimeError("无法在剑追踪结束时复位命中门闩")
    if not linked(trace_stopped, reset_input):
        raise RuntimeError("命中门闩连线复查失败")

    BEL.compile_blueprint(player)
    BEL.compile_blueprint(attack)
    if not unreal.EditorAssetLibrary.save_loaded_asset(player, False):
        raise RuntimeError("玩家蓝图保存失败")
    if not unreal.EditorAssetLibrary.save_loaded_asset(attack, False):
        raise RuntimeError("攻击系统蓝图保存失败")
    unreal.log("[FinisherFix] Execution rotation and per-window hit reset saved")


main()
