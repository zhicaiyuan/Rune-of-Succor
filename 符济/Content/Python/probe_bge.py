# -*- coding: utf-8 -*-
import unreal

bel = unreal.BlueprintEditorLibrary
CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"


def log(m):
    unreal.log(f"[ProbeBGE] {m}")


bge_cls = unreal.BlueprintGraphEditor
# docs
for m in (
    "get_graph_editor",
    "get_graph_editor_by_name",
    "add_call_function_node",
    "add_branch_node",
    "add_get_member_variable_node",
    "add_set_member_variable_node",
    "create_node_from_name",
    "list_available_nodes",
    "retarget_node_class",
):
    fn = getattr(bge_cls, m, None)
    log(f"{m} doc={getattr(fn, '__doc__', None)}")

# How to obtain editor instance?
bp = unreal.EditorAssetLibrary.load_asset(CHAR)
for args in (
    (bp,),
    (bp, "EventGraph"),
):
    try:
        r = bge_cls.get_graph_editor(*args)
        log(f"get_graph_editor{args} -> {r}")
    except Exception as e:
        log(f"get_graph_editor{args}: {e}")
    try:
        r = bge_cls.get_graph_editor_by_name(*args)
        log(f"get_graph_editor_by_name{args} -> {r}")
    except Exception as e:
        log(f"get_graph_editor_by_name{args}: {e}")

# static_class CDO
cdo = unreal.get_default_object(bge_cls.static_class())
log(f"CDO={cdo}")
for m in ("get_graph_editor", "get_graph_editor_by_name"):
    try:
        r = getattr(cdo, m)(bp)
        log(f"cdo.{m}(bp) -> {r}")
    except Exception as e:
        log(f"cdo.{m}: {e}")

# AssetEditorSubsystem open editor?
aes = unreal.get_editor_subsystem(unreal.AssetEditorSubsystem)
log(f"AES={aes}")
try:
    aes.open_editor_for_assets([bp])
    log("opened editor")
except Exception as e:
    log(f"open_editor: {e}")

for args in ((bp,), (bp, "EventGraph"), ("EventGraph",)):
    try:
        r = unreal.BlueprintGraphEditor.get_graph_editor(*args)
        log(f"BGE.get_graph_editor{args} -> {r}")
    except Exception as e:
        log(f"BGE.get_graph_editor{args}: {e}")
    try:
        r = unreal.BlueprintGraphEditor.get_graph_editor_by_name(*args)
        log(f"BGE.get_graph_editor_by_name{args} -> {r}")
    except Exception as e:
        log(f"BGE.get_graph_editor_by_name{args}: {e}")

# After open, find instances
for obj in unreal.ObjectIterator(unreal.BlueprintGraphEditor):
    log(f"BGE instance {obj.get_path_name()}")
    try:
        g = obj.get_graph()
        log(f"  graph={g}")
    except Exception as e:
        log(f"  get_graph: {e}")

# Try add_call_function_node on any instance
fn = unreal.load_object(None, "/Script/Engine.Character:PlayAnimMontage")
for obj in unreal.ObjectIterator(unreal.BlueprintGraphEditor):
    try:
        g = obj.get_graph()
        if not g or g.get_name() != "EventGraph":
            continue
        if "BP_ThirdPersonCharacter" not in g.get_path_name():
            continue
        log(f"using editor for {g.get_path_name()}")
        # try signatures
        for call in (
            lambda: obj.add_call_function_node(fn, unreal.Vector2D(0, 0)),
            lambda: obj.add_call_function_node(fn, unreal.IntPoint(0, 0)),
            lambda: obj.add_call_function_node(fn),
            lambda: obj.add_call_function_node(unreal.Name("PlayAnimMontage"), unreal.IntPoint(0, 0)),
            lambda: obj.add_call_function_node("PlayAnimMontage", unreal.IntPoint(0, 0)),
            lambda: obj.add_call_function_node(fn, 0, 0),
        ):
            try:
                r = call()
                log(f"add_call_function_node -> {r} title={bel.get_node_title(r) if r else None}")
                if r:
                    break
            except Exception as e:
                log(f"add_call attempt: {e}")
        # branch
        try:
            br = obj.add_branch_node(unreal.IntPoint(200, 0))
            log(f"add_branch_node -> {br}")
        except Exception as e:
            log(f"add_branch: {e}")
        # variable get
        try:
            vg = obj.add_get_member_variable_node(unreal.Name("SS_WasMoving"), unreal.IntPoint(0, 200))
            log(f"add_get_member_variable_node -> {vg}")
        except Exception as e:
            log(f"add_get_member: {e}")
        try:
            vg = obj.add_get_member_variable_node("SS_WasMoving", unreal.IntPoint(0, 200))
            log(f"add_get_member str -> {vg}")
        except Exception as e:
            log(f"add_get_member str: {e}")
        # create_node_from_name
        try:
            nodes = obj.list_available_nodes()
            log(f"available sample={list(nodes)[:30] if nodes else None}")
        except Exception as e:
            log(f"list_available: {e}")
        break
    except Exception as e:
        log(f"editor use: {e}")

# Also try ABP graph editor for Montage_Play on AnimInstance
abp = unreal.EditorAssetLibrary.load_asset(ABP)
try:
    aes.open_editor_for_assets([abp])
except Exception as e:
    log(f"open abp: {e}")

log("done")
