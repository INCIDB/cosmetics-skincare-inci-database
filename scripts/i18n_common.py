#!/usr/bin/env python3
"""i18n_common.py — shared localizer for the DataEngineered static sites.

Copied verbatim into each site repo's scripts/ directory (the repos are independent).
Source of truth: <portfolio root>/scripts/i18n_common.py — edit there, then re-copy.
Plan: <portfolio root>/I18N_PLAN.md. Translator rules: <portfolio root>/scripts/i18n_style.md.

How it works
------------
English pages stay the only source of truth, hand-written or generated exactly as today.
This module reads the finished English HTML and:

1. cuts every page into translation *segments* — one per run of text + inline markup
   (a paragraph, a heading, a button label, a title/alt/meta attribute, a JSON-LD string).
   Inline elements become numbered tags (``<0>…</0>``), and three things become opaque
   placeholders (``{0}``) that a translation must carry through unchanged:
     * any token containing a digit (counts, prices, CAS numbers, years) — so no number
       ever lives in a translation catalog, and CLAIMS stay the only source of counts;
     * elements marked ``translate="no"`` (the HTML standard attribute) — generators put
       it on data values (ingredient names, product names, codes);
     * text that repeats the content of such an element elsewhere on the page (e.g. the
       same ingredient name inside <title> or JSON-LD).
   Identical segments across pages share one catalog entry (id = sha1 of the pattern).
2. looks each segment up in ``locales/<lang>.json`` and writes ``<lang>/<same path>``
   only when the page's translated share of words reaches ``min_coverage``; a page that
   falls short is simply not published in that language (never a half-English page).
3. rewrites internal links to the localized page when one exists, sets <html lang>,
   canonical, og:url/og:locale, adds a hidden ``lang`` field to forms, formats grouped
   numbers per locale, and marks JSON-LD with inLanguage.
4. injects a reciprocal hreflang block + a static language switcher into EVERY page
   (English in place, idempotently, between ``<!-- i18n:… -->`` markers), writes
   ``/i18n/i18n.js`` (a dismissible "also available in …" suggestion, no redirects),
   and rewrites the sitemap with every locale URL and xhtml:link alternates.

Commands (run from the site repo root, after the page generators):
  python scripts/i18n_common.py init  --base-url https://x.dataengineered.io
  python scripts/i18n_common.py extract            # segment report -> locales/_work/source.json
  python scripts/i18n_common.py todo  --lang es    # untranslated segments -> locales/_work/todo/
  python scripts/i18n_common.py merge --lang es FILE...   # validate + merge translations
  python scripts/i18n_common.py build              # write /<lang>/ pages, hreflang, sitemap
  python scripts/i18n_common.py check              # verify what build wrote (exit 1 on errors)

Config (i18n.config.json at the repo root):
  base_url      canonical origin, e.g. https://roasterdb.dataengineered.io
  locales       ["es", "de", "fr", "pt-br"]
  include       globs of the deployed English pages (explicit beats "**/*.html")
  exclude       globs/paths to leave English-only (e.g. legal pages)
  not_found     the 404 page (localized, but never in hreflang or the sitemap)
  sitemap       sitemap file rewritten with locale URLs + alternates
  min_coverage  share of a page's words that must be translated to publish it (0.9)
  notranslate   CSS selectors treated as translate="no" when the generator can't mark data

Page scripts that set UI text at runtime read it from a string table the tool translates:
  <script type="application/json" id="i18n-strings" data-i18n>{"sending": "Sending…"}</script>

Requires beautifulsoup4.
"""

import argparse
import collections
import copy
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit, urlunsplit

try:
    from bs4 import BeautifulSoup, NavigableString, Tag
    from bs4.element import Script
except ImportError:  # pragma: no cover
    sys.exit("i18n_common.py needs beautifulsoup4:  pip install beautifulsoup4")

VERSION = "3"
CONFIG_NAME = "i18n.config.json"
MARKER_NAME = "_i18n-generated.txt"
PAGES_FILE_LIMIT = 20_000  # Cloudflare Pages: max files per deployment

# ---------------------------------------------------------------------------
# Locales
# ---------------------------------------------------------------------------

LOCALES = {
    "en": dict(hreflang="en", html="en", og="en_US", name="English", label="Language", group=",", dec="."),
    "es": dict(hreflang="es", html="es", og="es_ES", name="Español", label="Idioma", group=".", dec=","),
    "de": dict(hreflang="de", html="de", og="de_DE", name="Deutsch", label="Sprache", group=".", dec=","),
    "fr": dict(hreflang="fr", html="fr", og="fr_FR", name="Français", label="Langue", group="\u202f", dec=","),
    "pt-br": dict(hreflang="pt-BR", html="pt-BR", og="pt_BR", name="Português", label="Idioma", group=".", dec=","),
    # wave-2 candidates (I18N_PLAN.md §1) — defined so adding one is a config change only
    "it": dict(hreflang="it", html="it", og="it_IT", name="Italiano", label="Lingua", group=".", dec=","),
    "nl": dict(hreflang="nl", html="nl", og="nl_NL", name="Nederlands", label="Taal", group=".", dec=","),
    "id": dict(hreflang="id", html="id", og="id_ID", name="Bahasa Indonesia", label="Bahasa", group=".", dec=","),
    "tr": dict(hreflang="tr", html="tr", og="tr_TR", name="Türkçe", label="Dil", group=".", dec=","),
    "pl": dict(hreflang="pl", html="pl", og="pl_PL", name="Polski", label="Język", group="\u00a0", dec=","),
    "ja": dict(hreflang="ja", html="ja", og="ja_JP", name="日本語", label="言語", group=",", dec="."),
    "ko": dict(hreflang="ko", html="ko", og="ko_KR", name="한국어", label="언어", group=",", dec="."),
    "zh-tw": dict(hreflang="zh-TW", html="zh-TW", og="zh_TW", name="繁體中文", label="語言", group=",", dec="."),
}
SOURCE = "en"

# Tokens that are the same in every language. A segment whose words are ALL in this set
# (plus the repo's locales/glossary.json "keep" list) needs no translation.
KEEP_BASE = {
    "DataEngineered", "INCIDB", "RoasterDB", "SuppDB", "FloraDB", "MechanicDB", "WhiskyDB",
    "RecallDB", "WineDB", "ApplianceDB", "CSA", "CSV", "Parquet", "SQLite", "JSON", "JSONL",
    "API", "SQL", "Python", "pandas", "DuckDB", "Kaggle", "GitHub", "Stripe", "CosIng", "INCI",
    "CAS", "OBD-II", "DTC", "SAE", "OEM", "CPSC", "FDA", "FSIS", "NHTSA", "USCG", "USDA", "ODbL",
    "CC0", "Apify", "README", "ZIP", "SKU", "GTIN", "UPC", "EAN", "LLM", "PubChem", "Wikidata",
    "iNaturalist", "GBIF", "EDGAR", "SEC", "HTTPS", "URL", "ID", "PDF", "USD", "EUR", "Email",
}

# ---------------------------------------------------------------------------
# Segmentation
# ---------------------------------------------------------------------------

SKIP_TAGS = {"script", "style", "noscript", "pre", "textarea", "svg", "math", "template",
             "iframe", "object", "canvas", "video", "audio"}
INLINE_TAGS = {"a", "abbr", "b", "bdi", "bdo", "cite", "data", "dfn", "em", "i", "mark", "q",
               "s", "small", "span", "strong", "sub", "sup", "time", "u", "del", "ins", "font",
               "label", "output"}
OPAQUE_TAGS = {"br", "img", "code", "kbd", "samp", "var", "wbr", "input", "svg", "picture",
               "math", "meter", "progress"}
TRANSLATABLE_ATTRS = ("title", "alt", "placeholder", "aria-label", "aria-description")
META_NAMES = {"description", "twitter:title", "twitter:description", "twitter:image:alt"}
META_PROPS = {"og:title", "og:description", "og:site_name", "og:image:alt"}
JSONLD_KEYS = {"name", "description", "headline", "alternativeHeadline", "text", "caption",
               "abstract", "disambiguatingDescription", "keywords", "articleSection"}
JSONLD_NAME_OPAQUE_TYPES = {"Organization", "Brand", "Person", "ChemicalSubstance",
                            "ImageObject", "Corporation", "ContactPoint"}
JSONLD_LANG_TYPES = {"WebPage", "WebSite", "TechArticle", "Article", "BlogPosting", "Dataset",
                     "FAQPage", "ItemList", "CollectionPage", "AboutPage", "ContactPage",
                     "HowTo", "DefinedTermSet"}
