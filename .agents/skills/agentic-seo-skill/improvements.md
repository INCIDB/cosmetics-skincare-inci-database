Audited `Bhanunamikaze/Agentic-SEO-Skill` on `main`. No changes were pushed.

One caveat: I focused on repository-internal correctness, feature gaps, script coverage, and implementation consistency. I could not verify live/current Google SEO rule changes because web search is disabled in this environment.

## Found issues first, with action plan

| Priority | Gap / issue                                                                                                          | Evidence                                                                                                                                                                                                                                          | Action plan                                                                                                                                                                                       |
| -------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | `pagespeed.py` has a control-flow bug that can prevent successful PSI responses from being parsed.                   | The script fetches PageSpeed data, then `break`s after `resp.json()`, while metric extraction appears after that success path. This can leave `performance_score`, `metrics`, and opportunities empty.                                            | Fix the retry loop so extraction runs after a successful response. Add fixture-based tests for field data, lab data, rate limit, timeout, and invalid JSON. Add desktop + mobile combined mode.   |
| P0       | `seo-page.md` gives wrong script commands for page analysis.                                                         | It says to run `scripts/parse_html.py "$URL" --json`, but `parse_html.py` treats positional input as a local file and only uses `--url` as the base URL for resolving links.                                                                      | Update docs to `fetch_page.py "$URL" --output /tmp/page.html` then `parse_html.py /tmp/page.html --url "$URL" --json`. Also add a real `parse_html.py --fetch <url>` option to reduce user error. |
| P0       | The skill promises required markdown audit artifacts, but the automated report path does not reliably generate them. | `SKILL.md` requires `FULL-AUDIT-REPORT.md` and `ACTION-PLAN.md` for audit/page flows.  `generate_report.py` primarily produces an HTML dashboard and internal scoring.                                                                            | Add `audit_runner.py` or extend `generate_report.py` with `--markdown`, `--action-plan`, and `--html` outputs. Make the required artifacts automatic.                                             |
| P0       | No dependency/project manifest found.                                                                                | README lists requirements manually, but direct checks found no `requirements.txt` or `pyproject.toml`; install docs only mention ad hoc `pip install requests beautifulsoup4`.                                                                    | Add `pyproject.toml`, `requirements.txt`, and optional extras: `playwright`, `lxml`, `pytest`, `ruff`. Make installs reproducible.                                                                |
| P0       | No proper CI quality gate exists beyond tag packaging.                                                               | The only workflow found packages releases on tag.                                                                                                                                                                                                 | Add CI for Python syntax, script `--help`, JSON smoke tests, unit tests, `ruff`, dependency install, and markdown inventory validation.                                                           |
| P1       | No dedicated sitemap scanner/generator despite a full sitemap sub-skill.                                             | `seo-sitemap.md` describes XML validation, sitemap indexes, 50k URL limits, lastmod checks, robots references, canonical/noindex/redirect validation, and generation.  I did not find a dedicated `sitemap_checker.py` or `sitemap_generator.py`. | Add `sitemap_checker.py` and `sitemap_generator.py`; wire them into `generate_report.py`, `seo-audit.md`, and README examples.                                                                    |
| P1       | Full audit says it crawls up to 500 pages, but the implementation is mostly shallow/single-page plus helper scripts. | `seo-audit.md` defines a 500-page crawl config with robots respect, redirects, concurrency, and delay.                                                                                                                                            | Add `crawl_audit.py`: sitemap-seeded crawler, robots-aware, canonical/noindex aware, duplicate title/meta/H1 detection, status-code matrix, crawl depth, orphan pages.                            |
| P1       | Scoring weights are inconsistent.                                                                                    | `SKILL.md` and `seo-audit.md` define canonical weights.   `generate_report.py` has its own category weights.                                                                                                                                      | Create `resources/config/scoring.json` and have scripts/docs reference one source of truth.                                                                                                       |
| P1       | Network safety is inconsistent across scripts.                                                                       | `fetch_page.py` has SSRF prevention for the initial URL.  `analyze_visual.py` also blocks private/internal IPs.  But several scripts fetch URLs directly without the same shared guard.                                                           | Add shared `scripts/lib/safe_http.py` and use it everywhere. Re-check redirect targets, limit response size, enforce timeouts, validate schemes, and block private/reserved/loopback IPs.         |
| P1       | `fetch_page.py` still uses the upstream project’s old user agent.                                                    | User-Agent says `ClaudeSEO/1.0; +https://github.com/AgriciDaniel/claude-seo`.                                                                                                                                                                     | Change to this repo’s identity, for example `AgenticSEOSkill/1.0 (+https://github.com/Bhanunamikaze/Agentic-SEO-Skill)`.                                                                          |
| P1       | `entity_checker.py` exposes `--kg-api-key` but does not appear to use it in the actual analysis.                     | The CLI accepts `--kg-api-key`; the checker runs Wikidata/Wikipedia/sameAs logic, but the KG key is not used for a Google KG API request.                                                                                                         | Either implement Google Knowledge Graph API lookup or remove the flag and docs. Also make Wikidata/Wikipedia recommendations conditional on entity notability.                                    |
| P1       | Hreflang validation needs a stronger BCP 47 parser.                                                                  | The script says ISO 639-1 + ISO 3166-1, but its valid language set includes non-two-letter examples and manually handles Chinese/script variants.                                                                                                 | Replace manual language/region sets with a BCP 47 validator. Support script subtags, sitemap index discovery, robots sitemap discovery, and batch return-tag verification.                        |
| P1       | Pre-commit shell script is not portable.                                                                             | `pre_commit_seo_check.sh` uses `grep -P`, which fails on many macOS/BSD grep environments.                                                                                                                                                        | Replace with a Python pre-commit validator or POSIX-compatible patterns. Add it to CI.                                                                                                            |
| ~~P1~~ Resolved | ~~Windows installer may fail because it requires `python3`.~~ Already fixed.                                  | `install.ps1` now provides `Resolve-Python` (lines 138-152) which tries `python3` → `python` → `py -3` and caches the resolved interpreter. The earlier `Require-Cmd -Cmd 'python3'` claim is stale.                                              | No action — leave entry for historical context; remove on next cleanup.                                                                                                                           |
| P1       | User-Agent identity is fragmented across scripts, not just `fetch_page.py`.                                          | At least 10 distinct UAs in use: `ClaudeSEO/1.0` (fetch_page.py), `SEOSkill/1.0`, `SEOBot/1.0`, `SEOSkill-GapAnalysis/1.0`, `SEOSkill-DupCheck/1.0`, `SEOSkill-Entity/1.0`, `SEOSkill-IndexNow/1.0`, `SEOSkill-hreflang/1.0`, `SEOSkill-LinkProfile/1.0`, `SEOSkill-GitHubAPI/1.0`. | Centralize a single `AgenticSEOSkill/<version> (+repo-url)` UA constant in `scripts/lib/safe_http.py` and reuse from every network script. Roll into the same Phase 1 task as the safe_http migration. |
| P1       | Inventory drift already on disk: docs claim 33 scripts; repo has 34.                                                 | `SKILL.md:14` and `README.md:3,32` say "33 scripts". `scripts/` contains 33 `.py` + `pre_commit_seo_check.sh` = 34 entries.                                                                                                                       | Fix the count now (either bump to 34 or exclude the shell script from the "scripts" total and say "33 scripts + 1 shell hook"). Treat as the seed case for `validate_skill_inventory.py`.         |
| P1       | Reference freshness rule is already violated by 4 reference files today.                                             | `SKILL.md:338` requires `<!-- Updated: YYYY-MM-DD -->` in every reference file. Missing from `eeat-framework.md`, `link-building.md`, `llm-audit-rubric.md`, `quality-gates.md`.                                                                  | Backfill the four headers in Phase 1 (one-line edits), separate from the Phase 5 `reference_freshness.py` automation task.                                                                        |
| P1       | `verify=False` is concrete, not generic.                                                                             | Only `scripts/broken_links.py:71` (HEAD) and `:76` (GET) ship with `verify=False`. No other script disables TLS verification.                                                                                                                     | Remove both `verify=False` flags when migrating `broken_links.py` to `safe_http.py`. Make `safe_http.py` default to `verify=True`.                                                                 |
| P1       | `scripts/` is not a Python package — sibling imports rely on `cwd`/`sys.path`.                                       | `pagespeed.py:27`, `entity_checker.py:408`, `gsc_checker.py:258`, `link_profile.py:304`, `github_api.py:34` all `from env_loader import ...`. No `scripts/__init__.py` exists.                                                                    | Decide before Phase 1: either turn `scripts/` into a real package (add `__init__.py`, install via `pyproject.toml`), or move helpers to a `scripts/lib/` package. The proposed `safe_http.py` needs this fixed to import cleanly. |
| P1       | Proposed dependency list omits Google API client libs needed today.                                                  | `gsc_checker.py:26-27` and `link_profile.py:267-268` import `google.oauth2.service_account` and `googleapiclient.discovery`. Improvements.md lists only `playwright`, `lxml`, `pytest`, `ruff` for the new manifest.                              | Add `google-auth` and `google-api-python-client` to `pyproject.toml`/`requirements.txt`, ideally under a `[gsc]` extra so the base install stays light.                                           |
| P2       | Pre-commit script file-pattern gap, beyond `grep -P`.                                                                | `pre_commit_seo_check.sh:23` only scans `html\|htm\|php\|jsx\|tsx\|vue\|svelte`. Modern stacks ship schema in `.md`/`.mdx`/`.astro`/`.njk`/`.liquid`.                                                                                              | When replacing with a Python pre-commit validator, expand the file-pattern set to cover Markdown-based site generators and Liquid/Nunjucks templates.                                             |
| P2       | CI tag trigger is too permissive — any tag publishes a public release.                                               | `.github/workflows/package-on-tag.yml` triggers on `tags: ["*"]`, so any non-release tag (e.g. `wip-foo`) will create a GitHub release with archive assets attached.                                                                              | Restrict the trigger to `v*` or `v[0-9]*` so only intentional release tags publish. Folds into the Phase 1 CI work.                                                                               |
| P2       | Several network scripts still ship without `timeout=`.                                                               | `gsc_checker.py`, `github_seo_report.py`, `github_community_health.py`, `github_repo_audit.py` do not pass `timeout=` to their HTTP calls.                                                                                                        | Migrate these to `safe_http.py` first (alongside `broken_links.py`) so timeout, redirect cap, scheme allowlist, and SSRF guard land in one pass.                                                  |
| P2       | Governance list omits Dependabot/CODEOWNERS/FUNDING.                                                                 | Existing P2 row covers `CONTRIBUTING`/`CODE_OF_CONDUCT`/`SECURITY`/`SUPPORT`/`CITATION`/templates. `.github/dependabot.yml`, `.github/CODEOWNERS`, `.github/FUNDING.yml` are also absent.                                                          | Add `.github/dependabot.yml` (Python + GitHub Actions ecosystems) and `CODEOWNERS`; treat `FUNDING.yml` as optional. Same Phase 1 governance task.                                                |
| P3       | UA rebrand must not collide with upstream attribution in README/LICENSE.                                             | `README.md:567,577` credit `AgriciDaniel/claude-seo`. `LICENSE:4` retains the upstream copyright line. The P1 UA rename should not be done by find/replacing the upstream name everywhere.                                                        | When renaming UAs, scope the change to operational identity only (UA strings, in-script `SEOSkill-*` labels). Leave the README "Credits / Attribution" section and `LICENSE` copyright intact.    |
| P2       | Visual analysis has placeholders that are not actually populated.                                                    | `analyze_visual.py` returns `overlapping_elements` and `text_overflow`, but current logic only checks H1/CTA/hero, viewport, horizontal scroll, and base font size.                                                                               | Implement overlap detection, text clipping, tap target spacing, contrast, sticky header obstruction, and screenshot annotations.                                                                  |
| P2       | `parse_html.py` is too shallow for modern audits.                                                                    | It extracts h1-h3, images, links, JSON-LD, OG/Twitter, word count, and hreflang.                                                                                                                                                                  | Add h4-h6, viewport, charset, `lang`, favicon, pagination links, resource hints, preload/preconnect, x-robots/header support through fetch context, and `@graph` schema extraction.               |
| P2       | Reference freshness rule is documented but not enforced.                                                             | `SKILL.md` says every reference file should contain `<!-- Updated: YYYY-MM-DD -->` and references older than 90 days should be flagged.                                                                                                           | Add `reference_freshness.py` and CI enforcement. Produce a freshness report for `resources/references/`.                                                                                          |
| P2       | `.gitignore` is too minimal.                                                                                         | Current ignore file only covers `scripts/__pycache__/`, `scripts/*.pyc`, `seo-report-*.html`, and `plan.md`.                                                                                                                                      | Add `.venv/`, `dist/`, `.pytest_cache/`, `.ruff_cache/`, coverage files, audit outputs, screenshot folders, `.env`, caches, and local credentials.                                                |
| P2       | Governance/trust files are missing.                                                                                  | `LICENSE` exists.  Direct root checks for `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, and `CITATION.cff` returned not found.                                                                                                          | Add `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `CITATION.cff`, issue templates, and PR template.                                                                       |
| P3       | GitHub search/discoverability for helper files is imperfect.                                                         | Repository code search did not surface `finding_verifier.py`, but direct fetch confirms it exists.  Same for `github_api.py`.                                                                                                                     | Add a script inventory table and `validate_skill_inventory.py` so README/SKILL counts and file lists stay accurate regardless of search indexing.                                                 |

