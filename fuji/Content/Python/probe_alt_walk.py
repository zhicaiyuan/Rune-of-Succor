# -*- coding: utf-8 -*-
"""Probe current Alt/walk wiring on BP_ThirdPersonCharacter."""
from __future__ import annotations
import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
IMC = "/Game/Input/IMC_Default"
bel = unreal.BlueprintEditorLibrary


def log(m):
    unreal.log(f"[ProbeAlt] {m}")


def run():
    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    imc = unreal.EditorAssetLibrary.load_asset(IMC)
    dkm = imc.get_editor_property("default_key_mappings")
    text = dkm.export_text()
    log(f"IMC LeftAlt={'LeftAlt' in text} CapsLock={'CapsLock' in text} IA_Walk={'IA_Walk' in text}")

    ed = unreal.BlueprintGraphEditor.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    tick = None
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == graph and "Tick" in str(bel.get_node_title(n)):
            tick = n
            break
    if tick:
        then = bel.find_then_pin(tick)
        links = list(then.list_connected_pins() or [])
        log(f"Tick.then -> {[p.get_owning_node().get_name() for p in links]}")
    else:
        log("NO Tick")

    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() != graph:
                continue
            name = n.get_name()
            if name.startswith("WW_") or "bWantsWalk" in str(bel.get_node_title(n)) or "IsInputKeyDown" in str(bel.get_node_title(n)):
                pins = []
                for p in bel.list_all_pins(n) or []:
                    try:
                        pins.append(f"{p.get_pin_name()}={p.get_pin_value() if p.direction.name=='EGPD_Input' else ''} c={len(list(p.list_connected_pins() or []))}")
                    except Exception:
                        pins.append(str(p.get_pin_name()))
                log(f"NODE {name} title={bel.get_node_title(n)} | {pins[:12]}")
        except Exception:
            pass

    cdo = unreal.get_default_object(bp.generated_class())
    try:
        log(f"CDO bWantsWalk={cdo.get_editor_property('bWantsWalk')}")
    except Exception as e:
        log(f"CDO bWantsWalk: {e}")
    move = cdo.get_editor_property("character_movement")
    log(f"CDO MaxWalkSpeed={move.get_editor_property('max_walk_speed')}")


if __name__ == "__main__":
    run()
