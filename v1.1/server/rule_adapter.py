"""Rule Pack Adapter for Paper Setting v1.1.

Translates high-level preset standards (GB/T, UCAS, CASS, IEEE) into
concrete, executable RulePack configurations.
"""

from __future__ import annotations

from typing import Any

from paper_setting_core.rulepacks.defaults import default_rule_pack
from paper_setting_core.rulepacks.models import RulePack

from .presets import get_standard


def _parse_margin_mm(val_str: str) -> float:
    """Parse margin string with units (e.g., '2.5cm', '25.4mm') into millimeters."""
    s = str(val_str).strip().lower()
    if s.endswith("cm"):
        return round(float(s[:-2]) * 10.0, 1)
    if s.endswith("mm"):
        return round(float(s[:-2]), 1)
    return float(s)


def get_configured_rule_pack(standard_id: str = "gb-t-7713-1") -> RulePack:
    """Build and configure a RulePack adapted from built-in standard specifications."""
    std = get_standard(standard_id)
    rule_pack = default_rule_pack()
    rule_pack.name = std["name"]
    rule_pack.description = std["description"]

    # Configure margins from standard specification
    if "margins" in std:
        rule_pack.page.margin_top_mm = _parse_margin_mm(std["margins"]["top"])
        rule_pack.page.margin_bottom_mm = _parse_margin_mm(std["margins"]["bottom"])
        rule_pack.page.margin_left_mm = _parse_margin_mm(std["margins"]["left"])
        rule_pack.page.margin_right_mm = _parse_margin_mm(std["margins"]["right"])

    # Enforce pure black font, regular non-italic, and no stray underlines across all roles
    for role in rule_pack.roles:
        if role.character:
            role.character.italic = False
            role.character.color = "000000"
            role.character.underline = False

    # Customize based on standard preset
    if standard_id == "ucas-thesis":
        for role in rule_pack.roles:
            if role.role == "heading_1":
                if role.character:
                    role.character.size_pt = 18.0  # 小二 (18pt)
                if role.paragraph:
                    role.paragraph.space_before_pt = 18.0
                    role.paragraph.space_after_pt = 12.0
            elif role.role in ("body", "abstract_body"):
                if role.paragraph:
                    role.paragraph.line_spacing = 1.4  # 1.4倍行距
    elif standard_id == "cass-humanities":
        for role in rule_pack.roles:
            if role.role in ("body", "abstract_body"):
                if role.paragraph:
                    role.paragraph.line_spacing = 1.35
                if role.character:
                    role.character.east_asia_font = "仿宋"
                    role.character.size_pt = 10.5
            elif role.role == "heading_1":
                if role.character:
                    role.character.size_pt = 14.0
                if role.paragraph:
                    role.paragraph.alignment = "left"
            elif role.role == "heading_2":
                if role.character:
                    role.character.east_asia_font = "楷体"
                    role.character.size_pt = 10.5
                    role.character.bold = False
            elif role.role == "reference_entry":
                if role.character:
                    role.character.east_asia_font = "仿宋"
                    role.character.size_pt = 9.0
    elif standard_id == "ieee-style":
        for role in rule_pack.roles:
            if role.role in ("body", "abstract_body"):
                if role.paragraph:
                    role.paragraph.line_spacing = 1.15
                if role.character:
                    role.character.size_pt = 10.5
            elif role.role == "heading_1":
                if role.character:
                    role.character.size_pt = 12.0
                if role.paragraph:
                    role.paragraph.alignment = "left"
            elif role.role in ("figure_caption", "table_caption", "reference_entry"):
                if role.character:
                    role.character.size_pt = 9.0

    return rule_pack
