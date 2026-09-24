-- INCIDB Relational Schema (SQLite / PostgreSQL Compatible)

CREATE TABLE IF NOT EXISTS brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    -- NULLABLE on purpose: a source label with no brand recorded upstream gets
    -- brand_id NULL rather than a synthetic blank brand row (see
    -- DATA_DICTIONARY.md, "brand_id NULL = no brand on the source label").
    brand_id INTEGER,
    barcode_ean VARCHAR(50) UNIQUE,
    name VARCHAR(300) NOT NULL,
    -- The Open Beauty Facts `categories_tags` list for this product, joined
    -- with ';', VERBATIM. NULL when the source record carries none. The
    -- pre-rebuild `category` column was a hard-coded default plus a keyword
    -- heuristic with no per-row provenance -- a fabricated value -- and was
    -- dropped. Nothing here is normalised, translated or collapsed into a
    -- taxonomy of our own; that would only be a new guess.
    obf_categories_tags TEXT,
    raw_ingredient_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inci_name VARCHAR(255) NOT NULL UNIQUE,          -- canonical (CosIng-style upper-case)
    cosing_matched BOOLEAN,                          -- NULL until enrichment runs
    cosing_ref_no VARCHAR(20),
    cas_number VARCHAR(50),
    ec_number VARCHAR(50),
    functions TEXT,                                  -- ';'-separated CosIng functions
    chemical_description TEXT,
    cosing_restriction TEXT,
    cosing_update_date VARCHAR(10),
    annex_ii BOOLEAN, annex_iii BOOLEAN, annex_iv BOOLEAN, annex_v BOOLEAN, annex_vi BOOLEAN,
    is_common_allergen BOOLEAN,
    allergen_source VARCHAR(30),                     -- EU_ANNEX_III | FDA_MOCRA | BOTH
    comedogenic_rating INTEGER CHECK(comedogenic_rating BETWEEN 0 AND 5),
    is_fungal_acne_trigger BOOLEAN,
    rating_source TEXT                               -- citation for the two authored columns
);
CREATE TABLE IF NOT EXISTS ingredient_name_map (
    raw_name VARCHAR(255) NOT NULL,
    canonical_name VARCHAR(255) NOT NULL,
    method VARCHAR(20) NOT NULL,
    confidence REAL NOT NULL,
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(ingredient_id),
    part_index INTEGER NOT NULL,        -- 1-based order of this part within raw_name (1 when not cut)
    split_rule VARCHAR(120),            -- '+'-joined re-split rules; NULL when the token was not re-split
    PRIMARY KEY (raw_name, canonical_name)
);

-- Junction table mapping products to ingredients with exact order index
CREATE TABLE IF NOT EXISTS product_ingredients (
    product_id INTEGER NOT NULL,
    ingredient_id INTEGER NOT NULL,
    position_index INTEGER NOT NULL, -- 1 = first ingredient (highest concentration)
    concentration_percentage DECIMAL(5, 2) NULL,
    PRIMARY KEY (product_id, ingredient_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(ingredient_id)
);

-- EU fragrance allergens: Annex III labelling entries of Reg. (EC) 1223/2009 as amended by
-- Reg. (EU) 2023/1545 (corr. OJ L 2025/90876). One row per legal name x INCIDB match; legal
-- names with no match keep ingredient_id NULL. Review rows (botanical CAS hits) have flagged = 0.
CREATE TABLE IF NOT EXISTS fragrance_allergens (
    annex_iii_ref VARCHAR(10) NOT NULL,
    legal_name VARCHAR(255) NOT NULL,            -- column b as printed; LABEL_NAME rows carry column h
    label_as VARCHAR(100),                       -- collective label name from column h, else NULL
    cas_listed VARCHAR(255),
    ec_listed VARCHAR(255),
    leave_on_threshold_pct DECIMAL(6, 4),        -- 0.001 (percent) as printed
    rinse_off_threshold_pct DECIMAL(6, 4),       -- 0.01 (percent) as printed
    placing_on_market_until DATE,
    making_available_until DATE,
    transition_condition TEXT,
    instrument TEXT NOT NULL,
    ingredient_id INTEGER REFERENCES ingredients(ingredient_id),
    inci_name VARCHAR(255),
    match_method VARCHAR(30),                    -- NAME | LABEL_NAME | CAS | BOTANICAL_CAS_REVIEW
    flagged BOOLEAN NOT NULL,
    source VARCHAR(30) NOT NULL,                 -- EURLEX | COSING_ANNEX_III
    source_url TEXT NOT NULL,
    retrieved_at DATE NOT NULL
);

-- Regulatory status: one row per ingredient x jurisdiction x list entry. A row exists only
-- where a list says something; absence of a row is not a status.
CREATE TABLE IF NOT EXISTS regulatory_status (
    ingredient_id INTEGER NOT NULL REFERENCES ingredients(ingredient_id),
    inci_name VARCHAR(255) NOT NULL,
    cas VARCHAR(255),
    jurisdiction VARCHAR(10) NOT NULL,           -- EU (CA, ASEAN, CN reserved)
    list_ref VARCHAR(40) NOT NULL,               -- e.g. Annex III/98
    status VARCHAR(30) NOT NULL,                 -- PROHIBITED | RESTRICTED | ALLOWED_WITH_CONDITIONS | LISTED_EXISTING
    instrument TEXT,
    product_type TEXT,
    max_concentration TEXT,
    condition_text TEXT,
    effective_date DATE,                         -- only where the source states one
    match_method VARCHAR(30) NOT NULL,           -- NAME | IDENTIFIED_INGREDIENT | CAS
    source_url TEXT NOT NULL,
    retrieved_at DATE NOT NULL,
    source_update_date VARCHAR(10)
);

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_inci ON ingredients(inci_name);
CREATE INDEX IF NOT EXISTS idx_prod_ing_position ON product_ingredients(product_id, position_index);
