# -*- coding: utf-8 -*-
from __future__ import annotations

import unreal

BP = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def log(m):
    unreal.log(f"[Probe] {m}")


def run():
    bp = unreal.EditorAssetLibrary.load_asset(BP)
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    handles = subsystem.k2_gather_subobject_data_for_blueprint(bp)
    log(f"handles={len(handles)}")
    log(f"subsystem methods sample: {[m for m in dir(subsystem) if not m.startswith('_')][:80]}")

    # Try SubobjectDataBlueprintFunctionLibrary
    lib = None
    for name in (
        "SubobjectDataBlueprintFunctionLibrary",
        "SubobjectDataFunctionLibrary",
    ):
        try:
            lib = getattr(unreal, name)
            log(f"found lib {name}: {[m for m in dir(lib) if not m.startswith('_')]}")
            break
        except Exception:
            pass

    for i, h in enumerate(handles):
        log(f"--- handle {i} type={type(h)} dir={[m for m in dir(h) if not m.startswith('_')][:40]}")
        # try many accessors
        candidates = []
        for meth in (
            "get_object",
            "get_data",
            "get_variable_name",
            "get_display_name",
            "get_class",
            "is_component",
            "is_handle_valid",
        ):
            if hasattr(h, meth):
                try:
                    candidates.append(f"{meth}={getattr(h, meth)()}")
                except Exception as exc:
                    candidates.append(f"{meth}ERR={exc}")
        log("  handle attrs: " + " | ".join(candidates))

        if lib:
            for meth in (
                "get_object",
                "get_blueprint",
                "get_variable_name",
                "get_display_name",
                "is_component",
                "is_instanced_component",
                "get_data",
            ):
                if hasattr(lib, meth):
                    try:
                        val = getattr(lib, meth)(h)
                        log(f"  lib.{meth} => {val} ({type(val)})")
                        if isinstance(val, unreal.Object):
                            log(f"    name={val.get_name()} cls={val.get_class().get_name()}")
                            if isinstance(val, unreal.SpringArmComponent) or "Spring" in val.get_class().get_name():
                                try:
                                    val.set_editor_property("use_pawn_control_rotation", True)
                                    log(f"    SET boom UsePawnControlRotation={val.get_editor_property('use_pawn_control_rotation')}")
                                except Exception as exc:
                                    log(f"    set boom err {exc}")
                    except Exception as exc:
                        log(f"  lib.{meth} ERR {exc}")

        for meth in (
            "get_object_for_handle",
            "k2_find_subobject_data_from_handle",
            "get_data_for_handle",
            "find_handle_for_object",
        ):
            if hasattr(subsystem, meth):
                try:
                    val = getattr(subsystem, meth)(h)
                    log(f"  sub.{meth} => {val} ({type(val)})")
                except Exception as exc:
                    try:
                        val = getattr(subsystem, meth)(bp, h)
                        log(f"  sub.{meth}(bp,h) => {val}")
                    except Exception as exc2:
                        log(f"  sub.{meth} ERR {exc} / {exc2}")

    # Also inspect CDO component array via BlueprintEditorLibrary
    gen = bp.generated_class()
    cdo = unreal.get_default_object(gen)
    log(f"CDO={cdo}")
    try:
        comps = cdo.get_components_by_class(unreal.ActorComponent)
        log(f"get_components_by_class ActorComponent count={len(comps)}")
        for c in comps:
            log(f"  comp {c.get_name()} {c.get_class().get_name()}")
    except Exception as exc:
        log(f"comps err {exc}")

    # Inherited components via export text?
    try:
        root = cdo.get_editor_property("root_component")
        log(f"root={root}")
        if root:
            kids = root.get_children_components(True)
            log(f"children={len(kids)}")
            for k in kids:
                log(f"  child {k.get_name()} {k.get_class().get_name()}")
    except Exception as exc:
        log(f"root/children {exc}")

    # Try unreal.EditorUtilityLibrary / BlueprintEditorLibrary get components
    for name in dir(unreal.BlueprintEditorLibrary):
        if "component" in name.lower() or "subobject" in name.lower():
            log(f"BPLIB {name}")


if __name__ == "__main__":
    run()
else:
    run()
