"""
INCIDB Extraction Pipeline Skeleton
Demonstrates how to parse messy raw ingredient text into standardized INCI records
and export structured data to SQLite/Parquet.
"""

import json
import sqlite3
from typing import List, Dict

# Example raw scraped product record
RAW_SCRAPED_PRODUCT = {
    "brand": "CeraVe",
    "name": "Daily Moisturizing Lotion",
    "barcode": "3606000537422",
    "price": 14.99,
    "raw_ingredients": "Purified Water, Glycerin, Caprylic/Capric Triglyceride, Niacinamide, Cetearyl Alcohol, Ceramide NP"
}

def normalize_ingredients_with_llm(raw_text: str) -> List[Dict[str, str]]:
    """
    Simulates calling an LLM (e.g., Gemini Flash or OpenAI) to parse raw ingredient text
    into normalized INCI names and positions.
    """
    # In a production pipeline, this sends a prompt to Gemini/OpenAI API:
    # prompt = f"Extract canonical INCI ingredient names from: {raw_text}. Return JSON array."
    
    # Mock structured output
    return [
        {"position": 1, "inci_name": "AQUA", "common_name": "Water"},
        {"position": 2, "inci_name": "GLYCERIN", "common_name": "Glycerin"},
        {"position": 3, "inci_name": "CAPRYLIC/CAPRIC TRIGLYCERIDE", "common_name": "Caprylic/Capric Triglyceride"},
        {"position": 4, "inci_name": "NIACINAMIDE", "common_name": "Vitamin B3"},
        {"position": 5, "inci_name": "CETEARYL ALCOHOL", "common_name": "Cetearyl Alcohol"},
        {"position": 6, "inci_name": "CERAMIDE NP", "common_name": "Ceramide 3"}
    ]

def save_to_sqlite(db_path: str, product: dict, normalized_ingredients: List[dict]):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    # Insert Brand
    cur.execute("INSERT OR IGNORE INTO brands (name) VALUES (?);", (product["brand"],))
    cur.execute("SELECT brand_id FROM brands WHERE name = ?;", (product["brand"],))
    brand_id = cur.fetchone()[0]
    
    # Insert Product
    cur.execute("""
        INSERT OR REPLACE INTO products (brand_id, barcode_ean, name, retail_price_usd, raw_ingredient_text)
        VALUES (?, ?, ?, ?, ?);
    """, (brand_id, product["barcode"], product["name"], product["price"], product["raw_ingredients"]))
    product_id = cur.lastrowid
    
    # Insert Ingredients & Junction
    for ing in normalized_ingredients:
        cur.execute("""
            INSERT OR IGNORE INTO ingredients (inci_name, common_name) VALUES (?, ?);
        """, (ing["inci_name"], ing["common_name"]))
        
        cur.execute("SELECT ingredient_id FROM ingredients WHERE inci_name = ?;", (ing["inci_name"],))
        ing_id = cur.fetchone()[0]
        
        cur.execute("""
            INSERT OR REPLACE INTO product_ingredients (product_id, ingredient_id, position_index)
            VALUES (?, ?, ?);
        """, (product_id, ing_id, ing["position"]))
        
    conn.commit()
    conn.close()
    print(f"[Success] Processed {product['brand']} - {product['name']} into {db_path}")

if __name__ == "__main__":
    normalized = normalize_ingredients_with_llm(RAW_SCRAPED_PRODUCT["raw_ingredients"])
    save_to_sqlite("incidb_sample.sqlite", RAW_SCRAPED_PRODUCT, normalized)
