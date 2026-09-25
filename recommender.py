import numpy as np
from materials_db import PACKAGING_MATERIALS

def determine_target_barriers(food_data: dict):
    moisture = food_data["moisture_content"]
    fat = food_data["fat_content"]
    resp = food_data["respiration_rate"]
    shelf_life = food_data["desired_shelf_life_days"]
    temp = food_data["storage_temp"]
    storage_type = food_data.get("storage_type", "ambient").lower()

    is_produce = resp > 5.0 or (moisture > 75 and fat < 3.0 and resp > 0.0)

    # 1. Target OTR (Oxygen Transmission Rate)
    if is_produce:
        # High respiration requires gas permeation to avoid fermentation
        target_otr = max(1500.0, resp * 120.0)
    elif fat > 25.0 or (fat > 12.0 and shelf_life > 90):
        # High-fat products undergo rapid rancidity; require low OTR
        target_otr = 1.0 if shelf_life > 120 else 5.0
    elif moisture > 60.0 and shelf_life > 60:
        # Wet, ready-to-eat ambient food needs near-zero OTR (sterilized retort)
        target_otr = 0.5
    elif fat < 5.0 and moisture < 12.0:
        # Dry low-fat grains / biscuits
        target_otr = 500.0
    else:
        target_otr = 100.0

    # 2. Target WVTR (Water Vapor Transmission Rate)
    if moisture < 6.0:
        # Very dry, hygroscopic products (wafers, roasted nuts, powders)
        target_wvtr = 1.2
    elif moisture < 15.0:
        # Biscuits, whole spices, tea
        target_wvtr = 4.0
    elif is_produce:
        # Fresh produce needs moderate moisture escape to prevent condensation & mold
        target_wvtr = 25.0
    elif moisture > 60.0 and storage_type != "ambient":
        # Chilled paneer / meat
        target_wvtr = 3.5
    else:
        target_wvtr = 8.0

    return target_otr, target_wvtr, is_produce

def recommend_packaging(food_data: dict):
    target_otr, target_wvtr, is_produce = determine_target_barriers(food_data)
    storage_type = food_data.get("storage_type", "ambient").lower()
    shelf_life = food_data["desired_shelf_life_days"]
    moisture = food_data["moisture_content"]
    fat = food_data["fat_content"]

    scored_candidates = []

    for mat in PACKAGING_MATERIALS:
        # Barrier 1: Fresh produce MUST use breathable films
        if is_produce and not mat["breathable"]:
            continue
        # Barrier 2: Non-produce items MUST NOT use breathable films
        if not is_produce and mat["breathable"]:
            continue
        # Barrier 3: Freezer condition suitability
        if storage_type == "frozen" and not mat["freezer_grade"]:
            continue

        # Logarithmic barrier divergence
        dist_otr = abs(np.log10(mat["otr"] + 1e-3) - np.log10(target_otr + 1e-3))
        dist_wvtr = abs(np.log10(mat["wvtr"] + 1e-3) - np.log10(target_wvtr + 1e-3))

        # Base score (max 85)
        base_score = 85.0 / (1.0 + (0.45 * dist_otr) + (0.55 * dist_wvtr))

        # Context-aware modifiers
        bonus = 0.0
        # High shelf-life bonus for low-transmission laminates
        if shelf_life >= 180 and mat["otr"] < 5.0 and mat["wvtr"] < 2.0:
            bonus += 8.0
        # Wet RTE curries / gravies
        if moisture > 65.0 and storage_type == "ambient" and mat["material_id"] == "RETORT_POUCH":
            bonus += 15.0
        # Bakery & biscuits
        if moisture < 6.0 and fat < 20.0 and mat["material_id"] == "BOPP_25u":
            bonus += 10.0
        # Fresh dairy paneer / meat
        if moisture > 50.0 and storage_type in ["chilled", "frozen"] and mat["material_id"] == "PA_PE_VACUUM":
            bonus += 12.0
        # Whole spices / tea
        if moisture < 12.0 and fat < 15.0 and mat["material_id"] == "KRAFT_PE_POUCH":
            bonus += 7.0

        final_score = min(99.0, round(base_score + bonus, 2))

        scored_candidates.append({
            **mat,
            "match_score": final_score,
            "recommended_spec": {
                "film_thickness": f"{mat['typical_thickness_um']} µm",
                "recommended_otr": f"{mat['otr']} cc/m²/day",
                "recommended_wvtr": f"{mat['wvtr']} g/m²/day",
                "map_suitability": "Yes" if mat["map_suitable"] else "No"
            }
        })

    scored_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    # Calculate MAP gas mixture
    map_composition = None
    if is_produce:
        map_composition = {"O2": "3-5%", "CO2": "5-8%", "N2": "87-92%"}
    elif fat > 20.0:
        map_composition = {"O2": "< 0.5%", "CO2": "20-30%", "N2": "70-80%"}
    elif moisture > 50.0 and storage_type == "chilled":
        map_composition = {"O2": "< 1.0%", "CO2": "30-40%", "N2": "60-70%"}

    return {
        "primary_recommendation": scored_candidates[0] if scored_candidates else PACKAGING_MATERIALS[0],
        "target_parameters_calculated": {
            "required_otr": round(target_otr, 2),
            "required_wvtr": round(target_wvtr, 2)
        },
        "map_gas_mix": map_composition,
        "all_ranked_options": scored_candidates[:3]
    }
