# INCIDB Data Dictionary — snapshot 2026.09

Seven tables, exported as pipe-delimited UTF-8 CSV (`|`) and Apache Parquet
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
| `fragrance_allergens` | 268 |
| `regulatory_status` | 614 |

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
| `obf_categories_tags` | `STRING` | Open Beauty Facts' own `categories_tags` list for this product, joined with `;` and otherwise **verbatim** — not normalised, not translated, not collapsed into a taxonomy of ours. Present on 12,860 of 18,583 products (69.2%); `NULL` where the source record carries no tags | `en:hygiene;en:soaps` |
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
| `annex_ii` … `annex_vi` | `FLOAT` | CosIng | `1.0` / `0.0` membership of Annexes II (prohibited), III (restricted), IV (colorants), V (preservatives), VI (UV filters). `NULL` when not CosIng-matched. Legacy exact-name method; `regulatory_status` (table 7) is the precise source and may differ |
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
The `annex_ii` … `annex_vi` booleans keep their legacy exact-name method.
`regulatory_status` (table 7) is the precise, per-entry source, and the two
may differ for the same ingredient; when they do, use `regulatory_status`.

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

**EU fragrance allergens.** The 81 labelling entries of Annex III to
Regulation (EC) 1223/2009, as amended by Regulation (EU) 2023/1545
(consolidated text of 18.05.2026), are matched to INCIDB by exact INCI name,
then by the collective label name the Regulation prescribes (e.g. "Rose
Ketones"), then by CAS number for chemically defined substances only.
Botanical CAS hits are shipped as review rows, never flags. 121 names are
flagged; 43.9% of products contain at least one. About 6.4% of products list
ingredients as unsplit text that the allergen flags do not reach. The US FDA
has not yet published its MoCRA fragrance-allergen list, so this dataset
carries no US flag.

`is_common_allergen = 1` and `allergen_source = EU_ANNEX_III` mark exactly
the flagged names. The per-entry evidence (Annex reference, thresholds,
transition dates, match method, source) is in `fragrance_allergens`
(table 6). When the FDA list is published, flags derived from it will carry
a distinct `allergen_source` value.

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

## 6. `fragrance_allergens`

The EU fragrance-allergen labelling entries of Annex III to Regulation (EC)
1223/2009, as amended by Regulation (EU) 2023/1545. One row per legal name ×
INCIDB match. A legal name with no INCIDB match still gets one row, with
`ingredient_id` `NULL`, so the unmatched part of the list ships too. 77 of
the 81 entries match at least one INCIDB name.

| Field | Type | Description |
| :--- | :--- | :--- |
| `annex_iii_ref` | `STRING` | Annex III entry reference as printed |
| `legal_name` | `STRING` | The name as printed in the Regulation's glossary column, parenthetical alias kept (`Rose ketone 4 (Damascenone)`). On `LABEL_NAME` rows, the collective label name |
| `label_as` | `STRING` | The collective label name the Regulation prescribes for the entry (`Rose Ketones`, `Lemongrass Oil`); `NULL` when it prescribes none |
| `cas_listed`, `ec_listed` | `STRING` | CAS and EC numbers as printed for the entry |
| `leave_on_threshold_pct` | `DECIMAL` | Labelling threshold in leave-on products, in percent, parsed per entry (0.001 on every entry today) |
| `rinse_off_threshold_pct` | `DECIMAL` | Labelling threshold in rinse-off products, in percent, parsed per entry (0.01 on every entry today) |
| `placing_on_market_until` | `DATE` | End of the transition for placing non-compliant products on the market (31 Jul 2026) on the entries whose consolidated text carries the transition footnote ((37), (38) or (40)); `NULL` on the others |
| `making_available_until` | `DATE` | End of the transition for making them available (31 Jul 2028), likewise |
| `transition_condition` | `STRING` | The Regulation's proviso for replaced entries, verbatim; `NULL` elsewhere |
| `instrument` | `STRING` | The legal instrument for the entry: the 2023 amending regulation (with its corrigendum) for the entries it touched, the consolidated Annex III for the others |
| `ingredient_id`, `inci_name` | `INTEGER`, `STRING` | The matched INCIDB ingredient; `NULL` when the legal name matched nothing |
| `match_method` | `STRING` | `NAME`, `LABEL_NAME`, `CAS` or `BOTANICAL_CAS_REVIEW` (see below); `NULL` when unmatched |
| `flagged` | `BOOLEAN` | `1` for a flag that sets `ingredients.is_common_allergen`; `0` on review rows and unmatched rows |
| `source` | `STRING` | `EURLEX` (the consolidated legal text) or `COSING_ANNEX_III` (a name CosIng lists for the entry that the legal text does not print) |
| `source_url`, `retrieved_at` | `STRING`, `DATE` | Where the row came from and the date it was fetched |

| `match_method` | Meaning |
| :--- | :--- |
| `NAME` | Exact match of the legal name (upper-cased, whitespace collapsed, printed alias included) to an INCIDB canonical name |
| `LABEL_NAME` | Exact match of the collective label name the Regulation prescribes |
| `CAS` | A printed CAS number matched INCIDB's CAS. Used only for chemically defined substances, and only when no name matched |
| `BOTANICAL_CAS_REVIEW` | A CAS hit on a botanical entry. Shipped for review, `flagged = 0` |

**Review rows: `flagged = 0`, and why.** A CAS number printed for a botanical
entry (an essential oil or extract) is shared by many preparations of the
same plant (other plant parts, powders, waters, other extracts) that the
Regulation does not name. A CAS hit on a botanical entry therefore does not
establish that the INCIDB ingredient is the listed substance. These rows
ship so you can review them, but they never set `is_common_allergen`.

**CosIng-only names.** Names that CosIng's Annex III export lists for an
entry, in its glossary column or its "Identified INGREDIENTS or substances"
column, but that the legal text does not print are kept, matched by exact
name, and tagged `source = COSING_ANNEX_III` so you can filter them out.

**The unsplit caveat.** Some products carry part of their ingredient list as
one unsplit text string that never resolved into individual names; an
allergen inside such a string is not flagged. `unsplit`, as used in the
6.4% figure above, is defined as:

> share of products linked to an ingredient row with cosing_matched = 0 whose name is longer than 60 characters or has >= 2 commas or >= 2 ' - ' separators, and contains a flagged allergen name or label name at word boundaries; an estimate used only for the coverage caveat, never a flag

**Absence of a row is not a status.** An ingredient with no row here is
simply one this list did not match; it is not a statement about the
ingredient's labelling obligations. This table is not legal advice.

**Source versions.** EUR-Lex consolidated text of Regulation (EC) 1223/2009
as of 18.05.2026 (`source = EURLEX`) and the CosIng Annex III export
(`source = COSING_ANNEX_III`). Each row's `source_url` and `retrieved_at`
record the file and the fetch date; `build_report.json` records each source
file's hash.

---

## 7. `regulatory_status`

One row per ingredient × jurisdiction × list entry. Rows exist only where a
list says something about the ingredient; there is never a "not listed" row.
This snapshot carries the EU Annexes II–VI, from the European Commission
CosIng exports.

| Field | Type | Description |
| :--- | :--- | :--- |
| `ingredient_id`, `inci_name` | `INTEGER`, `STRING` | The INCIDB ingredient |
| `cas` | `STRING` | INCIDB's own CAS value for the ingredient (not used for matching) |
| `jurisdiction` | `STRING` | `EU`. `CA`, `ASEAN` and `CN` are reserved for later sources |
| `list_ref` | `STRING` | The list entry, e.g. `Annex III/98` |
| `status` | `STRING` | `PROHIBITED` (Annex II), `RESTRICTED` (Annex III), `ALLOWED_WITH_CONDITIONS` (Annex IV colorants, V preservatives, VI UV filters). `LISTED_EXISTING` is reserved for positive-only lists |
| `instrument` | `STRING` | CosIng's "Regulation" column as printed |
| `product_type` | `STRING` | Product type / body parts, verbatim; `NULL` when the entry states none |
| `max_concentration` | `STRING` | Maximum concentration in the ready-for-use preparation, verbatim. Multi-part values are never collapsed to one number |
| `condition_text` | `STRING` | Annex II: the entry's "Chemical name / INN" text verbatim, which is where conditional bans live (e.g. "unless the full refining history is known"). Annexes III–VI: the "Other" and "Wording of conditions of use and warnings" columns joined with ` \| ` |
| `effective_date` | `DATE` | Only where the source states one. CosIng does not, so it is `NULL` on every EU row |
| `match_method` | `STRING` | `NAME` or `IDENTIFIED_INGREDIENT` (see below). `CAS` is reserved for later sources |
| `source_url`, `retrieved_at` | `STRING`, `DATE` | The CosIng export the row came from and the date it was fetched |
| `source_update_date` | `STRING` | CosIng's "Update Date" for the entry, as printed |

**`status` is the entry's annex category, not a verdict on the ingredient.**
A row, especially one with `match_method = IDENTIFIED_INGREDIENT`, means
CosIng links the INCI name to that list entry. An Annex II ban covers only
the substance, form or use the entry describes in `condition_text` (for
example hair-dye use only, the nano form only, or a component such as
furocoumarins), so the same ingredient can also carry an Annex III–VI row.
Read `condition_text` before concluding anything.

| `match_method` | Meaning |
| :--- | :--- |
| `NAME` | Exact match of an INCIDB canonical name to the CosIng glossary name ("Name of Common Ingredients Glossary") |
| `IDENTIFIED_INGREDIENT` | Exact match to CosIng's "Identified INGREDIENTS or substances" column |

**No CAS route for the EU rows.** EU `regulatory_status` rows are matched by
glossary name and "Identified INGREDIENTS" name only. A CAS join adds
conditional or wrong rows here (a permitted Annex IV colorant can share a
CAS number with an Annex II entry), so CAS candidates are counted in
`build_report.json` and not emitted. Annex II prints chemical names rather
than INCI names, so its rows come through the "Identified INGREDIENTS"
column.

**Absence of a row is not a status.** An ingredient with no row is one these
lists did not match by name; it is not a statement that the ingredient is
permitted, unrestricted or unregulated anywhere. The `annex_ii` …
`annex_vi` booleans on `ingredients` use an older exact-name method and may
differ from this table; this table is the precise source. Nothing here is
legal advice.

**Source versions.** CosIng Annex II–VI CSV exports. Each row's
`retrieved_at` is the export's fetch date and `source_update_date` CosIng's
own update date for the entry; `build_report.json` records each export's
hash and row count.

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
EU regulatory overlay: Annex III to Regulation (EC) No 1223/2009 as amended
by Regulation (EU) 2023/1545 (EUR-Lex, © European Union) and the CosIng
Annex II–VI exports, reused with attribution. Not legal advice.
Provided as-is, without warranty; the flags and ratings above are
informational and are not medical, safety or regulatory-compliance advice.
