from __future__ import annotations

import re

HEADING_1 = re.compile(r"^(第[一二三四五六七八九十百0-9]+章|[一二三四五六七八九十]+[、．.])")
HEADING_3 = re.compile(r"^\d+\.\d+\.\d+(?:\s|　|[^.\d])")
HEADING_4 = re.compile(r"^\d+\.\d+\.\d+\.\d+(?:\s|　|[^.\d])")
HEADING_2 = re.compile(r"^\d+\.\d+(?:\s|　|[^.\d])")
REFERENCE_ENTRY = re.compile(
    r"^(\[\d+\]|\d+[.、]|【(?:文献)?\d+.*?】|\^\[\d+\]|\[Ref:?\s*\d+.*?\]|\*\d+\*|[（(]\d+[)）]|“参考文献[一二三四五六七八九十\d]+”[：:])"
)
ACADEMIC_REFERENCE = re.compile(
    r"(?:\[[JMDCRNPSZ]\]|\[EB/OL\]|\[DB/OL\]|\[M/CD\]|\[C//\w+\]|DOI:\s*10\.|doi\.org/10\.)"
    r"|(?:^\[\d+\]\s*[A-Za-z\u4e00-\u9fa5])"
    r"|(?:^\d+[.、]\s*[A-Za-z\u4e00-\u9fa5].*?(?:\[[A-Z/]+\]|\b(?:19|20)\d{2}\b))"
    r"|(?:^[（(]\d+[)）]\s*.*?(?:(?:19|20)\d{2}|未公开发表|内部交流|技术报告))"
    r"|(?:^“参考文献.*?”[：:])",
    re.I,
)
KEYWORDS = re.compile(r"^(关键词|关键字|Key\s*Words?)\s*[：:]", re.I)


def division_role(text: str) -> str | None:
    """Recognize actual division titles, allowing Word's full/half-width spaces."""
    value = re.sub(r"\s+", "", text).lower()
    exact = {
        "摘要": "abstract_heading",
        "abstract": "abstract_heading",
        "参考文献": "bibliography_heading",
        "references": "bibliography_heading",
        "目录": "toc_heading",
        "图目录": "figure_list_heading",
        "表目录": "table_list_heading",
        "致谢": "acknowledgments_heading",
        "符号说明": "symbols_heading",
        "符号和缩略语说明": "symbols_heading",
        "作者简历": "cv_heading",
        "作者简历及攻读学位期间发表的学术论文与其他相关学术成果": "cv_heading",
    }
    if value in exact:
        return exact[value]
    clean_val = re.sub(r"[:：;；\s]+$", "", value)
    if clean_val in exact:
        return exact[clean_val]
    if re.match(
        r"^(?:主要)?参考文献(?:\s*[/／\-_(（]\s*(?:references?|bibliography)\s*[)）]?)?[:：]?$",
        text.strip(),
        re.I,
    ):
        return "bibliography_heading"
    if re.match(r"^(?:references?|bibliography)[:：]?$", text.strip(), re.I):
        return "bibliography_heading"
    if re.match(r"^附录(?:[一二三四五六七八九十A-Z0-9]+)?(?:\s|[：:]|$)", text.strip()):
        return "appendix_heading"
    return None


def classify_paragraph(
    text: str,
    style_name: str | None,
    *,
    order: int,
    in_abstract: bool = False,
    in_references: bool = False,
    story: str = "body",
) -> tuple[str, float]:
    value = text.strip()
    style = (style_name or "").strip().lower()
    if not value:
        return "empty", 1.0
    if story == "table":
        return "table_body", 0.99
    if story in {"header", "footer"}:
        return story, 0.99
    if style.startswith("papersetting."):
        role = style.removeprefix("papersetting.").split(".", 1)[0]
        return role, 0.99
    # Generated lists are not headings/captions even when their text looks identical.
    toc = re.fullmatch(r"(?:toc|目录)\s*([1-9])", style)
    if toc:
        return f"toc_entry_{toc.group(1)}", 0.99
    if style in {"table of figures", "图表目录"}:
        return "figure_table_list_entry", 0.99
    division = division_role(value)
    if division:
        return division, 0.99
    if value in {"博士/硕士学位论文", "博士学位论文", "硕士学位论文"}:
        return "degree_label", 0.99
    if re.fullmatch(r"[,，\s]+", value):
        return "template_placeholder", 0.95
    if re.match(
        r"^(注[（(]注的内容在最后的论文里需要删除|如没有附录.*删除该页|如果存在多个附录则删除该页)",
        value,
    ):
        return "template_instruction", 0.99
    if in_references and re.match(
        r"^(著录格式[（(]|主要责任者\.\s*题名|[（(](顺序编码制|著者[—－-]出版年制)[）)]示例|正文[：:])",
        value,
    ):
        return "template_instruction", 0.98
    if in_references and value.rstrip("：:") in {
        "中文文献",
        "外文文献",
        "英文文献",
        "日文文献",
        "俄文文献",
        "中文",
        "英文",
        "外文",
        "电子资源",
        "普通图书",
        "论文集、会议集",
        "报告",
        "学位论文",
        "专利文献",
        "标准文献",
        "专著中析出文献",
        "报纸中析出文献",
        "档案资源",
        "期刊",
    }:
        return "bibliography_group_heading", 0.98
    if in_references:
        return "reference_entry", 0.98 if REFERENCE_ENTRY.match(value) else 0.94
    if order > 5 and ACADEMIC_REFERENCE.search(value):
        return "reference_entry", 0.96
    if style in {"title", "标题"}:
        return "paper_title", 0.99
    if style in {"heading 1", "标题 1", "标题1"}:
        return "heading_1", 0.99
    if style in {"heading 2", "标题 2", "标题2"}:
        return "heading_2", 0.99
    if style in {"heading 3", "标题 3", "标题3"}:
        return "heading_3", 0.99
    if style in {"heading 4", "标题 4", "标题4"}:
        return "heading_4", 0.99
    if KEYWORDS.match(value):
        return "keywords", 0.99
    if re.match(r"^Figure\s+\d+[-–—.]\d+", value, re.I):
        return "figure_caption_en", 0.98
    if re.match(r"^Table\s+\d+[-–—.]\d+", value, re.I):
        return "table_caption_en", 0.98
    if re.match(r"^图\s*[0-9一二三四五六七八九十]+[-—.、 ]", value):
        return "figure_caption", 0.98
    if re.match(r"^表\s*[0-9一二三四五六七八九十]+[-—.、 ]", value):
        return "table_caption", 0.98
    if HEADING_4.match(value):
        return "heading_4", 0.96
    if HEADING_3.match(value):
        return "heading_3", 0.96
    if HEADING_2.match(value):
        return "heading_2", 0.96
    if HEADING_1.match(value):
        return "heading_1", 0.96
    if in_abstract:
        return "abstract_body", 0.94
    if style in {"normal", "正文", "body text", "正文文本"} and len(value) >= 12:
        return "body", 0.95
    if order < 8 and 6 <= len(value) <= 60 and not re.search(r"[。！？；]$", value):
        return "paper_title", 0.72
    return "body", 0.76
