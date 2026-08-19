# -*- coding: utf-8 -*-
"""
Stitch crouch-walk Loop sequences so the last frames ease into frame 0.
Does not touch character/AnimBP crouch logic.
"""
from __future__ import annotations

import unreal

CROUCH_DIR = "/Game/Sword_Animations/Animations/Sequence1/Crouch"
BLEND_FRAC = 0.18
BLEND_MIN = 4
BLEND_MAX = 10


def log(m):
    unreal.log(f"[StitchCrouchLoop] {m}")


def smoothstep(t):
    t = 0.0 if t < 0.0 else (1.0 if t > 1.0 else t)
    return t * t * (3.0 - 2.0 * t)


def qslerp(a, b, t):
    try:
        return unreal.MathLibrary.quat_slerp(a, b, t)
    except Exception:
        try:
            return unreal.MathLibrary.qlerp(a, b, t, True)
        except Exception:
            return b if t >= 1.0 else a


def vlerp(a, b, t):
    try:
        return unreal.MathLibrary.vlerp(a, b, t)
    except Exception:
        return a + (b - a) * t


def as_vec(v):
    return unreal.Vector(float(v.x), float(v.y), float(v.z))


def as_quat(q):
    return unreal.Quat(float(q.x), float(q.y), float(q.z), float(q.w))


def bone_names(model):
    try:
        names = model.get_bone_track_names()
        if names:
            return [unreal.Name(str(n)) for n in names]
    except Exception as e:
        log(f"get_bone_track_names ret: {e}")
    names = unreal.Array(unreal.Name)
    try:
        model.get_bone_track_names(names)
        return list(names)
    except Exception as e:
        log(f"get_bone_track_names out: {e}")
        return []


def expand_keys(keys, nkeys):
    keys = list(keys or [])
    if not keys:
        return None
    if len(keys) == 1:
        return keys * nkeys
    if len(keys) == nkeys:
        return keys
    return None


def track_keys(model, name, nkeys):
    try:
        track = model.get_bone_track_by_name(name)
    except Exception as e:
        log(f"get_bone_track_by_name {name}: {e}")
        return None
    try:
        raw = track.internal_track_data
    except Exception:
        try:
            raw = track.get_editor_property("internal_track_data")
        except Exception as e:
            log(f"internal_track_data {name}: {e}")
            return None
    pos = expand_keys(raw.pos_keys, nkeys)
    rot = expand_keys(raw.rot_keys, nkeys)
    scl = expand_keys(raw.scale_keys, nkeys)
    if pos is None or rot is None:
        log(
            f"  skip {name} pos={len(list(raw.pos_keys or []))} rot={len(list(raw.rot_keys or []))}"
        )
        return None
    if scl is None:
        scl = [unreal.Vector(1.0, 1.0, 1.0)] * nkeys
    return (
        [as_vec(p) for p in pos],
        [as_quat(r) for r in rot],
        [as_vec(s) for s in scl],
    )


def is_root_name(name):
    s = str(name).lower()
    return s in ("root", "b_root", "armature")


def get_model_and_controller(seq):
    ctrl = None
    model = None
    for name in ("controller", "Controller"):
        try:
            ctrl = seq.get_editor_property(name)
            if ctrl:
                break
        except Exception:
            pass
    for name in ("data_model_interface", "data_model", "DataModelInterface", "DataModel"):
        try:
            model = seq.get_editor_property(name)
            if model:
                break
        except Exception:
            pass
    if ctrl and not model:
        for getter in ("get_model_interface", "get_model"):
            try:
                model = getattr(ctrl, getter)()
                if model:
                    break
            except Exception:
                pass
    if model and not ctrl:
        try:
            ctrl = unreal.AnimDataController()
            ctrl.set_model(model)
        except Exception as e:
            log(f"new AnimDataController: {e}")
    return model, ctrl


def stitch(seq):
    model, ctrl = get_model_and_controller(seq)
    if not model or not ctrl:
        raise RuntimeError("no data model/controller")
    nkeys = int(model.get_number_of_keys())
    if nkeys < 8:
        log(f"skip {seq.get_name()} keys={nkeys}")
        return False

    blend = max(BLEND_MIN, min(BLEND_MAX, int(nkeys * BLEND_FRAC)))
    start = nkeys - blend
    names = bone_names(model)
    if not names:
        log(f"no bones {seq.get_name()}")
        return False

    try:
        ctrl.open_bracket("Stitch crouch loop")
    except Exception:
        try:
            ctrl.open_bracket(unreal.Text("Stitch crouch loop"))
        except Exception as e:
            log(f"open_bracket: {e}")

    changed = 0
    first_err = None
    for name in names:
        packed = track_keys(model, name, nkeys)
        if not packed:
            continue
        pos, rot, scl = packed
        first_p, first_r, first_s = pos[0], rot[0], scl[0]
        root = is_root_name(name)
        last_i = nkeys - 1
        new_p, new_r, new_s = [], [], []
        for i in range(nkeys):
            if i < start:
                new_p.append(pos[i])
                new_r.append(rot[i])
                new_s.append(scl[i])
                continue
            t = smoothstep(float(i - start) / float(max(1, last_i - start)))
            if root:
                cur = pos[i]
                new_p.append(unreal.Vector(cur.x, cur.y, vlerp(cur, first_p, t).z))
                new_r.append(qslerp(rot[i], first_r, t))
                new_s.append(vlerp(scl[i], first_s, t))
            else:
                new_p.append(vlerp(pos[i], first_p, t))
                new_r.append(qslerp(rot[i], first_r, t))
                new_s.append(vlerp(scl[i], first_s, t))
        if not root:
            new_p[-1] = first_p
            new_r[-1] = first_r
            new_s[-1] = first_s
        else:
            new_r[-1] = first_r
            new_p[-1] = unreal.Vector(new_p[-1].x, new_p[-1].y, first_p.z)
            new_s[-1] = first_s

        ok = False
        try:
            ok = bool(ctrl.set_bone_track_keys(name, new_p, new_r, new_s, True))
        except Exception as e:
            first_err = first_err or f"set {name}: {e}"
            try:
                ok = bool(ctrl.set_bone_track_keys(name, new_p, new_r, new_s))
            except Exception as e2:
                first_err = first_err or f"set2 {name}: {e2}"
        if ok:
            changed += 1

    try:
        ctrl.close_bracket()
    except Exception:
        pass

    for prop, val in (
        ("enable_root_motion", False),
        ("force_root_lock", True),
    ):
        try:
            seq.set_editor_property(prop, val)
        except Exception:
            pass

    extra = f" err={first_err}" if first_err and changed == 0 else ""
    log(f"{seq.get_name()} keys={nkeys} blend={blend} bones={changed}/{len(names)}{extra}")
    return changed > 0


def main():
    assets = unreal.EditorAssetLibrary.list_assets(CROUCH_DIR, recursive=False)
    loops = [p.split(".")[0] for p in assets if "Crouch_Loop" in p]
    log(f"found {len(loops)} loop assets")
    n_ok = 0
    for path in sorted(loops):
        seq = unreal.EditorAssetLibrary.load_asset(path)
        if not seq:
            log(f"load fail {path}")
            continue
        try:
            if stitch(seq):
                unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
                n_ok += 1
        except Exception as e:
            log(f"FAIL {path}: {e}")
    log(f"DONE saved={n_ok}/{len(loops)}")


main()
