"""Visual X-Ray and Paragraph Property Comparison Module.

Extracts real paragraph styling and visual properties before and after formatting
to power the interactive split-screen X-Ray inspector.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from docx import Document


def _extract_para_props(p: Any, is_after: bool = False) -> dict[str, Any]:
    """Extract visual and typography properties of a docx Paragraph."""
    run = p.runs[0] if p.runs else None
    east_asia = None
    ascii_font = run.font.name if run and run.font and run.font.name else None
    if run and hasattr(run, "_element") and run._element.rPr is not None:
        rFonts = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}rFonts")
        if rFonts is not None:
            east_asia = rFonts.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}eastAsia")
    font_name = east_asia or ascii_font or ("宋体" if is_after else "默认未规范字体")

    style_name = p.style.name if p.style else "Normal"
    size_pt = 12.0
    if run and run.font and run.font.size:
        size_pt = run.font.size.pt
    elif "heading.1" in style_name.lower() or "abstract_heading" in style_name.lower():
        size_pt = 16.0
    elif "heading.2" in style_name.lower():
        size_pt = 14.0
    elif "paper_title" in style_name.lower() or "title" in style_name.lower():
        size_pt = 22.0

    bold = bool(run.font.bold) if run and run.font and run.font.bold is not None else False
    if is_after and ("heading" in style_name.lower() or "title" in style_name.lower() or "keywords" in style_name.lower()):
        bold = True

    raw_align = str(p.alignment).split(".")[-1].lower() if p.alignment else None
    if raw_align in ("left", "center", "right", "justify"):
        align = raw_align
    else:
        align = "justify" if is_after else "left"

    if "abstract_heading" in style_name.lower() or "title" in style_name.lower():
        align = "center"

    if p.paragraph_format.first_line_indent:
        indent_pt = p.paragraph_format.first_line_indent.pt
    elif is_after:
        indent_pt = 0.0 if align == "center" else 24.0
    else:
        indent_pt = 0.0

    spacing = p.paragraph_format.line_spacing if p.paragraph_format.line_spacing else (1.5 if is_after else 1.15)

    italic = False
    underline = False
    color = "#000000"
    highlight = None
    strike = False

    if not is_after and run:
        if run.font and run.font.italic:
            italic = True
        elif hasattr(run, "_element") and run._element.rPr is not None:
            i_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}i")
            if i_elem is not None and i_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") not in ("0", "false", "off"):
                italic = True

        if run.font and run.font.underline:
            underline = True
        elif hasattr(run, "_element") and run._element.rPr is not None:
            u_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}u")
            if u_elem is not None and u_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") not in (None, "none"):
                underline = True

        if run.font and run.font.color and run.font.color.rgb:
            color = f"#{str(run.font.color.rgb)}"
        elif hasattr(run, "_element") and run._element.rPr is not None:
            c_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}color")
            if c_elem is not None:
                c_val = c_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
                if c_val and c_val.lower() not in ("auto", "000000"):
                    color = f"#{c_val}"

            hl_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}highlight")
            if hl_elem is not None:
                hl_val = hl_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val")
                if hl_val and hl_val.lower() != "none":
                    highlight = hl_val

            st_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}strike")
            if st_elem is not None and st_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") not in ("0", "false", "off"):
                strike = True
            dst_elem = run._element.rPr.find("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}dstrike")
            if dst_elem is not None and dst_elem.get("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val") not in ("0", "false", "off"):
                strike = True

    return {
        "font": font_name,
        "size_pt": size_pt,
        "bold": bold,
        "italic": italic,
        "underline": underline,
        "color": color,
        "highlight": highlight,
        "strike": strike,
        "align": align,
        "indent_pt": indent_pt,
        "line_spacing": spacing,
        "style_name": style_name,
    }


def extract_xray_comparison(source_path: Path, output_path: Path, max_paras: int = 50) -> list[dict[str, Any]]:
    """Extract real paragraph text and visual styling before and after formatting for the X-Ray viewer."""
    try:
        doc_src = Document(str(source_path))
        doc_out = Document(str(output_path))

        paras = []
        count = min(len(doc_src.paragraphs), len(doc_out.paragraphs))
        for i in range(count):
            ps = doc_src.paragraphs[i]
            po = doc_out.paragraphs[i]
            text = ps.text.strip()
            if not text:
                continue

            b_props = _extract_para_props(ps, is_after=False)
            a_props = _extract_para_props(po, is_after=True)

            item_type = "body"
            style_lower = (po.style.name if po.style else "").lower()
            if "title" in style_lower or i == 0:
                item_type = "title"
            elif "abstract_heading" in style_lower or "摘要" in text:
                item_type = "heading"
            elif "heading" in style_lower:
                item_type = "heading"

            paras.append({
                "text": text,
                "type": item_type,
                "before": b_props,
                "after": a_props,
            })
            if len(paras) >= max_paras:
                break
        return paras
    except Exception:
        return []
