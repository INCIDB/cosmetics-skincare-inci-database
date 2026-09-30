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
| `products` | 19,764 |
| `brands` | 6,412 |
| `ingredients` | 45,327 |
| `product_ingredients` | 367,785 |
| `ingredient_name_map` | 77,367 |
| `fragrance_allergens` | 274 |
| `regulatory_status` | 637 |

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
| `brand_id` | `INTEGER` | FK → `brands.brand_id`. **`NULL` = no brand on the source label** — 2,184 products carry no brand in Open Beauty Facts, and are given NULL rather than being attached to a placeholder brand row | `55` |
| `barcode_ean` | `STRING` | GTIN / EAN barcode | `4006381333931` |
| `name` | `STRING` | Product name as recorded upstream | `Good Genes Lactic Acid Treatment` |
| `obf_categories_tags` | `STRING` | Open Beauty Facts' own `categories_tags` list for this product, joined with `;` and otherwise **verbatim** — not normalised, not translated, not collapsed into a taxonomy of ours. Present on 13,462 of 19,764 products (68.1%); `NULL` where the source record carries no tags | `en:hygiene;en:soaps` |
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

| Column | Share of the 45,327 distinct names | Share of the 367,785 label occurrences |
| :--- | ---: | ---: |
| CosIng match (any) | 12.2% | 85.1% |
| `functions` | 12.0% | 84.0% |
| `cas_number` | 9.0% | 78.6% |
| `chemical_description` | 9.5% (4,257 distinct values) | — |

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
inventory.

Tokens that no method resolves are re-split by explicit rules (unclosed
brackets, `(and)`/`&`, bullets, colons, `. ` separators with an abbreviation
guard, the last ingredient/"contains" marker, spacing around `/`, newlines and
spaced dashes only where re-joining does not resolve, and a strict
full-coverage split in which every word must belong to a matched name). Rules
run only on unresolved tokens; nothing is fuzzy. Unmatched text between
recovered names is kept as `unresolved_residual` rows, in label order. A pair
such as `CI 77891 / TITANIUM DIOXIDE` whose two CosIng names share a CAS
number is one ingredient (`slash_same_cas`, first-listed name).

The re-split is precision-first. Square brackets act as separators (the
`[+/- MAY CONTAIN …]` colour lists), except a bracketed qualifier such as
`[NANO]`, which stays attached to its name (Regulation (EC) 1223/2009,
Art. 19(1)(g)). `(and)` always separates a blend; ` & ` separates only when
every side resolves on its own. A name wrapped across a line break, hyphenated
wraps included (`COCO - BETAINE` → `COCO-BETAINE`), is re-joined before any
split. A translation synonym printed next to its canonical name (`AQUA` …
`WATER`) is one ingredient. A name cut off at a line end is not linked, and a
short misspelt fragment at a line end leaves the next line's first name
unlinked. A name cut by a period, colon or line break (`BENZYL. ALCOHOL`, or
`SHEA` at a line end with `BUTTER` on the next line) is re-joined when the words on
one side are the longest name there, one to four words on the other side
belong to no name of their own, and together they are exactly one different
name (`rejoin`). A complete name on either side of the separator is never cut
into (`SODIUM HYALURONATE. RH-OLIGOPEPTIDE-1` stays two names), and a cut is
never moved next to a slash. When both halves of a slash pair broken at the
slash by a line break or spaced dash resolve, it is still one pair: one link
when they share a CAS number or a canonical, otherwise neither is linked. A
same-CAS pair inside a list without separators is one name of the
full-coverage split. Every recovered name must match the CosIng inventory, or
the cited typo and synonym maps, exactly. `slash_same_cas` never merges two
colour-index codes.

Nothing is guessed at: a token that neither the methods nor the re-split
resolve is kept verbatim and recorded as `unresolved`. The method that
resolved each token is stored per row, with the part's order within the token
and the re-split rules applied, so the whole mapping is auditable and
reversible — see table 5.

### Method note — `is_common_allergen` / `allergen_source`

