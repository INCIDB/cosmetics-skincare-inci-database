import pytest
from pathlib import Path
import sqlite3
from src.cosing_ingest import parse_cosing_item, fetch_cosing_data, enrich_db_with_cosing

def test_parse_cosing_item():
    raw = {
        "inciName": "SALICYLIC ACID",
        "casNumber": "69-72-7",
        "function": "ANTIDANDRUFF / KERATOLYTIC / PRESERVATIVE / SKIN CONDITIONING",
        "restriction": "Annex V/3. Maximum authorized concentration: 0.5% in body lotions, 2.0% in other products."
    }
    parsed = parse_cosing_item(raw)
    assert parsed["inci_name"] == "SALICYLIC ACID"
    assert parsed["cas_number"] == "69-72-7"
    assert "KERATOLYTIC" in parsed["primary_function"]
    assert "Annex V/3" in parsed["description"]

def test_fetch_cosing_data(tmp_path):
    files = fetch_cosing_data(limit=10, output_dir=tmp_path, use_sample_if_offline=True)
    assert len(files) > 0
    assert files[0].exists()

def test_enrich_db_with_cosing(tmp_path):
    db_path = tmp_path / "test_cosing.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, inci_name TEXT UNIQUE, cas_number TEXT, primary_function TEXT, description TEXT);")
    conn.execute("INSERT INTO ingredients (inci_name) VALUES ('SALICYLIC ACID');")
    conn.commit()
    conn.close()
    
    items = [{
        "inci_name": "SALICYLIC ACID",
        "cas_number": "69-72-7",
        "primary_function": "KERATOLYTIC",
        "description": "Max 2.0% in rinse-off or leave-on."
    }]
    updated = enrich_db_with_cosing(db_path, items)
    assert updated == 1
    
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT cas_number, primary_function FROM ingredients WHERE inci_name = 'SALICYLIC ACID';").fetchone()
    conn.close()
    assert row[0] == "69-72-7"
    assert row[1] == "KERATOLYTIC"
