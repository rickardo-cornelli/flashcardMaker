import os
import spacy
import re
import argparse
from collections import Counter, defaultdict

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
BOOKS_DIR = os.path.join(ROOT_DIR, "books")
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
BASELINE_FILE = os.path.join(OUTPUT_DIR, "top_5000_french_lemmas.txt")
IGNORE_FILE = os.path.join(OUTPUT_DIR, "ignore_list.txt")
LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def load_lexique_data():
    lookup = {}
    surface_to_lemmas = defaultdict(set)
    lemma_to_forms = defaultdict(set)
    
    if not os.path.exists(LEXIQUE_FILE):
        print("WARNING: Lexique383.tsv not found.")
        return lookup, surface_to_lemmas, lemma_to_forms
    
    print("Loading Lexique dictionary...")
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f)
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                surface = parts[0].lower()
                lemma = parts[2].lower()
                
                if surface != lemma: lookup[surface] = lemma
                # For purging
                surface_to_lemmas[surface].add(lemma)
                surface_to_lemmas[surface].add(surface)
                # For corpus searching
                lemma_to_forms[lemma].add(surface)
                lemma_to_forms[surface].add(surface)
                
    return lookup, surface_to_lemmas, lemma_to_forms

def clean_gutenberg_text(text):
    start_match = re.search(r"\*\*\* START OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*", text, re.IGNORECASE)
    end_match = re.search(r"\*\*\* END OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*", text, re.IGNORECASE)
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    if start_idx >= end_idx: start_idx, end_idx = 0, len(text)
    return text[start_idx:end_idx].replace("’", "'").replace("_", "").replace("--", " ")

def reconstruct_paragraphs(text):
    return [re.sub(r'\s+', ' ', p.replace('\n', ' ')).strip() for p in re.split(r'\n\s*\n', text) if p.strip()]

def load_text_list(filepath):
    if not os.path.exists(filepath): return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}

def get_raw_corpus_text(book_names):
    combined = ""
    for name in book_names:
        path = os.path.join(BOOKS_DIR, f"{name}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                combined += f.read().lower() + " "
    return combined

def extract_master_vocabulary(target_book, corpus_books, book_thresh, corpus_thresh):
    book_path = os.path.join(BOOKS_DIR, f"{target_book}.txt")
    if not os.path.exists(book_path):
        print(f"ERROR: {book_path} not found.")
        return

    book_out_dir = os.path.join(OUTPUT_DIR, target_book)
    os.makedirs(book_out_dir, exist_ok=True)

    top_5000_lemmas = load_text_list(BASELINE_FILE)
    ignored_words = load_text_list(IGNORE_FILE)
    lex_lookup, surface_to_lemmas, lemma_to_forms = load_lexique_data()

    print("Loading SpaCy French model...")
    nlp = spacy.load("fr_core_news_lg")

    with open(book_path, "r", encoding="utf-8") as f:
        paragraphs = reconstruct_paragraphs(clean_gutenberg_text(f.read()))

    print(f"\n--- PHASE 1: EXTRACTING '{target_book}' ---")
    unique_all_found, filtered_top5000, filtered_ignore, filtered_ghosts = set(), set(), set(), set()
    valid_lemmas = []
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            if token.is_alpha and not token.is_stop and len(token) > 1 and token.pos_ not in {"PROPN", "PUNCT"} and token.pos_ in {"NOUN", "VERB", "ADJ", "ADV"}:
                raw_word = token.text.lower()
                lex_lemma = lex_lookup.get(raw_word, token.lemma_.lower()).replace("œ", "oe")
                
                unique_all_found.add(lex_lemma)
                
                if lex_lemma in top_5000_lemmas:
                    filtered_top5000.add(lex_lemma)
                    continue
                if lex_lemma in ignored_words:
                    filtered_ignore.add(lex_lemma)
                    continue
                
                is_ghost = False
                for root in surface_to_lemmas.get(raw_word, {raw_word, lex_lemma}):
                    if root in top_5000_lemmas:
                        filtered_ghosts.add(lex_lemma)
                        is_ghost = True; break
                    if root in ignored_words:
                        filtered_ignore.add(lex_lemma)
                        is_ghost = True; break
                
                if not is_ghost: valid_lemmas.append(lex_lemma)

    word_counts = Counter(valid_lemmas)
    core_words = {w: c for w, c in word_counts.items() if c >= book_thresh}
    tail_words = {w: c for w, c in word_counts.items() if c < book_thresh}

    # --- NEW: IN-MEMORY CORPUS RESCUE ---
    rescued_words = {}
    if corpus_books:
        print(f"\n--- PHASE 2: CORPUS RESCUE (Threshold: {corpus_thresh}+) ---")
        # Prevent double counting: only read the OTHER books in the corpus
        other_books = [b for b in corpus_books if b != target_book]
        corpus_text = get_raw_corpus_text(other_books)
        corpus_counts = Counter(re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', corpus_text))

        for word, base_freq in tail_words.items():
            total_freq = base_freq + sum(corpus_counts.get(form, 0) for form in lemma_to_forms.get(word, {word}))
            if total_freq >= corpus_thresh:
                rescued_words[word] = total_freq

    # --- NEW: MERGE EVERYTHING INTO ONE FILE ---
    print("\n--- PHASE 3: MERGING & SAVING ---")
    final_list = []
    
    # We will use the TOTAL corpus frequency for everything so the list is perfectly sorted
    for word, base_freq in core_words.items():
        if corpus_books:
            total_freq = base_freq + sum(corpus_counts.get(form, 0) for form in lemma_to_forms.get(word, {word}))
        else:
            total_freq = base_freq
        final_list.append((word, total_freq))
        
    for word, total_freq in rescued_words.items():
        final_list.append((word, total_freq))

    final_list.sort(key=lambda x: x[1], reverse=True)

    final_path = os.path.join(book_out_dir, f"{target_book}_frequent_all_dumas.txt")
    with open(final_path, "w", encoding="utf-8") as f:
        for word, freq in final_list: f.write(f"{word},{freq}\n")

    # --- PRINT STATS ---
    print("\n" + "="*50)
    print(f"✅ MASTER EXTRACTION COMPLETE FOR: {target_book}")
    print("="*50)
    print(f"Total Unique Words Extracted:     {len(unique_all_found)}")
    print("-" * 50)
    print(f"[-] Filtered by Top 5000 List:    {len(filtered_top5000)}")
    print(f"[-] Filtered by Ignore List:      {len(filtered_ignore)}")
    print(f"[-] Filtered as Disguised Ghosts: {len(filtered_ghosts)}")
    print("-" * 50)
    print(f"Core Words (>= {book_thresh} in book):       {len(core_words)}")
    if corpus_books:
        print(f"Tail Words (< {book_thresh} in book):        {len(tail_words)}")
        print(f"[+] Rescued from Corpus (>= {corpus_thresh}):   {len(rescued_words)}")
    print("-" * 50)
    print(f"Total Master List Generated:      {len(final_list)} words")
    print(f"\nSaved directly to: wordextractions/{target_book}/{target_book}_frequent_all_dumas.txt")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("target_book")
    parser.add_argument("corpus_books", nargs='*', help="List of other books to search against")
    parser.add_argument("-t", "--threshold", type=int, default=5, help="Minimum freq in the target book")
    parser.add_argument("-c", "--corpus-threshold", type=int, default=15, help="Minimum freq across the entire corpus")
    args = parser.parse_args()
    
    extract_master_vocabulary(args.target_book, args.corpus_books, args.threshold, args.corpus_threshold)