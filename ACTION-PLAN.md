# Prioritized SEO & GEO Action Plan — INCIDB
**Target:** `https://incidb.net/`  
**Status:** All technical SEO and agentic metadata have been integrated locally into `index.html`, `robots.txt`, `sitemap.xml`, and `llms.txt`.

---

## 🚀 Priority 1: High-Impact Deployment (Immediate)

### 1. Host Static Files on Production Domain (`https://incidb.net/`)
* **Task:** Deploy `index.html`, `index.css`, `favicon.svg`, `robots.txt`, `sitemap.xml`, and `llms.txt` to AWS S3 / Cloudflare Pages / Vercel.
* **Why:** Enables Google Search Console indexing, AI bot discovery (`GPTBot`, `ClaudeBot`), and Google Dataset Search rich snippets.

### 2. Configure HTTP Security & Caching Headers
* **Task:** Add the following response headers on your CDN/web server:
  ```http
  Strict-Transport-Security: max-age=31536000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Cache-Control: public, max-age=3600
  ```
* **Why:** Boosts Core Web Vitals performance and technical security trust scores.

---

## 📈 Priority 2: Ongoing Growth & Client Conversion

### 3. Submit Sitemap to Google Search Console & Bing Webmaster Tools
* **Task:** Register `https://incidb.net/sitemap.xml` directly in Google Search Console.
* **Why:** Accelerates discovery of data documentation pages (`DATA_DICTIONARY.md`, `SPEC.md`, `pricing_plan.md`).

### 4. Publish Sample Datasets to GitHub Release Tags
* **Task:** Attach `samples/products.csv` and `samples/products_sample.parquet` as release assets on GitHub (`v1.0.0`).
* **Why:** Attracts organic star growth and inbound backlink authority from data science community repositories.
