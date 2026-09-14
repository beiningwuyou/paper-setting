"""Test Yu Jun Value & Cognitive Optimizations (Text Conservation, HITL, Progressive Disclosure)."""

from __future__ import annotations

from pathlib import Path
from fastapi.testclient import TestClient

from server.app import app
from server.engine import compute_text_conservation, format_document_minimal, apply_document_detailed, analyze_document_detailed
from server.sample_generator import generate_sample_thesis
from server.agent_service import extract_rules_from_text


client = TestClient(app)


def test_text_conservation_computation(tmp_path: Path):
    source_docx = tmp_path / "thesis_src.docx"
    output_docx = tmp_path / "thesis_out.docx"
    generate_sample_thesis(source_docx)

    # Format document
    result = format_document_minimal(
        source_path=source_docx,
        output_path=output_docx,
        standard_id="gb-t-7713-1",
    )

    assert "text_conservation" in result
    tc = result["text_conservation"]
    assert tc["original_chars"] > 0
    assert tc["formatted_chars"] > 0
    assert tc["conservation_rate"] >= 99.0
    assert tc["zero_tamper_guaranteed"] is True
    assert "守恒" in tc["status_text"]


def test_api_minimal_returns_text_conservation():
    # 1. Upload sample
    up_res = client.post("/api/upload", data={"use_demo": "true"})
    assert up_res.status_code == 200
    job_id = up_res.json()["job_id"]

    # 2. Minimal format
    fmt_res = client.post("/api/format/minimal", json={"job_id": job_id, "standard_id": "gb-t-7713-1"})
    assert fmt_res.status_code == 200
    data = fmt_res.json()
    assert "text_conservation" in data
    assert data["text_conservation"]["zero_tamper_guaranteed"] is True
    assert data["text_conservation"]["conservation_rate"] >= 99.0


def test_api_detailed_apply_returns_text_conservation():
    # 1. Upload sample
    up_res = client.post("/api/upload", data={"use_demo": "true"})
    assert up_res.status_code == 200
    job_id = up_res.json()["job_id"]

    # 2. Get detailed analysis
    an_res = client.post(f"/api/jobs/{job_id}/detailed-analysis?standard_id=gb-t-7713-1")
    assert an_res.status_code == 200
    ops = an_res.json()["operations"]
    appr_ids = [op["operation_id"] for op in ops[:3]]

    # 3. Apply detailed
    apply_res = client.post(
        f"/api/jobs/{job_id}/detailed-apply",
        json={"standard_id": "gb-t-7713-1", "approved_operation_ids": appr_ids},
    )
    assert apply_res.status_code == 200
    data = apply_res.json()
    assert "text_conservation" in data
    assert data["text_conservation"]["zero_tamper_guaranteed"] is True


def test_hitl_tunable_fields_contract():
    notice = "关于毕业论文格式：正文要求小四号宋体，行距统一为 1.5 倍行距。"
    data = extract_rules_from_text(notice)
    assert "tunable_fields" in data
    tf = data["tunable_fields"]
    assert "body_fonts" in tf
    assert "宋体" in tf["body_fonts"]
    assert "body_sizes" in tf
    assert any(s["value"] == 12.0 for s in tf["body_sizes"])
    assert "line_spacings" in tf
    assert any(ls["value"] == 1.5 for ls in tf["line_spacings"])
    assert "citations_styles" in tf
