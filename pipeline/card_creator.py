"""Stage 2 — Composite individual flashcard images (front + back PNGs)."""

from __future__ import annotations

import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw, ImageFont

from pipeline.config import (
    BOX_AREA_HEIGHT,
    BOX_AREA_WIDTH,
    BOTTOM_TEXT_BOX_HEIGHT,
    BOTTOM_TEXT_VERTICAL_OFFSET,
    Difficulty,
    FlashCard,
    FONT_SIZE_LARGE,
    FRAME_BOTTOM_Y,
    FRAME_TOP_Y,
    IMAGE_BOX_DIMENSIONS,
    IMAGE_SCALE_FACTOR,
    IMAGE_VERTICAL_OFFSET,
    MAX_IMAGES_PER_ROW,
    Operation,
    PipelineConfig,
    Style,
    TEMPLATE_SIZE,
    TEXT_BOX_HEIGHT,
    TEXT_BOX_WIDTH,
    TOP_TEXT_BOX_HEIGHT,
    TOP_TEXT_VERTICAL_OFFSET,
    VERTICAL_SHIFT_BOTTOM,
    VERTICAL_SHIFT_TOP,
    check_cancelled,
    text_color_for,
)

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int, str], None] | None

# ---------------------------------------------------------------------------
# Template / symbol path helpers
# ---------------------------------------------------------------------------

_DIFFICULTY_KEYS = {
    Difficulty.EASY: "Easy",
    Difficulty.MEDIUM: "Medium",
    Difficulty.HARD: "Hard",
}


def _template_paths(template_dir: Path) -> dict[str, dict[str, Path]]:
    """Build lookup tables for all templates keyed by *type* then *difficulty*."""
    kinds: dict[str, dict[str, Path]] = {
        "front": {},
        "back": {},
        "plus": {},
        "minus": {},
    }
    for diff_enum, label in _DIFFICULTY_KEYS.items():
        kinds["front"][diff_enum] = template_dir / f"FC Front {label}.png"
        kinds["back"][diff_enum] = template_dir / f"FC Back {label}.png"
        kinds["plus"][diff_enum] = template_dir / f"Plus {label}.png"
        kinds["minus"][diff_enum] = template_dir / f"Minus {label}.png"

    kinds["front"]["standard"] = template_dir / "FC Front Standard.png"
    kinds["back"]["standard"] = template_dir / "FC Back Standard.png"
    kinds["plus"]["standard"] = template_dir / "Plus Standard.png"
    kinds["minus"]["standard"] = template_dir / "Minus Standard.png"

    return kinds


# ---------------------------------------------------------------------------
# CardCreator
# ---------------------------------------------------------------------------

