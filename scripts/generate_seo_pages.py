#!/usr/bin/env python3
"""
generate_seo_pages.py — INCIDB INCI monograph & category-hub generator.

Reads the free sample under `samples/` (the same seven tables the public can
download) plus `claims.json`, and writes one monograph per ingredient to
`landing/`, one hub per CosIng functional category, and `sitemap.xml`.

Two rules govern everything here, and they are the reason this file was
rewritten:

1. **No defaults.** Earlier versions defaulted `primary_function` to
   "Skin-Conditioning Agent" and `description` to "Standard cosmetic
   ingredient registered in INCI catalog." — so every page claimed a
   function and a description whether or not the data had one. Nothing is
   defaulted now: a field that is empty is simply not rendered.
2. **Hubs are driven by the `functions` values actually recorded.** An
   ingredient is placed in a hub because its CosIng functions match that
   hub's vocabulary, never as a fallback. An ingredient with no CosIng
   function gets no monograph at all — there would be nothing to say about
   it beyond its name, and a page like that is noise for readers and search
   engines alike.

Every count printed on a generated page comes from `claims.json`, which is
itself generated from `data/exports/build_report.json` by
`scripts/render_claims.py`.

Other names (since 2026-09-18). Search Console showed the monographs sitting
on page two for "<common name> inci name" queries — "aloe vera extract inci
name", "bees wax inci name", "glycerin inci" — because the common name a
searcher types appears nowhere on a page titled by its INCI name alone.
CosIng's inventory export (`data/reference/cosing_inventory.csv`, fetched by
the local pipeline, not shipped) records an INN, a European Pharmacopoeia
name and a chemical name for many entries. When that file is present the
generator reads those three columns and renders them as "Other names" — on
the page, in the meta description and as JSON-LD alternateName. When it is
absent, nothing is rendered: the names are CosIng's, never derived here.
"""

import csv
import html
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo_common  # noqa: E402
from css_version import css_href  # noqa: E402

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSS_HREF = css_href("../")
SAMPLES_DIR = os.path.join(ROOT_DIR, "samples")
LANDING_DIR = os.path.join(ROOT_DIR, "landing")
SITEMAP_PATH = os.path.join(ROOT_DIR, "sitemap.xml")
CLAIMS_PATH = os.path.join(ROOT_DIR, "claims.json")
# CosIng inventory export, present only where the local pipeline has fetched it
# (gitignored under data/). See the module docstring: absent file, no names.
COSING_INVENTORY_PATH = os.path.join(ROOT_DIR, "data", "reference", "cosing_inventory.csv")

# Labels for the three CosIng name columns, in the order they are rendered.
NAME_LABELS = (("inn_name", "INN"), ("ph_eur_name", "Ph. Eur."), ("chemical_name", "chemical name"))
# Names longer than this are still data, but a 300-character IUPAC string in a
# meta description or a fact grid helps nobody: it stays in the alternateName
# JSON-LD only.
NAME_DISPLAY_MAX = 90
# At most this many other names on the page / in the description.
NAME_DISPLAY_LIMIT = 4

BASE_URL = "https://incidb.dataengineered.io"

# The owner creates the real Stripe Payment Link for INCIDB Complete and
# swaps it in (Task 13). Until then every buy button carries this literal,
# and `tests/test_public_claims.py::test_no_stripe_placeholder_when_releasing`
# fails the release while it is still present.
STRIPE_COMPLETE_LINK_PLACEHOLDER = "https://buy.stripe.com/3cIfZi5t6fzwazV1E43840g?client_reference_id=incidb_en_landing"

# Layout rules shared by monographs and hubs. They live in classes, not inline
# styles, so the phone breakpoint can override them.
#
# `.page-main` needs `width: 100%`: <body> is a flex column and <main> carries
# `margin: 0 auto` (from .container), so without it <main> is not stretched but
# shrink-wrapped to its min-content width -- and the code <pre>'s longest line
# made that 801px on a 375px phone. `overflow-x: auto` on the <pre> does not
# lower its min-content contribution; a definite width on <main> does.
LAYOUT_CSS = """
        .page-header { border-bottom: 1px solid #232838; padding: 1rem 0; background: rgba(10, 11, 14, 0.85); backdrop-filter: blur(10px); position: sticky; top: 0; z-index: 100; }
        .page-header-inner { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 0.75rem 1.5rem; }
        .page-nav { display: flex; flex-wrap: wrap; gap: 0.5rem 1.5rem; align-items: center; }
        .page-main { flex: 1; width: 100%; padding: 3rem 1rem; overflow-wrap: anywhere; }
        /* Beats the `h1,h2,h3{overflow-wrap:break-word}` that i18n_common.py adds to the
           localized copies: break-word does not lower min-content, so a slash-joined INCI
           name ("ETHYLENE/PROPYLENE/STYRENE COPOLYMER") would still widen the title row. */
        .page-main h1, .page-main h2, .page-main h3 { overflow-wrap: anywhere; }
        .crumbs { margin-bottom: 1rem; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; }
        .page-main pre { max-width: 100%; }
        .monograph-card { background: #111318; border: 1px solid #232838; border-radius: 16px; padding: 2.5rem; margin-bottom: 2.5rem; box-shadow: 0 10px 30px -15px rgba(0,0,0,0.7); }
        .fact-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(min(200px, 100%), 1fr)); gap: 1.25rem; background: #161922; border: 1px solid #232838; border-radius: 12px; padding: 1.5rem; }
        .fact-grid > div { min-width: 0; }
        .query-card { background: #161922; border: 1px solid #232838; border-radius: 16px; padding: 2rem; }
        .hub-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(320px, 100%), 1fr)); gap: 1.25rem; margin-bottom: 3rem; }
        @media (max-width: 600px) {
            .page-header { position: static; }
            .page-header > .container, footer > .container { padding: 0 1rem; }
            .page-main { padding: 2rem 1rem; }
            .page-main h1 { font-size: 1.75rem !important; }
            .monograph-card { padding: 1.25rem; }
            .fact-grid { padding: 1rem; }
            .query-card { padding: 1.25rem; }
        }"""

