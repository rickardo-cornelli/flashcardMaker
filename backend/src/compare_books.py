import argparse
import os

def extract_words_from_file(filepath):
    """Reads a _frequent.txt file and returns a set of the words (ignoring counts)."""
    words = set()
    if not os.path.exists(filepath):
        print(f"ERROR: Could not find file -> {filepath}")
        return words
        
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                # Split by comma and grab the first part (the word itself)
                word = line.split(',')[0].strip()
                if word:
                    words.add(word)
    return words

def compute_intersection(file1, file2):
    print(f"Loading {os.path.basename(file1)}...")
    words1 = extract_words_from_file(file1)
    
    print(f"Loading {os.path.basename(file2)}...")
    words2 = extract_words_from_file(file2)
    
    if not words1 or not words2:
        print("Cannot compare because one or both files are empty/missing.")
        return

    # Calculate the intersection using Python Set logic
    shared_words = words1.intersection(words2)
    
    # Calculate percentages
    pct_file1 = (len(shared_words) / len(words1)) * 100
    pct_file2 = (len(shared_words) / len(words2)) * 100

    # Print the results beautifully
    print("\n" + "="*50)
    print("📚 VOCABULARY OVERLAP ANALYSIS")
    print("="*50)
    print(f"Book 1: {len(words1)} unique words to learn")
    print(f"Book 2: {len(words2)} unique words to learn")
    print("-" * 50)
    print(f"🔥 INTERSECTION: {len(shared_words)} words appear in BOTH books!")
    print("-" * 50)
    print(f"If you read Book 1 first, you already know {pct_file2:.1f}% of the tough vocabulary in Book 2.")
    print(f"If you read Book 2 first, you already know {pct_file1:.1f}% of the tough vocabulary in Book 1.")
    print("="*50 + "\n")
    
    if shared_words:
        # Show a quick sample of the overlapping words
        sample = list(shared_words)[:15]
        print(f"Sample of shared words:\n{', '.join(sample)}...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute the intersection of words between two books.")
    parser.add_argument("file1", type=str, help="Path to the first _frequent.txt file")
    parser.add_argument("file2", type=str, help="Path to the second _frequent.txt file")
    
    args = parser.parse_args()
    compute_intersection(args.file1, args.file2)