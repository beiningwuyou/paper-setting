from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from paper_setting_api.dependencies import get_rule_pack_service
from paper_setting_core.errors import RuleSourceInvalidError
from paper_setting_core.rulepacks import (
    extract_rule_pack_draft,
    list_capabilities,
    read_rule_source_file,
)
from paper_setting_core.rulepacks.extraction import SourceFormat
from paper_setting_core.rulepacks.models import (
    CapabilityDefinition,
    RulePack,
    RulePackCapabilityReport,
    RulePackDraft,
)
from paper_setting_runtime.schemas import RulePackSummary
from paper_setting_runtime.services import RulePackService

router = APIRouter(prefix="/api/v1/rule-packs", tags=["rule-packs"])
Service = Annotated[RulePackService, Depends(get_rule_pack_service)]


@router.get("")
def list_rule_packs(service: Service) -> list[RulePackSummary]:
    return service.list()


@router.get("/capabilities")
def get_capabilities() -> list[CapabilityDefinition]:
    return list_capabilities()


@router.get("/{rule_pack_id}")
def get_rule_pack(rule_pack_id: str, service: Service) -> RulePack:
    return service.get(rule_pack_id)


@router.get("/{rule_pack_id}/capabilities")
def get_rule_pack_capabilities(
    rule_pack_id: str, service: Service
) -> RulePackCapabilityReport:
    return service.capability_report(rule_pack_id)


@router.post("/drafts")
async def create_rule_pack_draft(
    text: Annotated[str | None, Form(description="Pasted formatting guide text")] = None,
    document: Annotated[
        UploadFile | None,
        File(description="UTF-8 TXT, Markdown, or DOCX formatting guide"),
    ] = None,
    rule_pack_id: Annotated[str | None, Form()] = None,
    name: Annotated[str | None, Form()] = None,
) -> RulePackDraft:
    parts: list[str] = []
    source_filename: str | None = None
    source_format: SourceFormat = "text"
    if text and text.strip():
        parts.append(text)
    if document is not None:
        payload = await document.read(5 * 1024 * 1024 + 1)
        if len(payload) > 5 * 1024 * 1024:
            raise RuleSourceInvalidError("规范文件超过 5 MiB 限制")
        source_filename = document.filename or "rules.txt"
        file_text, file_format = read_rule_source_file(source_filename, payload)
        parts.append(file_text)
        source_format = "mixed" if text and text.strip() else file_format
    if not parts:
        raise RuleSourceInvalidError("请粘贴规范文本或上传规范文件")
    return extract_rule_pack_draft(
        "\n".join(parts),
        source_filename=source_filename,
        source_format=source_format,
        rule_pack_id=rule_pack_id,
        name=name,
    )


@router.post("/import", status_code=status.HTTP_201_CREATED)
async def import_rule_pack(
    service: Service,
    document: Annotated[UploadFile, File(description="JSON rule pack")],
) -> RulePackSummary:
    payload = await document.read(2 * 1024 * 1024 + 1)
    if len(payload) > 2 * 1024 * 1024:
        from paper_setting_core.errors import RulePackInvalidError

        raise RulePackInvalidError("规则包超过 2 MiB")
    return service.import_json(payload)
