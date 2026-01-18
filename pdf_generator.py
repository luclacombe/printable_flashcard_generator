import os
import re
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
import PyPDF2

# Import the settings from the other file
import pdf_settings


def run_flashcard_generator(size, asset_pack, operation, standard_style):
    # Load configuration
    config = pdf_settings.get_config(size, asset_pack, operation, standard_style)

    image_folder, final_pdf_folder = config.get_paths()
    final_pdf_path = os.path.join(final_pdf_folder, f"{config.NAME}.pdf")

    if not os.path.exists(final_pdf_folder):
        os.makedirs(final_pdf_folder)

    print(f"\nGenerating PDF for Large Sized {asset_pack}-{operation}-{config.style_string} Flash Cards")

    # Helper functions

    def natural_keys(text):
        """Used to sort flashcards numerically from their file name"""
        return [int(c) if c.isdigit() else c.lower() for c in re.split('(\d+)', text)]

    def mirror_pdf_vertically(pdf_path):
        """Mirrors the back pages vertically (required for two sided printing)."""
        reader = PyPDF2.PdfReader(pdf_path)
        writer = PyPDF2.PdfWriter()

        for page in reader.pages:
            page.rotate(180)
            page.scale(1, -1)
            writer.add_page(page)

        with open(pdf_path, 'wb') as f:
            writer.write(f)

    def parse_difficulties():
        """Parses operations file"""
        order_dict = {'Easy': [], 'Medium': [], 'Hard': []}

        # Check standard paths
        base_ops_path = os.path.join(config.base_path, "Gen", asset_pack, "Flash Cards", operation)
        possible_files = [
            os.path.join(base_ops_path, f"{operation}_Operations.txt"),
            os.path.join(base_ops_path, "Operations_Sorted.txt"),
            os.path.join(config.base_path, "input", "Assets", asset_pack, f"{operation}_Operations.txt")
        ]

        found_file = None
        for p in possible_files:
            if os.path.exists(p):
                found_file = p
                break

        if not found_file:
            print("Warning: No Operations/Difficulty text file found")
            return order_dict

        with open(found_file, 'r') as file:
            card_number = None
            for line in file:
                if line.startswith("Card #"):
                    parts = line.strip().split("#")
                    if len(parts) > 1:
                        card_number = parts[1].strip()
                elif "Difficulty:" in line and card_number:
                    difficulty = line.strip().split(": ")[1]
                    if difficulty in order_dict:
                        order_dict[difficulty].append(card_number)
                    card_number = None
        return order_dict

    def get_order_score(image_name, order_dict):
        card_number_match = re.search(r'\d+', image_name)
        if card_number_match:
            card_number = card_number_match.group()
            for difficulty in ('Easy', 'Medium', 'Hard'):
                if card_number in order_dict[difficulty]:
                    return (
                        {"Easy": 1, "Medium": 2, "Hard": 3}[difficulty],
                        order_dict[difficulty].index(card_number)
                    )
        return (4, 9999)

    def preprocess_images():
        """Resizes images using the config.SCALE settings"""
        processed = {}
        if not os.path.exists(image_folder):
            print(f"Error: Image folder not found: {image_folder}")
            return {}

        for img_name in sorted(os.listdir(image_folder)):
            if img_name.endswith('.png'):
                img_path = os.path.join(image_folder, img_name)
                img = Image.open(img_path).convert("RGBA")

                if img_name.endswith('_Back.png'):
                    img = config.preprocess_back_image(img)

                # Resize flashcards
                new_size = (int(img.size[0] * config.SCALE), int(img.size[1] * config.SCALE))
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                processed[img_name] = img
        return processed

    def create_pdf_page(c, base_template_filename, image_set, page_w, page_h):
        full_template_path = os.path.join(pdf_settings.TEMPLATE_DIR, base_template_filename)

        if not os.path.exists(full_template_path):
            print(f"Error: Template not found at: {full_template_path}")
            return

        base_image = Image.open(full_template_path).convert("RGBA")

        for i, (img_name, img_obj) in enumerate(image_set):
            # Get layout from settings
            processed_img, x, y = config.get_layout(i, img_obj)
            base_image.paste(processed_img, (x, y), processed_img)

        temp_path = f"temp_page_{size}_{id(image_set)}.png"
        base_image.save(temp_path, format='PNG')
        c.drawImage(temp_path, 0, 0, width=page_w, height=page_h, mask='auto')
        os.remove(temp_path)

    ### Execution Flow

    preprocessed_images = preprocess_images()
    if not preprocessed_images:
        return

    order_dict = parse_difficulties()
    all_names = sorted(preprocessed_images.keys(), key=natural_keys)
    front_names = sorted(
        [img for img in all_names if not img.endswith('_Back.png')],
        key=lambda x: get_order_score(x, order_dict)
    )
    back_names = [f"{name[:-4]}_Back.png" for name in front_names]

    temp_pdfs = []
    chunk_size = config.CARDS_PER_PAGE

    for i in range(0, len(front_names), chunk_size):
        current_front = [(name, preprocessed_images[name]) for name in front_names[i:i + chunk_size] if
                         name in preprocessed_images]
        current_back = [(name, preprocessed_images[name]) for name in back_names[i:i + chunk_size] if
                        name in preprocessed_images]

        if not current_front: continue

        idx_start = i + 1
        idx_end = i + len(current_front)
        front_pdf = os.path.join(final_pdf_folder, f"temp_front_{idx_start}_{idx_end}.pdf")
        back_pdf = os.path.join(final_pdf_folder, f"temp_back_{idx_start}_{idx_end}.pdf")

        c_front = canvas.Canvas(front_pdf, pagesize=A4)
        create_pdf_page(c_front, config.TEMPLATE_FRONT, current_front, *A4)
        c_front.showPage()
        c_front.save()
        temp_pdfs.append(front_pdf)

        c_back = canvas.Canvas(back_pdf, pagesize=A4)
        create_pdf_page(c_back, config.TEMPLATE_BACK, current_back, *A4)
        c_back.showPage()
        c_back.save()

        mirror_pdf_vertically(back_pdf)
        temp_pdfs.append(back_pdf)

        page_num = (i // chunk_size) + 1
        print(f"Page {page_num} Generated")

    print("Merging pages...")

    merger = PyPDF2.PdfMerger()
    for pdf in temp_pdfs:
        if os.path.exists(pdf):
            merger.append(pdf)

    merger.write(final_pdf_path)
    merger.close()

    for pdf in temp_pdfs:
        if os.path.exists(pdf):
            os.remove(pdf)

    print(f"Success! Final PDF created at: {final_pdf_path}")


if __name__ == "__main__":
    run_flashcard_generator("Large", "Animals", "Addition", True)
    # run_flashcard_generator("Medium", "Animals", "Addition", False)
    # run_flashcard_generator("Small", "Animals", "Addition", False)