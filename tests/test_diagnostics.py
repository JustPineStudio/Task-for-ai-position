import json

from lexi_lens.benchmark import benchmark
from lexi_lens.diagnostics import analyze_text, segment_article


def test_diagnostics_and_segments_are_deterministic() -> None:
    text = (
        """Uvod je kratak. Druga rečenica obraća se tebi.

## Prvi dio

Ovo je sadržaj prvog dijela. """
        + "vrlo duga riječ " * 35
    )
    diagnostics = analyze_text(text)
    segments = segment_article(text)
    assert diagnostics.heading_count == 1
    assert diagnostics.sentence_count >= 3
    assert diagnostics.long_sentence_ratio > 0
    assert [item.segment_id for item in segments] == ["intro", "section-1"]


def test_benchmark_compares_saved_report_to_human_label(tmp_path) -> None:
    source = __import__("pathlib").Path("output/example.json")
    results = tmp_path / "results"
    results.mkdir()
    (results / "report.json").write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    labels = tmp_path / "labels.json"
    labels.write_text(
        json.dumps(
            [
                {
                    "url": "https://lexi.hr/psiholoski-mehanizmi-iza-clickbaita/",
                    "overall_score": 80.2,
                }
            ]
        ),
        encoding="utf-8",
    )
    result = benchmark(results, labels)
    assert result.matched_articles == 1
    assert result.mean_absolute_error == 2.0
