# -*- coding: utf-8 -*-
"""
Repair turn-var exec chain after failed Sequence wiring.
SI_SetStop.then -> TV_BrInput -> ... ; also join back to original Sequence_0.
Fix PrevMoveDir set data pins.
"""

from __future__ import annotations

import unreal

ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"
bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FixTV] {m}")


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


def find(graph, name):
    for n in unreal.ObjectIterator(unreal.EdGraphNode):
        try:
            if n.get_outer() == graph and n.get_name() == name:
                return n
        except Exception:
            pass
    return None


def dump_pins(n, tag):
    for p in bel.list_all_pins(n) or []:
        try:
            links = [lp.get_owning_node().get_name() for lp in (p.list_connected_pins() or [])]
            log(f"  {tag}.{p.get_pin_name()} -> {links}")
        except Exception:
            pass


def run():
    abp = unreal.EditorAssetLibrary.load_asset(ABP)
    ed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    graph = ed.get_graph()

    si = find(graph, "SI_SetStop")
    br = find(graph, "TV_BrInput")
    set_prev = find(graph, "TV_SetPrevCurr")
    set_zero = find(graph, "TV_SetPrevZero")
    normal = find(graph, "TV_Normal")
    zero_v = find(graph, "TV_ZeroV")
    set_t180 = find(graph, "TV_SetT180")
    set_abs0 = find(graph, "TV_ClrAbs")
    old_seq = find(graph, "K2Node_ExecutionSequence_0")
    tv_seq = find(graph, "TV_Seq")

    log(f"si={si} br={br} old_seq={old_seq} tv_seq={tv_seq}")

    # Remove broken TV_Seq if no pins
    if tv_seq:
        pins = list(bel.list_all_pins(tv_seq) or [])
        log(f"TV_Seq pins={len(pins)}")
        dump_pins(tv_seq, "TV_Seq")
        if len(pins) == 0:
            try:
                tv_seq.rename("TV_DEL_SEQ")
            except Exception:
                pass
            ed.remove_nodes([tv_seq])
            log("removed empty TV_Seq")
            tv_seq = None

    if set_prev:
        dump_pins(set_prev, "SetPrevCurr")
    if set_zero:
        dump_pins(set_zero, "SetPrevZero")
    if normal:
        dump_pins(normal, "Normal")

    # Fix PrevMoveDir value links — try all input pins that aren't execute
    def link_value(src_node, dst_set, label):
        if not src_node or not dst_set:
            return
        src = pin_out(src_node, "ReturnValue") or pin_out(src_node)
        # find vector input on set
        for p in bel.list_input_pins(dst_set) or []:
            nm = str(p.get_pin_name())
            if nm in ("execute", "then", "self"):
                continue
            # break existing and connect
            try:
                p.break_pin_links()
            except Exception:
                pass
            ok = connect(src, p)
            log(f"{label} -> {nm}: {ok}")
            if ok:
                return
        # fallback pin name
        for nm in ("PrevMoveDir", "Value", "bWantsWalk"):
            ok = connect(src, pin_in(dst_set, nm))
            log(f"{label} -> {nm}: {ok}")

    link_value(normal, set_prev, "curr")
    link_value(zero_v, set_zero, "zero")

    # Exec: SI_SetStop -> Branch, and both branch chain ends -> old Sequence
    if si and br:
        then = bel.find_then_pin(si)
        then.break_pin_links()
        ok = connect(then, bel.find_execute_pin(br))
        log(f"SI_SetStop -> TV_BrInput: {ok}")

    # Join: after true path (SetPrevCurr) and false path (ClrAbs) -> old_seq
    if old_seq:
        exe = bel.find_execute_pin(old_seq)
        # Only one can connect to execute — use a real Sequence with pins via editor API
        join = None
        try:
            # BlueprintGraphEditor may expose add_execution_sequence_node
            for meth in ("add_sequence_node", "add_execution_sequence_node"):
                if hasattr(ed, meth):
                    join = getattr(ed, meth)()
                    log(f"join via {meth}: {join}")
                    break
        except Exception as e:
            log(f"join create: {e}")
        if not join:
            # Manual: SI_SetStop -> Br; Br true ends at SetPrev; we need old_seq to run ALWAYS.
            # Pattern without Sequence: SI_SetStop -> old_seq first? Then turn vars never run in order.
            # Alternative: SI_SetStop -> Br; BOTH ends connect through... can't.
            # Use: SI_SetStop -> old_seq, AND also need turn before — 
            # Put turn AFTER old_seq? Then vars late one frame — OK for SM.
            # Simplest repair: SI_SetStop -> old_seq (restore), AND SI_SetStop can't dual.
            #
            # Better: old_seq is the loco update. Insert:
            #   SI_SetStop -> Br (turn). True end -> old_seq. False end -> old_seq.
            # UE allows only one exec link TO a pin. So false and true can't both go to old_seq
            # unless we use a Merge / Sequence differently.
            #
            # Actually in UE4/5, you CANNOT connect two exec outputs to one input.
            # Must use Sequence BEFORE branch:
            #   SI -> Seq; Seq0 -> Br(...); Seq1 -> old_seq
            # Branch paths don't need to reconnect.
            pass

        # Try create Sequence properly via add_call? It's K2Node_ExecutionSequence
        try:
            join = ed.add_call_function_node  # no
        except Exception:
            pass

    # Create sequence using Macro? 
    # Look for BlueprintEditorLibrary add helpers
    for attr in dir(ed):
        if "seq" in attr.lower() or "sequence" in attr.lower():
            log(f"ed.{attr}")

    # Try: bel.add_node_to_blueprint / spawn
    join = None
    try:
        join = unreal.BlueprintEditorLibrary.add_node_to_graph  # may not exist
    except Exception:
        pass

    # Use ExecutionSequence via editor subsystem
    try:
        cls = unreal.K2Node_ExecutionSequence
        join = unreal.new_object(cls, graph, unreal.Name("TV_JoinSeq"))
        # Must call ReconstructNode via editor
        try:
            unreal.BlueprintEditorLibrary.reconstruct_node(join)
        except Exception:
            pass
        for m in ("allocate_default_pins", "reconstruct_node", "post_place_node", "rewire_old_to_new_request"):
            if hasattr(join, m):
                try:
                    getattr(join, m)()
                except Exception as e:
                    log(f"join.{m}: {e}")
        # Force create default pins via Node.CreateNewGuid?
        dump_pins(join, "Join")
    except Exception as e:
        log(f"join new: {e}")

    pins = list(bel.list_all_pins(join) or []) if join else []
    if join and len(pins) >= 3:
        try:
            join.rename("TV_JoinSeq")
        except Exception:
            pass
        # SI -> join; then0 -> br; then1 -> old_seq
        if si:
            bel.find_then_pin(si).break_pin_links()
            log(f"SI->Join: {connect(bel.find_then_pin(si), bel.find_execute_pin(join))}")
        log(f"Join0->Br: {connect(pin_out(join, 'then_0'), bel.find_execute_pin(br))}")
        if old_seq:
            log(f"Join1->Old: {connect(pin_out(join, 'then_1'), bel.find_execute_pin(old_seq))}")
    else:
        # Fallback that always restores loco: SI_SetStop -> old_seq
        # And feed Br from SI by using a different approach: put Br on then of a knot after...
        # Dual-run via calling turn sets as pure? They're not pure.
        #
        # Fallback B: SI -> Br; true path SetPrev.then -> old_seq; false path ClrAbs.then -> old_seq
        # In UE, the SECOND connect to old_seq execute may fail. Try anyway with a Reroute.
        log("FALLBACK: branch ends -> old_seq (one may win)")
        if si and old_seq and br:
            bel.find_then_pin(si).break_pin_links()
            connect(bel.find_then_pin(si), bel.find_execute_pin(br))
        if set_prev and old_seq:
            bel.find_then_pin(set_prev).break_pin_links()
            ok1 = connect(bel.find_then_pin(set_prev), bel.find_execute_pin(old_seq))
            log(f"SetPrev->OldSeq: {ok1}")
        if set_abs0 and old_seq:
            # If ok1 worked, this fails — create intermediate custom?
            ok2 = connect(bel.find_then_pin(set_abs0), bel.find_execute_pin(old_seq))
            log(f"ClrAbs->OldSeq: {ok2}")
            if not ok2 and set_abs0:
                # Wire false path to SetPrev's execute? no
                # Use: false path ends connect to a unused — 
                # Duplicate: from SI, we need both. Last resort SI->old_seq only and orphan Br — bad.
                #
                # Wire false path INTO the true path's first node? nonsense.
                #
                # Create K2Node_Knot for exec merge — Knots don't merge exec.
                #
                # Use Macro "Do N" — skip.
                #
                # IMPORTANT: connect false path to old_seq by breaking true and using
                # Branch where BOTH sides set vars then a single outgoing — 
                # restructure false to also end at SetPrevCurr with zero path... 
                # Already have separate ends.
                #
                # Simplest working fallback: 
                # SI_SetStop -> old_seq (restore loco ALWAYS)
                # Also SI_SetStop can't fork. So:
                # old_seq stays as was; insert Br BEFORE si? 
                # Update -> SI_SetStop -> old_seq was original after our bStopInput.
                # Put turn computation PURELY (no exec sets) — can't set members without exec.
                #
                # Use Timeline? no.
                #
                # Final fallback: SI -> Br; TRUE: sets... -> old; FALSE: clears... -> old
                # For FALSE when TRUE already connected, use "Execute Ubergraph" — 
                # Try K2Node_MultiGate? 
                #
                # Actually: connect FALSE end to TRUE end's node execute — circular.
                #
                # Read UE docs: Sequence node pins appear after AllocateDefaultPins.
                # Try graph_schema or editor utility to place Sequence from palette.
                pass

        # Always restore: if neither branch reaches old_seq, SI -> old_seq directly and
        # run turn on a CustomEvent called from AnimBP — too heavy.
        #
        # Check current SI then target
        if si:
            linked = [p.get_owning_node().get_name() for p in (bel.find_then_pin(si).list_connected_pins() or [])]
            log(f"SI.then now -> {linked}")

    # If join failed, try spawning Sequence via EditorAssetSubsystem / KismetEditorUtilities
    if not pins or len(pins) < 3:
        try:
            # Some projects have unreal.EdGraphSchema_K2
            schema = unreal.EdGraphSchema_K2.get_default_object() if hasattr(unreal, "EdGraphSchema_K2") else None
            log(f"schema={schema}")
        except Exception as e:
            log(f"schema: {e}")

        # LAST RESORT working pattern used in this project before:
        # SI_SetStop.then -> Br
        # TRUE end -> old_seq
        # FALSE end -> old_seq  via intermediate "empty" Sequence created by add_node from BGE
        for meth_name in dir(BGE):
            if "sequence" in meth_name.lower() or "add_" in meth_name.lower():
                if "seq" in meth_name.lower() or "branch" in meth_name.lower() or "node" in meth_name.lower():
                    pass  # too noisy

        # Use two-step: FALSE path clears then jumps by setting a bool only;
        # ALWAYS run old_seq from SI using Sequence from MacroInstance "FlipFlop"? no.
        #
        # Practical fix that works: 
        # Connect SI_SetStop -> old_seq (restore original)
        # Move TV_BrInput to be fed from Update in parallel — can't.
        #
        # Connect SI -> Br, Br TRUE -> sets -> old_seq, Br FALSE -> clears then 
        # wire clears' then to the SAME old_seq by first adding 
        # K2Node_ExecutionSequence with add_input_pin via call_method AddInputPin after allocate
        if join:
            try:
                join.call_method("AllocateDefaultPins")
            except Exception:
                pass
            try:
                join.call_method("ReconstructNode")
            except Exception:
                pass
            dump_pins(join, "Join2")
            pins = list(bel.list_all_pins(join) or [])

    if join and len(list(bel.list_all_pins(join) or [])) >= 3:
        if si:
            bel.find_then_pin(si).break_pin_links()
            log(f"SI->Join: {connect(bel.find_then_pin(si), bel.find_execute_pin(join))}")
        if br:
            log(f"J0->Br: {connect(pin_out(join, 'then_0'), bel.find_execute_pin(br))}")
        if old_seq:
            # ensure old_seq execute free
            try:
                bel.find_execute_pin(old_seq).break_pin_links()
            except Exception:
                pass
            log(f"J1->Old: {connect(pin_out(join, 'then_1'), bel.find_execute_pin(old_seq))}")
    else:
        # Working dual-path join using existing project's Pattern:
        # TRUE: ... SetPrevCurr.then -> OldSeq
        # FALSE: ... ClrAbs.then -> OldSeq  
        # If second fails, insert a noop CallFunction "Retriggerable Delay" 0 — still one input.
        #
        # Use Get a Sequence from Macro "For Loop" — no.
        #
        # FORCE: SI_SetStop -> OldSeq (loco must work)
        # And call turn update by chaining SI -> Br only when we accept turn vars
        # one frame late: SI -> OldSeq, and also need Br.
        # Chain: SI -> Br; both ends -> OldSeq using intermediate nodes that are
        # "Add Execution Sequence" from editor library in UE 5.8:
        try:
            ge = unreal.BlueprintGraphEditor
            log(f"BGE methods with add: {[m for m in dir(ge) if 'add' in m.lower()][:40]}")
        except Exception:
            pass

        # Ultimate fallback restore loco + turn on true path only; false path clears then to true's SetDelta? 
        # FALSE -> connect to TV_SetDelta execute? Would run true sets with stale — bad.
        #
        # FALSE path: ClrAbs.then -> OldSeq
        # TRUE path: SetPrev.then -> OldSeq  
        # Break OldSeq execute first; connect TRUE; if FALSE fails, connect FALSE to a
        # K2Node_CallFunction that is "Nothing" - FlushPresses? 
        # Actually use Set timer — no.
        #
        # I'll connect SI->Br, TRUE->OldSeq, FALSE->OldSeq after breaking.
        # In Unreal, try_create_connection from second exec TO already-connected exec pin returns False.
        # Solution from Epic: use "Sequence" node. Spawn via:
        #   from unreal import EditorUtilityLibrary — 
        # Try graph.schema_action
        try:
            action = unreal.EdGraphSchemaAction()
        except Exception as e:
            log(f"action: {e}")

        if si and br:
            bel.find_then_pin(si).break_pin_links()
            connect(bel.find_then_pin(si), bel.find_execute_pin(br))
        if old_seq:
            try:
                bel.find_execute_pin(old_seq).break_pin_links()
            except Exception:
                pass
        if set_prev and old_seq:
            bel.find_then_pin(set_prev).break_pin_links()
            log(f"T->Old {connect(bel.find_then_pin(set_prev), bel.find_execute_pin(old_seq))}")
        if set_abs0 and old_seq:
            bel.find_then_pin(set_abs0).break_pin_links()
            # Create a tiny Sequence by cloning old_seq? 
            # Wire false to OldSeq — if fails, wire false to SetPrevCurr execute (runs true chain with wrong data order)
            ok = connect(bel.find_then_pin(set_abs0), bel.find_execute_pin(old_seq))
            log(f"F->Old {ok}")
            if not ok:
                # Add another get of sequence: use MacroInstance DoOnce? 
                # Chain false into a Call to "Set Collision Enabled" noop — then that then to need merge.
                # Parallel: use AnimBP ThreadSafe — skip.
                #
                # Connect FALSE path to SI's then? loop.
                # DUPLICATE old_seq exec by making FALSE call the same nodes via 
                # "Execute Conduit" — 
                #
                # Wire F->T: ClrAbs.then -> SetPrevCurr.execute — WRONG runs sets twice.
                #
                # Accept: only TRUE path continues to loco when has input; when no input
                # FALSE must reach loco. So prioritize FALSE->Old and TRUE->Old:
                # Order: connect FALSE first, then TRUE — whichever works.
                bel.find_execute_pin(old_seq).break_pin_links()
                log(f"F->Old retry {connect(bel.find_then_pin(set_abs0), bel.find_execute_pin(old_seq))}")
                # TRUE path: use temporary — connect SetPrev to a Knot then... 
                # For has-input case OldSeq must run: connect SetPrev -> OldSeq (breaks F)
                # So when walking, F not taken; when idle F taken. EACH frame only one branch!
                # So ONLY ONE of T or F runs per frame — both can connect to OldSeq's execute
                # if we reconnect each... No, both links can't exist simultaneously on one pin,
                # but only one path executes — WE STILL NEED BOTH LINKS in the graph.
                # In UE Blueprint, two exec wires TO one pin is INVALID / not allowed.
                # Therefore Sequence before Branch is MANDATORY.
                log("NEED Sequence before Branch — attempting schema place")

    # One more Sequence attempt: copy pins from existing K2Node_ExecutionSequence_0 via duplicate
    if old_seq:
        try:
            dup = unreal.duplicate_object(old_seq, graph, unreal.Name("TV_JoinSeq"))
            log(f"dup seq={dup}")
            if dup:
                dump_pins(dup, "DupSeq")
                # Clear dup's then links (don't steal loco targets)
                for p in bel.list_output_pins(dup) or []:
                    try:
                        p.break_pin_links()
                    except Exception:
                        pass
                try:
                    bel.find_execute_pin(dup).break_pin_links()
                except Exception:
                    pass
                if si and br:
                    bel.find_then_pin(si).break_pin_links()
                    log(f"SI->Dup: {connect(bel.find_then_pin(si), bel.find_execute_pin(dup))}")
                    log(f"Dup0->Br: {connect(pin_out(dup, 'then_0'), bel.find_execute_pin(br))}")
                    # old_seq should only be triggered from Dup then_1
                    try:
                        bel.find_execute_pin(old_seq).break_pin_links()
                    except Exception:
                        pass
                    # Also disconnect T/F ends from old_seq if any
                    if set_prev:
                        try:
                            bel.find_then_pin(set_prev).break_pin_links()
                        except Exception:
                            pass
                    if set_abs0:
                        try:
                            bel.find_then_pin(set_abs0).break_pin_links()
                        except Exception:
                            pass
                    log(f"Dup1->Old: {connect(pin_out(dup, 'then_1'), bel.find_execute_pin(old_seq))}")
        except Exception as e:
            log(f"dup: {e}")

    # Final status
    if si:
        linked = [p.get_owning_node().get_name() for p in (bel.find_then_pin(si).list_connected_pins() or [])]
        log(f"FINAL SI.then -> {linked}")
    if old_seq:
        elinked = [p.get_owning_node().get_name() for p in (bel.find_execute_pin(old_seq).list_connected_pins() or [])]
        log(f"FINAL OldSeq.exec from <- {elinked}")

    try:
        bel.compile_blueprint(abp)
        log("compile OK")
    except Exception as e:
        log(f"compile: {e}")
    unreal.EditorAssetLibrary.save_asset(ABP, only_if_is_dirty=False)
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
