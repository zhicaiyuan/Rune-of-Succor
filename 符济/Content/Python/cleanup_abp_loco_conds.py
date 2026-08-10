# -*- coding: utf-8 -*-
"""
Clean broken ABP sync from setup_loco_conditions_only.
Keep bool vars on ABP; wire a working copy from Character using TargetType.
Remove duplicate BlueprintUpdateAnimation events.
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixCast] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def connect(a, b):
    if not a or not b:
        return False
    try:
        return bool(a.try_create_connection(b))
    except Exception:
        try:
            return bool(b.try_create_connection(a))
        except Exception:
            return False


def pin_in(node, name):
    for cand in bel.list_input_pins(node) or []:
        try:
            if str(cand.get_pin_name()) == name:
                return cand
        except Exception:
            pass
    try:
        return bel.find_input_pin(node, name)
    except Exception:
        return None


def pin_out(node, name=None):
    if name:
        for cand in bel.list_output_pins(node) or []:
            try:
                if str(cand.get_pin_name()) == name:
                    return cand
            except Exception:
                pass
    try:
        return bel.find_result_pin(node)
    except Exception:
        outs = bel.list_output_pins(node) or []
        return outs[0] if outs else None


def pos(node, x, y):
    try:
        bel.set_node_pos(node, unreal.IntPoint(int(x), int(y)))
    except Exception:
        pass


def safe_rename(node, name):
    try:
        existing = unreal.find_object(node.get_outer(), name)
        if existing and existing != node:
            return False
        node.rename(name)
        return True
    except Exception:
        return False


def ensure_bool(bp, name):
    try:
        pin = bel.get_basic_type_by_name(unreal.Name("bool"))
        bel.add_member_variable(bp, unreal.Name(name), pin)
    except Exception:
        pass


def run():
    abp = load(ABP)
    ensure_bool(abp, "bHasMoveInput")
    ensure_bool(abp, "bWantsWalk")
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    # Collect Update events
    updates = []
    for n in unreal.ObjectIterator(unreal.K2Node_Event):
        try:
            if n.get_outer() == graph and "Blueprint Update Animation" in str(bel.get_node_title(n)):
                updates.append(n)
        except Exception:
            pass
    log(f"Update events: {len(updates)} {[u.get_name() for u in updates]}")

    kill = []
    # Kill all LC_* / LC_DEL_* and broken cast leftovers
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_DynamicCast,
        unreal.K2Node_IfThenElse,
        unreal.EdGraphNode_Comment,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != graph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if name.startswith("LC_") or "Loco conditions" in title or "copy bHasMoveInput" in title:
                    kill.append(n)
            except Exception:
                pass

    # Keep first Update event, remove extras
    keep_upd = updates[0] if updates else None
    for u in updates[1:]:
        kill.append(u)
        log(f"drop duplicate Update {u.get_name()}")

    uniq, seen = [], set()
    for n in kill:
        i = id(n)
        if i not in seen:
            seen.add(i)
            uniq.append(n)
    for i, n in enumerate(uniq):
        try:
            n.rename(f"LC_DEL_{i}")
        except Exception:
            pass
    if uniq:
        ed.remove_nodes(uniq)
        log(f"purged {len(uniq)}")

    if not keep_upd:
        try:
            keep_upd = bel.add_event_override(
                abp, "BlueprintUpdateAnimation", unreal.IntPoint(-1400, 200)
            )
        except Exception as e:
            log(f"add update: {e}")
    if not keep_upd:
        log("NO Update event — vars only on Character; use TryGetPawnOwner in SM")
        bel.compile_blueprint(abp)
        save(ABP)
        return

    pos(keep_upd, -1400, 200)
    then = bel.find_then_pin(keep_upd)
    old = list(then.list_connected_pins() or [])
    # Only break if old targets are our LC leftovers (already purged). Keep other chains.
    # If old points to Speed update etc, insert in front.
    then.break_pin_links()

    try_get = ed.add_call_function_node("/Script/Engine.AnimInstance:TryGetPawnOwner")
    safe_rename(try_get, "LC_TryGet")
    pos(try_get, -1150, 400)

    char_cls = load(CHAR).generated_class()
    cast_node = unreal.new_object(unreal.K2Node_DynamicCast, graph, unreal.Name("LC_CastChar"))
    # UE property is TargetType (UPROPERTY) — python may need TargetType
    for prop in ("TargetType", "target_type"):
        try:
            cast_node.set_editor_property(prop, char_cls)
            log(f"cast set {prop} OK")
            break
        except Exception as e:
            log(f"cast {prop}: {e}")
    for m in ("allocate_default_pins", "reconstruct_node", "post_place_node"):
        if hasattr(cast_node, m):
            try:
                getattr(cast_node, m)()
            except Exception:
                pass
    pins = [str(p.get_pin_name()) for p in (bel.list_all_pins(cast_node) or [])]
    log(f"cast pins={pins}")
    pos(cast_node, -900, 220)

    set_has = ed.add_set_member_variable_node("bHasMoveInput")
    safe_rename(set_has, "LC_SetHas")
    pos(set_has, -400, 200)
    set_walk = ed.add_set_member_variable_node("bWantsWalk")
    safe_rename(set_walk, "LC_SetWalk")
    pos(set_walk, -150, 200)

    # Character property gets — create with class path if API allows
    get_has = ed.add_get_member_variable_node("bHasMoveInput")
    get_walk = ed.add_get_member_variable_node("bWantsWalk")
    # These are ABP gets by default — we need external. Use CallFunction Get on cast?
    # Better: use "get object property" — or set from cast via FindProperty.
    # In BP, after Cast you drag off AsXxx and get bHasMoveInput.
    # Python: VariableGet with self pin from cast As pin — but VariableGet is for this ABP.
    #
    # Use K2Node_VariableGet with SetVariableReference to character? Hard.
    # Alternative: K2Node_CallFunction on a custom getter — skip.
    #
    # Simplest working approach for AnimBP: use "Get Boolean Attribute" — no.
    #
    # Use BlueprintEditorLibrary / spawn VariableGet for another class:
    for meth in ("add_get_member_variable_node",):
        pass

    # Try creating VariableGet and setting variable reference to Character's property
    def make_foreign_get(varname, tag, x, y):
        node = unreal.new_object(unreal.K2Node_VariableGet, graph, unreal.Name(tag))
        # VariableReference structure
        for prop in ("variable_reference", "VariableReference"):
            try:
                ref = node.get_editor_property(prop)
                # MemberParent / MemberName
                for mp in ("member_parent", "MemberParent"):
                    try:
                        ref.set_editor_property(mp, char_cls)
                    except Exception:
                        pass
                for mn in ("member_name", "MemberName"):
                    try:
                        ref.set_editor_property(mn, unreal.Name(varname))
                    except Exception:
                        pass
                node.set_editor_property(prop, ref)
                log(f"{tag} set via {prop}")
            except Exception as e:
                log(f"{tag} {prop}: {e}")
        for m in ("allocate_default_pins", "reconstruct_node"):
            if hasattr(node, m):
                try:
                    getattr(node, m)()
                except Exception:
                    pass
        pos(node, x, y)
        log(f"{tag} pins={[str(p.get_pin_name()) for p in (bel.list_all_pins(node) or [])]}")
        return node

    # Remove the wrong local gets if we created them
    bad = []
    if get_has:
        bad.append(get_has)
    if get_walk:
        bad.append(get_walk)
    if bad:
        ed.remove_nodes(bad)

    get_has = make_foreign_get("bHasMoveInput", "LC_GetHas", -650, 400)
    get_walk = make_foreign_get("bWantsWalk", "LC_GetWalk", -650, 520)

    links = []
    links.append(("upd->cast", connect(then, bel.find_execute_pin(cast_node))))
    obj_pin = pin_in(cast_node, "Object") or pin_in(cast_node, "object")
    links.append(("pawn->obj", connect(pin_out(try_get, "ReturnValue"), obj_pin)))
    succ = bel.find_then_pin(cast_node)
    links.append(("cast->setHas", connect(succ, bel.find_execute_pin(set_has))))
    links.append(("setHas->setWalk", connect(bel.find_then_pin(set_has), bel.find_execute_pin(set_walk))))

    # As pin
    as_pin = None
    for p in bel.list_output_pins(cast_node) or []:
        nm = str(p.get_pin_name())
        if nm not in ("then", "CastFailed", "execute") and "Failed" not in nm:
            if nm.startswith("As") or "Character" in nm or nm not in ("then",):
                as_pin = p
                log(f"as pin candidate {nm}")
                break
    if as_pin:
        for g in (get_has, get_walk):
            selfp = bel.find_self_pin(g) or pin_in(g, "self") or pin_in(g, "Target")
            links.append((f"as->{g.get_name()}", connect(as_pin, selfp)))

    links.append(("has->set", connect(pin_out(get_has), pin_in(set_has, "bHasMoveInput"))))
    links.append(("walk->set", connect(pin_out(get_walk), pin_in(set_walk, "bWantsWalk"))))

    if old:
        # reattach non-deleted
        for p in old:
            try:
                on = p.get_owning_node()
                if on and on.get_outer() == graph and not on.get_name().startswith("LC_DEL"):
                    links.append(("setWalk->old", connect(bel.find_then_pin(set_walk), p)))
                    break
            except Exception:
                pass

    try:
        ed.add_comment_node(
            "Loco conditions (NO montages)\n"
            "bHasMoveInput / bWantsWalk copied from Character\n"
            "Wire SM transitions with these bools",
            unreal.IntPoint(-1400, 40),
        )
    except Exception:
        pass

    for n, ok in links:
        log(f"link {n}: {ok}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    save(ABP)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
