import argparse
import os

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Adjust this to match your actual structure (3 levels up to root)
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")

def find_overlap(book1, book2):
    # Construct paths automatically
    file1_path = os.path.join(OUTPUT_DIR, book1, f"{book1}_frequent.txt")
    file2_path = os.path.join(OUTPUT_DIR, book2, f"{book2}_frequent.txt")

    if not os.path.exists(file1_path):
        print(f"Error: Could not find file for {book1} at {file1_path}")
        return
    if not os.path.exists(file2_path):
        print(f"Error: Could not find file for {book2} at {file2_path}")
        return

    def get_words(path):
        words = set()
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                parts = line.strip().split(',')
                if parts[0]:
                    words.add(parts[0].lower())
        return words

    words1 = get_words(file1_path)
    words2 = get_words(file2_path)

    overlap = words1.intersection(words2)
    unique_to_1 = words1 - words2
    unique_to_2 = words2 - words1
    
    sorted_overlap = sorted(list(overlap))

    print("\n" + "="*50)
    print(f"📊 VOCABULARY OVERLAP: {book1} vs {book2}")
    print("="*50)
    print(f"{book1:15} | Total Frequent: {len(words1)}")
    print(f"{book2:15} | Total Frequent: {len(words2)}")
    print("-" * 50)
    print(f"SHARED WORDS:    {len(overlap)}")
    print(f"UNIQUE TO {book1.upper()}: {len(unique_to_1)}")
    print(f"UNIQUE TO {book2.upper()}: {len(unique_to_2)}")
    print("="*50)
    
    if sorted_overlap:
        print("\nShared Vocabulary Sample:")
        # Print in 4 columns
        for i in range(0, len(sorted_overlap), 4):
            print("  ".join(f"{word:<15}" for word in sorted_overlap[i:i+4]))
    print("\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("book1", help="Folder name of first book")
    parser.add_argument("book2", help="Folder name of second book")
    args = parser.parse_args()

    find_overlap(args.book1, args.book2)