## Important correction

I initially treated `finding_verifier.py` as possibly missing because repository search did not return it. Direct fetch confirms it exists, so I am not counting it as missing. It is still worth adding inventory validation because the search/indexing behavior made the repo harder to audit reliably.

## Follow-up audit (added later)

A second pass against the working tree found:

- The "Windows installer requires `python3`" P1 is **already resolved** in `install.ps1` via `Resolve-Python` (kept in the table struck-through for audit history).
- The UA fix is broader than `fetch_page.py` — ~10 distinct UA strings exist across the script set.
- The freshness rule is **already violated** by four reference files; this is a Phase 1 backfill, not a Phase 5 automation item.
- `verify=False` is localized to `broken_links.py` only — concrete fix target, not a sweeping audit.
- `scripts/` has no `__init__.py`; the proposed `scripts/lib/safe_http.py` needs a packaging decision first.
- The proposed `pyproject.toml` deps omit `google-auth` / `google-api-python-client` even though `gsc_checker.py` and `link_profile.py` import them today.
- CI tag trigger `"*"` will publish a release for any tag — tighten to `v*`.
- Governance list should also include `CODEOWNERS` and `.github/dependabot.yml`.
- "33 scripts" in `SKILL.md` / `README.md` is already off-by-one (34 on disk).
- The UA rebrand must explicitly preserve upstream attribution in `README.md` and the `LICENSE` copyright line.

