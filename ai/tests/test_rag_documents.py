from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from ai.rag_documents import (
    DocumentCorpusBuilder,
    KnowledgeIndex,
    SourceType,
    classify_source,
)


class RAGDocumentTests(unittest.TestCase):
    def test_source_types_follow_project_origin_map(self) -> None:
        self.assertEqual(
            classify_source("01_задание_и_ограничения/ТЗ.txt"),
            SourceType.ORIGINAL_MATERIAL,
        )
        self.assertEqual(
            classify_source("02_проектное_решение/MVP.docx"),
            SourceType.TEAM_WORK,
        )
        self.assertEqual(
            classify_source("03_технологические_источники/насосы.pdf"),
            SourceType.TECHNOLOGY_SOURCE,
        )
        self.assertEqual(
            classify_source(
                "05_инфраструктура_и_тренажерные_данные/"
                "01_протокол_виртуального_инструктора_ЭЛОУ_АВТ.pdf"
            ),
            SourceType.SIMULATOR_DATA,
        )

    def test_build_save_and_load_text_index(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "03_технологические_источники" / "насосы.txt"
            source.parent.mkdir()
            source.write_text(
                "Насос Н-1А используется в учебном описании оборудования.",
                encoding="utf-8",
            )
            result = DocumentCorpusBuilder(max_chunk_chars=300).build(root)
            self.assertEqual(result.indexed_files, 1)
            self.assertEqual(len(result.index.chunks), 1)
            self.assertEqual(
                result.index.chunks[0].source_type,
                SourceType.TECHNOLOGY_SOURCE,
            )

            index_path = root / "index.json"
            result.index.save(index_path)
            loaded = KnowledgeIndex.load(index_path)
            self.assertEqual(loaded.chunks, result.index.chunks)

    def test_docx_is_read_without_python_docx_dependency(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "02_проектное_решение" / "MVP.docx"
            source.parent.mkdir()
            xml = """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
              <w:body><w:p><w:r><w:t>Сценарий Н-1А</w:t></w:r></w:p></w:body>
            </w:document>"""
            with ZipFile(source, "w", ZIP_DEFLATED) as archive:
                archive.writestr("word/document.xml", xml)

            result = DocumentCorpusBuilder(max_chunk_chars=300).build(root)
            self.assertIn("Сценарий Н-1А", result.index.chunks[0].content)

    def test_unclassified_files_are_skipped_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            (root / "notes.txt").write_text("непроверенные заметки", encoding="utf-8")
            result = DocumentCorpusBuilder().build(root)
            self.assertEqual(result.indexed_files, 0)
            self.assertEqual(len(result.skipped), 1)


if __name__ == "__main__":
    unittest.main()
