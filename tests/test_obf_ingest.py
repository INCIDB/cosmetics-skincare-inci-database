import json
from pathlib import Path
import pytest
from src.obf_ingest import parse_obf_item, save_obf_product, fetch_obf_products

MOCK_OBF_ITEM = {
    "code": "3014230021482",
    "product_name": "Hydrance Optinale Light Hydrating Cream",
    "brands": "Avène, Pierre Fabre",
    "ingredients_text": "AVENE THERMAL SPRING WATER (AVENE AQUA), CAPRYLIC/CAPRIC TRIGLYCERIDE, CARTHAMUS TINCTORIUS (SAFFLOWER) SEED OIL, GLYCERIN",
    "url": "https://world.openbeautyfacts.org/product/3014230021482"
}

def test_parse_obf_item():
    parsed = parse_obf_item(MOCK_OBF_ITEM)
    assert parsed["brand"] == "Avène, Pierre Fabre"
    assert parsed["name"] == "Hydrance Optinale Light Hydrating Cream"
    assert parsed["barcode"] == "3014230021482"
    assert "CAPRYLIC/CAPRIC TRIGLYCERIDE" in parsed["raw_ingredients"]

def test_save_obf_product(tmp_path):
    out_dir = tmp_path / "obf"
    parsed = parse_obf_item(MOCK_OBF_ITEM)
    file_path = save_obf_product(parsed, out_dir)
    
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["barcode"] == "3014230021482"

def test_fetch_obf_products(tmp_path):
    out_dir = tmp_path / "obf_raw"
    files = fetch_obf_products(limit=5, output_dir=out_dir, use_sample_if_offline=True)
    assert len(files) > 0
    assert files[0].exists()
