import pytest
import sqlite3
from pathlib import Path
from src.cir_ingest import parse_cir_item, fetch_cir_data, enrich_db_with_cir

def test_parse_cir_item():
    raw = {
        "inci": "RETINOL",
        "verdict": "Safe with qualifications",
        "notes": "Max 0.3% in face leave-on products due to skin irritation threshold."
    }
    parsed = parse_cir_item(raw)
    assert parsed["inci_name"] == "RETINOL"
    assert parsed["verdict"] == "Safe with qualifications"
    assert "0.3%" in parsed["notes"]

def test_fetch_cir_data(tmp_path):
    files = fetch_cir_data(limit=10, output_dir=tmp_path)
    assert len(files) > 0
    assert files[0].exists()

def test_enrich_db_with_cir(tmp_path):
    db_path = tmp_path / "test_cir.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, inci_name TEXT UNIQUE, cir_safety_verdict TEXT, description TEXT);")
    conn.execute("INSERT INTO ingredients (inci_name) VALUES ('RETINOL');")
    conn.commit()
    conn.close()
    
    items = [{
        "inci_name": "RETINOL",
        "verdict": "Safe with qualifications",
        "notes": "Max 0.3% face."
    }]
    updated = enrich_db_with_cir(db_path, items)
    assert updated == 1
    
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT cir_safety_verdict FROM ingredients WHERE inci_name = 'RETINOL';").fetchone()
    conn.close()
    assert row[0] == "Safe with qualifications"