# Hub definitions, evaluated IN THIS ORDER. An ingredient joins the first hub
# whose vocabulary appears in its `functions` value; the substrings below are
# matched against the real CosIng function vocabulary present in the data.
HUBS = [
    ("preservatives", "Preservatives, Antimicrobials & Antioxidants", "preservatives.html",
     ("PRESERVATIVE", "ANTIMICROBIAL", "ANTIOXIDANT", "ANTICORROSIVE", "CHELATING")),
    ("active_treatments", "Active Treatments, Exfoliants & UV Filters", "active_treatments.html",
     ("UV FILTER", "UV ABSORBER", "LIGHT STABILIZER", "EXFOLIATING", "KERATOLYTIC",
      "ANTI-SEBORRHEIC", "ANTI-SEBUM", "ANTIPLAQUE", "ANTIPERSPIRANT", "BLEACHING")),
    ("fragrance_colour", "Fragrance, Perfuming & Colorant Agents", "fragrance_colour.html",
     ("FRAGRANCE", "PERFUMING", "COLORANT", "HAIR DYEING", "FLAVOURING", "DENATURANT")),
    ("surfactants_cleansing", "Surfactants, Cleansing & Emulsifying Agents", "surfactants_cleansing.html",
     ("SURFACTANT", "CLEANSING", "FOAMING")),
    ("solvents", "Solvents, Viscosity & Structure Agents", "solvents.html",
     ("SOLVENT", "VISCOSITY CONTROLLING", "EMULSION STABILISING", "FILM FORMING",
      "GEL FORMING", "BINDING",
      "BULKING", "OPACIFYING", "ABSORBENT", "ABRASIVE", "ANTICAKING", "ANTIFOAMING",
      "PLASTICISER", "PROPELLANT", "BUFFERING", "PH ADJUSTERS", "SLIP MODIFIER")),
    ("skin_conditioning", "Skin-Conditioning & Emollient Agents", "skin_conditioning.html",
     ("SKIN CONDITIONING", "SKIN PROTECTING", "EMOLLIENT", "HUMECTANT", "MOISTURISING",
      "SMOOTHING", "REFATTING", "REFRESHING", "HAIR CONDITIONING", "NAIL CONDITIONING",
      "ANTISTATIC", "DETANGLING", "HAIR FIXING", "HAIR WAVING", "SOOTHING", "ASTRINGENT",
      "DEODORANT", "TONIC", "ORAL CARE")),
]


# What each hub groups, in plain words, for the reader who arrived from a
# search rather than from the homepage. These paraphrase the CosIng function
# definitions the hub's vocabulary (above) is matched against; they state no
# count -- the counts that follow them are computed from the data at
# generation time.
HUB_INTROS = {
    "preservatives": (
        "Ingredients whose recorded CosIng function is to keep a formulation stable: "
        "preservatives and antimicrobials that inhibit the growth of micro-organisms, "
        "antioxidants that slow oxidation, anticorrosives, and chelating agents that bind "
        "metal ions. The preservatives permitted in EU cosmetics are listed in Annex V of "
        "the Cosmetics Regulation; where CosIng records a restriction, the monograph shows it."),
    "active_treatments": (
        "Ingredients CosIng records with a treatment or protective function: UV filters and "
        "UV absorbers (the filters permitted in EU cosmetics are listed in Annex VI), "
        "exfoliating and keratolytic agents, and the anti-seborrheic, antiplaque, "
        "antiperspirant and bleaching functions."),
    "fragrance_colour": (
        "Fragrance and perfuming ingredients, colorants identified by their Colour Index "
        "number (the colorants permitted in EU cosmetics are listed in Annex IV), hair dyes, "
        "flavourings and denaturants. Fragrance allergens that must be named on the label are "
        "flagged from Annex III on each monograph."),
    "surfactants_cleansing": (
        "Surfactants in the sub-functions CosIng records for them — cleansing, foaming, "
        "emulsifying, solubilising: the ingredients that let an oil phase and a water phase "
        "mix, and that carry soil away in a rinse-off product."),
    "solvents": (
        "Solvents, viscosity-controlling and emulsion-stabilising agents, film formers, gel "
        "formers, binders, bulking and opacifying agents, absorbents, abrasives, propellants "
        "and buffering or pH-adjusting agents — the ingredients that give a product its "
        "texture, body and shelf stability rather than a treatment effect."),
    "skin_conditioning": (
        "Skin- and hair-conditioning agents in the sub-functions CosIng records — emollients, "
        "humectants, skin-protecting occlusives, soothing and refreshing agents — together with "
        "the hair-fixing, antistatic, deodorant, tonic, astringent and oral-care functions. "
        "Where an authored comedogenic grade (Fulton 1989) exists, the monograph shows it."),
}


def clean_slug(name):
    slug = re.sub(r'[^a-zA-Z0-9]+', '_', name.lower()).strip('_')
    return slug or "unknown"


def monograph_filename(ing):
    """`<slug>.html` from the INCI name alone.

    Until 2026-09-20 this was `inci_<ingredient_id>_<slug>.html`; ingredient_id
    is a database autoincrement, so every full rebuild renumbered every URL.
    functions/_middleware.js 301s the old form to this one.
    """
    inci_name = field(ing, 'inci_name') or 'UNKNOWN INCI'
    return f"{clean_slug(inci_name)}.html"


def assert_unique_filenames(ingredients):
    """Fail loudly if two INCI names normalise to the same slug, or a slug
    collides with a hub page: with the id gone from the filename a collision
    would silently overwrite a monograph."""
    owners = {}
    for ing in ingredients:
        owners.setdefault(monograph_filename(ing), []).append(field(ing, 'inci_name'))
    hub_files = {hub_file for _, _, hub_file, _ in HUBS}
    problems = [f"{fn}: {names}" for fn, names in owners.items() if len(names) > 1]
    problems += [f"{fn}: collides with hub page" for fn in owners if fn in hub_files]
    if problems:
        raise SystemExit("landing filename collision(s) -- extend clean_slug() or rename:\n  "
                         + "\n  ".join(problems))


def related_neighbors(hub_members, idx, hub_key, hub_order, buckets):
    """4 other members of the same hub for the related-ingredients block: the
    two before and two after `idx` in the hub's sorted (by INCI name) order,
    wrapping at the ends -- the same order the hub page lists its cards in.

    A hub with fewer than 5 members fills any remaining slots from the next
    non-empty hub's first entries (alphabetical). That path never triggers
    with the current data (every hub has 46+ members) but keeps the rule
    well-defined if a future refresh ever produces a tiny hub.
    """
    n = len(hub_members)
    if n >= 5:
        return [hub_members[(idx + offset) % n] for offset in (-2, -1, 1, 2)]
    others = [m for j, m in enumerate(hub_members) if j != idx]
    if len(others) >= 4:
        return others[:4]
    needed = 4 - len(others)
    start = hub_order.index(hub_key)
    for step in range(1, len(hub_order)):
        nb_key = hub_order[(start + step) % len(hub_order)]
        nb_members = buckets.get(nb_key, [])
        if nb_members:
            others = others + nb_members[:needed]
            break
    return others[:4]


