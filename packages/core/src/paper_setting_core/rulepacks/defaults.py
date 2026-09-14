from paper_setting_core.rulepacks.models import (
    AdvancedWordFormat,
    AutomaticNumberingFormat,
    CharacterFormat,
    CitationFormat,
    CrossReferenceFormat,
    FormulaFormat,
    PageFormat,
    ParagraphFormat,
    RoleRule,
    RulePack,
    TocFormat,
)


def default_rule_pack() -> RulePack:
    source = "Paper Setting MVP 内置中文学位论文通用规则"
    return RulePack(
        id="zh-thesis-default",
        name="中文学位论文通用格式",
        version="1.0.0",
        description="用于验证流程的通用规则；提交前仍应按学校要求调整。",
        page=PageFormat(),
        roles=[
            RoleRule(
                id="title.paper",
                role="paper_title",
                description="论文标题",
                source=source,
                paragraph=ParagraphFormat(alignment="center", space_after_pt=18),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=22, bold=True
                ),
            ),
            RoleRule(
                id="abstract.heading",
                role="abstract_heading",
                description="摘要标题",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="center", space_before_pt=12, space_after_pt=12
                ),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=16, bold=True
                ),
            ),
            RoleRule(
                id="abstract.body",
                role="abstract_body",
                description="摘要正文",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="justify", first_line_indent_pt=24, line_spacing=1.5
                ),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=12
                ),
            ),
            RoleRule(
                id="keywords",
                role="keywords",
                description="关键词",
                source=source,
                paragraph=ParagraphFormat(alignment="justify", line_spacing=1.5),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=12
                ),
            ),
            RoleRule(
                id="heading.1",
                role="heading_1",
                description="一级标题",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="center",
                    space_before_pt=12,
                    space_after_pt=6,
                    keep_with_next=True,
                ),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=16, bold=True
                ),
            ),
            RoleRule(
                id="heading.2",
                role="heading_2",
                description="二级标题",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="left",
                    space_before_pt=6,
                    space_after_pt=6,
                    keep_with_next=True,
                ),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=14, bold=True
                ),
            ),
            RoleRule(
                id="heading.3",
                role="heading_3",
                description="三级标题",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="left", space_before_pt=6, keep_with_next=True
                ),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=12, bold=True
                ),
            ),
            RoleRule(
                id="body.normal",
                role="body",
                description="正文",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="justify", first_line_indent_pt=24, line_spacing=1.5
                ),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=12
                ),
            ),
            RoleRule(
                id="caption.figure",
                role="figure_caption",
                description="图题",
                source=source,
                paragraph=ParagraphFormat(alignment="center", space_before_pt=6, space_after_pt=6),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=10.5
                ),
            ),
            RoleRule(
                id="caption.table",
                role="table_caption",
                description="表题",
                source=source,
                paragraph=ParagraphFormat(alignment="center", space_before_pt=6, space_after_pt=6),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=10.5
                ),
            ),
            RoleRule(
                id="references.heading",
                role="bibliography_heading",
                description="参考文献标题",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="center", space_before_pt=12, space_after_pt=12
                ),
                character=CharacterFormat(
                    east_asia_font="黑体", latin_font="Times New Roman", size_pt=16, bold=True
                ),
            ),
            RoleRule(
                id="references.entry",
                role="reference_entry",
                description="参考文献条目",
                source=source,
                paragraph=ParagraphFormat(
                    alignment="justify",
                    left_indent_pt=21,
                    first_line_indent_pt=-21,
                    line_spacing=1.0,
                ),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=10.5
                ),
            ),
            RoleRule(
                id="table.body",
                role="table_body",
                description="表格正文",
                source=source,
                paragraph=ParagraphFormat(alignment="left", line_spacing=1.0),
                character=CharacterFormat(
                    east_asia_font="宋体", latin_font="Times New Roman", size_pt=10.5
                ),
            ),
        ],
    )


def deep_rule_pack() -> RulePack:
    base = default_rule_pack()
    return base.model_copy(
        update={
            "id": "zh-thesis-deep",
            "name": "中文学位论文·深层 Word 自动化",
            "version": "1.2.0",
            "description": (
                "在通用格式上启用公式样式、数字引用规范化、目录域、Word 自动编号"
                "和显式图表交叉引用。"
            ),
            "advanced": AdvancedWordFormat(
                formula=FormulaFormat(enabled=True, math_font="Cambria Math", style="plain"),
                citations=CitationFormat(enabled=True),
                toc=TocFormat(enabled=True, min_level=1, max_level=3),
                numbering=AutomaticNumberingFormat(enabled=True),
                cross_references=CrossReferenceFormat(enabled=True),
            ),
        }
    )
