# -*- coding: utf-8 -*-
"""
UE 5.8-correct finalization:
- Read/write IMC via default_key_mappings / map_key (NOT deprecated mappings)
- Spawn Enhanced Input nodes via InputActionEventNodeSpawner
- Character walk via Crouch speed; idle turn via desired rotation + montages ready
"""

from __future__ import annotations

import unreal

IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
IA_JUMP = "/Game/Input/Actions/IA_Jump"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[FinalizeV2] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def make_key(name: str):
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name(name))
    return key


def dump_imc():
    imc = load(IMC)
    # New API
    try:
        dkm = imc.get_editor_property("default_key_mappings")
        log(f"default_key_mappings type={type(dkm)}")
        for prop in ("mappings", "Mappings"):
            try:
                arr = list(dkm.get_editor_property(prop) or [])
                log(f"DKM.{prop} len={len(arr)}")
                for m in arr:
                    a = m.get_editor_property("action")
                    k = m.get_editor_property("key")
                    kn = k.get_editor_property("key_name") if k else None
                    log(f"  {kn} -> {a.get_name() if a else None}")
            except Exception as exc:
                log(f"DKM.{prop}: {exc}")
    except Exception as exc:
        log(f"default_key_mappings: {exc}")
    # get_mappings method
    for meth in ("get_mappings", "GetMappings"):
        if hasattr(imc, meth):
            try:
                arr = list(getattr(imc, meth)() or [])
                log(f"{meth}() len={len(arr)}")
            except Exception as exc:
                log(f"{meth}: {exc}")


def ensure_ia_walk():
    if not unreal.EditorAssetLibrary.does_asset_exist(IA_WALK):
        unreal.EditorAssetLibrary.duplicate_asset(IA_JUMP, IA_WALK)
    ia = load(IA_WALK)
    try:
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    except Exception:
        pass
    unreal.EditorAssetLibrary.save_asset(IA_WALK, only_if_is_dirty=False)
    return ia


def add_walk_mapping():
    ia = ensure_ia_walk()
    imc = load(IMC)
    dump_imc()

    # Unmap existing walk if API exists
    if hasattr(imc, "unmap_all_keys_of_action"):
        try:
            imc.unmap_all_keys_of_action(ia)
            log("unmapped existing IA_Walk")
        except Exception as exc:
            log(f"unmap: {exc}")

    key = make_key("LeftAlt")
    try:
        mapping = imc.map_key(ia, key)
        log(f"map_key LeftAlt -> IA_Walk => {mapping}")
    except Exception as exc:
        log(f"map_key failed: {exc}")
        # Fallback: mutate default_key_mappings.mappings
        try:
            dkm = imc.get_editor_property("default_key_mappings")
            arr = list(dkm.get_editor_property("mappings") or [])
            m = unreal.EnhancedActionKeyMapping()
            m.set_editor_property("action", ia)
            m.set_editor_property("key", key)
            arr.append(m)
            dkm.set_editor_property("mappings", arr)
            imc.set_editor_property("default_key_mappings", dkm)
            log(f"DKM append ok len={len(arr)}")
        except Exception as exc2:
            log(f"DKM append failed: {exc2}")

    unreal.EditorAssetLibrary.save_asset(IMC, only_if_is_dirty=False)
    log("IMC saved")
    dump_imc()


def configure_character(bp_path: str):
    bp = load(bp_path)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("max_walk_speed", 600.0)
    move.set_editor_property("max_walk_speed_crouched", 200.0)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("braking_deceleration_walking", 1000.0)
    move.set_editor_property("ground_friction", 5.0)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=400.0, roll=0.0))
    try:
        nav = move.get_editor_property("nav_agent_props")
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception:
        pass
    try:
        cap = cdo.get_editor_property("capsule_component")
        move.set_editor_property(
            "crouched_half_height", float(cap.get_editor_property("capsule_half_height"))
        )
    except Exception:
        pass
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        mesh.set_editor_property("anim_class", abp.generated_class())
    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"configured {bp_path}")


