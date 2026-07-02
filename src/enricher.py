import json
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Dict, Any

# Dictionary for common rule-based INCI mapping fallback when no API key is set
FALLBACK_INCI_MAP = {
    "PURIFIED WATER": "AQUA",
    "WATER": "AQUA",
    "WATER (AQUA)": "AQUA",
    "AQUA (WATER)": "AQUA",
    "AQUA/WATER/EAU": "AQUA",
    "VITAMIN B3": "NIACINAMIDE",
    "NICOTINAMIDE": "NIACINAMIDE",
    "NIACINAMIDE (VITAMIN B3)": "NIACINAMIDE",
    "VITAMIN C": "ASCORBIC ACID",
    "HYALURONIC ACID": "HYALURONIC ACID",
    "GLYCERIN": "GLYCERIN",
    "SALICYLIC ACID": "SALICYLIC ACID",
    "CERAMIDE NP": "CERAMIDE NP",
    "CETEARYL ALCOHOL": "CETEARYL ALCOHOL"
}

def rule_based_normalize(raw_text: str) -> List[Dict[str, Any]]:
    """Tokenizes raw ingredient text and maps to standard INCI names using heuristics."""
    if not raw_text or not raw_text.strip():
        return []
    
    tokens = [t.strip() for t in raw_text.split(",") if t.strip()]
    results = []
    for idx, token in enumerate(tokens, 1):
        clean_token = re.sub(r"\s+", " ", token).strip()
        upper_token = clean_token.upper()
        
        # Strip trailing parenthetical details if not mapped directly
        inci_name = FALLBACK_INCI_MAP.get(upper_token)
        if not inci_name:
            no_parens = re.sub(r"\(.*?\)", "", upper_token).strip()
            inci_name = FALLBACK_INCI_MAP.get(no_parens, no_parens)
            
        common_name = clean_token.title() if inci_name != clean_token.upper() else ""
        results.append({
            "position": idx,
            "raw_name": clean_token,
            "inci_name": inci_name,
            "common_name": common_name
        })
    return results

def normalize_ingredients(raw_text: str, use_mock_if_no_key: bool = True) -> List[Dict[str, Any]]:
    """Normalizes raw ingredient strings into structured INCI records using Gemini API or rule-based fallback."""
    api_key = os.environ.get("GEMINI_API_KEY")
    
    if api_key:
        try:
            from google import genai
            from google.genai import types
            from pydantic import BaseModel
            
            class IngredientRecord(BaseModel):
                position: int
                raw_name: str
                inci_name: str
                common_name: str
                
            client = genai.Client(api_key=api_key)
            prompt = (
                f"Extract and normalize cosmetic ingredients from this raw listing: '{raw_text}'. "
                "Map each string to its standard INCI name in uppercase. "
                "Preserve position order starting from 1."
            )
            
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=list[IngredientRecord],
                    temperature=0.1
                )
            )
            parsed = json.loads(response.text)
            return parsed
        except Exception as e:
            print(f"[Enricher Note] Gemini API call failed or unavailable ({e}). Using rule-based fallback.")
            
    if use_mock_if_no_key:
        return rule_based_normalize(raw_text)
    return []

def ingest_product_record(db_path: Path, product_data: Dict[str, Any], normalized_ingredients: List[Dict[str, Any]]):
    """Inserts brand, product, ingredients, and junction records into SQLite."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    conn.execute("PRAGMA foreign_keys = ON;")
    
    # Insert or get Brand
    brand_name = product_data.get("brand", "Unknown Brand")
    cur.execute("INSERT OR IGNORE INTO brands (name) VALUES (?);", (brand_name,))
    cur.execute("SELECT brand_id FROM brands WHERE name = ?;", (brand_name,))
    brand_row = cur.fetchone()
    if not brand_row:
        conn.close()
        return
    brand_id = brand_row[0]
    
    # Insert or update Product
    barcode = product_data.get("barcode") or f"SKU_{abs(hash(product_data.get('name', '')))}"
    cur.execute("""
        INSERT OR REPLACE INTO products (brand_id, barcode_ean, name, category, retail_price_usd, raw_ingredient_text)
        VALUES (?, ?, ?, ?, ?, ?);
    """, (
        brand_id,
        barcode,
        product_data.get("name", "Unknown Product"),
        product_data.get("category", "Skincare"),
        product_data.get("price", 0.0),
        product_data.get("raw_ingredients", "")
    ))
    
    cur.execute("SELECT product_id FROM products WHERE barcode_ean = ?;", (barcode,))
    product_id = cur.fetchone()[0]
    
    # Insert ingredients and junction table records
    for ing in normalized_ingredients:
        inci_name = (ing.get("inci_name") or ing.get("raw_name") or "UNKNOWN").strip().upper()
        common_name = ing.get("common_name", "")
        
        cur.execute("""
            INSERT OR IGNORE INTO ingredients (inci_name, common_name) VALUES (?, ?);
        """, (inci_name, common_name))
        
        cur.execute("SELECT ingredient_id FROM ingredients WHERE inci_name = ?;", (inci_name,))
        ing_row = cur.fetchone()
        if not ing_row:
            continue
        ing_id = ing_row[0]
        
        position = ing.get("position", 1)
        cur.execute("""
            INSERT OR REPLACE INTO product_ingredients (product_id, ingredient_id, position_index)
            VALUES (?, ?, ?);
        """, (product_id, ing_id, position))
        
    conn.commit()
    conn.close()

def process_sephora_cache(raw_dir: Path, db_path: Path) -> int:
    """Reads all JSON files in raw_dir, normalizes ingredients, and stores them in SQLite DB."""
    if not raw_dir.exists():
        return 0
        
    count = 0
    for json_file in raw_dir.glob("product_*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            product_data = json.load(f)
            
        raw_text = product_data.get("raw_ingredients", "")
        normalized = normalize_ingredients(raw_text, use_mock_if_no_key=True)
        ingest_product_record(db_path, product_data, normalized)
        count += 1
        
    return count

if __name__ == "__main__":
    db = Path("data/incidb.sqlite")
    raw = Path("data/raw/sephora")
    processed = process_sephora_cache(raw, db)
    print(f"[Success] Processed and ingested {processed} Sephora products into {db}.")
