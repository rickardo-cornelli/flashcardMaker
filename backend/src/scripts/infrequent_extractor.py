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
                surface_to_lemmas[surface].add(lemma)
                surface_to_lemmas[surface].add(surface)
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

def extract_infrequent_vocabulary(target_book, corpus_books, book_thresh, corpus_thresh):
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

    print(f"\n--- PHASE 1: EXTRACTING NOISE FROM '{target_book}' ---")
    valid_lemmas = []
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            if token.is_alpha and not token.is_stop and len(token) > 1 and token.pos_ not in {"PROPN", "PUNCT"} and token.pos_ in {"NOUN", "VERB", "ADJ", "ADV"}:
                raw_word = token.text.lower()
                lex_lemma = lex_lookup.get(raw_word, token.lemma_.lower()).replace("œ", "oe")
                
                if lex_lemma in top_5000_lemmas or lex_lemma in ignored_words:
                    continue
                
                is_ghost = False
                for root in surface_to_lemmas.get(raw_word, {raw_word, lex_lemma}):
                    if root in top_5000_lemmas or root in ignored_words:
                        is_ghost = True; break
                
                if not is_ghost: valid_lemmas.append(lex_lemma)

    word_counts = Counter(valid_lemmas)
    
    # We ONLY care about the tail words
    tail_words = {w: c for w, c in word_counts.items() if c < book_thresh}
    
    true_infrequent_list = []

    if corpus_books:
        print(f"\n--- PHASE 2: FILTERING OUT RESCUED WORDS ---")
        other_books = [b for b in corpus_books if b != target_book]
        corpus_text = get_raw_corpus_text(other_books)
        corpus_counts = Counter(re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', corpus_text))

        for word, base_freq in tail_words.items():
            total_freq = base_freq + sum(corpus_counts.get(form, 0) for form in lemma_to_forms.get(word, {word}))
            # Only keep it if it FAILS the rescue check
            if total_freq < corpus_thresh:
                true_infrequent_list.append((word, total_freq))
    else:
        for word, base_freq in tail_words.items():
            true_infrequent_list.append((word, base_freq))

    # Sort the noise by total frequency
    true_infrequent_list.sort(key=lambda x: x[1], reverse=True)

    # Save ONLY to _infrequent.txt
    infrequent_path = os.path.join(book_out_dir, f"{target_book}_infrequent.txt")
    with open(infrequent_path, "w", encoding="utf-8") as f:
        for word, freq in true_infrequent_list: f.write(f"{word},{freq}\n")

    print("\n" + "="*50)
    print(f"✅ INFREQUENT EXTRACTION COMPLETE FOR: {target_book}")
    print("="*50)
    print(f"Isolated {len(true_infrequent_list)} true 'noise' words (Freq < {book_thresh} in book AND < {corpus_thresh} in corpus).")
    print(f"Saved directly to: wordextractions/{target_book}/{target_book}_infrequent.txt")
    print("Your _frequent.txt file was untouched.")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract ONLY the rare 'noise' words that fail both thresholds.")
    parser.add_argument("target_book")
    parser.add_argument("corpus_books", nargs='*', help="List of other books to search against")
    parser.add_argument("-t", "--threshold", type=int, default=5, help="Minimum freq in the target book")
    parser.add_argument("-c", "--corpus-threshold", type=int, default=15, help="Minimum freq across the entire corpus")
    args = parser.parse_args()
    
    extract_infrequent_vocabulary(args.target_book, args.corpus_books, args.threshold, args.corpus_threshold)