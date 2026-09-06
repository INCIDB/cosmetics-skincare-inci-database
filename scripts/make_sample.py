#!/usr/bin/env python3
"""
make_sample.py — INCIDB free sample builder

Builds the free sample distributed as `samples/incidb_free_samples.zip` from
the private `data/incidb.sqlite` database. This script is public and tracked
in git, but the database it reads is NOT: `data/incidb.sqlite` is gitignored
(commercial asset) and is only present on the maintainer's machine. Running
this script anywhere else will fail at the `sqlite3.connect` step with "no
such table" errors once a query executes against an empty/absent database —
that is expected. The pre-built `samples/incidb_free_samples.zip` is what
public readers actually get; this script is provided for transparency about
how it was produced.

Only stdlib + `sqlite3`/`pandas`/`pyarrow`/`zipfile` are used here — no
imports from the internal (gitignored) `src/` enrichment pipeline. That keeps
this script runnable, standalone, and auditable by anyone who does have a
copy of the database, without pulling in code a public reader could never
execute anyway.

Sample design
-------------
`select_sample_products()` draws `n` products (default 200) from the pool of
ELIGIBLE products, uniformly at random and deterministically for a given
`seed`. Nothing stratifies the draw. The sample used to be stratified across
`products.category`, but that column was a hard-coded default plus a keyword
heuristic with no per-row provenance — a fabricated value — so it was dropped
(see `src/enrichment/obf_categories.py`). Stratifying on the source's own
`obf_categories_tags` instead is not a like-for-like swap: it is present on
only about 69% of products, and a draw stratified over it would silently
over-represent classified products. A seeded uniform draw over the eligible
pool makes no claim the data cannot support.

A product is ELIGIBLE when it has at least one linked ingredient AND at least
80% of its linked ingredients (`product_ingredients` rows) have
`ingredients.cosing_matched = 1`. Products with zero linked ingredients are
excluded (the match ratio is undefined for them, and including them would
misrepresent the enrichment quality the sample exists to showcase). This
eligibility rule is disclosed on every surface that quotes a sample number:
the sample reads better than the corpus average BY CONSTRUCTION.

`write_sample()` then writes the 5 relational tables (`brands`, `products`,
`ingredients`, `product_ingredients`, `ingredient_name_map`) restricted to
the selected products — their own rows, their brands, the ingredients they
link to, the ingredient_name_map rows for those ingredients, and the
product-ingredient links themselves — as pipe-delimited CSV and Parquet,
using the same column set as the full dataset export (`src/exporter.py`'s
`SELECT * FROM <table>`), and zips all 10 files flat (no directory prefix)
into `<out_dir>/incidb_free_samples.zip`. It also writes
`<out_dir>/sample_stats.json` — the same counts it returns — so that
`scripts/render_claims.py` can build `claims.json` from measured numbers
instead of hand-typed ones.
"""

import argparse
import json
import random
import sqlite3
import zipfile
from pathlib import Path

import pandas as pd

TABLES = ["brands", "products", "ingredients", "product_ingredients", "ingredient_name_map"]
ELIGIBILITY_THRESHOLD = 0.80


def _sanitize(df: pd.DataFrame) -> pd.DataFrame:
    """Collapses embedded newlines/tabs/runs of whitespace in string columns to a single space,
    matching the full export's flat-file formatting, while leaving actual NULLs as NULL."""
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].map(lambda v: " ".join(str(v).split()) if pd.notna(v) else v)
    return df


