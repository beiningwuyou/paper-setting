from __future__ import annotations

import hashlib
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, cast

from docx import Document

from paper_setting_core.documents.safety import validate_docx_bytes
from paper_setting_core.errors import AppError, RuleSourceInvalidError
from paper_setting_core.rulepacks.capabilities import evaluate_rule_pack
from paper_setting_core.rulepacks.models import (
    AdvancedWordFormat,
    CharacterFormat,
    NotesFormat,
    PageFormat,
    ParagraphFormat,
    RequirementSource,
    RoleRule,
    RuleEvidence,
    RulePack,
    RulePackDraft,
    RuleRequirements,
)

MAX_SOURCE_CHARACTERS = 200_000
SourceFormat = Literal["text", "txt", "md", "docx", "mixed"]

ROLE_ALIASES: dict[str, tuple[str, ...]] = {
    "paper_title": ("论文题目", "论文标题", "封面题目", "题目"),
    "abstract_heading": ("摘要标题",),
    "abstract_body": ("摘要正文", "中文摘要"),
    "keywords": ("关键词", "关键字"),
    "heading_1": ("一级标题", "章标题"),
    "heading_2": ("二级标题", "节标题"),
    "heading_3": ("三级标题", "小节标题"),
    "body": ("正文文本", "普通正文", "正文"),
    "figure_caption": ("图片标题", "图题", "图注"),
    "table_caption": ("表格标题", "表题", "表注"),
    "bibliography_heading": ("参考文献标题",),
    "reference_entry": ("参考文献条目", "参考文献正文", "参考文献"),
    "table_body": ("表格正文", "表内文字", "表格文字"),
}

ROLE_META: dict[str, tuple[str, str]] = {
    "paper_title": ("title.paper", "论文标题"),
    "abstract_heading": ("abstract.heading", "摘要标题"),
    "abstract_body": ("abstract.body", "摘要正文"),
    "keywords": ("keywords", "关键词"),
    "heading_1": ("heading.1", "一级标题"),
    "heading_2": ("heading.2", "二级标题"),
    "heading_3": ("heading.3", "三级标题"),
    "body": ("body.normal", "正文"),
    "figure_caption": ("caption.figure", "图题"),
    "table_caption": ("caption.table", "表题"),
    "bibliography_heading": ("references.heading", "参考文献标题"),
    "reference_entry": ("references.entry", "参考文献条目"),
    "table_body": ("table.body", "表格正文"),
}

CHINESE_FONT_SIZES = {
    "小初": 36.0,
    "小一": 24.0,
    "小二": 18.0,
    "小三": 15.0,
    "小四": 12.0,
    "小五": 9.0,
    "小六": 6.5,
    "初号": 42.0,
    "一号": 26.0,
    "二号": 22.0,
    "三号": 16.0,
    "四号": 14.0,
    "五号": 10.5,
    "六号": 7.5,
    "七号": 5.5,
    "八号": 5.0,
}

EAST_ASIA_FONTS = (
    "方正小标宋简体",
    "方正小标宋",
    "方正黑体",
    "仿宋_GB2312",
    "微软雅黑",
    "华文仿宋",
    "华文宋体",
    "华文黑体",
    "仿宋",
    "楷体",
    "宋体",
    "黑体",
)

LATIN_FONTS = ("Times New Roman", "Arial", "Calibri", "Cambria")
MEASUREMENT = r"(\d+(?:\.\d+)?)\s*(磅|pt|厘米|cm|毫米|mm)"


