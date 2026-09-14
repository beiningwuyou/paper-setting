from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from paper_setting_core.errors import AppError
from paper_setting_runtime.logging import get_logger


def problem_response(
    request: Request,
    *,
    title: str,
    status: int,
    detail: str,
    code: str,
    field_errors: list[dict] | None = None,
    job_id: str | None = None,
) -> JSONResponse:
    content = {
        "type": f"https://paper-setting.local/errors/{code.lower().replace('_', '-')}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
        "request_id": getattr(request.state, "request_id", None),
        "job_id": job_id,
        "field_errors": field_errors or [],
    }
    return JSONResponse(status_code=status, content=content, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    logger = get_logger()

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        return problem_response(
            request,
            title=exc.title,
            status=exc.status_code,
            detail=exc.detail,
            code=exc.code,
            field_errors=exc.field_errors,
            job_id=exc.job_id,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(part) for part in error["loc"]),
                "message": error["msg"],
                "code": error["type"],
            }
            for error in exc.errors()
        ]
        return problem_response(
            request,
            title="Validation Error",
            status=422,
            detail="请求参数校验失败",
            code="VALIDATION_ERROR",
            field_errors=errors,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception(
            "unexpected_api_error",
            request_id=getattr(request.state, "request_id", None),
            error_type=type(exc).__name__,
        )
        return problem_response(
            request,
            title="Internal Server Error",
            status=500,
            detail="服务发生未预期错误",
            code="INTERNAL_ERROR",
        )