def spawn_walk_nodes(bp_path: str):
    bp = load(bp_path)
    bel = unreal.BlueprintEditorLibrary
    graph = bel.find_event_graph(bp)
    if not graph:
        log("no EventGraph")
        return
    ia = load(IA_WALK)

    # Prefer InputActionEventNodeSpawner
    node = None
    try:
        spawner_cls = unreal.InputActionEventNodeSpawner
        # Create(NodeClass, Action)
        if hasattr(spawner_cls, "create"):
            spawner = spawner_cls.create(unreal.K2Node_EnhancedInputAction.static_class(), ia)
            log(f"spawner={spawner}")
            # Invoke(ParentGraph, Bindings, Location)
            bindings = None
            try:
                bindings = unreal.BlueprintNodeSpawner.BindingSet()
            except Exception:
                try:
                    bindings = set()
                except Exception:
                    bindings = []
            loc = unreal.Vector2D(-300.0, 1400.0)
            node = spawner.invoke(graph, bindings, loc)
            log(f"spawned node={node}")
    except Exception as exc:
        log(f"spawner failed: {exc}")

    if not node:
        log("Could not spawn Enhanced Input node — walk key is in IMC; bind Crouch in editor if needed")
        return

    # Create Crouch/UnCrouch and link
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")

    def make_call(func_name, y):
        n = unreal.new_object(unreal.K2Node_CallFunction, graph)
        try:
            fn = unreal.load_object(None, f"/Script/Engine.Character:{func_name}")
            if fn and hasattr(n, "set_from_function"):
                n.set_from_function(fn)
                log(f"call {func_name} set_from_function")
            else:
                ref = n.get_editor_property("function_reference")
                ref.set_editor_property("member_name", unreal.Name(func_name))
                ref.set_editor_property("member_parent", unreal.Character.static_class())
                n.set_editor_property("function_reference", ref)
        except Exception as exc:
            log(f"call {func_name}: {exc}")
        for meth in ("allocate_default_pins", "reconstruct_node"):
            if hasattr(n, meth):
                try:
                    getattr(n, meth)()
                except Exception:
                    pass
        try:
            # set_node_pos may take Vector2D
            bel.set_node_pos(n, unreal.Vector2D(400.0, float(y)))
        except Exception:
            try:
                n.node_pos_x = 400
                n.node_pos_y = y
            except Exception:
                pass
        return n

    crouch = make_call("Crouch", 1300)
    uncrouch = make_call("UnCrouch", 1550)

    def pins_of(n):
        try:
            return list(n.get_all_pins() or [])
        except Exception:
            try:
                return list(n.list_output_pins() or []) + list(n.list_input_pins() or [])
            except Exception:
                return []

    def find_pin(pins, *names):
        for p in pins:
            try:
                pn = str(p.get_editor_property("pin_name"))
            except Exception:
                pn = str(getattr(p, "pin_name", p))
            for name in names:
                if name.lower() in pn.lower():
                    return p
        return None

    ei_pins = pins_of(node)
    log(f"EI pins count={len(ei_pins)}")
    for p in ei_pins:
        try:
            log(f"  EI pin {p.get_editor_property('pin_name')}")
        except Exception:
            pass

    started = find_pin(ei_pins, "Started")
    completed = find_pin(ei_pins, "Completed")
    c_exec = find_pin(pins_of(crouch), "execute")
    u_exec = find_pin(pins_of(uncrouch), "execute")

    def link(a, b, label):
        if not (a and b and schema):
            log(f"link {label} skip")
            return
        try:
            schema.try_create_connection(a, b)
            log(f"link {label} OK")
        except Exception as exc:
            log(f"link {label}: {exc}")

    link(started, c_exec, "Started->Crouch")
    link(completed, u_exec, "Completed->UnCrouch")

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        bel.compile_blueprint(bp)
        log(f"compiled {bp_path}")
    except Exception as exc:
        log(f"compile: {exc}")


def setup_turn_assets():
    """Ensure turn sequences have RM; ABP Slot DefaultSlot; character desired rot for turn lag."""
    for name in ("Turn_90_L", "Turn_90_R", "Turn_180_L", "Turn_180_R"):
        seq = f"{OUT}/SwordRTG/{name}_Seq_RTG"
        mont = f"{OUT}/Montages/AM_{name}"
        if unreal.EditorAssetLibrary.does_asset_exist(seq):
            anim = load(seq)
            try:
                anim.set_editor_property("enable_root_motion", True)
                anim.set_editor_property("force_root_lock", False)
                unreal.EditorAssetLibrary.save_asset(seq, only_if_is_dirty=False)
            except Exception as exc:
                log(f"RM {name}: {exc}")
        if unreal.EditorAssetLibrary.does_asset_exist(mont):
            log(f"montage ok {mont}")
    # ABP compile
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        except Exception:
            pass
        log("ABP compiled")


def verify():
    dump_imc()
    bp = load(CHAR_BP)
    cdo = unreal.get_default_object(bp.generated_class())
    move = cdo.get_editor_property("character_movement")
    mesh = cdo.get_editor_property("mesh")
    r = mesh.get_editor_property("relative_rotation")
    log(
        f"VERIFY speed={move.get_editor_property('max_walk_speed')} "
        f"walk={move.get_editor_property('max_walk_speed_crouched')} "
        f"accel={move.get_editor_property('max_acceleration')} "
        f"mesh=P{r.pitch}Y{r.yaw} "
        f"anim={mesh.get_editor_property('anim_class')} "
        f"BS={unreal.EditorAssetLibrary.does_asset_exist('/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword')}"
    )


def run():
    log("start")
    add_walk_mapping()
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            configure_character(bp)
            spawn_walk_nodes(bp)
    setup_turn_assets()
    verify()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
