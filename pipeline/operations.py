"""Stage 1 — Generate flashcard data: math pairs, plurals, difficulty, and text."""

from __future__ import annotations

import logging
import random
from pathlib import Path
from typing import Callable

import inflect

from pipeline.config import (
    Difficulty,
    FlashCard,
    Operation,
    PipelineConfig,
    number_word,
)

logger = logging.getLogger(__name__)

_inflect_engine = inflect.engine()

ProgressCallback = Callable[[int, int], None] | None


# ---------------------------------------------------------------------------
# Asset discovery
# ---------------------------------------------------------------------------

def get_asset_names(assets_dir: Path) -> list[str]:
    """Return sorted list of asset names (no extension) from *assets_dir*."""
    if not assets_dir.is_dir():
        logger.warning("Asset directory not found: %s", assets_dir)
        return []

    names = sorted(
        p.stem for p in assets_dir.iterdir()
        if p.suffix.lower() == ".png"
    )

    if not names:
        logger.warning("No PNG files found in %s", assets_dir)
    return names


# ---------------------------------------------------------------------------
# Pluralisation (inflect — replaces Ollama)
# ---------------------------------------------------------------------------

def pluralize(names: list[str]) -> dict[str, str]:
    """Return ``{singular: plural}`` mapping using the *inflect* library."""
    return {name: _inflect_engine.plural(name) for name in names}


# ---------------------------------------------------------------------------
# Difficulty
# ---------------------------------------------------------------------------

def determine_difficulty(num1: int, num2: int, operation: Operation) -> Difficulty:
    if operation is Operation.ADDITION:
        total = num1 + num2
        if total <= 7:
            return Difficulty.EASY
        if total <= 14:
            return Difficulty.MEDIUM
        return Difficulty.HARD
    else:
        if num1 <= 5:
            return Difficulty.EASY
        if num1 <= 8:
            return Difficulty.MEDIUM
        return Difficulty.HARD


# ---------------------------------------------------------------------------
# Math pair generation
# ---------------------------------------------------------------------------

def generate_math_pairs(operation: Operation, seed: int = 234) -> list[tuple[int, int]]:
    """Deterministically generate all ``(a, b)`` pairs for the given operation."""
    rng = random.Random(seed)
    pairs: list[tuple[int, int]] = []

    for a in range(1, 11):
        for b in range(a, 11):
            if operation is Operation.ADDITION:
                pair = (a, b) if rng.choice([True, False]) else (b, a)
            else:
                # For subtraction the larger number must come first so the
                # result is non-negative.  We randomise only when a == b.
                pair = (b, a)
            pairs.append(pair)

    return pairs


# ---------------------------------------------------------------------------
# Asset assignment
# ---------------------------------------------------------------------------

def assign_assets(
    pairs: list[tuple[int, int]],
    asset_names: list[str],
    seed: int = 234,
) -> list[tuple[tuple[int, int], str]]:
    """Assign an asset to each pair via round-robin over a shuffled asset list."""
    rng = random.Random(seed + 1)          # separate stream from pair generation
    pool = asset_names[:]
    rng.shuffle(pool)

    assignments: list[tuple[tuple[int, int], str]] = []
    for pair in pairs:
        if not pool:
            pool = asset_names[:]
            rng.shuffle(pool)
        assignments.append((pair, pool.pop()))

    return assignments


# ---------------------------------------------------------------------------
# Card text generation
# ---------------------------------------------------------------------------

def _build_card(
    index: int,
    num1: int,
    num2: int,
    asset_name: str,
    operation: Operation,
    plural_map: dict[str, str],
) -> FlashCard:
    """Build a single :class:`FlashCard` from raw data."""
    if operation is Operation.ADDITION:
        answer = num1 + num2
        op_symbol = "+"
        op_verb = "plus"
    else:
        answer = num1 - num2
        op_symbol = "-"
        op_verb = "minus"

    plural = plural_map.get(asset_name, asset_name + "s")

    form1 = plural if num1 != 1 else asset_name
    form2 = plural if num2 != 1 else asset_name
    form_ans = plural if answer != 1 else asset_name

    front_text = f"How many {plural} are there now?"
    rear_text = (
        f"{number_word(num1).capitalize()} {form1} {op_verb} "
        f"{number_word(num2)} {form2} equals "
        f"{number_word(answer)} {form_ans}."
    )
    operation_text = f"{num1} {op_symbol} {num2} = {answer}"
    difficulty = determine_difficulty(num1, num2, operation)

    return FlashCard(
        index=index,
        num1=num1,
        num2=num2,
        operation=operation,
        asset_name=asset_name,
        plural_form=plural,
        difficulty=difficulty,
        front_text=front_text,
        rear_text=rear_text,
        operation_text=operation_text,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def generate_cards(
    config: PipelineConfig,
    progress: ProgressCallback = None,
) -> list[FlashCard]:
    """Generate all flashcard data. Returns an in-memory list of cards."""
    asset_names = get_asset_names(config.assets_dir)
    if not asset_names:
        raise FileNotFoundError(f"No assets found in {config.assets_dir}")

    logger.info("Pluralising %d asset names with inflect…", len(asset_names))
    plural_map = pluralize(asset_names)

    pairs = generate_math_pairs(config.operation, config.random_seed)
    assignments = assign_assets(pairs, asset_names, config.random_seed)

    cards: list[FlashCard] = []
    total = len(assignments)
    for i, ((num1, num2), asset_name) in enumerate(assignments, 1):
        card = _build_card(i, num1, num2, asset_name, config.operation, plural_map)
        cards.append(card)
        if progress:
            progress(i, total)

    logger.info("Generated %d flashcard entries.", len(cards))
    return cards


# ---------------------------------------------------------------------------
# Optional: write operations file for backward compatibility / debugging
# ---------------------------------------------------------------------------

def save_operations_file(cards: list[FlashCard], path: Path) -> Path:
    """Write the classic operations text file used by the legacy pipeline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for card in cards:
            f.write(
                f'Card #{card.index}\n'
                f'Front Text: "{card.front_text}"\n'
                f'Rear Text: "{card.rear_text}"\n'
                f'Operation: "{card.operation_text}"\n'
                f'Image: {card.asset_name}\n'
                f'Difficulty: {card.difficulty.value.capitalize()}\n\n'
            )
    logger.info("Operations file written to %s", path)
    return path
