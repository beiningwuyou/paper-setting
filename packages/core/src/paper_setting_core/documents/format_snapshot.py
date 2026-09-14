from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from docx.enum.section import WD_ORIENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

from paper_setting_core.documents.models import EffectiveFormat, SectionFormatSnapshot

MIXED = "mixed"


@dataclass(frozen=True)
class FormatContext:
    paragraph_defaults: dict[str, Any] = field(default_factory=dict)
    character_defaults: dict[str, Any] = field(default_factory=dict)
    theme_fonts: dict[str, str] = field(default_factory=dict)

ALIGNMENT_NAMES = {
    WD_ALIGN_PARAGRAPH.LEFT: "left",
    WD_ALIGN_PARAGRAPH.CENTER: "center",
    WD_ALIGN_PARAGRAPH.RIGHT: "right",
    WD_ALIGN_PARAGRAPH.JUSTIFY: "justify",
}

OOXML_ALIGNMENT_NAMES = {
    "left": "left",
    "center": "center",
    "right": "right",
    "both": "justify",
    "distribute": "justify",
}

LINE_SPACING_MODES = {
    WD_LINE_SPACING.SINGLE: "multiple",
    WD_LINE_SPACING.ONE_POINT_FIVE: "multiple",
    WD_LINE_SPACING.DOUBLE: "multiple",
    WD_LINE_SPACING.MULTIPLE: "multiple",
    WD_LINE_SPACING.EXACTLY: "exact",
    WD_LINE_SPACING.AT_LEAST: "at_least",
}

DRAWINGML_NS = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}


def _style_chain(style: Any) -> Iterable[Any]:
    seen: set[str] = set()
    current = style
    while current is not None:
        style_id = str(getattr(current, "style_id", id(current)))
        if style_id in seen:
            return
        seen.add(style_id)
        yield current
        current = getattr(current, "base_style", None)


def _first_value(objects: Iterable[Any], attribute: str) -> Any:
    for item in objects:
        value = getattr(item, attribute, None)
        if value is not None:
            return value
    return None


def _round_number(value: float, digits: int = 3) -> float:
    return round(float(value), digits)


def _points(value: Any) -> float | None:
    if value is None:
        return None
    if hasattr(value, "pt"):
        return _round_number(value.pt)
    return _round_number(value)


def _alignment(value: Any) -> str | None:
    return ALIGNMENT_NAMES.get(value)


def _line_spacing_mode(value: Any, line_spacing: Any) -> str | None:
    if value in LINE_SPACING_MODES:
        return LINE_SPACING_MODES[value]
    return "multiple" if line_spacing is not None else None


def _on_off(element: Any) -> bool | None:
    if element is None:
        return None
    value = element.get(qn("w:val"))
    return value is None or value.casefold() not in {"0", "false", "off", "none"}


def _numeric_attribute(element: Any, attribute: str, divisor: float) -> float | None:
    if element is None:
        return None
    value = element.get(qn(f"w:{attribute}"))
    if value is None:
        return None
    try:
        return _round_number(float(value) / divisor)
    except ValueError:
        return None


def _theme_font_map(document: Any) -> dict[str, str]:
    theme_part = next(
        (part for part in document.part.package.parts if "theme" in str(part.partname)),
        None,
    )
    if theme_part is None:
        return {}
    try:
        root = etree.fromstring(theme_part.blob)
    except (etree.XMLSyntaxError, ValueError, TypeError):
        return {}
    result: dict[str, str] = {}
    for family in ("major", "minor"):
        node = root.find(f".//a:{family}Font", namespaces=DRAWINGML_NS)
        if node is None:
            continue
        latin_node = node.find("./a:latin", namespaces=DRAWINGML_NS)
        latin = latin_node.get("typeface") if latin_node is not None else None
        east_asia_node = node.find("./a:ea", namespaces=DRAWINGML_NS)
        east_asia = east_asia_node.get("typeface") if east_asia_node is not None else None
        if not east_asia:
            hans_node = next(
                (
                    font_node
                    for font_node in node.findall("./a:font", namespaces=DRAWINGML_NS)
                    if font_node.get("script") == "Hans"
                ),
                None,
            )
            east_asia = hans_node.get("typeface") if hans_node is not None else None
        if latin:
            for suffix in ("Ascii", "HAnsi", "Latin"):
                result[f"{family}{suffix}".casefold()] = latin
        if east_asia:
            result[f"{family}EastAsia".casefold()] = east_asia
    return result


