-- INCIDB Relational Schema (SQLite / PostgreSQL Compatible)

CREATE TABLE IF NOT EXISTS brands (
    brand_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    brand_id INTEGER NOT NULL,
    barcode_ean VARCHAR(50) UNIQUE,
    name VARCHAR(300) NOT NULL,
    category VARCHAR(100), -- e.g., 'Cleanser', 'Moisturizer', 'Serum'
    raw_ingredient_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inci_name VARCHAR(255) NOT NULL UNIQUE,          -- canonical (CosIng-style upper-case)
    common_name VARCHAR(255),
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

CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand_id);
CREATE INDEX IF NOT EXISTS idx_ingredients_inci ON ingredients(inci_name);
CREATE INDEX IF NOT EXISTS idx_prod_ing_position ON product_ingredients(product_id, position_index);
