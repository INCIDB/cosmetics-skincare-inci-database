import pytest
import json
from pathlib import Path
from src.kbeauty_ingest import parse_kbeauty_product, fetch_kbeauty_products

def test_parse_kbeauty_product():
    raw = {
        "brand": "COSRX",
        "title": "Advanced Snail 96 Mucin Power Essence",
        "price_usd": 25.00,
        "sku": "KB1001",
        "ingredients_text": "Snail Secretion Filtrate, Betaine, Butylene Glycol, 1,2-Hexanediol, Sodium Hyaluronate, Panthenol, Allantoin, Ethyl Hexanediol, Sodium Polyacrylate, Carbomer, Phenoxyethanol"
    }
    parsed = parse_kbeauty_product(raw)
    assert parsed["brand"] == "COSRX"
    assert parsed["name"] == "Advanced Snail 96 Mucin Power Essence"
    assert "Snail Secretion Filtrate" in parsed["raw_ingredients"]

def test_fetch_kbeauty_products(tmp_path):
    files = fetch_kbeauty_products(limit=10, output_dir=tmp_path)
    assert len(files) == 10
    assert files[0].exists()
    with open(files[0], "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "brand" in data
    assert "raw_ingredients" in data
