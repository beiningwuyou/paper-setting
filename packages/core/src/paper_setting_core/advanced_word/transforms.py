from __future__ import annotations

import re
from copy import deepcopy
from typing import Any, cast

from docx.opc.constants import CONTENT_TYPE as CT
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.opc.packuri import PackURI
from docx.opc.part import Part
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from lxml import etree

from paper_setting_core.advanced_word.citations import normalize_numeric_citations
from paper_setting_core.advanced_word.cross_references import TARGET_MARKER
from paper_setting_core.documents.models import DocumentInspection

HEADING_PREFIXES = {
    "heading_1": re.compile(
        r"^\s*(?:第\s*[一二三四五六七八九十百0-9]+\s*章\s*|"
        r"[一二三四五六七八九十]+[、．.]\s*|\d+[.、]\s*)"
        r"|^\s*\d+\s+"
    ),
    "heading_2": re.compile(r"^\s*\d+\.\d+(?:[.、])?\s*"),
    "heading_3": re.compile(r"^\s*\d+\.\d+\.\d+(?:[.、])?\s*"),
    "reference_entry": re.compile(
        r"^\s*(?:\[\d+\]|【(?:文献)?\d+.*?】|\^\[\d+\]|\[Ref:?\s*\d+.*?\]|\*\d+\*|[（(]\d+[)）]|“参考文献[一二三四五六七八九十\d]+”[：:])\s*"
    ),
    "figure_caption": re.compile(
        r"^\s*图\s*[一二三四五六七八九十百0-9]+"
        r"(?:[-—.、][一二三四五六七八九十百0-9]+)*\s*"
    ),
    "table_caption": re.compile(
        r"^\s*表\s*[一二三四五六七八九十百0-9]+"
        r"(?:[-—.、][一二三四五六七八九十百0-9]+)*\s*"
    ),
}

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
INLINE_NOTE_MARKER = re.compile(
    r"(?:〔\s*(?P<round>\d+(?:\s*[,，、;；]\s*\d+)*)\s*〕|"
    r"[\[［【]\s*(?P<square>\d+(?:\s*[,，、;；]\s*\d+)*)\s*[\]］】])"
)
BIBLIOGRAPHY_HEADINGS = {"参考文献", "参 考 文 献", "References", "REFERENCES"}


def is_bibliography_heading_text(text: str) -> bool:
    s = text.strip()
    if s in BIBLIOGRAPHY_HEADINGS:
        return True
    clean = re.sub(r"\s+", "", s).lower().rstrip(":：")
    if clean in {"参考文献", "references", "bibliography"}:
        return True
    return bool(
        re.match(
            r"^(?:主要)?参考文献(?:[/／\-_(（](?:references?|bibliography)[)）]?)?$",
            clean,
            re.I,
        )
    )


def _xml_xpath(root: Any, expression: str) -> list[Any]:
    return cast(list[Any], etree.XPath(expression, namespaces={"w": W, "m": M})(root))


def _text_node_indexes(document: Any) -> dict[Any, int]:
    indexes: dict[Any, int] = {}
    visible_index = 0
    for node in document.element.iter():
        if node.tag == f"{{{W}}}t":
            indexes[node] = visible_index
            visible_index += 1
        elif node.tag in {f"{{{W}}}tab", f"{{{W}}}br", f"{{{W}}}cr"}:
            visible_index += 1
    return indexes


def _record_text_change(
    changes: list[dict[str, object]],
    indexes: dict[Any, int],
    node: Any,
    before: str,
    after: str,
) -> None:
    changes.append(
        {
            "story": "word/document.xml",
            "text_index": indexes[node],
            "before": before,
            "after": after,
        }
    )


