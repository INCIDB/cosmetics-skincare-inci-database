import sqlite3
from pathlib import Path
import pytest
from src.db import init_database, get_connection
from src.safety_enricher import lookup_ingredient_safety, enrich_database_safety

def test_lookup_ingredient_safety():
    water_safety = lookup_ingredient_safety("AQUA")
    assert water_safety["ewg_hazard_score"] == 1
    assert water_safety["comedogenic_rating"] == 0
    assert not water_safety["is_common_allergen"]
    
    niacinamide_safety = lookup_ingredient_safety("NIACINAMIDE")
    assert niacinamide_safety["ewg_hazard_score"] == 1
    assert "Humectant" in niacinamide_safety["primary_function"] or "Skin-Conditioning" in niacinamide_safety["primary_function"]

def test_enrich_database_safety(tmp_path):
    db_file = tmp_path / "test_safety.sqlite"
    init_database(db_file, Path("docs/schema.sql"))
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    cur.execute("INSERT INTO ingredients (inci_name, common_name) VALUES ('AQUA', 'Water');")
    cur.execute("INSERT INTO ingredients (inci_name, common_name) VALUES ('NIACINAMIDE', 'Vitamin B3');")
    conn.commit()
    conn.close()
    
    updated_count = enrich_database_safety(db_file)
    assert updated_count >= 2
    
    conn = get_connection(db_file)
    cur = conn.cursor()
    cur.execute("SELECT ewg_hazard_score, comedogenic_rating FROM ingredients WHERE inci_name = 'AQUA';")
    row = cur.fetchone()
    assert row[0] == 1
    assert row[1] == 0
    conn.close()
