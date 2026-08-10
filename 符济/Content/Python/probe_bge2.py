# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeBGE2] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
log(f"ed={ed}")

# Call with function path string
for path in (
    "/Script/Engine.Character:PlayAnimMontage",
    "/Script/Engine.Actor:GetVelocity",
    "/Script/Engine.KismetMathLibrary:VSize",
    "/Script/Engine.KismetMathLibrary:Greater_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Greater_FloatFloat",
    "/Script/Engine.Character:GetCharacterMovement",
    "/Script/Engine.CharacterMovementComponent:GetMaxSpeed",
    "/Script/Engine.KismetMathLibrary:LessEqual_DoubleDouble",
    "/Script/Engine.KismetMathLibrary:Not_PreBool",
    "/Script/Engine.KismetSystemLibrary:MakeLiteralBool",
):
    try:
        n = ed.add_call_function_node(path)
        title = bel.get_node_title(n) if n else None
        pins = len(bel.list_all_pins(n) or []) if n else 0
        log(f"call {path} -> {n} title={title} pins={pins}")
        if n:
            bel.set_node_pos(n, unreal.IntPoint(0, 0))
    except Exception as e:
        log(f"call {path}: {e}")

try:
    br = ed.add_branch_node()
    log(f"branch -> {br} title={bel.get_node_title(br)} pins={len(bel.list_all_pins(br) or [])}")
except Exception as e:
    log(f"branch: {e}")

for args in (
    ("SS_WasMoving",),
    ("SS_WasMoving", ""),
    ("SS_WalkStart",),
    ("SS_WalkStart", "/Script/Engine.AnimMontage"),
):
    try:
        n = ed.add_get_member_variable_node(*args)
        log(f"get{args} -> {n} title={bel.get_node_title(n) if n else None}")
    except Exception as e:
        log(f"get{args}: {e}")
    try:
        n = ed.add_set_member_variable_node(*args)
        log(f"set{args} -> {n} title={bel.get_node_title(n) if n else None}")
    except Exception as e:
        log(f"set{args}: {e}")

# Tick
try:
    tick = bel.add_event_override(bp, "ReceiveTick", unreal.IntPoint(-1600, 1600))
    log(f"tick={tick}")
except Exception as e:
    log(f"tick: {e}")

# Connect tick then to GetVelocity
tick = None
for n in unreal.ObjectIterator(unreal.K2Node_Event):
    try:
        if n.get_outer() == ed.get_graph() and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    except Exception:
        continue
vel = None
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    try:
        if n.get_outer() == ed.get_graph() and str(bel.get_node_title(n)) == "GetVelocity":
            vel = n
    except Exception:
        continue
log(f"tick={tick} vel={vel}")
if tick and vel:
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
    ok = unreal.EdGraphSchema_K2.try_create_connection(
        schema, bel.find_then_pin(tick), bel.find_execute_pin(vel)
    )
    log(f"connect tick->vel: {ok}")

try:
    bel.compile_blueprint(bp)
    log("compile OK")
except Exception as e:
    log(f"compile: {e}")

unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
log("done")
