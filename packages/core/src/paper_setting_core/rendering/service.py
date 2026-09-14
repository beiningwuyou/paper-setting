from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from lxml import etree

FONT_CANDIDATES: dict[str, tuple[str, ...]] = {
    "宋体": ("SimSun", "Songti SC", "STSong", "Noto Serif CJK SC"),
    "黑体": ("SimHei", "Heiti SC", "STHeiti", "Noto Sans CJK SC"),
    "楷体": ("KaiTi", "Kaiti SC", "STKaiti", "Noto Serif CJK SC"),
    "仿宋": ("FangSong", "STFangsong", "Noto Serif CJK SC"),
}
FONT_ATTRIBUTE_NAMES = {"ascii", "hAnsi", "eastAsia", "cs", "name"}


def _available_font_families() -> set[str]:
    executable = shutil.which("fc-list")
    if executable is None:
        return set()
    try:
        result = subprocess.run(
            [executable, "--format=%{family}\n"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return set()
    if result.returncode != 0:
        return set()
    return {
        family.strip().casefold()
        for line in result.stdout.splitlines()
        for family in line.split(",")
        if family.strip()
    }


def _preview_font_substitutions() -> dict[str, str]:
    available = _available_font_families()
    return {
        requested: candidate
        for requested, candidates in FONT_CANDIDATES.items()
        if (candidate := next(
            (name for name in candidates if name.casefold() in available), None
        ))
    }


def _fontconfig_file(executable: str) -> Path | None:
    configured = os.environ.get("FONTCONFIG_FILE")
    if configured and (configured_path := Path(configured)).is_file():
        return configured_path

    executable_path = Path(executable).resolve()
    candidates = [
        executable_path.parent.parent / "Resources" / "fontconfig" / "fonts.conf",
        *(
            parent
            / "native"
            / "libreoffice-headless"
            / "libreoffice"
            / "LibreOfficeDev.app"
            / "Contents"
            / "Resources"
            / "fontconfig"
            / "fonts.conf"
            for parent in executable_path.parents[:5]
        ),
    ]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _substitute_xml_fonts(payload: bytes, substitutions: dict[str, str]) -> bytes:
    try:
        root = etree.fromstring(payload)
    except etree.XMLSyntaxError:
        return payload
    changed = False
    for element in root.iter():
        if etree.QName(element).localname == "rFonts":
            east_asia_attribute = next(
                (
                    attribute
                    for attribute in element.attrib
                    if etree.QName(attribute).localname == "eastAsia"
                ),
                None,
            )
            if east_asia_attribute is not None:
                replacement = substitutions.get(element.get(east_asia_attribute, ""))
                if replacement is not None:
                    namespace = etree.QName(east_asia_attribute).namespace
                    for name in ("ascii", "hAnsi", "eastAsia", "cs"):
                        element.set(f"{{{namespace}}}{name}", replacement)
                    changed = True
        for attribute, value in list(element.attrib.items()):
            if etree.QName(attribute).localname not in FONT_ATTRIBUTE_NAMES:
                continue
            font_name = value.decode() if isinstance(value, bytes) else value
            replacement = substitutions.get(font_name)
            if replacement is not None:
                element.set(attribute, replacement)
                changed = True
    return etree.tostring(root, encoding="UTF-8", xml_declaration=True) if changed else payload


def _copy_for_preview(
    source: Path,
    target: Path,
    substitutions: dict[str, str],
) -> None:
    with zipfile.ZipFile(source) as input_archive, zipfile.ZipFile(target, "w") as output_archive:
        for entry in input_archive.infolist():
            payload = input_archive.read(entry.filename)
            if substitutions and entry.filename.endswith(".xml"):
                payload = _substitute_xml_fonts(payload, substitutions)
            output_archive.writestr(entry, payload)


def render_pdf(
    document: Path,
    output_dir: Path,
    *,
    timeout_seconds: int = 90,
) -> tuple[str, str | None, Path | None]:
    executable = shutil.which("soffice") or shutil.which("libreoffice")
    if executable is None:
        return "preview_unavailable", "未找到 LibreOffice/soffice", None
    output_dir.mkdir(parents=True, exist_ok=True)
    expected = output_dir / f"{document.stem}.pdf"
    expected.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="paper-setting-render-") as temporary:
        temporary_directory = Path(temporary)
        preview_document = temporary_directory / document.name
        profile = temporary_directory / "libreoffice-profile"
        profile.mkdir()
        _copy_for_preview(document, preview_document, _preview_font_substitutions())
        environment = os.environ.copy()
        environment["HOME"] = str(temporary_directory)
        if fontconfig_file := _fontconfig_file(executable):
            environment["FONTCONFIG_FILE"] = str(fontconfig_file)
        try:
            result = subprocess.run(
                [
                    executable,
                    "--headless",
                    f"-env:UserInstallation={profile.resolve().as_uri()}",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(output_dir),
                    str(preview_document),
                ],
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=environment,
            )
        except subprocess.TimeoutExpired:
            return "preview_failed", "LibreOffice 渲染超时", None
    if result.returncode != 0 or not expected.exists():
        detail = (result.stderr or result.stdout or "LibreOffice 渲染失败").strip()[:500]
        return "preview_failed", detail, None
    return "preview_ready", None, expected
