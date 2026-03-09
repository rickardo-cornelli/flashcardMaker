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

def load_lexique_dictionary():
    lookup = {}
    surface_to_lemmas = defaultdict(set)
    
    if not os.path.exists(LEXIQUE_FILE):
        print("WARNING: Lexique383.tsv not found.")
        return lookup, surface_to_lemmas
    
    print("Loading Lexique dictionary for extraction & purging...")
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f)
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                surface = parts[0].lower()
                lemma = parts[2].lower()
                
                if surface != lemma: 
                    lookup[surface] = lemma
                surface_to_lemmas[surface].add(lemma)
                surface_to_lemmas[surface].add(surface)
                
    return lookup, surface_to_lemmas

def clean_gutenberg_text(text):
    start_pattern = r"\*\*\* START OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    end_pattern = r"\*\*\* END OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    end_match = re.search(end_pattern, text, re.IGNORECASE)
    
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    
    if start_idx >= end_idx:
        start_idx = 0
        end_idx = len(text)
        
    clean_text = text[start_idx:end_idx]
    clean_text = clean_text.replace("’", "'").replace("_", "").replace("--", " ")
    return clean_text

def reconstruct_paragraphs(text):
    raw_paragraphs = re.split(r'\n\s*\n', text)
    return [re.sub(r'\s+', ' ', p.replace('\n', ' ')).strip() for p in raw_paragraphs if p.strip()]

def load_text_list(filepath):
    if not os.path.exists(filepath): 
        return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip() and not line.startswith('#')}

def extract_book_vocabulary(book_name, threshold):
    book_path = os.path.join(BOOKS_DIR, f"{book_name}.txt")
    if not os.path.exists(book_path):
        print(f"ERROR: {book_path} not found.")
        return

    book_out_dir = os.path.join(OUTPUT_DIR, book_name)
    os.makedirs(book_out_dir, exist_ok=True)

    top_5000_lemmas = load_text_list(BASELINE_FILE)
    ignored_words = load_text_list(IGNORE_FILE)
    lex_lookup, surface_to_lemmas = load_lexique_dictionary()

    print("Loading SpaCy French model...")
    nlp = spacy.load("fr_core_news_lg")

    with open(book_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    clean_text = clean_gutenberg_text(raw_text)
    paragraphs = reconstruct_paragraphs(clean_text)

    print(f"Processing '{book_name}'...")
    
    # --- NEW: Trackers for unique words to give precise stats ---
    unique_all_found = set()
    filtered_top5000 = set()
    filtered_ignore = set()
    filtered_ghosts = set()
    valid_lemmas = []
    
    desired_pos = {"NOUN", "VERB", "ADJ", "ADV"}
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            if (token.is_alpha and not token.is_stop and len(token) > 1 
                and token.pos_ != "PROPN" and token.pos_ in desired_pos):
                
                raw_word = token.text.lower()
                lex_lemma = lex_lookup.get(raw_word, token.lemma_.lower()).replace("œ", "oe")
                
                unique_all_found.add(lex_lemma)
                
                # Check 1: Is the lemma directly in the Top 5000?
                if lex_lemma in top_5000_lemmas:
                    filtered_top5000.add(lex_lemma)
                    continue
                    
                # Check 2: Is it directly in your Personal Ignore List?
                if lex_lemma in ignored_words:
                    filtered_ignore.add(lex_lemma)
                    continue
                
                # Check 3: Is it a Disguised Ghost/Participle?
                roots = surface_to_lemmas.get(raw_word, {raw_word, lex_lemma})
                is_ghost = False
                for root in roots:
                    if root in top_5000_lemmas:
                        filtered_ghosts.add(lex_lemma)
                        is_ghost = True
                        break
                    if root in ignored_words:
                        filtered_ignore.add(lex_lemma)
                        is_ghost = True
                        break
                
                if is_ghost:
                    continue
                
                # If it survives all checks, it's a valid word to learn!
                valid_lemmas.append(lex_lemma)

    word_counts = Counter(valid_lemmas)
    
    frequent_words = {w: c for w, c in word_counts.items() if c >= threshold}
    infrequent_words = {w: c for w, c in word_counts.items() if c < threshold}

    sorted_frequent = sorted(frequent_words.items(), key=lambda x: x[1], reverse=True)
    sorted_infrequent = sorted(infrequent_words.items(), key=lambda x: x[1], reverse=True)

    frequent_path = os.path.join(book_out_dir, f"{book_name}_frequent.txt")
    with open(frequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted_frequent: 
            f.write(f"{word},{count}\n")

    infrequent_path = os.path.join(book_out_dir, f"{book_name}_infrequent.txt")
    with open(infrequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted_infrequent: 
            f.write(f"{word},{count}\n")

    # --- NEW: Beautifully detailed printout ---
    print("\n" + "="*50)
    print(f"✅ EXTRACTION & PURGE COMPLETE FOR: {book_name}")
    print("="*50)
    print(f"Total Unique Words Extracted:     {len(unique_all_found)}")
    print("-" * 50)
    print(f"[-] Filtered by Top 5000 List:    {len(filtered_top5000)}")
    print(f"[-] Filtered by Ignore List:      {len(filtered_ignore)}")
    print(f"[-] Filtered as Disguised Ghosts: {len(filtered_ghosts)}")
    print("-" * 50)
    print(f"Total Valid Words Remaining:      {len(word_counts)}")
    print(f"  -> Frequent Words (>= {threshold}):     {len(sorted_frequent)}")
    print(f"  -> Infrequent Words (< {threshold}):    {len(sorted_infrequent)}")
    print("\nSaved files into: wordextractions/" + book_name + "/")
    print("="*50 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("book_name")
    parser.add_argument("-t", "--threshold", type=int, default=5)
    args = parser.parse_args()
    extract_book_vocabulary(args.book_name, args.threshold)