def _rfonts_from_rprs(
    rprs: Iterable[Any],
    literal_attributes: tuple[str, ...],
    theme_attributes: tuple[str, ...],
    context: FormatContext,
) -> str | None:
    for rpr in rprs:
        rfonts = getattr(rpr, "rFonts", None)
        if rfonts is None:
            continue
        for attribute in literal_attributes:
            value = rfonts.get(qn(f"w:{attribute}"))
            if value:
                return str(value)
        for attribute in theme_attributes:
            reference = rfonts.get(qn(f"w:{attribute}"))
            if reference:
                resolved = context.theme_fonts.get(str(reference).casefold())
                if resolved:
                    return resolved
    return None


def _paragraph_defaults(styles_element: Any) -> dict[str, Any]:
    nodes = styles_element.xpath("./w:docDefaults/w:pPrDefault/w:pPr")
    if not nodes:
        return {}
    ppr = nodes[0]
    spacing = ppr.find(qn("w:spacing"))
    indentation = ppr.find(qn("w:ind"))
    raw_line_rule = spacing.get(qn("w:lineRule")) if spacing is not None else None
    line_rule = str(raw_line_rule) if raw_line_rule is not None else None
    line_value = spacing.get(qn("w:line")) if spacing is not None else None
    line_spacing: float | None = None
    line_spacing_mode: str | None = None
    if line_value is not None:
        divisor = 240 if line_rule in {None, "auto"} else 20
        line_spacing = _round_number(float(line_value) / divisor)
        line_spacing_mode = {
            "exact": "exact",
            "atLeast": "at_least",
        }.get(line_rule or "", "multiple")
    first_line = _numeric_attribute(indentation, "firstLine", 20)
    hanging = _numeric_attribute(indentation, "hanging", 20)
    if first_line is None and hanging is not None:
        first_line = -hanging
    alignment = ppr.find(qn("w:jc"))
    values = {
        "alignment": (
            OOXML_ALIGNMENT_NAMES.get(alignment.get(qn("w:val")))
            if alignment is not None
            else None
        ),
        "first_line_indent_pt": first_line,
        "left_indent_pt": _numeric_attribute(indentation, "left", 20),
        "right_indent_pt": _numeric_attribute(indentation, "right", 20),
        "space_before_pt": _numeric_attribute(spacing, "before", 20),
        "space_after_pt": _numeric_attribute(spacing, "after", 20),
        "line_spacing": line_spacing,
        "line_spacing_mode": line_spacing_mode,
        "keep_with_next": _on_off(ppr.find(qn("w:keepNext"))),
        "keep_together": _on_off(ppr.find(qn("w:keepLines"))),
        "page_break_before": _on_off(ppr.find(qn("w:pageBreakBefore"))),
    }
    return {key: value for key, value in values.items() if value is not None}


def _character_defaults(styles_element: Any, theme_fonts: dict[str, str]) -> dict[str, Any]:
    nodes = styles_element.xpath("./w:docDefaults/w:rPrDefault/w:rPr")
    if not nodes:
        return {}
    rpr = nodes[0]
    context = FormatContext(theme_fonts=theme_fonts)
    size = rpr.find(qn("w:sz"))
    color = rpr.find(qn("w:color"))
    color_value = color.get(qn("w:val")) if color is not None else None
    values = {
        "east_asia_font": _rfonts_from_rprs(
            [rpr], ("eastAsia",), ("eastAsiaTheme",), context
        ),
        "latin_font": _rfonts_from_rprs(
            [rpr], ("ascii", "hAnsi"), ("asciiTheme", "hAnsiTheme"), context
        ),
        "size_pt": _numeric_attribute(size, "val", 2),
        "color": (
            str(color_value).upper()
            if color_value and str(color_value).casefold() != "auto"
            else None
        ),
        "bold": _on_off(rpr.find(qn("w:b"))),
        "italic": _on_off(rpr.find(qn("w:i"))),
        "underline": _on_off(rpr.find(qn("w:u"))),
    }
    return {key: value for key, value in values.items() if value is not None}


