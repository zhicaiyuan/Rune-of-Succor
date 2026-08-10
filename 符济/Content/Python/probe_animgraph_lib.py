# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeAG] {m}")


# AnimGraphLibrary
agl = unreal.AnimGraphLibrary
log(f"AnimGraphLibrary methods={[m for m in dir(agl) if not m.startswith('_')]}")

lal = unreal.LinkedAnimGraphLibrary
log(f"LinkedAnimGraphLibrary methods={[m for m in dir(lal) if not m.startswith('_')]}")

# Dump character Move graph nodes
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
try:
    graphs = []
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if "BP_ThirdPersonCharacter" in g.get_path_name():
            graphs.append(g.get_path_name())
    log(f"graphs={graphs}")
except Exception as e:
    log(f"graphs: {e}")

move = bel.find_graph(bp, "Move") if hasattr(bel, "find_graph") else None
log(f"find_graph Move={move}")
for g in unreal.ObjectIterator(unreal.EdGraph):
    if g.get_name() == "Move" and "BP_ThirdPersonCharacter" in g.get_path_name():
        move = g
        break
log(f"Move graph={move.get_path_name() if move else None}")
if move:
    for cls_name in ("K2Node_CallFunction", "K2Node_VariableGet", "K2Node_VariableSet", "K2Node_IfThenElse", "K2Node_EnhancedInputAction"):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != move and n.get_typed_outer(unreal.EdGraph) != move:
                    continue
                title = str(bel.get_node_title(n))
                log(f"Move/{cls_name}: {n.get_name()} title={title}")
            except Exception:
                continue

# EventGraph call titles
eg = bel.find_event_graph(bp)
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    try:
        if n.get_outer() != eg:
            continue
        log(f"EG CALL {n.get_name()} title={bel.get_node_title(n)}")
    except Exception:
        continue

# Transitions in ABP
for n in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if "ABP_StrafeLocomotion" not in n.get_path_name():
        continue
    log(f"TRANS {n.get_name()} path={n.get_path_name()}")
    for prop in ("Bidirectional", "PriorityOrder", "CrossfadeDuration", "LogicType", "PreviousState", "NextState"):
        try:
            log(f"  {prop}={n.get_editor_property(prop)}")
        except Exception as e:
            try:
                log(f"  {prop.lower()}={n.get_editor_property(prop.lower())}")
            except Exception as e2:
                log(f"  {prop}: {e2}")

# Identify states by path of children
states = {}
for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
    if "ABP_StrafeLocomotion" not in sp.get_path_name():
        continue
    p = sp.get_path_name()
    # extract AnimStateNode_X
    import re
    m = re.search(r"(AnimStateNode_\d+|WalkStart|WalkStop|RunStart|RunStop)", p)
    key = m.group(1) if m else "?"
    try:
        node = sp.get_editor_property("node")
        seq = node.get_editor_property("sequence")
        sname = seq.get_name() if seq else None
    except Exception:
        sname = None
    states.setdefault(key, set()).add(sname)
for k, v in states.items():
    log(f"state-content {k}: {v}")

# BlendSpaceGraph states
for bpnode in unreal.ObjectIterator(unreal.AnimGraphNode_BlendSpaceGraph):
    if "ABP_StrafeLocomotion" not in bpnode.get_path_name():
        continue
    log(f"BSG path={bpnode.get_path_name()}")

# Try AnimGraphLibrary methods that look useful
for m in dir(agl):
    if any(k in m.lower() for k in ("state", "transition", "sequence", "add", "set", "play", "montage")):
        log(f"AGL interesting: {m}")

log("done")
