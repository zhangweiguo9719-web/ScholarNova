from types import SimpleNamespace

from app.api.v1.analysis import _document_text


def test_document_context_includes_sections_figures_and_tables():
    document = SimpleNamespace(
        sections=[
            SimpleNamespace(heading="Methods", text="We train the proposed model."),
            SimpleNamespace(heading="Results", text="The model improves F1."),
        ],
        full_text="fallback",
        figures=[{"caption": "Figure 1: Overall architecture."}],
        tables=[{
            "page": 4,
            "caption": "Table 1: Main results.",
            "rows": [["Model", "F1"], ["Ours", "0.42"]],
        }],
    )

    context = _document_text(document)

    assert "Methods" in context
    assert "Figure 1: Overall architecture" in context
    assert "Ours | 0.42" in context
