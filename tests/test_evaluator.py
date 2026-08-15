import asyncio

import pytest

from lexi_lens.agents import AGENTS, AgentDefinition
from lexi_lens.evaluator import EvaluationError, _normalize_text, analyze
from lexi_lens.models import (
    AgentEvaluation,
    AgentResult,
    Article,
    ChallengeFinding,
    ChallengeReport,
    ContentProfile,
    CriterionScore,
    EditorialPlan,
    EditorialPriority,
    FinalSynthesis,
    OutcomeAssessment,
    RewriteSuggestion,
    RewriteValidation,
    ScoreDimension,
    SegmentAssessment,
    SegmentReport,
)


class FakeProvider:
    def __init__(self, scores: list[int] | None = None, invalid_first: bool = False) -> None:
        self.scores = iter(scores or [80] * 20)
        self.invalid_first = invalid_first
        self.corrections = 0
        self.active = 0
        self.max_active = 0

    async def classify(self, article: Article, brief=None) -> ContentProfile:
        return ContentProfile(
            content_type="educational",
            target_audience="Marketinški stručnjaci",
            primary_goal="Objasniti čitatelju praktičan princip pisanja.",
            reader_stage="awareness",
            success_criteria=["Jasno objašnjenje", "Primjenjiv savjet"],
            rationale="Naslov i sadržaj objašnjavaju koncept kroz praktičan primjer.",
        )

    async def assess_outcomes(self, prompt: str) -> OutcomeAssessment:
        return OutcomeAssessment(
            dimensions=[
                ScoreDimension(
                    name=name,
                    score=80,
                    rationale="Dimenzija je dobro podržana rezultatima procjene.",
                )
                for name in (
                    "Kvaliteta pisanja",
                    "Usklađenost s publikom",
                    "Ostvarenje cilja",
                    "Vjerodostojnost",
                )
            ],
            publish_readiness="minor_edits",
            readiness_reason=(
                "Tekst je kvalitetan, ali zahtijeva nekoliko ciljanih uredničkih izmjena."
            ),
        )

    async def assess_segments(self, prompt: str) -> SegmentReport:
        return SegmentReport(
            assessments=[
                SegmentAssessment(
                    segment_id="intro",
                    heading="Uvod",
                    score=75,
                    role="Glavni sadržaj",
                    strength="Jasno prenosi osnovnu poruku ciljanoj publici.",
                    issue="Može konkretnije završiti preporučenom sljedećom radnjom.",
                )
            ],
            weakest_segment_id="intro",
        )

    async def validate_rewrites(self, prompt: str) -> list[RewriteValidation]:
        return [
            RewriteValidation(
                preserves_meaning=True,
                introduces_unsupported_claim=False,
                matches_tone=True,
                solves_stated_problem=True,
                quality="better",
                explanation="Prijedlog čuva značenje i jasnije prenosi poruku bez novih tvrdnji.",
            )
            for _ in range(3)
        ]

    async def synthesize(self, prompt: str) -> FinalSynthesis:
        profile = await self.classify(Article(url="https://lexi.hr/x", title="x", text="x " * 100))
        outcomes = await self.assess_outcomes(prompt)
        segments = await self.assess_segments(prompt)
        challenge = await self.challenge(
            Article(url="https://lexi.hr/x", title="x", text="x " * 100), profile, []
        )
        editorial = await self.create_editorial_plan(
            Article(url="https://lexi.hr/x", title="x", text="x " * 100), profile, [], challenge
        )
        validations = await self.validate_rewrites(prompt)
        rewrites = [item for priority in editorial.priorities for item in priority.rewrites]
        for rewrite, validation in zip(rewrites, validations, strict=True):
            rewrite.validation = validation
        return FinalSynthesis(
            outcomes=outcomes,
            segments=segments,
            challenge=challenge,
            editorial_plan=editorial,
        )

    async def evaluate(
        self,
        agent: AgentDefinition,
        article: Article,
        profile: ContentProfile,
        correction: str | None = None,
    ) -> AgentEvaluation:
        self.active += 1
        self.max_active = max(self.max_active, self.active)
        await asyncio.sleep(0.01)
        self.active -= 1
        if correction:
            self.corrections += 1
        score = next(self.scores)
        evidence = "Izvorni dokaz iz članka"
        if self.invalid_first and not correction:
            evidence = "Izmišljeni citat"
        return AgentEvaluation(
            agent_id=agent.id,
            perspective=agent.perspective,
            criteria=[
                CriterionScore(
                    criterion=item.name,
                    score=score,
                    rationale="Obrazloženje koje je dovoljno dugo za validaciju modela.",
                    evidence=[evidence],
                    improvement="Konkretan prijedlog za poboljšanje.",
                )
                for item in agent.criteria
            ],
            summary="Sažetak procjene koji jasno objašnjava glavne prednosti i slabosti teksta.",
        )

    async def challenge(
        self, article: Article, profile: ContentProfile, results: list[AgentResult]
    ) -> ChallengeReport:
        return ChallengeReport(
            findings=[
                ChallengeFinding(
                    agent_id="structure",
                    criterion="Obećanje i fokus",
                    severity="medium",
                    issue="Ocjena je previsoka u odnosu na dokaz i svrhu edukativnog sadržaja.",
                    recommended_adjustment=-10,
                )
            ],
            summary="Jedna procjena zahtijeva korekciju nakon adversarial provjere.",
        )

    async def create_editorial_plan(
        self,
        article: Article,
        profile: ContentProfile,
        results: list[AgentResult],
        challenge: ChallengeReport,
        correction: str | None = None,
    ) -> EditorialPlan:
        return EditorialPlan(
            priorities=[
                EditorialPriority(
                    rank=rank,
                    title=f"Prioritet {rank}",
                    impact="Ova promjena izravno povećava razumljivost i korisnost sadržaja.",
                    action="Preoblikovati odabrani ulomak tako da jasnije vodi čitatelja.",
                    source_agents=["structure"],
                    rewrites=[
                        RewriteSuggestion(
                            before="Izvorni dokaz iz članka",
                            after=f"Jasnija verzija izvornog dokaza {rank}.",
                            reason="Nova verzija konkretnije prenosi glavnu poruku čitatelju.",
                        )
                    ],
                )
                for rank in range(1, 4)
            ]
        )


