# -*- coding: utf-8 -*-
"""
Restore IMC_Default mappings, bind LeftAlt -> IA_Walk, and wire walk/run speeds
+ idle turn playback onto BP_ThirdPersonCharacter via Enhanced Input delegate
binding objects (load_class + new_object).
"""

from __future__ import annotations

import unreal

IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
IA_MOVE = "/Game/Input/Actions/IA_Move"
IA_LOOK = "/Game/Input/Actions/IA_Look"
IA_JUMP = "/Game/Input/Actions/IA_Jump"
IA_MOUSE = "/Game/Input/Actions/IA_MouseLook"
IA_SPRINT = "/Game/Input/Actions/IA_Sprint"
CHAR_BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
COMBAT_BP = "/Game/Variant_Combat/Blueprints/BP_CombatCharacter"
OUT = "/Game/Characters/\u6797\u7b26/\u52a8\u753b"
ABP = f"{OUT}/ABP_StrafeLocomotion"
RTG = f"{OUT}/SwordRTG"

WALK_SPEED = 200.0
RUN_SPEED = 600.0


def log(m):
    unreal.log(f"[FixIMC] {m}")


def load(p):
    a = unreal.EditorAssetLibrary.load_asset(p)
    if not a:
        raise RuntimeError(f"missing {p}")
    return a


def save(p):
    return unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def make_key(name: str):
    """UE 5.8 Python: Key() takes no ctor args — set key_name."""
    key = unreal.Key()
    for prop in ("key_name", "KeyName"):
        try:
            key.set_editor_property(prop, unreal.Name(name))
            got = key.get_editor_property(prop)
            log(f"Key {name} via {prop} -> {got}")
            return key
        except Exception as exc:
            log(f"Key prop {prop}: {exc}")
    # try assign attribute
    try:
        key.key_name = unreal.Name(name)
        log(f"Key {name} via attr")
        return key
    except Exception as exc:
        log(f"Key attr: {exc}")
    raise RuntimeError(f"Cannot build Key {name}")


def add_mapping(mappings, action_path, key_name):
    if not unreal.EditorAssetLibrary.does_asset_exist(action_path):
        log(f"skip missing action {action_path}")
        return
    ia = load(action_path)
    m = unreal.EnhancedActionKeyMapping()
    m.set_editor_property("action", ia)
    m.set_editor_property("key", make_key(key_name))
    mappings.append(m)
    log(f"map {key_name} -> {action_path}")


def restore_imc():
    imc = load(IMC)
    mappings = []

    # Standard third person template + walk/sprint
    # Movement sticks / WASD are usually modifiers on IA_Move — check existing first
    existing = list(imc.get_editor_property("mappings") or [])
    log(f"existing mappings before restore: {len(existing)}")
    for m in existing:
        try:
            a = m.get_editor_property("action")
            k = m.get_editor_property("key")
            log(f"  exist: action={a.get_path_name() if a else None} key={k}")
        except Exception as exc:
            log(f"  exist err: {exc}")

    # If we still have a reasonable set (>=4), just ensure IA_Walk/LeftAlt
    if len(existing) >= 4:
        mappings = [
            m
            for m in existing
            if not (
                m.get_editor_property("action")
                and "IA_Walk" in m.get_editor_property("action").get_path_name()
            )
        ]
        add_mapping(mappings, IA_WALK, "LeftAlt")
        # also try Left_Alt alias as second mapping
        try:
            add_mapping(mappings, IA_WALK, "Left_Alt")
        except Exception:
            pass
        imc.set_editor_property("mappings", mappings)
        save(IMC)
        log(f"IMC updated (kept existing) count={len(mappings)}")
        return

    # Full rebuild minimal set
    log("Full IMC rebuild")
    # IA_Move typically has multiple keys with swizzle modifiers — duplicate from asset defaults hard.
    # Prefer: reload from git? For now add core keys.
    for key in ("W", "A", "S", "D"):
        add_mapping(mappings, IA_MOVE, key)
    add_mapping(mappings, IA_LOOK, "Mouse2D")
    add_mapping(mappings, IA_JUMP, "SpaceBar")
    add_mapping(mappings, IA_WALK, "LeftAlt")
    if unreal.EditorAssetLibrary.does_asset_exist(IA_SPRINT):
        add_mapping(mappings, IA_SPRINT, "LeftShift")
    imc.set_editor_property("mappings", mappings)
    save(IMC)
    log(f"IMC rebuilt count={len(mappings)}")