## Missing features and scripts to add

### Core technical SEO scripts

| Script                       | What it should scan                                                                                                                                                                |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `audit_runner.py`            | One orchestrator that runs all selected scans and outputs JSON, `FULL-AUDIT-REPORT.md`, `ACTION-PLAN.md`, and optional HTML.                                                       |
| `crawl_audit.py`             | Full-site crawl with sitemap seeds, robots handling, canonical/noindex awareness, crawl depth, status codes, duplicate metadata, and orphan candidates.                            |
| `sitemap_checker.py`         | Discover sitemaps from robots and standard paths; validate XML, sitemap indexes, URL limits, status codes, redirects, noindex, canonical mismatch, HTTP URLs, and lastmod quality. |
| `sitemap_generator.py`       | Generate valid sitemap XML/index files from crawl results or a URL manifest.                                                                                                       |
| `indexability_matrix.py`     | Per-URL verdict: status, robots.txt, meta robots, x-robots-tag, canonical, sitemap inclusion, hreflang, redirects.                                                                 |
| `canonical_checker.py`       | Self/cross-domain canonicals, canonical chains, canonicalized URLs in sitemap, duplicates.                                                                                         |
| `x_robots_header_checker.py` | Header-level noindex/nofollow/noarchive/max-snippet directives.                                                                                                                    |
| `robots_path_tester.py`      | Test specific URLs against Googlebot, Bingbot, GPTBot, ClaudeBot, PerplexityBot, etc.                                                                                              |
| `url_quality.py`             | Slug length, uppercase URLs, parameters, trailing slash variants, duplicate paths, HTTP/HTTPS/www variants.                                                                        |
| `faceted_nav_audit.py`       | Detect crawl traps, parameter explosions, sort/filter URLs, canonical/noindex rules.                                                                                               |
| `javascript_render_audit.py` | Compare raw HTML vs rendered DOM for title, meta, canonical, links, schema, and body text.                                                                                         |

