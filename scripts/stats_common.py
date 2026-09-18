"""Shared helpers for the /stats/ page generators of the DataEngineered sites.

Copied verbatim into each site repo's scripts/ directory (the repos are independent).
Source of truth: <portfolio root>/scripts/stats_common.py — edit there, then re-copy.

A stats generator (scripts/generate_stats.py in a site repo) reads the FULL private
snapshot, computes aggregates only, and writes:

    stats/index.html          the page (URL /stats/)
    stats/charts/<slug>.svg   one standalone SVG per chart (for <img> embeds elsewhere)
    stats/data.json           every figure on the page, machine-readable

This module holds everything that is the same for every site: the SVG charts
(single-series, thin marks, hairline grid, direct labels, hover titles), the figure /
embed-snippet / table / section builders, the copy-button script and the writer.
Colours, fonts, URLs and brand words come in through a `Site` instance.

Chart rules (see the portfolio's dataviz notes): one hue per chart, text in ink/muted
tokens never in the data colour, bars <= 24px with a 4px rounded data end and a square
baseline, 2px lines with a >= 8px end marker ringed in the surface colour, solid hairline
gridlines, a legend only for >= 2 series (so none here), and a table twin for every chart.
"""
import datetime as dt
import html
import json
from dataclasses import dataclass
from pathlib import Path


# ---------------------------------------------------------------------------
# site parameters
# ---------------------------------------------------------------------------

@dataclass
class Site:
    base_url: str                 # https://roasterdb.dataengineered.io
    brand: str                    # RoasterDB
    snippet_label: str            # "RoasterDB specialty coffee statistics" (embed attribution text)
    surface: str                  # chart / page background
    surface2: str                 # card background
    ink: str                      # primary text
    muted: str                    # secondary text
    grid: str                     # one-step-off-surface hairline
    accent: str                   # the single data hue
    font: str = "'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif"
    mono: str = "ui-monospace, Menlo, Consolas, monospace"
    heading_class: str = ""       # CSS class put on <h2>/<h3> (e.g. "font-display")
    page_path: str = "/stats/"

    @property
    def page_url(self):
        return self.base_url.rstrip("/") + self.page_path

    @property
    def download_prefix(self):
        return self.brand.lower()


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------

def esc(s):
    return html.escape(str(s), quote=True)


def n(v):
    """1,234 style thousands grouping for ints."""
    return f"{int(round(v)):,}"


def pct(part, whole, digits=1):
    return 0.0 if not whole else round(100.0 * part / whole, digits)


def data(v):
    """A data value (country, agency, firm...) kept verbatim by scripts/i18n_common.py."""
    return f'<span translate="no">{esc(v)}</span>'


def nice_step(vmax, target_ticks=5):
    raw = vmax / target_ticks
    mag = 10 ** (len(str(int(raw))) - 1) if raw >= 1 else 1
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


# ---------------------------------------------------------------------------
# SVG charts (self-contained: work inline and as standalone files)
# ---------------------------------------------------------------------------

def _svg_head(site, width, height, title, subtitle):
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'role="img" aria-labelledby="t d" font-family="{site.font}" font-size="12">',
        f'<title id="t">{esc(title)}</title><desc id="d">{esc(subtitle)}</desc>',
        f'<rect width="{width}" height="{height}" fill="{site.surface}"/>',
        f'<text x="20" y="26" font-size="15" font-weight="600" fill="{site.ink}">{esc(title)}</text>',
        f'<text x="20" y="44" font-size="12" fill="{site.muted}">{esc(subtitle)}</text>',
    ]


def _svg_foot(site, width, height, note):
    return [f'<text x="20" y="{height - 12}" font-size="11" fill="{site.muted}">{esc(note)}</text>', "</svg>"]