LINK_ATTRS = ("href", "src", "action", "poster", "data-src", "xlink:href")

TOKEN_RE = re.compile(r"<(\d+)>|</(\d+)>|\{(\d+)\}")
DIGIT_TOKEN_RE = re.compile(r"[^\s<>{}]*\d[^\s<>{}]*")
# a plain number (optionally $/€ prefixed, grouped, decimal, %) followed by "-word" suffixes
NUM_SUFFIX_RE = re.compile(r"([$€£]?\d[\d,.]*%?)(?=(?:-[^\W\d_]+)+$)")
WORD_RE = re.compile(r"[^\W\d_][\w'’.+-]*")
ENTITY_RE = re.compile(r"&#?\w+;")
LEAD_PUNCT = "([«\"'“‘"
TRAIL_PUNCT = ".,;:!?)]»\"'”’"


def is_text(node):
    return type(node) is NavigableString


def notranslate(tag):
    return (tag.get("translate", "").lower() == "no"
            or "notranslate" in (tag.get("class") or [])
            or tag.has_attr("data-i18n-skip"))


def pure_inline(tag):
    """True when tag holds only text, inline and opaque elements (no block content)."""
    for child in tag.children:
        if isinstance(child, Tag):
            if child.name in OPAQUE_TAGS or notranslate(child):
                continue
            if child.name not in INLINE_TAGS or not pure_inline(child):
                return False
    return True


def has_words(s):
    return bool(WORD_RE.search(s))


def iter_runs(el):
    """Yield lists of sibling nodes that form one translatable run of text."""
    run = []

    def flush():
        nonlocal run
        out, run = run, []
        if not out:
            return
        direct = "".join(str(n) for n in out if is_text(n))
        if has_words(direct):
            yield out
            return
        # Only elements separated by whitespace/punctuation (a nav bar, a breadcrumb):
        # translate each element on its own so segments stay reusable across pages.
        for n in out:
            if isinstance(n, Tag) and n.name not in OPAQUE_TAGS and not notranslate(n):
                yield from iter_runs(n)

    for child in list(el.children):
        if isinstance(child, NavigableString):
            if is_text(child):
                run.append(child)
            else:  # comment, doctype, CDATA: break the run
                yield from flush()
            continue
        if not isinstance(child, Tag):
            continue
        name = child.name
        if name in SKIP_TAGS:
            yield from flush()
            continue
        if name in OPAQUE_TAGS or (notranslate(child) and name in INLINE_TAGS):
            run.append(child)
            continue
        if notranslate(child):
            yield from flush()
            continue
        if name in INLINE_TAGS and pure_inline(child):
            run.append(child)
            continue
        yield from flush()
        yield from iter_runs(child)
    yield from flush()


def _escape_text(s):
    return html.escape(s, quote=False).replace("{", "&#123;").replace("}", "&#125;")


class Protector:
    """Replaces page data (translate="no" texts) and digit tokens with placeholders."""

    def __init__(self, protected, copy_texts=()):
        items = sorted({p for p in protected if len(p) >= 3 and has_words(p) and len(p) <= 120},
                       key=len, reverse=True)
        self.rx = (re.compile("|".join(r"(?<!\w)" + re.escape(p) + r"(?!\w)" for p in items))
                   if items else None)
        # Where a string repeats translatable body copy verbatim (a hub name inside <title>),
        # that region is copy, not data: protected matches inside it are ignored — e.g. a card's
        # "Fragrance, Perfuming" must not eat into "Fragrance, Perfuming & Colorant Agents".
        copies = sorted({c for c in copy_texts if len(c) >= 8}, key=len, reverse=True)
        self.copy_rx = (re.compile("|".join(re.escape(c) for c in copies))
                        if copies and self.rx else None)

    def text(self, s, mapping):
        s = re.sub(r"\s+", " ", s)
        spans = []
        if self.rx:
            copy_spans = [(m.start(), m.end()) for m in self.copy_rx.finditer(s)] if self.copy_rx else []
            spans += [(m.start(), m.end()) for m in self.rx.finditer(s)
                      if not any(a <= m.start() and m.end() <= b for a, b in copy_spans)]
        digits = []
        for m in DIGIT_TOKEN_RE.finditer(s):
            a, b = m.start(), m.end()
            while a < b and s[a] in LEAD_PUNCT:
                a += 1
            while b > a and s[b - 1] in TRAIL_PUNCT:
                b -= 1
            # "55,426-row", "5-table", "1-indexed": the number is data, the word is copy
            m2 = NUM_SUFFIX_RE.match(s, a, b)
            if m2 and m2.end() < b and m2.end(1) == m2.end():
                b = m2.end()
            if a < b and any(ch.isdigit() for ch in s[a:b]):
                if not any(x < b and a < y for x, y in spans):
                    digits.append([a, b])
        # adjacent numeric tokens joined only by punctuation/space ("64-02-8 --- 6381-92-6",
        # "7-5, 8-4") are one value: one placeholder keeps segments from multiplying
        merged = []
        for d in digits:
            if merged and re.fullmatch(r"[\s\-–—/,;:·|+]{1,5}", s[merged[-1][1]:d[0]]):
                merged[-1][1] = d[1]
            else:
                merged.append(d)
        spans += [tuple(d) for d in merged]
        spans.sort()
        out, pos = [], 0
        for a, b in spans:
            out.append(_escape_text(s[pos:a]))
            out.append("{%d}" % len(mapping))
            mapping.append(s[a:b])
            pos = b
        out.append(_escape_text(s[pos:]))
        return "".join(out)


def build_run_pattern(nodes, prot):
    mapping = []

    def ser(ns):
        parts = []
        for n in ns:
            if is_text(n):
                parts.append(prot.text(str(n), mapping))
            elif isinstance(n, Tag):
                idx = len(mapping)
                mapping.append(n)
                if n.name in OPAQUE_TAGS or notranslate(n) or not n.contents:
                    parts.append("{%d}" % idx)
                else:
                    parts.append("<%d>%s</%d>" % (idx, ser(list(n.children)), idx))
        return "".join(parts)

    pattern = re.sub(r" {2,}", " ", ser(nodes)).strip()
    return pattern, mapping


def pattern_words(pattern):
    return len(WORD_RE.findall(html.unescape(ENTITY_RE.sub(" ", TOKEN_RE.sub(" ", pattern)))))


def seg_id(pattern):
    return hashlib.sha1(pattern.encode("utf-8")).hexdigest()[:16]


class Segment:
    __slots__ = ("kind", "pattern", "mapping", "words", "ref", "id")

    def __init__(self, kind, pattern, mapping, ref):
        self.kind, self.pattern, self.mapping, self.ref = kind, pattern, mapping, ref
        self.words = pattern_words(pattern)
        self.id = seg_id(pattern)


def _jsonld_walk(node, parent_type, visit):
    if isinstance(node, list):
        for i, v in enumerate(node):
            if isinstance(v, (dict, list)):
                _jsonld_walk(v, parent_type, visit)
        return
    if not isinstance(node, dict):
        return
    t = node.get("@type")
    types = set(t) if isinstance(t, list) else {t}
    for k, v in list(node.items()):
        if isinstance(v, (dict, list)) and k != "keywords":
            _jsonld_walk(v, types, visit)
        elif k in JSONLD_KEYS:
            if k == "name" and types & JSONLD_NAME_OPAQUE_TYPES:
                continue
            if isinstance(v, str):
                visit(node, k)
            elif k == "keywords" and isinstance(v, list):
                for i, kw in enumerate(v):
                    if isinstance(kw, str):
                        visit(v, i)


