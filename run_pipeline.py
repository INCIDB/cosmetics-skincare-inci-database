from pathlib import Path
import json
from src.init import main as init_env
from src.scraper import scrape_sephora_products
from src.enricher import process_sephora_cache, process_raw_directory
from src.obf_ingest import fetch_obf_products, ingest_obf_dump
from src.dailymed_ingest import fetch_dailymed_products
from src.cosing_ingest import fetch_cosing_data, enrich_db_with_cosing
from src.kbeauty_ingest import fetch_kbeauty_products
from src.cir_ingest import fetch_cir_data, enrich_db_with_cir
from src.fda_cosmetics_ingest import fetch_fda_cosmetics_data, enrich_db_with_fda
from src.ewg_ingest import fetch_ewg_data, enrich_db_with_ewg
from src.safety_enricher import enrich_database_safety
from src.exporter import export_to_csv, export_to_parquet

def load_json_records(files: list[Path]) -> list[dict]:
    items = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                items.append(json.load(f))
        except Exception:
            pass
    return items

def run(max_dump_records: int = None, live_limit: int = None, live_pages: int = 50):
    print("=== INCIDB Global Multi-Source Ingestion Pipeline ===")
    
    # Step 1: Init DB & dirs
    init_env()
    
    # Step 2: Scrape & Fetch across all global sources
    sephora_dir = Path("data/raw/sephora")
    obf_dir = Path("data/raw/obf")
    dailymed_dir = Path("data/raw/dailymed")
    cosing_dir = Path("data/raw/cosing")
    kbeauty_dir = Path("data/raw/kbeauty")
    cir_dir = Path("data/raw/cir")
    fda_dir = Path("data/raw/fda")
    ewg_dir = Path("data/raw/ewg")
    
    scraped_sephora = scrape_sephora_products(sephora_dir)
    scraped_obf = fetch_obf_products(limit=live_limit, max_pages=live_pages, output_dir=obf_dir)
    scraped_dailymed = fetch_dailymed_products(limit=live_limit, max_pages=live_pages, output_dir=dailymed_dir)
    scraped_kbeauty = fetch_kbeauty_products(limit=live_limit or 120, output_dir=kbeauty_dir)
    
    cosing_files = fetch_cosing_data(limit=500, output_dir=cosing_dir)
    cir_files = fetch_cir_data(limit=500, output_dir=cir_dir)
    fda_files = fetch_fda_cosmetics_data(limit=500, output_dir=fda_dir)
    ewg_files = fetch_ewg_data(limit=500, output_dir=ewg_dir)
    
    total_raw = len(scraped_sephora) + len(scraped_obf) + len(scraped_dailymed) + len(scraped_kbeauty)
    total_reg = len(cosing_files) + len(cir_files) + len(fda_files) + len(ewg_files)
    print(f"[*] Step 2 Complete: Scraped/Fetched {total_raw} product records ({len(scraped_sephora)} Retail, {len(scraped_kbeauty)} K-Beauty, {len(scraped_obf)} OBF, {len(scraped_dailymed)} DailyMed) and {total_reg} safety/regulatory records.")
    
    # Step 3: Ingest & Normalize Formulations into SQLite
    db_path = Path("data/incidb.sqlite")
    ingested_sephora = process_sephora_cache(sephora_dir, db_path)
    ingested_obf = process_raw_directory(obf_dir, db_path, "obf_*.json")
    ingested_dailymed = process_raw_directory(dailymed_dir, db_path, "dailymed_*.json")
    ingested_kbeauty = process_raw_directory(kbeauty_dir, db_path, "kbeauty_*.json")
    
    ingested_dump = 0
    for dump_file in obf_dir.glob("*.jsonl.gz"):
        ingested_dump += ingest_obf_dump(dump_file, db_path, max_records=max_dump_records)
        
    total_ingested = ingested_sephora + ingested_obf + ingested_dailymed + ingested_kbeauty + ingested_dump
    print(f"[*] Step 3 Complete: Normalized & ingested {total_ingested} total products across all formulation sources into SQLite ({ingested_dump} from offline .jsonl.gz dump).")
    
    # Step 4: Enrich Safety Ratings, Toxicological Scores & Regulatory Verdicts
    updated_safety = enrich_database_safety(db_path)
    updated_cosing = enrich_db_with_cosing(db_path, load_json_records(cosing_files))
    updated_cir = enrich_db_with_cir(db_path, load_json_records(cir_files))
    updated_fda = enrich_db_with_fda(db_path, load_json_records(fda_files))
    updated_ewg = enrich_db_with_ewg(db_path, load_json_records(ewg_files))
    
    print(f"[*] Step 4 Complete: Enriched database with safety ratings ({updated_safety}), CosIng EU definitions ({updated_cosing}), CIR expert verdicts ({updated_cir}), FDA MoCRA allergen warnings ({updated_fda}), and EWG toxicological scores ({updated_ewg}).")
    
    # Step 5: Export CSV & Parquet
    csv_files = export_to_csv(db_path, Path("data/exports/csv"))
    parquet_files = export_to_parquet(db_path, Path("data/exports/parquet"))
    print(f"[*] Step 5 Complete: Exported {len(csv_files)} CSV and {len(parquet_files)} Parquet files.")
    print("=== Pipeline Execution Successful ===")

if __name__ == "__main__":
    run()