def load_claims():
    with open(CLAIMS_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_data():
    """Loads the sample tables. Missing files yield empty structures."""
    ingredients = []
    products = {}
    prod_ing = {}

    ing_path = os.path.join(SAMPLES_DIR, "ingredients.csv")
    if os.path.exists(ing_path):
        with open(ing_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                ingredients.append(row)

    prod_path = os.path.join(SAMPLES_DIR, "products.csv")
    if os.path.exists(prod_path):
        with open(prod_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                products[row.get('product_id')] = row

    pi_path = os.path.join(SAMPLES_DIR, "product_ingredients.csv")
    if os.path.exists(pi_path):
        with open(pi_path, mode='r', encoding='utf-8', errors='replace') as f:
            for row in csv.DictReader(f, delimiter='|'):
                iid = row.get('ingredient_id')
                pid = row.get('product_id')
                prod_ing.setdefault(iid, [])
                if pid in products:
                    prod_ing[iid].append({
                        'product_name': products[pid].get('name', 'Product #' + pid),
                        'position': row.get('position_index', ''),
                    })

    return ingredients, products, prod_ing


def field(row, name):
    """A field's value, or '' — never a default."""
    return (row.get(name) or '').strip()


def function_list(row):
    """The CosIng functions recorded on this ingredient, as a list."""
    raw = field(row, 'functions')
    return [f.strip() for f in raw.split(';') if f.strip()] if raw else []


def is_flag(row, name):
    """True only for an explicit positive flag; '' and '0' are both False."""
    value = field(row, name)
    return value not in ('', '0', '0.0')


REG_STATUS_LABEL = {
    "PROHIBITED": "Annex II entry (prohibited substance) — scope in the entry text",
    "RESTRICTED": "Restricted",
    "ALLOWED_WITH_CONDITIONS": "Allowed with conditions",
    "LISTED_EXISTING": "Listed (existing ingredient)",
}
REG_JURISDICTION_LABEL = {"EU": "European Union"}


def load_regulatory(samples_dir=SAMPLES_DIR):
    """ingredient_id -> {"allergens": [...], "status": [...]} from the sample tables.
    No file, no rows, no block: absence of a row is never rendered as a status."""
    out = {}
    for fname, key in (("fragrance_allergens.csv", "allergens"), ("regulatory_status.csv", "status")):
        path = os.path.join(samples_dir, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="utf-8", errors="replace", newline="") as f:
            for row in csv.DictReader(f, delimiter="|"):
                iid = (row.get("ingredient_id") or "").strip()
                if iid and (key == "status" or is_flag(row, "flagged")):
                    out.setdefault(iid, {"allergens": [], "status": []})[key].append(row)
    return out


def _date(iso):
    import datetime as _dt
    try:
        return _dt.date.fromisoformat(iso).strftime("%-d %b %Y") if os.name != "nt" else \
            _dt.date.fromisoformat(iso).strftime("%d %b %Y").lstrip("0")
    except ValueError:
        return ""


def regulatory_block(allergens, status):
    """'Regulatory status by region': rendered only from rows. Legal text is data
    (translate="no", captioned 'Official text (EN)'); labels are copy."""
    if not allergens and not status:
        return ""
    e = html.escape

    def data(v):
        return f'<span translate="no" lang="en">{e(v)}</span>'

    items = []
    for a in allergens[:1]:  # one allergen line per ingredient; rows share thresholds and dates
        s = (f"<span>Fragrance allergen: must be named in the ingredient list above "
             f"{data(field(a, 'leave_on_threshold_pct') + ' %')} in leave-on and "
             f"{data(field(a, 'rinse_off_threshold_pct') + ' %')} in rinse-off products.</span>")
        if field(a, "label_as"):
            s += f" <span>Labelled as {data(field(a, 'label_as'))}.</span>"
        if field(a, "source") == "COSING_ANNEX_III":
            s += " <span>(name listed by CosIng for this entry; not printed in the Official Journal text)</span>"
        s += f" <span>Annex III/{data(field(a, 'annex_iii_ref'))}, {data(field(a, 'instrument'))}.</span>"
        placing, making = _date(field(a, "placing_on_market_until")), _date(field(a, "making_available_until"))
        if placing and making:
            s += (f" <span>Transition: non-compliant products could be placed on the market until {data(placing)} "
                  f"and may be made available until {data(making)}")
            s += (f" ({data(field(a, 'transition_condition'))}).</span>" if field(a, "transition_condition") else ".</span>")
        s += (f' <a href="{e(field(a, "source_url"))}" rel="nofollow noopener">Source</a>'
              f' <span>retrieved {data(field(a, "retrieved_at"))}</span>')
        items.append(f"<li>{s}</li>")
    for r in status:
        parts = [f"<strong>{e(REG_STATUS_LABEL.get(field(r, 'status'), field(r, 'status')))}</strong>",
                 data(field(r, "list_ref"))]
        # An Annex II row's text is the entry's scope (substance, form or use), not a condition.
        text_caption = "Entry text" if field(r, "status") == "PROHIBITED" else "Conditions"
        for label, col in (
            ("Product type", "product_type"), ("Maximum concentration", "max_concentration"),
            (text_caption, "condition_text"), ("Instrument", "instrument"),
        ):
            if field(r, col):
                parts.append(f"<span>{label}:</span> {data(field(r, col))}")
        parts.append(f'<a href="{e(field(r, "source_url"))}" rel="nofollow noopener">Source</a> '
                     f'<span>retrieved {data(field(r, "retrieved_at"))}</span>')
        items.append("<li>" + " · ".join(parts) + "</li>")
    jur = REG_JURISDICTION_LABEL["EU"]
    return (f'<section class="regulatory" style="margin: 2rem 0;"><h2 style="font-size: 1.3rem; color: #F8FAFC;">'
            f'Regulatory status by region</h2><h3 style="font-size: 1rem; color: #CBD5E1;">{jur}</h3>'
            f'<p style="font-size: 0.8rem; color: #64748B;">Official text (EN), quoted verbatim from the source list.</p>'
            f'<ul style="color: #CBD5E1; line-height: 1.6;">{"".join(items)}</ul></section>')


def load_cosing_names(path=COSING_INVENTORY_PATH):
    """INCI name -> the CosIng inventory row's name/opinion columns, or {} if
    the export is not on this machine. First row wins on a duplicate name,
    matching `src.enrichment.cosing_join.apply_cosing`."""
    if not os.path.exists(path):
        return {}
    out = {}
    with open(path, mode='r', encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.DictReader(f):
            name = (row.get('inci_name') or '').strip()
            if name and name not in out:
                out[name] = {k: (row.get(k) or '').strip()
                             for k in ('inn_name', 'ph_eur_name', 'chemical_name', 'sccs_opinion')}
    return out


# CosIng suffixes a chemical name with the registry it is taken from:
# "Glycerol (INN); Glycerolum (EP); Glycerol (RIFM)". The tag is provenance,
# not part of the name, and the INN / Ph. Eur. columns already carry those
# two names under their own labels.
_NAME_SOURCE_TAG = re.compile(r"\s*\((?:INN|EP|RIFM|USAN|BAN|JAN|IUPAC|CAS)\)\s*$")


def other_names(inci_name, ref_row):
    """[(name, label), ...] — CosIng's other names for this INCI entry, in
    NAME_LABELS order, de-duplicated case-insensitively, never the INCI name
    itself, never a CosIng source tag. Empty list when there is nothing.

    Splits: INN is one value; Ph. Eur. joins alternatives with " / "; the
    chemical-name column joins alternatives with ";"."""
    if not ref_row:
        return []
    seen = {inci_name.strip().upper()}
    out = []
    for column, label in NAME_LABELS:
        raw = ref_row.get(column, '')
        parts = raw.split(' / ') if column == 'ph_eur_name' else raw.split(';')
        for part in parts:
            name = _NAME_SOURCE_TAG.sub('', part.strip()).strip()
            if not name or name.upper() in seen:
                continue
            seen.add(name.upper())
            out.append((name, label))
    return out


def display_names(names):
    """The subset of other_names() short enough to render as text."""
    return [(n, lbl) for n, lbl in names if len(n) <= NAME_DISPLAY_MAX][:NAME_DISPLAY_LIMIT]


def description_name(names):
    """The one other name that goes in the meta description: the INN if there is
    one, else the Ph. Eur. name, else the shortest chemical name -- CosIng lists
    the systematic (IUPAC-style) chemical name first and the trivial name after
    it, and it is the trivial name a searcher types."""
    if not names:
        return None
    for wanted in ("INN", "Ph. Eur."):
        for n, lbl in names:
            if lbl == wanted:
                return (n, lbl)
    return min(names, key=lambda item: len(item[0]))


def categorize_ingredient(functions):
    """Returns the hub tuple for these CosIng functions, or None.

    None means "this ingredient has no CosIng function we publish a hub for",
    and the caller skips it: no hub, no monograph, no sitemap entry.
    """
    joined = ";".join(functions).upper()
    if not joined:
        return None
    for hub_key, hub_name, hub_file, vocabulary in HUBS:
        if any(term in joined for term in vocabulary):
            return (hub_key, hub_name, hub_file)
    return None


def names_sentence(inci_name, names, data):
    """The "other names" sentence, or '' — `data` wraps a value as translate="no".

    Leads with the INN when CosIng has one, because "GLYCERIN is the INCI name
    of the substance known as glycerol" is the literal answer to the query that
    brought most searchers to these pages ("glycerol inci name")."""
    if not names:
        return ""
    labelled = [f"{data(n)} ({lbl})" for n, lbl in names]

    def join(items):
        return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]

    if names[0][1] == "INN":
        head = (f"{data(inci_name)} is the INCI name of the substance known as {labelled[0]}")
        if len(labelled) == 1:
            return head + "."
        return head + f", also recorded as {join(labelled[1:])}."
    return f"CosIng also records it as {join(labelled)}."


def ingredient_profile(ing, prod_list, names=()):
    """A data-derived prose paragraph. Clauses appear only when the data does."""
    e = html.escape
    inci_name = field(ing, 'inci_name')
    cas = field(ing, 'cas_number')
    ec = field(ing, 'ec_number')
    functions = function_list(ing)
    restriction = field(ing, 'cosing_restriction')
    comedo = field(ing, 'comedogenic_rating')
    allergen = is_flag(ing, 'is_common_allergen')
    fungal = is_flag(ing, 'is_fungal_acne_trigger')

    sentences = []

    # Data values carry translate="no" (see scripts/i18n_common.py): the localized copies
    # keep them verbatim and translate only the sentence around them.
    def data(value):
        return f'<span translate="no">{e(value)}</span>'

    ident = f'<strong translate="no">{e(inci_name)}</strong>' if inci_name else "This ingredient"
    if functions:
        s1 = (f"{ident} is listed in the European Commission CosIng inventory under "
              f"{'the functional category' if len(functions) == 1 else 'the functional categories'} "
              + data(", ".join(f.title() for f in functions)))
    else:
        s1 = f"{ident} is catalogued in INCIDB"
    if cas and ec:
        s1 += f", with CAS number {data(cas)} and EC number {data(ec)}."
    elif cas:
        s1 += f", with CAS number {data(cas)}."
    else:
        s1 += ". CosIng records no CAS number for it, so the column is NULL rather than guessed."
    sentences.append(s1)

    s_names = names_sentence(inci_name, names, data)
    if s_names:
        sentences.append(s_names)

    if restriction:
        sentences.append(
            f"CosIng records a restriction against it ({data(restriction)}), so check the "
            f"corresponding Annex entry before formulating.")

    n_prod = len(prod_list)
    ranked = [p for p in prod_list if str(p.get('position', '')).strip().isdigit()]
    if n_prod:
        s2 = (f"In the free INCIDB sample it appears on {n_prod} product label"
              + ("s" if n_prod != 1 else ""))
        if ranked:
            best = min(ranked, key=lambda p: int(p['position']))
            best_pos = int(best['position'])
            best_name = (best.get('product_name') or '').strip()
            if best_pos == 1 and best_name:
                s2 += f", leading the declaration on {data(best_name)}"
            elif best_name:
                s2 += f", reaching position {best_pos} on {data(best_name)}"
        s2 += "."
        sentences.append(s2)

    if comedo:
        sentences.append(
            f"Fulton (1989) grades it {e(comedo)} on the 0–5 comedogenicity scale; "
            f"that grade is transcribed as-is and is the only rating source used.")

    if allergen:
        sentences.append(
            "It is on the EU Annex III fragrance-allergen list (Regulation (EC) 1223/2009 "
            "as amended by Regulation (EU) 2023/1545), so labelling rules apply above the "
            "regulated thresholds.")
    if fungal:
        sentences.append(
            "INCIDB's rule-derived heuristic flags it as a possible Malassezia "
            "(fungal-acne) trigger. That is a rule, not a measurement — treat it as a "
            "filter rather than a finding.")

    # one <span> per sentence: each optional clause is its own translation segment
    # instead of every combination of clauses being a different paragraph
    body = " ".join(f"<span>{s}</span>" for s in sentences)
    return (
        '<p style="font-size: 1rem; color: #CBD5E1; line-height: 1.75; '
        'margin-bottom: 1.75rem; padding-left: 1rem; border-left: 3px solid #06B6D4;">'
        f'{body}</p>'
    )


def generate_monograph(ing, prod_list, hub_info, claims, related_members, ref_row=None, regulatory=None):
    e = html.escape
    reg = regulatory or {"allergens": [], "status": []}
    inci_name = field(ing, 'inci_name') or 'UNKNOWN INCI'
    cas = field(ing, 'cas_number')
    functions = function_list(ing)
    functions_label = ", ".join(f.title() for f in functions)
    description = field(ing, 'chemical_description')
    comedo = field(ing, 'comedogenic_rating')
    allergen = is_flag(ing, 'is_common_allergen')
    fungal = is_flag(ing, 'is_fungal_acne_trigger')
    all_names = other_names(inci_name, ref_row)
    names = display_names(all_names)
    sccs_opinion = (ref_row or {}).get('sccs_opinion', '')

    filename = monograph_filename(ing)
    filepath = os.path.join(LANDING_DIR, filename)

    hub_key, hub_name, hub_file = hub_info
    products_total = f"{claims['products']:,}"
    price = claims['price_usd']

    badges = []
    if allergen:
        badges.append('<span style="background: rgba(244, 63, 94, 0.15); color: #F43F5E; border: 1px solid #F43F5E; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem; font-weight: 600;">EU Annex III fragrance allergen</span>')
    if fungal:
        badges.append('<span style="background: rgba(245, 158, 11, 0.15); color: #F59E0B; border: 1px solid #F59E0B; padding: 0.3rem 0.75rem; border-radius: 99px; font-family: \'JetBrains Mono\', monospace; font-size: 0.8rem;">Rule-flagged fungal-acne trigger</span>')
    badges_html = "\n                    ".join(badges)

    description_block = ""
    if description:
        # CosIng's English chemical description is source data, not site copy.
        description_block = (
            '<p translate="no" lang="en" style="font-size: 1.05rem; color: #94A3B8; line-height: 1.7; '
            f'margin-bottom: 1.75rem;">{e(description)}</p>')

    # Fact grid: only facts that exist.
    facts = []
    if cas:
        facts.append(("CAS REGISTRY NUMBER", f'<div translate="no" style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: #38BDF8; font-weight: 600;">{e(cas)}</div>'))
    if field(ing, 'ec_number'):
        facts.append(("EC NUMBER", f'<div translate="no" style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: #38BDF8; font-weight: 600;">{e(field(ing, "ec_number"))}</div>'))
    if functions:
        # one span per function so a truncated list in the meta description still
        # matches term by term (i18n_common.py placeholders them in <meta> too)
        fn_spans = ", ".join(f'<span translate="no">{e(f.title())}</span>' for f in functions)
        facts.append(("COSING FUNCTIONS", f'<div translate="no" style="font-size: 1.05rem; color: #F8FAFC; font-weight: 500;">{fn_spans}</div>'))
    if field(ing, 'cosing_restriction') and not reg["status"]:
        facts.append(("COSING RESTRICTION", f'<div translate="no" style="font-family: \'JetBrains Mono\', monospace; font-size: 1.05rem; color: #F59E0B;">{e(field(ing, "cosing_restriction"))}</div>'))
    if comedo:
        colour = '#F43F5E' if float(comedo) >= 3 else '#10B981'
        facts.append(("COMEDOGENIC RATING (FULTON 1989)", f'<div style="font-family: \'JetBrains Mono\', monospace; font-size: 1.1rem; color: {colour}; font-weight: 600;">{e(comedo)} / 5</div>'))
    if names:
        # one line per name; the registry label is copy, the name is data
        name_lines = "".join(
            f'<div><span translate="no">{e(n)}</span> <span style="color: #64748B; font-size: 0.8rem;">({e(lbl)})</span></div>'
            for n, lbl in names)
        facts.append(("OTHER NAMES (COSING)", f'<div style="font-size: 1rem; color: #F8FAFC; font-weight: 500; line-height: 1.5;">{name_lines}</div>'))
    if sccs_opinion:
        # The title of the SCCS (Scientific Committee on Consumer Safety) opinion
        # CosIng attaches to the entry -- a document title, rendered verbatim.
        facts.append(("SCCS OPINION ON FILE", f'<div translate="no" lang="en" style="font-size: 0.92rem; color: #CBD5E1; line-height: 1.5;">{e(sccs_opinion)}</div>'))
    facts_html = "\n".join(
        f'''                <div>
                    <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #64748B; margin-bottom: 0.25rem;">{label}</div>
                    {value}
                </div>''' for label, value in facts)

    prod_rows = ""
    if prod_list:
        for p in prod_list[:8]:
            prod_rows += f"""
            <tr style="border-bottom: 1px solid #232838;">
                <td translate="no" style="padding: 0.75rem; color: #F8FAFC; font-weight: 500;">{e(p['product_name'])}</td>
                <td style="padding: 0.75rem; color: #38BDF8; font-family: 'JetBrains Mono', monospace;">#{e(str(p['position']))}</td>
            </tr>
            """
    else:
        prod_rows = f"""
        <tr>
            <td colspan="2" style="padding: 1rem; color: #64748B; text-align: center;">No sample product links this ingredient. The full snapshot covers {products_total} products.</td>
        </tr>
        """

    # Title and description lead with the answer, not with boilerplate.
    #
    # GSC on 13 Sep 2026 showed these monographs already holding page one for
    # the questions they answer -- "aqua cas no" at position 8.2, "aqua cas
    # number" 7.1, "parfum cas no" 6.7, "purified water inci name" 8.0,
    # "octyldodecanol inci name" 9.7 -- and taking 0% CTR on every one of
    # them. The ranking was never the problem: every page carried the same
    # title, "<NAME> - INCI profile, CosIng functions & CAS number", which
    # tells a searcher looking for a CAS number nothing about whether this
    # result has it. So the CAS number now goes in the title itself.
    #
    # Budgets are 60 characters for the title and 155 for the description --
    # roughly where Google truncates. Both trim tail-first, so the ingredient
    # name and its CAS number always survive; only the trailing descriptive
    # clause and the function list are ever cut.
    # CosIng lists multiple CAS numbers separated by "/" or ";", sometimes with
    # a parenthetical note ("10034-99-8 (heptahydrate)"). Take the first and
    # drop the note -- the title has room for one number, not a list.
    primary_cas = re.split(r"[/;]", cas)[0].strip() if cas else ""
    primary_cas = re.sub(r"\s*\(.*$", "", primary_cas).strip()

    if primary_cas:
        title_head = f"{inci_name} — CAS {primary_cas}"
    else:
        title_head = inci_name
    page_title = title_head
    for tail in (" · INCI Name & CosIng Functions", " · INCI Name & Functions",
                 " · INCI Name", ""):
        if len(title_head + tail) <= 60:
            page_title = title_head + tail
            break

    if primary_cas:
        desc = f"{inci_name} — CAS {primary_cas}."
        closer = " INCI name as listed in the EU CosIng inventory."
    else:
        desc = f"{inci_name} — INCI name in the EU CosIng inventory."
        # State the absence rather than staying silent about it: a reader
        # searching for the CAS number deserves to know CosIng has none.
        closer = " CosIng lists no CAS number for this name."

    # After the name and CAS number, the two facts searchers ask for by name
    # ("<x> inci name", "<x> comedogenic rating") go in before the function
    # list, which is the part that gets trimmed. The other-names clause is the
    # first name only: the description has 155 characters, not a fact grid.
    # The boilerplate closer is what the first name replaces when present.
    if names:
        first_name, first_label = description_name(names)
        desc += f" INCI name for {first_name} ({first_label})."
        closer = ""
    if comedo:
        desc += f" Comedogenic {comedo}/5 (Fulton)."

    if functions:
        fn = functions_label
        # Drop functions from the end until the whole description fits.
        while fn and len(desc) + len(f" CosIng functions: {fn}.") + len(closer) > 155:
            if ", " not in fn:
                fn = ""
                break
            fn = fn.rsplit(", ", 1)[0]
        if fn:
            desc += f" CosIng functions: {fn}."
    meta_description = desc + closer
    if len(meta_description) > 155:
        # A long INCI name plus a long first synonym can exceed the budget on
        # their own; drop the closer, then the comedogenic clause, never the name.
        meta_description = desc
    if len(meta_description) > 155 and comedo:
        meta_description = desc.replace(f" Comedogenic {comedo}/5 (Fulton).", "", 1)

    alternate_names = [n for n, _ in all_names]
    alternate_ld = f', "alternateName": {json.dumps(alternate_names)}' if alternate_names else ''

    # 4 other ingredients from the same CosIng-function hub (the two before
    # and two after this one in the hub's sorted order -- see
    # `related_neighbors`), each labelled with the reason they're grouped,
    # plus the hub itself.
    related_items = [
        (f"/landing/{m['filename'][:-5]}", m['inci_name'], "same CosIng function group", False)
        for m in related_members
    ]
    related_items.append((f"/landing/{hub_file[:-5]}", hub_name, None))
    related_html = seo_common.related_block(related_items, "Related ingredients")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(page_title)}</title>
    <meta name="description" content="{e(meta_description)}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{BASE_URL}/landing/{filename[:-5]}">
    <link rel="alternate" hreflang="en" href="{BASE_URL}/landing/{filename[:-5]}">
    <link rel="alternate" hreflang="x-default" href="{BASE_URL}/landing/{filename[:-5]}">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="{CSS_HREF}">
    <style>
        .related {{ margin-top: 2.5rem; }}
        .related h2 {{ font-size: 1.3rem; margin-bottom: 1rem; color: #F8FAFC; }}
        .related ul {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 0.6rem; }}
        .related li {{ background: #161922; border: 1px solid #232838; border-radius: 8px; padding: 0.5rem 0.9rem; font-size: 0.85rem; }}
        .related a {{ color: #38BDF8; text-decoration: none; }}
        .related a:hover {{ text-decoration: underline; }}
        .related-why {{ color: #64748B; font-size: 0.78rem; }}{LAYOUT_CSS}
    </style>

    <script type="application/ld+json">
    [
      {{
        "@context": "https://schema.org",
        "@type": "TechArticle",
        "headline": "INCI monograph: {e(inci_name)}",
        "description": {json.dumps(meta_description)},
        "url": "{BASE_URL}/landing/{filename[:-5]}",
        "author": {{"@type": "Organization", "name": "INCIDB"}},
        "publisher": {{
          "@type": "Organization",
          "name": "INCIDB",
          "logo": {{"@type": "ImageObject", "url": "{BASE_URL}/favicon.svg"}}
        }},
        "about": {{
          "@type": "ChemicalSubstance",
          "name": {json.dumps(inci_name)}{f', "identifier": {json.dumps(cas)}' if cas else ''}{alternate_ld}
        }}
      }},
      {{
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
          {{"@type": "ListItem", "position": 1, "name": "Home", "item": "{BASE_URL}/"}},
          {{"@type": "ListItem", "position": 2, "name": {json.dumps(hub_name)}, "item": "{BASE_URL}/landing/{hub_file[:-5]}"}},
          {{"@type": "ListItem", "position": 3, "name": {json.dumps(inci_name)}, "item": "{BASE_URL}/landing/{filename[:-5]}"}}
        ]
      }}
    ]
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header class="page-header">
        <div class="container page-header-inner">
            <a href="/" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav class="page-nav">
                <a href="/#coverage" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Coverage</a>
                <a href="/landing/{hub_file[:-5]}" style="color: #38BDF8; text-decoration: none; font-size: 0.9rem;">{e(hub_name)}</a>
                <a href="/#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get INCIDB Complete — ${price}</a>
            </nav>
        </div>
    </header>

    <main class="container page-main" style="max-width: 900px;">
        <div class="crumbs">
            <a href="/" style="color: #64748B; text-decoration: none;">HOME</a> /
            <a href="/landing/{hub_file[:-5]}" style="color: #38BDF8; text-decoration: none;">{e(hub_name.upper())}</a> /
            <span translate="no" style="color: #F8FAFC;">{e(inci_name)}</span>
        </div>

        <div class="monograph-card">
            <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: flex-start; gap: 1rem; margin-bottom: 1.5rem;">
                <div>
                    <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Canonical INCI monograph</span>
                    <h1 translate="no" style="font-size: 2.2rem; line-height: 1.2; margin-top: 0.25rem; color: #F8FAFC;">{e(inci_name)}</h1>
                </div>
                <div style="display: flex; gap: 0.5rem; flex-wrap: wrap;">
                    {badges_html}
                </div>
            </div>

            {description_block}

            {ingredient_profile(ing, prod_list, names)}

            <div class="fact-grid">
{facts_html}
            </div>

            {regulatory_block(reg["allergens"], reg["status"])}
        </div>

        <div style="margin-bottom: 2.5rem;">
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem; color: #F8FAFC;">Sample products containing <span translate="no">{e(inci_name)}</span></h2>
            <p style="color: #94A3B8; font-size: 0.92rem; margin-bottom: 1.25rem;">Label positions from the free INCIDB sample. A lower position means the ingredient is declared earlier, i.e. present in a higher proportion.</p>

            <div style="background: #111318; border: 1px solid #232838; border-radius: 12px; overflow: hidden;">
                <table style="width: 100%; border-collapse: collapse; text-align: left; font-size: 0.92rem;">
                    <thead>
                        <tr style="background: #161922; border-bottom: 1px solid #232838; font-family: 'JetBrains Mono', monospace; font-size: 0.78rem; color: #64748B;">
                            <th style="padding: 0.85rem;">PRODUCT</th>
                            <th style="padding: 0.85rem;">LABEL POSITION</th>
                        </tr>
                    </thead>
                    <tbody>
                        {prod_rows}
                    </tbody>
                </table>
            </div>
        </div>

        <div class="query-card">
            <h3 style="font-size: 1.3rem; margin-bottom: 0.75rem; color: #F8FAFC;">Query <span translate="no">{e(inci_name)}</span> in the full snapshot</h3>
            <pre style="background: #0A0B0E; border: 1px solid #232838; padding: 1.25rem; border-radius: 8px; font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #38BDF8; overflow-x: auto; margin-bottom: 1.5rem;"><code>import pyarrow.parquet as pq

ingredients = pq.read_table('ingredients.parquet').to_pandas()
target = ingredients[ingredients['inci_name'] == {json.dumps(inci_name)}]
print(target[['ingredient_id', 'functions', 'cas_number', 'is_common_allergen']])</code></pre>
            <p style="color: #94A3B8; font-size: 0.88rem; margin-bottom: 1.25rem;">The complete snapshot covers {products_total} products. Coverage of each enrichment column is published, both per distinct name and weighted by label occurrence — see the <a href="/#coverage" style="color: #38BDF8;">coverage table</a>.</p>
            <div style="text-align: right;">
                <a href="{STRIPE_COMPLETE_LINK_PLACEHOLDER}" class="btn btn-primary" style="padding: 0.75rem 1.5rem; text-decoration: none;">Get INCIDB Complete — ${price} →</a>
            </div>
        </div>

        {related_html}
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB · snapshot {claims['snapshot']} · counts generated from the build report</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="/LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
            <p style="margin-top: 0.5rem; font-size: 0.78rem;">Product data © Open Beauty Facts contributors (ODbL v1.0). Ingredient enrichment contains data from the European Commission CosIng database.</p>
            <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(page)

    return filename


def hub_intro_html(hub_key, ing_list):
    """The hub's authored scope sentence plus counts read from its members."""
    e = html.escape
    n = len(ing_list)
    n_cas = sum(1 for i in ing_list if field(i['ingredient'], 'cas_number'))
    n_allergen = sum(1 for i in ing_list if is_flag(i['ingredient'], 'is_common_allergen'))
    n_comedo = sum(1 for i in ing_list if field(i['ingredient'], 'comedogenic_rating'))
    n_restricted = sum(1 for i in ing_list if field(i['ingredient'], 'cosing_restriction'))

    facts = [f"{n} ingredients from the free INCIDB sample whose recorded CosIng "
             f"<code>functions</code> place them here, {n_cas} of them with a CAS number in CosIng"]
    extras = []
    if n_restricted:
        extras.append(f"{n_restricted} " + ("carries" if n_restricted == 1 else "carry") + " a CosIng restriction")
    if n_allergen:
        extras.append(f"{n_allergen} " + ("is an Annex III fragrance allergen" if n_allergen == 1
                                          else "are Annex III fragrance allergens"))
    if n_comedo:
        extras.append(f"{n_comedo} " + ("has" if n_comedo == 1 else "have") + " an authored comedogenic grade")
    if extras:
        facts.append("; ".join(extras))
    facts_sentence = ". ".join(facts) + "."
    intro = HUB_INTROS.get(hub_key, "")
    intro_html = f"<span>{e(intro)}</span> " if intro else ""
    return (f'{intro_html}<span>{facts_sentence}</span> '
            '<span>Membership is read from the data, not assigned by hand — an ingredient '
            'with no CosIng function has no monograph, because there would be nothing to say about it.</span>')


def generate_hub(hub_key, hub_name, hub_file, ing_list, claims):
    e = html.escape
    filepath = os.path.join(LANDING_DIR, hub_file)
    price = claims['price_usd']

    cards = ""
    for item in sorted(ing_list, key=lambda i: field(i['ingredient'], 'inci_name')):
        ing = item['ingredient']
        inci = field(ing, 'inci_name')
        cas = field(ing, 'cas_number')
        functions = ", ".join(f.title() for f in function_list(ing))
        allergen = is_flag(ing, 'is_common_allergen')

        flag_tag = ('<span style="color: #F43F5E; font-size: 0.75rem; font-family: \'JetBrains Mono\', '
                    'monospace; font-weight: 600;">[Annex III]</span>') if allergen else ""
        cas_tag = (f'<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.75rem; '
                   f'color: #06B6D4;">CAS <span translate="no">{e(cas)}</span></span>') if cas else \
                  ('<span style="font-family: \'JetBrains Mono\', monospace; font-size: 0.75rem; '
                   'color: #475569;">no CAS in CosIng</span>')

        cards += f"""
        <a href="/landing/{item['filename'][:-5]}" style="display: block; background: #161922; border: 1px solid #232838; border-radius: 10px; padding: 1.25rem; text-decoration: none;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.35rem;">
                {cas_tag}
                {flag_tag}
            </div>
            <h3 translate="no" style="font-size: 1.05rem; color: #F8FAFC; margin-bottom: 0.35rem;">{e(inci)}</h3>
            <div translate="no" style="font-size: 0.8rem; color: #94A3B8;">{e(functions)}</div>
        </a>
        """

    # Title and description are budgeted the same way the monograph ones are
    # (`seo_common.fit_title` / `fit_desc`): the hub name is kept intact
    # whenever a shorter descriptor allows it, and the description's first
    # sentence states what the hub groups and how many monographs it holds.
    page_title = seo_common.fit_title(
        hub_name, [f"{len(ing_list)} INCI monographs", "INCI ingredient hub"], "INCIDB")
    meta_description = seo_common.fit_desc(
        f"{len(ing_list)} INCI monographs whose recorded CosIng functions place them under "
        f"{hub_name}. CAS numbers, functional categories and label occurrences, sourced from CosIng.")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{e(page_title)}</title>
    <meta name="description" content="{e(meta_description)}">
    <meta name="robots" content="index, follow">
    <link rel="canonical" href="{BASE_URL}/landing/{hub_file[:-5]}">
    <link rel="alternate" hreflang="en" href="{BASE_URL}/landing/{hub_file[:-5]}">
    <link rel="alternate" hreflang="x-default" href="{BASE_URL}/landing/{hub_file[:-5]}">

    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'">
    <noscript><link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300..800;1,300..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet"></noscript>
    <link rel="stylesheet" href="{CSS_HREF}">
    <style>{LAYOUT_CSS}
    </style>

    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "ItemList",
      "name": {json.dumps(hub_name)},
      "description": {json.dumps(f"INCI monographs whose recorded CosIng functions place them under {hub_name}.")},
      "numberOfItems": {len(ing_list)}
    }}
    </script>
</head>
<body style="background: #0A0B0E; color: #F8FAFC; font-family: 'Space Grotesk', -apple-system, sans-serif; min-height: 100vh; display: flex; flex-direction: column;">
    <div class="grid-overlay"></div>

    <header class="page-header">
        <div class="container page-header-inner">
            <a href="/" class="logo" style="font-weight: 700; font-size: 1.3rem; color: #F8FAFC; text-decoration: none;">INCIDB</a>
            <nav class="page-nav">
                <a href="/#coverage" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Coverage</a>
                <a href="/schema" style="color: #94A3B8; text-decoration: none; font-size: 0.9rem;">Schema</a>
                <a href="/#pricing" class="btn btn-primary" style="padding: 0.5rem 1rem; font-size: 0.85rem;">Get INCIDB Complete — ${price}</a>
            </nav>
        </div>
    </header>

    <main class="container page-main" style="max-width: 1100px;">
        <div class="crumbs">
            <a href="/" style="color: #64748B; text-decoration: none;">HOME</a> /
            <span style="color: #38BDF8;">{e(hub_name.upper())}</span>
        </div>

        <div style="text-align: center; max-width: 820px; margin: 0 auto 3rem auto;">
            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #06B6D4; text-transform: uppercase; letter-spacing: 1px;">Category hub</div>
            <h1 style="font-size: 2.5rem; margin-top: 0.35rem; color: #F8FAFC;">{e(hub_name)}</h1>
            <p style="color: #94A3B8; font-size: 1.02rem; margin-top: 0.75rem; line-height: 1.7; text-align: left;">{hub_intro_html(hub_key, ing_list)}</p>
        </div>

        <div class="hub-grid">
            {cards}
        </div>
    </main>

    <footer style="background: #111318; border-top: 1px solid #232838; padding: 2rem 0; text-align: center; font-size: 0.85rem; color: #64748B; margin-top: auto;">
        <div class="container">
            <p>INCIDB · snapshot {claims['snapshot']} · counts generated from the build report</p>
            <p style="margin-top: 0.5rem;"><a href="/schema" style="color: #38BDF8; text-decoration: none;">Schema Specification</a> · <a href="/LICENSE" style="color: #38BDF8; text-decoration: none;">License Terms</a> · <a href="/documentation" style="color: #38BDF8; text-decoration: none;">Documentation</a></p>
            <p style="margin-top: 0.5rem; font-size: 0.78rem;">Product data © Open Beauty Facts contributors (ODbL v1.0). Ingredient enrichment contains data from the European Commission CosIng database.</p>
            <div class="catalog-line" style="text-align:center; margin-top:14px; font-size:0.85rem; opacity:0.85;"><a href="https://dataengineered.io/">Part of the DataEngineered catalog →</a> · <a href="https://dataengineered.io/about">About</a> · <a href="https://dataengineered.io/terms">Terms</a> · <a href="https://dataengineered.io/privacy">Privacy</a> · <a href="https://dataengineered.io/refund-policy">Refund policy</a></div>
        </div>
    </footer>
</body>
</html>"""

    with open(filepath, mode='w', encoding='utf-8') as f:
        f.write(page)


def main():
    os.makedirs(LANDING_DIR, exist_ok=True)

    # Regenerating is authoritative: stale monographs from an earlier schema
    # must not survive as live URLs.
    for existing in os.listdir(LANDING_DIR):
        if existing.endswith(".html"):
            os.remove(os.path.join(LANDING_DIR, existing))

    claims = load_claims()
    ingredients, products, prod_ing = load_data()
    regulatory = load_regulatory()
    print(f"Loaded {len(ingredients)} sample ingredients and {len(products)} sample products.")
    cosing_names = load_cosing_names()
    if cosing_names:
        print(f"CosIng inventory: {len(cosing_names)} entries with name columns.")
    else:
        print(f"CosIng inventory not found at {COSING_INVENTORY_PATH}: monographs carry no other names.")

    hub_order = [hub_key for hub_key, _, _, _ in HUBS]
    hub_meta = {hub_key: (hub_name, hub_file) for hub_key, hub_name, hub_file, _ in HUBS}
    buckets = {hub_key: [] for hub_key in hub_order}
    skipped = 0

    # Pass 1: sort every ingredient into its hub bucket (filename computed up
    # front, page not written yet) so the related-ingredients block on each
    # monograph -- computed from its neighbours in the hub's sorted order --
    # can be built before that monograph's page is rendered.
    for ing in ingredients:
        hub_info = categorize_ingredient(function_list(ing))
        if hub_info is None:
            skipped += 1
            continue
        hub_key, hub_name, hub_file = hub_info
        buckets[hub_key].append({
            'ingredient': ing,
            'filename': monograph_filename(ing),
            'inci_name': field(ing, 'inci_name') or 'UNKNOWN INCI',
        })

    print(f"Skipped {skipped} ingredients with no publishable CosIng function.")
    assert_unique_filenames([m['ingredient'] for members in buckets.values() for m in members])

    # Sorted by INCI name -- the same order the hub page lists its cards in --
    # so "the two before and two after" means what a reader would expect.
    for hub_key in buckets:
        buckets[hub_key].sort(key=lambda m: m['inci_name'])

    sitemap_entries = [
        (BASE_URL + "/", os.path.join(ROOT_DIR, "index.html"), "weekly", "1.0"),
        (BASE_URL + "/schema", os.path.join(ROOT_DIR, "schema.html"), "monthly", "0.8"),
        (BASE_URL + "/documentation", os.path.join(ROOT_DIR, "documentation.html"), "monthly", "0.8"),
    ]
    if os.path.exists(os.path.join(ROOT_DIR, "stats", "index.html")):  # scripts/generate_stats.py -- citable, embeddable asset
        sitemap_entries.append((BASE_URL + "/stats/", os.path.join(ROOT_DIR, "stats", "index.html"), "monthly", "0.9"))

    # Pass 2: render every monograph, now that each hub's full sorted
    # membership is known.
    for hub_key in hub_order:
        hub_name, hub_file = hub_meta[hub_key]
        members = buckets[hub_key]
        for idx, member in enumerate(members):
            ing = member['ingredient']
            p_list = prod_ing.get(field(ing, 'ingredient_id'), [])
            related_members = related_neighbors(members, idx, hub_key, hub_order, buckets)
            filename = generate_monograph(ing, p_list, (hub_key, hub_name, hub_file), claims, related_members,
                                          cosing_names.get(field(ing, 'inci_name')),
                                          regulatory.get(field(ing, 'ingredient_id')))
            sitemap_entries.append(
                (f"{BASE_URL}/landing/{filename[:-5]}", os.path.join(LANDING_DIR, filename), "monthly", "0.8"))

    for hub_key in hub_order:
        hub_name, hub_file = hub_meta[hub_key]
        ing_list = buckets[hub_key]
        if not ing_list:
            print(f"Hub {hub_file} has no ingredients — not generated.")
            continue
        generate_hub(hub_key, hub_name, hub_file, ing_list, claims)
        sitemap_entries.append(
            (f"{BASE_URL}/landing/{hub_file[:-5]}", os.path.join(LANDING_DIR, hub_file), "weekly", "0.9"))
        print(f"Generated hub {hub_file} ({len(ing_list)} monographs)")

    n_urls = seo_common.write_sitemap(ROOT_DIR, sitemap_entries)
    print(f"Sitemap written to {SITEMAP_PATH} with {n_urls} entries.")


if __name__ == "__main__":
    main()
