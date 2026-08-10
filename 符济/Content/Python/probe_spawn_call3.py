# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[Probe3] {m}")


fn = unreal.load_object(None, "/Script/Engine.AnimInstance:Montage_Play")
log(f"Montage_Play fn={fn}")

# Default__BlueprintFunctionNodeSpawner Create via every trick
cdo = unreal.load_object(None, "/Script/BlueprintGraph.Default__BlueprintFunctionNodeSpawner")
for args in (
    (fn,),
    (fn, None),
    (unreal.K2Node_CallFunction.static_class(), fn),
):
    for meth in ("Create", "create", "CreateWithFunction", "Make"):
        try:
            r = cdo.call_method(meth, args)
            log(f"cdo.{meth}{args} -> {r}")
        except Exception as e:
            pass

# new_object spawner then set Function / invoke
spawner_cls = unreal.load_class(None, "/Script/BlueprintGraph.BlueprintFunctionNodeSpawner")
sp = unreal.new_object(spawner_cls)
log(f"new spawner={sp}")
for prop in ("Function", "function", "NodeClass", "node_class", "AssociatedAction"):
    try:
        sp.set_editor_property(prop, fn)
        log(f"set {prop} OK")
    except Exception as e:
        log(f"set {prop}: {e}")

# BlueprintGraphEditor
bge = unreal.BlueprintGraphEditor
log(f"BGE methods={[m for m in dir(bge) if not m.startswith('_')]}")

# Try creating AnimationStateGraph under WalkStart
abp = unreal.EditorAssetLibrary.load_asset(ABP)
walk_start = None
for n in unreal.ObjectIterator(unreal.AnimStateNode):
    if "ABP_StrafeLocomotion" in n.get_path_name() and n.get_name() == "WalkStart":
        walk_start = n
        break
log(f"WalkStart={walk_start}")
if walk_start:
    ag_cls = getattr(unreal, "AnimationStateGraph", None)
    log(f"AnimationStateGraph cls={ag_cls}")
    if ag_cls:
        # Does one already exist as child?
        for g in unreal.ObjectIterator(ag_cls):
            if g.get_outer() == walk_start:
                log(f"existing child graph {g.get_path_name()}")
        try:
            g = unreal.new_object(ag_cls, walk_start, unreal.Name("WalkStart"))
            log(f"created graph {g.get_path_name()}")
            # try assign
            for prop in ("BoundGraph", "bound_graph"):
                try:
                    walk_start.set_editor_property(prop, g)
                    log(f"assigned {prop}")
                except Exception as e:
                    log(f"assign {prop}: {e}")
            # create SP + StateResult
            spn = unreal.new_object(unreal.AnimGraphNode_SequencePlayer, g, unreal.Name("SP"))
            seq = unreal.EditorAssetLibrary.load_asset(
                "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Walk_Start_F_0_Seq_RTG"
            )
            node = spn.get_editor_property("node")
            node.set_editor_property("sequence", seq)
            try:
                node.set_editor_property("loop_animation", False)
            except Exception:
                pass
            spn.set_editor_property("node", node)
            log(f"SP sequence set title path check")
            # StateResult
            rcls = getattr(unreal, "AnimGraphNode_StateResult", None)
            log(f"StateResult={rcls}")
            if rcls:
                res = unreal.new_object(rcls, g, unreal.Name("Result"))
                log(f"Result={res}")
        except Exception as e:
            log(f"graph create: {e}")

# Verify via iterator
for spn in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
    if "WalkStart" in spn.get_path_name():
        try:
            seq = spn.get_editor_property("node").get_editor_property("sequence")
            log(f"FOUND WalkStart SP seq={seq.get_name() if seq else None} path={spn.get_path_name()}")
        except Exception as e:
            log(f"FOUND WalkStart SP err={e}")

# Try Schema create transition between Idle and WalkStart
idle = loco = ws = None
for n in unreal.ObjectIterator(unreal.AnimStateNode):
    p = n.get_path_name()
    if "StateMachine_0.Locomotion" not in p:
        continue
    # identify by child graph names
    name = n.get_name()
    if name == "AnimStateNode_1":
        idle = n
    elif name == "AnimStateNode_2":
        loco = n
    elif name == "WalkStart":
        ws = n
log(f"idle={idle} loco={loco} ws={ws}")

schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationStateMachineSchema")
log(f"schema={schema} dir={[m for m in dir(schema) if not m.startswith('_')] if schema else None}")

# Pin connect Idle -> WalkStart
if idle and ws:
    try:
        pins_i = list(idle.get_editor_property("pins") or [])
        pins_w = list(ws.get_editor_property("pins") or [])
        log(f"idle pins={[p.get_name() for p in pins_i]}")
        log(f"ws pins={[p.get_name() for p in pins_w]}")
    except Exception as e:
        log(f"pins: {e}")

# AutomaticRule property on existing transition
for t in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if "StateMachine_0.Locomotion" not in t.get_path_name():
        continue
    for prop in (
        "AutomaticRuleBasedOnSequencePlayerInState",
        "automatic_rule_based_on_sequence_player_in_state",
        "bAutomaticRuleBasedOnSequencePlayerInState",
        "PriorityOrder",
        "CrossfadeDuration",
    ):
        try:
            log(f"T {t.get_name()}.{prop}={t.get_editor_property(prop)}")
        except Exception as e:
            log(f"T {t.get_name()}.{prop}: {e}")
    break

# Can we play montage from AnimBP using existing Get + new approach:
# AnimGraphNode_Slot already there — Character PlayAnimMontage is the missing piece.
# Try duplicating Jump call? Jump is CallFunction — can we clone via export?
# Use unreal.DuplicateObject if exists
log(f"hasattr duplicate_object={hasattr(unreal, 'duplicate_object')}")
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
eg = bel.find_event_graph(bp)
jump = None
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    if n.get_outer() == eg and str(bel.get_node_title(n)) == "Jump":
        jump = n
        break
if jump and hasattr(unreal, "duplicate_object"):
    try:
        clone = unreal.duplicate_object(jump, eg, unreal.Name("SS_PlayMontageClone"))
        log(f"duplicate_object -> {clone} title={bel.get_node_title(clone)}")
    except Exception as e:
        log(f"duplicate_object: {e}")

# Also try engine DuplicateObject via load
for path in (
    "/Script/CoreUObject.Default__Object",
):
    pass

log("done")
