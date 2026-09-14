"""Test Detailed Mode Agent Rule Extractor and AI QA Audit."""

from __future__ import annotations

from pathlib import Path
from server.agent_service import extract_rules_from_text, run_ai_qa_audit
from server.sample_generator import generate_sample_thesis
from server.engine import analyze_document_detailed, apply_document_detailed


def test_agent_rule_extraction():
    notice = (
        "各学院请注意：今年本科学位论文正文请统一采用仿宋字体，行间距设置为 1.5 倍行距。"
        "页边距要求：上边距 2.8cm，下边距 2.5cm，左边距 3.0cm，右边距 2.5cm。"
        "文中有参考文献引用处需采用页下脚注形式。"
    )

    draft = extract_rules_from_text(notice)
    assert draft["confidence"] >= 0.9
    assert draft["typography"]["body_font"] == "仿宋"
    assert draft["typography"]["line_spacing"] == 1.5
    assert draft["margins"]["top"] == "2.8cm"
    assert draft["margins"]["left"] == "3.0cm"
    assert "页下" in draft["citations_style"] or "脚注" in draft["citations_style"]
    assert len(draft["reasoning"]) >= 3
    assert "contract_cards" in draft
    assert len(draft["contract_cards"]) >= 4
    card_categories = [c["category"] for c in draft["contract_cards"]]
    assert "正文字体" in card_categories
    assert "版面版心" in card_categories




def test_detailed_analysis_and_selective_apply(tmp_path: Path):
    source_docx = tmp_path / "raw_sample.docx"
    output_docx = tmp_path / "formatted_detailed.docx"
    generate_sample_thesis(source_docx)

    analysis = analyze_document_detailed(source_docx, standard_id="gb-t-7713-1")
    assert analysis["status"] == "ready"
    assert analysis["total_operations"] > 0
    assert len(analysis["deep_candidates"]["citations_detected"]) >= 2

    # Select only first half of operations
    ops = analysis["operations"]
    approved_ids = [op["operation_id"] for op in ops[:len(ops) // 2]]

    result = apply_document_detailed(
        source_path=source_docx,
        output_path=output_docx,
        standard_id="gb-t-7713-1",
        approved_operation_ids=approved_ids,
        deep_options={"fix_cross_references": False},
    )

    assert result["status"] == "success"
    assert result["mode"] == "detailed"
    assert result["operations_applied"] == len(approved_ids)
    assert output_docx.exists()


def test_ai_qa_audit(tmp_path: Path):
    source_docx = tmp_path / "sample.docx"
    generate_sample_thesis(source_docx)

    audit = run_ai_qa_audit(source_docx, standard_id="gb-t-7713-1")
    assert "verdict" in audit
    assert "summary" in audit
    assert isinstance(audit["issues"], list)
    assert "blind_review_score" in audit
    assert 0 <= audit["blind_review_score"] <= 100
    assert "dimension_scores" in audit
    dims = audit["dimension_scores"]
    assert "structure" in dims
    assert "typography" in dims
    assert "tables_figures" in dims
    assert "citations" in dims
    assert "review_grade" in audit
    assert any(keyword in audit["review_grade"] for keyword in ["通过", "优秀", "良好", "整改"])
    assert "reviewer_summary" in audit




def test_agent_scanner():
    from server.agent_scanner import scan_local_agents
    result = scan_local_agents()
    assert "agents" in result
    assert "workbuddy" in result["agents"]
    assert "trae" in result["agents"]
    assert "doubao" in result["agents"]
    assert "deepseek" in result["agents"]
    assert "environment" in result
    assert result["environment"]["uv_available"] is True
