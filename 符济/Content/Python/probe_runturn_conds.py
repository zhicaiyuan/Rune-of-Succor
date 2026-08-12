# -*- coding: utf-8 -*-
"""Map Locomotion transitions to RunTurn/Turn states and dump condition vars."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeRTC] {m}")


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


def state_name_from_node(st):
    # bound graph name under AnimStateNode is the state name
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() == st:
            return g.get_name()
    return st.get_name()


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# Map AnimStateNode -> state name via child graph
state_nodes = {}
for st in unreal.ObjectIterator(unreal.AnimStateNode):
    if not under_abp(st, bp):
        continue
    # only Locomotion SM states (outer chain contains Locomotion graph under SM)
    try:
        if st.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue
    sn = state_name_from_node(st)
    state_nodes[st.get_name()] = (st, sn)
    log(f"STATE {st.get_name()} = {sn}")

# For each transition, find its Transition graph(s) and vars; infer from/to via shared Locomotion links
for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if not under_abp(tr, bp):
        continue
    try:
        if tr.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue

    # child transition graphs
    tgraphs = [g for g in unreal.ObjectIterator(unreal.EdGraph) if g.get_outer() == tr]
    vars_used = []
    calls = []
    for g in tgraphs:
        for n in unreal.ObjectIterator(unreal.EdGraphNode):
            if n.get_outer() != g:
                continue
            cname = n.get_class().get_name()
            if cname == "K2Node_VariableGet":
                vn = None
                for prop in ("variable_reference", "VariableReference"):
                    try:
                        ref = n.get_editor_property(prop)
                        for mp in ("member_name", "MemberName"):
                            try:
                                vn = str(ref.get_editor_property(mp))
                                break
                            except Exception:
                                pass
                        if vn:
                            break
                    except Exception:
                        pass
                if not vn:
                    # fallback: export text snippet
                    try:
                        vn = str(n.get_editor_property("variable_reference"))
                    except Exception:
                        vn = "?"
                if vn not in vars_used:
                    vars_used.append(vn)
            elif cname in ("K2Node_CallFunction", "K2Node_PromotableOperator", "K2Node_CommutativeAssociativeBinaryOperator"):
                fname = None
                try:
                    fname = str(n.get_editor_property("function_reference").member_name)
                except Exception:
                    try:
                        fname = str(n.get_editor_property("FunctionReference").member_name)
                    except Exception:
                        fname = cname
                calls.append(fname)

    auto = None
    for prop in (
        "automatic_rule_based_on_sequence_player_in_state",
        "bAutomaticRuleBasedOnSequencePlayerInState",
    ):
        try:
            auto = tr.get_editor_property(prop)
            break
        except Exception:
            pass

    # Try every possible way to get prev/next
    prev = next_ = None
    for attr in (
        "previous_state",
        "PreviousState",
        "prev_state",
        "previous",
        "next_state",
        "NextState",
        "next",
    ):
        try:
            v = tr.get_editor_property(attr)
            if v and "previous" in attr.lower():
                prev = v
            if v and "next" in attr.lower():
                next_ = v
        except Exception:
            pass
        try:
            v = getattr(tr, attr, None)
            if v and "previous" in attr.lower():
                prev = prev or v
            if v and "next" in attr.lower():
                next_ = next_ or v
        except Exception:
            pass

    pl = state_name_from_node(prev) if prev else "?"
    nl = state_name_from_node(next_) if next_ else "?"

    # Heuristic: if vars mention turn and we can't get links, still print
    log(
        f"TRANS {tr.get_name()} auto={auto} prev={pl} next={nl} vars={vars_used} calls={calls} graphs={[g.get_name() for g in tgraphs]}"
    )

# Extra: dump VariableGet member via export_text for transitions that have vars
for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if not under_abp(tr, bp):
        continue
    try:
        if tr.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() != tr:
            continue
        for n in unreal.ObjectIterator(unreal.K2Node_VariableGet):
            if n.get_outer() != g:
                continue
            try:
                txt = unreal.export_text(n)
            except Exception:
                try:
                    txt = n.export_text()
                except Exception:
                    txt = None
            if txt:
                # keep short
                s = str(txt).replace("\n", " | ")
                if len(s) > 300:
                    s = s[:300]
                log(f"EXPORT {tr.get_name()} VarGet: {s}")

log("done")