def reformat_formulas(document: Any, values: dict[str, Any]) -> dict[str, Any]:
    settings = document.settings.element
    math_pr_nodes = settings.xpath("./m:mathPr")
    if math_pr_nodes:
        math_pr = math_pr_nodes[0]
    else:
        math_pr = OxmlElement("m:mathPr")
        settings.insert(0, math_pr)
    math_font = math_pr.find(qn("m:mathFont"))
    if math_font is None:
        math_font = OxmlElement("m:mathFont")
        math_pr.insert(0, math_font)
    math_font.set(qn("m:val"), values["math_font"])

    style_name = str(values.get("style", "preserve"))
    style_value = {
        "plain": "p",
        "italic": "i",
        "bold": "b",
        "bold_italic": "bi",
    }.get(style_name)
    math_runs = document.element.xpath(".//m:oMath//m:r")
    changed_styles = 0
    if style_value is not None:
        for math_run in math_runs:
            run_property = math_run.find(qn("m:rPr"))
            if run_property is None:
                run_property = OxmlElement("m:rPr")
                math_run.insert(0, run_property)
            style = run_property.find(qn("m:sty"))
            if style is None:
                style = OxmlElement("m:sty")
                run_property.append(style)
            if style.get(qn("m:val")) != style_value:
                style.set(qn("m:val"), style_value)
                changed_styles += 1
    return {
        "formula_count": len(math_runs),
        "math_font": values["math_font"],
        "styled_run_count": changed_styles,
    }


def normalize_citations(
    document: Any,
    inspection: DocumentInspection,
    paragraphs: list[Paragraph],
    values: dict[str, Any],
) -> dict[str, Any]:
    indexes = _text_node_indexes(document)
    changes: list[dict[str, object]] = []
    body_items = [item for item in inspection.items if item.story in {"body", "table"}]
    for item, paragraph in zip(body_items, paragraphs, strict=False):
        if item.semantic_role == "reference_entry" or item.risks.protected:
            continue
        for node in paragraph._p.xpath(".//w:t"):
            before = str(node.text or "")
            after = normalize_numeric_citations(
                before,
                sort_numbers=values.get("sort_numbers", True),
                collapse_ranges=values.get("collapse_ranges", True),
                range_separator=values.get("range_separator", "–"),
            )
            if before != after:
                node.text = after
                _record_text_change(changes, indexes, node, before, after)
    return {"changed_text_nodes": len(changes), "text_changes": changes}


def _package_part(document: Any, name: str) -> Any | None:
    return next(
        (part for part in document.part.package.parts if str(part.partname) == name),
        None,
    )


def _visible_values(root: Any) -> list[str]:
    values: list[str] = []
    for node in root.iter():
        if node.tag == qn("w:t"):
            values.append(str(node.text or ""))
        elif node.tag == qn("w:tab"):
            values.append("\t")
        elif node.tag in {qn("w:br"), qn("w:cr")}:
            values.append("\n")
    return values


def _new_footnotes_root() -> Any:
    root = OxmlElement("w:footnotes")
    for note_id, note_type, marker in (
        (0, "separator", "w:separator"),
        (1, "continuationSeparator", "w:continuationSeparator"),
    ):
        note = OxmlElement("w:footnote")
        note.set(qn("w:id"), str(note_id))
        note.set(qn("w:type"), note_type)
        paragraph = OxmlElement("w:p")
        run = OxmlElement("w:r")
        run.append(OxmlElement(marker))
        paragraph.append(run)
        note.append(paragraph)
        root.append(note)
    return root


def _footnotes_part(document: Any) -> tuple[Any, Any, bool]:
    part = _package_part(document, "/word/footnotes.xml")
    if part is not None:
        return part, parse_xml(part.blob), False
    root = _new_footnotes_root()
    part = Part(
        PackURI("/word/footnotes.xml"),
        CT.WML_FOOTNOTES,
        etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True),
        document.part.package,
    )
    document.part.relate_to(part, RT.FOOTNOTES)
    return part, root, True


def _next_note_id(footnotes: Any) -> int:
    ids = [
        int(note.get(qn("w:id"), "-1"))
        for note in _xml_xpath(footnotes, "./w:footnote[not(@w:type)]")
    ]
    return max(ids, default=1) + 1


