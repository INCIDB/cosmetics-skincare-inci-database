#!/usr/bin/env python3
"""
render_claims.py — regenerate `claims.json` from the measured build outputs.

`claims.json` is the single source of truth for every number printed on a
public INCIDB surface (README.md, index.html, schema.html, llms.txt,
DATA_DICTIONARY.md, docs/pricing_plan.md). `tests/test_public_claims.py`
re-reads those files and fails if any of them states a count or a coverage
percentage that this file does not contain, so marketing copy cannot drift
away from the corpus.

Inputs (all produced by the build, none hand-typed):

* `data/exports/build_report.json` — row counts, per-column fill rates and
  distinct-value counts, the CosIng match rates, the allergen counts, the
  authored-rating counts, and the `regulatory` block (EU allergen overlay).
  Written by `src/enrichment/report.py`.
* `data/exports/csv/ingredients.csv` + `data/exports/csv/product_ingredients.csv`
  — used only to compute LINK-WEIGHTED coverage: the share of ingredient
  OCCURRENCES across product labels (not the share of distinct ingredient
  names) for which CosIng gave us a function / a CAS number / any match at
  all. `build_report.json` carries the link-weighted figure for the CosIng
  match itself but not per enrichment column, so those two are recomputed
  here from the same exports the customer receives.
* `samples/sample_stats.json` — written by `scripts/make_sample.py` when it
  builds `samples/incidb_free_samples.zip`.

Both coverage views matter and the copy states both: row-level coverage is
low because the long tail of the corpus is one-off marketing tokens and
botanical variants that CosIng does not list; link-weighted coverage is high
because the ingredients that actually appear on labels are the ones CosIng
covers. Quoting only one of the two would be misleading, in either direction.

Like `scripts/make_sample.py`, this script is public but its inputs are not:
`data/` is gitignored (commercial asset), so running this outside the
maintainer's machine will fail on the missing report. The committed
`claims.json` is the artefact; this script documents exactly how it was
produced.

Usage:  PYTHONUTF8=1 python scripts/render_claims.py [--check]

`--check` recomputes and diffs against the committed `claims.json` without
writing, exiting non-zero on any difference.
"""

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_PATH = ROOT / "data" / "exports" / "build_report.json"
CSV_DIR = ROOT / "data" / "exports" / "csv"
SAMPLE_STATS_PATH = ROOT / "samples" / "sample_stats.json"
CLAIMS_PATH = ROOT / "claims.json"
KOREA_REPORT_PATH = ROOT / "data" / "exports" / "korea" / "korea_report.json"

# The one number here that is a decision rather than a measurement.
PRICE_USD = 79

# INCIDB Korea launch constants: decisions, not measurements, kept here like PRICE_USD
# because claims.json is regenerated whole. claims.json gets a "korea" block only once
# `released` is True; until then nothing public may name the tier
# (tests/test_public_claims.py::test_no_korea_tier_before_launch). At launch the owner
# supplies the Stripe price id and payment link, set here together with released=True.
#
# Adaptation note (spec §6 amended 2026-09-26): claims.json is a public file and spec §7
# requires no Korea content before launch, so claims["korea"] is added by build_claims()
# only once korea_claims() returns a non-None block (tier released). The Korea ZIP's
# report-vs-CSV/Parquet count gates (build_delivery.build_korea) run every month regardless
# of whether the tier is released; its claims-vs-report gate starts only once released,
# since there is no "korea" block in claims.json to check before then.
KOREA_TIER = {
    "price_usd": 149,
    "released": False,
    "payment_link": "https://buy.stripe.com/REPLACE-WITH-INCIDB-KOREA-LINK",
    "stripe_price_id": None,
}
# korea_report.json keys (written by src.enrichment.regulatory.kr_mfds_build) that the
# block carries; build_delivery.build_korea checks the same keys against the ZIP.
KOREA_MEASURED_KEYS = ("entries_annex1", "entries_annex2", "substances", "linked_names",
                       "products_pct", "notice_no", "notice_date")


def pct(value):
    """Fraction (0..1) -> percentage rounded to 1 decimal, as the copy prints it."""
    return round(value * 100, 1)


