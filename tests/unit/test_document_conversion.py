from __future__ import annotations

from pathlib import Path

import pytest
from paper_setting_core.documents import conversion
from paper_setting_core.errors import (
    DocumentConversionFailedError,
    DocumentConversionTimeoutError,
    DocumentConversionUnavailableError,
    InvalidLegacyDocError,
    UnsupportedDocumentFormatError,
)


def test_normalized_manuscript_keeps_docx_unchanged(tmp_path: Path) -> None:
    source = tmp_path / "paper.docx"
    source.write_bytes(b"content")
    with conversion.normalized_manuscript(source, source_filename="paper.docx") as normalized:
        assert normalized == source


def test_normalized_manuscript_rejects_other_extensions(tmp_path: Path) -> None:
    source = tmp_path / "paper.txt"
    source.write_text("content", encoding="utf-8")
    with (
        pytest.raises(UnsupportedDocumentFormatError),
        conversion.normalized_manuscript(source, source_filename="paper.txt"),
    ):
        pass


def test_convert_legacy_doc_rejects_renamed_file(tmp_path: Path) -> None:
    source = tmp_path / "paper.doc"
    source.write_bytes(b"not a compound document")
    with pytest.raises(InvalidLegacyDocError):
        conversion.convert_legacy_doc(source, tmp_path / "paper.docx")


def test_convert_legacy_doc_reports_missing_converter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.doc"
    source.write_bytes(conversion.LEGACY_DOC_SIGNATURE + b"legacy")
    monkeypatch.setattr(conversion.shutil, "which", lambda _name: None)
    with pytest.raises(DocumentConversionUnavailableError):
        conversion.convert_legacy_doc(source, tmp_path / "paper.docx")


def test_convert_legacy_doc_uses_isolated_office_process(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.doc"
    source.write_bytes(conversion.LEGACY_DOC_SIGNATURE + b"legacy")
    target = tmp_path / "paper.docx"
    observed: dict[str, object] = {}

    class FakeProcess:
        pid = 42
        returncode = 0

        def __init__(self, command: list[str], **kwargs: object) -> None:
            observed["command"] = command
            observed["kwargs"] = kwargs
            output_dir = Path(command[command.index("--outdir") + 1])
            (output_dir / "source.docx").write_bytes(b"PK converted")

        def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
            observed["timeout"] = timeout
            return b"", b""

    monkeypatch.setattr(conversion.shutil, "which", lambda _name: "/opt/soffice")
    monkeypatch.setattr(conversion.subprocess, "Popen", FakeProcess)
    conversion.convert_legacy_doc(source, target, timeout_seconds=17)

    assert target.read_bytes() == b"PK converted"
    command = observed["command"]
    assert isinstance(command, list)
    assert command[0] == "/opt/soffice"
    assert "--headless" in command
    assert observed["timeout"] == 17
    kwargs = observed["kwargs"]
    assert isinstance(kwargs, dict)
    assert kwargs["start_new_session"] is True
    assert kwargs["env"]["HOME"] != str(Path.home())


@pytest.mark.parametrize("returncode,create_output", [(1, False), (0, False), (0, True)])
def test_convert_legacy_doc_rejects_failed_or_empty_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    returncode: int,
    create_output: bool,
) -> None:
    source = tmp_path / "paper.doc"
    source.write_bytes(conversion.LEGACY_DOC_SIGNATURE + b"legacy")

    class FailedProcess:
        pid = 42

        def __init__(self, command: list[str], **_kwargs: object) -> None:
            self.returncode = returncode
            if create_output:
                output_dir = Path(command[command.index("--outdir") + 1])
                (output_dir / "source.docx").touch()

        def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
            return b"", b"conversion error"

    monkeypatch.setattr(conversion.shutil, "which", lambda _name: "/opt/soffice")
    monkeypatch.setattr(conversion.subprocess, "Popen", FailedProcess)
    with pytest.raises(DocumentConversionFailedError):
        conversion.convert_legacy_doc(source, tmp_path / "paper.docx")


def test_convert_legacy_doc_reports_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "paper.doc"
    source.write_bytes(conversion.LEGACY_DOC_SIGNATURE + b"legacy")

    class TimedOutProcess:
        pid = 42
        returncode = None

        def __init__(self, _command: list[str], **_kwargs: object) -> None:
            pass

        def communicate(self, *, timeout: int) -> tuple[bytes, bytes]:
            raise conversion.subprocess.TimeoutExpired("soffice", timeout)

        def wait(self, *, timeout: int) -> int:
            self.returncode = -15
            return self.returncode

    monkeypatch.setattr(conversion.shutil, "which", lambda _name: "/opt/soffice")
    monkeypatch.setattr(conversion.subprocess, "Popen", TimedOutProcess)
    monkeypatch.setattr(conversion.os, "killpg", lambda _pid, _signal: None)
    with pytest.raises(DocumentConversionTimeoutError):
        conversion.convert_legacy_doc(source, tmp_path / "paper.docx", timeout_seconds=1)