def read_rule_source_file(filename: str, payload: bytes) -> tuple[str, SourceFormat]:
    suffix = Path(filename).suffix.casefold()
    if suffix in {".txt", ".md"}:
        try:
            text = payload.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise RuleSourceInvalidError("文本文件必须使用 UTF-8 编码") from exc
        return text, cast(SourceFormat, suffix[1:])
    if suffix == ".docx":
        try:
            validate_docx_bytes(payload)
            document = Document(BytesIO(payload))
            lines = [
                "".join(node.text or "" for node in paragraph.iter() if node.tag.endswith("}t"))
                for paragraph in document.element.body.iter()
                if paragraph.tag.endswith("}p")
            ]
        except AppError as exc:
            raise RuleSourceInvalidError(exc.detail) from exc
        except Exception as exc:
            raise RuleSourceInvalidError("无法读取 DOCX 规范文件") from exc
        return "\n".join(line for line in lines if line.strip()), "docx"
    raise RuleSourceInvalidError("仅支持 .txt、.md 和 .docx 规范文件")


def _clean_line(line: str) -> str:
    return re.sub(r"^[\s#>*|\-\d.()（）]+", "", line).strip().strip("|").strip()


def _match_role(line: str) -> tuple[str | None, str]:
    candidates = sorted(
        ((alias, role) for role, aliases in ROLE_ALIASES.items() for alias in aliases),
        key=lambda item: len(item[0]),
        reverse=True,
    )
    for alias, role in candidates:
        match = re.match(rf"^{re.escape(alias)}\s*(?:格式|要求)?\s*[：:|]?\s*(.*)$", line)
        if match:
            return role, match.group(1).strip().strip("|").strip()
    return None, line


def _to_points(value: float, unit: str) -> float:
    if unit.casefold() in {"磅", "pt"}:
        return round(value, 3)
    if unit.casefold() in {"厘米", "cm"}:
        return round(value * 72 / 2.54, 3)
    return round(value * 72 / 25.4, 3)


def _to_mm(value: float, unit: str) -> float:
    if unit.casefold() in {"厘米", "cm"}:
        return round(value * 10, 3)
    if unit.casefold() in {"毫米", "mm"}:
        return round(value, 3)
    return round(value * 25.4 / 72, 3)


def _measurement(text: str, label: str) -> tuple[float, str] | None:
    match = re.search(rf"(?:{label})\s*(?:为|[:：])?\s*{MEASUREMENT}", text, re.I)
    return (float(match.group(1)), match.group(2)) if match else None


