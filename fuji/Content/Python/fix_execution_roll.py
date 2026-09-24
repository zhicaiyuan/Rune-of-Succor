# -*- coding: utf-8 -*-
"""修复锁定翻滚的根运动模式，并让处决对齐点跟随移动的目标。"""

import unreal


BP_PATH = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BP_ThirdPersonCharacter"
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"Missing pin: {node.get_name()}.{name}")


def main():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not bp:
        raise RuntimeError("Player Blueprint was not found")
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    if not editor:
        raise RuntimeError("Player EventGraph was not found")
    graph = editor.get_graph()
    nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
             if node.get_outer() == graph}

    # 锁定目标有效时两个分支都会每帧覆盖根运动模式；仅蒙太奇模式仍保留攻击、翻滚和处决的根位移。
    for node_name, previous in (
        ("K2Node_CallFunction_128", "IgnoreRootMotion"),
        ("K2Node_CallFunction_119", "RootMotionFromEverything"),
    ):
        node = nodes.get(node_name)
        if not node or str(BEL.get_node_title(node)) != "SetRootMotionMode":
            raise RuntimeError(f"Unexpected root-motion node: {node_name}")
        value = pin(node, "Value")
        current = str(value.get_pin_value())
        if current not in (previous, "RootMotionFromMontagesOnly"):
            raise RuntimeError(f"Unexpected root-motion mode at {node_name}: {current}")
        value.set_pin_value("RootMotionFromMontagesOnly")
        if str(value.get_pin_value()) != "RootMotionFromMontagesOnly":
            raise RuntimeError(f"Could not update root-motion mode at {node_name}")

    # 第 2、3 组处决会带动目标移动，WarpTarget 应跟随目标胶囊体，而不是固定在起始位置。
    warp = nodes.get("K2Node_CallFunction_51")
    target = nodes.get("K2Node_MacroInstance_1")
    if not warp or str(BEL.get_node_title(warp)) != "AddOrUpdateWarpTarget" or not target:
        raise RuntimeError("Execution warp path was not found")
    component_input = pin(warp, "WarpTarget_Component")
    connected_sources = list(component_input.list_connected_pins() or [])
    if not connected_sources:
        root = editor.add_call_function_node("/Script/Engine.Actor:K2_GetRootComponent")
        if not root:
            raise RuntimeError("Could not add target root-component getter")
        try:
            BEL.set_node_pos(root, unreal.IntPoint(-2280, 510))
        except Exception:
            pass
        target_output = pin(target, "Array Element")
        if not target_output.try_create_connection(pin(root, "self")):
            raise RuntimeError("Could not connect execution target to root getter")
        if not pin(root, "ReturnValue").try_create_connection(component_input):
            raise RuntimeError("Could not connect target capsule to warp target")
    follow = pin(warp, "WarpTarget_bFollowComponent")
    follow.set_pin_value("true")
    if str(follow.get_pin_value()).lower() != "true":
        raise RuntimeError("Could not enable moving warp target")

    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("Could not save player Blueprint")
    unreal.log("[ExecutionRollFix] Montage root motion and moving execution warp target saved")


main()
