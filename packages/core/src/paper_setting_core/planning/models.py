from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from paper_setting_core.rulepacks.policy import FormattingPolicy

OperationStatus = Literal["proposed", "manual_review", "approved", "applied", "skipped", "failed"]
ExecutionScope = Literal["full", "preserve_protected_content", "controlled_ooxml_rewrite"]


class PatchOperation(BaseModel):
    operation_id: str
    target_id: str
    rule_id: str
    semantic_role: str
    operation_type: Literal[
        "apply_role_format",
        "apply_page_format",
        "reformat_formulas",
        "normalize_citations",
        "rebuild_toc",
        "apply_automatic_numbering",
        "create_cross_references",
        "convert_notes_to_footnotes",
    ]
    before: dict[str, Any]
    after: dict[str, Any]
    text_preview: str = ""
    precondition_hash: str
    risk: Literal["low", "medium", "high"] = "low"
    confidence: float = Field(ge=0, le=1)
    status: OperationStatus
    execution_scope: ExecutionScope = "full"
    changed_fields: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    result: dict[str, Any] = Field(default_factory=dict)
    field_sources: dict[str, str] = Field(default_factory=dict)


class PatchPlan(BaseModel):
    schema_version: str = "1.0"
    source_sha256: str
    rule_pack_id: str
    rule_pack_version: str
    rule_pack_hash: str
    plan_version: str
    operations: list[PatchOperation]
    summary: dict[str, int]
    formatting_policy: FormattingPolicy | None = None
    notices: list[str] = Field(default_factory=list)
    uncovered_roles: list[str] = Field(default_factory=list)
