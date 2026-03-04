from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deep_translator import GoogleTranslator
import requests
import mwparserfromhell
import re
import time

# --- Configuration ---
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "anki-french-dict/1.0 (your_email@example.com)"})

def fetch_batch_wikitext(word_list):
    """Fetches wikitext for up to 50 words in a single API call."""
    url = "https://fr.wiktionary.org/w/api.php"
    params = {
        "action": "query",
        "prop": "revisions",
        "rvprop": "content",
        "format": "json",
        "titles": "|".join(word_list),
        "redirects": 1
    }
    try:
        resp = SESSION.get(url, params=params, timeout=15)
        data = resp.json()
        
        results_map = {}
        if "query" in data and "pages" in data["query"]:
            for page_data in data["query"]["pages"].values():
                title = page_data["title"]
                if "revisions" in page_data:
                    results_map[title] = page_data["revisions"][0]["*"]
                else:
                    results_map[title] = None
        return results_map
    except Exception as e:
        print(f"Error fetching batch: {e}")
        return {}

def extract_french_section(raw_text):
    """Isolates the French portion of the Wiktionary page."""
    if not raw_text: 
        return ""
    sections = re.split(r'==\s*\{\{langue\|fr\}\}\s*==', raw_text, flags=re.IGNORECASE)
    if len(sections) < 2: 
        return ""
    # Stop before the next language section (== {{langue|...}} ==)
    return re.split(r'==\s*\{\{langue\|', sections[1], flags=re.IGNORECASE)[0]

def process_wiktionary_templates(fr_section):
    """
    Resolves multi-line templates and converts domain tags 
    (flags) into readable text like '(Militaire)'.
    """
    parsed = mwparserfromhell.parse(fr_section)
    
    # Templates to delete entirely
    delete_templates = ['source', 'sans source', 'citation', 'ouvrage', 'réf', 'référer', 'lien web', 'article', 'pron']
    # Structural templates to keep as-is (just for their text)
    structural_templates = ['lien', 'l', 'm', 'f', 'p', 's', 'w', 'langue', 'variante de']

    for template in parsed.filter_templates():
        t_name = str(template.name).lower().strip()
        
        # 1. Handle Example Templates ({{exemple|...}})
        if t_name in ['exemple', 'ex', 'ux', 'q']:
            text_val = ""
            for param in template.params:
                p_name = str(param.name).strip()
                if p_name in ['lang', 'source', 'auteur', 'titre', 'ouvrage', 'date', 'page']: continue
                p_val = str(param.value).strip()
                if p_val == "fr": 
                    continue
                text_val = p_val
                break
            try:
                # Flatten newlines within examples to keep the # list structure clean
                parsed.replace(template, text_val.replace('\n', ' '))
            except ValueError: 
                pass

        # 2. Convert standard Context Tags
        elif t_name in ['lexique', 'term', 'itf', 'inflected']:
            labels = [str(p.value).strip() for p in template.params if str(p.value).strip() not in ["fr", ""]]
            label_text = f"({', '.join(labels)}) " if labels else ""
            try: 
                parsed.replace(template, label_text)
            except ValueError: 
                pass

        # 3. Dynamic Catch-all for Flags (e.g. {{militaire|fr}})
        elif t_name not in structural_templates and t_name not in delete_templates:
            # If it's a simple template (no key=value pairs), treat it as a flag
            has_named_params = any(not str(p.name).isdigit() for p in template.params)
            if not has_named_params:
                extra_labels = [str(p.value).strip() for p in template.params if str(p.value).strip() not in ['fr', '']]
                all_labels = [t_name.capitalize()] + extra_labels
                try: 
                    parsed.replace(template, f"({', '.join(all_labels)}) ")
                except ValueError: 
                    pass

        # 4. Cleanup junk
        elif t_name in delete_templates:
            try: 
                parsed.remove(template)
            except ValueError: 
                pass

    return str(parsed)

