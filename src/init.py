from pathlib import Path
from src.utils import ensure_directories
from src.db import init_database

def main():
    data_dir = Path("data")
    ensure_directories(data_dir)
    print("[+] Verified raw data directories under data/raw/")
    
    db_path = data_dir / "incidb.sqlite"
    schema_path = Path("docs/schema.sql")
    init_database(db_path, schema_path)
    print(f"[+] Initialized SQLite database at {db_path}")

if __name__ == "__main__":
    main()
