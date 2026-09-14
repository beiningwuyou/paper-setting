from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, File, Form, Request, Response, UploadFile
from paper_setting_core.errors import InvalidDocxError
from paper_setting_core.templates import (
    TemplateCombinedPreview,
    TemplateFillPreview,
    TemplateSectionStructureConfig,
    TemplateStructurePreview,
    apply_section_structure,
    apply_template_combined,
    build_section_structure_preview,
    build_template_combined_preview,
    build_template_fill_preview,
    fill_template,
    inspect_template,
    parse_section_structure_config,
    parse_template_values,
)
from paper_setting_core.templates.models import TemplateInspection

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])
DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


async def _read_template(request: Request, document: UploadFile) -> tuple[bytes, str]:
    settings = request.app.state.settings
    payload = await document.read(settings.max_upload_bytes + 1)
    if len(payload) > settings.max_upload_bytes:
        raise InvalidDocxError(f"模板超过 {settings.max_upload_bytes} 字节限制")
    filename = Path(document.filename or "template.docx").name
    if Path(filename).suffix.casefold() != ".docx":
        raise InvalidDocxError("模板必须是 .docx 文件")
    return payload, filename


@router.post("/inspect")
async def inspect_template_document(
    request: Request,
    document: Annotated[UploadFile, File(description="School or journal DOCX template")],
) -> TemplateInspection:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    with tempfile.TemporaryDirectory(prefix="paper-setting-template-") as directory:
        template_path = Path(directory) / "template.docx"
        template_path.write_bytes(payload)
        return inspect_template(
            template_path,
            source_filename=filename,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )


@router.post("/fill/preview")
async def preview_template_fill(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to fill")],
    values: Annotated[str, Form(description="JSON object keyed by placeholder or control tag")],
    source_sha256: Annotated[str | None, Form()] = None,
) -> TemplateFillPreview:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_values = parse_template_values(values)
    with tempfile.TemporaryDirectory(prefix="paper-setting-template-preview-") as directory:
        template_path = Path(directory) / "template.docx"
        template_path.write_bytes(payload)
        return build_template_fill_preview(
            template_path,
            parsed_values,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )


@router.post(
    "/fill",
    response_class=Response,
    responses={
        200: {
            "description": "Filled DOCX copy",
            "content": {DOCX_MEDIA_TYPE: {}},
        }
    },
)
async def generate_filled_template(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to fill")],
    values: Annotated[str, Form(description="JSON object keyed by placeholder or control tag")],
    source_sha256: Annotated[str, Form()],
    plan_version: Annotated[str, Form()],
) -> Response:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_values = parse_template_values(values)
    with tempfile.TemporaryDirectory(prefix="paper-setting-template-fill-") as directory:
        template_path = Path(directory) / "template.docx"
        output_path = Path(directory) / "filled.docx"
        template_path.write_bytes(payload)
        result = fill_template(
            template_path,
            output_path,
            parsed_values,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            expected_plan_version=plan_version,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )
        encoded_filename = quote(result.output_filename)
        return Response(
            content=output_path.read_bytes(),
            media_type=DOCX_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "X-Template-Output-SHA256": result.output_sha256,
                "X-Template-Replacements": str(result.preview.replacement_count),
            },
        )


@router.post("/structure/preview")
async def preview_template_structure(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to restructure")],
    configuration: Annotated[str, Form(description="Section structure configuration JSON")],
    source_sha256: Annotated[str | None, Form()] = None,
) -> TemplateStructurePreview:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_configuration = parse_section_structure_config(configuration)
    with tempfile.TemporaryDirectory(prefix="paper-setting-structure-preview-") as directory:
        template_path = Path(directory) / "template.docx"
        template_path.write_bytes(payload)
        return build_section_structure_preview(
            template_path,
            parsed_configuration,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )


@router.post(
    "/structure",
    response_class=Response,
    responses={
        200: {
            "description": "DOCX copy with updated section structure",
            "content": {DOCX_MEDIA_TYPE: {}},
        }
    },
)
async def generate_template_structure(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to restructure")],
    configuration: Annotated[str, Form(description="Section structure configuration JSON")],
    source_sha256: Annotated[str, Form()],
    plan_version: Annotated[str, Form()],
) -> Response:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_configuration: TemplateSectionStructureConfig = parse_section_structure_config(
        configuration
    )
    with tempfile.TemporaryDirectory(prefix="paper-setting-structure-") as directory:
        template_path = Path(directory) / "template.docx"
        output_path = Path(directory) / "structured.docx"
        template_path.write_bytes(payload)
        result = apply_section_structure(
            template_path,
            output_path,
            parsed_configuration,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            expected_plan_version=plan_version,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )
        encoded_filename = quote(result.output_filename)
        return Response(
            content=output_path.read_bytes(),
            media_type=DOCX_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "X-Template-Output-SHA256": result.output_sha256,
                "X-Template-Structure-Operations": str(len(result.preview.operations)),
            },
        )


@router.post("/combined/preview")
async def preview_template_combined(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to fill and restructure")],
    values: Annotated[str, Form(description="JSON object keyed by placeholder or control tag")],
    configuration: Annotated[str, Form(description="Section structure configuration JSON")],
    source_sha256: Annotated[str | None, Form()] = None,
) -> TemplateCombinedPreview:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_values = parse_template_values(values)
    parsed_configuration = parse_section_structure_config(configuration)
    with tempfile.TemporaryDirectory(prefix="paper-setting-combined-preview-") as directory:
        template_path = Path(directory) / "template.docx"
        template_path.write_bytes(payload)
        return build_template_combined_preview(
            template_path,
            parsed_values,
            parsed_configuration,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )


@router.post(
    "/combined",
    response_class=Response,
    responses={
        200: {
            "description": "DOCX copy with filled fields and updated section structure",
            "content": {DOCX_MEDIA_TYPE: {}},
        }
    },
)
async def generate_template_combined(
    request: Request,
    document: Annotated[UploadFile, File(description="DOCX template to fill and restructure")],
    values: Annotated[str, Form(description="JSON object keyed by placeholder or control tag")],
    configuration: Annotated[str, Form(description="Section structure configuration JSON")],
    source_sha256: Annotated[str, Form()],
    plan_version: Annotated[str, Form()],
) -> Response:
    settings = request.app.state.settings
    payload, filename = await _read_template(request, document)
    parsed_values = parse_template_values(values)
    parsed_configuration: TemplateSectionStructureConfig = parse_section_structure_config(
        configuration
    )
    with tempfile.TemporaryDirectory(prefix="paper-setting-combined-") as directory:
        template_path = Path(directory) / "template.docx"
        output_path = Path(directory) / "combined.docx"
        template_path.write_bytes(payload)
        result = apply_template_combined(
            template_path,
            output_path,
            parsed_values,
            parsed_configuration,
            source_filename=filename,
            expected_source_sha256=source_sha256,
            expected_plan_version=plan_version,
            max_upload_bytes=settings.max_upload_bytes,
            max_uncompressed_bytes=settings.max_uncompressed_bytes,
            max_entries=settings.max_zip_entries,
        )
        encoded_filename = quote(result.output_filename)
        return Response(
            content=output_path.read_bytes(),
            media_type=DOCX_MEDIA_TYPE,
            headers={
                "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}",
                "X-Template-Output-SHA256": result.output_sha256,
                "X-Template-Replacements": str(result.preview.fill.replacement_count),
                "X-Template-Structure-Operations": str(len(result.preview.structure.operations)),
            },
        )
