# ---> TARGETED FIX: LE ROBERT FUNCTION <---
def get_robert_data(word):
    url = f"https://dictionnaire.lerobert.com/definition/{word.lower()}"
    print(f"\n{'='*50}")
    print(f"--- [LE ROBERT SCRAPER START: {word.upper()}] ---")
    
    try:
        resp = SESSION.get(url, timeout=10)
        
        # 1. WRITE THE FULL RAW HTML TO A FILE
        raw_filename = f"lerobert_{word.lower()}_raw.html"
        with open(raw_filename, "w", encoding="utf-8") as f:
            f.write(resp.text)
        print(f"-> SAVED: Full raw HTML written to '{raw_filename}'")
        
        if resp.status_code != 200:
            print(f"HTTP Error: {resp.status_code}")
            return {"defs": [], "synonyms": [], "article": ""}
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # EXTRACT ARTICLE / GENDER
        article = ""
        pos_tag = soup.select_one('.d_cat')
        if pos_tag:
            pos_text = pos_tag.get_text(strip=True).lower()
            if "masculin" in pos_text and "nom" in pos_text:
                article = "le / un"
            elif "féminin" in pos_text and "nom" in pos_text:
                article = "la / une"
        
        # EXTRACT DEFINITIONS & INLINE EXAMPLES
        def_blocks = soup.select('.d_dfn')
        results = []
        for i, block in enumerate(def_blocks):
            marq = block.select_one('.d_marq')
            tag = marq.get_text(strip=True) if marq else ""
            
            inline_examples = [ex.get_text(strip=True) for ex in block.select('.d_ex')]
            
            def_node = block.select_one('.d_def')
            if def_node:
                def_str = def_node.get_text(strip=True)
            else:
                raw_text = block.get_text(" ", strip=True).replace(tag, "")
                for ex in inline_examples:
                    raw_text = raw_text.replace(ex, "")
                def_str = raw_text.strip(": ").strip()
                
            if def_str:
                results.append({
                    "definition": def_str,
                    "examples": inline_examples,
                    "tags": [tag] if tag else []
                })

        # EXTRACT EXTERNAL / LITERARY EXAMPLES
        # Targeting the exact class from your paste: .ex_example
        corpus_elements = soup.select('.ex_example')
        literary_examples = []
        for c in corpus_elements:
            author_tag = c.select_one('.ex_author')
            if author_tag:
                author_tag.extract()
            text = c.get_text(" ", strip=True)
            if len(text) > 15:
                literary_examples.append(text)
                
        # Attach literary examples to the first definition
        if literary_examples and results:
            results[0]["examples"].extend(literary_examples[:10])
        elif literary_examples and not results:
            results.append({"definition": "Exemples divers:", "examples": literary_examples[:10], "tags": []})
            
        # EXTRACT SYNONYMS (.s_syn based on your paste)
        syn_elements = soup.select('.s_syn')
        synonyms = list(dict.fromkeys([s.get_text(strip=True) for s in syn_elements]))

        # ASSEMBLE FINAL DATA
        final_data = {
            "defs": results,
            "synonyms": synonyms[:10],
            "article": article
        }
        
        # 2. WRITE THE RETURNED JSON TO A FILE
        json_filename = f"lerobert_{word.lower()}_parsed.json"
        with open(json_filename, "w", encoding="utf-8") as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False)
        print(f"-> SAVED: Parsed JSON written to '{json_filename}'")
        print(f"{'='*50}\n")
        
        return final_data
        
    except Exception as e:
        print(f"CRITICAL ERROR: {str(e)}")
        traceback.print_exc()
        return {"defs": [], "synonyms": [], "article": ""}