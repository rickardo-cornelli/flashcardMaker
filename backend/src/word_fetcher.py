from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import requests
import mwparserfromhell
import re
import time
import os
from collections import Counter

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "anki-french-dict/2.0 (your_email@example.com)"})

# --- GLOBAL STATE FOR BOOKS ---
LIBRARY_TEXT = ""
WORD_FREQUENCIES = Counter()
KNOWN_WORDS_FILE = "known_words.txt"
NAMES_TO_HIDE = [
    "D'Artagnan", "Athos", "Porthos", "Aramis", "Milady", "Richelieu", 
    "Bonacieux", "Buckingham", "Anne d'Autriche", "Louis XIII", "Felton", 
    "de Winter", "Rochefort", "Tréville"
]

class WordRequest(BaseModel):
    words: list[str]

class ExportRequest(BaseModel):
    selected_data: dict

# --- HELPER FUNCTIONS ---

def get_known_words():
    """Reads the list of words already added to Anki."""
    if not os.path.exists(KNOWN_WORDS_FILE):
        return set()
    with open(KNOWN_WORDS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())

def anonymize_sentence(text):
    """Replaces character names with [Personnage] to avoid spoilers."""
    for name in NAMES_TO_HIDE:
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        text = pattern.sub("[Personnage]", text)
    return text

def get_wikimedia_images(word, limit=15):
    url = "https://commons.wikimedia.org/w/api.php"
    def run_query(query_term):
        params = {
            "action": "query", "generator": "search", "gsrsearch": query_term,
            "gsrnamespace": 6, "gsrlimit": limit, "prop": "imageinfo",
            "iiprop": "url|thumburl", "iiurlwidth": 400, "format": "json"
        }
        try:
            resp = SESSION.get(url, params=params, timeout=10)
            pages = resp.json().get("query", {}).get("pages", {})
            urls = []
            for p in pages.values():
                info = p.get("imageinfo", [{}])[0]
                img_url = info.get("thumburl") or info.get("url")
                if img_url:
                    if img_url.startswith("//"): img_url = "https:" + img_url
                    urls.append(img_url)
            return urls
        except: return []

    fr_images = run_query(word)
    en_images = []
    try:
        en_word = GoogleTranslator(source='fr', target='en').translate(word)
        if en_word.lower() != word.lower(): en_images = run_query(en_word)
    except: pass
    
    return list(dict.fromkeys(fr_images + en_images))[:limit]

def get_robert_data(word):
    url = f"https://dictionnaire.lerobert.com/definition/{word.lower()}"
    try:
        resp = SESSION.get(url, timeout=5)
        if resp.status_code != 200: return []
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Le Robert blocks
        def_blocks = soup.select('.d_dfn') # Definition wrapper
        results = []
        
        for block in def_blocks[:4]:
            # Extract Register/Tag (e.g., Littér., Fig.)
            marq = block.select_one('.d_marq')
            tag = marq.get_text(strip=True) if marq else ""
            if marq: marq.extract() # Remove tag from definition text
            
            # Extract Definition text
            def_text = block.select_one('.d_def')
            def_str = def_text.get_text(strip=True) if def_text else ""
            
            # Extract Example
            ex_text = block.select_one('.d_ex')
            ex_str = ex_text.get_text(strip=True) if ex_text else ""
            
            if def_str:
                results.append({
                    "definition": def_str,
                    "examples": [ex_str] if ex_str else [],
                    "tags": [tag] if tag else []
                })
        return results
    except: return []

def fetch_batch_wikitext(word_list):
    url = "https://fr.wiktionary.org/w/api.php"
    params = {
        "action": "query", "prop": "revisions", "rvprop": "content",
        "format": "json", "titles": "|".join(word_list), "redirects": 1
    }
    try:
        resp = SESSION.get(url, params=params, timeout=15)
        data = resp.json()
        results_map = {}
        if "query" in data and "pages" in data["query"]:
            for page_data in data["query"]["pages"].values():
                title = page_data["title"]
                results_map[title] = page_data["revisions"][0]["*"] if "revisions" in page_data else None
        return results_map
    except: return {}

def extract_french_section(raw_text):
    if not raw_text: return ""
    sections = re.split(r'==\s*\{\{langue\|fr\}\}\s*==', raw_text, flags=re.IGNORECASE)
    if len(sections) < 2: return ""
    return re.split(r'==\s*\{\{langue\|', sections[1], flags=re.IGNORECASE)[0]

