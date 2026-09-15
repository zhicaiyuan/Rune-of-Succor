# -*- coding: utf-8 -*-
"""Dump current run-pivot / turn wiring from ABP + character."""
from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
BS = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/MoveTurnBlendSpace"
bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log(f"[PivotProbe] {m}")


def under(obj, root, depth=16):
    o = obj
    for _ in range(depth):
        if o == root:
            return True
        try:
            o = o.get_outer()
        except Exception:
            return False
        if o is None:
            return False
    return False


def pin_name(p):
    try:
        return str(p.get_pin_name())
    except Exception:
        return "?"


def dump_bs():
    bs = unreal.EditorAssetLibrary.load_asset(BS)
    if not bs:
        log("NO blendspace")
        return
    log(f"BS class={bs.get_class().get_name()} path={bs.get_path_name()}")
    try:
        sk = bs.get_editor_property("skeleton")
        log(f"BS skeleton={sk.get_path_name() if sk else None}")
    except Exception as e:
        log(f"BS skeleton err {e}")
    for prop in ("blend_parameters", "BlendParameters", "axis_to_scale", "sample_data", "SampleData"):
        try:
            v = bs.get_editor_property(prop)
            log(f"BS.{prop}={v}")
        except Exception as e:
            log(f"BS.{prop} err {e}")
    try:
        params = bs.get_editor_property("blend_parameters")
        for i, p in enumerate(params or []):
            try:
                log(
                    f"AXIS[{i}] name={p.get_editor_property('display_name')} "
                    f"min={p.get_editor_property('min')} max={p.get_editor_property('max')} "
                    f"grid={p.get_editor_property('grid_num')}"
                )
            except Exception:
                try:
                    log(f"AXIS[{i}] {p} display={getattr(p,'display_name',None)} min={getattr(p,'min',None)} max={getattr(p,'max',None)}")
                except Exception as e:
                    log(f"AXIS[{i}] err {e}")
    except Exception as e:
        log(f"params loop {e}")
    try:
        samples = bs.get_editor_property("sample_data")
        for i, s in enumerate(samples or []):
            anim = None
            val = None
            try:
                anim = s.get_editor_property("animation")
            except Exception:
                try:
                    anim = s.get_editor_property("Animation")
                except Exception:
                    pass
            try:
                val = s.get_editor_property("sample_value")
            except Exception:
                try:
                    val = s.get_editor_property("SampleValue")
                except Exception:
                    pass
            ap = anim.get_path_name() if anim else None
            log(f"SAMPLE[{i}] anim={ap} value={val}")
    except Exception as e:
        log(f"samples {e}")


