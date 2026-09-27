"""Section links (#pricing, #contact, ...) on the portfolio sites: one inline snippet, shared by every
site, that keeps fragment jumps clear of a sticky header and lands arrivals from other pages on
their section once late web fonts / late content have moved the page.

Why (measured 2026-09-27): the sites load Google Fonts without blocking the page (media="print"
onload, display=swap), so the fonts swap in after the browser has scrolled to the fragment and move
the sections (up to ~200 px, 877 px on WineDB whose tables are sized by the font); some pages also
build content after load (WineDB tables, RecallDB preview rows). Sticky headers with no
scroll-padding covered section headings on arrival, on phones on almost every site.

The snippet is placed right after the page's sticky header (so the header exists when it runs):
- scroll-padding-top = the header's live height + 8 px while the header is sticky/fixed (it
  follows the header through breakpoints and language menus with a ResizeObserver, and re-checks
  which header is sticky, since some are sticky only above a breakpoint);
- on a fresh navigation with a #hash (not a reload or Back/Forward, where the browser restores
  the visitor's own position), it jumps to the section again after the fonts have loaded, just
  after window load (behind i18n.js, which may move the language menu then), and when a page that renders content late calls window.realignSectionLink() -
  never after the visitor has scrolled or pressed a key, never after 15 s.

Source of truth for the portfolio; copied into each site repo's scripts/ like i18n_common.py.
    python scripts/section_links.py <file.html> [...]   # insert or refresh the snippet
"""
import re
import sys
from pathlib import Path

BEGIN = "<!-- section-links -->"
END = "<!-- /section-links -->"

SNIPPET = BEGIN + """<script>
/* Section links (#pricing, ...): keep jumps clear of the sticky header, and land an arrival from
   another page again once late web fonts or late content have moved the page - on a fresh
   navigation only, never after the visitor has scrolled. Shared portfolio snippet
   (scripts/section_links.py). */
(function () {
  var root = document.documentElement, watched = [];
  var ro = window.ResizeObserver && new ResizeObserver(function () { pad(); });
  function pad() {  /* re-checked each time: some headers are sticky only above a breakpoint */
    var hdr = null;
    [].forEach.call(document.querySelectorAll('header, .page-header, .navbar, .site-nav'), function (h) {
      if (ro && watched.indexOf(h) < 0) { watched.push(h); ro.observe(h); }
      if (!hdr && /sticky|fixed/.test(getComputedStyle(h).position)) hdr = h;
    });
    root.style.scrollPaddingTop = hdr ? Math.ceil(hdr.getBoundingClientRect().height) + 8 + 'px' : '';
  }
  pad();
  document.addEventListener('DOMContentLoaded', pad);
  window.addEventListener('resize', pad);
  window.realignSectionLink = function () {};
  var id;
  try { id = decodeURIComponent(location.hash.slice(1)); } catch (e) { return; }
  if (!id) return;
  var nav = window.performance && performance.getEntriesByType && performance.getEntriesByType('navigation')[0];
  if (nav ? (nav.type === 'reload' || nav.type === 'back_forward')
          : (window.performance && performance.navigation && performance.navigation.type !== 0)) return;
  var moved = false;
  ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(function (ev) {
    window.addEventListener(ev, function () { moved = true; }, { passive: true, once: true });
  });
  function realign() {
    var el = document.getElementById(id);
    if (moved || !el || !el.getClientRects().length || performance.now() > 15000) return;
    if (getComputedStyle(el).position === 'fixed') return;  /* an open dialog, not a section */
    pad();
    var behavior = root.style.scrollBehavior;
    root.style.scrollBehavior = 'auto';  /* a jump, not a second smooth scroll */
    el.scrollIntoView({ block: 'start' });
    root.style.scrollBehavior = behavior;
  }
  window.realignSectionLink = realign;  /* pages that render content late call it afterwards */
  if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', realign);
  /* after the other load handlers (i18n.js may move the language menu then) */
  window.addEventListener('load', function () { setTimeout(realign, 0); });
})();
</script>""" + END

_BLOCK_RE = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)


def insert(html, after=(r"</header>", r"<body\b[^>]*>")):
    """Return html with the snippet refreshed in place, or inserted right after the first match of
    the first pattern in `after` that matches (default: the first </header>, else the <body> tag).
    Idempotent."""
    if BEGIN in html:
        return _BLOCK_RE.sub(lambda _m: SNIPPET, html, count=1)
    for pattern in ([after] if isinstance(after, str) else after):
        m = re.search(pattern, html)
        if m:
            return html[:m.end()] + "\n" + SNIPPET + html[m.end():]
    raise ValueError("no insertion point %r" % (after,))


def main(paths):
    for p in paths:
        path = Path(p)
        raw = path.read_bytes().decode("utf-8")
        eol = "\r\n" if "\r\n" in raw else "\n"
        new = insert(raw.replace("\r\n", "\n"))
        path.write_bytes(new.replace("\n", eol).encode("utf-8"))
        print("section-links:", p)


if __name__ == "__main__":
    main(sys.argv[1:])
