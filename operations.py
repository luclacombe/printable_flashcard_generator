import os
import random
import json
import ollama

# CONFIGURATION
TOTAL_NUMBERS = 10
RANDOM_SEED = 234
OLLAMA_MODEL = "qwen2.5:14b"

NUMBER_WORDS = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
                "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen",
                "nineteen", "twenty"]


def get_number_word(n):
    return NUMBER_WORDS[n] if n <= 20 else str(n)


def get_assets_from_folder(base_path, asset_pack):
    """
    Scans the specific Asset folder for .png files and returns a list of names.
    """
    assets_dir = os.path.join(base_path, "input", "Assets", asset_pack)

    if not os.path.exists(assets_dir):
        print(f"Warning: Directory not found: {assets_dir}")
        return []

    asset_names = []
    for filename in os.listdir(assets_dir):
        if filename.lower().endswith(".png"):
            # Remove .png extension to get the name
            name = os.path.splitext(filename)[0]
            asset_names.append(name)

    if not asset_names:
        print(f"No PNG files found in {assets_dir}")

    return sorted(asset_names)


def fetch_plurals_from_ollama(asset_list, asset_pack):
    """
    Sends the full list of asset names to local Ollama instance and requests
    a JSON mapping of Singular -> Plural.
    """
    if not asset_list:
        return {}

    print(f"Generating {len(asset_list)} plurals for {asset_pack} asset pack items using {OLLAMA_MODEL}...")

    system_prompt = (
        "You are a linguistic assistant for an elementary school project. "
        "I will provide a list of nouns. You must output a valid JSON object where "
        "the keys are the input nouns and the values are their most common grammatical "
        "plural forms used in counting contexts (e.g., '1 Fish, 2 Fish'). "
        "Use 'Fish' for the plural of Fish, not 'Fishes'. "
        "Do not include markdown formatting, code blocks, or conversational text. "
        "Return ONLY the JSON object."
    )

    user_prompt = f"List: {', '.join(asset_list)}"

    try:
        response = ollama.chat(model=OLLAMA_MODEL, messages=[
            {
                'role': 'system',
                'content': system_prompt,
            },
            {
                'role': 'user',
                'content': user_prompt,
            },
        ])

        content = response['message']['content'].strip()

        # Clean up potential markdown code
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "")
        elif content.startswith("```"):
            content = content.replace("```", "")

        plural_map = json.loads(content)
        return plural_map

    except ollama.ResponseError as e:
        print(f"Ollama API returned an error: {e.error}")
        return {}
    except json.JSONDecodeError:
        print("AI returned invalid JSON. Adding 's' to asset names.")
        print(f"Raw Output: {content}")
        return {}
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return {}


def determine_difficulty(num1, num2, is_addition):
    if is_addition:
        sum_value = num1 + num2
        if 2 <= sum_value <= 7:
            return 'Easy'
        elif 8 <= sum_value <= 14:
            return 'Medium'
        else:
            return 'Hard'
    else:
        if num1 <= 5:
            return 'Easy'
        elif 6 <= num1 <= 8:
            return 'Medium'
        else:
            return 'Hard'


def _generate_math_pairs(is_addition):
    random.seed(RANDOM_SEED)
    operations_list = []

    if is_addition:
        for a in range(1, 10 + 1):
            for b in range(a, 10 + 1):
                op = (a, b) if random.choice([True, False]) else (b, a)
                operations_list.append(op)
    else:
        for a in range(1, 10 + 1):
            for b in range(a, 10 + 1):
                if random.choice([True, False]):
                    if (a - b) >= 0:
                        op = (a, b)
                    elif (b - a) >= 0:
                        op = (b, a)
                else:
                    if (b - a) >= 0:
                        op = (b, a)
                    elif (a - b) >= 0:
                        op = (a, b)
                operations_list.append(op)
    return operations_list


def assign_assets(operations_list, asset_list):
    random.seed(RANDOM_SEED)
    assignment_output = []
    shuffled_assets = asset_list[:]
    random.shuffle(shuffled_assets)

    for operation in operations_list:
        if not shuffled_assets:
            shuffled_assets = asset_list[:]
            random.shuffle(shuffled_assets)

        assigned_asset = shuffled_assets.pop()
        assignment_output.append((operation, assigned_asset))

    return assignment_output


def generate_card_text(card_index, num1, num2, asset_name, is_addition, plural_map):
    # Calculate Math
    if is_addition:
        answer = num1 + num2
        op_symbol = "+"
        op_verb = "plus"
    else:
        answer = num1 - num2
        op_symbol = "-"
        op_verb = "minus"

    # Pluralization logic
    # Fallback to adding 's' if AI failed
    plural_form = plural_map.get(asset_name, asset_name + "s")

    item_plural = plural_form
    item_base = asset_name

    # If number is 1, use base. If not 1, use plural.
    item_form1 = item_plural if num1 != 1 else item_base
    item_form2 = item_plural if num2 != 1 else item_base
    item_form_answer = item_plural if answer != 1 else item_base

    # Text generation
    front_text = f"How many {item_plural} are there now?"

    rear_text = (f"{get_number_word(num1).capitalize()} {item_form1} {op_verb} "
                 f"{get_number_word(num2)} {item_form2} equals "
                 f"{get_number_word(answer)} {item_form_answer}.")

    operation_text = f"{num1} {op_symbol} {num2} = {answer}"

    # Difficulty
    difficulty = determine_difficulty(num1, num2, is_addition)

    # Final string assembly
    return (f"Card #{card_index}\n"
            f"Front Text: \"{front_text}\"\n"
            f"Rear Text: \"{rear_text}\"\n"
            f"Operation: \"{operation_text}\"\n"
            f"Image: {asset_name}\n"
            f"Difficulty: {difficulty}\n\n")


def generate_operations(asset_pack, operation):
    base_path = os.path.dirname(os.path.abspath(__file__))

    is_addition = operation == "Addition"

    # Get asset names from folders
    asset_list = get_assets_from_folder(base_path, asset_pack)

    if not asset_list:
        print("Error: No assets found. Aborting.")
        return None

    # Get plurals from local AI
    plural_map = fetch_plurals_from_ollama(asset_list, asset_pack)

    # Setup data
    ops = _generate_math_pairs(is_addition)
    assignments = assign_assets(ops, asset_list)

    # Generate content strings
    output_lines = []
    for i, (op_tuple, asset_name) in enumerate(assignments, 1):
        num1, num2 = op_tuple
        # Pass the plural_map to generator
        card_text = generate_card_text(i, num1, num2, asset_name, is_addition, plural_map)
        output_lines.append(card_text)

    # Create folder structure
    output_dir = os.path.join(base_path, "Gen", asset_pack, "Flash Cards", operation)
    os.makedirs(output_dir, exist_ok=True)

    # Write to file
    filename = f"{operation}_Operations.txt"
    file_path = os.path.join(output_dir, filename)

    with open(file_path, 'w') as f:
        f.writelines(output_lines)

    print(f"Success! Operations File Generated. {len(output_lines)} flash cards can now be generated.")
    return file_path


if __name__ == "__main__":
    # Test
    generate_operations("Animals", "Addition")