def _append_footnote(footnotes: Any, note_id: int, text: str) -> None:
    note = OxmlElement("w:footnote")
    note.set(qn("w:id"), str(note_id))
    paragraph = OxmlElement("w:p")
    paragraph_properties = OxmlElement("w:pPr")
    paragraph_style = OxmlElement("w:pStyle")
    paragraph_style.set(qn("w:val"), "FootnoteText")
    paragraph_properties.append(paragraph_style)
    justification = OxmlElement("w:jc")
    justification.set(qn("w:val"), "left")
    paragraph_properties.append(justification)
    word_wrap = OxmlElement("w:wordWrap")
    word_wrap.set(qn("w:val"), "off")
    paragraph_properties.append(word_wrap)
    paragraph.append(paragraph_properties)

    reference_run = OxmlElement("w:r")
    reference_properties = OxmlElement("w:rPr")
    reference_style = OxmlElement("w:rStyle")
    reference_style.set(qn("w:val"), "FootnoteReference")
    reference_properties.append(reference_style)
    reference_run.append(reference_properties)
    reference_run.append(OxmlElement("w:footnoteRef"))
    paragraph.append(reference_run)

    text_run = OxmlElement("w:r")
    text_node = OxmlElement("w:t")
    text_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    text_node.text = f" {text.strip()}"
    text_run.append(text_node)
    paragraph.append(text_run)
    note.append(paragraph)
    footnotes.append(note)


def _set_footnote_numbering(document: Any, values: dict[str, Any]) -> int:
    restart_value = {
        "continuous": "continuous",
        "each_section": "eachSect",
        "each_page": "eachPage",
    }[str(values.get("numbering_restart", "continuous"))]
    format_value = {
        "decimal": "decimal",
        "decimal_enclosed_circle": "decimalEnclosedCircle",
    }[str(values.get("number_format", "decimal"))]
    sections = document.element.xpath(".//w:sectPr")
    for section in sections:
        properties = section.find(qn("w:footnotePr"))
        if properties is None:
            properties = OxmlElement("w:footnotePr")
            insertion_index = 0
            for child in section:
                if child.tag not in {qn("w:headerReference"), qn("w:footerReference")}:
                    break
                insertion_index += 1
            section.insert(insertion_index, properties)

        numbering_format = properties.find(qn("w:numFmt"))
        if numbering_format is None:
            numbering_format = OxmlElement("w:numFmt")
            properties.append(numbering_format)
        numbering_format.set(qn("w:val"), format_value)

        numbering_start = properties.find(qn("w:numStart"))
        if numbering_start is None:
            numbering_start = OxmlElement("w:numStart")
            properties.append(numbering_start)
        numbering_start.set(qn("w:val"), "1")

        numbering_restart = properties.find(qn("w:numRestart"))
        if numbering_restart is None:
            numbering_restart = OxmlElement("w:numRestart")
            properties.append(numbering_restart)
        numbering_restart.set(qn("w:val"), restart_value)
    return len(sections)


def _text_run(template_run: Any, text: str) -> Any:
    run = OxmlElement("w:r")
    properties = template_run.find(qn("w:rPr"))
    if properties is not None:
        run.append(deepcopy(properties))
    node = OxmlElement("w:t")
    if text[:1].isspace() or text[-1:].isspace():
        node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    node.text = text
    run.append(node)
    return run


def _footnote_reference_run(template_run: Any, note_id: int) -> Any:
    run = OxmlElement("w:r")
    current_properties = template_run.find(qn("w:rPr"))
    properties = (
        deepcopy(current_properties)
        if current_properties is not None
        else OxmlElement("w:rPr")
    )
    style = properties.find(qn("w:rStyle"))
    if style is None:
        style = OxmlElement("w:rStyle")
        properties.insert(0, style)
    style.set(qn("w:val"), "FootnoteReference")
    vertical = properties.find(qn("w:vertAlign"))
    if vertical is None:
        vertical = OxmlElement("w:vertAlign")
        properties.append(vertical)
    vertical.set(qn("w:val"), "superscript")
    run.append(properties)
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), str(note_id))
    run.append(reference)
    return run


def _bibliography(document: Any) -> tuple[Any | None, list[str], dict[int, str]]:
    paragraphs = list(document.paragraphs)
    heading_index = next(
        (
            index
            for index in range(len(paragraphs) - 1, -1, -1)
            if is_bibliography_heading_text(paragraphs[index].text)
        ),
        None,
    )
    if heading_index is None:
        return None, [], {}
    entries = [
        paragraph.text.strip()
        for paragraph in paragraphs[heading_index + 1 :]
        if paragraph.text.strip()
    ]
    indexed: dict[int, str] = {}
    for fallback, entry in enumerate(entries, start=1):
        explicit = re.match(
            r"^\s*(?:[\[［【〔^]|\*\s*|[（(]|“参考文献[一二三四五六七八九十\d]+”[：:])?\s*(?:文献|Ref:\s*)?(\d+)(?:[\]］】〕*]|[.、:：]|[)）]|\s+)\s*",
            entry,
        )
        number = int(explicit.group(1)) if explicit else fallback
        indexed[number] = entry[explicit.end() :] if explicit else entry
    return paragraphs[heading_index]._p, entries, indexed


