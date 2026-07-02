import os
import sqlite3
import pytest
from pathlib import Path

# We import modules that we will implement to satisfy TDD
from src.db import init_database, get_connection
from src.utils import ensure_directories

def test_ensure_directories(tmp_path):
    raw_sephora = tmp_path / "data" / "raw" / "sephora"
    raw_ewg = tmp_path / "data" / "raw" / "ewg"
    
    ensure_directories(tmp_path / "data")
    
    assert raw_sephora.exists() and raw_sephora.is_dir()
    assert raw_ewg.exists() and raw_ewg.is_dir()

def test_init_database(tmp_path):
    db_file = tmp_path / "test_incidb.sqlite"
    schema_file = Path("docs/schema.sql")
    
    init_database(db_file, schema_file)
    
    assert db_file.exists()
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    
    # Query sqlite_master to verify tables were created
    cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cur.fetchall()}
    
    expected_tables = {"brands", "products", "ingredients", "product_ingredients"}
    assert expected_tables.issubset(tables)
    
    conn.close()
