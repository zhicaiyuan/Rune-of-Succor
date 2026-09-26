"""在原有地面攻击前接入空中左键攻击。"""

import unreal


ASSET = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BPC_\u653b\u51fb\u7cfb\u7edf"
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError("Missing pin %s.%s" % (node.get_name(), name))


def linked(source, target):
    return any(p.get_owning_node() == target.get_owning_node()
               and str(p.get_pin_name()) == str(target.get_pin_name())
               for p in source.list_connected_pins() or [])


def connect(source, target, name):
    if not source.try_create_connection(target):
        raise RuntimeError("Failed to connect " + name)


bp = unreal.EditorAssetLibrary.load_asset(ASSET)
if not bp:
    raise RuntimeError("Attack Blueprint not found")
editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
graph = editor.get_graph()
nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
         if node.get_outer() == graph}
key = nodes.get("K2Node_InputKey_0")
ground = nodes.get("K2Node_IfThenElse_1")
if not key or not ground or str(BEL.get_node_title(key)) != "\u9f20\u6807\u5de6\u952e":
    raise RuntimeError("Existing left-click attack path changed")

existing = next((node for node in nodes.values()
                 if str(BEL.get_node_title(node)) == "Try Air Attack"), None)
if existing:
    unreal.log("[AirAttackInput] Existing aerial attack node found; no duplicate added")
else:
    pressed = pin(key, "Pressed")
    if not linked(pressed, pin(ground, "execute")):
        raise RuntimeError("Left click is no longer connected to the ground attack gate")
    aerial = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:TryAirAttack")
    branch = editor.add_branch_node()
    if not aerial or not branch:
        raise RuntimeError("Could not create aerial input nodes")
    try:
        x = int(key.get_editor_property("node_pos_x"))
        y = int(key.get_editor_property("node_pos_y"))
        BEL.set_node_pos(aerial, unreal.IntPoint(x + 260, y))
        BEL.set_node_pos(branch, unreal.IntPoint(x + 570, y))
    except Exception:
        pass
    pressed.break_pin_links()
    connect(pressed, pin(aerial, "execute"), "left click to air attack")
    connect(pin(aerial, "then"), pin(branch, "execute"), "air result branch")
    connect(pin(aerial, "ReturnValue"), pin(branch, "Condition"), "air handled result")
    connect(pin(branch, "else"), pin(ground, "execute"), "ground attack fallback")
    if not linked(pin(branch, "else"), pin(ground, "execute")):
        raise RuntimeError("Ground combo fallback was not preserved")
    BEL.compile_blueprint(bp)
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
        raise RuntimeError("Failed saving attack Blueprint")
    unreal.log("[AirAttackInput] Left click now runs aerial combo while falling")
