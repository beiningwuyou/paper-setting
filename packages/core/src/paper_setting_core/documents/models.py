from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

StoryType = Literal["body", "table", "header", "footer"]


class RiskFlags(BaseModel):
    formula: bool = False
    text_box: bool = False
    drawing: bool = False
    revision: bool = False
    field: bool = False
    external_link: bool = False
    embedded_object: bool = False
    nested_table: bool = False

    @property
    def protected(self) -> bool:
        return any(self.model_dump().values())


class EffectiveFormat(BaseModel):
    paragraph: dict[str, Any] = Field(default_factory=dict)
    character: dict[str, Any] = Field(default_factory=dict)


class SectionFormatSnapshot(BaseModel):
    section_index: int
    width_mm: float
    height_mm: float
    orientation: Literal["portrait", "landscape"]
    margin_top_mm: float
    margin_bottom_mm: float
    margin_left_mm: float
    margin_right_mm: float
    header_distance_mm: float
    footer_distance_mm: float


class DocumentItem(BaseModel):
    stable_id: str
    story: StoryType
    path: str
    section_index: int | None = None
    order: int
    text_preview: str
    exact_text_hash: str
    normalized_text_hash: str
    style_id: str | None = None
    style_name: str | None = None
    semantic_role: str
    confidence: float = Field(ge=0, le=1)
    risks: RiskFlags = Field(default_factory=RiskFlags)
    effective_format: EffectiveFormat = Field(default_factory=EffectiveFormat)


class InspectionSummary(BaseModel):
    paragraphs: int = 0
    table_paragraphs: int = 0
    headers: int = 0
    footers: int = 0
    protected_items: int = 0
    role_counts: dict[str, int] = Field(default_factory=dict)
    risk_counts: dict[str, int] = Field(default_factory=dict)


class AdvancedWordInspection(BaseModel):
    formula_count: int = 0
    formula_math_font: str | None = None
    formula_styles: list[str] = Field(default_factory=list)
    citation_candidate_count: int = 0
    toc_instructions: list[str] = Field(default_factory=list)
    update_fields_on_open: bool = False
    numbered_role_counts: dict[str, int] = Field(default_factory=dict)
    cross_reference_target_count: int = 0
    cross_reference_marker_count: int = 0
    cross_reference_page_marker_count: int = 0
    cross_reference_existing_field_count: int = 0
    cross_reference_target_counts: dict[str, int] = Field(default_factory=dict)
    sequence_numbered_role_counts: dict[str, int] = Field(default_factory=dict)
    cross_reference_issues: list[str] = Field(default_factory=list)
    footnote_count: int = 0
    endnote_count: int = 0
    inline_note_candidate_count: int = 0
    bibliography_entry_count: int = 0
    footnote_numbering_restarts: list[str] = Field(default_factory=list)
    footnote_number_formats: list[str] = Field(default_factory=list)


class DocumentInspection(BaseModel):
    schema_version: str = "1.0"
    source_sha256: str
    source_filename: str
    items: list[DocumentItem]
    sections: list[SectionFormatSnapshot] = Field(default_factory=list)
    summary: InspectionSummary
    advanced: AdvancedWordInspection = Field(default_factory=AdvancedWordInspection)
    warnings: list[str] = Field(default_factory=list)