def _inline_note_nodes(document: Any, bibliography_heading: Any | None) -> list[Any]:
    nodes: list[Any] = []
    for child in document.element.body.iterchildren():
        if bibliography_heading is not None and child is bibliography_heading:
            break
        nodes.extend(child.xpath(".//w:t"))
    return [node for node in nodes if INLINE_NOTE_MARKER.search(str(node.text or ""))]


def _note_text(numbers: list[int], references: dict[int, str]) -> str:
    return "；".join(references[number].rstrip("；; ") for number in numbers)


def _citation_field_span(node: Any) -> tuple[Any, list[Any]] | None:
    run = node.getparent()
    paragraph = run.getparent() if run is not None else None
    if run is None or paragraph is None or run.tag != qn("w:r") or paragraph.tag != qn("w:p"):
        return None
    children = list(paragraph)
    run_index = children.index(run)
    begin_index: int | None = None
    separate_seen = False
    for index in range(run_index - 1, -1, -1):
        field_chars = children[index].xpath(".//w:fldChar")
        field_types = {field.get(qn("w:fldCharType")) for field in field_chars}
        if "end" in field_types:
            break
        if "separate" in field_types:
            separate_seen = True
        if "begin" in field_types:
            begin_index = index
            break
    if begin_index is None or not separate_seen:
        return None
    end_index = next(
        (
            index
            for index in range(run_index + 1, len(children))
            if any(
                field.get(qn("w:fldCharType")) == "end"
                for field in children[index].xpath(".//w:fldChar")
            )
        ),
        None,
    )
    if end_index is None:
        return None
    instructions = "".join(
        str(instruction.text or "")
        for child in children[begin_index : end_index + 1]
        for instruction in child.xpath(".//w:instrText")
    ).strip()
    if not re.match(r"^(?:REF|ADDIN\s+(?:ZOTERO_ITEM|CSL_CITATION))\b", instructions, re.I):
        return None
    return paragraph, children[begin_index : end_index + 1]


def _field_values(root: Any | None) -> list[str]:
    if root is None:
        return []
    nodes = _xml_xpath(root, ".//w:instrText")
    return [str(node.text or "") for node in nodes]


def _protected_counts(roots: list[Any | None]) -> dict[str, int]:
    expressions = {
        "formula": ".//m:oMath | .//m:oMathPara",
        "revision_insert": ".//w:ins",
        "revision_delete": ".//w:del",
        "field": ".//w:fldChar | .//w:fldSimple",
        "text_box": ".//w:txbxContent",
        "embedded_object": ".//w:object",
        "footnote_reference": ".//w:footnoteReference",
        "endnote_reference": ".//w:endnoteReference",
        "comment_reference": ".//w:commentReference",
    }
    return {
        name: sum(
            len(_xml_xpath(root, expression))
            for root in roots
            if root is not None
        )
        for name, expression in expressions.items()
    }


