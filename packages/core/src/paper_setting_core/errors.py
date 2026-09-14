from __future__ import annotations

from typing import Any


class AppError(Exception):
    def __init__(
        self,
        detail: str,
        code: str,
        status_code: int = 422,
        *,
        title: str | None = None,
        field_errors: list[dict[str, Any]] | None = None,
        job_id: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.code = code
        self.status_code = status_code
        self.title = title or code.replace("_", " ").title()
        self.field_errors = field_errors or []
        self.job_id = job_id


class InvalidDocxError(AppError):
    def __init__(self, detail: str = "文件不是有效的 DOCX") -> None:
        super().__init__(detail, "INVALID_DOCX", 422)


class UnsupportedDocumentFormatError(AppError):
    def __init__(self, detail: str = "主论文仅支持 .doc 或 .docx 文件") -> None:
        super().__init__(detail, "UNSUPPORTED_DOCUMENT_FORMAT", 422)


class InvalidLegacyDocError(AppError):
    def __init__(self, detail: str = "文件不是有效的旧版 Word DOC 文档") -> None:
        super().__init__(detail, "INVALID_DOC", 422)


class DocumentConversionUnavailableError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "本机未找到 DOC 转换组件，请安装 LibreOffice 后重试",
            "DOC_CONVERSION_UNAVAILABLE",
            503,
        )


class DocumentConversionBusyError(AppError):
    def __init__(self) -> None:
        super().__init__("已有 DOC 正在转换，请稍后重试", "DOC_CONVERSION_BUSY", 429)


class DocumentConversionTimeoutError(AppError):
    def __init__(self) -> None:
        super().__init__("DOC 转换超时，请检查文档后重试", "DOC_CONVERSION_TIMEOUT", 422)


class DocumentConversionFailedError(AppError):
    def __init__(self) -> None:
        super().__init__(
            "DOC 转换失败，文档可能已损坏或包含不受支持的内容",
            "DOC_CONVERSION_FAILED",
            422,
        )


class UnsafeZipPackageError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "UNSAFE_ZIP_PACKAGE", 422)


class RulePackInvalidError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "RULE_PACK_INVALID", 422)


class RulePackNotExecutableError(AppError):
    def __init__(self, detail: str, blockers: list[str]) -> None:
        super().__init__(
            detail,
            "RULE_PACK_NOT_EXECUTABLE",
            422,
            field_errors=[
                {"field": "requirements", "message": blocker, "code": "blocked"}
                for blocker in blockers
            ],
        )


class RuleSourceInvalidError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "RULE_SOURCE_INVALID", 422)


class NotFoundError(AppError):
    def __init__(self, resource: str, identifier: str, code: str = "ARTIFACT_NOT_FOUND") -> None:
        super().__init__(f"{resource} 不存在: {identifier}", code, 404)


class JobConflictError(AppError):
    def __init__(self, detail: str, code: str = "JOB_CONFLICT", job_id: str | None = None) -> None:
        super().__init__(detail, code, 409, job_id=job_id)


class IntegrityCheckFailedError(AppError):
    def __init__(self, detail: str, job_id: str | None = None) -> None:
        super().__init__(detail, "INTEGRITY_CHECK_FAILED", 422, job_id=job_id)


class TemplateFillInvalidError(AppError):
    def __init__(self, detail: str, field_errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail, "TEMPLATE_FILL_INVALID", 422, field_errors=field_errors)


class TemplateFillBlockedError(AppError):
    def __init__(self, detail: str, blockers: list[str]) -> None:
        super().__init__(
            detail,
            "TEMPLATE_FILL_BLOCKED",
            422,
            field_errors=[
                {"field": "values", "message": blocker, "code": "protected_target"}
                for blocker in blockers
            ],
        )


class StaleTemplateFillPlanError(AppError):
    def __init__(self, detail: str = "模板或填写值已变化，请重新生成填写预览") -> None:
        super().__init__(detail, "STALE_TEMPLATE_FILL_PLAN", 409)


class TemplateStructureInvalidError(AppError):
    def __init__(self, detail: str, field_errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail, "TEMPLATE_STRUCTURE_INVALID", 422, field_errors=field_errors)


class TemplateStructureBlockedError(AppError):
    def __init__(self, detail: str, blockers: list[str]) -> None:
        super().__init__(
            detail,
            "TEMPLATE_STRUCTURE_BLOCKED",
            422,
            field_errors=[
                {"field": "sections", "message": blocker, "code": "blocked"}
                for blocker in blockers
            ],
        )


class StaleTemplateStructurePlanError(AppError):
    def __init__(self, detail: str = "模板或分节设置已变化，请重新生成结构预览") -> None:
        super().__init__(detail, "STALE_TEMPLATE_STRUCTURE_PLAN", 409)


class TemplateCombinedInvalidError(AppError):
    def __init__(self, detail: str, field_errors: list[dict[str, Any]] | None = None) -> None:
        super().__init__(detail, "TEMPLATE_COMBINED_INVALID", 422, field_errors=field_errors)


class TemplateCombinedBlockedError(AppError):
    def __init__(self, detail: str, blockers: list[str]) -> None:
        super().__init__(
            detail,
            "TEMPLATE_COMBINED_BLOCKED",
            422,
            field_errors=[
                {"field": "values", "message": blocker, "code": "blocked"} for blocker in blockers
            ],
        )


class StaleTemplateCombinedPlanError(AppError):
    def __init__(self, detail: str = "模板、填写值或分节设置已变化，请重新生成组合预览") -> None:
        super().__init__(detail, "STALE_TEMPLATE_COMBINED_PLAN", 409)


class CrossReferenceInvalidError(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail, "CROSS_REFERENCE_INVALID", 422)
