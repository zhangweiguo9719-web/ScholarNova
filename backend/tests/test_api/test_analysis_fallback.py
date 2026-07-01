from app.api.v1.analysis import _build_fallback_analysis, _build_missing_content_analysis


def test_fallback_analysis_uses_only_available_paper_information():
    result = _build_fallback_analysis(
        {
            "title": "A Test Paper",
            "authors": "Ada Lovelace",
            "year": 2026,
            "venue": "Test Conference",
            "abstract": "This abstract states the supported finding.",
        },
        "What is the contribution?",
    )

    assert "基础分析（模型服务暂时不可用）" in result
    assert "A Test Paper" in result
    assert "Ada Lovelace" in result
    assert "This abstract states the supported finding." in result
    assert "What is the contribution?" in result
    assert "不包含摘要之外的推断" in result


def test_missing_content_analysis_refuses_to_invent_details():
    result = _build_missing_content_analysis(
        {
            "title": "Metadata Only Paper",
            "authors": "Researcher",
            "year": 2025,
            "venue": "Test Venue",
            "abstract": None,
        },
        "Describe the experiments",
    )

    assert "信息不足，未执行推断性分析" in result
    assert "避免生成未经论文支持" in result
    assert "Describe the experiments" in result