def link_weighted_coverage(csv_dir=CSV_DIR):
    """Share of ingredient occurrences on product labels covered by each column.

    Reads the shipped exports rather than the database so the numbers describe
    exactly what the customer downloads. Returns fractions in 0..1.
    """
    csv_dir = Path(csv_dir)
    occurrences = Counter()
    with open(csv_dir / "product_ingredients.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="|"):
            occurrences[row["ingredient_id"]] += 1

    total = sum(occurrences.values())
    if not total:
        raise ValueError("product_ingredients.csv has no rows — cannot weight by link")

    covered = {"cosing_matched": 0, "functions": 0, "cas_number": 0}
    with open(csv_dir / "ingredients.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="|"):
            n = occurrences.get(row["ingredient_id"], 0)
            if not n:
                continue
            if (row.get("cosing_matched") or "").strip() == "1":
                covered["cosing_matched"] += n
            if (row.get("functions") or "").strip():
                covered["functions"] += n
            if (row.get("cas_number") or "").strip():
                covered["cas_number"] += n

    return {k: v / total for k, v in covered.items()}


def korea_claims(report_path=KOREA_REPORT_PATH, tier=KOREA_TIER):
    """The claims.json "korea" block, or None while the tier is unreleased.

    A released tier must carry a live Stripe payment link and price id: the worker
    maps the price id to the two ZIPs, and a placeholder link on the site would be a
    dead checkout. `products_pct` is copied as the build wrote it (a percentage with
    one decimal)."""
    if tier.get("released") is not True:
        return None
    link, price_id = tier.get("payment_link") or "", tier.get("stripe_price_id") or ""
    if not link.startswith("https://buy.stripe.com/") or "REPLACE-WITH" in link:
        raise ValueError(f"KOREA_TIER is released but payment_link is not a live Stripe link: {link!r}")
    if not price_id.startswith("price_"):
        raise ValueError(f"KOREA_TIER is released but stripe_price_id is not a Stripe price id: {price_id!r}")
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    block = {k: report[k] for k in KOREA_MEASURED_KEYS}
    block.update(price_usd=tier["price_usd"], released=True, payment_link=link,
                 stripe_price_id=price_id)
    return block


def build_claims(report_path=REPORT_PATH, csv_dir=CSV_DIR,
                 sample_stats_path=SAMPLE_STATS_PATH, korea_report_path=KOREA_REPORT_PATH,
                 korea_tier=None):
    report = json.loads(Path(report_path).read_text(encoding="utf-8"))
    sample = json.loads(Path(sample_stats_path).read_text(encoding="utf-8"))

    counts = report["counts"]
    ing = report["tables"]["ingredients"]
    prod = report["tables"]["products"]
    lw = link_weighted_coverage(csv_dir)

    # "2026-09-06T13:35:09+00:00" -> "2026.09"
    generated_at = report["generated_at"]
    snapshot = f"{generated_at[0:4]}.{generated_at[5:7]}"

    claims = {
        # Corpus row counts.
        "products": counts["products"],
        "brands": counts["brands"],
        # Products whose source label records no brand: they carry
        # products.brand_id = NULL rather than pointing at a placeholder brand
        # row. column_profile counts a blank/NULL as "not non_null".
        "products_without_brand": (
            report["tables"]["products"]["brand_id"]["rows"]
            - report["tables"]["products"]["brand_id"]["non_null"]
        ),
        "ingredients": counts["ingredients"],
        "links": counts["product_ingredients"],
        "name_map_rows": counts["ingredient_name_map"],
        # Row-level coverage: share of the 46,973 DISTINCT ingredient names.
        "cosing_matched_pct": pct(report["cosing"]["match_rate_rows"]),
        "functions_pct": pct(ing["functions"]["fill_rate"]),
        "cas_pct": pct(ing["cas_number"]["fill_rate"]),
        "chemical_description_pct": pct(ing["chemical_description"]["fill_rate"]),
        "chemical_description_distinct": ing["chemical_description"]["distinct"],
        # The source's own product classification (Open Beauty Facts
        # `categories_tags`), joined verbatim. Published as the exact measured
        # fill, count and percent, because it is well below 90% and the copy
        # may never round a partial column up to "every product".
        "obf_categories_filled": prod["obf_categories_tags"]["non_null"],
        "obf_categories_pct": pct(prod["obf_categories_tags"]["fill_rate"]),
        # Link-weighted coverage: share of ingredient OCCURRENCES on labels.
        "cosing_link_weighted_pct": pct(lw["cosing_matched"]),
        "functions_link_weighted_pct": pct(lw["functions"]),
        "cas_link_weighted_pct": pct(lw["cas_number"]),
        # Flag counts.
        "allergen_flagged": report["allergens"]["flagged"],
        # EU fragrance-allergen overlay (build_report.json "regulatory" block).
        "allergen_entries_total": report["regulatory"]["allergens"]["entries_total"],
        "allergen_entries_matched": report["regulatory"]["allergens"]["entries_matched"],
        "allergen_products_pct": pct(report["regulatory"]["allergens"]["products_share"]),
        "allergen_list_version": report["regulatory"]["allergens"]["list_version"],
        "unsplit_allergen_products_pct": pct(report["regulatory"]["allergens"]["unsplit_products_share"]),
        "fragrance_allergens_rows": counts["fragrance_allergens"],
        "regulatory_status_rows": counts["regulatory_status"],
        "rated_comedogenic": report["authored"]["rated"],
        "fungal_flagged": report["authored"]["fungal_flagged"],
        # Free sample.
        "sample_products": sample["products"],
        "sample_ingredients": sample["ingredients"],
        # Release metadata.
        "snapshot": snapshot,
        "price_usd": PRICE_USD,
    }
    korea = korea_claims(korea_report_path, KOREA_TIER if korea_tier is None else korea_tier)
    if korea is not None:
        claims["korea"] = korea
    return claims


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--check", action="store_true",
                    help="compare against the committed claims.json instead of writing it")
    args = ap.parse_args(argv)

    claims = build_claims()
    rendered = json.dumps(claims, indent=2, sort_keys=True) + "\n"

    if args.check:
        current = CLAIMS_PATH.read_text(encoding="utf-8") if CLAIMS_PATH.exists() else ""
        if current != rendered:
            print("claims.json is STALE — re-run scripts/render_claims.py", file=sys.stderr)
            print(rendered, file=sys.stderr)
            return 1
        print("claims.json is current")
        return 0

    CLAIMS_PATH.write_text(rendered, encoding="utf-8")
    print(f"wrote {CLAIMS_PATH}")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
