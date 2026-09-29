# Security Policy — INCIDB

## Reporting a vulnerability or data concern

We take the integrity of the INCIDB data seriously. If you discover any of the
following, please report it privately:

- A security vulnerability in the site ([incidb.dataengineered.io](https://incidb.dataengineered.io))
  or in anything published in this repository.
- A critical regulatory data error, such as a misclassified EU Annex II–VI
  restriction or a wrong EU fragrance-allergen flag.
- A data-privacy concern, or content that should be removed.
- Any suspected leak of the full (paid) dataset or pipeline source.

**Please email: incidb@dataengineered.io**

Do **not** open a public GitHub issue for security-sensitive reports. Ordinary
data corrections (a typo in an INCI name, an outdated CAS number) are welcome as
issues; see [`CONTRIBUTING.md`](CONTRIBUTING.md).

## What to include

- A clear description of the issue and its impact.
- Steps to reproduce (for site issues) or the affected `ingredient_id`,
  `inci_name` or `barcode_ean` (for data concerns).
- Your contact details if you'd like a response.

## Our commitment

- We aim to acknowledge reports within **5 business days**.
- We will keep you informed as we investigate and resolve the issue.
- We aim to ship a confirmed data correction in the next monthly snapshot.
- We will not pursue legal action against good-faith security research that
  respects user privacy and avoids service disruption or data destruction.

## Supported snapshots

INCIDB is released as monthly snapshots named `YYYY.MM`. Only the latest
snapshot receives corrections; earlier snapshots are superseded, not re-issued.

## Data files

- The CSV (pipe-delimited) and Apache Parquet files hold flat values only (text,
  numbers, true/false flags and dates): no macros, embedded scripts or
  executables.
- Before export, line breaks, carriage returns and tabs inside text fields are
  replaced by a single space, and each field is trimmed.

## Scope

This repository contains only a **public sample**, the site and its
documentation. It holds no credentials, no pipeline source and not the full
dataset. Reports about those (e.g. a suspected leak) are still very welcome via
the email above.