def svg_hbar(site, title, subtitle, rows, note, width=720, label_w=196):
    """rows: [(label, value, display)] -- one series, bars in the accent hue,
    <= 24px thick, 4px rounded data-end and square at the baseline, value at the tip."""
    top, row_h, bar_h, val_w = 62, 30, 18, 84
    x0 = label_w + 12
    plot_w = width - x0 - val_w - 16
    vmax = max(v for _, v, _ in rows) or 1
    height = top + len(rows) * row_h + 40
    out = _svg_head(site, width, height, title, subtitle)
    out.append(f'<line x1="{x0}" y1="{top - 6}" x2="{x0}" y2="{top + len(rows) * row_h}" stroke="{site.grid}" stroke-width="1"/>')
    for i, (label, v, disp) in enumerate(rows):
        y = top + i * row_h + (row_h - bar_h) / 2
        w = max(2.0, plot_w * v / vmax)
        if w >= 8:
            shape = (f'<path d="M{x0} {y} h{w - 4:.1f} a4 4 0 0 1 4 4 v{bar_h - 8} a4 4 0 0 1 -4 4 h-{w - 4:.1f} z" '
                     f'fill="{site.accent}"/>')
        else:
            shape = f'<rect x="{x0}" y="{y}" width="{w:.1f}" height="{bar_h}" fill="{site.accent}"/>'
        out.append(
            f'<g><title>{esc(label)}: {esc(disp)}</title>'
            f'<rect x="0" y="{top + i * row_h}" width="{width}" height="{row_h}" fill="transparent"/>'
            f'{shape}'
            f'<text x="{x0 - 10}" y="{y + bar_h / 2 + 4}" text-anchor="end" fill="{site.ink}">{esc(label)}</text>'
            f'<text x="{x0 + w + 8:.1f}" y="{y + bar_h / 2 + 4}" fill="{site.muted}" '
            f'font-family="{site.mono}" font-size="11">{esc(disp)}</text></g>')
    out += _svg_foot(site, width, height, note)
    return "\n".join(out)


