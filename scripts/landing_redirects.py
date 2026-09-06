#!/usr/bin/env python3
"""
landing_redirects.py — generate Cloudflare Pages `_redirects` rules for
renamed INCI monograph pages.

The enrichment rebuild reassigned every ingredient's numeric id (a fresh
canonicalisation pass over the same CosIng/label data), so a landing page
that used to live at `/landing/inci_<old-id>_<slug>` now lives at
`/landing/inci_<new-id>_<slug>` — same name-slug, different id, because the
id is a row number in the new `ingredients` table, not a stable key. Every
other old landing URL (an ingredient dropped for having no CosIng function,
or a genuine rename) has no successor and should 404.

This script maps mechanically and conservatively: for each `/landing/inci_
<id>_<slug>` URL in a PREVIOUS sitemap.xml, if the current `landing/`
directory contains EXACTLY ONE file whose slug (the part after the numeric
id) matches, emit a 301 redirect to it. Zero matches or two-or-more matches
(an ambiguous rename) get no rule — a real 404 is acceptable there per the
Task 12 fix-round-1 brief; this script prints the unmapped slugs so a human
can review them.

Category-hub pages (`/landing/skin_conditioning` etc., no `inci_<id>_`
prefix) are left alone: they are not renamed by the rebuild and either still
exist (no redirect needed) or genuinely retired (404 is fine).

Any existing `_redirects` content is preserved — new rules are appended, not
overwritten, and existing lines are not duplicated when re-run.

Usage:  PYTHONUTF8=1 python scripts/landing_redirects.py <previous-sitemap.xml>
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LANDING_DIR = ROOT / "landing"
REDIRECTS_PATH = ROOT / "_redirects"

OLD_URL_RE = re.compile(r"<loc>https?://[^/]+(/landing/inci_(\d+)_([a-z0-9_]+))</loc>")
CURRENT_FILE_RE = re.compile(r"^inci_(\d+)_([a-z0-9_]+)\.html$")


def old_landing_urls(sitemap_path):
    """[(old_path, old_id, slug), ...] for every inci_<id>_<slug> URL."""
    text = Path(sitemap_path).read_text(encoding="utf-8")
    return [(m.group(1), m.group(2), m.group(3)) for m in OLD_URL_RE.finditer(text)]


def current_slug_index(landing_dir=LANDING_DIR):
    """slug -> [new_id, ...] for every current inci_<id>_<slug>.html file."""
    index = {}
    for path in Path(landing_dir).glob("inci_*.html"):
        m = CURRENT_FILE_RE.match(path.name)
        if not m:
            continue
        new_id, slug = m.group(1), m.group(2)
        index.setdefault(slug, []).append(new_id)
    return index


def build_rules(sitemap_path, landing_dir=LANDING_DIR):
    """Returns (rules, unmapped) where rules is a list of '/old /new 301'
    strings and unmapped is a list of (old_path, reason) for slugs with
    zero or multiple current matches."""
    slug_index = current_slug_index(landing_dir)
    rules = []
    unmapped = []

    for old_path, old_id, slug in old_landing_urls(sitemap_path):
        # Skip a slug that still resolves under its old id (nothing moved).
        if (landing_dir / f"inci_{old_id}_{slug}.html").exists():
            continue
        matches = slug_index.get(slug, [])
        if len(matches) == 1:
            new_path = f"/landing/inci_{matches[0]}_{slug}"
            rules.append(f"{old_path} {new_path} 301")
        elif not matches:
            unmapped.append((old_path, "0 matches"))
        else:
            unmapped.append((old_path, f"{len(matches)} matches: {matches}"))

    return rules, unmapped


def write_redirects(rules, redirects_path=REDIRECTS_PATH):
    existing_lines = []
    if Path(redirects_path).exists():
        existing_lines = Path(redirects_path).read_text(encoding="utf-8").splitlines()
    existing_set = set(existing_lines)

    new_lines = [r for r in rules if r not in existing_set]
    all_lines = existing_lines + new_lines
    Path(redirects_path).write_text("\n".join(all_lines) + "\n", encoding="utf-8")
    return len(new_lines)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if len(argv) != 1:
        print("usage: landing_redirects.py <previous-sitemap.xml>", file=sys.stderr)
        return 2

    rules, unmapped = build_rules(argv[0])
    written = write_redirects(rules)

    print(f"mapped: {len(rules)} (wrote {written} new rule(s) to {REDIRECTS_PATH})")
    print(f"unmapped: {len(unmapped)}")
    for old_path, reason in unmapped:
        print(f"  {old_path}  ({reason})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