**EU fragrance allergens.** The 81 labelling entries of Annex III to
Regulation (EC) 1223/2009, as amended by Regulation (EU) 2023/1545
(consolidated text of 18.05.2026), are matched to INCIDB by exact INCI name,
then by the collective label name the Regulation prescribes (e.g. "Rose
Ketones"), then by CAS number for chemically defined substances only.
Botanical CAS hits are shipped as review rows, never flags. 120 names are
flagged; 47.2% of products contain at least one. About 2.4% of products list
ingredients as unsplit text that the allergen flags do not reach. The US FDA
has not yet published its MoCRA fragrance-allergen list, so this dataset
carries no US flag.

`is_common_allergen = 1` and `allergen_source = EU_ANNEX_III` mark exactly
the flagged names. The per-entry evidence (Annex reference, thresholds,
transition dates, match method, source) is in `fragrance_allergens`
(table 6). When the FDA list is published, flags derived from it will carry
a distinct `allergen_source` value.

### Method note — `comedogenic_rating`

**142** ingredients carry a rating on the 0–5 scale, transcribed from
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
the flag is a known one). **275** ingredients are flagged. The basis is the
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
| `position_index` | `INTEGER` | 1-indexed position on the label, contiguous 1..n per product (a repeated ingredient keeps its first position); lower means declared earlier, i.e. present in a higher proportion | `1` |
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
| `part_index` | `INTEGER` | Order of this part within `raw_name`; 1 when the token was not cut | `2` |
| `split_rule` | `STRING` | The re-split rules applied to `raw_name`, `+`-joined; `NULL` when not re-split | `bracket+period` |

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
| `slash_same_cas` | Two slash-joined CosIng names that share a CAS number (`CI 77891 / TITANIUM DIOXIDE`): one ingredient, mapped to the first-listed name |
| `unresolved_residual` | Unmatched text left between names recovered by the re-split, kept in label order (contiguous pieces joined with `, `), never guessed |
| `unresolved` | No canonical match — the token is kept verbatim and flagged, never guessed |

A part cut out of a token by the re-split carries its method's usual
confidence minus 0.1 (the usual confidence of `slash_same_cas` is 0.75);
`unresolved_residual` rows carry 0.0. `split_rule` lists the rules in this order:
`retokenise`, `slash_same_cas`, `bracket`, `square_bracket`, `blend`,
`bullet`, `colon`, `period`, `marker`, `slash_space`, `newline`, `dash`,
`cover`, `rejoin`. `retokenise` on its own means the token resolved after
re-tokenising its original text (line breaks intact) and re-joining line- or
dash-wrapped names; no separator rule split it. `rejoin` means a name cut by a
period, colon or line break was re-joined across it; a period or colon that was
re-joined, not cut, does not also record `period` or `colon`.

`unresolved` is the largest bucket by distinct token and a small one by label
occurrence: the same long-tail effect that produces the two coverage columns
above.

---

## 6. `fragrance_allergens`

The EU fragrance-allergen labelling entries of Annex III to Regulation (EC)
1223/2009, as amended by Regulation (EU) 2023/1545. One row per legal name ×
INCIDB match. A legal name with no INCIDB match still gets one row, with
`ingredient_id` `NULL`, so the unmatched part of the list ships too. 76 of
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
2.4% figure above, is defined as:

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
| `condition_text` | `STRING` | Annex II: the entry's "Chemical name / INN" text verbatim, which is where conditional bans live (e.g. "unless the full refining history is known"). Annexes III–VI: the "Other" and "Wording of conditions of use and warnings" columns joined with ` \| `. The separator is the CSV delimiter too: those values are double-quoted in the CSV, so read the file with a CSV parser (`csv`, pandas, DuckDB), never by splitting lines on `\|`. Parquet is unaffected |
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

`(ingredient_id, list_ref)` is not unique. CosIng can list one substance twice
under the same entry with different conditions (1-NAPHTHOL under Annex III/16
has one row limited to 1 % and one to 2,0 %, both stated in `condition_text`),
and both rows are kept verbatim. Key on the whole row, or group by
`(ingredient_id, list_ref)` and keep every row's `condition_text`.

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

## 8. INCIDB Korea tables (sold separately; not in this archive)

