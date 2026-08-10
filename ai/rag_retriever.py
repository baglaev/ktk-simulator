"""Small BM25-style retriever for a local RAG knowledge index."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass

from .rag_documents import DocumentChunk, KnowledgeIndex


_TOKEN_PATTERN = re.compile(r"[a-zа-яё0-9]+(?:-[a-zа-яё0-9]+)*", re.IGNORECASE)
_STOP_WORDS = {
    "а",
    "без",
    "бы",
    "в",
    "во",
    "для",
    "до",
    "его",
    "ее",
    "и",
    "из",
    "или",
    "как",
    "какая",
    "какие",
    "какой",
    "к",
    "на",
    "не",
    "о",
    "об",
    "от",
    "по",
    "при",
    "с",
    "со",
    "что",
    "это",
}


@dataclass(frozen=True)
class SearchResult:
    chunk: DocumentChunk
    score: float


class LocalRetriever:
    """Rank indexed chunks without a vector database or network calls."""

    def __init__(self, index: KnowledgeIndex) -> None:
        self.index = index
        self._tokenized = [tokenize(chunk.content) for chunk in index.chunks]
        self._term_frequencies = [Counter(tokens) for tokens in self._tokenized]
        self._document_frequencies: Counter[str] = Counter()
        for tokens in self._tokenized:
            self._document_frequencies.update(set(tokens))
        self._average_length = (
            sum(len(tokens) for tokens in self._tokenized) / len(self._tokenized)
            if self._tokenized
            else 0.0
        )

    def search(
        self,
        query: str,
        *,
        limit: int = 4,
        min_score: float = 0.2,
        max_per_source: int = 2,
    ) -> tuple[SearchResult, ...]:
        if limit <= 0 or max_per_source <= 0:
            return ()
        query_tokens = tokenize(query)
        if not query_tokens or not self.index.chunks:
            return ()

        query_terms = Counter(query_tokens)
        scored: list[SearchResult] = []
        for position, chunk in enumerate(self.index.chunks):
            score = self._bm25_score(position, query_terms)
            if _normalize_for_match(query) in _normalize_for_match(chunk.content):
                score += 1.5
            if score >= min_score:
                scored.append(SearchResult(chunk=chunk, score=score))
        scored.sort(key=lambda item: (-item.score, item.chunk.source_ref))
        selected: list[SearchResult] = []
        source_counts: Counter[str] = Counter()
        for result in scored:
            source_path = result.chunk.source_path
            if source_counts[source_path] >= max_per_source:
                continue
            selected.append(result)
            source_counts[source_path] += 1
            if len(selected) >= limit:
                break
        return tuple(selected)

    def _bm25_score(self, position: int, query_terms: Counter[str]) -> float:
        total_documents = len(self.index.chunks)
        frequencies = self._term_frequencies[position]
        document_length = len(self._tokenized[position])
        average_length = self._average_length or 1.0
        k1 = 1.5
        b = 0.75
        score = 0.0
        for term, query_frequency in query_terms.items():
            term_frequency = frequencies.get(term, 0)
            if term_frequency == 0:
                continue
            document_frequency = self._document_frequencies[term]
            inverse_frequency = math.log(
                1 + (total_documents - document_frequency + 0.5)
                / (document_frequency + 0.5)
            )
            denominator = term_frequency + k1 * (
                1 - b + b * document_length / average_length
            )
            score += (
                inverse_frequency
                * term_frequency
                * (k1 + 1)
                / denominator
                * query_frequency
            )
        return score


def tokenize(text: str) -> tuple[str, ...]:
    raw_tokens = [token.casefold().replace("ё", "е") for token in _TOKEN_PATTERN.findall(text)]
    expanded: list[str] = []
    for token in raw_tokens:
        if token not in _STOP_WORDS:
            expanded.append(token)
        if "-" in token:
            joined = token.replace("-", "")
            if joined and joined not in _STOP_WORDS:
                expanded.append(joined)
            expanded.extend(
                part for part in token.split("-") if part and part not in _STOP_WORDS
            )
    return tuple(expanded)


def _normalize_for_match(text: str) -> str:
    return " ".join(tokenize(text))
