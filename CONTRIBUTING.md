# Contributing to INCIDB

First off, thank you for considering contributing to **INCIDB**! Whether you are a cosmetic chemist, data engineer, dermatological researcher, or mobile app builder, your contributions help maintain the gold standard for open cosmetic nomenclature and safety transparency.

---

## 1. How You Can Contribute

### Reporting Schema or Data Issues
If you notice a typo in an INCI compound name, an outdated CAS number, or a missing brand in our preview samples (`samples/`):
1. Check existing open [GitHub Issues](https://github.com/INCIDB/cosmetics-skincare-inci-database/issues) to avoid duplicate reports.
2. Open a new issue with clear descriptive details:
   * **Affected Field:** e.g., `ingredients.cas_number`
   * **Current Value vs. Expected Value:** e.g., `50-81-7` -> `50-81-8`
   * **Regulatory Citation:** Link to official EU CosIng, US FDA MoCRA, or PubChem monographs.

### Suggesting Schema Enhancements
If you have ideas for new columns (such as comedogenic breakdown by skin type or K-Beauty PAO shelf-life tracking):
* Open a **Feature Request** issue detailing the scientific rationale and sample data formats.

---

## 2. Submitting Pull Requests for Sample & Schema Updates

If you want to improve `DATA_DICTIONARY.md`, `SPEC.md`, or the sample datasets under `samples/`:

1. **Fork the Repository:** Create a fork under your GitHub account.
2. **Create a Feature Branch:**
   ```bash
   git checkout -b fix/cas-number-correction
   ```
3. **Make & Verify Your Changes:**
   * Ensure any CSV sample additions maintain exact pipe delimitation (`|`) without unescaped carriage returns (`\r` or `\n`).
   * Verify Parquet schema compatibility if updating sample Parquet files.
4. **Commit & Push:**
   ```bash
   git commit -m "fix(schema): correct CAS registry mapping for ascorbic acid derivatives"
   git push origin fix/cas-number-correction
   ```
5. **Open a Pull Request:** Provide a clear summary of your updates and cite relevant regulatory sources.

---

## 3. Commercial Dataset Additions & Partnerships

If you represent an international beauty brand or formulation lab and wish to ingest your product catalog directly into the INCIDB Core Database:
* Please email our data engineering team directly at `support@INCIDB.net`.
