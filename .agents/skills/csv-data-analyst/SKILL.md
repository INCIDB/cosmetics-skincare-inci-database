---
name: csv-data-analyst
description: Use when inspecting, querying, analyzing, profiling, cleaning, validating, or generating insights and reports from CSV or flat tabular data files
---

# CSV Data Analyst

## Overview
**CSV Data Analyst** provides a systematic, memory-efficient methodology for exploring, querying, auditing, and analyzing CSV and tabular data files. It prevents common data analysis failures (such as out-of-memory crashes, delimiter encoding misreadings, and unverified statistical claims) by establishing strict inspection protocols and leveraging high-performance querying tools (`python`, `sqlite3`, `duckdb`, `pandas`).

## When to Use
Use this skill when:
- Explored or analyzing newly exported or third-party CSV files (e.g., `products.csv`, `ingredients.csv`).
- Investigating data anomalies, duplicate entries, missing values, or schema drift.
- Performing aggregations, frequency distributions, or statistical profiling across large tabular datasets.
- Generating structured reports, markdown summaries, or comparative tables for the user from flat files.
- Verifying data pipeline export integrity and delimiter/encoding correctness.

## Core Methodology: The 4-Step Analysis Protocol

### Step 1: Safe Initial Inspection (Never Blindly Load Large Files)
Never load an entire CSV into memory without profiling its scale and structure first.
1. **Check file scale and line count:**
   ```bash
   python -c "import os; print('Size:', os.path.getsize('data.csv')/1024/1024, 'MB'); print('Lines:', sum(1 for _ in open('data.csv', encoding='utf-8', errors='ignore')))"
   ```
2. **Identify delimiter, headers, and quote rules:**
   Inspect the first 5 lines to verify whether the delimiter is comma `,`, pipe `|`, tab `\t`, or semicolon `;`.
   ```bash
   python -c "with open('data.csv', encoding='utf-8') as f: [print(repr(f.readline())) for _ in range(5)]"
   ```

### Step 2: High-Performance SQL Querying & Profiling
Instead of writing complex ad-hoc loops, use standard Python `sqlite3` in-memory tables or standard `csv` / `pandas` tools to execute analytical SQL queries directly against CSV data.

**Pattern: In-Memory SQLite Analysis for Flat Files:**
```python
import sqlite3
import pandas as pd

# Load CSV into an in-memory SQLite database specifying exact delimiter
df = pd.read_csv('data/exports/csv/products.csv', sep='|', dtype=str)
conn = sqlite3.connect(':memory:')
df.to_sql('products', conn, index=False)

# Query aggregations and distributions
query = """
SELECT brand, count(*) as count 
FROM products 
GROUP BY brand 
ORDER BY count DESC 
LIMIT 10;
"""
print(pd.read_sql_query(query, conn))
```

### Step 3: Comprehensive Data Quality Audit
Conduct rigorous checks across five quality pillars before reporting findings:
1. **Completeness:** Check for null, empty (`""`), or whitespace-only strings across required fields.
2. **Uniqueness:** Verify primary keys and flag duplicate rows or ID collisions.
3. **Consistency:** Check categorical fields for case anomalies (e.g., `'SKINCARE'` vs `'Skincare'`) or trailing spaces.
4. **Referential Integrity:** When analyzing relational CSV exports (e.g., `products.csv` joined with `product_ingredients.csv`), verify foreign key mappings.
5. **Encoding & Special Characters:** Audit non-ASCII characters, UTF-8 BOM prefixes (`\ufeff`), or unescaped newline characters inside quoted strings.

### Step 4: Structured Reporting & Synthesis
When presenting data insights to the user:
- **Summarize first:** State total record counts, time ranges, and key findings at the top.
- **Use Markdown Tables:** Format comparative distributions cleanly with clear column headers.
- **Highlight Anomalies:** Use GitHub alerts (`> [!WARNING]`, `> [!NOTE]`) to call out missing fields, outliers, or suspicious data distributions.

---

## Quick Reference & One-Line Tools

| Task | Command / Pattern |
| :--- | :--- |
| **Inspect Header & Column Types** | `python -c "import pandas as pd; df=pd.read_csv('file.csv', sep='\|', nrows=5); print(df.dtypes)"` |
| **Check Null Counts per Column** | `python -c "import pandas as pd; df=pd.read_csv('file.csv', sep='\|'); print(df.isnull().sum())"` |
| **Find Duplicate Primary Keys** | `python -c "import pandas as pd; df=pd.read_csv('file.csv', sep='\|'); print(df[df.duplicated(subset=['id'])])"` |
| **Top 10 Frequency Distribution** | `python -c "import pandas as pd; df=pd.read_csv('file.csv', sep='\|'); print(df['brand'].value_counts().head(10))"` |

---

## Common Pitfalls & Anti-Patterns

### ❌ Anti-Pattern: Assuming Comma Delimiters
Many enterprise or pipeline exports use pipes (`|`) or tabs (`\t`) to avoid collisions with commas in text descriptions.
* **Fix:** Always explicitly verify `sep='|'` or inspect header bytes before parsing.

### ❌ Anti-Pattern: Silent Type Coercion
Pandas or CSV readers may auto-convert numeric-looking barcodes (e.g., `'0860014244759'`) into floating point notation (`8.600142e+12`), losing leading zeros or precision.
* **Fix:** Always specify `dtype=str` during initial loading unless performing pure mathematical operations.

### ❌ Anti-Pattern: Unverified Assertions
Claiming "there are no duplicates" or "all records have ingredients" without running exact quantitative verification commands.
* **Fix:** Apply the verification-before-completion mindset: run quantitative queries and inspect exact outputs before making assertions.
