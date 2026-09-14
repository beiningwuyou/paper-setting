from paper_setting_core.classification import classify_paragraph


def test_high_confidence_semantic_roles() -> None:
    assert classify_paragraph("摘要", "Normal", order=1) == ("abstract_heading", 0.99)
    assert classify_paragraph("1.2 研究方法", "Normal", order=5)[0] == "heading_2"
    assert classify_paragraph("图 2-1 架构", "Normal", order=8)[0] == "figure_caption"
    assert classify_paragraph("任意内容", "Heading 1", order=8) == ("heading_1", 0.99)
    assert classify_paragraph("自定义标题", "PaperSetting.heading_2", order=8) == (
        "heading_2",
        0.99,
    )
