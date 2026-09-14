from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Any, Literal

from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph

from paper_setting_core.errors import CrossReferenceInvalidError

if TYPE_CHECKING:
    from paper_setting_core.documents.models import DocumentInspection, DocumentItem

KEY_PATTERN = r"[a-z0-9][a-z0-9_.-]{0,63}"
TARGET_MARKER = re.compile(rf"\[\[xref-target:(?P<key>{KEY_PATTERN})\]\]")
REFERENCE_MARKER = re.compile(rf"\[\[xref:(?P<key>{KEY_PATTERN})\]\]")
PAGE_MARKER = re.compile(rf"\[\[xref-page:(?P<key>{KEY_PATTERN})\]\]")
XREF_CANDIDATE = re.compile(r"\[\[xref.*?(?:\]\]|$)", re.IGNORECASE)

TargetKind = Literal["figure", "table"]
MarkerKind = Literal["target", "reference", "page"]

CAPTION_PREFIXES: dict[TargetKind, re.Pattern[str]] = {
    "figure": re.compile(
        r"^\s*图\s*[一二三四五六七八九十百0-9]+"
        r"(?:[-—.、][一二三四五六七八九十百0-9]+)*\s*[：:、.]?\s*"
    ),
    "table": re.compile(
        r"^\s*表\s*[一二三四五六七八九十百0-9]+"
        r"(?:[-—.、][一二三四五六七八九十百0-9]+)*\s*[：:、.]?\s*"
    ),
}

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
XML = "http://www.w3.org/XML/1998/namespace"


@dataclass(frozen=True)
class CrossReferenceTarget:
    key: str
    kind: TargetKind
    paragraph_index: int
    ordinal: int
    bookmark_name: str


@dataclass(frozen=True)
class CrossReferenceMarker:
    key: str
    kind: MarkerKind
    paragraph_index: int
    start: int
    end: int


@dataclass(frozen=True)
class CrossReferenceAnalysis:
    targets: dict[str, CrossReferenceTarget]
    markers: list[CrossReferenceMarker]
    issues: list[str]

    @property
    def reference_count(self) -> int:
        return sum(marker.kind == "reference" for marker in self.markers)

    @property
    def page_reference_count(self) -> int:
        return sum(marker.kind == "page" for marker in self.markers)


def _target_kind(key: str) -> TargetKind | None:
    if key.startswith(("fig-", "figure-", "fig.", "figure.")):
        return "figure"
    if key.startswith(("tab-", "table-", "tab.", "table.")):
        return "table"
    return None


def _bookmark_name(key: str) -> str:
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:20]
    return f"_PSX_{digest}"


def _paragraph_text_nodes(paragraph: Paragraph) -> list[Any]:
    return [
        node
        for node in paragraph._p.xpath(".//w:t")
        if next(
            (ancestor for ancestor in node.iterancestors() if ancestor.tag == qn("w:p")),
            None,
        )
        is paragraph._p
    ]


def _paragraph_text(paragraph: Paragraph) -> str:
    return "".join(str(node.text or "") for node in _paragraph_text_nodes(paragraph))


def _run_is_plain_text(run: Any) -> bool:
    return all(child.tag in {qn("w:rPr"), qn("w:t")} for child in run)


def _marker_is_safely_replaceable(paragraph: Paragraph, start: int, end: int) -> bool:
    spans: list[tuple[int, int, Any]] = []
    cursor = 0
    for node in _paragraph_text_nodes(paragraph):
        length = len(str(node.text or ""))
        spans.append((cursor, cursor + length, node))
        cursor += length
    involved = [node for left, right, node in spans if left < end and right > start]
    if not involved:
        return False
    runs: list[Any] = []
    for node in involved:
        run = next(
            (ancestor for ancestor in node.iterancestors() if ancestor.tag == qn("w:r")),
            None,
        )
        if run is None or run.getparent() is not paragraph._p or not _run_is_plain_text(run):
            return False
        if run not in runs:
            runs.append(run)
    return True


def _markers_for_paragraph(
    paragraph: Paragraph,
    paragraph_index: int,
) -> list[CrossReferenceMarker]:
    text = _paragraph_text(paragraph)
    markers: list[CrossReferenceMarker] = []
    marker_patterns: tuple[tuple[MarkerKind, re.Pattern[str]], ...] = (
        ("target", TARGET_MARKER),
        ("reference", REFERENCE_MARKER),
        ("page", PAGE_MARKER),
    )
    for kind, pattern in marker_patterns:
        markers.extend(
            CrossReferenceMarker(
                key=match.group("key"),
                kind=kind,
                paragraph_index=paragraph_index,
                start=match.start(),
                end=match.end(),
            )
            for match in pattern.finditer(text)
        )
    return sorted(markers, key=lambda marker: marker.start)


