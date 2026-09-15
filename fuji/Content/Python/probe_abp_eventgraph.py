# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeABP] {m}")


abp = unreal.EditorAssetLibrary.load_asset(ABP)

# all graphs under ABP
for g in unreal.ObjectIterator(unreal.EdGraph):
    if "ABP_StrafeLocomotion" not in g.get_path_name():
        continue
    if "AnimGraph" in g.get_name() or "Locomotion" in g.get_name() or "State" in g.get_name():
        continue
    log(f"GRAPH {g.get_name()} path={g.get_path_name()}")

eg = None
try:
    eg = bel.find_event_graph(abp)
except Exception as e:
    log(f"find_event_graph: {e}")
log(f"ABP EventGraph={eg}")

# Also EventGraph by name
for g in unreal.ObjectIterator(unreal.EdGraph):
    if g.get_name() == "EventGraph" and "ABP_StrafeLocomotion" in g.get_path_name():
        eg = g
        log(f"found EG {g.get_path_name()}")

if eg:
    for cls_name in (
        "K2Node_CallFunction",
        "K2Node_VariableGet",
        "K2Node_VariableSet",
        "K2Node_IfThenElse",
        "K2Node_Event",
        "K2Node_AnimGetter",
        "K2Node_TransitionRuleGetter",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            log(f"no class {cls_name}")
            continue
        ncount = 0
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_typed_outer(unreal.EdGraph) != eg and n.get_outer() != eg:
                    continue
            except Exception:
                continue
            ncount += 1
            try:
                title = str(bel.get_node_title(n))
            except Exception:
                title = "?"
            if ncount <= 40:
                log(f"EG {cls_name} {n.get_name()} title={title}")
        log(f"EG {cls_name} total={ncount}")

# Try duplicating a CallFunction node via rename/export?
# Check if BlueprintGraphPin has connect via BEL.connect?
for name in ("connect_pins", "try_connect_pins", "make_link", "create_connection"):
    log(f"BEL.{name}={hasattr(bel, name)}")

# Inspect existing Idle sequence player - can we swap to use Start as additive?
# Better idea: use AnimNode_Slot with montage from character - need PlayAnimMontage

# Try spawning FunctionNodeSpawner via BlueprintNodeSpawner.invoke
fn = unreal.load_object(None, "/Script/Engine.Character:PlayAnimMontage")
spawner_cls = unreal.load_class(None, "/Script/BlueprintGraph.BlueprintFunctionNodeSpawner")
# UObject reflection: find UFunction Create on the class default
try:
    ucls = spawner_cls
    # iterate class functions?
    log(f"spawner class={ucls}")
except Exception as e:
    log(f"{e}")

# Use EditorLevelLibrary / Subsystem to run BP utility?
for name in dir(unreal):
    if "NodeSpawner" in name or "GraphEditor" in name or "KismetEditor" in name:
        log(f"unreal.{name}")

# Try load KismetEditorUtilities
for path in (
    "/Script/UnrealEd.KismetEditorUtilities",
    "/Script/BlueprintGraph.KismetEditorUtilities",
    "/Script/UnrealEd.Default__KismetEditorUtilities",
):
    log(f"{path} -> {unreal.load_class(None, path)} / {unreal.load_object(None, path)}")

# Can we set SequencePlayer.bLoopAnimation = false and change Idle to Start when speed>0?
# That would need dynamic sequence - SequencePlayer doesn't switch easily without SM.

# Check AnimGraphNode_SequencePlayer for Start/Stop already present
for key in ("Start", "Stop", "Idle"):
    count = 0
    for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
        if "ABP_StrafeLocomotion" not in sp.get_path_name():
            continue
        try:
            seq = sp.get_editor_property("node").get_editor_property("sequence")
            if seq and key.lower() in seq.get_name().lower():
                count += 1
                if count <= 3:
                    log(f"SP {key}: {seq.get_name()} @ {sp.get_path_name()}")
        except Exception:
            pass
    log(f"SP containing {key}: {count}")

# Character vars present?
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
try:
    names = list(bel.list_member_variable_names(bp) or [])
    log(f"char vars SS_*={[n for n in names if 'SS_' in str(n)]}")
    log(f"char vars sample={names[:30]}")
except Exception as e:
    log(f"vars: {e}")

log("done")
