"""Layout configuration classes for A4 PDF page assembly."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from pipeline.config import CardSize, PipelineConfig, Style

BASE_PATH = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE_PATH / "input" / "templates"


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class FlashCardLayout:
    """Base configuration for a specific card-size PDF layout."""

    NAME: str
    SCALE: float
    CARDS_PER_PAGE: int
    TEMPLATE_FRONT: str
    TEMPLATE_BACK: str

    def __init__(self, config: PipelineConfig, style: Style) -> None:
        self.config = config
        self.style = style

    @property
    def style_label(self) -> str:
        return self.style.value

    def get_paths(self) -> tuple[Path, Path]:
        img_folder = self.config.gen_dir(self.style)
        pdf_folder = self.config.pdf_dir(self.style)
        return img_folder, pdf_folder

    def get_layout(self, index: int, img: Image.Image) -> tuple[Image.Image, int, int]:
        raise NotImplementedError

    def preprocess_back_image(self, img: Image.Image) -> Image.Image:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Size-specific layouts
# ---------------------------------------------------------------------------

class LargeLayout(FlashCardLayout):
    NAME = "A4_Large"
    SCALE = 0.5792
    CARDS_PER_PAGE = 2
    TEMPLATE_FRONT = "A4_Page_Large.png"
    TEMPLATE_BACK = "A4_Page_Large.png"

    def get_layout(self, index: int, img: Image.Image) -> tuple[Image.Image, int, int]:
        img = img.rotate(90, expand=True)
        y = 505 if index == 0 else 3516
        return img, 627, y

    def preprocess_back_image(self, img: Image.Image) -> Image.Image:
        return img.rotate(180, expand=True)


class MediumLayout(FlashCardLayout):
    NAME = "A4_Medium"
    SCALE = 0.5101
    CARDS_PER_PAGE = 4
    TEMPLATE_FRONT = "A4_Page_Medium.png"
    TEMPLATE_BACK = "A4_Page_Medium.png"

    def get_layout(self, index: int, img: Image.Image) -> tuple[Image.Image, int, int]:
        col = index % 2
        row = index // 2
        x = 175 if col == 0 else 2262
        y = 259 if row == 0 else 3195
        return img, x, y

    def preprocess_back_image(self, img: Image.Image) -> Image.Image:
        return img.transpose(Image.FLIP_TOP_BOTTOM).rotate(180)


class SmallLayout(FlashCardLayout):
    NAME = "A4_Small"
    SCALE = 0.4087
    CARDS_PER_PAGE = 5
    TEMPLATE_FRONT = "A4_Page_Small.png"
    TEMPLATE_BACK = "A4_Page_Small_Back.png"

    _VERTICAL_SHIFTS = [306, 2324, 4337, 324, 3675]

    def get_layout(self, index: int, img: Image.Image) -> tuple[Image.Image, int, int]:
        if index < 3:
            img = img.rotate(90, expand=True)
            x = 178
        else:
            x = 2668
        return img, x, self._VERTICAL_SHIFTS[index]

    def preprocess_back_image(self, img: Image.Image) -> Image.Image:
        return img.transpose(Image.FLIP_TOP_BOTTOM).rotate(180)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

_LAYOUT_MAP: dict[CardSize, type[FlashCardLayout]] = {
    CardSize.LARGE: LargeLayout,
    CardSize.MEDIUM: MediumLayout,
    CardSize.SMALL: SmallLayout,
}


def get_layout(
    size: CardSize,
    config: PipelineConfig,
    style: Style,
) -> FlashCardLayout:
    cls = _LAYOUT_MAP.get(size)
    if cls is None:
        raise ValueError(f"Unknown card size: {size}")
    return cls(config, style)