def _target_marker_with_caption_prefix(
    paragraph: Paragraph,
    marker: CrossReferenceMarker,
    kind: TargetKind,
) -> CrossReferenceMarker:
    suffix = _paragraph_text(paragraph)[marker.end :]
    match = CAPTION_PREFIXES[kind].match(suffix)
    return replace(marker, end=marker.end + match.end()) if match else marker


def analyze_cross_references(
    document: Any,
    items: list[DocumentItem],
    paragraphs: list[Paragraph],
) -> CrossReferenceAnalysis:
    body_items = [item for item in items if item.story in {"body", "table"}]
    issues: list[str] = []
    markers: list[CrossReferenceMarker] = []
    target_locations: dict[str, tuple[TargetKind, int, int]] = {}
    counters: dict[TargetKind, int] = {"figure": 0, "table": 0}
    existing_bookmarks = {
        str(node.get(qn("w:name")) or "")
        for node in document.element.xpath(".//w:bookmarkStart")
    }

    for index, (item, paragraph) in enumerate(
        zip(body_items, paragraphs, strict=False)
    ):
        paragraph_markers = _markers_for_paragraph(paragraph, index)
        text = _paragraph_text(paragraph)
        valid_spans = {(marker.start, marker.end) for marker in paragraph_markers}
        malformed = [
            match.group(0)
            for match in XREF_CANDIDATE.finditer(text)
            if (match.start(), match.end()) not in valid_spans
        ]
        for value in malformed:
            issues.append(f"无法识别交叉引用标记：{value[:80]}")
        if not paragraph_markers:
            continue
        markers.extend(paragraph_markers)
        target_markers = [marker for marker in paragraph_markers if marker.kind == "target"]
        if len(target_markers) > 1:
            issues.append("每个题注段落只能包含一个交叉引用目标")
        if target_markers and len(paragraph_markers) > 1:
            issues.append("交叉引用目标段落不能同时包含其他引用标记")
        if item.risks.protected:
            issues.append(f"第 {item.order + 1} 个段落包含受保护对象，不能写入交叉引用字段")
        for marker in paragraph_markers:
            if not _marker_is_safely_replaceable(paragraph, marker.start, marker.end):
                issues.append(f"交叉引用标记 {marker.key} 跨越不可安全拆分的 Word 结构")
            if marker.kind != "target":
                continue
            kind = _target_kind(marker.key)
            if kind is None:
                issues.append(
                    f"目标 {marker.key} 必须使用 fig-/figure- 或 tab-/table- 前缀"
                )
                continue
            if text[: marker.start].strip():
                issues.append(f"目标 {marker.key} 必须位于题注段落开头")
            replacement_marker = _target_marker_with_caption_prefix(
                paragraph, marker, kind
            )
            if not _marker_is_safely_replaceable(
                paragraph, replacement_marker.start, replacement_marker.end
            ):
                issues.append(f"目标 {marker.key} 的已有题注编号不能安全移除")
            caption = text[replacement_marker.end :].strip(" \t：:、.—-")
            if not caption:
                issues.append(f"目标 {marker.key} 缺少题注文字")
            if marker.key in target_locations:
                issues.append(f"交叉引用目标 {marker.key} 重复")
                continue
            counters[kind] += 1
            target_locations[marker.key] = (kind, index, counters[kind])

    targets = {
        key: CrossReferenceTarget(
            key=key,
            kind=kind,
            paragraph_index=index,
            ordinal=ordinal,
            bookmark_name=_bookmark_name(key),
        )
        for key, (kind, index, ordinal) in target_locations.items()
    }
    for marker in markers:
        if marker.kind != "target" and marker.key not in targets:
            issues.append(f"交叉引用 {marker.key} 没有唯一目标")
    for target in targets.values():
        if target.bookmark_name in existing_bookmarks:
            issues.append(f"目标 {target.key} 的书签名已存在")

    return CrossReferenceAnalysis(
        targets=targets,
        markers=markers,
        issues=list(dict.fromkeys(issues)),
    )