def collect_segments(soup):
    """All translatable segments of a parsed page, plus JSON-LD documents to re-serialize.

    Body text relies on explicit markup: data carries translate="no" and becomes {n}.
    <title>, attributes and JSON-LD cannot carry markup, so there the texts of this page's
    translate="no" elements are replaced by placeholders wherever they occur verbatim.
    """
    protected = set()
    for tag in soup.find_all(True):
        if notranslate(tag) and "i18n-switch" not in (tag.get("class") or []):
            txt = re.sub(r"\s+", " ", tag.get_text()).strip()
            if txt:
                protected.add(txt)
    runs = list(iter_runs(soup))

    def visible(nodes):
        out = []
        for n in nodes:
            if is_text(n):
                out.append(str(n))
            elif isinstance(n, Tag) and n.name not in OPAQUE_TAGS and not notranslate(n):
                out.append(visible(list(n.children)))
        return "".join(out)

    copy_texts = [re.sub(r"\s+", " ", visible(r)).strip() for r in runs
                  if not (r[0].parent is not None and r[0].parent.name == "title")]
    prot = Protector(protected, copy_texts)
    prot_digits = Protector(())
    segs, jsonld_docs = [], []

    def in_skip(tag):
        # a <textarea>'s *content* is user input (skipped), but its placeholder/title/aria
        # attributes are site copy — so SKIP_TAGS applies to the tag itself except textarea
        if notranslate(tag) or (tag.name in SKIP_TAGS and tag.name != "textarea"):
            return True
        for p in tag.parents:
            if isinstance(p, Tag) and (p.name in SKIP_TAGS or notranslate(p)):
                return True
        return False

    # attributes first (apply order matters: text runs clone tags with their attributes)
    for tag in soup.find_all(True):
        if in_skip(tag):
            continue
        attrs = list(TRANSLATABLE_ATTRS)
        if tag.name == "input" and (tag.get("type") or "").lower() in ("submit", "button", "reset"):
            attrs.append("value")
        if tag.name == "meta":
            nm, pr = (tag.get("name") or "").lower(), (tag.get("property") or "").lower()
            if nm in META_NAMES or pr in META_PROPS:
                attrs.append("content")
        for a in attrs:
            v = tag.get(a)
            if isinstance(v, str) and has_words(v):
                mapping = []
                pat = prot.text(v, mapping).strip()
                if pattern_words(pat):
                    segs.append(Segment("attr", pat, mapping, (tag, a)))

    def visit(container, key):
        v = container[key]
        mapping = []
        pat = prot.text(v, mapping).strip()
        if pattern_words(pat):
            segs.append(Segment("jsonld", pat, mapping, (container, key)))

    for script in soup.find_all("script"):
        stype = (script.get("type") or "").lower()
        is_ld = stype == "application/ld+json"
        # <script type="application/json" data-i18n>{"key": "English UI string"}</script>:
        # the string table page scripts read runtime messages from (every string value)
        is_strings = stype == "application/json" and script.has_attr("data-i18n")
        if not (is_ld or is_strings):
            continue
        try:
            data = json.loads(script.string or "")
        except (ValueError, TypeError):
            continue
        jsonld_docs.append({"script": script, "data": data, "strings": is_strings})
        if is_ld:
            _jsonld_walk(data, set(), visit)
        else:
            def walk_all(node):
                items = node.items() if isinstance(node, dict) else enumerate(node)
                for k, v in list(items):
                    if isinstance(k, str) and k.startswith("_"):
                        continue
                    if isinstance(v, str):
                        visit(node, k)
                    elif isinstance(v, (dict, list)):
                        walk_all(v)
            if isinstance(data, (dict, list)):
                walk_all(data)

    for run in runs:
        parent = run[0].parent
        in_title = parent is not None and parent.name == "title"
        pattern, mapping = build_run_pattern(run, prot if in_title else prot_digits)
        if not pattern_words(pattern):
            continue
        first, last = run[0], run[-1]
        lead = re.match(r"\s*", str(first)).group(0) if is_text(first) else ""
        trail = re.search(r"\s*$", str(last)).group(0) if is_text(last) else ""
        segs.append(Segment("text", pattern, mapping, (run, lead, trail)))
    return segs, jsonld_docs


# ---------------------------------------------------------------------------
# Translation lookup / validation / rendering
# ---------------------------------------------------------------------------

def validate_translation(src, t):
    """'' when t is a usable translation of src, else the reason it is not."""
    if not isinstance(t, str) or not t.strip():
        return "empty"
    a = collections.Counter(m.group(0) for m in TOKEN_RE.finditer(src))
    b = collections.Counter(m.group(0) for m in TOKEN_RE.finditer(t))
    if a != b:
        return "placeholder/tag mismatch: expected %s, got %s" % (sorted(a), sorted(b))
    stack = []
    for m in TOKEN_RE.finditer(t):
        if m.group(1) is not None:
            stack.append(m.group(1))
        elif m.group(2) is not None:
            if not stack or stack.pop() != m.group(2):
                return "tags not properly nested"
    if stack:
        return "unclosed tag"
    if re.search(r"&amp;(?:amp|lt|gt|quot|#\d+);", t) and not re.search(r"&amp;(?:amp|lt|gt|quot|#\d+);", src):
        return "double-escaped entity (write &amp; not &amp;amp;)"
    rest = ENTITY_RE.sub("", TOKEN_RE.sub("", t))
    if re.search(r"\d", rest):
        return "literal digit outside a placeholder (numbers must stay in {n})"
    if re.search(r"[{}<>]", rest):
        return "stray { } < or > (escape as &#123; &#125; &lt; &gt;)"
    return ""


def auto_identity(pattern, keep):
    words = WORD_RE.findall(html.unescape(ENTITY_RE.sub(" ", TOKEN_RE.sub(" ", pattern))))
    return bool(words) and all(w.strip(".-'’") in keep for w in words)


def localize_number(tok, loc):
    L = LOCALES[loc]
    if loc == SOURCE:
        return tok

    def grp(m):
        s = m.group(1).replace(",", L["group"])
        return s + (L["dec"] + m.group(2) if m.group(2) else "")

    out = re.sub(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+)(?:\.(\d+))?(?![\d,])", grp, tok)
    if out == tok:
        out = re.sub(r"^(\d+)\.(\d+)%$", lambda m: m.group(1) + L["dec"] + m.group(2) + "%", tok)
    return out


THOUSANDS_IN_TEXT_RE = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+)(?:\.(\d+))?(?![\d,]|\.\d)")
PERCENT_IN_TEXT_RE = re.compile(r"(?<![\w.,])(\d+)\.(\d+)%")


def localize_numbers_in_text(s, loc):
    """Grouped thousands and decimal percentages in free text, per locale (idempotent)."""
    L = LOCALES[loc]
    if loc == SOURCE:
        return s
    s = THOUSANDS_IN_TEXT_RE.sub(
        lambda m: m.group(1).replace(",", L["group"]) + (L["dec"] + m.group(2) if m.group(2) else ""), s)
    return PERCENT_IN_TEXT_RE.sub(lambda m: m.group(1) + L["dec"] + m.group(2) + "%", s)


# Localized pages only: German/French/Spanish text is longer; let table cells and headings
# wrap instead of pushing the layout wider than a phone screen. Hyphenation follows <html lang>.
LOCALIZED_CSS = ("<style>th,td{overflow-wrap:anywhere;hyphens:auto}"
                 "h1,h2,h3,h4,button,.btn{overflow-wrap:break-word}</style>")


def render_pattern(soup, pattern, mapping, loc):
    stack = [(None, [])]
    pos = 0
    for m in TOKEN_RE.finditer(pattern):
        text = pattern[pos:m.start()]
        if text:
            stack[-1][1].append(NavigableString(html.unescape(text)))
        pos = m.end()
        if m.group(1) is not None:
            stack.append((int(m.group(1)), []))
        elif m.group(2) is not None:
            idx, kids = stack.pop()
            orig = mapping[idx]
            new = soup.new_tag(orig.name, attrs=copy.deepcopy(dict(orig.attrs)))
            for k in kids:
                new.append(k)
            stack[-1][1].append(new)
        else:
            orig = mapping[int(m.group(3))]
            if isinstance(orig, str):
                stack[-1][1].append(NavigableString(localize_number(orig, loc)))
            else:
                stack[-1][1].append(copy.copy(orig))
    if pattern[pos:]:
        stack[-1][1].append(NavigableString(html.unescape(pattern[pos:])))
    return stack[0][1]


def render_plain(pattern, mapping, loc):
    def sub(m):
        v = mapping[int(m.group(3))]
        return localize_number(v, loc)
    return html.unescape(TOKEN_RE.sub(lambda m: sub(m) if m.group(3) is not None else "", pattern))


# ---------------------------------------------------------------------------
# Site model
# ---------------------------------------------------------------------------

def clean_path(rel):
    p = "/" + rel
    if p.endswith("/index.html"):
        return p[: -len("index.html")]
    if p.endswith(".html"):
        return p[:-5]
    return p