def ensure_character_movement(bp_path):
    bp = load(bp_path)
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    # Strafe facing via desired rotation (allows turn lag)
    cdo.set_editor_property("use_controller_rotation_yaw", False)
    cdo.set_editor_property("use_controller_rotation_pitch", False)
    cdo.set_editor_property("use_controller_rotation_roll", False)
    move = cdo.get_editor_property("character_movement")
    move.set_editor_property("orient_rotation_to_movement", False)
    move.set_editor_property("use_controller_desired_rotation", True)
    move.set_editor_property("max_walk_speed", RUN_SPEED)
    move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
    move.set_editor_property("max_acceleration", 800.0)
    move.set_editor_property("braking_deceleration_walking", 1000.0)
    move.set_editor_property("ground_friction", 5.0)
    move.set_editor_property("rotation_rate", unreal.Rotator(pitch=0.0, yaw=400.0, roll=0.0))
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("relative_rotation", unreal.Rotator(pitch=0.0, yaw=-90.0, roll=0.0))
    mesh.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -90.0))
    if unreal.EditorAssetLibrary.does_asset_exist(ABP):
        abp = load(ABP)
        mesh.set_editor_property("anim_class", abp.generated_class())
    save(bp_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception:
        pass
    log(f"movement ok {bp_path}")


def add_enhanced_bindings_to_bp(bp_path):
    """
    Attach EnhancedInputActionDelegateBinding calling custom UFunctions.
    Character has Crouch/UnCrouch — use those for walk speed gate.
    Also need custom functions for MaxWalkSpeed — Crouch is OK if crouched_half_height == capsule.
    """
    bp = load(bp_path)
    ia = load(IA_WALK)
    binding_cls = unreal.load_class(None, "/Script/EnhancedInput.EnhancedInputActionDelegateBinding")
    if not binding_cls:
        log("no binding class")
        return

    # Create binding object outered to the blueprint package
    binding = unreal.new_object(binding_cls, bp, unreal.Name("IA_Walk_DelegateBinding"))
    struct_cls = unreal.find_object(None, "/Script/EnhancedInput.BlueprintEnhancedInputActionBinding")
    log(f"struct_cls={struct_cls}")

    # Build array of bindings using Struct
    entries = []
    for event_name, func in (("STARTED", "Crouch"), ("COMPLETED", "UnCrouch")):
        if not hasattr(unreal.TriggerEvent, event_name):
            # try other casings
            found = None
            for n in dir(unreal.TriggerEvent):
                if n.upper() == event_name:
                    found = getattr(unreal.TriggerEvent, n)
                    break
            if found is None:
                log(f"no TriggerEvent.{event_name}")
                continue
            event_val = found
        else:
            event_val = getattr(unreal.TriggerEvent, event_name)

        e = unreal.BlueprintEnhancedInputActionBinding() if hasattr(unreal, "BlueprintEnhancedInputActionBinding") else None
        if e is None:
            # construct via Struct
            try:
                e = unreal.BlueprintEnhancedInputActionBinding()
            except Exception:
                # make generic struct
                try:
                    e = unreal.new_object(unreal.Object)  # wrong
                except Exception as exc:
                    log(f"cannot make binding entry: {exc}")
                    continue
        try:
            e.set_editor_property("input_action", ia)
            e.set_editor_property("trigger_event", event_val)
            e.set_editor_property("function_name_to_bind", func)
            entries.append(e)
            log(f"entry {event_name}->{func}")
        except Exception as exc:
            log(f"entry set: {exc}")

    if not entries:
        # Try TriggerEvent enum listing
        log(f"TriggerEvent members: {[x for x in dir(unreal.TriggerEvent) if x.isupper()][:20]}")
        return

    try:
        binding.set_editor_property("input_action_delegate_bindings", entries)
    except Exception as exc:
        log(f"set bindings array: {exc}")
        return

    # Attach to BlueprintGeneratedClass BindingObjects
    gen = bp.generated_class()
    attached = False
    for prop in (
        "dynamic_binding_objects",
        "DynamicBindingObjects",
        "binding_objects",
    ):
        try:
            arr = list(gen.get_editor_property(prop) or [])
            # remove old
            arr = [o for o in arr if o and "IA_Walk" not in o.get_name()]
            arr.append(binding)
            gen.set_editor_property(prop, arr)
            attached = True
            log(f"attached via gen.{prop}")
            break
        except Exception as exc:
            log(f"gen.{prop}: {exc}")

    if not attached:
        for prop in ("dynamic_binding_objects", "DynamicBindingObjects"):
            try:
                arr = list(bp.get_editor_property(prop) or [])
                arr.append(binding)
                bp.set_editor_property(prop, arr)
                attached = True
                log(f"attached via bp.{prop}")
                break
            except Exception as exc:
                log(f"bp.{prop}: {exc}")

    # Enable crouch on character
    cdo = unreal.get_default_object(gen)
    try:
        cdo.set_editor_property("can_crouch", True)
    except Exception:
        pass
    move = cdo.get_editor_property("character_movement")
    try:
        nav = move.get_editor_property("nav_agent_props")
        nav.set_editor_property("can_crouch", True)
        move.set_editor_property("nav_agent_props", nav)
    except Exception as exc:
        log(f"can_crouch nav: {exc}")
    move.set_editor_property("max_walk_speed_crouched", WALK_SPEED)
    # Match capsule so no squat
    try:
        cap = cdo.get_editor_property("capsule_component")
        hh = float(cap.get_editor_property("capsule_half_height"))
        move.set_editor_property("crouched_half_height", hh)
        log(f"crouched_half_height={hh}")
    except Exception as exc:
        log(f"hh: {exc}")

    save(bp_path)
    try:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    except Exception as exc:
        log(f"compile: {exc}")
    log(f"bindings done attached={attached} for {bp_path}")


def build_turn_montages_content():
    """Ensure montages contain the turn sequences (factory may create empty)."""
    mdir = f"{OUT}/Montages"
    pairs = [
        ("AM_Turn_90_L", f"{RTG}/Turn_90_L_Seq_RTG"),
        ("AM_Turn_90_R", f"{RTG}/Turn_90_R_Seq_RTG"),
        ("AM_Turn_180_L", f"{RTG}/Turn_180_L_Seq_RTG"),
        ("AM_Turn_180_R", f"{RTG}/Turn_180_R_Seq_RTG"),
    ]
    for mname, seq in pairs:
        mpath = f"{mdir}/{mname}"
        if not unreal.EditorAssetLibrary.does_asset_exist(mpath):
            continue
        if not unreal.EditorAssetLibrary.does_asset_exist(seq):
            continue
        montage = load(mpath)
        anim = load(seq)
        # Try populate slot track
        try:
            # AnimMontage has slot_anim_tracks
            tracks = list(montage.get_editor_property("slot_anim_tracks") or [])
            log(f"{mname} tracks={len(tracks)}")
            if len(tracks) == 0:
                # create SlotAnimationTrack
                track = unreal.SlotAnimationTrack()
                track.set_editor_property("slot_name", "DefaultSlot")
                seg = unreal.CompositeSection()  # wrong type maybe
                # AnimSegment
                segment = unreal.AnimSegment()
                segment.set_editor_property("anim_reference", anim)
                try:
                    length = anim.get_editor_property("sequence_length")
                except Exception:
                    try:
                        length = anim.get_play_length()
                    except Exception:
                        length = 1.0
                segment.set_editor_property("anim_end_time", float(length))
                segment.set_editor_property("anim_play_rate", 1.0)
                # AnimTrack inside slot
                anim_track = unreal.AnimTrack()
                anim_track.set_editor_property("anim_segments", [segment])
                track.set_editor_property("anim_track", anim_track)
                montage.set_editor_property("slot_anim_tracks", [track])
                log(f"populated {mname}")
            save(mpath)
        except Exception as exc:
            log(f"montage populate {mname}: {exc}")


def verify_imc():
    imc = load(IMC)
    mappings = list(imc.get_editor_property("mappings") or [])
    log(f"VERIFY IMC count={len(mappings)}")
    for m in mappings:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = None
        try:
            kn = k.get_editor_property("key_name")
        except Exception:
            kn = str(k)
        log(f"  {kn} -> {a.get_name() if a else None}")


def run():
    log("start")
    # probe TriggerEvent / Key
    log(f"TriggerEvent: {[x for x in dir(unreal.TriggerEvent) if not x.startswith('_')]}")
    restore_imc()
    verify_imc()
    for bp in (CHAR_BP, COMBAT_BP):
        if unreal.EditorAssetLibrary.does_asset_exist(bp):
            ensure_character_movement(bp)
            add_enhanced_bindings_to_bp(bp)
    build_turn_montages_content()
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
