# -*- coding: utf-8 -*-
"""空中连击期间阻止普通攻击通知触发地面连击事件。"""

import unreal


PATH = "/Game/蓝图/玩家/BPC_攻击系统"
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
bp = unreal.EditorAssetLibrary.load_asset(PATH)
if not bp:
    raise RuntimeError("攻击系统蓝图未找到")
editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
if not editor:
    raise RuntimeError("攻击系统 EventGraph 未找到")
graph = editor.get_graph()


def title(node):
    return str(BEL.get_node_title(node))


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"缺少引脚 {node.get_name()}.{name}")


def connect(source, target):
    if not source.try_create_connection(target):
        raise RuntimeError(f"连接失败 {source.get_owning_node().get_name()} -> {target.get_owning_node().get_name()}")


events = {title(node): node for node in unreal.ObjectIterator(unreal.K2Node_CustomEvent)
          if node.get_outer() == graph}
changed = False
for event_title in ("普通攻击连击", "终止普通攻击连击"):
    event = events.get(event_title)
    if not event:
        raise RuntimeError(f"缺少事件 {event_title}")
    source = pin(event, "then")
    downstream = list(source.list_connected_pins() or [])
    if any(title(item.get_owning_node()) == "分支"
           and any(title(connected.get_owning_node()) == "Is Air Attack Active"
                   for connected in pin(item.get_owning_node(), "Condition").list_connected_pins() or [])
           for item in downstream):
        unreal.log(f"[AirComboGate] {event_title} 已有空中攻击保护")
        continue
    if len(downstream) != 1:
        raise RuntimeError(f"{event_title} 的现有执行连接不符合预期")
    active = editor.add_call_function_node("/Script/RuneofSuccor.CombatFeelLibrary:IsAirAttackActive")
    branch = editor.add_branch_node()
    if not active or not branch:
        raise RuntimeError("创建空中攻击状态节点失败")
    try:
        x = int(event.get_editor_property("node_pos_x"))
        y = int(event.get_editor_property("node_pos_y"))
        BEL.set_node_pos(active, unreal.IntPoint(x + 270, y + 135))
        BEL.set_node_pos(branch, unreal.IntPoint(x + 510, y))
    except Exception:
        pass
    source.break_pin_links()
    connect(source, pin(branch, "execute"))
    connect(pin(active, "ReturnValue"), pin(branch, "Condition"))
    connect(pin(branch, "else"), downstream[0])
    changed = True
    unreal.log(f"[AirComboGate] {event_title} 已屏蔽空中攻击")

if changed:
    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("保存攻击系统蓝图失败")