### Performance / Core Web Vitals scripts

| Script                         | What it should scan                                                                |
| ------------------------------ | ---------------------------------------------------------------------------------- |
| `lighthouse_runner.py`         | Optional local Lighthouse run for performance, SEO, accessibility, best-practices. |
| `lcp_subparts.py`              | TTFB, resource load delay, resource load duration, element render delay.           |
| `third_party_script_audit.py`  | Heavy tags, blocking scripts, long tasks, ad/analytics impact.                     |
| `font_audit.py`                | Font-display, preload, FOIT/FOUT risk, oversized font files.                       |
| `image_weight_audit.py`        | Image bytes, responsive images, AVIF/WebP opportunity, LCP candidate images.       |
| `cache_compression_checker.py` | Brotli/gzip, cache-control, ETag, immutable assets, Vary header.                   |
| `critical_request_chain.py`    | Render-blocking CSS/JS and preload/preconnect recommendations.                     |

### Content, E-E-A-T, AEO, and GEO scripts

| Script                        | What it should scan                                                                                        |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------- |
| `content_intent_matcher.py`   | Match title/H1/meta/body sections to target keyword and intent.                                            |
| `eeat_signal_checker.py`      | Author bios, credentials, editorial policy, about/contact, citations, first-hand experience markers.       |
| `freshness_checker.py`        | Published/modified dates, stale stats, schema `dateModified` mismatch.                                     |
| `topical_cluster_mapper.py`   | Hub/spoke structure, topic coverage, missing internal links.                                               |
| `content_decay_detector.py`   | Use GSC/exported data to find declining pages and striking-distance keywords.                              |
| `answer_block_scanner.py`     | Direct answer blocks, definitions, ordered lists, tables, snippet-ready formatting.                        |
| `citation_readiness.py`       | Source quality, factual claims with citations, author/entity signals for AI answers.                       |
| `ai_crawler_policy_matrix.py` | Robots + llms.txt alignment for GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Applebot-Extended, etc. |
| `llms_txt_generator.py`       | Generate a clean `/llms.txt` draft from site structure and priority URLs.                                  |

