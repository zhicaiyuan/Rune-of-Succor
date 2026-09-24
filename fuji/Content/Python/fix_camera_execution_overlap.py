"""Keep the camera stable near enemies and leave space between execution actors."""

import unreal


PLAYER = "/Game/\u84dd\u56fe/\u73a9\u5bb6/BP_ThirdPersonCharacter"
ENEMIES = (
    "/Game/\u84dd\u56fe/BP_\u6d4b\u8bd5\u5047\u4eba",
    "/Game/Variant_Combat/Blueprints/AI/BP_CombatEnemy",
)
BEL = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(message):
    unreal.log("[CameraExecutionFix] " + str(message))


def pin(node, name):
    for item in BEL.list_all_pins(node) or []:
        if str(item.get_pin_name()) == name:
            return item
    raise RuntimeError("Missing pin: %s.%s" % (node.get_name(), name))


def connect(source, target, label):
    if not source.try_create_connection(target):
        raise RuntimeError("Connection failed: " + label)


def patch_enemy_camera_collision(path):
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not bp:
        log("Enemy asset missing: " + path)
        return
    changed = 0
    seen = set()
    cdo = unreal.get_default_object(bp.generated_class())
    objects = list(cdo.get_components_by_class(unreal.SkeletalMeshComponent) or [])
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
        data = lib.get_data(handle)
        for method, args in (("get_object_for_blueprint", (data, bp)),
                             ("get_object", (data,))):
            try:
                obj = getattr(lib, method)(*args)
                if obj:
                    if isinstance(obj, unreal.SkeletalMeshComponent):
                        objects.append(obj)
                    break
            except Exception:
                continue
    for mesh in objects:
        if mesh.get_path_name() in seen:
            continue
        seen.add(mesh.get_path_name())
        current = mesh.get_collision_response_to_channel(unreal.CollisionChannel.ECC_CAMERA)
        if current != unreal.CollisionResponseType.ECR_IGNORE:
            mesh.set_collision_response_to_channel(
                unreal.CollisionChannel.ECC_CAMERA,
                unreal.CollisionResponseType.ECR_IGNORE,
            )
            changed += 1
            log("Camera ignores %s.%s" % (path, mesh.get_name()))
    if changed:
        BEL.compile_blueprint(bp)
        if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
            raise RuntimeError("Failed saving enemy Blueprint: " + path)
    log("Enemy camera collision updated: %s (%s meshes)" % (path, changed))


def patch_player_camera_and_execution():
    bp = unreal.EditorAssetLibrary.load_asset(PLAYER)
    if not bp:
        raise RuntimeError("Player Blueprint missing")
    editor = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = editor.get_graph()
    nodes = {node.get_name(): node for node in unreal.ObjectIterator(unreal.K2Node)
             if node.get_outer() == graph}
    changed = False

    look = nodes.get("K2Node_CallFunction_70")
    interp = nodes.get("K2Node_CallFunction_73")
    if look and interp and str(BEL.get_node_title(look)) == "FindLookAtRotation":
        start_sources = list(pin(look, "Start").list_connected_pins() or [])
        target_sources = list(pin(look, "Target").list_connected_pins() or [])
        current_sources = list(pin(interp, "Current").list_connected_pins() or [])
        if len(start_sources) != 1 or len(target_sources) != 1 or len(current_sources) != 1:
            raise RuntimeError("Unexpected lock-on camera graph")
        stable = editor.add_call_function_node(
            "/Script/RuneofSuccor.CombatFeelLibrary:FindStableLockOnRotation")
        if not stable:
            raise RuntimeError("Could not add stable lock-on camera node")
        try:
            BEL.set_node_pos(stable, unreal.IntPoint(-150, 350))
        except Exception:
            pass
        pin(interp, "Target").break_pin_links()
        connect(start_sources[0], pin(stable, "Start"), "camera start")
        connect(target_sources[0], pin(stable, "Target"), "camera target")
        connect(current_sources[0], pin(stable, "CurrentRotation"), "previous view")
        connect(pin(stable, "ReturnValue"), pin(interp, "Target"), "stable view")
        editor.remove_nodes([look])
        changed = True
        log("Lock-on view holds its yaw when player and enemy overlap")

    warp = nodes.get("K2Node_CallFunction_51")
    if not warp or str(BEL.get_node_title(warp)) != "AddOrUpdateWarpTarget":
        raise RuntimeError("Execution warp node not found")
    offset = pin(warp, "WarpTarget_LocationOffset")
    if offset.list_connected_pins():
        raise RuntimeError("Execution warp offset is already driven by another node")
    desired = "-70.000000,0.000000,0.000000"
    if str(offset.get_pin_value()).replace(" ", "") != desired:
        offset.set_pin_value(desired)
        changed = True
    if "-70" not in str(offset.get_pin_value()):
        raise RuntimeError("Execution root spacing was not applied")
    log("Execution warp follows the target with 70 cm root spacing")

    if changed:
        BEL.compile_blueprint(bp)
        if not unreal.EditorAssetLibrary.save_loaded_asset(bp, False):
            raise RuntimeError("Failed saving player Blueprint")
    log("Player camera and execution Blueprint complete")


for enemy in ENEMIES:
    patch_enemy_camera_collision(enemy)
patch_player_camera_and_execution()
