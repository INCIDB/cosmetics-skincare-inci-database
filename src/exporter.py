import sqlite3
from pathlib import Path
from typing import List
import pandas as pd

EXPORT_TABLES = ["brands", "products", "ingredients", "product_ingredients"]

def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Removes embedded newlines, returns, and tabs from string columns for clean flat-file formatting."""
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or df[col].dtype in ["object", "str"]:
            df[col] = df[col].astype(str).str.replace(r"[\r\n\t]+", " ", regex=True).str.strip()
    return df

def export_to_csv(db_path: Path, output_dir: Path) -> List[Path]:
    """Exports all main relational SQLite tables to pipe-delimited CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    saved_files = []
    
    for table in EXPORT_TABLES:
        df = pd.read_sql_query(f"SELECT * FROM {table};", conn)
        df = sanitize_df(df)
        file_path = output_dir / f"{table}.csv"
        df.to_csv(file_path, sep="|", index=False, encoding="utf-8")
        saved_files.append(file_path)
        
    conn.close()
    return saved_files

def export_to_parquet(db_path: Path, output_dir: Path) -> List[Path]:
    """Exports all main relational SQLite tables to Apache Parquet format."""
    output_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    saved_files = []
    
    for table in EXPORT_TABLES:
        df = pd.read_sql_query(f"SELECT * FROM {table};", conn)
        df = sanitize_df(df)
        file_path = output_dir / f"{table}.parquet"
        df.to_parquet(file_path, engine="pyarrow", index=False)
        saved_files.append(file_path)
        
    conn.close()
    return saved_files

if __name__ == "__main__":
    db = Path("data/incidb.sqlite")
    csv_dir = Path("data/exports/csv")
    parquet_dir = Path("data/exports/parquet")
    
    csv_files = export_to_csv(db, csv_dir)
    parquet_files = export_to_parquet(db, parquet_dir)
    print(f"[Success] Exported {len(csv_files)} CSV files and {len(parquet_files)} Parquet files.")
