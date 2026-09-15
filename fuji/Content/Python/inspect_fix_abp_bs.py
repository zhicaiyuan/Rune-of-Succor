# -*- coding: utf-8 -*-
"""Inspect why ABP may not play BS_WalkRun_Sword samples; rebind samples + ABP player."""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_WalkRun_Sword"
RTG = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/SwordRTG"
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"

# Direction, Speed samples (same layout as setup scripts)
SAMPLES = [
    ("Idle_Seq_RTG", 0.0, 0.0),
    ("Walk_Loop_F_0_Seq_RTG", 0.0, 200.0),
    ("Walk_Loop_F_L_45_Seq_RTG", -45.0, 200.0),
    ("Walk_Loop_F_R_45_Seq_RTG", 45.0, 200.0),
    ("Walk_Loop_F_L_90_Seq_RTG", -90.0, 200.0),
    ("Walk_Loop_F_R_90_Seq_RTG", 90.0, 200.0),
    ("Walk_Loop_B_L_45_Seq_RTG", -135.0, 200.0),
    ("Walk_Loop_B_R_45_Seq_RTG", 135.0, 200.0),
    ("Walk_Loop_B_L_90_Seq_RTG", -90.0, 200.0),  # keep if present; else B_180
    ("Walk_Loop_B_R_90_Seq_RTG", 90.0, 200.0),
    ("Walk_Loop_B_180_Seq_RTG", 180.0, 200.0),
    ("Walk_Loop_B_180_Seq_RTG", -180.0, 200.0),
    ("Run_Loop_F_0_Seq_RTG", 0.0, 500.0),
    ("Run_Loop_F_L_45_Seq_RTG", -45.0, 500.0),
    ("Run_Loop_F_R_45_Seq_RTG", 45.0, 500.0),
    ("Run_Loop_F_L_90_Seq_RTG", -90.0, 500.0),
    ("Run_Loop_F_R_90_Seq_RTG", 90.0, 500.0),
    ("Run_Loop_B_L_45_Seq_RTG", -135.0, 500.0),
    ("Run_Loop_B_R_45_Seq_RTG", 135.0, 500.0),
    ("Run_Loop_B_L_90_Seq_RTG", -90.0, 500.0),
    ("Run_Loop_B_R_90_Seq_RTG", 90.0, 500.0),
    ("Run_Loop_B_180_Seq_RTG", 180.0, 500.0),
    ("Run_Loop_B_180_Seq_RTG", -180.0, 500.0),
    ("Run_Loop_F_0_Seq_RTG", 0.0, 600.0),
]


