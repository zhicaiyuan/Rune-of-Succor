# -*- coding: utf-8 -*-
"""在原左键短按连击前加长按挑飞计时，并刷新敌人空中 Y 轴限速节点。"""

import unreal


BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
ATTACK_BP = "/Game/蓝图/玩家/BPC_攻击系统"
ENEMY_BP = "/Game/蓝图/BP_测试假人"
UPPER_SEQ = "/Game/Sword_Animations/Animations/Sequence1/02_Attack/11_Attack_Up/Attack_Up_01_Seq"


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚 {node.get_name()}.{name}")


def linked(source, target):
    return any(item.get_owning_node() == target.get_owning_node()
               and str(item.get_pin_name()) == str(target.get_pin_name())
               for item in source.list_connected_pins() or [])


def connect(source, target):
    if not source.try_create_connection(target):
        raise RuntimeError(f"连接失败 {source.get_owning_node().get_name()} -> {target.get_owning_node().get_name()}")


sequence = unreal.EditorAssetLibrary.load_asset(UPPER_SEQ)
if not isinstance(sequence, unreal.AnimSequence):
    raise RuntimeError("Attack_Up_01_Seq 动画缺失")
if not sequence.get_editor_property("enable_root_motion"):
    sequence.set_editor_property("enable_root_motion", True)
    sequence.set_editor_property("force_root_lock", False)
    if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, False):
        raise RuntimeError("无法保存挑飞动画根运动")
    unreal.log("[Uppercut] Attack_Up_01_Seq 已启用根运动")

bp = unreal.EditorAssetLibrary.load_asset(ATTACK_BP)
if not bp:
    raise RuntimeError("玩家攻击组件蓝图未找到")
editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
if not editor:
    raise RuntimeError("玩家攻击 EventGraph 未找到")
graph = editor.get_graph()
nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
         if node.get_outer() == graph}
key = nodes.get("K2Node_InputKey_0")
air_attack = nodes.get("K2Node_CallFunction_51")
if not key or not air_attack or str(BEL.get_node_title(key)) != "鼠标左键":
    raise RuntimeError("原左键或空中攻击节点已变化，未改动攻击蓝图")

pressed = pin(key, "Pressed")
released = pin(key, "Released")
begin = next((node for node in nodes.values()
              if str(BEL.get_node_title(node)) == "Begin Uppercut Hold"), None)
end = next((node for node in nodes.values()
            if str(BEL.get_node_title(node)) == "End Uppercut Hold"), None)
if begin or end:
    if not begin or not end or not linked(pressed, pin(begin, "execute")) \
            or not linked(pin(begin, "then"), pin(air_attack, "execute")) \
            or not linked(released, pin(end, "execute")):
        raise RuntimeError("已有挑飞接线不完整，未重复修改")
    unreal.log("[Uppercut] 左键按下与松开接线已保存")
else:
    if not linked(pressed, pin(air_attack, "execute")):
        raise RuntimeError("原左键短按入口已变化，未改动攻击蓝图")
    release_links = list(released.list_connected_pins() or [])
    begin = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:BeginUppercutHold")
    end = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:EndUppercutHold")
    if not begin or not end:
        raise RuntimeError("创建挑飞长按节点失败")
    try:
        x = int(key.get_editor_property("node_pos_x"))
        y = int(key.get_editor_property("node_pos_y"))
        BEL.set_node_pos(begin, unreal.IntPoint(x + 210, y - 170))
        BEL.set_node_pos(end, unreal.IntPoint(x + 210, y + 190))
    except Exception:
        pass
    pressed.break_pin_links()
    connect(pressed, pin(begin, "execute"))
    connect(pin(begin, "then"), pin(air_attack, "execute"))
    released.break_pin_links()
    connect(released, pin(end, "execute"))
    for downstream in release_links:
        connect(pin(end, "then"), downstream)
    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("保存玩家攻击蓝图失败")
    unreal.log("[Uppercut] 短按保持普通/空中连击，长按约 0.4 秒触发挑飞")

enemy = unreal.EditorAssetLibrary.load_asset(ENEMY_BP)
if not enemy:
    raise RuntimeError("测试假人蓝图未找到")
BEL.compile_blueprint(enemy)
if not unreal.EditorAssetLibrary.save_loaded_asset(enemy, False):
    raise RuntimeError("保存假人受击蓝图失败")
unreal.log("[Uppercut] 假人 Apply Tuned Knockback 已刷新，可调 MaxAirborneYSpeed")