def convert_notes_to_footnotes(document: Any, values: dict[str, Any]) -> dict[str, Any]:
    document_before = _visible_values(document.element)
    footnote_part_before = _package_part(document, "/word/footnotes.xml")
    endnote_part = _package_part(document, "/word/endnotes.xml")
    footnotes_before = (
        _visible_values(parse_xml(footnote_part_before.blob))
        if footnote_part_before is not None
        else None
    )
    endnotes_root = parse_xml(endnote_part.blob) if endnote_part is not None else None
    endnotes_before = _visible_values(endnotes_root) if endnotes_root is not None else None
    footnotes_root_before = (
        parse_xml(footnote_part_before.blob) if footnote_part_before is not None else None
    )
    protected_before = _protected_counts(
        [document.element, footnotes_root_before, endnotes_root]
    )
    fields_before = {
        "word/document.xml": _field_values(document.element),
        "word/footnotes.xml": _field_values(footnotes_root_before),
        "word/endnotes.xml": _field_values(endnotes_root),
    }

    heading, bibliography_entries, references = _bibliography(document)
    inline_nodes = (
        _inline_note_nodes(document, heading)
        if values.get("convert_inline_citations", True)
        else []
    )
    inline_matches = []
    for node in inline_nodes:
        matches = list(INLINE_NOTE_MARKER.finditer(str(node.text or "")))
        inline_matches.append((node, matches, _citation_field_span(node)))
    unresolved: set[int] = set()
    for node, matches, field_span in inline_matches:
        run = node.getparent()
        if field_span is not None and (
            len(matches) != 1 or str(node.text or "").strip() != matches[0].group(0)
        ):
            raise ValueError("citation field result contains unsupported surrounding text")
        if (
            field_span is None
            and (run is None or run.tag != qn("w:r") or len(run.xpath("./w:t")) != 1)
        ):
            raise ValueError("inline citation is inside a complex run")
        for match in matches:
            raw_numbers = match.group("round") or match.group("square") or ""
            numbers = [int(value) for value in re.split(r"\s*[,，、;；]\s*", raw_numbers)]
            unresolved.update(number for number in numbers if number not in references)
    if inline_matches and not bibliography_entries:
        raise ValueError("inline citations have no final bibliography")
    if unresolved:
        joined = ", ".join(str(number) for number in sorted(unresolved))
        raise ValueError(f"bibliography entries are missing for citations: {joined}")

    endnote_references = (
        document.element.xpath(".//w:endnoteReference")
        if values.get("convert_endnotes", True)
        else []
    )
    endnote_texts: dict[int, str] = {}
    if endnotes_root is not None:
        for note in _xml_xpath(endnotes_root, "./w:endnote[not(@w:type)]"):
            note_id = int(note.get(qn("w:id"), "-1"))
            endnote_texts[note_id] = "".join(
                str(node.text or "") for node in _xml_xpath(note, ".//w:t")
            ).strip()
    missing_endnotes = {
        int(node.get(qn("w:id"), "-1"))
        for node in endnote_references
        if int(node.get(qn("w:id"), "-1")) not in endnote_texts
    }
    if missing_endnotes:
        raise ValueError("endnote references point to missing endnotes")

    numbered_sections = _set_footnote_numbering(document, values)
    footnote_part, footnotes, created_part = _footnotes_part(document)
    next_id = _next_note_id(footnotes)
    converted_inline = 0
    for node, matches, field_span in inline_matches:
        run = node.getparent()
        assert run is not None
        source_text = str(node.text or "")
        if field_span is not None:
            match = matches[0]
            raw_numbers = match.group("round") or match.group("square") or ""
            numbers = [int(value) for value in re.split(r"\s*[,，、;；]\s*", raw_numbers)]
            _append_footnote(footnotes, next_id, _note_text(numbers, references))
            reference_run = _footnote_reference_run(run, next_id)
            parent, members = field_span
            position = parent.index(members[0])
            for member in members:
                parent.remove(member)
            parent.insert(position, reference_run)
            next_id += 1
            converted_inline += 1
            continue
        replacement_runs: list[Any] = []
        cursor = 0
        for match in matches:
            if match.start() > cursor:
                replacement_runs.append(_text_run(run, source_text[cursor : match.start()]))
            raw_numbers = match.group("round") or match.group("square") or ""
            numbers = [int(value) for value in re.split(r"\s*[,，、;；]\s*", raw_numbers)]
            _append_footnote(footnotes, next_id, _note_text(numbers, references))
            replacement_runs.append(_footnote_reference_run(run, next_id))
            next_id += 1
            converted_inline += 1
            cursor = match.end()
        if cursor < len(source_text):
            replacement_runs.append(_text_run(run, source_text[cursor:]))
        parent = run.getparent()
        assert parent is not None
        position = parent.index(run)
        parent.remove(run)
        for offset, replacement in enumerate(replacement_runs):
            parent.insert(position + offset, replacement)

    converted_endnotes = 0
    endnote_id_map: dict[int, int] = {}
    for reference in endnote_references:
        old_id = int(reference.get(qn("w:id"), "-1"))
        new_id = endnote_id_map.get(old_id)
        if new_id is None:
            new_id = next_id
            next_id += 1
            endnote_id_map[old_id] = new_id
            _append_footnote(footnotes, new_id, endnote_texts[old_id])
            converted_endnotes += 1
        reference.tag = qn("w:footnoteReference")
        reference.set(qn("w:id"), str(new_id))
    if endnotes_root is not None and endnote_id_map:
        for note in _xml_xpath(endnotes_root, "./w:endnote[not(@w:type)]"):
            endnotes_root.remove(note)

    removed_bibliography = 0
    if values.get("delete_bibliography", False) and heading is not None:
        body = document.element.body
        start = body.index(heading)
        for child in list(body)[start:]:
            if child.tag == qn("w:sectPr"):
                continue
            body.remove(child)
        removed_bibliography = len(bibliography_entries)

    footnote_part._blob = etree.tostring(
        footnotes, xml_declaration=True, encoding="UTF-8", standalone=True
    )
    if endnote_part is not None and endnotes_root is not None:
        endnote_part._blob = etree.tostring(
            endnotes_root, xml_declaration=True, encoding="UTF-8", standalone=True
        )

    protected_after = _protected_counts([document.element, footnotes, endnotes_root])
    protected_deltas = {
        name: protected_after[name] - count
        for name, count in protected_before.items()
        if protected_after[name] != count
    }

    replacements = [
        {
            "story": "word/document.xml",
            "before": document_before,
            "after": _visible_values(document.element),
        },
        {
            "story": "word/footnotes.xml",
            "before": footnotes_before,
            "after": _visible_values(footnotes),
        },
    ]
    if endnotes_root is not None:
        replacements.append(
            {
                "story": "word/endnotes.xml",
                "before": endnotes_before,
                "after": _visible_values(endnotes_root),
            }
        )
    fields_after = {
        "word/document.xml": _field_values(document.element),
        "word/footnotes.xml": _field_values(footnotes),
        "word/endnotes.xml": _field_values(endnotes_root),
    }
    return {
        "converted_inline_citations": converted_inline,
        "converted_endnotes": converted_endnotes,
        "removed_bibliography_entries": removed_bibliography,
        "numbered_sections": numbered_sections,
        "numbering_restart": values.get("numbering_restart", "continuous"),
        "number_format": values.get("number_format", "decimal"),
        "story_replacements": replacements,
        "field_replacements": [
            {
                "story": story,
                "before": (
                    fields_before[story]
                    if story != "word/footnotes.xml" or footnote_part_before
                    else None
                ),
                "after": fields_after[story],
            }
            for story in fields_after
            if story != "word/endnotes.xml" or endnotes_root is not None
        ],
        "added_parts": ["word/footnotes.xml"] if created_part else [],
        "protected_count_deltas": protected_deltas,
    }


