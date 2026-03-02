"""Shared configuration, data models, and constants for the flashcard pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


# ---------------------------------------------------------------------------
# Cancellation
# ---------------------------------------------------------------------------

class PipelineCancelled(Exception):
    """Raised when the user cancels the pipeline mid-run."""


def check_cancelled(cancelled: Callable[[], bool] | None) -> None:
    """Call at each iteration boundary; raises PipelineCancelled if set."""
    if cancelled is not None and cancelled():
        raise PipelineCancelled("Pipeline cancelled by user.")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class Operation(str, Enum):
    ADDITION = "Addition"
    SUBTRACTION = "Subtraction"


class Difficulty(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Style(str, Enum):
    STANDARD = "Standard"
    COLOR_GRADED = "Color Graded"


class CardSize(str, Enum):
    LARGE = "Large"
    MEDIUM = "Medium"
    SMALL = "Small"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FlashCard:
    """Immutable representation of a single flashcard's data."""
    index: int
    num1: int
    num2: int
    operation: Operation
    asset_name: str
    plural_form: str
    difficulty: Difficulty
    front_text: str
    rear_text: str
    operation_text: str


# ---------------------------------------------------------------------------
# Pipeline configuration
# ---------------------------------------------------------------------------

@dataclass
class PipelineConfig:
    """All settings needed to run the full pipeline."""
    base_path: Path
    asset_pack: str
    operation: Operation
    styles: list[Style] = field(default_factory=lambda: [Style.STANDARD, Style.COLOR_GRADED])
    sizes: list[CardSize] = field(default_factory=lambda: [CardSize.MEDIUM, CardSize.SMALL])
    random_seed: int = 234

    # Derived paths --------------------------------------------------------

    @property
    def assets_dir(self) -> Path:
        return self.base_path / "input" / "Assets" / self.asset_pack

    @property
    def template_dir(self) -> Path:
        return self.base_path / "input" / "templates"

    @property
    def font_path(self) -> Path:
        return self.base_path / "input" / "Assets" / "Quicksand-Bold.ttf"

    def gen_dir(self, style: Style) -> Path:
        return (
            self.base_path
            / "Gen"
            / self.asset_pack
            / "Flash Cards"
            / self.operation.value
            / style.value
        )

    def pdf_dir(self, style: Style) -> Path:
        return (
            self.base_path
            / "Gen"
            / self.asset_pack
            / "Final_PDFs"
            / self.operation.value
            / style.value
        )

    def ops_file_path(self) -> Path:
        return (
            self.base_path
            / "Gen"
            / self.asset_pack
            / "Flash Cards"
            / self.operation.value
            / f"{self.operation.value}_Operations.txt"
        )


# ---------------------------------------------------------------------------
# Colour scheme
# ---------------------------------------------------------------------------

DIFFICULTY_COLORS: dict[str, str] = {
    Difficulty.EASY: "#4F8BC6",
    Difficulty.MEDIUM: "#59A96A",
    Difficulty.HARD: "#D94E4E",
}
STANDARD_COLOR = "#2967CA"


def text_color_for(difficulty: Difficulty | str, is_standard: bool) -> str:
    if is_standard:
        return STANDARD_COLOR
    return DIFFICULTY_COLORS.get(difficulty, STANDARD_COLOR)


# ---------------------------------------------------------------------------
# Number words
# ---------------------------------------------------------------------------

NUMBER_WORDS = [
    "zero", "one", "two", "three", "four", "five",
    "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen",
    "sixteen", "seventeen", "eighteen", "nineteen", "twenty",
]


def number_word(n: int) -> str:
    return NUMBER_WORDS[n] if 0 <= n <= 20 else str(n)


# ---------------------------------------------------------------------------
# Card template size / layout constants (pixels at full resolution)
# ---------------------------------------------------------------------------

TEMPLATE_SIZE = (3875, 5463)
IMAGE_SIZE = (1000, 1000)
FONT_SIZE_LARGE = 300
MAX_IMAGES_PER_ROW = 5
TEXT_BOX_WIDTH = 3000

# Front card layout
FRAME_TOP_Y = 250
FRAME_BOTTOM_Y = TEMPLATE_SIZE[1] - 1225
BOX_AREA_WIDTH = 3000
BOX_AREA_HEIGHT = TEMPLATE_SIZE[1] // 3 - 250
SYMBOL_BOX_HEIGHT = 500
VERTICAL_SHIFT_TOP = 100
VERTICAL_SHIFT_BOTTOM = -100
SYMBOL_BOX_VERTICAL_GAP = 75
TEXT_BOX_HEIGHT = 900

# Back card layout
TOP_TEXT_VERTICAL_OFFSET = 1075
IMAGE_VERTICAL_OFFSET = 2375
BOTTOM_TEXT_VERTICAL_OFFSET = 3760
TOP_TEXT_BOX_HEIGHT = 700
IMAGE_BOX_DIMENSIONS = 1200
BOTTOM_TEXT_BOX_HEIGHT = 300
IMAGE_SCALE_FACTOR = 1.65
