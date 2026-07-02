import json
import sqlite3
from pathlib import Path
import pytest
from src.db import init_database, get_connection
from src.enricher import normalize_ingredients, ingest_product_record, process_sephora_cache

def test_normalize_ingredients():
    raw_text = "Purified Water, Glycerin, Niacinamide (Vitamin B3)"
    normalized = normalize_ingredients(raw_text, use_mock_if_no_key=True)
    
    assert len(normalized) == 3
    assert normalized[0]["inci_name"] in ["AQUA", "WATER"]
    assert normalized[0]["position"] == 1
    assert normalized[2]["inci_name"] == "NIACINAMIDE"

def test_ingest_product_record(tmp_path):
    db_file = tmp_path / "test_ingest.sqlite"
    init_database(db_file, Path("docs/schema.sql"))
    
    product_data = {
        "brand": "CeraVe",
        "name": "Daily Moisturizing Lotion",
        "barcode": "P123456",
        "price": 14.99,
        "raw_ingredients": "Purified Water, Glycerin"
    }
    
    normalized = [
        {"position": 1, "raw_name": "Purified Water", "inci_name": "AQUA", "common_name": "Water"},
        {"position": 2, "raw_name": "Glycerin", "inci_name": "GLYCERIN", "common_name": "Glycerin"}
    ]
    
    ingest_product_record(db_file, product_data, normalized)
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    
    cur.execute("SELECT name FROM brands WHERE name = 'CeraVe';")
    assert cur.fetchone()[0] == "CeraVe"
    
    cur.execute("SELECT name, retail_price_usd FROM products WHERE barcode_ean = 'P123456';")
    prod_row = cur.fetchone()
    assert prod_row[0] == "Daily Moisturizing Lotion"
    assert prod_row[1] == 14.99
    
    cur.execute("SELECT count(*) FROM product_ingredients;")
    assert cur.fetchone()[0] == 2
    
    conn.close()

def test_process_sephora_cache(tmp_path):
    raw_dir = tmp_path / "raw_sephora"
    raw_dir.mkdir(parents=True)
    
    mock_prod = {
        "brand": "Glow Recipe",
        "name": "Dew Drops",
        "barcode": "P9999",
        "price": 35.0,
        "raw_ingredients": "Water, Niacinamide, Glycerin"
    }
    
    with open(raw_dir / "product_P9999.json", "w", encoding="utf-8") as f:
        json.dump(mock_prod, f)
        
    db_file = tmp_path / "cache_test.sqlite"
    init_database(db_file, Path("docs/schema.sql"))
    
    count = process_sephora_cache(raw_dir, db_file)
    assert count == 1
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM ingredients;")
    assert cur.fetchone()[0] == 3
    conn.close()
