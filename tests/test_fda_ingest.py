import pytest
import sqlite3
from pathlib import Path
from src.fda_cosmetics_ingest import parse_fda_item, fetch_fda_cosmetics_data, enrich_db_with_fda

def test_parse_fda_item():
    raw = {
        "ingredient": "LINALOOL",
        "allergenFlag": True,
        "warning": "Mandatory MoCRA contact allergen disclosure when >0.001% in leave-on."
    }
    parsed = parse_fda_item(raw)
    assert parsed["inci_name"] == "LINALOOL"
    assert parsed["is_allergen"] is True
    assert "MoCRA" in parsed["fda_warning"]

def test_fetch_fda_cosmetics_data(tmp_path):
    files = fetch_fda_cosmetics_data(limit=10, output_dir=tmp_path)
    assert len(files) > 0
    assert files[0].exists()

def test_enrich_db_with_fda(tmp_path):
    db_path = tmp_path / "test_fda.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, inci_name TEXT UNIQUE, is_common_allergen BOOLEAN DEFAULT 0, fda_warning TEXT);")
    conn.execute("INSERT INTO ingredients (inci_name) VALUES ('LINALOOL');")
    conn.commit()
    conn.close()
    
    items = [{
        "inci_name": "LINALOOL",
        "is_allergen": True,
        "fda_warning": "Mandatory disclosure."
    }]
    updated = enrich_db_with_fda(db_path, items)
    assert updated == 1
    
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT is_common_allergen, fda_warning FROM ingredients WHERE inci_name = 'LINALOOL';").fetchone()
    conn.close()
    assert row[0] == 1
    assert row[1] == "Mandatory disclosure."
