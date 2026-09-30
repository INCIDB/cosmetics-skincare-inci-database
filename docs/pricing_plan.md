# INCIDB Pricing & Access

Two products: INCIDB Complete, and INCIDB Korea (INCIDB Complete plus the
South Korea MFDS overlay, delivered as two archives from the same edition).
Snapshot 2026.09.

| | Free sample | **INCIDB Complete** | **INCIDB Korea** |
| :--- | :--- | :--- | :--- |
| **Price** | `$0` | **`$79`** one-time | **`$149`** one-time |
| **Products** | 200 (seeded random draw) | 20,029 | as Complete |
| **Brands** | the 200 products' brands | 6,453 | as Complete |
| **Distinct canonical INCI names** | 1,123 | 45,584 | as Complete |
| **Composition links** | the 200 products' links | 373,216 | as Complete |
| **`ingredient_name_map` rows** | the rows for the sampled products' own label tokens | 78,151 | as Complete |
| **Tables** | all 7 | all 7 | the 7, plus 3 Korea tables |
| **Formats** | CSV (`\|`) + Parquet | CSV (`\|`) + Parquet | CSV (`\|`) + Parquet |
| **CosIng enrichment columns** | included | included | included |
| **Allergen flags, authored ratings** | included | included | included |
| **EU overlay: `fragrance_allergens`, `regulatory_status`** | rows for the sampled ingredients | included | included |
| **South Korea MFDS overlay (Notice 2026-19)** | — | — | included |
| **`build_report.json` quality report** | — | included | included |
| **Delivery** | direct download | Stripe checkout, instant download | Stripe checkout, instant download of both archives |
| **Updates** | static | one-time snapshot | one-time snapshot of the same edition |

The sample is not a crippled subset: it has the identical schema and the
identical columns. It is smaller, and it is drawn from products whose
ingredient lists are at least 80% CosIng-matched, so its enrichment looks
better than the corpus average. Evaluate against the coverage table below,
not against the sample.

👉 [Buy INCIDB Complete — $79](https://buy.stripe.com/3cIfZi5t6fzwazV1E43840g) · [Buy INCIDB Korea — $149](https://buy.stripe.com/eVq6oIg7K1IG4bxeqQ3840k)

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

## INCIDB Korea

INCIDB Korea is INCIDB Complete plus three tables built from South Korea's
MFDS Notice 2026-19 (Regulation on Safety Standards etc. of Cosmetics),
Annex 1 (ingredients that may not be used) and Annex 2 (ingredients with use
restrictions):

* **Both annexes in full.** 1,077 Annex 1 and 248 Annex 2 entries and 1,784
  CAS sub-rows, including entries that match nothing in INCIDB. The Korean
  text ships as printed; limits and rinse-off scope are parsed into their own
  fields only where the entry states them; later effective dates come from
  the notice's supplementary provisions (부칙).
* **English identities by CAS.** A CAS sub-row carries the CosIng inventory
  names that share its CAS number, where CosIng lists it. That is a
  cross-reference, not a translation of the Korean entry.
* **Links by exact CAS.** 191 INCIDB ingredient names are linked by
  exact CAS and hand-checked; 73.2% of products contain at least one.
  Nothing is fuzzy, and names are never used to match. Links on botanical
  entries, links a hand check found wrong, links whose CAS number several
  INCIDB names share, and links not yet hand-checked stay outside those
  figures; a shared CAS still links normally for a name hand-checked as
  that same substance.

Why it is sold with Complete: `kr_mfds_links` joins to Complete by
`ingredient_id`, and ids are reassigned on every edition, so that join only
works between the two archives of the same edition (across editions, rejoin
on `inci_name` + `cas`). The EU overlay stays inside INCIDB Complete at no
extra cost; Korea is a separate parse of a separate legal text, which is what
the higher price pays for.

Read before relying on it: a link is a positive listing, and an ingredient
without a link has no status in this data, because the notice gives its CAS
numbers as examples. Many Annex 1 entries apply only as limited by a
condition or exception written in the entry (a peroxide value, an impurity
limit, a hair-dye exception). Not legal advice.

---

## Measured coverage — read this before you buy

Coverage is reported two ways because the two differ by an order of
magnitude, and quoting only one of them would be a lie by omission.

| Column | Share of the 45,584 distinct names | Share of the 373,216 label occurrences |
| :--- | ---: | ---: |
| CosIng match (any) | 12.2% | 85.2% |
| `functions` | 12.0% | 84.2% |
| `cas_number` | 9.0% | 78.7% |
| `chemical_description` | 9.5% (4,281 distinct values) | — |

A cosmetic label corpus contains far more distinct strings than a regulatory
inventory lists — botanical variants, multilingual spellings, marketing
names, one-off blends. Those make up the long tail of the 45,584 names and
are mostly unmatched. The ingredients that actually fill label slots are
overwhelmingly the ones CosIng covers, which is why the right-hand column is
high. Pick the column that matches your use case.

Flags and ratings are deliberately small:

* `is_common_allergen` — EU fragrance-allergen overlay (Reg. (EU) 2023/1545):
  **120** names flagged by exact INCI name, label name or CAS for defined
  substances; 47.3% of products carry at least one (about 2.4% of products
  list ingredients as unsplit text that the allergen flags do not reach). The
  per-entry evidence ships in `fragrance_allergens`. The US FDA has not yet published its MoCRA
  fragrance-allergen list, so there is no US flag in this dataset.
* `regulatory_status` — EU Annex II–VI status rows from the CosIng exports,
  conditions verbatim, matched by CosIng glossary or "Identified INGREDIENTS"
  name only. Absence of a row is not a status; not legal advice.
* `comedogenic_rating` — **142** ingredients rated 0–5, transcribed from
  Fulton JE Jr., J Soc Cosmet Chem 1989;40:321–333 (Table I). `NULL`
  everywhere the paper does not reach.
* `is_fungal_acne_trigger` — **276** flags from an explicit rule (C11–C24
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
* **EU regulatory overlay:** Annex III to Regulation (EC) No 1223/2009 as
  amended by Regulation (EU) 2023/1545 (EUR-Lex, © European Union) and the
  CosIng Annex II–VI exports, reused on the same terms, with attribution.
  Not legal advice.
* **South Korea overlay (INCIDB Korea only):** Annexes 1 and 2 of MFDS
  Notice 2026-19, from law.go.kr. Our reading is that Korean Copyright Act
  Art. 7(2) excludes such public notices from protection; not legal advice.
* **Schema & documentation:** CC BY 4.0.
* Provided as-is, without warranty. Flags and ratings are informational, not
  medical, safety or regulatory-compliance advice.

Company invoice, a custom slice, or a question before buying? Use the contact
form on [the portal](https://incidb.dataengineered.io/#pricing).
