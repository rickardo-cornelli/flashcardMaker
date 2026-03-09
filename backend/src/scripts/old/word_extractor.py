import os
import spacy
import re
import argparse
from collections import Counter

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
BOOKS_DIR = os.path.join(ROOT_DIR, "books")
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
BASELINE_FILE = os.path.join(OUTPUT_DIR, "top_5000_french_lemmas.txt")
IGNORE_FILE = os.path.join(OUTPUT_DIR, "ignore_list.txt")
LEXIQUE_FILE = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def load_lexique_dictionary():
    """Creates a mapping from conjugation to infinitive (e.g., 'cria' -> 'crier')."""
    lookup = {}
    if not os.path.exists(LEXIQUE_FILE):
        print("WARNING: Lexique383.tsv not found. Lemmatization might be less accurate.")
        return lookup
    
    print("Loading Lexique dictionary for perfect lemmatization...")
    with open(LEXIQUE_FILE, "r", encoding="utf-8", errors="ignore") as f:
        next(f) # Skip header
        for line in f:
            parts = line.split('\t')
            if len(parts) > 3:
                word = parts[0].lower()
                lemma = parts[2].lower()
                if word != lemma:
                    lookup[word] = lemma
    return lookup

def clean_gutenberg_text(text):
    start_pattern = r"\*\*\* START OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    end_pattern = r"\*\*\* END OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    end_match = re.search(end_pattern, text, re.IGNORECASE)
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    clean_text = text[start_idx:end_idx]
    clean_text = clean_text.replace("’", "'").replace("_", "").replace("--", " ")
    return clean_text

def reconstruct_paragraphs(text):
    raw_paragraphs = re.split(r'\n\s*\n', text)
    return [re.sub(r'\s+', ' ', p.replace('\n', ' ')).strip() for p in raw_paragraphs if p.strip()]

def load_text_list(filepath):
    if not os.path.exists(filepath): return set()
    with open(filepath, "r", encoding="utf-8") as f:
        return {line.strip().lower() for line in f if line.strip()}

def extract_book_vocabulary(book_name, threshold):
    book_path = os.path.join(BOOKS_DIR, f"{book_name}.txt")
    if not os.path.exists(book_path):
        print(f"ERROR: {book_path} not found.")
        return

    top_5000_lemmas = load_text_list(BASELINE_FILE)
    ignored_words = load_text_list(IGNORE_FILE)
    lexique_lookup = load_lexique_dictionary()

    print("Loading SpaCy French model...")
    nlp = spacy.load("fr_core_news_lg")

    with open(book_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    clean_text = clean_gutenberg_text(raw_text)
    paragraphs = reconstruct_paragraphs(clean_text)
    total_words = sum(len(p.split()) for p in paragraphs)

    print(f"Processing '{book_name}'...")
    valid_lemmas = []
    desired_pos = {"NOUN", "VERB", "ADJ", "ADV"}
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            # 1. First check: Is it a valid type and NOT a proper noun?
            if (token.is_alpha and not token.is_stop and len(token) > 1 
                and token.pos_ != "PROPN" and token.pos_ in desired_pos):
                
                raw_word = token.text.lower()
                
                # 2. Get the true lemma using Lexique (fallback to SpaCy)
                lex_lemma = lexique_lookup.get(raw_word, token.lemma_.lower())
                
                norm_raw = raw_word.replace("œ", "oe")
                norm_lemma = lex_lemma.replace("œ", "oe")
                
                # 3. The Double Check: Neither the raw word NOR the lemma is in the top 5000
                if (norm_raw not in top_5000_lemmas) and (norm_lemma not in top_5000_lemmas):
                    if lex_lemma not in ignored_words:
                        valid_lemmas.append(lex_lemma)

    # 2. Count and separate into Frequent and Infrequent
    word_counts = Counter(valid_lemmas)
    
    frequent_words = {w: c for w, c in word_counts.items() if c >= threshold}
    infrequent_words = {w: c for w, c in word_counts.items() if c < threshold}

    # 3. Sort BOTH lists by frequency (Highest frequency first)
    sorted_frequent = sorted(frequent_words.items(), key=lambda x: x[1], reverse=True)
    sorted_infrequent = sorted(infrequent_words.items(), key=lambda x: x[1], reverse=True)

    # 4. Save the FREQUENT words file
    frequent_path = os.path.join(OUTPUT_DIR, f"{book_name}_frequent.txt")
    with open(frequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted_frequent: 
            f.write(f"{word},{count}\n")

    # 5. Save the INFREQUENT words file
    infrequent_path = os.path.join(OUTPUT_DIR, f"{book_name}_infrequent.txt")
    with open(infrequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted_infrequent: 
            f.write(f"{word},{count}\n")

    print("\n" + "="*50)
    print(f"STATS FOR: {book_name}")
    print(f"Unique Lemmas: {len(word_counts)}")
    print(f"Frequent Words (>= {threshold}): {len(sorted_frequent)}")
    print(f"Infrequent Words (< {threshold}): {len(sorted_infrequent)}")
    print("="*50 + "\n")

    for i, (word, count) in enumerate(sorted_frequent[:20]): # Just print top 20 to keep console clean
        print(f"{word.ljust(15)} count: {count}")
        
    print(f"\nSaved frequent list to: {frequent_path}")
    print(f"Saved infrequent list to: {infrequent_path}")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("book_name")
    parser.add_argument("-t", "--threshold", type=int, default=2)
    args = parser.parse_args()
    extract_book_vocabulary(args.book_name, args.threshold)