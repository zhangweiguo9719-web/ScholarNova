from app.schemas.paper import PaperQuality
from app.services import journal_quality


def test_import_and_apply_licensed_quartiles(tmp_path, monkeypatch):
    data_path = tmp_path / "journal_rankings.json"
    monkeypatch.setattr(journal_quality, "_DATA_PATH", data_path)
    csv_text = "Journal,JCR Quartile,中科院分区,SJR Best Quartile,Year,Source\nTest Journal,Q1,2区,Q2,2025,licensed test file\n"

    status = journal_quality.import_ranking_content(csv_text, "rankings.csv")
    quality = journal_quality.apply_local_ranking(PaperQuality(), "Test Journal")

    assert status["entry_count"] == 1
    assert quality.jcr_quartile == "Q1"
    assert quality.cas_quartile == "2区"
    assert quality.sjr_quartile == "Q2"
    assert quality.partition_status == "verified_import"
    assert quality.partition_source == "licensed test file"


def test_import_rejects_files_without_quartiles(tmp_path, monkeypatch):
    monkeypatch.setattr(journal_quality, "_DATA_PATH", tmp_path / "rankings.json")
    try:
        journal_quality.import_ranking_content("Journal,Year\nTest Journal,2025\n", "bad.csv")
    except ValueError as exc:
        assert "没有识别到分区记录" in str(exc)
    else:
        raise AssertionError("missing quartiles should be rejected")
