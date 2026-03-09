import os
import argparse

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")

def filter_corpus_list(filename, total_threshold, output_name):
    input_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(input_path):
        print(f"ERROR: Could not find {input_path}")
        return

    # Ensure it ends with _frequent.txt so Quasar finds it!
    if not output_name.endswith("_frequent.txt"):
        output_name += "_frequent.txt"
        
    output_path = os.path.join(OUTPUT_DIR, output_name)

    kept_words = []
    removed_count = 0

    print(f"Filtering '{filename}' for words with TOTAL frequency >= {total_threshold}...")

    with open(input_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        if "Total_Freq" in lines[0] or "Base_Freq" in lines[0]:
            lines = lines[1:]

        for line in lines:
            parts = line.strip().split(',')
            if len(parts) >= 3:
                word = parts[0].strip()
                base_freq = int(parts[1].strip())
                total_freq = int(parts[2].strip())

                if total_freq >= total_threshold:
                    kept_words.append((word, total_freq))
                else:
                    removed_count += 1

    with open(output_path, 'w', encoding='utf-8') as f:
        for word, total_freq in kept_words:
            f.write(f"{word},{total_freq}\n")

    print("\n" + "="*50)
    print("🧹 CORPUS CLEANUP COMPLETE")
    print("="*50)
    print(f"Words Kept (The God List): {len(kept_words)}")
    print(f"Ghost Words Trashed:       {removed_count}")
    print(f"\nSaved directly for your Quasar App as: {output_name}")
    print("="*50)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Filter corpus results by minimum total frequency.")
    parser.add_argument("filename", type=str, default="total_freq_count.txt", nargs="?", help="The corpus results file")
    parser.add_argument("-t", "--threshold", type=int, default=10, help="Minimum total corpus frequency to keep")
    parser.add_argument("-o", "--output", type=str, default="dumas_high_value", help="Name of the output file")
    
    args = parser.parse_args()
    filter_corpus_list(args.filename, args.threshold, args.output)