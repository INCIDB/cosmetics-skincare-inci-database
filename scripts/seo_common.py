"""Shared SEO helpers for the DataEngineered site generators.

Copied verbatim into each site repo's scripts/ directory (the repos are independent).
Source of truth: <portfolio root>/scripts/seo_common.py — edit there, then re-copy.
"""
import datetime
import html
import os
import re
import subprocess
from pathlib import Path

TITLE_MAX = 60
DESC_MAX = 155
_TRAIL = " ,;:-–—(/"
# a cut must not end on one of these — the reader loses the word that mattered ("Loss of")
# "a"/"an" are deliberately NOT here: a trailing "A" is often a designator ("Sensor A", "Vitamin A")
_STOPWORDS = {"and", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the",
              "to", "with", "without", "vs", "&"}


def _cut(text, room):
    """Truncate text to <= room chars at a word boundary; fall back to a hard cut."""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= room:
        return text
    cut = text[:room].rsplit(" ", 1)[0].rstrip(_TRAIL)
    if len(cut) < max(8, room // 2):
        cut = text[:room].rstrip(_TRAIL)
    # never end inside an unclosed bracket: drop the dangling "(…" / "[…" fragment
    for open_, close in (("(", ")"), ("[", "]")):
        if cut.count(open_) > cut.count(close):
            cut = cut[: cut.rfind(open_)].rstrip(_TRAIL)
    # never end on a stopword (only when more than one word remains)
    words = cut.split(" ")
    while len(words) > 1 and words[-1].lower().strip(",;:") in _STOPWORDS:
        words.pop()
    return " ".join(words).rstrip(_TRAIL)


def fit_title(entity, descriptor, brand, max_len=TITLE_MAX, sep=" — "):
    """'<entity><sep><descriptor> | <brand>' within max_len.

    `descriptor` may be a string or a list of strings in preference order: the first
    descriptor that lets the whole entity fit is used, so the entity is kept intact
    whenever a shorter descriptor allows it. Only then is the entity truncated at a
    word boundary. If that would leave fewer than 12 characters of entity, the
    descriptor is dropped instead: '<entity> | <brand>'.
    """
    entity = re.sub(r"\s+", " ", str(entity)).strip()
    options = [descriptor] if isinstance(descriptor, str) else list(descriptor)
    options = [re.sub(r"\s+", " ", str(d)).strip() for d in options] or [""]
    tail = f" | {brand}"
    for d in options + [""]:  # last resort before cutting the entity: no descriptor at all
        full = f"{entity}{sep}{d}{tail}" if d else f"{entity}{tail}"
        if len(full) <= max_len:
            return full
    descriptor = options[-1]
    room = max_len - len(sep) - len(descriptor) - len(tail)
    if room >= 12:
        return f"{_cut(entity, room)}{sep}{descriptor}{tail}"
    return f"{_cut(entity, max_len - len(tail))}{tail}"


def fit_desc(text, max_len=DESC_MAX):
    """Collapse whitespace and cut at a word boundary; append an ellipsis when cut."""
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) <= max_len:
        return text
    cut = _cut(text, max_len - 1)
    return cut if cut.endswith((".", "!", "?")) else cut + "…"


# What scripts/i18n_common.py build rewrites in every English page: it drops any hreflang
# <link> from <head> and injects its own blocks (hreflang alternates, the header language
# menu, the footer switcher). Same patterns as its BLOCK_RE / HREFLANG_RE; keep them in
# step. The page generators run BEFORE the i18n build, so when they write the sitemap a
# freshly regenerated page still has the generator's hreflang links and none of the blocks.
I18N_BLOCK_RE = re.compile(r"[ \t]*<!-- i18n:alternates -->.*?<!-- /i18n:alternates -->[ \t]*(?:\r?\n)?"
                           r"|<!-- i18n:(switcher|header) -->.*?<!-- /i18n:\1 -->", re.S)
I18N_HREFLANG_RE = re.compile(r"[ \t]*<link\b[^>]*\bhreflang\s*=[^>]*>[ \t]*(?:\r?\n)?", re.I)