def _set_outline_level(paragraph: Paragraph, level: int) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    outline = paragraph_properties.find(qn("w:outlineLvl"))
    if outline is None:
        outline = OxmlElement("w:outlineLvl")
        paragraph_properties.append(outline)
    outline.set(qn("w:val"), str(level))


def _field_instructions(document: Any) -> list[str]:
    return [str(node.text or "") for node in document.element.xpath(".//w:instrText")]


def _field_count(document: Any) -> int:
    return len(document.element.xpath(".//w:fldChar | .//w:fldSimple"))


def _new_toc_paragraph(instruction: str) -> Any:
    paragraph = OxmlElement("w:p")
    begin_run = OxmlElement("w:r")
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    begin_run.append(begin)
    instruction_run = OxmlElement("w:r")
    instruction_node = OxmlElement("w:instrText")
    instruction_node.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    instruction_node.text = instruction
    instruction_run.append(instruction_node)
    separator_run = OxmlElement("w:r")
    separator = OxmlElement("w:fldChar")
    separator.set(qn("w:fldCharType"), "separate")
    separator_run.append(separator)
    end_run = OxmlElement("w:r")
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run.append(end)
    paragraph.extend([begin_run, instruction_run, separator_run, end_run])
    return paragraph


def rebuild_toc(
    document: Any,
    inspection: DocumentInspection,
    paragraphs: list[Paragraph],
    values: dict[str, Any],
) -> dict[str, Any]:
    before_instructions = _field_instructions(document)
    before_field_count = _field_count(document)
    switches = [f'\\o "{values["min_level"]}-{values["max_level"]}"']
    if values.get("hyperlinks", True):
        switches.append("\\h")
    switches.extend(["\\z", "\\u"])
    instruction = " TOC " + " ".join(switches) + " "
    toc_nodes = [
        node
        for node in document.element.xpath(".//w:instrText")
        if "TOC" in str(node.text or "").upper()
    ]
    if toc_nodes:
        for node in toc_nodes:
            node.text = instruction
            parent = node.getparent()
            if parent is not None:
                begin_nodes = parent.getparent().xpath(".//w:fldChar[@w:fldCharType='begin']")
                for begin in begin_nodes:
                    begin.set(qn("w:dirty"), "true")
        created = False
    else:
        toc_paragraph = _new_toc_paragraph(instruction)
        body_items = [item for item in inspection.items if item.story in {"body", "table"}]
        anchor = next(
            (
                paragraph
                for item, paragraph in zip(body_items, paragraphs, strict=False)
                if item.text_preview.strip() in {"目录", "Contents", "CONTENTS"}
            ),
            None,
        )
        if anchor is not None:
            anchor._p.addnext(toc_paragraph)
        else:
            first_heading = next(
                (
                    paragraph
                    for item, paragraph in zip(body_items, paragraphs, strict=False)
                    if item.semantic_role == "heading_1"
                ),
                None,
            )
            if first_heading is not None:
                first_heading._p.addprevious(toc_paragraph)
            else:
                document.element.body.insert(0, toc_paragraph)
        created = True

    if values.get("update_on_open", True):
        settings = document.settings.element
        update_nodes = settings.xpath("./w:updateFields")
        update = update_nodes[0] if update_nodes else OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        if not update_nodes:
            settings.append(update)

    body_items = [item for item in inspection.items if item.story in {"body", "table"}]
    for item, paragraph in zip(body_items, paragraphs, strict=False):
        if item.semantic_role in {"heading_1", "heading_2", "heading_3"}:
            _set_outline_level(paragraph, int(item.semantic_role[-1]) - 1)

    return {
        "created": created,
        "field_count_delta": _field_count(document) - before_field_count,
        "field_instructions_before": before_instructions,
        "field_instructions_after": _field_instructions(document),
    }


