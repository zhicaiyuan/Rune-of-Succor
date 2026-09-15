# -*- coding: utf-8 -*-
import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeVG] {m}")


bp = unreal.EditorAssetLibrary.load_asset(ABP)

# Find one VariableGet under a Locomotion transition and dump attrs
for tr in unreal.ObjectIterator(unreal.AnimStateTransitionNode):
    try:
        if tr.get_outer().get_name() != "Locomotion":
            continue
    except Exception:
        continue
    # ensure under abp
    o = tr
    ok = False
    for _ in range(12):
        if o == bp:
            ok = True
            break
        o = o.get_outer()
        if o is None:
            break
    if not ok:
        continue

    for g in unreal.ObjectIterator(unreal.EdGraph):
        if g.get_outer() != tr:
            continue
        for n in unreal.ObjectIterator(unreal.K2Node_VariableGet):
            if n.get_outer() != g:
                continue
            log(f"found VarGet under {tr.get_name()}")
            attrs = [a for a in dir(n) if "var" in a.lower() or "member" in a.lower() or "pin" in a.lower() or "ref" in a.lower()]
            log(f"attrs={attrs}")
            for a in (
                "variable_reference",
                "VariableReference",
                "get_variable_name",
                "get_var_name",
                "variable_name",
            ):
                if hasattr(n, a):
                    try:
                        log(f"hasattr {a}={getattr(n, a)}")
                    except Exception as e:
                        log(f"hasattr {a} err {e}")
            # pins
            try:
                pins = n.pins
                log(f"pins={pins}")
            except Exception as e:
                log(f"pins err {e}")
            try:
                for p in n.node_pins:
                    log(f"node_pin {p}")
            except Exception as e:
                log(f"node_pins err {e}")
            # try BlueprintEditorLibrary helpers
            bel = unreal.BlueprintEditorLibrary
            for meth in dir(bel):
                if "var" in meth.lower() or "pin" in meth.lower():
                    pass
            # Pin names via get_pin_name if available through schema
            try:
                # UE5: EdGraphNode.get_pins()
                get_pins = getattr(n, "get_pins", None) or getattr(n, "get_all_pins", None)
                if get_pins:
                    for p in get_pins():
                        log(f"pin name={p.get_pin_name()} type={p.pin_type}")
            except Exception as e:
                log(f"get_pins err {e}")

            # Try serialize
            for meth in ("get_node_title", "get_descriptive_compiled_name", "get_find_reference_search_string"):
                if hasattr(n, meth):
                    try:
                        log(f"{meth}={getattr(n, meth)()}")
                    except Exception as e:
                        try:
                            log(f"{meth}={getattr(n, meth)}")
                        except Exception as e2:
                            log(f"{meth} err {e} / {e2}")
            raise SystemExit  # only first

log("none found")
