from datetime import datetime, timedelta

def parse_purchase_date(date_str):
    if not date_str:
        return None

    formats = [
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%Y/%m/%d",
        "%d/%m/%y",
        "%m/%d/%y",
        "%y/%m/%d",
        "%y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass

    return None


def get_receipt_age_info(purchase_date_str):
    purchase_date = parse_purchase_date(purchase_date_str)

    if purchase_date is None:
        return {
            "is_old": False,
            "days_old": None,
            "purchase_date": "",
            "message": ""
        }

    current_year = datetime.now().year
    allowed_years = {current_year, current_year - 1}

    # Only current year and previous year are valid
    if purchase_date.year not in allowed_years:
        return {
            "is_old": True,
            "days_old": None,
            "purchase_date": purchase_date.strftime("%Y-%m-%d"),
            "message": f"Old receipt detected. Only {current_year - 1} and {current_year} receipts are supported."
        }

    days_old = (datetime.now() - purchase_date).days

    return {
        "is_old": False,
        "days_old": days_old,
        "purchase_date": purchase_date.strftime("%Y-%m-%d"),
        "message": ""
    }


def get_shelf_life_days(item_name: str, category: str) -> int:
    text = f"{item_name} {category}".lower()

    if any(word in text for word in ["milk", "curd", "yogurt", "butter", "paneer", "cheese"]):
        return 7

    if any(word in text for word in ["egg", "eggs"]):
        return 21

    if any(word in text for word in ["bread", "bun", "bakery", "cake", "pastry"]):
        return 5

    if any(word in text for word in ["fruit", "apple", "banana", "orange", "grape"]):
        return 7

    if any(word in text for word in ["vegetable", "spinach", "lettuce", "tomato", "potato"]):
        return 5

    if any(word in text for word in ["coffee", "tea"]):
        return 365

    if any(word in text for word in ["chocolate", "candy", "biscuit", "cookies", "snack", "chips"]):
        return 180

    if any(word in text for word in ["rice", "pasta", "flour", "atta", "dal", "lentil"]):
        return 365

    return 30


def estimate_expiry_range(purchase_date_str: str, item_name: str, category: str = ""):
    receipt_info = get_receipt_age_info(purchase_date_str)
    purchase_dt = parse_purchase_date(receipt_info["purchase_date"]) or datetime.now()
    days = get_shelf_life_days(item_name, category)

    min_expiry = purchase_dt + timedelta(days=max(days - 2, 1))
    max_expiry = purchase_dt + timedelta(days=days)

    return {
        "min_days": max(days - 2, 1),
        "max_days": days,
        "storage": "Check Package",
        "nutrition": "Varies by product",
        "expiry_start": min_expiry.strftime("%Y-%m-%d"),
        "expiry_end": max_expiry.strftime("%Y-%m-%d"),
        "receipt_is_old": receipt_info["is_old"],
        "receipt_days_old": receipt_info["days_old"],
        "receipt_message": receipt_info["message"]
    }


def get_risk_label(max_days):
    if max_days <= 7:
        return "High Priority"
    if max_days <= 14:
        return "Use Soon"
    return "Fresh"