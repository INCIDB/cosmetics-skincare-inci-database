# INCIDB Pricing & Access

One product. One price. Snapshot 2026.09.

| | Free sample | **INCIDB Complete** |
| :--- | :--- | :--- |
| **Price** | `$0` | **`$79`** one-time |
| **Products** | 200 (all 15 categories) | 18,583 |
| **Brands** | the 200 products' brands | 5,926 |
| **Distinct canonical INCI names** | 1,075 | 46,973 |
| **Composition links** | the 200 products' links | 318,758 |
| **`ingredient_name_map` rows** | for the sampled ingredients | 55,426 |
| **Tables** | all 5 | all 5 |
| **Formats** | CSV (`\|`) + Parquet | CSV (`\|`) + Parquet |
| **CosIng enrichment columns** | included | included |
| **Allergen flags, authored ratings** | included | included |
| **`build_report.json` quality report** | — | included |
| **Delivery** | direct download | Stripe checkout, instant download |
| **Updates** | static | one-time snapshot |

The sample is not a crippled subset: it has the identical schema and the
identical columns. It is smaller, and it is drawn from products whose
ingredient lists are at least 80% CosIng-matched, so its enrichment looks
better than the corpus average. Evaluate against the coverage table below,
not against the sample.

👉 [Buy INCIDB Complete — $79](https://buy.stripe.com/REPLACE-WITH-INCIDB-COMPLETE-LINK)

---

## What you are actually buying

The underlying product data is **open**: it is derived from Open Beauty
Facts and licensed under the Open Database License (ODbL) v1.0, with
attribution and share-alike. You could assemble something like this yourself
from the OBF dump and the CosIng inventory.

What `$79` buys is the work between those raw sources and a table you can
query today:

* **Canonicalisation.** Raw label tokens (HTML entities, stray punctuation,
  declared percentages, parenthetical synonyms, slash-joined multilingual
  variants, run-together fragments) resolved to canonical INCI names by an
  explicit, ordered method — and the `ingredient_name_map` table that records
  which method resolved each token, so you can audit or override it.
* **The CosIng join.** Exact canonical-name match against the European
  Commission CosIng inventory, giving functions, CAS and EC numbers, chemical
  descriptions, restrictions and Annex II–VI membership. Unmatched names get
  `NULL` in every CosIng-derived column, never a placeholder.
* **Measurement.** A `build_report.json` with per-column fill rates,
  distinct-value counts and the SHA-256 of every source file downloaded, so
  you can check the claims below rather than believe them.
* **Delivery.** Both formats, zipped, instant download after checkout.

You are **not** buying exclusive rights to the data. Redistribute it under
ODbL if you want to.

---

## Measured coverage — read this before you buy

Coverage is reported two ways because the two differ by an order of
magnitude, and quoting only one of them would be a lie by omission.

| Column | Share of the 46,973 distinct names | Share of the 318,758 label occurrences |
| :--- | ---: | ---: |
| CosIng match (any) | 11.0% | 82.5% |
| `functions` | 10.9% | 81.5% |
| `cas_number` | 8.3% | 76.4% |
| `chemical_description` | 8.5% (3,966 distinct values) | — |

A cosmetic label corpus contains far more distinct strings than a regulatory
inventory lists — botanical variants, multilingual spellings, marketing
names, one-off blends. Those make up the long tail of the 46,973 names and
are mostly unmatched. The ingredients that actually fill label slots are
overwhelmingly the ones CosIng covers, which is why the right-hand column is
high. Pick the column that matches your use case.

Flags and ratings are deliberately small:

* `is_common_allergen` — **99** names, from the EU Annex III fragrance-allergen
  list (Regulation (EC) 1223/2009 as amended by Regulation (EU) 2023/1545).
  The US FDA has not yet published its MoCRA fragrance-allergen list, so
  there is no US flag in this dataset.
* `comedogenic_rating` — **145** ingredients rated 0–5, transcribed from
  Fulton JE Jr., J Soc Cosmet Chem 1989;40:321–333 (Table I). `NULL`
  everywhere the paper does not reach.
* `is_fungal_acne_trigger` — **270** flags from an explicit rule (C11–C24
  fatty acids and their esters, polysorbates 20/40/60/80, applied only to
  CosIng-matched ingredients). A heuristic, not a measured property. Basis:
  DOI 10.3389/fcimb.2020.00112 and DOI 10.1093/femsyr/foaf043.

---

## Licence

* **Product data:** © Open Beauty Facts contributors, Open Database License
  (ODbL) v1.0 — https://opendatacommons.org/licenses/odbl/1-0/. Use and
  redistribute freely, including commercially, with attribution and
  share-alike.
* **Ingredient enrichment:** contains data from the European Commission
  CosIng database, reused under the Commission's public-sector information
  reuse policy, with attribution.
* **Schema & documentation:** CC BY 4.0.
* Provided as-is, without warranty. Flags and ratings are informational, not
  medical, safety or regulatory-compliance advice.

Company invoice, a custom slice, or a question before buying? Use the contact
form on [the portal](https://incidb.dataengineered.io/#pricing).