class Site:
    def __init__(self, root):
        self.root = Path(root).resolve()
        cfg_path = self.root / CONFIG_NAME
        if not cfg_path.exists():
            sys.exit(f"{CONFIG_NAME} not found in {self.root} — run `init` first")
        self.cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
        self.base = self.cfg["base_url"].rstrip("/")
        self.host = urlsplit(self.base).netloc
        self.locales = [lg for lg in self.cfg.get("locales", []) if lg != SOURCE]
        unknown = [lg for lg in self.locales if lg not in LOCALES]
        if unknown:
            sys.exit(f"unknown locale(s) {unknown}; known: {sorted(LOCALES)}")
        self.min_cov = float(self.cfg.get("min_coverage", 0.9))
        self.not_found = self.cfg.get("not_found", "404.html")
        self.sitemap = self.cfg.get("sitemap", "sitemap.xml")
        self.pages = self._discover()
        self.page_set = set(self.pages)
        self.page_langs = {}
        keep = set(KEEP_BASE)
        gpath = self.root / "locales" / "glossary.json"
        if gpath.exists():
            keep |= set(json.loads(gpath.read_text(encoding="utf-8")).get("keep", []))
        self.keep = keep

    def _discover(self):
        excluded_dirs = set(LOCALES) | {".git", "node_modules", "venv", ".venv", "i18n", "locales",
                                        "__pycache__", ".wrangler"}
        found = set()
        for pat in self.cfg.get("include", ["**/*.html"]):
            for p in self.root.glob(pat):
                if not p.is_file() or p.suffix.lower() != ".html":
                    continue
                rel = p.relative_to(self.root).as_posix()
                if rel.split("/")[0] in excluded_dirs:
                    continue
                found.add(rel)
        for pat in self.cfg.get("exclude", []):
            found -= {r for r in found if Path(r).match(pat) or r == pat}
        return sorted(found)

    def url_path(self, rel, lang):
        cp = clean_path(rel)
        return cp if lang == SOURCE else f"/{lang}{cp}"

    def url(self, rel, lang):
        return self.base + self.url_path(rel, lang)

    def url_to_page(self, path):
        path = unquote(path or "/")
        if not path.startswith("/"):
            return None
        cands = [path + "index.html"] if path.endswith("/") else (
            [path] if path.endswith(".html") else [path + ".html", path + "/index.html"])
        for c in cands:
            rel = c.lstrip("/")
            if rel in self.page_set:
                return rel
        return None

    def catalog_path(self, lang):
        return self.root / "locales" / f"{lang}.json"

    def load_catalog(self, lang):
        p = self.catalog_path(lang)
        if not p.exists():
            return {}
        raw = json.loads(p.read_text(encoding="utf-8"))
        return {k: v for k, v in raw.items() if not k.startswith("_")}

    def read(self, rel):
        return (self.root / rel).read_text(encoding="utf-8")


def parse(text, site=None):
    soup = BeautifulSoup(strip_blocks(text), "html.parser")
    # config "notranslate": CSS selectors treated as translate="no" (data the generator does
    # not mark itself). Applied to the parse only — English files are never modified by it.
    if site is not None:
        for sel in site.cfg.get("notranslate", []):
            for tag in soup.select(sel):
                tag["translate"] = "no"
    return soup


def lookup(seg, catalog, keep):
    entry = catalog.get(seg.id)
    if entry and entry.get("src") == seg.pattern and not validate_translation(seg.pattern, entry.get("t")):
        return entry["t"]
    if auto_identity(seg.pattern, keep):
        return seg.pattern
    return None


def coverage(segs, catalog, keep):
    total = sum(s.words for s in segs)
    if not total:
        return 1.0, True
    done = sum(s.words for s in segs if lookup(s, catalog, keep) is not None)
    title_ok = all(lookup(s, catalog, keep) is not None for s in segs
                   if s.kind == "text" and s.ref[0][0].parent is not None
                   and s.ref[0][0].parent.name == "title")
    return done / total, title_ok


# ---------------------------------------------------------------------------
# HTML text injection (English in place + localized copies)
# ---------------------------------------------------------------------------

BLOCK_RE = re.compile(r"[ \t]*<!-- i18n:alternates -->.*?<!-- /i18n:alternates -->[ \t]*(?:\r?\n)?"
                      r"|<!-- i18n:(switcher|header) -->.*?<!-- /i18n:\1 -->", re.S)

# Header language menu: a <details> dropdown (works without JS; i18n.js only closes it on an
# outside click / Escape). Placement, first match wins:
#   1. config "header_switcher": [{"selector": css, "position": append|after|before|row|float}]
#   2. the header's nav (nav, .nav-links, .navlinks, .bar-nav)  -> appended as its last item
#   3. the last link container of the header row                -> appended as its last item
#   4. the header row itself                                    -> appended, pushed right
#   5. no header at all                                         -> floating, top-right of the page
HEADER_ROOTS = "header, .header-bar, .site-nav"
HEADER_NAVS = "nav, .nav-links, .navlinks, .bar-nav"
HEADER_CSS = (
    "<style>"
    ".i18n-menu{position:relative;display:inline-block;align-self:center;font-size:.85rem;line-height:1;"
    "font-weight:500;text-transform:none;letter-spacing:normal}"
    ".i18n-menu.i18n-menu>summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;"
    "gap:.35rem;padding:.4rem .65rem;border:1px solid currentColor;"
    "border-color:color-mix(in srgb,currentColor 40%,transparent);border-radius:999px;white-space:nowrap;"
    "user-select:none;color:inherit;background:transparent}"
    ".i18n-menu>summary::-webkit-details-marker{display:none}"
    ".i18n-menu>summary:focus-visible{outline:2px solid #93c5fd;outline-offset:2px}"
    ".i18n-menu.i18n-menu>ul{display:block;position:absolute;right:0;top:calc(100% + 6px);z-index:2147482000;"
    "min-width:10rem;margin:0;padding:.35rem;list-style:none;background:#111827;border:1px solid #374151;"
    "border-radius:10px;box-shadow:0 10px 24px rgba(0,0,0,.35);text-align:left}"
    ".i18n-menu.i18n-menu li{display:block;margin:0;padding:0;list-style:none}"
    ".i18n-menu.i18n-menu li>a,.i18n-menu.i18n-menu li>span{display:block;padding:.5rem .75rem;"
    "border-radius:6px;color:#f9fafb;background:transparent;text-decoration:none;white-space:nowrap;"
    "font-size:.9rem;font-weight:400;line-height:1.2;border:0;box-shadow:none}"
    ".i18n-menu.i18n-menu li>a:hover,.i18n-menu.i18n-menu li>a:focus-visible{background:#1f2937;color:#fff}"
    ".i18n-menu.i18n-menu li>span{font-weight:600;color:#93c5fd}"
    ".i18n-menu--row{margin-left:auto}"
    ":is(nav,a,button):has(+ .i18n-menu--row){margin-left:auto}"
    ":is(nav,a,button):has(+ .i18n-menu--row)+.i18n-menu--row{margin-left:.75rem}"
    ".i18n-menu--float{position:absolute;top:14px;right:16px;z-index:2147481000;color:#e5e7eb}"
    "</style>"
)
GLOBE_SVG = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
             'stroke-width="2" stroke-linecap="round" aria-hidden="true" focusable="false">'
             '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/>'
             '<path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>'
             '</svg>')
HREFLANG_RE = re.compile(r"[ \t]*<link\b[^>]*\bhreflang\s*=[^>]*>[ \t]*(?:\r?\n)?", re.I)
CANON_RE = re.compile(r"([ \t]*)<link\b[^>]*\brel\s*=\s*[\"']?canonical[\"']?[^>]*>[ \t]*(\r?\n)?", re.I)


def strip_blocks(text):
    return BLOCK_RE.sub("", text)


def ordered_langs(site, langs):
    return [lg for lg in [SOURCE] + site.locales if lg in langs]


def alternates_block(site, rel, langs, cur, has_og_locale, nl, indent):
    lines = ["<!-- i18n:alternates -->"]
    for lg in ordered_langs(site, langs):
        lines.append(f'<link rel="alternate" hreflang="{LOCALES[lg]["hreflang"]}" href="{site.url(rel, lg)}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{site.url(rel, SOURCE)}">')
    if cur != SOURCE:
        lines.append(LOCALIZED_CSS)
    if len(langs) > 1:
        lines.append(HEADER_CSS)
        if not has_og_locale:
            lines.append(f'<meta property="og:locale" content="{LOCALES[cur]["og"]}">')
        for lg in ordered_langs(site, langs):
            if lg != cur:
                lines.append(f'<meta property="og:locale:alternate" content="{LOCALES[lg]["og"]}">')
        lines.append(f'<script src="/i18n/i18n.js?v={VERSION}" defer></script>')
    lines.append("<!-- /i18n:alternates -->")
    return "".join(indent + line + nl for line in lines)


