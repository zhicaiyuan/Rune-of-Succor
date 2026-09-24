# -*- coding: utf-8 -*-
"""Patch the existing combat Blueprints to use the native hit and execution helpers."""

import unreal


ATTACK_BP = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BPC_\u653b\u51fb\u7cfb\u7edf"
PLAYER_BP = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BP_ThirdPersonCharacter"
DUMMY_BP = "/Game/\u84dd\u56fe/BP_\u6d4b\u8bd5\u5047\u4eba"
EVENT_GRAPH = "EventGraph"
EXECUTION_FUNCTION = "\u6f5c\u884c\u80cc\u523a\u6697\u6740"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(message):
    unreal.log(f"[CombatFeelUpgrade] {message}")


def pin(node, name):
    if not node:
        return None
    for item in bel.list_all_pins(node) or []:
        try:
            if str(item.get_pin_name()) == name:
                return item
        except Exception:
            pass
    return None


def connected(graph_pin):
    if not graph_pin:
        return []
    return list(graph_pin.list_connected_pins() or [])


def connect(source, target, label):
    if not source or not target:
        raise RuntimeError(f"Missing pin while connecting {label}")
    try:
        ok = bool(source.try_create_connection(target))
    except Exception:
        ok = bool(target.try_create_connection(source))
    if not ok:
        raise RuntimeError(f"Could not connect {label}")


def break_links(graph_pin):
    if not graph_pin:
        return
    if hasattr(graph_pin, "break_all_pin_links"):
        graph_pin.break_all_pin_links()
    else:
        graph_pin.break_pin_links()


def set_default(node, pin_name, value):
    graph_pin = pin(node, pin_name)
    if graph_pin:
        try:
            graph_pin.set_default_value(str(value))
        except Exception as exc:
            log(f"Default skipped: {node.get_name()}.{pin_name}: {exc}")


def set_pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(x, y))
    except Exception:
        pass


def title(node):
    try:
        return str(bel.get_node_title(node))
    except Exception:
        return node.get_name()


def graph_nodes(editor):
    graph = editor.get_graph()
    return [node for node in unreal.ObjectIterator(unreal.EdGraphNode) if node.get_outer() == graph]


def find_by_name(nodes, object_name):
    return next((node for node in nodes if node.get_name() == object_name), None)


def find_by_title(nodes, expected):
    return next((node for node in nodes if title(node) == expected), None)


def move_links(old_pin, new_pin, label):
    links = connected(old_pin)
    break_links(old_pin)
    for item in links:
        connect(item, new_pin, label)


def patch_attack_blueprint(bp):
    editor = BGE.get_graph_editor_by_name(bp, EVENT_GRAPH)
    if not editor:
        raise RuntimeError("Attack EventGraph was not found")
    nodes = graph_nodes(editor)
    new_trace = find_by_title(nodes, "Assisted Melee Trace")
    if not new_trace:
        old_trace = find_by_name(nodes, "K2Node_CallFunction_28")
        if not old_trace or title(old_trace) != "Sphere Trace For Objects":
            old_trace = find_by_title(nodes, "Sphere Trace For Objects")
        if not old_trace:
            raise RuntimeError("The existing sword Sphere Trace node was not found")

        old_links = {
            name: connected(pin(old_trace, name))
            for name in ("execute", "Start", "End", "ObjectTypes", "then", "OutHit", "ReturnValue")
        }
        for name in old_links:
            break_links(pin(old_trace, name))

        new_trace = editor.add_call_function_node(
            "/Script/RuneofSuccor.CombatFeelLibrary:AssistedMeleeTrace"
        )
        if not new_trace:
            raise RuntimeError("Could not create Assisted Melee Trace")
        set_pos(new_trace, 1280, 620)

        for name in ("execute", "Start", "End", "ObjectTypes"):
            for source in old_links[name]:
                connect(source, pin(new_trace, name), f"trace {name}")
        for name in ("then", "OutHit", "ReturnValue"):
            for target in old_links[name]:
                connect(pin(new_trace, name), target, f"trace {name}")

        set_default(new_trace, "Radius", "22.0")
        set_default(new_trace, "bTraceComplex", "false")
        set_default(new_trace, "bIgnoreSelf", "true")
        set_default(new_trace, "AssistDistance", "210.0")
        set_default(new_trace, "AssistHalfAngleDegrees", "65.0")
        editor.remove_nodes([old_trace])
        log("Replaced the single-frame sword trace with swept assisted tracing")
    else:
        log("Assisted sword trace already exists")

    nodes = graph_nodes(editor)
    trace_timer = find_by_name(nodes, "K2Node_CallFunction_8")
    if trace_timer and title(trace_timer) == "Set Timer by Event":
        set_default(trace_timer, "Time", "0.0125")
        set_default(trace_timer, "bLooping", "true")
        set_default(trace_timer, "bMaxOncePerFrame", "true")

    hit_stop_start = find_by_name(nodes, "K2Node_VariableSet_19")
    hit_stop_timer = find_by_name(nodes, "K2Node_CallFunction_2")
    hit_stop_end = find_by_name(nodes, "K2Node_VariableSet_18")
    set_default(hit_stop_start, "CustomTimeDilation", "0.10")
    set_default(hit_stop_timer, "Time", "0.055")
    set_default(hit_stop_timer, "bLooping", "false")
    set_default(hit_stop_end, "CustomTimeDilation", "1.0")

    camera_shake = find_by_name(nodes, "K2Node_CallFunction_9")
    if camera_shake and title(camera_shake) == "PlayWorldCameraShake":
        set_default(camera_shake, "InnerRadius", "0.0")
        set_default(camera_shake, "OuterRadius", "600.0")
        set_default(camera_shake, "Falloff", "1.0")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    log("Attack Blueprint patched")


