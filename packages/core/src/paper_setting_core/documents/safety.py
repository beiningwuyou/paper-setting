from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path, PurePosixPath

from paper_setting_core.errors import InvalidDocxError, UnsafeZipPackageError

REQUIRED_PARTS = {"[Content_Types].xml", "word/document.xml", "_rels/.rels"}


def _validate_archive(
    archive: zipfile.ZipFile,
    *,
    max_uncompressed_bytes: int,
    max_entries: int,
) -> None:
    entries = archive.infolist()
    if len(entries) > max_entries:
        raise UnsafeZipPackageError("DOCX 内部文件数量超过安全限制")
    total_size = 0
    names: set[str] = set()
    for entry in entries:
        pure_path = PurePosixPath(entry.filename)
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise UnsafeZipPackageError("DOCX 包含不安全的内部路径")
        if entry.flag_bits & 0x1:
            raise UnsafeZipPackageError("不支持加密的 DOCX 包")
        total_size += entry.file_size
        if total_size > max_uncompressed_bytes:
            raise UnsafeZipPackageError("DOCX 解压后体积超过安全限制")
        if entry.file_size > 100 * 1024 * 1024:
            raise UnsafeZipPackageError("DOCX 单个内部文件过大")
        names.add(entry.filename)
    if not REQUIRED_PARTS.issubset(names):
        raise InvalidDocxError("DOCX 缺少必要的 OOXML 部件")


def validate_docx_package(
    path: Path,
    *,
    max_upload_bytes: int = 50 * 1024 * 1024,
    max_uncompressed_bytes: int = 500 * 1024 * 1024,
    max_entries: int = 20_000,
) -> None:
    if path.suffix.lower() != ".docx":
        raise InvalidDocxError("只支持 .docx 文件")
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise InvalidDocxError("无法读取上传文件") from exc
    if size > max_upload_bytes:
        raise InvalidDocxError(f"文件超过 {max_upload_bytes} 字节限制")

    try:
        with zipfile.ZipFile(path) as archive:
            _validate_archive(
                archive,
                max_uncompressed_bytes=max_uncompressed_bytes,
                max_entries=max_entries,
            )
    except zipfile.BadZipFile as exc:
        raise InvalidDocxError() from exc


def validate_docx_bytes(
    payload: bytes,
    *,
    max_upload_bytes: int = 5 * 1024 * 1024,
    max_uncompressed_bytes: int = 50 * 1024 * 1024,
    max_entries: int = 5_000,
) -> None:
    if len(payload) > max_upload_bytes:
        raise InvalidDocxError(f"文件超过 {max_upload_bytes} 字节限制")
    try:
        with zipfile.ZipFile(BytesIO(payload)) as archive:
            _validate_archive(
                archive,
                max_uncompressed_bytes=max_uncompressed_bytes,
                max_entries=max_entries,
            )
    except zipfile.BadZipFile as exc:
        raise InvalidDocxError() from exc
