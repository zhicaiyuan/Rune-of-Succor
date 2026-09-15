# -*- coding: utf-8 -*-
"""
Cha_2 uses Leg_L/Leg_R/Arm_L/Arm_R; Characters auto-def uses LeftLeg/RightLeg.
Manually map chains, verify via GetSourceChain, re-retarget, keep FootIK off.
"""

from __future__ import annotations

import unreal

OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
RTG_DIR = f"{OUT}/SwordRTG"
IKR = f"{OUT}/IK/IKR_SwordToCharacters"
IK_CHAR = f"{OUT}/IK/IK_Characters_Manny"
CHA2 = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/Cha_2_IKRig"
SRC_MESH = "/Game/Sword_Animations/Demo/Mannequins/Character/Meshes/SKM_Manny"
TGT_MESH = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ABP = f"{OUT}/ABP_StrafeLocomotion"

# source_chain -> target_chain
CHAIN_MAP = {
    "Spine": "Spine",
    "Head": "Head",
    "Leg_L": "LeftLeg",
    "Leg_R": "RightLeg",
    "Arm_L": "LeftArm",
    "Arm_R": "RightArm",
    # optional feet if source has them (often included in Leg_*)
    "Finger_L_Thumb": "LeftThumb",
    "Finger_L_Index": "LeftIndex",
    "Finger_L_Middle": "LeftMiddle",
    "Finger_L_Ring": "LeftRing",
    "Finger_L_Pinky": "LeftPinky",
    "Finger_R_Thumb": "RightThumb",
    "Finger_R_Index": "RightIndex",
    "Finger_R_Middle": "RightMiddle",
    "Finger_R_Ring": "RightRing",
    "Finger_R_Pinky": "RightPinky",
}

SRC_ANIMS = [
    "/Game/Sword_Animations/Animations/Sequence2/01_Idle/Idle_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/01_Walk_F_0/Walk_Loop_F_0_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/02_Walk_F_L_45/Walk_Loop_F_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/03_Walk_F_R_45/Walk_Loop_F_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/04_Walk_F_L_90/Walk_Loop_F_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/05_Walk_F_R_90/Walk_Loop_F_R_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/06_Walk_B_180/Walk_Loop_B_180_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/07_Walk_B_L_45/Walk_Loop_B_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/08_Walk_B_R_45/Walk_Loop_B_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/09_Walk_B_L_90/Walk_Loop_B_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/03_Walk/01_Walk/10_Walk_B_R_90/Walk_Loop_B_R_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/01_Run_F_0/Run_Loop_F_0_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/02_Run_F_L_45/Run_Loop_F_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/03_Run_F_R_45/Run_Loop_F_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/04_Run_F_L_90/Run_Loop_F_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/05_Run_F_R_90/Run_Loop_F_R_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/06_Run_B_180/Run_Loop_B_180_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/07_Run_B_L_45/Run_Loop_B_L_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/08_Run_B_R_45/Run_Loop_B_R_45_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/09_Run_B_L_90/Run_Loop_B_L_90_Seq",
    "/Game/Sword_Animations/Animations/Sequence2/04_Run/01_Run/10_Run_B_R_90/Run_Loop_B_R_90_Seq",
]


