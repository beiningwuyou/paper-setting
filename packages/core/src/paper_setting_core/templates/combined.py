from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

from docx import Document

from paper_setting_core.documents import sha256_file, validate_docx_package
from paper_setting_core.errors import (
    IntegrityCheckFailedError,
    StaleTemplateCombinedPlanError,
    TemplateCombinedBlockedError,
    TemplateCombinedInvalidError,
)
from paper_setting_core.templates.filling import (
    _parse,
    _protection_inventory,
    apply_fill_to_parts,
)
from paper_setting_core.templates.models import (
    TemplateCombinedPreview,
    TemplateCombinedResult,
    TemplateFillPreview,
    TemplateSectionStructureConfig,
    TemplateStructurePreview,
)
from paper_setting_core.templates.structure import (
    DOCUMENT_PART,
    DOCUMENT_RELS_PART,
    _relationship_inventory,
    apply_structure_to_parts,
)


def build_template_combined_preview(
    path: Path,
    values: dict[str, str],
    structure_configuration: TemplateSectionStructureConfig,
    *,
    source_filename: str | None = None,
    expected_source_sha256: str | None = None,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> TemplateCombinedPreview:
    from paper_setting_core.templates.filling import build_template_fill_preview
    from paper_setting_core.templates.structure import build_section_structure_preview

    fill = build_template_fill_preview(
        path,
        values,
        source_filename=source_filename,
        expected_source_sha256=expected_source_sha256,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    structure = build_section_structure_preview(
        path,
        structure_configuration,
        source_filename=source_filename,
        expected_source_sha256=fill.source_sha256,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    return _compose_combined_preview(fill, structure)


def _composition_plan_version(
    fill: TemplateFillPreview, structure: TemplateStructurePreview
) -> str:
    payload = {
        "source_sha256": fill.source_sha256,
        "fill_plan_version": fill.plan_version,
        "fill_operations": [item.operation_id for item in fill.operations],
        "fill_blocks": [item.model_dump() for item in fill.blocked_targets],
        "structure_plan_version": structure.plan_version,
        "structure_operations": [item.operation_id for item in structure.operations],
        "structure_blockers": structure.blockers,
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()


def _compose_combined_preview(
    fill: TemplateFillPreview, structure: TemplateStructurePreview
) -> TemplateCombinedPreview:
    blockers: list[str] = list(structure.blockers)
    for item in fill.blocked_targets:
        blockers.append(f"{item.key}: {item.reason}")
    fill_has_work = bool(fill.operations) and fill.can_generate
    structure_has_work = bool(structure.operations) and structure.can_generate
    has_work = fill_has_work or structure_has_work
    filename = fill.source_filename or structure.source_filename
    return TemplateCombinedPreview(
        source_filename=filename,
        source_sha256=fill.source_sha256,
        plan_version=_composition_plan_version(fill, structure),
        fill=fill,
        structure=structure,
        can_generate=bool(has_work) and not blockers,
        blockers=blockers,
        output_filename=f"{Path(filename).stem[:100] or 'template'}-combined.docx",
    )


def apply_template_combined(
    source: Path,
    output: Path,
    values: dict[str, str],
    structure_configuration: TemplateSectionStructureConfig,
    *,
    source_filename: str | None = None,
    expected_source_sha256: str,
    expected_plan_version: str,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> TemplateCombinedResult:
    preview = build_template_combined_preview(
        source,
        values,
        structure_configuration,
        source_filename=source_filename,
        expected_source_sha256=expected_source_sha256,
        max_upload_bytes=max_upload_bytes,
        max_uncompressed_bytes=max_uncompressed_bytes,
        max_entries=max_entries,
    )
    if preview.plan_version != expected_plan_version:
        raise StaleTemplateCombinedPlanError()
    if preview.blockers:
        raise TemplateCombinedBlockedError("组合计划包含不可执行项", preview.blockers)
    if not preview.can_generate:
        raise TemplateCombinedInvalidError("没有需要执行的模板填写或分节结构修改")

    with zipfile.ZipFile(source) as archive:
        infos = archive.infolist()
        parts: dict[str, bytes] = {info.filename: archive.read(info.filename) for info in infos}

    fill_changed_parts, applied_count = apply_fill_to_parts(parts, values)
    if applied_count != preview.fill.replacement_count:
        from paper_setting_core.errors import StaleTemplateFillPlanError

        raise StaleTemplateFillPlanError("模板目标数量已变化，请重新生成填写预览")
    structure_changed_parts, added_parts = apply_structure_to_parts(
        parts, structure_configuration
    )

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
    checks = _verify_combined_output(
        source,
        temporary,
        source_sha256=preview.source_sha256,
        fill_changed_parts=fill_changed_parts,
        structure_changed_parts=structure_changed_parts,
        added_parts=added_parts,
        structure_configuration=structure_configuration,
    )
    temporary.replace(output)
    return TemplateCombinedResult(
        preview=preview,
        output_sha256=sha256_file(output),
        output_filename=preview.output_filename,
        changed_parts=sorted(fill_changed_parts | structure_changed_parts),
        added_parts=sorted(added_parts),
        integrity_checks=checks,
    )


def _verify_combined_output(
    source: Path,
    output: Path,
    *,
    source_sha256: str,
    fill_changed_parts: set[str],
    structure_changed_parts: set[str],
    added_parts: set[str],
    structure_configuration: TemplateSectionStructureConfig,
) -> dict[str, bool]:
    from paper_setting_core.templates.structure import (
        _field_values,
        _structure_matches,
    )

    checks = {
        "source_unchanged": sha256_file(source) == source_sha256,
        "original_parts_preserved": False,
        "added_parts_expected": False,
        "unchanged_parts_exact": False,
        "field_instructions_unchanged": False,
        "relationships_preserved": False,
        "media_unchanged": False,
        "protected_objects_unchanged": False,
        "requested_structure_applied": False,
        "reopens_with_word_model": False,
    }
    changed = set(fill_changed_parts) | set(structure_changed_parts)
    with zipfile.ZipFile(source) as before, zipfile.ZipFile(output) as after:
        before_names = set(before.namelist())
        after_names = set(after.namelist())
        checks["original_parts_preserved"] = before_names <= after_names
        checks["added_parts_expected"] = after_names - before_names == added_parts
        untouched = before_names - changed
        checks["unchanged_parts_exact"] = all(
            before.read(name) == after.read(name) for name in untouched
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
        checks["protected_objects_unchanged"] = all(
            _protection_inventory(_parse(before.read(name)))
            == _protection_inventory(_parse(after.read(name)))
            for name in changed
            if name in before_names
        )
    checks["requested_structure_applied"] = _structure_matches(output, structure_configuration)
    try:
        Document(str(output))
        checks["reopens_with_word_model"] = True
    except Exception:
        checks["reopens_with_word_model"] = False
    if not all(checks.values()):
        failures = ", ".join(name for name, passed in checks.items() if not passed)
        raise IntegrityCheckFailedError(f"模板组合执行未通过完整性检查: {failures}")
    return checks