These three tables are not in the INCIDB Complete archive this dictionary
ships in. They are sold separately as INCIDB Korea: INCIDB Complete plus a
second archive from the same edition that holds them, with its own
`README-DELIVERY.txt`, `schema_kr.sql` and `korea_report.json`. They are
built from South Korea's MFDS Notice 2026-19 (Regulation on Safety
Standards etc. of Cosmetics), Annexes 1 and 2. Every printed entry ships,
linked or not. `name_ko`, `limit_ko`, `note_ko` and `chemical_name_ko` are
the Korean text as printed, line-wrap spacing normalised: the source PDF
carries no space characters, so word spaces are inferred from glyph
positions and can differ from the print where a line wraps. Compare on text
with the spaces removed. Join on `entry_id` and CAS, never on Korean text.
No condition text is translated.

**Read an Annex 1 entry with its condition.** Many Annex 1 entries apply
only as limited by a condition or exception written in the entry;
`condition_kind`, `hair_dye_exemption` and each link's `scope_note` point to
it. Limonene is listed only above a peroxide value (`peroxide_value`), talc
only where it fails the Korean Pharmacopoeia asbestos specification
(`impurity_spec`), and an entry with the hair-dye footnote does not cover
use as a hair dye that meets the Annex 2 hair-dye standard
(`hair_dye_exemption`). Read the entry text before treating a link as a ban.

**Links are checked by hand.** Every link with `review = 0` is checked
against the printed entry before the website shows it. A link that a later
edition adds ships in the archive at once and is listed under
`unaudited_links` in `korea_report.json` until it has been checked.
`linked_names` and `products_pct` in `korea_report.json` count only links
that have passed the hand check; `nonreview_names` counts every link with
`review = 0`, and `unaudited_links` lists the difference.

### `kr_mfds_entries`

| Field | Type | Description |
| :--- | :--- | :--- |
| `entry_id` | `STRING` | Stable entry id in print order: `A1-0001`… for Annex 1, `A2-0001`… for Annex 2 |
| `annex` | `INTEGER` | `1` (ingredients that may not be used) or `2` (ingredients with use restrictions) |
| `section` | `STRING` | `prohibited` (the section code of every Annex 1 entry; its scope is in `name_ko`, see `status_label` and `condition_kind`), or the Annex 2 section: `preservative`, `uv_filter`, `hair_dye`, `other` |
| `name_ko` | `STRING` | The 원료명 (ingredient) cell as printed, conditions included: an Annex 1 condition lives in this text |
| `limit_ko` | `STRING` | Annex 2 only: the 사용한도 (use limit) cell, or 사용할 때 농도상한 for hair dyes, as printed; `NULL` on Annex 1 |
| `note_ko` | `STRING` | Annex 2 only: the 비고 (remarks) cell as printed; `NULL` on Annex 1 |
| `hair_dye_exemption` | `BOOLEAN` | `1` when the Annex 1 name carries the ¹⁾ footnote: excepted from the entry when used as a hair dye that meets the Annex 2 hair-dye standard; `0` otherwise (always `0` on Annex 2) |
| `max_pct` | `DECIMAL` | The limit as a number, set only when the printed limit is one unconditional percentage; `NULL` otherwise |
| `limit_basis_ko` | `STRING` | The "~로서" (expressed-as) basis of `max_pct`, spaces removed; `NULL` when the limit states none or the basis cannot be read without guessing |
| `rinse_off_only` | `BOOLEAN` | `1` rinse-off products only (other products banned); `0` the limit also covers leave-on or other products; `NULL` when the entry states neither |
| `banned_in_other_products` | `BOOLEAN` | `1` when the note says 기타 제품에는 사용금지 (not to be used in other products); `NULL` otherwise |
| `condition_kind` | `STRING` | `peroxide_value`, `impurity_spec`, `exception` or `none`: the kind of condition printed in the name cell |
| `status_label` | `STRING` | "Annex 1 entry: scope in entry text" or "Annex 2 restricted: limit in entry text"; never a bare "prohibited" |
| `effective_from` | `DATE` | `NULL` when the entry is in force under this notice; otherwise the later date set by a supplementary provision (부칙) |
| `effective_from_notice` | `STRING` | The notice whose supplementary provision sets `effective_from`; `NULL` when `effective_from` is `NULL` |
| `notice_no` | `STRING` | MFDS notice number of the consolidated text, e.g. `2026-19` |
| `notice_date` | `DATE` | Date of that notice |
| `source_url` | `STRING` | law.go.kr page of the notice |
| `pdf_sha256` | `STRING` | SHA-256 of the annex PDF the entry was parsed from |
| `page_from` | `INTEGER` | First PDF page the entry is printed on |
| `page_to` | `INTEGER` | Last PDF page the entry is printed on (entries can run across a page break) |