def clean_sentence(text):
    """Final strip of Wiki formatting like [[links]] or '''bold'''."""
    parsed = mwparserfromhell.parse(text)
    clean = parsed.strip_code()
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = clean.replace("'''", "").replace("''", "")
    # Cleanup parentheses spacing
    clean = re.sub(r'\(\s+', '(', clean)
    clean = re.sub(r'\s+\)', ')', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

def parse_dictionary(wikitext_processed):
    """Splits processed text into definition and example pairs."""
    entries = []
    current_entry = None
    
    for line in wikitext_processed.split('\n'):
        line = line.strip()
        if not line: 
            continue
        
        # DEFINITION (#)
        if line.startswith('#') and not (line.startswith('#*') or line.startswith('##')):
            clean_def = clean_sentence(line.lstrip('# '))
            if clean_def:
                current_entry = {'definition': clean_def, 'examples': []}
                entries.append(current_entry)
                
        # EXAMPLE (#*)
        elif line.startswith('#*') and current_entry is not None:
            clean_ex = clean_sentence(line.lstrip('#* '))
            if clean_ex and clean_ex != current_entry['definition']:
                if clean_ex not in current_entry['examples']:
                    current_entry['examples'].append(clean_ex)
    return entries

def run_anki_generator(word_list):
    """Main coordinator that handles batching and processing."""
    master_results = {}
    
    # Chunking into 50s
    for i in range(0, len(word_list), 50):
        chunk = word_list[i : i + 50]
        print(f"Processing batch {i//50 + 1}: {chunk[0]}...")
        
        batch_raw = fetch_batch_wikitext(chunk)
        
        for word, raw in batch_raw.items():
            if not raw:
                master_results[word] = []
                continue
            
            fr_text = extract_french_section(raw)
            clean_wikitext = process_wiktionary_templates(fr_text)
            master_results[word] = parse_dictionary(clean_wikitext)
        
        time.sleep(1) # Respectful delay
        
    return master_results



app = FastAPI()

# Allow Quasar to talk to Python locally
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Since it's local dev, * is fine for now
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "anki-french-dict/1.0 (your_email@example.com)"})

class WordRequest(BaseModel):
    words: list[str]

def get_wikimedia_images(word, limit=5):
    """Fetches image URLs from Wikimedia Commons, falls back to English if empty."""
    url = "https://commons.wikimedia.org/w/api.php"
    
    def search_commons(search_term):
        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"filetype:bitmap {search_term}", # bitmap filters out audio/video
            "gsrlimit": limit,
            "prop": "imageinfo",
            "iiprop": "url",
            "format": "json"
        }
        try:
            resp = SESSION.get(url, params=params, timeout=10)
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            return [p.get("imageinfo", [{}])[0].get("url") for p in pages.values() if p.get("imageinfo")]
        except Exception:
            return []

    # 1. Try French first
    images = search_commons(word)
    
    # 2. Fallback to English if no images found
    if not images:
        try:
            english_word = GoogleTranslator(source='fr', target='en').translate(word)
            print(f"No images for '{word}'. Trying English: '{english_word}'")
            images = search_commons(english_word)
        except Exception as e:
            print(f"Translation failed: {e}")
            
    return images

# ... [KEEP YOUR EXISTING FUNCS: fetch_batch_wikitext, extract_french_section, process_wiktionary_templates, clean_sentence, parse_dictionary] ...
# (I am omitting them here for brevity, just paste your exact functions here)

@app.post("/api/fetch-words")
def fetch_words_endpoint(req: WordRequest):
    """The API endpoint Quasar will call."""
    master_results = {}
    word_list = req.words
    
    # Process in chunks of 50
    for i in range(0, len(word_list), 50):
        chunk = word_list[i : i + 50]
        batch_raw = fetch_batch_wikitext(chunk) # Your existing function
        
        for word, raw in batch_raw.items():
            if not raw:
                master_results[word] = {"definitions": [], "images": []}
                continue
            
            fr_text = extract_french_section(raw)
            clean_wikitext = process_wiktionary_templates(fr_text)
            definitions = parse_dictionary(clean_wikitext)
            
            # Fetch images for this word
            images = get_wikimedia_images(word, limit=5)
            
            master_results[word] = {
                "definitions": definitions,
                "images": images
            }
        time.sleep(1)
        
    return master_results

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)