from __future__ import annotations

import re
from collections import Counter
from typing import TYPE_CHECKING, Any, cast

from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

from paper_setting_core.advanced_word.citations import citation_needs_normalization
from paper_setting_core.advanced_word.cross_references import analyze_cross_references

INLINE_NOTE_MARKER = re.compile(
    r"(?:〔\s*\d+(?:\s*[,，、;；]\s*\d+)*\s*〕|"
    r"[\[［【]\s*\d+(?:\s*[,，、;；]\s*\d+)*\s*[\]］】])"
)


def _note_part_root(document: Any, part_name: str) -> etree._Element | None:
    part = next(
        (part for part in document.part.package.parts if str(part.partname) == part_name),
        None,
    )
    if part is None:
        return None
    return etree.fromstring(part.blob)


def _real_note_count(root: etree._Element | None, element_name: str) -> int:
    if root is None:
        return 0
    return len(
        cast(
            list[Any],
            root.xpath(
                f"./w:{element_name}[not(@w:type)]",
                namespaces={
                    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
                },
            ),
        )
    )


def _footnote_numbering(document: Any) -> tuple[list[str], list[str]]:
    restart_values = {
        "continuous": "continuous",
        "eachSect": "each_section",
        "eachPage": "each_page",
    }
    format_values = {
        "decimal": "decimal",
        "decimalEnclosedCircle": "decimal_enclosed_circle",
    }
    settings = document.settings.element
    default_restart_nodes = settings.xpath("./w:footnotePr/w:numRestart")
    default_format_nodes = settings.xpath("./w:footnotePr/w:numFmt")
    default_restart_raw = (
        str(default_restart_nodes[0].get(qn("w:val")))
        if default_restart_nodes
        else "continuous"
    )
    default_format_raw = (
        str(default_format_nodes[0].get(qn("w:val")))
        if default_format_nodes
        else "decimal"
    )
    default_restart = restart_values.get(default_restart_raw, default_restart_raw)
    default_format = format_values.get(default_format_raw, default_format_raw)
    restarts: list[str] = []
    formats: list[str] = []
    for section in document.element.xpath(".//w:sectPr"):
        restart_nodes = section.xpath("./w:footnotePr/w:numRestart")
        format_nodes = section.xpath("./w:footnotePr/w:numFmt")
        restart_raw = (
            str(restart_nodes[0].get(qn("w:val")))
            if restart_nodes
            else default_restart
        )
        format_raw = (
            str(format_nodes[0].get(qn("w:val"))) if format_nodes else default_format
        )
        restarts.append(restart_values.get(restart_raw, restart_raw))
        formats.append(format_values.get(format_raw, format_raw))
    return restarts, formats


if TYPE_CHECKING:
    from paper_setting_core.documents.models import AdvancedWordInspection, DocumentItem


def _on(value: str | None) -> bool:
    return value is None or value.casefold() not in {"0", "false", "off", "none"}


def snapshot_advanced_word(
    document: Any,
    items: list[DocumentItem],
    body_paragraphs: list[Paragraph],
) -> AdvancedWordInspection:
    from paper_setting_core.documents.models import AdvancedWordInspection

    settings = document.settings.element
    math_fonts = settings.xpath("./m:mathPr/m:mathFont")
    math_font = math_fonts[0].get(qn("m:val")) if math_fonts else None
    formula_count = len(document.element.xpath(".//m:oMath | .//m:oMathPara"))
    formula_styles = sorted(
        {
            str(node.get(qn("m:val")))
            for node in document.element.xpath(".//m:oMath//m:rPr/m:sty")
            if node.get(qn("m:val"))
        }
    )
    update_nodes = settings.xpath("./w:updateFields")
    update_on_open = bool(update_nodes and _on(update_nodes[0].get(qn("w:val"))))
    toc_instructions = [
        str(node.text or "").strip()
        for node in document.element.xpath(".//w:instrText")
        if "TOC" in str(node.text or "").upper()
    ]
    cross_reference_instructions = [
        str(node.text or "").strip()
        for node in document.element.xpath(".//w:instrText")
        if re.match(r"^(?:SEQ|REF|PAGEREF)\b", str(node.text or "").strip(), re.I)
    ]
    cross_references = analyze_cross_references(document, items, body_paragraphs)
    target_counts = Counter(target.kind for target in cross_references.targets.values())
    sequence_numbered: Counter[str] = Counter()
    for paragraph in body_paragraphs:
        instruction = " ".join(
            str(node.text or "") for node in paragraph._p.xpath(".//w:instrText")
        )
        if re.search(r"\bSEQ\s+Figure\b", instruction, re.I):
            sequence_numbered["figure_caption"] += 1
        if re.search(r"\bSEQ\s+Table\b", instruction, re.I):
            sequence_numbered["table_caption"] += 1

    citation_candidates = 0
    inline_note_candidates = 0
    numbered: Counter[str] = Counter()
    in_bibliography = False
    for item, paragraph in zip(items, body_paragraphs, strict=False):
        if paragraph._p.xpath("./w:pPr/w:numPr/w:numId"):
            numbered[item.semantic_role] += 1
        if paragraph.text.strip() in {
            "参考文献",
            "参 考 文 献",
            "References",
            "REFERENCES",
        }:
            in_bibliography = True
            continue
        if in_bibliography or item.semantic_role == "reference_entry":
            continue
        inline_note_candidates += sum(
            len(INLINE_NOTE_MARKER.findall(str(node.text or "")))
            for node in paragraph._p.xpath(".//w:t")
        )
        citation_candidates += sum(
            citation_needs_normalization(str(node.text or ""))
            for node in paragraph._p.xpath(".//w:t")
        )

    footnote_restarts, footnote_formats = _footnote_numbering(document)
    return AdvancedWordInspection(
        formula_count=formula_count,
        formula_math_font=str(math_font) if math_font else None,
        formula_styles=formula_styles,
        citation_candidate_count=citation_candidates,
        toc_instructions=toc_instructions,
        update_fields_on_open=update_on_open,
        numbered_role_counts=dict(numbered),
        cross_reference_target_count=len(cross_references.targets),
        cross_reference_marker_count=cross_references.reference_count,
        cross_reference_page_marker_count=cross_references.page_reference_count,
        cross_reference_existing_field_count=len(cross_reference_instructions),
        cross_reference_target_counts=dict(target_counts),
        sequence_numbered_role_counts=dict(sequence_numbered),
        cross_reference_issues=cross_references.issues,
        footnote_count=_real_note_count(
            _note_part_root(document, "/word/footnotes.xml"), "footnote"
        ),
        endnote_count=_real_note_count(
            _note_part_root(document, "/word/endnotes.xml"), "endnote"
        ),
        inline_note_candidate_count=inline_note_candidates,
        bibliography_entry_count=_bibliography_entry_count(body_paragraphs),
        footnote_numbering_restarts=footnote_restarts,
        footnote_number_formats=footnote_formats,
    )


def _bibliography_entry_count(paragraphs: list[Paragraph]) -> int:
    headings = {"参考文献", "参 考 文 献", "References", "REFERENCES"}
    heading_index = next(
        (
            index
            for index in range(len(paragraphs) - 1, -1, -1)
            if paragraphs[index].text.strip() in headings
        ),
        None,
    )
    if heading_index is None:
        return 0
    return sum(bool(paragraph.text.strip()) for paragraph in paragraphs[heading_index + 1 :])
