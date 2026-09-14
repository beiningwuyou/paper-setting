import zipfile
from pathlib import Path

import pytest
from paper_setting_core.documents import validate_docx_package
from paper_setting_core.errors import InvalidDocxError, UnsafeZipPackageError


def test_rejects_non_docx(tmp_path: Path) -> None:
    path = tmp_path / "paper.docx"
    path.write_bytes(b"not-a-zip")
    with pytest.raises(InvalidDocxError):
        validate_docx_package(path)


def test_rejects_path_traversal(tmp_path: Path) -> None:
    path = tmp_path / "paper.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("_rels/.rels", "<Relationships/>")
        archive.writestr("word/document.xml", "<document/>")
        archive.writestr("../escape", "bad")
    with pytest.raises(UnsafeZipPackageError):
        validate_docx_package(path)