def _next_integer(nodes: list[Any], attribute: str) -> int:
    values = [int(node.get(qn(attribute), "0")) for node in nodes]
    return max(values, default=0) + 1


def _append_level(abstract: Any, level: int, level_text: str) -> None:
    level_node = OxmlElement("w:lvl")
    level_node.set(qn("w:ilvl"), str(level))
    start = OxmlElement("w:start")
    start.set(qn("w:val"), "1")
    number_format = OxmlElement("w:numFmt")
    number_format.set(qn("w:val"), "decimal")
    text = OxmlElement("w:lvlText")
    text.set(qn("w:val"), level_text)
    justification = OxmlElement("w:lvlJc")
    justification.set(qn("w:val"), "left")
    level_node.extend([start, number_format, text, justification])
    abstract.append(level_node)


def _create_numbering_definition(numbering: Any, level_texts: list[str]) -> tuple[int, int]:
    abstract_id = _next_integer(numbering.xpath("./w:abstractNum"), "w:abstractNumId")
    abstract = OxmlElement("w:abstractNum")
    abstract.set(qn("w:abstractNumId"), str(abstract_id))
    multi_level = OxmlElement("w:multiLevelType")
    multi_level.set(qn("w:val"), "multilevel" if len(level_texts) > 1 else "singleLevel")
    abstract.append(multi_level)
    for level, level_text in enumerate(level_texts):
        _append_level(abstract, level, level_text)
    numbering.append(abstract)

    number_id = _next_integer(numbering.xpath("./w:num"), "w:numId")
    number = OxmlElement("w:num")
    number.set(qn("w:numId"), str(number_id))
    abstract_reference = OxmlElement("w:abstractNumId")
    abstract_reference.set(qn("w:val"), str(abstract_id))
    number.append(abstract_reference)
    numbering.append(number)
    return abstract_id, number_id


def _bind_numbering(paragraph: Paragraph, number_id: int, level: int) -> None:
    paragraph_properties = paragraph._p.get_or_add_pPr()
    current = paragraph_properties.find(qn("w:numPr"))
    if current is not None:
        paragraph_properties.remove(current)
    number_properties = OxmlElement("w:numPr")
    indentation_level = OxmlElement("w:ilvl")
    indentation_level.set(qn("w:val"), str(level))
    number_reference = OxmlElement("w:numId")
    number_reference.set(qn("w:val"), str(number_id))
    number_properties.extend([indentation_level, number_reference])
    paragraph_properties.insert(0, number_properties)


