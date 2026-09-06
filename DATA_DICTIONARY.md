# INCIDB Data Dictionary — snapshot 2026.09

Five tables, exported as pipe-delimited UTF-8 CSV (`|`) and Apache Parquet
with identical columns. Every enrichment column is either populated from a
named public source with a documented join, or `NULL`. There are no default
values, no placeholder rows and no inferred chemistry.

The authoritative per-column fill rates, distinct-value counts and the
SHA-256 of every source file are in `build_report.json`, shipped in the same
archive as these tables. The headline numbers below are also published as
`claims.json` on the repository, and a test fails the build if the two ever
disagree.

| Table | Rows |
| :--- | ---: |
| `products` | 18,583 |
| `brands` | 5,925 |
| `ingredients` | 46,973 |
| `product_ingredients` | 318,758 |
| `ingredient_name_map` | 55,426 |

---

## 1. `brands`

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `brand_id` | `INTEGER` | Primary key | `1` |
| `name` | `STRING` | Brand name as recorded in Open Beauty Facts. Never blank: a product whose source label records no brand carries `products.brand_id = NULL` instead of pointing at an unnamed brand row | `Laneige` |

---

## 2. `products`

One row per Open Beauty Facts product that carried a usable ingredient
declaration.

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `product_id` | `INTEGER` | Primary key | `68597` |
| `brand_id` | `INTEGER` | FK → `brands.brand_id`. **`NULL` = no brand on the source label** — 1,151 products carry no brand in Open Beauty Facts, and are given NULL rather than being attached to a placeholder brand row | `55` |
| `barcode_ean` | `STRING` | GTIN / EAN barcode | `4006381333931` |
| `name` | `STRING` | Product name as recorded upstream | `Good Genes Lactic Acid Treatment` |
| `category` | `STRING` | Product category — 15 distinct values across the corpus | `Skincare` |
| `raw_ingredient_text` | `STRING` | The unparsed on-pack ingredient declaration, kept verbatim so you can re-derive the parse | `Water, Glycerin, ...` |
| `created_at` | `STRING` | Ingestion timestamp (ISO 8601) | `2026-07-02T14:01:48Z` |

---

## 3. `ingredients`

One row per **distinct canonical INCI name** across the corpus. CosIng-derived
columns are populated only where the canonical name matched the European
Commission CosIng inventory on an exact name match; they are `NULL` otherwise.

| Field | Type | Source | Description |
| :--- | :--- | :--- | :--- |
| `ingredient_id` | `INTEGER` | — | Primary key |
| `inci_name` | `STRING` | canonicalisation | The canonical name. Every raw label token that resolved here is listed in `ingredient_name_map` |
| `cosing_matched` | `INTEGER` | CosIng | `1` when the canonical name matched the CosIng inventory, else `0`. Gates every column below it that is marked CosIng |
| `cosing_ref_no` | `STRING` | CosIng | CosIng reference number |
| `cas_number` | `STRING` | CosIng | CAS registry number, taken from CosIng only |
| `ec_number` | `STRING` | CosIng | EC number. A CosIng entry covering several substances joins their EC numbers with ` / `; a substance CosIng lists no EC number for is omitted from that join, and an entry with none at all is `NULL` — the `-` placeholder is never shipped |
| `functions` | `STRING` | CosIng | CosIng functional categories, multi-valued, `;`-separated (`SKIN CONDITIONING;HUMECTANT`) |
| `chemical_description` | `STRING` | CosIng | CosIng chemical / IUPAC description text |
| `cosing_restriction` | `STRING` | CosIng | CosIng restriction reference (`V/21` = Annex V entry 21) |
| `cosing_update_date` | `STRING` | CosIng | **Always `NULL` in this snapshot** — the inventory export used carries no update date |
| `annex_ii` … `annex_vi` | `FLOAT` | CosIng | `1.0` / `0.0` membership of Annexes II (prohibited), III (restricted), IV (colorants), V (preservatives), VI (UV filters). `NULL` when not CosIng-matched |
| `is_common_allergen` | `INTEGER` | EU Annex III | `1` for the EU fragrance allergens, else `0`. See the method note below |
| `allergen_source` | `STRING` | EU Annex III | `EU_ANNEX_III` on flagged rows, `NULL` otherwise |
| `comedogenic_rating` | `FLOAT` | authored | 0–5 rating for the ingredients covered by the cited paper; `NULL` otherwise |
| `is_fungal_acne_trigger` | `FLOAT` | rule | `1.0` / `0.0` rule-derived flag; `NULL` where the rule was not applicable |
| `rating_source` | `STRING` | authored / rule | The per-row citation (or the rule text) behind `comedogenic_rating` and `is_fungal_acne_trigger` |

### Coverage of the CosIng columns — both views

| Column | Share of the 46,973 distinct names | Share of the 318,758 label occurrences |
| :--- | ---: | ---: |
| CosIng match (any) | 11.0% | 82.5% |
| `functions` | 10.9% | 81.5% |
| `cas_number` | 8.3% | 76.4% |
| `chemical_description` | 8.5% (3,965 distinct values) | — |

The left column counts distinct names; the right counts ingredient
occurrences across product labels. They differ by an order of magnitude
because a label corpus contains far more distinct strings — botanical
variants, multilingual spellings, marketing tokens, one-off blends — than any
regulatory inventory lists, while the slots on a real label are filled
overwhelmingly by ingredients CosIng does cover. Neither number alone
describes the data; use whichever matches your query.

