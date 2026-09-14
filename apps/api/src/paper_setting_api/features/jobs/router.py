from __future__ import annotations

import asyncio
import json
import os
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, File, Form, Header, Query, Response, UploadFile, status
from fastapi.responses import FileResponse, StreamingResponse
from paper_setting_api.dependencies import get_job_service
from paper_setting_core.documents import DocumentInspection
from paper_setting_core.errors import AppError
from paper_setting_core.planning.models import PatchPlan
from paper_setting_core.templates.models import (
    ManuscriptCompositionPreview,
    TemplateCombinedPreview,
)
from paper_setting_core.verification import ValidationReport
from paper_setting_runtime.schemas import ApprovalRequest, ArtifactView, JobPage, JobView
from paper_setting_runtime.services import JobService

router = APIRouter(prefix="/api/v1/jobs", tags=["jobs"])
Service = Annotated[JobService, Depends(get_job_service)]


@router.get("")
def list_jobs(
    service: Service,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> JobPage:
    return service.list_jobs(limit=limit, cursor=cursor)


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def create_job(
    service: Service,
    document: Annotated[UploadFile, File()],
    rule_pack_id: Annotated[str, Form()],
    render_preview: Annotated[bool, Form()] = True,
    mode: Annotated[Literal["format", "template"] | None, Form()] = None,
    template_document: Annotated[UploadFile | None, File()] = None,
    formatting_mode: Annotated[Literal["standardize", "preserve"], Form()] = "standardize",
) -> JobView:
    suffix = Path(document.filename or "source.docx").suffix.lower()
    descriptor, temporary_name = tempfile.mkstemp(suffix=suffix)
    os.close(descriptor)
    temporary = Path(temporary_name)
    template_temporary: Path | None = None
    try:
        total = 0
        with temporary.open("wb") as handle:
            while chunk := await document.read(1024 * 1024):
                total += len(chunk)
                if total > service.settings.max_upload_bytes:
                    raise AppError("文件超过上传限制", "FILE_TOO_LARGE", 413)
                handle.write(chunk)
        if template_document is not None:
            template_suffix = Path(template_document.filename or "template.docx").suffix.lower()
            template_descriptor, template_name = tempfile.mkstemp(suffix=template_suffix)
            os.close(template_descriptor)
            template_temporary = Path(template_name)
            total = 0
            with template_temporary.open("wb") as handle:
                while chunk := await template_document.read(1024 * 1024):
                    total += len(chunk)
                    if total > service.settings.max_upload_bytes:
                        raise AppError("模板超过上传限制", "FILE_TOO_LARGE", 413)
                    handle.write(chunk)
        return await asyncio.to_thread(
            service.create_from_file,
            temporary,
            source_filename=document.filename or "source.docx",
            rule_pack_id=rule_pack_id,
            render_preview=render_preview,
            mode=mode,
            formatting_mode=formatting_mode,
            template_path=template_temporary,
            template_filename=(
                template_document.filename if template_document is not None else None
            ),
        )
    finally:
        temporary.unlink(missing_ok=True)
        if template_temporary is not None:
            template_temporary.unlink(missing_ok=True)


@router.get("/{job_id}")
def get_job(job_id: str, service: Service) -> JobView:
    return service.get(job_id)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_job(job_id: str, service: Service) -> Response:
    service.delete(job_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{job_id}/plan")
def get_plan(job_id: str, service: Service) -> PatchPlan:
    return service.get_plan(job_id)


@router.get("/{job_id}/template-plan")
def get_template_plan(
    job_id: str, service: Service
) -> TemplateCombinedPreview | ManuscriptCompositionPreview:
    return service.get_template_plan(job_id)


@router.get("/{job_id}/inspection")
def get_inspection(job_id: str, service: Service) -> DocumentInspection:
    return service.get_inspection(job_id)


@router.post("/{job_id}/approve")
def approve_job(job_id: str, approval: ApprovalRequest, service: Service) -> JobView:
    return service.approve(job_id, approval)


@router.post("/{job_id}/cancel")
def cancel_job(job_id: str, service: Service) -> JobView:
    return service.cancel(job_id)


@router.get("/{job_id}/report")
def get_report(job_id: str, service: Service) -> ValidationReport:
    return service.get_report(job_id)


@router.get("/{job_id}/artifacts")
def list_artifacts(job_id: str, service: Service) -> list[ArtifactView]:
    return service.list_artifacts(job_id)


@router.get("/{job_id}/artifacts/{artifact}")
def download_artifact(job_id: str, artifact: str, service: Service) -> FileResponse:
    path, digest, download_filename = service.artifact_path(job_id, artifact)
    media_type = {
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".pdf": "application/pdf",
        ".json": "application/json",
        ".html": "text/html",
    }.get(path.suffix.lower(), "application/octet-stream")
    return FileResponse(
        path,
        media_type=media_type,
        filename=download_filename,
        headers={"ETag": f'"{digest}"'},
    )


@router.get("/{job_id}/events")
async def stream_events(
    job_id: str,
    service: Service,
    last_event_id: Annotated[int | None, Header(alias="Last-Event-ID")] = None,
) -> StreamingResponse:
    service.get(job_id)

    async def events() -> AsyncIterator[str]:
        cursor = last_event_id or 0
        idle_ticks = 0
        while True:
            records = service.events_after(job_id, cursor)
            if records:
                idle_ticks = 0
                for record in records:
                    cursor = record["id"]
                    payload = json.dumps(record["data"], ensure_ascii=False, separators=(",", ":"))
                    yield f"id: {cursor}\nevent: {record['event']}\ndata: {payload}\n\n"
                status_value = service.get(job_id).status
                if status_value in {"completed", "failed", "cancelled"}:
                    return
            else:
                idle_ticks += 1
                if idle_ticks % 20 == 0:
                    yield ": keep-alive\n\n"
            await asyncio.sleep(0.5)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
