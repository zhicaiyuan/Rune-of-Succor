# -*- coding: utf-8 -*-
"""Probe turn variable graph on ABP_StrafeLocomotion."""
from __future__ import annotations
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ProbeTV] {m}")


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    cdo = unreal.get_default_object(abp.generated_class())
    for name in (
        "bWantsTurn90", "bWantsTurn180", "bTurnLeft",
        "MoveYawDelta", "AbsMoveYawDelta", "TurnAngle90", "TurnAngle180",
        "PrevMoveYaw", "bHasPrevMoveDir", "bStopInput",
    ):
        try:
            log(f"CDO {name}={cdo.get_editor_property(name)}")
        except Exception as e:
            log(f"CDO {name}: MISSING ({e})")

    # SI_SetStop then chain
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() != graph:
                continue
            if n.get_name() in ("SI_SetStop", "TV_SetT180", "TV_SetPrevYaw", "TV_SetHasPrevT", "TV_ClrAbs"):
                then = bel.find_then_pin(n)
                links = [p.get_owning_node().get_name() for p in (then.list_connected_pins() or [])]
                log(f"{n.get_name()}.then -> {links}")
        except Exception:
            pass

    # Key TV nodes and critical pins
    for name in (
        "TV_BrInput", "TV_SubYaw", "TV_NormAxis", "TV_SelDelta",
        "TV_CurrYaw", "TV_AndValid", "TV_GetHasPrev", "TV_SetPrevYaw",
        "TV_HasInput", "TV_Atan2",
    ):
        node = None
        for n in unreal.ObjectIterator(unreal.EdGraphNode):
            if n.get_outer() == graph and n.get_name() == name:
                node = n
                break
        if not node:
            log(f"MISSING {name}")
            continue
        for p in bel.list_all_pins(node) or []:
            try:
                links = []
                for lp in p.list_connected_pins() or []:
                    links.append(f"{lp.get_owning_node().get_name()}.{lp.get_pin_name()}")
                if links or str(p.get_pin_name()) in ("A", "B", "Angle", "Y", "X", "bPickA", "ReturnValue", "execute", "then"):
                    log(f"  {name}.{p.get_pin_name()} -> {links}")
            except Exception:
                pass

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")


if __name__ == "__main__":
    run()
else:
    run()
