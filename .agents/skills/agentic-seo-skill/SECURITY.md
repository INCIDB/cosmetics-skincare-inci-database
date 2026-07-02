# Security Policy

## Supported Versions

Security fixes target the `main` branch and the latest tagged release.

## Reporting a Vulnerability

Please do not open a public issue for vulnerabilities. Report security concerns through GitHub private vulnerability reporting if enabled for the repository, or contact the maintainer listed in the repository profile.

Include:

- Affected file, script, workflow, or installer.
- Steps to reproduce.
- Impact and realistic attack scenario.
- Any logs or proof-of-concept details that do not expose third-party secrets.

## Scope

In scope:

- Credential leakage risks.
- Unsafe URL fetching, SSRF, redirect, or TLS handling bugs.
- GitHub Actions permission or release-publishing risks.
- Installer behavior that writes outside the requested target.

Out of scope:

- SEO recommendations that are merely outdated unless they create a security risk.
- Rate-limit behavior against third-party APIs without data exposure.
- Reports requiring access to private systems you do not own.
