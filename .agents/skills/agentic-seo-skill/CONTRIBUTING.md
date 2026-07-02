# Contributing

Thanks for improving Agentic SEO Skill. This repository is a skill package: changes should keep the skill instructions, reference files, scripts, and installer behavior aligned.

## Development Workflow

1. Create a focused branch from `main`.
2. Keep edits scoped to the workflow you are changing.
3. Update README/SKILL inventory whenever files are added or removed.
4. Add or update `<!-- Updated: YYYY-MM-DD -->` markers when reference files change.
5. Run validation before opening a pull request:

```bash
python3 scripts/validate_skill_inventory.py
python3 scripts/reference_freshness.py resources/references --max-age-days 90
python3 -m compileall scripts
```

## Pull Request Expectations

- Describe the user-facing behavior change.
- List the exact validation commands you ran.
- Include sample output paths for generated reports when relevant.
- Do not commit secrets, local credentials, generated audit reports, screenshots, or virtual environments.

## Documentation and Reference Updates

Reference files in `resources/references/` must include a freshness marker:

```markdown
<!-- Updated: YYYY-MM-DD -->
```

When a Google, Schema.org, Core Web Vitals, GitHub, or AI crawler policy change affects guidance, update the affected reference within 7 days when possible.

## Script Changes

Prefer deterministic, offline tests where possible. Network scripts should use explicit timeouts, bounded retries, and clear error output so agents can report environment limitations instead of treating collection failures as SEO findings.
