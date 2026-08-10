# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[ProbeTick] {m}")


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
graph = bel.find_event_graph(bp)
log(f"graph={graph}")

# BEL methods related to event
meths = [m for m in dir(bel) if "event" in m.lower() or "tick" in m.lower() or "override" in m.lower()]
log(f"BEL event meths={meths}")

# try signatures
for args in (
    ("ReceiveTick",),
    (unreal.Name("ReceiveTick"),),
    ("ReceiveTick", 0, 0),
    ("ReceiveTick", unreal.IntPoint(-600, 1800)),
):
    try:
        r = bel.add_event_override(bp, *args)
        log(f"add_event_override{args} -> {r}")
    except Exception as exc:
        log(f"add_event_override{args}: {exc}")

# dump all event nodes
for n in unreal.ObjectIterator(unreal.K2Node_Event):
    try:
        if n.get_outer() != graph:
            continue
    except Exception:
        continue
    title = ""
    try:
        title = str(bel.get_node_title(n))
    except Exception:
        pass
    mn = ""
    try:
        ref = n.get_editor_property("event_reference")
        mn = str(ref.get_editor_property("member_name"))
    except Exception:
        pass
    pins = []
    try:
        pins = [str(bel.get_pin_name(p)) for p in (bel.list_all_pins(n) or [])]
    except Exception:
        pass
    log(f"EVENT {n.get_name()} title={title} member={mn} pins={pins}")

# dump call function nodes titles containing Tick / Montage / Crouch
for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
    try:
        if n.get_outer() != graph:
            continue
        title = str(bel.get_node_title(n))
        if any(k in title for k in ("Tick", "Montage", "Crouch", "Velocity", "Max", "Walk")):
            log(f"CALL {n.get_name()} title={title}")
    except Exception:
        continue

# UFunction load tests
for path in (
    "/Script/Engine.Actor:ReceiveTick",
    "/Script/Engine.Actor:GetVelocity",
    "/Script/Engine.KismetMathLibrary:VSize",
    "/Script/Engine.Character:PlayAnimMontage",
    "/Script/Engine.KismetSystemLibrary:MakeLiteralBool",
):
    obj = unreal.load_object(None, path)
    log(f"load {path} -> {obj}")

# Class load
for path in (
    "/Script/Engine.KismetMathLibrary",
    "/Script/Engine.Default__KismetMathLibrary",
):
    log(f"load_class {path} -> {unreal.load_class(None, path)}")
    log(f"load_object {path} -> {unreal.load_object(None, path)}")

log("done")
