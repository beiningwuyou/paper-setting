from __future__ import annotations

import posixpath
import re
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, cast

from lxml import etree

from paper_setting_core.documents import inspect_document, sha256_file, validate_docx_package
from paper_setting_core.rulepacks.capabilities import list_capabilities
from paper_setting_core.rulepacks.models import CapabilityId
from paper_setting_core.templates.models import (
    ContentControlCandidate,
    HeaderFooterReference,
    PlaceholderCandidate,
    SemanticMappingCandidate,
    TemplateCapabilityFinding,
    TemplateInspection,
    TemplateSectionSummary,
    TemplateStyleSummary,
    TemplateSummary,
)

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
NS = {"w": W, "r": R, "pr": PR}
PLACEHOLDER = re.compile(
    r"(?P<token>\{\{\s*(?P<brace>[A-Za-z0-9_\u3400-\u9fff.-]+)\s*\}\}|"
    r"\[\[\s*(?P<bracket>[A-Za-z0-9_\u3400-\u9fff.-]+)\s*\]\]|"
    r"<<\s*(?P<angle>[A-Za-z0-9_\u3400-\u9fff.-]+)\s*>>)"
)
FIELD_KIND = re.compile(r"^\s*([A-Z]+)", re.I)


def _xpath(root: etree._Element, expression: str) -> list[Any]:
    return cast(list[Any], root.xpath(expression, namespaces=NS))


def _parse(payload: bytes) -> etree._Element:
    return etree.fromstring(payload)


def _story_parts(archive: zipfile.ZipFile) -> dict[str, etree._Element]:
    parts: dict[str, etree._Element] = {}
    for name in sorted(archive.namelist()):
        if name == "word/document.xml" or re.fullmatch(r"word/(?:header|footer)\d+\.xml", name):
            parts[name] = _parse(archive.read(name))
    return parts


def _paragraph_text(paragraph: etree._Element) -> str:
    values: list[str] = []
    for node in _xpath(paragraph, ".//w:t"):
        nearest_paragraph = next(
            (ancestor for ancestor in node.iterancestors() if ancestor.tag == f"{{{W}}}p"),
            None,
        )
        if nearest_paragraph is paragraph:
            values.append(str(node.text or ""))
    return "".join(values)


def _story_name(part_name: str, paragraph: etree._Element | None = None) -> str:
    if part_name.startswith("word/header"):
        return "header"
    if part_name.startswith("word/footer"):
        return "footer"
    if paragraph is not None and any(
        ancestor.tag == f"{{{W}}}txbxContent" for ancestor in paragraph.iterancestors()
    ):
        return "text_box"
    return "body"


def _style_summaries(
    archive: zipfile.ZipFile, parts: dict[str, etree._Element]
) -> list[TemplateStyleSummary]:
    if "word/styles.xml" not in archive.namelist():
        return []
    usage = Counter(
        str(node.get(f"{{{W}}}val"))
        for root in parts.values()
        for node in _xpath(root, ".//w:pPr/w:pStyle")
        if node.get(f"{{{W}}}val")
    )
    root = _parse(archive.read("word/styles.xml"))
    styles: list[TemplateStyleSummary] = []
    for node in _xpath(root, "./w:style"):
        style_id = str(node.get(f"{{{W}}}styleId") or "")
        if not style_id:
            continue
        names = _xpath(node, "./w:name")
        bases = _xpath(node, "./w:basedOn")
        styles.append(
            TemplateStyleSummary(
                style_id=style_id,
                name=str(names[0].get(f"{{{W}}}val")) if names else None,
                style_type=node.get(f"{{{W}}}type"),
                based_on=str(bases[0].get(f"{{{W}}}val")) if bases else None,
                usage_count=usage[style_id],
            )
        )
    return sorted(styles, key=lambda item: (-item.usage_count, item.style_id))


def _placeholders(parts: dict[str, etree._Element]) -> list[PlaceholderCandidate]:
    counts: Counter[tuple[str, str, str, str, bool]] = Counter()
    for part_name, root in parts.items():
        for paragraph in _xpath(root, ".//w:p"):
            text = _paragraph_text(paragraph)
            if not text:
                continue
            story = _story_name(part_name, paragraph)
            in_text_box = story == "text_box"
            for match in PLACEHOLDER.finditer(text):
                key = match.group("brace") or match.group("bracket") or match.group("angle")
                counts[(match.group("token"), key, story, part_name, in_text_box)] += 1
    return [
        PlaceholderCandidate(
            token=token,
            key=key,
            story=story,
            part_name=part_name,
            occurrences=occurrences,
            in_text_box=in_text_box,
        )
        for (token, key, story, part_name, in_text_box), occurrences in counts.items()
    ]