def extract_rule_pack_draft(
    text: str,
    *,
    source_filename: str | None = None,
    source_format: SourceFormat = "text",
    rule_pack_id: str | None = None,
    name: str | None = None,
) -> RulePackDraft:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        raise RuleSourceInvalidError("请粘贴规范文本或上传规范文件")
    if len(normalized) > MAX_SOURCE_CHARACTERS:
        raise RuleSourceInvalidError(f"规范文本超过 {MAX_SOURCE_CHARACTERS} 字符限制")

    evidence: list[RuleEvidence] = []
    handled_lines: set[int] = set()
    page_values: dict[str, Any] = {}
    role_values: dict[str, dict[str, dict[str, Any]]] = {}
    notes_values: dict[str, Any] = {}
    current_role: str | None = None

    def record(
        role: str,
        path: str,
        value: str | float | bool,
        line_number: int,
        quote: str,
        confidence: float = 0.98,
    ) -> None:
        if any(
            item.role == role
            and item.property_path == path
            and item.value == value
            and item.source_line == line_number
            for item in evidence
        ):
            return
        evidence.append(
            RuleEvidence(
                role=role,
                property_path=path,
                value=value,
                source_line=line_number,
                quote=quote[:240],
                confidence=confidence,
            )
        )
        handled_lines.add(line_number)

    def set_page(path: str, value: str | float, line_number: int, quote: str) -> None:
        page_values[path] = value
        record("page", f"page.{path}", value, line_number, quote)

    def set_role(
        role: str,
        group: str,
        path: str,
        value: str | float | bool,
        line_number: int,
        quote: str,
        confidence: float = 0.98,
    ) -> None:
        values = role_values.setdefault(role, {"paragraph": {}, "character": {}})
        values[group][path] = value
        record(role, f"{group}.{path}", value, line_number, quote, confidence)

    def set_notes(path: str, value: str | bool, line_number: int, quote: str) -> None:
        notes_values["enabled"] = True
        notes_values[path] = value
        record("notes", f"advanced.notes.{path}", value, line_number, quote)

    raw_lines = [line for line in normalized.split("\n") if line.strip()]
    for line_number, raw_line in enumerate(raw_lines, start=1):
        line = _clean_line(raw_line)
        if not line:
            continue

        if re.search(r"\bA4\b|A4纸", line, re.I):
            set_page("width_mm", 210.0, line_number, line)
            set_page("height_mm", 297.0, line_number, line)
        if "横向" in line:
            set_page("orientation", "landscape", line_number, line)
        elif "纵向" in line:
            set_page("orientation", "portrait", line_number, line)

        for label, paths in {
            "上下页边距|上下边距": ("margin_top_mm", "margin_bottom_mm"),
            "左右页边距|左右边距": ("margin_left_mm", "margin_right_mm"),
        }.items():
            found = _measurement(line, label)
            if found:
                value = _to_mm(*found)
                for path in paths:
                    set_page(path, value, line_number, line)
        for path, label in {
            "margin_top_mm": "上页边距|上边距",
            "margin_bottom_mm": "下页边距|下边距",
            "margin_left_mm": "左页边距|左边距",
            "margin_right_mm": "右页边距|右边距",
            "header_distance_mm": "页眉距离|页眉",
            "footer_distance_mm": "页脚距离|页脚",
        }.items():
            found = _measurement(line, label)
            if found:
                set_page(path, _to_mm(*found), line_number, line)

        notes_as_footnotes = bool(
            re.search(
                r"(?:所有|全部|一律|统一)?(?:注释|注解|引注|引用|尾注)"
                r".{0,12}(?:改|转|转换|采用|使用|置于|作为).{0,6}脚注|"
                r"脚注.{0,12}(?:替代|取代)(?:尾注|文末注|注释)",
                line,
            )
        )
        if notes_as_footnotes:
            set_notes("convert_inline_citations", True, line_number, line)
            set_notes("convert_endnotes", True, line_number, line)
        if re.search(
            r"(?:删除|删去|移除|不保留|取消|不列|不再列)(?:最后的|文末的|末尾的)?"
            r"参考文献|(?:最后|文末|末尾)(?:不列|不保留|删除)参考文献",
            line,
        ):
            set_notes("delete_bibliography", True, line_number, line)
        if re.search(
            r"(?:每页|逐页).{0,8}(?:脚注|注释).{0,8}(?:重新|重置|从头)(?:编号|计数)|"
            r"(?:脚注|注释).{0,8}(?:每页|逐页).{0,8}(?:重新|重置|从头)(?:编号|计数)",
            line,
        ):
            set_notes("numbering_restart", "each_page", line_number, line)
        if re.search(
            r"(?:编号|序号|号码)(?:格式)?(?:为|采用|使用|：|:)?(?:带圈|加圈|圈号|圆圈)"
            r"(?:数字|数码|号码)?|(?:带圈|加圈|圈号|圆圈)(?:数字|数码)(?:编号|序号)?",
            line,
        ):
            set_notes("number_format", "decimal_enclosed_circle", line_number, line)

        matched_role, role_text = _match_role(line)
        if matched_role is not None:
            current_role = matched_role
            handled_lines.add(line_number)
        if current_role is None:
            continue
        content = role_text if matched_role is not None else line

        for font_name in EAST_ASIA_FONTS:
            if font_name.casefold() in content.casefold():
                set_role(
                    current_role, "character", "east_asia_font", font_name, line_number, line
                )
                break
        for font_name in LATIN_FONTS:
            if font_name.casefold() in content.casefold():
                set_role(current_role, "character", "latin_font", font_name, line_number, line)
                break

        size_found = False
        for size_name, size_pt in CHINESE_FONT_SIZES.items():
            if size_name in content:
                set_role(current_role, "character", "size_pt", size_pt, line_number, line)
                size_found = True
                break
        if not size_found:
            numeric_size = re.search(rf"字号\s*(?:为|[:：])?\s*{MEASUREMENT}", content, re.I)
            if numeric_size:
                set_role(
                    current_role,
                    "character",
                    "size_pt",
                    _to_points(float(numeric_size.group(1)), numeric_size.group(2)),
                    line_number,
                    line,
                )

        if "不加粗" in content or "非粗体" in content:
            set_role(current_role, "character", "bold", False, line_number, line)
        elif "加粗" in content or "粗体" in content:
            set_role(current_role, "character", "bold", True, line_number, line)
        if "不斜体" in content or "非斜体" in content or "取消斜体" in content:
            set_role(current_role, "character", "italic", False, line_number, line)
        elif "斜体" in content:
            set_role(current_role, "character", "italic", True, line_number, line)
        if "无下划线" in content or "不加下划线" in content or "取消下划线" in content:
            set_role(current_role, "character", "underline", False, line_number, line)
        elif "下划线" in content:
            set_role(current_role, "character", "underline", True, line_number, line)
        color_match = re.search(r"#?([0-9A-Fa-f]{6})", content)
        if color_match:
            set_role(
                current_role,
                "character",
                "color",
                color_match.group(1).upper(),
                line_number,
                line,
            )

        for keyword, alignment in {
            "两端对齐": "justify",
            "居中对齐": "center",
            "居中": "center",
            "左对齐": "left",
            "右对齐": "right",
        }.items():
            if keyword in content:
                set_role(
                    current_role, "paragraph", "alignment", alignment, line_number, line
                )
                break

        point_size = role_values.get(current_role, {}).get("character", {}).get("size_pt", 12.0)
        indent = re.search(
            r"首行缩进\s*(?:为|[:：])?\s*(\d+(?:\.\d+)?)\s*"
            r"(字符|个字|字|磅|pt|厘米|cm|毫米|mm)",
            content,
            re.I,
        )
        if indent:
            indent_value = float(indent.group(1))
            indent_unit = indent.group(2)
            is_character_unit = indent_unit in {"字符", "个字", "字"}
            indent_pt = (
                round(indent_value * float(point_size), 3)
                if is_character_unit
                else _to_points(indent_value, indent_unit)
            )
            set_role(
                current_role,
                "paragraph",
                "first_line_indent_pt",
                indent_pt,
                line_number,
                line,
                0.96 if is_character_unit else 0.99,
            )

        for path, label in {
            "left_indent_pt": "左缩进",
            "right_indent_pt": "右缩进",
            "space_before_pt": "段前(?:间距)?",
            "space_after_pt": "段后(?:间距)?",
        }.items():
            found = _measurement(content, label)
            if found:
                set_role(
                    current_role,
                    "paragraph",
                    path,
                    _to_points(*found),
                    line_number,
                    line,
                )

        exact = re.search(
            rf"(?:固定值|固定行距)\s*(?:为|[:：])?\s*{MEASUREMENT}", content, re.I
        )
        at_least = re.search(
            rf"(?:最小值|最小行距|至少)\s*(?:为|[:：])?\s*{MEASUREMENT}", content, re.I
        )
        multiple = re.search(r"(\d+(?:\.\d+)?)\s*倍(?:行距)?", content)
        if exact or at_least:
            match = exact or at_least
            assert match is not None
            set_role(
                current_role,
                "paragraph",
                "line_spacing",
                _to_points(float(match.group(1)), match.group(2)),
                line_number,
                line,
            )
            set_role(
                current_role,
                "paragraph",
                "line_spacing_mode",
                "exact" if exact else "at_least",
                line_number,
                line,
            )
        elif multiple or "单倍行距" in content or "双倍行距" in content:
            spacing = (
                float(multiple.group(1))
                if multiple
                else (1.0 if "单倍行距" in content else 2.0)
            )
            set_role(
                current_role, "paragraph", "line_spacing", spacing, line_number, line
            )
            set_role(
                current_role,
                "paragraph",
                "line_spacing_mode",
                "multiple",
                line_number,
                line,
            )

        for keyword, path in {
            "与下段同页": "keep_with_next",
            "段中不分页": "keep_together",
            "段前分页": "page_break_before",
        }.items():
            if keyword in content:
                set_role(current_role, "paragraph", path, True, line_number, line)

    if not evidence:
        raise RuleSourceInvalidError(
            "未识别到可用的排版规则；请使用‘正文：宋体，小四，1.5 倍行距’类似表述"
        )

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:10]
    normalized_id = re.sub(r"[^a-z0-9-]+", "-", (rule_pack_id or "").casefold()).strip("-")
    normalized_id = normalized_id or f"imported-rules-{digest}"
    display_name = (name or "").strip() or (
        f"{Path(source_filename).stem} 排版规则" if source_filename else "导入的论文排版规则"
    )
    source_label = source_filename or "粘贴文本"
    roles = [
        RoleRule(
            id=ROLE_META[role][0],
            role=role,
            description=ROLE_META[role][1],
            source=f"从 {source_label} 确定性提取",
            paragraph=ParagraphFormat.model_validate(values["paragraph"]),
            character=CharacterFormat.model_validate(values["character"]),
        )
        for role, values in role_values.items()
    ]
    if not roles:
        roles.append(
            RoleRule(
                id="body.noop",
                role="body",
                description="未指定段落规则，仅应用页面设置",
                source=f"从 {source_label} 确定性提取",
            )
        )

    warnings: list[str] = []
    if set(page_values) != set(PageFormat.model_fields):
        warnings.append(
            "规范未完整描述所有页面字段；未提及项由排版模式决定：标准化时用默认基线，保守时保留原文。"
        )
    if role_values:
        missing_roles = len(ROLE_META) - len(role_values)
        if missing_roles:
            warnings.append(
                f"仅生成了规范明确提及的 {len(role_values)} 个语义角色；"
                f"其余 {missing_roles} 个角色由默认基线补全，保守模式则保留原文。"
            )
    elif not notes_values:
        warnings.append("只识别到页面设置，该规则包不会修改段落和字符格式。")
    if notes_values:
        warnings.append(
            "已识别注释/脚注结构规则；转换引注或删除文末参考文献属于高风险操作，"
            "执行前需在工作台明确确认。"
        )
    unrecognized = sum(
        1
        for index, raw_line in enumerate(raw_lines, start=1)
        if _clean_line(raw_line) and index not in handled_lines
    )
    if unrecognized:
        warnings.append(f"有 {unrecognized} 行文本未识别为支持的排版属性。")

    rule_pack = RulePack(
        schema_version="2.0",
        id=normalized_id,
        name=display_name[:100],
        version="1.0.0",
        description=f"由 Paper Setting 从 {source_label} 生成；导入前应人工复核。",
        requirements=RuleRequirements(
            sources=[
                RequirementSource(
                    kind="docx" if source_format == "docx" else "text",
                    label=source_label,
                )
            ]
        ),
        page=PageFormat.model_validate(page_values),
        explicit_page_fields=list(page_values),
        roles=roles,
        advanced=AdvancedWordFormat(
            notes=NotesFormat.model_validate(notes_values) if notes_values else NotesFormat()
        ),
    )
    return RulePackDraft(
        rule_pack=rule_pack,
        evidence=evidence,
        warnings=warnings,
        source_filename=source_filename,
        source_format=source_format,
        recognized_properties=len(evidence),
        unrecognized_lines=unrecognized,
        capability_report=evaluate_rule_pack(rule_pack),
    )
