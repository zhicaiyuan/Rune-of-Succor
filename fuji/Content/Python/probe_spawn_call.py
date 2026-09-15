# -*- coding: utf-8 -*-
"""Find a way to spawn configured K2 call / variable nodes in UE 5.8."""
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeSpawn] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
graph = bel.find_event_graph(bp)

# 1) BlueprintNodeSpawner / ActionDatabase
names = [n for n in dir(unreal) if "Spawner" in n or "ActionDatabase" in n or "BlueprintAction" in n]
log(f"unreal spawn-related={names}")

for path in (
    "/Script/BlueprintGraph.BlueprintActionDatabase",
    "/Script/BlueprintGraph.BlueprintNodeSpawner",
    "/Script/BlueprintGraph.BlueprintFunctionNodeSpawner",
    "/Script/BlueprintGraph.BlueprintVariableNodeSpawner",
    "/Script/BlueprintGraph.K2Node_CallFunction",
):
    log(f"load_class {path} -> {unreal.load_class(None, path)}")
    log(f"load_object {path} -> {unreal.load_object(None, path)}")

# 2) Try FunctionNodeSpawner create
fn = unreal.load_object(None, "/Script/Engine.Character:PlayAnimMontage")
cls = unreal.load_class(None, "/Script/BlueprintGraph.BlueprintFunctionNodeSpawner")
if cls:
    log(f"FunctionNodeSpawner dir={[m for m in dir(cls) if not m.startswith('_')][:40]}")
    cdo = unreal.get_default_object(cls)
    log(f"CDO dir={[m for m in dir(cdo) if 'reate' in m or 'nvoke' in m or 'pawn' in m]}")
    for meth in ("create", "Create", "make"):
        if hasattr(cls, meth):
            try:
                sp = getattr(cls, meth)(fn)
                log(f"cls.{meth}(fn) -> {sp}")
            except Exception as e:
                log(f"cls.{meth}: {e}")
        if hasattr(cdo, meth):
            try:
                sp = getattr(cdo, meth)(fn)
                log(f"cdo.{meth}(fn) -> {sp}")
            except Exception as e:
                log(f"cdo.{meth}: {e}")

# 3) call_method Create on FunctionNodeSpawner
if cls:
    for args in (
        (fn,),
        (unreal.K2Node_CallFunction.static_class(), fn),
    ):
        try:
            sp = cls.call_method("Create", args)
            log(f"call_method Create{args} -> {sp}")
        except Exception as e:
            log(f"call_method Create{args}: {e}")

# 4) Inspect BlueprintGraphPin API for defaults / connect
tick = None
for n in unreal.ObjectIterator(unreal.K2Node_Event):
    try:
        if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    except Exception:
        continue
if tick:
    pins = bel.list_all_pins(tick) or []
    log(f"tick pins count={len(pins)}")
    for p in pins:
        log(f"pin attrs={[a for a in dir(p) if not a.startswith('_')]}")
        for a in ("get_name", "get_pin_name", "pin_name", "name", "get_display_name", "default_value"):
            if hasattr(p, a):
                try:
                    log(f"  p.{a}={getattr(p, a) if not callable(getattr(p, a)) else getattr(p, a)()}")
                except Exception as e:
                    try:
                        log(f"  p.{a}() -> {getattr(p, a)()}")
                    except Exception as e2:
                        log(f"  p.{a}: {e}/{e2}")
        break

# 5) AnimState BoundGraph access
for n in unreal.ObjectIterator(unreal.AnimStateNode):
    if "ABP_StrafeLocomotion" not in n.get_path_name():
        continue
    log(f"AnimState {n.get_name()}")
    for prop in ("BoundGraph", "bound_graph", "StateGraph", "state_graph"):
        try:
            v = n.get_editor_property(prop)
            log(f"  {prop}={v}")
        except Exception as e:
            log(f"  {prop}: {e}")
    # only a couple
    break

# 6) Existing SequencePlayers in ABP - can we change sequence?
count = 0
for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
    if "ABP_StrafeLocomotion" not in sp.get_path_name():
        continue
    count += 1
    if count > 3:
        continue
    log(f"SP {sp.get_path_name()}")
    for outer in ("node", "Node"):
        try:
            node = sp.get_editor_property(outer)
            seq = node.get_editor_property("sequence")
            log(f"  {outer}.sequence={seq.get_name() if seq else None}")
        except Exception as e:
            log(f"  {outer}: {e}")

# 7) try EditorGraphUtils / GraphEditor
gnames = [n for n in dir(unreal) if "Graph" in n and ("Editor" in n or "Util" in n or "Schema" in n)]
log(f"Graph utils={gnames[:40]}")

# 8) add_function_override ReceiveTick then inspect
try:
    r = bel.add_function_override(bp, "ReceiveTick", unreal.IntPoint(0, 0))
    log(f"add_function_override ReceiveTick -> {r}")
except Exception as e:
    log(f"add_function_override: {e}")

# 9) list_functions on character BP
try:
    fns = bel.list_functions(bp)
    log(f"list_functions sample={list(fns)[:20] if fns else None}")
except Exception as e:
    log(f"list_functions: {e}")

log("done")
