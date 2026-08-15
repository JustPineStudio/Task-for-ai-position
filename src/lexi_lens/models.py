from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, model_validator


class Article(BaseModel):
    url: str
    title: str
    author: str | None = None
    published_at: str | None = None
    text: str = Field(min_length=200)

    @property
    def word_count(self) -> int:
        return len(self.text.split())


class CriterionScore(BaseModel):
    criterion: str = Field(description="Criterion name, exactly as supplied")
    score: int = Field(ge=0, le=100)
    rationale: str = Field(min_length=20, max_length=700)
    evidence: list[str] = Field(min_length=1, max_length=3)
    improvement: str = Field(min_length=10, max_length=400)
    evidence_valid: bool = True


class AgentEvaluation(BaseModel):
    agent_id: str
    perspective: str
    criteria: list[CriterionScore] = Field(min_length=3, max_length=5)
    summary: str = Field(min_length=40, max_length=1000)


class AgentResult(AgentEvaluation):
    score: float = Field(ge=0, le=100)
    weight: float = Field(gt=0, le=1)
    sample_scores: list[float] = Field(default_factory=list)


class ContentProfile(BaseModel):
    content_type: str = Field(description="e.g. educational, case-study, sales, thought-leadership")
    target_audience: str = Field(min_length=3, max_length=200)
    primary_goal: str = Field(min_length=10, max_length=300)
    reader_stage: str = Field(min_length=3, max_length=100)
    success_criteria: list[str] = Field(min_length=2, max_length=5)
    rationale: str = Field(min_length=20, max_length=500)


class ContentBrief(BaseModel):
    content_type: str | None = None
    target_audience: str | None = None
    primary_goal: str | None = None
    reader_stage: str | None = None
    desired_action: str | None = None
    tone: str | None = None
    channel: str | None = None
    success_criteria: list[str] | None = None


class ScoreDimension(BaseModel):
    name: str
    score: float = Field(ge=0, le=100)
    rationale: str = Field(min_length=15, max_length=500)


class OutcomeAssessment(BaseModel):
    dimensions: list[ScoreDimension] = Field(min_length=4, max_length=4)
    publish_readiness: str = Field(pattern="^(ready|minor_edits|major_revision|not_ready)$")
    readiness_reason: str = Field(min_length=20, max_length=500)


class TextDiagnostics(BaseModel):
    sentence_count: int
    paragraph_count: int
    heading_count: int
    average_sentence_words: float
    average_paragraph_words: float
    long_sentence_ratio: float
    long_paragraph_ratio: float
    repeated_phrases: list[str]
    second_person_singular: int
    second_person_plural: int
    estimated_reading_minutes: float


class ArticleSegment(BaseModel):
    segment_id: str
    heading: str
    text: str
    word_count: int


class SegmentAssessment(BaseModel):
    segment_id: str
    heading: str
    score: int = Field(ge=0, le=100)
    role: str = Field(min_length=3, max_length=120)
    strength: str = Field(min_length=15, max_length=400)
    issue: str = Field(min_length=15, max_length=400)


class SegmentReport(BaseModel):
    assessments: list[SegmentAssessment] = Field(min_length=1)
    weakest_segment_id: str


class FinalSynthesis(BaseModel):
    outcomes: OutcomeAssessment
    segments: SegmentReport
    challenge: ChallengeReport
    editorial_plan: EditorialPlan


class ChallengeFinding(BaseModel):
    agent_id: str
    criterion: str
    severity: str = Field(pattern="^(low|medium|high)$")
    issue: str = Field(min_length=20, max_length=500)
    recommended_adjustment: int = Field(ge=-30, le=30)


class ChallengeReport(BaseModel):
    findings: list[ChallengeFinding] = Field(default_factory=list, max_length=12)
    summary: str = Field(min_length=20, max_length=700)


class ConfidenceReport(BaseModel):
    level: str = Field(pattern="^(low|medium|high)$")
    score_min: float = Field(ge=0, le=100)
    score_max: float = Field(ge=0, le=100)
    standard_deviation: float = Field(ge=0)
    largest_disagreement: str
    sample_count: int = Field(ge=1)


class RewriteSuggestion(BaseModel):
    before: str = Field(min_length=3, max_length=700)
    after: str = Field(min_length=3, max_length=900)
    reason: str = Field(min_length=15, max_length=400)
    validation: RewriteValidation | None = None


class RewriteValidation(BaseModel):
    preserves_meaning: bool
    introduces_unsupported_claim: bool
    matches_tone: bool
    solves_stated_problem: bool
    quality: str = Field(pattern="^(better|different|worse)$")
    explanation: str = Field(min_length=20, max_length=500)


class EditorialPriority(BaseModel):
    rank: int = Field(ge=1, le=3)
    title: str = Field(min_length=3, max_length=120)
    impact: str = Field(min_length=20, max_length=400)
    action: str = Field(min_length=20, max_length=600)
    source_agents: list[str] = Field(min_length=1, max_length=4)
    rewrites: list[RewriteSuggestion] = Field(min_length=1, max_length=2)


class EditorialPlan(BaseModel):
    priorities: list[EditorialPriority] = Field(min_length=3, max_length=3)


class AnalysisReport(BaseModel):
    url: str
    title: str
    word_count: int
    model: str
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    overall_score: float = Field(ge=0, le=100)
    grade: str
    verdict: str
    content_profile: ContentProfile
    supplied_brief: ContentBrief | None = None
    outcomes: OutcomeAssessment
    diagnostics: TextDiagnostics
    segments: SegmentReport
    confidence: ConfidenceReport
    challenge: ChallengeReport
    editorial_plan: EditorialPlan
    agents: list[AgentResult] = Field(min_length=3)

    @model_validator(mode="after")
    def weights_sum_to_one(self) -> AnalysisReport:
        if abs(sum(agent.weight for agent in self.agents) - 1) > 0.001:
            raise ValueError("Agent weights must sum to 1")
        return self
