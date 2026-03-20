from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import requests
import mwparserfromhell
import re
import json
import os
from collections import Counter
from datetime import datetime
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "anki-french-dict/2.0 (your_email@example.com)"})

LIBRARY_TEXT = ""
WORD_FREQUENCIES = Counter()
KNOWN_WORDS_FILE = "known_words.txt"
NAMES_TO_HIDE = [
    "D'Artagnan", "Athos", "Porthos", "Aramis", "Milady", "Richelieu", 
    "Bonacieux", "Buckingham", "Anne d'Autriche", "Louis XIII", "Felton", 
    "de Winter", "Rochefort", "Tréville"
]

API_RESULTS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apiresults"))
os.makedirs(API_RESULTS_DIR, exist_ok=True)

def process_uploaded_books(file_contents: list[str]):
    global LIBRARY_TEXT, WORD_FREQUENCIES
    combined_text = ""
    for content in file_contents:
        combined_text += content + "\n"
    
    LIBRARY_TEXT = combined_text
    words = re.findall(r'\b[a-zàâçéèêëîïôûùüÿñæœ]+\b', LIBRARY_TEXT.lower())
    WORD_FREQUENCIES = Counter(words)
    return {"status": "success", "length": len(LIBRARY_TEXT), "unique_words": len(WORD_FREQUENCIES)}

def get_known_words():
    if not os.path.exists(KNOWN_WORDS_FILE):
        return set()
    with open(KNOWN_WORDS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())
    
def get_pipeline_words():
    # 1. Locate the cleaning directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    pipeline_file = os.path.join(root_dir, "wordextractions", "cleaning", "words_in_flashcard_pipeline.txt")
    
    # 2. Return an empty set if the file doesn't exist yet
    if not os.path.exists(pipeline_file):
        return set()
        
    # 3. Read the words into a highly-efficient Python set
    with open(pipeline_file, "r", encoding="utf-8") as f:
        return set(line.strip().lower() for line in f if line.strip())
    
