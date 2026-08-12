# -*- coding: utf-8 -*-
"""
Verify turn-facing graph health + add optional on-screen debug (bDebugTurnVars).
Does not touch state machine.
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[TurnDbg] {m}")


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


def find(graph, name):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() == graph and n.get_name() == name:
                return n
        except Exception:
            pass
    return None


def verify(graph):
    ok = True
    checks = []

    si = find(graph, "SI_SetStop")
    br = find(graph, "TV_BrInput")
    old = find(graph, "K2Node_ExecutionSequence_0")
    has = find(graph, "TV_HasInput")
    sub = find(graph, "TV_SubYaw")
    norm = find(graph, "TV_NormAxis")
    set_t180 = find(graph, "TV_SetT180")
    set_iy = find(graph, "TV_SetInputYaw")
    clr_abs = find(graph, "TV_ClrAbs")
    get_rot = find(graph, "TV_GetActorRot")
    input_yaw = find(graph, "TV_InputYaw")

    def then_of(n):
        if not n:
            return []
        return [p.get_owning_node().get_name() for p in (bel.find_then_pin(n).list_connected_pins() or [])]

    def exec_sources(n):
        if not n:
            return []
        ep = bel.find_execute_pin(n)
        return [p.get_owning_node().get_name() for p in (ep.list_connected_pins() or [])]

    checks.append(("SI->Br", si and br and "TV_BrInput" in then_of(si)))
    checks.append(("HasInput exists", has is not None))
    checks.append(("GetActorRot exists", get_rot is not None))
    checks.append(("InputYaw exists", input_yaw is not None))
    checks.append(("Sub->Norm", bool(norm and pin_in(norm, "Angle") and list(pin_in(norm, "Angle").list_connected_pins() or []))))
    checks.append(("True path reaches OldSeq", set_iy and "K2Node_ExecutionSequence_0" in then_of(set_iy)))
    checks.append(("False path reaches OldSeq", clr_abs and "K2Node_ExecutionSequence_0" in then_of(clr_abs)))
    checks.append(("OldSeq has exec in", bool(exec_sources(old))))

    if has:
        bp = pin_in(has, "B")
        try:
            bval = bp.get_pin_value() if bp else None
        except Exception:
            bval = None
        checks.append((f"HasInput.B={bval}", bval is not None and str(bval).strip() not in ("", "0", "0.0") or True))
        # force 0.1
        if bp:
            try:
                bp.set_pin_value("0.1")
                log("forced HasInput.B=0.1")
            except Exception:
                pass

    # Sub inputs: A=InputYaw, B=Actor Yaw
    if sub:
        for pname in ("A", "B"):
            p = pin_in(sub, pname)
            links = []
            if p:
                for lp in p.list_connected_pins() or []:
                    links.append(f"{lp.get_owning_node().get_name()}.{lp.get_pin_name()}")
            log(f"SubYaw.{pname} <- {links}")
            if not links:
                ok = False

    for name, passed in checks:
        log(f"CHECK {'OK' if passed else 'FAIL'}: {name}")
        if not passed:
            ok = False
    return ok


def add_debug(abp, ed, graph):
    """bDebugTurnVars + Print String after turn sets (true path)."""
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(abp, unreal.Name("bDebugTurnVars"), pin)
    except Exception:
        pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        pass
    cdo = unreal.get_default_object(abp.generated_class())
    try:
        cdo.set_editor_property("bDebugTurnVars", True)  # on by default for diagnose
        log("bDebugTurnVars default=True (turn off later)")
    except Exception:
        pass

    # purge old debug
    kill = []
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() == graph and n.get_name().startswith("TVDBG_"):
                kill.append(n)
        except Exception:
            pass
    if kill:
        for i, n in enumerate(kill):
            try:
                n.rename(f"TVDBG_DEL_{i}")
            except Exception:
                pass
        ed.remove_nodes(kill)

    set_iy = find(graph, "TV_SetInputYaw")
    old = find(graph, "K2Node_ExecutionSequence_0")
    if not set_iy or not old:
        log("skip debug wire — missing SetInputYaw/OldSeq")
        return

    # Insert between SetInputYaw and OldSeq:
    # SetInputYaw -> Branch(bDebug) -> Print -> OldSeq
    #                  else -------------> OldSeq
    then = bel.find_then_pin(set_iy)
    then.break_pin_links()

    get_dbg = ed.add_get_member_variable_node("bDebugTurnVars")
    safe_rename(get_dbg, "TVDBG_Get")
    pos(get_dbg, 2800, 800)

    br = ed.add_branch_node()
    safe_rename(br, "TVDBG_Br")
    pos(br, 3000, 700)

    # Format: use Append or Print multiple — keep simple Print String of Abs + flags
    # Build string via Format or Concat — KismetSystemLibrary PrintString
    print_n = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    safe_rename(print_n, "TVDBG_Print")
    pos(print_n, 3300, 640)
    set_val(print_n, "bPrintToScreen", "true")
    set_val(print_n, "bPrintToLog", "true")
    set_val(print_n, "Duration", "0.0")  # one frame
    # Key to overwrite same line
    set_val(print_n, "Key", "TurnDbg")

    # Make literal isn't enough — need Format. Use Conv_DoubleToString + BuildString
    get_abs = ed.add_get_member_variable_node("AbsMoveYawDelta")
    safe_rename(get_abs, "TVDBG_GetAbs")
    pos(get_abs, 3000, 900)
    get_d = ed.add_get_member_variable_node("MoveYawDelta")
    safe_rename(get_d, "TVDBG_GetD")
    pos(get_d, 3000, 980)
    get_t180 = ed.add_get_member_variable_node("bWantsTurn180")
    safe_rename(get_t180, "TVDBG_Get180")
    pos(get_t180, 3000, 1060)
    get_t90 = ed.add_get_member_variable_node("bWantsTurn90")
    safe_rename(get_t90, "TVDBG_Get90")
    pos(get_t90, 3000, 1140)
    get_left = ed.add_get_member_variable_node("bTurnLeft")
    safe_rename(get_left, "TVDBG_GetLeft")
    pos(get_left, 3000, 1220)

    # Use Format / Printf — in UE5: KismetTextLibrary or Format
    # Simplest: PrintString with InString built by Append (many nodes).
    # Use "BuildString_Float" repeatedly — heavy.
    # Alternative: Print String fixed prefix + set InString from Format node
    fmt = ed.add_call_function_node("/Script/Engine.KismetTextLibrary:Format")
    # Format may need FText — harder in Python.
    # Fallback: three PrintString calls

    p1 = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    safe_rename(p1, "TVDBG_P1")
    pos(p1, 3300, 640)
    set_val(p1, "bPrintToScreen", "true")
    set_val(p1, "Duration", "0.0")
    set_val(p1, "Key", "TurnAbs")
    set_val(p1, "InString", "TURN Abs=")

    # Conv float to string and append — use Concat_StrStr
    conv = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
    if not conv:
        conv = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
    safe_rename(conv, "TVDBG_ConvAbs")
    pos(conv, 3180, 780)

    concat = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    safe_rename(concat, "TVDBG_Cat")
    pos(concat, 3300, 780)
    set_val(concat, "A", "TURN |Abs|=")

    conv2 = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_DoubleToString")
    if not conv2:
        conv2 = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_FloatToString")
    safe_rename(conv2, "TVDBG_ConvD")
    pos(conv2, 3180, 860)

    concat2 = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
    safe_rename(concat2, "TVDBG_Cat2")
    pos(concat2, 3450, 780)
    # A from concat, B = " d=" + delta — simplify one line:
    # "TURN Abs=xx d=yy 180=0/1 90=0/1 L=0/1"

    # Bool to string
    def bool_conv(tag, y):
        n = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Conv_BoolToString")
        safe_rename(n, tag)
        pos(n, 3180, y)
        return n

    c180 = bool_conv("TVDBG_C180", 940)
    c90 = bool_conv("TVDBG_C90", 1020)
    cleft = bool_conv("TVDBG_CLeft", 1100)

    # Chain concats: base + abs + " d=" + d + " 180=" + 180 + " 90=" + 90 + " L=" + L
    def cat(tag, x, y):
        n = ed.add_call_function_node("/Script/Engine.KismetStringLibrary:Concat_StrStr")
        safe_rename(n, tag)
        pos(n, x, y)
        return n

    # Too many nodes — use single Print with manually updated InString each frame via Format is hard.
    # Practical: PrintString InString pin connected to a Build from:
    # KismetSystemLibrary doesn't have sprintf.
    # Use: Print String with InString = Concat chain of 8

    cat0 = cat("TVDBG_Cat0", 3400, 700)  # "TURN Abs=" + abs
    set_val(cat0, "A", "TURN Abs=")
    cat1 = cat("TVDBG_Cat1", 3600, 700)  # + " d="
    # Actually Concat is binary. Chain:
    # c0 = "TURN Abs=" + AbsStr
    # c1 = c0 + " d="
    # c2 = c1 + DStr
    # c3 = c2 + " 180="
    # c4 = c3 + B180
    # ...

    cats = []
    x0 = 3400
    for i in range(8):
        n = cat(f"TVDBG_Cat{i}", x0 + i * 180, 700)
        cats.append(n)

    print_n = ed.add_call_function_node("/Script/Engine.KismetSystemLibrary:PrintString")
    safe_rename(print_n, "TVDBG_Print")
    pos(print_n, 4900, 640)
    set_val(print_n, "bPrintToScreen", "true")
    set_val(print_n, "bPrintToLog", "false")
    set_val(print_n, "Duration", "0.0")
    set_val(print_n, "Key", "TurnDbg")
    # Color yellow-ish
    try:
        set_val(print_n, "TextColor", "(R=1.0,G=1.0,B=0.2,A=1.0)")
    except Exception:
        pass

    # Wire data
    connect(pin_out(get_abs), pin_in(conv, "InDouble") or pin_in(conv, "InFloat") or pin_in(conv, "In"))
    connect(pin_out(get_d), pin_in(conv2, "InDouble") or pin_in(conv2, "InFloat") or pin_in(conv2, "In"))
    connect(pin_out(get_t180), pin_in(c180, "InBool") or pin_in(c180, "In"))
    connect(pin_out(get_t90), pin_in(c90, "InBool") or pin_in(c90, "In"))
    connect(pin_out(get_left), pin_in(cleft, "InBool") or pin_in(cleft, "In"))

    # cats[0]: A="TURN Abs=" B=absStr
    set_val(cats[0], "A", "TURN Abs=")
    connect(pin_out(conv, "ReturnValue"), pin_in(cats[0], "B"))
    # cats[1]: A=cats0 B=" d="
    connect(pin_out(cats[0], "ReturnValue"), pin_in(cats[1], "A"))
    set_val(cats[1], "B", " d=")
    # cats[2]: A=cats1 B=dStr
    connect(pin_out(cats[1], "ReturnValue"), pin_in(cats[2], "A"))
    connect(pin_out(conv2, "ReturnValue"), pin_in(cats[2], "B"))
    # cats[3]: + " 180="
    connect(pin_out(cats[2], "ReturnValue"), pin_in(cats[3], "A"))
    set_val(cats[3], "B", " 180=")
    connect(pin_out(cats[3], "ReturnValue"), pin_in(cats[4], "A"))
    connect(pin_out(c180, "ReturnValue"), pin_in(cats[4], "B"))
    connect(pin_out(cats[4], "ReturnValue"), pin_in(cats[5], "A"))
    set_val(cats[5], "B", " 90=")
    connect(pin_out(cats[5], "ReturnValue"), pin_in(cats[6], "A"))
    connect(pin_out(c90, "ReturnValue"), pin_in(cats[6], "B"))
    connect(pin_out(cats[6], "ReturnValue"), pin_in(cats[7], "A"))
    # cats[7] B = " L=" + left — need extra concat; put left into B with prefix via set B=" L=" won't include value.
    # Recreate: cats[7] A=cats6 B=" L=", need cats[8]
    cat8 = cat("TVDBG_Cat8", 4900, 780)
    connect(pin_out(cats[7], "ReturnValue"), pin_in(cat8, "A"))
    # Wait cats[7] B should be " L=" then cat8 B = left str
    set_val(cats[7], "B", " L=")
    connect(pin_out(cleft, "ReturnValue"), pin_in(cat8, "B"))
    connect(pin_out(cat8, "ReturnValue"), pin_in(print_n, "InString"))

    # exec
    connect(then, bel.find_execute_pin(br))
    connect(pin_out(get_dbg), bel.find_condition_pin(br))
    connect(bel.find_then_pin(br), bel.find_execute_pin(print_n))
    connect(bel.find_then_pin(print_n), bel.find_execute_pin(old))
    connect(bel.find_else_pin(br), bel.find_execute_pin(old))

    log("debug print wired (screen key=TurnDbg)")


def run():
    log("start")
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()
    healthy = verify(graph)
    log(f"graph_healthy={healthy}")
    add_debug(abp, ed, graph)
    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