def switcher_html(site, rel, langs, cur):
    items = []
    for lg in ordered_langs(site, langs):
        L = LOCALES[lg]
        if lg == cur:
            items.append(f'<span aria-current="true" style="font-weight:600">{html.escape(L["name"])}</span>')
        else:
            items.append(f'<a href="{site.url_path(rel, lg)}" hreflang="{L["hreflang"]}" lang="{L["html"]}" '
                         f'data-i18n-lang="{lg}">{html.escape(L["name"])}</a>')
    return ("<!-- i18n:switcher --><nav class=\"i18n-switch\" translate=\"no\" "
            f"aria-label=\"{html.escape(LOCALES[cur]['label'])}\" "
            "style=\"text-align:center;margin:14px auto;font-size:0.85rem;opacity:0.85;\">"
            + " · ".join(items) + "</nav><!-- /i18n:switcher -->")


def header_menu_html(site, rel, langs, cur, variant):
    L = LOCALES[cur]
    items = []
    for lg in ordered_langs(site, langs):
        M = LOCALES[lg]
        if lg == cur:
            items.append(f'<li><span aria-current="true" lang="{M["html"]}">{html.escape(M["name"])}</span></li>')
        else:
            items.append(f'<li><a href="{site.url_path(rel, lg)}" hreflang="{M["hreflang"]}" lang="{M["html"]}" '
                         f'data-i18n-lang="{lg}">{html.escape(M["name"])}</a></li>')
    short = "中文" if cur.startswith("zh") else cur.split("-")[0].upper()
    label = html.escape(f'{L["label"]}: {L["name"]}')
    return (f'<!-- i18n:header --><details class="i18n-menu i18n-menu--{variant}" translate="no">'
            f'<summary aria-label="{label}" title="{label}">{GLOBE_SVG}<span>{short}</span></summary>'
            f'<ul>{"".join(items)}</ul></details><!-- /i18n:header -->')


def _element_span(text, start, name):
    """(start, close_start, close_end) of the element whose start tag begins at `start`."""
    rx = re.compile(r"<(/?)" + re.escape(name) + r"(?=[\s>/])[^>]*>", re.I)
    depth = 0
    for m in rx.finditer(text, start):
        if m.group(1):
            depth -= 1
            if depth == 0:
                return start, m.start(), m.end()
        elif not m.group(0).endswith("/>"):
            depth += 1
    return None


def header_target(soup, site):
    for rule in site.cfg.get("header_switcher", []):
        t = soup.select_one(rule["selector"])
        if t is not None:
            return t, rule.get("position", "append")
    root = soup.select_one(HEADER_ROOTS)
    if root is None:
        return None, "float"
    nav = root.select_one(HEADER_NAVS)
    if nav is not None:
        return nav, "append"
    row = root
    while True:
        kids = [c for c in row.children if isinstance(c, Tag) and c.name not in ("script", "style")]
        if len(kids) == 1 and kids[0].name not in ("a", "button", "img", "svg"):
            row = kids[0]
            continue
        break
    if len(kids) > 1 and kids[-1].name in ("div", "span", "ul", "p") and kids[-1].find("a") is not None:
        return kids[-1], "append"
    return row, "row"


def insert_header_menu(text, site, rel, langs, cur):
    """Insert the header language menu into (block-stripped) page text; unchanged if no safe spot."""
    soup = BeautifulSoup(text, "html.parser")
    target, position = header_target(soup, site)
    starts = [0] + [m.end() for m in re.finditer("\n", text)]
    if position == "float" or target is None:
        body = soup.body
        if body is None or body.sourceline is None:
            return text
        off = starts[body.sourceline - 1] + body.sourcepos
        end = text.find(">", off)
        if end < 0:
            return text
        menu = header_menu_html(site, rel, langs, cur, "float")
        return text[:end + 1] + menu + text[end + 1:]
    if target.sourceline is None:
        return text
    off = starts[target.sourceline - 1] + target.sourcepos
    if not text[off:off + len(target.name) + 1].lower() == "<" + target.name:
        return text  # position mismatch: never guess
    span = _element_span(text, off, target.name)
    if span is None:
        return text
    start, close_start, close_end = span
    if position == "append":
        return text[:close_start] + header_menu_html(site, rel, langs, cur, "nav") + text[close_start:]
    if position == "row":
        return text[:close_start] + header_menu_html(site, rel, langs, cur, "row") + text[close_start:]
    if position == "after":
        return text[:close_end] + header_menu_html(site, rel, langs, cur, "row") + text[close_end:]
    if position == "before":
        return text[:start] + header_menu_html(site, rel, langs, cur, "nav") + text[start:]
    return text


def inject(text, site, rel, langs, cur, is_404=False):
    text = strip_blocks(text)
    if not is_404 and len(langs) > 1:
        text = insert_header_menu(text, site, rel, langs, cur)
    nl = "\r\n" if "\r\n" in text else "\n"
    lower = text.lower()
    head_end = lower.find("</head>")
    if head_end < 0:
        return text
    head = HREFLANG_RE.sub("", text[:head_end])
    body = text[head_end:]
    if is_404:
        return head + body
    has_og_locale = re.search(r"property\s*=\s*[\"']og:locale[\"']", head, re.I) is not None
    m = CANON_RE.search(head)
    if m:
        indent = m.group(1)
        block = alternates_block(site, rel, langs, cur, has_og_locale, nl, indent)
        end = m.end() if m.group(2) else m.end()
        if not m.group(2):
            block = nl + block
        head = head[:end] + block + head[end:]
    else:
        block = alternates_block(site, rel, langs, cur, has_og_locale, nl, "    ")
        head = head + block
    text = head + body
    if len(langs) > 1:
        sw = switcher_html(site, rel, langs, cur)
        lower = text.lower()
        idx = lower.rfind("</footer>")
        if idx < 0:
            idx = lower.rfind("</body>")
        if idx >= 0:
            text = text[:idx] + sw + text[idx:]
    return text


# ---------------------------------------------------------------------------
# Localizing one page
# ---------------------------------------------------------------------------

def rewrite_url(value, page_url, site, lang):
    v = value.strip()
    if (not v or v.startswith("#") or v.startswith("//")
            or re.match(r"^[a-z][a-z0-9+.-]*:", v, re.I) and not re.match(r"^https?:", v, re.I)):
        return value
    absu = urljoin(page_url, v)
    parts = urlsplit(absu)
    if parts.netloc != site.host:
        return value
    target = site.url_to_page(parts.path)
    if target and lang in site.page_langs.get(target, ()):
        path = site.url_path(target, lang)
    else:
        path = parts.path or "/"
    if urlsplit(v).netloc:
        return urlunsplit((parts.scheme, parts.netloc, path, parts.query, parts.fragment))
    return urlunsplit(("", "", path, parts.query, parts.fragment))


