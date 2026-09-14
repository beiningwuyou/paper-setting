from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Alignment = Literal["left", "center", "right", "justify"]
Severity = Literal["info", "warning", "error"]
LineSpacingMode = Literal["multiple", "exact", "at_least"]
CapabilityId = Literal[
    "document.page_layout",
    "document.paragraph_formatting",
    "document.character_formatting",
    "word.formula_formatting",
    "word.citation_normalization",
    "word.toc",
    "word.automatic_numbering",
    "word.notes",
    "template.inspect",
    "template.fill",
    "template.placeholders",
    "sections.page_numbering",
    "sections.headers_footers",
    "word.cross_references",
    "word.content_controls",
]
CapabilityStatus = Literal["supported", "planned"]


class RequirementSource(BaseModel):
    kind: Literal["builtin", "text", "docx", "template", "manual"] = "manual"
    label: str = Field(min_length=1, max_length=200)
    sha256: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{64}$")


class RuleRequirements(BaseModel):
    sources: list[RequirementSource] = Field(default_factory=list)
    unresolved: list[str] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)
    required_capabilities: list[CapabilityId] = Field(default_factory=list)


class CapabilityDefinition(BaseModel):
    id: CapabilityId
    label: str
    status: CapabilityStatus
    detail: str


class RulePackCapabilityReport(BaseModel):
    executable: bool
    required: list[CapabilityId]
    supported: list[CapabilityId]
    unsupported: list[CapabilityId]
    blockers: list[str] = Field(default_factory=list)


class PageFormat(BaseModel):
    width_mm: float = Field(default=210, gt=0)
    height_mm: float = Field(default=297, gt=0)
    orientation: Literal["portrait", "landscape"] = "portrait"
    margin_top_mm: float = Field(default=25.4, ge=0)
    margin_bottom_mm: float = Field(default=25.4, ge=0)
    margin_left_mm: float = Field(default=25.4, ge=0)
    margin_right_mm: float = Field(default=25.4, ge=0)
    header_distance_mm: float = Field(default=15, ge=0)
    footer_distance_mm: float = Field(default=17.5, ge=0)

    @model_validator(mode="after")
    def validate_content_area(self) -> PageFormat:
        page_width = self.height_mm if self.orientation == "landscape" else self.width_mm
        page_height = self.width_mm if self.orientation == "landscape" else self.height_mm
        if self.margin_left_mm + self.margin_right_mm >= page_width:
            raise ValueError("left and right margins must leave a positive content width")
        if self.margin_top_mm + self.margin_bottom_mm >= page_height:
            raise ValueError("top and bottom margins must leave a positive content height")
        return self


class ParagraphFormat(BaseModel):
    alignment: Alignment | None = None
    first_line_indent_pt: float | None = None
    left_indent_pt: float | None = None
    right_indent_pt: float | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    space_before_lines: float | None = Field(default=None, ge=0)
    space_after_lines: float | None = Field(default=None, ge=0)
    line_spacing: float | None = Field(default=None, gt=0)
    line_spacing_mode: LineSpacingMode | None = None
    keep_with_next: bool | None = None
    keep_together: bool | None = None
    page_break_before: bool | None = None

    @model_validator(mode="after")
    def normalize_line_spacing_mode(self) -> ParagraphFormat:
        if self.space_before_pt is not None and self.space_before_lines is not None:
            raise ValueError("space_before_pt and space_before_lines are mutually exclusive")
        if self.space_after_pt is not None and self.space_after_lines is not None:
            raise ValueError("space_after_pt and space_after_lines are mutually exclusive")
        if self.line_spacing is None and self.line_spacing_mode is not None:
            raise ValueError("line_spacing is required when line_spacing_mode is set")
        if self.line_spacing is not None and self.line_spacing_mode is None:
            self.line_spacing_mode = "multiple"
        return self


class CharacterFormat(BaseModel):
    east_asia_font: str | None = None
    latin_font: str | None = None
    size_pt: float | None = Field(default=None, gt=0)
    color: str | None = Field(default=None, pattern=r"^[0-9A-Fa-f]{6}$")
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None


class FormulaFormat(BaseModel):
    enabled: bool = False
    math_font: str = Field(default="Cambria Math", min_length=1)
    style: Literal["preserve", "plain", "italic", "bold", "bold_italic"] = "preserve"


class CitationFormat(BaseModel):
    enabled: bool = False
    style: Literal["numeric_brackets"] = "numeric_brackets"
    sort_numbers: bool = True
    collapse_ranges: bool = True
    range_separator: Literal["-", "–"] = "–"


class TocFormat(BaseModel):
    enabled: bool = False
    min_level: int = Field(default=1, ge=1, le=9)
    max_level: int = Field(default=3, ge=1, le=9)
    hyperlinks: bool = True
    update_on_open: bool = True

    @model_validator(mode="after")
    def validate_levels(self) -> TocFormat:
        if self.min_level > self.max_level:
            raise ValueError("toc min_level must not exceed max_level")
        return self


class AutomaticNumberingFormat(BaseModel):
    enabled: bool = False
    headings: bool = True
    bibliography: bool = True
    captions: bool = True
    strip_existing_prefix: bool = True


class CrossReferenceFormat(BaseModel):
    enabled: bool = False
    hyperlinks: bool = True
    update_on_open: bool = True
    strip_existing_prefix: bool = True
    figure_label: str = Field(default="图", min_length=1, max_length=20)
    table_label: str = Field(default="表", min_length=1, max_length=20)


