from __future__ import annotations

import sys
import os
from pathlib import Path


class RAGUnavailableError(RuntimeError):
    pass


class PostSessionRAGGateway:
    """Thin monorepo adapter around the independently testable ``ai`` package."""

    def __init__(self, index_path: Path | None = None) -> None:
        self._repository_root = Path(__file__).resolve().parents[3]
        configured = index_path or Path(
            os.getenv("AI_RAG_INDEX_PATH", "ai/data/rag_index.json")
        )
        self._index_path = (
            configured
            if configured.is_absolute()
            else self._repository_root / configured
        )
        self._assistant = None

    def ask(self, question: str) -> dict:
        assistant = self._get_assistant()
        return assistant.ask(question).to_payload()

    def _get_assistant(self):
        if self._assistant is not None:
            return self._assistant
        if not self._index_path.is_file():
            raise RAGUnavailableError(
                "RAG index is missing; build it with "
                "python3 -m ai.examples.build_rag_index"
            )
        root = str(self._repository_root)
        if root not in sys.path:
            sys.path.insert(0, root)
        try:
            from ai.openai_compatible import LLMConfig, OpenAICompatibleClient
            from ai.rag_assistant import RAGAssistant
            from ai.rag_documents import KnowledgeIndex
            from ai.rag_retriever import LocalRetriever

            index = KnowledgeIndex.load(self._index_path)
            self._assistant = RAGAssistant(
                LocalRetriever(index),
                OpenAICompatibleClient(LLMConfig.from_env()),
            )
        except Exception as error:
            raise RAGUnavailableError(str(error)) from error
        return self._assistant
