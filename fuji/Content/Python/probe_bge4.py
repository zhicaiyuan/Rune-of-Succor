# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeBGE4] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
log(f"ed methods connect-related={[m for m in dir(ed) if 'pin' in m.lower() or 'link' in m.lower() or 'connect' in m.lower() or 'wire' in m.lower()]}")

# BlueprintGraphPin methods via a real pin
tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(-1600, 1600))
then = bel.find_then_pin(tick)
log(f"then={then} dir={[m for m in dir(then) if not m.startswith('_')]}")

vel = ed.add_call_function_node("/Script/Engine.Actor:GetVelocity")
exe = bel.find_execute_pin(vel)

# Try pin methods
for meth in ("make_link_to", "connect", "create_connection", "link_to", "try_connect"):
    if hasattr(then, meth):
        try:
            r = getattr(then, meth)(exe)
            log(f"then.{meth}(exe) -> {r}")
        except Exception as e:
            log(f"then.{meth}: {e}")

# Schema class methods
schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
log(f"schema dir={[m for m in dir(schema) if 'connect' in m.lower() or 'link' in m.lower() or 'create' in m.lower()]}")
for meth in ("try_create_connection", "create_connection", "create_new_connection", "try_create_connection_python"):
    if hasattr(schema, meth):
        try:
            log(f"schema.{meth} -> {getattr(schema, meth)(then, exe)}")
        except Exception as e:
            log(f"schema.{meth}: {e}")
    # class level
    cls = schema.get_class()
    try:
        log(f"cls.call_method {meth}: {cls.call_method(meth, (then, exe))}")
    except Exception as e:
        log(f"cls.call_method {meth}: {e}")
    try:
        log(f"schema.call_method {meth}: {schema.call_method(meth, (then, exe))}")
    except Exception as e:
        log(f"schema.call_method {meth}: {e}")

# BEL find_input_pin by name
play = ed.add_call_function_node("/Script/Engine.Character:PlayAnimMontage")
for pname in ("AnimMontage", "MontageToPlay", "Montage", "InAnimMontage", "execute", "then", "self", "ReturnValue", "PlayRate", "TimeToStart"):
    try:
        p = bel.find_input_pin(play, pname)
        log(f"Play in '{pname}' -> {p}")
    except Exception as e:
        log(f"Play in '{pname}': {e}")
    try:
        p = bel.find_output_pin(play, pname)
        log(f"Play out '{pname}' -> {p}")
    except Exception as e:
        log(f"Play out '{pname}': {e}")

# list pins and try export_text on pin
for i, p in enumerate(bel.list_all_pins(play) or []):
    try:
        # FBlueprintGraphPin might wrap
        log(f"pin[{i}] type={type(p)} export={p.export_text() if hasattr(p,'export_text') else 'n/a'}")
    except Exception as e:
        log(f"pin[{i}]: {e}")
    # try get_editor_property on pin struct - unlikely
    for prop in ("PinName", "pin_name", "PinType", "DefaultValue", "default_value", "Direction"):
        try:
            log(f"  {prop}={p.get_editor_property(prop)}")
        except Exception:
            pass

# set default via find_input_pin + something on editor
cmpn = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
b = bel.find_input_pin(cmpn, "B")
log(f"cmp B={b}")
# BlueprintGraphEditor set pin default?
for m in dir(ed):
    if "default" in m.lower() or "pin" in m.lower():
        log(f"ed.{m}")

# Try create_node_from_name for literal
try:
    lit = ed.create_node_from_name("Make Literal Bool|Utilities|String|Conversions", unreal.Vector2D(0, 0), [])
    log(f"create_node_from_name lit -> {lit}")
except Exception as e:
    log(f"create_node_from_name: {e}")

log("done")