class CardCreator:
    """Creates front and back flashcard PNGs for a given style."""

    def __init__(self, config: PipelineConfig, style: Style) -> None:
        self.config = config
        self.style = style
        self.output_dir = config.gen_dir(style)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self._templates = _template_paths(config.template_dir)
        self._font_cache: dict[int, ImageFont.FreeTypeFont] = {}
        self._asset_cache: dict[tuple[str, int, int], Image.Image] = {}

    # -- Caches ------------------------------------------------------------

    def _font(self, size: int) -> ImageFont.FreeTypeFont:
        if size not in self._font_cache:
            self._font_cache[size] = ImageFont.truetype(
                str(self.config.font_path), size=size,
            )
        return self._font_cache[size]

    def _asset_image(self, name: str, size: tuple[int, int]) -> Image.Image:
        key = (name, *size)
        if key not in self._asset_cache:
            path = self.config.assets_dir / f"{name}.png"
            self._asset_cache[key] = Image.open(path).resize(size)
        return self._asset_cache[key]

    def _open_template(self, kind: str, difficulty: str) -> Image.Image:
        path = self._templates[kind].get(difficulty, self._templates[kind]["standard"])
        return Image.open(path).convert("RGBA")

    # -- Geometry helpers --------------------------------------------------

    @staticmethod
    def _row_positions(
        count: int,
        box_w: int,
        img_w: int,
        box_x: int,
        box_y: int,
        v_offset: int,
    ) -> list[tuple[int, int]]:
        remaining = box_w - img_w * count
        margin = remaining // (count + 1)
        return [
            (box_x + margin * (i + 1) + img_w * i, box_y + v_offset)
            for i in range(count)
        ]

    @staticmethod
    def _grid_positions(
        count: int,
        box: tuple[int, int, int, int],
        img_size: tuple[int, int],
    ) -> list[tuple[int, int]]:
        bw, bh, bx, by = box
        iw, ih = img_size

        if count <= 4:
            v_off = (bh - ih) // 2
            return CardCreator._row_positions(count, bw, iw, bx, by, v_off)

        top_n = (count + 1) // 2
        bot_n = count // 2
        gap = (bh - 2 * ih) // 3

        top = CardCreator._row_positions(top_n, bw, iw, bx, by, gap)
        bot = CardCreator._row_positions(bot_n, bw, iw, bx, by, 2 * gap + ih)
        return top + bot

    # -- Front card --------------------------------------------------------

    def _place_images(
        self,
        canvas: Image.Image,
        num_top: int,
        num_bottom: int,
        asset_name: str,
    ) -> None:
        top_y = FRAME_TOP_Y + VERTICAL_SHIFT_TOP
        bot_y = FRAME_BOTTOM_Y + VERTICAL_SHIFT_BOTTOM - BOX_AREA_HEIGHT
        cx = (TEMPLATE_SIZE[0] - BOX_AREA_WIDTH) // 2

        top_box = (BOX_AREA_WIDTH, BOX_AREA_HEIGHT, cx, top_y)
        bot_box = (BOX_AREA_WIDTH, BOX_AREA_HEIGHT, cx, bot_y)

        if num_top < 5 and num_bottom < 5:
            side = BOX_AREA_WIDTH // max(num_top, num_bottom)
            if side > BOX_AREA_HEIGHT:
                side = BOX_AREA_HEIGHT
            img_size = (side, side)
        else:
            side = BOX_AREA_WIDTH // MAX_IMAGES_PER_ROW
            img_size = (side, side)

        img = self._asset_image(asset_name, img_size)

        for pos in self._grid_positions(num_top, top_box, img_size):
            canvas.paste(img, pos, img)
        for pos in self._grid_positions(num_bottom, bot_box, img_size):
            canvas.paste(img, pos, img)

    def _draw_front_text(self, canvas: Image.Image, text: str) -> None:
        draw = ImageDraw.Draw(canvas)
        font = self._font(FONT_SIZE_LARGE)
        box_x = (TEMPLATE_SIZE[0] - TEXT_BOX_WIDTH) // 2
        box_y = TEMPLATE_SIZE[1] - TEXT_BOX_HEIGHT - 170

        words = text.split()
        row1 = " ".join(words[:3])
        row2 = " ".join(words[3:])

        for i, line in enumerate([row1, row2]):
            tw, th = draw.textbbox((0, 0), line, font=font)[2:]
            x = box_x + (TEXT_BOX_WIDTH - tw) // 2
            y = box_y + i * TEXT_BOX_HEIGHT // 2 + (TEXT_BOX_HEIGHT // 4 - th // 2)
            draw.text((x, y), line, fill=(255, 255, 255), font=font)

    def create_front(self, card: FlashCard) -> Image.Image:
        diff_key = "standard" if self.style is Style.STANDARD else card.difficulty
        fc = self._open_template("front", diff_key)

        match = re.match(r"(\d+)\s*([+\-])\s*(\d+)\s*=\s*\d+", card.operation_text)
        if not match:
            raise ValueError(f"Bad operation format: {card.operation_text}")
        num_top, symbol, num_bottom = int(match[1]), match[2], int(match[3])

        self._place_images(fc, num_top, num_bottom, card.asset_name)
        self._draw_front_text(fc, card.front_text)

        sym_kind = "plus" if symbol == "+" else "minus"
        sym = self._open_template(sym_kind, diff_key)
        fc.paste(sym, (0, 0), sym)

        return fc

    # -- Back card ---------------------------------------------------------

    def _draw_back_text(
        self,
        canvas: Image.Image,
        rear_text: str,
        operation_text: str,
        difficulty: str,
        is_standard: bool,
    ) -> None:
        FONT_TOP_ORIG = 250
        FONT_BOT_ORIG = 260
        FONT_TOP_SMALL = 235
        FONT_BOT_SMALL = 250

        if "plus" in rear_text:
            kw1, kw2 = "plus", "equals"
        elif "minus" in rear_text:
            kw1, kw2 = "minus", "equals"
        else:
            raise ValueError("Rear text must contain 'plus' or 'minus'.")

        idx1 = rear_text.index(kw1) + len(kw1)
        idx2 = rear_text.index(kw2) + len(kw2)
        row1 = rear_text[:idx1].strip()
        row2 = rear_text[idx1:idx2].strip()
        row3 = rear_text[idx2:].strip(" .\"")

        if len(row2) > 23:
            font_top_sz, font_bot_sz = FONT_TOP_SMALL, FONT_BOT_SMALL
        else:
            font_top_sz, font_bot_sz = FONT_TOP_ORIG, FONT_BOT_ORIG

        font_top = self._font(font_top_sz)
        font_bot = self._font(font_bot_sz)
        draw = ImageDraw.Draw(canvas)
        w = canvas.size[0]
        color = text_color_for(difficulty, is_standard)

        offsets = [
            TOP_TEXT_VERTICAL_OFFSET,
            TOP_TEXT_VERTICAL_OFFSET + 325,
            TOP_TEXT_VERTICAL_OFFSET + 650,
        ]
        for text, y in zip([row1, row2, row3], offsets):
            bbox = draw.textbbox((0, 0), text, font=font_top)
            x = (w - bbox[2]) // 2
            draw.text((x, y), text, fill=color, font=font_top)

        op_clean = operation_text.strip('"')
        bbox = draw.textbbox((0, 0), op_clean, font=font_bot)
        x = (w - bbox[2]) // 2
        y_nudge = 50 if is_standard else 0
        y = BOTTOM_TEXT_VERTICAL_OFFSET + (BOTTOM_TEXT_BOX_HEIGHT - bbox[3]) // 2 + y_nudge
        draw.text((x, y), op_clean, fill=color, font=font_bot)

    def _place_back_image(self, canvas: Image.Image, asset_name: str) -> None:
        path = self.config.assets_dir / f"{asset_name}.png"
        img = Image.open(path)
        scaled = (
            int(img.size[0] * IMAGE_SCALE_FACTOR),
            int(img.size[1] * IMAGE_SCALE_FACTOR),
        )
        img = img.resize(scaled)
        w = canvas.size[0]
        x = (w - scaled[0]) // 2
        y = IMAGE_VERTICAL_OFFSET + (IMAGE_BOX_DIMENSIONS - scaled[1]) // 2
        canvas.paste(img, (x, y), img)

    def create_back(self, card: FlashCard) -> Image.Image:
        diff_key = "standard" if self.style is Style.STANDARD else card.difficulty
        fc = self._open_template("back", diff_key)

        self._draw_back_text(
            fc,
            card.rear_text,
            card.operation_text,
            diff_key,
            is_standard=(self.style is Style.STANDARD),
        )
        self._place_back_image(fc, card.asset_name)
        return fc

    # -- Bulk generation ---------------------------------------------------

    def generate_all(
        self,
        cards: list[FlashCard],
        progress: ProgressCallback = None,
        cancelled: Callable[[], bool] | None = None,
    ) -> list[Path]:
        """Create front + back PNGs for every card. Returns list of created file paths."""
        total = len(cards)
        label = self.style.value
        created_files: list[Path] = []

        for card in cards:
            check_cancelled(cancelled)

            front_path = self.output_dir / f"Card_{card.index}.png"
            front = self.create_front(card)
            front.save(front_path, "PNG")
            front.close()
            created_files.append(front_path)

            back_path = self.output_dir / f"Card_{card.index}_Back.png"
            back = self.create_back(card)
            back.save(back_path, "PNG")
            back.close()
            created_files.append(back_path)

            if progress:
                progress(card.index, total, label)

        logger.info(
            "%d %s flashcards saved to %s", total, label, self.output_dir,
        )
        return created_files
