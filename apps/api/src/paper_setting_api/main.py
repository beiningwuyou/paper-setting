from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from paper_setting_runtime.bootstrap import run_migrations
from paper_setting_runtime.config import Settings, get_settings
from paper_setting_runtime.database import create_database_engine, create_session_factory
from paper_setting_runtime.logging import configure_logging, get_logger
from paper_setting_runtime.services import JobService, RulePackService

from paper_setting_api.errors import install_error_handlers
from paper_setting_api.features.health.router import router as health_router
from paper_setting_api.features.jobs.router import router as jobs_router
from paper_setting_api.features.rulepacks.router import router as rulepacks_router
from paper_setting_api.features.templates.router import router as templates_router
from paper_setting_api.middleware import install_middleware


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)
    run_migrations(settings)
    engine = create_database_engine(settings)
    session_factory = create_session_factory(engine)
    rule_pack_service = RulePackService(settings, session_factory)
    rule_pack_service.bootstrap()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        get_logger().info("api_started", host=settings.host, port=settings.port)
        yield
        engine.dispose()
        get_logger().info("api_stopped")

    app = FastAPI(
        title="Paper Setting API",
        version="0.1.0",
        description="Local-first DOCX thesis formatting compiler",
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.session_factory = session_factory
    app.state.rule_pack_service = rule_pack_service
    app.state.job_service = JobService(settings, session_factory)
    install_middleware(app, settings)
    install_error_handlers(app)
    app.include_router(health_router)
    app.include_router(rulepacks_router)
    app.include_router(templates_router)
    app.include_router(jobs_router)
    if settings.web_dist_dir.exists():
        app.mount("/", StaticFiles(directory=settings.web_dist_dir, html=True), name="web")
    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    uvicorn.run(
        "paper_setting_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.env == "development",
    )


if __name__ == "__main__":
    run()
