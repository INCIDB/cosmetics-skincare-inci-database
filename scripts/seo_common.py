"""Shared SEO helpers for the DataEngineered site generators.

Copied verbatim into each site repo's scripts/ directory (the repos are independent).
Source of truth: <portfolio root>/scripts/seo_common.py — edit there, then re-copy.
"""
import datetime
import html
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


def git_lastmod(path, repo_dir):
    """YYYY-MM-DD of the last commit touching path; today if untracked or modified."""
    today = datetime.date.today().isoformat()
    rel = str(Path(path))

    def git(*args):
        return subprocess.run(["git", *args, "--", rel], cwd=str(repo_dir),
                              capture_output=True, text=True)

    if git("ls-files", "--error-unmatch").returncode != 0:
        return today
    if git("diff", "--quiet").returncode != 0 or git("diff", "--cached", "--quiet").returncode != 0:
        return today
    out = git("log", "-1", "--format=%cs").stdout.strip()
    return out or today


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
    """items: list of (href, label, reason_or_None). Empty list -> ''.

    At most `limit` links (default 6); pass limit=None when every item must appear,
    e.g. to keep parent<->child links reciprocal.
    """
    if not items:
        return ""
    lis = []
    for href, label, reason in (items if limit is None else items[:limit]):
        why = f' <span class="{css_class}-why">— {html.escape(str(reason))}</span>' if reason else ""
        lis.append(f'<li><a href="{html.escape(href)}">{html.escape(str(label))}</a>{why}</li>')
    return (f'<section class="{css_class}"><h2>{html.escape(heading)}</h2><ul>'
            + "".join(lis) + "</ul></section>")
