from __future__ import annotations

import unittest

from ai.rag_documents import DocumentChunk, KnowledgeIndex, SourceType
from ai.rag_retriever import LocalRetriever, tokenize


def _chunk(number: int, path: str, content: str) -> DocumentChunk:
    return DocumentChunk(
        chunk_id=str(number),
        source_ref=f"{path}#{number}",
        source_path=path,
        source_type=SourceType.TECHNOLOGY_SOURCE,
        locator=None,
        chunk_index=number,
        content=content,
    )


class LocalRetrieverTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = KnowledgeIndex(
            source_root="test",
            chunks=(
                _chunk(1, "насосы.pdf", "Назначение сырьевого насоса Н-1А."),
                _chunk(2, "колонна.pdf", "Описание колонны и продуктов."),
                _chunk(3, "насосы.pdf", "Диагностические признаки насоса Н-1А."),
                _chunk(4, "насосы.pdf", "Дополнительное описание насоса Н-1А."),
                _chunk(5, "сценарий.docx", "Учебный сценарий отказа Н-1А."),
            ),
        )

    def test_equipment_identifier_is_searchable(self) -> None:
        results = LocalRetriever(self.index).search("Что известно о Н-1А?")
        self.assertTrue(results)
        self.assertIn("Н-1А", results[0].chunk.content)

    def test_results_are_diversified_by_source_file(self) -> None:
        results = LocalRetriever(self.index).search("насос Н-1А", limit=4)
        source_paths = [result.chunk.source_path for result in results]
        self.assertLessEqual(source_paths.count("насосы.pdf"), 2)
        self.assertIn("сценарий.docx", source_paths)

    def test_hyphenated_identifier_has_joined_token(self) -> None:
        self.assertIn("н1а", tokenize("Н-1А"))


if __name__ == "__main__":
    unittest.main()
