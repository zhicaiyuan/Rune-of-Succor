# -*- coding: utf-8 -*-
"""Dump transition condition titles mapped via node titles (works in UE5.8)."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeRTT2] {m}")


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


def child_graph_name(st):
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() == st:
            return g.get_name()
    return "?"


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# state map
states = {}
for st in unreal.ObjectIterator(unreal.AnimStateNode):
    if not under_abp(st, bp):
        continue
    try:
        if st.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue
    states[st] = child_graph_name(st)
    log(f"STATE {st.get_name()}={states[st]}")

# For transitions: dump node titles in Transition graph
for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if not under_abp(tr, bp):
        continue
    try:
        if tr.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue

    auto = False
    try:
        auto = tr.get_editor_property("automatic_rule_based_on_sequence_player_in_state")
    except Exception:
        pass

    titles = []
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() != tr:
            continue
        for n in unreal.ObjectIterator(unreal.EdGraphNode):
            if n.get_outer() != g:
                continue
            try:
                t = n.get_node_title()
            except Exception:
                t = n.get_class().get_name()
            titles.append(str(t))

    # Also try to find linked states via list_all_pins on transition if available
    links = []
    try:
        for p in tr.list_all_pins():
            pname = str(p.get_pin_name()) if hasattr(p, "get_pin_name") else "?"
            linked = []
            try:
                for lp in p.get_linked_to():
                    on = lp.get_owning_node()
                    linked.append(states.get(on, on.get_name()))
            except Exception:
                pass
            if linked:
                links.append(f"{pname}->{linked}")
    except Exception as e:
        links.append(f"pinerr:{e}")

    log(f"TRANS {tr.get_name()} auto={auto} links={links}")
    for t in titles:
        log(f"  TITLE {t}")

log("done")
