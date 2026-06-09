from __future__ import annotations

import math
import re
from dataclasses import dataclass

from insights_repetition.types import ProblemRecord


def tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def record_key(record: ProblemRecord, fields: tuple[str, ...] = ("question", "topic")) -> str:
    parts: list[str] = []
    for field in fields:
        if field == "question":
            parts.append(record.question)
        elif field == "skill_text":
            parts.append(record.skill_text)
        else:
            value = record.metadata.get(field)
            if value:
                parts.append(str(value))
    return "\n".join(parts)


@dataclass(frozen=True)
class RetrievalHit:
    record: ProblemRecord
    score: float


class BM25Retriever:
    def __init__(
        self,
        records: list[ProblemRecord],
        *,
        fields: tuple[str, ...] = ("question", "topic"),
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.records = records
        self.documents = [record_key(record, fields) for record in records]
        self.tokenized = [tokenize(document) for document in self.documents]
        self.k1 = k1
        self.b = b
        self.doc_len = [len(doc) for doc in self.tokenized]
        self.avgdl = sum(self.doc_len) / max(len(self.doc_len), 1)
        self.idf: dict[str, float] = {}
        self.freqs: list[dict[str, int]] = []
        self._index()

    def _index(self) -> None:
        doc_counts: dict[str, int] = {}
        for doc in self.tokenized:
            freqs: dict[str, int] = {}
            for token in doc:
                freqs[token] = freqs.get(token, 0) + 1
            self.freqs.append(freqs)
            for token in freqs:
                doc_counts[token] = doc_counts.get(token, 0) + 1
        n_docs = max(len(self.tokenized), 1)
        for token, count in doc_counts.items():
            self.idf[token] = math.log(1 + (n_docs - count + 0.5) / (count + 0.5))

    def scores(self, query: str) -> list[float]:
        query_tokens = tokenize(query)
        out: list[float] = []
        for idx, freqs in enumerate(self.freqs):
            score = 0.0
            doc_len = self.doc_len[idx] or 1
            for token in query_tokens:
                freq = freqs.get(token, 0)
                if not freq:
                    continue
                denom = freq + self.k1 * (1 - self.b + self.b * doc_len / max(self.avgdl, 1e-9))
                score += self.idf.get(token, 0.0) * (freq * (self.k1 + 1) / max(denom, 1e-9))
            out.append(score)
        return out

    def top_k(self, query: str, k: int, *, exclude_question_id: str | None = None) -> list[RetrievalHit]:
        scored: list[RetrievalHit] = []
        for idx, score in enumerate(self.scores(query)):
            record = self.records[idx]
            if exclude_question_id and record.question_id == exclude_question_id:
                continue
            if score > 0:
                scored.append(RetrievalHit(record=record, score=score))
        scored.sort(key=lambda hit: hit.score, reverse=True)
        return scored[:k]
