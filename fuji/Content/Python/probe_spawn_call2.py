# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log(f"[Probe2] {m}")


# Wrap FunctionNodeSpawner into unreal namespace tricks
cls = unreal.load_class(None, "/Script/BlueprintGraph.BlueprintFunctionNodeSpawner")
fn = unreal.load_object(None, "/Script/Engine.Character:PlayAnimMontage")

# Try generate python class dynamically
try:
    # UE sometimes exposes via find_object Default__
    cdo = unreal.load_object(None, "/Script/BlueprintGraph.Default__BlueprintFunctionNodeSpawner")
    log(f"CDO object={cdo} dir={[m for m in dir(cdo) if not m.startswith('_')]}")
except Exception as e:
    log(f"CDO: {e}")

# EditorScripting / AssetEditor
for name in dir(unreal):
    if "AnimBlueprint" in name or "AnimationBlueprint" in name or "AnimGraph" in name:
        if "Library" in name or "Editor" in name or "Subsystem" in name:
            log(f"anim api: {name}")

for path in (
    "/Script/AnimGraph.AnimationBlueprintLibrary",
    "/Script/AnimGraph.AnimBlueprintFunctionLibrary",
    "/Script/AnimGraphEditor.AnimationBlueprintEditorLibrary",
    "/Script/AnimGraph.AnimBlueprintEditorLibrary",
    "/Script/BlueprintEditorLibrary.BlueprintEditorLibrary",
    "/Script/Engine.AnimationBlueprintLibrary",
    "/Script/AnimationModifiers.AnimationBlueprintLibrary",
):
    log(f"{path} class={unreal.load_class(None, path)} obj={unreal.load_object(None, path)}")

# Search all CallFunctions titled PlayAnimMontage / Montage
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    try:
        title = str(bel.get_node_title(n))
    except Exception:
        continue
    if "Montage" in title or "Play Anim" in title or "PlayAnim" in title:
        log(f"FOUND {n.get_path_name()} title={title}")

# Try invoke Create via process_event-like call_method on CDO with different names
cdo = unreal.get_default_object(cls)
for meth in dir(cdo):
    if "reate" in meth.lower() or "pawn" in meth.lower() or "invoke" in meth.lower():
        log(f"CDO meth {meth}")

# Try BlueprintVariableNodeSpawner for SS_WasMoving
vcls = unreal.load_class(None, "/Script/BlueprintGraph.BlueprintVariableNodeSpawner")
log(f"VarSpawner={vcls}")
vcdo = unreal.get_default_object(vcls)
log(f"Var CDO meths={[m for m in dir(vcdo) if not m.startswith('_')]}")

# Subobject: EditorUtilitySubsystem execute python?
# Try unreal.EditorAssetLibrary.duplicate on a node? unlikely

# Inspect BlueprintGraphPin fields via export_text / to_tuple
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
graph = bel.find_event_graph(bp)
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    if n.get_outer() != graph:
        continue
    title = str(bel.get_node_title(n))
    if title != "StopJumping":
        continue
    pins = bel.list_all_pins(n) or []
    for p in pins:
        try:
            log(f"pin to_tuple={p.to_tuple() if hasattr(p,'to_tuple') else None}")
            log(f"pin to_dict={p.to_dict() if hasattr(p,'to_dict') else None}")
        except Exception as e:
            log(f"pin export: {e}")
        # pin might have .pin inner
        for attr in ("pin", "Pin", "name", "direction", "default_value", "get_name"):
            if hasattr(p, attr):
                try:
                    v = getattr(p, attr)
                    log(f"  .{attr}={v() if callable(v) else v}")
                except Exception as e:
                    log(f"  .{attr}: {e}")
    # try find_then on node directly (node has pin helpers!)
    try:
        log(f"node.find_then_pin={n.find_then_pin()}")
        log(f"node.find_execute_pin={n.find_execute_pin()}")
        log(f"node.find_result_pin={n.find_result_pin() if hasattr(n,'find_result_pin') else 'n/a'}")
    except Exception as e:
        log(f"node pin helpers: {e}")
    break

# Can we use call_method on K2Node_CallFunction class for CreateFromFunction?
k2 = unreal.K2Node_CallFunction.static_class()
log(f"K2Node_CallFunction class meths via call_method test")
for fname in ("CreateFromFunction", "SetFromFunction", "SetFunctionReference", "ConfigureFromFunction"):
    try:
        log(f"call_method {fname}: {k2.call_method(fname, (fn,))}")
    except Exception as e:
        log(f"call_method {fname}: {e}")

# Try on instance
node = unreal.new_object(unreal.K2Node_CallFunction, graph, unreal.Name("ProbePlay"))
for fname in ("SetFromFunction", "set_from_function", "CreateFromFunction"):
    try:
        log(f"node.call_method {fname}: {node.call_method(fname, (fn,))}")
    except Exception as e:
        log(f"node.call_method {fname}: {e}")

# After SetFromFunction via call_method, dump title/pins
try:
    log(f"after title={bel.get_node_title(node)} pins={len(bel.list_all_pins(node) or [])}")
except Exception as e:
    log(f"after: {e}")

log("done")
