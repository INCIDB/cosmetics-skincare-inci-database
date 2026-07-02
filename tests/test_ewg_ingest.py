import pytest
import sqlite3
from pathlib import Path
from src.ewg_ingest import parse_ewg_item, fetch_ewg_data, enrich_db_with_ewg

def test_parse_ewg_item():
    raw = {
        "name": "OXYBENZONE",
        "score": 8,
        "cancerConcern": False,
        "endocrineDisruption": True
    }
    parsed = parse_ewg_item(raw)
    assert parsed["inci_name"] == "OXYBENZONE"
    assert parsed["ewg_score"] == 8
    assert parsed["cancer_flag"] is False
    assert parsed["endocrine_flag"] is True

def test_fetch_ewg_data(tmp_path):
    files = fetch_ewg_data(limit=10, output_dir=tmp_path)
    assert len(files) > 0
    assert files[0].exists()

def test_enrich_db_with_ewg(tmp_path):
    db_path = tmp_path / "test_ewg.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE ingredients (ingredient_id INTEGER PRIMARY KEY, inci_name TEXT UNIQUE, ewg_hazard_score INTEGER, cancer_hazard_flag BOOLEAN, endocrine_hazard_flag BOOLEAN);")
    conn.execute("INSERT INTO ingredients (inci_name) VALUES ('OXYBENZONE');")
    conn.commit()
    conn.close()
    
    items = [{
        "inci_name": "OXYBENZONE",
        "ewg_score": 8,
        "cancer_flag": False,
        "endocrine_flag": True
    }]
    updated = enrich_db_with_ewg(db_path, items)
    assert updated == 1
    
    conn = sqlite3.connect(db_path)
    row = conn.execute("SELECT ewg_hazard_score, endocrine_hazard_flag FROM ingredients WHERE inci_name = 'OXYBENZONE';").fetchone()
    conn.close()
    assert row[0] == 8
    assert row[1] == 1