### Schema and rich-result scripts

| Script                         | What it should scan                                                                      |
| ------------------------------ | ---------------------------------------------------------------------------------------- |
| `schema_required_props.py`     | Required/recommended properties by schema type; validate `@graph`, nested entities, IDs. |
| `schema_template_generator.py` | Generate JSON-LD templates from detected site/page type.                                 |
| `schema_diff.py`               | Compare current schema to recommended schema and output exact changes.                   |
| `rich_results_guard.py`        | Warn on deprecated/restricted rich-result types and eligibility risks.                   |
| `product_schema_checker.py`    | Product, Offer, price, availability, shipping, returns, variants, ratings.               |
| `video_schema_checker.py`      | VideoObject, thumbnail, transcript, upload date, duration, embed indexability.           |

### Image, accessibility, and UX scripts

| Script                          | What it should scan                                                                            |
| ------------------------------- | ---------------------------------------------------------------------------------------------- |
| `image_inventory.py`            | Alt text, dimensions, byte size, lazy/eager loading, `srcset`, `sizes`, format, LCP candidate. |
| `a11y_seo_checker.py`           | Headings, landmarks, labels, alt text, contrast, tap targets.                                  |
| `mobile_render_checker.py`      | Viewport, horizontal scroll, clipping, sticky elements, mobile nav usability.                  |
| `visual_regression_snapshot.py` | Screenshot comparison between runs and viewport-level layout changes.                          |

### Links and crawl equity scripts

| Script                         | What it should scan                                                             |
| ------------------------------ | ------------------------------------------------------------------------------- |
| `anchor_text_audit.py`         | Internal anchor diversity, generic anchors, exact-match overuse, empty anchors. |
| `orphan_pages_from_sitemap.py` | Pages in sitemap that are not reachable from crawl.                             |
| `external_link_quality.py`     | Broken external links, redirects, nofollow/sponsored/ugc, low-trust patterns.   |
| `redirect_backlink_reclaim.py` | From backlink export, find backlinks pointing to 404s or long redirect chains.  |
| `log_file_analyzer.py`         | Server-log crawl budget, Googlebot hits, wasted crawl, status-code patterns.    |

### Local, ecommerce, and international SEO scripts

| Script                          | What it should scan                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------------ |
| `local_seo_checker.py`          | NAP consistency, LocalBusiness schema, service areas, GBP link, reviews, map embeds. |
| `review_schema_checker.py`      | Review/rating policy compliance and markup misuse.                                   |
| `collection_page_checker.py`    | Category copy, filter canonicalization, pagination, product-grid crawlability.       |
| `hreflang_sitemap_validator.py` | Full sitemap-index hreflang validation beyond only `/sitemap.xml`.                   |

### GitHub SEO scripts