def _set_text(run: Any, value: str) -> None:
    nodes = list(run.xpath("./w:t"))
    if not nodes:
        node = OxmlElement("w:t")
        run.append(node)
        nodes = [node]
    nodes[0].text = value
    for node in nodes[1:]:
        node.text = ""
    attribute = f"{{{XML}}}space"
    if value.startswith(" ") or value.endswith(" "):
        nodes[0].set(attribute, "preserve")
    elif attribute in nodes[0].attrib:
        del nodes[0].attrib[attribute]


def _new_run_like(template_run: Any, text: str | None = None) -> Any:
    run = OxmlElement("w:r")
    properties = template_run.find(qn("w:rPr"))
    if properties is not None:
        run.append(deepcopy(properties))
    if text is not None:
        node = OxmlElement("w:t")
        node.text = text
        if text.startswith(" ") or text.endswith(" "):
            node.set(f"{{{XML}}}space", "preserve")
        run.append(node)
    return run


def _field_runs(template_run: Any, instruction: str, visible: str) -> list[Any]:
    begin_run = _new_run_like(template_run)
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin.set(qn("w:dirty"), "true")
    begin_run.append(begin)

    instruction_run = _new_run_like(template_run)
    instruction_node = OxmlElement("w:instrText")
    instruction_node.set(f"{{{XML}}}space", "preserve")
    instruction_node.text = instruction
    instruction_run.append(instruction_node)

    separator_run = _new_run_like(template_run)
    separator = OxmlElement("w:fldChar")
    separator.set(qn("w:fldCharType"), "separate")
    separator_run.append(separator)

    result_run = _new_run_like(template_run, visible)

    end_run = _new_run_like(template_run)
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run.append(end)
    return [begin_run, instruction_run, separator_run, result_run, end_run]


def _run_bounds(paragraph: Paragraph) -> tuple[str, list[tuple[int, int, Any, Any]]]:
    text = _paragraph_text(paragraph)
    spans: list[tuple[int, int, Any, Any]] = []
    cursor = 0
    for node in _paragraph_text_nodes(paragraph):
        value = str(node.text or "")
        run = next(ancestor for ancestor in node.iterancestors() if ancestor.tag == qn("w:r"))
        spans.append((cursor, cursor + len(value), node, run))
        cursor += len(value)
    return text, spans


def _replace_marker(
    paragraph: Paragraph,
    marker: CrossReferenceMarker,
    elements_factory: Any,
) -> None:
    text, spans = _run_bounds(paragraph)
    start_entry = next(entry for entry in spans if entry[0] <= marker.start < entry[1])
    end_entry = next(entry for entry in spans if entry[0] < marker.end <= entry[1])
    start_run = start_entry[3]
    end_run = end_entry[3]
    run_ranges: dict[Any, tuple[int, int]] = {}
    for left, right, _, run in spans:
        current = run_ranges.get(run)
        run_ranges[run] = (
            min(left, current[0]) if current else left,
            max(right, current[1]) if current else right,
        )
    start_left, _ = run_ranges[start_run]
    _, end_right = run_ranges[end_run]
    prefix = text[start_left : marker.start]
    suffix = text[marker.end : end_right]
    _set_text(start_run, prefix)

    paragraph_children = list(paragraph._p)
    start_index = paragraph_children.index(start_run)
    end_index = paragraph_children.index(end_run)
    if start_run is not end_run:
        for child in paragraph_children[start_index + 1 : end_index]:
            if child.tag == qn("w:r"):
                _set_text(child, "")
        _set_text(end_run, suffix)

    insertion_index = paragraph._p.index(start_run) + 1
    for element in elements_factory(start_run):
        paragraph._p.insert(insertion_index, element)
        insertion_index += 1
    if start_run is end_run and suffix:
        paragraph._p.insert(insertion_index, _new_run_like(start_run, suffix))


def _visible_text_values(document: Any) -> list[str]:
    values: list[str] = []
    for node in document.element.iter():
        if node.tag == f"{{{W}}}t":
            values.append(str(node.text or ""))
        elif node.tag == f"{{{W}}}tab":
            values.append("\t")
        elif node.tag in {f"{{{W}}}br", f"{{{W}}}cr"}:
            values.append("\n")
    return values


def _field_instructions(document: Any) -> list[str]:
    return [str(node.text or "") for node in document.element.xpath(".//w:instrText")]


def _field_count(document: Any) -> int:
    return len(document.element.xpath(".//w:fldChar | .//w:fldSimple"))


