"""Preset Academic Formatting Standards for Paper Setting v1.1."""

from __future__ import annotations

from typing import Any

PRESET_STANDARDS: list[dict[str, Any]] = [
    {
        "id": "gb-t-7713-1",
        "name": "GB/T 7713.1-2006 学位论文通用规范 (推荐)",
        "badge": "国家标准",
        "badge_color": "emerald",
        "category": "学位论文",
        "description": "国家标准研究生/本科毕业论文基础规范。版芯规范、正文小四宋体、1.5倍行距、首行缩进2字符。",
        "margins": {"top": "2.5cm", "bottom": "2.5cm", "left": "3.0cm", "right": "2.5cm"},
        "typography": {
            "body": {"font": "宋体 / Times New Roman", "size": "小四 (12pt)", "line_spacing": 1.5, "indent": "2字符 (24pt)"},
            "heading1": {"font": "黑体", "size": "三号 (16pt)", "align": "居中", "space": "段前12pt 段后6pt"},
            "heading2": {"font": "黑体", "size": "四号 (14pt)", "align": "居左", "space": "段前6pt 段后6pt"},
            "heading3": {"font": "黑体", "size": "小四 (12pt)", "align": "居左", "space": "段前3pt 段后3pt"},
            "caption": {"font": "宋体 / Times New Roman", "size": "五号 (10.5pt)", "align": "居中"},
            "references": {"font": "宋体 / Times New Roman", "size": "五号 (10.5pt)", "standard": "GB/T 7714-2015 顺序编码制"},
        },
        "is_default": True,
    },
    {
        "id": "ucas-thesis",
        "name": "中国科学院大学 (国科大) 学位论文规范",
        "badge": "理工权威",
        "badge_color": "blue",
        "category": "高校模板",
        "description": "严格对齐国科大学位办标准。支持复杂科技文献引用、图表双语题注与数学公式居中编号右对齐。",
        "margins": {"top": "2.8cm", "bottom": "2.5cm", "left": "3.0cm", "right": "2.5cm"},
        "typography": {
            "body": {"font": "宋体 / Times New Roman", "size": "小四 (12pt)", "line_spacing": 1.4, "indent": "2字符"},
            "heading1": {"font": "黑体", "size": "小二 (18pt)", "align": "居中", "space": "段前18pt 段后12pt"},
            "heading2": {"font": "黑体", "size": "四号 (14pt)", "align": "居左", "space": "段前12pt 段后6pt"},
            "heading3": {"font": "黑体", "size": "小四 (12pt)", "align": "居左", "space": "段前6pt 段后3pt"},
            "caption": {"font": "黑体 (中文) / Arial", "size": "五号 (10.5pt)", "align": "居中"},
            "references": {"font": "宋体 / Times New Roman", "size": "五号 (10.5pt)", "standard": "国科大顺序编码"},
        },
        "is_default": False,
    },
    {
        "id": "cass-humanities",
        "name": "高校人文社科学报标准预设",
        "badge": "社科经管",
        "badge_color": "purple",
        "category": "期刊社科",
        "description": "专为人文社科、经管法学论文设计。支持正文夹注转换为页下真脚注、双语摘要与独立引文块缩进。",
        "margins": {"top": "2.54cm", "bottom": "2.54cm", "left": "3.18cm", "right": "3.18cm"},
        "typography": {
            "body": {"font": "仿宋 / Times New Roman", "size": "五号 (10.5pt)", "line_spacing": 1.35, "indent": "2字符"},
            "heading1": {"font": "黑体", "size": "四号 (14pt)", "align": "居左", "space": "段前8pt 段后4pt"},
            "heading2": {"font": "楷体", "size": "五号 (10.5pt)", "align": "居左", "space": "段前4pt 段后2pt"},
            "heading3": {"font": "仿宋加粗", "size": "五号 (10.5pt)", "align": "居左", "space": "段前2pt 段后0pt"},
            "caption": {"font": "仿宋", "size": "小五 (9pt)", "align": "居中"},
            "references": {"font": "仿宋", "size": "小五 (9pt)", "standard": "著者-出版年制 / 页下真脚注"},
        },
        "is_default": False,
    },
    {
        "id": "ieee-style",
        "name": "工程技术期刊双栏排版预设 (IEEE / 中国电机工程)",
        "badge": "工程期刊",
        "badge_color": "amber",
        "category": "科技期刊",
        "description": "适用于国内顶级工程学报与 IEEE 风格投稿。规范小五号字高密度排版、多栏版心与紧凑行间距。",
        "margins": {"top": "2.0cm", "bottom": "2.0cm", "left": "2.0cm", "right": "2.0cm"},
        "typography": {
            "body": {"font": "宋体 / Times New Roman", "size": "五号 (10.5pt)", "line_spacing": 1.15, "indent": "2字符"},
            "heading1": {"font": "黑体", "size": "小四 (12pt)", "align": "居左", "space": "段前6pt 段后3pt"},
            "heading2": {"font": "黑体", "size": "五号 (10.5pt)", "align": "居左", "space": "段前3pt 段后2pt"},
            "heading3": {"font": "楷体", "size": "五号 (10.5pt)", "align": "居左", "space": "段前2pt 段后0pt"},
            "caption": {"font": "黑体", "size": "小五 (9pt)", "align": "居中"},
            "references": {"font": "宋体", "size": "小五 (9pt)", "standard": "IEEE 顺序编码"},
        },
        "is_default": False,
    },
]


def get_standard(standard_id: str) -> dict[str, Any]:
    for std in PRESET_STANDARDS:
        if std["id"] == standard_id:
            return std
    return PRESET_STANDARDS[0]
