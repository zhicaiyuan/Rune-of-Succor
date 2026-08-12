# -*- coding: utf-8 -*-
"""Dump Locomotion SM transitions involving RunTurn / Turn / WalkRun."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log(f"[ProbeRTT] {m}")


def under_abp(n, bp):
    o = n
    for _ in range(12):
        if o == bp:
            return True
        try:
            o = o.get_outer()
        except Exception:
            return False
        if o is None:
            return False
    return False


def state_label(st):
    if not st:
        return "?"
    # bound graph name often is the state name
    try:
        g = st.get_editor_property("bound_graph")
        if g:
            return str(g.get_name())
    except Exception:
        pass
    try:
        return str(bel.get_node_title(st))
    except Exception:
        return st.get_name()


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# Map state nodes
for n in unreal.ObjectIterator(unreal.AnimStateNode):
    if not under_abp(n, bp):
        continue
    try:
        if n.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue
    log(f"STATE {n.get_name()} -> {state_label(n)}")

# Transitions
for n in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if not under_abp(n, bp):
        continue
    try:
        if n.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue

    prev = next_ = None
    try:
        prev = n.get_editor_property("previous_state")
    except Exception:
        pass
    try:
        next_ = n.get_editor_property("next_state")
    except Exception:
        pass
    # alternate property names
    if prev is None:
        try:
            prev = n.get_editor_property("PreviousState")
        except Exception:
            pass
    if next_ is None:
        try:
            next_ = n.get_editor_property("NextState")
        except Exception:
            pass

    pl = state_label(prev)
    nl = state_label(next_)
    interesting = any(
        k in (pl + nl)
        for k in ("RunTurn", "Turn90", "Turn180", "Walk", "Run")
    )
    if not interesting:
        continue

    auto = None
    bidir = None
    priority = None
    try:
        auto = n.get_editor_property("automatic_rule_based_on_sequence_player_in_state")
    except Exception:
        try:
            auto = n.get_editor_property("bAutomaticRuleBasedOnSequencePlayerInState")
        except Exception:
            pass
    try:
        bidir = n.get_editor_property("bidirectional")
    except Exception:
        pass
    try:
        priority = n.get_editor_property("transition_priority_order")
    except Exception:
        try:
            priority = n.get_editor_property("PriorityOrder")
        except Exception:
            pass

    # Bound transition graph: list get-variable nodes
    bound = None
    try:
        bound = n.get_editor_property("bound_graph")
    except Exception:
        pass
    vars_used = []
    if bound:
        for gn in unreal.ObjectIterator(unreal.EdGraphNode):
            try:
                if gn.get_outer() != bound and gn.get_outer().get_outer() != bound:
                    # also nodes directly in bound
                    if gn.get_outer() != bound:
                        continue
            except Exception:
                continue
            try:
                cname = gn.get_class().get_name()
            except Exception:
                continue
            if "VariableGet" in cname or cname == "K2Node_VariableGet":
                try:
                    vn = str(gn.get_editor_property("variable_reference").member_name)
                except Exception:
                    try:
                        vn = str(bel.get_node_title(gn))
                    except Exception:
                        vn = gn.get_name()
                vars_used.append(vn)
            elif "AnimGraphNode_TransitionResult" in cname:
                pass

        # also scan all nodes whose outer chain includes bound
        for gn in unreal.ObjectIterator(unreal.K2Node_VariableGet):
            if not under_abp(gn, bp):
                continue
            o = gn.get_outer()
            hit = False
            for _ in range(6):
                if o == bound:
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
            try:
                vn = str(gn.get_editor_property("variable_reference").member_name)
            except Exception:
                try:
                    vn = str(bel.get_node_title(gn))
                except Exception:
                    vn = "?"
            if vn not in vars_used:
                vars_used.append(vn)

    log(
        f"TRANS {n.get_name()}: {pl} -> {nl} auto={auto} prio={priority} vars={vars_used}"
    )

# Check sequence players inside RunTurnL/R
for graph_name in ("RunTurnL", "RunTurnR", "Turn180L", "Turn180R", "Walk / Run"):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if not under_abp(n, bp):
            continue
        try:
            if n.get_outer().get_name() != graph_name:
                continue
        except Exception:
            continue
        cname = n.get_class().get_name()
        if "SequencePlayer" in cname or "SequenceEvaluator" in cname:
            seq = None
            try:
                seq = n.get_editor_property("sequence")
            except Exception:
                try:
                    # UE5 often nests in node struct
                    seq = n.get_editor_property("Node").get_editor_property("Sequence")
                except Exception:
                    pass
            log(f"PLAYER in {graph_name}: {cname} {n.get_name()} seq={seq}")

log("done")