def dump_abp():
    bp = unreal.EditorAssetLibrary.load_asset(ABP)
    log(f"ABP={bp}")
    try:
        sk = bp.get_editor_property("target_skeleton")
        log(f"ABP skeleton={sk.get_path_name() if sk else None}")
    except Exception as e:
        log(f"ABP skel {e}")

    # CDO vars
    try:
        cdo = unreal.get_default_object(bp.generated_class())
        for prop in (
            "bWantsTurn90", "bWantsTurn180", "bTurnLeft", "bTurnYawLocked", "bInTurnAnim",
            "TurnAngle90", "TurnAngle180", "MoveYawDelta", "AbsMoveYawDelta",
            "ActorYaw", "InputYaw", "GroundSpeed", "bHasMoveInput",
        ):
            try:
                log(f"CDO {prop}={cdo.get_editor_property(prop)}")
            except Exception as e:
                log(f"CDO {prop}: {e}")
    except Exception as e:
        log(f"cdo {e}")

    # states
    for n in unreal.ObjectIterator(unreal.AnimStateNode):
        if not under(n, bp):
            continue
        g = None
        try:
            g = n.get_editor_property("bound_graph")
        except Exception:
            pass
        gname = g.get_name() if g else "?"
        outer = n.get_outer().get_name() if n.get_outer() else "?"
        if any(k in (gname + outer).lower() for k in ("turn", "trun", "run", "walk", "loco", "pivot")):
            log(f"STATE outer={outer} bound={gname} node={n.get_name()}")

    # sequence / blendspace players in turn-like graphs
    for n in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
        if not under(n, bp):
            continue
        gname = n.get_outer().get_name()
        if not any(k in gname.lower() for k in ("turn", "trun", "pivot", "runturn")):
            continue
        seq = None
        try:
            seq = n.get_editor_property("node").get_editor_property("sequence")
        except Exception:
            pass
        log(f"SEQPLAYER graph={gname} seq={seq.get_path_name() if seq else None}")

    for cls_name in ("AnimGraphNode_BlendSpacePlayer", "AnimGraphNode_BlendSpaceGraph"):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        for n in unreal.ObjectIterator(cls):
            if not under(n, bp):
                continue
            gname = n.get_outer().get_name()
            title = ""
            try:
                title = str(bel.get_node_title(n))
            except Exception:
                title = n.get_name()
            bs = None
            try:
                node = n.get_editor_property("node")
                for p in ("blend_space", "BlendSpace", "blendspace_asset"):
                    try:
                        bs = node.get_editor_property(p)
                        if bs:
                            break
                    except Exception:
                        pass
            except Exception:
                pass
            pins = []
            try:
                for p in n.get_all_pins():
                    links = []
                    try:
                        links = [f"{lnk.get_owning_node().get_name()}.{pin_name(lnk)}" for lnk in (p.get_linked_to() or [])]
                    except Exception:
                        pass
                    pins.append(f"{pin_name(p)}->{links}")
            except Exception as e:
                pins = [str(e)]
            log(f"{cls_name} graph={gname} title={title} bs={bs.get_path_name() if bs else None} pins={pins}")

    # EventGraph nodes related to accel / yaw / foot
    interesting_fn = (
        "GetCurrentAcceleration", "GetVelocity", "Dot_VectorVector", "Cross_VectorVector",
        "DegAtan2", "NormalizeAxis", "GetPendingMovementInputVector", "GetLastMovementInputVector",
        "GetSocketLocation", "VSizeXY",
    )
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        if not under(n, bp):
            continue
        fn = ""
        try:
            fn = str(n.get_editor_property("function_reference").member_name)
        except Exception:
            try:
                fn = str(bel.get_node_title(n))
            except Exception:
                fn = n.get_name()
        if not any(k.lower() in (fn + n.get_name()).lower() for k in interesting_fn + ("TV_", "accel", "foot", "turn")):
            continue
        pins = []
        try:
            for p in n.get_all_pins():
                links = []
                try:
                    links = [f"{lnk.get_owning_node().get_name()}.{pin_name(lnk)}" for lnk in (p.get_linked_to() or [])]
                except Exception:
                    pass
                val = ""
                try:
                    val = p.get_default_as_string()
                except Exception:
                    try:
                        val = p.get_pin_value()
                    except Exception:
                        val = ""
                if links or (val and val not in ("", "None", "0", "0.0")):
                    pins.append(f"{pin_name(p)} val={val} links={links}")
        except Exception as e:
            pins = [str(e)]
        log(f"CALL {n.get_name()} fn={fn} outer={n.get_outer().get_name()} pins={pins}")

    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if not under(n, bp):
            continue
        vn = n.get_name()
        try:
            vn = str(n.get_editor_property("variable_reference").member_name)
        except Exception:
            pass
        if not any(k.lower() in str(vn).lower() for k in ("turn", "yaw", "left", "foot", "accel", "delta")):
            continue
        pins = []
        try:
            for p in n.get_all_pins():
                links = []
                try:
                    links = [f"{lnk.get_owning_node().get_name()}.{pin_name(lnk)}" for lnk in (p.get_linked_to() or [])]
                except Exception:
                    pass
                if links:
                    pins.append(f"{pin_name(p)}->{links}")
        except Exception:
            pass
        log(f"SET {n.get_name()} var={vn} outer={n.get_outer().get_name()} {pins}")

    # transitions mentioning turn
    for n in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
        if not under(n, bp):
            continue
        bound = None
        try:
            bound = n.get_editor_property("bound_graph")
        except Exception:
            pass
        vars_used = []
        if bound:
            for gn in unreal.ObjectIterator(unreal.K2Node_VariableGet):
                if gn.get_outer() != bound and not under(gn, bound, 6):
                    continue
                try:
                    vn = str(gn.get_editor_property("variable_reference").member_name)
                except Exception:
                    vn = "?"
                if vn not in vars_used:
                    vars_used.append(vn)
        auto = prio = None
        try:
            auto = n.get_editor_property("bAutomaticRuleBasedOnSequencePlayerInState")
        except Exception:
            pass
        try:
            prio = n.get_editor_property("priority_order")
        except Exception:
            try:
                prio = n.get_editor_property("TransitionPriorityOrder")
            except Exception:
                pass
        title = ""
        try:
            title = str(bel.get_node_title(n))
        except Exception:
            title = n.get_name()
        if vars_used or "turn" in title.lower() or "trun" in title.lower():
            log(f"TRANS {n.get_name()} title={title} auto={auto} prio={prio} vars={vars_used} outer={n.get_outer().get_name()}")


def dump_char():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    log(f"CHAR={bp}")
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        if not under(n, bp):
            continue
        fn = n.get_name()
        try:
            fn = str(n.get_editor_property("function_reference").member_name)
        except Exception:
            pass
        if not any(k.lower() in (fn + n.get_name()).lower() for k in (
            "SetActorRotation", "Orient", "DegAtan2", "MakeRotator", "Add_Double",
            "NormalizeAxis", "GetPending", "GetLastMovement", "SetBoolProperty",
        )):
            continue
        pins = []
        try:
            for p in n.get_all_pins():
                links = []
                try:
                    links = [f"{lnk.get_owning_node().get_name()}.{pin_name(lnk)}" for lnk in (p.get_linked_to() or [])]
                except Exception:
                    pass
                val = ""
                try:
                    val = p.get_default_as_string()
                except Exception:
                    val = ""
                if links or (val and val not in ("", "None")):
                    pins.append(f"{pin_name(p)} val={val} links={links}")
        except Exception as e:
            pins = [str(e)]
        log(f"CHARCALL {n.get_name()} fn={fn} {pins}")

    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if not under(n, bp):
            continue
        vn = n.get_name()
        try:
            vn = str(n.get_editor_property("variable_reference").member_name)
        except Exception:
            pass
        if not any(k.lower() in str(vn).lower() for k in ("yaw", "turn", "orient", "lock")):
            continue
        pins = []
        try:
            for p in n.get_all_pins():
                links = []
                try:
                    links = [f"{lnk.get_owning_node().get_name()}.{pin_name(lnk)}" for lnk in (p.get_linked_to() or [])]
                except Exception:
                    pass
                if links:
                    pins.append(f"{pin_name(p)}->{links}")
        except Exception:
            pass
        log(f"CHARSET {n.get_name()} var={vn} {pins}")


def run():
    log("start")
    dump_bs()
    dump_abp()
    dump_char()
    log("done")


if __name__ == "__main__":
    run()
