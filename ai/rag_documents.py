"""Document loading and persistent local index for the minimal RAG module."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import xml.etree.ElementTree as ElementTree
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable
from zipfile import BadZipFile, ZipFile


class DocumentLoadError(RuntimeError):
    """A document could not be converted to searchable text."""


class SourceType(str, Enum):
    """Origin categories from the project source map."""

    PROJECT_INSTRUCTION = "project_instruction"
    ORIGINAL_MATERIAL = "original_material"
    TEAM_WORK = "team_work"
    TECHNOLOGY_SOURCE = "technology_source"
    SAFETY_SOURCE = "safety_source"
    SIMULATOR_DATA = "simulator_data"
    UNCLASSIFIED = "unclassified"


SOURCE_TYPE_LABELS: dict[SourceType, str] = {
    SourceType.PROJECT_INSTRUCTION: "инструкция проекта",
    SourceType.ORIGINAL_MATERIAL: "исходный материал",
    SourceType.TEAM_WORK: "наработка команды",
    SourceType.TECHNOLOGY_SOURCE: "технологический источник",
    SourceType.SAFETY_SOURCE: "источник по безопасности",
    SourceType.SIMULATOR_DATA: "тренажёрные данные",
    SourceType.UNCLASSIFIED: "не классифицировано",
}


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_ref: str
    source_path: str
    source_type: SourceType
    locator: str | None
    chunk_index: int
    content: str

    def to_payload(self) -> dict[str, object]:
        return {
            "chunkId": self.chunk_id,
            "sourceRef": self.source_ref,
            "sourcePath": self.source_path,
            "sourceType": self.source_type.value,
            "locator": self.locator,
            "chunkIndex": self.chunk_index,
            "content": self.content,
        }

    @classmethod
    def from_payload(cls, payload: dict[str, object]) -> "DocumentChunk":
        return cls(
            chunk_id=str(payload["chunkId"]),
            source_ref=str(payload["sourceRef"]),
            source_path=str(payload["sourcePath"]),
            source_type=SourceType(str(payload["sourceType"])),
            locator=(
                str(payload["locator"])
                if payload.get("locator") is not None
                else None
            ),
            chunk_index=int(payload["chunkIndex"]),
            content=str(payload["content"]),
        )


@dataclass(frozen=True)
class SkippedDocument:
    source_path: str
    reason: str


@dataclass(frozen=True)
class KnowledgeIndex:
    source_root: str
    chunks: tuple[DocumentChunk, ...]
    version: int = 1

    def save(self, target: str | Path) -> None:
        path = Path(target)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "sourceRoot": self.source_root,
            "chunks": [chunk.to_payload() for chunk in self.chunks],
        }
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, source: str | Path) -> "KnowledgeIndex":
        path = Path(source)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise DocumentLoadError(f"Не удалось прочитать индекс: {path}") from error
        if not isinstance(payload, dict) or payload.get("version") != 1:
            raise DocumentLoadError("Неподдерживаемая версия индекса RAG")
        raw_chunks = payload.get("chunks")
        if not isinstance(raw_chunks, list):
            raise DocumentLoadError("В индексе RAG отсутствует список chunks")
        try:
            chunks = tuple(
                DocumentChunk.from_payload(item)
                for item in raw_chunks
                if isinstance(item, dict)
            )
        except (KeyError, TypeError, ValueError) as error:
            raise DocumentLoadError("Индекс RAG содержит некорректный chunk") from error
        return cls(
            source_root=str(payload.get("sourceRoot", "")),
            chunks=chunks,
            version=1,
        )


@dataclass(frozen=True)
class IndexBuildResult:
    index: KnowledgeIndex
    indexed_files: int
    skipped: tuple[SkippedDocument, ...]


@dataclass(frozen=True)
class _TextSection:
    content: str
    locator: str | None = None


class DocumentCorpusBuilder:
    """Build a compact index from text, Markdown, DOCX and text PDFs."""

    SUPPORTED_SUFFIXES = {".txt", ".md", ".mmd", ".docx", ".pdf"}
    SKIPPED_DIRECTORIES = {".git", "__pycache__", "output", "tmp"}

    def __init__(
        self,
        *,
        max_chunk_chars: int = 1_400,
        overlap_words: int = 30,
        include_unclassified: bool = False,
    ) -> None:
        if max_chunk_chars < 300:
            raise ValueError("max_chunk_chars must be at least 300")
        if overlap_words < 0:
            raise ValueError("overlap_words must be non-negative")
        self.max_chunk_chars = max_chunk_chars
        self.overlap_words = overlap_words
        self.include_unclassified = include_unclassified

    def build(self, source_root: str | Path) -> IndexBuildResult:
        root = Path(source_root).expanduser().resolve()
        if not root.is_dir():
            raise DocumentLoadError(f"Папка документов не найдена: {root}")

        chunks: list[DocumentChunk] = []
        skipped: list[SkippedDocument] = []
        indexed_files = 0
        paths = sorted(
            (
                path
                for path in root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in self.SUPPORTED_SUFFIXES
                and not any(part in self.SKIPPED_DIRECTORIES for part in path.parts)
            ),
            key=lambda path: path.as_posix(),
        )
        for path in paths:
            relative_path = path.relative_to(root).as_posix()
            if (
                classify_source(relative_path) is SourceType.UNCLASSIFIED
                and not self.include_unclassified
            ):
                skipped.append(
                    SkippedDocument(
                        relative_path,
                        "Источник отсутствует в карте происхождения файлов",
                    )
                )
                continue
            try:
                sections = self._extract_sections(path)
            except DocumentLoadError as error:
                skipped.append(SkippedDocument(relative_path, str(error)))
                continue

            document_chunks = self._build_document_chunks(
                relative_path,
                sections,
            )
            if not document_chunks:
                skipped.append(
                    SkippedDocument(relative_path, "В документе не найден текст")
                )
                continue
            chunks.extend(document_chunks)
            indexed_files += 1

        return IndexBuildResult(
            index=KnowledgeIndex(source_root=str(root), chunks=tuple(chunks)),
            indexed_files=indexed_files,
            skipped=tuple(skipped),
        )

    def _build_document_chunks(
        self,
        relative_path: str,
        sections: Iterable[_TextSection],
    ) -> list[DocumentChunk]:
        source_type = classify_source(relative_path)
        chunks: list[DocumentChunk] = []
        chunk_index = 0
        for section in sections:
            for content in self._split_text(section.content):
                chunk_index += 1
                locator_suffix = f"-{section.locator}" if section.locator else ""
                source_ref = f"{relative_path}#{chunk_index}{locator_suffix}"
                digest = hashlib.sha256(source_ref.encode("utf-8")).hexdigest()[:16]
                chunks.append(
                    DocumentChunk(
                        chunk_id=digest,
                        source_ref=source_ref,
                        source_path=relative_path,
                        source_type=source_type,
                        locator=section.locator,
                        chunk_index=chunk_index,
                        content=content,
                    )
                )
        return chunks

    def _split_text(self, text: str) -> tuple[str, ...]:
        normalized = _normalize_text(text)
        if not normalized:
            return ()
        words = normalized.split()
        chunks: list[str] = []
        start = 0
        while start < len(words):
            end = start
            current_length = 0
            while end < len(words):
                next_length = len(words[end]) + (1 if current_length else 0)
                if end > start and current_length + next_length > self.max_chunk_chars:
                    break
                current_length += next_length
                end += 1
            chunks.append(" ".join(words[start:end]))
            if end >= len(words):
                break
            start = max(start + 1, end - self.overlap_words)
        return tuple(chunks)

    def _extract_sections(self, path: Path) -> tuple[_TextSection, ...]:
        suffix = path.suffix.lower()
        if suffix in {".txt", ".md", ".mmd"}:
            return (_TextSection(_read_plain_text(path)),)
        if suffix == ".docx":
            return (_TextSection(_read_docx(path)),)
        if suffix == ".pdf":
            return _read_pdf(path)
        raise DocumentLoadError(f"Неподдерживаемый формат: {suffix}")


def classify_source(relative_path: str) -> SourceType:
    """Classify a file using ``КАРТА_ПРОИСХОЖДЕНИЯ_ФАЙЛОВ.md`` rules."""

    parts = Path(relative_path).parts
    top_level = parts[0] if parts else ""
    filename = parts[-1] if parts else relative_path
    if top_level.startswith("00_инструкция"):
        return SourceType.PROJECT_INSTRUCTION
    if top_level.startswith("01_задание_и_ограничения"):
        return SourceType.ORIGINAL_MATERIAL
    if top_level.startswith("02_проектное_решение"):
        return SourceType.TEAM_WORK
    if top_level.startswith("03_технологические_источники"):
        return SourceType.TECHNOLOGY_SOURCE
    if top_level.startswith("04_безопасность"):
        return SourceType.SAFETY_SOURCE
    if top_level.startswith("05_инфраструктура_и_тренажерные_данные"):
        if filename.startswith("01_протокол_виртуального_инструктора"):
            return SourceType.SIMULATOR_DATA
        return SourceType.TEAM_WORK
    if top_level in {"architecture", "output"}:
        return SourceType.TEAM_WORK
    return SourceType.UNCLASSIFIED


def _read_plain_text(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1251"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError as error:
            raise DocumentLoadError(f"Не удалось прочитать файл {path.name}") from error
    raise DocumentLoadError(f"Неизвестная кодировка файла {path.name}")


def _read_docx(path: Path) -> str:
    namespace = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    try:
        with ZipFile(path) as archive:
            document_xml = archive.read("word/document.xml")
        root = ElementTree.fromstring(document_xml)
    except (OSError, BadZipFile, KeyError, ElementTree.ParseError) as error:
        raise DocumentLoadError(f"Не удалось извлечь DOCX {path.name}") from error

    paragraphs: list[str] = []
    for paragraph in root.iter(f"{{{namespace}}}p"):
        text = "".join(
            node.text or "" for node in paragraph.iter(f"{{{namespace}}}t")
        ).strip()
        if text:
            paragraphs.append(text)
    return "\n\n".join(paragraphs)


def _read_pdf(path: Path) -> tuple[_TextSection, ...]:
    executable = shutil.which("pdftotext")
    if executable is None:
        raise DocumentLoadError(
            "Для PDF требуется утилита pdftotext из пакета Poppler"
        )
    try:
        result = subprocess.run(
            [executable, "-enc", "UTF-8", str(path), "-"],
            check=False,
            capture_output=True,
            text=True,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise DocumentLoadError(f"Не удалось извлечь PDF {path.name}") from error
    if result.returncode != 0:
        reason = " ".join(result.stderr.split())[:200]
        raise DocumentLoadError(
            f"pdftotext завершился с ошибкой: {reason or result.returncode}"
        )
    return tuple(
        _TextSection(page, locator=f"page-{number}")
        for number, page in enumerate(result.stdout.split("\f"), start=1)
        if _normalize_text(page)
    )


def _normalize_text(text: str) -> str:
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    return " ".join(line for line in lines if line).strip()
