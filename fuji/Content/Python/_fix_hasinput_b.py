import unreal
bel=unreal.BlueprintEditorLibrary
BGE=unreal.BlueprintGraphEditor
ABP="/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
abp=unreal.EditorAssetLibrary.load_asset(ABP)
ed=BGE.get_graph_editor_by_name(abp,"EventGraph")
g=ed.get_graph()
for n in unreal.ObjectIterator(unreal.EdGraphNode):
    if n.get_outer()==g and n.get_name()=="TV_HasInput":
        for p in bel.list_input_pins(n) or []:
            if str(p.get_pin_name())=="B":
                p.set_pin_value("0.1")
                unreal.log(f"[FixB] B={p.get_pin_value()}")
bel.compile_blueprint(abp)
unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
unreal.log("[FixB] done")
