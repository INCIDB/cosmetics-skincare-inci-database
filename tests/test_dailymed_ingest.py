import json
from pathlib import Path
import pytest
from src.dailymed_ingest import parse_dailymed_item, save_dailymed_product, fetch_dailymed_products

MOCK_DAILYMED_ITEM = {
    "setid": "6d2d3121-724e-4c75-8025-05d6e24578ef",
    "title": "CeraVe Hydrating Mineral Sunscreen Broad Spectrum SPF 30 (Titanium Dioxide and Zinc Oxide Lotion)",
    "labeler": "L'Oreal USA Products Inc",
    "active_ingredients": "TITANIUM DIOXIDE, ZINC OXIDE",
    "inactive_ingredients": "WATER, CETEARYL ALCOHOL, GLYCERIN, NIACINAMIDE, CERAMIDE NP, HYALURONIC ACID"
}

def test_parse_dailymed_item():
    parsed = parse_dailymed_item(MOCK_DAILYMED_ITEM)
    assert parsed["brand"] == "L'Oreal USA Products Inc"
    assert "Sunscreen" in parsed["name"]
    assert parsed["barcode"] == "6d2d3121-724e-4c75-8025-05d6e24578ef"
    assert "TITANIUM DIOXIDE" in parsed["raw_ingredients"]
    assert "NIACINAMIDE" in parsed["raw_ingredients"]

def test_save_dailymed_product(tmp_path):
    out_dir = tmp_path / "dailymed"
    parsed = parse_dailymed_item(MOCK_DAILYMED_ITEM)
    file_path = save_dailymed_product(parsed, out_dir)
    
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["brand"] == "L'Oreal USA Products Inc"

def test_fetch_dailymed_products(tmp_path):
    out_dir = tmp_path / "dailymed_raw"
    files = fetch_dailymed_products(limit=5, output_dir=out_dir, use_sample_if_offline=True)
    assert len(files) > 0
    assert files[0].exists()
