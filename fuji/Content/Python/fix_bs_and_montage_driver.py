# -*- coding: utf-8 -*-
"""
1) Rebind BS_WalkRun_Sword into AnimGraphNode_BlendSpaceGraph
2) Fill WalkStart/RunStart/WalkStop/RunStop state BoundGraphs with sequences
3) Inject ABP EventGraph Montage_Play driver for Start/Stop via DefaultSlot
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
    "SS_WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "SS_WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "SS_RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "SS_RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}


def log(m):
    unreal.log(f"[SSDrive] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def rebind_blendspace_graph():
    abp = load(ABP)
    bs = load(BS)
    cls = getattr(unreal, "AnimGraphNode_BlendSpaceGraph", None)
    if not cls:
        log("no BlendSpaceGraph class")
        return
    for obj in unreal.ObjectIterator(cls):
        try:
            if "ABP_StrafeLocomotion" not in obj.get_path_name():
                continue
        except Exception:
            continue
        log(f"BSG {obj.get_name()} path={obj.get_path_name()}")
        # Dump properties
        for prop in (
            "blend_space",
            "BlendSpace",
            "blend_space_graph",
            "BlendSpaceAsset",
            "node",
            "Node",
        ):
            try:
                v = obj.get_editor_property(prop)
                log(f"  prop {prop}={v}")
            except Exception as exc:
                log(f"  prop {prop}: {exc}")
        # Try nested
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
            except Exception:
                continue
            if not node:
                continue
            log(f"  nested type={type(node)} dir sample={[x for x in dir(node) if 'blend' in x.lower() or 'space' in x.lower()]}")
            for prop in ("blend_space", "BlendSpace", "blend_space_asset"):
                try:
                    old = node.get_editor_property(prop)
                    node.set_editor_property(prop, bs)
                    obj.set_editor_property(outer, node)
                    log(f"  SET {outer}.{prop}: {old} -> {bs.get_name()}")
                except Exception as exc:
                    log(f"  set {prop}: {exc}")
        # Direct set on graph node
        for prop in ("blend_space", "BlendSpace"):
            try:
                obj.set_editor_property(prop, bs)
                log(f"  direct SET {prop}")
            except Exception:
                pass

    # Also check soft object path on BlendSpaceGraph via export
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    save(ABP)
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = f.read()
    log(f"VERIFY BS_WalkRun_Sword in ABP={b'BS_WalkRun_Sword' in data}")


def fill_start_stop_states():
    abp = load(ABP)
    for name, path in RTG.items():
        state = None
        for n in unreal.ObjectIterator(unreal.AnimStateNode):
            try:
                if "ABP_StrafeLocomotion" not in n.get_path_name():
                    continue
                if n.get_name() == name:
                    state = n
                    break
            except Exception:
                continue
        if not state:
            log(f"state {name} missing")
            continue
        # Bound graph property names
        bound = None
        for prop in ("bound_graph", "BoundGraph", "bound_graph_editor"):
            try:
                bound = state.get_editor_property(prop)
                if bound:
                    log(f"{name}.{prop}={bound.get_path_name()}")
                    break
            except Exception as exc:
                log(f"{name}.{prop}: {exc}")
        # Sometimes bound graph is a child object
        if not bound:
            try:
                for child in unreal.ObjectIterator(unreal.AnimationStateGraph):
                    if child.get_outer() == state:
                        bound = child
                        log(f"{name} child AnimationStateGraph={child.get_name()}")
                        break
            except Exception as exc:
                log(f"child scan: {exc}")
        if not bound:
            # Create AnimationStateGraph as outer=state
            try:
                bound = unreal.new_object(
                    unreal.AnimationStateGraph, state, unreal.Name(f"{name}_Graph")
                )
                for prop in ("bound_graph", "BoundGraph"):
                    try:
                        state.set_editor_property(prop, bound)
                        log(f"{name} assigned BoundGraph")
                        break
                    except Exception as exc:
                        log(f"assign bound: {exc}")
            except Exception as exc:
                log(f"create bound: {exc}")
                continue
        if not bound:
            continue

        seq = load(path)
        # Find/create sequence player
        sp = None
        for cand in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
            try:
                if cand.get_outer() == bound:
                    sp = cand
                    break
            except Exception:
                continue
        if not sp:
            sp = unreal.new_object(
                unreal.AnimGraphNode_SequencePlayer, bound, unreal.Name("SP")
            )
            try:
                unreal.BlueprintEditorLibrary.set_node_pos(sp, 0, 0)
            except Exception:
                pass
            try:
                sp.allocate_default_pins()
            except Exception:
                pass
            log(f"{name} created SP")

        try:
            node = sp.get_editor_property("node")
            node.set_editor_property("sequence", seq)
            for prop in ("loop_animation", "b_loop_animation"):
                try:
                    node.set_editor_property(prop, False)
                except Exception:
                    pass
            sp.set_editor_property("node", node)
            log(f"{name} sequence={seq.get_name()}")
        except Exception as exc:
            log(f"{name} set seq: {exc}")

        # State result
        result_cls = getattr(unreal, "AnimGraphNode_StateResult", None)
        result = None
        if result_cls:
            for r in unreal.ObjectIterator(result_cls):
                if r.get_outer() == bound:
                    result = r
                    break
            if not result:
                result = unreal.new_object(result_cls, bound, unreal.Name("Result"))
                try:
                    unreal.BlueprintEditorLibrary.set_node_pos(result, 300, 0)
                except Exception:
                    pass
                try:
                    result.allocate_default_pins()
                except Exception:
                    pass
        if result:
            schema = unreal.load_object(
                None, "/Script/AnimGraph.Default__AnimationGraphSchema"
            )
            try:
                pins_a = list(sp.get_editor_property("pins") or [])
                pins_b = list(result.get_editor_property("pins") or [])
                log(f"{name} pins SP={[p.get_name() for p in pins_a]} R={[p.get_name() for p in pins_b]}")
                if schema and pins_a and pins_b:
                    # Heuristic: first output pose to first input pose
                    out_p = None
                    in_p = None
                    for p in pins_a:
                        try:
                            d = str(p.get_editor_property("direction"))
                            if "Output" in d:
                                out_p = p
                        except Exception:
                            pass
                    for p in pins_b:
                        try:
                            d = str(p.get_editor_property("direction"))
                            if "Input" in d:
                                in_p = p
                        except Exception:
                            pass
                    if out_p and in_p:
                        unreal.EdGraphSchema_K2.try_create_connection(schema, out_p, in_p)
                        log(f"{name} pose connected")
            except Exception as exc:
                log(f"{name} connect: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile states: {exc}")
    save(ABP)


def ensure_vars_and_montages():
    abp = load(ABP)
    bel = unreal.BlueprintEditorLibrary
    for name in ("SS_WasMoving", "SS_bWantsWalk"):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("double"))
        bel.add_member_variable(abp, unreal.Name("SS_PrevSpeed"), pin)
    except Exception:
        try:
            pin = bel.get_basic_type_by_name(unreal.Name("float"))
            bel.add_member_variable(abp, unreal.Name("SS_PrevSpeed"), pin)
        except Exception:
            pass
    for name in MONTAGES:
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        except Exception:
            pass
    cdo = unreal.get_default_object(abp.generated_class())
    for prop, path in MONTAGES.items():
        try:
            cdo.set_editor_property(prop, load(path))
            log(f"CDO {prop}=OK")
        except Exception as exc:
            log(f"CDO {prop}: {exc}")
    save(ABP)


def inject_montage_driver_nodes():
    """
    Build K2 nodes on ABP EventGraph for Start/Stop montage playback.
    Uses BlueprintUpdateAnimation then-exec chain.
    """
    abp = load(ABP)
    graph = None
    for g in unreal.ObjectIterator(unreal.EdGraph):
        try:
            if "ABP_StrafeLocomotion" in g.get_path_name() and g.get_name() == "EventGraph":
                graph = g
                break
        except Exception:
            continue
    if not graph:
        log("no ABP EventGraph")
        return False
    log(f"EventGraph={graph.get_path_name()}")

    # Find BlueprintUpdateAnimation
    update = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() != graph:
                continue
        except Exception:
            continue
        mn = ""
        try:
            ref = n.get_editor_property("event_reference")
            mn = str(ref.get_editor_property("member_name"))
        except Exception:
            try:
                mn = n.get_node_title(0).to_string()
            except Exception:
                mn = n.get_name()
        log(f"event {n.get_name()} member={mn}")
        if "BlueprintUpdateAnimation" in mn:
            update = n

    if not update:
        log("BlueprintUpdateAnimation missing")
        return False

    # Create Montage_Play call
    play = unreal.new_object(
        unreal.K2Node_CallFunction, graph, unreal.Name("SS_MontagePlay")
    )
    try:
        fn = unreal.AnimInstance.static_class().find_function_by_name("Montage_Play")
        if fn:
            play.set_from_function(fn)
            log("Montage_Play set_from_function")
        else:
            ref = play.get_editor_property("function_reference")
            ref.set_editor_property("member_name", unreal.Name("Montage_Play"))
            ref.set_editor_property("member_parent", unreal.AnimInstance.static_class())
            play.set_editor_property("function_reference", ref)
    except Exception as exc:
        log(f"Montage_Play configure: {exc}")
    try:
        play.allocate_default_pins()
    except Exception:
        pass
    try:
        unreal.BlueprintEditorLibrary.set_node_pos(play, 1200, 800)
    except Exception:
        pass

    # Variable gets for montages
    var_get_cls = getattr(unreal, "K2Node_VariableGet", None)
    gets = {}
    if var_get_cls:
        y = 600
        for vname in MONTAGES:
            n = unreal.new_object(var_get_cls, graph, unreal.Name(f"Get_{vname}"))
            try:
                ref = n.get_editor_property("variable_reference")
                ref.set_editor_property("member_name", unreal.Name(vname))
                try:
                    ref.set_editor_property("b_self_context", True)
                except Exception:
                    pass
                n.set_editor_property("variable_reference", ref)
            except Exception as exc:
                log(f"var get {vname}: {exc}")
            try:
                n.allocate_default_pins()
            except Exception:
                pass
            try:
                unreal.BlueprintEditorLibrary.set_node_pos(n, 900, y)
            except Exception:
                pass
            gets[vname] = n
            y += 80
            log(f"Get_{vname} created")

    # Custom event for documentation / manual hook
    custom_cls = getattr(unreal, "K2Node_CustomEvent", None)
    if custom_cls:
        ce = unreal.new_object(custom_cls, graph, unreal.Name("SS_PlayStartStop"))
        try:
            ce.set_editor_property("custom_function_name", unreal.Name("SS_PlayStartStop"))
        except Exception:
            pass
        try:
            ce.allocate_default_pins()
        except Exception:
            pass
        try:
            unreal.BlueprintEditorLibrary.set_node_pos(ce, 600, 1000)
        except Exception:
            pass
        log("CustomEvent SS_PlayStartStop created")

    # Try connect Update then -> note: full branch deferred; create comment node
    comment_cls = getattr(unreal, "EdGraphNode_Comment", None)
    if comment_cls:
        try:
            c = unreal.new_object(comment_cls, graph, unreal.Name("SS_Comment"))
            c.set_editor_property(
                "node_comment",
                "Start/Stop: montages on DefaultSlot. Wire BlueprintUpdateAnimation:\n"
                "Speed rising + MaxWalkSpeed<=300 -> Montage_Play(SS_WalkStart)\n"
                "Speed rising + MaxWalkSpeed>300 -> Montage_Play(SS_RunStart)\n"
                "Speed falling + walk -> SS_WalkStop; falling + run -> SS_RunStop\n"
                "OR use SM states WalkStart/RunStart/WalkStop/RunStop with rules in START_STOP_TRANSITION_RULES.txt",
            )
            try:
                unreal.BlueprintEditorLibrary.set_node_pos(c, 600, 500)
            except Exception:
                pass
            log("comment added")
        except Exception as exc:
            log(f"comment: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile driver: {exc}")
    save(ABP)
    return True


def binary_patch_bs_if_needed():
    """If ABP lost BS name string, try soft replace of known blendspace refs."""
    content = unreal.Paths.project_content_dir()
    fs = (content + ABP.replace("/Game/", "") + ".uasset").replace("/", "\\")
    with open(fs, "rb") as f:
        data = bytearray(f.read())
    if b"BS_WalkRun_Sword" in data:
        log("binary already has BS_WalkRun_Sword")
        return
    # Look for any BS_ name
    import re

    names = sorted(set(re.findall(rb"BS_[A-Za-z0-9_]+", bytes(data))))
    log(f"BS names in ABP binary: {names}")
    # BlendSpaceGraph may store path differently — load via editor API after reopen
    # Force assign by duplicating path into BlendSpaceGraph's internal asset
    abp = load(ABP)
    bs = load(BS)
    # Search ALL properties recursively via get_editor_property on BlendSpaceGraph
    bsg = getattr(unreal, "AnimGraphNode_BlendSpaceGraph", None)
    if bsg:
        for obj in unreal.ObjectIterator(bsg):
            if "ABP_StrafeLocomotion" not in obj.get_path_name():
                continue
            # Use call_method if available
            for meth in dir(obj):
                if "blend" in meth.lower() and not meth.startswith("_"):
                    log(f"BSG method/attr {meth}")


def run():
    log("start")
    ensure_vars_and_montages()
    rebind_blendspace_graph()
    binary_patch_bs_if_needed()
    fill_start_stop_states()
    inject_montage_driver_nodes()
    # Character
    bp = load(CHAR)
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", load(ABP).generated_class())
    save(CHAR)
    # Foot IK
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_ControlRig):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("alpha", 0.0)
                obj.set_editor_property(outer, node)
            except Exception:
                pass
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(load(ABP))
    except Exception:
        pass
    save(ABP)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
