# -*- coding: utf-8 -*-
"""
Turn + run pivot (折返跑) — clean rebuild via Python (no manual uasset edit).

1) IK-retarget Turn_90/180 + Run_Fast_Turn -> SwordRTG
2) AnimBP: facing-vs-input turn vars (reuse rebuild_turn_facing_vs_input logic)
3) Locomotion SM: RTG sequences on turn states + gated transition rules
4) AnimBP: bInTurnAnim from GetCurrentStateName
5) Character: Orient OFF during turn, snap yaw to input when turn ends
   (removes old YL_* yaw-lock nodes if present)

Run with editor CLOSED:
  UnrealEditor-Cmd.exe ... -ExecutePythonScript=.../setup_turn_runpivot.py
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
RTG_DIR = f"{OUT}/SwordRTG"
IKR = f"{OUT}/IK/IKR_SwordToCharacters"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"

SNAP_YAW_OFFSET = 0.0  # mesh RelativeYaw -90 is visual; do NOT add +90 on capsule snap
STATIONARY_SPEED = 40.0
INPUT_EPS = 0.1

TURN_SRC = {
    "Turn90L": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_90_L_Seq",
    "Turn90R": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_90_R_Seq",
    "Turn180L": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_180_L_Seq",
    "Turn180R": "/Game/Sword_Animations/Animations/Sequence2/09_Turn/01_Turn/Turn_180_R_Seq",
    "RunTurnL": "/Game/Sword_Animations/Animations/Sequence2/04_Run/03_Run_RM/11_Run_Fast_RM/Run_Fast_Turn_L_Seq",
    "RunTurnR": "/Game/Sword_Animations/Animations/Sequence2/04_Run/03_Run_RM/11_Run_Fast_RM/Run_Fast_Turn_R_Seq",
}

IKR_CANDIDATES = (
    f"{OUT}/IK/IKR_SwordToCharacters",
    "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/NewIKRetargeter",
)


def resolve_ikr():
    for p in IKR_CANDIDATES:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            log(f"using IKR {p}")
            return p
    # create via setup_ordinary_locomotion helper
    try:
        import os
        import importlib.util
        import sys

        path = os.path.join(os.path.dirname(__file__), "setup_ordinary_locomotion.py")
        if not os.path.exists(path):
            path = unreal.Paths.project_content_dir() + "Python/setup_ordinary_locomotion.py"
        spec = importlib.util.spec_from_file_location("setup_ordinary_locomotion", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules["setup_ordinary_locomotion"] = mod
        spec.loader.exec_module(mod)
        mod.setup_ik_retargeter()
        if unreal.EditorAssetLibrary.does_asset_exist(IKR_CANDIDATES[0]):
            return IKR_CANDIDATES[0]
    except Exception as e:
        log(f"setup_ik_retargeter failed: {e}")
    for p in IKR_CANDIDATES:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            return p
    return None


def resolve_state_seq():
    """Prefer *_RTG; fall back to Sword source if same-skeleton."""
    out = {}
    for sname, src in TURN_SRC.items():
        rtg = f"{RTG_DIR}/{src.split('/')[-1]}_RTG"
        if unreal.EditorAssetLibrary.does_asset_exist(rtg):
            out[sname] = rtg
        elif unreal.EditorAssetLibrary.does_asset_exist(src):
            log(f"WARN {sname}: no RTG, using source {src.split('/')[-1]}")
            out[sname] = src
        else:
            raise RuntimeError(f"missing anim for {sname}: {rtg} / {src}")
    return out

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[TurnPivot] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def connect(a, b):
    if not a or not b:
        return False
    try:
        return bool(a.try_create_connection(b))
    except Exception:
        try:
            return bool(b.try_create_connection(a))
        except Exception:
            return False


def pin_in(node, name):
    for cand in bel.list_input_pins(node) or []:
        try:
            if str(cand.get_pin_name()) == name:
                return cand
        except Exception:
            pass
    try:
        return bel.find_input_pin(node, name)
    except Exception:
        return None


def pin_out(node, name=None):
    if name:
        for cand in bel.list_output_pins(node) or []:
            try:
                if str(cand.get_pin_name()) == name:
                    return cand
            except Exception:
                pass
        try:
            return bel.find_output_pin(node, name)
        except Exception:
            pass
    try:
        return bel.find_result_pin(node)
    except Exception:
        outs = bel.list_output_pins(node) or []
        return outs[0] if outs else None


def set_val(node, pin_name, value):
    p = pin_in(node, pin_name)
    if not p:
        return False
    try:
        p.set_pin_value(str(value))
        return True
    except Exception:
        return False


def pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        pass


def safe_rename(node, name):
    try:
        existing = unreal.find_object(node.get_outer(), name)
        if existing and existing != node:
            return False
        node.rename(name)
        return True
    except Exception:
        return False


def under_abp(n, bp):
    o = n
    for _ in range(14):
        if o == bp:
            return True
        try:
            o = o.get_outer()
        except Exception:
            return False
        if o is None:
            return False
    return False


# ---------------------------------------------------------------------------
# 1) Retarget
# ---------------------------------------------------------------------------
def retarget_turn_anims():
    if not unreal.EditorAssetLibrary.does_directory_exist(RTG_DIR):
        unreal.EditorAssetLibrary.make_directory(RTG_DIR)

    missing_rtg = [
        f"{RTG_DIR}/{src.split('/')[-1]}_RTG"
        for src in TURN_SRC.values()
        if not unreal.EditorAssetLibrary.does_asset_exist(f"{RTG_DIR}/{src.split('/')[-1]}_RTG")
    ]
    if not missing_rtg:
        log("all turn RTG already exist — skip retarget")
        return

    ikr_path = resolve_ikr()
    if not ikr_path:
        log("WARN: no IKR — will use Sword source sequences if skeleton matches")
        return

    ikr = load(ikr_path)
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)
    srcs = list(TURN_SRC.values())
    datas = []
    for p in srcs:
        if unreal.EditorAssetLibrary.does_asset_exist(p):
            datas.append(unreal.EditorAssetLibrary.find_asset_data(p))
        else:
            log(f"WARN missing src {p}")

    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", datas)
    inputs.set_editor_property("source_mesh", src_mesh)
    inputs.set_editor_property("target_mesh", tgt_mesh)
    inputs.set_editor_property("ik_retarget_asset", ikr)
    inputs.set_editor_property("suffix", "_RTG")
    inputs.set_editor_property("target_path", RTG_DIR)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("overwrite_existing_files", True)

    log(f"retarget {len(datas)} turn/pivot clips -> {RTG_DIR}")
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs) or []
    for ad in created:
        try:
            obj = ad.get_asset()
            path = obj.get_path_name().split(".")[0] if obj else str(ad.package_name)
            save(path)
            log(f"  saved {path}")
        except Exception as e:
            log(f"  save err {e}")
    try:
        unreal.EditorAssetLibrary.save_directory(RTG_DIR, only_if_is_dirty=False, recursive=True)
    except Exception:
        pass
    log("retarget pass done")


# ---------------------------------------------------------------------------
# 2) Turn vars — delegate to existing script body inline
# ---------------------------------------------------------------------------
def run_turn_vars():
    import os

    candidates = [
        os.path.join(os.path.dirname(__file__), "rebuild_turn_facing_vs_input.py"),
        unreal.Paths.project_content_dir() + "Python/rebuild_turn_facing_vs_input.py",
    ]
    path = None
    for c in candidates:
        if os.path.exists(c):
            path = c
            break
    if not path:
        raise RuntimeError("rebuild_turn_facing_vs_input.py not found")
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("rebuild_turn_facing_vs_input", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["rebuild_turn_facing_vs_input"] = mod
    spec.loader.exec_module(mod)
    mod.run()
    log("turn vars OK")


# ---------------------------------------------------------------------------
# 3) SM helpers (from finalize_start_stop_sm patterns)
# ---------------------------------------------------------------------------
def state_graph_name(st):
    g = state_bound_graph(st)
    return g.get_name() if g else st.get_name()


def find_locomotion_sm(abp):
    sm = None
    for st in unreal.ObjectIterator(unreal.AnimStateNode):
        if not under_abp(st, abp):
            continue
        try:
            if st.get_outer().get_name() == "Locomotion":
                sm = st.get_outer()
                break
        except Exception:
            pass
    if sm:
        return sm
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if not under_abp(g, abp):
            continue
        if g.get_name() == "Locomotion":
            try:
                if g.get_outer().get_class().get_name().endswith("StateMachine"):
                    return g
            except Exception:
                return g
    return None


def map_states(abp, sm):
    out = {}
    for st in unreal.ObjectIterator(unreal.AnimStateNode):
        if not under_abp(st, abp):
            continue
        try:
            if st.get_outer() != sm:
                continue
        except Exception:
            continue
        name = state_graph_name(st)
        if name:
            out[name] = st
    log(f"SM states: {sorted(out.keys())}")
    return out


def state_bound_graph(st):
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() == st:
            return g
    for prop in ("bound_graph", "BoundGraph", "state_graph"):
        try:
            g = st.get_editor_property(prop)
            if g:
                return g
        except Exception:
            pass
    try:
        st.reconstruct_node()
        for g in unreal.ObjectIterator(unreal.EdGraph):
            if g.get_outer() == st:
                return g
    except Exception:
        pass
    return None


def ensure_sequence_in_state(state_node, seq_path, loop=False):
    seq = load(seq_path)
    bound = state_bound_graph(state_node)
    if not bound:
        log(f"no bound graph for {state_node.get_name()}")
        return False

    sp = None
    for cand in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
        try:
            if cand.get_outer() == bound:
                sp = cand
                break
        except Exception:
            continue
    if not sp:
        sp = unreal.new_object(unreal.AnimGraphNode_SequencePlayer, bound, unreal.Name("SequencePlayer"))
        try:
            sp.allocate_default_pins()
            sp.reconstruct_node()
        except Exception:
            pass

    try:
        node = sp.get_editor_property("node")
        node.set_editor_property("sequence", seq)
        for prop in ("loop_animation", "b_loop_animation"):
            try:
                node.set_editor_property(prop, loop)
            except Exception:
                pass
        sp.set_editor_property("node", node)
        log(f"  seq {state_graph_name(state_node)} <- {seq.get_name()}")
    except Exception as e:
        log(f"  set seq err {e}")
        return False
    return True


def create_state(sm, name, x, y):
    node = unreal.new_object(unreal.AnimStateNode, sm, unreal.Name(name))
    pos(node, x, y)
    for prop in ("state_name", "StateName"):
        try:
            node.set_editor_property(prop, unreal.Name(name))
        except Exception:
            pass
    try:
        node.allocate_default_pins()
        node.reconstruct_node()
    except Exception:
        pass
    return node


def ensure_transition_graph(tr):
    g = get_transition_graph(tr)
    if g:
        return g
    try:
        tr.allocate_default_pins()
        tr.reconstruct_node()
    except Exception:
        pass
    return get_transition_graph(tr)


def create_transition(sm, src, dst, name, automatic=False, priority=0):
    t = unreal.new_object(unreal.AnimStateTransitionNode, sm, unreal.Name(name))
    for prop in ("previous_state", "PreviousState"):
        try:
            t.set_editor_property(prop, src)
            break
        except Exception:
            pass
    for prop in ("next_state", "NextState"):
        try:
            t.set_editor_property(prop, dst)
            break
        except Exception:
            pass
    for prop in (
        "automatic_rule_based_on_sequence_player_in_state",
        "bAutomaticRuleBasedOnSequencePlayerInState",
    ):
        try:
            t.set_editor_property(prop, automatic)
            break
        except Exception:
            pass
    for prop in ("crossfade_duration", "CrossfadeDuration"):
        try:
            t.set_editor_property(prop, 0.2)
            break
        except Exception:
            pass
    for prop in ("priority_order", "PriorityOrder", "transition_priority_order"):
        try:
            t.set_editor_property(prop, priority)
            break
        except Exception:
            pass
    try:
        t.allocate_default_pins()
        t.reconstruct_node()
    except Exception:
        pass
    return t


def get_transition_graph(tr):
    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() == tr:
            return g
    return None


def find_transition_result(graph):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if "TransitionResult" in n.get_class().get_name():
            return n
    return None


def purge_transition_logic(ed, graph):
    kill = []
    result = None
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if "TransitionResult" in n.get_class().get_name():
            result = n
        else:
            kill.append(n)
    if kill:
        ed.remove_nodes(kill)
    return result


def graph_editor_for(bp, graph):
    for args in ((bp, graph), (graph,)):
        try:
            ed = BGE.get_graph_editor(*args)
            if ed:
                return ed
        except Exception:
            pass
    try:
        return BGE.get_graph_editor_by_name(bp, graph.get_name())
    except Exception:
        return None


def spawn_var_get(graph, var_name, x, y):
    n = unreal.new_object(unreal.K2Node_VariableGet, graph, unreal.Name(f"TR_Get_{var_name}"))
    pos(n, x, y)
    try:
        ref = n.get_editor_property("variable_reference")
        ref.set_editor_property("member_name", unreal.Name(var_name))
        n.set_editor_property("variable_reference", ref)
    except Exception:
        pass
    try:
        n.allocate_default_pins()
        n.reconstruct_node()
    except Exception:
        pass
    return n


def spawn_call(graph, path, x, y, name):
    n = unreal.new_object(unreal.K2Node_CallFunction, graph, unreal.Name(name))
    pos(n, x, y)
    try:
        fn = unreal.load_object(None, path)
        ref = n.get_editor_property("function_reference")
        ref.set_editor_property("member_name", fn.get_name())
        n.set_editor_property("function_reference", ref)
    except Exception:
        pass
    try:
        n.allocate_default_pins()
        n.reconstruct_node()
    except Exception:
        pass
    return n


def make_get_bool(ed, graph, var_name, x, y):
    if ed:
        try:
            n = ed.add_get_member_variable_node(var_name)
            safe_rename(n, f"TR_Get_{var_name}")
            pos(n, x, y)
            return n
        except Exception:
            pass
    return spawn_var_get(graph, var_name, x, y)


def make_not(ed, graph, x, y):
    if ed:
        try:
            n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
            safe_rename(n, f"TR_Not_{x}")
            pos(n, x, y)
            return n
        except Exception:
            pass
    return spawn_call(graph, "/Script/Engine.KismetMathLibrary:Not_PreBool", x, y, f"TR_Not_{x}")


def make_and(ed, graph, x, y):
    if ed:
        try:
            n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
            safe_rename(n, f"TR_And_{x}_{y}")
            pos(n, x, y)
            return n
        except Exception:
            pass
    return spawn_call(
        graph, "/Script/Engine.KismetMathLibrary:BooleanAND", x, y, f"TR_And_{x}_{y}"
    )


def make_cmp_ge(ed, graph, literal, x, y):
    if ed:
        try:
            n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat")
            safe_rename(n, f"TR_Ge_{literal}")
            pos(n, x, y)
            set_val(n, "B", str(literal))
            return n
        except Exception:
            pass
    n = spawn_call(
        graph,
        "/Script/Engine.KismetMathLibrary:GreaterEqual_FloatFloat",
        x,
        y,
        f"TR_Ge_{literal}",
    )
    set_val(n, "B", str(literal))
    return n


def make_cmp_lt(ed, graph, literal, x, y):
    if ed:
        try:
            n = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Less_FloatFloat")
            safe_rename(n, f"TR_Lt_{literal}")
            pos(n, x, y)
            set_val(n, "B", str(literal))
            return n
        except Exception:
            pass
    n = spawn_call(
        graph,
        "/Script/Engine.KismetMathLibrary:Less_FloatFloat",
        x,
        y,
        f"TR_Lt_{literal}",
    )
    set_val(n, "B", str(literal))
    return n


def purge_transition_logic_simple(graph):
    kill = []
    result = None
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if "TransitionResult" in n.get_class().get_name():
            result = n
        else:
            kill.append(n)
    for n in kill:
        try:
            n.destroy_node()
        except Exception:
            try:
                graph.remove_node(n)
            except Exception:
                pass
    return result


def wire_and_to_result(ed, graph, bool_out_pin, result_node, x0=0):
    """Connect bool_out_pin -> TransitionResult."""
    res_in = pin_in(result_node, "Result") or pin_in(result_node, "CanEnterTransition")
    if not res_in:
        for cand in bel.list_input_pins(result_node) or []:
            try:
                if "Result" in str(cand.get_pin_name()) or "CanEnter" in str(
                    cand.get_pin_name()
                ):
                    res_in = cand
                    break
            except Exception:
                pass
    return connect(bool_out_pin, res_in)


def chain_and(ed, graph, pins):
    if not pins:
        return None
    if len(pins) == 1:
        return pins[0]
    cur = pins[0]
    for i, nxt in enumerate(pins[1:], 1):
        nd = make_and(ed, graph, 200 + i * 120, 100)
        connect(cur, pin_in(nd, "A"))
        connect(nxt, pin_in(nd, "B"))
        cur = pin_out(nd, "ReturnValue")
    return cur


def var_out(get_node, var_name):
    return pin_out(get_node, var_name) or pin_out(get_node)


def wire_transition_rule(bp, tr, spec):
    """
    spec keys:
      wants90/wants180, left (True/False/None), moving (True=run pivot, False=stationary, None=ignore)
    """
    graph = ensure_transition_graph(tr)
    if not graph:
        log(f"no transition graph for {tr.get_name()}")
        return False
    ed = graph_editor_for(bp, graph)

    if ed:
        result = purge_transition_logic(ed, graph)
    else:
        result = purge_transition_logic_simple(graph)
    if not result:
        log(f"no TransitionResult in {tr.get_name()}")
        return False

    pins = []
    y = 0
    if spec.get("wants180"):
        g = make_get_bool(ed, graph, "bWantsTurn180", 0, y)
        pins.append(var_out(g, "bWantsTurn180"))
        y += 80
    elif spec.get("wants90"):
        g = make_get_bool(ed, graph, "bWantsTurn90", 0, y)
        pins.append(var_out(g, "bWantsTurn90"))
        y += 80

    if spec.get("left") is True:
        g = make_get_bool(ed, graph, "bTurnLeft", 0, y)
        pins.append(var_out(g, "bTurnLeft"))
        y += 80
    elif spec.get("left") is False:
        g = make_get_bool(ed, graph, "bTurnLeft", 0, y)
        nt = make_not(ed, graph, 120, y)
        connect(var_out(g, "bTurnLeft"), pin_in(nt, "A"))
        pins.append(pin_out(nt, "ReturnValue"))
        y += 80

    moving = spec.get("moving")
    if moving is not None:
        gs = make_get_bool(ed, graph, "GroundSpeed", 0, y)
        gs_pin = var_out(gs, "GroundSpeed")
        if moving:
            cmpn = make_cmp_ge(ed, graph, STATIONARY_SPEED, 120, y)
        else:
            cmpn = make_cmp_lt(ed, graph, STATIONARY_SPEED, 120, y)
        connect(gs_pin, pin_in(cmpn, "A"))
        pins.append(pin_out(cmpn, "ReturnValue"))
        y += 80

    out = chain_and(ed, graph, pins)
    ok = wire_and_to_result(ed, graph, out, result)
    log(f"  rule {tr.get_name()} spec={spec} wired={ok}")
    return ok


def find_transition_between(sm, states, src_name, dst_name):
    src = states.get(src_name)
    dst = states.get(dst_name)
    if not src or not dst:
        return None, src, dst
    for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
        try:
            if tr.get_outer() != sm:
                continue
        except Exception:
            continue
        ensure_transition_graph(tr)
        prev = next_ = None
        for p in ("previous_state", "PreviousState"):
            try:
                prev = tr.get_editor_property(p)
                if prev:
                    break
            except Exception:
                pass
        for p in ("next_state", "NextState"):
            try:
                next_ = tr.get_editor_property(p)
                if next_:
                    break
            except Exception:
                pass
        if prev == src and next_ == dst:
            return tr, src, dst
    return None, src, dst


def setup_sm(abp):
    state_seq = resolve_state_seq()
    sm = find_locomotion_sm(abp)
    if not sm:
        raise RuntimeError("Locomotion state machine not found")
    states = map_states(abp, sm)

    loop = states.get("Walk / Run") or states.get("Walk/Run")
    if not loop:
        for name, st in states.items():
            if "Walk" in name and "Stop" not in name and "Start" not in name:
                loop = st
                break
    if not loop:
        raise RuntimeError("Walk/Run loop state not found")

    lx = 900
    ly = -400
    for i, sname in enumerate(("Turn90L", "Turn90R", "Turn180L", "Turn180R", "RunTurnL", "RunTurnR")):
        if sname not in states:
            states[sname] = create_state(sm, sname, lx + (i % 3) * 220, ly + (i // 3) * 180)
        ensure_sequence_in_state(states[sname], state_seq[sname], loop=False)

    loop_name = state_graph_name(loop)
    log(f"loop state={loop_name}")

    # Transition wiring is fragile in headless Python — wire rules only on EXISTING transitions.
    entry_map = {
        "Turn180L": {"wants180": True, "left": True, "moving": False},
        "Turn180R": {"wants180": True, "left": False, "moving": False},
        "Turn90L": {"wants90": True, "left": True, "moving": False},
        "Turn90R": {"wants90": True, "left": False, "moving": False},
        "RunTurnL": {"wants180": True, "left": True, "moving": True},
        "RunTurnR": {"wants180": True, "left": False, "moving": True},
    }
    turn_names = set(entry_map.keys())

    wired_in = wired_out = 0
    for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
        try:
            if tr.get_outer() != sm:
                continue
        except Exception:
            continue
        prev = next_ = None
        for p in ("previous_state", "PreviousState"):
            try:
                prev = tr.get_editor_property(p)
                if prev:
                    break
            except Exception:
                pass
        for p in ("next_state", "NextState"):
            try:
                next_ = tr.get_editor_property(p)
                if next_:
                    break
            except Exception:
                pass
        if not prev or not next_:
            continue
        pn = state_graph_name(prev)
        nn = state_graph_name(next_)

        if pn == loop_name and nn in entry_map:
            try:
                wire_transition_rule(abp, tr, entry_map[nn])
                wired_in += 1
            except Exception as e:
                log(f"  skip rule {tr.get_name()}->{nn}: {e}")
        elif pn in turn_names and nn == loop_name:
            for prop in (
                "automatic_rule_based_on_sequence_player_in_state",
                "bAutomaticRuleBasedOnSequencePlayerInState",
            ):
                try:
                    tr.set_editor_property(prop, True)
                    break
                except Exception:
                    pass
            wired_out += 1

    log(f"SM wired in={wired_in} out={wired_out}")
    if wired_in == 0:
        log("MANUAL: draw Walk/Run -> Turn* / RunTurn* transitions in Locomotion SM (see TURN_RUNPIVOT_README.txt)")
    log("SM setup OK")


# ---------------------------------------------------------------------------
# 4) AnimBP bInTurnAnim
# ---------------------------------------------------------------------------
def ensure_abp_var(abp, name, kind="bool"):
    try:
        if kind == "bool":
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        else:
            pin = bel.get_basic_type_by_name(unreal.Name("real"))
        bel.add_member_variable(abp, unreal.Name(name), pin)
    except Exception:
        pass


def wire_b_in_turn_anim(abp):
    ensure_abp_var(abp, "bInTurnAnim", "bool")
    try:
        ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    except Exception as e:
        log(f"WARN: skip bInTurnAnim ({e})")
        return
    graph = ed.get_graph()

    # purge old ITA_ nodes
    kill = []
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if not n.get_name().startswith("ITA_"):
            continue
        kill.append(n)
    if kill:
        ed.remove_nodes(kill)

    upd = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() != graph:
            continue
        try:
            if "BlueprintUpdateAnimation" in n.get_name() or "UpdateAnimation" in str(
                bel.get_node_title(n)
            ):
                upd = n
                break
        except Exception:
            pass
    if not upd:
        log("WARN: no BlueprintUpdateAnimation — skip bInTurnAnim")
        return

    # attach at end of update chain — find last exec node from update
    get_state = ed.add_call_function_node(
        "/Script/Engine.AnimInstance:GetCurrentStateName"
    )
    safe_rename(get_state, "ITA_GetState")
    pos(get_state, 2200, 400)
    set_val(get_state, "MachineIndex", "0")

    contains = ed.add_call_function_node(
        "/Script/Engine.KismetStringLibrary:Contains"
    )
    safe_rename(contains, "ITA_ContainsTurn")
    pos(contains, 2500, 400)
    set_val(contains, "SearchIn", "Turn")

    contains2 = ed.add_call_function_node(
        "/Script/Engine.KismetStringLibrary:Contains"
    )
    safe_rename(contains2, "ITA_ContainsRunTurn")
    pos(contains2, 2500, 520)
    set_val(contains2, "SearchIn", "RunTurn")

    or_b = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanOR")
    safe_rename(or_b, "ITA_Or")
    pos(or_b, 2720, 460)

    set_turn = ed.add_set_member_variable_node("bInTurnAnim")
    safe_rename(set_turn, "ITA_SetInTurn")
    pos(set_turn, 2940, 460)

    connect(pin_out(get_state, "ReturnValue"), pin_in(contains, "SearchIn"))
    connect(pin_out(get_state, "ReturnValue"), pin_in(contains2, "SearchIn"))
    connect(pin_out(contains, "ReturnValue"), pin_in(or_b, "A"))
    connect(pin_out(contains2, "ReturnValue"), pin_in(or_b, "B"))
    connect(pin_out(or_b, "ReturnValue"), pin_in(set_turn, "bInTurnAnim"))

    # Try hook exec from SI_SetStop chain tail or update event
    exec_out = bel.find_then_pin(upd)
    if exec_out:
        for n in unreal.ObjectIterator(unreal.K2Node):
            if n.get_outer() != graph:
                continue
            if n.get_name() == "K2Node_ExecutionSequence_0":
                exec_out = pin_out(n, "Then 1") or pin_out(n, "Then 0") or exec_out
    if exec_out:
        connect(exec_out, pin_in(set_turn, "execute"))
    log("bInTurnAnim wired")


# ---------------------------------------------------------------------------
# 5) Character — simple orient + end snap (purge YL_*)
# ---------------------------------------------------------------------------
def purge_yl_nodes(ed, graph):
    kill = []
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        name = n.get_name()
        title = ""
        try:
            title = str(bel.get_node_title(n))
        except Exception:
            pass
        if name.startswith("YL_") or "YawLock" in title or name.startswith("YL_DEL"):
            kill.append(n)
    if kill:
        ed.remove_nodes(kill)
        log(f"purged {len(kill)} old yaw-lock nodes")


def ensure_char_vars(bp):
    for name, kind in (
        ("bPrevInTurn", "bool"),
        ("TurnSnapYaw", "real"),
    ):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(kind if kind != "real" else "double"))
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception:
            try:
                pin = bel.get_basic_type_by_name(unreal.Name("float"))
                bel.add_member_variable(bp, unreal.Name(name), pin)
            except Exception:
                pass


def wire_character_turn_orient(bp):
    ensure_char_vars(bp)
    try:
        ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    except Exception as e:
        log(f"WARN: skip character orient ({e})")
        return
    graph = ed.get_graph()
    purge_yl_nodes(ed, graph)

    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() != graph:
            continue
        if "ReceiveTick" in n.get_name() or "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if not tick:
        log("WARN: no Tick event")
        return

    # get anim instance + bInTurnAnim
    get_mesh = ed.add_call_function_node("/Script/Engine.Character:GetMesh")
    safe_rename(get_mesh, "TO_GetMesh")
    pos(get_mesh, 800, 1200)

    get_anim = ed.add_call_function_node("/Script/Engine.SkeletalMeshComponent:GetAnimInstance")
    safe_rename(get_anim, "TO_GetAnim")
    pos(get_anim, 1000, 1200)

    get_in_turn = ed.add_call_function_node(
        "/Script/Engine.KismetSystemLibrary:GetBoolPropertyByName"
    )
    safe_rename(get_in_turn, "TO_GetInTurn")
    pos(get_in_turn, 1220, 1200)
    set_val(get_in_turn, "PropertyName", "bInTurnAnim")

    get_move = ed.add_call_function_node("/Script/Engine.Pawn:GetLastMovementInputVector")
    safe_rename(get_move, "TO_GetMove")
    pos(get_move, 1220, 1360)

    brk = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BreakVector")
    safe_rename(brk, "TO_Brk")
    pos(brk, 1440, 1360)

    atan = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:DegAtan2")
    safe_rename(atan, "TO_Atan")
    pos(atan, 1660, 1360)

    add_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if not add_yaw:
        add_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    safe_rename(add_yaw, "TO_OffAdd")
    pos(add_yaw, 1780, 1360)
    set_val(add_yaw, "B", str(SNAP_YAW_OFFSET))

    norm_yaw = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    safe_rename(norm_yaw, "TO_OffNorm")
    pos(norm_yaw, 1960, 1360)

    get_rot = ed.add_call_function_node("/Script/Engine.Actor:K2_GetActorRotation")
    safe_rename(get_rot, "TO_GetRot")
    pos(get_rot, 1660, 1500)

    make_rot = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:MakeRotator")
    safe_rename(make_rot, "TO_MakeRot")
    pos(make_rot, 1880, 1420)

    set_rot = ed.add_call_function_node("/Script/Engine.Actor:K2_SetActorRotation")
    safe_rename(set_rot, "TO_SetRot")
    pos(set_rot, 2100, 1420)

    get_cmc = ed.add_call_function_node("/Script/Engine.Character:GetCharacterMovement")
    safe_rename(get_cmc, "TO_GetCMC")
    pos(get_cmc, 1220, 1100)

    set_orient = ed.add_call_function_node(
        "/Script/Engine.CharacterMovementComponent:SetOrientRotationToMovement"
    )
    safe_rename(set_orient, "TO_SetOrient")
    pos(set_orient, 2100, 1100)

    get_prev = ed.add_get_member_variable_node("bPrevInTurn")
    safe_rename(get_prev, "TO_GetPrev")
    pos(get_prev, 1440, 1100)

    not_in_turn = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(not_in_turn, "TO_NotInTurn")
    pos(not_in_turn, 1660, 1080)

    and_end = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:BooleanAND")
    safe_rename(and_end, "TO_AndEnd")
    pos(and_end, 1880, 1080)

    set_prev = ed.add_set_member_variable_node("bPrevInTurn")
    safe_rename(set_prev, "TO_SetPrev")
    pos(set_prev, 2320, 1200)

    branch_end = ed.add_branch_node()
    safe_rename(branch_end, "TO_BranchEnd")
    pos(branch_end, 1880, 1200)

    branch_in = ed.add_branch_node()
    safe_rename(branch_in, "TO_BranchIn")
    pos(branch_in, 1440, 1200)

    lit_f = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(lit_f, "TO_LitF")
    pos(lit_f, 1880, 1080)

    lit_t = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Not_PreBool")
    safe_rename(lit_t, "TO_LitT")
    pos(lit_t, 1880, 1140)

    # wiring
    try:
        self_ref = ed.add_self_node()
    except Exception:
        self_ref = ed.add_call_function_node("/Script/Engine.Actor:GetOwner")
    pos(self_ref, 600, 1200)

    connect(pin_out(self_ref, "self"), pin_in(get_mesh, "self"))
    connect(pin_out(get_mesh, "ReturnValue"), pin_in(get_anim, "self"))
    connect(pin_out(get_anim, "ReturnValue"), pin_in(get_in_turn, "Object"))
    connect(pin_out(self_ref, "self"), pin_in(get_move, "self"))
    connect(pin_out(get_move, "ReturnValue"), pin_in(brk, "InVec"))
    connect(pin_out(brk, "Y"), pin_in(atan, "Y"))
    connect(pin_out(brk, "X"), pin_in(atan, "X"))
    connect(pin_out(self_ref, "self"), pin_in(get_rot, "self"))
    connect(pin_out(atan, "ReturnValue"), pin_in(add_yaw, "A"))
    connect(pin_out(add_yaw, "ReturnValue"), pin_in(norm_yaw, "Angle") or pin_in(norm_yaw, "A"))
    connect(pin_out(norm_yaw, "ReturnValue"), pin_in(make_rot, "Y"))
    connect(pin_out(get_rot, "ReturnValue"), pin_in(make_rot, "Roll"))
    connect(pin_out(get_rot, "ReturnValue"), pin_in(make_rot, "Pitch"))
    connect(pin_out(make_rot, "ReturnValue"), pin_in(set_rot, "NewRotation"))
    connect(pin_out(self_ref, "self"), pin_in(set_rot, "self"))
    connect(pin_out(self_ref, "self"), pin_in(get_cmc, "self"))
    connect(pin_out(get_cmc, "ReturnValue"), pin_in(set_orient, "self"))

    connect(pin_out(get_in_turn, "PropertyValue"), pin_in(branch_in, "Condition"))
    connect(pin_out(get_in_turn, "PropertyValue"), pin_in(lit_f, "A"))
    connect(pin_out(lit_f, "ReturnValue"), pin_in(set_orient, "bOrientRotationToMovement"))
    connect(pin_out(get_in_turn, "PropertyValue"), pin_in(lit_t, "A"))
    set_orient_on = ed.add_call_function_node(
        "/Script/Engine.CharacterMovementComponent:SetOrientRotationToMovement"
    )
    safe_rename(set_orient_on, "TO_SetOrientOn")
    pos(set_orient_on, 2100, 1260)
    connect(pin_out(lit_t, "ReturnValue"), pin_in(set_orient_on, "bOrientRotationToMovement"))

    connect(pin_out(get_in_turn, "PropertyValue"), pin_in(not_in_turn, "A"))
    connect(pin_out(get_prev, "bPrevInTurn"), pin_in(and_end, "A"))
    connect(pin_out(not_in_turn, "ReturnValue"), pin_in(and_end, "B"))
    connect(pin_out(and_end, "ReturnValue"), pin_in(branch_end, "Condition"))
    connect(pin_out(get_in_turn, "PropertyValue"), pin_in(set_prev, "bPrevInTurn"))

    exec_pin = bel.find_then_pin(tick)
    if exec_pin:
        connect(exec_pin, bel.find_execute_pin(branch_in))
        connect(bel.find_then_pin(branch_in), bel.find_execute_pin(set_orient))
        connect(bel.find_else_pin(branch_in), bel.find_execute_pin(set_orient_on))
        connect(bel.find_then_pin(set_orient), bel.find_execute_pin(branch_end))
        connect(bel.find_then_pin(set_orient_on), bel.find_execute_pin(branch_end))
        connect(bel.find_then_pin(branch_end), bel.find_execute_pin(set_rot))
        connect(bel.find_then_pin(set_rot), bel.find_execute_pin(set_prev))
        connect(bel.find_else_pin(branch_end), bel.find_execute_pin(set_prev))
    connect(pin_out(get_cmc, "ReturnValue"), pin_in(set_orient_on, "self"))

    log("character turn orient wired")


def write_readme():
    path = unreal.Paths.project_content_dir() + "Python/TURN_RUNPIVOT_README.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(
            """Turn + Run Pivot — setup_turn_runpivot.py

