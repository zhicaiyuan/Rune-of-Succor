# -*- coding: utf-8 -*-
"""Cap dummy knockback and remove ordinary combo root translation."""

import unreal


BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
DUMMY = "/Game/\u84dd\u56fe/BP_\u6d4b\u8bd5\u5047\u4eba"
ATTACK = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BPC_\u653b\u51fb\u7cfb\u7edf"
COMBO_DIR = "/Game/Sword_Animations/Animations/Sequence1/02_Attack/03_Combo_Attack_03"


def log(message):
    unreal.log(f"[CombatTuning] {message}")


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError(f"Missing pin {node.get_name()}.{name}")


def connected(graph_pin):
    return list(graph_pin.list_connected_pins() or [])


def break_links(graph_pin):
    if hasattr(graph_pin, "break_all_pin_links"):
        graph_pin.break_all_pin_links()
    else:
        graph_pin.break_pin_links()


def connect(source, target, label):
    try:
        ok = bool(source.try_create_connection(target))
    except Exception:
        ok = bool(target.try_create_connection(source))
    if not ok:
        raise RuntimeError(f"Connection failed: {label}")


def patch_dummy():
    bp = unreal.EditorAssetLibrary.load_asset(DUMMY)
    if not bp:
        raise RuntimeError("Dummy Blueprint could not be loaded")
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = editor.get_graph()
    nodes = [n for n in unreal.ObjectIterator(unreal.EdGraphNode) if n.get_outer() == graph]
    old = next((n for n in nodes if n.get_name() == "K2Node_CallFunction_4"), None)
    existing = next(
        (n for n in nodes if isinstance(n, unreal.K2Node) and str(BEL.get_node_title(n)) == "Apply Tuned Knockback"),
        None,
    )
    if existing:
        log("Tuned knockback node already exists")
        return
    if not old or str(BEL.get_node_title(old)) != "LaunchCharacter":
        raise RuntimeError("Original dummy LaunchCharacter node was not found")

    inputs = connected(pin(old, "execute"))
    outputs = connected(pin(old, "then"))
    velocities = connected(pin(old, "LaunchVelocity"))
    if len(inputs) != 1 or not outputs or len(velocities) != 1:
        raise RuntimeError("Original knockback connections differ from expected graph")
    attack_index = next((n for n in nodes if n.get_name() == "K2Node_VariableGet_1"), None)
    if not attack_index:
        raise RuntimeError("AttackIndex getter was not found")

    for name in ("execute", "then", "LaunchVelocity"):
        break_links(pin(old, name))
    call = editor.add_call_function_node(
        "/Script/RuneofSuccor.CombatFeelLibrary:ApplyTunedKnockback"
    )
    if not call:
        raise RuntimeError("Could not create tuned knockback node")
    try:
        BEL.set_node_pos(call, unreal.IntPoint(940, 450))
    except Exception:
        pass
    connect(inputs[0], pin(call, "execute"), "hit event to tuned knockback")
    for target in outputs:
        connect(pin(call, "then"), target, "tuned knockback to damage")
    connect(velocities[0], pin(call, "RequestedVelocity"), "original knockback direction")
    connect(pin(attack_index, "AttackIndex"), pin(call, "AttackIndex"), "combo index")
    editor.remove_nodes([old])
    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    log("Dummy now caps final knockback velocity and resets accumulated momentum")


def patch_combo_sequences():
    for index in range(1, 5):
        path = f"{COMBO_DIR}/Combo_Attack_03_0{index}_Seq"
        sequence = unreal.EditorAssetLibrary.load_asset(path)
        if not isinstance(sequence, unreal.AnimSequence):
            raise RuntimeError(f"Combo sequence missing: {path}")
        was_enabled = bool(sequence.get_editor_property("enable_root_motion"))
        sequence.set_editor_property("enable_root_motion", True)
        sequence.set_editor_property("force_root_lock", False)
        unreal.EditorAssetLibrary.save_loaded_asset(sequence, False)
        log(f"Combo {index} root movement restored (was_enabled={was_enabled})")


def title(node):
    try:
        return str(BEL.get_node_title(node))
    except Exception:
        return node.get_name()


def add_root_motion_node(editor, function_name, x, y):
    node = editor.add_call_function_node(
        f"/Script/RuneofSuccor.CombatFeelLibrary:{function_name}"
    )
    if not node:
        raise RuntimeError(f"Could not create {function_name}")
    try:
        BEL.set_node_pos(node, unreal.IntPoint(x, y))
    except Exception:
        pass
    return node


def insert_after(editor, output_pin, function_name, x, y, label):
    downstream = connected(output_pin)
    if any(title(item.get_owning_node()) == label for item in downstream):
        return False
    break_links(output_pin)
    helper = add_root_motion_node(editor, function_name, x, y)
    connect(output_pin, pin(helper, "execute"), f"{label} input")
    for target in downstream:
        connect(pin(helper, "then"), target, f"{label} continuation")
    return True


def patch_attack_root_motion():
    bp = unreal.EditorAssetLibrary.load_asset(ATTACK)
    if not bp:
        raise RuntimeError("Attack component Blueprint could not be loaded")
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    if not editor:
        raise RuntimeError("Attack EventGraph could not be edited")
    graph = editor.get_graph()
    montage_nodes = [
        node for node in unreal.ObjectIterator(unreal.K2Node_PlayMontage)
        if node.get_outer() == graph
    ]
    if not montage_nodes:
        raise RuntimeError("No attack montage nodes were found")
    patched = 0
    for montage in montage_nodes:
        if insert_after(
            editor, pin(montage, "then"), "BeginAttackRootMotion",
            1800, 300 + patched * 650, "Begin Attack Root Motion"
        ):
            patched += 1
        for index, output_name in enumerate(("OnCompleted", "OnBlendOut", "OnInterrupted")):
            insert_after(
                editor, pin(montage, output_name), "EndAttackRootMotion",
                2200 + index * 220, 300 + patched * 650,
                "End Attack Root Motion"
            )
    BEL.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    log(f"Attack root translation scaled to 55% for {len(montage_nodes)} montage nodes ({patched} new)")


patch_dummy()
patch_combo_sequences()
patch_attack_root_motion()
log("Combat tuning assets saved")
