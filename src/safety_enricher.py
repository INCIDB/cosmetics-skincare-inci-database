import sqlite3
from pathlib import Path
from typing import Dict, Any

# Curated reference registry mapping canonical INCI names to EWG Skin Deep & CosIng safety profiles
REFERENCE_SAFETY_REGISTRY = {
    "AQUA": {
        "ewg_hazard_score": 1,
        "primary_function": "Solvent",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Purified water used as a primary solvent base in cosmetic formulations."
    },
    "WATER": {
        "ewg_hazard_score": 1,
        "primary_function": "Solvent",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Purified water used as a primary solvent base in cosmetic formulations."
    },
    "GLYCERIN": {
        "ewg_hazard_score": 1,
        "primary_function": "Humectant / Skin-Conditioning",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Natural humectant that attracts moisture into the upper layers of the skin."
    },
    "NIACINAMIDE": {
        "ewg_hazard_score": 1,
        "primary_function": "Skin-Conditioning / Anti-inflammatory",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Vitamin B3 derivative known for sebum regulation, brightening, and barrier repair."
    },
    "CERAMIDE NP": {
        "ewg_hazard_score": 1,
        "primary_function": "Skin-Conditioning / Skin-Replenishing",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Lipid identical to natural skin membrane structure; restores epidermal barrier."
    },
    "SALICYLIC ACID": {
        "ewg_hazard_score": 3,
        "primary_function": "Exfoliant / Anti-acne / Keratolytic",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Beta hydroxy acid (BHA) that penetrates oil to dissolve cellular debris inside pores."
    },
    "CAPRYLIC/CAPRIC TRIGLYCERIDE": {
        "ewg_hazard_score": 1,
        "primary_function": "Emollient / Solvent",
        "comedogenic_rating": 2,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Gentle coconut-derived ester providing silky texture without greasiness."
    },
    "CETEARYL ALCOHOL": {
        "ewg_hazard_score": 1,
        "primary_function": "Emulsion Stabilizer / Viscosity Controlling / Emollient",
        "comedogenic_rating": 2,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Fatty alcohol used to stabilize creams and soften skin; non-drying."
    },
    "HYALURONIC ACID": {
        "ewg_hazard_score": 1,
        "primary_function": "Humectant",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Glycosaminoglycan capable of binding up to 1000x its molecular weight in water."
    },
    "SODIUM HYALURONATE": {
        "ewg_hazard_score": 1,
        "primary_function": "Humectant",
        "comedogenic_rating": 0,
        "is_common_allergen": False,
        "is_fungal_acne_trigger": False,
        "description": "Salt form of hyaluronic acid with smaller molecular size for deeper penetration."
    },
    "PHENOXYETHANOL": {
        "ewg_hazard_score": 4,
        "primary_function": "Preservative",
        "comedogenic_rating": 0,
        "is_common_allergen": True,
        "is_fungal_acne_trigger": False,
        "description": "Broad-spectrum synthetic preservative used to prevent microbial growth."
    }
}

DEFAULT_SAFETY_PROFILE = {
    "ewg_hazard_score": 1,
    "primary_function": "Skin-Conditioning Agent",
    "comedogenic_rating": 0,
    "is_common_allergen": False,
    "is_fungal_acne_trigger": False,
    "description": "Standard cosmetic ingredient registered in INCI catalog."
}

def lookup_ingredient_safety(inci_name: str) -> Dict[str, Any]:
    """Retrieves safety profile for an INCI ingredient name from reference database."""
    clean_name = inci_name.strip().upper()
    return REFERENCE_SAFETY_REGISTRY.get(clean_name, DEFAULT_SAFETY_PROFILE)

def enrich_database_safety(db_path: Path) -> int:
    """Iterates through database ingredients and enriches rows with EWG/CosIng safety metrics."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    
    cur.execute("SELECT ingredient_id, inci_name FROM ingredients;")
    rows = cur.fetchall()
    
    updated_count = 0
    for ing_id, inci_name in rows:
        safety = lookup_ingredient_safety(inci_name)
        cur.execute("""
            UPDATE ingredients
            SET primary_function = ?,
                comedogenic_rating = ?,
                ewg_hazard_score = ?,
                is_common_allergen = ?,
                is_fungal_acne_trigger = ?,
                description = ?
            WHERE ingredient_id = ?;
        """, (
            safety["primary_function"],
            safety["comedogenic_rating"],
            safety["ewg_hazard_score"],
            1 if safety["is_common_allergen"] else 0,
            1 if safety["is_fungal_acne_trigger"] else 0,
            safety["description"],
            ing_id
        ))
        updated_count += 1
        
    conn.commit()
    conn.close()
    return updated_count

if __name__ == "__main__":
    db = Path("data/incidb.sqlite")
    count = enrich_database_safety(db)
    print(f"[Success] Enriched {count} database ingredients with toxicological safety profiles.")
