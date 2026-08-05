# Security Policy — INCIDB

## Supported Versions

Only the latest major data release (v1.0.x) receives active security audits, regulatory synchronization, and data hygiene updates.

| Version | Supported          | Status |
| ------- | ------------------ | ------ |
| 1.0.x   | :white_check_mark: | Active Production Release |
| < 1.0   | :x:                | Deprecated Alpha Pre-releases |

---

## Reporting a Vulnerability or Data Anomaly

If you discover a potential security issue, pipeline vulnerability, or critical regulatory data discrepancy (such as a misclassified EU CosIng chemical restriction or FDA MoCRA allergen flag), please follow responsible disclosure protocols:

1. **DO NOT open a public GitHub issue** for sensitive security flaws or potential data integrity exploits.
2. **Email the INCIDB Security Team directly at:** `incidb@proton.me`.
3. Include clear reproduction steps, affected INCI compound IDs or EAN barcodes, and your contact details.

### Response Timeline
* **Initial Acknowledgement:** Within 24 hours.
* **Triage & Audit Verification:** Within 72 hours.
* **Patch / Data Correction Release:** Issued in the immediate bi-weekly data update cycle.

---

## Dataset Hygiene & Execution Safeguards

INCIDB adheres to strict data engineering security practices:
* **No Active Payloads:** All CSV (`|`) and Apache Parquet (`pyarrow`) files contain strictly flat scalar primitives (`STRING`, `INTEGER`, `FLOAT`). They contain zero macros, embedded scripts, or executable binaries.
* **Sanitization Audits:** All string fields undergo automated stripping of unescaped carriage returns (`\r`), control characters, and multiline linebreaks (`\n`) prior to release.
* **Cryptographic Checksums:** Official commercial release packages ship with SHA-256 validation hashes to prevent tampering during transfer.
