# -*- coding: utf-8 -*-
"""Probe AnimBP SM states/transitions related to run turn / fold-back."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log(f"[ProbeRT] {m}")


def pin_name(p):
    try:
        return str(p.get_pin_name())
    except Exception:
        return "?"


bp = unreal.EditorAssetLibrary.load_asset(ABP)
if not bp:
    raise RuntimeError("no abp")

# AnimBP state machines
try:
    sms = bel.get_animation_blueprint_state_machines(bp)  # may not exist
    log(f"get_animation_blueprint_state_machines: {sms}")
except Exception as e:
    log(f"no get_animation_blueprint_state_machines: {e}")

# Iterate all ed graph nodes
from collections import defaultdict

states = []
trans = []
for cls_name in (
    "AnimStateNode",
    "AnimStateTransitionNode",
    "AnimStateConduitNode",
    "AnimStateEntryNode",
):
    try:
        cls = getattr(unreal, "K2Node_" + cls_name, None) or getattr(unreal, cls_name, None)
    except Exception:
        cls = None
    if not cls:
        # try AnimGraphNode variants
        for cand in (
            f"AnimStateNode",
            f"AnimGraphNode_{cls_name}",
        ):
            pass

# Broad scan
for n in unreal.ObjectIterator(unreal.EdGraphNode):
    try:
        outer = n.get_outer()
        if outer is None:
            continue
        # must be under this abp
        o = outer
        ok = False
        for _ in range(8):
            if o == bp:
                ok = True
                break
            try:
                o = o.get_outer()
            except Exception:
                break
            if o is None:
                break
        if not ok:
            continue
        title = ""
        try:
            title = str(bel.get_node_title(n))
        except Exception:
            title = n.get_name()
        cname = n.get_class().get_name()
        low = (title + " " + cname + " " + n.get_name()).lower()
        if "turn" in low or "runturn" in low or "transition" in cname.lower() or "state" in cname.lower():
            if "transition" in cname.lower() or "Transition" in cname:
                trans.append((cname, n.get_name(), title, str(outer.get_name())))
            elif "state" in cname.lower() or "State" in cname:
                states.append((cname, n.get_name(), title, str(outer.get_name())))
    except Exception:
        pass

log(f"states found: {len(states)}")
for s in states[:80]:
    log(f"STATE {s}")

log(f"trans found: {len(trans)}")
for t in trans[:80]:
    log(f"TRANS {t}")

# Also list member variables related to turn
try:
    # dump via CDO
    cdo = unreal.get_default_object(bp.generated_class())
    for prop in (
        "bWantsTurn90",
        "bWantsTurn180",
        "bTurnLeft",
        "bTurnYawLocked",
        "TurnAngle90",
        "TurnAngle180",
        "bStopInput",
        "bWantsWalk",
        "AbsMoveYawDelta",
    ):
        try:
            v = cdo.get_editor_property(prop)
            log(f"CDO {prop}={v}")
        except Exception as e:
            log(f"CDO {prop}: {e}")
except Exception as e:
    log(f"cdo err {e}")

log("done")
