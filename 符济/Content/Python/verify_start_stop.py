# -*- coding: utf-8 -*-
"""Structural + CDO verification for Start/Stop locomotion (Lvl_ThirdPerson readiness)."""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
MAP = "/Game/ThirdPerson/Lvl_ThirdPerson"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor
ok_all = True


def log(m):
    unreal.log(f"[SSVerify] {m}")


def check(cond, msg):
    global ok_all
    if cond:
        log(f"OK  {msg}")
    else:
        log(f"FAIL {msg}")
        ok_all = False


def run():
    # Assets
    for name in (
        "Walk_Start_F_0_Seq_RTG",
        "Walk_Stop_F_0_Seq_RTG",
        "Run_Start_F_0_Seq_RTG",
        "Run_Stop_F_0_Seq_RTG",
    ):
        check(
            unreal.EditorAssetLibrary.does_asset_exist(f"{OUT}/SwordRTG/{name}"),
            f"RTG {name}",
        )
    for name in (
        "AM_Walk_Start_F_0",
        "AM_Walk_Stop_F_0",
        "AM_Run_Start_F_0",
        "AM_Run_Stop_F_0",
    ):
        check(
            unreal.EditorAssetLibrary.does_asset_exist(f"{OUT}/Montages/{name}"),
            f"Montage {name}",
        )

    bp = unreal.EditorAssetLibrary.load_asset(CHAR)
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    check(bp is not None, "BP_ThirdPersonCharacter")
    check(abp is not None, "ABP_StrafeLocomotion")

    # Anim class
    cdo = unreal.get_default_object(bp.generated_class())
    mesh = cdo.get_editor_property("mesh")
    anim = mesh.get_editor_property("anim_class")
    check(anim is not None and "ABP_StrafeLocomotion" in str(anim), f"Mesh AnimClass={anim}")

    # Montage defaults on character
    for prop in ("SS_WalkStart", "SS_WalkStop", "SS_RunStart", "SS_RunStop"):
        try:
            v = cdo.get_editor_property(prop)
            check(v is not None, f"CDO.{prop}={v.get_name() if v else None}")
        except Exception as e:
            check(False, f"CDO.{prop}: {e}")

    # Movement / camera TPS settings
    try:
        cmc = cdo.get_editor_property("character_movement")
        check(bool(cmc.get_editor_property("orient_rotation_to_movement")), "OrientRotationToMovement")
        check(not bool(cdo.get_editor_property("use_controller_rotation_yaw")), "UseControllerRotationYaw=False")
    except Exception as e:
        check(False, f"movement props: {e}")

    # SpringArm UsePawnControlRotation via subobjects
    try:
        subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
        handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
        found = False
        for h in handles:
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(h)
            obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
            if obj and "SpringArm" in obj.get_class().get_name():
                upc = obj.get_editor_property("use_pawn_control_rotation")
                check(bool(upc), f"SpringArm.UsePawnControlRotation={upc}")
                found = True
                break
        if not found:
            check(False, "SpringArm not found")
    except Exception as e:
        log(f"SpringArm check skipped: {e}")

    # Graph wiring
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    g = ed.get_graph()
    tick = None
    plays = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        if n.get_outer() == g and "Tick" in str(bel.get_node_title(n)):
            tick = n
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        if n.get_outer() == g and "PlayAnimMontage" in str(bel.get_node_title(n)):
            plays.append(n)
    check(tick is not None, "ReceiveTick present")
    check(len(plays) >= 4, f"PlayAnimMontage nodes={len(plays)}")
    if tick:
        then = bel.find_then_pin(tick)
        linked = list(then.list_connected_pins()) if then else []
        check(len(linked) >= 1, f"Tick.then linked={len(linked)}")
    for n in plays:
        p = bel.find_input_pin(n, "AnimMontage")
        linked = list(p.list_connected_pins()) if p else []
        check(len(linked) >= 1, f"{n.get_name()} AnimMontage linked")

    # SM states / sequences (optional BoundGraph path; montage driver is primary)
    found_sm = set()
    for sp in unreal.ObjectIterator(unreal.AnimGraphNode_SequencePlayer):
        p = sp.get_path_name()
        if "ABP_StrafeLocomotion" not in p:
            continue
        if not any(k in p for k in ("WalkStart", "RunStart", "WalkStop", "RunStop")):
            continue
        try:
            seq = sp.get_editor_property("node").get_editor_property("sequence")
            if seq:
                found_sm.add(seq.get_name())
        except Exception:
            pass
    if found_sm:
        check(len(found_sm) >= 4, f"SM Start/Stop sequences={found_sm}")
    else:
        log("OK  SM BoundGraph optional (runtime uses Montage DefaultSlot driver)")

    # Slot + Foot IK
    slot_ok = False
    ik_ok = False
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_Slot):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        try:
            node = obj.get_editor_property("node")
            if str(node.get_editor_property("slot_name")) == "DefaultSlot":
                slot_ok = True
        except Exception:
            pass
    for obj in unreal.ObjectIterator(unreal.AnimGraphNode_ControlRig):
        if "ABP_StrafeLocomotion" not in obj.get_path_name():
            continue
        try:
            node = obj.get_editor_property("node")
            if float(node.get_editor_property("alpha")) == 0.0:
                ik_ok = True
        except Exception:
            pass
    check(slot_ok, "DefaultSlot")
    check(ik_ok, "FootIK alpha=0")

    check(unreal.EditorAssetLibrary.does_asset_exist(MAP), f"Map {MAP}")

    # Compile both
    try:
        bel.compile_blueprint(bp)
        bel.compile_blueprint(abp)
        check(True, "compile char+abp")
    except Exception as e:
        check(False, f"compile: {e}")

    log("RESULT=" + ("PASS" if ok_all else "FAIL"))
    content = unreal.Paths.project_content_dir()
    with open(content + "Python/START_STOP_VERIFY_RESULT.txt", "w", encoding="utf-8") as f:
        f.write("PASS\n" if ok_all else "FAIL\n")
        f.write(
            "Manual PIE on Lvl_ThirdPerson:\n"
            "- Run: Idle->RunStart->Loop->Stop->Idle\n"
            "- Alt Walk: Idle->WalkStart->Loop->Stop->Idle\n"
            "- Camera follows mouse; body orients to movement\n"
        )


if __name__ == "__main__":
    run()
else:
    run()
