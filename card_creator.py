import os
import re
from PIL import Image, ImageDraw, ImageFont

# CONFIGURATION & CONSTANTS

# 1. DYNAMIC BASE PATH
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# 2. TEMPLATE DIRECTORY
TEMPLATE_DIR = os.path.join(BASE_PATH, "input", "templates")

# Template Paths
FRONT_TEMPLATES = {
    "easy": os.path.join(TEMPLATE_DIR, "FC Front Easy.png"),
    "medium": os.path.join(TEMPLATE_DIR, "FC Front Medium.png"),
    "hard": os.path.join(TEMPLATE_DIR, "FC Front Hard.png"),
    "standard": os.path.join(TEMPLATE_DIR, "FC Front Standard.png")
}

BACK_TEMPLATES = {
    "easy": os.path.join(TEMPLATE_DIR, "FC Back Easy.png"),
    "medium": os.path.join(TEMPLATE_DIR, "FC Back Medium.png"),
    "hard": os.path.join(TEMPLATE_DIR, "FC Back Hard.png"),
    "standard": os.path.join(TEMPLATE_DIR, "FC Back Standard.png")
}

PLUS_PATHS = {
    "easy": os.path.join(TEMPLATE_DIR, "Plus Easy.png"),
    "medium": os.path.join(TEMPLATE_DIR, "Plus Medium.png"),
    "hard": os.path.join(TEMPLATE_DIR, "Plus Hard.png"),
    "standard": os.path.join(TEMPLATE_DIR, "Plus Standard.png")
}

MINUS_PATHS = {
    "easy": os.path.join(TEMPLATE_DIR, "Minus Easy.png"),
    "medium": os.path.join(TEMPLATE_DIR, "Minus Medium.png"),
    "hard": os.path.join(TEMPLATE_DIR, "Minus Hard.png"),
    "standard": os.path.join(TEMPLATE_DIR, "Minus Standard.png")
}

# Backside text color based on difficulty
BACK_TEXT_COLORS = {
    "easy": "#4F8BC6",
    "medium": "#59A96A",
    "hard": "#D94E4E",
    "standard": "#2967CA"
}

# Font
QUICKSAND_BOLD = os.path.join(BASE_PATH, "input", "Assets", "Quicksand-Bold.ttf")

# Global Layout Constants
TEMPLATE_SIZE = (3875, 5463)
IMAGE_SIZE = (1000, 1000)
FONT_SIZE_LARGE = 300
MAX_IMAGES_PER_ROW = 5
TEXT_BOX_WIDTH = 3000

# Constants for front card layout
FRAME_TOP_Y = 250
FRAME_BOTTOM_Y = 5463 - 1225
BOX_AREA_WIDTH = 3000
BOX_AREA_HEIGHT = 5463 // 3 - 250
SYMBOL_BOX_HEIGHT = 500
VERTICAL_SHIFT_TOP = 100
VERTICAL_SHIFT_BOTTOM = -100
SYMBOL_BOX_VERTICAL_GAP = 75
TEXT_BOX_HEIGHT = 900

# Constants for back card layout
TOP_TEXT_VERTICAL_OFFSET = 1075
IMAGE_VERTICAL_OFFSET = 2375
BOTTOM_TEXT_VERTICAL_OFFSET = 3760

TOP_TEXT_BOX_HEIGHT = 700
IMAGE_BOX_DIMENSIONS = 1200
BOTTOM_TEXT_BOX_HEIGHT = 300
IMAGE_SCALE_FACTOR = 1.65


