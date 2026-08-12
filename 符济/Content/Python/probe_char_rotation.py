# -*- coding: utf-8 -*-
"""Probe character rotation mode + TO_* snap chain."""
import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[ProbeRot] {m}")


def run():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    move = cdo.get_editor_property("character_movement")
    mesh = cdo.get_editor_property("mesh")

    log(f"use_controller_rotation_yaw={cdo.get_editor_property('use_controller_rotation_yaw')}")
    log(f"use_controller_desired_rotation={move.get_editor_property('use_controller_desired_rotation')}")
    log(f"orient_rotation_to_movement={move.get_editor_property('orient_rotation_to_movement')}")
    log(f"mesh.relative_rotation={mesh.get_editor_property('relative_rotation')}")

    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if not n.get_name().startswith("TO_"):
            continue
        log(f"node {n.get_name()}")
        for pin in (bel.list_input_pins(n) or []):
            try:
                links = list(pin.list_connected_pins() or [])
                log(
                    f"  in {pin.get_pin_name()} val={pin.get_pin_value()} "
                    f"links={len(links)}"
                )
            except Exception:
                pass
        for pin in (bel.list_output_pins(n) or []):
            try:
                links = list(pin.list_connected_pins() or [])
                log(
                    f"  out {pin.get_pin_name()} links={len(links)}"
                )
            except Exception:
                pass


if __name__ == "__main__":
    run()
