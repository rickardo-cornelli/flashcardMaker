import os
import argparse

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")

# Pointing to your personal ignore list
PERSONAL_IGNORE_LIST = os.path.join(OUTPUT_DIR, "ignore_list.txt")

def merge_to_ignore_list(input_filename):
    input_path = os.path.join(OUTPUT_DIR, input_filename)
    
    if not os.path.exists(input_path):
        print(f"ERROR: Cannot find {input_path}")
        return

    # 1. Load existing ignore list to prevent duplicates
    existing_words = set()
    if os.path.exists(PERSONAL_IGNORE_LIST):
        with open(PERSONAL_IGNORE_LIST, 'r', encoding='utf-8') as f:
            for line in f:
                word = line.strip().lower()
                if word and not word.startswith('#'):
                    existing_words.add(word)

    # 2. Extract pure words from the given list (strips the ",count" part automatically)
    new_words_to_ignore = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 1:
                word = parts[0].strip().lower()
                if word and word not in existing_words:
                    new_words_to_ignore.append(word)
                    existing_words.add(word)

    # 3. Safely append to the bottom of your personal ignore list
    if new_words_to_ignore:
        with open(PERSONAL_IGNORE_LIST, 'a', encoding='utf-8') as f:
            # Dynamically label the comment block so you know exactly where words came from
            f.write(f"\n# --- ADDED FROM {input_filename.upper()} ---\n")
            for word in new_words_to_ignore:
                f.write(f"{word}\n")

    print("\n" + "="*50)
    print("🧠 PERSONAL IGNORE LIST UPDATED")
    print("="*50)
    print(f"Successfully appended {len(new_words_to_ignore)} words to {os.path.basename(PERSONAL_IGNORE_LIST)}.")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add words from a list to your personal ignore list.")
    parser.add_argument("input_file", help="The vocabulary file to merge (e.g., dumas_ultimate_frequent.txt)")
    
    args = parser.parse_args()
    merge_to_ignore_list(args.input_file)