| Script                           | What it should scan                                                                |
| -------------------------------- | ---------------------------------------------------------------------------------- |
| `repo_file_inventory.py`         | README, license, docs, examples, demos, governance files, workflows.               |
| `repo_release_seo.py`            | Release cadence, release titles, changelog quality, keyword-aligned release notes. |
| `repo_docs_site_checker.py`      | Homepage/docs URL availability, docs metadata, install CTA path.                   |
| `repo_social_preview_checker.py` | GitHub social preview image, description, topics, pinned repo readiness.           |
| `repo_topic_suggester.py`        | Topic gaps vs competitor repos and search-intent terms.                            |
| `github_weekly_scorecard.py`     | Weekly score snapshot from GitHub SEO scripts and traffic archives.                |

## SEO scan categories to add

The skill already covers a lot: technical SEO, content, schema, sitemap, images, GEO, AEO, links, programmatic SEO, competitors, hreflang, planning, GitHub SEO, and articles. The missing scan categories are mostly deeper automation and validation:

1. Full-site crawl and indexability matrix.
2. Sitemap XML validation and generation.
3. JavaScript-rendered SEO parity.
4. Canonical, noindex, x-robots, and robots path validation.
5. Page-type-specific thin content detection.
6. Duplicate title/meta/H1 detection across crawl.
7. Core Web Vitals subpart analysis.
8. Resource, cache, compression, and third-party script audits.
9. Accessibility checks that matter for SEO and UX.
10. Local SEO and ecommerce SEO.
11. Log-file crawl budget analysis.
12. GSC-driven content decay and keyword opportunity scans.
13. AI crawler policy + llms.txt generator.
14. GitHub SEO release/docs/social-preview scoring.
15. Baseline comparison and regression tracking.

## Recommended implementation phases after approval

### Phase 1 — Stabilize current skill claims

This should be done first because it fixes correctness and trust.

* Fix `pagespeed.py`.
* Fix `seo-page.md` command contract.
* Add `pyproject.toml`, `requirements.txt`, test fixtures, and CI.
* Add `audit_runner.py` or extend `generate_report.py` to produce required markdown artifacts.
* Unify scoring weights.
* Add `safe_http.py` and remove `verify=False` from `broken_links.py`.
* Migrate `gsc_checker.py`, `github_seo_report.py`, `github_community_health.py`, `github_repo_audit.py` onto `safe_http.py` to pick up timeouts/SSRF guard in one pass.
* Centralize the User-Agent: one `AgenticSEOSkill/<version>` constant reused by every network script (retires `SEOSkill-*`, `SEOBot`, `ClaudeSEO`).
* Decide `scripts/` packaging (proper package with `__init__.py` or `scripts/lib/` package) so the new `safe_http.py` import works regardless of CWD.
* Backfill `<!-- Updated: YYYY-MM-DD -->` headers in `eeat-framework.md`, `link-building.md`, `llm-audit-rubric.md`, `quality-gates.md`.
* Reconcile the "33 scripts" claim in `SKILL.md` / `README.md` with the actual file count (34).
* Restrict `package-on-tag.yml` trigger to `v*` so non-release tags don't publish.
* Add governance files (`CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `SUPPORT.md`, `CITATION.cff`, issue/PR templates, `CODEOWNERS`, `.github/dependabot.yml`) and improve `.gitignore`.

### Phase 2 — Add missing core SEO automation

* `sitemap_checker.py`
* `sitemap_generator.py`
* `crawl_audit.py`
* `indexability_matrix.py`
* `canonical_checker.py`
* `x_robots_header_checker.py`
* `javascript_render_audit.py`
* `image_inventory.py`

### Phase 3 — Add strategic scans

* `content_intent_matcher.py`
* `eeat_signal_checker.py`
* `freshness_checker.py`
* `answer_block_scanner.py`
* `citation_readiness.py`
* `local_seo_checker.py`
* `product_schema_checker.py`
* `log_file_analyzer.py`

### Phase 4 — Add GitHub SEO depth

* `repo_file_inventory.py`
* `repo_release_seo.py`
* `repo_docs_site_checker.py`
* `repo_social_preview_checker.py`
* `repo_topic_suggester.py`
* `github_weekly_scorecard.py`

### Phase 5 — Documentation and release polish

* Update README inventory and command examples.
* Add `CHANGELOG.md`.
* Add `validate_skill_inventory.py`.
* Add `reference_freshness.py`.
* Create a release tag after tests pass.
