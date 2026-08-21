# -*- coding: utf-8 -*-
"""为课件注入单击进入动画与淡入换页。"""
from __future__ import annotations

import shutil
from pathlib import Path

import win32com.client

SRC = Path(r"E:\游戏\符济\Rune-of-Succor\课件_数据结构_第二章线性表") / (
    "南京中医药大学_数据结构_第二章_线性表.pptx"
)
TMP = Path(r"C:\Users\vwuya\AppData\Local\Temp\njucm_linear_list.pptx")
TMP_OUT = Path(r"C:\Users\vwuya\AppData\Local\Temp\njucm_linear_list_anim.pptx")

FADE, WIPE, ON_CLICK, WITH_PREV, BY_PARA = 10, 22, 1, 2, 1
PP_FADE, PP_ALERTS_NONE, PP_OPENXML = 3844, 1, 24
MSO_TEXTBOX, MSO_ARROW_HINT = 17, 1


def should_skip(name: str) -> bool:
    n = (name or "").lower()
    return n.startswith("chrome_") or n.startswith("placeholder")


def is_bullet_box(name: str) -> bool:
    n = (name or "").lower()
    if n in {"anim_b", "anim_lb", "anim_rb"}:
        return True
    return "bullet" in n or n.startswith("anim_cb")


def is_arrow(shape, name: str) -> bool:
    n = (name or "").lower()
    if n.startswith("anim_a") and n[6:].isdigit():
        return True
    try:
        return "arrow" in shape.AutoShapeType._prop_map_get_  # unused
    except Exception:
        return False


def animate(src: Path) -> Path:
    shutil.copy2(src, TMP)
    if TMP_OUT.exists():
        TMP_OUT.unlink()

    app = win32com.client.DispatchEx("PowerPoint.Application")
    app.Visible = True
    try:
        app.DisplayAlerts = PP_ALERTS_NONE
    except Exception:
        pass

    pres = app.Presentations.Open(str(TMP), False, False, True)
    try:
        for si, slide in enumerate(pres.Slides, 1):
            try:
                slide.SlideShowTransition.EntryEffect = PP_FADE
                slide.SlideShowTransition.Duration = 0.3
            except Exception:
                pass

            seq = slide.TimeLine.MainSequence
            for shape in slide.Shapes:
                try:
                    name = shape.Name
                    stype = int(shape.Type)
                except Exception:
                    continue
                if should_skip(name):
                    continue

                nlow = name.lower()
                if nlow.startswith("title_"):
                    trigger, effect_id = WITH_PREV, FADE
                elif is_bullet_box(name):
                    trigger, effect_id = ON_CLICK, FADE
                elif nlow.startswith("anim_a") and nlow.replace("anim_a", "").isdigit():
                    trigger, effect_id = WITH_PREV, FADE
                elif stype == MSO_TEXTBOX:
                    trigger, effect_id = WITH_PREV, FADE
                elif "code" in nlow:
                    trigger, effect_id = ON_CLICK, WIPE
                else:
                    trigger, effect_id = ON_CLICK, FADE

                try:
                    effect = seq.AddEffect(shape, effect_id, trigger)
                    effect.Timing.Duration = 0.35
                    if is_bullet_box(name) and shape.HasTextFrame and shape.TextFrame.HasText:
                        try:
                            if shape.TextFrame.TextRange.Paragraphs().Count >= 2:
                                effect.EffectParameters.TextUnitEffect = BY_PARA
                        except Exception:
                            pass
                except Exception as e:
                    print(f"skip {si} {name}: {e}")
            print("slide", si, "effects", seq.Count)

        pres.SaveAs(str(TMP_OUT), PP_OPENXML)
        print("saved", TMP_OUT.stat().st_size)
    finally:
        try:
            pres.Close()
        except Exception:
            pass
        try:
            if app.Presentations.Count == 0:
                app.Quit()
        except Exception:
            pass

    dest = src.with_name(src.stem.replace("_可放映", "") + "_可放映.pptx")
    shutil.copy2(TMP_OUT, dest)
    shutil.copy2(TMP_OUT, src)
    print("ready", dest)
    return dest


if __name__ == "__main__":
    animate(SRC)
