from pathlib import Path

from paper_setting_runtime.bootstrap import run_migrations
from paper_setting_runtime.config import Settings
from paper_setting_runtime.database import (
    create_database_engine,
    create_session_factory,
    session_scope,
)
from paper_setting_runtime.repositories import JobRepository
from paper_setting_runtime.services import JobService, RulePackService


def test_worker_retries_unexpected_failure(sample_docx: Path, tmp_path: Path, monkeypatch) -> None:
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'retry.db'}",
        data_dir=tmp_path / "data",
    )
    run_migrations(settings)
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    RulePackService(settings, factory).bootstrap()
    service = JobService(settings, factory)
    job = service.create_from_file(
        sample_docx,
        source_filename=sample_docx.name,
        rule_pack_id="zh-thesis-default",
        render_preview=False,
    )
    original = service._inspect_and_plan

    def fail_once(_: str) -> None:
        raise ValueError("transient test failure")

    monkeypatch.setattr(service, "_inspect_and_plan", fail_once)
    assert service.process_next("retry-worker")
    retrying = service.get(job.id)
    assert retrying.status == "uploaded"
    assert retrying.failure_count == 1

    monkeypatch.setattr(service, "_inspect_and_plan", original)
    assert service.process_next("retry-worker")
    assert service.get(job.id).status == "plan_ready"
    engine.dispose()


def test_active_worker_lease_cannot_be_stolen(sample_docx: Path, tmp_path: Path) -> None:
    settings = Settings(
        env="test",
        database_url=f"sqlite:///{tmp_path / 'lease.db'}",
        data_dir=tmp_path / "data",
    )
    run_migrations(settings)
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    RulePackService(settings, factory).bootstrap()
    service = JobService(settings, factory)
    job = service.create_from_file(
        sample_docx,
        source_filename=sample_docx.name,
        rule_pack_id="zh-thesis-default",
        render_preview=False,
    )

    with session_scope(factory) as session:
        claimed = JobRepository(session).claim_next("worker-a", settings.worker_lease_seconds)
        assert claimed is not None and claimed.id == job.id
    with session_scope(factory) as session:
        assert JobRepository(session).claim_next("worker-b", settings.worker_lease_seconds) is None
        JobRepository(session).release_lease(job.id, "worker-b")
    with session_scope(factory) as session:
        assert JobRepository(session).claim_next("worker-b", settings.worker_lease_seconds) is None
        assert JobRepository(session).renew_lease(
            job.id, "worker-a", settings.worker_lease_seconds
        )
        JobRepository(session).release_lease(job.id, "worker-a")
    with session_scope(factory) as session:
        claimed = JobRepository(session).claim_next("worker-b", settings.worker_lease_seconds)
        assert claimed is not None and claimed.id == job.id

    engine.dispose()