def run_card_creator(asset_pack, operation, standard_style):
    """
    Generates flashcards.
    :param asset_pack: e.g., "Animals"
    :param operation: e.g., "Addition"
    :param standard_style: "True" (Standard: Blue/Unified) or "False" (Colored: Difficulty based R/G/B)
    """

    # Determine directories
    ASSETS_DIR = os.path.join(BASE_PATH, "input", "Assets", asset_pack)
    GEN_DIR = os.path.join(BASE_PATH, "Gen", asset_pack, "Flash Cards", operation)

    OPERATIONS_FILE = os.path.join(GEN_DIR, f"{operation}_Operations.txt")

    output_folder_name = "Standard" if standard_style else "Color Graded"
    EXPORT_DIR = os.path.join(GEN_DIR, output_folder_name)

    if not os.path.exists(EXPORT_DIR):
        os.makedirs(EXPORT_DIR)

    def calculate_positions(num_images, box_area, image_size):
        if num_images <= 4:
            return calculate_row_positions(num_images, box_area, image_size[0], (box_area[1] - image_size[1]) // 2)
        else:
            num_top_row = (num_images + 1) // 2 if num_images % 2 != 0 else num_images // 2
            num_bottom_row = num_images // 2
            vertical_offset = (box_area[1] - 2 * image_size[1]) // 3

            top_positions = calculate_row_positions(num_top_row, box_area, image_size[0], vertical_offset)
            bottom_positions = calculate_row_positions(num_bottom_row, box_area, image_size[0],
                                                       2 * vertical_offset + image_size[1])
            return top_positions + bottom_positions

    def calculate_row_positions(num_images, box_area, image_size, vertical_offset):
        positions = []
        total_image_width = image_size * num_images
        remaining_space = box_area[0] - total_image_width
        margin = remaining_space // (num_images + 1)

        for i in range(num_images):
            x = box_area[2] + margin * (i + 1) + image_size * i
            y = box_area[3] + vertical_offset
            positions.append((x, y))
        return positions

    def place_images(flashcard, num_top_images, num_bottom_images, image_path):
        top_box_area_y = FRAME_TOP_Y + VERTICAL_SHIFT_TOP
        bottom_box_area_y = FRAME_BOTTOM_Y + VERTICAL_SHIFT_BOTTOM - BOX_AREA_HEIGHT
        top_box_area = (BOX_AREA_WIDTH, BOX_AREA_HEIGHT, (TEMPLATE_SIZE[0] - BOX_AREA_WIDTH) // 2, top_box_area_y)
        bottom_box_area = (BOX_AREA_WIDTH, BOX_AREA_HEIGHT, (TEMPLATE_SIZE[0] - BOX_AREA_WIDTH) // 2, bottom_box_area_y)

        if num_top_images < 5 and num_bottom_images < 5:
            max_num = max(num_top_images, num_bottom_images)
            image_size = (BOX_AREA_WIDTH // max_num, BOX_AREA_WIDTH // max_num)
            if image_size[1] > BOX_AREA_HEIGHT:
                image_size = (BOX_AREA_HEIGHT, BOX_AREA_HEIGHT)
        else:
            image_size = (BOX_AREA_WIDTH // MAX_IMAGES_PER_ROW, BOX_AREA_WIDTH // MAX_IMAGES_PER_ROW)

        top_positions = calculate_positions(num_top_images, top_box_area, image_size)
        bottom_positions = calculate_positions(num_bottom_images, bottom_box_area, image_size)
        animal_image = Image.open(image_path).resize(image_size)

        for pos in top_positions:
            flashcard.paste(animal_image, pos, animal_image)
        for pos in bottom_positions:
            flashcard.paste(animal_image, pos, animal_image)
        return flashcard

    def draw_text_on_flashcard(flashcard, front_text):
        draw = ImageDraw.Draw(flashcard)
        text_box_x = (TEMPLATE_SIZE[0] - TEXT_BOX_WIDTH) // 2
        text_box_y = TEMPLATE_SIZE[1] - TEXT_BOX_HEIGHT - 170

        front_text = front_text.replace('"', '').strip().split()
        text_row1 = ' '.join(front_text[:3])
        text_row2 = ' '.join(front_text[3:])

        font = ImageFont.truetype(QUICKSAND_BOLD, size=FONT_SIZE_LARGE)

        for i, text in enumerate([text_row1, text_row2]):
            text_width, text_height = draw.textbbox((0, 0), text, font=font)[2:]
            text_x = text_box_x + (TEXT_BOX_WIDTH - text_width) // 2
            text_y = text_box_y + i * TEXT_BOX_HEIGHT // 2 + (TEXT_BOX_HEIGHT // 4 - text_height // 2)
            draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)

    def place_image_on_back(flashcard_back, image_path):
        animal_image = Image.open(image_path)

        original_size = animal_image.size
        scaled_size = (int(original_size[0] * IMAGE_SCALE_FACTOR), int(original_size[1] * IMAGE_SCALE_FACTOR))
        animal_image = animal_image.resize(scaled_size)

        width, _ = flashcard_back.size
        x = (width - scaled_size[0]) // 2
        y = IMAGE_VERTICAL_OFFSET + (IMAGE_BOX_DIMENSIONS - scaled_size[1]) // 2
        flashcard_back.paste(animal_image, (x, y), animal_image)

    def draw_text_on_back(flashcard_back, rear_text, operation, difficulty):
        FONT_SIZE_TOP_TEXT_ORIGINAL = 250
        FONT_SIZE_BOTTOM_TEXT_ORIGINAL = 260
        FONT_SIZE_TOP_TEXT_REDUCED = 235
        FONT_SIZE_BOTTOM_TEXT_REDUCED = 250

        if "plus" in rear_text:
            keyword1, keyword2 = "plus", "equals"
        elif "minus" in rear_text:
            keyword1, keyword2 = "minus", "equals"
        else:
            raise ValueError("Rear text must contain 'plus' or 'minus' for correct formatting.")

        index1 = rear_text.index(keyword1) + len(keyword1)
        index2 = rear_text.index(keyword2) + len(keyword2)
        row1_text = rear_text[:index1].strip()
        row2_text = rear_text[index1:index2].strip()
        row3_text = rear_text[index2:].strip(' ."')

        if len(row2_text) > 23:
            font_size_top = FONT_SIZE_TOP_TEXT_REDUCED
            font_size_bottom = FONT_SIZE_BOTTOM_TEXT_REDUCED
        else:
            font_size_top = FONT_SIZE_TOP_TEXT_ORIGINAL
            font_size_bottom = FONT_SIZE_BOTTOM_TEXT_ORIGINAL

        draw = ImageDraw.Draw(flashcard_back)
        width, _ = flashcard_back.size

        try:
            font_top = ImageFont.truetype(QUICKSAND_BOLD, size=font_size_top)
            font_bottom = ImageFont.truetype(QUICKSAND_BOLD, size=font_size_bottom)
        except IOError:
            font_top = font_bottom = ImageFont.load_default()
            print("Custom font not found, using default font.")

        text_color = BACK_TEXT_COLORS.get(difficulty, BACK_TEXT_COLORS["standard"])

        for i, (text, offset) in enumerate(
                zip([row1_text, row2_text, row3_text],
                    [TOP_TEXT_VERTICAL_OFFSET, TOP_TEXT_VERTICAL_OFFSET + 325, TOP_TEXT_VERTICAL_OFFSET + 650])):
            text_bbox = draw.textbbox((0, 0), text, font=font_top)
            x = (width - text_bbox[2]) // 2
            y = offset
            draw.text((x, y), text, fill=text_color, font=font_top)

        operation = operation.strip('"')
        text_bbox = draw.textbbox((0, 0), operation, font=font_bottom)
        x = (width - text_bbox[2]) // 2

        y_nudge = 50 if difficulty == "standard" else 0
        y = BOTTOM_TEXT_VERTICAL_OFFSET + (BOTTOM_TEXT_BOX_HEIGHT - text_bbox[3]) // 2 + y_nudge

        draw.text((x, y), operation, fill=text_color, font=font_bottom)

    def create_flashcard(front_text, operation, image_name, card_index, difficulty):
        front_template_path = FRONT_TEMPLATES.get(difficulty, FRONT_TEMPLATES["standard"])
        flashcard = Image.open(front_template_path).convert("RGBA")

        match = re.match(r'"?(\d+)\s*(\+|-)\s*(\d+)\s*=\s*\d+"?', operation)
        if not match:
            raise ValueError(f"Unexpected operation format: {operation}")

        num_top, symbol, num_bottom = match.groups()
        num_top = int(num_top)
        num_bottom = int(num_bottom)

        image_path = os.path.join(ASSETS_DIR, f"{image_name}.png")
        flashcard = place_images(flashcard, num_top, num_bottom, image_path)
        draw_text_on_flashcard(flashcard, front_text)

        symbol_map = PLUS_PATHS if symbol == "+" else MINUS_PATHS
        symbol_image_path = symbol_map.get(difficulty, symbol_map["standard"])
        symbol_image = Image.open(symbol_image_path)
        flashcard.paste(symbol_image, (0, 0), symbol_image)

        png_output_path = os.path.join(EXPORT_DIR, f"Card_{card_index}.png")
        flashcard.save(png_output_path, "PNG")

    def create_flashcard_backside(rear_text, operation, image_name, card_index, difficulty):
        back_template_path = BACK_TEMPLATES.get(difficulty, BACK_TEMPLATES["standard"])
        flashcard_back = Image.open(back_template_path).convert("RGBA")

        draw_text_on_back(flashcard_back, rear_text, operation, difficulty)

        image_path = os.path.join(ASSETS_DIR, f"{image_name}.png")
        place_image_on_back(flashcard_back, image_path)

        png_back_output_path = os.path.join(EXPORT_DIR, f"Card_{card_index}_Back.png")
        flashcard_back.save(png_back_output_path, "PNG")

    def generate_flashcards():
        if not os.path.exists(OPERATIONS_FILE):
            print(f"Error: Operations file not found at {OPERATIONS_FILE}")
            return

        with open(OPERATIONS_FILE, 'r') as file:
            lines = [line.strip() for line in file.readlines()]
            lines = [line for line in lines if line]  # Remove empty lines

            lines_per_card = 6

            for i in range(0, len(lines), lines_per_card):
                if i + 5 < len(lines):
                    try:
                        # Parse headers
                        front_text_line = lines[i + 1].split(": ", 1)[1].strip('"').strip()
                        rear_text_line = lines[i + 2].split(": ", 1)[1].strip('"').strip()
                        operation_line = lines[i + 3].split(": ", 1)[1].strip()
                        image_line = lines[i + 4].split(": ", 1)[1].strip().strip('"').strip()
                        difficulty_line = lines[i + 5].split(": ", 1)[1].strip().lower()
                    except IndexError:
                        print(f"Skipping malformed block starting at line {i}")
                        continue

                    card_number = (i // lines_per_card) + 1
                    print(f"Processing Card {card_number} (Style: {output_folder_name})")

                    if standard_style:
                        difficulty = "standard"
                    else:
                        difficulty = difficulty_line

                    create_flashcard(front_text_line, operation_line, image_line, card_number, difficulty)
                    create_flashcard_backside(rear_text_line, operation_line, image_line, card_number, difficulty)

        print(f"{card_number} {output_folder_name} Flash Cards Generated at {EXPORT_DIR}")

    generate_flashcards()


# Test run
if __name__ == "__main__":
    run_card_creator("Animals", "Addition", standard_style=True)
