"""Test FastAPI REST endpoints for v1.1 workbench."""

from __future__ import annotations

from fastapi.testclient import TestClient
from server.app import app

client = TestClient(app)


def test_health_endpoint():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.1.0"


def test_standards_endpoint():
    resp = client.get("/api/standards")
    assert resp.status_code == 200
    standards = resp.json()
    assert len(standards) >= 4
    ids = [s["id"] for s in standards]
    assert "gb-t-7713-1" in ids


def test_full_minimal_flow_via_api():
    # 1. Upload demo document
    resp = client.post("/api/upload", data={"use_demo": "true"})
    assert resp.status_code == 200
    data = resp.json()
    job_id = data["job_id"]
    assert data["doc_info"]["total_paragraphs"] > 5

    format_resp = client.post(
        "/api/format/minimal",
        json={"job_id": job_id, "standard_id": "gb-t-7713-1"},
    )
    assert format_resp.status_code == 200
    format_data = format_resp.json()
    assert format_data["status"] == "success"
    assert format_data["compliance_score"] == 100
    assert len(format_data["highlights"]) >= 4
    assert "qa_report" in format_data
    assert "blind_review_score" in format_data["qa_report"]
    assert 0 <= format_data["qa_report"]["blind_review_score"] <= 100

    # 3. Verify QA report standalone endpoint
    qa_resp = client.get(f"/api/jobs/{job_id}/qa-report")
    assert qa_resp.status_code == 200
    qa_data = qa_resp.json()
    assert qa_data["job_id"] == job_id
    assert "qa_report" in qa_data
    assert "dimension_scores" in qa_data["qa_report"]

    # 4. Download output DOCX
    dl_resp = client.get(f"/api/jobs/{job_id}/download")
    assert dl_resp.status_code == 200
    assert len(dl_resp.content) > 1000
    assert dl_resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"



def test_detailed_flow_and_agent_via_api():
    # 1. Upload demo
    resp = client.post("/api/upload", data={"use_demo": "true"})
    assert resp.status_code == 200
    job_id = resp.json()["job_id"]

    # 2. Get detailed analysis
    analysis_resp = client.post(f"/api/jobs/{job_id}/detailed-analysis?standard_id=gb-t-7713-1")
    assert analysis_resp.status_code == 200
    analysis_data = analysis_resp.json()
    assert analysis_data["total_operations"] > 0
    op_ids = [op["operation_id"] for op in analysis_data["operations"]]

    # 3. Apply detailed
    apply_resp = client.post(
        f"/api/jobs/{job_id}/detailed-apply",
        json={
            "standard_id": "gb-t-7713-1",
            "approved_operation_ids": op_ids[:3],
            "deep_options": {"convert_citations_to_footnotes": False},
        },
    )
    assert apply_resp.status_code == 200
    apply_data = apply_resp.json()
    assert apply_data["operations_applied"] == 3
    assert "qa_report" in apply_data
    assert "blind_review_score" in apply_data["qa_report"]

    # 4. Agent rule extraction
    rule_resp = client.post(
        "/api/agent/extract-rule",
        json={"raw_text": "全文字体采用宋体，行距1.5倍行距，页边距上2.5cm下2.5cm"},
    )
    assert rule_resp.status_code == 200
    rule_data = rule_resp.json()
    assert rule_data["typography"]["body_font"] == "宋体"
    assert "contract_cards" in rule_data
    assert len(rule_data["contract_cards"]) >= 2

    # 5. Agent audit
    audit_resp = client.post(
        "/api/agent/audit",
        json={"job_id": job_id, "standard_id": "gb-t-7713-1"},
    )
    assert audit_resp.status_code == 200
    audit_data = audit_resp.json()
    assert "verdict" in audit_data
    assert "blind_review_score" in audit_data
    assert "dimension_scores" in audit_data



def test_frontend_static_serving():
    resp_index = client.get("/")
    assert resp_index.status_code == 200
    assert "Paper Setting v1.1" in resp_index.text

    resp_css = client.get("/style.css")
    assert resp_css.status_code == 200
    assert "--brand-emerald" in resp_css.text

    resp_js = client.get("/app.js")
    assert resp_js.status_code == 200
    assert "startMinimalFormatting" in resp_js.text


def test_audit_download_endpoint():
    up_resp = client.post("/api/upload", data={"use_demo": True})
    assert up_resp.status_code == 200
    job_id = up_resp.json()["job_id"]

    audit_dl_resp = client.get(f"/api/jobs/{job_id}/audit-download")
    assert audit_dl_resp.status_code == 200
    assert audit_dl_resp.headers["content-type"].startswith("application/json")


def test_pdf_download_endpoint():
    up_resp = client.post("/api/upload", data={"use_demo": True})
    assert up_resp.status_code == 200
    job_id = up_resp.json()["job_id"]

    pdf_resp = client.get(f"/api/jobs/{job_id}/pdf-download")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"].startswith("application/pdf")
    assert len(pdf_resp.content) > 0



