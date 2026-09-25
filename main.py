import os
import io
import base64
import difflib
import uvicorn
import httpx
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import qrcode
from recommender import recommend_packaging

app = FastAPI(title="PackWisely AI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------------------
# COMPREHENSIVE AGRO & FOOD COMMODITY DATASET (CFTRI / ICAR / USDA Standard)
# -------------------------------------------------------------------------
COMMODITY_DATASET = {
    # FRUITS & FRESH PRODUCE
    "apple": {"name": "Fresh Apple", "moisture": 85.5, "fat": 0.2, "resp": 15.0, "temp": 4.0, "shelf": 30, "storage": "chilled"},
    "mango": {"name": "Fresh Mango (Alphonso)", "moisture": 83.5, "fat": 0.4, "resp": 30.0, "temp": 12.0, "shelf": 18, "storage": "chilled"},
    "banana": {"name": "Fresh Banana", "moisture": 75.0, "fat": 0.3, "resp": 40.0, "temp": 14.0, "shelf": 10, "storage": "ambient"},
    "strawberry": {"name": "Fresh Strawberry", "moisture": 91.0, "fat": 0.3, "resp": 45.0, "temp": 2.0, "shelf": 7, "storage": "chilled"},
    "grapes": {"name": "Fresh Table Grapes", "moisture": 81.0, "fat": 0.2, "resp": 18.0, "temp": 2.0, "shelf": 21, "storage": "chilled"},
    "guava": {"name": "Fresh Guava", "moisture": 83.0, "fat": 0.5, "resp": 25.0, "temp": 8.0, "shelf": 14, "storage": "chilled"},
    "papaya": {"name": "Fresh Papaya", "moisture": 88.0, "fat": 0.1, "resp": 28.0, "temp": 10.0, "shelf": 12, "storage": "chilled"},
    "orange": {"name": "Fresh Sweet Orange / Citrus", "moisture": 87.0, "fat": 0.2, "resp": 12.0, "temp": 6.0, "shelf": 28, "storage": "chilled"},
    "pomegranate": {"name": "Fresh Pomegranate Arils", "moisture": 78.0, "fat": 0.3, "resp": 10.0, "temp": 5.0, "shelf": 20, "storage": "chilled"},
    "litchi": {"name": "Fresh Litchi", "moisture": 82.0, "fat": 0.4, "resp": 22.0, "temp": 4.0, "shelf": 14, "storage": "chilled"},

    # VEGETABLES & TUBERS
    "potato": {"name": "Table Potatoes", "moisture": 79.0, "fat": 0.1, "resp": 6.0, "temp": 15.0, "shelf": 90, "storage": "ambient"},
    "onion": {"name": "Fresh Onions", "moisture": 89.0, "fat": 0.1, "resp": 7.0, "temp": 20.0, "shelf": 60, "storage": "ambient"},
    "tomato": {"name": "Fresh Tomatoes", "moisture": 94.5, "fat": 0.2, "resp": 20.0, "temp": 12.0, "shelf": 14, "storage": "ambient"},
    "spinach": {"name": "Fresh Spinach / Palak", "moisture": 91.5, "fat": 0.4, "resp": 60.0, "temp": 2.0, "shelf": 5, "storage": "chilled"},
    "mushroom": {"name": "Button Mushrooms", "moisture": 92.5, "fat": 0.3, "resp": 70.0, "temp": 3.0, "shelf": 6, "storage": "chilled"},
    "cauliflower": {"name": "Fresh Cauliflower Florets", "moisture": 92.0, "fat": 0.3, "resp": 25.0, "temp": 4.0, "shelf": 14, "storage": "chilled"},
    "capsicum": {"name": "Green Bell Pepper (Capsicum)", "moisture": 92.0, "fat": 0.2, "resp": 18.0, "temp": 8.0, "shelf": 16, "storage": "chilled"},
    "chilli": {"name": "Fresh Green Chillies", "moisture": 88.0, "fat": 0.4, "resp": 22.0, "temp": 8.0, "shelf": 14, "storage": "chilled"},
    "ginger": {"name": "Fresh Ginger Rhizomes", "moisture": 80.0, "fat": 0.8, "resp": 10.0, "temp": 14.0, "shelf": 45, "storage": "ambient"},
    "garlic": {"name": "Dry Garlic Bulbs", "moisture": 60.0, "fat": 0.5, "resp": 5.0, "temp": 18.0, "shelf": 120, "storage": "ambient"},
    "carrot": {"name": "Fresh Red Carrots", "moisture": 88.0, "fat": 0.2, "resp": 22.0, "temp": 2.0, "shelf": 28, "storage": "chilled"},

    # DRY NUTS, SEEDS & DRIED SNACKS
    "cashew": {"name": "Roasted Cashews", "moisture": 3.0, "fat": 46.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "kaju": {"name": "Roasted Cashews (Kaju)", "moisture": 3.0, "fat": 46.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "almond": {"name": "Raw & Roasted Almonds (Badam)", "moisture": 4.0, "fat": 50.0, "resp": 0.0, "temp": 25.0, "shelf": 240, "storage": "ambient"},
    "walnut": {"name": "Shelled Walnuts (Akhrot)", "moisture": 4.2, "fat": 65.0, "resp": 0.0, "temp": 18.0, "shelf": 180, "storage": "ambient"},
    "peanut": {"name": "Roasted Peanuts (Groundnut)", "moisture": 2.5, "fat": 48.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "makhana": {"name": "Popped Fox Nuts (Makhana)", "moisture": 8.0, "fat": 0.5, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "raisin": {"name": "Kismis / Dried Grapes", "moisture": 15.0, "fat": 0.5, "resp": 0.0, "temp": 22.0, "shelf": 270, "storage": "ambient"},
    "dates": {"name": "Dried Dates (Khajoor)", "moisture": 18.0, "fat": 0.4, "resp": 0.0, "temp": 22.0, "shelf": 300, "storage": "ambient"},

    # GRAINS, FLOURS & PULSES
    "rice": {"name": "Polished Basmati Rice", "moisture": 12.0, "fat": 0.8, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "wheat": {"name": "Whole Wheat Grain", "moisture": 11.5, "fat": 1.5, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "atta": {"name": "Whole Wheat Flour (Chakki Atta)", "moisture": 12.5, "fat": 2.0, "resp": 0.0, "temp": 25.0, "shelf": 120, "storage": "ambient"},
    "maida": {"name": "Refined Wheat Flour (Maida)", "moisture": 12.0, "fat": 1.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "dal": {"name": "Yellow Split Pulses (Moong/Arhar Dal)", "moisture": 10.0, "fat": 1.2, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "chana": {"name": "Whole Chickpeas / Bengal Gram", "moisture": 9.5, "fat": 5.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "besan": {"name": "Gram Flour (Besan)", "moisture": 10.5, "fat": 5.5, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "oats": {"name": "Rolled Breakfast Oats", "moisture": 8.5, "fat": 6.8, "resp": 0.0, "temp": 25.0, "shelf": 240, "storage": "ambient"},

    # PROCESSED PACKAGED SNACKS & BAKERY
    "chips": {"name": "Fried Potato Chips", "moisture": 2.0, "fat": 35.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "namkeen": {"name": "Bhujia / Sev Mixture Namkeen", "moisture": 2.5, "fat": 38.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "biscuit": {"name": "Sweet & Salty Bakery Biscuits", "moisture": 4.0, "fat": 19.0, "resp": 0.0, "temp": 25.0, "shelf": 240, "storage": "ambient"},
    "cookies": {"name": "Butter Cookies", "moisture": 3.8, "fat": 25.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "bread": {"name": "Sliced White / Brown Bread", "moisture": 36.0, "fat": 2.5, "resp": 0.0, "temp": 25.0, "shelf": 6, "storage": "ambient"},
    "rusk": {"name": "Crispy Toast Rusk", "moisture": 4.0, "fat": 10.0, "resp": 0.0, "temp": 25.0, "shelf": 180, "storage": "ambient"},
    "noodles": {"name": "Instant Fried Wheat Noodles", "moisture": 4.5, "fat": 17.0, "resp": 0.0, "temp": 25.0, "shelf": 270, "storage": "ambient"},
    "pasta": {"name": "Dry Durum Wheat Pasta", "moisture": 9.5, "fat": 1.2, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},

    # DAIRY, MEAT & POULTRY
    "paneer": {"name": "Fresh Dairy Paneer (Cottage Cheese)", "moisture": 54.0, "fat": 24.0, "resp": 0.0, "temp": 4.0, "shelf": 21, "storage": "chilled"},
    "milk": {"name": "Pasteurized Liquid Cow Milk", "moisture": 87.5, "fat": 3.8, "resp": 0.0, "temp": 4.0, "shelf": 3, "storage": "chilled"},
    "curd": {"name": "Fermented Curd / Dahi", "moisture": 86.0, "fat": 4.0, "resp": 0.0, "temp": 4.0, "shelf": 14, "storage": "chilled"},
    "cheese": {"name": "Processed Cheddar Cheese Block", "moisture": 38.0, "fat": 32.0, "resp": 0.0, "temp": 4.0, "shelf": 180, "storage": "chilled"},
    "butter": {"name": "Table Butter", "moisture": 16.0, "fat": 81.0, "resp": 0.0, "temp": 4.0, "shelf": 180, "storage": "chilled"},
    "ghee": {"name": "Clarified Butter Fat (Desi Ghee)", "moisture": 0.3, "fat": 99.5, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "milk powder": {"name": "Skimmed / Whole Milk Powder", "moisture": 3.5, "fat": 26.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "fish": {"name": "Fresh Frozen Fish Fillets", "moisture": 76.0, "fat": 4.5, "resp": 0.0, "temp": -18.0, "shelf": 180, "storage": "frozen"},
    "chicken": {"name": "Raw Chilled Chicken Breast", "moisture": 74.0, "fat": 3.0, "resp": 0.0, "temp": 2.0, "shelf": 7, "storage": "chilled"},
    "meat": {"name": "Dressed Fresh Mutton / Meat", "moisture": 72.0, "fat": 7.0, "resp": 0.0, "temp": 2.0, "shelf": 6, "storage": "chilled"},

    # SPICES, CONDIMENTS & PLANTATION CROPS
    "turmeric": {"name": "Dry Turmeric Powder (Haldi)", "moisture": 9.0, "fat": 5.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "red chilli": {"name": "Dry Red Chilli Powder", "moisture": 8.5, "fat": 12.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "pepper": {"name": "Black Whole Peppercorns", "moisture": 10.0, "fat": 3.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "cardamom": {"name": "Green Cardamom Pods (Elaichi)", "moisture": 9.5, "fat": 4.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "tea": {"name": "CTC Black Tea Leaves", "moisture": 6.5, "fat": 1.5, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},
    "coffee": {"name": "Roasted Ground Coffee Powder", "moisture": 4.0, "fat": 14.0, "resp": 0.0, "temp": 25.0, "shelf": 240, "storage": "ambient"},
    "honey": {"name": "Natural Raw Honey", "moisture": 17.5, "fat": 0.0, "resp": 0.0, "temp": 25.0, "shelf": 540, "storage": "ambient"},
    "pickle": {"name": "Traditional Mango Oil Pickle", "moisture": 45.0, "fat": 20.0, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"},

    # RTE / STERILIZED WET FOODS
    "curry": {"name": "Ready-to-Eat Cooked Vegetable Curry", "moisture": 72.0, "fat": 12.0, "resp": 0.0, "temp": 25.0, "shelf": 270, "storage": "ambient"},
    "jam": {"name": "Mixed Fruit Sweet Jam", "moisture": 32.0, "fat": 0.1, "resp": 0.0, "temp": 25.0, "shelf": 365, "storage": "ambient"}
}

USDA_API_KEY = os.environ.get("USDA_API_KEY", "fKgxafIiRmnI786e4h6aAioWYNJsDsKk07A94zo1")

class CommodityInput(BaseModel):
    commodity_name: str = Field(..., examples=["Roasted Cashews"])
    moisture_content: float = Field(..., examples=[3.0])
    fat_content: float = Field(..., examples=[44.0])
    ph_level: float = Field(default=6.5, examples=[6.5])
    respiration_rate: float = Field(..., examples=[0.0])
    desired_shelf_life_days: int = Field(..., examples=[180])
    storage_temp: float = Field(..., examples=[25.0])
    relative_humidity: float = Field(default=60.0, examples=[60.0])
    storage_type: str = Field(default="ambient", examples=["ambient"])

@app.get("/")
def read_root():
    return {"status": "PackWisely AI Engine is Online"}

@app.get("/api/v1/food-lookup")
async def lookup_food(query: str = Query(..., min_length=2)):
    q = query.lower().strip()
    
    # 1. Exact or substring matching in built-in dataset
    for key, data in COMMODITY_DATASET.items():
        if key in q or q in key:
            return {"success": True, **data}

    # 2. Fuzzy similarity matching (matches typos, plurals, slight variations)
    keys = list(COMMODITY_DATASET.keys())
    matches = difflib.get_close_matches(q, keys, n=1, cutoff=0.5)
    if matches:
        matched_key = matches[0]
        return {"success": True, **COMMODITY_DATASET[matched_key]}

    # 3. Comprehensive USDA Fallback if not found locally
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "api_key": USDA_API_KEY,
        "query": query,
        "pageSize": 5
    }
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                body = resp.json()
                foods = body.get("foods", [])
                if foods:
                    food_item = foods[0]
                    moisture, fat = None, None
                    for n in food_item.get("foodNutrients", []):
                        name = n.get("nutrientName", "").lower()
                        if "water" in name or "moisture" in name:
                            moisture = round(float(n.get("value", 0.0)), 1)
                        elif "total lipid" in name or "fat" in name:
                            fat = round(float(n.get("value", 0.0)), 1)
                    
                    return {
                        "success": True,
                        "name": food_item.get("description", query),
                        "moisture": moisture if moisture is not None else 10.0,
                        "fat": fat if fat is not None else 5.0,
                        "resp": 0.0,
                        "temp": 25.0,
                        "shelf": 90,
                        "storage": "ambient"
                    }
    except Exception:
        pass

    return {"success": False, "message": "No match found"}

@app.post("/api/v1/recommend")
def get_recommendation(payload: CommodityInput):
    data = payload.model_dump()
    result = recommend_packaging(data)
    
    qr_data = (
        f"PackWisely AI | Item: {data['commodity_name']} | "
        f"Rec: {result['primary_recommendation']['name']} | "
        f"OTR: {result['primary_recommendation']['recommended_spec']['recommended_otr']}"
    )
    qr = qrcode.make(qr_data)
    buffered = io.BytesIO()
    qr.save(buffered, format="PNG")
    qr_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    result["traceability_qr_base64"] = f"data:image/png;base64,{qr_base64}"
    return result

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
