import unreal
bel=unreal.BlueprintEditorLibrary
BGE=unreal.BlueprintGraphEditor
ABP="/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
abp=unreal.EditorAssetLibrary.load_asset(ABP)
ed=BGE.get_graph_editor_by_name(abp,"EventGraph")
g=ed.get_graph()
sub=norm=sel=None
for n in unreal.ObjectIterator(unreal.EdGraphNode):
    if n.get_outer()!=g: continue
    if n.get_name()=="TV_SubYaw": sub=n
    if n.get_name()=="TV_NormAxis": norm=n
    if n.get_name()=="TV_SelDelta": sel=n
def pins(n,t):
    unreal.log(f"[Norm] {t} {[str(p.get_pin_name()) for p in (bel.list_all_pins(n) or [])]}")
pins(sub,"sub"); pins(norm,"norm")
sp=None
for p in bel.list_output_pins(sub) or []:
    if str(p.get_pin_name())=="ReturnValue": sp=p
for p in bel.list_input_pins(norm) or []:
    unreal.log(f"[Norm] try {p.get_pin_name()}")
    try:
        p.break_pin_links()
    except: pass
    ok=bool(sp.try_create_connection(p)) if sp else False
    unreal.log(f"[Norm] sub->norm.{p.get_pin_name()}={ok}")
    if ok: break
# also connect sub directly to sel.A if norm fails
if sel and sp:
    ap=None
    for p in bel.list_input_pins(sel) or []:
        if str(p.get_pin_name())=="A": ap=p
    if ap:
        # Prefer NormalizeAxis out if linked
        nout=None
        for p in bel.list_output_pins(norm) or []:
            if str(p.get_pin_name())=="ReturnValue": nout=p
        linked=list(ap.list_connected_pins() or [])
        unreal.log(f"[Norm] sel.A linked={len(linked)}")
bel.compile_blueprint(abp)
unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
unreal.log("[Norm] done")