def build_format_context(document: Any) -> FormatContext:
    theme_fonts = _theme_font_map(document)
    return FormatContext(
        paragraph_defaults=_paragraph_defaults(document.styles.element),
        character_defaults=_character_defaults(document.styles.element, theme_fonts),
        theme_fonts=theme_fonts,
    )


def _paragraph_sources(paragraph: Paragraph) -> list[Any]:
    sources = [paragraph.paragraph_format]
    sources.extend(style.paragraph_format for style in _style_chain(paragraph.style))
    return sources


def _paragraph_line_spacing_value(paragraph: Paragraph, attribute: str) -> float | None:
    pprs = [paragraph._p.pPr]
    pprs.extend(getattr(style.element, "pPr", None) for style in _style_chain(paragraph.style))
    for ppr in pprs:
        if ppr is None:
            continue
        spacing = ppr.find(qn("w:spacing"))
        value = spacing.get(qn(f"w:{attribute}")) if spacing is not None else None
        if value is not None:
            try:
                return _round_number(float(value) / 100)
            except ValueError:
                return None
    return None


def _font_sources(paragraph: Paragraph, run: Any) -> list[Any]:
    sources = [run.font]
    run_style = getattr(run, "style", None)
    sources.extend(style.font for style in _style_chain(run_style))
    sources.extend(style.font for style in _style_chain(paragraph.style))
    return sources


def _rpr_sources(paragraph: Paragraph, run: Any) -> Iterable[Any]:
    run_rpr = getattr(run._r, "rPr", None)
    if run_rpr is not None:
        yield run_rpr
    run_style = getattr(run, "style", None)
    for style in _style_chain(run_style):
        rpr = getattr(style.element, "rPr", None)
        if rpr is not None:
            yield rpr
    for style in _style_chain(paragraph.style):
        rpr = getattr(style.element, "rPr", None)
        if rpr is not None:
            yield rpr


def _rfonts_value(
    paragraph: Paragraph,
    run: Any,
    literal_attributes: tuple[str, ...],
    theme_attributes: tuple[str, ...],
    context: FormatContext,
) -> str | None:
    return _rfonts_from_rprs(
        _rpr_sources(paragraph, run),
        literal_attributes,
        theme_attributes,
        context,
    )


def _font_color(fonts: Iterable[Any]) -> str | None:
    for font in fonts:
        rgb = getattr(getattr(font, "color", None), "rgb", None)
        if rgb is not None:
            return str(rgb).upper()
    return None


def _run_is_protected(run: Any) -> bool:
    xml = run._r.xml
    return any(
        marker in xml
        for marker in ("<w:fldChar", "<w:instrText", "<w:drawing", "<w:object", "<m:oMath")
    )


def _run_format(paragraph: Paragraph, run: Any, context: FormatContext) -> dict[str, Any]:
    fonts = _font_sources(paragraph, run)
    name = _first_value(fonts, "name")
    size = _first_value(fonts, "size")
    bold = _first_value(fonts, "bold")
    italic = _first_value(fonts, "italic")
    underline = _first_value(fonts, "underline")
    return {
        "east_asia_font": _rfonts_value(
            paragraph, run, ("eastAsia",), ("eastAsiaTheme",), context
        )
        or context.character_defaults.get("east_asia_font"),
        "latin_font": _rfonts_value(
            paragraph,
            run,
            ("ascii", "hAnsi"),
            ("asciiTheme", "hAnsiTheme"),
            context,
        )
        or name
        or context.character_defaults.get("latin_font"),
        "size_pt": _points(size) or context.character_defaults.get("size_pt"),
        "color": _font_color(fonts) or context.character_defaults.get("color"),
        "bold": (
            bool(bold) if bold is not None else context.character_defaults.get("bold")
        ),
        "italic": (
            bool(italic) if italic is not None else context.character_defaults.get("italic", False)
        ),
        "underline": (
            bool(underline)
            if underline is not None
            else context.character_defaults.get("underline", False)
        ),
    }


