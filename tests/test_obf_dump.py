import gzip
import json
from pathlib import Path
import sqlite3
import pytest
from src.obf_ingest import ingest_obf_dump
from src.init import main as init_db

def test_ingest_obf_dump(tmp_path):
    # Create test database
    db_path = tmp_path / "test_dump.sqlite"
    
    # Run schema init on db_path
    conn = sqlite3.connect(db_path)
    schema_sql = Path("docs/schema.sql").read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    conn.close()
    
    # Create a dummy jsonl.gz file
    dump_path = tmp_path / "test_dump.jsonl.gz"
    sample_lines = [
        {"code": "9990001", "product_name": "Test Gel 1", "brands": "TestBrand A", "ingredients_text": "AQUA, GLYCERIN, SALICYLIC ACID"},
        {"code": "9990002", "product_name": "Test Cream 2", "brands": "TestBrand B", "ingredients_text": "WATER, CETEARYL ALCOHOL, NIACINAMIDE"},
        {"code": "9990003", "product_name": "Invalid Item No Ingredients", "brands": "TestBrand C"},
    ]
    
    with gzip.open(dump_path, "wt", encoding="utf-8") as f:
        for item in sample_lines:
            f.write(json.dumps(item) + "\n")
            
    ingested_count = ingest_obf_dump(dump_path, db_path, max_records=10, batch_size=2)
    assert ingested_count == 2
    
    conn = sqlite3.connect(db_path)
    products_count = conn.execute("SELECT count(*) FROM products;").fetchone()[0]
    conn.close()
    assert products_count == 2
