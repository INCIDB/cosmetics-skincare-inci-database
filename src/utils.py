from pathlib import Path

def ensure_directories(base_data_path: Path):
    """Ensures raw data directory structures for sephora and ewg exist."""
    base = Path(base_data_path)
    (base / "raw" / "sephora").mkdir(parents=True, exist_ok=True)
    (base / "raw" / "ewg").mkdir(parents=True, exist_ok=True)
    (base / "raw" / "obf").mkdir(parents=True, exist_ok=True)
    (base / "raw" / "dailymed").mkdir(parents=True, exist_ok=True)
