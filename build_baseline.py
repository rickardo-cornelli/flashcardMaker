import os
import csv
import zipfile
import io
import requests

OUTPUT_DIR = "wordextractions"
os.makedirs(OUTPUT_DIR, exist_ok=True)
list_path = os.path.join(OUTPUT_DIR, "top_5000_french_lemmas.txt")
# Define the path where we want to save the actual dictionary
tsv_save_path = os.path.join(OUTPUT_DIR, "Lexique383.tsv")

def build_lexique_baseline():
    print("Downloading the official Lexique 3.83 database (approx 15MB)...")
    url = "http://www.lexique.org/databases/Lexique383/Lexique383.zip"
    
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        
        print("Unzipping and SAVING Lexique383.tsv...")
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            # --- NEW PART: Actually save the file to disk ---
            with z.open('Lexique383.tsv') as f_in:
                content_bytes = f_in.read()
                # Save the raw TSV file so the word_extractor.py can use it later
                with open(tsv_save_path, "wb") as f_out:
                    f_out.write(content_bytes)
                print(f"Dictionary saved to {tsv_save_path}")
            # ------------------------------------------------
            
            # Now decode for processing the top 5000 list
            content = content_bytes.decode('utf-8').splitlines()
                
        print("Parsing Lexique database for book frequencies...")
        reader = csv.DictReader(content, delimiter='\t')
        
        lemma_frequencies = {}
        
        for row in reader:
            lemma = row['lemme']
            freq = float(row['freqlemlivres']) if row['freqlemlivres'] else 0.0
            cgram = row['cgram']
            
            valid_pos = ['NOM', 'VER', 'ADJ', 'ADV', 'PRE', 'CON', 'ART', 'PRO']
            
            if cgram in valid_pos and lemma.isalpha():
                if lemma not in lemma_frequencies or freq > lemma_frequencies[lemma]:
                    lemma_frequencies[lemma] = freq
                    
        print("Sorting lemmas by book frequency...")
        sorted_lemmas = sorted(lemma_frequencies.items(), key=lambda item: item[1], reverse=True)
        top_5000 = [lemma for lemma, freq in sorted_lemmas[:5000]]
        
        print(f"Success! Saving {len(top_5000)} baseline lemmas to {list_path}...")
        with open(list_path, "w", encoding="utf-8") as f:
            for lemma in sorted(top_5000):
                f.write(f"{lemma}\n")
                
        print("Everything is ready! You now have both the baseline AND the dictionary file.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    build_lexique_baseline()