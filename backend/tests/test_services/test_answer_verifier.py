"""Deterministic tests for FTI-3A answer verification."""

from app.services.inference import build_retrieval_fallback, verify_answer_citations


def test_verifier_accepts_complete_valid_citations() -> None:
    result = verify_answer_citations(
        "方法采用混合检索。[S1]\n实验结果显示召回率提升。[S2]",
        ["S1", "S2"],
    )

    assert result.status == "verified"
    assert result.coverage == 1.0
    assert result.uncited_claim_count == 0
    assert result.used_citation_ids == ("S1", "S2")


def test_verifier_marks_uncited_claims_as_partial() -> None:
    result = verify_answer_citations(
        "方法采用混合检索。[S1]\n实验仍需要跨领域验证。",
        ["S1"],
    )

    assert result.status == "partial"
    assert result.coverage == 0.5
    assert result.uncited_claim_count == 1


def test_verifier_rejects_unknown_source_ids() -> None:
    result = verify_answer_citations(
        "The method improves traceability. [S9]",
        ["S1"],
    )

    assert result.status == "failed"
    assert result.invalid_citation_ids == ("S9",)


def test_retrieval_fallback_remains_fully_traceable() -> None:
    answer = build_retrieval_fallback(
        "请总结证据",
        [
            ("S1", "第一篇论文", "研究采用可追溯证据片段。"),
            ("S2", "第二篇论文", "研究保留页码和章节定位。"),
        ],
    )
    result = verify_answer_citations(answer, ["S1", "S2"])

    assert result.status == "verified"
    assert result.coverage == 1.0
    assert "[S1]" in answer
    assert "[S2]" in answer
