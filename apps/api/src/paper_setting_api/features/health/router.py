from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready(request: Request) -> JSONResponse:
    checks = {"database": {"status": "ok"}}
    headers = {"X-Paper-Setting-Instance": request.app.state.settings.instance_id}
    try:
        with request.app.state.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception:
        checks["database"] = {"status": "error"}
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "checks": checks},
            headers=headers,
        )
    return JSONResponse(
        status_code=200,
        content={"status": "ok", "checks": checks},
        headers=headers,
    )
