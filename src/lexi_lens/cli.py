from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Annotated

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from lexi_lens.benchmark import benchmark as run_benchmark
from lexi_lens.evaluator import OpenAIProvider, analyze
from lexi_lens.models import AnalysisReport, ContentBrief
from lexi_lens.scraper import scrape_article

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

app = typer.Typer(help="Procijeni kvalitetu Lexi članka s četiri AI agenta.")
console = Console()


@app.callback()
def main() -> None:
    """Provjerljiva multi-agent evaluacija Lexi sadržaja."""


@app.command()
def evaluate(
    url: Annotated[str, typer.Argument(help="HTTPS URL Lexi blog posta ili case studyja")],
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Spremi puni JSON rezultat")
    ] = None,
    model: Annotated[str | None, typer.Option(help="OpenAI model; inače LEXI_LENS_MODEL")] = None,
    brief: Annotated[
        Path | None, typer.Option("--brief", help="JSON datoteka s ciljem, publikom i tonom")
    ] = None,
) -> None:
    """Scrape and evaluate one Lexi article."""
    load_dotenv()
    selected_model = model or os.getenv("LEXI_LENS_MODEL", "gpt-5.6-luna")
    if not os.getenv("OPENAI_API_KEY"):
        console.print(
            "[red]Nedostaje OPENAI_API_KEY. Kopiraj .env.example u .env i dodaj ključ.[/red]"
        )
        raise typer.Exit(2)
    try:
        with console.status("Dohvaćam i čistim članak…"):
            supplied_brief = _load_brief(brief) if brief else None
            report = asyncio.run(_run(url, selected_model, supplied_brief))
    except Exception as exc:
        console.print(f"[red]Analiza nije uspjela:[/red] {exc}")
        raise typer.Exit(1) from exc
    _render(report)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        console.print(f"\nPuni rezultat spremljen u [cyan]{output}[/cyan]")


def _load_brief(path: Path) -> ContentBrief:
    try:
        return ContentBrief.model_validate(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError) as exc:
        raise typer.BadParameter(f"Ne mogu učitati brief: {exc}") from exc


async def _run(url: str, model: str, brief: ContentBrief | None) -> AnalysisReport:
    article = await scrape_article(url)
    return await analyze(article, OpenAIProvider(model), model, brief=brief)


def _render(report: AnalysisReport) -> None:
    console.print(
        Panel.fit(
            f"[bold]{report.overall_score:.1f}/100 · {report.grade}[/bold]\n"
            f"{report.verdict}\n"
            f"Pouzdanost: {report.confidence.level} "
            f"({report.confidence.score_min:.1f}–{report.confidence.score_max:.1f})",
            title=report.title,
            subtitle=f"{report.word_count} riječi · {report.model}",
        )
    )
    table = Table(title="Rezultat po agentu")
    table.add_column("Perspektiva", style="cyan")
    table.add_column("Ocjena", justify="right")
    table.add_column("Sažetak")
    for agent in report.agents:
        table.add_row(agent.perspective, f"{agent.score:.1f}", agent.summary)
    console.print(table)
    dimensions = Table(title=f"Spremnost za objavu: {report.outcomes.publish_readiness}")
    dimensions.add_column("Dimenzija")
    dimensions.add_column("Ocjena", justify="right")
    for dimension in report.outcomes.dimensions:
        dimensions.add_row(dimension.name, f"{dimension.score:.1f}")
    console.print(dimensions)
    console.print(
        f"\n[bold]Profil:[/bold] {report.content_profile.content_type} · "
        f"{report.content_profile.target_audience}\n"
        f"[bold]Cilj:[/bold] {report.content_profile.primary_goal}"
    )
    priorities = Table(title="Tri najvažnije uredničke promjene")
    priorities.add_column("#", justify="right")
    priorities.add_column("Prioritet", style="yellow")
    priorities.add_column("Akcija")
    for priority in sorted(report.editorial_plan.priorities, key=lambda item: item.rank):
        priorities.add_row(str(priority.rank), priority.title, priority.action)
    console.print(priorities)
    weakest = next(
        item
        for item in report.segments.assessments
        if item.segment_id == report.segments.weakest_segment_id
    )
    console.print(
        f"\n[bold]Najslabiji segment:[/bold] {weakest.heading} "
        f"({weakest.score}/100) — {weakest.issue}"
    )


@app.command("benchmark")
def benchmark_command(
    results: Annotated[Path, typer.Argument(help="Direktorij JSON rezultata")],
    labels: Annotated[Path, typer.Argument(help="JSON s ljudskim ocjenama")],
) -> None:
    """Usporedi spremljene rezultate s ocjenama ljudskih urednika."""
    result = run_benchmark(results, labels)
    console.print(
        f"Članci: {result.matched_articles}\n"
        f"MAE: {result.mean_absolute_error}\n"
        f"RMSE: {result.root_mean_squared_error}\n"
        f"Unutar ±5 bodova: {result.within_five_points:.1%}"
    )


if __name__ == "__main__":
    app()
