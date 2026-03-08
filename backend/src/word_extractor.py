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
IGNORE_FILE = os.path.join(OUTPUT_DIR, "my_ignored_words.txt")

def clean_gutenberg_text(text):
    """Removes Gutenberg headers, footers, and normalizes typography for SpaCy."""
    start_pattern = r"\*\*\* START OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    end_pattern = r"\*\*\* END OF TH[E|IS] PROJECT GUTENBERG EBOOK.*? \*\*\*"
    
    start_match = re.search(start_pattern, text, re.IGNORECASE)
    end_match = re.search(end_pattern, text, re.IGNORECASE)
    
    start_idx = start_match.end() if start_match else 0
    end_idx = end_match.start() if end_match else len(text)
    
    clean_text = text[start_idx:end_idx]
    
    # --- TYPOGRAPHY NORMALIZATION ---
    clean_text = clean_text.replace("’", "'") 
    clean_text = clean_text.replace("_", "")
    clean_text = clean_text.replace("--", " ")
    
    return clean_text

def reconstruct_paragraphs(text):
    """Glues hard-wrapped lines back together into proper NLP sentences."""
    # Split by double-newlines (which Gutenberg uses for actual paragraphs)
    raw_paragraphs = re.split(r'\n\s*\n', text)
    
    healed_paragraphs = []
    for p in raw_paragraphs:
        # Replace single newlines inside the paragraph with a space
        joined_text = p.replace('\n', ' ')
        # Clean up any accidental double spaces
        joined_text = re.sub(r'\s+', ' ', joined_text).strip()
        
        if joined_text:
            healed_paragraphs.append(joined_text)
            
    return healed_paragraphs

def load_text_list(filepath):
    words = set()
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                word = line.strip().lower()
                if word: words.add(word)
    return words

def extract_book_vocabulary(book_name, threshold):
    book_filename = f"{book_name}.txt"
    book_path = os.path.join(BOOKS_DIR, book_filename)
    
    if not os.path.exists(book_path):
        print(f"ERROR: Could not find '{book_filename}' inside the '{BOOKS_DIR}' folder.")
        return

    top_5000_lemmas = load_text_list(BASELINE_FILE)
    ignored_words = load_text_list(IGNORE_FILE)

    print("Loading SpaCy Large French model...")
    nlp = spacy.load("fr_core_news_lg")

    with open(book_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("Stripping Gutenberg headers and normalizing typography...")
    clean_text = clean_gutenberg_text(raw_text)
    
    print("Reconstructing hard-wrapped sentences for NLP accuracy...")
    paragraphs = reconstruct_paragraphs(clean_text)
    
    # Calculate words based on healed paragraphs
    total_words = sum(len(p.split()) for p in paragraphs)

    print(f"Lemmatizing '{book_name}' content...")
    valid_lemmas = []
    
    # ... (start of the script remains the same)

    print(f"Lemmatizing '{book_name}' content...")
    valid_lemmas = []
    
    # Define the Parts of Speech (POS) we actually want for flashcards
    # NOUN = Nouns, VERB = Verbs, ADJ = Adjectives, ADV = Adverbs
    desired_pos = {"NOUN", "VERB", "ADJ", "ADV"}
    
    for doc in nlp.pipe(paragraphs, batch_size=50):
        for token in doc:
            # New filter: We added the check for token.pos_ in desired_pos
            if (token.is_alpha and 
                not token.is_stop and 
                len(token) > 1 and 
                token.pos_ != "PROPN" and
                token.pos_ in desired_pos): # <-- THIS IS THE NEW LINE
                
                lemma = token.lemma_.lower()
                normalized = lemma.replace("œ", "oe")
                
                if normalized not in top_5000_lemmas and lemma not in ignored_words:
                    valid_lemmas.append(lemma)

    # ... (rest of the script remains the same)

    word_counts = Counter(valid_lemmas)
    frequent_words = {w: c for w, c in word_counts.items() if c >= threshold}
    infrequent_words = {w: c for w, c in word_counts.items() if c < threshold}

    sorted_frequent = sorted(frequent_words.items(), key=lambda item: item[1], reverse=True)
    frequent_path = os.path.join(OUTPUT_DIR, f"{book_name}_frequent.txt")
    with open(frequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted_frequent:
            f.write(f"{word}\n")

    infrequent_path = os.path.join(OUTPUT_DIR, f"{book_name}_infrequent.txt")
    with open(infrequent_path, "w", encoding="utf-8") as f:
        for word, count in sorted(infrequent_words.items()):
            f.write(f"{word}\n")

    print("\n" + "="*50)
    print(f"STATS FOR: {book_name}")
    print(f"Total Words Processed: {total_words}")
    print(f"Unique Lemmas Found: {len(word_counts)}")
    print(f"Frequent Words (Count >= {threshold}): {len(frequent_words)}")
    print(f"Infrequent Words: {len(infrequent_words)}")
    print("="*50 + "\n")

    for i, (word, count) in enumerate(sorted_frequent):
        print(f"{word.ljust(15)} occurred {count} times.")
        if (i + 1) % 5 == 0:
            print("-" * 30)

    print(f"\nSaved list to: {frequent_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract B2+ vocabulary from a French text file.")
    parser.add_argument("book_name", type=str, help="Name of the text file in the 'books' folder WITHOUT the .txt extension")
    parser.add_argument("-t", "--threshold", type=int, default=2, help="Minimum number of occurrences to be considered frequent")
    
    args = parser.parse_args()
    extract_book_vocabulary(args.book_name, args.threshold)