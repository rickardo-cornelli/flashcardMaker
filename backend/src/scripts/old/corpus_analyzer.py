import os
import re
import argparse
from collections import defaultdict, Counter

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
BOOKS_DIR = os.path.join(ROOT_DIR, "books")
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def build_reverse_lexique():
    """Builds a dictionary mapping a lemma to all its possible conjugated forms."""
    lemma_to_forms = defaultdict(set)
    if not os.path.exists(LEXIQUE_FILE):
        print("ERROR: Lexique383.tsv not found.")
        return lemma_to_forms
    
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f)
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                surface_form = parts[0].lower()
                lemma = parts[2].lower()
                lemma_to_forms[lemma].add(surface_form)
                
    for lemma in list(lemma_to_forms.keys()):
        lemma_to_forms[lemma].add(lemma)
        
    return lemma_to_forms

def get_raw_book_text(book_names):
    """Loads the raw text of multiple books into a single massive string."""
    combined_text = ""
    for name in book_names:
        book_path = os.path.join(BOOKS_DIR, f"{name}.txt")
        if os.path.exists(book_path):
            print(f"Loading {name}.txt into memory...")
            with open(book_path, "r", encoding="utf-8") as f:
                combined_text += f.read().lower() + " "
        else:
            print(f"WARNING: {name}.txt not found. Skipping.")
    return combined_text

def analyze_corpus(input_file, book_names, min_freq, max_freq):
    input_path = os.path.join(OUTPUT_DIR, input_file)
    if not os.path.exists(input_path):
        print(f"ERROR: Input file {input_path} not found.")
        return

    # 1. Load words that fall within our target frequency range
    print(f"Reading words from {input_file} (Filtering: {min_freq} <= freq <= {max_freq})...")
    base_words = {}
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                word = parts[0].strip()
                count = int(parts[1].strip())
                if min_freq <= count <= max_freq:
                    base_words[word] = count

    if not base_words:
        print("No words found in that frequency range! Exiting.")
        return

    # 2. THE SPEED UPGRADE: Build the Index ONCE
    print("Building master index of all words in the corpus. This takes ~2 seconds...")
    corpus_text = get_raw_book_text(book_names)
    
    # Extract every single word in the corpus into a list
    all_words_in_corpus = re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', corpus_text)
    
    # Count them all instantly
    corpus_counts = Counter(all_words_in_corpus)
    print(f"Index built! Found {len(all_words_in_corpus):,} total words, {len(corpus_counts):,} unique forms.")

    # 3. Setup Lexique mapping
    lemma_to_forms = build_reverse_lexique()
    
    # 4. Instant Lookup (WITH PROGRESS TRACKER)
    total_words = len(base_words)
    print(f"Instantly looking up {total_words} words...")
    results = []
    
    count = 0
    for word, base_freq in base_words.items():
        count += 1
        
        # --- NEW: Progress Tracker ---
        if count % 50 == 0 or count == total_words:
            print(f"[{count}/{total_words}] (now at word: {word})")
            
        forms_to_search = lemma_to_forms.get(word, {word})
        
        # Instead of scanning text, just ask the dictionary for the pre-calculated number!
        corpus_freq = sum(corpus_counts.get(form, 0) for form in forms_to_search)
            
        total_freq = base_freq + corpus_freq
        results.append((word, base_freq, corpus_freq, total_freq))

    # 5. Sort by Total Frequency and Save
    results.sort(key=lambda x: x[3], reverse=True)
    
    output_path = os.path.join(OUTPUT_DIR, "total_freq_count.txt")
    with open(output_path, "w", encoding="utf-8") as f:
        # Save exact formatting requested: Word, Freq in Book 1, Total Freq
        for word, base_f, corpus_f, total_f in results:
            f.write(f"{word},{base_f},{total_f}\n")

    print("\n" + "="*50)
    print(f"✅ FAST CORPUS ANALYSIS COMPLETE")
    print(f"Results saved to: {output_path}")
    print("="*50 + "\n")
    
    print(f"{'WORD'.ljust(18)} | {'BASE'.ljust(6)} | {'CORPUS'.ljust(8)} | {'TOTAL'}")
    print("-" * 50)
    for word, base_f, corpus_f, total_f in results[:20]:
        print(f"{word.ljust(18)} | {str(base_f).ljust(6)} | {str(corpus_f).ljust(8)} | {total_f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Calculate corpus frequency for a list of words.")
    parser.add_argument("input_file", help="e.g., les_trois_mousquetaires_frequent.txt")
    parser.add_argument("books", nargs='+', help="List of book filenames (without .txt) to search across")
    
    parser.add_argument("--min", type=int, default=1, help="Minimum frequency in the base book")
    parser.add_argument("--max", type=int, default=9999, help="Maximum frequency in the base book")
    
    args = parser.parse_args()
    analyze_corpus(args.input_file, args.books, args.min, args.max)