import sqlite3
from pathlib import Path

def get_connection(db_path: Path) -> sqlite3.Connection:
    """Returns an open SQLite database connection."""
    return sqlite3.connect(db_path)

def ensure_columns_exist(conn: sqlite3.Connection):
    """Safely migrates existing database schema by adding new columns if missing."""
    cur = conn.cursor()
    new_columns = [
        ("cir_safety_verdict", "VARCHAR(100)"),
        ("fda_warning", "VARCHAR(255)"),
        ("cancer_hazard_flag", "BOOLEAN DEFAULT 0"),
        ("endocrine_hazard_flag", "BOOLEAN DEFAULT 0")
    ]
    
    try:
        cur.execute("PRAGMA table_info(ingredients);")
        cols = {row[1] for row in cur.fetchall()}
        for col_name, col_type in new_columns:
            if col_name not in cols:
                try:
                    cur.execute(f"ALTER TABLE ingredients ADD COLUMN {col_name} {col_type};")
                except sqlite3.OperationalError:
                    pass
        conn.commit()
    except Exception:
        pass

def init_database(db_path: Path, schema_path: Path):
    """Initializes SQLite database using provided schema file and runs migrations."""
    conn = get_connection(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    ensure_columns_exist(conn)
    conn.commit()
    conn.close()
