# -*- coding: utf-8 -*-
"""
Finalize Start/Stop in ABP_StrafeLocomotion state machine.

Creates WalkStart/RunStart/WalkStop/RunStop states with SequencePlayers,
rewires Idle <-> Locomotion transitions through them, and sets automatic
time-based rules for Start/Stop completion.
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"

RTG = {
    "WalkStart": f"{OUT}/SwordRTG/Walk_Start_F_0_Seq_RTG",
    "WalkStop": f"{OUT}/SwordRTG/Walk_Stop_F_0_Seq_RTG",
    "RunStart": f"{OUT}/SwordRTG/Run_Start_F_0_Seq_RTG",
    "RunStop": f"{OUT}/SwordRTG/Run_Stop_F_0_Seq_RTG",
}

MONTAGES = {
    "WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}


def log(m):
    unreal.log(f"[SSFinal] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def dump_pin_type_api():
    bel = unreal.BlueprintEditorLibrary
    for name in (
        "get_basic_type_by_name",
        "get_object_reference_type",
        "get_class_reference_type",
        "add_member_variable",
        "set_node_pos",
        "remove_unused_nodes",
    ):
        log(f"BEL.{name}={hasattr(bel, name)}")
    pin = bel.get_basic_type_by_name(unreal.Name("bool"))
    log(f"bool pin={pin}")
    try:
        log(f"pin dict={pin.to_tuple() if hasattr(pin,'to_tuple') else pin}")
    except Exception:
        pass
    # property names on EdGraphPinType
    try:
        p = unreal.EdGraphPinType()
        log(f"EdGraphPinType props sample: {[x for x in dir(p) if not x.startswith('_')][:40]}")
    except Exception as exc:
        log(f"EdGraphPinType: {exc}")


def add_vars(abp):
    bel = unreal.BlueprintEditorLibrary
    # bool / float
    for name, tname in (("SS_WasMoving", "bool"), ("SS_PrevSpeed", "double"), ("SS_bWantsWalk", "bool")):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(tname))
            ok = bel.add_member_variable(abp, unreal.Name(name), pin)
            log(f"add {name}: {ok}")
        except Exception as exc:
            # try float
            try:
                pin = bel.get_basic_type_by_name(unreal.Name("float" if tname == "double" else tname))
                ok = bel.add_member_variable(abp, unreal.Name(name), pin)
                log(f"add {name} alt: {ok}")
            except Exception as exc2:
                log(f"add {name}: {exc} / {exc2}")
    # montage object refs
    for name in ("SS_WalkStart", "SS_WalkStop", "SS_RunStart", "SS_RunStop"):
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            ok = bel.add_member_variable(abp, unreal.Name(name), pin)
            log(f"add {name}: {ok}")
        except Exception as exc:
            log(f"add {name}: {exc}")


def set_montage_defaults(abp):
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile vars: {exc}")
    cdo = unreal.get_default_object(abp.generated_class())
    for prop, key in (
        ("SS_WalkStart", "WalkStart"),
        ("SS_WalkStop", "WalkStop"),
        ("SS_RunStart", "RunStart"),
        ("SS_RunStop", "RunStop"),
    ):
        try:
            cdo.set_editor_property(prop, load(MONTAGES[key]))
            log(f"CDO {prop}=OK")
        except Exception as exc:
            log(f"CDO {prop}: {exc}")


def classify_states():
    """Return (sm_graph, idle, loco, jumps, all_states)."""
    states = []
    for n in unreal.ObjectIterator(unreal.AnimStateNode):
        try:
            if "ABP_StrafeLocomotion" not in n.get_path_name():
                continue
        except Exception:
            continue
        bound = None
        try:
            bound = n.get_editor_property("bound_graph")
        except Exception:
            pass
        kind = "empty"
        detail = ""
        if bound:
            # sequence players in this bound graph
            for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
                try:
                    if sp.get_outer() != bound and sp.get_typed_outer(unreal.EdGraph) != bound:
                        continue
                except Exception:
                    continue
                try:
                    node = sp.get_editor_property("node")
                    seq = node.get_editor_property("sequence")
                    if seq:
                        kind = "seq"
                        detail = seq.get_name()
                except Exception:
                    pass
            bs_cls = getattr(unreal, "AnimGraphNode_BlendSpacePlayer", None)
            if bs_cls:
                for bp in unreal.ObjectIterator(bs_cls):
                    try:
                        if bp.get_outer() != bound and bp.get_typed_outer(unreal.EdGraph) != bound:
                            continue
                        kind = "bs"
                        try:
                            node = bp.get_editor_property("node")
                            bso = node.get_editor_property("blend_space")
                            detail = bso.get_name() if bso else "BS"
                        except Exception:
                            detail = "BS"
                    except Exception:
                        continue
        try:
            x = n.get_editor_property("node_pos_x")
            y = n.get_editor_property("node_pos_y")
        except Exception:
            x = y = 0
        log(f"state {n.get_name()} kind={kind}:{detail} pos=({x},{y})")
        states.append({"node": n, "kind": kind, "detail": detail, "bound": bound, "x": x, "y": y})

    if not states:
        return None, None, None, [], []

    sm = states[0]["node"].get_outer()
    idle = None
    loco = None
    jumps = []
    for s in states:
        d = s["detail"]
        if s["kind"] == "bs":
            loco = s
        elif s["kind"] == "seq":
            if any(k in d for k in ("Jump", "Land", "Fall")):
                jumps.append(s)
            elif "Idle" in d or idle is None:
                if "Idle" in d:
                    idle = s
                elif idle is None and not any(k in d for k in ("Jump", "Land", "Fall")):
                    idle = s
    return sm, idle, loco, jumps, states


def ensure_sequence_in_state(state_node, seq_path: str, loop: bool = False) -> bool:
    seq = load(seq_path)
    bound = None
    try:
        bound = state_node.get_editor_property("bound_graph")
    except Exception:
        pass
    if not bound:
        try:
            # Force reconstruct to create bound graph
            state_node.reconstruct_node()
            bound = state_node.get_editor_property("bound_graph")
        except Exception as exc:
            log(f"no bound: {exc}")
            return False
    if not bound:
        log(f"still no bound for {state_node.get_name()}")
        return False

    # Find existing SP or create
    sp = None
    for cand in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
        try:
            if cand.get_outer() == bound or cand.get_typed_outer(unreal.EdGraph) == bound:
                sp = cand
                break
        except Exception:
            continue
    if not sp:
        sp = unreal.new_object(
            unreal.AnimGraphNode_SequencePlayer, bound, unreal.Name("SequencePlayer")
        )
        try:
            unreal.BlueprintEditorLibrary.set_node_pos(sp, 0, 0)
        except Exception:
            try:
                sp.set_editor_property("node_pos_x", 0)
                sp.set_editor_property("node_pos_y", 0)
            except Exception:
                pass
        try:
            sp.allocate_default_pins()
            sp.reconstruct_node()
        except Exception:
            pass
        log(f"created SP in {bound.get_name()}")

    try:
        node = sp.get_editor_property("node")
        node.set_editor_property("sequence", seq)
        for prop in ("loop_animation", "b_loop_animation"):
            try:
                node.set_editor_property(prop, loop)
            except Exception:
                pass
        sp.set_editor_property("node", node)
        log(f"SP -> {seq.get_name()} loop={loop}")
    except Exception as exc:
        log(f"set sequence: {exc}")
        return False

    # Connect to StateResult
    result = None
    result_cls = getattr(unreal, "AnimGraphNode_StateResult", None)
    if result_cls:
        for r in unreal.ObjectIterator(result_cls):
            try:
                if r.get_outer() == bound or r.get_typed_outer(unreal.EdGraph) == bound:
                    result = r
                    break
            except Exception:
                continue
    if not result and result_cls:
        result = unreal.new_object(result_cls, bound, unreal.Name("OutputPose"))
        try:
            unreal.BlueprintEditorLibrary.set_node_pos(result, 400, 0)
        except Exception:
            pass
        try:
            result.allocate_default_pins()
            result.reconstruct_node()
        except Exception:
            pass

    if result:
        schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationGraphSchema")
        if not schema:
            schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
        try:
            pins_sp = list(sp.get_editor_property("pins") or [])
            pins_r = list(result.get_editor_property("pins") or [])
            log(f"SP pins={[p.get_name() for p in pins_sp]} Result={[p.get_name() for p in pins_r]}")
            # find pose out / result in
            pout = None
            pin_in = None
            for p in pins_sp:
                n = p.get_name()
                if n in ("Pose", "Animation", "Pose Out"):
                    pout = p
            for p in pins_r:
                n = p.get_name()
                if n in ("Result", "Pose", "Animation"):
                    pin_in = p
            if not pout and pins_sp:
                # usually last output pose
                for p in pins_sp:
                    try:
                        if str(p.get_editor_property("direction")).endswith("Output"):
                            pout = p
                    except Exception:
                        pass
            if pout and pin_in and schema:
                unreal.EdGraphSchema_K2.try_create_connection(schema, pout, pin_in)
                log("connected pose->result")
        except Exception as exc:
            log(f"connect: {exc}")
    return True


def create_state(sm_graph, name: str, x: int, y: int):
    node = unreal.new_object(unreal.AnimStateNode, sm_graph, unreal.Name(name))
    try:
        unreal.BlueprintEditorLibrary.set_node_pos(node, x, y)
    except Exception:
        try:
            node.set_editor_property("node_pos_x", x)
            node.set_editor_property("node_pos_y", y)
        except Exception:
            pass
    for prop in ("state_name", "StateName"):
        try:
            node.set_editor_property(prop, unreal.Name(name))
        except Exception:
            pass
    try:
        node.allocate_default_pins()
    except Exception:
        pass
    try:
        node.reconstruct_node()
    except Exception as exc:
        log(f"reconstruct {name}: {exc}")
    # List nodes of sm_graph
    try:
        nodes = list(sm_graph.get_editor_property("nodes") or [])
        log(f"SM nodes after {name}: {len(nodes)}")
    except Exception as exc:
        log(f"SM nodes prop: {exc}")
    return node


def create_transition(sm_graph, src, dst, name: str, automatic: bool = False):
    tcls = unreal.AnimStateTransitionNode
    tnode = unreal.new_object(tcls, sm_graph, unreal.Name(name))
    try:
        unreal.BlueprintEditorLibrary.set_node_pos(
            tnode,
            int((src.get_editor_property("node_pos_x") + dst.get_editor_property("node_pos_x")) / 2),
            int((src.get_editor_property("node_pos_y") + dst.get_editor_property("node_pos_y")) / 2),
        )
    except Exception:
        pass

    # Link previous/next
    for prop, val in (
        ("previous_state", src),
        ("next_state", dst),
        ("PreviousState", src),
        ("NextState", dst),
    ):
        try:
            tnode.set_editor_property(prop, val)
        except Exception:
            pass

    # Automatic rule based on sequence player finishing
    for prop, val in (
        ("automatic_rule_based_on_sequence_player_in_state", automatic),
        ("b_automatic_rule_based_on_sequence_player_in_state", automatic),
        ("AutomaticRuleBasedOnSequencePlayerInState", automatic),
    ):
        try:
            tnode.set_editor_property(prop, val)
            log(f"{name} set {prop}={val}")
        except Exception:
            pass

    # Bidirectional logic share / duration
    for prop, val in (
        ("crossfade_duration", 0.15),
        ("CrossfadeDuration", 0.15),
    ):
        try:
            tnode.set_editor_property(prop, val)
        except Exception:
            pass

    try:
        tnode.allocate_default_pins()
        tnode.reconstruct_node()
    except Exception:
        pass

    # Try schema helper
    schema = unreal.load_object(None, "/Script/AnimGraph.Default__AnimationStateMachineSchema")
    if schema:
        log(f"SM schema methods={[m for m in dir(schema) if 'trans' in m.lower() or 'create' in m.lower()]}")
        for meth in (
            "create_transition_node_between",
            "create_transition",
            "try_create_connection",
        ):
            if hasattr(schema, meth):
                try:
                    getattr(schema, meth)(src, dst)
                    log(f"schema.{meth} ok")
                except Exception as exc:
                    log(f"schema.{meth}: {exc}")

    # Pin connect Out->Transition->In
    try:
        schema_k2 = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")
        src_pins = list(src.get_editor_property("pins") or [])
        dst_pins = list(dst.get_editor_property("pins") or [])
        t_pins = list(tnode.get_editor_property("pins") or [])
        log(
            f"trans {name} src_pins={[p.get_name() for p in src_pins]} "
            f"t={[p.get_name() for p in t_pins]} dst={[p.get_name() for p in dst_pins]}"
        )
    except Exception as exc:
        log(f"pin dump: {exc}")

    log(f"transition {name} created")
    return tnode


def rebind_bs():
    abp = load(ABP)
    if not unreal.EditorAssetLibrary.does_asset_exist(BS):
        log("BS missing")
        return
    bs = load(BS)
    n = 0
    # Search all objects for blend_space property mentioning ABP
    for cls_name in (
        "AnimGraphNode_BlendSpacePlayer",
        "AnimGraphNode_BlendSpaceEvaluator",
        "AnimGraphNode_RotationOffsetBlendSpace",
        "AnimGraphNode_BlendSpaceGraph",
        "AnimGraphNode_BlendSpaceSampleResult",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for obj in unreal.ObjectIterator(cls):
            try:
                if "ABP_StrafeLocomotion" not in obj.get_path_name():
                    continue
            except Exception:
                continue
            log(f"found {cls_name} {obj.get_name()}")
            for outer in ("node", "Node"):
                try:
                    node = obj.get_editor_property(outer)
                    for prop in ("blend_space", "BlendSpace"):
                        try:
                            node.set_editor_property(prop, bs)
                            obj.set_editor_property(outer, node)
                            n += 1
                            log(f"rebound via {outer}.{prop}")
                        except Exception:
                            pass
                except Exception:
                    pass
    # Soft binary check
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = f.read()
    log(f"ABP has BS_WalkRun_Sword={b'BS_WalkRun_Sword' in data} BS_Idle={b'BS_Idle_Walk_Run' in data}")
    log(f"BS rebinds={n}")


def disable_foot_ik():
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_ControlRig):
        try:
            if "ABP_StrafeLocomotion" not in obj.get_path_name():
                continue
        except Exception:
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("alpha", 0.0)
                obj.set_editor_property(outer, node)
                log("FootIK=0")
            except Exception:
                pass


def try_inject_update_montage_play(abp):
    """
    Append to BlueprintUpdateAnimation a CallFunction Montage_Play when
    SS_WasMoving flips — simplified: expose montages; rely on SM for transitions.
    """
    # Find EventGraph and existing update event — optional enhancement
    return


def run():
    log("start")
    dump_pin_type_api()
    abp = load(ABP)
    add_vars(abp)
    set_montage_defaults(abp)
    rebind_bs()
    disable_foot_ik()

    sm, idle, loco, jumps, all_states = classify_states()
    if not sm:
        raise RuntimeError("no state machine")
    log(f"SM={sm.get_path_name()} class={sm.get_class().get_name()}")
    log(f"idle={idle['node'].get_name() if idle else None} loco={loco['node'].get_name() if loco else None}")

    # Create 4 states
    created = {}
    base_x = 500
    base_y = -100
    for i, (name, path) in enumerate(RTG.items()):
        # Skip if already exists by name
        exists = None
        for s in all_states:
            if s["node"].get_name() == name or name in s["node"].get_name():
                exists = s["node"]
                break
        node = exists or create_state(sm, name, base_x, base_y + i * 160)
        ok = ensure_sequence_in_state(node, path, loop=False)
        created[name] = node
        log(f"state {name} ready={ok}")

    # Re-classify after create
    sm2, idle2, loco2, _, _ = classify_states()
    idle = idle2 or idle
    loco = loco2 or loco

    if idle and loco:
        # Transitions
        # Prefer Run as default start (no Alt). Walk when SS_bWantsWalk — rule graph hard;
        # create both Idle->WalkStart and Idle->RunStart; user/Alt via MaxWalkSpeed in rule
        # For automatic wiring: Idle->RunStart (primary), Idle->WalkStart also.
        # Start->Loco automatic; Loco->Stop; Stop->Idle automatic.

        # Remove/repurpose direct Idle->Loco transitions by creating parallel path
        create_transition(sm, idle["node"], created["RunStart"], "Idle_to_RunStart", automatic=False)
        create_transition(sm, idle["node"], created["WalkStart"], "Idle_to_WalkStart", automatic=False)
        create_transition(sm, created["WalkStart"], loco["node"], "WalkStart_to_Loco", automatic=True)
        create_transition(sm, created["RunStart"], loco["node"], "RunStart_to_Loco", automatic=True)
        create_transition(sm, loco["node"], created["WalkStop"], "Loco_to_WalkStop", automatic=False)
        create_transition(sm, loco["node"], created["RunStop"], "Loco_to_RunStop", automatic=False)
        create_transition(sm, created["WalkStop"], idle["node"], "WalkStop_to_Idle", automatic=True)
        create_transition(sm, created["RunStop"], idle["node"], "RunStop_to_Idle", automatic=True)
    else:
        log("WARNING: idle/loco not identified — states created without full transitions")

    # Also create a Linked approach fallback: document transition conditions
    content = unreal.Paths.project_content_dir()
    guide = content + "Python/START_STOP_TRANSITION_RULES.txt"
    with open(guide, "w", encoding="utf-8") as f:
        f.write(
            "\n".join(
                [
                    "ABP_StrafeLocomotion Start/Stop transition rules (set in Transition Rule graphs):",
                    "",
                    "Idle -> WalkStart:  Speed > 15 AND (TryGetPawnOwner as Character).CharacterMovement.MaxWalkSpeed <= 300",
                    "Idle -> RunStart:   Speed > 15 AND MaxWalkSpeed > 300",
                    "WalkStart -> Locomotion: Automatic (sequence end) OR Time Remaining Ratio < 0.15",
                    "RunStart  -> Locomotion: Automatic (sequence end) OR Time Remaining Ratio < 0.15",
                    "Locomotion -> WalkStop: Speed < 10 AND MaxWalkSpeed <= 300",
                    "Locomotion -> RunStop:  Speed < 10 AND MaxWalkSpeed > 300",
                    "WalkStop -> Idle: Automatic (sequence end)",
                    "RunStop  -> Idle: Automatic (sequence end)",
                    "",
                    "Disable or raise priority of old direct Idle <-> Locomotion transitions",
                    "so Start/Stop path is preferred (or keep as fallback with lower priority).",
                    "",
                    "Montages (DefaultSlot fallback):",
                    *[f"  {k}={v}" for k, v in MONTAGES.items()],
                ]
            )
        )
    log(f"wrote {guide}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    save(ABP)

    # Character anim class
    bp = load(CHAR)
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", abp.generated_class())
    save(CHAR)

    # Verify states exist
    sm, idle, loco, _, states = classify_states()
    names = [s["node"].get_name() for s in states]
    log(f"FINAL states={names}")
    log("done")


if __name__ == "__main__":
    run()
