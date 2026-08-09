# -*- coding: utf-8 -*-
import unreal

def log(m):
    unreal.log(f"[DiagIMC] {m}")

imc = unreal.EditorAssetLibrary.load_asset("/Game/Input/IMC_Default")
log(f"imc={imc} class={imc.get_class()}")
# List all editor properties via try common names
for prop in (
    "mappings", "Mappings", "context_description", "mapping_contexts",
    "input_modifiers", "default_key_profile",
):
    try:
        v = imc.get_editor_property(prop)
        log(f"{prop}={v} type={type(v)} len={len(v) if hasattr(v,'__len__') else 'n/a'}")
    except Exception as exc:
        log(f"{prop}: {exc}")

# Asset data
ad = unreal.EditorAssetLibrary.find_asset_data("/Game/Input/IMC_Default")
log(f"asset_class={ad.asset_class_path} pkg={ad.package_name}")

# Try force reload
unreal.EditorAssetLibrary.sync_browser_to_objects(["/Game/Input/IMC_Default"])
imc2 = unreal.EditorAssetLibrary.load_asset("/Game/Input/IMC_Default")
m = imc2.get_editor_property("mappings")
log(f"reload mappings len={len(list(m or []))}")

# Inspect K2Node_EnhancedInputAction properties
n = unreal.K2Node_EnhancedInputAction()
for prop in ("InputAction", "input_action", "Action", "action"):
    try:
        n.set_editor_property(prop, unreal.EditorAssetLibrary.load_asset("/Game/Input/Actions/IA_Jump"))
        log(f"K2 set {prop} OK")
    except Exception as exc:
        log(f"K2 set {prop}: {exc}")
# dir filtered
attrs = [a for a in dir(n) if "action" in a.lower() or "input" in a.lower()]
log(f"node attrs: {attrs}")
