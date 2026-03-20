from fastapi import FastAPI, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import selector_logic
import fetcher_logic
from datetime import datetime
import os
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Database on boot
selector_logic.init_db()

# --- PYDANTIC MODELS (From word_fetcher.py) ---
class WordRequest(BaseModel):
    words: list[str]

class CardExportData(BaseModel):
    word: str
    article: str
    definition: str
    example: str
    imageUrl: str
    transEn: str
    transSv: str
    synonyms: str

class ExportRequest(BaseModel):
    cards: list[CardExportData]
    deck_name: str = "French words"

class DecisionRequest(BaseModel):
    book_name: str
    word: str
    decision: str

class UndoRequest(BaseModel):
    book_name: str

class ManualAddRequest(BaseModel):
    book_name: str
    word: str

# ==========================================
# THE WORD SELECTOR API (NEW)
# ==========================================
@app.get("/api/selector/books")
def api_get_books():
    return selector_logic.get_available_books()

@app.get("/api/selector/next")
def api_get_next_word(book_name: str = Query(...)):
    return selector_logic.get_next_selector_word(book_name)

@app.post("/api/selector/decide")
def api_save_decision(req: DecisionRequest):
    return selector_logic.save_selector_decision(req.book_name, req.word, req.decision)

@app.get("/api/selector/stats")
def api_get_stats():
    return selector_logic.get_all_stats()

@app.post("/api/selector/undo")
def api_undo_decision(req: UndoRequest):
    return selector_logic.undo_selector_decision(req.book_name)

@app.post("/api/selector/add-manual")
def api_add_manual(req: ManualAddRequest):
    return selector_logic.add_manual_word(req.book_name, req.word)
# ==========================================
# DICTIONARY & ANKI API (EXISTING)
# ==========================================
@app.post("/api/upload-books")
async def upload_books(files: list[UploadFile] = File(...)):
    contents = [await file.read().decode("utf-8", errors="ignore") for file in files]
    return fetcher_logic.process_uploaded_books(contents)

@app.post("/api/fetch-words")
def fetch_words_endpoint(req: WordRequest):
    return fetcher_logic.fetch_words_data(req.words)

@app.post("/api/book-examples")
def fetch_book_examples(word: str = Form(...), offset: int = Form(0)):
    return fetcher_logic.fetch_book_examples_logic(word, offset)

@app.post("/api/export-anki")
def export_to_anki(req: ExportRequest):
    return fetcher_logic.export_to_anki_logic(req.cards, req.deck_name)

@app.post("/api/aggregate-lists")
async def aggregate_lists(files: list[UploadFile] = File(...)):
    unique_words = set()
    
    # 1. Read all files and extract words
    for file in files:
        content = (await file.read()).decode("utf-8", errors="ignore")
        lines = content.split('\n')
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
            # Extract just the word in case the list has commas (e.g., word,frequency)
            word = line.split(',')[0].strip().lower()
            if word:
                unique_words.add(word)
    
    # 2. Setup the directory path to wordextractions/aggregations
    # Assuming main.py is in backend/src
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    agg_dir = os.path.join(root_dir, "wordextractions", "aggregations")
    os.makedirs(agg_dir, exist_ok=True)
    
    # 3. Format the filename with today's date
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"big_list_For_cards_{date_str}.txt"
    filepath = os.path.join(agg_dir, filename)
    
    # 4. Save the alphabetically sorted list
    with open(filepath, "w", encoding="utf-8") as f:
        for word in sorted(unique_words):
            f.write(f"{word}\n")
            
    return {
        "status": "success", 
        "filename": filename, 
        "unique_count": len(unique_words)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)