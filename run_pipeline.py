from pathlib import Path
from src.init import main as init_env
from src.scraper import scrape_sephora_products
from src.enricher import process_sephora_cache, process_raw_directory
from src.obf_ingest import fetch_obf_products, ingest_obf_dump
from src.dailymed_ingest import fetch_dailymed_products
from src.safety_enricher import enrich_database_safety
from src.exporter import export_to_csv, export_to_parquet

def run(max_dump_records: int = None, live_limit: int = None, live_pages: int = 50):
    print("=== INCIDB Multi-Source Ingestion Pipeline ===")
    
    # Step 1: Init DB & dirs
    init_env()
    
    # Step 2: Scrape Sephora, Open Beauty Facts, & NLM DailyMed OTC Skincare
    sephora_dir = Path("data/raw/sephora")
    obf_dir = Path("data/raw/obf")
    dailymed_dir = Path("data/raw/dailymed")
    
    scraped_sephora = scrape_sephora_products(sephora_dir)
    scraped_obf = fetch_obf_products(limit=live_limit, max_pages=live_pages, output_dir=obf_dir)
    scraped_dailymed = fetch_dailymed_products(limit=live_limit, max_pages=live_pages, output_dir=dailymed_dir)
    
    total_raw = len(scraped_sephora) + len(scraped_obf) + len(scraped_dailymed)
    print(f"[*] Step 2 Complete: Scraped/Fetched {total_raw} raw product records ({len(scraped_sephora)} Sephora, {len(scraped_obf)} Open Beauty Facts, {len(scraped_dailymed)} NLM DailyMed).")
    
    # Step 3: Ingest & Normalize via Gemini/Rules
    db_path = Path("data/incidb.sqlite")
    ingested_sephora = process_sephora_cache(sephora_dir, db_path)
    ingested_obf = process_raw_directory(obf_dir, db_path, "obf_*.json")
    ingested_dailymed = process_raw_directory(dailymed_dir, db_path, "dailymed_*.json")
    
    ingested_dump = 0
    for dump_file in obf_dir.glob("*.jsonl.gz"):
        ingested_dump += ingest_obf_dump(dump_file, db_path, max_records=max_dump_records)
        
    total_ingested = ingested_sephora + ingested_obf + ingested_dailymed + ingested_dump
    print(f"[*] Step 3 Complete: Normalized & ingested {total_ingested} total products across all sources into SQLite ({ingested_dump} from offline .jsonl.gz dump).")
    
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
