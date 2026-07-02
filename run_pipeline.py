from pathlib import Path
from src.init import main as init_env
from src.scraper import scrape_sephora_products
from src.enricher import process_sephora_cache
from src.safety_enricher import enrich_database_safety
from src.exporter import export_to_csv, export_to_parquet

def run():
    print("=== INCIDB Prototype Ingestion Pipeline ===")
    
    # Step 1: Init DB & dirs
    init_env()
    
    # Step 2: Scrape Sephora
    raw_dir = Path("data/raw/sephora")
    scraped = scrape_sephora_products(raw_dir)
    print(f"[*] Step 2 Complete: Scraped {len(scraped)} raw product records.")
    
    # Step 3: Ingest & Normalize via Gemini/Rules
    db_path = Path("data/incidb.sqlite")
    ingested = process_sephora_cache(raw_dir, db_path)
    print(f"[*] Step 3 Complete: Normalized & ingested {ingested} products into SQLite.")
    
    # Step 4: Enrich Safety Ratings
    updated = enrich_database_safety(db_path)
    print(f"[*] Step 4 Complete: Enriched {updated} ingredients with EWG/CosIng safety scores.")
    
    # Step 5: Export CSV & Parquet
    csv_files = export_to_csv(db_path, Path("data/exports/csv"))
    parquet_files = export_to_parquet(db_path, Path("data/exports/parquet"))
    print(f"[*] Step 5 Complete: Exported {len(csv_files)} CSV and {len(parquet_files)} Parquet files.")
    print("=== Pipeline Execution Successful ===")

if __name__ == "__main__":
    run()
