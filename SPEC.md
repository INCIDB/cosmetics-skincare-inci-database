# INCIDB Apache Parquet Technical Specification

INCIDB ships high-performance Apache Parquet archives formatted with `pyarrow` under `data/exports/parquet/` (and preview samples under `samples/`).

## Parquet Archive Metrics

| Dataset Name | File Size | Row Count | Column Count | Compression / Encoding |
| :--- | :---: | :---: | :---: | :--- |
| `brands.parquet` | 121 KB | 5,994 | 5 | Snappy / Dictionary |
| `ingredients.parquet` | 4.84 MB | 57,181 | 14 | Snappy / Dictionary |
| `products.parquet` | 5.13 MB | 19,847 | 8 | Snappy / Plain |
| `product_ingredients.parquet` | 1.09 MB | 330,088 | 4 | Snappy / Bit-Packed |

## Quick Start in Python (PyArrow / Pandas)

```python
import pyarrow.parquet as pq
import pandas as pd

# Load 19,847 cosmetic products
products = pq.read_table('data/exports/parquet/products.parquet').to_pandas()
print(f"Loaded {len(products):,} products across {products['brand_id'].nunique():,} brands.")

# Load 57,181 canonical INCI ingredients
ingredients = pq.read_table('data/exports/parquet/ingredients.parquet').to_pandas()

# Filter for carcinogenic or endocrine-disrupting ingredients
hazards = ingredients[(ingredients['cancer_hazard_flag'] == 1) | (ingredients['endocrine_hazard_flag'] == 1)]
print(f"Flagged {len(hazards)} high-hazard cosmetic compounds.")

# Join product formulations with ingredient toxicology profiles
junction = pq.read_table('data/exports/parquet/product_ingredients.parquet').to_pandas()
full_formulations = junction.merge(products[['product_id', 'name']], on='product_id') \
                            .merge(ingredients[['ingredient_id', 'inci_name', 'ewg_hazard_score']], on='ingredient_id')

print(full_formulations.head(10))
```

## SQL Querying with DuckDB

You can execute blazing-fast analytical SQL directly against the Parquet files without loading them into RAM:

```python
import duckdb

# Find top 5 ingredients with the highest average EWG hazard score used across products
query = """
SELECT 
    i.inci_name,
    COUNT(pi.product_id) AS formulation_count,
    ROUND(AVG(i.ewg_hazard_score), 2) AS avg_hazard
FROM 'data/exports/parquet/product_ingredients.parquet' pi
JOIN 'data/exports/parquet/ingredients.parquet' i ON pi.ingredient_id = i.ingredient_id
GROUP BY i.inci_name
HAVING formulation_count > 50
ORDER BY avg_hazard DESC
LIMIT 5;
"""
print(duckdb.query(query).to_df())
```
