import os

# Import files
import operations
import card_creator
import pdf_generator

# ====================================================
#                 MASTER SETTINGS
# ====================================================

# 1. Project Definitions
ASSET_PACK = "Animals"      # Must have same name as folder in /input/assets/
OPERATION = "Addition"  # Options: "Addition", "Subtraction"

# 2. Pipeline Stages (Toggle True/False to skip steps)
RUN_OPERATIONS = False
RUN_CARD_GEN = False
RUN_PDF_GEN = True

# 3. Output Options
GENERATE_STANDARD = True    # Standard = All cards are navy blue (Unified)
GENERATE_COLOR_GRADED = True     # Colored Graded = Cards are difficulty coded. Easy (blue), Medium (green), Hard (red)

# 4. Final PDF Size Options
TARGET_SIZES = ["Small", "Medium"] # "Large"


# ====================================================

def main():
    print("******************************************")
    print("      FLASHCARD PIPELINE STARTED")
    print("******************************************\n")

    global RUN_OPERATIONS, RUN_CARD_GEN

    # Base path for projects generations
    base_gen_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "Gen", ASSET_PACK, "Flash Cards", OPERATION
    )

    # STEP 1: OPERATIONS (Text Generation)

    # 1. Expected Path Calculation
    ops_filename = f"{OPERATION}_Operations.txt"
    ops_file_path = os.path.join(base_gen_path, ops_filename)

    # 2. Auto-Correction Check
    if not RUN_OPERATIONS:
        if not os.path.exists(ops_file_path):
            print(f"Operations file missing at: {ops_filename}")
            print("    Forcing RUN_OPERATIONS = True to prevent errors.\n")
            RUN_OPERATIONS = True

    # 3. Execution
    if RUN_OPERATIONS:
        print("\n** Starting Operations File Generation **")
        ops_file_path = operations.generate_operations(
            asset_pack=ASSET_PACK,
            operation=OPERATION
        )
        print(f"Operations File Created At: {ops_file_path}")
    else:
        print(f"** Skipping Operations Gen. Found existing file: {ops_filename} **")

    # STEP 2: CARD IMAGE GENERATION

    # 1. Auto-Correction Check
    if not RUN_CARD_GEN:
        missing_images = False

        # Check Standard Folder if Standard is requested
        if GENERATE_STANDARD:
            std_path = os.path.join(base_gen_path, "Standard")
            # If folder doesn't exist OR it's empty
            if not os.path.exists(std_path) or not os.listdir(std_path):
                print("'Standard' card images are missing.")
                missing_images = True

        # Check Colored Folder if Colored is requested
        if GENERATE_COLOR_GRADED:
            col_path = os.path.join(base_gen_path, "Color Graded")
            if not os.path.exists(col_path) or not os.listdir(col_path):
                print("'Color Graded' card images are missing.")
                missing_images = True

        if missing_images:
            print("Forcing RUN_CARD_GEN = True to prevent errors.\n")
            RUN_CARD_GEN = True

    # 2. Execution
    if RUN_CARD_GEN:
        print(f"\n** Starting Standard {OPERATION} Flash Card Generation **")
        if GENERATE_STANDARD:
            card_creator.run_card_creator(
                asset_pack=ASSET_PACK,
                operation=OPERATION,
                standard_style=True,
            )

        if GENERATE_COLOR_GRADED:
            print(f"\n** Starting Color Graded {OPERATION} Flash Card Generation **")
            card_creator.run_card_creator(
                asset_pack=ASSET_PACK,
                operation=OPERATION,
                standard_style=False,
            )
    else:
        print("Skipping Flash Card Generation. Images verified.")


    # STEP 3: PDF GENERATION

    if RUN_PDF_GEN:
        print("\n** Starting PDF Generation **")

        for size in TARGET_SIZES:
            # Standard PDFs
            if GENERATE_STANDARD:
                try:
                    pdf_generator.run_flashcard_generator(
                        size=size,
                        asset_pack=ASSET_PACK,
                        operation=OPERATION,
                        standard_style=True
                    )
                except Exception as e:
                    print(f"FAILED to generate {size} Standard PDF: {e}")

            # Colored PDFs
            if GENERATE_COLOR_GRADED:
                try:
                    pdf_generator.run_flashcard_generator(
                        size=size,
                        asset_pack=ASSET_PACK,
                        operation=OPERATION,
                        standard_style=False
                    )
                except Exception as e:
                    print(f"FAILED to generate {size} Color Graded PDF: {e}")
    else:
        print("Skipping PDF Generation.")

    print("******************************************")
    print("           PIPELINE COMPLETE")
    print("******************************************")


if __name__ == "__main__":
    main()