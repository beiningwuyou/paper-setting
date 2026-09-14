from __future__ import annotations

import json
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from paper_setting_core.errors import AppError
from paper_setting_core.rulepacks.models import (
    RulePack,
    TemplateFillRule,
    TemplateRule,
    TemplateStructureRule,
)
from paper_setting_core.rulepacks.service import canonical_rule_pack_json
from paper_setting_core.templates import inspect_template as inspect_template_document
from paper_setting_core.templates import parse_template_values
from paper_setting_runtime.bootstrap import run_migrations
from paper_setting_runtime.config import get_settings
from paper_setting_runtime.database import create_database_engine, create_session_factory
from paper_setting_runtime.logging import configure_logging
from paper_setting_runtime.services import JobService, RulePackService

settings = get_settings()
configure_logging(settings.log_level, stream=sys.stderr)
run_migrations(settings)
engine = create_database_engine(settings)
factory = create_session_factory(engine)
rule_pack_service = RulePackService(settings, factory)
rule_pack_service.bootstrap()
job_service = JobService(settings, factory)
mcp = FastMCP("Paper Setting")


def _safe_input_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    roots = [root.expanduser().resolve() for root in settings.allowed_input_roots]
    if not roots:
        roots = [Path.cwd().resolve()]
    if not any(path.is_relative_to(root) for root in roots):
        raise AppError("输入文件不在允许目录中", "INPUT_PATH_NOT_ALLOWED", 403)
    if not path.is_file():
        raise AppError("输入文件不存在", "INVALID_DOCX", 422)
    return path


def _create_job(
    input_path: str,
    rule_pack_id: str,
    render_preview: bool,
    template_input_path: str | None = None,
) -> dict:
    path = _safe_input_path(input_path)
    template_path = _safe_input_path(template_input_path) if template_input_path else None
    return job_service.create_from_file(
        path,
        source_filename=path.name,
        rule_pack_id=rule_pack_id,
        render_preview=render_preview,
        template_path=template_path,
        template_filename=template_path.name if template_path else None,
    ).model_dump(mode="json")


@mcp.tool()
def list_rule_packs() -> list[dict]:
    """列出可用于论文排版的确定性规则包。"""
    return [item.model_dump(mode="json") for item in rule_pack_service.list()]


@mcp.tool()
def get_rule_pack(rule_pack_id: str) -> dict:
    """读取完整规则包，用于生成或调整 Agent 驱动的模板配置。"""
    return rule_pack_service.get(rule_pack_id).model_dump(mode="json")


@mcp.tool()
def inspect_template(input_path: str) -> dict:
    """分析允许目录内的 DOCX 模板，返回字段、分节和能力候选；不修改文件。"""
    path = _safe_input_path(input_path)
    return inspect_template_document(
        path,
        source_filename=path.name,
        max_upload_bytes=settings.max_upload_bytes,
        max_uncompressed_bytes=settings.max_uncompressed_bytes,
        max_entries=settings.max_zip_entries,
    ).model_dump(mode="json")


@mcp.tool()
def create_template_rule_pack(
    rule_pack_id: str,
    name: str,
    values: dict[str, str],
    structure: dict | None = None,
    base_rule_pack_id: str = "zh-thesis-default",
    version: str = "1.0.0",
) -> dict:
    """
    从现有规则包创建可执行的模板规则包。

    values 是占位符或内容控件的字段值；structure 接受与 RulePack.template.structure
    相同的 sections/even_and_odd_headers 对象。
    """
    if rule_pack_id == base_rule_pack_id:
        raise AppError(
            "新模板规则包不能覆盖其基础规则包",
            "RULE_PACK_INVALID",
            422,
        )
    normalized_values = parse_template_values(json.dumps(values, ensure_ascii=False))
    normalized_structure = TemplateStructureRule.model_validate(structure or {})
    if not normalized_values and not (
        normalized_structure.sections
        or normalized_structure.even_and_odd_headers is not None
    ):
        raise AppError(
            "模板规则包至少需要一个填写值或分节结构设置",
            "RULE_PACK_INVALID",
            422,
        )
    base = rule_pack_service.get(base_rule_pack_id)
    payload = base.model_dump(mode="python")
    payload.update(
        {
            "id": rule_pack_id,
            "name": name,
            "version": version,
            "template": TemplateRule(
                fill=TemplateFillRule(values=normalized_values),
                structure=normalized_structure,
            ).model_dump(mode="python"),
        }
    )
    rule_pack = RulePack.model_validate(payload)
    return rule_pack_service.import_json(
        canonical_rule_pack_json(rule_pack).encode("utf-8")
    ).model_dump(mode="json")


@mcp.tool()
def create_job(
    input_path: str,
    rule_pack_id: str = "zh-thesis-default",
    render_preview: bool = True,
    template_input_path: str | None = None,
) -> dict:
    """创建自动模式任务；可传学校模板以智能映射字段并注入整篇正文，计划须在 Web 审批。"""
    return _create_job(input_path, rule_pack_id, render_preview, template_input_path)


@mcp.tool()
def create_format_job(
    input_path: str,
    rule_pack_id: str = "zh-thesis-default",
    render_preview: bool = True,
) -> dict:
    """兼容工具：创建由 RulePack 自动选择模式的任务。新工作流请使用 create_job。"""
    return _create_job(input_path, rule_pack_id, render_preview)


@mcp.tool()
def list_jobs(limit: int = 20, cursor: str | None = None) -> dict:
    """按时间倒序列出本地任务；使用 next_cursor 获取下一页。"""
    return job_service.list_jobs(limit=max(1, min(limit, 100)), cursor=cursor).model_dump(
        mode="json"
    )


@mcp.tool()
def get_job(job_id: str) -> dict:
    """读取 format/template 任务的状态和进度。"""
    return job_service.get(job_id).model_dump(mode="json")


@mcp.tool()
def get_format_job(job_id: str) -> dict:
    """兼容工具：读取任务状态和进度。新工作流请使用 get_job。"""
    return job_service.get(job_id).model_dump(mode="json")


@mcp.tool()
def get_format_plan(job_id: str) -> dict:
    """读取可审计修改计划；不能通过此工具批准计划。"""
    return job_service.get_plan(job_id).model_dump(mode="json")


@mcp.tool()
def get_template_plan(job_id: str) -> dict:
    """读取模板任务计划（字段填写、正文注入和分节结构）；不能通过此工具批准。"""
    return job_service.get_template_plan(job_id).model_dump(mode="json")


@mcp.tool()
def get_validation_report(job_id: str) -> dict:
    """读取完成任务的内容完整性和格式执行报告。"""
    return job_service.get_report(job_id).model_dump(mode="json")


@mcp.tool()
def list_artifacts(job_id: str) -> list[dict]:
    """列出任务生成的 DOCX、报告和可选 PDF artifact。"""
    return [item.model_dump(mode="json") for item in job_service.list_artifacts(job_id)]


def run() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    run()
