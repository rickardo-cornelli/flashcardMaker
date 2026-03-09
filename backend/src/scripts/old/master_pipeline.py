import os
import spacy
import re
import argparse
from collections import Counter, defaultdict

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
BOOKS_DIR = os.path.join(ROOT_DIR, "books")
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
BASELINE_FILE = os.path.join(OUTPUT_DIR, "top_5000_french_lemmas.txt")
IGNORE_FILE = os.path.join(OUTPUT_DIR, "ignore_list.txt")
LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def load_text_list(filepath):
    if not os.path.exists(filepath): return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}

def load_lexique_data():
    """Loads mapping, reverse mapping, and valid existence set."""
    lookup = {}
    lemma_to_forms = defaultdict(set)
    valid_lemmas = set()
    
    if not os.path.exists(LEXIQUE_FILE):
        print("ERROR: Lexique383.tsv not found.")
        return lookup, lemma_to_forms, valid_lemmas
    
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f)
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                surface = parts[0].lower()
                lemma = parts[2].lower()
                
                if surface != lemma: lookup[surface] = lemma
                lemma_to_forms[lemma].add(surface)
                lemma_to_forms[surface].add(surface) # self map
                valid_lemmas.add(lemma)
                
    return lookup, lemma_to_forms, valid_lemmas

def clean_gutenberg_text(text):
    start_pattern = r"\*\*\* START OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    end_pattern = r"\*\*\* END OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    end_match = re.search(end_pattern, text, re.IGNORECASE)
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    return text[start_idx:end_idx].replace("’", "'").replace("_", "").replace("--", " ")

def get_raw_corpus_text(book_names):
    combined = ""
    for name in book_names:
        path = os.path.join(BOOKS_DIR, f"{name}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                combined += f.read().lower() + " "
    return combined

def run_pipeline(target_book, corpus_books):
    print(f"\n🚀 STARTING MASTER PIPELINE FOR: {target_book.upper()}")
    
    # 1. LOAD ASSETS
    top_5000 = load_text_list(BASELINE_FILE)
    ignored_words = load_text_list(IGNORE_FILE)
    lex_lookup, lemma_to_forms, valid_lemmas = load_lexique_data()
    
    # 2. EXTRACT TARGET BOOK
    print("\n--- PHASE 1: EXTRACTION ---")
    print("Loading SpaCy & extracting book...")
    nlp = spacy.load("fr_core_news_lg")
    
    book_path = os.path.join(BOOKS_DIR, f"{target_book}.txt")
    with open(book_path, "r", encoding="utf-8") as f:
        clean_text = clean_gutenberg_text(f.read())
        
    paragraphs = [re.sub(r'\s+', ' ', p.replace('\n', ' ')).strip() for p in re.split(r'\n\s*\n', clean_text) if p.strip()]
    
    valid_extracted = []
    desired_pos = {"NOUN", "VERB", "ADJ", "ADV"}
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            if token.is_alpha and not token.is_stop and len(token) > 1 and token.pos_ != "PROPN" and token.pos_ in desired_pos:
                raw_word = token.text.lower()
                lex_lemma = lex_lookup.get(raw_word, token.lemma_.lower())
                
                norm_raw = raw_word.replace("œ", "oe")
                norm_lemma = lex_lemma.replace("œ", "oe")
                
                if norm_raw not in top_5000 and norm_lemma not in top_5000 and lex_lemma not in ignored_words:
                    valid_extracted.append(lex_lemma)

    word_counts = Counter(valid_extracted)
    
    # Splitting into Core (>=5) and Tail (<5)
    core_words = {w: c for w, c in word_counts.items() if c >= 5}
    tail_words = {w: c for w, c in word_counts.items() if c < 5}
    
    print(f"Extracted {len(word_counts)} unique valid lemmas.")
    print(f"  -> {len(core_words)} Core Words (freq >= 5)")
    print(f"  -> {len(tail_words)} Tail Words (freq < 5) to check against corpus")

    # 3. CORPUS CHECK FOR TAIL WORDS
    print("\n--- PHASE 2: CORPUS RESCUE ---")
    print("Building master corpus index (2 seconds)...")
    corpus_text = get_raw_corpus_text(corpus_books)
    corpus_counts = Counter(re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', corpus_text))
    
    tail_10_rescued = {}
    tail_15_rescued = {}
    
    for word, base_freq in tail_words.items():
        forms = lemma_to_forms.get(word, {word})
        total_freq = base_freq + sum(corpus_counts.get(form, 0) for form in forms)
        
        if total_freq >= 10: tail_10_rescued[word] = total_freq
        if total_freq >= 15: tail_15_rescued[word] = total_freq

    print("Corpus Check Complete.")
    print(f"  -> Words rescued at Threshold 10: {len(tail_10_rescued)}")
    print(f"  -> Words rescued at Threshold 15: {len(tail_15_rescued)}")
    print(f"  -> DIFFERENCE: You gain {len(tail_10_rescued) - len(tail_15_rescued)} extra stylistic words by using Threshold 10.")
    
    # 4. MERGE & PURGE
    print("\n--- PHASE 3: THE PURGE ---")
    print("Merging Core words with Threshold 10 rescued words...")
    
    # We will use Threshold 10 for the final list to give you the best coverage
    merged_list = {**core_words, **tail_10_rescued}
    
    kept_words = []
    trashed_words = []
    
    for word, count in merged_list.items():
        is_common = False
        is_fake = False
        
        # Disguised Word Check
        lemmas = lemma_to_forms.get(word, {word})
        for lem in lemmas:
            if lem in top_5000:
                is_common = True
                break
                
        # Existence Check
        if word not in valid_lemmas:
            is_fake = True
            
        if is_common or is_fake:
            trashed_words.append(word)
        else:
            kept_words.append((word, count))

    print(f"Purge Complete.")
    print(f"  -> Kept pure words: {len(kept_words)}")
    print(f"  -> Trashed ghosts/participles: {len(trashed_words)}")

    # 5. SAVE OUTPUT
    kept_words.sort(key=lambda x: x[1], reverse=True)
    output_path = os.path.join(OUTPUT_DIR, f"{target_book}_ultimate_frequent.txt")
    
    with open(output_path, "w", encoding="utf-8") as f:
        for word, count in kept_words:
            f.write(f"{word},{count}\n")
            
    print("\n" + "="*50)
    print(f"✅ PIPELINE FINISHED FOR {target_book.upper()}")
    print(f"Saved directly to: {os.path.basename(output_path)}")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract, analyze, and purge in one go.")
    parser.add_argument("target_book", help="The book to extract (e.g., vingt_ans_apres)")
    parser.add_argument("corpus_books", nargs='+', help="List of all books in corpus (including target)")
    
    args = parser.parse_args()
    run_pipeline(args.target_book, args.corpus_books)