def select_sample_products(db_path: Path, n: int = 200, seed: int = 20260905) -> list:
    """Returns a deterministic, uniformly random sample of eligible product_ids.

    See the module docstring for the eligibility rule and for why the draw is
    unstratified. Returns every eligible product when the pool is smaller than
    `n`, sorted by product_id in all cases.
    """
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT p.product_id,
                   COUNT(pi.ingredient_id) AS total_ing,
                   SUM(CASE WHEN i.cosing_matched = 1 THEN 1 ELSE 0 END) AS matched_ing
            FROM products p
            LEFT JOIN product_ingredients pi ON pi.product_id = p.product_id
            LEFT JOIN ingredients i ON i.ingredient_id = pi.ingredient_id
            GROUP BY p.product_id
            ORDER BY p.product_id
            """
        ).fetchall()
    finally:
        conn.close()

    eligible = []
    for product_id, total_ing, matched_ing in rows:
        total_ing = total_ing or 0
        matched_ing = matched_ing or 0
        if total_ing == 0:
            continue
        if (matched_ing / total_ing) >= ELIGIBILITY_THRESHOLD:
            eligible.append(product_id)

    if not eligible:
        return []

    eligible.sort()
    rng = random.Random(seed)
    return sorted(rng.sample(eligible, min(n, len(eligible))))


def write_sample(db_path: Path, product_ids: list, out_dir: Path) -> dict:
    """Writes the 5 sample tables (CSV + Parquet) restricted to `product_ids` and zips them.

    Returns a dict of summary counts (see module docstring / DATA_DICTIONARY.md
    sample table for how these are used).
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    product_ids = sorted(set(product_ids))

    conn = sqlite3.connect(db_path)
    try:
        if not product_ids:
            products_df = pd.read_sql_query("SELECT * FROM products WHERE 0", conn)
        else:
            placeholders = ",".join("?" * len(product_ids))
            products_df = pd.read_sql_query(
                f"SELECT * FROM products WHERE product_id IN ({placeholders}) ORDER BY product_id",
                conn, params=product_ids,
            )

        brand_ids = sorted({int(b) for b in products_df["brand_id"].dropna().unique()})
        if brand_ids:
            bp = ",".join("?" * len(brand_ids))
            brands_df = pd.read_sql_query(
                f"SELECT * FROM brands WHERE brand_id IN ({bp}) ORDER BY brand_id", conn, params=brand_ids,
            )
        else:
            brands_df = pd.read_sql_query("SELECT * FROM brands WHERE 0", conn)

        if not product_ids:
            links_df = pd.read_sql_query("SELECT * FROM product_ingredients WHERE 0", conn)
        else:
            placeholders = ",".join("?" * len(product_ids))
            links_df = pd.read_sql_query(
                f"SELECT * FROM product_ingredients WHERE product_id IN ({placeholders}) "
                "ORDER BY product_id, position_index",
                conn, params=product_ids,
            )

        ingredient_ids = sorted({int(i) for i in links_df["ingredient_id"].dropna().unique()})
        if ingredient_ids:
            ip = ",".join("?" * len(ingredient_ids))
            ingredients_df = pd.read_sql_query(
                f"SELECT * FROM ingredients WHERE ingredient_id IN ({ip}) ORDER BY ingredient_id",
                conn, params=ingredient_ids,
            )
            name_map_df = pd.read_sql_query(
                f"SELECT * FROM ingredient_name_map WHERE ingredient_id IN ({ip}) "
                "ORDER BY ingredient_id, raw_name",
                conn, params=ingredient_ids,
            )
        else:
            ingredients_df = pd.read_sql_query("SELECT * FROM ingredients WHERE 0", conn)
            name_map_df = pd.read_sql_query("SELECT * FROM ingredient_name_map WHERE 0", conn)
    finally:
        conn.close()

    tables = {
        "brands": brands_df,
        "products": products_df,
        "ingredients": ingredients_df,
        "product_ingredients": links_df,
        "ingredient_name_map": name_map_df,
    }

    for name, df in tables.items():
        df = _sanitize(df)
        df.to_csv(out_dir / f"{name}.csv", sep="|", index=False, encoding="utf-8")
        df.to_parquet(out_dir / f"{name}.parquet", engine="pyarrow", index=False)

    zip_path = out_dir / "incidb_free_samples.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for name in TABLES:
            zf.write(out_dir / f"{name}.csv", arcname=f"{name}.csv")
            zf.write(out_dir / f"{name}.parquet", arcname=f"{name}.parquet")

    stats = {
        "products": len(products_df),
        "brands": len(brands_df),
        "ingredients": len(ingredients_df),
        "links": len(links_df),
        "name_map_rows": len(name_map_df),
        "ingredients_cosing_matched": int((ingredients_df["cosing_matched"] == 1).sum()) if len(ingredients_df) else 0,
        "ingredients_with_functions": int(ingredients_df["functions"].notna().sum()) if len(ingredients_df) else 0,
        "ingredients_with_cas": int(ingredients_df["cas_number"].notna().sum()) if len(ingredients_df) else 0,
        "allergen_flagged": int((ingredients_df["is_common_allergen"] == 1).sum()) if len(ingredients_df) else 0,
        "rated": int(ingredients_df["comedogenic_rating"].notna().sum()) if len(ingredients_df) else 0,
    }

    # Published alongside the zip so the public copy generator (scripts/render_claims.py)
    # never has to hand-type the sample's numbers. Written outside the zip on purpose:
    # it describes the sample, it is not part of it.
    (out_dir / "sample_stats.json").write_text(
        json.dumps(stats, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the INCIDB free sample zip from data/incidb.sqlite.")
    parser.add_argument("--db", type=Path, default=Path("data/incidb.sqlite"))
    parser.add_argument("--out", type=Path, default=Path("samples"))
    parser.add_argument("--n", type=int, default=200)
    parser.add_argument("--seed", type=int, default=20260905)
    args = parser.parse_args()

    product_ids = select_sample_products(args.db, n=args.n, seed=args.seed)
    result = write_sample(args.db, product_ids, args.out)
    print(f"[Success] Sampled {len(product_ids)} products -> {args.out / 'incidb_free_samples.zip'}")
    print(result)