def _content_controls(parts: dict[str, etree._Element]) -> list[ContentControlCandidate]:
    controls: list[ContentControlCandidate] = []
    for part_name, root in parts.items():
        for node in _xpath(root, ".//w:sdt"):
            tags = _xpath(node, "./w:sdtPr/w:tag")
            aliases = _xpath(node, "./w:sdtPr/w:alias")
            controls.append(
                ContentControlCandidate(
                    tag=str(tags[0].get(f"{{{W}}}val")) if tags else None,
                    alias=str(aliases[0].get(f"{{{W}}}val")) if aliases else None,
                    part_name=part_name,
                    story=_story_name(part_name),
                )
            )
    return controls


def _relationship_targets(archive: zipfile.ZipFile) -> dict[str, str]:
    relationship_name = "word/_rels/document.xml.rels"
    if relationship_name not in archive.namelist():
        return {}
    root = _parse(archive.read(relationship_name))
    targets: dict[str, str] = {}
    for node in _xpath(root, "./pr:Relationship"):
        if node.get("TargetMode") == "External":
            continue
        relationship_id = str(node.get("Id") or "")
        target = str(node.get("Target") or "")
        normalized = posixpath.normpath(posixpath.join("word", target))
        if relationship_id and normalized.startswith("word/"):
            targets[relationship_id] = normalized
    return targets


def _section_summaries(
    archive: zipfile.ZipFile,
    document_root: etree._Element,
    pages: list[Any],
) -> list[TemplateSectionSummary]:
    targets = _relationship_targets(archive)
    summaries: list[TemplateSectionSummary] = []
    for section_index, section in enumerate(_xpath(document_root, ".//w:sectPr")):
        references: list[HeaderFooterReference] = []
        for story, tag in (("header", "headerReference"), ("footer", "footerReference")):
            for node in _xpath(section, f"./w:{tag}"):
                relationship_id = str(node.get(f"{{{R}}}id") or "")
                references.append(
                    HeaderFooterReference(
                        story=story,
                        kind=str(node.get(f"{{{W}}}type") or "default"),
                        relationship_id=relationship_id,
                        part_name=targets.get(relationship_id),
                    )
                )
        page_number_nodes = _xpath(section, "./w:pgNumType")
        page_number = page_number_nodes[0] if page_number_nodes else None
        start_value = page_number.get(f"{{{W}}}start") if page_number is not None else None
        summaries.append(
            TemplateSectionSummary(
                section_index=section_index,
                page=pages[section_index],
                page_number_format=(
                    str(page_number.get(f"{{{W}}}fmt")) if page_number is not None else None
                ),
                page_number_start=int(start_value) if start_value is not None else None,
                different_first_page=bool(_xpath(section, "./w:titlePg")),
                inherits_headers=section_index > 0
                and not any(item.story == "header" for item in references),
                inherits_footers=section_index > 0
                and not any(item.story == "footer" for item in references),
                references=references,
            )
        )
    return summaries


def _semantic_candidates(document_inspection: Any) -> list[SemanticMappingCandidate]:
    grouped: dict[tuple[str, str | None], list[Any]] = {}
    for item in document_inspection.items:
        if item.semantic_role == "empty" or item.confidence < 0.9:
            continue
        grouped.setdefault((item.semantic_role, item.style_id), []).append(item)
    candidates = [
        SemanticMappingCandidate(
            role=role,
            stable_id=max(items, key=lambda item: item.confidence).stable_id,
            story=max(items, key=lambda item: item.confidence).story,
            style_id=style_id,
            confidence=max(item.confidence for item in items),
            occurrences=len(items),
            text_preview=max(items, key=lambda item: item.confidence).text_preview[:160],
        )
        for (role, style_id), items in grouped.items()
    ]
    return sorted(candidates, key=lambda item: (item.role, -item.occurrences))


