from __future__ import annotations

import hashlib
import json
from typing import Any

from paper_setting_core.documents.models import DocumentInspection
from paper_setting_core.errors import CrossReferenceInvalidError
from paper_setting_core.planning.models import PatchOperation, PatchPlan
from paper_setting_core.rulepacks.models import RulePack
from paper_setting_core.rulepacks.policy import FormattingPolicy, resolve_formatting
from paper_setting_core.rulepacks.service import rule_pack_hash


def _operation_id(target_id: str, rule_id: str, after: dict[str, Any]) -> str:
    material = json.dumps([target_id, rule_id, after], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def _plan_version(payload: list[dict[str, object]], source_hash: str, rules_hash: str) -> str:
    material = json.dumps(
        {"source": source_hash, "rules": rules_hash, "operations": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def _values_equal(current: object, target: object) -> bool:
    if isinstance(current, bool) or isinstance(target, bool):
        return current is target
    if isinstance(current, (int, float)) and isinstance(target, (int, float)):
        return abs(float(current) - float(target)) <= 0.05
    if isinstance(current, str) and isinstance(target, str):
        return current.casefold() == target.casefold()
    return current == target


def _changed_fields(
    current: dict[str, Any],
    target: dict[str, Any],
    prefix: str,
) -> list[str]:
    # Word omits zero paragraph spacing in many templates.  An absent
    # w:before/w:after therefore means the same thing as an explicit 0 pt;
    # treating it as a change creates needless direct formatting and makes a
    # template-faithful paragraph look different in Word's formatting pane.
    inherited_zero_fields = {"space_before_pt", "space_after_pt"}
    return [
        f"{prefix}.{name}"
        for name, target_value in target.items()
        if not (
            name in inherited_zero_fields
            and current.get(name) is None
            and _values_equal(target_value, 0)
        )
        and not _values_equal(current.get(name), target_value)
    ]


def _page_comparison_target(page_after: dict[str, Any]) -> dict[str, Any]:
    target = dict(page_after)
    if target.get("orientation") == "landscape" and "width_mm" in target and "height_mm" in target:
        target["width_mm"], target["height_mm"] = target["height_mm"], target["width_mm"]
    return target


def _append_advanced_operations(
    operations: list[PatchOperation],
    counts: dict[str, int],
    inspection: DocumentInspection,
    rule_pack: RulePack,
) -> None:
    advanced = rule_pack.advanced
    current = inspection.advanced
    if advanced.formula.enabled and current.formula_count:
        style_value = {
            "plain": "p",
            "italic": "i",
            "bold": "b",
            "bold_italic": "bi",
        }.get(advanced.formula.style)
        style_matches = style_value is None or current.formula_styles == [style_value]
        if current.formula_math_font != advanced.formula.math_font or not style_matches:
            after = advanced.formula.model_dump(mode="json")
            operations.append(
                PatchOperation(
                    operation_id=_operation_id("document:formulas", "advanced.formula", after),
                    target_id="document:formulas",
                    rule_id="advanced.formula",
                    semantic_role="formula",
                    operation_type="reformat_formulas",
                    before={
                        "count": current.formula_count,
                        "math_font": current.formula_math_font,
                        "styles": current.formula_styles,
                    },
                    after=after,
                    text_preview=f"{current.formula_count} 个 OMML 公式",
                    precondition_hash=inspection.source_sha256,
                    risk="high",
                    confidence=1.0,
                    status="manual_review",
                    execution_scope="controlled_ooxml_rewrite",
                    changed_fields=["formula.math_font", "formula.style"],
                    reasons=["重构公式运行属性，保留公式文本和 OMML 结构"],
                )
            )
            counts["manual_review"] += 1

    if advanced.citations.enabled and current.citation_candidate_count:
        after = advanced.citations.model_dump(mode="json")
        operations.append(
            PatchOperation(
                operation_id=_operation_id("document:citations", "advanced.citations", after),
                target_id="document:citations",
                rule_id="advanced.citations",
                semantic_role="citations",
                operation_type="normalize_citations",
                before={"candidate_count": current.citation_candidate_count},
                after=after,
                text_preview=f"{current.citation_candidate_count} 处数字引用可规范化",
                precondition_hash=inspection.source_sha256,
                risk="high",
                confidence=1.0,
                status="manual_review",
                execution_scope="controlled_ooxml_rewrite",
                changed_fields=["citations.numeric_brackets"],
                reasons=["仅规范化明确的数字引用，不猜测作者、年份或文献语义"],
            )
        )
        counts["manual_review"] += 1

    if advanced.toc.enabled:
        level_switch = f'\\o "{advanced.toc.min_level}-{advanced.toc.max_level}"'
        toc_matches = any(
            level_switch in instruction and "TOC" in instruction.upper()
            for instruction in current.toc_instructions
        )
        update_matches = not advanced.toc.update_on_open or current.update_fields_on_open
        if not toc_matches or not update_matches:
            after = advanced.toc.model_dump(mode="json")
            operations.append(
                PatchOperation(
                    operation_id=_operation_id("document:toc", "advanced.toc", after),
                    target_id="document:toc",
                    rule_id="advanced.toc",
                    semantic_role="toc",
                    operation_type="rebuild_toc",
                    before={
                        "instructions": current.toc_instructions,
                        "update_on_open": current.update_fields_on_open,
                    },
                    after=after,
                    text_preview="重建 Word 目录域并绑定标题大纲级别",
                    precondition_hash=inspection.source_sha256,
                    risk="high",
                    confidence=1.0,
                    status="manual_review",
                    execution_scope="controlled_ooxml_rewrite",
                    changed_fields=["toc.field", "toc.outline_levels", "toc.update_on_open"],
                    reasons=["页码将由 Word 或 LibreOffice 打开文档时更新"],
                )
            )
            counts["manual_review"] += 1

    if advanced.numbering.enabled:
        target_roles: list[str] = []
        if advanced.numbering.headings:
            target_roles.extend(["heading_1", "heading_2", "heading_3"])
        if advanced.numbering.bibliography:
            target_roles.append("reference_entry")
        if advanced.numbering.captions:
            target_roles.extend(["figure_caption", "table_caption"])
        expected = {role: inspection.summary.role_counts.get(role, 0) for role in target_roles}
        effectively_numbered = dict(current.numbered_role_counts)
        for role, count in current.sequence_numbered_role_counts.items():
            effectively_numbered[role] = effectively_numbered.get(role, 0) + count
        if advanced.cross_references.enabled:
            for kind, role in (
                ("figure", "figure_caption"),
                ("table", "table_caption"),
            ):
                effectively_numbered[role] = effectively_numbered.get(role, 0) + (
                    current.cross_reference_target_counts.get(kind, 0)
                )
        needs_numbering = any(
            effectively_numbered.get(role, 0) < count for role, count in expected.items()
        )
        if needs_numbering:
            after = advanced.numbering.model_dump(mode="json")
            after["exclude_cross_reference_targets"] = advanced.cross_references.enabled
            operations.append(
                PatchOperation(
                    operation_id=_operation_id("document:numbering", "advanced.numbering", after),
                    target_id="document:numbering",
                    rule_id="advanced.numbering",
                    semantic_role="numbering",
                    operation_type="apply_automatic_numbering",
                    before={
                        "expected": expected,
                        "numbered": current.numbered_role_counts,
                        "sequence_numbered": current.sequence_numbered_role_counts,
                        "cross_reference_targets": current.cross_reference_target_counts,
                    },
                    after=after,
                    text_preview=("一至三级标题、图表题与参考文献使用 Word 动态编号"),
                    precondition_hash=inspection.source_sha256,
                    risk="high",
                    confidence=1.0,
                    status="manual_review",
                    execution_scope="controlled_ooxml_rewrite",
                    changed_fields=["numbering.definitions", "numbering.paragraph_bindings"],
                    reasons=[
                        "已有文本编号可移除，编号改由 Word 列表定义管理",
                        "显式交叉引用目标由 SEQ 字段编号，不重复绑定列表编号",
                    ],
                )
            )
            counts["manual_review"] += 1

    cross_reference_work = (
        current.cross_reference_target_count > 0
        or current.cross_reference_marker_count > 0
        or current.cross_reference_page_marker_count > 0
        or bool(current.cross_reference_issues)
    )
    if advanced.cross_references.enabled and cross_reference_work:
        if current.cross_reference_issues:
            raise CrossReferenceInvalidError("；".join(current.cross_reference_issues))
        after = advanced.cross_references.model_dump(mode="json")
        operations.append(
            PatchOperation(
                operation_id=_operation_id(
                    "document:cross-references",
                    "advanced.cross_references",
                    after,
                ),
                target_id="document:cross-references",
                rule_id="advanced.cross_references",
                semantic_role="cross_references",
                operation_type="create_cross_references",
                before={
                    "targets": current.cross_reference_target_count,
                    "references": current.cross_reference_marker_count,
                    "page_references": current.cross_reference_page_marker_count,
                    "existing_fields": current.cross_reference_existing_field_count,
                },
                after=after,
                text_preview=(
                    f"为 {current.cross_reference_target_count} 个图表题注创建书签，"
                    f"写入 {current.cross_reference_marker_count} 个 REF 和 "
                    f"{current.cross_reference_page_marker_count} 个 PAGEREF 字段"
                ),
                precondition_hash=inspection.source_sha256,
                risk="high",
                confidence=1.0,
                status="manual_review",
                execution_scope="controlled_ooxml_rewrite",
                changed_fields=[
                    "cross_references.seq_fields",
                    "cross_references.bookmarks",
                    "cross_references.ref_fields",
                    "cross_references.pageref_fields",
                ],
                reasons=[
                    "只处理显式 xref 标记，不猜测正文中的图表语义",
                    "目标键唯一且每个引用都已解析",
                    "Word 或 LibreOffice 打开文档时更新字段结果",
                ],
            )
        )
        counts["manual_review"] += 1

    note_work = (
        (advanced.notes.convert_inline_citations and current.inline_note_candidate_count > 0)
        or (advanced.notes.convert_endnotes and current.endnote_count > 0)
        or (advanced.notes.delete_bibliography and current.bibliography_entry_count > 0)
        or any(
            value != advanced.notes.numbering_restart
            for value in current.footnote_numbering_restarts
        )
        or any(value != advanced.notes.number_format for value in current.footnote_number_formats)
    )
    if advanced.notes.enabled and note_work:
        after = advanced.notes.model_dump(mode="json")
        operations.append(
            PatchOperation(
                operation_id=_operation_id("document:notes", "advanced.notes", after),
                target_id="document:notes",
                rule_id="advanced.notes",
                semantic_role="notes",
                operation_type="convert_notes_to_footnotes",
                before={
                    "footnotes": current.footnote_count,
                    "endnotes": current.endnote_count,
                    "inline_citations": current.inline_note_candidate_count,
                    "bibliography_entries": current.bibliography_entry_count,
                    "numbering_restarts": current.footnote_numbering_restarts,
                    "number_formats": current.footnote_number_formats,
                },
                after=after,
                text_preview=(
                    f"将 {current.inline_note_candidate_count} 处正文引注及 "
                    f"{current.endnote_count} 条尾注转换为脚注"
                    + (
                        f"，并删除文末 {current.bibliography_entry_count} 条参考文献"
                        if advanced.notes.delete_bibliography
                        else ""
                    )
                ),
                precondition_hash=inspection.source_sha256,
                risk="high",
                confidence=1.0,
                status="manual_review",
                execution_scope="controlled_ooxml_rewrite",
                changed_fields=[
                    "notes.inline_citations",
                    "notes.endnotes",
                    "notes.bibliography",
                    "notes.numbering_restart",
                    "notes.number_format",
                ],
                reasons=[
                    "正文数字引注将变为真实 Word 脚注，内容取自对应参考文献条目",
                    (
                        "脚注编号按页重新从 1 开始，并使用带圈数字格式"
                        if advanced.notes.numbering_restart == "each_page"
                        and advanced.notes.number_format == "decimal_enclosed_circle"
                        else "脚注编号重启方式和编号格式按规则包统一设置"
                    ),
                    "该操作会改变注释结构并可能删除文末参考文献，必须明确确认",
                ],
            )
        )
        counts["manual_review"] += 1


def generate_plan(
    inspection: DocumentInspection,
    rule_pack: RulePack,
    formatting_policy: FormattingPolicy | None = None,
) -> PatchPlan:
    original_rule_pack = rule_pack
    field_sources: dict[str, dict[str, str]] = {}
    page_after = rule_pack.page.model_dump(mode="json")
    if formatting_policy is not None:
        rule_pack, page_after, field_sources = resolve_formatting(rule_pack, formatting_policy)
    operations: list[PatchOperation] = []
    counts = {status: 0 for status in ["proposed", "manual_review", "compliant"]}
    page_target = "sections:all"
    comparison_target = _page_comparison_target(page_after)
    section_changes: list[str] = []
    for section in inspection.sections:
        current = section.model_dump(mode="json", exclude={"section_index"})
        section_changes.extend(
            _changed_fields(current, comparison_target, f"section[{section.section_index}]")
        )
    if section_changes:
        operations.append(
            PatchOperation(
                operation_id=_operation_id(page_target, "page.default", page_after),
                target_id=page_target,
                rule_id="page.default",
                semantic_role="page",
                operation_type="apply_page_format",
                before={
                    "sections": [section.model_dump(mode="json") for section in inspection.sections]
                },
                after=page_after,
                field_sources=field_sources.get("page", {}),
                precondition_hash=inspection.source_sha256,
                confidence=1.0,
                status="proposed",
                changed_fields=section_changes,
                reasons=[f"页面设置有 {len(section_changes)} 处需按有效排版配置调整"],
            )
        )
        counts["proposed"] += 1
    elif page_after:
        counts["compliant"] += 1
    uncovered_roles: set[str] = set()
    for item in inspection.items:
        if item.semantic_role == "empty" or item.story in {"header", "footer"}:
            continue
        rule = rule_pack.rule_for(item.semantic_role)
        if rule is None:
            uncovered_roles.add(item.semantic_role)
            continue
        after: dict[str, Any] = {
            "style_name": f"PaperSetting.{item.semantic_role}",
            "paragraph": rule.paragraph.model_dump(mode="json", exclude_none=True),
            "character": rule.character.model_dump(mode="json", exclude_none=True),
        }
        if rule.preserve_style_identity:
            after["preserve_style_identity"] = True
        if formatting_policy is not None:
            # Keep original style inheritance for all unspecified/semantic fields.
            after["preserve_original_style"] = True
            after["style_name"] = (
                item.style_name
                if (item.style_name or "").startswith("PaperSetting.")
                else f"PaperSetting.{item.semantic_role}.{item.style_id}"
            )
        paragraph_changes = _changed_fields(
            item.effective_format.paragraph,
            after["paragraph"],
            "paragraph",
        )
        character_changes = _changed_fields(
            item.effective_format.character,
            after["character"],
            "character",
        )
        changed_fields = paragraph_changes + character_changes
        if not changed_fields:
            counts["compliant"] += 1
            continue
        status = "proposed"
        risk = "low"
        execution_scope = "full"
        reasons = [
            rule.description,
            f"{len(changed_fields)} 个格式属性需要调整",
            f"分类置信度 {item.confidence:.2f}",
        ]
        if item.risks.protected:
            status = "manual_review"
            risk = "high"
            execution_scope = "preserve_protected_content"
            reasons.append("目标包含受保护的 Word 对象")
            reasons.append("可安全执行：保留对象 XML，仅调整段落、样式和普通文字")
        elif item.confidence < rule.min_confidence:
            status = "manual_review"
            risk = "medium"
            reasons.append(f"低于自动执行阈值 {rule.min_confidence:.2f}")
        operations.append(
            PatchOperation(
                operation_id=_operation_id(item.stable_id, rule.id, after),
                target_id=item.stable_id,
                rule_id=rule.id,
                semantic_role=item.semantic_role,
                operation_type="apply_role_format",
                before={
                    "style_id": item.style_id,
                    "style_name": item.style_name,
                    "paragraph": item.effective_format.paragraph,
                    "character": item.effective_format.character,
                },
                after=after,
                field_sources=field_sources.get(item.semantic_role, {}),
                text_preview=item.text_preview,
                precondition_hash=item.exact_text_hash,
                risk=risk,
                confidence=item.confidence,
                status=status,
                execution_scope=execution_scope,
                changed_fields=changed_fields,
                reasons=reasons,
            )
        )
        counts[status] += 1
    _append_advanced_operations(operations, counts, inspection, rule_pack)
    for operation in operations:
        if operation.execution_scope == "controlled_ooxml_rewrite":
            operation.field_sources = dict.fromkeys(operation.changed_fields, "rule_pack")
    rules_hash = rule_pack_hash(original_rule_pack)
    operation_payload = [operation.model_dump(mode="json") for operation in operations]
    version_hash = rules_hash
    if formatting_policy is not None:
        version_hash = hashlib.sha256(
            (rules_hash + formatting_policy.model_dump_json()).encode()
        ).hexdigest()
    return PatchPlan(
        source_sha256=inspection.source_sha256,
        rule_pack_id=rule_pack.id,
        rule_pack_version=rule_pack.version,
        rule_pack_hash=rules_hash,
        plan_version=_plan_version(operation_payload, inspection.source_sha256, version_hash),
        operations=operations,
        summary=counts,
        formatting_policy=formatting_policy,
        uncovered_roles=sorted(uncovered_roles),
        notices=(
            ["过渡基线复用现有通用格式，正式默认模板尚未选定。"]
            if formatting_policy and formatting_policy.baseline_status == "provisional"
            else []
        )
        + (
            ["未覆盖角色保留原格式，请人工复核：" + "、".join(sorted(uncovered_roles))]
            if uncovered_roles
            else []
        ),
    )