def log(m):
    unreal.log(f"[ABPBS] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def inspect_bs(bs):
    sk = bs.get_editor_property("skeleton")
    log(f"BS skeleton={sk.get_path_name() if sk else None}")
    samples = None
    for prop in ("sample_data", "blend_samples", "BlendSamples"):
        try:
            samples = bs.get_editor_property(prop)
            if samples is not None:
                log(f"samples via {prop}: count={len(samples)}")
                break
        except Exception as exc:
            log(f"{prop}: {exc}")
    if samples:
        for i, s in enumerate(list(samples)[:40]):
            anim = None
            sample_value = None
            for ap in ("animation", "Animation"):
                try:
                    anim = s.get_editor_property(ap)
                    break
                except Exception:
                    pass
            for vp in ("sample_value", "SampleValue"):
                try:
                    sample_value = s.get_editor_property(vp)
                    break
                except Exception:
                    pass
            aname = anim.get_path_name() if anim else "NONE"
            log(f"  [{i}] {aname} @ {sample_value}")
    return samples


def clear_and_rebuild_samples(bs):
    # Prefer BlendSpaceLibrary / AnimationLibrary helpers if present
    helpers = []
    for name in (
        "BlendSpaceLibrary",
        "AnimationBlendSpaceLibrary",
        "BlendSpaceModifiers",
    ):
        if hasattr(unreal, name):
            helpers.append(getattr(unreal, name))
            log(f"found {name}: {[m for m in dir(getattr(unreal, name)) if 'sample' in m.lower() or 'blend' in m.lower()]}")

    # Try unreal.BlendSpaceUtilities / EditorAssetLibrary no-op; use notify + sample API
    # UE5: BlendSpace.add_sample exists on some versions via editor scripting
    added = 0
    # Clear existing if API allows
    try:
        if hasattr(bs, "empty_samples"):
            bs.empty_samples()
            log("empty_samples()")
    except Exception as exc:
        log(f"empty_samples: {exc}")

    try:
        # Some versions: AnimationLibrary / EditorAnimationUtils
        eal = getattr(unreal, "AnimationLibrary", None)
        if eal:
            log(f"AnimationLibrary methods: {[m for m in dir(eal) if 'blend' in m.lower() or 'sample' in m.lower()]}")
    except Exception:
        pass

    # Use BlendSpaceFactory path: delete & recreate is safer
    return rebuild_bs_asset()


def rebuild_bs_asset():
    sk = load("/Game/Characters/Mannequins/Meshes/SK_Mannequin")
    preview = unreal.EditorAssetLibrary.load_asset(
        "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
    )
    if unreal.EditorAssetLibrary.does_asset_exist(BS):
        unreal.EditorAssetLibrary.delete_asset(BS)

    factory = unreal.BlendSpaceFactoryNew()
    factory.set_editor_property("target_skeleton", sk)
    if preview:
        try:
            factory.set_editor_property("preview_skeletal_mesh", preview)
        except Exception:
            pass
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    bs = asset_tools.create_asset(
        "BS_WalkRun_Sword",
        "/Game/Characters/Mannequins/Anims/Unarmed",
        unreal.BlendSpace,
        factory,
    )
    if not bs:
        raise RuntimeError("create BS failed")

    # Axis setup
    try:
        # X = Direction, Y = Speed (common for strafe BS)
        x = unreal.BlendParameter()
        x.set_editor_property("display_name", "Direction")
        x.set_editor_property("min", -180.0)
        x.set_editor_property("max", 180.0)
        x.set_editor_property("grid_num", 9)
        y = unreal.BlendParameter()
        y.set_editor_property("display_name", "Speed")
        y.set_editor_property("min", 0.0)
        y.set_editor_property("max", 600.0)
        y.set_editor_property("grid_num", 4)
        bs.set_editor_property("blend_parameters", [x, y])
    except Exception as exc:
        log(f"blend_parameters: {exc}")
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
        except Exception as exc2:
            log(f"params alt: {exc2}")

    # Deduplicate sample points (same XY only once)
    unique = {}
    for name, dx, spd in SAMPLES:
        # Prefer proper walk B90 only once; our list has overlapping -90 walk walk B_L_90 with F_L_90
        # Use a curated unique set below instead
        pass

    curated = [
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
        ("Run_Loop_F_L_90_Seq_RTG", -90.0, 600.0),
        ("Run_Loop_F_R_90_Seq_RTG", 90.0, 600.0),
        ("Run_Loop_B_180_Seq_RTG", 180.0, 600.0),
        ("Run_Loop_B_180_Seq_RTG", -180.0, 600.0),
    ]

    add_fn = None
    if hasattr(bs, "add_sample"):
        add_fn = bs.add_sample
        log("using bs.add_sample")
    else:
        # Editor scripting object
        try:
            mod = unreal.AnimationBlendSpaceLibrary
            log(f"AnimationBlendSpaceLibrary: {dir(mod)}")
        except Exception:
            pass

    added = 0
    for name, dx, spd in curated:
        path = f"{RTG}/{name}"
        if not unreal.EditorAssetLibrary.does_asset_exist(path):
            log(f"MISSING sample anim {path}")
            continue
        anim = load(path)
        ok = False
        # Try multiple APIs
        for call in (
            lambda: bs.add_sample(anim, unreal.Vector(dx, spd, 0.0)),
            lambda: bs.add_sample(unreal.Vector(dx, spd, 0.0), anim),
            lambda: unreal.BlendSpaceLibrary.add_sample(bs, anim, unreal.Vector(dx, spd, 0.0))
            if hasattr(unreal, "BlendSpaceLibrary")
            else (_ for _ in ()).throw(Exception("no lib")),
        ):
            try:
                call()
                ok = True
                break
            except Exception:
                continue
        if not ok:
            # Manual BlendSample append
            try:
                sample = unreal.BlendSample()
                sample.set_editor_property("animation", anim)
                sample.set_editor_property("sample_value", unreal.Vector(dx, spd, 0.0))
                data = list(bs.get_editor_property("sample_data") or [])
                data.append(sample)
                bs.set_editor_property("sample_data", data)
                ok = True
            except Exception as exc:
                log(f"manual sample fail {name}: {exc}")
        if ok:
            added += 1
            log(f"added {name} ({dx},{spd})")
        else:
            log(f"FAILED add {name}")

    unreal.EditorAssetLibrary.save_asset(BS, only_if_is_dirty=False)
    log(f"rebuild done added={added}")
    return load(BS)


def rebind_abp(bs):
    abp = load(ABP)
    replaced = 0
    lib = unreal.SubobjectDataBlueprintFunctionLibrary
    # Walk anim graph nodes via ObjectIterator
    for cls_name in (
        "AnimGraphNode_BlendSpacePlayer",
        "AnimGraphNode_BlendSpaceEvaluator",
    ):
        cls = getattr(unreal, cls_name, None)
        if not cls:
            continue
        try:
            it = unreal.ObjectIterator(cls)
        except Exception as exc:
            log(f"iter {cls_name}: {exc}")
            continue
        for obj in it:
            try:
                path = obj.get_path_name()
            except Exception:
                continue
            if "ABP_StrafeLocomotion" not in path:
                continue
            for prop in ("blend_space", "BlendSpace"):
                try:
                    old = obj.get_editor_property(prop)
                    obj.set_editor_property(prop, bs)
                    replaced += 1
                    log(f"ABP node {obj.get_name()} {old} -> {bs.get_name()}")
                    break
                except Exception as exc:
                    log(f"set prop {prop}: {exc}")
    log(f"ABP blendspace nodes updated: {replaced}")

    # Also check sequence players still pointing at MM_Idle in locomotion (informational)
    seq_cls = getattr(unreal, "AnimGraphNode_SequencePlayer", None)
    if seq_cls:
        try:
            for obj in unreal.ObjectIterator(seq_cls):
                path = obj.get_path_name()
                if "ABP_StrafeLocomotion" not in path:
                    continue
                for prop in ("sequence", "Sequence"):
                    try:
                        seq = obj.get_editor_property(prop)
                        log(f"SeqPlayer {obj.get_name()} -> {seq.get_path_name() if seq else None}")
                        break
                    except Exception:
                        pass
        except Exception as exc:
            log(f"seq scan: {exc}")

    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(abp)
    except Exception as exc:
        log(f"compile abp: {exc}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)

    # Ensure character uses this ABP
    bp = load(CHAR)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("anim_class", abp.generated_class())
    unreal.EditorAssetLibrary.save_asset(CHAR, only_if_is_dirty=False)
    log("character AnimClass refreshed")


def run():
    log("start")
    if not unreal.EditorAssetLibrary.does_asset_exist(BS):
        log("BS missing, rebuild")
        bs = rebuild_bs_asset()
    else:
        bs = load(BS)
        log("=== BEFORE ===")
        samples = inspect_bs(bs)
        broken = False
        if not samples:
            broken = True
        else:
            for s in samples:
                anim = None
                try:
                    anim = s.get_editor_property("animation")
                except Exception:
                    pass
                if not anim:
                    broken = True
                    break
                p = anim.get_path_name()
                if "NONE" in p or "SwordRTG" not in p and "RTG" not in p:
                    # still ok if path contains RTG asset
                    if "_RTG" not in p:
                        broken = True
                        break
        if broken:
            log("BS samples broken/missing paths — rebuilding")
            bs = rebuild_bs_asset()
        else:
            log("BS samples look valid")
    log("=== AFTER ===")
    inspect_bs(bs)
    rebind_abp(bs)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