`ec_number`, `cosing_restriction` and the Annex flags are populated on the
CosIng-matched subset only, at their own rates — see `build_report.json`.

### Method note — canonicalisation and `ingredient_name_map`

Raw label tokens are resolved to canonical INCI names by an explicit ordered
procedure: HTML-entity decode, strip characters outside the INCI character
set, collapse whitespace, upper-case, then attempt (in order) an exact
inventory match, a cleaned match, a small cited typo map, percentage
stripping, parenthesis stripping, a synonym map, slash-variant splitting, and
longest-match concatenation splitting where **both** halves match the
inventory. Nothing that fails all of these is guessed at: it is kept verbatim
and recorded as `unresolved`. The method that resolved each token is stored
per row, so the whole mapping is auditable and reversible — see table 5.

### Method note — `is_common_allergen` / `allergen_source`

Flags come from **one** list: the fragrance allergens of Annex III to the EU
Cosmetics Regulation (Regulation (EC) 1223/2009, as amended by Regulation
(EU) 2023/1545), matched on exact canonical name. **99** names are flagged.
The US FDA has not yet published its MoCRA fragrance-allergen list; when it
does, flags derived from it will carry a distinct `allergen_source` value.
Until then no row in this dataset carries a US flag.

### Method note — `comedogenic_rating`

**145** ingredients carry a rating on the 0–5 scale, transcribed from
Table I (pp. 324–326) of Fulton JE Jr., *Comedogenicity and irritancy of
commonly used ingredients in skin care products*, J Soc Cosmet Chem
1989;40:321–333 (ISSN 0037-9832; the paper predates DOI and PMID
assignment). Where the paper prints a range rather than a single grade the
rating is left `NULL`. Every other ingredient is `NULL` — the absence of a
rating means "not covered by the cited source", never "safe".

### Method note — `is_fungal_acne_trigger`

This is a **rule-derived heuristic, not a measured property.** No
per-ingredient *Malassezia* assay exists to transcribe. The rule flags
C11–C24 fatty acids and their esters, and polysorbates 20/40/60/80, and it is
applied only to CosIng-matched ingredients (so the chemical identity behind
the flag is a known one). **270** ingredients are flagged. The basis is the
lipid dependence of *Malassezia* — Saunte et al., *Front Cell Infect
Microbiol* 2020;10:112 (DOI 10.3389/fcimb.2020.00112) — with the chain-length
window taken from Liebregts et al., *FEMS Yeast Res* 2025;25:foaf043 (DOI
10.1093/femsyr/foaf043). Specific oils, butters and waxes are **not** flagged:
the literature does not support ingredient-level calls on them. Use this
column as a filter, never as a finding.

---

## 4. `product_ingredients`

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `product_id` | `INTEGER` | FK → `products.product_id` | `68597` |
| `ingredient_id` | `INTEGER` | FK → `ingredients.ingredient_id` | `1214` |
| `position_index` | `INTEGER` | 1-indexed position on the label; lower means declared earlier, i.e. present in a higher proportion | `1` |
| `concentration_percentage` | `STRING` | **Always `NULL` in this snapshot** — labels almost never declare percentages, and none survived parsing | |

---

## 5. `ingredient_name_map`

The canonicalisation evidence, shipped with the data. Every raw label token
seen anywhere in the corpus appears here exactly once per canonical target.

| Field | Type | Description | Example |
| :--- | :--- | :--- | :--- |
| `raw_name` | `STRING` | The token as it appeared in `products.raw_ingredient_text` | `AQUA (WATER)` |
| `canonical_name` | `STRING` | The canonical INCI name it resolved to | `AQUA` |
| `method` | `STRING` | How it resolved — see the table below | `paren_stripped` |
| `confidence` | `FLOAT` | Confidence attached to the method | `0.9` |
| `ingredient_id` | `INTEGER` | FK → `ingredients.ingredient_id` | `162` |

| `method` | Meaning |
| :--- | :--- |
| `exact` | The cleaned token is already a CosIng inventory name |
| `cleaned` | Resolved after entity decoding, character stripping and whitespace collapse |
| `typo_map` | Resolved through a small, explicit, cited typo table |
| `percent_stripped` | A declared percentage was removed (`GLYCERIN 5%`) |
| `paren_stripped` | A parenthetical was removed (`AQUA (WATER)`) |
| `synonym_map` | Resolved through an explicit synonym table |
| `slash_variant` | A slash-joined multilingual variant (`WATER/EAU/AQUA`) |
| `split` | A run-together token split into two names, both of which matched the inventory |
| `unresolved` | No canonical match — the token is kept verbatim and flagged, never guessed |

`unresolved` is the largest bucket by distinct token and a small one by label
occurrence: the same long-tail effect that produces the two coverage columns
above.

---

## Columns present but empty in this snapshot

Named here so nothing in the archive is a surprise. They carry no data and
must not be relied on: `ingredients.cosing_update_date` and
`product_ingredients.concentration_percentage`.

Two columns inherited from a much earlier schema — a product price and an
ingredient common name — were filled for 0 rows and have been dropped
outright in this snapshot rather than shipped empty.

---

## Licence

Product, brand and composition data © Open Beauty Facts contributors,
licensed under the Open Database License (ODbL) v1.0 — attribution and
share-alike apply to any redistributed derivative. Ingredient enrichment
contains data from the European Commission CosIng database, reused with
attribution under the Commission's public-sector information reuse policy.
Provided as-is, without warranty; the flags and ratings above are
informational and are not medical, safety or regulatory-compliance advice.
