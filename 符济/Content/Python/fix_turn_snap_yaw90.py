# -*- coding: utf-8 -*-
"""
Fix fixed +90° facing after turn snap (Mesh Relative Yaw often -90).

Patches BP_ThirdPersonCharacter EventGraph TO_* chain:
  InputYaw = DegAtan2(move) + SNAP_YAW_OFFSET (+90 default)
  then NormalizeAxis before MakeRotator -> SetActorRotation

If still wrong, set SNAP_YAW_OFFSET = -90.0 and re-run.
"""
from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
SNAP_YAW_OFFSET = 0.0

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[SnapYaw90] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(p)
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


def find_in_graph(graph, prefix):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if n.get_name().startswith(prefix):
            return n
    return None


def run():
    bp = load(CHAR)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    atan = find_in_graph(graph, "TO_Atan")
    make_rot = find_in_graph(graph, "TO_MakeRot")
    if not atan or not make_rot:
        raise RuntimeError("TO_Atan / TO_MakeRot not found — run setup_turn_runpivot.py first")

    # Remove old offset nodes if re-run
    kill = []
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        if n.get_outer() != graph:
            continue
        if n.get_name().startswith("TO_Off"):
            kill.append(n)
    if kill:
        ed.remove_nodes(kill)
        log(f"removed {len(kill)} old offset nodes")

    # Break atan -> make_rot Y
    y_in = pin_in(make_rot, "Y")
    if y_in:
        try:
            y_in.break_pin_links()
        except Exception:
            pass

    add = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_DoubleDouble")
    if not add:
        add = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:Add_FloatFloat")
    add.rename("TO_OffAdd")
    pos(add, 1780, 1360)
    set_val(add, "B", str(SNAP_YAW_OFFSET))

    norm = ed.add_call_function_node("/Script/Engine.KismetMathLibrary:NormalizeAxis")
    norm.rename("TO_OffNorm")
    pos(norm, 1960, 1360)

    ok1 = connect(pin_out(atan, "ReturnValue"), pin_in(add, "A"))
    ok2 = connect(pin_out(add, "ReturnValue"), pin_in(norm, "Angle") or pin_in(norm, "A"))
    ok3 = connect(pin_out(norm, "ReturnValue"), pin_in(make_rot, "Y"))
    log(f"wired atan+{SNAP_YAW_OFFSET} norm->make_rot Y: {ok1}/{ok2}/{ok3}")

    try:
        bel.compile_blueprint(bp)
    except Exception as e:
        log(f"compile: {e}")
    save(CHAR)
    log(f"DONE — snap yaw offset = {SNAP_YAW_OFFSET:+.0f}. If still wrong, set SNAP_YAW_OFFSET=-90 and re-run.")


if __name__ == "__main__":
    run()
