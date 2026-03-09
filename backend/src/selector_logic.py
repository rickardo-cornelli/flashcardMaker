import os
import sqlite3

# --- PATH SETUP ---
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.abspath(os.path.join(CURRENT_DIR, "..", ".."))
OUTPUT_DIR = os.path.join(ROOT_DIR, "wordextractions")
DB_PATH = os.path.join(OUTPUT_DIR, "flashcard_progress.db")

def init_db():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS book_progress (
            book_name TEXT PRIMARY KEY,
            selector_index INTEGER DEFAULT 0,
            anki_index INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

def get_progress(book_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT selector_index, anki_index FROM book_progress WHERE book_name = ?', (book_name,))
    row = cursor.fetchone()
    
    if row is None:
        cursor.execute('INSERT INTO book_progress (book_name, selector_index, anki_index) VALUES (?, 0, 0)', (book_name,))
        conn.commit()
        row = (0, 0)
    conn.close()
    return {"selector_index": row[0], "anki_index": row[1]}

def get_available_books():
    if not os.path.exists(OUTPUT_DIR): return []
    return [f.replace("_frequent.txt", "") for f in os.listdir(OUTPUT_DIR) if f.endswith("_frequent.txt")]

def get_next_selector_word(book_name):
    progress = get_progress(book_name)
    current_index = progress["selector_index"]
    filepath = os.path.join(OUTPUT_DIR, f"{book_name}_frequent.txt")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        if current_index >= len(lines):
            return {"word": None, "message": "Finished"}
            
        raw_line = lines[current_index].strip()
        line_data = raw_line.split(',')
        
        word = line_data[0]
        frequency = line_data[1] if len(line_data) > 1 else "Unknown"
        
        return {
            "word": word, 
            "frequency": frequency, 
            "index": current_index, 
            "total": len(lines)
        }
    except FileNotFoundError:
        return {"error": "File not found"}

def save_selector_decision(book_name, word, decision):
    if decision.lower() == 'y':
        learn_filepath = os.path.join(OUTPUT_DIR, f"words_from_{book_name}_to_learn.txt")
        with open(learn_filepath, 'a', encoding='utf-8') as f:
            f.write(f"{word}\n")
            
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE book_progress SET selector_index = selector_index + 1 WHERE book_name = ?', (book_name,))
    conn.commit()
    conn.close()
    
    return {"success": True}

def get_all_stats():
    """Calculates sorting and flashcard progress for all tracked books."""
    if not os.path.exists(DB_PATH):
        return []
        
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT book_name, selector_index, anki_index FROM book_progress')
    rows = cursor.fetchall()
    conn.close()

    stats = []
    for row in rows:
        book_name, sel_idx, anki_idx = row
        
        # 1. Get Selector Progress (Y/N sorting)
        freq_path = os.path.join(OUTPUT_DIR, f"{book_name}_frequent.txt")
        total_freq = 0
        last_sel_word = "-"
        if os.path.exists(freq_path):
            with open(freq_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_freq = len(lines)
                if sel_idx > 0 and sel_idx <= len(lines):
                    # Split by comma because of our "word,frequency" format
                    last_sel_word = lines[sel_idx - 1].split(',')[0].strip()

        # 2. Get Anki Progress (Flashcards made)
        learn_path = os.path.join(OUTPUT_DIR, f"words_from_{book_name}_to_learn.txt")
        total_learn = 0
        last_anki_word = "-"
        if os.path.exists(learn_path):
            with open(learn_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                total_learn = len(lines)
                if anki_idx > 0 and anki_idx <= len(lines):
                    last_anki_word = lines[anki_idx - 1].strip()

        # Only add to stats if there is actually a frequent words file
        if total_freq > 0:
            stats.append({
                "book_name": book_name,
                "sel_idx": sel_idx,
                "total_freq": total_freq,
                "last_sel_word": last_sel_word,
                "anki_idx": anki_idx,
                "total_learn": total_learn,
                "last_anki_word": last_anki_word
            })
            
    return stats

def undo_selector_decision(book_name):
    """Goes back one word and removes it from the 'to_learn' file if it was added."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('SELECT selector_index FROM book_progress WHERE book_name = ?', (book_name,))
    row = cursor.fetchone()
    
    if not row or row[0] <= 0:
        conn.close()
        return {"success": False, "message": "Already at the beginning"}
        
    new_index = row[0] - 1
    
    # 1. Figure out what the previous word was
    filepath = os.path.join(OUTPUT_DIR, f"{book_name}_frequent.txt")
    target_word = None
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if new_index < len(lines):
                target_word = lines[new_index].split(',')[0].strip()

    # 2. If it was added to the 'learn' list, remove it
    learn_filepath = os.path.join(OUTPUT_DIR, f"words_from_{book_name}_to_learn.txt")
    if target_word and os.path.exists(learn_filepath):
        with open(learn_filepath, 'r', encoding='utf-8') as f:
            learn_lines = f.readlines()
        
        # If the last word saved perfectly matches the one we are undoing, pop it off!
        if learn_lines and learn_lines[-1].strip() == target_word:
            learn_lines.pop()
            with open(learn_filepath, 'w', encoding='utf-8') as f:
                f.writelines(learn_lines)

    # 3. Update the database index
    cursor.execute('UPDATE book_progress SET selector_index = ? WHERE book_name = ?', (new_index, book_name))
    conn.commit()
    conn.close()
    
    return {"success": True}

def add_manual_word(book_name, word):
    """Manually injects a typed word directly into the 'to_learn' file."""
    if not word.strip(): return {"success": False}
    
    learn_filepath = os.path.join(OUTPUT_DIR, f"words_from_{book_name}_to_learn.txt")
    with open(learn_filepath, 'a', encoding='utf-8') as f:
        f.write(f"{word.strip().lower()}\n")
        
    return {"success": True}