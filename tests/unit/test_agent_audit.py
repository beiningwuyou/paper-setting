import json
import subprocess
from pathlib import Path

from paper_setting_runtime import agent_audit


def test_agent_audit_runs_codex_read_only(tmp_path: Path, monkeypatch) -> None:
    output = tmp_path / "output" / "formatted.docx"
    output.parent.mkdir()
    output.write_bytes(b"docx")
    (tmp_path / "rule-pack.json").write_text("{}", encoding="utf-8")
    (tmp_path / "output" / "report.json").write_text("{}", encoding="utf-8")
    (tmp_path / "output" / "operations.json").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(agent_audit.shutil, "which", lambda command: "/bin/codex")

    def fake_run(command, **kwargs):
        response = Path(command[command.index("--output-last-message") + 1])
        response.write_text(
            json.dumps({"verdict": "pass", "summary": "ok", "issues": []}),
            encoding="utf-8",
        )
        assert command[command.index("--sandbox") + 1] == "read-only"
        assert command[command.index("--ask-for-approval") + 1] == "never"
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(agent_audit.subprocess, "run", fake_run)
    result = agent_audit.run_agent_audit(
        tmp_path, output, command="codex", timeout_seconds=30
    )
    assert result == {"status": "completed", "verdict": "pass", "summary": "ok", "issues": []}
    assert not (tmp_path / "output" / "agent-audit-schema.json").exists()
    assert not (tmp_path / "output" / "agent-audit-response.json").exists()


def test_agent_audit_is_optional_when_cli_is_missing(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(agent_audit.shutil, "which", lambda command: None)
    result = agent_audit.run_agent_audit(
        tmp_path, tmp_path / "output.docx", command="missing", timeout_seconds=30
    )
    assert result["status"] == "unavailable"
