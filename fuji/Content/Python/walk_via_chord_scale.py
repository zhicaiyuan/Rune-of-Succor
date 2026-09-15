# -*- coding: utf-8 -*-
"""
Walk without Character graph:
- When IA_Walk (LeftAlt) held: scale Move input to 200/600 via Chord+Scalar mappings
- When released: normal Move mappings (optionally blocked while walking via ChordBlocker)
"""

from __future__ import annotations

import unreal

IMC = "/Game/Input/IMC_Default"
IA_WALK = "/Game/Input/Actions/IA_Walk"
IA_MOVE = "/Game/Input/Actions/IA_Move"
WALK_SCALE = 200.0 / 600.0  # ~0.333


def log(m):
    unreal.log(f"[WalkChord] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def make_key(name: str):
    key = unreal.Key()
    key.set_editor_property("key_name", unreal.Name(name))
    return key


def get_dkm_mappings(imc):
    dkm = imc.get_editor_property("default_key_mappings")
    return dkm, list(dkm.get_editor_property("mappings") or [])


def set_dkm_mappings(imc, dkm, mappings):
    dkm.set_editor_property("mappings", mappings)
    imc.set_editor_property("default_key_mappings", dkm)


def make_scalar_modifier(scale: float):
    # UInputModifierScalar
    for cls_name in ("InputModifierScalar", "InputModifierNegate", "InputModifierDeadZone"):
        if hasattr(unreal, cls_name):
            log(f"has {cls_name}")
    mod = None
    try:
        mod = unreal.InputModifierScalar()
        # scalar property
        for prop in ("scalar", "Scalar"):
            try:
                # often FVector
                mod.set_editor_property(prop, unreal.Vector(scale, scale, scale))
                log(f"scalar via {prop}={scale}")
                break
            except Exception as exc:
                log(f"scalar {prop}: {exc}")
                try:
                    mod.set_editor_property(prop, scale)
                    break
                except Exception as exc2:
                    log(f"scalar f {prop}: {exc2}")
    except Exception as exc:
        log(f"InputModifierScalar: {exc}")
        # new_object
        cls = unreal.load_class(None, "/Script/EnhancedInput.InputModifierScalar")
        if cls:
            mod = unreal.new_object(cls)
            try:
                mod.set_editor_property("scalar", unreal.Vector(scale, scale, scale))
            except Exception as exc2:
                log(f"new scalar: {exc2}")
    return mod


def make_chord_trigger(ia_walk):
    # UInputTriggerChordAction
    trig = None
    try:
        trig = unreal.InputTriggerChordAction()
    except Exception:
        cls = unreal.load_class(None, "/Script/EnhancedInput.InputTriggerChordAction")
        if cls:
            trig = unreal.new_object(cls)
    if not trig:
        log("no ChordAction trigger class")
        return None
    for prop in ("chord_action", "ChordAction", "action", "Action"):
        try:
            trig.set_editor_property(prop, ia_walk)
            log(f"chord.{prop} set")
            break
        except Exception as exc:
            log(f"chord.{prop}: {exc}")
    return trig


def make_chord_blocker(ia_walk):
    trig = None
    try:
        trig = unreal.InputTriggerChordBlocker()
    except Exception:
        cls = unreal.load_class(None, "/Script/EnhancedInput.InputTriggerChordBlocker")
        if cls:
            trig = unreal.new_object(cls)
    if not trig:
        log("no ChordBlocker class")
        return None
    for prop in ("chord_action", "ChordAction", "action", "Action"):
        try:
            trig.set_editor_property(prop, ia_walk)
            log(f"blocker.{prop} set")
            break
        except Exception as exc:
            log(f"blocker.{prop}: {exc}")
    return trig


def run():
    log("start")
    imc = load(IMC)
    ia_walk = load(IA_WALK)
    ia_move = load(IA_MOVE)
    dkm, mappings = get_dkm_mappings(imc)
    log(f"mappings before={len(mappings)}")

    # Ensure LeftAlt -> IA_Walk
    has_walk = any(
        m.get_editor_property("action")
        and "IA_Walk" in m.get_editor_property("action").get_path_name()
        for m in mappings
    )
    if not has_walk:
        m = unreal.EnhancedActionKeyMapping()
        m.set_editor_property("action", ia_walk)
        m.set_editor_property("key", make_key("LeftAlt"))
        mappings.append(m)
        log("added LeftAlt IA_Walk")

    scalar = make_scalar_modifier(WALK_SCALE)
    chord = make_chord_trigger(ia_walk)
    blocker = make_chord_blocker(ia_walk)

    # Collect existing Move key names (keyboard only for walk-scaled duplicates)
    move_keys = []
    for m in mappings:
        a = m.get_editor_property("action")
        if a and "IA_Move" in a.get_path_name():
            k = m.get_editor_property("key")
            kn = str(k.get_editor_property("key_name")) if k else ""
            move_keys.append((m, kn))
            log(f"existing move key={kn}")

    # Add ChordBlocker to existing Move mappings so they don't fire while Alt held
    if blocker:
        for m, kn in move_keys:
            try:
                triggers = list(m.get_editor_property("triggers") or [])
                # avoid dup
                triggers = [t for t in triggers if t and "ChordBlocker" not in t.get_class().get_name()]
                triggers.append(blocker)
                m.set_editor_property("triggers", triggers)
                log(f"blocker on Move {kn}")
            except Exception as exc:
                log(f"set blocker {kn}: {exc}")

    # Add walk-scaled Move mappings for W/A/S/D (and arrows) with Chord+Scalar
    # Copy modifiers from original mapping of same key if possible
    keys_to_scale = {"W", "A", "S", "D", "Up", "Down", "Left", "Right"}
    for m, kn in move_keys:
        if kn not in keys_to_scale:
            continue
        # Check if walk-scaled mapping already exists (detect by scalar modifier presence + chord)
        new_m = unreal.EnhancedActionKeyMapping()
        new_m.set_editor_property("action", ia_move)
        new_m.set_editor_property("key", make_key(kn))
        # copy modifiers from original then add scalar
        try:
            mods = list(m.get_editor_property("modifiers") or [])
        except Exception:
            mods = []
        if scalar:
            mods = list(mods) + [scalar]
        try:
            new_m.set_editor_property("modifiers", mods)
        except Exception as exc:
            log(f"set mods: {exc}")
        if chord:
            try:
                new_m.set_editor_property("triggers", [chord])
            except Exception as exc:
                log(f"set chord trigger: {exc}")
        mappings.append(new_m)
        log(f"added walk-scaled Move {kn}")

    set_dkm_mappings(imc, dkm, mappings)
    unreal.EditorAssetLibrary.save_asset(IMC, only_if_is_dirty=False)

    dkm, mappings = get_dkm_mappings(imc)
    log(f"mappings after={len(mappings)}")
    for m in mappings:
        a = m.get_editor_property("action")
        k = m.get_editor_property("key")
        kn = k.get_editor_property("key_name") if k else None
        n_tr = len(list(m.get_editor_property("triggers") or []))
        n_mo = len(list(m.get_editor_property("modifiers") or []))
        log(f"  {kn} -> {a.get_name() if a else None} trig={n_tr} mod={n_mo}")
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
