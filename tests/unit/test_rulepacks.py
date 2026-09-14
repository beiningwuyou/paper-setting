import json

import pytest
from paper_setting_core.errors import RulePackInvalidError
from paper_setting_core.rulepacks import default_rule_pack, rule_pack_hash
from paper_setting_core.rulepacks.capabilities import implied_capabilities
from paper_setting_core.rulepacks.models import (
    TemplateFillRule,
    TemplateRule,
    TemplateSectionRule,
    TemplateStructureRule,
)
from paper_setting_core.rulepacks.service import parse_rule_pack


def test_default_rule_pack_is_stable() -> None:
    rule_pack = default_rule_pack()
    assert rule_pack.id == "zh-thesis-default"
    assert rule_pack.rule_for("body") is not None
    assert rule_pack_hash(rule_pack) == rule_pack_hash(rule_pack.model_copy(deep=True))


def test_invalid_rule_pack_is_rejected() -> None:
    try:
        parse_rule_pack(b'{"schema_version":"2"}')
    except RulePackInvalidError as error:
        assert error.code == "RULE_PACK_INVALID"
    else:
        raise AssertionError("invalid rule pack should fail")


def test_legacy_line_spacing_defaults_to_multiple() -> None:
    payload = default_rule_pack().model_dump(mode="json")
    body = next(rule for rule in payload["roles"] if rule["role"] == "body")
    body["paragraph"].pop("line_spacing_mode")

    parsed = parse_rule_pack(json.dumps(payload).encode())
    parsed_body = parsed.rule_for("body")

    assert parsed_body is not None
    assert parsed_body.paragraph.line_spacing_mode == "multiple"


def test_line_spacing_mode_requires_value() -> None:
    payload = default_rule_pack().model_dump(mode="json")
    body = next(rule for rule in payload["roles"] if rule["role"] == "body")
    body["paragraph"]["line_spacing"] = None
    body["paragraph"]["line_spacing_mode"] = "exact"

    try:
        parse_rule_pack(json.dumps(payload).encode())
    except RulePackInvalidError as error:
        assert error.code == "RULE_PACK_INVALID"
    else:
        raise AssertionError("line spacing mode without a value should fail")


@pytest.mark.parametrize(
    "page_update",
    [
        {"margin_left_mm": 150, "margin_right_mm": 60},
        {"margin_top_mm": 200, "margin_bottom_mm": 97},
        {
            "orientation": "landscape",
            "margin_left_mm": 160,
            "margin_right_mm": 137,
        },
    ],
)
def test_page_margins_must_leave_positive_content_area(
    page_update: dict[str, object],
) -> None:
    payload = default_rule_pack().model_dump(mode="json")
    payload["page"].update(page_update)

    with pytest.raises(RulePackInvalidError) as captured:
        parse_rule_pack(json.dumps(payload).encode())

    assert captured.value.code == "RULE_PACK_INVALID"


def test_implied_capabilities_omits_template_by_default() -> None:
    required = implied_capabilities(default_rule_pack())
    assert "template.fill" not in required
    assert "sections.page_numbering" not in required
    assert "sections.headers_footers" not in required


def test_implied_capabilities_gates_template_fill() -> None:
    rule_pack = default_rule_pack().model_copy(
        update={"template": TemplateRule(fill=TemplateFillRule(values={"a": "b"}))}
    )
    required = implied_capabilities(rule_pack)
    assert "template.fill" in required
    assert "template.placeholders" in required


def test_implied_capabilities_gates_section_structure() -> None:
    rule_pack = default_rule_pack().model_copy(
        update={
            "template": TemplateRule(
                structure=TemplateStructureRule(
                    sections=[
                        TemplateSectionRule(
                            section_index=1,
                            page_number_format="decimal",
                            page_number_start=1,
                            header_mode="independent_copy",
                        )
                    ],
                    even_and_odd_headers=True,
                )
            )
        }
    )
    required = implied_capabilities(rule_pack)
    assert "sections.page_numbering" in required
    assert "sections.headers_footers" in required


def test_template_section_rule_validates_page_count() -> None:
    payload = default_rule_pack().model_dump(mode="json")
    payload["template"] = {
        "structure": {
            "sections": [
                {
                    "section_index": 1,
                    "page_number_format": "decimal",
                    "page_number_start": 1,
                    "clear_page_numbering": True,
                }
            ]
        }
    }
    try:
        parse_rule_pack(json.dumps(payload).encode())
    except RulePackInvalidError as error:
        assert error.code == "RULE_PACK_INVALID"
    else:
        raise AssertionError("clear_page_numbering with page_number_start should fail")