def svg_line(site, title, subtitle, points, fmt, note, width=720, height=320, peak_label=None, last_label=None,
             right=96):
    """points: [(xlabel, value)] -- one 2px line in the accent hue, 10% area wash,
    hairline solid gridlines, >= 8px end marker with a 2px surface ring, direct labels
    only at the end and the peak, per-point hover titles."""
    top, left, bottom = 62, 56, 46
    plot_w, plot_h = width - left - right, height - top - bottom
    vmax = max(v for _, v in points)
    step = nice_step(vmax)
    ymax = step * (int(vmax / step) + 1)
    xs = [left + plot_w * i / (len(points) - 1) for i in range(len(points))]
    ys = [top + plot_h - plot_h * v / ymax for _, v in points]
    out = _svg_head(site, width, height, title, subtitle)
    t = 0
    while t <= ymax + 1e-9:
        y = top + plot_h - plot_h * t / ymax
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_w}" y2="{y:.1f}" stroke="{site.grid}" stroke-width="1"/>')
        out.append(f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="{site.muted}" font-size="11" '
                   f'font-family="{site.mono}">{esc(fmt(t))}</text>')
        t += step
    every = max(1, len(points) // 9)
    for i, (xl, _) in enumerate(points):
        if i % every == 0 or i == len(points) - 1:
            out.append(f'<text x="{xs[i]:.1f}" y="{top + plot_h + 18}" text-anchor="middle" fill="{site.muted}" '
                       f'font-size="11" font-family="{site.mono}">{esc(xl)}</text>')
    path = " ".join(f"{'M' if i == 0 else 'L'}{xs[i]:.1f} {ys[i]:.1f}" for i in range(len(points)))
    out.append(f'<path d="{path} L{xs[-1]:.1f} {top + plot_h} L{xs[0]:.1f} {top + plot_h} Z" fill="{site.accent}" fill-opacity="0.1"/>')
    out.append(f'<path d="{path}" fill="none" stroke="{site.accent}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>')
    for i, (xl, v) in enumerate(points):
        out.append(f'<g><title>{esc(xl)}: {esc(fmt(v))}</title><circle cx="{xs[i]:.1f}" cy="{ys[i]:.1f}" r="12" fill="transparent"/></g>')
    if peak_label:
        pi = max(range(len(points)), key=lambda i: points[i][1])
        out.append(f'<circle cx="{xs[pi]:.1f}" cy="{ys[pi]:.1f}" r="5" fill="{site.accent}" stroke="{site.surface}" stroke-width="2"/>')
        out.append(f'<text x="{xs[pi]:.1f}" y="{ys[pi] - 12:.1f}" text-anchor="middle" fill="{site.ink}" font-size="11">{esc(peak_label)}</text>')
    out.append(f'<circle cx="{xs[-1]:.1f}" cy="{ys[-1]:.1f}" r="5" fill="{site.accent}" stroke="{site.surface}" stroke-width="2"/>')
    if last_label:
        out.append(f'<text x="{xs[-1] + 10:.1f}" y="{ys[-1] + 4:.1f}" fill="{site.ink}" font-size="11">{esc(last_label)}</text>')
    out += _svg_foot(site, width, height, note)
    return "\n".join(out)


# ---------------------------------------------------------------------------
# page building blocks
# ---------------------------------------------------------------------------

def embed_block(site, slug, title):
    img = f"{site.base_url}{site.page_path}charts/{slug}.svg"
    snippet = (f'<a href="{site.page_url}#{slug}"><img src="{img}" alt="{esc(title)}" width="720" '
               f'style="max-width:100%;height:auto"></a>\n'
               f'<p><small>Source: <a href="{site.page_url}">{site.snippet_label}</a> (CC BY 4.0)</small></p>')
    return (f'<details><summary>Embed this chart</summary>'
            f'<p style="margin-top:8px;color:var(--text-muted)">Paste the snippet into your post. It links the chart back to this page, which is the only attribution we ask for.</p>'
            f'<pre translate="no"><code id="embed-{slug}">{esc(snippet)}</code></pre>'
            f'<button type="button" class="copy" data-target="embed-{slug}">Copy snippet</button></details>')


def figure(site, slug, svg, title, note):
    return (f'<figure id="fig-{slug}">{svg}<figcaption><span>{esc(note)}</span>'
            f'<a href="{site.page_path}charts/{slug}.svg" download="{site.download_prefix}-{slug}.svg">Download SVG</a></figcaption></figure>'
            + embed_block(site, slug, title))


def table(headers, rows, num_cols, data_fn=data):
    """headers: list of str; rows: list of tuples; num_cols: set of column indexes that hold
    numbers (right-aligned, escaped); other cells are data values (translate="no")."""
    th = "".join(f'<th{" class=\"num\"" if i in num_cols else ""}>{esc(h)}</th>' for i, h in enumerate(headers))
    body = []
    for r in rows:
        tds = []
        for i, c in enumerate(r):
            tds.append(f'<td class="num">{esc(c)}</td>' if i in num_cols else f"<td>{data_fn(c)}</td>")
        body.append("<tr>" + "".join(tds) + "</tr>")
    return f'<div class="tbl"><table><thead><tr>{th}</tr></thead><tbody>{"".join(body)}</tbody></table></div>'


def section(site, slug, heading, finding, fig_html, table_html, method):
    cls = f' class="{site.heading_class}"' if site.heading_class else ""
    return (f'<section class="stat" id="{slug}"><h2{cls}>{heading}</h2>'
            f'<p class="finding">{finding}</p>{fig_html}{table_html}'
            f'<p class="method">{method}</p></section>')


def toc(items):
    """items: [(slug, label)] -> the 'On this page' list."""
    return "".join(f'<li><a href="#{slug}">{label}</a></li>' for slug, label in items)


def tiles(items, date_labels=("Snapshot",)):
    """items: [(label, value)] -> stat tiles; labels in `date_labels` get the compact .date style."""
    return "".join(
        f'<li{" class=\"date\"" if lbl in date_labels else ""}><span>{lbl}</span><strong>{val}</strong></li>'
        for lbl, val in items)


def article_ld(site, headline, description, first_published, image, about, today=None):
    """Article + BreadcrumbList JSON-LD for the page (two <script> blocks, ready to embed)."""
    today = today or dt.date.today().isoformat()
    article = json.dumps({
        "@context": "https://schema.org", "@type": "Article", "headline": headline, "description": description,
        "url": site.page_url, "datePublished": first_published, "dateModified": today, "image": image, "inLanguage": "en",
        "author": {"@type": "Organization", "name": site.brand, "url": site.base_url},
        "publisher": {"@type": "Organization", "name": "DataEngineered", "url": "https://dataengineered.io/"},
        "isBasedOn": site.base_url + "/", "license": "https://creativecommons.org/licenses/by/4.0/", "about": about},
        ensure_ascii=False, indent=2)
    crumbs = json.dumps({
        "@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Home", "item": site.base_url + "/"},
            {"@type": "ListItem", "position": 2, "name": "Statistics", "item": site.page_url}]}, ensure_ascii=False, indent=2)
    return (f'  <script type="application/ld+json">\n{article}\n  </script>\n'
            f'  <script type="application/ld+json">\n{crumbs}\n  </script>')


