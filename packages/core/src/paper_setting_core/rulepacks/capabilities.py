from __future__ import annotations

from paper_setting_core.rulepacks.models import (
    CapabilityDefinition,
    CapabilityId,
    RulePack,
    RulePackCapabilityReport,
)

CAPABILITIES: tuple[CapabilityDefinition, ...] = (
    CapabilityDefinition(
        id="document.page_layout",
        label="页面与页边距",
        status="supported",
        detail="应用纸张、方向、页边距及页眉页脚距离。",
    ),
    CapabilityDefinition(
        id="document.paragraph_formatting",
        label="段落格式",
        status="supported",
        detail="应用对齐、缩进、间距、行距和分页控制。",
    ),
    CapabilityDefinition(
        id="document.character_formatting",
        label="字符格式",
        status="supported",
        detail="应用中西文字体、字号、颜色和粗体。",
    ),
    CapabilityDefinition(
        id="word.formula_formatting",
        label="公式样式",
        status="supported",
        detail="受控调整 OMML 数学字体和运行样式。",
    ),
    CapabilityDefinition(
        id="word.citation_normalization",
        label="数字引用规范化",
        status="supported",
        detail="排序、去重并合并明确的数字引用。",
    ),
    CapabilityDefinition(
        id="word.toc",
        label="目录域",
        status="supported",
        detail="创建或更新 TOC 域并设置打开时更新。",
    ),
    CapabilityDefinition(
        id="word.automatic_numbering",
        label="自动编号",
        status="supported",
        detail="为标题、图表题和参考文献绑定 Word 编号。",
    ),
    CapabilityDefinition(
        id="word.notes",
        label="注释与脚注",
        status="supported",
        detail="转换正文引注或尾注、删除文末参考文献并设置脚注编号。",
    ),
    CapabilityDefinition(
        id="template.inspect",
        label="学校模板分析",
        status="supported",
        detail="分析模板分节、样式、字段、占位符和语义候选。",
    ),
    CapabilityDefinition(
        id="template.fill",
        label="模板底座填充",
        status="supported",
        detail="复制模板并按显式字段映射生成新的 DOCX 副本。",
    ),
    CapabilityDefinition(
        id="template.placeholders",
        label="跨部件占位符替换",
        status="supported",
        detail="替换正文、页眉页脚和文本框中的结构化占位符。",
    ),
    CapabilityDefinition(
        id="sections.page_numbering",
        label="分节页码",
        status="supported",
        detail="设置罗马/阿拉伯页码、起始值和分节重启。",
    ),
    CapabilityDefinition(
        id="sections.headers_footers",
        label="分节页眉页脚",
        status="supported",
        detail="控制首页、奇偶页，并安全继承或克隆页眉页脚部件。",
    ),
    CapabilityDefinition(
        id="word.cross_references",
        label="题注与交叉引用",
        status="supported",
        detail="根据显式标记创建 SEQ、书签、REF 和 PAGEREF 字段。",
    ),
    CapabilityDefinition(
        id="word.content_controls",
        label="内容控件写入",
        status="supported",
        detail="按标签或别名填写不含数据绑定和受保护对象的普通内容控件。",
    ),
)

_BY_ID = {item.id: item for item in CAPABILITIES}


def list_capabilities() -> list[CapabilityDefinition]:
    return list(CAPABILITIES)


def implied_capabilities(rule_pack: RulePack) -> set[CapabilityId]:
    required: set[CapabilityId] = {"document.page_layout"}
    if any(
        any(value is not None for value in rule.paragraph.model_dump().values())
        for rule in rule_pack.roles
    ):
        required.add("document.paragraph_formatting")
    if any(
        any(value is not None for value in rule.character.model_dump().values())
        for rule in rule_pack.roles
    ):
        required.add("document.character_formatting")
    advanced = rule_pack.advanced
    advanced_capabilities: tuple[tuple[bool, CapabilityId], ...] = (
        (advanced.formula.enabled, "word.formula_formatting"),
        (advanced.citations.enabled, "word.citation_normalization"),
        (advanced.toc.enabled, "word.toc"),
        (advanced.numbering.enabled, "word.automatic_numbering"),
        (advanced.cross_references.enabled, "word.cross_references"),
        (advanced.notes.enabled, "word.notes"),
    )
    for enabled, capability in advanced_capabilities:
        if enabled:
            required.add(capability)
    template = rule_pack.template
    if template.fill.values:
        required.add("template.fill")
        required.add("template.placeholders")
    if template.structure.sections or template.structure.even_and_odd_headers is not None:
        required.add("sections.page_numbering")
        required.add("sections.headers_footers")
    required.update(rule_pack.requirements.required_capabilities)
    return required


def evaluate_rule_pack(rule_pack: RulePack) -> RulePackCapabilityReport:
    required = implied_capabilities(rule_pack)
    supported = sorted(
        capability
        for capability in required
        if _BY_ID[capability].status == "supported"
    )
    unsupported = sorted(required - set(supported))
    blockers = [
        *(f"未决要求：{item}" for item in rule_pack.requirements.unresolved),
        *(f"冲突要求：{item}" for item in rule_pack.requirements.conflicts),
        *(f"当前执行器尚不支持：{_BY_ID[item].label}" for item in unsupported),
    ]
    return RulePackCapabilityReport(
        executable=not blockers,
        required=sorted(required),
        supported=supported,
        unsupported=unsupported,
        blockers=blockers,
    )