def anonymize_sentence(text):
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
        resp = SESSION.get(url, timeout=10)
        raw_filename = os.path.join(API_RESULTS_DIR, f"lerobert_{word.lower()}_raw.html")
        with open(raw_filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
            
        if resp.status_code != 200: return {"defs": [], "synonyms": [], "article": ""}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        article = ""
        pos_tag = soup.select_one('.d_cat')
        if pos_tag:
            pos_text = pos_tag.get_text(strip=True).lower()
            if "masculin" in pos_text and "nom" in pos_text: article = "un"
            elif "féminin" in pos_text and "nom" in pos_text: article = "une"
        
        results = []
        def_blocks = soup.select('.d_dvn, .d_dvl')
        for block in def_blocks:
            context_tags = [t.get_text(strip=True) for t in block.select('.d_mta, .d_marq') if t.get_text(strip=True)]
            def_node = block.select_one('.d_dfn')
            inline_examples = [ex.get_text(strip=True) for ex in block.select('.d_xpl')]
            if def_node:
                results.append({"definition": def_node.get_text(strip=True), "examples": inline_examples, "tags": context_tags})
            elif inline_examples and results:
                prefix = f"[{', '.join(context_tags)}] " if context_tags else ""
                results[-1]["examples"].extend([f"{prefix}{ex}" for ex in inline_examples])

        if not results:
            for block in soup.select('#formes .infl_links .b'):
                h3 = block.select_one('h3')
                if h3:
                    link = block.select_one('.def-link a')
                    def_str = h3.get_text(" ", strip=True) + (f" (Voir: {link.get_text(strip=True)})" if link else "")
                    results.append({"definition": def_str, "examples": [], "tags": ["Forme fléchie"]})

        literary_examples = []
        for c in soup.select('.ex_example, .infl_example'):
            if author_tag := c.select_one('.ex_author'): author_tag.extract()
            text = c.get_text(" ", strip=True)
            if len(text) > 15: literary_examples.append(text)
                
        if literary_examples:
            results.append({"definition": "Exemples Littéraires / Presse :", "examples": literary_examples[:10], "tags": ["Corpus"]})
            
        synonyms = list(dict.fromkeys([s.get_text(strip=True) for s in soup.select('.s_syn')]))
        final_data = {"defs": results, "synonyms": synonyms[:10], "article": article}
        
        json_filename = os.path.join(API_RESULTS_DIR, f"lerobert_{word.lower()}_parsed.json")
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        return final_data
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        return {"defs": [], "synonyms": [], "article": ""}

def fetch_batch_wikitext(word_list):
    url = "https://fr.wiktionary.org/w/api.php"
    params = {"action": "query", "prop": "revisions", "rvprop": "content", "format": "json", "titles": "|".join(word_list), "redirects": 1}
    try:
        resp = SESSION.get(url, params=params, timeout=15)
        data = resp.json()
        results_map = {}
        if "query" in data and "pages" in data["query"]:
            for page_data in data["query"]["pages"].values():
                results_map[page_data["title"]] = page_data["revisions"][0]["*"] if "revisions" in page_data else None
        return results_map
    except: return {}

def extract_french_section(raw_text):
    if not raw_text: return ""
    sections = re.split(r'==\s*\{\{langue\|fr\}\}\s*==', raw_text, flags=re.IGNORECASE)
    return re.split(r'==\s*\{\{langue\|', sections[1], flags=re.IGNORECASE)[0] if len(sections) >= 2 else ""

def process_wiktionary_templates(fr_section):
    parsed = mwparserfromhell.parse(fr_section)
    for template in parsed.filter_templates():
        t_name = str(template.name).lower().strip()
        if t_name in ['exemple', 'ex', 'ux']:
            text_val = next((str(p.value).strip() for p in template.params if str(p.name).strip() not in ['lang','source','auteur'] and str(p.value).strip() != "fr"), "")
            try: parsed.replace(template, text_val.replace('\n', ' '))
            except ValueError: pass
        elif t_name not in ['lien', 'l', 'm', 'f', 'p', 's', 'w', 'langue'] and t_name not in ['source', 'sans source', 'citation', 'ouvrage', 'réf', 'lien web', 'pron']:
            labels = [str(p.value).strip() for p in template.params if not str(p.name).isdigit() and str(p.value).strip() not in ['fr', '']]
            try: parsed.replace(template, f"[{', '.join([t_name.capitalize()] + labels)}]")
            except ValueError: pass
        elif t_name in ['source', 'sans source', 'citation', 'ouvrage', 'réf', 'lien web', 'pron']:
            try: parsed.remove(template)
            except ValueError: pass
    return str(parsed)

def clean_sentence(text):
    clean = mwparserfromhell.parse(text).strip_code()
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', clean).replace("'''", "").replace("''", "")).strip()

def parse_dictionary(wikitext_processed):
    entries = []
    current_entry = None
    for line in wikitext_processed.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith('#') and not (line.startswith('#*') or line.startswith('##')):
            clean_def = clean_sentence(line.lstrip('# '))
            if clean_def:
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
            if clean_ex and clean_ex != current_entry['definition']: current_entry['examples'].append(clean_ex)
    return entries

def get_multiple_translations(word, target_lang):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "fr", "tl": target_lang, "dt": ["t", "bd"], "q": word}
    try:
        data = SESSION.get(url, params=params, timeout=5).json()
        translations = []
        if data[0] and data[0][0] and data[0][0][0]: translations.append(data[0][0][0].lower())
        if len(data) > 1 and data[1]:
            for pos_block in data[1]:
                if len(pos_block) > 1 and isinstance(pos_block[1], list):
                    for alt in pos_block[1]:
                        if alt.lower() not in translations: translations.append(alt.lower())
        return translations[:6]
    except: return []

