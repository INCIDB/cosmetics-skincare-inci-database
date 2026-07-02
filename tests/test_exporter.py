import sqlite3
from pathlib import Path
import pandas as pd
import pytest
from src.db import init_database, get_connection
from src.exporter import export_to_csv, export_to_parquet

@pytest.fixture
def sample_db(tmp_path):
    db_file = tmp_path / "test_export.sqlite"
    init_database(db_file, Path("docs/schema.sql"))
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    cur.execute("INSERT INTO brands (name) VALUES ('CeraVe');")
    cur.execute("INSERT INTO products (brand_id, barcode_ean, name, retail_price_usd) VALUES (1, '123', 'Lotion', 15.0);")
    cur.execute("INSERT INTO ingredients (inci_name, common_name, ewg_hazard_score) VALUES ('AQUA', 'Water', 1);")
    cur.execute("INSERT INTO product_ingredients (product_id, ingredient_id, position_index) VALUES (1, 1, 1);")
    conn.commit()
    conn.close()
    return db_file

def test_export_to_csv(sample_db, tmp_path):
    out_dir = tmp_path / "csv_out"
    files = export_to_csv(sample_db, out_dir)
    
    assert len(files) == 4
    brands_csv = out_dir / "brands.csv"
    assert brands_csv.exists()
    
    df = pd.read_csv(brands_csv, sep="|")
    assert len(df) == 1
    assert df.iloc[0]["name"] == "CeraVe"

def test_export_to_parquet(sample_db, tmp_path):
    out_dir = tmp_path / "parquet_out"
    files = export_to_parquet(sample_db, out_dir)
    
    assert len(files) == 4
    products_parquet = out_dir / "products.parquet"
    assert products_parquet.exists()
    
    df = pd.read_parquet(products_parquet)
    assert len(df) == 1
    assert df.iloc[0]["name"] == "Lotion"
