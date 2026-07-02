import sqlite3
from pathlib import Path

def get_connection(db_path: Path) -> sqlite3.Connection:
    """Returns an open SQLite database connection."""
    return sqlite3.connect(db_path)

def init_database(db_path: Path, schema_path: Path):
    """Initializes SQLite database using provided schema file."""
    conn = get_connection(db_path)
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
