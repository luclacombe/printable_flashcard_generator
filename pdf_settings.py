import os
from PIL import Image

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_PATH, "input", "templates")


class FlashCardConfig:
    """Base configuration class."""

    def __init__(self, asset_pack, operation, standard_style):
        self.asset = asset_pack
        self.operation = operation
        self.standard_style = standard_style
        self.base_path = BASE_PATH
        self.style_string = "Standard"

    def get_paths(self):
        flashcard_base = os.path.join(self.base_path, "Gen", self.asset, "Flash Cards", self.operation)
        export_base = os.path.join(self.base_path, "Gen", self.asset, "Final_PDFs", self.operation)

        if self.standard_style:
            img_folder = os.path.join(flashcard_base, "Standard")
            pdf_folder = os.path.join(export_base, "Standard")
        else:
            img_folder = os.path.join(flashcard_base, "Color Graded")
            pdf_folder = os.path.join(export_base, "Color Graded")
            self.style_string = "Color Graded"
        return img_folder, pdf_folder


class LargeConfig(FlashCardConfig):
    NAME = "A4_Large"
    # Original scale: 0.1856
    SCALE = 0.5792 # x3.12
    CARDS_PER_PAGE = 2
    TEMPLATE_FRONT = "A4_Page_Large.png"
    TEMPLATE_BACK = "A4_Page_Large.png"

    def get_layout(self, index, img):
        img = img.rotate(90, expand=True)
        # Original: x=201, y=162/1127
        x = 627 # x3.12
        y = 505 if index == 0 else 3516 # x3.12
        return img, x, y

    def preprocess_back_image(self, img):
        return img.rotate(180, expand=True)


class MediumConfig(FlashCardConfig):
    NAME = "A4_Medium"
    # Original scale: 0.1635
    SCALE = 0.5101 # x3.12
    CARDS_PER_PAGE = 4
    TEMPLATE_FRONT = "A4_Page_Medium.png"
    TEMPLATE_BACK = "A4_Page_Medium.png"

    def get_layout(self, index, img):
        col = index % 2
        row = index // 2

        # Original X: 56, 725
        # Original Y: 83, 1024
        x = 175 if col == 0 else 2262 # x3.12
        y = 259 if row == 0 else 3195 # x3.12

        return img, x, y

    def preprocess_back_image(self, img):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img = img.rotate(180)
        return img


class SmallConfig(FlashCardConfig):
    NAME = "A4_Small"
    # Original scale: 0.131
    SCALE = 0.4087 # x3.12
    CARDS_PER_PAGE = 5
    TEMPLATE_FRONT = "A4_Page_Small.png"
    TEMPLATE_BACK = "A4_Page_Small_Back.png"

    def get_layout(self, index, img):
        # Original vertical shifts: [98, 745, 1390, 104, 1178]
        vertical_shifts = [306, 2324, 4337, 324, 3675] # x3.12

        if index < 3:
            # Original X: 57
            x = 178 # x3.12
            img = img.rotate(90, expand=True)
        else:
            # Original X: 855
            x = 2668 # x3.12

        y = vertical_shifts[index]
        return img, x, y

    def preprocess_back_image(self, img):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
        img = img.rotate(180)
        return img


def get_config(size, asset, operation, standard_style):
    if size == "Large":
        return LargeConfig(asset, operation, standard_style)
    elif size == "Medium":
        return MediumConfig(asset, operation, standard_style)
    elif size == "Small":
        return SmallConfig(asset, operation, standard_style)
    else:
        raise ValueError("Invalid size. Choose Large, Medium, or Small.")