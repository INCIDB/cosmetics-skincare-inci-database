# Changelog

All notable changes to this project should be documented here.

## v3.0.1 - 2026-05-15

### Changed

- Expanded the GitHub Wiki with installation, example prompts, report generation, troubleshooting, and script inventory guidance.
- Shortened the README script inventory and linked to the full wiki inventory.
- Updated README credits wording to reflect inspiration from `claude-seo` while documenting this repository as an independently evolved package.

### Fixed

- Suppressed noindex pages from actionable thin-content and duplicate-content findings.
- Treated Next.js responsive fill images as dimension-safe in image inventory checks.
- Fixed readability paragraph counting for normal HTML paragraph tags.
- Normalized reference freshness markers so UTC CI runners do not flag same-day updates as future dates.

## v3.0.0 - 2026-05-15

### Added

- CI workflow for Python syntax compilation, inventory validation, and reference freshness checks.
- Inventory validator for README/SKILL/script drift.
- Reference freshness validator for `resources/references/`.
- Governance files: contributing guide, code of conduct, security policy, support guide, citation metadata, issue templates, pull request template, CODEOWNERS, and Dependabot configuration.

### Changed

- Documented script inventory now reflects 89 scripts: 88 Python scripts plus one shell helper.
- Release packaging workflow now only publishes for `v*` tags.
- `.gitignore` now excludes common Python caches, build output, generated SEO reports, screenshots, traffic archives, and local credentials.

### Fixed

- Added missing freshness markers to reference files that lacked `<!-- Updated: YYYY-MM-DD -->`.
