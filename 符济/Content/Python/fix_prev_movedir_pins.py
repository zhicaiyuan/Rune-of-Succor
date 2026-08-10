# -*- coding: utf-8 -*-
from __future__ import annotations
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixPrev] {m}")


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    nodes = {}
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() == graph and n.get_name().startswith("TV_"):
                nodes[n.get_name()] = n
        except Exception:
            pass
    log(f"TV nodes: {sorted(nodes)}")

    normal = nodes.get("TV_Normal")
    make_flat = nodes.get("TV_MakeFlat")
    zero_v = nodes.get("TV_ZeroV")
    set_prev = nodes.get("TV_SetPrevCurr")
    set_zero = nodes.get("TV_SetPrevZero")

    def try_link(src_node, dst_node, dst_pin_name):
        if not src_node or not dst_node:
            log("missing node")
            return False
        src = None
        for p in bel.list_output_pins(src_node) or []:
            if str(p.get_pin_name()) == "ReturnValue":
                src = p
                break
        if not src:
            outs = bel.list_output_pins(src_node) or []
            src = outs[0] if outs else None
        dst = None
        for p in bel.list_input_pins(dst_node) or []:
            if str(p.get_pin_name()) == dst_pin_name:
                dst = p
                break
        log(f"src={src_node.get_name()}:{src.get_pin_name() if src else None} "
            f"type={src.pin_type if src and hasattr(src,'pin_type') else '?'}")
        log(f"dst={dst_node.get_name()}:{dst.get_pin_name() if dst else None} "
            f"type={dst.pin_type if dst and hasattr(dst,'pin_type') else '?'}")
        try:
            if src and hasattr(src, "get_pin_type_sub_category_object"):
                log(f"src sub={src.get_pin_type_sub_category_object()}")
        except Exception:
            pass
        # try all methods
        for label, fn in (
            ("src.try(dst)", lambda: src.try_create_connection(dst)),
            ("dst.try(src)", lambda: dst.try_create_connection(src)),
            ("bel.connect?", None),
        ):
            if fn is None:
                continue
            try:
                ok = bool(fn())
                log(f"  {label}: {ok}")
                if ok:
                    return True
            except Exception as e:
                log(f"  {label}: {e}")
        # make_compatible?
        try:
            ok = bool(src.make_link_to(dst))
            log(f"  make_link_to: {ok}")
            if ok:
                return True
        except Exception as e:
            log(f"  make_link_to: {e}")
        return False

    # Prefer MakeFlat (vector) if Normal type mismatches
    ok1 = try_link(normal, set_prev, "PrevMoveDir")
    if not ok1:
        ok1 = try_link(make_flat, set_prev, "PrevMoveDir")
    ok2 = try_link(zero_v, set_zero, "PrevMoveDir")
    log(f"result curr={ok1} zero={ok2}")

    # Verify chain SI -> Br and OldSeq inputs
    si = None
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        if n.get_outer() == graph and n.get_name() == "SI_SetStop":
            si = n
            break
    if si:
        then = bel.find_then_pin(si)
        log(f"SI.then -> {[p.get_owning_node().get_name() for p in (then.list_connected_pins() or [])]}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)


if __name__ == "__main__":
    run()
else:
    run()
