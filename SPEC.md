# INCIDB Apache Parquet Technical Specification

Snapshot <!--claims:snapshot-->2026.09<!--/claims-->. Every table ships twice: as pipe-delimited (`|`) UTF-8 CSV
and as an Apache Parquet archive written with `pyarrow` (Snappy compression,
dictionary encoding where it pays). Both carry identical columns, so you can
prototype against the CSV and ship against the Parquet.

## Archive metrics

| Table | Parquet size | CSV size | Rows | Columns |
| :--- | ---: | ---: | ---: | ---: |
| `brands` | <!--archive:parquet_mib.brands-->0.12<!--/archive--> MiB | <!--archive:csv_mib.brands-->0.12<!--/archive--> MiB | <!--claims:brands-->6,453<!--/claims--> | 2 |
| `products` | <!--archive:parquet_mib.products-->5.03<!--/archive--> MiB | <!--archive:csv_mib.products-->10.35<!--/archive--> MiB | <!--claims:products-->20,029<!--/claims--> | 7 |
| `ingredients` | <!--archive:parquet_mib.ingredients-->2.09<!--/archive--> MiB | <!--archive:csv_mib.ingredients-->4.35<!--/archive--> MiB | <!--claims:ingredients-->45,584<!--/claims--> | 20 |
| `product_ingredients` | <!--archive:parquet_mib.product_ingredients-->1.10<!--/archive--> MiB | <!--archive:csv_mib.product_ingredients-->5.29<!--/archive--> MiB | <!--claims:links-->373,216<!--/claims--> | 4 |
| `ingredient_name_map` | <!--archive:parquet_mib.ingredient_name_map-->4.19<!--/archive--> MiB | <!--archive:csv_mib.ingredient_name_map-->19.66<!--/archive--> MiB | <!--claims:name_map_rows-->78,151<!--/claims--> | 7 |
| `fragrance_allergens` | <!--archive:parquet_mib.fragrance_allergens-->0.02<!--/archive--> MiB | <!--archive:csv_mib.fragrance_allergens-->0.09<!--/archive--> MiB | <!--claims:fragrance_allergens_rows-->274<!--/claims--> | 18 |
| `regulatory_status` | <!--archive:parquet_mib.regulatory_status-->0.05<!--/archive--> MiB | <!--archive:csv_mib.regulatory_status-->0.27<!--/archive--> MiB | <!--claims:regulatory_status_rows-->637<!--/claims--> | 15 |

Parquet is roughly **<!--archive:parquet_saving_pct-->69<!--/archive-->%** smaller than the equivalent CSV across the whole
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

## Regulatory overlay

Two further tables ship in the same formats: `fragrance_allergens`, the EU
fragrance-allergen labelling entries of Annex III to Regulation (EC)
1223/2009 as amended by Regulation (EU) 2023/1545, one row per legal name and
INCIDB match (matched by exact INCI name, then collective label name, then
CAS for chemically defined substances only; botanical CAS hits ship as review
rows with `flagged = 0`); and `regulatory_status`, the EU Annex II–VI status
rows from the CosIng exports, matched by CosIng glossary name or "Identified
INGREDIENTS" name only, with conditions verbatim. A `regulatory_status` row
exists only where a list says something; absence of a row is not a status,
and neither table is legal advice. Columns, match methods and source versions
are in [DATA_DICTIONARY.md](DATA_DICTIONARY.md) (tables 6 and 7).
