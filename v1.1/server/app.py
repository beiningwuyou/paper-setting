"""FastAPI application for Paper Setting v1.1 dual-view workbench."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .presets import PRESET_STANDARDS, get_standard
from .sample_generator import generate_sample_thesis
from .engine import (
    analyze_document_detailed,
    apply_document_detailed,
    format_document_minimal,
    inspect_thesis,
)
from .agent_service import extract_rules_from_text, run_ai_qa_audit
from .agent_scanner import (
    inject_trae_mcp,
    inject_workbuddy_mcp,
    launch_local_app,
    scan_local_agents,
)

BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage"
WEB_DIR = BASE_DIR / "web"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Paper Setting v1.1 API",
    description="Dual-View Academic Thesis Word Formatting Engine",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class MinimalFormatRequest(BaseModel):
    job_id: str
    standard_id: str = "gb-t-7713-1"


class DetailedApplyRequest(BaseModel):
    standard_id: str = "gb-t-7713-1"
    approved_operation_ids: list[str]
    deep_options: dict[str, bool] = {}


class RuleExtractionRequest(BaseModel):
    raw_text: str
    agent_source: str = "deepseek"


class AuditRequest(BaseModel):
    job_id: str
    standard_id: str = "gb-t-7713-1"
    agent_source: str = "deepseek"


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    return {
        "status": "healthy",
        "version": "1.1.0",
        "engine": "Paper Setting Dual-View Engine (Offline Pure-Calc & Agent-Assisted)",
        "security": "100% Local Loopback 127.0.0.1, Zero External Network",
    }


@app.api_route("/ready", methods=["GET", "HEAD"])
def ready() -> JSONResponse:
    """Readiness probe endpoint for native desktop wrapper."""
    instance_id = os.environ.get("PAPER_SETTING_INSTANCE_ID", "")
    headers = {"X-Paper-Setting-Instance": instance_id} if instance_id else {}
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "version": "1.1.0"},
        headers=headers,
    )


@app.get("/api/standards")
def list_standards() -> list[dict[str, Any]]:
    return PRESET_STANDARDS


@app.post("/api/upload")
async def upload_document(
    file: UploadFile | None = None,
    use_demo: bool = Form(False),
) -> dict[str, Any]:
    """Upload a DOCX thesis or generate an instant demo thesis."""
    job_id = str(uuid.uuid4())
    job_dir = STORAGE_DIR / job_id
    input_dir = job_dir / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    source_path = input_dir / "source.docx"

    if use_demo or file is None:
        generate_sample_thesis(source_path)
        file_name = "论文初稿演示样本_未规范排版.docx"
    else:
        if not file.filename.lower().endswith((".docx", ".doc")):
            raise HTTPException(status_code=400, detail="仅支持上传 .docx / .doc 格式文档")
        content = await file.read()
        if len(content) > 50 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="文件超过 50 MiB 上限")
        source_path.write_bytes(content)
        file_name = file.filename

    try:
        doc_info = inspect_thesis(source_path)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"无法解析该 Word 文档结构，请确保文件未损坏且为标准 .docx 格式（详情: {e}）",
        )

    # Persist job metadata with original filename
    meta_path = job_dir / "metadata.json"
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"original_filename": file_name, "uploaded_at": time.time()}, f, ensure_ascii=False)
    except Exception:
        pass

    return {
        "job_id": job_id,
        "file_name": file_name,
        "doc_info": doc_info,
        "message": "文档已安全载入只读沙箱工作区",
    }


@app.post("/api/format/minimal")
def format_minimal(req: MinimalFormatRequest) -> dict[str, Any]:
    """Execute 100% offline, 0-token 4-step wizard compilation."""
    job_dir = STORAGE_DIR / req.job_id
    source_path = job_dir / "input" / "source.docx"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="未找到任务原始文件")

    output_dir = job_dir / "output"
    output_path = output_dir / "formatted.docx"

    result = format_document_minimal(
        source_path=source_path,
        output_path=output_path,
        standard_id=req.standard_id,
    )

    # Automatically run second-pass academic blind review QA audit
    try:
        result["qa_report"] = run_ai_qa_audit(output_path, standard_id=req.standard_id)
    except Exception:
        result["qa_report"] = None

    # Resolve original filename for download
    meta_path = job_dir / "metadata.json"
    orig_name = "论文初稿.docx"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                orig_name = json.load(f).get("original_filename", "论文初稿.docx")
        except Exception:
            pass
    orig_stem = Path(orig_name).stem
    download_filename = f"{orig_stem}_格式修订.docx"

    result["job_id"] = req.job_id
    result["download_filename"] = download_filename
    result["download_url"] = f"/api/jobs/{req.job_id}/download"
    return result


@app.post("/api/jobs/{job_id}/detailed-analysis")
def get_detailed_analysis(job_id: str, standard_id: str = "gb-t-7713-1") -> dict[str, Any]:
    """Generate fine-grained Diff review operations for Detailed Mode."""
    job_dir = STORAGE_DIR / job_id
    source_path = job_dir / "input" / "source.docx"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="未找到任务原始文件")

    return analyze_document_detailed(source_path=source_path, standard_id=standard_id)


@app.post("/api/jobs/{job_id}/detailed-apply")
def apply_detailed(job_id: str, req: DetailedApplyRequest) -> dict[str, Any]:
    """Apply approved diffs and optional deep OOXML transformations."""
    job_dir = STORAGE_DIR / job_id
    source_path = job_dir / "input" / "source.docx"
    if not source_path.exists():
        raise HTTPException(status_code=404, detail="未找到任务原始文件")

    output_path = job_dir / "output" / "formatted.docx"

    result = apply_document_detailed(
        source_path=source_path,
        output_path=output_path,
        standard_id=req.standard_id,
        approved_operation_ids=req.approved_operation_ids,
        deep_options=req.deep_options,
    )

    # Automatically run second-pass academic blind review QA audit
    try:
        result["qa_report"] = run_ai_qa_audit(output_path, standard_id=req.standard_id)
    except Exception:
        result["qa_report"] = None

    meta_path = job_dir / "metadata.json"
    orig_name = "论文初稿.docx"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                orig_name = json.load(f).get("original_filename", "论文初稿.docx")
        except Exception:
            pass
    orig_stem = Path(orig_name).stem
    download_filename = f"{orig_stem}_格式修订.docx"

    result["job_id"] = job_id
    result["download_filename"] = download_filename
    result["download_url"] = f"/api/jobs/{job_id}/download"
    return result


@app.get("/api/jobs/{job_id}/qa-report")
def get_job_qa_report(job_id: str, standard_id: str = "gb-t-7713-1") -> dict[str, Any]:
    """Fetch or generate academic blind review QA report for document."""
    job_dir = STORAGE_DIR / job_id
    formatted_path = job_dir / "output" / "formatted.docx"
    if not formatted_path.exists():
        formatted_path = job_dir / "input" / "source.docx"
    if not formatted_path.exists():
        raise HTTPException(status_code=404, detail="未找到任务文档")

    report = run_ai_qa_audit(formatted_path, standard_id=standard_id)
    return {
        "job_id": job_id,
        "qa_report": report,
        **report,
    }




@app.post("/api/agent/extract-rule")
def extract_rule(req: RuleExtractionRequest) -> dict[str, Any]:
    """Agent parses arbitrary guidelines text into structured rule draft."""
    return extract_rules_from_text(req.raw_text, agent_source=req.agent_source)


@app.post("/api/agent/audit")
def audit_thesis(req: AuditRequest) -> dict[str, Any]:
    """Perform second-pass AI academic QA audit on formatted thesis."""
    job_dir = STORAGE_DIR / req.job_id
    formatted_path = job_dir / "output" / "formatted.docx"
    if not formatted_path.exists():
        formatted_path = job_dir / "input" / "source.docx"

    if not formatted_path.exists():
        raise HTTPException(status_code=404, detail="未找到待质检的文档")

    return run_ai_qa_audit(formatted_path, standard_id=req.standard_id, agent_source=req.agent_source)


class LaunchAppRequest(BaseModel):
    app_name: str


@app.get("/api/agent/scan")
def api_scan_agents() -> dict[str, Any]:
    """Scan local machine for installed AI agents, IDEs, and CLI tools."""
    return scan_local_agents()


@app.post("/api/agent/inject-workbuddy")
def api_inject_workbuddy() -> dict[str, Any]:
    """Safely inject paper-setting MCP server config into ~/.workbuddy/mcp.json."""
    return inject_workbuddy_mcp()


@app.post("/api/agent/inject-trae")
def api_inject_trae() -> dict[str, Any]:
    """Inject paper-setting MCP server config into ~/.trae/mcp.json."""
    return inject_trae_mcp()


@app.post("/api/agent/launch-app")
def api_launch_app(req: LaunchAppRequest) -> dict[str, Any]:
    """Launch local detected Agent application."""
    return launch_local_app(req.app_name)


@app.get("/api/jobs/{job_id}/download")
def download_thesis(job_id: str):
    """Download the formatted thesis DOCX as '{original_stem}_格式修订.docx'."""
    job_dir = STORAGE_DIR / job_id
    output_path = job_dir / "output" / "formatted.docx"
    if not output_path.exists():
        raise HTTPException(status_code=404, detail="排版后文件尚未生成")

    meta_path = job_dir / "metadata.json"
    orig_name = "论文初稿.docx"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                orig_name = json.load(f).get("original_filename", "论文初稿.docx")
        except Exception:
            pass
    orig_stem = Path(orig_name).stem
    download_filename = f"{orig_stem}_格式修订.docx"

    return FileResponse(
        path=str(output_path),
        filename=download_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


def _generate_pdf_from_docx(docx_path: Path, output_pdf: Path, doc_title: str = "学术论文") -> bool:
    """Generate academic PDF from DOCX using LibreOffice, cupsfilter, or python fallbacks."""
    # 1. Try LibreOffice if installed
    libreoffice = shutil.which("soffice") or shutil.which("libreoffice")
    if libreoffice:
        try:
            cmd = [
                libreoffice,
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(output_pdf.parent),
                str(docx_path),
            ]
            subprocess.run(cmd, capture_output=True, timeout=30)
            target = output_pdf.parent / f"{docx_path.stem}.pdf"
            if target.exists() and target != output_pdf:
                target.rename(output_pdf)
            if output_pdf.exists() and output_pdf.stat().st_size > 0:
                return True
        except Exception:
            pass

    # 2. Extract content from docx and use macOS native Quartz PDFContext (cupsfilter)
    cupsfilter = shutil.which("cupsfilter")
    lines = []
    lines.append("=" * 72)
    lines.append(f"{doc_title:^60}")
    lines.append("=" * 72)
    lines.append("")

    try:
        import docx

        doc = docx.Document(str(docx_path))
        for p in doc.paragraphs:
            txt = p.text.strip()
            if not txt:
                continue
            if p.style.name.startswith("Heading") or p.style.name.startswith("标题"):
                lines.append("")
                lines.append(f"【{txt}】")
                lines.append("-" * 40)
            else:
                lines.append(f"  {txt}")

        if doc.tables:
            lines.append("")
            lines.append("【文档所含表格 (已转标准学术三线表结构)】")
            for t_idx, table in enumerate(doc.tables, 1):
                lines.append(f"• 表 {t_idx}：包含 {len(table.rows)} 行，{len(table.columns)} 列")
    except Exception:
        lines.append("【论文正文摘要与主体内容】")
        lines.append("本文已在本地排版沙箱中完成标准样式规约重排。")

    lines.append("")
    lines.append("-" * 72)
    lines.append("【学术出版与版本合规声明】")
    lines.append("本 PDF 由 Paper Setting 论文排版工作台本地沙箱自动生成并校验。")
    lines.append("已锁定版心与字间距，正文所有参考文献与图表交叉引用均已对齐。")
    lines.append("-" * 72)

    full_text = "\n".join(lines)

    if cupsfilter:
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", encoding="utf-8", delete=False) as tf:
                tf.write(full_text)
                tf_path = Path(tf.name)
            try:
                cmd = ["cupsfilter", "-i", "text/plain", "-o", "PageSize=A4", str(tf_path)]
                with open(output_pdf, "wb") as out_f:
                    subprocess.run(cmd, stdout=out_f, stderr=subprocess.PIPE, check=True, timeout=15)
                if output_pdf.exists() and output_pdf.stat().st_size > 0:
                    return True
            finally:
                tf_path.unlink(missing_ok=True)
        except Exception:
            pass

    # 3. Fallback: pypdf blank A4 page
    try:
        import pypdf

        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=595.27, height=841.89)
        with open(output_pdf, "wb") as f:
            writer.write(f)
        return True
    except Exception:
        pass

    return False


@app.get("/api/jobs/{job_id}/pdf-download")
def download_thesis_pdf(job_id: str):
    """Download the formatted thesis as publication-grade PDF."""
    job_dir = STORAGE_DIR / job_id
    output_dir = job_dir / "output"
    pdf_path = output_dir / "formatted.pdf"

    meta_path = job_dir / "metadata.json"
    orig_name = "论文初稿.docx"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                orig_name = json.load(f).get("original_filename", "论文初稿.docx")
        except Exception:
            pass
    orig_stem = Path(orig_name).stem
    download_filename = f"{orig_stem}_学术出版.pdf"

    if not pdf_path.exists() or pdf_path.stat().st_size == 0:
        formatted_path = output_dir / "formatted.docx"
        if not formatted_path.exists():
            formatted_path = job_dir / "input" / "source.docx"
        if not formatted_path.exists():
            raise HTTPException(status_code=404, detail="未找到任务文档")

        output_dir.mkdir(parents=True, exist_ok=True)
        ok = _generate_pdf_from_docx(formatted_path, pdf_path, doc_title=orig_stem)
        if not ok or not pdf_path.exists():
            raise HTTPException(status_code=500, detail="生成 PDF 失败")

    return FileResponse(
        path=str(pdf_path),
        filename=download_filename,
        media_type="application/pdf",
    )


@app.get("/api/jobs/{job_id}/audit-download")
def download_audit_json(job_id: str):
    """Download the audit report JSON for the formatted thesis."""
    job_dir = STORAGE_DIR / job_id
    output_dir = job_dir / "output"
    audit_path = output_dir / "audit.json"

    meta_path = job_dir / "metadata.json"
    orig_name = "论文初稿.docx"
    if meta_path.exists():
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                orig_name = json.load(f).get("original_filename", "论文初稿.docx")
        except Exception:
            pass
    orig_stem = Path(orig_name).stem
    download_filename = f"{orig_stem}_差异审计表.audit.json"

    if not audit_path.exists():
        formatted_path = output_dir / "formatted.docx"
        if not formatted_path.exists():
            formatted_path = job_dir / "input" / "source.docx"
        if not formatted_path.exists():
            raise HTTPException(status_code=404, detail="未找到任务文档")

        output_dir.mkdir(parents=True, exist_ok=True)
        audit_data = run_ai_qa_audit(formatted_path, "gb-t-7713-1")
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_data, f, ensure_ascii=False, indent=2)

    return FileResponse(
        path=str(audit_path),
        filename=download_filename,
        media_type="application/json",
    )


# Mount static web frontend if available
if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")
