from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from deep_translator import GoogleTranslator
import requests
import mwparserfromhell
import re
import time

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