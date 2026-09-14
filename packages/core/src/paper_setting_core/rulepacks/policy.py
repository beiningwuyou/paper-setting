"""Versioned formatting baseline, independent of institution rule packs.

Only non-null, explicit rule values override the baseline. The policy is snapshotted
with each job so replacing the baseline cannot change an approved plan.
"""

from typing import Literal

from pydantic import BaseModel

from paper_setting_core.rulepacks.defaults import default_rule_pack
from paper_setting_core.rulepacks.models import RulePack

FormattingMode = Literal["standardize", "preserve"]


class FormattingPolicy(BaseModel):
    mode: FormattingMode = "standardize"
    baseline: RulePack | None = None
    baseline_status: Literal["provisional", "configured", "not_used"] = "not_used"


def default_formatting_policy(mode: FormattingMode = "standardize") -> FormattingPolicy:
    if mode == "preserve":
        return FormattingPolicy(mode=mode)
    baseline = default_rule_pack()
    baseline.id = "workbench-baseline-provisional"
    baseline.name = "工作台过渡基线（非最终模板）"
    baseline.description = "复用现有通用格式；正式默认模板待配置。"
    # Table interiors are deliberately not normalized by the provisional baseline.
    baseline.roles = [rule for rule in baseline.roles if rule.role != "table_body"]
    for rule in baseline.roles:
        rule.character.color = "000000"
        rule.character.italic = False
        rule.character.underline = False
        if rule.character.bold is None:
            rule.character.bold = False
        for key, value in {
            "left_indent_pt": 0,
            "right_indent_pt": 0,
            "first_line_indent_pt": 0,
            "space_before_pt": 0,
            "space_after_pt": 0,
            "line_spacing": 1.5,
            "line_spacing_mode": "multiple",
        }.items():
            if getattr(rule.paragraph, key) is None:
                setattr(rule.paragraph, key, value)
    return FormattingPolicy(mode=mode, baseline=baseline, baseline_status="provisional")


def resolve_formatting(rule_pack: RulePack, policy: FormattingPolicy):
    """Return effective rules and property-level provenance without mutating inputs."""
    effective = rule_pack.model_copy(deep=True)
    baseline = policy.baseline if policy.mode == "standardize" else None
    sources: dict[str, dict[str, str]] = {}
    page = baseline.page.model_dump() if baseline else {}
    page_sources = {key: "default_template" for key in page}
    explicit = rule_pack.explicit_page_fields
    for key in explicit if explicit is not None else type(rule_pack.page).model_fields:
        page[key] = getattr(rule_pack.page, key)
        page_sources[key] = "rule_pack"
    sources["page"] = page_sources
    roles = {rule.role: rule.model_copy(deep=True) for rule in baseline.roles} if baseline else {}
    for role, rule in roles.items():
        sources[role] = {
            f"{group}.{key}": "default_template"
            for group in ("paragraph", "character")
            for key in getattr(rule, group).model_dump(exclude_none=True)
        }
    for rule in rule_pack.roles:
        base = roles.get(rule.role)
        merged = rule.model_copy(deep=True)
        sources.setdefault(rule.role, {})
        for group in ("paragraph", "character"):
            values = getattr(base, group).model_dump(exclude_none=True) if base else {}
            explicit_values = getattr(rule, group).model_dump(exclude_none=True)
            values.update(explicit_values)
            setattr(merged, group, type(getattr(rule, group)).model_validate(values))
            sources[rule.role].update({f"{group}.{key}": "rule_pack" for key in explicit_values})
        roles[rule.role] = merged
    effective.roles = list(roles.values())
    return effective, page, sources
