"""Stage 3 — Assemble flashcard PNGs into print-ready A4 PDFs."""

from __future__ import annotations

import logging
import re
import tempfile
from pathlib import Path
from typing import Callable

from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

import pypdf

from pipeline.config import CardSize, Difficulty, FlashCard, PipelineConfig, Style, check_cancelled
from pipeline.pdf_settings import TEMPLATE_DIR, FlashCardLayout, get_layout

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[str], None] | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _natural_sort_key(text: str) -> list[int | str]:
    return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", text)]


def _mirror_page(page: pypdf.PageObject) -> pypdf.PageObject:
    """Rotate 180 ° and flip vertically — needed for double-sided printing."""
    page.rotate(180)
    page.scale(1, -1)
    return page


def _difficulty_order(cards: list[FlashCard]) -> dict[str, list[int]]:
    """Build card-index → difficulty lookup from in-memory cards."""
    order: dict[str, list[int]] = {"Easy": [], "Medium": [], "Hard": []}
    for card in cards:
        label = card.difficulty.value.capitalize()
        if label in order:
            order[label].append(card.index)
    return order


def _sort_score(
    image_name: str,
    order: dict[str, list[int]],
) -> tuple[int, int]:
    match = re.search(r"\d+", image_name)
    if match:
        idx = int(match.group())
        for diff, priority in [("Easy", 1), ("Medium", 2), ("Hard", 3)]:
            if idx in order[diff]:
                return priority, order[diff].index(idx)
    return 4, 9999


# ---------------------------------------------------------------------------
# Image pre-processing
# ---------------------------------------------------------------------------

def _preprocess_images(
    image_folder: Path,
    layout: FlashCardLayout,
) -> dict[str, Image.Image]:
    processed: dict[str, Image.Image] = {}
    if not image_folder.is_dir():
        logger.error("Image folder not found: %s", image_folder)
        return processed

    for p in sorted(image_folder.iterdir()):
        if p.suffix.lower() != ".png":
            continue
        img = Image.open(p).convert("RGBA")

        if p.name.endswith("_Back.png"):
            img = layout.preprocess_back_image(img)

        new_w = int(img.size[0] * layout.SCALE)
        new_h = int(img.size[1] * layout.SCALE)
        img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
        processed[p.name] = img

    return processed


# ---------------------------------------------------------------------------
# PDF page creation
# ---------------------------------------------------------------------------

def _create_pdf_page(
    c: canvas.Canvas,
    template_filename: str,
    image_set: list[tuple[str, Image.Image]],
    layout: FlashCardLayout,
    page_w: float,
    page_h: float,
) -> None:
    template_path = TEMPLATE_DIR / template_filename
    if not template_path.exists():
        logger.error("Template not found: %s", template_path)
        return

    base = Image.open(template_path).convert("RGBA")

    for i, (_name, img_obj) in enumerate(image_set):
        processed, x, y = layout.get_layout(i, img_obj)
        base.paste(processed, (x, y), processed)

    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        base.save(tmp_path, format="PNG")

    c.drawImage(str(tmp_path), 0, 0, width=page_w, height=page_h, mask="auto")
    tmp_path.unlink(missing_ok=True)
    base.close()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def create_pdf(
    config: PipelineConfig,
    style: Style,
    size: CardSize,
    cards: list[FlashCard],
    progress: ProgressCallback = None,
    cancelled: Callable[[], bool] | None = None,
) -> Path:
    """Assemble card PNGs into a single A4 PDF. Returns path to the PDF."""
    layout = get_layout(size, config, style)
    image_folder, pdf_folder = layout.get_paths()
    pdf_folder.mkdir(parents=True, exist_ok=True)
    final_path = pdf_folder / f"{layout.NAME}.pdf"

    logger.info(
        "Generating %s %s-%s-%s PDF…",
        size.value, config.asset_pack, config.operation.value, layout.style_label,
    )
    if progress:
        progress(f"Assembling {size.value} {layout.style_label} PDF…")

    # Pre-process card images
    images = _preprocess_images(image_folder, layout)
    if not images:
        raise FileNotFoundError(f"No card images found in {image_folder}")

    # Sort by difficulty
    order = _difficulty_order(cards)
    all_names = sorted(images.keys(), key=_natural_sort_key)
    front_names = sorted(
        [n for n in all_names if not n.endswith("_Back.png")],
        key=lambda n: _sort_score(n, order),
    )
    back_names = [f"{n[:-4]}_Back.png" for n in front_names]

    chunk = layout.CARDS_PER_PAGE
    temp_pdfs: list[Path] = []

    try:
        for i in range(0, len(front_names), chunk):
            check_cancelled(cancelled)

            fronts = [
                (n, images[n]) for n in front_names[i : i + chunk] if n in images
            ]
            backs = [
                (n, images[n]) for n in back_names[i : i + chunk] if n in images
            ]
            if not fronts:
                continue

            idx_s, idx_e = i + 1, i + len(fronts)
            front_pdf = pdf_folder / f"_tmp_front_{idx_s}_{idx_e}.pdf"
            back_pdf = pdf_folder / f"_tmp_back_{idx_s}_{idx_e}.pdf"

            # Front page
            c_front = canvas.Canvas(str(front_pdf), pagesize=A4)
            _create_pdf_page(c_front, layout.TEMPLATE_FRONT, fronts, layout, *A4)
            c_front.showPage()
            c_front.save()
            temp_pdfs.append(front_pdf)

            # Back page (mirrored for double-sided printing)
            c_back = canvas.Canvas(str(back_pdf), pagesize=A4)
            _create_pdf_page(c_back, layout.TEMPLATE_BACK, backs, layout, *A4)
            c_back.showPage()
            c_back.save()

            _mirror_back_pdf(back_pdf)
            temp_pdfs.append(back_pdf)

            page_num = (i // chunk) + 1
            logger.info("  Page %d generated", page_num)

        # Merge all temp PDFs
        writer = pypdf.PdfWriter()
        for pdf in temp_pdfs:
            if pdf.exists():
                reader = pypdf.PdfReader(str(pdf))
                for page in reader.pages:
                    writer.add_page(page)

        with open(final_path, "wb") as f:
            writer.write(f)

        logger.info("PDF created: %s", final_path)
        return final_path
    finally:
        for pdf in temp_pdfs:
            pdf.unlink(missing_ok=True)


def _mirror_back_pdf(pdf_path: Path) -> None:
    """Mirror every page in a back-page PDF for double-sided printing."""
    reader = pypdf.PdfReader(str(pdf_path))
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        _mirror_page(page)
        writer.add_page(page)
    with open(pdf_path, "wb") as f:
        writer.write(f)
