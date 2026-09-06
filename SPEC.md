# INCIDB Apache Parquet Technical Specification

Snapshot 2026.09. Every table ships twice: as pipe-delimited (`|`) UTF-8 CSV
and as an Apache Parquet archive written with `pyarrow` (Snappy compression,
dictionary encoding where it pays). Both carry identical columns, so you can
prototype against the CSV and ship against the Parquet.

## Archive metrics

| Table | Parquet size | CSV size | Rows | Columns |
| :--- | ---: | ---: | ---: | ---: |
| `brands` | 0.11 MiB | 0.12 MiB | 5,925 | 2 |
| `products` | 4.77 MiB | 9.55 MiB | 18,583 | 8 |
| `ingredients` | 2.33 MiB | 4.96 MiB | 46,973 | 21 |
| `product_ingredients` | 1.18 MiB | 4.97 MiB | 318,758 | 4 |
| `ingredient_name_map` | 4.06 MiB | 7.72 MiB | 55,426 | 5 |

Parquet is roughly **54%** smaller than the equivalent CSV across the whole
snapshot — less than the headline figures compression benchmarks usually
quote, because most of the payload is high-cardinality free text (raw label
declarations, chemical descriptions, per-row citations) rather than the
repeated low-cardinality columns dictionary encoding thrives on.

## Quick start — PyArrow / Pandas

```python
import pyarrow.parquet as pq
import pandas as pd

products = pq.read_table('products.parquet').to_pandas()
ingredients = pq.read_table('ingredients.parquet').to_pandas()
links = pq.read_table('product_ingredients.parquet').to_pandas()

# Coverage on your slice, weighted by label occurrence rather than by
# distinct name — the two differ by an order of magnitude.
merged = links.merge(ingredients, on='ingredient_id', how='left')
print(merged['functions'].notna().mean())

# EU Annex III fragrance allergens
allergens = ingredients[ingredients['is_common_allergen'] == 1]

# Full composition, in label order
full = (links.merge(products[['product_id', 'name']], on='product_id')
             .merge(ingredients[['ingredient_id', 'inci_name', 'functions', 'cas_number']],
                    on='ingredient_id')
             .sort_values(['product_id', 'position_index']))
```

## Quick start — DuckDB

```python
import duckdb

# Which CosIng functional categories fill the most label slots?
duckdb.query("""
SELECT f.function, COUNT(*) AS label_slots
FROM 'product_ingredients.parquet' pi
JOIN 'ingredients.parquet' i USING (ingredient_id)
CROSS JOIN UNNEST(string_split(i.functions, ';')) AS f(function)
WHERE i.functions IS NOT NULL
GROUP BY 1
ORDER BY 2 DESC
LIMIT 10;
""").show()
```

```python
# Audit the canonicalisation: how was each raw label token resolved?
duckdb.query("""
SELECT method, COUNT(*) AS rows
FROM 'ingredient_name_map.parquet'
GROUP BY 1
ORDER BY 2 DESC;
""").show()
```

`functions` is multi-valued and `;`-separated; `cas_number`,
`chemical_description`, `ec_number` and the Annex flags are `NULL` wherever
the canonical name did not match the CosIng inventory. See
[DATA_DICTIONARY.md](DATA_DICTIONARY.md) for the measured coverage of each
column and the method notes behind the flags.
