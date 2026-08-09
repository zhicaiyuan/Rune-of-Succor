# -*- coding: utf-8 -*-
"""
Attach EnhancedInputActionDelegateBinding with Crouch/UnCrouch function names
using Array mutation / struct construction.
"""

from __future__ import annotations

import unreal

CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
IA_WALK = "/Game/Input/Actions/IA_Walk"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[BindDel] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def make_binding_entry(ia, trigger, func_name):
    """Try multiple ways to construct FBlueprintEnhancedInputActionBinding."""
    # Method A: if exposed
    if hasattr(unreal, "BlueprintEnhancedInputActionBinding"):
        e = unreal.BlueprintEnhancedInputActionBinding()
        e.set_editor_property("input_action", ia)
        e.set_editor_property("trigger_event", trigger)
        e.set_editor_property("function_name_to_bind", func_name)
        return e

    # Method B: Array element factory via temporary binding object
    return None


def attach(bp_path: str):
    bp = load(bp_path)
    ia = load(IA_WALK)
    binding_cls = unreal.load_class(None, "/Script/EnhancedInput.EnhancedInputActionDelegateBinding")
    binding = unreal.new_object(binding_cls, bp, unreal.Name("WalkInputBinding"))
    log(f"binding={binding}")

    # Inspect array property
    for prop in ("input_action_delegate_bindings", "InputActionDelegateBindings"):
        try:
            arr = binding.get_editor_property(prop)
            log(f"{prop} type={type(arr)} len={len(arr) if arr is not None else None}")
            # Try Array.add / append
            for meth in dir(arr):
                if not meth.startswith("_"):
                    pass
            log(f"array methods: {[m for m in dir(arr) if not m.startswith('_')]}")
        except Exception as exc:
            log(f"{prop}: {exc}")

    # Construct entries using EnhancedActionKeyMapping-like pattern via copy from Jump binding
    # Find existing EnhancedInputActionDelegateBinding in BP package
    try:
        # Use AssetRegistry to find
        pass
    except Exception:
        pass

    # Try creating struct via unreal.Array typed add
    arr = binding.get_editor_property("input_action_delegate_bindings")
    log(f"arr={arr}")

    # Method: use binding.call_method
    for trigger_name, func in (("STARTED", "Crouch"), ("COMPLETED", "UnCrouch")):
        trigger = getattr(unreal.TriggerEvent, trigger_name)
        # Try Array's add_default / resize
        try:
            if hasattr(arr, "append"):
                # need struct
                pass
            # Some Arrays support:
            # arr.add(value)
            if hasattr(arr, "add"):
                log(f"arr.add exists")
        except Exception as exc:
            log(f"arr mutate: {exc}")

    # Method: set entire array from list of dicts — unlikely
    # Method: use export_text / import_text on the binding
    try:
        # FBlueprintEnhancedInputActionBinding export format
        text = (
            f'((InputAction="/Script/EnhancedInput.InputAction\'{IA_WALK}.{IA_WALK.split("/")[-1]}\'",'
            f'TriggerEvent=Started,FunctionNameToBind="Crouch"),'
            f'(InputAction="/Script/EnhancedInput.InputAction\'{IA_WALK}.{IA_WALK.split("/")[-1]}\'",'
            f'TriggerEvent=Completed,FunctionNameToBind="UnCrouch"))'
        )
        log(f"import text={text}")
        # Property import
        for prop in ("input_action_delegate_bindings", "InputActionDelegateBindings"):
            try:
                # Object.import_text?
                if hasattr(binding, "import_property"):
                    binding.import_property(prop, text)
                # Or
                unreal.SystemLibrary.execute_console_command(
                    None,
                    f'OBJ SET OBJECT="{binding.get_path_name()}" PROPERTY={prop} VALUE={text}',
                )
                log(f"OBJ SET {prop}")
            except Exception as exc:
                log(f"import {prop}: {exc}")
    except Exception as exc:
        log(f"text import: {exc}")

    # Attach binding to Blueprint Generated Class DynamicBindingObjects
    gen = bp.generated_class()
    attached = False
    for obj, label in ((bp, "bp"), (gen, "gen")):
        for prop in (
            "dynamic_binding_objects",
            "DynamicBindingObjects",
            "binding_objects",
            "BindingObjects",
        ):
            try:
                cur = list(obj.get_editor_property(prop) or [])
                cur = [o for o in cur if o and o.get_name() != "WalkInputBinding"]
                cur.append(binding)
                obj.set_editor_property(prop, cur)
                log(f"attached to {label}.{prop} count={len(cur)}")
                attached = True
            except Exception as exc:
                log(f"{label}.{prop}: {exc}")

    # Also try ComponentTemplates path used by some UE versions
    # Ensure crouch
    cdo = unreal.get_default_object(gen)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("max_walk_speed", 600.0)
    move.set_editor_property("max_walk_speed_crouched", 200.0)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("orient_rotation_to_movement", False)
    cdo.set_editor_property("use_controller_rotation_yaw", False)
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
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        mesh.set_editor_property("anim_class", load(ABP).generated_class())

    unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        log(f"compiled attached={attached}")
    except Exception as exc:
        log(f"compile: {exc}")

    # Verify binding array after import
    try:
        arr = binding.get_editor_property("input_action_delegate_bindings")
        log(f"final bindings len={len(list(arr or []))}")
        for b in list(arr or []):
            log(f"  entry={b}")
    except Exception as exc:
        log(f"verify arr: {exc}")


def run():
    log("start")
    # Probe struct construction
    log(f"has BlueprintEnhancedInputActionBinding={hasattr(unreal, 'BlueprintEnhancedInputActionBinding')}")
    names = [n for n in dir(unreal) if "BlueprintEnhanced" in n or "EnhancedInputAction" in n]
    log(f"related: {names}")
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            attach(bp)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