def patch_player_blueprint(bp):
    editor = BGE.get_graph_editor_by_name(bp, EVENT_GRAPH)
    if not editor:
        raise RuntimeError("Player EventGraph was not found")
    nodes = graph_nodes(editor)

    loop = find_by_name(nodes, "K2Node_MacroInstance_1")
    overlap = find_by_name(nodes, "K2Node_CallFunction_45")
    branch = find_by_name(nodes, "K2Node_IfThenElse_6")
    message = find_by_name(nodes, "K2Node_Message_0")
    warp = find_by_name(nodes, "K2Node_CallFunction_51")
    random_item = find_by_name(nodes, "K2Node_CallArrayFunction_0")
    if not all((loop, overlap, branch, message, warp, random_item)):
        raise RuntimeError("One or more existing execution nodes were not found")

    best = find_by_title(nodes, "Is Best Execution Target")
    if not best:
        best = editor.add_call_function_node(
            "/Script/RuneofSuccor.CombatFeelLibrary:IsBestExecutionTarget"
        )
        if not best:
            raise RuntimeError("Could not create Is Best Execution Target")
        set_pos(best, 1000, 2550)
        connect(pin(overlap, "OverlappingActors"), pin(best, "Candidates"), "execution candidates")
        connect(pin(loop, "Array Element"), pin(best, "Candidate"), "execution candidate")
        break_links(pin(branch, "Condition"))
        connect(pin(best, "ReturnValue"), pin(branch, "Condition"), "closest execution target")
        set_default(best, "MaxDistance", "240.0")
        log("Execution now selects one closest valid target")

    pair = find_by_title(nodes, "Prepare Execution Pair")
    if not pair:
        pair = editor.add_call_function_node(
            "/Script/RuneofSuccor.CombatFeelLibrary:PrepareExecutionPair"
        )
        if not pair:
            raise RuntimeError("Could not create Prepare Execution Pair")
        set_pos(pair, 1660, 2640)

        break_links(pin(message, "then"))
        break_links(pin(warp, "execute"))
        break_links(pin(warp, "WarpTarget_Location"))
        break_links(pin(warp, "WarpTarget_Rotation"))

        connect(pin(message, "then"), pin(pair, "execute"), "message to execution preparation")
        connect(pin(pair, "then"), pin(warp, "execute"), "execution preparation to motion warp")
        connect(pin(loop, "Array Element"), pin(pair, "Target"), "execution target")
        connect(pin(random_item, "OutIndex"), pin(pair, "AnimationIndex"), "execution animation index")
        connect(pin(pair, "WarpLocation"), pin(warp, "WarpTarget_Location"), "root warp location")
        connect(pin(pair, "WarpRotation"), pin(warp, "WarpTarget_Rotation"), "root warp rotation")
        set_default(pair, "IgnoreCollisionDuration", "2.5")
        log("Execution motion warping now uses the target actor root")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    log("Player Blueprint patched")


def patch_dummy_blueprint(bp):
    editor = BGE.get_graph_editor_by_name(bp, EXECUTION_FUNCTION)
    if not editor:
        raise RuntimeError("Dummy execution function was not found")
    nodes = graph_nodes(editor)
    result = next((node for node in nodes if isinstance(node, unreal.K2Node_FunctionResult)), None)
    if not result:
        raise RuntimeError("Dummy execution return node was not found")

    get_location = find_by_title(nodes, "Get Actor Location")
    get_rotation = find_by_title(nodes, "Get Actor Rotation")
    if not get_location:
        get_location = editor.add_call_function_node("/Script/Engine.Actor:K2_GetActorLocation")
        if not get_location:
            get_location = editor.add_call_function_node("/Script/Engine.Actor:GetActorLocation")
        set_pos(get_location, 400, 320)
    if not get_rotation:
        get_rotation = editor.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation")
        if not get_rotation:
            get_rotation = editor.add_call_function_node("/Script/Engine.Actor:GetActorRotation")
        set_pos(get_rotation, 400, 460)
    if not get_location or not get_rotation:
        raise RuntimeError("Could not create actor transform nodes for dummy execution")

    location_result = pin(result, "\u53c2\u8003\u4f4d\u7f6e")
    rotation_result = pin(result, "\u65cb\u8f6c")
    break_links(location_result)
    break_links(rotation_result)
    connect(pin(get_location, "ReturnValue"), location_result, "dummy actor location")
    connect(pin(get_rotation, "ReturnValue"), rotation_result, "dummy actor rotation")

    bel.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, False)
    log("Dummy execution interface now returns the actor root transform")


def main():
    attack = unreal.EditorAssetLibrary.load_asset(ATTACK_BP)
    player = unreal.EditorAssetLibrary.load_asset(PLAYER_BP)
    dummy = unreal.EditorAssetLibrary.load_asset(DUMMY_BP)
    if not attack or not player or not dummy:
        raise RuntimeError("Could not load all combat Blueprints")

    patch_attack_blueprint(attack)
    patch_player_blueprint(player)
    patch_dummy_blueprint(dummy)
    log("Combat feel upgrade completed")


main()