def _uniform_run_format(paragraph: Paragraph, context: FormatContext) -> dict[str, Any]:
    values = [
        _run_format(paragraph, run, context)
        for run in paragraph.runs
        if not _run_is_protected(run)
    ]
    keys = (
        "east_asia_font",
        "latin_font",
        "size_pt",
        "color",
        "bold",
        "italic",
        "underline",
    )
    if not values:
        return {key: None for key in keys}
    result: dict[str, Any] = {}
    for key in keys:
        observed = {item[key] for item in values}
        result[key] = observed.pop() if len(observed) == 1 else MIXED
    return result


def snapshot_paragraph_format(
    paragraph: Paragraph,
    context: FormatContext | None = None,
) -> EffectiveFormat:
    context = context or FormatContext()
    sources = _paragraph_sources(paragraph)
    line_spacing = _first_value(sources, "line_spacing")
    line_spacing_rule = _first_value(sources, "line_spacing_rule")
    if line_spacing is None:
        line_spacing = context.paragraph_defaults.get("line_spacing")
        line_spacing_mode = context.paragraph_defaults.get("line_spacing_mode")
    else:
        line_spacing_mode = _line_spacing_mode(line_spacing_rule, line_spacing)

    def inherited(attribute: str, default_key: str) -> Any:
        value = _first_value(sources, attribute)
        return value if value is not None else context.paragraph_defaults.get(default_key)

    paragraph_values = {
        "alignment": _alignment(inherited("alignment", "alignment"))
        or context.paragraph_defaults.get("alignment"),
        "first_line_indent_pt": _points(
            inherited("first_line_indent", "first_line_indent_pt")
        ),
        "left_indent_pt": _points(inherited("left_indent", "left_indent_pt")),
        "right_indent_pt": _points(inherited("right_indent", "right_indent_pt")),
        "space_before_pt": _points(inherited("space_before", "space_before_pt")),
        "space_after_pt": _points(inherited("space_after", "space_after_pt")),
        "space_before_lines": _paragraph_line_spacing_value(paragraph, "beforeLines"),
        "space_after_lines": _paragraph_line_spacing_value(paragraph, "afterLines"),
        "line_spacing": _points(line_spacing),
        "line_spacing_mode": line_spacing_mode,
        "keep_with_next": inherited("keep_with_next", "keep_with_next"),
        "keep_together": inherited("keep_together", "keep_together"),
        "page_break_before": inherited("page_break_before", "page_break_before"),
    }
    return EffectiveFormat(
        paragraph=paragraph_values,
        character=_uniform_run_format(paragraph, context),
    )


def snapshot_sections(document: Any) -> list[SectionFormatSnapshot]:
    snapshots = []
    for index, section in enumerate(document.sections):
        snapshots.append(
            SectionFormatSnapshot(
                section_index=index,
                width_mm=_round_number(section.page_width.mm),
                height_mm=_round_number(section.page_height.mm),
                orientation=(
                    "landscape" if section.orientation == WD_ORIENT.LANDSCAPE else "portrait"
                ),
                margin_top_mm=_round_number(section.top_margin.mm),
                margin_bottom_mm=_round_number(section.bottom_margin.mm),
                margin_left_mm=_round_number(section.left_margin.mm),
                margin_right_mm=_round_number(section.right_margin.mm),
                header_distance_mm=_round_number(section.header_distance.mm),
                footer_distance_mm=_round_number(section.footer_distance.mm),
            )
        )
    return snapshots
