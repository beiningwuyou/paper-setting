from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from paper_setting_core.documents.models import SectionFormatSnapshot
from paper_setting_core.rulepacks.models import CapabilityId, CapabilityStatus


class TemplateSummary(BaseModel):
    sections: int = 0
    styles: int = 0
    used_styles: int = 0
    placeholders: int = 0
    content_controls: int = 0
    text_boxes: int = 0
    fields: int = 0
    bookmarks: int = 0
    header_parts: int = 0
    footer_parts: int = 0


class TemplateStyleSummary(BaseModel):
    style_id: str
    name: str | None = None
    style_type: str | None = None
    based_on: str | None = None
    usage_count: int = 0


class HeaderFooterReference(BaseModel):
    story: Literal["header", "footer"]
    kind: Literal["default", "first", "even"]
    relationship_id: str
    part_name: str | None = None


class TemplateSectionSummary(BaseModel):
    section_index: int
    page: SectionFormatSnapshot
    page_number_format: str | None = None
    page_number_start: int | None = None
    different_first_page: bool = False
    inherits_headers: bool = False
    inherits_footers: bool = False
    references: list[HeaderFooterReference] = Field(default_factory=list)


class PlaceholderCandidate(BaseModel):
    token: str
    key: str
    story: str
    part_name: str
    occurrences: int = Field(ge=1)
    in_text_box: bool = False


class ContentControlCandidate(BaseModel):
    tag: str | None = None
    alias: str | None = None
    part_name: str
    story: str


class SemanticMappingCandidate(BaseModel):
    role: str
    stable_id: str
    story: str
    style_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    occurrences: int = Field(ge=1)
    text_preview: str = Field(max_length=160)


class TemplateCapabilityFinding(BaseModel):
    id: CapabilityId
    label: str
    status: CapabilityStatus
    evidence_count: int = Field(ge=0)
    detail: str


