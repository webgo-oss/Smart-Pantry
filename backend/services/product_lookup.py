import requests

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"

def format_nutrition(nutriments):
    if not isinstance(nutriments, dict):
        return ""

    parts = []

    def add(label, *keys):
        for key in keys:
            value = nutriments.get(key)
            if value not in (None, "", "null"):
                parts.append(f"{label}: {value}")
                return

    add("Calories", "energy-kcal_100g", "energy-kcal")
    add("Protein", "proteins_100g", "proteins")
    add("Fat", "fat_100g", "fat")
    add("Carbs", "carbohydrates_100g", "carbohydrates")
    add("Sugar", "sugars_100g", "sugars")
    add("Salt", "salt_100g", "salt")

    return ", ".join(parts)

def search_product(product_name):
    if not product_name:
        return None

    params = {
        "search_terms": product_name,
        "search_simple": 1,
        "action": "process",
        "json": 1,
        "page_size": 1
    }

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        if response.status_code != 200:
            return None

        data = response.json()
        if data.get("count", 0) == 0 or not data.get("products"):
            return None

        product = data["products"][0]
        nutriments = product.get("nutriments", {})

        return {
            "name": product.get("product_name", product_name),
            "brand": product.get("brands", ""),
            "category": product.get("categories", ""),
            "image": product.get("image_front_url", ""),
            "nutrition_value": format_nutrition(nutriments),
            "ingredients": product.get("ingredients_text", "")
        }

    except Exception:
        return None