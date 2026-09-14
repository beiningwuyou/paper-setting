from __future__ import annotations

import hashlib
import json
import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any, Literal, cast

from docx import Document
from lxml import etree
from pydantic import ValidationError

from paper_setting_core.documents import sha256_file, validate_docx_package
from paper_setting_core.errors import (
    IntegrityCheckFailedError,
    StaleTemplateStructurePlanError,
    TemplateStructureBlockedError,
    TemplateStructureInvalidError,
)
from paper_setting_core.templates.inspection import NS, PR, R, W, _parse, inspect_template
from paper_setting_core.templates.models import (
    TemplateSectionStructureConfig,
    TemplateSectionUpdate,
    TemplateStructureOperation,
    TemplateStructurePreview,
    TemplateStructureResult,
)

CT = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_BASE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
CONTENT_TYPES_PART = "[Content_Types].xml"
DOCUMENT_PART = "word/document.xml"
DOCUMENT_RELS_PART = "word/_rels/document.xml.rels"
SETTINGS_PART = "word/settings.xml"
NS_ALL = {**NS, "ct": CT}


def _xpath(root: etree._Element, expression: str) -> list[Any]:
    return cast(list[Any], root.xpath(expression, namespaces=NS_ALL))


def _serialize(root: etree._Element) -> bytes:
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def parse_section_structure_config(payload: str) -> TemplateSectionStructureConfig:
    try:
        return TemplateSectionStructureConfig.model_validate_json(payload)
    except ValidationError as exc:
        field_errors = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": str(error["msg"]),
                "code": str(error["type"]),
            }
            for error in exc.errors()
        ]
        raise TemplateStructureInvalidError("分节结构设置校验失败", field_errors) from exc


def _relationship_targets(parts: dict[str, bytes]) -> dict[str, str]:
    if DOCUMENT_RELS_PART not in parts:
        return {}
    root = _parse(parts[DOCUMENT_RELS_PART])
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


def _effective_references(
    parts: dict[str, bytes], sections: list[etree._Element]
) -> list[dict[tuple[str, str], str | None]]:
    targets = _relationship_targets(parts)
    effective: dict[tuple[str, str], str | None] = {}
    snapshots: list[dict[tuple[str, str], str | None]] = []
    for section in sections:
        current = dict(effective)
        for story, tag in (("header", "headerReference"), ("footer", "footerReference")):
            for reference in _xpath(section, f"./w:{tag}"):
                kind = str(reference.get(f"{{{W}}}type") or "default")
                relationship_id = str(reference.get(f"{{{R}}}id") or "")
                current[(story, kind)] = targets.get(relationship_id)
        effective = current
        snapshots.append(dict(effective))
    return snapshots


def _mode(section: Any, story: Literal["header", "footer"]) -> str:
    references = [item for item in section.references if item.story == story]
    if references:
        return "independent_copy"
    if section.section_index > 0:
        return "inherit"
    return "none"


def _operation_id(operation: TemplateStructureOperation) -> str:
    payload = operation.model_dump(mode="json", exclude={"operation_id"})
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()[:24]


def _operation(
    *,
    section_index: int | None,
    operation_type: Literal[
        "page_numbering",
        "different_first_page",
        "even_and_odd_headers",
        "header_link",
        "footer_link",
    ],
    before: dict[str, str | int | bool | None],
    after: dict[str, str | int | bool | None],
    risk: Literal["low", "medium"],
    detail: str,
) -> TemplateStructureOperation:
    item = TemplateStructureOperation(
        operation_id="pending",
        section_index=section_index,
        operation_type=operation_type,
        before=before,
        after=after,
        risk=risk,
        detail=detail,
    )
    return item.model_copy(update={"operation_id": _operation_id(item)})


