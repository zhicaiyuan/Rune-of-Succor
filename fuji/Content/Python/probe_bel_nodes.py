# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeBEL] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
graph = bel.find_event_graph(bp)

meths = sorted([m for m in dir(bel) if not m.startswith("_")])
log(f"BEL count={len(meths)}")
for key in ("add_", "create_", "find_", "set_", "connect", "call", "variable", "function", "pin", "node"):
    hits = [m for m in meths if key in m.lower()]
    if hits:
        log(f"[{key}] {hits}")

# Inspect K2Node_CallFunction
node = unreal.new_object(unreal.K2Node_CallFunction, graph, unreal.Name("Probe_Call"))
log(f"CallFunction methods: {[m for m in dir(node) if 'function' in m.lower() or 'set_from' in m.lower() or 'pin' in m.lower()]}")
log(f"has set_from_function={hasattr(node, 'set_from_function')}")
fn = unreal.load_object(None, "/Script/Engine.Actor:GetVelocity")
log(f"fn={fn}")
if hasattr(node, "set_from_function"):
    try:
        node.set_from_function(fn)
        log("set_from_function OK")
    except Exception as exc:
        log(f"set_from_function: {exc}")

# Try BEL helpers to create nodes
for name in meths:
    if any(k in name.lower() for k in ("call_function", "variable_get", "variable_set", "function_node", "add_node")):
        log(f"interesting BEL.{name}")

# Pin helpers signatures via help/doc
for name in (
    "find_data_input_pin",
    "find_then_pin",
    "find_execute_pin",
    "find_result_pin",
    "find_condition_pin",
    "list_all_pins",
    "get_pin_name",
    "set_pin_default_value",
    "connect_pins",
    "try_connect_pins",
):
    if hasattr(bel, name):
        try:
            doc = getattr(bel, name).__doc__
            log(f"BEL.{name} doc={doc}")
        except Exception as exc:
            log(f"BEL.{name}: {exc}")

# Existing call nodes in graph - how were they set up?
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    try:
        if n.get_outer() != graph:
            continue
        title = str(bel.get_node_title(n))
        log(f"EXISTING CALL {n.get_name()} title={title}")
        # try property names
        for prop in ("FunctionReference", "function_reference", "Function", "function"):
            try:
                v = n.get_editor_property(prop)
                log(f"  prop {prop}={v}")
            except Exception as exc:
                log(f"  prop {prop}: {exc}")
        # dump pins via BEL
        try:
            pins = bel.list_all_pins(n) or []
            for p in pins:
                try:
                    pname = bel.get_pin_name(p) if hasattr(bel, "get_pin_name") else "?"
                except Exception:
                    pname = "?"
                log(f"  pin={pname} raw={p}")
        except Exception as exc:
            log(f"  pins: {exc}")
        # only first few
        break
    except Exception:
        continue

# Try Schema create
schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
log(f"schema methods sample={[m for m in dir(schema) if 'spawn' in m.lower() or 'create' in m.lower() or 'place' in m.lower()][:40]}")

# Variable get via BEL?
for name in meths:
    if "variable" in name.lower():
        log(f"var API BEL.{name}")

# Try add_member and get via create_variable_get if exists
if hasattr(bel, "add_variable_get_node"):
    log("has add_variable_get_node")
if hasattr(bel, "create_variable_get"):
    log("has create_variable_get")

# Inspect VariableGet props
vg = unreal.new_object(unreal.K2Node_VariableGet, graph, unreal.Name("Probe_VG"))
log(f"VG dir funcs={[m for m in dir(vg) if 'var' in m.lower() or 'set_' in m.lower() or 'member' in m.lower()][:50]}")
for prop in ("VariableReference", "variable_reference", "variable_name", "VariableName"):
    try:
        log(f"VG.{prop}={vg.get_editor_property(prop)}")
    except Exception as exc:
        log(f"VG.{prop}: {exc}")

# Try set_variable_reference / create_self_reference methods from BEL
for name in ("set_variable_on_node", "set_node_variable", "configure_variable_node", "set_member_reference"):
    log(f"has {name}={hasattr(bel, name)}")

log("done")
