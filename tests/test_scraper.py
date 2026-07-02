import json
from pathlib import Path
import pytest
from src.scraper import parse_sephora_html, save_raw_product, scrape_sephora_products

MOCK_HTML = """
<html>
  <body>
    <div data-comp="ProductBrand">CeraVe</div>
    <h1 data-comp="ProductName">Daily Moisturizing Lotion</h1>
    <span data-comp="Price">$14.99</span>
    <div data-comp="Ingredients">
      Water, Glycerin, Caprylic/Capric Triglyceride, Niacinamide, Cetearyl Alcohol, Ceramide NP
    </div>
  </body>
</html>
"""

def test_parse_sephora_html():
    product = parse_sephora_html(MOCK_HTML, "https://www.sephora.com/product/daily-moisturizing-lotion-P12345")
    assert product["brand"] == "CeraVe"
    assert product["name"] == "Daily Moisturizing Lotion"
    assert product["price"] == 14.99
    assert "Niacinamide" in product["raw_ingredients"]
    assert product["barcode"] == "12345"
    assert product["url"] == "https://www.sephora.com/product/daily-moisturizing-lotion-P12345"

def test_save_raw_product(tmp_path):
    output_dir = tmp_path / "sephora"
    product = {
        "brand": "CeraVe",
        "name": "Daily Moisturizing Lotion",
        "price": 14.99,
        "barcode": "P12345",
        "raw_ingredients": "Water, Glycerin",
        "url": "https://www.sephora.com/product/daily-moisturizing-lotion-P12345"
    }
    
    file_path = save_raw_product(product, output_dir)
    
    assert file_path.exists()
    with open(file_path, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["brand"] == "CeraVe"
    assert saved_data["name"] == "Daily Moisturizing Lotion"

def test_scrape_sephora_products(tmp_path):
    output_dir = tmp_path / "sephora_raw"
    files = scrape_sephora_products(output_dir, use_mock_fallback=True)
    
    assert len(files) == 5
    for f in files:
        assert f.exists()
        with open(f, "r", encoding="utf-8") as file:
            data = json.load(file)
            assert "brand" in data
            assert "raw_ingredients" in data
