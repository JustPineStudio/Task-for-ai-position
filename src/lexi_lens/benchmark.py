from __future__ import annotations

import json
import math
from pathlib import Path

from pydantic import BaseModel, Field

from lexi_lens.models import AnalysisReport


class HumanLabel(BaseModel):
    url: str
    overall_score: float = Field(ge=0, le=100)
    top_priorities: list[str] = Field(default_factory=list, max_length=3)


class BenchmarkResult(BaseModel):
    matched_articles: int
    mean_absolute_error: float
    root_mean_squared_error: float
    within_five_points: float


def benchmark(results_dir: Path, labels_path: Path) -> BenchmarkResult:
    labels = {
        item.url: item
        for item in [HumanLabel.model_validate(row) for row in _load_rows(labels_path)]
    }
    pairs: list[tuple[float, float]] = []
    for path in results_dir.glob("*.json"):
        report = AnalysisReport.model_validate_json(path.read_text(encoding="utf-8"))
        if report.url in labels:
            pairs.append((report.overall_score, labels[report.url].overall_score))
    if not pairs:
        raise ValueError("No matching URLs between results and human labels")
    errors = [predicted - human for predicted, human in pairs]
    return BenchmarkResult(
        matched_articles=len(pairs),
        mean_absolute_error=round(sum(abs(error) for error in errors) / len(errors), 2),
        root_mean_squared_error=round(
            math.sqrt(sum(error**2 for error in errors) / len(errors)), 2
        ),
        within_five_points=round(sum(abs(error) <= 5 for error in errors) / len(errors), 3),
    )


def _load_rows(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("Human labels must be a JSON array")
    return data
