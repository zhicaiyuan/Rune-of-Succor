# -*- coding: utf-8 -*-
import unreal

def log(m):
    unreal.log(f"[Probe] {m}")

# Find how to construct BlueprintEnhancedInputActionBinding
names = [n for n in dir(unreal) if "Enhanced" in n or "BlueprintEnhanced" in n or "InputAction" in n]
log(f"names: {names}")

for n in names:
    cls = getattr(unreal, n)
    try:
        inst = cls()
        log(f"OK ctor {n} -> {type(inst)}")
    except Exception as exc:
        log(f"fail ctor {n}: {exc}")

# Try make_struct style
try:
    s = unreal.BlueprintEnhancedInputActionBinding()
    log(f"direct OK {s}")
except Exception as exc:
    log(f"direct fail: {exc}")

# Array assign test on a temp binding object
binding_cls = unreal.load_class(None, "/Script/EnhancedInput.EnhancedInputActionDelegateBinding")
bp = unreal.EditorAssetLibrary.load_asset("/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter")
binding = unreal.new_object(binding_cls, bp, unreal.Name("ProbeWalkBinding"))
log(f"binding={binding}")

# Inspect properties
try:
    for prop in binding.properties():  # may not exist
        log(f"prop {prop}")
except Exception as exc:
    log(f"properties(): {exc}")

# Try unreal.Array
try:
    arr_type = unreal.Array(unreal.BlueprintEnhancedInputActionBinding)
    log(f"Array type {arr_type}")
except Exception as exc:
    log(f"Array: {exc}")

# ScriptStruct construct via unreal.create_property / make_struct_from_dict
for fn in ("make_struct", "create_struct", "new_struct"):
    if hasattr(unreal, fn):
        log(f"has {fn}")

# Try from EnhancedActionKeyMapping pattern — get type of struct field
imc = unreal.EditorAssetLibrary.load_asset("/Game/Input/IMC_Default")
mappings = imc.get_editor_property("mappings")
log(f"mapping elem type {type(mappings[0]) if mappings else None}")