def localize_page(site, rel, lang, catalog):
    text = site.read(rel)
    soup = parse(text, site)
    segs, docs = collect_segments(soup)
    is_404 = rel == site.not_found
    page_url = site.base + clean_path(rel)

    for seg in segs:
        t = lookup(seg, catalog, site.keep)
        if t is None:
            continue
        if seg.kind == "attr":
            tag, a = seg.ref
            tag[a] = render_plain(t, seg.mapping, lang)
        elif seg.kind == "jsonld":
            container, key = seg.ref
            container[key] = render_plain(t, seg.mapping, lang)
    for seg in segs:
        if seg.kind != "text":
            continue
        t = lookup(seg, catalog, site.keep)
        if t is None:
            continue
        run, lead, trail = seg.ref
        nodes = render_pattern(soup, t, seg.mapping, lang)
        if lead:
            nodes.insert(0, NavigableString(lead))
        if trail:
            nodes.append(NavigableString(trail))
        anchor = run[0]
        if nodes:
            anchor.insert_before(*nodes)
        for n in run:
            n.extract()

    # numbers that stand alone (stat tiles, table cells) never went through a segment
    for node in list(soup.find_all(string=True)):
        if not is_text(node) or not re.search(r"\d", node):
            continue
        skip = False
        for p in node.parents:
            if isinstance(p, Tag) and (p.name in SKIP_TAGS or p.name in OPAQUE_TAGS or notranslate(p)):
                skip = True
                break
        if not skip:
            new = localize_numbers_in_text(str(node), lang)
            if new != str(node):
                node.replace_with(NavigableString(new))

    # JSON-LD: urls + inLanguage, then re-serialize
    def fix_ld(node):
        if isinstance(node, list):
            for v in node:
                fix_ld(v)
            return
        if not isinstance(node, dict):
            return
        t = node.get("@type")
        types = set(t) if isinstance(t, list) else {t}
        if types & JSONLD_LANG_TYPES and "inLanguage" not in node:
            node["inLanguage"] = LOCALES[lang]["html"]
        for k, v in list(node.items()):
            if k in ("url", "item", "@id", "mainEntityOfPage") and isinstance(v, str):
                node[k] = rewrite_url(v, page_url, site, lang)
            elif isinstance(v, (dict, list)):
                fix_ld(v)

    for doc in docs:
        if not doc["strings"]:
            fix_ld(doc["data"])
        payload = json.dumps(doc["data"], ensure_ascii=False, indent=2).replace("</", "<\\/")
        doc["script"].clear()
        doc["script"].append(Script("\n" + payload + "\n"))

    # document-level attributes
    if soup.html is not None:
        soup.html["lang"] = LOCALES[lang]["html"]
    for link in soup.find_all("link"):
        rels = [r.lower() for r in (link.get("rel") or [])]
        if "alternate" in rels and link.has_attr("hreflang"):
            link.decompose()
            continue
        if "canonical" in rels:
            link["href"] = site.url(rel, lang) if not is_404 else f"{site.base}/{lang}/"
    for meta in soup.find_all("meta"):
        prop = (meta.get("property") or "").lower()
        if prop == "og:url":
            meta["content"] = site.url(rel, lang)
        elif prop in ("og:locale", "og:locale:alternate"):
            meta.decompose()

    for tag in soup.find_all(True):
        for a in LINK_ATTRS:
            v = tag.get(a)
            if isinstance(v, str):
                tag[a] = rewrite_url(v, page_url, site, lang)
        ss = tag.get("srcset")
        if isinstance(ss, str):
            parts = []
            for item in ss.split(","):
                bits = item.strip().split(None, 1)
                if bits:
                    bits[0] = rewrite_url(bits[0], page_url, site, lang)
                    parts.append(" ".join(bits))
            tag["srcset"] = ", ".join(parts)

    for form in soup.find_all("form"):
        if (form.get("method") or "").lower() == "post" and not form.find("input", attrs={"name": "lang"}):
            form.insert(0, soup.new_tag("input", attrs={"type": "hidden", "name": "lang",
                                                        "value": LOCALES[lang]["html"]}))

    out = str(soup)
    return inject(out, site, rel, site.page_langs.get(rel, [SOURCE]), lang, is_404=is_404)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def scan(site, catalogs):
    """Parse every English page once: coverage per locale + the segment index."""
    index = {}
    report = {}
    for rel in site.pages:
        soup = parse(site.read(rel), site)
        segs, _ = collect_segments(soup)
        langs = [SOURCE]
        covs = {}
        for lg in site.locales:
            cov, title_ok = coverage(segs, catalogs.get(lg, {}), site.keep)
            covs[lg] = cov
            if cov >= site.min_cov and title_ok:
                langs.append(lg)
        site.page_langs[rel] = langs
        report[rel] = covs
        seen = set()
        for s in segs:
            kind = s.kind
            if kind == "text" and s.ref[0][0].parent is not None and s.ref[0][0].parent.name == "title":
                kind = "title"
            elif kind == "attr" and s.ref[0].name == "meta":
                kind = "meta"
            e = index.setdefault(s.id, {"src": s.pattern, "kind": kind, "pages": 0, "words": s.words,
                                        "sample": rel})
            if s.id not in seen:
                e["pages"] += 1
                seen.add(s.id)
    return index, report


