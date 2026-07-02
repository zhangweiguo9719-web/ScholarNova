from datetime import date
from types import SimpleNamespace

from app.services.evaluation.benchmark import evaluate_cases, extract_gold, extract_predictions
from scripts.run_official_benchmark import filter_by_snapshot_date, structured_result_limit


def test_pasa_answer_and_tree_are_supported():
    gold = {"extra": {"answer": ["Attention Is All You Need"]}}
    prediction = {
        "child": {
            "seed": [
                {"title": "Attention Is All You Need", "select_score": 0.9, "child": {}},
                {"title": "Unrelated", "select_score": 0.1, "child": {}},
            ]
        }
    }
    assert "attentionisallyouneed" in extract_gold(gold)
    assert extract_predictions(prediction)[0] == "attentionisallyouneed"


def test_micro_f1_and_efficiency():
    gold = [{"case_id": "q1", "answers": ["Paper A", "Paper B"]}]
    predictions = [{
        "case_id": "q1",
        "results": [{"title": "Paper A"}, {"title": "Paper C"}],
        "runtime_metrics": {
            "api_calls": 2,
            "latency_ms": 1200,
            "token_usage": {"total_tokens": 0},
        },
    }]
    report = evaluate_cases(gold, predictions)
    assert report["micro"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}
    assert report["efficiency"]["avg_api_calls"] == 2
    assert report["recall_at_k"]["20"] == 0.5


def test_asta_nested_gold_and_corpus_ids_are_supported():
    gold = [{
        "input": {"query_id": "semantic_1", "query": "test"},
        "scorer_criteria": {"known_to_be_good": ["123", "456"]},
    }]
    predictions = [{
        "case_id": "semantic_1",
        "results": [{"corpus_id": "123"}, {"corpus_id": "999"}],
    }]
    report = evaluate_cases(gold, predictions)
    assert report["cases"] == 1
    assert report["micro"] == {"precision": 0.5, "recall": 0.5, "f1": 0.5}


def test_pasa_released_qid_and_answer_fields_are_supported():
    gold = [{"qid": "RealScholarQuery_0", "answer": ["Paper A"]}]
    predictions = [{
        "case_id": "RealScholarQuery_0",
        "results": [{"title": "Paper A"}],
    }]
    report = evaluate_cases(gold, predictions)
    assert report["cases"] == 1
    assert report["micro"]["f1"] == 1.0


def test_structured_result_limit_reflects_query_selectivity():
    assert structured_result_limit(
        "Papers citing DistilBERT after 2022 with more than 50 citations",
        300,
    ) == 200
    assert structured_result_limit(
        "paper citing the T5 paper and the spider paper",
        300,
    ) == 50
    assert structured_result_limit("broad literature review", 300) == 300


def test_snapshot_filter_excludes_only_known_future_papers():
    papers = [
        SimpleNamespace(publication_date=date(2025, 5, 1)),
        SimpleNamespace(publication_date=date(2025, 6, 1)),
        SimpleNamespace(publication_date=None),
    ]
    filtered = filter_by_snapshot_date(papers, date(2025, 5, 31))
    assert filtered == [papers[0], papers[2]]
