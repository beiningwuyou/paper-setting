from __future__ import annotations

import hashlib
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, cast

from lxml import etree

from paper_setting_core.documents.inspection import sha256_file
from paper_setting_core.planning.models import PatchOperation
from paper_setting_core.verification.models import PackageSnapshot, ValidationReport

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
M = "http://schemas.openxmlformats.org/officeDocument/2006/math"
NS = {"w": W, "m": M}
STORY_PREFIXES = (
    "word/document.xml",
    "word/header",
    "word/footer",
    "word/footnotes.xml",
    "word/endnotes.xml",
    "word/comments.xml",
)


def _hash_text(values: list[str]) -> str:
    return hashlib.sha256("\u241e".join(values).encode("utf-8")).hexdigest()


def _xpath(root: etree._Element, expression: str) -> list[Any]:
    return cast(list[Any], root.xpath(expression, namespaces=NS))


def snapshot_package(path: Path) -> PackageSnapshot:
    story_text_hashes: dict[str, str] = {}
    story_text_values: dict[str, list[str]] = {}
    field_hashes: dict[str, str] = {}
    field_values: dict[str, list[str]] = {}
    media_hashes: dict[str, str] = {}
    counts: Counter[str] = Counter()
    with zipfile.ZipFile(path) as archive:
        part_names = sorted(entry.filename for entry in archive.infolist() if not entry.is_dir())
        for name in part_names:
            payload = archive.read(name)
            if name.startswith("word/media/"):
                media_hashes[name] = hashlib.sha256(payload).hexdigest()
            if not name.endswith(".xml"):
                continue
            try:
                root = etree.fromstring(payload)
            except etree.XMLSyntaxError:
                continue
            counts["formula"] += len(_xpath(root, ".//m:oMath | .//m:oMathPara"))
            counts["revision_insert"] += len(_xpath(root, ".//w:ins"))
            counts["revision_delete"] += len(_xpath(root, ".//w:del"))
            counts["field"] += len(_xpath(root, ".//w:fldChar | .//w:fldSimple"))
            counts["text_box"] += len(_xpath(root, ".//w:txbxContent"))
            counts["embedded_object"] += len(_xpath(root, ".//w:object"))
            counts["footnote_reference"] += len(_xpath(root, ".//w:footnoteReference"))
            counts["endnote_reference"] += len(_xpath(root, ".//w:endnoteReference"))
            counts["comment_reference"] += len(_xpath(root, ".//w:commentReference"))
            if name.startswith(STORY_PREFIXES):
                visible: list[str] = []
                for node in root.iter():
                    if node.tag == f"{{{W}}}t":
                        visible.append(node.text or "")
                    elif node.tag == f"{{{W}}}tab":
                        visible.append("\t")
                    elif node.tag in {f"{{{W}}}br", f"{{{W}}}cr"}:
                        visible.append("\n")
                story_text_hashes[name] = _hash_text(visible)
                story_text_values[name] = visible
                instructions = [node.text or "" for node in _xpath(root, ".//w:instrText")]
                field_hashes[name] = _hash_text(instructions)
                field_values[name] = instructions
    return PackageSnapshot(
        file_sha256=sha256_file(path),
        part_names=part_names,
        story_text_hashes=story_text_hashes,
        story_text_values=story_text_values,
        field_instruction_hashes=field_hashes,
        field_instruction_values=field_values,
        media_hashes=media_hashes,
        protected_counts=dict(counts),
    )


