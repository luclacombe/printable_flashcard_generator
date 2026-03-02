"""Flashcard generation pipeline — public API."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable

from pipeline.config import (
    CardSize,
    Difficulty,
    FlashCard,
    Operation,
    PipelineCancelled,
    PipelineConfig,
    Style,
    check_cancelled,
)
from pipeline.card_creator import CardCreator
from pipeline.operations import generate_cards, save_operations_file
from pipeline.pdf_generator import create_pdf

__all__ = [
    "CardSize",
    "Difficulty",
    "FlashCard",
    "Operation",
    "PipelineCancelled",
    "PipelineConfig",
    "Style",
    "run_pipeline",
]

logger = logging.getLogger(__name__)


def _cleanup_files(files: list[Path]) -> None:
    """Delete every file in *files* that still exists on disk."""
    for f in files:
        try:
            f.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not delete %s", f)


def run_pipeline(
    config: PipelineConfig,
    on_stage: Callable[[str], None] | None = None,
    on_card_progress: Callable[[int, int, str], None] | None = None,
    on_pdf_progress: Callable[[str], None] | None = None,
    cancelled: Callable[[], bool] | None = None,
) -> dict[str, list[Path]]:
    """Run the full pipeline and return ``{"pdfs": [path, ...]}``."""

    created_files: list[Path] = []

    def _stage(msg: str) -> None:
        logger.info(msg)
        if on_stage:
            on_stage(msg)

    try:
        # Stage 1 — Generate card data
        _stage("Generating math problems…")
        cards = generate_cards(config)
        check_cancelled(cancelled)

        # Write operations file for reference
        ops_path = config.ops_file_path()
        ops_path.parent.mkdir(parents=True, exist_ok=True)
        save_operations_file(cards, ops_path)
        created_files.append(ops_path)

        # Stage 2 — Create card images for each style
        for style in config.styles:
            _stage(f"Creating {style.value} card images…")
            creator = CardCreator(config, style)
            files = creator.generate_all(
                cards, progress=on_card_progress, cancelled=cancelled,
            )
            created_files.extend(files)

        # Stage 3 — Assemble PDFs
        pdf_paths: list[Path] = []
        for style in config.styles:
            for size in config.sizes:
                _stage(f"Assembling {size.value} {style.value} PDF…")
                path = create_pdf(
                    config, style, size, cards,
                    progress=on_pdf_progress, cancelled=cancelled,
                )
                created_files.append(path)
                pdf_paths.append(path)

        _stage("Pipeline complete.")
        return {"pdfs": pdf_paths}

    except PipelineCancelled:
        logger.info("Pipeline cancelled — cleaning up %d file(s).", len(created_files))
        _cleanup_files(created_files)
        raise
