# -*- coding: utf-8 -*-
"""List EdGraphs under ABP Locomotion + variable gets in transition-like graphs."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeSMG] {m}")


def under_abp(n, bp):
    o = n
    for _ in range(16):
        if o == bp:
            return True
        try:
            o = o.get_outer()
        except Exception:
            return False
        if o is None:
            return False
    return False


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# All graphs under ABP
graphs = []
for g in unreal.ObjectIterator(unreal.EdGraph):
    if not under_abp(g, bp):
        continue
    try:
        outer = g.get_outer().get_name()
    except Exception:
        outer = "?"
    graphs.append((g.get_name(), outer, g.get_path_name()))

graphs.sort()
log(f"graph count={len(graphs)}")
for name, outer, path in graphs:
    log(f"GRAPH name={name} outer={outer}")

# For graphs that look like transitions or RunTurn, dump var gets + result
interesting = []
for name, outer, path in graphs:
    low = (name + " " + outer).lower()
    if any(k in low for k in ("trans", "runturn", "turn180", "turn90", "walk", "run", "loco")):
        interesting.append(name)

# Dump K2 nodes in each interesting graph
for g in unreal.ObjectIterator(unreal.EdGraph):
    if not under_abp(g, bp):
        continue
    gname = g.get_name()
    try:
        outer = g.get_outer().get_name()
    except Exception:
        outer = "?"
    key = (gname + " " + outer).lower()
    if not any(k in key for k in ("transition", "runturn", "turn180", "turn90")):
        # also dump if graph name equals state names from earlier probe
        if gname not in (
            "RunTurnL",
            "RunTurnR",
            "Turn180L",
            "Turn180R",
            "Turn90L",
            "Turn90R",
            "Walk / Run",
            "Locomotion",
        ):
            continue

    log(f"--- DUMP {gname} outer={outer} ---")
    nodes = []
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != g:
            # nodes can be nested?
            o = n.get_outer()
            hit = False
            for _ in range(4):
                if o == g:
                    hit = True
                    break
                try:
                    o = o.get_outer()
                except Exception:
                    break
                if o is None:
                    break
            if not hit:
                continue
        cname = n.get_class().get_name()
        extra = ""
        if "VariableGet" in cname or "VariableSet" in cname:
            try:
                extra = " var=" + str(n.get_editor_property("variable_reference").member_name)
            except Exception:
                pass
        elif "AnimGraphNode_SequencePlayer" in cname:
            try:
                seq = n.get_editor_property("node").get_editor_property("sequence")
                extra = " seq=" + (seq.get_name() if seq else "None")
            except Exception:
                pass
        elif "TransitionResult" in cname:
            extra = " (result)"
        nodes.append(f"{cname}{extra}")
    for s in sorted(set(nodes)):
        log(f"  NODE {s}")

# Also inspect FBakedStateMachine / property links on generated class if any
try:
    gc = bp.generated_class()
    cdo = unreal.get_default_object(gc)
    log(f"generated_class={gc.get_name()}")
    # property_links often holds anim nodes
    try:
        links = cdo.get_editor_property("property_links")
        log(f"property_links len={len(links) if links else 0}")
    except Exception as e:
        log(f"property_links: {e}")
except Exception as e:
    log(f"gen class: {e}")

log("done")
