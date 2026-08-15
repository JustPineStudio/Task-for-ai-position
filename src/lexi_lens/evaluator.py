from __future__ import annotations

import asyncio
import html
import math
import re
import statistics
import unicodedata
from typing import Protocol

from openai import AsyncOpenAI

from lexi_lens.agents import AGENTS, AgentDefinition
from lexi_lens.diagnostics import analyze_text, segment_article
from lexi_lens.models import (
    AgentEvaluation,
    AgentResult,
    AnalysisReport,
    Article,
    ChallengeReport,
    ConfidenceReport,
    ContentBrief,
    ContentProfile,
    EditorialPlan,
    FinalSynthesis,
    OutcomeAssessment,
    SegmentReport,
)
from lexi_lens.prompts import (
    SYSTEM_PROMPT,
    build_agent_prompt,
    build_profile_prompt,
    build_synthesis_prompt,
)


class EvaluationError(RuntimeError):
    pass


class EvaluationProvider(Protocol):
    async def classify(
        self, article: Article, brief: ContentBrief | None = None
    ) -> ContentProfile: ...

    async def evaluate(
        self,
        agent: AgentDefinition,
        article: Article,
        profile: ContentProfile,
        correction: str | None = None,
    ) -> AgentEvaluation: ...

    async def synthesize(self, prompt: str) -> FinalSynthesis: ...


class OpenAIProvider:
    def __init__(self, model: str, client: AsyncOpenAI | None = None) -> None:
        self.model = model
        self.client = client or AsyncOpenAI()

    async def _parse(self, prompt: str, schema: type):
        response = await self.client.responses.parse(
            model=self.model,
            instructions=SYSTEM_PROMPT,
            input=prompt,
            text_format=schema,
        )
        if response.output_parsed is None:
            raise EvaluationError(f"Model did not return valid {schema.__name__}")
        return response.output_parsed

    async def classify(self, article: Article, brief: ContentBrief | None = None) -> ContentProfile:
        return await self._parse(build_profile_prompt(article, brief), ContentProfile)

    async def synthesize(self, prompt: str) -> FinalSynthesis:
        return await self._parse(prompt, FinalSynthesis)

    async def evaluate(
        self,
        agent: AgentDefinition,
        article: Article,
        profile: ContentProfile,
        correction: str | None = None,
    ) -> AgentEvaluation:
        return await self._parse(
            build_agent_prompt(agent, article, profile, correction), AgentEvaluation
        )


async def analyze(
    article: Article,
    provider: EvaluationProvider,
    model: str,
    agents: tuple[AgentDefinition, ...] = AGENTS,
    brief: ContentBrief | None = None,
) -> AnalysisReport:
    profile = await provider.classify(article, brief)
    diagnostics = analyze_text(article.text)
    article_segments = segment_article(article.text)
    tasks = [_evaluate_with_evidence_retry(provider, agent, article, profile) for agent in agents]
    raw = await asyncio.gather(*tasks)
    results = [
        _aggregate_samples(agent, [evaluation])
        for agent, evaluation in zip(agents, raw, strict=True)
    ]
    confidence = _measure_confidence(results, 1)
    synthesis = await provider.synthesize(
        build_synthesis_prompt(article, profile, results, diagnostics, article_segments)
    )
    _validate_outcomes(synthesis.outcomes)
    _validate_segments(article_segments, synthesis.segments)
    _validate_editorial_plan(article, synthesis.editorial_plan)
    _validate_rewrite_results(synthesis.editorial_plan)
    _apply_challenge(results, agents, synthesis.challenge)
    overall = round(sum(result.score * result.weight for result in results), 1)

    return AnalysisReport(
        url=article.url,
        title=article.title,
        word_count=article.word_count,
        model=model,
        overall_score=overall,
        grade=_grade(overall),
        verdict=_verdict(overall),
        content_profile=profile,
        supplied_brief=brief,
        outcomes=synthesis.outcomes,
        diagnostics=diagnostics,
        segments=synthesis.segments,
        confidence=confidence,
        challenge=synthesis.challenge,
        editorial_plan=synthesis.editorial_plan,
        agents=results,
    )


def _validate_outcomes(outcomes: OutcomeAssessment) -> None:
    expected = {
        "Kvaliteta pisanja",
        "Usklađenost s publikom",
        "Ostvarenje cilja",
        "Vjerodostojnost",
    }
    if {item.name for item in outcomes.dimensions} != expected:
        raise EvaluationError("Outcome assessment returned unexpected dimensions")


def _validate_segments(source, report: SegmentReport) -> None:
    expected = [segment.segment_id for segment in source]
    actual = [segment.segment_id for segment in report.assessments]
    if actual != expected or report.weakest_segment_id not in expected:
        raise EvaluationError("Segment assessment does not match source segments")


def _validate_rewrite_results(plan: EditorialPlan) -> None:
    if any(
        rewrite.validation is None for priority in plan.priorities for rewrite in priority.rewrites
    ):
        raise EvaluationError("Synthesis omitted rewrite validation")


async def _evaluate_with_evidence_retry(
    provider: EvaluationProvider,
    agent: AgentDefinition,
    article: Article,
    profile: ContentProfile,
) -> AgentEvaluation:
    result = await provider.evaluate(agent, article, profile)
    invalid = _invalid_evidence(result, article.text)
    if invalid:
        correction = (
            "Sljedeći citati nisu doslovno pronađeni u članku: "
            + " | ".join(repr(quote) for quote in invalid)
            + ". Vrati cijelu procjenu ponovno i koristi samo kratke doslovne citate."
        )
        result = await provider.evaluate(agent, article, profile, correction)
        invalid = _invalid_evidence(result, article.text)
    if invalid:
        raise EvaluationError(f"Agent {agent.id} returned unverifiable evidence: {invalid}")
    return result


