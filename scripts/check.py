#!/usr/bin/env python3
"""Run local regression checks without starting services or touching user jobs."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGRESSION = [
    "tests/unit/test_formatting_policy.py",
    "tests/unit/test_thesis_template_boundaries.py",
    "tests/integration/test_formatting_policy_workflow.py",
    "tests/integration/test_safety.py",
    "tests/integration/test_mcp_template_workflow.py",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--full", action="store_true", help="Run all tests with project coverage gate"
    )
    parser.add_argument("--report-dir", type=Path, help="New directory for logs and result.json")
    args = parser.parse_args()
    # macOS bootstrap python3 can be 3.9; the actual suite runs with the project Python.
    report = args.report_dir or ROOT / "artifacts" / "checks" / datetime.now(timezone.utc).strftime(  # noqa: UP017
        "%Y%m%dT%H%M%S-%fZ"
    )
    report = report.resolve()
    report.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result: dict = {"project": str(ROOT), "suite": "full" if args.full else "regression"}
    python = ROOT / ".venv" / "bin" / "python"
    # Use the interpreter directly: console-script shebangs can retain pre-migration paths.
    preflight = (
        "import pathlib,sys,pytest,pytest_cov,paper_setting_core; "
        "actual=pathlib.Path(paper_setting_core.__file__).resolve(); "
        "expected=pathlib.Path(sys.argv[1]).resolve(); "
        "print('Python:',sys.version.split()[0]); print('Core:',actual); "
        "assert actual.is_relative_to(expected), 'Editable install points to another checkout'"
    )
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTEST_ADDOPTS", None)
    env["COVERAGE_FILE"] = str(report / ".coverage")
    commands = [
        [str(python), "-c", preflight, str(ROOT / "packages" / "core" / "src")],
        [str(python), "-m", "pytest"] + ([] if args.full else ["--no-cov", *REGRESSION]),
    ]
    code = 2
    try:
        missing = [p for p in ["pyproject.toml", *REGRESSION] if not (ROOT / p).is_file()]
        if missing:
            raise RuntimeError(f"Missing project files: {', '.join(missing)}")
        if not python.is_file():
            raise RuntimeError(
                "Missing .venv/bin/python; restore declared dependencies with make install"
            )
        result["commands"] = commands
        for index, command in enumerate(commands):
            log = report / ("preflight.log" if index == 0 else "pytest.log")
            print(f"Running {'preflight' if index == 0 else result['suite']}: {log}", flush=True)
            with log.open("w") as output:
                completed = subprocess.run(
                    command, cwd=ROOT, env=env, stdout=output, stderr=subprocess.STDOUT,
                    timeout=600, check=False,
                )
            code = completed.returncode
            if code:
                result["failed_stage"] = "preflight" if index == 0 else "pytest"
                if index == 0:
                    result["hint"] = "Inspect preflight.log; restore dependencies in this checkout."
                break
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        result["error"] = str(error)
        code = 2
    result.update(
        exit_code=code, passed=code == 0, elapsed_seconds=round(time.monotonic() - started, 2)
    )
    (report / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(f"{'PASS' if code == 0 else 'FAIL'}: {report / 'result.json'}")
    return code if code >= 0 else 1


if __name__ == "__main__":
    sys.exit(main())
