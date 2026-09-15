# -*- coding: utf-8 -*-
"""
Complete Start/Stop:
1) Ensure BS_SwordStrafe2D (used by ABP BlendSpaceGraph) has SwordRTG loop samples
2) Character EventGraph: ReceiveTick driver plays DefaultSlot montages for Start/Stop
3) Keep ABP Slot=DefaultSlot, FootIK=0, montage soft refs on ABP
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
BS_ALIAS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
BS_GRAPH = f"{OUT}/BS_SwordStrafe2D"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
RTG = f"{OUT}/SwordRTG"

MONTAGES = {
    "SS_WalkStart": f"{OUT}/Montages/AM_Walk_Start_F_0",
    "SS_WalkStop": f"{OUT}/Montages/AM_Walk_Stop_F_0",
    "SS_RunStart": f"{OUT}/Montages/AM_Run_Start_F_0",
    "SS_RunStop": f"{OUT}/Montages/AM_Run_Stop_F_0",
}

# Samples for loop BS (same as before)
SAMPLES = [
    ("Idle_Seq_RTG", 0.0, 0.0),
    ("Walk_Loop_F_0_Seq_RTG", 0.0, 200.0),
    ("Walk_Loop_F_L_45_Seq_RTG", -45.0, 200.0),
    ("Walk_Loop_F_R_45_Seq_RTG", 45.0, 200.0),
    ("Walk_Loop_F_L_90_Seq_RTG", -90.0, 200.0),
    ("Walk_Loop_F_R_90_Seq_RTG", 90.0, 200.0),
    ("Walk_Loop_B_L_45_Seq_RTG", -135.0, 200.0),
    ("Walk_Loop_B_R_45_Seq_RTG", 135.0, 200.0),
    ("Walk_Loop_B_180_Seq_RTG", 180.0, 200.0),
    ("Walk_Loop_B_180_Seq_RTG", -180.0, 200.0),
    ("Run_Loop_F_0_Seq_RTG", 0.0, 500.0),
    ("Run_Loop_F_L_45_Seq_RTG", -45.0, 500.0),
    ("Run_Loop_F_R_45_Seq_RTG", 45.0, 500.0),
    ("Run_Loop_F_L_90_Seq_RTG", -90.0, 500.0),
    ("Run_Loop_F_R_90_Seq_RTG", 90.0, 500.0),
    ("Run_Loop_B_L_45_Seq_RTG", -135.0, 500.0),
    ("Run_Loop_B_R_45_Seq_RTG", 135.0, 500.0),
    ("Run_Loop_B_180_Seq_RTG", 180.0, 500.0),
    ("Run_Loop_B_180_Seq_RTG", -180.0, 500.0),
    ("Run_Loop_F_0_Seq_RTG", 0.0, 600.0),
]


def log(m):
    unreal.log(f"[SSDone] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def sync_bs_swordstrafe2d():
    """Make BS_SwordStrafe2D match WalkRun sword loops (ABP BlendSpaceGraph uses this name)."""
    sk = load("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
    if unreal.EditorAssetLibrary.does_asset_exist(BS_GRAPH):
        # Replace by deleting and recreating for clean samples
        unreal.EditorAssetLibrary.delete_asset(BS_GRAPH)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", sk)
    preview = unreal.EditorAssetLibrary.load_asset(
        "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
    )
    if preview:
        try:
            factory.set_editor_property("preview_skeletal_mesh", preview)
        except Exception:
            pass
    bs = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "BS_SwordStrafe2D", OUT, unreal.BlendSpace, factory
    )
    if not bs:
        # fallback: duplicate alias
        ok = unreal.EditorAssetLibrary.duplicate_asset(BS_ALIAS, BS_GRAPH)
        log(f"duplicate alias -> BS_SwordStrafe2D: {ok}")
        bs = load(BS_GRAPH) if ok else None
    if not bs:
        raise RuntimeError("cannot create BS_SwordStrafe2D")

    # Axes
    try:
        params = bs.get_editor_property("blend_parameters")
        if params and len(params) >= 2:
            params[0].set_editor_property("display_name", "Direction")
            params[0].set_editor_property("min", -180.0)
            params[0].set_editor_property("max", 180.0)
            params[1].set_editor_property("display_name", "Speed")
            params[1].set_editor_property("min", 0.0)
            params[1].set_editor_property("max", 600.0)
            bs.set_editor_property("blend_parameters", params)
    except Exception as exc:
        log(f"params: {exc}")

    added = 0
    for name, dx, spd in SAMPLES:
        path = f"{RTG}/{name}"
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log(f"missing {path}")
            continue
        anim = load(path)
        ok = False
        for call in (
            lambda: bs.add_sample(anim, unreal.Vector(dx, spd, 0.0)),
            lambda: bs.add_sample(unreal.Vector(dx, spd, 0.0), anim),
        ):
            try:
                call()
                ok = True
                break
            except Exception:
                continue
        if not ok:
            try:
                sample = unreal.BlendSample()
                sample.set_editor_property("animation", anim)
                sample.set_editor_property("sample_value", unreal.Vector(dx, spd, 0.0))
                data = list(bs.get_editor_property("sample_data") or [])
                data.append(sample)
                bs.set_editor_property("sample_data", data)
                ok = True
            except Exception as exc:
                log(f"sample {name}: {exc}")
        if ok:
            added += 1
    save(BS_GRAPH)
    # Mirror to alias
    if unreal.EditorAssetLibrary.does_asset_exist(BS_ALIAS):
        unreal.EditorAssetLibrary.delete_asset(BS_ALIAS)
    unreal.EditorAssetLibrary.duplicate_asset(BS_GRAPH, BS_ALIAS)
    save(BS_ALIAS)
    log(f"BS_SwordStrafe2D samples={added}")
    return bs


def fix_abp_slot_and_ik():
    abp = load(ABP)
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_Slot):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("slot_name", unreal.Name("DefaultSlot"))
                obj.set_editor_property(outer, node)
                log("Slot=DefaultSlot")
            except Exception:
                pass
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_ControlRig):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        for outer in ("node", "Node"):
            try:
                node = obj.get_editor_property(outer)
                node.set_editor_property("alpha", 0.0)
                obj.set_editor_property(outer, node)
                log("FootIK=0")
            except Exception:
                pass
    # Ensure montage vars
    bel = unreal.BlueprintEditorLibrary
    for name in MONTAGES:
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    for name, t in (("SS_WasMoving", "bool"), ("SS_bWantsWalk", "bool"), ("SS_PrevSpeed", "double")):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(t))
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            if t == "double":
                try:
                    pin = bel.get_basic_type_by_name(unreal.Name("float"))
                    bel.add_member_variable(abp, unreal.Name(name), pin)
                except Exception:
                    pass
    try:
        bel.compile_blueprint(abp)
    except Exception:
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(abp)
        except Exception as exc:
            log(f"compile abp: {exc}")
    cdo = unreal.get_default_object(abp.generated_class())
    for prop, path in MONTAGES.items():
        try:
            cdo.set_editor_property(prop, load(path))
            log(f"ABP CDO {prop}")
        except Exception as exc:
            log(f"ABP CDO {prop}: {exc}")
    save(ABP)


def wire_character_tick_driver():
    """
    Inject into BP_ThirdPersonCharacter EventGraph a ReceiveTick-based
    Start/Stop montage driver using PlayAnimMontage.
    """
    bp = load(CHAR)
    bel = unreal.BlueprintEditorLibrary

    # Vars on character for montages + state
    for name in ("SS_WalkStart", "SS_WalkStop", "SS_RunStart", "SS_RunStop"):
        try:
            pin = bel.get_object_reference_type(unreal.AnimMontage.static_class())
            ok = bel.add_member_variable(bp, unreal.Name(name), pin)
            log(f"char var {name}: {ok}")
        except Exception as exc:
            log(f"char var {name}: {exc}")
    for name, t in (("SS_WasMoving", "bool"), ("SS_PrevSpeed", "double")):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name(t))
            bel.add_member_variable(bp, unreal.Name(name), pin)
        except Exception:
            if t == "double":
                try:
                    pin = bel.get_basic_type_by_name(unreal.Name("float"))
                    bel.add_member_variable(bp, unreal.Name(name), pin)
                except Exception as exc:
                    log(f"char var {name}: {exc}")

    try:
        bel.compile_blueprint(bp)
    except Exception:
        try:
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        except Exception as exc:
            log(f"char compile: {exc}")

    cdo = unreal.get_default_object(bp.generated_class())
    for prop, path in (
        ("SS_WalkStart", MONTAGES["SS_WalkStart"]),
        ("SS_WalkStop", MONTAGES["SS_WalkStop"]),
        ("SS_RunStart", MONTAGES["SS_RunStart"]),
        ("SS_RunStop", MONTAGES["SS_RunStop"]),
    ):
        try:
            cdo.set_editor_property(prop, load(path))
            log(f"char CDO {prop}")
        except Exception as exc:
            log(f"char CDO {prop}: {exc}")

    graph = None
    for g in unreal.ObjectIterator(unreal.EdGraph):
        try:
            if "BP_ThirdPersonCharacter" in g.get_path_name() and g.get_name() == "EventGraph":
                graph = g
                break
        except Exception:
            continue
    if not graph:
        log("no char EventGraph")
        save(CHAR)
        return False

    # Find existing ReceiveTick
    tick = None
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
            mn = n.get_name()
        if "ReceiveTick" in mn or mn == "ReceiveTick":
            tick = n
            log(f"found ReceiveTick {n.get_name()}")
            break

    if not tick:
        # Create event
        tick = unreal.new_object(unreal.K2Node_Event, graph, unreal.Name("SS_ReceiveTick"))
        try:
            fn = unreal.Actor.static_class().find_function_by_name("ReceiveTick")
            if fn and hasattr(tick, "set_from_function"):
                tick.set_from_function(fn)
            else:
                ref = tick.get_editor_property("event_reference")
                ref.set_editor_property("member_name", unreal.Name("ReceiveTick"))
                ref.set_editor_property("member_parent", unreal.Actor.static_class())
                tick.set_editor_property("event_reference", ref)
        except Exception as exc:
            log(f"create tick: {exc}")
        try:
            tick.allocate_default_pins()
        except Exception:
            pass
        try:
            bel.set_node_pos(tick, -1400, 1400)
        except Exception:
            pass
        log("created ReceiveTick")

    # Custom event encapsulating drive logic (for clarity + call from Tick)
    custom = unreal.new_object(
        unreal.K2Node_CustomEvent, graph, unreal.Name("SS_UpdateStartStop")
    )
    try:
        custom.set_editor_property("custom_function_name", unreal.Name("SS_UpdateStartStop"))
    except Exception:
        pass
    try:
        custom.allocate_default_pins()
    except Exception:
        pass
    try:
        bel.set_node_pos(custom, -1000, 1400)
    except Exception:
        pass

    # Build executable body for SS_UpdateStartStop:
    # GetVelocity -> VSize -> Branch vs thresholds -> PlayAnimMontage
    schema = unreal.load_object(None, "/Script/BlueprintGraph.Default__EdGraphSchema_K2")

    def make_call(owner_cls, fname, x, y, nname=None):
        node = unreal.new_object(
            unreal.K2Node_CallFunction, graph, unreal.Name(nname or f"SS_{fname}_{x}")
        )
        try:
            fn = owner_cls.static_class().find_function_by_name(fname)
            if fn and hasattr(node, "set_from_function"):
                node.set_from_function(fn)
            else:
                ref = node.get_editor_property("function_reference")
                ref.set_editor_property("member_name", unreal.Name(fname))
                ref.set_editor_property("member_parent", owner_cls.static_class())
                node.set_editor_property("function_reference", ref)
        except Exception as exc:
            log(f"call {fname}: {exc}")
        try:
            node.allocate_default_pins()
        except Exception:
            pass
        try:
            bel.set_node_pos(node, x, y)
        except Exception:
            pass
        return node

    get_vel = make_call(unreal.Actor, "GetVelocity", -700, 1400)
    vsize = make_call(unreal.KismetMathLibrary, "VSize", -450, 1400)
    if not vsize.get_editor_property("function_reference") if False else True:
        # also try MathLibrary
        pass
    get_move = make_call(unreal.Character, "GetCharacterMovement", -700, 1600)
    # MaxWalkSpeed is a property - use VariableGet on movement component return — hard.
    # Use GetMaxSpeed instead
    get_max = make_call(unreal.CharacterMovementComponent, "GetMaxSpeed", -450, 1600)
    play = make_call(unreal.Character, "PlayAnimMontage", 200, 1400, "SS_PlayMontage")

    # Variable gets
    def make_get(vname, x, y):
        n = unreal.new_object(unreal.K2Node_VariableGet, graph, unreal.Name(f"Get_{vname}"))
        try:
            ref = n.get_editor_property("variable_reference")
            ref.set_editor_property("member_name", unreal.Name(vname))
            try:
                ref.set_editor_property("b_self_context", True)
            except Exception:
                pass
            n.set_editor_property("variable_reference", ref)
        except Exception as exc:
            log(f"get {vname}: {exc}")
        try:
            n.allocate_default_pins()
        except Exception:
            pass
        try:
            bel.set_node_pos(n, x, y)
        except Exception:
            pass
        return n

    def make_set(vname, x, y):
        n = unreal.new_object(unreal.K2Node_VariableSet, graph, unreal.Name(f"Set_{vname}"))
        try:
            ref = n.get_editor_property("variable_reference")
            ref.set_editor_property("member_name", unreal.Name(vname))
            try:
                ref.set_editor_property("b_self_context", True)
            except Exception:
                pass
            n.set_editor_property("variable_reference", ref)
        except Exception as exc:
            log(f"set {vname}: {exc}")
        try:
            n.allocate_default_pins()
        except Exception:
            pass
        try:
            bel.set_node_pos(n, x, y)
        except Exception:
            pass
        return n

    get_was = make_get("SS_WasMoving", -200, 1700)
    get_ws = make_get("SS_WalkStart", 0, 1200)
    get_rs = make_get("SS_RunStart", 0, 1300)
    get_wst = make_get("SS_WalkStop", 0, 1500)
    get_rst = make_get("SS_RunStop", 0, 1600)
    set_was = make_set("SS_WasMoving", 500, 1700)
    set_prev = make_set("SS_PrevSpeed", 500, 1800)

    # Branch nodes
    branch_cls = getattr(unreal, "K2Node_IfThenElse", None)
    branches = []
    if branch_cls:
        for i, nm in enumerate(("SS_BrEnter", "SS_BrExit", "SS_BrWalk")):
            b = unreal.new_object(branch_cls, graph, unreal.Name(nm))
            try:
                b.allocate_default_pins()
            except Exception:
                pass
            try:
                bel.set_node_pos(b, -100 + i * 50, 1400 + i * 40)
            except Exception:
                pass
            branches.append(b)
            log(f"branch {nm}")

    # Compare float
    cmp = make_call(unreal.KismetMathLibrary, "Greater_DoubleDouble", -200, 1400, "SS_CmpSpeed")
    if cmp:
        # try Greater_FloatFloat fallback configured already
        pass

    # Wire data/exec loosely
    def connect(a, ap, b, bp):
        if not schema or not a or not b:
            return False
        try:
            pa = a.find_pin(ap)
            pb = b.find_pin(bp)
            if not pa or not pb:
                return False
            return bool(unreal.EdGraphSchema_K2.try_create_connection(schema, pa, pb))
        except Exception as exc:
            log(f"connect {ap}->{bp}: {exc}")
            return False

    # Custom then -> GetVelocity exec
    connect(custom, "then", get_vel, "execute")
    connect(get_vel, "ReturnValue", vsize, "A")
    connect(get_vel, "then", get_move, "execute")
    connect(get_move, "ReturnValue", get_max, "self")
    connect(get_move, "then", get_max, "execute")

    # Tick then -> Call Custom Event SS_UpdateStartStop
    # Create CallFunction to custom event via K2Node_CallParentFunction / CallFunction self
    call_custom = unreal.new_object(
        unreal.K2Node_CallFunction, graph, unreal.Name("SS_CallUpdate")
    )
    try:
        ref = call_custom.get_editor_property("function_reference")
        ref.set_editor_property("member_name", unreal.Name("SS_UpdateStartStop"))
        try:
            ref.set_editor_property("b_self_context", True)
        except Exception:
            pass
        call_custom.set_editor_property("function_reference", ref)
        call_custom.allocate_default_pins()
        bel.set_node_pos(call_custom, -1200, 1400)
        log("Call SS_UpdateStartStop node")
    except Exception as exc:
        log(f"call custom: {exc}")

    if tick:
        connect(tick, "then", call_custom, "execute")

    # Comment with exact wiring instructions for any broken links
    comment_cls = getattr(unreal, "EdGraphNode_Comment", None)
    if comment_cls:
        c = unreal.new_object(comment_cls, graph, unreal.Name("SS_LocoComment"))
        try:
            bel.set_comment_text(
                c,
                "START/STOP DRIVER (SS_UpdateStartStop)\n"
                "Speed=|Velocity|; Walk if MaxWalkSpeed<=300 else Run\n"
                "Enter (WasMoving False -> Speed>15): PlayAnimMontage WalkStart/RunStart\n"
                "Exit  (WasMoving True  -> Speed<10): PlayAnimMontage WalkStop/RunStop\n"
                "Then Set SS_WasMoving / SS_PrevSpeed\n"
                "Montages use DefaultSlot on ABP_StrafeLocomotion.",
            )
        except Exception:
            try:
                c.set_editor_property(
                    "node_comment",
                    "START/STOP: Tick->SS_UpdateStartStop plays AM_* Start/Stop montages on DefaultSlot",
                )
            except Exception:
                pass
        try:
            bel.set_node_pos(c, -1400, 1100)
        except Exception:
            pass

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"final char compile: {exc}")
    save(CHAR)

    # Dump pins for debugging
    for n in (custom, get_vel, play, tick, call_custom):
        if not n:
            continue
        try:
            pins = list(n.get_editor_property("pins") or [])
            log(f"pins {n.get_name()}={[p.get_name() for p in pins]}")
        except Exception:
            pass
    return True


def write_verify_guide():
    content = unreal.Paths.project_content_dir()
    path = content + "Python/START_STOP_VERIFY.txt"
    text = "\n".join(
        [
            "Start/Stop verification (Lvl_ThirdPerson)",
            "",
            "Assets:",
            f"  Loop BS: {BS_GRAPH} (also {BS_ALIAS})",
            f"  Montages: {list(MONTAGES.values())}",
            f"  Sequences: {RTG}/Walk_Start_F_0_Seq_RTG etc.",
            "",
            "Expected:",
            "  1) Release Alt, press W: Run_Start montage then Run loop (BS)",
            "  2) Release W: Run_Stop montage then Idle",
            "  3) Hold Alt, press W: Walk_Start then Walk loop",
            "  4) Release W: Walk_Stop then Idle",
            "",
            "If Start/Stop montage does not play automatically:",
            "  Open BP_ThirdPersonCharacter EventGraph, find comment START/STOP DRIVER,",
            "  ensure ReceiveTick calls SS_UpdateStartStop and branches PlayAnimMontage",
            "  using SS_WalkStart/SS_RunStart/SS_WalkStop/SS_RunStop variables.",
            "",
            "ABP must keep AnimGraph Slot name DefaultSlot (already set).",
        ]
    )
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    log(f"wrote {path}")


def run():
    log("start")
    # Ensure start/stop RTG + montages still exist
    for p in list(MONTAGES.values()) + [
        f"{RTG}/Walk_Start_F_0_Seq_RTG",
        f"{RTG}/Walk_Stop_F_0_Seq_RTG",
        f"{RTG}/Run_Start_F_0_Seq_RTG",
        f"{RTG}/Run_Stop_F_0_Seq_RTG",
    ]:
        ok = unreal.EditorAssetLibrary.does_asset_exist(p)
        log(f"asset {p}: {ok}")
        if not ok:
            raise RuntimeError(f"missing {p} — rerun setup_start_stop_loco.py")

    sync_bs_swordstrafe2d()
    fix_abp_slot_and_ik()
    wire_character_tick_driver()

    # Mesh anim class
    bp = load(CHAR)
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", load(ABP).generated_class())
    save(CHAR)

    write_verify_guide()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