@pytest.fixture
def article() -> Article:
    return Article(
        url="https://lexi.hr/test",
        title="Test",
        text=" ".join(["Dovoljno dugačak sadržaj članka. Izvorni dokaz iz članka."] * 30),
    )


@pytest.mark.asyncio
async def test_complete_pipeline_is_parallel_and_deterministic(article: Article) -> None:
    provider = FakeProvider()
    report = await analyze(article, provider, "fake-model")
    assert report.overall_score == 79.1  # -10 × 30% criterion × 30% agent = -0.9
    assert report.grade == "C"
    assert report.content_profile.content_type == "educational"
    assert report.confidence.level == "high"
    assert report.confidence.sample_count == 1
    assert len(report.editorial_plan.priorities) == 3
    assert report.outcomes.publish_readiness == "minor_edits"
    assert report.diagnostics.estimated_reading_minutes > 0
    assert report.segments.weakest_segment_id == "intro"
    assert report.editorial_plan.priorities[0].rewrites[0].validation.quality == "better"
    assert provider.max_active == 4


@pytest.mark.asyncio
async def test_invalid_evidence_is_retried_once(article: Article) -> None:
    provider = FakeProvider(invalid_first=True)
    await analyze(article, provider, "fake-model")
    assert provider.corrections == 4


@pytest.mark.asyncio
async def test_rejects_wrong_agent_identity(article: Article) -> None:
    class WrongProvider(FakeProvider):
        async def evaluate(self, *args, **kwargs) -> AgentEvaluation:
            result = await super().evaluate(*args, **kwargs)
            result.agent_id = "wrong"
            return result

    with pytest.raises(EvaluationError, match="Expected agent_id"):
        await analyze(article, WrongProvider(), "fake-model", agents=AGENTS[:1])


def test_evidence_normalization_handles_quotes_dashes_and_whitespace() -> None:
    assert _normalize_text("„Dobar   tekst”—da") == _normalize_text('"Dobar tekst"-da')


@pytest.mark.asyncio
async def test_rejects_hallucinated_rewrite(article: Article) -> None:
    class BadPlanProvider(FakeProvider):
        async def create_editorial_plan(self, *args, **kwargs) -> EditorialPlan:
            plan = await super().create_editorial_plan(*args, **kwargs)
            plan.priorities[0].rewrites[0].before = "Tekst koji ne postoji"
            return plan

    with pytest.raises(EvaluationError, match="unverifiable before-text"):
        await analyze(article, BadPlanProvider(), "fake-model")
