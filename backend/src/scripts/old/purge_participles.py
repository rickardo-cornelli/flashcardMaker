import os

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")

LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")
TOP_5000_FILE = os.path.join(OUTPUT_DIR, "top_5000_french_lemmas.txt")
INPUT_FILE = os.path.join(OUTPUT_DIR, "dumas_total_best_value_frequent.txt")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dumas_ultimate_frequent.txt")

def purge_participles():
    if not os.path.exists(INPUT_FILE):
        print(f"ERROR: Cannot find {INPUT_FILE}")
        return

    # 1. Load Top 5000 words
    with open(TOP_5000_FILE, 'r', encoding='utf-8') as f:
        top_5000 = set(line.strip().lower() for line in f if line.strip())

    # 2. Map Lexique roots
    surface_to_lemmas = {}
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f)
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                surface = parts[0].lower()
                lemma = parts[2].lower()
                if surface not in surface_to_lemmas:
                    surface_to_lemmas[surface] = set()
                surface_to_lemmas[surface].add(lemma)

    kept_words = []
    trashed_words = []

    print("Purging common participles safely using Lexique...")
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                word = parts[0].strip()
                count = parts[1].strip()
                
                is_common = False
                
                # Check 1: Normal Lexique Root Check (Safely catches "trouvé", "reçu")
                lemmas = surface_to_lemmas.get(word, {word})
                for lem in lemmas:
                    if lem in top_5000:
                        is_common = True
                        break

                if is_common:
                    trashed_words.append(word)
                else:
                    kept_words.append((word, count))

    # Save the absolute final list
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        for word, count in kept_words:
            f.write(f"{word},{count}\n")

    print("\n" + "="*50)
    print("🔥 THE SAFE PURGE IS COMPLETE 🔥")
    print("="*50)
    print(f"Pure Words Kept: {len(kept_words)}")
    print(f"Imposters Trashed: {len(trashed_words)}")
    print(f"\nSaved final list as: {os.path.basename(OUTPUT_FILE)}")
    print("="*50)
    print("Note: Phantoms like 'chambrer' may still exist. Just press 'N' in your Vue app!")

if __name__ == "__main__":
    purge_participles()