import subprocess
import zipfile
from pathlib import Path

from lxml import etree
from paper_setting_core.rendering import service
from pytest import MonkeyPatch


def test_substitute_xml_fonts_changes_attributes_without_changing_text() -> None:
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    payload = f"""<?xml version="1.0" encoding="UTF-8"?>
    <w:document xmlns:w="{namespace}">
      <w:r>
        <w:rPr><w:rFonts w:ascii="Times New Roman" w:eastAsia="宋体" /></w:rPr>
        <w:t>正文仍然包含宋体这个词</w:t>
      </w:r>
    </w:document>
    """.encode()

    result = service._substitute_xml_fonts(payload, {"宋体": "Songti SC"})

    root = etree.fromstring(result)
    fonts = root.find(f".//{{{namespace}}}rFonts")
    assert fonts is not None
    for attribute in ("ascii", "hAnsi", "eastAsia", "cs"):
        assert fonts.get(f"{{{namespace}}}{attribute}") == "Songti SC"
    assert root.findtext(f".//{{{namespace}}}t") == "正文仍然包含宋体这个词"


def test_fontconfig_file_finds_bundled_runtime_from_wrapper(tmp_path: Path) -> None:
    executable = tmp_path / "dependencies" / "bin" / "override" / "soffice"
    executable.parent.mkdir(parents=True)
    executable.touch()
    expected = (
        tmp_path
        / "dependencies"
        / "native"
        / "libreoffice-headless"
        / "libreoffice"
        / "LibreOfficeDev.app"
        / "Contents"
        / "Resources"
        / "fontconfig"
        / "fonts.conf"
    )
    expected.parent.mkdir(parents=True)
    expected.touch()

    assert service._fontconfig_file(str(executable)) == expected


def test_render_pdf_uses_isolated_profile_and_bundled_fontconfig(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    document = tmp_path / "论文.docx"
    with zipfile.ZipFile(document, "w") as archive:
        archive.writestr("word/document.xml", b"<document />")
    original_payload = document.read_bytes()
    output_dir = tmp_path / "preview"
    executable = tmp_path / "soffice"
    executable.touch()
    fontconfig = tmp_path / "fonts.conf"
    fontconfig.touch()
    captured: dict[str, object] = {}

    monkeypatch.setattr(service.shutil, "which", lambda name: str(executable))
    monkeypatch.setattr(service, "_preview_font_substitutions", lambda: {})
    monkeypatch.setattr(service, "_fontconfig_file", lambda _: fontconfig)

    def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["command"] = command
        captured["environment"] = kwargs["env"]
        (output_dir / "论文.pdf").write_bytes(b"pdf")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(service.subprocess, "run", fake_run)

    status, detail, result = service.render_pdf(document, output_dir)

    assert (status, detail, result) == ("preview_ready", None, output_dir / "论文.pdf")
    command = captured["command"]
    assert isinstance(command, list)
    assert any(str(value).startswith("-env:UserInstallation=file:") for value in command)
    environment = captured["environment"]
    assert isinstance(environment, dict)
    assert environment["FONTCONFIG_FILE"] == str(fontconfig)
    assert environment["HOME"] != str(Path.home())
    assert document.read_bytes() == original_payload
