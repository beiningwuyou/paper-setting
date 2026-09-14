from __future__ import annotations

from fastapi import Request
from paper_setting_runtime.services import JobService, RulePackService


def get_job_service(request: Request) -> JobService:
    return request.app.state.job_service


def get_rule_pack_service(request: Request) -> RulePackService:
    return request.app.state.rule_pack_service