def log(m):
    unreal.log(f"[LegMap] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def list_ops(rctrl):
    ops = []
    for meth in (
        "get_retarget_ops",
        "get_op_names",
        "get_retarget_op_names",
        "get_stack_names",
    ):
        if hasattr(rctrl, meth):
            try:
                ops = list(getattr(rctrl, meth)() or [])
                log(f"{meth}={ops}")
                return ops
            except Exception as exc:
                log(f"{meth}: {exc}")
    # index walk
    for i in range(16):
        for meth in ("get_retarget_op_name_at_index", "get_retarget_op_at_index"):
            if hasattr(rctrl, meth):
                try:
                    v = getattr(rctrl, meth)(i)
                    log(f"op[{i}] via {meth}={v}")
                    ops.append(v)
                except Exception:
                    break
    return ops


def map_chains():
    src_ik = load(CHA2)
    char_ik = load(IK_CHAR)
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)
    ikr = load(IKR)

    rctrl = unreal.IKRetargeterController.get_controller(ikr)
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.SOURCE, src_ik)
    rctrl.set_ik_rig(unreal.RetargetSourceOrTarget.TARGET, char_ik)
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.SOURCE, src_mesh)
    rctrl.set_preview_mesh(unreal.RetargetSourceOrTarget.TARGET, tgt_mesh)
    try:
        rctrl.add_default_ops()
    except Exception as exc:
        log(f"AddDefaultOps: {exc}")

    list_ops(rctrl)

    # Clear all first
    try:
        rctrl.auto_map_chains(unreal.AutoMapChainType.CLEAR, True)
        log("cleared maps")
    except Exception as exc:
        log(f"clear: {exc}")

    for src, tgt in CHAIN_MAP.items():
        try:
            ok = rctrl.set_source_chain(unreal.Name(src), unreal.Name(tgt))
            log(f"map {src} -> {tgt}: {ok}")
        except Exception as exc:
            log(f"map {src}->{tgt} ERR {exc}")

    # Verify critical legs
    ok_legs = True
    for tgt in ("LeftLeg", "RightLeg", "LeftArm", "RightArm", "Spine", "Head"):
        try:
            src = rctrl.get_source_chain(unreal.Name(tgt))
            log(f"VERIFY target {tgt} <= source {src}")
            if str(src) in ("None", "", "None"):
                ok_legs = False
            if tgt in ("LeftLeg", "RightLeg") and "Leg" not in str(src):
                ok_legs = False
        except Exception as exc:
            log(f"get_source_chain {tgt}: {exc}")
            ok_legs = False

    save(IKR)
    return ikr, ok_legs


def reretarget(ikr):
    src_mesh = load(SRC_MESH)
    tgt_mesh = load(TGT_MESH)
    datas = [
        unreal.EditorAssetLibrary.find_asset_data(p)
        for p in SRC_ANIMS
        if unreal.EditorAssetLibrary.does_asset_exist(p)
    ]
    log(f"retarget count={len(datas)}")
    inputs = unreal.IKRetargetBatchOperationInputs()
    inputs.set_editor_property("assets_to_retarget", datas)
    inputs.set_editor_property("source_mesh", src_mesh)
    inputs.set_editor_property("target_mesh", tgt_mesh)
    inputs.set_editor_property("ik_retarget_asset", ikr)
    inputs.set_editor_property("search", "")
    inputs.set_editor_property("replace", "")
    inputs.set_editor_property("prefix", "")
    inputs.set_editor_property("suffix", "_RTG")
    inputs.set_editor_property("target_path", RTG_DIR)
    inputs.set_editor_property("use_source_path", False)
    inputs.set_editor_property("include_referenced_assets", False)
    inputs.set_editor_property("overwrite_existing_files", True)
    created = unreal.IKRetargetBatchOperation.run_batch_retarget(inputs) or []
    try:
        unreal.EditorAssetLibrary.save_directory(RTG_DIR, only_if_is_dirty=False, recursive=True)
    except Exception:
        pass
    log(f"created={len(created)}")
    return len(created)


def disable_foot_ik():
    abp = load(ABP)
    cls = getattr(unreal, "AnimGraphNode_ControlRig", None)
    if cls:
        for obj in unreal.ObjectIterator(cls):
            try:
                if "ABP_StrafeLocomotion" not in obj.get_path_name():
                    continue
            except Exception:
                continue
            for outer in ("node", "Node"):
                try:
                    node = obj.get_editor_property(outer)
                    node.set_editor_property("alpha", 0.0)
                    obj.set_editor_property(outer, node)
                    log("FootIK alpha=0")
                except Exception:
                    pass
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile: {exc}")
    save(ABP)


def run():
    log("start")
    ikr, ok = map_chains()
    if not ok:
        log("CRITICAL: leg chains still unmapped")
    n = reretarget(ikr)
    disable_foot_ik()
    # Re-verify after save
    rctrl = unreal.IKRetargeterController.get_controller(load(IKR))
    for tgt in ("LeftLeg", "RightLeg"):
        try:
            log(f"FINAL {tgt} <= {rctrl.get_source_chain(unreal.Name(tgt))}")
        except Exception as exc:
            log(f"FINAL {tgt}: {exc}")
    log(f"done ok_legs={ok} retargeted={n}")


if __name__ == "__main__":
    run()
else:
    run()