def cmd_init(root, args):
    root = Path(root)
    cfg = root / CONFIG_NAME
    if cfg.exists():
        print(f"{CONFIG_NAME} already exists — left untouched")
    else:
        cfg.write_text(json.dumps({
            "base_url": args.base_url,
            "locales": ["es", "de", "fr", "pt-br"],
            "include": ["**/*.html"],
            "exclude": [],
            "not_found": "404.html",
            "sitemap": "sitemap.xml",
            "min_coverage": 0.9,
            "notranslate": [],
        }, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {cfg}")
    (root / "locales").mkdir(exist_ok=True)
    gi = root / ".gitignore"
    line = "locales/_work/"
    existing = gi.read_text(encoding="utf-8") if gi.exists() else ""
    if line not in existing:
        with gi.open("a", encoding="utf-8") as f:
            f.write(("" if existing.endswith("\n") or not existing else "\n") + line + "\n")
        print("added locales/_work/ to .gitignore")


def cmd_extract(site, args):
    index, _ = scan(site, {})
    work = site.root / "locales" / "_work"
    work.mkdir(parents=True, exist_ok=True)
    (work / "source.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    needs = {k: v for k, v in index.items() if not auto_identity(v["src"], site.keep)}
    words = sum(v["words"] for v in needs.values())
    single = [v for v in needs.values() if v["pages"] == 1]
    print(f"pages: {len(site.pages)}   segments: {len(index)}   needing translation: {len(needs)} "
          f"({words:,} words)   on a single page only: {len(single)}")
    gen_dirs = collections.Counter(v["sample"].split("/")[0] for v in single if "/" in v["sample"])
    if gen_dirs:
        print("single-page segments inside sub-directories (likely data that should carry translate=\"no\"):")
        for d, n in gen_dirs.most_common(10):
            print(f"  {d}/: {n}")
        shown = [v for v in single if "/" in v["sample"]][:15]
        for v in shown:
            print(f"    {v['sample']}: {v['src'][:110]}")
    print(f"full index: {work / 'source.json'}")


def cmd_todo(site, args):
    lang = args.lang
    catalog = site.load_catalog(lang)
    index, _ = scan(site, {})
    missing = {}
    for k, v in index.items():
        e = catalog.get(k)
        if e and e.get("src") == v["src"] and not validate_translation(v["src"], e.get("t")):
            continue
        if auto_identity(v["src"], site.keep):
            continue
        missing[k] = {"src": v["src"], "kind": v["kind"], "pages": v["pages"], "sample": v["sample"]}
    out = site.root / "locales" / "_work" / "todo"
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob(f"{lang}-*.json"):
        old.unlink()
    # most-used first: the chrome that appears on every page is translated first
    items = sorted(missing.items(), key=lambda kv: (-kv[1]["pages"], kv[1]["sample"], kv[0]))
    n = args.chunk
    files = 0
    for i in range(0, len(items), n):
        files += 1
        p = out / f"{lang}-{files:03d}.json"
        p.write_text(json.dumps(dict(items[i:i + n]), ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{lang}: {len(missing)} segments to translate in {files} file(s) under {out}")


def cmd_merge(site, args):
    lang = args.lang
    index, _ = scan(site, {})
    catalog = site.load_catalog(lang)
    added = bad = unknown = 0
    today = datetime.date.today().isoformat()
    for f in args.files:
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        for k, v in data.items():
            if k.startswith("_"):
                continue
            t = v.get("t") if isinstance(v, dict) else v
            if k not in index:
                unknown += 1
                continue
            src = index[k]["src"]
            why = validate_translation(src, t)
            if why:
                bad += 1
                print(f"  REJECTED {k}: {why}\n    src: {src[:160]}\n    t:   {str(t)[:160]}")
                continue
            entry = {"src": src, "t": t}
            if args.by:
                entry["by"] = args.by
                entry["at"] = today
            catalog[k] = entry
            added += 1
    if args.prune:
        catalog = {k: v for k, v in catalog.items() if k in index}
    site.catalog_path(lang).parent.mkdir(parents=True, exist_ok=True)
    site.catalog_path(lang).write_text(
        json.dumps(dict(sorted(catalog.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{lang}: merged {added}, rejected {bad}, unknown id {unknown}; catalog now {len(catalog)} entries")
    if bad:
        sys.exit(1)


I18N_JS = r"""/* i18n.js — DataEngineered language suggestion. Generated by scripts/i18n_common.py; do not edit.
   Suggests the visitor's language when this page has it. Never redirects; remembers a choice. */
(function () {
  'use strict';
  var KEY = 'de-lang-choice';
  var MSG = {
    'en': ['This page is also available in English.', 'Read in English', 'Close'],
    'es': ['Esta página también está disponible en español.', 'Leer en español', 'Cerrar'],
    'de': ['Diese Seite ist auch auf Deutsch verfügbar.', 'Auf Deutsch lesen', 'Schließen'],
    'fr': ['Cette page est aussi disponible en français.', 'Lire en français', 'Fermer'],
    'pt-br': ['Esta página também está disponível em português.', 'Ler em português', 'Fechar'],
    'it': ['Questa pagina è disponibile anche in italiano.', 'Leggi in italiano', 'Chiudi'],
    'nl': ['Deze pagina is ook beschikbaar in het Nederlands.', 'Lees in het Nederlands', 'Sluiten'],
    'id': ['Halaman ini juga tersedia dalam Bahasa Indonesia.', 'Baca dalam Bahasa Indonesia', 'Tutup'],
    'tr': ['Bu sayfa Türkçe olarak da mevcut.', 'Türkçe oku', 'Kapat'],
    'pl': ['Ta strona jest dostępna również po polsku.', 'Czytaj po polsku', 'Zamknij'],
    'ja': ['このページは日本語でもご覧いただけます。', '日本語で読む', '閉じる'],
    'ko': ['이 페이지는 한국어로도 제공됩니다.', '한국어로 보기', '닫기'],
    'zh-tw': ['本頁面也提供繁體中文版本。', '閱讀繁體中文版', '關閉']
  };
  // header language menu (<details class="i18n-menu">): close on outside click and Escape
  document.addEventListener('click', function (e) {
    var open = document.querySelectorAll('details.i18n-menu[open]');
    for (var n = 0; n < open.length; n++) { if (!open[n].contains(e.target)) open[n].removeAttribute('open'); }
  });
  // keep the opened list on screen: right-aligned by default, flipped left when the pill sits
  // near the left edge (e.g. a stacked mobile nav)
  document.addEventListener('toggle', function (e) {
    var d = e.target;
    if (!d || !d.classList || !d.classList.contains('i18n-menu') || !d.open) return;
    var ul = d.querySelector('ul');
    if (!ul) return;
    ul.style.left = ''; ul.style.right = '';
    var r = ul.getBoundingClientRect();
    var vw = document.documentElement.clientWidth || window.innerWidth;
    if (r.left < 8) { ul.style.left = '0'; ul.style.right = 'auto'; }
    else if (r.right > vw - 8) { ul.style.right = '0'; ul.style.left = 'auto'; }
  }, true);
  document.addEventListener('keydown', function (e) {
    if (e.key !== 'Escape') return;
    var open = document.querySelectorAll('details.i18n-menu[open]');
    for (var n = 0; n < open.length; n++) {
      open[n].removeAttribute('open');
      var s = open[n].querySelector('summary');
      if (s) s.focus();
    }
  });
  function store(v) { try { window.localStorage.setItem(KEY, v); } catch (e) {} }
  function stored() { try { return window.localStorage.getItem(KEY); } catch (e) { return null; } }
  document.addEventListener('click', function (e) {
    var a = e.target && e.target.closest ? e.target.closest('a[data-i18n-lang]') : null;
    if (a) store(a.getAttribute('data-i18n-lang'));
  });
  if (stored()) return;
  var cur = (document.documentElement.getAttribute('lang') || 'en').toLowerCase();
  var alts = {};
  var links = document.querySelectorAll('link[rel="alternate"][hreflang]');
  for (var i = 0; i < links.length; i++) {
    var h = (links[i].getAttribute('hreflang') || '').toLowerCase();
    if (h && h !== 'x-default') alts[h] = links[i].href;
  }
  var prefs = navigator.languages && navigator.languages.length ? navigator.languages : [navigator.language || ''];
  var target = null;
  for (var j = 0; j < prefs.length && !target; j++) {
    var p = String(prefs[j] || '').toLowerCase();
    var base = p.split('-')[0];
    if (!base) continue;
    if (p === cur || base === cur.split('-')[0]) return;
    if (alts[p]) { target = p; break; }
    for (var k in alts) { if (k.split('-')[0] === base) { target = k; break; } }
  }
  if (!target || !MSG[target] || !alts[target]) return;
  var m = MSG[target];
  var bar = document.createElement('div');
  bar.setAttribute('role', 'region');
  bar.setAttribute('lang', target);
  bar.setAttribute('translate', 'no');
  bar.style.cssText = 'position:fixed;left:12px;right:12px;bottom:12px;max-width:560px;margin:0 auto;' +
    'z-index:2147483000;background:#111827;color:#f9fafb;border:1px solid #374151;border-radius:10px;' +
    'padding:10px 14px;font:14px/1.4 system-ui,-apple-system,Segoe UI,sans-serif;display:flex;gap:12px;' +
    'align-items:center;box-shadow:0 8px 24px rgba(0,0,0,.35)';
  var txt = document.createElement('span');
  txt.style.flex = '1';
  txt.textContent = m[0] + ' ';
  var go = document.createElement('a');
  go.href = alts[target];
  go.textContent = m[1];
  go.setAttribute('data-i18n-lang', target);
  go.style.cssText = 'color:#93c5fd;font-weight:600;text-decoration:underline';
  txt.appendChild(go);
  var close = document.createElement('button');
  close.type = 'button';
  close.setAttribute('aria-label', m[2]);
  close.textContent = '\u00d7';
  close.style.cssText = 'background:none;border:0;color:#9ca3af;font-size:20px;line-height:1;cursor:pointer;padding:0 4px';
  close.addEventListener('click', function () { store(cur); bar.parentNode && bar.parentNode.removeChild(bar); });
  bar.appendChild(txt);
  bar.appendChild(close);
  document.body.appendChild(bar);
})();
"""


def git_file_count(root):
    candidates = [os.environ.get("I18N_GIT"), "git",
                  os.path.expandvars(r"%LOCALAPPDATA%\Programs\PortableGit\cmd\git.exe")]
    for g in candidates:
        if not g:
            continue
        try:
            r = subprocess.run([g, "ls-files", "--cached", "--others", "--exclude-standard"],
                               cwd=str(root), capture_output=True, text=True, encoding="utf-8")
        except (OSError, ValueError):
            continue
        if r.returncode == 0:
            return len([line for line in r.stdout.splitlines() if line.strip()])
    return None


def rewrite_sitemap(site):
    path = site.root / site.sitemap
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    entries = []
    for u in re.findall(r"<url>(.*?)</url>", text, re.S):
        m = re.search(r"<loc>(.*?)</loc>", u, re.S)
        if not m:
            continue
        loc = html.unescape(m.group(1).strip())
        parts = urlsplit(loc)
        first = parts.path.strip("/").split("/")[0] if parts.path.strip("/") else ""
        if parts.netloc == site.host and first in LOCALES and first != SOURCE:
            continue  # a locale URL from a previous build
        fields = re.findall(r"<(lastmod|changefreq|priority)>(.*?)</\1>", u, re.S)
        entries.append((loc, fields))
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
           'xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    n = 0
    for loc, fields in entries:
        parts = urlsplit(loc)
        rel = site.url_to_page(parts.path) if parts.netloc == site.host else None
        langs = site.page_langs.get(rel, [SOURCE]) if rel else [SOURCE]
        for lg in ordered_langs(site, langs):
            u = loc if lg == SOURCE else site.url(rel, lg)
            block = ["  <url>", f"    <loc>{html.escape(u)}</loc>"]
            block += [f"    <{k}>{v.strip()}</{k}>" for k, v in fields]
            if rel and len(langs) > 1:
                for lg2 in ordered_langs(site, langs):
                    block.append(f'    <xhtml:link rel="alternate" hreflang="{LOCALES[lg2]["hreflang"]}" '
                                 f'href="{html.escape(site.url(rel, lg2))}"/>')
                block.append(f'    <xhtml:link rel="alternate" hreflang="x-default" '
                             f'href="{html.escape(site.url(rel, SOURCE))}"/>')
            block.append("  </url>")
            out.extend(block)
            n += 1
    out.append("</urlset>")
    path.write_text("\n".join(out) + "\n", encoding="utf-8", newline="\n")
    return n


def cmd_build(site, args):
    catalogs = {lg: site.load_catalog(lg) for lg in site.locales}
    _, report = scan(site, catalogs)

    # authoritative: previous locale output is removed first (only dirs this tool created)
    for lg in site.locales:
        d = site.root / lg
        if d.exists():
            if not (d / MARKER_NAME).exists():
                sys.exit(f"refusing to delete {d}: it exists but was not generated by i18n_common.py")
            shutil.rmtree(d)
    for lg in set(LOCALES) - set(site.locales) - {SOURCE}:
        d = site.root / lg
        if d.exists() and (d / MARKER_NAME).exists():
            shutil.rmtree(d)  # a locale removed from the config

    written = collections.Counter()
    for rel in site.pages:
        langs = site.page_langs[rel]
        is_404 = rel == site.not_found
        src_text = site.read(rel)
        new_text = inject(src_text, site, rel, langs, SOURCE, is_404=is_404)
        if new_text != src_text:
            with open(site.root / rel, "w", encoding="utf-8", newline="") as f:
                f.write(new_text)
        for lg in langs:
            if lg == SOURCE:
                continue
            out = localize_page(site, rel, lg, catalogs[lg])
            dest = site.root / lg / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            with open(dest, "w", encoding="utf-8", newline="") as f:
                f.write(out)
            written[lg] += 1

    for lg in site.locales:
        if written[lg]:
            (site.root / lg / MARKER_NAME).write_text(
                "Generated by scripts/i18n_common.py build — do not edit; edit the English page "
                "or locales/%s.json and rebuild.\n" % lg, encoding="utf-8")
    js = site.root / "i18n" / "i18n.js"
    js.parent.mkdir(exist_ok=True)
    js.write_text(I18N_JS, encoding="utf-8", newline="\n")
    n_sitemap = rewrite_sitemap(site)

    print(f"pages: {len(site.pages)}   sitemap URLs: {n_sitemap}")
    for lg in site.locales:
        covs = [report[r][lg] for r in site.pages]
        below = [r for r in site.pages if lg not in site.page_langs[r]]
        avg = sum(covs) / len(covs) if covs else 0
        print(f"  {lg:6s} published {written[lg]:5d}/{len(site.pages)}   mean coverage {avg:6.1%}   "
              f"not published: {len(below)}" + (f" (e.g. {', '.join(below[:4])})" if below else ""))
    count = git_file_count(site.root)
    if count is not None:
        print(f"files in deployment (git tracked + untracked, not ignored): {count:,} / {PAGES_FILE_LIMIT:,}")
        if count >= PAGES_FILE_LIMIT:
            sys.exit(f"ERROR: {count} files exceeds the Cloudflare Pages limit of {PAGES_FILE_LIMIT}")


def _redirect_sources(site):
    p = site.root / "_redirects"
    out = []
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                out.append(line.split()[0])
    return out


def _exists(site, path, redirects):
    path = unquote(path)
    for src in redirects:
        if src == path or (src.endswith("*") and path.startswith(src[:-1])):
            return True
    rel = path.lstrip("/")
    root = site.root
    if path.endswith("/"):
        return (root / rel / "index.html").exists() or rel == "" and (root / "index.html").exists()
    return ((root / rel).is_file() or (root / (rel + ".html")).is_file()
            or (root / rel / "index.html").is_file())


def _internal_paths(site, soup, page_url):
    paths = set()
    for tag in soup.find_all(True):
        if tag.name == "link" and "alternate" in [r.lower() for r in (tag.get("rel") or [])]:
            continue
        if tag.name == "link" and "canonical" in [r.lower() for r in (tag.get("rel") or [])]:
            continue
        for a in ("href", "src", "action"):
            v = tag.get(a)
            if not isinstance(v, str):
                continue
            v = v.strip()
            if not v or v.startswith("#") or re.match(r"^[a-z][a-z0-9+.-]*:", v, re.I) and not v.lower().startswith("http"):
                continue
            parts = urlsplit(urljoin(page_url, v))
            if parts.netloc == site.host:
                paths.add(parts.path or "/")
    return paths


def cmd_check(site, args):
    errors, warnings = [], []
    redirects = _redirect_sources(site)
    # clusters as written on disk
    clusters = {}
    files = []
    for rel in site.pages:
        files.append((SOURCE, rel))
    for lg in site.locales:
        d = site.root / lg
        if d.exists():
            for p in d.rglob("*.html"):
                files.append((lg, p.relative_to(d).as_posix()))
    english_broken = {}
    for lg, rel in files:
        path = site.root / rel if lg == SOURCE else site.root / lg / rel
        soup = BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")
        url_here = site.url(rel, lg)
        is_404 = rel == site.not_found
        if lg != SOURCE:
            got = soup.html.get("lang") if soup.html else None
            if got != LOCALES[lg]["html"]:
                errors.append(f"{lg}/{rel}: <html lang> is {got!r}")
            canon = [link.get("href") for link in soup.find_all("link") if "canonical" in (link.get("rel") or [])]
            want = f"{site.base}/{lg}/" if is_404 else url_here
            if canon != [want]:
                errors.append(f"{lg}/{rel}: canonical {canon} != {want}")
        alts = {link.get("hreflang"): link.get("href") for link in soup.find_all("link")
                if "alternate" in (link.get("rel") or []) and link.has_attr("hreflang")}
        if not is_404:
            if alts.get(LOCALES[lg]["hreflang"]) != url_here:
                errors.append(f"{lg}/{rel}: no self hreflang (got {alts.get(LOCALES[lg]['hreflang'])})")
            if alts.get("x-default") != site.url(rel, SOURCE):
                errors.append(f"{lg}/{rel}: x-default is {alts.get('x-default')}")
            clusters[(lg, rel)] = alts
        page_url = site.base + clean_path(rel) if lg == SOURCE else url_here
        broken = {p for p in _internal_paths(site, soup, page_url) if not _exists(site, p, redirects)}
        if lg == SOURCE:
            english_broken[rel] = broken
        else:
            base_broken = english_broken.get(rel, set())
            new = {p for p in broken if p not in base_broken and re.sub(r"^/" + re.escape(lg), "", p) not in base_broken}
            for p in sorted(new):
                errors.append(f"{lg}/{rel}: broken internal link {p}")
            for s in soup.find_all("script"):
                body = s.string or ""
                if re.search(r"""(fetch|register|open)\(\s*['"](?![/a-z]+:|/|#)""", body):
                    warnings.append(f"{lg}/{rel}: inline script uses a relative URL (breaks under /{lg}/)")
                    break
    # reciprocity
    for (lg, rel), alts in clusters.items():
        for hl, href in alts.items():
            if hl == "x-default":
                continue
            other = next((code for code in LOCALES if LOCALES[code]["hreflang"] == hl), None)
            if other is None:
                errors.append(f"{lg}/{rel}: unknown hreflang {hl}")
                continue
            back = clusters.get((other, rel))
            if back is None:
                errors.append(f"{lg}/{rel}: hreflang {hl} -> {href} but that page does not exist")
            elif back != alts:
                errors.append(f"{lg}/{rel}: hreflang cluster differs from {other}/{rel}")
    # catalogs
    for lg in site.locales:
        for k, v in site.load_catalog(lg).items():
            why = validate_translation(v.get("src", ""), v.get("t"))
            if why or seg_id(v.get("src", "")) != k:
                errors.append(f"locales/{lg}.json {k}: {why or 'id does not match src'}")
    # sitemap
    sm = site.root / site.sitemap
    if sm.exists():
        for loc in re.findall(r"<loc>(.*?)</loc>", sm.read_text(encoding="utf-8")):
            parts = urlsplit(html.unescape(loc))
            if parts.netloc == site.host and not _exists(site, parts.path or "/", redirects):
                errors.append(f"sitemap: {loc} has no file")
    count = git_file_count(site.root)
    if count is not None and count >= PAGES_FILE_LIMIT:
        errors.append(f"{count} files exceeds the Cloudflare Pages limit")
    for w in warnings[:20]:
        print("WARN ", w)
    if len(warnings) > 20:
        print(f"WARN  … {len(warnings) - 20} more")
    for e in errors[:60]:
        print("ERROR", e)
    if len(errors) > 60:
        print(f"ERROR … {len(errors) - 60} more")
    print(f"check: {len(files)} pages, {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        sys.exit(1)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", default=".", help="site repo root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("init")
    p.add_argument("--base-url", required=True)
    sub.add_parser("extract")
    p = sub.add_parser("todo")
    p.add_argument("--lang", required=True)
    p.add_argument("--chunk", type=int, default=250)
    p = sub.add_parser("merge")
    p.add_argument("--lang", required=True)
    p.add_argument("--by", default="")
    p.add_argument("--prune", action="store_true")
    p.add_argument("files", nargs="+")
    sub.add_parser("build")
    sub.add_parser("check")
    args = ap.parse_args(argv)
    if args.cmd == "init":
        return cmd_init(args.root, args)
    site = Site(args.root)
    return {"extract": cmd_extract, "todo": cmd_todo, "merge": cmd_merge,
            "build": cmd_build, "check": cmd_check}[args.cmd](site, args)


if __name__ == "__main__":
    main()
