from __future__ import annotations

import json
import unittest

from ai.openai_compatible import (
    CompletionResult,
    LLMConfigurationError,
)
from ai.rag_assistant import RAGAssistant
from ai.rag_documents import DocumentChunk, KnowledgeIndex, SourceType
from ai.rag_retriever import LocalRetriever


class FakeClient:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self.payload = payload
        self.error = error
        self.calls = 0

    def complete_json(self, *, system_prompt, user_payload):
        self.calls += 1
        if self.error:
            raise self.error
        return CompletionResult(
            content=json.dumps(self.payload, ensure_ascii=False),
            requested_model="openrouter/free",
            resolved_model="test/free",
            usage={"total_tokens": 10},
        )


def _retriever() -> LocalRetriever:
    chunk = DocumentChunk(
        chunk_id="1",
        source_ref="03_технологические_источники/насосы.pdf#1-page-2",
        source_path="03_технологические_источники/насосы.pdf",
        source_type=SourceType.TECHNOLOGY_SOURCE,
        locator="page-2",
        chunk_index=1,
        content="Н-1А относится к сырьевым насосам установки.",
    )
    return LocalRetriever(KnowledgeIndex(source_root="test", chunks=(chunk,)))


class RAGAssistantTests(unittest.TestCase):
    def test_grounded_answer_contains_only_used_sources(self) -> None:
        client = FakeClient(
            {
                "answer": "Н-1А указан как сырьевой насос [S1].",
                "usedSourceRefs": ["S1"],
                "insufficientEvidence": False,
            }
        )
        payload = RAGAssistant(_retriever(), client).ask("Что такое Н-1А?").to_payload()
        self.assertTrue(payload["provenance"]["llmUsed"])
        self.assertEqual(payload["sources"][0]["sourceType"], "technology_source")
        self.assertEqual(client.calls, 1)

    def test_no_retrieval_evidence_does_not_call_llm(self) -> None:
        client = FakeClient({})
        answer = RAGAssistant(_retriever(), client).ask("квантовый телепорт")
        self.assertTrue(answer.insufficient_evidence)
        self.assertEqual(client.calls, 0)

    def test_disabled_llm_returns_safe_retrieval_fallback(self) -> None:
        client = FakeClient(error=LLMConfigurationError("disabled"))
        answer = RAGAssistant(_retriever(), client).ask("Что такое Н-1А?")
        self.assertFalse(answer.provenance["llmUsed"])
        self.assertFalse(answer.provenance["llmAttempted"])
        self.assertTrue(answer.sources)

    def test_unknown_source_reference_is_rejected(self) -> None:
        client = FakeClient(
            {
                "answer": "Ответ из неизвестного источника [S99].",
                "usedSourceRefs": ["S99"],
                "insufficientEvidence": False,
            }
        )
        answer = RAGAssistant(_retriever(), client).ask("Что такое Н-1А?")
        self.assertFalse(answer.provenance["llmUsed"])
        self.assertEqual(answer.provenance["llmError"], "LLMResponseError")

    def test_missing_inline_citation_is_added_deterministically(self) -> None:
        client = FakeClient(
            {
                "answer": "Н-1А указан как сырьевой насос.",
                "usedSourceRefs": ["S1"],
                "insufficientEvidence": False,
            }
        )
        answer = RAGAssistant(_retriever(), client).ask("Что такое Н-1А?")
        self.assertTrue(answer.provenance["llmUsed"])
        self.assertIn("[S1]", answer.answer)


if __name__ == "__main__":
    unittest.main()
