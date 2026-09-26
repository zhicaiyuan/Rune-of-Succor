# -*- coding: utf-8 -*-
"""让原八方向闪避蒙太奇在空中播放期间悬空，结束后恢复下落。"""

import unreal


BP_PATH = "/Game/蓝图/玩家/BP_ThirdPersonCharacter"
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚 {node.get_name()}.{name}")


def link(source, target):
    if not source.try_create_connection(target):
        raise RuntimeError(
            f"连接失败 {source.get_owning_node().get_name()}.{source.get_pin_name()}"
            f" -> {target.get_owning_node().get_name()}.{target.get_pin_name()}"
        )


def connected_to(target, source):
    return any(item.get_owning_node() == source.get_owning_node()
               and str(item.get_pin_name()) == str(source.get_pin_name())
               for item in target.list_connected_pins() or [])


bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
if not bp:
    raise RuntimeError("玩家蓝图未找到")
editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
if not editor:
    raise RuntimeError("玩家 EventGraph 未找到")
graph = editor.get_graph()
nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
         if node.get_outer() == graph}
set_direction = nodes.get("K2Node_VariableSet_29")
play_montage = nodes.get("K2Node_PlayMontage_3")
reset_direction = nodes.get("K2Node_VariableSet_31")
selector = next((node for node in nodes.values()
                 if str(BEL.get_node_title(node)) == "Select Air Dodge Montage"), None)
if not all((set_direction, play_montage, reset_direction, selector)):
    raise RuntimeError("八方向闪避节点未找到，未改动蓝图")

old_play_input = pin(play_montage, "execute")
montage_input = pin(play_montage, "MontageToPlay")
old_completed = pin(play_montage, "OnCompleted")
old_interrupted = pin(play_montage, "OnInterrupted")
old_reset_input = pin(reset_direction, "execute")
existing_begin = next((item.get_owning_node() for item in old_play_input.list_connected_pins() or []
                       if str(BEL.get_node_title(item.get_owning_node())) == "Begin Air Dodge Hover"), None)
if existing_begin:
    existing_end = next((node for node in nodes.values()
                         if str(BEL.get_node_title(node)) == "End Air Dodge Hover"), None)
    if not existing_end or not connected_to(pin(existing_begin, "execute"), pin(set_direction, "then")) \
            or not connected_to(pin(existing_begin, "DodgeMontage"), pin(selector, "ReturnValue")) \
            or not connected_to(pin(existing_end, "execute"), old_completed) \
            or not connected_to(pin(existing_end, "execute"), old_interrupted) \
            or not connected_to(old_reset_input, pin(existing_end, "then")):
        raise RuntimeError("已有悬空节点连接不完整，未重复改动蓝图")
    if not connected_to(montage_input, pin(existing_begin, "ReturnValue")):
        if not connected_to(montage_input, pin(selector, "ReturnValue")):
            raise RuntimeError("闪避动画来源已改变，未改动蓝图")
        montage_input.break_pin_links()
        link(pin(existing_begin, "ReturnValue"), montage_input)
        BEL.compile_blueprint(bp)
        if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
            raise RuntimeError("玩家蓝图保存失败")
        unreal.log("[AirDodgeHover] 已缓存选定的闪避动画，悬空期间方向不会被重新计算")
    else:
        unreal.log("[AirDodgeHover] 悬空和动画选择连接均已保存")
else:
    if not connected_to(old_play_input, pin(set_direction, "then")):
        raise RuntimeError("原蒙太奇执行顺序已变化，未改动蓝图")
    if not connected_to(old_reset_input, old_completed) or not connected_to(old_reset_input, old_interrupted):
        raise RuntimeError("原蒙太奇结束回调已变化，未改动蓝图")

    begin = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:BeginAirDodgeHover")
    end = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:EndAirDodgeHover")
    if not begin or not end:
        raise RuntimeError("创建悬空节点失败")
    try:
        x = int(play_montage.get_editor_property("node_pos_x"))
        y = int(play_montage.get_editor_property("node_pos_y"))
        BEL.set_node_pos(begin, unreal.IntPoint(x - 280, y - 180))
        BEL.set_node_pos(end, unreal.IntPoint(x + 330, y + 90))
    except Exception:
        pass

    old_play_input.break_pin_links()
    link(pin(set_direction, "then"), pin(begin, "execute"))
    link(pin(selector, "ReturnValue"), pin(begin, "DodgeMontage"))
    link(pin(begin, "then"), old_play_input)
    montage_input.break_pin_links()
    link(pin(begin, "ReturnValue"), montage_input)

    old_completed.break_pin_links()
    old_interrupted.break_pin_links()
    link(old_completed, pin(end, "execute"))
    link(old_interrupted, pin(end, "execute"))
    link(pin(end, "then"), old_reset_input)

    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("玩家蓝图保存失败")
    unreal.log("[AirDodgeHover] 闪避开始悬空，结束或中断恢复下落；地面翻滚保持原样")