def _invalid_evidence(result: AgentEvaluation, article_text: str) -> list[str]:
    haystack = _normalize_text(article_text)
    invalid: list[str] = []
    for criterion in result.criteria:
        criterion.evidence_valid = True
        for quote in criterion.evidence:
            if _normalize_text(quote) not in haystack:
                criterion.evidence_valid = False
                invalid.append(quote)
    return invalid


def _normalize_text(value: str) -> str:
    value = html.unescape(unicodedata.normalize("NFKC", value))
    value = value.translate(
        str.maketrans({"“": '"', "”": '"', "„": '"', "’": "'", "–": "-", "—": "-"})
    )
    return re.sub(r"\s+", " ", value).strip().casefold()


def _aggregate_samples(agent: AgentDefinition, evaluations: list[AgentEvaluation]) -> AgentResult:
    scored = [_validate_and_score(agent, evaluation) for evaluation in evaluations]
    base = scored[0].model_copy(deep=True)
    sample_scores = [result.score for result in scored]
    for index, criterion in enumerate(base.criteria):
        criterion.score = round(statistics.mean(result.criteria[index].score for result in scored))
        criterion.evidence = list(
            dict.fromkeys(quote for result in scored for quote in result.criteria[index].evidence)
        )[:3]
    base.score = round(statistics.mean(sample_scores), 1)
    base.sample_scores = sample_scores
    return base


def _validate_and_score(agent: AgentDefinition, result: AgentEvaluation) -> AgentResult:
    if result.agent_id != agent.id:
        raise EvaluationError(f"Expected agent_id {agent.id}, got {result.agent_id}")
    expected = [criterion.name for criterion in agent.criteria]
    actual = [criterion.criterion for criterion in result.criteria]
    if actual != expected:
        raise EvaluationError(f"Agent {agent.id} returned unexpected criteria: {actual}")
    score = round(
        sum(
            item.score * definition.weight
            for item, definition in zip(result.criteria, agent.criteria, strict=True)
        ),
        1,
    )
    return AgentResult(**result.model_dump(), score=score, weight=agent.weight)


def _measure_confidence(results: list[AgentResult], samples: int) -> ConfidenceReport:
    overall_samples = [
        sum(result.sample_scores[index] * result.weight for result in results)
        for index in range(samples)
    ]
    stdev = statistics.pstdev(overall_samples) if len(overall_samples) > 1 else 0.0
    spreads = {
        result.perspective: max(result.sample_scores) - min(result.sample_scores)
        for result in results
    }
    largest = max(spreads, key=spreads.get) if spreads else "Nema podataka"
    level = "high" if stdev < 2 else "medium" if stdev < 5 else "low"
    margin = max(2.0, 1.96 * stdev / math.sqrt(len(overall_samples)))
    center = statistics.mean(overall_samples)
    return ConfidenceReport(
        level=level,
        score_min=round(max(0, center - margin), 1),
        score_max=round(min(100, center + margin), 1),
        standard_deviation=round(stdev, 2),
        largest_disagreement=largest,
        sample_count=len(overall_samples),
    )


def _apply_challenge(
    results: list[AgentResult],
    agents: tuple[AgentDefinition, ...],
    challenge: ChallengeReport,
) -> None:
    by_id = {result.agent_id: result for result in results}
    definitions = {agent.id: agent for agent in agents}
    for finding in challenge.findings:
        result = by_id.get(finding.agent_id)
        if result is None:
            raise EvaluationError(f"Challenger referenced unknown agent {finding.agent_id}")
        criterion = next(
            (item for item in result.criteria if item.criterion == finding.criterion), None
        )
        if criterion is None:
            raise EvaluationError(f"Challenger referenced unknown criterion {finding.criterion}")
        criterion.score = max(0, min(100, criterion.score + finding.recommended_adjustment))
    for result in results:
        agent = definitions[result.agent_id]
        result.score = round(
            sum(
                item.score * definition.weight
                for item, definition in zip(result.criteria, agent.criteria, strict=True)
            ),
            1,
        )


def _validate_editorial_plan(article: Article, plan: EditorialPlan) -> None:
    ranks = [priority.rank for priority in plan.priorities]
    if sorted(ranks) != [1, 2, 3]:
        raise EvaluationError("Editorial priorities must be ranked exactly 1, 2, 3")
    haystack = _normalize_text(article.text)
    invalid = [
        rewrite.before
        for priority in plan.priorities
        for rewrite in priority.rewrites
        if _normalize_text(rewrite.before) not in haystack
    ]
    if invalid:
        raise EvaluationError(f"Editorial plan contains unverifiable before-text: {invalid}")


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _verdict(score: float) -> str:
    if score >= 90:
        return "Izvrsno napisan tekst"
    if score >= 80:
        return "Vrlo dobro napisan tekst"
    if score >= 70:
        return "Dobar tekst s jasnim prostorom za poboljšanje"
    if score >= 60:
        return "Solidna osnova, ali potrebna je značajna dorada"
    return "Tekst zahtijeva temeljitu doradu"
