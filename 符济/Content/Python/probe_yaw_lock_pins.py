# -*- coding: utf-8 -*-
"""Dump pin names for existing YL_ nodes and try create GetBoolPropertyByName."""
import unreal

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"


def dump(n, label):
    if not n:
        print("[Probe] === %s IS NONE ===" % label)
        return
    cls = "?"
    try:
        cls = n.get_class().get_name()
    except Exception as e:
        cls = "err:%s" % e
    print("[Probe] === %s (%s) ===" % (label, cls))
    try:
        for p in (bel.list_input_pins(n) or []):
            print("  IN  %s cat=%s" % (p.get_pin_name(), getattr(p.pin_type, "pin_category", "?")))
    except Exception as e:
        print("  IN err %s" % e)
    try:
        for p in (bel.list_output_pins(n) or []):
            print("  OUT %s cat=%s" % (p.get_pin_name(), getattr(p.pin_type, "pin_category", "?")))
    except Exception as e:
        print("  OUT err %s" % e)
    for fn in ("find_self_pin", "find_execute_pin", "find_then_pin", "find_result_pin"):
        try:
            p = getattr(bel, fn)(n)
            print("  %s -> %s" % (fn, p.get_pin_name() if p else None))
        except Exception as e:
            print("  %s err %s" % (fn, e))


bp = unreal.EditorAssetLibrary.load_asset(CHAR)
ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
graph = ed.get_graph()

for n in graph.nodes:
    try:
        nm = n.get_name()
    except Exception:
        continue
    if nm.startswith("YL_"):
        dump(n, nm)

paths = [
    "/Script/Engine.KismetSystemLibrary:GetBoolPropertyByName",
    "/Script/Engine.KismetSystemLibrary:GetBoolPropertyByName",
    "GetBoolPropertyByName",
]
for p in paths:
    n = None
    try:
        n = ed.add_call_function_node(p)
    except Exception as e:
        print("[Probe] create %s exception %s" % (p, e))
    print("[Probe] create %s -> %s" % (p, n))
    if n:
        dump(n, "NEW " + p)
        try:
            ed.remove_node(n)
        except Exception:
            pass

# also try set_member Orient again
set_or = ed.add_set_member_variable_node(
    "OrientRotationToMovement", "/Script/Engine.CharacterMovementComponent"
)
dump(set_or, "NEW SetOrient")
if set_or:
    try:
        ed.remove_node(set_or)
    except Exception:
        pass

# SW_SetProp from sync walk for comparison
for n in graph.nodes:
    try:
        nm = n.get_name()
    except Exception:
        continue
    if nm in ("SW_SetProp", "SW_GetAnim", "SW_LitName"):
        dump(n, nm)

print("[Probe] done")