def validate_result(
    source: Path,
    output: Path,
    operations: list[PatchOperation],
    *,
    already_compliant: int = 0,
    compliant_targets: int | None = None,
    total_rule_targets: int | None = None,
    renderer_status: str = "not_requested",
    renderer_detail: str | None = None,
) -> ValidationReport:
    before = snapshot_package(source)
    after = snapshot_package(output)
    applied = [operation for operation in operations if operation.status == "applied"]

    expected_text = {story: list(values) for story, values in before.story_text_values.items()}
    text_changes_valid = True
    for operation in applied:
        for change in operation.result.get("text_changes", []):
            story = str(change.get("story", ""))
            index = int(change.get("text_index", -1))
            values = expected_text.get(story)
            if (
                values is None
                or index < 0
                or index >= len(values)
                or values[index] != change.get("before")
            ):
                text_changes_valid = False
                continue
            values[index] = str(change.get("after", ""))
        for replacement in operation.result.get("story_replacements", []):
            story = str(replacement.get("story", ""))
            before_values = replacement.get("before")
            current_values = expected_text.get(story)
            if before_values is None:
                if current_values is not None:
                    text_changes_valid = False
                    continue
            elif current_values != before_values:
                text_changes_valid = False
                continue
            expected_text[story] = [str(value) for value in replacement.get("after") or []]
    story_text_integrity = text_changes_valid and expected_text == after.story_text_values

    expected_fields = {
        story: list(values) for story, values in before.field_instruction_values.items()
    }
    field_changes_valid = True
    for operation in applied:
        if operation.operation_type != "rebuild_toc":
            continue
        before_values = operation.result.get("field_instructions_before")
        after_values = operation.result.get("field_instructions_after")
        story = "word/document.xml"
        if before_values != expected_fields.get(story, []):
            field_changes_valid = False
            continue
        expected_fields[story] = [str(value) for value in after_values or []]
    for operation in applied:
        for replacement in operation.result.get("field_replacements", []):
            story = str(replacement.get("story", ""))
            before_values = replacement.get("before")
            current_values = expected_fields.get(story)
            if before_values is None:
                if current_values is not None:
                    field_changes_valid = False
                    continue
            elif current_values != before_values:
                field_changes_valid = False
                continue
            expected_fields[story] = [str(value) for value in replacement.get("after") or []]
    field_integrity = field_changes_valid and expected_fields == after.field_instruction_values

    expected_counts = Counter(before.protected_counts)
    for operation in applied:
        if operation.operation_type == "rebuild_toc":
            field_delta = int(operation.result.get("field_count_delta", 0))
            if field_delta:
                expected_counts["field"] += field_delta
        for name, delta in operation.result.get("protected_count_deltas", {}).items():
            expected_counts[str(name)] += int(delta)
    protected_counts_integrity = dict(expected_counts) == after.protected_counts
    expected_parts = set(before.part_names)
    for operation in applied:
        expected_parts.update(str(name) for name in operation.result.get("added_parts", []))
        expected_parts.difference_update(
            str(name) for name in operation.result.get("removed_parts", [])
        )
    checks = {
        "story_text_unchanged": story_text_integrity,
        "field_instructions_unchanged": field_integrity,
        "media_unchanged": before.media_hashes == after.media_hashes,
        "protected_counts_unchanged": protected_counts_integrity,
        "part_inventory_unchanged": sorted(expected_parts) == after.part_names,
    }
    differences = [name for name, passed in checks.items() if not passed]
    operation_counts: Counter[str] = Counter(operation.status for operation in operations)
    operation_counts["compliant"] = already_compliant
    operation_issues = []
    for operation in operations:
        if operation.status not in {"skipped", "failed"}:
            continue
        status_label = "未执行" if operation.status == "skipped" else "执行失败"
        target = (
            operation.text_preview.strip() or operation.semantic_role or operation.operation_type
        )
        reason = "；".join(operation.reasons) if operation.reasons else "未提供具体原因"
        operation_issues.append(f"{status_label}：{target}。原因：{reason}。")
    if total_rule_targets is None:
        total_rule_targets = already_compliant + len(operations)
    if compliant_targets is None:
        compliant_targets = already_compliant + operation_counts["applied"]
    compliance_rate = compliant_targets / total_rule_targets if total_rule_targets else 1.0
    return ValidationReport(
        source_sha256=before.file_sha256,
        output_sha256=after.file_sha256,
        integrity_ok=all(checks.values()),
        checks=checks,
        differences=differences,
        operation_counts=dict(operation_counts),
        format_source_counts=dict(
            Counter(
                source
                for operation in applied
                for key, source in operation.field_sources.items()
                if key in operation.changed_fields
                or (
                    operation.operation_type == "apply_page_format"
                    and any(field.endswith(f".{key}") for field in operation.changed_fields)
                )
            )
        ),
        operation_issues=operation_issues,
        already_compliant=already_compliant,
        compliant_targets=compliant_targets,
        total_rule_targets=total_rule_targets,
        compliance_rate=compliance_rate,
        renderer_status=renderer_status,
        renderer_detail=renderer_detail,
    )
