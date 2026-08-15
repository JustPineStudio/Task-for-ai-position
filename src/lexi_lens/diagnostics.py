from __future__ import annotations

import re
from collections import Counter

from lexi_lens.models import ArticleSegment, TextDiagnostics

HEADING = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
SENTENCE = re.compile(r"(?<=[.!?])\s+")
WORD = re.compile(r"\b[\wÀ-ž'-]+\b", re.UNICODE)


def analyze_text(text: str) -> TextDiagnostics:
    plain = HEADING.sub("", text)
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", plain) if part.strip()]
    sentences = [item.strip() for item in SENTENCE.split(plain) if item.strip()]
    sentence_lengths = [len(WORD.findall(item)) for item in sentences]
    paragraph_lengths = [len(WORD.findall(item)) for item in paragraphs]
    words = [word.casefold() for word in WORD.findall(plain)]
    trigrams = Counter(" ".join(words[index : index + 3]) for index in range(len(words) - 2))
    repeated = [phrase for phrase, count in trigrams.most_common(10) if count >= 3]
    total_words = len(words)
    return TextDiagnostics(
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
        heading_count=len(HEADING.findall(text)),
        average_sentence_words=_mean(sentence_lengths),
        average_paragraph_words=_mean(paragraph_lengths),
        long_sentence_ratio=_ratio(sentence_lengths, 30),
        long_paragraph_ratio=_ratio(paragraph_lengths, 120),
        repeated_phrases=repeated[:5],
        second_person_singular=sum(words.count(word) for word in ("ti", "te", "tvoj", "tvoja")),
        second_person_plural=sum(words.count(word) for word in ("vi", "vas", "vaš", "vaša")),
        estimated_reading_minutes=round(total_words / 220, 1),
    )


def segment_article(text: str) -> list[ArticleSegment]:
    matches = list(HEADING.finditer(text))
    segments: list[ArticleSegment] = []
    intro_end = matches[0].start() if matches else len(text)
    intro = text[:intro_end].strip()
    if intro:
        segments.append(_segment("intro", "Uvod", intro))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body:
            segments.append(_segment(f"section-{index + 1}", match.group(2).strip(), body))
    if not segments:
        segments.append(_segment("article", "Cijeli članak", text))
    return segments


def _segment(segment_id: str, heading: str, text: str) -> ArticleSegment:
    return ArticleSegment(
        segment_id=segment_id, heading=heading, text=text, word_count=len(WORD.findall(text))
    )


def _mean(values: list[int]) -> float:
    return round(sum(values) / len(values), 1) if values else 0.0


def _ratio(values: list[int], threshold: int) -> float:
    return round(sum(value > threshold for value in values) / len(values), 3) if values else 0.0
