# INCIDB Apache Parquet Technical Specification

INCIDB ships high-performance Apache Parquet archives formatted with `pyarrow` (`products.parquet`, `ingredients.parquet`, `brands.parquet`, `product_ingredients.parquet`), plus preview samples in the free download.

## Parquet Archive Metrics

| Dataset Name | File Size | Row Count | Column Count | Compression / Encoding |
| :--- | :---: | :---: | :---: | :--- |
| `brands.parquet` | 121 KB | 5,994 | 5 | Snappy / Dictionary |
| `ingredients.parquet` | 4.84 MB | 44,816 | 14 | Snappy / Dictionary |
| `products.parquet` | 5.13 MB | 19,645 | 8 | Snappy / Plain |
| `product_ingredients.parquet` | 1.09 MB | 323,730 | 4 | Snappy / Bit-Packed |

## Quick Start in Python (PyArrow / Pandas)

```python
import pyarrow.parquet as pq
import pandas as pd

# Load 19,645 cosmetic products
products = pq.read_table('products.parquet').to_pandas()
print(f"Loaded {len(products):,} products across {products['brand_id'].nunique():,} brands.")

# Load 44,816 canonical INCI ingredients
ingredients = pq.read_table('ingredients.parquet').to_pandas()

# Filter for FDA MoCRA contact allergens
allergens = ingredients[ingredients['is_common_allergen'] == 1]
print(f"Flagged {len(allergens)} MoCRA contact allergens.")

# Join product formulations with ingredient functional profiles
junction = pq.read_table('product_ingredients.parquet').to_pandas()
full_formulations = junction.merge(products[['product_id', 'name']], on='product_id') \
                            .merge(ingredients[['ingredient_id', 'inci_name', 'primary_function']], on='ingredient_id')

print(full_formulations.head(10))
```

## SQL Querying with DuckDB

You can execute blazing-fast analytical SQL directly against the Parquet files without loading them into RAM:

```python
import duckdb

# Find the 5 most-used ingredients that are flagged MoCRA contact allergens
query = """
SELECT 
    i.inci_name,
    i.primary_function,
    COUNT(pi.product_id) AS formulation_count
FROM 'product_ingredients.parquet' pi
JOIN 'ingredients.parquet' i ON pi.ingredient_id = i.ingredient_id
WHERE i.is_common_allergen = 1
GROUP BY i.inci_name, i.primary_function
ORDER BY formulation_count DESC
LIMIT 5;
"""
print(duckdb.query(query).to_df())
```