One row per printed entry. `status_label` is the entry's annex category,
not a verdict: the form, condition or exception an entry covers is in
`name_ko` (on Annex 2, also in `limit_ko` and `note_ko`).

### `kr_mfds_substances`

| Field | Type | Description |
| :--- | :--- | :--- |
| `entry_id` | `STRING` | The entry this CAS sub-row belongs to |
| `substance_seq` | `INTEGER` | Sub-row order within the entry, from `1` |
| `cas_printed` | `STRING` | The CAS cell as printed (`-` and `a / b` alternatives kept); `NULL` when the cell is empty |
| `cas` | `STRING` | The checksum-valid CAS numbers of the cell, joined with ` / `; `NULL` when none is valid |
| `cas_valid` | `BOOLEAN` | `1` when every hyphenated number printed in the cell is a checksum-valid CAS number; `0` when any fails the check digit (a misprinted CAS, or another number such as the EC number `280-855-6`); `NULL` when the cell prints none |
| `chemical_name_ko` | `STRING` | The 화학물질명 (chemical name) cell as printed |
| `cosing_inci_names` | `STRING` | CosIng inventory names sharing a CAS of the cell, joined with `; `: a CAS cross-reference, not the Korean entry's name. `NULL` when the cell has no valid CAS or CosIng does not know it |

One row per CAS sub-row of an entry. The notice gives its CAS numbers as
representative examples (Annex 1, note 1), so a CAS that is not here proves
nothing.

### `kr_mfds_links`

| Field | Type | Description |
| :--- | :--- | :--- |
| `ingredient_id` | `INTEGER` | INCIDB ingredient id in the INCIDB Complete archive of the same edition |
| `inci_name` | `STRING` | The INCIDB canonical name, carried so a link can be re-joined if ids move between editions |
| `cas` | `STRING` | The CAS number that matched: the one valid CAS INCIDB holds for the ingredient |
| `entry_id` | `STRING` | The linked Korean entry |
| `substance_seq` | `INTEGER` | The sub-row of the entry that printed the CAS |
| `match_method` | `STRING` | `CAS` (exact CAS equality; names are never used to match) |
| `review` | `BOOLEAN` | `1` for a link held for review, `0` otherwise |
| `review_reason` | `STRING` | `EXCLUDED` (a link a hand check found wrong), `BOTANICAL` (the entry prints a Latin plant name, so a CAS match cannot confirm the plant part or preparation) or `FAN_OUT_CAS` (several INCIDB names share the sub-row's CAS; a name hand-checked as that same substance links with `review = 0` instead, a `(NANO)` or colour-index name only where the entry states that grade); `NULL` when `review = 0` |
| `scope_note` | `STRING` | What the link means for this entry, one of four fixed phrases: `listed in Annex 1 (ingredients that may not be used); scope as stated in the entry`, `banned only under the condition stated in the entry`, `banned except as a hair dye meeting the Annex 2 hair-dye standard` (followed by `; further conditions stated in the entry` when the entry also states one), or `listed in the Annex 2 <section> section; see the entry for limit and scope` (`<section>` is the section's English name with its Korean heading, e.g. `preservative (보존제)`) |

Links are many-to-many: the same CAS can sit in several Annex 2 sections.
Review links, and links not yet hand-checked, ship but are left out of the
published link counts.

**A missing link is not a status.** An ingredient without a link is one for
which no printed CAS equals the single CAS INCIDB holds for it; many INCIDB
names hold no CAS, or several. Nothing here is legal advice.

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
INCIDB Korea tables: Annexes 1 and 2 of MFDS Notice 2026-19, from law.go.kr;
our reading is that Korean Copyright Act Art. 7(2) excludes such public
notices from protection (not legal advice).
Provided as-is, without warranty; the flags and ratings above are
informational and are not medical, safety or regulatory-compliance advice.
