# -*- coding: utf-8 -*-
"""复用原八方向翻滚索引，空中选择 Dodge_Air 蒙太奇。"""

import unreal


BP_PATH = "/Game/蓝图/玩家/BP_ThirdPersonCharacter"
SOURCE_BASE = "/Game/Sword_Animations/Animations/Sequence1/06_Dodge/03_Dodge_Air"
DIRECTIONS = ("F", "F_R_45", "R", "B_R_45", "B", "B_L_45", "L", "F_L_45")
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚 {node.get_name()}.{name}")


def connect(source, target):
    if not source.try_create_connection(target):
        raise RuntimeError(f"连接失败 {source.get_owning_node().get_name()} -> {target.get_owning_node().get_name()}")


for direction in DIRECTIONS:
    name = f"Dodge_Air_{direction}_Seq"
    sequence = unreal.EditorAssetLibrary.load_asset(f"{SOURCE_BASE}/{name}")
    if not isinstance(sequence, unreal.AnimSequence):
        raise RuntimeError(f"空中闪避序列缺失：{name}")
    if not sequence.get_editor_property("enable_root_motion"):
        sequence.set_editor_property("enable_root_motion", True)
        sequence.set_editor_property("force_root_lock", False)
        if not unreal.EditorAssetLibrary.save_loaded_asset(sequence, False):
            raise RuntimeError(f"无法保存根运动：{name}")
        unreal.log(f"[AirDodge] 启用根运动：{name}")

bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
if not bp:
    raise RuntimeError("角色蓝图未找到")
editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
if not editor:
    raise RuntimeError("角色 EventGraph 未找到")
graph = editor.get_graph()
nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
         if node.get_outer() == graph}
ground_array_item = nodes.get("K2Node_GetArrayItem_0")
direction_getter = nodes.get("K2Node_VariableGet_58")
roll_montage = nodes.get("K2Node_PlayMontage_3")
if not all((ground_array_item, direction_getter, roll_montage)):
    raise RuntimeError("原八方向翻滚节点已变化，未修改蓝图")
montage_input = pin(roll_montage, "MontageToPlay")
existing = list(montage_input.list_connected_pins() or [])
if len(existing) == 1 and str(BEL.get_node_title(existing[0].get_owning_node())) == "Select Air Dodge Montage":
    unreal.log("[AirDodge] 八方向空中选择已接入，无需重复修改")
else:
    if len(existing) != 1 or existing[0].get_owning_node() != ground_array_item:
        raise RuntimeError("原翻滚蒙太奇输入已变化，未修改蓝图")
    selector = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:SelectAirDodgeMontage")
    if not selector:
        raise RuntimeError("创建空中闪避选择节点失败")
    try:
        x = int(roll_montage.get_editor_property("node_pos_x"))
        y = int(roll_montage.get_editor_property("node_pos_y"))
        BEL.set_node_pos(selector, unreal.IntPoint(x - 390, y + 180))
    except Exception:
        pass
    montage_input.break_pin_links()
    connect(pin(ground_array_item, "Output"), pin(selector, "GroundMontage"))
    connect(pin(direction_getter, "翻滚方向"), pin(selector, "DirectionIndex"))
    connect(pin(selector, "ReturnValue"), montage_input)
    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("角色蓝图保存失败")
    unreal.log("[AirDodge] 左 Shift 空中使用 Dodge_Air 八方向，地面保持原翻滚")