def _strip_prefix(
    document: Any,
    paragraph: Paragraph,
    role: str,
    changes: list[dict[str, object]],
    indexes: dict[Any, int],
) -> None:
    pattern = HEADING_PREFIXES.get(role)
    if pattern is None:
        return
    for node in paragraph._p.xpath(".//w:t"):
        before = str(node.text or "")
        after = pattern.sub("", before, count=1)
        if before != after:
            node.text = after
            _record_text_change(changes, indexes, node, before, after)
        if before.strip():
            return


def apply_automatic_numbering(
    document: Any,
    inspection: DocumentInspection,
    paragraphs: list[Paragraph],
    values: dict[str, Any],
) -> dict[str, Any]:
    numbering = document.part.numbering_part.element
    heading_ids: tuple[int, int] | None = None
    bibliography_ids: tuple[int, int] | None = None
    figure_ids: tuple[int, int] | None = None
    table_ids: tuple[int, int] | None = None
    if values.get("headings", True):
        heading_ids = _create_numbering_definition(numbering, ["%1", "%1.%2", "%1.%2.%3"])
    if values.get("bibliography", True):
        bibliography_ids = _create_numbering_definition(numbering, ["[%1]"])
    if values.get("captions", True):
        figure_ids = _create_numbering_definition(numbering, ["图 %1"])
        table_ids = _create_numbering_definition(numbering, ["表 %1"])

    indexes = _text_node_indexes(document)
    text_changes: list[dict[str, object]] = []
    bound_counts: dict[str, int] = {}
    excluded_cross_reference_targets: dict[str, int] = {}
    body_items = [item for item in inspection.items if item.story in {"body", "table"}]
    for item, paragraph in zip(body_items, paragraphs, strict=False):
        role = item.semantic_role
        paragraph_text = "".join(
            str(node.text or "") for node in paragraph._p.xpath(".//w:t")
        )
        instruction = " ".join(
            str(node.text or "") for node in paragraph._p.xpath(".//w:instrText")
        )
        cross_reference_managed = (
            role in {"figure_caption", "table_caption"}
            and (
                bool(re.search(r"\bSEQ\s+(?:Figure|Table)\b", instruction, re.I))
                or (
                    values.get("exclude_cross_reference_targets", False)
                    and TARGET_MARKER.search(paragraph_text) is not None
                )
            )
        )
        if cross_reference_managed:
            excluded_cross_reference_targets[role] = (
                excluded_cross_reference_targets.get(role, 0) + 1
            )
            continue
        if heading_ids is not None and role in {"heading_1", "heading_2", "heading_3"}:
            level = int(role[-1]) - 1
            _bind_numbering(paragraph, heading_ids[1], level)
            _set_outline_level(paragraph, level)
        elif bibliography_ids is not None and role == "reference_entry":
            _bind_numbering(paragraph, bibliography_ids[1], 0)
        elif figure_ids is not None and role == "figure_caption":
            _bind_numbering(paragraph, figure_ids[1], 0)
        elif table_ids is not None and role == "table_caption":
            _bind_numbering(paragraph, table_ids[1], 0)
        else:
            continue
        if values.get("strip_existing_prefix", True):
            _strip_prefix(document, paragraph, role, text_changes, indexes)
        bound_counts[role] = bound_counts.get(role, 0) + 1

    return {
        "heading_abstract_num_id": heading_ids[0] if heading_ids else None,
        "heading_num_id": heading_ids[1] if heading_ids else None,
        "bibliography_abstract_num_id": bibliography_ids[0] if bibliography_ids else None,
        "bibliography_num_id": bibliography_ids[1] if bibliography_ids else None,
        "figure_abstract_num_id": figure_ids[0] if figure_ids else None,
        "figure_num_id": figure_ids[1] if figure_ids else None,
        "table_abstract_num_id": table_ids[0] if table_ids else None,
        "table_num_id": table_ids[1] if table_ids else None,
        "bound_counts": bound_counts,
        "excluded_cross_reference_targets": excluded_cross_reference_targets,
        "changed_text_nodes": len(text_changes),
        "text_changes": text_changes,
    }