# Copy button: clipboard API with a select-the-text fallback; no relative URLs (i18n check).
COPY_JS = """  <script>
    document.querySelectorAll('button.copy').forEach(function (b) {
      b.addEventListener('click', function () {
        var el = document.getElementById(b.getAttribute('data-target'));
        if (!el) return;
        var done = function () { var old = b.textContent; b.textContent = 'Copied'; setTimeout(function () { b.textContent = old; }, 1500); };
        var select = function () { var r = document.createRange(); r.selectNodeContents(el); var s = window.getSelection(); s.removeAllRanges(); s.addRange(r); };
        if (navigator.clipboard && navigator.clipboard.writeText) {
          navigator.clipboard.writeText(el.textContent).then(done, select);
        } else { select(); }
      });
    });
  </script>"""

# Shared layout rules for the stats page; each site prepends its own colour tokens/fonts.
STATS_CSS = """
    .tiles { list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; margin-top: 28px; padding: 0; }
    .tiles li { background: var(--bg-paper-2); border: 1px solid var(--rule-color); padding: 14px 16px; border-radius: var(--radius, 0); }
    .tiles span { display: block; color: var(--text-muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.06em; }
    .tiles strong { font-size: 1.6rem; font-weight: 700; line-height: 1.2; }
    .tiles li.date strong { font-size: 1.15rem; white-space: nowrap; }
    .toc { margin-top: 28px; padding: 16px 20px; border: 1px solid var(--rule-color); border-radius: var(--radius, 0); font-size: 0.88rem; }
    .toc ol { margin: 8px 0 0 18px; columns: 2; column-gap: 32px; }
    .toc li { break-inside: avoid; }
    section.stat { margin-top: 56px; padding-top: 32px; border-top: 1px solid var(--rule-color); }
    .finding { margin-top: 12px; font-size: 1rem; max-width: 72ch; }
    .finding strong { color: var(--accent); }
    figure { margin: 24px 0 0; border: 1px solid var(--rule-color); border-radius: var(--radius, 0); overflow: hidden; }
    figure svg { display: block; width: 100%; height: auto; }
    figcaption { padding: 10px 14px; font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid var(--rule-color); display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    details { margin-top: 14px; font-size: 0.85rem; }
    summary { cursor: pointer; color: var(--accent); }
    details pre { margin-top: 10px; padding: 12px 14px; background: var(--bg-paper-2); border: 1px solid var(--rule-color); border-radius: var(--radius, 0); font-size: 0.74rem; white-space: pre-wrap; word-break: break-all; }
    .copy { margin-top: 8px; background: none; border: 1px solid var(--rule-color); color: var(--text-ink); font-family: inherit; font-size: 0.78rem; padding: 6px 12px; border-radius: var(--radius, 0); cursor: pointer; }
    .copy:hover { border-color: var(--accent); color: var(--accent); }
    .tbl { overflow-x: auto; margin-top: 18px; }
    .tbl table { width: 100%; border-collapse: collapse; font-size: 0.84rem; min-width: 0; }
    .tbl th, .tbl td { padding: 9px 12px; text-align: left; border-bottom: 1px solid var(--rule-color); vertical-align: top; }
    .tbl th { background: var(--bg-paper-2); text-transform: uppercase; font-size: 0.7rem; letter-spacing: 0.08em; }
    .tbl td.num, .tbl th.num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
    .method { margin-top: 12px; font-size: 0.84rem; color: var(--text-muted); max-width: 80ch; }
    .method li { margin: 6px 0 0 18px; }
    @media (max-width: 640px) { .toc ol { columns: 1; } }
"""


def write_outputs(out_dir, page, charts, data_json):
    """Write stats/index.html, stats/charts/*.svg and stats/data.json (LF line endings)."""
    out_dir = Path(out_dir)
    (out_dir / "charts").mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(page, encoding="utf-8", newline="\n")
    for slug, svg in charts.items():
        (out_dir / "charts" / f"{slug}.svg").write_text(svg + "\n", encoding="utf-8", newline="\n")
    (out_dir / "data.json").write_text(json.dumps(data_json, ensure_ascii=False, indent=1) + "\n",
                                       encoding="utf-8", newline="\n")