def fetch_words_data(words):
    known_words = get_known_words()
    pipeline_words = get_pipeline_words()
    
    # Combine both lists so we ignore everything you've already processed
    words_to_ignore = known_words.union(pipeline_words)
    
    words_to_process = []
    excluded_words = []
    
    # 1. Sort the incoming words into the Process or Exclude piles
    for w in words:
        clean_w = w.lower().strip()
        if not clean_w: 
            continue
            
        if clean_w in words_to_ignore:
            if clean_w not in excluded_words:
                excluded_words.append(clean_w)
        else:
            if clean_w not in words_to_process:
                words_to_process.append(clean_w)

    # 2. NEW: Log the excluded words to a file so you can see what was filtered
    if excluded_words:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
        cleaning_dir = os.path.join(root_dir, "wordextractions", "cleaning")
        os.makedirs(cleaning_dir, exist_ok=True)
        
        excluded_file = os.path.join(cleaning_dir, "words_excluded_from_pipeline.txt")
        
        # Append to the file with a clear timestamp header
        with open(excluded_file, "a", encoding="utf-8") as f:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"\n--- Excluded during fetch on {timestamp} ---\n")
            for ew in excluded_words:
                f.write(f"{ew}\n")
                
        print(f"Skipped {len(excluded_words)} duplicate words. Logged to words_excluded_from_pipeline.txt")

    master_results = {}
    
    # If all words were duplicates, return empty immediately
    if not words_to_process:
        return master_results
    batch_raw = fetch_batch_wikitext(words_to_process)
    
    for word in words_to_process:
        raw = batch_raw.get(word)
        master_results[word] = {
            "occurrences": WORD_FREQUENCIES.get(word.lower(), 0),
            "wik_definitions": parse_dictionary(process_wiktionary_templates(extract_french_section(raw))) if raw else [],
            "rob_definitions": (rob := get_robert_data(word)).get("defs", []), 
            "synonyms": rob.get("synonyms", []),
            "article": rob.get("article", ""),
            "translations": {"en": get_multiple_translations(word, "en"), "sv": get_multiple_translations(word, "sv")},
            "images": get_wikimedia_images(word, limit=15)
        }
    return master_results

def fetch_book_examples_logic(word, offset):
    if not LIBRARY_TEXT: return {"examples": [], "total": 0, "hasMore": False}
    safe_text = LIBRARY_TEXT[:int(len(LIBRARY_TEXT) * 0.3)]
    sentences = re.split(r'(?<=[.!?])\s+', safe_text)
    pattern = re.compile(rf'\b{word}\b', re.IGNORECASE)
    
    matches = []
    for s in sentences:
        clean = " ".join(s.split())
        if pattern.search(clean) and clean not in matches and len(clean) < 300: matches.append(clean)
            
    clean_matches = [anonymize_sentence(m) for m in matches]
    return {"examples": clean_matches[offset : offset + 5], "total": len(matches), "hasMore": len(matches) > (offset + 5)}

def export_to_anki_logic(cards, deck_name):
    words_added = set()
    for card in cards:
        back_html = card.definition
        if card.transEn or card.transSv:
            back_html += "<br><br>"
            if card.transEn: back_html += f"🇬🇧 {card.transEn}<br>"
            if card.transSv: back_html += f"🇸🇪 {card.transSv}"
        if card.synonyms: back_html += f"<br><br><i>Syn: {card.synonyms}</i>"
        if card.imageUrl: back_html += f'<br><br><img src="{card.imageUrl}">'

        note = {
            "action": "addNote", "version": 6,
            "params": {
                "note": {
                    "deckName": deck_name, "modelName": "Basic", 
                    "fields": {"Front": card.example, "Back": back_html},
                    
                    "options": {"allowDuplicate": True}, "tags": ["book_vocab"],
                    "audio": [{"url": f"https://translate.google.com/translate_tts?ie=UTF-8&client=tw-ob&tl=fr&q={card.word}", "filename": f"_google_tts_fr_{card.word}.mp3", "fields": ["Front"]}]
                    
                }
                
            }
        }
        try:
            resp = requests.post("http://127.0.0.1:8765", json=note).json()
            if resp.get("error") is None: words_added.add(card.word.lower())
            else: print(f"Anki Error for '{card.word}': {resp.get('error')}")
        except Exception as e:
            return {"status": "error", "message": "Could not connect to Anki. Make sure Anki is open!"}

    # --- AFTER SUCCESSFUL ANKI EXPORT ---

    # 1. Original behavior (optional, keeps your old known_words.txt updated)
    with open(KNOWN_WORDS_FILE, "a", encoding="utf-8") as f:
        for word in words_added: f.write(word + "\n")
        
    # 2. NEW: Append the successfully exported words to your pipeline file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    cleaning_dir = os.path.join(root_dir, "wordextractions", "cleaning")
    os.makedirs(cleaning_dir, exist_ok=True)
    
    pipeline_file = os.path.join(cleaning_dir, "words_in_flashcard_pipeline.txt")
    with open(pipeline_file, "a", encoding="utf-8") as f:
        for word in words_added: 
            f.write(word + "\n")
            
    return {"status": "success", "added_words": list(words_added)}