DONE BY SCRIPT
  - SwordRTG: Turn_90/180 + Run_Fast_Turn (retargeted)
  - AnimBP turn vars: bWantsTurn90/180, bTurnLeft, MoveYawDelta...
  - Turn state SequencePlayers -> *_RTG assets

YOU WIRE IN EDITOR (Locomotion SM)
  Draw transitions if missing, then set rules:

  Walk/Run -> Turn180L
    bWantsTurn180 AND bTurnLeft AND GroundSpeed < 40

  Walk/Run -> Turn180R
    bWantsTurn180 AND NOT bTurnLeft AND GroundSpeed < 40

  Walk/Run -> Turn90L / Turn90R
    bWantsTurn90 AND left/right AND GroundSpeed < 40

  Walk/Run -> RunTurnL
    bWantsTurn180 AND bTurnLeft AND GroundSpeed >= 40
    Priority HIGHER than Turn180 (lower number)

  Walk/Run -> RunTurnR
    bWantsTurn180 AND NOT bTurnLeft AND GroundSpeed >= 40

  Turn* / RunTurn* -> Walk/Run
    Automatic Rule (sequence finished)
    Do NOT exit on NOT bWantsTurn*

CHARACTER (optional, if script wired TO_* nodes)
  During turn: OrientRotationToMovement OFF
  Turn ended: SetActorRotation to input yaw, Orient ON

TEST
  1) Stand still A->D : Turn180
  2) Run A->D : RunTurn (not Turn180)
  3) If facing off 90 after turn: tweak end snap or mesh -90 offset
"""
        )
    log(f"wrote {path}")


def run():
    log("=== setup turn + run pivot ===")
    retarget_turn_anims()
    run_turn_vars()

    abp = load(ABP)
    setup_sm(abp)
    try:
        wire_b_in_turn_anim(abp)
    except Exception as e:
        log(f"WARN bInTurnAnim: {e}")
    try:
        bel.compile_blueprint(abp)
    except Exception as e:
        log(f"compile abp: {e}")
    save(ABP)

    bp = load(CHAR)
    try:
        wire_character_turn_orient(bp)
    except Exception as e:
        log(f"WARN character orient: {e}")
    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log(f"compile char: {e}")
    save(CHAR)

    write_readme()
    log("=== DONE ===")


if __name__ == "__main__":
    run()
