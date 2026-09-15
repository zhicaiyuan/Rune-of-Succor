# -*- coding: utf-8 -*-
"""Dump all Locomotion SM transitions + sequence skeletons."""
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[Probe2] {m}")


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


def in_locomotion(n):
    o = n
    for _ in range(10):
        try:
            name = o.get_name()
        except Exception:
            return False
        if name == "Locomotion":
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
    for getter in (
        lambda: st.get_editor_property("state_name"),
        lambda: st.get_editor_property("StateName"),
        lambda: st.get_editor_property("bound_graph").get_name(),
        lambda: st.get_name(),
    ):
        try:
            v = getter()
            if v is not None and str(v).strip() and str(v) != "None":
                return str(v)
        except Exception:
            pass
    return "?"


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# States
for n in unreal.ObjectIterator(unreal.AnimStateNode):
    if not under_abp(n, bp) or not in_locomotion(n):
        continue
    bg = None
    try:
        bg = n.get_editor_property("bound_graph")
    except Exception:
        pass
    log(f"STATE {n.get_name()} label={state_label(n)} bound={bg.get_name() if bg else None}")

# All transitions in Locomotion
count = 0
for n in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    if not under_abp(n, bp) or not in_locomotion(n):
        continue
    count += 1
    prev = next_ = None
    for prop in ("previous_state", "PreviousState", "prev_state"):
        try:
            prev = n.get_editor_property(prop)
            if prev:
                break
        except Exception:
            pass
    for prop in ("next_state", "NextState", "next_state"):
        try:
            next_ = n.get_editor_property(prop)
            if next_:
                break
        except Exception:
            pass

    # Fallback: use pin links
    if prev is None or next_ is None:
        try:
            for p in n.get_all_pins():
                pname = str(p.get_pin_name())
                links = p.get_linked_to()
                if not links:
                    continue
                other = links[0].get_owning_node()
                if "State" in other.get_class().get_name():
                    if "Previous" in pname or pname.lower() in ("in", "previous", "prev"):
                        prev = prev or other
                    if "Next" in pname or pname.lower() in ("out", "next"):
                        next_ = next_ or other
        except Exception as e:
            log(f"pin err {e}")

    pl = state_label(prev)
    nl = state_label(next_)

    auto = priority = cross = None
    for prop in (
        "automatic_rule_based_on_sequence_player_in_state",
        "bAutomaticRuleBasedOnSequencePlayerInState",
    ):
        try:
            auto = n.get_editor_property(prop)
            break
        except Exception:
            pass
    for prop in ("transition_priority_order", "PriorityOrder"):
        try:
            priority = n.get_editor_property(prop)
            break
        except Exception:
            pass
    for prop in ("crossfade_duration", "CrossfadeDuration"):
        try:
            cross = n.get_editor_property(prop)
            break
        except Exception:
            pass

    bound = None
    try:
        bound = n.get_editor_property("bound_graph")
    except Exception:
        pass

    vars_used = []
    if bound:
        for gn in unreal.ObjectIterator(unreal.K2Node_VariableGet):
            if not under_abp(gn, bp):
                continue
            o = gn.get_outer()
            hit = False
            for _ in range(8):
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
                vn = "?"
            if vn not in vars_used:
                vars_used.append(vn)

    log(
        f"TRANS {n.get_name()}: {pl} -> {nl} auto={auto} prio={priority} cross={cross} vars={vars_used} bound={bound.get_name() if bound else None}"
    )

log(f"transition count={count}")

# Sequence players under any graph whose name contains Turn/Walk/Run
for n in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
    if not under_abp(n, bp):
        continue
    try:
        gname = n.get_outer().get_name()
    except Exception:
        continue
    low = gname.lower()
    if not any(k in low for k in ("turn", "walk", "run", "idle", "start", "stop")):
        continue
    seq = None
    try:
        node = n.get_editor_property("node")
        seq = node.get_editor_property("sequence")
    except Exception:
        try:
            seq = n.get_editor_property("sequence")
        except Exception:
            pass
    skel = None
    path = None
    length = None
    if seq:
        try:
            path = seq.get_path_name()
            skel = seq.get_editor_property("skeleton")
            length = seq.get_editor_property("sequence_length")
        except Exception as e:
            path = str(seq)
            log(f"seq meta err {e}")
    log(
        f"PLAYER graph={gname} seq={path} skel={skel.get_name() if skel else None} len={length}"
    )

try:
    sk = bp.get_editor_property("target_skeleton")
    log(f"ABP target_skeleton={sk.get_path_name() if sk else None}")
except Exception as e:
    log(f"ABP skel err {e}")

for path in (
    "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Run_Fast_Turn_L_Seq_RTG",
    "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Run_Fast_Turn_R_Seq_RTG",
    "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG/Turn_180_L_Seq_RTG",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/03_Run_RM/11_Run_Fast_RM/Run_Fast_Turn_L_Seq",
    "/Game/Sword_Animations/Animations/Sequence1/04_Run/01_Run/11_Run_Fast/Run_Fast_Turn_L_Seq",
):
    exists = unreal.EditorAssetLibrary.does_asset_exist(path)
    log(f"ASSET exists={exists} {path}")

log("done")
