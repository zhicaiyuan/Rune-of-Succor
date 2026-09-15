# -*- coding: utf-8 -*-
"""Force-remove leftover duplicate BlueprintUpdateAnimation nodes."""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ForceDup] {m}")


def is_update(n):
    try:
        return "BlueprintUpdateAnimation" in str(bel.get_node_title(n)).replace(" ", "")
    except Exception:
        return False


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    updates = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and is_update(n):
                updates.append(n)
                log(f"found {n.get_name()} title={bel.get_node_title(n)}")
        except Exception:
            pass

    keep = None
    for u in updates:
        if u.get_name() == "K2Node_Event_0":
            keep = u
            break
    if keep is None and updates:
        keep = updates[0]

    drop = [u for u in updates if u != keep]
    log(f"keep={keep.get_name() if keep else None} drop={[d.get_name() for d in drop]}")

    for u in drop:
        try:
            bel.find_then_pin(u).break_all_pin_links() if hasattr(bel.find_then_pin(u), "break_all_pin_links") else bel.find_then_pin(u).break_pin_links()
        except Exception:
            pass

    if drop:
        try:
            ed.remove_nodes(drop)
            log("remove_nodes OK")
        except Exception as e:
            log(f"remove_nodes: {e}")
        for u in drop:
            for meth in ("destroy", "mark_as_garbage", "remove_from_root"):
                if hasattr(u, meth):
                    try:
                        getattr(u, meth)()
                    except Exception:
                        pass
            try:
                if hasattr(graph, "remove_node"):
                    graph.remove_node(u)
                    log(f"graph.remove_node {u.get_name()}")
            except Exception as e:
                log(f"graph.remove_node: {e}")

    # Also kill any node named DUP_UPDATE*
    extra = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and (
                n.get_name().startswith("DUP_UPDATE") or (is_update(n) and n != keep)
            ):
                extra.append(n)
        except Exception:
            pass
    if extra:
        try:
            ed.remove_nodes(extra)
            log(f"extra removed {len(extra)}")
        except Exception as e:
            log(f"extra: {e}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")

    left = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and is_update(n):
                left.append(n.get_name())
        except Exception:
            pass
    log(f"final Update count={len(left)} {left}")

    # Check SI_SetStop still on keep
    if keep:
        then = bel.find_then_pin(keep)
        linked = []
        for p in then.list_connected_pins() or []:
            try:
                linked.append(p.get_owning_node().get_name())
            except Exception:
                pass
        log(f"keep.then -> {linked}")

    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
