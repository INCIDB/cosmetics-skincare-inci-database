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
    retail_price_usd DECIMAL(10, 2),
    raw_ingredient_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(brand_id)
);

CREATE TABLE IF NOT EXISTS ingredients (
    ingredient_id INTEGER PRIMARY KEY AUTOINCREMENT,
    inci_name VARCHAR(255) NOT NULL UNIQUE,
    cas_number VARCHAR(50),
    common_name VARCHAR(255),
    primary_function VARCHAR(150), -- e.g., 'Humectant', 'Preservative', 'UV Filter'
    comedogenic_rating INTEGER CHECK(comedogenic_rating BETWEEN 0 AND 5),
    is_common_allergen BOOLEAN DEFAULT 0,
    is_fungal_acne_trigger BOOLEAN DEFAULT 0,
    fda_warning VARCHAR(255),
    description TEXT
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