def _capability_findings(
    *,
    placeholders: int,
    content_controls: int,
    page_numbering: int,
    header_footer_references: int,
    cross_reference_fields: int,
) -> list[TemplateCapabilityFinding]:
    definitions = {item.id: item for item in list_capabilities()}
    evidence: dict[CapabilityId, int] = {
        "template.inspect": 1,
        "template.fill": 1,
    }
    detected: tuple[tuple[CapabilityId, int], ...] = (
        ("template.placeholders", placeholders),
        ("word.content_controls", content_controls),
        ("sections.page_numbering", page_numbering),
        ("sections.headers_footers", header_footer_references),
        ("word.cross_references", cross_reference_fields),
    )
    for capability, count in detected:
        if count:
            evidence[capability] = count
    return [
        TemplateCapabilityFinding(
            id=capability,
            label=definitions[capability].label,
            status=definitions[capability].status,
            evidence_count=count,
            detail=definitions[capability].detail,
        )
        for capability, count in evidence.items()
    ]


def inspect_template(
    path: Path,
    *,
    source_filename: str | None = None,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> TemplateInspection:
    validate_docx_package(
        path,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    document_inspection = inspect_document(path, source_filename=source_filename)
    with zipfile.ZipFile(path) as archive:
        parts = _story_parts(archive)
        document_root = parts["word/document.xml"]
        styles = _style_summaries(archive, parts)
        placeholders = _placeholders(parts)
        controls = _content_controls(parts)
        sections = _section_summaries(
            archive,
            document_root,
            document_inspection.sections,
        )
        field_instructions = sorted(
            {
                " ".join(str(node.text or "").split())
                for root in parts.values()
                for node in _xpath(root, ".//w:instrText")
                if str(node.text or "").strip()
            }
        )
        cross_reference_fields = sum(
            bool(
                (match := FIELD_KIND.match(instruction))
                and match.group(1).upper() in {"SEQ", "REF", "PAGEREF"}
            )
            for instruction in field_instructions
        )
        text_boxes = sum(len(_xpath(root, ".//w:txbxContent")) for root in parts.values())
        bookmarks = len(_xpath(document_root, ".//w:bookmarkStart"))
        header_parts = sum(name.startswith("word/header") for name in parts)
        footer_parts = sum(name.startswith("word/footer") for name in parts)
        settings_root = (
            _parse(archive.read("word/settings.xml"))
            if "word/settings.xml" in archive.namelist()
            else None
        )
        even_and_odd = bool(
            settings_root is not None and _xpath(settings_root, "./w:evenAndOddHeaders")
        )

    semantic_candidates = _semantic_candidates(document_inspection)
    page_numbering = sum(
        section.page_number_format is not None or section.page_number_start is not None
        for section in sections
    )
    header_footer_references = sum(len(section.references) for section in sections)
    capabilities = _capability_findings(
        placeholders=sum(item.occurrences for item in placeholders),
        content_controls=len(controls),
        page_numbering=page_numbering,
        header_footer_references=header_footer_references,
        cross_reference_fields=cross_reference_fields,
    )
    warnings: list[str] = []
    if not placeholders and not controls:
        warnings.append("未发现结构化占位符或内容控件；模板填充前需要人工确认字段锚点。")
    planned = [item.label for item in capabilities if item.status == "planned"]
    if planned:
        warnings.append("模板包含工作台尚未执行的能力：" + "、".join(planned))
    if document_inspection.summary.protected_items:
        warnings.append(
            f"模板包含 {document_inspection.summary.protected_items} 个受保护对象，"
            "后续填充必须保留其内部 OOXML。"
        )
    return TemplateInspection(
        source_filename=source_filename or path.name,
        source_sha256=sha256_file(path),
        summary=TemplateSummary(
            sections=len(sections),
            styles=len(styles),
            used_styles=sum(item.usage_count > 0 for item in styles),
            placeholders=sum(item.occurrences for item in placeholders),
            content_controls=len(controls),
            text_boxes=text_boxes,
            fields=len(field_instructions),
            bookmarks=bookmarks,
            header_parts=header_parts,
            footer_parts=footer_parts,
        ),
        sections=sections,
        styles=styles,
        placeholders=placeholders,
        content_controls=controls,
        semantic_candidates=semantic_candidates,
        field_instructions=field_instructions,
        capabilities=capabilities,
        even_and_odd_headers=even_and_odd,
        warnings=warnings,
    )
