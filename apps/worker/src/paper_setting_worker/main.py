from __future__ import annotations

import signal
import socket
import threading
import uuid

from paper_setting_runtime.bootstrap import run_migrations
from paper_setting_runtime.config import get_settings
from paper_setting_runtime.database import create_database_engine, create_session_factory
from paper_setting_runtime.logging import configure_logging, get_logger
from paper_setting_runtime.services import JobService, RulePackService


def run() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    run_migrations(settings)
    engine = create_database_engine(settings)
    factory = create_session_factory(engine)
    RulePackService(settings, factory).bootstrap()
    service = JobService(settings, factory)
    worker_id = f"{socket.gethostname()}-{uuid.uuid4().hex[:8]}"
    stop = threading.Event()

    def request_stop(signum: int, _: object) -> None:
        get_logger().info("worker_shutdown_requested", worker_id=worker_id, signal=signum)
        stop.set()

    signal.signal(signal.SIGTERM, request_stop)
    signal.signal(signal.SIGINT, request_stop)
    get_logger().info("worker_started", worker_id=worker_id)
    try:
        while not stop.is_set():
            processed = service.process_next(worker_id)
            if not processed:
                stop.wait(settings.worker_poll_seconds)
    finally:
        engine.dispose()
        get_logger().info("worker_stopped", worker_id=worker_id)


if __name__ == "__main__":
    run()

