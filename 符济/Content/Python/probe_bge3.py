# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeBGE3] {m}")


for m in (
    "find_data_input_pin",
    "find_input_pin",
    "find_input_pin_by_index",
    "find_output_pin",
    "find_output_pin_by_index",
    "list_input_pins",
    "list_output_pins",
    "get_pin_name",
    "set_pin_default_value",
    "find_self_pin",
):
    fn = getattr(bel, m, None)
    log(f"BEL.{m} doc={getattr(fn,'__doc__',None)}")

bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
g = ed.get_graph()

# Get CharacterMovement member
for name in ("CharacterMovement", "Mesh", "MaxWalkSpeed"):
    try:
        n = ed.add_get_member_variable_node(name)
        log(f"get {name} -> {bel.get_node_title(n) if n else None}")
    except Exception as e:
        log(f"get {name}: {e}")

# Get MaxWalkSpeed from CMC class
try:
    n = ed.add_get_member_variable_node("MaxWalkSpeed", "/Script/Engine.CharacterMovementComponent")
    log(f"get MaxWalkSpeed CMC -> {n} title={bel.get_node_title(n) if n else None}")
except Exception as e:
    log(f"MaxWalkSpeed CMC: {e}")

# Inspect pins on PlayAnimMontage / VSize / comparison
for title_key in ("PlayAnimMontage", "Vector Length", "float > float", "MakeLiteralBool", "获得SS_WasMoving", "设置SS_WasMoving"):
    for n in unreal.ObjectIterator(unreal.K2Node):
        try:
            if n.get_outer() != g:
                continue
            title = str(bel.get_node_title(n))
            if title_key not in title and title != title_key:
                continue
            log(f"NODE {title}")
            for i, p in enumerate(bel.list_all_pins(n) or []):
                # try get name via various
                pname = "?"
                for meth in ("get_pin_name",):
                    if hasattr(bel, meth):
                        try:
                            pname = str(getattr(bel, meth)(p))
                        except Exception:
                            pass
                # BlueprintGraphPin fields
                for attr in ("name", "pin_name", "direction", "default_value", "get_name"):
                    if hasattr(p, attr):
                        try:
                            v = getattr(p, attr)
                            log(f"  pin[{i}].{attr}={v() if callable(v) else v}")
                        except Exception as e:
                            log(f"  pin[{i}].{attr}: {e}")
                # export
                try:
                    log(f"  pin[{i}] str={p} dict={getattr(p,'to_dict',lambda:{})()}")
                except Exception:
                    pass
            # indexed
            try:
                for i in range(8):
                    ip = bel.find_input_pin_by_index(n, i)
                    op = bel.find_output_pin_by_index(n, i)
                    if ip:
                        log(f"  in[{i}]={ip}")
                    if op:
                        log(f"  out[{i}]={op}")
            except Exception as e:
                log(f"  index: {e}")
            break
        except Exception:
            continue

# Connect via schema instance method
schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
log(f"schema={schema} has try={hasattr(schema,'try_create_connection')}")
tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(-1600, 1600))
vel = ed.add_call_function_node("/Script/Engine.Actor:GetVelocity")
try:
    ok = schema.try_create_connection(bel.find_then_pin(tick), bel.find_execute_pin(vel))
    log(f"schema.try_create_connection -> {ok}")
except Exception as e:
    log(f"schema connect: {e}")

# pin default value
cmpn = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Greater_FloatFloat")
try:
    # find B pin - usually input index 1 after self? For pure math, A=0 B=1
    bpin = bel.find_input_pin_by_index(cmpn, 1)
    log(f"B pin={bpin}")
    if hasattr(bel, "set_pin_default_value"):
        bel.set_pin_default_value(bpin, "15.0")
        log("set_pin_default_value OK")
    elif hasattr(bpin, "set_editor_property"):
        bpin.set_editor_property("default_value", "15.0")
        log("pin default via set_editor_property")
except Exception as e:
    log(f"default: {e}")

log("done")
