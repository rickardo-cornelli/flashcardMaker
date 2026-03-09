import os
import re
import argparse
from collections import defaultdict, Counter

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
BOOKS_DIR = os.path.join(ROOT_DIR, "books")
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def build_reverse_lexique():
    lemma_to_forms = defaultdict(set)
    if not os.path.exists(LEXIQUE_FILE):
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

def analyze_and_filter_corpus(input_file, book_names, threshold):
    # --- NEW: Figure out the subfolder name based on the input file ---
    folder_name = input_file.replace("_infrequent.txt", "")
    book_out_dir = os.path.join(OUTPUT_DIR, folder_name)
    input_path = os.path.join(book_out_dir, input_file)
    
    if not os.path.exists(input_path):
        print(f"ERROR: {input_path} not found. Did you run the extractor first?")
        return

    # Load the base words
    base_words = {}
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) >= 2:
                word = parts[0].strip()
                count = int(parts[1].strip())
                base_words[word] = count

    # Build the massive index
    print("Building master index of all words in the corpus. This takes ~2 seconds...")
    corpus_text = get_raw_book_text(book_names)
    
    all_words_in_corpus = re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', corpus_text)
    corpus_counts = Counter(all_words_in_corpus)
    lemma_to_forms = build_reverse_lexique()
    
    print(f"Calculating totals and filtering at threshold >= {threshold}...")
    results = []
    
    for word, base_freq in base_words.items():
        forms_to_search = lemma_to_forms.get(word, {word})
        corpus_freq = sum(corpus_counts.get(form, 0) for form in forms_to_search)
        total_freq = base_freq + corpus_freq
            
        # Actual Filtering
        if total_freq >= threshold:
            results.append((word, total_freq))

    # Sort and Save
    results.sort(key=lambda x: x[1], reverse=True)
    
    # --- NEW: Save into the subfolder ---
    output_name = f"{folder_name}_rescued_corpus_frequent.txt"
    output_path = os.path.join(book_out_dir, output_name)
    
    with open(output_path, "w", encoding="utf-8") as f:
        for word, total_f in results:
            f.write(f"{word},{total_f}\n")

    print("\n" + "="*50)
    print("✅ CORPUS ANALYSIS & FILTER COMPLETE")
    print(f"Threshold Used: {threshold}")
    print(f"Final List ({len(results)} words) saved to: wordextractions/{folder_name}/{output_name}")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyze corpus and filter in one step.")
    parser.add_argument("input_file", help="e.g., vingt_ans_apres_infrequent.txt")
    parser.add_argument("books", nargs='+', help="List of corpus books")
    parser.add_argument("-t", "--threshold", type=int, default=10, help="Total corpus frequency to keep")
    
    args = parser.parse_args()
    analyze_and_filter_corpus(args.input_file, args.books, args.threshold)