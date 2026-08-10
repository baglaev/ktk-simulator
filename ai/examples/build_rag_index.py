"""Build the local RAG index from the project document package."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ai.rag_documents import DocumentCorpusBuilder


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the KTK RAG index")
    parser.add_argument(
        "--source-dir",
        default=os.getenv("AI_RAG_DOCUMENTS_DIR"),
        help="Path to КТК_ЭЛОУ_АВТ_пакет_для_промта",
    )
    parser.add_argument(
        "--output",
        default=os.getenv("AI_RAG_INDEX_PATH", "ai/data/rag_index.json"),
        help="Target JSON index path",
    )
    arguments = parser.parse_args()
    if not arguments.source_dir:
        parser.error("set --source-dir or AI_RAG_DOCUMENTS_DIR")

    result = DocumentCorpusBuilder().build(arguments.source_dir)
    if not result.index.chunks:
        raise SystemExit("Индекс не создан: в источниках не найден текст")
    result.index.save(arguments.output)
    print(
        json.dumps(
            {
                "indexPath": str(Path(arguments.output).resolve()),
                "indexedFiles": result.indexed_files,
                "chunks": len(result.index.chunks),
                "skipped": [
                    {"filePath": item.source_path, "reason": item.reason}
                    for item in result.skipped
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
