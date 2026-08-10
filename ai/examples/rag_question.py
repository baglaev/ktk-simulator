"""Ask one grounded question using a prepared local RAG index."""

from __future__ import annotations

import argparse
import json
import os

from ai.openai_compatible import LLMConfig, OpenAICompatibleClient
from ai.rag_assistant import RAGAssistant
from ai.rag_documents import KnowledgeIndex
from ai.rag_retriever import LocalRetriever


def main() -> None:
    parser = argparse.ArgumentParser(description="Ask the KTK RAG assistant")
    parser.add_argument("question", help="Question in Russian")
    parser.add_argument(
        "--index",
        default=os.getenv("AI_RAG_INDEX_PATH", "ai/data/rag_index.json"),
        help="Path to the prepared JSON index",
    )
    arguments = parser.parse_args()

    index = KnowledgeIndex.load(arguments.index)
    assistant = RAGAssistant(
        LocalRetriever(index),
        OpenAICompatibleClient(LLMConfig.from_env()),
        top_k=int(os.getenv("AI_RAG_TOP_K", "4")),
        max_context_chars=int(os.getenv("AI_RAG_MAX_CONTEXT_CHARS", "8000")),
    )
    answer = assistant.ask(arguments.question)
    print(json.dumps(answer.to_payload(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