class NotesFormat(BaseModel):
    enabled: bool = False
    convert_inline_citations: bool = True
    convert_endnotes: bool = True
    delete_bibliography: bool = False
    numbering_restart: Literal["continuous", "each_section", "each_page"] = "continuous"
    number_format: Literal["decimal", "decimal_enclosed_circle"] = "decimal"


class AdvancedWordFormat(BaseModel):
    formula: FormulaFormat = Field(default_factory=FormulaFormat)
    citations: CitationFormat = Field(default_factory=CitationFormat)
    toc: TocFormat = Field(default_factory=TocFormat)
    numbering: AutomaticNumberingFormat = Field(default_factory=AutomaticNumberingFormat)
    cross_references: CrossReferenceFormat = Field(default_factory=CrossReferenceFormat)
    notes: NotesFormat = Field(default_factory=NotesFormat)


TemplatePageNumberFormat = Literal[
    "decimal",
    "lowerRoman",
    "upperRoman",
    "lowerLetter",
    "upperLetter",
]
TemplateHeaderFooterMode = Literal["keep", "inherit", "independent_copy"]


class TemplateSectionRule(BaseModel):
    section_index: int = Field(ge=0)
    page_number_format: TemplatePageNumberFormat | None = None
    page_number_start: int | None = Field(default=None, ge=0, le=32767)
    clear_page_numbering: bool = False
    clear_page_number_start: bool = False
    different_first_page: bool | None = None
    header_mode: TemplateHeaderFooterMode = "keep"
    footer_mode: TemplateHeaderFooterMode = "keep"

    @model_validator(mode="after")
    def validate_page_numbering(self) -> TemplateSectionRule:
        if self.clear_page_numbering and (
            self.page_number_format is not None
            or self.page_number_start is not None
            or self.clear_page_number_start
        ):
            raise ValueError("清除页码设置时不能同时设置格式、起始值或清除起始值")
        if self.clear_page_number_start and self.page_number_start is not None:
            raise ValueError("不能同时设置和清除页码起始值")
        return self


class TemplateStructureRule(BaseModel):
    sections: list[TemplateSectionRule] = Field(default_factory=list, max_length=200)
    even_and_odd_headers: bool | None = None

    @model_validator(mode="after")
    def unique_sections(self) -> TemplateStructureRule:
        indices = [item.section_index for item in self.sections]
        if len(indices) != len(set(indices)):
            raise ValueError("每个分节只能出现一次")
        return self


class TemplateFillRule(BaseModel):
    values: dict[str, str] = Field(default_factory=dict)


class TemplateRule(BaseModel):
    fill: TemplateFillRule = Field(default_factory=TemplateFillRule)
    structure: TemplateStructureRule = Field(default_factory=TemplateStructureRule)


class RoleRule(BaseModel):
    id: str = Field(min_length=1, pattern=r"^[a-z0-9_.-]+$")
    role: str = Field(min_length=1)
    description: str
    source: str
    severity: Severity = "error"
    priority: int = 100
    min_confidence: float = Field(default=0.9, ge=0, le=1)
    preserve_style_identity: bool = False
    paragraph: ParagraphFormat = Field(default_factory=ParagraphFormat)
    character: CharacterFormat = Field(default_factory=CharacterFormat)


class RulePack(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal["1.0", "2.0"] = "1.0"
    id: str = Field(min_length=1, pattern=r"^[a-z0-9-]+$")
    name: str = Field(min_length=1)
    version: str = Field(min_length=1)
    locale: str = "zh-CN"
    description: str = ""
    requirements: RuleRequirements = Field(default_factory=RuleRequirements)
    page: PageFormat = Field(default_factory=PageFormat)
    explicit_page_fields: list[str] | None = None
    roles: list[RoleRule] = Field(min_length=1)
    advanced: AdvancedWordFormat = Field(default_factory=AdvancedWordFormat)
    template: TemplateRule = Field(default_factory=TemplateRule)

    @model_validator(mode="before")
    @classmethod
    def capture_page_fields(cls, data):
        if isinstance(data, dict) and "explicit_page_fields" not in data:
            data = dict(data)
            page = data.get("page")
            # A PageFormat instance supplied by code denotes a complete page rule.
            data["explicit_page_fields"] = (
                list(PageFormat.model_fields) if isinstance(page, PageFormat)
                else list(page or {})
            )
        return data

    @model_validator(mode="after")
    def unique_roles(self) -> RulePack:
        if self.explicit_page_fields is not None and (
            set(self.explicit_page_fields) - set(PageFormat.model_fields)
        ):
            raise ValueError("unknown explicit page field")
        roles = [rule.role for rule in self.roles]
        if len(roles) != len(set(roles)):
            raise ValueError("role rules must be unique")
        rule_ids = [rule.id for rule in self.roles]
        if len(rule_ids) != len(set(rule_ids)):
            raise ValueError("rule ids must be unique")
        return self

    def rule_for(self, role: str) -> RoleRule | None:
        matching = [rule for rule in self.roles if rule.role == role]
        if not matching:
            return None
        return sorted(matching, key=lambda item: item.priority, reverse=True)[0]


class RuleEvidence(BaseModel):
    role: str
    property_path: str
    value: str | float | bool
    source_line: int = Field(ge=1)
    quote: str = Field(max_length=240)
    confidence: float = Field(ge=0, le=1)


class RulePackDraft(BaseModel):
    rule_pack: RulePack
    evidence: list[RuleEvidence]
    warnings: list[str]
    source_filename: str | None = None
    source_format: Literal["text", "txt", "md", "docx", "mixed"]
    recognized_properties: int = Field(ge=0)
    unrecognized_lines: int = Field(ge=0)
    capability_report: RulePackCapabilityReport