def _page_operation(
    section: Any, update: TemplateSectionUpdate
) -> TemplateStructureOperation | None:
    current_format = section.page_number_format
    current_start = section.page_number_start
    if update.clear_page_numbering:
        target_format = None
        target_start = None
    else:
        target_format = update.page_number_format or current_format
        target_start = (
            None
            if update.clear_page_number_start
            else update.page_number_start
            if update.page_number_start is not None
            else current_start
        )
    requested = (
        update.clear_page_numbering
        or update.clear_page_number_start
        or update.page_number_format is not None
        or update.page_number_start is not None
    )
    if not requested or (target_format, target_start) == (current_format, current_start):
        return None
    return _operation(
        section_index=section.section_index,
        operation_type="page_numbering",
        before={"format": current_format, "start": current_start},
        after={"format": target_format, "start": target_start},
        risk="low",
        detail=f"更新第 {section.section_index + 1} 节的页码格式与起始值。",
    )


def build_section_structure_preview(
    path: Path,
    configuration: TemplateSectionStructureConfig,
    *,
    source_filename: str | None = None,
    expected_source_sha256: str | None = None,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> TemplateStructurePreview:
    inspection = inspect_template(
        path,
        source_filename=source_filename,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    if expected_source_sha256 and expected_source_sha256 != inspection.source_sha256:
        raise StaleTemplateStructurePlanError("模板文件已变化，请重新分析分节结构")
    with zipfile.ZipFile(path) as archive:
        parts = {info.filename: archive.read(info.filename) for info in archive.infolist()}
        document_root = _parse(parts[DOCUMENT_PART])
        section_nodes = _xpath(document_root, ".//w:sectPr")
        effective = _effective_references(parts, section_nodes)

    operations: list[TemplateStructureOperation] = []
    blockers: list[str] = []
    for update in sorted(configuration.sections, key=lambda item: item.section_index):
        if update.section_index >= len(inspection.sections):
            blockers.append(f"第 {update.section_index + 1} 节不存在")
            continue
        section = inspection.sections[update.section_index]
        page_operation = _page_operation(section, update)
        if page_operation:
            operations.append(page_operation)
        if (
            update.different_first_page is not None
            and update.different_first_page != section.different_first_page
        ):
            operations.append(
                _operation(
                    section_index=update.section_index,
                    operation_type="different_first_page",
                    before={"enabled": section.different_first_page},
                    after={"enabled": update.different_first_page},
                    risk="low",
                    detail=f"更新第 {update.section_index + 1} 节的首页不同设置。",
                )
            )
        for story, target_mode in (
            ("header", update.header_mode),
            ("footer", update.footer_mode),
        ):
            if target_mode == "keep":
                continue
            current_mode = _mode(section, cast(Literal["header", "footer"], story))
            if target_mode == current_mode:
                continue
            if update.section_index == 0 and target_mode == "inherit":
                label = "页眉" if story == "header" else "页脚"
                blockers.append(f"第 1 节没有前一节，不能继承{label}")
                continue
            sources = {
                kind: part_name
                for (source_story, kind), part_name in effective[update.section_index].items()
                if source_story == story
            }
            broken = [kind for kind, part_name in sources.items() if part_name is None]
            if target_mode == "independent_copy" and broken:
                blockers.append(
                    f"第 {update.section_index + 1} 节的{'页眉' if story == 'header' else '页脚'}"
                    f"存在断开的关系：{'、'.join(broken)}"
                )
                continue
            operations.append(
                _operation(
                    section_index=update.section_index,
                    operation_type=cast(
                        Literal["header_link", "footer_link"], f"{story}_link"
                    ),
                    before={"mode": current_mode},
                    after={"mode": target_mode, "parts": len(sources) or 1},
                    risk="medium",
                    detail=(
                        f"第 {update.section_index + 1} 节{'页眉' if story == 'header' else '页脚'}"
                        + (
                            "改为继承前一节。"
                            if target_mode == "inherit"
                            else "复制为独立 OOXML 部件。"
                        )
                    ),
                )
            )
    if (
        configuration.even_and_odd_headers is not None
        and configuration.even_and_odd_headers != inspection.even_and_odd_headers
    ):
        operations.append(
            _operation(
                section_index=None,
                operation_type="even_and_odd_headers",
                before={"enabled": inspection.even_and_odd_headers},
                after={"enabled": configuration.even_and_odd_headers},
                risk="low",
                detail="更新整份文档的奇偶页页眉页脚设置。",
            )
        )

    version_payload = {
        "source_sha256": inspection.source_sha256,
        "configuration": configuration.model_dump(mode="json"),
        "operations": [item.model_dump(mode="json") for item in operations],
        "blockers": blockers,
    }
    plan_version = hashlib.sha256(
        json.dumps(version_payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
    filename = source_filename or path.name
    return TemplateStructurePreview(
        source_filename=filename,
        source_sha256=inspection.source_sha256,
        plan_version=plan_version,
        configuration=configuration,
        operations=operations,
        blockers=blockers,
        can_generate=bool(operations) and not blockers,
        output_filename=f"{Path(filename).stem[:100] or 'template'}-sections.docx",
    )


def _remove_children(section: etree._Element, tag: str) -> None:
    for node in _xpath(section, f"./w:{tag}"):
        section.remove(node)


def _apply_page_numbering(section: etree._Element, update: TemplateSectionUpdate) -> None:
    nodes = _xpath(section, "./w:pgNumType")
    if update.clear_page_numbering:
        for node in nodes:
            section.remove(node)
        return
    requested = (
        update.page_number_format is not None
        or update.page_number_start is not None
        or update.clear_page_number_start
    )
    if not requested:
        return
    node = nodes[0] if nodes else etree.Element(f"{{{W}}}pgNumType")
    if not nodes:
        section.append(node)
    if update.page_number_format is not None:
        node.set(f"{{{W}}}fmt", update.page_number_format)
    if update.page_number_start is not None:
        node.set(f"{{{W}}}start", str(update.page_number_start))
    elif update.clear_page_number_start and f"{{{W}}}start" in node.attrib:
        del node.attrib[f"{{{W}}}start"]


def _apply_first_page(section: etree._Element, enabled: bool | None) -> None:
    if enabled is None:
        return
    nodes = _xpath(section, "./w:titlePg")
    if enabled and not nodes:
        section.append(etree.Element(f"{{{W}}}titlePg"))
    elif not enabled:
        for node in nodes:
            section.remove(node)


def _new_relationship_id(root: etree._Element) -> str:
    existing = {str(node.get("Id") or "") for node in _xpath(root, "./pr:Relationship")}
    number = 1
    while f"rId{number}" in existing:
        number += 1
    return f"rId{number}"


def _ensure_document_relationships(parts: dict[str, bytes]) -> etree._Element:
    if DOCUMENT_RELS_PART in parts:
        return _parse(parts[DOCUMENT_RELS_PART])
    return etree.Element(f"{{{PR}}}Relationships")


def _add_relationship(root: etree._Element, relationship_type: str, target: str) -> str:
    relationship_id = _new_relationship_id(root)
    node = etree.SubElement(root, f"{{{PR}}}Relationship")
    node.set("Id", relationship_id)
    node.set("Type", f"{REL_BASE}/{relationship_type}")
    node.set("Target", target)
    return relationship_id


def _ensure_content_type(root: etree._Element, part_name: str, content_type: str) -> None:
    package_name = f"/{part_name}"
    for node in _xpath(root, "./ct:Override"):
        if node.get("PartName") == package_name:
            return
    node = etree.SubElement(root, f"{{{CT}}}Override")
    node.set("PartName", package_name)
    node.set("ContentType", content_type)


def _next_story_part(parts: dict[str, bytes], story: Literal["header", "footer"]) -> str:
    pattern = re.compile(rf"word/{story}(\d+)\.xml")
    numbers = [int(match.group(1)) for name in parts if (match := pattern.fullmatch(name))]
    number = max(numbers, default=0) + 1
    while f"word/{story}{number}.xml" in parts:
        number += 1
    return f"word/{story}{number}.xml"


def _empty_story(story: Literal["header", "footer"]) -> bytes:
    tag = "hdr" if story == "header" else "ftr"
    root = etree.Element(f"{{{W}}}{tag}", nsmap={"w": W})
    etree.SubElement(root, f"{{{W}}}p")
    return _serialize(root)


def _rels_part_name(part_name: str) -> str:
    folder, filename = posixpath.split(part_name)
    return posixpath.join(folder, "_rels", f"{filename}.rels")


def _insert_reference(
    section: etree._Element,
    story: Literal["header", "footer"],
    kind: str,
    relationship_id: str,
) -> None:
    tag = "headerReference" if story == "header" else "footerReference"
    reference = etree.Element(f"{{{W}}}{tag}")
    reference.set(f"{{{W}}}type", kind)
    reference.set(f"{{{R}}}id", relationship_id)
    insertion_index = 0
    for index, child in enumerate(section):
        if child.tag in {f"{{{W}}}headerReference", f"{{{W}}}footerReference"}:
            insertion_index = index + 1
        else:
            break
    if story == "header":
        first_footer = next(
            (
                index
                for index, child in enumerate(section)
                if child.tag == f"{{{W}}}footerReference"
            ),
            insertion_index,
        )
        insertion_index = first_footer
    section.insert(insertion_index, reference)


def _clone_story_references(
    *,
    parts: dict[str, bytes],
    added_parts: set[str],
    section: etree._Element,
    story: Literal["header", "footer"],
    sources: dict[str, str | None],
    relationships: etree._Element,
    content_types: etree._Element,
) -> None:
    tag = "headerReference" if story == "header" else "footerReference"
    _remove_children(section, tag)
    items = sorted(sources.items()) if sources else [("default", None)]
    for kind, source_part in items:
        new_part = _next_story_part(parts, story)
        parts[new_part] = parts[source_part] if source_part else _empty_story(story)
        added_parts.add(new_part)
        if source_part:
            source_relationships = _rels_part_name(source_part)
            if source_relationships in parts:
                new_relationships = _rels_part_name(new_part)
                parts[new_relationships] = parts[source_relationships]
                added_parts.add(new_relationships)
        _ensure_content_type(
            content_types,
            new_part,
            f"application/vnd.openxmlformats-officedocument.wordprocessingml.{story}+xml",
        )
        relationship_id = _add_relationship(
            relationships,
            story,
            posixpath.basename(new_part),
        )
        _insert_reference(section, story, kind, relationship_id)


def _ensure_settings(
    parts: dict[str, bytes],
    added_parts: set[str],
    relationships: etree._Element,
    content_types: etree._Element,
) -> etree._Element:
    if SETTINGS_PART in parts:
        return _parse(parts[SETTINGS_PART])
    root = etree.Element(f"{{{W}}}settings", nsmap={"w": W})
    parts[SETTINGS_PART] = _serialize(root)
    added_parts.add(SETTINGS_PART)
    _ensure_content_type(
        content_types,
        SETTINGS_PART,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml",
    )
    if not any(
        str(node.get("Type") or "").endswith("/settings")
        for node in _xpath(relationships, "./pr:Relationship")
    ):
        _add_relationship(relationships, "settings", "settings.xml")
    return root


def _set_even_and_odd(settings: etree._Element, enabled: bool) -> None:
    nodes = _xpath(settings, "./w:evenAndOddHeaders")
    if enabled and not nodes:
        settings.append(etree.Element(f"{{{W}}}evenAndOddHeaders"))
    elif not enabled:
        for node in nodes:
            settings.remove(node)


def _text_values(payload: bytes) -> list[str]:
    return [str(value) for value in _xpath(_parse(payload), ".//w:t/text()")]


def _field_values(payload: bytes) -> list[str]:
    return [str(value) for value in _xpath(_parse(payload), ".//w:instrText/text()")]


def _relationship_inventory(payload: bytes) -> set[tuple[tuple[str, str], ...]]:
    root = _parse(payload)
    return {
        tuple(sorted((str(key), str(value)) for key, value in node.attrib.items()))
        for node in _xpath(root, "./pr:Relationship")
    }


def _structure_matches(path: Path, configuration: TemplateSectionStructureConfig) -> bool:
    inspection = inspect_template(path)
    for update in configuration.sections:
        if update.section_index >= len(inspection.sections):
            return False
        section = inspection.sections[update.section_index]
        if update.clear_page_numbering and (
            section.page_number_format is not None or section.page_number_start is not None
        ):
            return False
        if (
            update.page_number_format is not None
            and section.page_number_format != update.page_number_format
        ):
            return False
        if (
            update.page_number_start is not None
            and section.page_number_start != update.page_number_start
        ):
            return False
        if update.clear_page_number_start and section.page_number_start is not None:
            return False
        if (
            update.different_first_page is not None
            and section.different_first_page != update.different_first_page
        ):
            return False
        if update.header_mode == "inherit" and not section.inherits_headers:
            return False
        if update.header_mode == "independent_copy" and section.inherits_headers:
            return False
        if update.footer_mode == "inherit" and not section.inherits_footers:
            return False
        if update.footer_mode == "independent_copy" and section.inherits_footers:
            return False
    return not (
        configuration.even_and_odd_headers is not None
        and inspection.even_and_odd_headers != configuration.even_and_odd_headers
    )


def _verify_structure_output(
    source: Path,
    output: Path,
    *,
    source_sha256: str,
    changed_parts: set[str],
    added_parts: set[str],
    configuration: TemplateSectionStructureConfig,
) -> dict[str, bool]:
    checks = {
        "source_unchanged": sha256_file(source) == source_sha256,
        "original_parts_preserved": False,
        "added_parts_expected": False,
        "unchanged_parts_exact": False,
        "body_text_unchanged": False,
        "field_instructions_unchanged": False,
        "relationships_preserved": False,
        "media_unchanged": False,
        "requested_structure_applied": False,
        "reopens_with_word_model": False,
    }
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(output) as after:
        before_names = set(before.namelist())
        after_names = set(after.namelist())
        checks["original_parts_preserved"] = before_names <= after_names
        checks["added_parts_expected"] = after_names - before_names == added_parts
        checks["unchanged_parts_exact"] = all(
            before.read(name) == after.read(name)
            for name in before_names
            if name not in changed_parts
        )
        checks["body_text_unchanged"] = _text_values(before.read(DOCUMENT_PART)) == _text_values(
            after.read(DOCUMENT_PART)
        )
        checks["field_instructions_unchanged"] = _field_values(
            before.read(DOCUMENT_PART)
        ) == _field_values(after.read(DOCUMENT_PART))
        if DOCUMENT_RELS_PART in before_names:
            checks["relationships_preserved"] = _relationship_inventory(
                before.read(DOCUMENT_RELS_PART)
            ) <= _relationship_inventory(after.read(DOCUMENT_RELS_PART))
        else:
            checks["relationships_preserved"] = True
        media_names = {name for name in before_names if name.startswith("word/media/")}
        checks["media_unchanged"] = all(
            before.read(name) == after.read(name) for name in media_names
        )
    checks["requested_structure_applied"] = _structure_matches(output, configuration)
    try:
        Document(str(output))
        checks["reopens_with_word_model"] = True
    except Exception:
        checks["reopens_with_word_model"] = False
    if not all(checks.values()):
        failures = ", ".join(name for name, passed in checks.items() if not passed)
        raise IntegrityCheckFailedError(f"分节结构结果未通过完整性检查: {failures}")
    return checks


def apply_structure_to_parts(
    parts: dict[str, bytes],
    configuration: TemplateSectionStructureConfig,
) -> tuple[set[str], set[str]]:
    document_root = _parse(parts[DOCUMENT_PART])
    section_nodes = _xpath(document_root, ".//w:sectPr")
    effective = _effective_references(parts, section_nodes)

    relationships = _ensure_document_relationships(parts)
    content_types = _parse(parts[CONTENT_TYPES_PART])
    changed_parts: set[str] = {DOCUMENT_PART}
    added_parts: set[str] = set()
    relationships_changed = False
    content_types_changed = False
    settings_changed = False

    for update in sorted(configuration.sections, key=lambda item: item.section_index):
        section = section_nodes[update.section_index]
        _apply_page_numbering(section, update)
        _apply_first_page(section, update.different_first_page)
        for story, mode in (
            ("header", update.header_mode),
            ("footer", update.footer_mode),
        ):
            if mode == "keep":
                continue
            typed_story = cast(Literal["header", "footer"], story)
            tag = "headerReference" if story == "header" else "footerReference"
            has_explicit = bool(_xpath(section, f"./w:{tag}"))
            if mode == "inherit":
                if has_explicit:
                    _remove_children(section, tag)
                continue
            if has_explicit:
                continue
            sources = {
                kind: part_name
                for (source_story, kind), part_name in effective[update.section_index].items()
                if source_story == story
            }
            _clone_story_references(
                parts=parts,
                added_parts=added_parts,
                section=section,
                story=typed_story,
                sources=sources,
                relationships=relationships,
                content_types=content_types,
            )
            relationships_changed = True
            content_types_changed = True

    if configuration.even_and_odd_headers is not None:
        settings = _ensure_settings(parts, added_parts, relationships, content_types)
        _set_even_and_odd(settings, configuration.even_and_odd_headers)
        parts[SETTINGS_PART] = _serialize(settings)
        settings_changed = True
        relationships_changed = True
        content_types_changed = True

    parts[DOCUMENT_PART] = _serialize(document_root)
    if relationships_changed:
        if DOCUMENT_RELS_PART in parts:
            changed_parts.add(DOCUMENT_RELS_PART)
        else:
            added_parts.add(DOCUMENT_RELS_PART)
        parts[DOCUMENT_RELS_PART] = _serialize(relationships)
    if content_types_changed:
        changed_parts.add(CONTENT_TYPES_PART)
        parts[CONTENT_TYPES_PART] = _serialize(content_types)
    if settings_changed and SETTINGS_PART not in added_parts:
        changed_parts.add(SETTINGS_PART)

    return changed_parts, added_parts


def apply_section_structure(
    source: Path,
    output: Path,
    configuration: TemplateSectionStructureConfig,
    *,
    source_filename: str | None = None,
    expected_source_sha256: str,
    expected_plan_version: str,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> TemplateStructureResult:
    preview = build_section_structure_preview(
        source,
        configuration,
        source_filename=source_filename,
        expected_source_sha256=expected_source_sha256,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    if preview.plan_version != expected_plan_version:
        raise StaleTemplateStructurePlanError()
    if preview.blockers:
        raise TemplateStructureBlockedError("分节结构计划包含不可执行项", preview.blockers)
    if not preview.operations:
        raise TemplateStructureInvalidError("没有需要执行的分节结构修改")

    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        parts = {info.filename: archive.read(info.filename) for info in infos}

    changed_parts, added_parts = apply_structure_to_parts(parts, configuration)

    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.docx")
    original_names = {info.filename for info in infos}
    with zipfile.ZipFile(temporary, "w") as target_archive:
        for info in infos:
            target_archive.writestr(info, parts[info.filename])
        for name in sorted(set(parts) - original_names):
            target_archive.writestr(name, parts[name], compress_type=zipfile.ZIP_DEFLATED)
    validate_docx_package(
        temporary,
        max_upload_bytes=max(max_upload_bytes, temporary.stat().st_size),
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    checks = _verify_structure_output(
        source,
        temporary,
        source_sha256=preview.source_sha256,
        changed_parts=changed_parts,
        added_parts=added_parts,
        configuration=configuration,
    )
    temporary.replace(output)
    return TemplateStructureResult(
        preview=preview,
        output_sha256=sha256_file(output),
        output_filename=preview.output_filename,
        changed_parts=sorted(changed_parts),
        added_parts=sorted(added_parts),
        integrity_checks=checks,
    )