def _next_bookmark_id(document: Any) -> int:
    values = [
        int(str(node.get(qn("w:id"))))
        for node in document.element.xpath(".//w:bookmarkStart")
        if str(node.get(qn("w:id")) or "").isdigit()
    ]
    return max(values, default=0) + 1


def apply_cross_references(
    document: Any,
    inspection: DocumentInspection,
    paragraphs: list[Paragraph],
    values: dict[str, Any],
) -> dict[str, Any]:
    analysis = analyze_cross_references(document, inspection.items, paragraphs)
    if analysis.issues:
        raise CrossReferenceInvalidError("；".join(analysis.issues))
    if not analysis.targets or not (
        analysis.reference_count or analysis.page_reference_count
    ):
        raise CrossReferenceInvalidError("没有可执行的交叉引用目标和引用标记")

    before_text = _visible_text_values(document)
    before_fields = _field_instructions(document)
    before_field_count = _field_count(document)
    next_bookmark_id = _next_bookmark_id(document)
    hyperlinks = bool(values.get("hyperlinks", True))
    labels = {
        "figure": str(values.get("figure_label", "图")),
        "table": str(values.get("table_label", "表")),
    }

    markers_by_paragraph: dict[int, list[CrossReferenceMarker]] = {}
    for marker in analysis.markers:
        markers_by_paragraph.setdefault(marker.paragraph_index, []).append(marker)

    for paragraph_index, markers in markers_by_paragraph.items():
        paragraph = paragraphs[paragraph_index]
        for marker in sorted(markers, key=lambda item: item.start, reverse=True):
            target = analysis.targets[marker.key]
            label = labels[target.kind]
            hyperlink_switch = " \\h" if hyperlinks else ""
            if marker.kind == "target":
                replacement_marker = (
                    _target_marker_with_caption_prefix(paragraph, marker, target.kind)
                    if values.get("strip_existing_prefix", True)
                    else marker
                )
                bookmark_id = next_bookmark_id
                next_bookmark_id += 1

                def target_elements(
                    template_run: Any,
                    bookmark_id: int = bookmark_id,
                    target: CrossReferenceTarget = target,
                    label: str = label,
                ) -> list[Any]:
                    bookmark_start = OxmlElement("w:bookmarkStart")
                    bookmark_start.set(qn("w:id"), str(bookmark_id))
                    bookmark_start.set(qn("w:name"), target.bookmark_name)
                    bookmark_end = OxmlElement("w:bookmarkEnd")
                    bookmark_end.set(qn("w:id"), str(bookmark_id))
                    return [
                        bookmark_start,
                        _new_run_like(template_run, f"{label} "),
                        *_field_runs(
                            template_run,
                            f" SEQ {target.kind.title()} \\* ARABIC ",
                            str(target.ordinal),
                        ),
                        bookmark_end,
                        _new_run_like(template_run, " "),
                    ]

                _replace_marker(paragraph, replacement_marker, target_elements)
            else:
                instruction_kind = "REF" if marker.kind == "reference" else "PAGEREF"
                visible = (
                    f"{label} {target.ordinal}"
                    if marker.kind == "reference"
                    else "1"
                )
                instruction = (
                    f" {instruction_kind} {target.bookmark_name}{hyperlink_switch} "
                )

                def reference_elements(
                    template_run: Any,
                    instruction: str = instruction,
                    visible: str = visible,
                ) -> list[Any]:
                    return _field_runs(template_run, instruction, visible)

                _replace_marker(paragraph, marker, reference_elements)

    if values.get("update_on_open", True):
        settings = document.settings.element
        update_nodes = settings.xpath("./w:updateFields")
        update = update_nodes[0] if update_nodes else OxmlElement("w:updateFields")
        update.set(qn("w:val"), "true")
        if not update_nodes:
            settings.append(update)

    after_text = _visible_text_values(document)
    after_fields = _field_instructions(document)
    field_delta = _field_count(document) - before_field_count
    return {
        "targets": len(analysis.targets),
        "references": analysis.reference_count,
        "page_references": analysis.page_reference_count,
        "bookmark_names": sorted(target.bookmark_name for target in analysis.targets.values()),
        "story_replacements": [
            {
                "story": "word/document.xml",
                "before": before_text,
                "after": after_text,
            }
        ],
        "field_replacements": [
            {
                "story": "word/document.xml",
                "before": before_fields,
                "after": after_fields,
            }
        ],
        "protected_count_deltas": {"field": field_delta},
        "field_count_delta": field_delta,
    }
