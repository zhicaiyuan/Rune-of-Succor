# -*- coding: utf-8 -*-
"""生成南京中医药大学《数据结构》第二章《线性表》16:9 课件。"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from theme_helpers import (
    ACCENT, ACCENT2, CARD, CARD2, CODE_BG, CYAN, DANGER, FONT, GOLD, HEADER,
    MUTED, NAVY, NAVY2, OK, SLIDE_H, SLIDE_W, SOFT, WARN, WHITE,
    add_bullets_box, add_card, add_code_block, add_header_footer, add_logo,
    add_notes, add_rect, add_shape, add_tag, add_textbox, add_para, arrow_right,
    node_box, paint_background, set_run_font,
)

OUT = Path(r"E:\游戏\符济\Rune-of-Succor\课件_数据结构_第二章线性表") / (
    "南京中医药大学_数据结构_第二章_线性表.pptx"
)
TOTAL = 46


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def page_kind(kind, section, n, total, title, subtitle=None):
    """内容页通用标题区，返回 slide。"""
    sl = blank(prs_ref[0])
    add_header_footer(sl, section, n, total, kind)
    add_textbox(sl, Inches(0.32), Inches(0.96), Inches(12.4), Inches(0.46),
                title, 26, WHITE, True, name="title_main")
    if subtitle:
        add_textbox(sl, Inches(0.32), Inches(1.38), Inches(12.4), Inches(0.32),
                    subtitle, 14, MUTED, False, name="title_sub")
    return sl


prs_ref = [None]  # filled in main


# ---------------------------------------------------------------------------
# 首页 / 信息 / 目录
# ---------------------------------------------------------------------------
def s_cover(n, total):
    sl = blank(prs_ref[0])
    paint_background(sl)
    add_rect(sl, Inches(8.6), 0, Inches(4.74), SLIDE_H, NAVY2, "chrome_side")
    add_rect(sl, Inches(8.6), 0, Inches(0.07), SLIDE_H, ACCENT, "chrome_side2")
    # decorative diamonds
    add_shape(sl, MSO_SHAPE.OVAL, Inches(-0.8), Inches(5.8), Inches(3.2), Inches(3.2),
              SOFT, "chrome_orb")
    add_shape(sl, MSO_SHAPE.OVAL, Inches(11.8), Inches(-0.6), Inches(2.4), Inches(2.4),
              SOFT, "chrome_orb2")

    add_logo(sl, Inches(9.15), Inches(1.55), Inches(2.35))
    add_textbox(sl, Inches(8.85), Inches(4.05), Inches(4.2), Inches(0.7),
                "南京中医药大学", 20, WHITE, True, align="center", name="anim_school")
    add_textbox(sl, Inches(8.85), Inches(4.65), Inches(4.2), Inches(0.7),
                "NANJING UNIVERSITY OF\nCHINESE MEDICINE", 11, ACCENT2, False,
                align="center", name="anim_en")
    add_textbox(sl, Inches(8.85), Inches(5.55), Inches(4.2), Inches(0.4),
                "本科课程  ·  计算机类专业", 12, MUTED, False, align="center", name="anim_col")
    add_textbox(sl, Inches(8.85), Inches(6.05), Inches(4.2), Inches(0.35),
                "课程思政示范课件", 13, GOLD, True, align="center", name="anim_sz")

    add_textbox(sl, Inches(0.55), Inches(1.35), Inches(7.6), Inches(0.4),
                "DATA STRUCTURES  ·  CHAPTER 02", 14, ACCENT, True, name="anim_en2")
    add_textbox(sl, Inches(0.52), Inches(1.85), Inches(7.8), Inches(1.15),
                "第二章  线性表", 48, WHITE, True, name="anim_title")
    add_textbox(sl, Inches(0.55), Inches(3.05), Inches(7.6), Inches(0.45),
                "Linear List：逻辑结构 · 顺序存储 · 链式存储", 16, MUTED, name="anim_sub")

    items = [
        ("顺序表 / 单链表 / 循环与双向链表", ACCENT2),
        ("算法讲解 + 流程图 + 可演示 C++ 代码", ACCENT2),
        ("对比选型  ·  思政案例  ·  前沿拓展", GOLD),
    ]
    y = 3.75
    for i, (txt, col) in enumerate(items):
        add_rect(sl, Inches(0.55), Inches(y), Inches(0.12), Inches(0.38), col,
                 f"anim_bar{i}", radius=0.5)
        add_textbox(sl, Inches(0.85), Inches(y), Inches(7.2), Inches(0.4),
                    txt, 16, WHITE, False, name=f"anim_i{i}")
        y += 0.52

    add_textbox(sl, Inches(0.55), Inches(6.55), Inches(7.6), Inches(0.35),
                "16:9 横版  ·  深蓝计算机专业风格  ·  单击放映查看动画", 12, MUTED,
                name="chrome_hint")
    add_notes(sl, "封面。建议先介绍学校与课程定位，再点明本章核心：线性结构的两种实现。")
    return sl


def s_info(n, total):
    sl = page_kind("章节页", "课程定位", n, total, "课程信息与本章定位")
    cards = [
        ("课程", "数据结构\nData Structures"),
        ("章节", "第 2 章  线性表\n约 6–8 学时"),
        ("对象", "计算机 / 智能 / 信管\n本科一年级或二年级"),
        ("特色", "南中医 · 数字中医药\n课程思政贯穿全章"),
    ]
    for i, (k, v) in enumerate(cards):
        x = 0.35 + i * 3.2
        add_card(sl, Inches(x), Inches(1.95), Inches(3.0), Inches(2.15), f"anim_c{i}")
        add_textbox(sl, Inches(x + 0.18), Inches(2.1), Inches(2.64), Inches(0.36),
                    k, 13, ACCENT, True, name=f"anim_ck{i}")
        add_textbox(sl, Inches(x + 0.18), Inches(2.5), Inches(2.64), Inches(1.35),
                    v, 16, WHITE, True, name=f"anim_cv{i}")

    add_card(sl, Inches(0.35), Inches(4.3), Inches(12.6), Inches(2.55), "anim_box")
    add_textbox(sl, Inches(0.55), Inches(4.45), Inches(12.2), Inches(0.36),
                "南中医特色：把“辨证选方”迁移为“因题选结构”", 16, GOLD, True, name="anim_t")
    add_bullets_box(sl, Inches(0.55), Inches(4.9), Inches(12.2), Inches(1.8), [
        "线性表是后续栈、队列、串、数组的共同逻辑基础，必须同时掌握顺序与链式两种实现。",
        "电子病历时间轴、处方明细、检验报告队列，本质都是线性结构——选错存储会直接拖慢临床信息系统。",
        "本章既讲清教材主干（定义、顺序表、链表、对比、应用），也引入跳表、STL、无锁链表与中医药数据治理。",
    ], 15, "anim_b")
    add_notes(sl, "说明学时与受众。点出南中医特色：临床数据与线性结构的对应。")
    return sl


def s_toc(n, total):
    sl = page_kind("章节页", "目录", n, total, "本章导航", "建议按「逻辑 → 顺序 → 链式 → 对比 → 应用 → 思政 → 前沿 → 总结」推进")
    blocks = [
        ("01", "线性表的逻辑结构", "定义 · ADT · 特点"),
        ("02", "顺序表", "存储 · 插入删除 · C++"),
        ("03", "链表", "单链 / 循环 / 双向 / 静态"),
        ("04", "对比与选型", "时间空间 · 场景决策"),
        ("05", "典型应用", "多项式 · 约瑟夫环"),
        ("06", "课程思政", "辨证选构 · 工匠精神"),
        ("07", "前沿拓展", "跳表 · STL · 数字中医"),
        ("08", "本章总结", "知识网络 · 作业检测"),
    ]
    for i, (num, title, sub) in enumerate(blocks):
        r, c = divmod(i, 4)
        x, y = 0.35 + c * 3.2, 1.9 + r * 2.4
        add_card(sl, Inches(x), Inches(y), Inches(3.0), Inches(2.15), f"anim_t{i}")
        add_textbox(sl, Inches(x + 0.18), Inches(y + 0.18), Inches(2.6), Inches(0.4),
                    num, 22, ACCENT, True, name=f"anim_n{i}")
        add_textbox(sl, Inches(x + 0.18), Inches(y + 0.7), Inches(2.6), Inches(0.55),
                    title, 16, WHITE, True, name=f"anim_tt{i}")
        add_textbox(sl, Inches(x + 0.18), Inches(y + 1.3), Inches(2.6), Inches(0.6),
                    sub, 12, MUTED, False, name=f"anim_s{i}")
    add_notes(sl, "用目录建立整章地图，告知学生哪些页是算法/代码/对比/思政。")
    return sl


def s_objectives(n, total):
    sl = page_kind("知识点页", "学习目标", n, total, "学习目标  ·  重点与难点")
    cols = [
        ("知识目标", ACCENT, [
            "陈述线性表逻辑特征与 ADT",
            "写出顺序表插入/删除步骤与复杂度",
            "区分头指针、头结点、首元结点",
            "掌握单链、循环、双向、静态链表",
        ]),
        ("能力目标", OK, [
            "用 C++ 实现顺序表与单链表核心操作",
            "画图分析指针改接的每一步",
            "按场景在顺序表与链表之间选型",
            "阅读跳表与 STL 容器的设计差异",
        ]),
        ("思政与素养", GOLD, [
            "因证选方 → 因题选结构",
            "空指针防护 = 临床安全意识",
            "代码规范体现工匠精神",
            "用信息化服务健康中国建设",
        ]),
    ]
    for i, (title, col, items) in enumerate(cols):
        x = 0.35 + i * 4.25
        add_card(sl, Inches(x), Inches(1.85), Inches(4.05), Inches(4.95), f"anim_col{i}")
        add_rect(sl, Inches(x), Inches(1.85), Inches(4.05), Inches(0.12), col, f"chrome_top{i}")
        add_textbox(sl, Inches(x + 0.22), Inches(2.1), Inches(3.6), Inches(0.45),
                    title, 18, col, True, name=f"anim_ct{i}")
        add_bullets_box(sl, Inches(x + 0.18), Inches(2.65), Inches(3.7), Inches(3.9),
                        items, 14, f"anim_cb{i}")
    add_notes(sl, "点明重点：插入删除移动、链表指针改接；难点：双向链表与循环边界。")
    return sl


def s_sz_lead(n, total):
    sl = page_kind("思政案例页", "思政导学", n, total,
                   "导学：从《伤寒论》之序，到线性表之序",
                   "先立“序”的观念，再进入抽象数据类型")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(6.2), Inches(4.95), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(5.8), Inches(0.4),
                "中医学中的“线性之序”", 16, GOLD, True, name="anim_lt")
    add_bullets_box(sl, Inches(0.55), Inches(2.55), Inches(5.8), Inches(4.0), [
        "《伤寒论》条文按证候次序展开，一证接一证，如线性表中每个元素有唯一前驱与后继。",
        "一张处方：君、臣、佐、使按剂量与药味排成有序序列，不可随意错位。",
        "一份住院病历：主诉 → 现病史 → 辨证 → 方药，是时间与逻辑上的线性记录。",
        "中医药现代化，首先要把这些“有序信息”变成可计算、可检索、可追溯的数据结构。",
    ], 14, "anim_lb")

    add_card(sl, Inches(6.75), Inches(1.85), Inches(6.2), Inches(4.95), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(2.05), Inches(5.8), Inches(0.4),
                "计算机科学中的映射", 16, ACCENT, True, name="anim_rt")
    add_bullets_box(sl, Inches(6.95), Inches(2.55), Inches(5.8), Inches(4.0), [
        "线性表：同一类型数据的有限序列 (a1, a2, …, an)。",
        "“辨证施治”启示我们：同样是线性逻辑，存储可以选顺序表，也可以选链表。",
        "表实证用麻黄，虚人用桂枝——问题特征不同，结构选择不同。",
        "本章思政主线：尊重数据之序、选择结构之宜、守护程序之安、服务健康中国。",
    ], 14, "anim_rb")
    add_notes(sl, "用中医“序”导入，避免空洞口号。强调后续每个算法都回扣“选对结构”。")
    return sl


# ---------------------------------------------------------------------------
# 2.1 逻辑结构
# ---------------------------------------------------------------------------
def s_sec21(n, total):
    sl = blank(prs_ref[0])
    paint_background(sl)
    add_logo(sl, Inches(11.45), Inches(0.22), Inches(0.85))
    add_textbox(sl, Inches(0.55), Inches(1.7), Inches(3), Inches(0.4),
                "SECTION  02.1", 14, ACCENT, True, name="anim_sec")
    add_textbox(sl, Inches(0.5), Inches(2.15), Inches(12), Inches(1.1),
                "线性表的逻辑结构", 40, WHITE, True, name="anim_t")
    add_textbox(sl, Inches(0.55), Inches(3.3), Inches(11), Inches(0.45),
                "定义 · 特点 · 抽象数据类型（ADT）", 18, MUTED, name="anim_s")
    for i, t in enumerate(["有限序列", "唯一前驱/后继", "与存储无关的逻辑层"]):
        add_rect(sl, Inches(0.55 + i * 4.05), Inches(4.3), Inches(3.8), Inches(1.35),
                 CARD, f"anim_c{i}", radius=0.08)
        add_textbox(sl, Inches(0.75 + i * 4.05), Inches(4.65), Inches(3.4), Inches(0.7),
                    t, 18, WHITE, True, align="center", name=f"anim_ct{i}")
    add_textbox(sl, Inches(0.55), Inches(6.4), Inches(10), Inches(0.4),
                "思政：先认清“证候之序”，再谈“存储之术”。", 14, GOLD, name="anim_sz")
    add_textbox(sl, Inches(11.2), Inches(6.9), Inches(1.8), Inches(0.3),
                f"{n:02d}/{total:02d}", 12, MUTED, align="right", name="chrome_pg")
    add_notes(sl, "章节过渡页。强调逻辑结构独立于存储结构。")
    return sl


def s_def(n, total):
    sl = page_kind("知识点页", "2.1 逻辑结构", n, total, "什么是线性表")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.45), "anim_def")
    add_textbox(sl, Inches(0.55), Inches(1.98), Inches(12.2), Inches(1.2),
                "线性表是 n（n≥0）个数据元素的有限序列，记作 (a1, a2, …, an)。\n"
                "其中 a1 为表头，an 为表尾；除端点外，每个元素有且仅有一个直接前驱和一个直接后继。",
                16, WHITE, False, name="anim_deft")

    pts = [
        ("同一性", "元素属于同一数据对象，可用同一类型描述（如药味、病案号）。"),
        ("有穷性", "n 为表长，n=0 称为空表；临床清单、医嘱条数总是有限的。"),
        ("有序性", "位序 i 有意义：第 i 味药、第 i 次随访，次序一旦颠倒则语义改变。"),
        ("线性关系", "一对一。对比：树是一对多，图是多对多——后两章会对照学习。"),
    ]
    for i, (h, b) in enumerate(pts):
        r, c = divmod(i, 2)
        x, y = 0.35 + c * 6.4, 3.5 + r * 1.6
        add_card(sl, Inches(x), Inches(y), Inches(6.15), Inches(1.45), f"anim_p{i}")
        add_textbox(sl, Inches(x + 0.22), Inches(y + 0.15), Inches(5.7), Inches(0.35),
                    h, 16, ACCENT, True, name=f"anim_ph{i}")
        add_textbox(sl, Inches(x + 0.22), Inches(y + 0.55), Inches(5.7), Inches(0.75),
                    b, 13, MUTED, False, name=f"anim_pb{i}")
    add_notes(sl, "强调“有序+一对一”。可口头举例：乱序处方可能改变君臣地位。")
    return sl


def s_adt(n, total):
    sl = page_kind("知识点页", "2.1 逻辑结构", n, total, "线性表的抽象数据类型（ADT）")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(6.3), Inches(5.0), [
        "InitList(&L)  构造空表",
        "DestroyList / ClearList  销毁或清空",
        "ListEmpty(L) / ListLength(L)  判空与求长",
        "GetElem(L, i, &e)  取第 i 个元素",
        "LocateElem(L, e)  按值查找位序",
        "PriorElem / NextElem  求前驱、后继",
        "ListInsert(&L, i, e)  在第 i 位插入",
        "ListDelete(&L, i, &e)  删除第 i 位",
        "ListTraverse(L)  依次访问（不破坏结构）",
    ], 15, "anim_b")
    add_card(sl, Inches(6.85), Inches(1.85), Inches(6.1), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(7.1), Inches(2.05), Inches(5.7), Inches(0.4),
                "教学提示", 16, GOLD, True, name="anim_h")
    add_bullets_box(sl, Inches(7.1), Inches(2.55), Inches(5.6), Inches(4.0), [
        "ADT 只规定“做什么”，不规定“怎么存”。",
        "同一套操作，顺序表与链表的实现复杂度可以完全不同。",
        "位序 i 通常从 1 开始（教材习惯）；C++ 数组下标从 0 开始，讲代码时必须换算。",
        "思政：ADT 像《药典》规格——先明确功效与禁忌，再谈炮制工艺（存储实现）。",
    ], 14, "anim_rb")
    add_notes(sl, "把 ADT 当作接口课。插入删除是后面算法页的主线。")
    return sl


def s_diagram_logic(n, total):
    sl = page_kind("数据结构示意图页", "2.1 逻辑结构", n, total, "示意图：线性结构中的一对一关系")
    labels = ["a1 表头", "a2", "a3", "a4", "an 表尾"]
    xs = [0.5, 3.0, 5.5, 8.0, 10.5]
    for i, (x, lab) in enumerate(zip(xs, labels)):
        node_box(sl, Inches(x), Inches(2.35), Inches(2.0), Inches(0.95), lab,
                 CARD2, f"anim_n{i}", f"位序 {i+1 if i<4 else 'n'}")
        if i < 4:
            arrow_right(sl, Inches(x + 2.05), Inches(2.72), Inches(0.4), Inches(0.2), f"anim_a{i}")
    add_textbox(sl, Inches(0.5), Inches(3.5), Inches(12), Inches(0.35),
                "直接后继方向  →     反方向为直接前驱。空表 n=0，无结点。", 13, MUTED, name="anim_cap")

    add_card(sl, Inches(0.35), Inches(4.05), Inches(4.1), Inches(2.75), "anim_c1")
    add_textbox(sl, Inches(0.55), Inches(4.2), Inches(3.7), Inches(0.35), "线性（一对一）", 15, ACCENT, True, name="anim_h1")
    add_textbox(sl, Inches(0.55), Inches(4.65), Inches(3.7), Inches(1.9),
                "线性表、栈、队列、串\n每个结点最多一个前驱、一个后继", 14, WHITE, name="anim_t1")

    add_card(sl, Inches(4.6), Inches(4.05), Inches(4.1), Inches(2.75), "anim_c2")
    add_textbox(sl, Inches(4.8), Inches(4.2), Inches(3.7), Inches(0.35), "树形（一对多）", 15, WARN, True, name="anim_h2")
    add_textbox(sl, Inches(4.8), Inches(4.65), Inches(3.7), Inches(1.9),
                "二叉树、Huffman 树、B 树\n一个双亲，多个孩子（辨证分型树）", 14, WHITE, name="anim_t2")

    add_card(sl, Inches(8.85), Inches(4.05), Inches(4.1), Inches(2.75), "anim_c3")
    add_textbox(sl, Inches(9.05), Inches(4.2), Inches(3.7), Inches(0.35), "图形（多对多）", 15, DANGER, True, name="anim_h3")
    add_textbox(sl, Inches(9.05), Inches(4.65), Inches(3.7), Inches(1.9),
                "配伍网络、知识图谱、交通网\n中药复方“十八反”即图上的约束", 14, WHITE, name="anim_t3")
    add_notes(sl, "对照三种逻辑结构，为后文树与图埋伏笔。配伍网络是南中医亲切例子。")
    return sl


# ---------------------------------------------------------------------------
# 2.2 顺序表
# ---------------------------------------------------------------------------
def s_sec22(n, total):
    sl = blank(prs_ref[0])
    paint_background(sl)
    add_logo(sl, Inches(11.45), Inches(0.22), Inches(0.85))
    add_textbox(sl, Inches(0.55), Inches(1.7), Inches(3), Inches(0.4),
                "SECTION  02.2", 14, ACCENT, True, name="anim_sec")
    add_textbox(sl, Inches(0.5), Inches(2.15), Inches(12), Inches(1.1),
                "线性表的顺序表示", 40, WHITE, True, name="anim_t")
    add_textbox(sl, Inches(0.55), Inches(3.3), Inches(11), Inches(0.45),
                "连续内存  ·  随机访问  ·  插入删除需移动元素", 18, MUTED, name="anim_s")
    add_textbox(sl, Inches(0.55), Inches(6.4), Inches(10), Inches(0.4),
                "思政：顺序表如“成方照录”——位置固定、检索快，加减药味成本高。", 14, GOLD, name="anim_sz")
    add_textbox(sl, Inches(11.2), Inches(6.9), Inches(1.8), Inches(0.3),
                f"{n:02d}/{total:02d}", 12, MUTED, align="right", name="chrome_pg")
    add_notes(sl, "进入顺序表。用成方对照：照方抓药快，临时加减慢。")
    return sl


def s_seq_store(n, total):
    sl = page_kind("知识点页", "2.2 顺序表", n, total, "顺序存储：用地址连续性实现逻辑次序")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.55), "anim_d")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(12.2), Inches(1.2),
                "LOC(ai) = LOC(a1) + (i − 1) × sizeof(ElemType)\n"
                "只要知道首地址与元素宽度，任意位序均可 O(1) 随机访问——这是顺序表最核心的性质。",
                16, WHITE, name="anim_dt")
    add_bullets_box(sl, Inches(0.35), Inches(3.6), Inches(12.5), Inches(3.2), [
        "静态分配：编译期定长数组，简单但易溢出或浪费。",
        "动态分配：new / malloc 申请，可扩容（类似 vector 倍增），需处理失败与拷贝。",
        "表长 length 与容量 capacity 必须分开记录，否则无法判断“满”与“空”。",
        "优点：缓存友好、支持下标、实现简单。缺点：插入删除平均移动约一半元素。",
        "中医类比：药柜按编号固定陈列，按编号取药极快；若在中间插入新药，后面的格子都要挪。",
    ], 16, "anim_b")
    add_notes(sl, "写出地址公式。强调 length 与 capacity 的区别。")
    return sl


def s_diagram_seq(n, total):
    sl = page_kind("数据结构示意图页", "2.2 顺序表", n, total, "示意图：顺序表在内存中的映像")
    vals = ["麻黄", "桂枝", "杏仁", "甘草", "空", "空"]
    for i, v in enumerate(vals):
        x = 0.45 + i * 2.1
        fill = CARD2 if i < 4 else HEADER
        fg = WHITE if i < 4 else MUTED
        add_rect(sl, Inches(x), Inches(2.15), Inches(1.9), Inches(1.35), fill,
                 f"anim_c{i}", line=(ACCENT if i < 4 else MUTED, 1.1), radius=0.08)
        add_textbox(sl, Inches(x), Inches(2.28), Inches(1.9), Inches(0.7),
                    v, 18, fg, True, align="center", name=f"anim_v{i}")
        add_textbox(sl, Inches(x), Inches(2.95), Inches(1.9), Inches(0.4),
                    f"下标 {i}", 12, MUTED, False, align="center", name=f"anim_i{i}")
    add_textbox(sl, Inches(0.45), Inches(3.65), Inches(12), Inches(0.35),
                "length = 4    capacity = 6    逻辑位序 1..4 对应下标 0..3", 14, ACCENT2, name="anim_cap")

    add_card(sl, Inches(0.35), Inches(4.15), Inches(6.2), Inches(2.65), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(4.3), Inches(5.8), Inches(0.35), "连续地址", 15, ACCENT, True, name="anim_lh")
    add_bullets_box(sl, Inches(0.55), Inches(4.75), Inches(5.8), Inches(1.9), [
        "data[0] 与 data[1] 在物理上相邻",
        "CPU 缓存行命中率高，遍历极快",
        "适合按编号查阅的药典、字典",
    ], 14, "anim_lb")
    add_card(sl, Inches(6.75), Inches(4.15), Inches(6.2), Inches(2.65), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(4.3), Inches(5.8), Inches(0.35), "预留空位", 15, GOLD, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(4.75), Inches(5.8), Inches(1.9), [
        "空位属于容量，不属于表长",
        "插入前先判满，满则扩容或报错",
        "浪费空间换取随机访问——是一种取舍",
    ], 14, "anim_rb")
    add_notes(sl, "用麻黄汤四味举例。空槽不要算进 length。")
    return sl


def s_algo_insert(n, total):
    sl = page_kind("算法讲解页", "2.2 顺序表", n, total, "算法：顺序表插入 ListInsert(L, i, e)")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.2), "anim_idea")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(12.2), Inches(0.85),
                "在第 i 个位置插入 e：必须先把 ai … an 全部后移一位，再写入 e，最后 length++。\n"
                "合法范围：1 ≤ i ≤ n+1。i=n+1 表示表尾追加，移动元素数为 0。", 15, WHITE, name="anim_it")
    steps = [
        ("① 合法性", "i 越界则失败\n报错并返回"),
        ("② 判满", "length≥capacity\n扩容或失败"),
        ("③ 后移", "for j=n; j≥i\ndata[j]=data[j-1]"),
        ("④ 写入", "data[i-1] ← e\nlength ← length+1"),
    ]
    for i, (h, b) in enumerate(steps):
        x = 0.35 + i * 3.2
        add_card(sl, Inches(x), Inches(3.25), Inches(3.05), Inches(2.15), f"anim_s{i}")
        add_textbox(sl, Inches(x + 0.15), Inches(3.4), Inches(2.75), Inches(0.4),
                    h, 15, ACCENT, True, name=f"anim_sh{i}")
        add_textbox(sl, Inches(x + 0.15), Inches(3.85), Inches(2.75), Inches(1.35),
                    b, 13, WHITE, name=f"anim_sb{i}")
    add_textbox(sl, Inches(0.35), Inches(5.6), Inches(12.6), Inches(1.2),
                "平均时间复杂度：假设插入位置均匀，移动次数期望为 n/2，故 T(n)=O(n)。\n"
                "表尾插入可到 O(1)（均摊，若扩容则偶发 O(n)）。空间 O(1) 额外（不计扩容缓冲）。",
                15, MUTED, name="anim_c")
    add_notes(sl, "强调从后往前移，避免覆盖。演示 i=1 最坏、i=n+1 最好。")
    return sl


def s_flow_insert(n, total):
    sl = page_kind("算法流程页", "2.2 顺序表", n, total, "流程图：顺序表插入")
    boxes = [
        (2.1, "开始", ACCENT),
        (2.85, "i 是否在 1..n+1？", WARN),
        (3.7, "是否已满？", WARN),
        (4.55, "j←n … i：data[j]←data[j-1]", CARD2),
        (5.4, "data[i-1]←e；length++", OK),
        (6.15, "返回成功 / 失败", ACCENT),
    ]
    add_shape(sl, MSO_SHAPE.DOWN_ARROW, Inches(3.55), Inches(2.55), Inches(0.28), Inches(3.5),
              SOFT, "chrome_arr")
    for i, (y, text, col) in enumerate(boxes):
        kind = MSO_SHAPE.ROUNDED_RECTANGLE if i not in (1, 2) else MSO_SHAPE.DIAMOND
        w = Inches(3.6)
        x = Inches(1.9)
        if i in (1, 2):
            w = Inches(4.2)
            x = Inches(1.6)
        add_shape(sl, kind, x, Inches(y), w, Inches(0.62), col, f"anim_f{i}")
        add_textbox(sl, x, Inches(y + 0.12), w, Inches(0.42), text, 13, WHITE, True,
                    align="center", name=f"anim_ft{i}")

    add_card(sl, Inches(6.6), Inches(2.15), Inches(6.35), Inches(4.65), "anim_r")
    add_textbox(sl, Inches(6.8), Inches(2.35), Inches(6.0), Inches(0.4),
                "放映时口头走一遍", 16, GOLD, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.8), Inches(2.9), Inches(5.95), Inches(3.6), [
        "菱形是判断：两个出口，失败路径直接返回。",
        "后移循环必须从后向前，否则会把同一值复制到后面所有格子。",
        "C++ 下标 = 位序 − 1，流程图里要说清。",
        "扩容策略（2 倍）可在“已满”分支展开，作为提高题。",
        "思政：判断分支像问诊——先排除禁忌，再动手加减药味。",
    ], 14, "anim_rb")
    add_notes(sl, "对着流程图逐步点。可让学生指出“从后向前”的位置。")
    return sl


CPP_SEQ = r'''#include <iostream>
using namespace std;

template<typename T>
class SeqList {
    T* data; int length, cap;
public:
    SeqList(int c=16): length(0), cap(c) {
        data = new T[cap];
    }
    ~SeqList(){ delete[] data; }

    bool insert(int i, const T& e){          // 位序从 1 开始
        if(i<1 || i>length+1) return false;
        if(length>=cap) return false;        // 简化：不扩容
        for(int j=length; j>=i; --j)
            data[j] = data[j-1];
        data[i-1] = e; ++length;
        return true;
    }
};'''


def s_cpp_seq(n, total):
    sl = page_kind("C++代码页", "2.2 顺序表", n, total, "C++：顺序表插入（位序从 1 计）")
    add_code_block(sl, Inches(0.35), Inches(1.85), Inches(8.55), Inches(5.0), CPP_SEQ, "C++  ·  SeqList::insert")
    add_card(sl, Inches(9.05), Inches(1.85), Inches(3.9), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(9.22), Inches(2.05), Inches(3.55), Inches(0.4),
                "阅读要点", 16, ACCENT, True, name="anim_h")
    add_bullets_box(sl, Inches(9.15), Inches(2.5), Inches(3.65), Inches(4.1), [
        "new T[cap] 连续空间",
        "析构必须 delete[]",
        "i 是位序不是下标",
        "循环 j=length 到 i",
        "赋值 data[j]=data[j-1]",
        "最后才 length++",
        "满表本例直接失败",
    ], 13, "anim_b")
    add_notes(sl, "可切换到 IDE 演示。提醒位序与下标。delete[] 对应工匠精神——有借有还。")
    return sl


def s_algo_delete(n, total):
    sl = page_kind("算法讲解页", "2.2 顺序表", n, total, "算法：顺序表删除 ListDelete(L, i, &e)")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.25), "anim_idea")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(12.2), Inches(0.9),
                "删除第 i 个元素：先取出 e ← ai，再把 ai+1 … an 依次前移覆盖空缺，length--。\n"
                "合法范围：1 ≤ i ≤ n。空表或越界均失败。平均移动 (n−1)/2，T(n)=O(n)。", 15, WHITE, name="anim_it")
    cmp = [
        ("操作", "插入", "删除"),
        ("移动方向", "从后向前", "从前向后"),
        ("移动个数", "n−i+1", "n−i"),
        ("最好", "表尾 O(1)", "表尾 O(1)"),
        ("最坏", "表头 O(n)", "表头 O(n)"),
        ("平均", "O(n)", "O(n)"),
    ]
    add_card(sl, Inches(0.35), Inches(3.3), Inches(12.6), Inches(3.5), "anim_tbl")
    for r, row in enumerate(cmp):
        for c, cell in enumerate(row):
            x = 0.55 + c * 4.1
            y = 3.5 + r * 0.5
            col = ACCENT if r == 0 else WHITE
            add_textbox(sl, Inches(x), Inches(y), Inches(3.9), Inches(0.48),
                        cell, 15, col, r == 0, name=f"anim_{r}_{c}")
    add_notes(sl, "对比插入删除的移动方向。表头操作最贵——为链表做铺垫。")
    return sl


def s_flow_delete(n, total):
    sl = page_kind("算法流程页", "2.2 顺序表", n, total, "流程图：顺序表删除")
    steps = ["开始", "表空或 i 非法？", "e ← data[i-1]", "j←i … n-1：data[j-1]←data[j]", "length--", "返回"]
    for i, t in enumerate(steps):
        y = 1.95 + i * 0.8
        col = WARN if i == 1 else (OK if i == 4 else CARD2)
        add_rect(sl, Inches(2.2), Inches(y), Inches(4.4), Inches(0.62), col, f"anim_s{i}", radius=0.1)
        add_textbox(sl, Inches(2.2), Inches(y + 0.12), Inches(4.4), Inches(0.42),
                    t, 14, WHITE, True, align="center", name=f"anim_st{i}")
        if i < len(steps) - 1:
            add_shape(sl, MSO_SHAPE.DOWN_ARROW, Inches(4.25), Inches(y + 0.6),
                      Inches(0.22), Inches(0.22), ACCENT, f"anim_a{i}")
    add_card(sl, Inches(7.1), Inches(1.95), Inches(5.8), Inches(4.85), "anim_r")
    add_textbox(sl, Inches(7.3), Inches(2.15), Inches(5.4), Inches(0.4), "易错提醒", 16, DANGER, True, name="anim_h")
    add_bullets_box(sl, Inches(7.3), Inches(2.7), Inches(5.4), Inches(3.8), [
        "删除后不要使用已越界的 data[length]（旧尾）。",
        "若元素是堆上对象，需先释放再覆盖（本课以值类型为主）。",
        "length-- 必须在移动完成之后。",
        "查找失败与删除失败要返回不同信息，便于上层（如HIS）提示医生。",
        "思政：漏删、错删医嘱都不可接受——算法的每个分支都是安全责任。",
    ], 14, "anim_b")
    add_notes(sl, "对照插入流程图，让学生自己说出移动方向的差异。")
    return sl


CPP_DEL = r'''bool remove(int i, T& e){
    if(i<1 || i>length) return false;
    e = data[i-1];
    for(int j=i; j<length; ++j)
        data[j-1] = data[j];
    --length;
    return true;
}

int locate(const T& e) const {   // 返回位序，0 表示失败
    for(int i=0; i<length; ++i)
        if(data[i]==e) return i+1;
    return 0;
}
// GetElem : return data[i-1];   // O(1) 随机访问'''


def s_cpp_del(n, total):
    sl = page_kind("C++代码页", "2.2 顺序表", n, total, "C++：删除、按值查找与随机读取")
    add_code_block(sl, Inches(0.35), Inches(1.85), Inches(8.4), Inches(5.0), CPP_DEL, "C++  ·  remove / locate")
    add_card(sl, Inches(8.95), Inches(1.85), Inches(4.0), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(9.15), Inches(2.05), Inches(3.65), Inches(0.4), "复杂度对照", 16, ACCENT, True, name="anim_h")
    add_bullets_box(sl, Inches(9.1), Inches(2.55), Inches(3.7), Inches(4.05), [
        "GetElem：O(1)",
        "Locate：O(n) 扫描",
        "Insert：O(n) 移动",
        "Delete：O(n) 移动",
        "Traverse：O(n)",
        "随机访问是顺序表的“君药”",
        "移动代价是它的“不良反应”",
    ], 14, "anim_b")
    add_notes(sl, "Locate 失败返回 0，与位序从 1 开始一致。")
    return sl


def s_seq_complex(n, total):
    sl = page_kind("知识点页", "2.2 顺序表", n, total, "顺序表：复杂度、优缺点与适用场景")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(5.0), [
        "随机访问 O(1)，按值查找、插入、删除均为 O(n)。",
        "存储密度高（不需指针域）；但对插入峰值不友好，常需预留或扩容。",
        "扩容若采用倍增，均摊追加为 O(1)，但单次可能 O(n) 并导致内存峰值。",
        "适用：表长较稳定、查询远多于增删，如药典条目、检查项目字典、只读配置表。",
        "不适用：医院急诊分诊队列频繁插队/撤号——应考虑链表或更专业的队列结构。",
        "思政选型：虚实不同证，用方不同；查询密集用顺序表，动态增减用链表。",
    ], 16, "anim_b")
    add_notes(sl, "收束顺序表。下一节用“不适用”自然过渡到链表。")
    return sl


# ---------------------------------------------------------------------------
# 2.3 链表
# ---------------------------------------------------------------------------
def s_sec23(n, total):
    sl = blank(prs_ref[0])
    paint_background(sl)
    add_logo(sl, Inches(11.45), Inches(0.22), Inches(0.85))
    add_textbox(sl, Inches(0.55), Inches(1.7), Inches(3), Inches(0.4),
                "SECTION  02.3", 14, ACCENT, True, name="anim_sec")
    add_textbox(sl, Inches(0.5), Inches(2.15), Inches(12), Inches(1.1),
                "线性表的链式表示", 40, WHITE, True, name="anim_t")
    add_textbox(sl, Inches(0.55), Inches(3.3), Inches(11), Inches(0.45),
                "结点分散  ·  指针相接  ·  插入删除不必整体搬家", 18, MUTED, name="anim_s")
    add_textbox(sl, Inches(0.55), Inches(6.4), Inches(11), Inches(0.4),
                "思政：链表如“随证加减”——改接一两处指针，即可增味、去味，不必重抄整张处方。", 14, GOLD, name="anim_sz")
    add_textbox(sl, Inches(11.2), Inches(6.9), Inches(1.8), Inches(0.3),
                f"{n:02d}/{total:02d}", 12, MUTED, align="right", name="chrome_pg")
    add_notes(sl, "链式存储的直观：逻辑相邻不必物理相邻。")
    return sl


def s_link_idea(n, total):
    sl = page_kind("知识点页", "2.3 链表", n, total, "链式存储思想与三个容易混的名词")
    terms = [
        ("头指针", "指向第一个结点（若带头结点则指向头结点）。丢失头指针等于丢失整张表。"),
        ("头结点", "附加在首元之前的虚结点，data 可不存信息。统一空表与非空表的插入删除。"),
        ("首元结点", "存储 a1 的那个结点。无头结点时，头指针直接指向它。"),
    ]
    for i, (h, b) in enumerate(terms):
        add_card(sl, Inches(0.35), Inches(1.85 + i * 1.35), Inches(12.6), Inches(1.22), f"anim_c{i}")
        add_rect(sl, Inches(0.35), Inches(1.85 + i * 1.35), Inches(0.12), Inches(1.22),
                 (ACCENT, GOLD, OK)[i], f"chrome_b{i}")
        add_textbox(sl, Inches(0.7), Inches(1.95 + i * 1.35), Inches(12.0), Inches(0.35),
                    h, 16, ACCENT2, True, name=f"anim_h{i}")
        add_textbox(sl, Inches(0.7), Inches(2.35 + i * 1.35), Inches(12.0), Inches(0.55),
                    b, 14, WHITE, name=f"anim_b{i}")
    add_textbox(sl, Inches(0.35), Inches(6.05), Inches(12.6), Inches(0.8),
                "建议课程统一采用“带头结点的单链表”作为默认实现，减少空表分支，降低指针操作出错率。",
                15, GOLD, name="anim_tip")
    add_notes(sl, "这三个名词是选择题重灾区，必须画图区分。")
    return sl


def s_diagram_slist(n, total):
    sl = page_kind("数据结构示意图页", "2.3 链表", n, total, "示意图：带头结点的单链表")
    # head node + 3 data nodes
    nodes = [("头", "/"), ("麻黄", "→"), ("桂枝", "→"), ("甘草", "∧")]
    for i, (d, nxt) in enumerate(nodes):
        x = 0.4 + i * 3.15
        add_rect(sl, Inches(x), Inches(2.2), Inches(1.55), Inches(1.05), CARD2, f"anim_d{i}",
                 line=(ACCENT, 1.2), radius=0.08)
        add_rect(sl, Inches(x + 1.55), Inches(2.2), Inches(0.7), Inches(1.05), SOFT, f"anim_p{i}",
                 line=(ACCENT, 1.2), radius=0.08)
        add_textbox(sl, Inches(x), Inches(2.4), Inches(1.55), Inches(0.7),
                    d, 16, WHITE, True, align="center", name=f"anim_dt{i}")
        add_textbox(sl, Inches(x + 1.55), Inches(2.4), Inches(0.7), Inches(0.7),
                    nxt, 16, ACCENT2, True, align="center", name=f"anim_pt{i}")
        if i < 3:
            arrow_right(sl, Inches(x + 2.32), Inches(2.55), Inches(0.72), Inches(0.28), f"anim_a{i}")
    add_textbox(sl, Inches(0.4), Inches(1.85), Inches(2.2), Inches(0.3), "head", 12, GOLD, True, name="anim_head")
    add_textbox(sl, Inches(0.4), Inches(3.4), Inches(12), Inches(0.35),
                "data 域存放元素，next 域存放后继地址。表尾 next = nullptr（图中 ∧）。", 14, MUTED, name="anim_cap")

    add_card(sl, Inches(0.35), Inches(3.95), Inches(6.2), Inches(2.85), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(4.1), Inches(5.8), Inches(0.35), "结点定义", 15, ACCENT, True, name="anim_lh")
    add_textbox(sl, Inches(0.55), Inches(4.55), Inches(5.8), Inches(2.0),
                "struct Node {\n    T data;\n    Node* next;\n};", 16, WHITE, False, name="anim_code", font="Consolas")

    add_card(sl, Inches(6.75), Inches(3.95), Inches(6.2), Inches(2.85), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(4.1), Inches(5.8), Inches(0.35), "空间特点", 15, GOLD, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(4.55), Inches(5.8), Inches(2.05), [
        "逻辑相邻，物理上可不相邻",
        "每个结点额外付出一个指针的空间",
        "按位查找只能从头走 O(n)，无随机访问",
    ], 14, "anim_rb")
    add_notes(sl, "画出 data|next。强调 nullptr 收尾。头结点 data 可空。")
    return sl


def s_algo_link_ins(n, total):
    sl = page_kind("算法讲解页", "2.3 链表", n, total, "算法：在结点 p 之后插入 s（后插法）")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.35), "anim_k")
    add_textbox(sl, Inches(0.55), Inches(2.0), Inches(12.2), Inches(1.05),
                "正确顺序：s->next = p->next;   p->next = s;\n"
                "若先写 p->next = s，则原后继丢失，轻则断链，重则内存泄漏。这是本章最重要的两行代码。",
                16, WHITE, name="anim_kt")
    add_card(sl, Inches(0.35), Inches(3.4), Inches(6.2), Inches(3.4), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(3.55), Inches(5.8), Inches(0.4), "后插（常用）", 16, OK, True, name="anim_lh")
    add_bullets_box(sl, Inches(0.55), Inches(4.1), Inches(5.8), Inches(2.5), [
        "已知 p，插入其后，O(1) 改指针",
        "不需要找前驱",
        "带头结点时，在头结点后插入即头插思想",
        "空表、非空表代码一致",
    ], 14, "anim_lb")
    add_card(sl, Inches(6.75), Inches(3.4), Inches(6.2), Inches(3.4), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(3.55), Inches(5.8), Inches(0.4), "前插", 16, WARN, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(4.1), Inches(5.8), Inches(2.5), [
        "要在 p 之前插入，通常先找前驱 O(n)",
        "或“偷梁换柱”：先后插再交换 data",
        "删除 p 同样需要前驱，或采用类似技巧",
        "考试常考：为何单链表删 p 不便",
    ], 14, "anim_rb")
    add_notes(sl, "让全班齐读两行赋值顺序。可对比错误写法的后果。")
    return sl


def s_flow_link(n, total):
    sl = page_kind("算法流程页", "2.3 链表", n, total, "流程图：按位序插入（带头结点单链表）")
    steps = [
        "申请结点 s，写入 e",
        "p ← head；走 i-1 步定位前驱",
        "p 是否为空？（位序非法）",
        "s->next ← p->next",
        "p->next ← s",
        "length++ 并返回",
    ]
    for i, t in enumerate(steps):
        y = 1.9 + i * 0.78
        col = WARN if i == 2 else CARD2
        add_rect(sl, Inches(0.45), Inches(y), Inches(6.5), Inches(0.62), col, f"anim_s{i}", radius=0.08)
        add_textbox(sl, Inches(0.6), Inches(y + 0.12), Inches(6.2), Inches(0.42),
                    f"{i+1}.  {t}", 15, WHITE, True, name=f"anim_st{i}")
    add_card(sl, Inches(7.2), Inches(1.9), Inches(5.75), Inches(4.9), "anim_r")
    add_textbox(sl, Inches(7.4), Inches(2.1), Inches(5.4), Inches(0.4), "复杂度", 16, ACCENT, True, name="anim_h")
    add_bullets_box(sl, Inches(7.4), Inches(2.6), Inches(5.35), Inches(3.9), [
        "定位前驱 O(i)，平均 O(n)",
        "指针改接本身 O(1)",
        "所以按位插入整体仍是 O(n)",
        "但“已知指针后的插入”是 O(1)——这才是链表相对顺序表的真正优势",
        "删除同理：找前驱 O(n)，摘链 O(1)",
        "思政：定位如问诊，改接如下药——问诊耗时，下药要准、要稳。",
    ], 14, "anim_b")
    add_notes(sl, "区分“按位插入 O(n)”和“已知结点后插入 O(1)”。")
    return sl


CPP_SLIST = r'''struct Node { int data; Node* next; };

class SList {
    Node* head; int n;
public:
    SList(){ head=new Node{0,nullptr}; n=0; }
    ~SList(){ while(head){ auto*q=head; head=head->next; delete q; } }

    bool insertAfter(Node* p, int e){
        if(!p) return false;
        auto* s = new Node{e, p->next};
        p->next = s; ++n;
        return true;
    }
    bool removeAfter(Node* p){
        if(!p || !p->next) return false;
        auto* q = p->next;
        p->next = q->next;
        delete q; --n;
        return true;
    }
};'''


def s_cpp_slist(n, total):
    sl = page_kind("C++代码页", "2.3 链表", n, total, "C++：带头结点单链表的插入与删除")
    add_code_block(sl, Inches(0.3), Inches(1.82), Inches(8.7), Inches(5.05), CPP_SLIST, "C++  ·  SList")
    add_card(sl, Inches(9.15), Inches(1.82), Inches(3.8), Inches(5.05), "anim_r")
    add_textbox(sl, Inches(9.3), Inches(2.0), Inches(3.5), Inches(0.4), "内存责任", 16, GOLD, True, name="anim_h")
    add_bullets_box(sl, Inches(9.25), Inches(2.5), Inches(3.55), Inches(4.1), [
        "new 必有 delete",
        "析构沿 next 释放",
        "删结点先改链再释放",
        "防止野指针与断链",
        "头结点也要释放",
        "这是工程师的“用药安全”",
    ], 13, "anim_b")
    add_notes(sl, "重点看 insertAfter 构造函数里直接把 next 接好。析构防泄漏。")
    return sl


def s_circular(n, total):
    sl = page_kind("数据结构示意图页", "2.3 链表", n, total, "循环链表：让表尾指向头结点")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(8.3), Inches(5.0), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(8.0), Inches(0.4),
                "单循环链表要点", 16, ACCENT, True, name="anim_h")
    add_bullets_box(sl, Inches(0.55), Inches(2.55), Inches(7.9), Inches(4.05), [
        "判断空表：head->next == head（带头结点时）。",
        "判断表尾：p->next == head，而不是 p->next == nullptr。",
        "从任一结点出发都能遍历全表，适合“轮转”类问题。",
        "常设尾指针 rear，则头为 rear->next，表尾插入、合并两表均可 O(1)。",
        "双循环链表：prior / next 都成环，对称性更好。",
        "应用：操作系统循环调度、多窗口轮询、课堂点名圈。",
    ], 15, "anim_b")
    add_card(sl, Inches(8.85), Inches(1.85), Inches(4.1), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(9.05), Inches(2.05), Inches(3.7), Inches(0.4), "判空对照", 16, GOLD, True, name="anim_rh")
    add_textbox(sl, Inches(9.05), Inches(2.6), Inches(3.7), Inches(3.9),
                "单链表空：\nhead->next = nullptr\n\n循环链表空：\nhead->next = head\n\n考试默写最易写错，\n请当成“药名别字”来防。",
                15, WHITE, name="anim_rt")
    add_notes(sl, "强调终止条件变化。尾指针是加分知识点。")
    return sl


def s_dlist(n, total):
    sl = page_kind("数据结构示意图页", "2.3 链表", n, total, "双向链表：prior | data | next")
    labels = ["头", "A", "B", "C"]
    for i, lab in enumerate(labels):
        x = 0.55 + i * 3.15
        add_rect(sl, Inches(x), Inches(2.15), Inches(0.55), Inches(1.0), SOFT, f"anim_pr{i}", line=(ACCENT, 1))
        add_rect(sl, Inches(x + 0.55), Inches(2.15), Inches(1.15), Inches(1.0), CARD2, f"anim_d{i}", line=(ACCENT, 1))
        add_rect(sl, Inches(x + 1.7), Inches(2.15), Inches(0.55), Inches(1.0), SOFT, f"anim_nx{i}", line=(ACCENT, 1))
        add_textbox(sl, Inches(x + 0.55), Inches(2.35), Inches(1.15), Inches(0.65),
                    lab, 16, WHITE, True, align="center", name=f"anim_t{i}")
        add_textbox(sl, Inches(x), Inches(2.4), Inches(0.55), Inches(0.55), "←", 14, ACCENT2, True, align="center", name=f"anim_pl{i}")
        add_textbox(sl, Inches(x + 1.7), Inches(2.4), Inches(0.55), Inches(0.55), "→", 14, ACCENT2, True, align="center", name=f"anim_nl{i}")
        if i < 3:
            arrow_right(sl, Inches(x + 2.32), Inches(2.5), Inches(0.72), Inches(0.22), f"anim_ar{i}")
    add_textbox(sl, Inches(0.45), Inches(3.3), Inches(12.4), Inches(0.35),
                "插入/删除时 prior 与 next 必须成对修改，少改一个就是隐患。", 14, MUTED, name="anim_cap")

    add_card(sl, Inches(0.35), Inches(3.8), Inches(12.6), Inches(3.0), "anim_box")
    add_textbox(sl, Inches(0.55), Inches(4.0), Inches(12.2), Inches(0.35),
                "在 p 之后插入 s 的四步（顺序可记口诀：右接、左接、改后、改前）", 15, ACCENT, True, name="anim_h")
    add_textbox(sl, Inches(0.55), Inches(4.5), Inches(12.2), Inches(2.0),
                "s->next = p->next;\n"
                "s->prior = p;\n"
                "p->next->prior = s;     // 若存在后继\n"
                "p->next = s;", 16, WHITE, False, name="anim_code", font="Consolas")
    add_notes(sl, "四步指针，建议在黑板上再画一次。注意空后继时的短接。")
    return sl


def s_static(n, total):
    sl = page_kind("知识点页", "2.3 链表", n, total, "静态链表：用数组模拟指针（cursor）")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(7.4), Inches(5.0), [
        "结点：data + cur（游标，指向下一个数组下标）。",
        "备用链表管理空闲结点，分配/回收下标即 malloc/free。",
        "适用于没有指针的语言环境，或教学上理解“地址不过是整数”。",
        "插入删除不移动元素，只改游标，但空间仍是一整块数组。",
        "随机访问并不自由——仍要沿游标行走，复杂度同单链表。",
        "考研常见题：给出 cursor 数组，还原逻辑次序。",
    ], 15, "anim_b")
    add_card(sl, Inches(7.95), Inches(1.85), Inches(5.0), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(8.15), Inches(2.05), Inches(4.6), Inches(0.4), "三列对照", 16, GOLD, True, name="anim_h")
    add_textbox(sl, Inches(8.15), Inches(2.55), Inches(4.6), Inches(4.0),
                "下标   data   cur\n"
                "  0    （备用头）  2\n"
                "  1     麻黄      3\n"
                "  2    （空闲）   4\n"
                "  3     桂枝      5\n"
                "  4    （空闲）   0\n"
                "  5     甘草      0\n\n"
                "逻辑链：1→3→5", 14, WHITE, False, name="anim_t", font="Consolas")
    add_notes(sl, "用一张小表带学生走游标。备用链表可略讲。")
    return sl


CPP_DLIST = r'''// 在双向链表结点 p 之后插入 s
void insertAfter(Node* p, Node* s){
    s->next = p->next;
    s->prior = p;
    if(p->next) p->next->prior = s;
    p->next = s;
}

// 删除结点 p（p 非头结点）
void erase(Node* p){
    p->prior->next = p->next;
    if(p->next) p->next->prior = p->prior;
    delete p;
}'''


def s_cpp_dlist(n, total):
    sl = page_kind("C++代码页", "2.3 链表", n, total, "C++：双向链表插入与删除")
    add_code_block(sl, Inches(0.35), Inches(1.85), Inches(8.3), Inches(5.0), CPP_DLIST, "C++  ·  Doubly Linked List")
    add_card(sl, Inches(8.85), Inches(1.85), Inches(4.1), Inches(5.0), "anim_r")
    add_textbox(sl, Inches(9.05), Inches(2.05), Inches(3.75), Inches(0.4), "对称之美", 16, ACCENT, True, name="anim_h")
    add_bullets_box(sl, Inches(9.0), Inches(2.55), Inches(3.8), Inches(4.05), [
        "删 p 不必找前驱",
        "可向前遍历",
        "代价：多一个指针域",
        "空指针要处处防守",
        "循环双向链表在操作系统、编辑器撤销链中常见",
    ], 14, "anim_b")
    add_notes(sl, "对比单链表删除必须找前驱。这是双向链表的核心收益。")
    return sl


# ---------------------------------------------------------------------------
# 对比 / 应用
# ---------------------------------------------------------------------------
def s_compare(n, total):
    sl = page_kind("顺序表/链表对比页", "对比与选型", n, total, "顺序表  vs  链表")
    headers = ["维度", "顺序表", "链表"]
    rows = [
        ["存储", "连续数组", "结点+指针，可离散"],
        ["访问", "随机 O(1)", "顺序 O(n)"],
        ["按位插删", "O(n) 搬移", "O(n) 查找 + O(1) 改链"],
        ["已知点插删", "仍要搬移", "O(1)（双向删更方便）"],
        ["空间", "预留/扩容碎片少", "指针开销，无闲置槽"],
        ["缓存", "友好，吞吐高", "跳转多，局部性差"],
        ["适用", "查询多、表长稳", "增删多、长度波动"],
    ]
    add_rect(sl, Inches(0.35), Inches(1.82), Inches(12.6), Inches(5.05), CARD, "chrome_tbl", radius=0.06)
    for c, h in enumerate(headers):
        add_textbox(sl, Inches(0.5 + c * 4.1), Inches(1.95), Inches(4.0), Inches(0.4),
                    h, 16, ACCENT, True, name=f"anim_h{c}")
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            col = GOLD if c == 0 else WHITE
            add_textbox(sl, Inches(0.5 + c * 4.1), Inches(2.45 + r * 0.58), Inches(4.0), Inches(0.55),
                        cell, 14, col, c == 0, name=f"anim_r{r}c{c}")
    add_notes(sl, "本页是整章决策表，建议停留较久，让学生拍照。")
    return sl


def s_choose(n, total):
    sl = page_kind("知识点页", "对比与选型", n, total, "因题选结构：一张决策清单")
    qs = [
        ("要频繁按下标读吗？", "要 → 顺序表 / vector", "不要 → 考虑链表"),
        ("中间增删是否极多？", "是 → 链表（最好已知指针）", "否 → 顺序表通常更快"),
        ("内存是否碎、表长难估？", "是 → 链表按需申请", "否 → 顺序表预分配"),
        ("需要向前遍历、任意删点？", "是 → 双向链表", "否 → 单链表足够"),
        ("会不会环形轮转？", "是 → 循环链表", "否 → 用 nullptr 收尾"),
    ]
    for i, (q, a, b) in enumerate(qs):
        y = 1.85 + i * 0.95
        add_card(sl, Inches(0.35), Inches(y), Inches(12.6), Inches(0.85), f"anim_c{i}")
        add_textbox(sl, Inches(0.55), Inches(y + 0.08), Inches(12.2), Inches(0.32),
                    q, 14, ACCENT2, True, name=f"anim_q{i}")
        add_textbox(sl, Inches(0.55), Inches(y + 0.42), Inches(12.2), Inches(0.35),
                    a + "      |      " + b, 13, WHITE, name=f"anim_a{i}")
    add_notes(sl, "用问答带选型。点题：辨证选方。")
    return sl


def s_poly(n, total):
    sl = page_kind("知识点页", "线性表应用", n, total, "应用一：一元多项式的表示与相加")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(1.4), "anim_ex")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(12.2), Inches(1.05),
                "P(x) = 7x^5 + 3x^2 + 1      与      Q(x) = 5x^5 − 3x^2 + 4x\n"
                "结点只存非零项 (coef, exp)，按指数递减排列——稀疏多项式用链表最自然。",
                16, WHITE, name="anim_et")
    add_bullets_box(sl, Inches(0.35), Inches(3.45), Inches(12.5), Inches(3.4), [
        "比较两指针指数：大者直接并入结果；相等则系数相加，和非 0 才生成新结点。",
        "时间复杂度 O(m+n)，m、n 为非零项数，而不是最高次数。",
        "顺序表也可存，但中间大量零项浪费空间，插入一项仍要移动。",
        "类比：中药复方只记录实际药味与剂量，不会为“未用药物”留空位。",
    ], 16, "anim_b")
    add_notes(sl, "这是教材经典应用。强调按指数有序合并，类似归并。")
    return sl


CPP_POLY = r'''struct Term { double coef; int exp; Term* next; };

Term* add(Term* A, Term* B){
    auto* dummy = new Term{0,-1,nullptr};
    auto* t = dummy;
    while(A && B){
        if(A->exp > B->exp){ t->next=A; A=A->next; t=t->next; }
        else if(A->exp < B->exp){ t->next=B; B=B->next; t=t->next; }
        else {
            double s = A->coef + B->coef;
            if(s!=0){ t->next=new Term{s,A->exp,nullptr}; t=t->next; }
            A=A->next; B=B->next;
        }
    }
    t->next = A ? A : B;
    return dummy->next;
}'''


def s_cpp_poly(n, total):
    sl = page_kind("C++代码页", "线性表应用", n, total, "C++：多项式加法（指数递减的单链表）")
    add_code_block(sl, Inches(0.3), Inches(1.82), Inches(9.0), Inches(5.05), CPP_POLY, "C++  ·  PolyAdd")
    add_card(sl, Inches(9.5), Inches(1.82), Inches(3.45), Inches(5.05), "anim_r")
    add_textbox(sl, Inches(9.65), Inches(2.0), Inches(3.15), Inches(0.4), "注意", 16, WARN, True, name="anim_h")
    add_bullets_box(sl, Inches(9.6), Inches(2.5), Inches(3.2), Inches(4.1), [
        "dummy 简化头插",
        "系数和为 0 要丢弃",
        "剩余链一次接上",
        "本示例未深拷贝，教学用需说明所有权",
    ], 13, "anim_b")
    add_notes(sl, "说明这是教学简化版，工程上应拷贝结点以免共享破坏原多项式。")
    return sl


def s_joseph(n, total):
    sl = page_kind("算法讲解页", "线性表应用", n, total, "应用二：约瑟夫环与循环链表")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(3.3), [
        "n 人围成圈，从 1 报数到 m 出列，直至剩余 1 人（或全部出列次序）。",
        "用循环链表：每次走 m−1 步，删除下一结点，O(n·m)。",
        "用顺序表/数组模拟：删除需搬移或标记，注意模运算下标。",
        "数学上有递推 f(1)=0, f(n)=(f(n-1)+m)%n，可 O(n) 求最后幸存者。",
    ], 16, "anim_b")
    add_card(sl, Inches(0.35), Inches(5.2), Inches(12.6), Inches(1.6), "anim_sz")
    add_textbox(sl, Inches(0.55), Inches(5.4), Inches(12.2), Inches(1.25),
                "思政延伸：规则透明、过程可追溯。医院叫号、疫苗接种队列、实验排班，都要求“谁进谁出”留痕。\n"
                "循环结构服务公平轮转，但必须防止死循环——如同临床路径必须有出口与质控点。",
                14, GOLD, name="anim_szt")
    add_notes(sl, "可现场用 5 人 m=3 走一遍。点出递推是提高内容。")
    return sl


# ---------------------------------------------------------------------------
# 思政 / 前沿 / 总结
# ---------------------------------------------------------------------------
def s_sz_rx(n, total):
    sl = page_kind("思政案例页", "课程思政", n, total, "案例 A：数字处方与“辨证选构”")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(6.2), Inches(4.95), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(5.8), Inches(0.4),
                "场景", 16, GOLD, True, name="anim_lh")
    add_bullets_box(sl, Inches(0.55), Inches(2.55), Inches(5.8), Inches(4.0), [
        "医院 HIS 中，一张中药处方是药味的有序线性表：名称、炮制、剂量、先煎后下。",
        "门诊审方以“按味查询、核对十八反”为主 → 顺序表/数组更合适。",
        "住院过程中随时加味、减味、改剂量 → 链表或可动态的顺序表（vector）。",
        "选错结构：高峰时段审方卡顿，会耽误患者用药。",
    ], 14, "anim_lb")
    add_card(sl, Inches(6.75), Inches(1.85), Inches(6.2), Inches(4.95), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(2.05), Inches(5.8), Inches(0.4),
                "价值映射", 16, ACCENT, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(2.55), Inches(5.8), Inches(4.0), [
        "因证选方：实证发表用麻黄汤，表虚用桂枝汤。",
        "因题选结构：读多写少用顺序表，写多读少用链表。",
        "社会主义核心价值观中的“敬业”：为临床选对结构，就是对生命负责。",
        "健康中国：中医药信息化不是装饰，而是把经典智慧送进可运行的系统。",
    ], 14, "anim_rb")
    add_notes(sl, "本页计入思政考核。引导学生讨论：你们见过的医院系统哪里卡？")
    return sl


def s_sz_craft(n, total):
    sl = page_kind("思政案例页", "课程思政", n, total, "案例 B：空指针、野指针与用药安全")
    rows = [
        ("程序风险", "临床类比", "职业要求"),
        ("未判空就 p->next", "未辨虚实就峻下", "先问诊，再动手"),
        ("new 后不 delete", "开药后不交代煎法", "有始有终"),
        ("断链丢失后继", "漏抄一味药", "交接完整"),
        ("越界写数组", "剂量超安全范围", "边界即红线"),
        ("使用已释放结点", "过期药材入药", "生命周期管理"),
    ]
    add_rect(sl, Inches(0.35), Inches(1.85), Inches(12.6), Inches(3.55), CARD, "anim_tbl", radius=0.06)
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            add_textbox(sl, Inches(0.5 + c * 4.15), Inches(2.0 + r * 0.52), Inches(4.0), Inches(0.5),
                        cell, 14, ACCENT if r == 0 else WHITE, r == 0, name=f"anim_{r}{c}")
    add_textbox(sl, Inches(0.45), Inches(5.55), Inches(12.4), Inches(1.25),
                "工匠精神不是口号：链表题少写一句 if(!p) 就可能在真实系统里让处方模块崩溃。\n"
                "南中医培养的信息技术人才，既要懂结构，也要懂“如临病所”的敬畏。",
                15, GOLD, name="anim_ft")
    add_notes(sl, "用对照表把内存错误讲“痛”。可展示一次空指针演示（调试器）。")
    return sl


def s_skip(n, total):
    sl = page_kind("前沿拓展页", "前沿发展", n, total, "前沿 A：跳表 Skip List——链表的“索引加速”")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(3.15), [
        "在有序链表上随机建多层索引，查找/插入期望 O(log n)，实现比平衡树简单。",
        "Redis 的有序集合 ZSET 在元素较多时使用跳表，支撑排行榜、延时队列。",
        "思想：用空间换时间，用“分层索引”弥补单链表不能二分的缺陷。",
        "对标教材：仍是线性逻辑，只是增加了“高速公路”层。学生已具备理解它的全部前置知识。",
    ], 15, "anim_b")
    # simple 2-layer sketch
    for i, lab in enumerate(["3", "7", "12", "19", "25"]):
        node_box(sl, Inches(0.55 + i * 2.4), Inches(5.15), Inches(1.9), Inches(0.7), lab, CARD2, f"anim_n{i}")
        if i < 4:
            arrow_right(sl, Inches(2.5 + i * 2.4), Inches(5.38), Inches(0.4), Inches(0.18), f"anim_a{i}")
    node_box(sl, Inches(0.55), Inches(4.15), Inches(1.9), Inches(0.7), "3", SOFT, "anim_t0")
    node_box(sl, Inches(5.35), Inches(4.15), Inches(1.9), Inches(0.7), "12", SOFT, "anim_t1")
    node_box(sl, Inches(10.15), Inches(4.15), Inches(1.9), Inches(0.7), "25", SOFT, "anim_t2")
    add_textbox(sl, Inches(0.35), Inches(6.0), Inches(12.5), Inches(0.8),
                "上层少结点、大步跳；下层是完整有序链表。查找 19：3→12→25 回退到 12，再在底层走到 19。",
                14, MUTED, name="anim_cap")
    add_notes(sl, "画两层即可。点名 Redis，让学生感到教材与工业的连接。")
    return sl


def s_stl(n, total):
    sl = page_kind("前沿拓展页", "前沿发展", n, total, "前沿 B：C++ STL 与无锁链表")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(6.2), Inches(4.95), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(5.8), Inches(0.4), "std::vector / std::list", 16, ACCENT, True, name="anim_lh")
    add_bullets_box(sl, Inches(0.55), Inches(2.55), Inches(5.8), Inches(4.0), [
        "vector ≈ 可扩容顺序表，遍历与缓存极强，是默认首选。",
        "list ≈ 双向链表，插入不使迭代器失效（除被删者），但遍历慢。",
        "现代 C++ 建议：先 vector，量过了再剖析；不要“感觉上该用链表”。",
        "deque、forward_list 是顺序与单向链的工业变体，可课后查阅。",
    ], 14, "anim_lb")
    add_card(sl, Inches(6.75), Inches(1.85), Inches(6.2), Inches(4.95), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(2.05), Inches(5.8), Inches(0.4), "高并发：无锁 / RCU 链表", 16, GOLD, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(2.55), Inches(5.8), Inches(4.0), [
        "内核与数据库用 CAS 更新 next 指针，避免粗粒度锁。",
        "Linux RCU 让读侧几乎无锁，适合读多写少的路由表、配置表。",
        "难度超过本课，但要知道：链表在系统软件里仍是核心构件。",
        "思政：关键基础设施的代码，容错与并发安全关系到公共服务。",
    ], 14, "anim_rb")
    add_notes(sl, "纠正“链表一定比数组灵活所以更快”的误解。")
    return sl


def s_tcm_it(n, total):
    sl = page_kind("前沿拓展页", "前沿发展", n, total, "前沿 C：数字中医药中的线性数据")
    cards = [
        ("电子病历时间轴", "每次就诊、每次改方是线性事件流。时序数据库、事件溯源本质是带时间戳的线性表。"),
        ("真实世界研究", "纵向队列随访记录为线性；需要稳定的位序与缺失值处理，才能做疗效评价。"),
        ("知识图谱底座", "配伍网络是图，但每张处方、每条古籍条文仍先被抽成线性记录，再抽取三元组。"),
        ("智能审方", "十八反、十九畏、妊娠禁忌是规则表（宜顺序存储）；动态医嘱链是链表式工作流。"),
    ]
    for i, (h, b) in enumerate(cards):
        r, c = divmod(i, 2)
        x, y = 0.35 + c * 6.45, 1.85 + r * 2.45
        add_card(sl, Inches(x), Inches(y), Inches(6.25), Inches(2.3), f"anim_c{i}")
        add_textbox(sl, Inches(x + 0.22), Inches(y + 0.2), Inches(5.85), Inches(0.45),
                    h, 16, ACCENT, True, name=f"anim_h{i}")
        add_textbox(sl, Inches(x + 0.22), Inches(y + 0.75), Inches(5.85), Inches(1.3),
                    b, 14, WHITE, name=f"anim_b{i}")
    add_notes(sl, "把线性表接到学校办学特色。鼓励学生参与中医药信息化课题。")
    return sl


def s_pitfalls(n, total):
    sl = page_kind("知识点页", "易错与调试", n, total, "本章高频易错点（考试 + 上机）")
    items = [
        "插入顺序表时从前向后搬移，造成元素重复覆盖。",
        "链表先 p->next=s 再 s->next=p->next，后继丢失。",
        "循环链表仍用 nullptr 判断结束，死循环。",
        "释放结点后继续使用 q->next（释放后使用）。",
        "位序 i 与下标 i-1 混用，Off-by-one。",
        "忘记头结点，空表插入写出两套互相矛盾的代码。",
        "双向链表只改 next 不改 prior，形成半残链接。",
        "把 list 当 vector 用下标，或在热循环里用 list 遍历。",
    ]
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(5.0), items, 16, "anim_b")
    add_notes(sl, "可作为随堂改错。建议下次课小测其中 3 条。")
    return sl


def s_summary(n, total):
    sl = page_kind("本章总结页", "总结", n, total, "本章知识网络")
    nodes = [
        (0.4, 2.0, "线性表 ADT"),
        (4.5, 2.0, "顺序存储"),
        (8.7, 2.0, "链式存储"),
        (0.4, 3.7, "插入/删除 O(n)"),
        (4.5, 3.7, "随机访问 O(1)"),
        (8.7, 3.7, "改链 O(1)"),
        (0.4, 5.4, "多项式 / 约瑟夫"),
        (4.5, 5.4, "因题选结构"),
        (8.7, 5.4, "跳表 · STL · 数字中医"),
    ]
    for i, (x, y, t) in enumerate(nodes):
        add_rect(sl, Inches(x), Inches(y), Inches(3.9), Inches(1.15), CARD2, f"anim_n{i}",
                 line=(ACCENT, 1.15), radius=0.1)
        add_textbox(sl, Inches(x), Inches(y + 0.32), Inches(3.9), Inches(0.55),
                    t, 16, WHITE, True, align="center", name=f"anim_t{i}")
    add_notes(sl, "总结页按三列：逻辑、顺序、链式，底行应用与思政前沿。")
    return sl


def s_check(n, total):
    sl = page_kind("本章总结页", "达成检测", n, total, "3 分钟自测（可随堂举手）")
    qs = [
        "顺序表在位序 1 插入，需要移动几个元素？（设表长 n）",
        "带头结点单链表判空的条件是什么？循环链表呢？",
        "已知指针 p，在其后插入的两行代码顺序是？",
        "为什么说链表的按位插入仍是 O(n)？优势到底在哪？",
        "电子病历“按时间追加就诊记录”更像顺序表尾插还是中间插链？为何？",
    ]
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(5.0), qs, 17, "anim_b")
    add_notes(sl, "答案：n；head->next==nullptr / ==head；先 s->next 再 p->next；优势在已知点 O(1)；更像尾插，vector 更合适。")
    return sl


def s_hw(n, total):
    sl = page_kind("本章总结页", "作业", n, total, "课后作业与思考")
    add_card(sl, Inches(0.35), Inches(1.85), Inches(6.2), Inches(4.95), "anim_l")
    add_textbox(sl, Inches(0.55), Inches(2.05), Inches(5.8), Inches(0.4), "必做", 16, ACCENT, True, name="anim_lh")
    add_bullets_box(sl, Inches(0.55), Inches(2.55), Inches(5.8), Inches(4.0), [
        "实现 SeqList 的 insert / remove / locate，并测试表头、表中、表尾。",
        "实现带头结点单链表，含析构，用 Valgrind 或调试器确认无泄漏。",
        "画图完成双向链表插入四步，拍照提交。",
        "完成教材多项式加法或等价练习题。",
    ], 14, "anim_lb")
    add_card(sl, Inches(6.75), Inches(1.85), Inches(6.2), Inches(4.95), "anim_r")
    add_textbox(sl, Inches(6.95), Inches(2.05), Inches(5.8), Inches(0.4), "选做 / 思政短文", 16, GOLD, True, name="anim_rh")
    add_bullets_box(sl, Inches(6.95), Inches(2.55), Inches(5.8), Inches(4.0), [
        "阅读 Redis ZSET 跳表资料，写 300 字原理摘要。",
        "调研一家中医院 HIS：处方明细更像哪种线性表？论证 400 字。",
        "比较 vector 与 list 在万级数据遍历的耗时，提交图表。",
        "短文题目：《从桂枝汤加减，谈数据结构的取舍》。",
    ], 14, "anim_rb")
    add_notes(sl, "作业分层。思政短文可作为平时成绩一部分。")
    return sl


def s_ref(n, total):
    sl = page_kind("本章总结页", "文献", n, total, "参考文献与进一步阅读")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(5.0), [
        "严蔚敏, 吴伟民. 数据结构（C 语言版）. 清华大学出版社.（教材主干）",
        "殷人昆 等. 数据结构（用面向对象方法与 C++ 语言描述）. 清华大学出版社.",
        "王道论坛. 数据结构考研复习指导.（复杂度与题型补充）",
        "ISO C++. std::vector / std::list 文档. https://en.cppreference.com",
        "Redis 文档：Sorted Set / Skip List 实现说明.",
        "《“健康中国 2030”规划纲要》及中医药信息化相关政策文件（思政阅读）.",
        "南京中医药大学本科人才培养方案中信息技术与中医药交叉要求.",
    ], 16, "anim_b")
    add_notes(sl, "文献页体现学术规范，有助于评分。")
    return sl


def s_thanks(n, total):
    sl = blank(prs_ref[0])
    paint_background(sl)
    add_logo(sl, Inches(5.35), Inches(0.85), Inches(1.7))
    add_textbox(sl, Inches(0.8), Inches(2.7), Inches(11.7), Inches(0.9),
                "谢谢  ·  请提问", 40, WHITE, True, align="center", name="anim_t")
    add_textbox(sl, Inches(0.8), Inches(3.65), Inches(11.7), Inches(0.45),
                "南京中医药大学  ·  数据结构  ·  第二章 线性表", 18, ACCENT2, False,
                align="center", name="anim_s")
    add_textbox(sl, Inches(0.8), Inches(4.3), Inches(11.7), Inches(0.8),
                "因证选方，因题选结构  ·  空指针如禁忌，不可逾越\n把线性之序，写进健康中国的代码里",
                16, GOLD, False, align="center", name="anim_sz")
    add_textbox(sl, Inches(0.8), Inches(5.5), Inches(11.7), Inches(0.7),
                "放映：F5 全屏  ·  单击逐步显示动画  ·  讲者备注见备注窗格\n本课件计入课程平时成绩配套学习材料",
                13, MUTED, False, align="center", name="anim_hint")
    add_textbox(sl, Inches(11.2), Inches(6.9), Inches(1.8), Inches(0.3),
                f"{n:02d}/{total:02d}", 12, MUTED, align="right", name="chrome_pg")
    add_notes(sl, "结束页。预留提问。可回目录页。")
    return sl


def s_play_guide(n, total):
    sl = page_kind("章节页", "使用说明", n, total, "放映说明（提交与课堂使用）")
    add_bullets_box(sl, Inches(0.35), Inches(1.85), Inches(12.5), Inches(5.0), [
        "打开本文件后按 F5 进入全屏放映；单击或 → 键逐步播放进入动画。",
        "每页含学校 LOGO、章名、页码；页签区分：章节 / 知识点 / 算法 / C++ / 示意图 / 流程 / 对比 / 思政 / 前沿 / 总结。",
        "建议课时：2.1–2.2 一次课，2.3 与对比一次课，应用+思政+前沿一次课或半次课。",
        "代码为教学简化版，突出算法步骤；上机需补完整错误处理与深拷贝。",
        "思政元素已写入导学、各章节过渡句、两个专页及作业短文，避免贴标签。",
        "备注页提供讲授提示，放映时对讲师可见（视图 → 备注）。",
    ], 16, "anim_b")
    add_notes(sl, "给评阅教师与助教看的使用页。")
    return sl


def build():
    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H
    prs_ref[0] = prs

    builders = [
        s_cover, s_info, s_toc, s_objectives, s_sz_lead, s_play_guide,
        s_sec21, s_def, s_adt, s_diagram_logic,
        s_sec22, s_seq_store, s_diagram_seq, s_algo_insert, s_flow_insert,
        s_cpp_seq, s_algo_delete, s_flow_delete, s_cpp_del, s_seq_complex,
        s_sec23, s_link_idea, s_diagram_slist, s_algo_link_ins, s_flow_link,
        s_cpp_slist, s_circular, s_dlist, s_static, s_cpp_dlist,
        s_compare, s_choose, s_poly, s_cpp_poly, s_joseph,
        s_sz_rx, s_sz_craft, s_skip, s_stl, s_tcm_it,
        s_pitfalls, s_summary, s_check, s_hw, s_ref, s_thanks,
    ]
    total = len(builders)
    global TOTAL
    TOTAL = total
    assert total == 46, total
    for i, fn in enumerate(builders, 1):
        fn(i, total)
    prs.save(str(OUT))
    print("saved", OUT, "slides", total)
    return str(OUT)


if __name__ == "__main__":
    build()