def process_wiktionary_templates(fr_section):
    parsed = mwparserfromhell.parse(fr_section)
    delete_templates = ['source', 'sans source', 'citation', 'ouvrage', 'réf', 'lien web', 'pron']
    structural = ['lien', 'l', 'm', 'f', 'p', 's', 'w', 'langue']

    for template in parsed.filter_templates():
        t_name = str(template.name).lower().strip()
        if t_name in ['exemple', 'ex', 'ux']:
            text_val = next((str(p.value).strip() for p in template.params if str(p.name).strip() not in ['lang','source','auteur'] and str(p.value).strip() != "fr"), "")
            try: parsed.replace(template, text_val.replace('\n', ' '))
            except ValueError: pass
        elif t_name not in structural and t_name not in delete_templates:
            # Format tags as [TAG] to parse later
            labels = [str(p.value).strip() for p in template.params if not str(p.name).isdigit() and str(p.value).strip() not in ['fr', '']]
            all_labels = [t_name.capitalize()] + labels
            try: parsed.replace(template, f"[{', '.join(all_labels)}]")
            except ValueError: pass
        elif t_name in delete_templates:
            try: parsed.remove(template)
            except ValueError: pass
    return str(parsed)

def clean_sentence(text):
    parsed = mwparserfromhell.parse(text)
    clean = parsed.strip_code()
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = clean.replace("'''", "").replace("''", "")
    return re.sub(r'\s+', ' ', clean).strip()

def parse_dictionary(wikitext_processed):
    entries = []
    current_entry = None
    
    for line in wikitext_processed.split('\n'):
        line = line.strip()
        if not line: continue
        
        if line.startswith('#') and not (line.startswith('#*') or line.startswith('##')):
            clean_def = clean_sentence(line.lstrip('# '))
            if clean_def:
                # Extract tags formatted as [Tag] at the start of the definition
                tags = []
                while clean_def.startswith('['):
                    end_idx = clean_def.find(']')
                    if end_idx != -1:
                        tags.append(clean_def[1:end_idx])
                        clean_def = clean_def[end_idx+1:].strip()
                    else: break
                
                current_entry = {'definition': clean_def, 'examples': [], 'tags': tags}
                entries.append(current_entry)
                
        elif line.startswith('#*') and current_entry is not None:
            clean_ex = clean_sentence(line.lstrip('#* '))
            if clean_ex and clean_ex != current_entry['definition']:
                current_entry['examples'].append(clean_ex)
    return entries


# --- API ENDPOINTS ---

@app.post("/api/upload-books")
async def upload_books(files: list[UploadFile] = File(...)):
    global LIBRARY_TEXT, WORD_FREQUENCIES
    combined_text = ""
    for file in files:
        content = await file.read()
        combined_text += content.decode("utf-8", errors="ignore") + "\n"
    
    LIBRARY_TEXT = combined_text
    # Build frequency counter (lowercased words, stripped of punctuation)
    words = re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', LIBRARY_TEXT.lower())
    WORD_FREQUENCIES = Counter(words)
    
    return {"status": "success", "length": len(LIBRARY_TEXT), "unique_words": len(WORD_FREQUENCIES)}

@app.post("/api/fetch-words")
def fetch_words_endpoint(req: WordRequest):
    known_words = get_known_words()
    
    # Filter out already known words
    words_to_process = [w for w in req.words if w.lower() not in known_words]
    
    master_results = {}
    batch_raw = fetch_batch_wikitext(words_to_process)
    
    for word in words_to_process:
        raw = batch_raw.get(word)
        wik_defs = parse_dictionary(process_wiktionary_templates(extract_french_section(raw))) if raw else []
        rob_defs = get_robert_data(word)
        images = get_wikimedia_images(word, limit=15)
        
        master_results[word] = {
            "occurrences": WORD_FREQUENCIES.get(word.lower(), 0),
            "wik_definitions": wik_defs,
            "rob_definitions": rob_defs,
            "images": images
        }
    return master_results

@app.post("/api/book-examples")
def fetch_book_examples(word: str = Form(...), offset: int = Form(0)):
    if not LIBRARY_TEXT: return {"examples": [], "total": 0, "hasMore": False}
    
    # Safe zone (first 30%)
    safe_zone = int(len(LIBRARY_TEXT) * 0.3)
    safe_text = LIBRARY_TEXT[:safe_zone]
    
    sentences = re.split(r'(?<=[.!?])\s+', safe_text)
    pattern = re.compile(rf'\b{word}\b', re.IGNORECASE)
    
    matches = []
    for s in sentences:
        clean = " ".join(s.split())
        if pattern.search(clean) and clean not in matches and len(clean) < 300:
            matches.append(clean)
            
    clean_matches = [anonymize_sentence(m) for m in matches]
    paginated = clean_matches[offset : offset + 5]
    
    return {"examples": paginated, "total": len(matches), "hasMore": len(matches) > (offset + 5)}

@app.post("/api/export-anki")
def export_to_anki(req: ExportRequest):
    """Saves the final payload and appends words to known_words.txt"""
    words_added = list(req.selected_data.keys())
    
    with open(KNOWN_WORDS_FILE, "a", encoding="utf-8") as f:
        for word in words_added:
            f.write(word.lower() + "\n")
            
    # Here you would typically generate the CSV or connect to AnkiConnect.
    # For now, we return success and the frontend can handle the JSON.
    return {"status": "success", "added_words": words_added}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)