def _page_content(data):
    """What lastmod compares: the page with LF line ends and without what the i18n build
    owns (I18N_BLOCK_RE anywhere, I18N_HREFLANG_RE in <head>)."""
    # LF: a checkout with core.autocrlf=true has every page in CRLF.
    text = I18N_BLOCK_RE.sub("", data.decode("utf-8", "surrogateescape").replace("\r\n", "\n"))
    head_end = text.lower().find("</head>")
    if head_end < 0:
        return text
    return I18N_HREFLANG_RE.sub("", text[:head_end]) + text[head_end:]


def git_lastmod(path, repo_dir):
    """YYYY-MM-DD the page's content last changed: today if the working copy differs from
    HEAD (or is untracked), else the date of the last commit that changed it.

    Both comparisons ignore line endings and what the i18n build owns (_page_content): a
    page the generator rewrote identically, before the i18n build re-injects its blocks,
    is unchanged, and a commit that only moved those blocks (a new locale, an i18n.js
    version bump) is skipped over. So lastmod moves only when the page itself changes,
    and a rerun on an unchanged tree reproduces the committed dates.

    A relative path is relative to repo_dir, as it was when git ran with cwd=repo_dir:
    ApplianceDB's tools/generate_landing.py passes "landing/<page>.html" with repo_dir
    "../ApplianceDB-public".
    """
    today = datetime.date.today().isoformat()
    path = os.path.join(str(repo_dir), path)  # unchanged when path is absolute
    rel = os.path.relpath(path, repo_dir).replace(os.sep, "/")

    def git(*args):
        return subprocess.run(["git", *args], cwd=str(repo_dir), capture_output=True)

    def committed(rev):
        r = git("cat-file", "blob", f"{rev}:./{rel}")
        return _page_content(r.stdout) if r.returncode == 0 else None

    newer = committed("HEAD")
    if newer is None or not os.path.isfile(path):
        return today
    if _page_content(Path(path).read_bytes()) != newer:
        return today
    log = git("log", "--format=%H %cs", "--", rel).stdout.decode("ascii").split()
    commits = list(zip(log[0::2], log[1::2]))  # newest first
    for i, (_, day) in enumerate(commits):
        older = committed(commits[i + 1][0]) if i + 1 < len(commits) else None
        if older != newer:  # this commit changed the page itself; else it was i18n-only
            return day
    return today


def write_sitemap(repo_dir, entries, out="sitemap.xml"):
    """entries: iterable of (url, local_file_path, changefreq, priority).

    Drops duplicates and non-HTML targets, sorts by URL, stamps lastmod from git.
    Returns the number of URLs written.
    """
    seen, rows = set(), []
    for url, fp, freq, prio in entries:
        fp = Path(fp)
        if url in seen or (fp.suffix and fp.suffix.lower() not in (".html", ".htm")):
            continue
        seen.add(url)
        rows.append((url, git_lastmod(fp, repo_dir), freq, prio))
    rows.sort()
    xml = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for url, lm, freq, prio in rows:
        xml.append(f"  <url>\n    <loc>{html.escape(url)}</loc>\n    <lastmod>{lm}</lastmod>\n"
                   f"    <changefreq>{freq}</changefreq>\n    <priority>{prio}</priority>\n  </url>")
    xml.append("</urlset>")
    Path(repo_dir, out).write_text("\n".join(xml) + "\n", encoding="utf-8", newline="\n")
    return len(rows)


def related_block(items, heading="Related", css_class="related", limit=6):
    """items: list of (href, label, reason_or_None[, translatable]). Empty list -> ''.

    At most `limit` links (default 6); pass limit=None when every item must appear,
    e.g. to keep parent<->child links reciprocal.

    The optional 4th element is False when the label is data (an ingredient, product or
    code name): the link then carries translate="no" so i18n_common.py keeps it verbatim.
    Omitted -> True, and the output is byte-identical to the 3-tuple form.
    """
    if not items:
        return ""
    lis = []
    for item in (items if limit is None else items[:limit]):
        href, label, reason = item[:3]
        translatable = item[3] if len(item) > 3 else True
        why = f' <span class="{css_class}-why">— {html.escape(str(reason))}</span>' if reason else ""
        tn = "" if translatable else ' translate="no"'
        lis.append(f'<li><a href="{html.escape(href)}"{tn}>{html.escape(str(label))}</a>{why}</li>')
    return (f'<section class="{css_class}"><h2>{html.escape(heading)}</h2><ul>'
            + "".join(lis) + "</ul></section>")
