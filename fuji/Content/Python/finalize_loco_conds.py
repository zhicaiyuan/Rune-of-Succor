# -*- coding: utf-8 -*-
"""
Final: verify Character has NO PlayAnimMontage Start/Stop.
Strip broken LC_* AnimBP nodes that have no pins.
Keep Character bWantsWalk + bHasMoveInput.
Keep AnimBP bool vars (user fills them OR reads Character in SM).
"""

from __future__ import annotations

import unreal

CHAR = "/Game/ThirdPerson/Blueprints/BP_ThirdPersonCharacter"
ABP = "/Game/Characters/\u6797\u7b26/\u52a8\u753b/ABP_StrafeLocomotion"

bel = unreal.BlueprintEditorLibrary
BGE = unreal.BlueprintGraphEditor


def log(m):
    unreal.log(f"[FinalCond] {m}")


def load(p):
    return unreal.EditorAssetLibrary.load_asset(p)


def save(p):
    unreal.EditorAssetLibrary.save_asset(p, only_if_is_dirty=False)


def run():
    bp = load(CHAR)
    ed = BGE.get_graph_editor_by_name(bp, "EventGraph")
    graph = ed.get_graph()

    plays = []
    for n in unreal.ObjectIterator(unreal.K2Node_CallFunction):
        try:
            if n.get_outer() != graph:
                continue
            if "PlayAnimMontage" in str(bel.get_node_title(n)):
                plays.append(n)
        except Exception:
            pass
    if plays:
        for i, n in enumerate(plays):
            try:
                n.rename(f"KILL_MONTAGE_{i}")
            except Exception:
                pass
        ed.remove_nodes(plays)
        log(f"REMOVED {len(plays)} PlayAnimMontage")
    else:
        log("Character PlayAnimMontage: none (good)")

    # presence of condition setters
    has_ww = False
    has_lc = False
    for n in unreal.ObjectIterator(unreal.K2Node_VariableSet):
        try:
            if n.get_outer() != graph:
                continue
            name = n.get_name()
            title = str(bel.get_node_title(n))
            if name == "WW_SetBool" or "bWantsWalk" in title:
                has_ww = True
            if name == "LC_SetHasInput" or "bHasMoveInput" in title:
                has_lc = True
        except Exception:
            pass
    log(f"bWantsWalk setter present={has_ww}")
    log(f"bHasMoveInput setter present={has_lc}")

    try:
        bel.compile_blueprint(bp)
        log("char compile OK")
    except Exception as e:
        log(f"char compile: {e}")
    save(CHAR)

    # ABP: remove broken LC_* (no pins)
    abp = load(ABP)
    aed = BGE.get_graph_editor_by_name(abp, "EventGraph")
    agraph = aed.get_graph()
    kill = []
    for cls in (
        unreal.K2Node_CallFunction,
        unreal.K2Node_VariableGet,
        unreal.K2Node_VariableSet,
        unreal.K2Node_DynamicCast,
        unreal.EdGraphNode_Comment,
        unreal.K2Node_Event,
    ):
        for n in unreal.ObjectIterator(cls):
            try:
                if n.get_outer() != agraph:
                    continue
                name = n.get_name()
                title = str(bel.get_node_title(n))
                if not (name.startswith("LC_") or name.startswith("LC_DEL_") or "Loco conditions" in title):
                    continue
                # never delete a real BlueprintUpdateAnimation that isn't LC_
                if cls is unreal.K2Node_Event and "Blueprint Update Animation" in title and not name.startswith("LC_"):
                    continue
                pins = list(bel.list_all_pins(n) or [])
                if name.startswith("LC_") or "Loco conditions" in title:
                    kill.append(n)
                    log(f"abp drop {name} title={title} pins={len(pins)}")
            except Exception:
                pass
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
        aed.remove_nodes(uniq)
        log(f"abp purged {len(uniq)} broken LC nodes")

    # Ensure ABP has the two bools for user convenience
    for name in ("bHasMoveInput", "bWantsWalk"):
        try:
            pin = bel.get_basic_type_by_name(unreal.Name("bool"))
            bel.add_member_variable(abp, unreal.Name(name), pin)
        except Exception:
            pass
    try:
        bel.compile_blueprint(abp)
        log("abp compile OK")
    except Exception as e:
        log(f"abp compile: {e}")
    save(ABP)

    rules = """条件变量（无蒙太奇）

角色 BP_ThirdPersonCharacter 每帧更新：
  bWantsWalk     — 按住 Alt = true（走路）
  bHasMoveInput  — 有 WASD/移动输入 = true

在 AnimBP 状态机过渡里这样用（推荐直接读角色）：
  TryGetPawnOwner -> Cast to BP_ThirdPersonCharacter
  -> bHasMoveInput / bWantsWalk

或自己在 AnimBP EventGraph 的 Blueprint Update Animation
把这两个 bool 拷到 AnimBP 变量上，过渡里直接用变量。

建议过渡：
  Idle -> WalkStart:     bHasMoveInput AND bWantsWalk
  Idle -> RunStart:      bHasMoveInput AND NOT bWantsWalk
  WalkLoop -> WalkStop:  NOT bHasMoveInput AND bWantsWalk
  RunLoop  -> RunStop:   NOT bHasMoveInput AND NOT bWantsWalk
  Start/Stop 播完 -> 下一状态：勾 Automatic Rule

不要再用 PlayAnimMontage 做起步/停止。
"""
    path = unreal.Paths.project_content_dir() + "Python/START_STOP_TRANSITION_RULES.txt"
    with open(path, "w", encoding="utf-8") as f:
        f.write(rules)
    log("rules updated")
    log("done")


if __name__ == "__main__":
    run()
else:
    run()
