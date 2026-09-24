"""Cache-busting stamp for the shared stylesheet.

_headers serves /index.css as ``max-age=31536000, immutable``, so the only way a CSS
change reaches Cloudflare's edge and returning browsers is a new URL. Every page links
``index.css?v=<first 10 hex of the file's sha256>``; the generators call css_href(), the
hand-edited pages and sw.js are rewritten by ``stamp``.

    python scripts/css_version.py            # rewrite every stale reference in place
    python scripts/css_version.py --check    # exit 1 if any reference is stale (CI)

After editing index.css: run this, then ``scripts/i18n_common.py build`` and ``check``.
"""

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CSS = ROOT / "index.css"
SKIP_DIRS = {"venv", "node_modules", "data", "delivery", "kaggle_dataset", "docs", "SEO Optimisation"}

# href="index.css", "../index.css", "/index.css", optionally already carrying ?v=...
REF_RE = re.compile(r"""((?:href=["']|['"])(?:\.\./|/)?index\.css)(?:\?v=[0-9a-f]*)?(?=["'])""")


def css_version():
    # Hash with normalised line endings so a CRLF checkout (autocrlf) stamps the same
    # value as the LF blob CI checks out.
    return hashlib.sha256(CSS.read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:10]


def css_href(prefix=""):
    """Stylesheet URL for a generated page; prefix is "", "../" or "/"."""
    return f"{prefix}index.css?v={css_version()}"


def targets():
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in SKIP_DIRS]
        for f in filenames:
            if f.endswith(".html"):
                yield Path(dirpath) / f
    yield ROOT / "sw.js"


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--check", action="store_true", help="report stale references, change nothing")
    args = ap.parse_args(argv)
    v = css_version()
    stale = []
    for p in targets():
        raw = p.read_bytes().decode("utf-8")
        new = REF_RE.sub(lambda m: f"{m.group(1)}?v={v}", raw)
        if new != raw:
            stale.append(p.relative_to(ROOT).as_posix())
            if not args.check:
                p.write_bytes(new.encode("utf-8"))
    verb = "stale" if args.check else "stamped"
    print(f"index.css v={v}: {len(stale)} file(s) {verb}")
    for rel in stale[:10]:
        print(f"  {rel}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
