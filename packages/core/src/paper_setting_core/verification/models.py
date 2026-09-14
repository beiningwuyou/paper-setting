from __future__ import annotations

from pydantic import BaseModel, Field


class PackageSnapshot(BaseModel):
    file_sha256: str
    part_names: list[str]
    story_text_hashes: dict[str, str]
    story_text_values: dict[str, list[str]]
    field_instruction_hashes: dict[str, str]
    field_instruction_values: dict[str, list[str]]
    media_hashes: dict[str, str]
    protected_counts: dict[str, int]


class ValidationReport(BaseModel):
    schema_version: str = "1.0"
    source_sha256: str
    output_sha256: str
    integrity_ok: bool
    checks: dict[str, bool]
    differences: list[str] = Field(default_factory=list)
    operation_counts: dict[str, int] = Field(default_factory=dict)
    operation_issues: list[str] = Field(default_factory=list)
    already_compliant: int = 0
    compliant_targets: int = 0
    total_rule_targets: int = 0
    compliance_rate: float = Field(ge=0, le=1)
    renderer_status: str = "not_requested"
    renderer_detail: str | None = None
    formatting_mode: str = "preserve"
    formatting_notices: list[str] = Field(default_factory=list)
    uncovered_roles: list[str] = Field(default_factory=list)
    format_source_counts: dict[str, int] = Field(default_factory=dict)
    agent_audit: dict[str, object] | None = None