class TemplateInspection(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source_filename: str
    source_sha256: str
    summary: TemplateSummary
    sections: list[TemplateSectionSummary]
    styles: list[TemplateStyleSummary]
    placeholders: list[PlaceholderCandidate]
    content_controls: list[ContentControlCandidate]
    semantic_candidates: list[SemanticMappingCandidate]
    field_instructions: list[str]
    capabilities: list[TemplateCapabilityFinding]
    even_and_odd_headers: bool = False
    warnings: list[str] = Field(default_factory=list)


class TemplateFillOperation(BaseModel):
    operation_id: str
    key: str
    mechanism: Literal["placeholder", "content_control"]
    story: str
    part_name: str
    occurrences: int = Field(ge=1)
    value_preview: str = Field(max_length=80)


class TemplateFillBlockedTarget(BaseModel):
    key: str
    mechanism: Literal["placeholder", "content_control"]
    story: str
    part_name: str
    reason: str


class TemplateFillPreview(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source_filename: str
    source_sha256: str
    plan_version: str
    operations: list[TemplateFillOperation]
    missing_keys: list[str] = Field(default_factory=list)
    unused_keys: list[str] = Field(default_factory=list)
    blocked_targets: list[TemplateFillBlockedTarget] = Field(default_factory=list)
    replacement_count: int = Field(ge=0)
    can_generate: bool
    output_filename: str


class TemplateFillResult(BaseModel):
    preview: TemplateFillPreview
    output_sha256: str
    output_filename: str
    changed_parts: list[str]
    integrity_checks: dict[str, bool]


PageNumberFormat = Literal[
    "decimal",
    "lowerRoman",
    "upperRoman",
    "lowerLetter",
    "upperLetter",
]
HeaderFooterMode = Literal["keep", "inherit", "independent_copy"]


class TemplateSectionUpdate(BaseModel):
    section_index: int = Field(ge=0)
    page_number_format: PageNumberFormat | None = None
    page_number_start: int | None = Field(default=None, ge=0, le=32767)
    clear_page_numbering: bool = False
    clear_page_number_start: bool = False
    different_first_page: bool | None = None
    header_mode: HeaderFooterMode = "keep"
    footer_mode: HeaderFooterMode = "keep"

    @model_validator(mode="after")
    def validate_page_numbering(self) -> TemplateSectionUpdate:
        if self.clear_page_numbering and (
            self.page_number_format is not None
            or self.page_number_start is not None
            or self.clear_page_number_start
        ):
            raise ValueError("清除页码设置时不能同时设置格式、起始值或清除起始值")
        if self.clear_page_number_start and self.page_number_start is not None:
            raise ValueError("不能同时设置和清除页码起始值")
        return self


class TemplateSectionStructureConfig(BaseModel):
    sections: list[TemplateSectionUpdate] = Field(default_factory=list, max_length=200)
    even_and_odd_headers: bool | None = None

    @model_validator(mode="after")
    def unique_sections(self) -> TemplateSectionStructureConfig:
        indices = [item.section_index for item in self.sections]
        if len(indices) != len(set(indices)):
            raise ValueError("每个分节只能出现一次")
        return self


class TemplateStructureOperation(BaseModel):
    operation_id: str
    section_index: int | None = None
    operation_type: Literal[
        "page_numbering",
        "different_first_page",
        "even_and_odd_headers",
        "header_link",
        "footer_link",
    ]
    before: dict[str, str | int | bool | None]
    after: dict[str, str | int | bool | None]
    risk: Literal["low", "medium"] = "low"
    detail: str


class TemplateStructurePreview(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    source_filename: str
    source_sha256: str
    plan_version: str
    configuration: TemplateSectionStructureConfig
    operations: list[TemplateStructureOperation]
    blockers: list[str] = Field(default_factory=list)
    can_generate: bool
    output_filename: str


class TemplateStructureResult(BaseModel):
    preview: TemplateStructurePreview
    output_sha256: str
    output_filename: str
    changed_parts: list[str]
    added_parts: list[str]
    integrity_checks: dict[str, bool]


class TemplateCombinedPreview(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    plan_kind: Literal["template_combined"] = "template_combined"
    source_filename: str
    source_sha256: str
    plan_version: str
    fill: TemplateFillPreview
    structure: TemplateStructurePreview
    can_generate: bool
    blockers: list[str] = Field(default_factory=list)
    output_filename: str


class TemplateCombinedResult(BaseModel):
    preview: TemplateCombinedPreview
    output_sha256: str
    output_filename: str
    changed_parts: list[str]
    added_parts: list[str]
    integrity_checks: dict[str, bool]


class ManuscriptFieldMapping(BaseModel):
    key: str
    value_preview: str = Field(max_length=160)
    source: Literal["rule_pack", "semantic_role", "label", "unmapped"]
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(max_length=240)


class ManuscriptBodyInjectionPreview(BaseModel):
    operation_id: str
    anchor_key: str
    source_blocks: int = Field(ge=0)
    paragraph_blocks: int = Field(ge=0)
    table_blocks: int = Field(ge=0)
    image_relationships: int = Field(ge=0)
    formula_count: int = Field(ge=0)
    stripped_section_properties: int = Field(ge=0)
    excluded_front_matter_blocks: int = Field(ge=0)
    blockers: list[str] = Field(default_factory=list)


class ManuscriptCompositionPreview(BaseModel):
    schema_version: Literal["1.0"] = "1.0"
    plan_kind: Literal["manuscript_composition"] = "manuscript_composition"
    source_filename: str
    source_sha256: str
    template_filename: str
    template_sha256: str
    plan_version: str
    mappings: list[ManuscriptFieldMapping]
    fill: TemplateFillPreview
    body_injection: ManuscriptBodyInjectionPreview
    structure: TemplateStructurePreview
    can_generate: bool
    blockers: list[str] = Field(default_factory=list)
    output_filename: str


class ManuscriptCompositionResult(BaseModel):
    preview: ManuscriptCompositionPreview
    output_sha256: str
    output_filename: str
    changed_parts: list[str]
    added_parts: list[str]
    integrity_checks: dict[str, bool]
