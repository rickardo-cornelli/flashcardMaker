from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import requests
import mwparserfromhell
import re
import json
import traceback
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
# --- NEW GLOBAL DIRECTORY FOR RESULTS ---
API_RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apiresults"))
os.makedirs(API_RESULTS_DIR, exist_ok=True) # Creates it immediately when the server starts

class WordRequest(BaseModel):
    words: list[str]

# --- 1. Replace the old ExportRequest near the top ---
class CardExportData(BaseModel):
    word: str
    article: str
    definition: str
    examples: list[str]
    imageUrl: str
    transEn: list[str]
    transSv: list[str]
    synonyms: list[str]

class ExportRequest(BaseModel):
    cards: list[CardExportData]
    deck_name: str = "French words"

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

# ---> TARGETED FIX: LE ROBERT FUNCTION (NOW WITH HTML LOGGING) <---
# ---> TARGETED FIX: LE ROBERT FUNCTION (SMART PARSER) <---
def get_robert_data(word):
    url = f"https://dictionnaire.lerobert.com/definition/{word.lower()}"
    print(f"\n{'='*50}\n--- [LE ROBERT SCRAPER START: {word.upper()}] ---\nURL: {url}")
    
    try:
        resp = SESSION.get(url, timeout=10)
        
        # 1. WRITE THE RAW HTML
        raw_filename = os.path.join(API_RESULTS_DIR, f"lerobert_{word.lower()}_raw.html")
        with open(raw_filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
            
        if resp.status_code != 200:
            return {"defs": [], "synonyms": [], "article": ""}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 2. EXTRACT ARTICLE / GENDER
        article = ""
        pos_tag = soup.select_one('.d_cat')
        if pos_tag:
            pos_text = pos_tag.get_text(strip=True).lower()
            if "masculin" in pos_text and "nom" in pos_text: article = "un"
            elif "féminin" in pos_text and "nom" in pos_text: article = "une"
        
        # 3. SMART EXTRACT: DEFINITIONS, CONTEXT, AND INLINE EXAMPLES
        results = []
        
        # Le Robert uses .d_dvn for main definitions and .d_dvl for sub-definitions
        def_blocks = soup.select('.d_dvn, .d_dvl')
        
        for block in def_blocks:
            # Find Context Tags (e.g., "littéraire", "figuré")
            context_tags = [t.get_text(strip=True) for t in block.select('.d_mta, .d_marq') if t.get_text(strip=True)]
            
            # Find the Definition text
            def_node = block.select_one('.d_dfn')
            
            # Find Inline Examples
            inline_examples = [ex.get_text(strip=True) for ex in block.select('.d_xpl')]
            
            if def_node:
                def_str = def_node.get_text(strip=True)
                results.append({
                    "definition": def_str,
                    "examples": inline_examples,
                    "tags": context_tags
                })
            elif inline_examples:
                # Sometimes a sub-block only has context and an example, no strict definition
                # e.g., "par exagération : Taisez-vous, ma tête va éclater !"
                if results:
                    # Append it as an example to the previous definition, but prefix the context
                    prefix = f"[{', '.join(context_tags)}] " if context_tags else ""
                    formatted_examples = [f"{prefix}{ex}" for ex in inline_examples]
                    results[-1]["examples"].extend(formatted_examples)

        # 4. EXTRACT INFLECTED FORMS (Like "ravie")
        if not results:
            inflection_blocks = soup.select('#formes .infl_links .b')
            for block in inflection_blocks:
                h3 = block.select_one('h3')
                if h3:
                    # Also grab the link text if it points to the root word
                    link = block.select_one('.def-link a')
                    def_str = h3.get_text(" ", strip=True)
                    if link:
                        def_str += f" (Voir: {link.get_text(strip=True)})"
                        
                    results.append({
                        "definition": def_str,
                        "examples": [],
                        "tags": ["Forme fléchie"]
                    })

        # 5. EXTRACT EXTERNAL EXAMPLES (.ex_example)
        corpus_elements = soup.select('.ex_example, .infl_example')
        literary_examples = []
        for c in corpus_elements:
            author_tag = c.select_one('.ex_author')
            if author_tag: author_tag.extract()
            text = c.get_text(" ", strip=True)
            if len(text) > 15: literary_examples.append(text)
                
        # FIX: Create a dedicated "Exemples Supplémentaires" block instead of clumping them
        if literary_examples:
            results.append({
                "definition": "Exemples Littéraires / Presse :",
                "examples": literary_examples[:10],
                "tags": ["Corpus"]
            })
            
        # 6. EXTRACT SYNONYMS
        syn_elements = soup.select('.s_syn')
        synonyms = list(dict.fromkeys([s.get_text(strip=True) for s in syn_elements]))

        final_data = {"defs": results, "synonyms": synonyms[:10], "article": article}
        
        # 7. WRITE PARSED JSON
        json_filename = os.path.join(API_RESULTS_DIR, f"lerobert_{word.lower()}_parsed.json")
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
            
        return final_data
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"defs": [], "synonyms": [], "article": ""}

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
def get_multiple_translations(word, target_lang):
    """Fetches the main translation AND alternative synonyms from Google Translate."""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "fr",
        "tl": target_lang,
        "dt": ["t", "bd"], # 't' gets the main translation, 'bd' gets the dictionary alternatives
        "q": word
    }
    try:
        resp = SESSION.get(url, params=params, timeout=5)
        data = resp.json()
        
        translations = []
        # 1. Get the primary translation
        if data[0] and data[0][0] and data[0][0][0]:
            translations.append(data[0][0][0].lower())
            
        # 2. Get the alternative dictionary translations
        if len(data) > 1 and data[1]:
            for pos_block in data[1]:
                # pos_block[1] contains the list of alternative words
                if len(pos_block) > 1 and isinstance(pos_block[1], list):
                    for alt in pos_block[1]:
                        alt_lower = alt.lower()
                        if alt_lower not in translations:
                            translations.append(alt_lower)
                            
        return translations[:6] # Return the top 6 options
    except Exception as e:
        print(f"Translation error ({target_lang}): {e}")
        return []

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
    words_to_process = [w for w in req.words if w.lower() not in known_words]
    master_results = {}
    
    batch_raw = fetch_batch_wikitext(words_to_process)
    
    for word in words_to_process:
        raw = batch_raw.get(word)
        wik_defs = parse_dictionary(process_wiktionary_templates(extract_french_section(raw))) if raw else []
        images = get_wikimedia_images(word, limit=15)
        rob_data = get_robert_data(word)
        
        master_results[word] = {
            "occurrences": WORD_FREQUENCIES.get(word.lower(), 0),
            "wik_definitions": wik_defs,
            # THE FIX: Ensure this is ONLY the array of definitions, not the whole dictionary!
            "rob_definitions": rob_data.get("defs", []), 
            "synonyms": rob_data.get("synonyms", []),
            "article": rob_data.get("article", ""),
            "translations": {
                "en": get_multiple_translations(word, "en"),
                "sv": get_multiple_translations(word, "sv")
            },
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
def export_to_anki(req: ExportRequest): # <-- Removed deck_name from here
    """Generates the Green HTML cards and sends them directly to AnkiConnect."""
    words_added = set()
    added_count = 0
    
    # Grab the deck name sent from Vue
    target_deck = req.deck_name 
    
    for card in req.cards:
        # Combine article and word (e.g., "un bateau" or "ôter")
        word_display = f"{card.article} {card.word}".strip() if card.article else card.word
        
        # --- HTML STYLING ---
        green_style = 'color: #2ecc71; font-weight: bold;'
        
        # 1. FRONT HTML (Updated for Smart Conjugation Highlighting)
        front_html = ""
        if card.examples:
            # Match the first 5 characters (or whole word if shorter) to catch conjugations
            stem_len = min(len(card.word), 5)
            stem = card.word[:stem_len]
            # Regex: \b matches word boundary, [a-zà-ÿ]* matches the rest of the conjugated word
            pattern = re.compile(rf'\b({re.escape(stem)}[a-zàâçéèêëîïôûùüÿñæœ]*)\b', re.IGNORECASE)
            
            highlighted_ex = pattern.sub(rf'<span style="{green_style}">\1</span>', card.examples[0])
            front_html = f"{highlighted_ex}"
        else:
            front_html = f'<span style="{green_style}">{word_display}</span>'
            
        # Add Google TTS Audio tag (AnkiConnect will download this automatically)
        front_html += f"<br><br>[sound:_google_tts_fr_{card.word}.mp3]"
        
        # 2. BACK HTML
        back_html = f'<span style="{green_style}">{word_display} =</span> {card.definition}'
        
        if card.transEn or card.transSv:
            back_html += "<br><br>"
            if card.transEn: back_html += f"🇬🇧 {', '.join(card.transEn)}<br>"
            if card.transSv: back_html += f"🇸🇪 {', '.join(card.transSv)}"
            
        if card.synonyms:
            back_html += f"<br><br><i>Syn: {', '.join(card.synonyms)}</i>"
            
        if card.imageUrl:
            back_html += f'<br><br><img src="{card.imageUrl}">'

        # --- ANKICONNECT PAYLOAD ---
        note = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": {
                    "deckName": target_deck, # <-- USE IT HERE
                    "modelName": "Basic", 
                    "fields": {
                        "Front": front_html,
                        "Back": back_html
                    },
                    "options": {"allowDuplicate": True},
                    "tags": ["book_vocab"],
                    "audio": [{
                        "url": f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=fr&q={card.word}",
                        "filename": f"_google_tts_fr_{card.word}.mp3",
                        "fields": ["Front"]
                    }]
                }
            }
        }
        
        try:
            # Send to AnkiConnect
            resp = requests.post("http://127.0.0.1:8765", json=note).json()
            if resp.get("error") is None:
                words_added.add(card.word.lower())
                added_count += 1
            else:
                print(f"Anki Error for '{card.word}': {resp.get('error')}")
        except Exception as e:
            print(f"Failed to reach AnkiConnect: {e}")
            return {"status": "error", "message": "Could not connect to Anki. Make sure Anki is open and AnkiConnect is installed!"}

    # Save to your text file to track progress
    with open(KNOWN_WORDS_FILE, "a", encoding="utf-8") as f:
        for word in words_added:
            f.write(word + "\n")
            
    return {"status": "success", "added_words": list(words_added)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)