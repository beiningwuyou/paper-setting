from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from paper_setting_core.errors import (
    DocumentConversionBusyError,
    DocumentConversionFailedError,
    DocumentConversionTimeoutError,
    DocumentConversionUnavailableError,
    InvalidLegacyDocError,
    UnsupportedDocumentFormatError,
)

LEGACY_DOC_SIGNATURE = bytes.fromhex("D0CF11E0A1B11AE1")
_CONVERSION_SLOT = threading.BoundedSemaphore(value=1)


def _office_executable() -> str:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable is None:
        raise DocumentConversionUnavailableError()
    return executable


def _terminate(process: subprocess.Popen[bytes]) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        with suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
        with suppress(ChildProcessError):
            process.wait()


def convert_legacy_doc(source: Path, target: Path, *, timeout_seconds: int = 60) -> None:
    """Convert an OLE Word DOC into a DOCX without modifying the source file."""
    try:
        with source.open("rb") as handle:
            signature = handle.read(len(LEGACY_DOC_SIGNATURE))
    except OSError as exc:
        raise InvalidLegacyDocError("无法读取旧版 Word DOC 文档") from exc
    if signature != LEGACY_DOC_SIGNATURE:
        raise InvalidLegacyDocError()

    executable = _office_executable()
    with tempfile.TemporaryDirectory(prefix="paper-setting-doc-convert-") as temporary:
        root = Path(temporary)
        input_path = root / "source.doc"
        output_dir = root / "output"
        profile_dir = root / "profile"
        home_dir = root / "home"
        output_dir.mkdir()
        profile_dir.mkdir()
        home_dir.mkdir()
        shutil.copyfile(source, input_path)
        environment = {
            key: os.environ[key]
            for key in ("PATH", "LANG", "LC_ALL", "TMPDIR", "FONTCONFIG_FILE")
            if key in os.environ
        }
        environment["HOME"] = str(home_dir)
        environment["SAL_DISABLE_OPENCL"] = "1"
        command = [
            executable,
            "--headless",
            "--nologo",
            "--norestore",
            "--nodefault",
            "--nolockcheck",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile_dir.as_uri()}",
            "--convert-to",
            "docx:Office Open XML Text",
            "--outdir",
            str(output_dir),
            str(input_path),
        ]
        try:
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=environment,
                start_new_session=True,
            )
        except OSError as exc:
            raise DocumentConversionUnavailableError() from exc
        try:
            process.communicate(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as exc:
            _terminate(process)
            raise DocumentConversionTimeoutError() from exc
        converted = output_dir / "source.docx"
        if process.returncode != 0 or not converted.is_file() or converted.stat().st_size == 0:
            raise DocumentConversionFailedError()
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary_target = target.with_suffix(target.suffix + ".tmp")
        shutil.copyfile(converted, temporary_target)
        os.replace(temporary_target, target)


@contextmanager
def normalized_manuscript(
    source: Path,
    *,
    source_filename: str,
    timeout_seconds: int = 60,
) -> Iterator[Path]:
    suffix = Path(source_filename).suffix.lower()
    if suffix == ".docx":
        yield source
        return
    if suffix != ".doc":
        raise UnsupportedDocumentFormatError()
    if not _CONVERSION_SLOT.acquire(blocking=False):
        raise DocumentConversionBusyError()
    try:
        with tempfile.TemporaryDirectory(prefix="paper-setting-normalized-") as temporary:
            converted = Path(temporary) / "source.docx"
            convert_legacy_doc(source, converted, timeout_seconds=timeout_seconds)
            yield converted
    finally:
        _CONVERSION_SLOT.release()
