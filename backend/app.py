from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
import os
from datetime import datetime as dt

from services.ocr import read_receipt
from services.gemini_parser import extract_receipt_data
from services.product_lookup import search_product
from services.shelf_life import estimate_expiry_range, get_risk_label, get_receipt_age_info
from services.db import (
    init_db,
    save_user,
    get_user_by_email,
    save_receipt,
    get_receipt_history,
    get_receipt_by_id,
)
from services.reminder import check_and_send_reminders

load_dotenv()

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

init_db()

# Initialize background scheduler to run every 6 hours
scheduler = BackgroundScheduler(daemon=True)
scheduler.add_job(
    check_and_send_reminders,
    "interval",
    hours=6,
    id="smartpantry_reminders",
    replace_existing=True,
)
scheduler.start()


@app.route("/")
def home():
    return "SmartPantry backend is running with automated background reminders active."


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(force=True)

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    phone = (data.get("phone") or "").strip()
    password = data.get("password") or ""

    if not username or not email or not password:
        return jsonify({"error": "Username, email and password are required"}), 400

    if get_user_by_email(email):
        return jsonify({"error": "User already exists"}), 400

    password_hash = generate_password_hash(password)
    save_user(username, email, phone, password_hash)

    return jsonify({
        "message": "Registration successful",
        "user": {
            "username": username,
            "email": email,
            "phone": phone,
        },
    })


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(force=True)

    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify({
        "message": "Login successful",
        "user": {
            "username": user.get("username", ""),
            "email": user.get("email", ""),
            "phone": user.get("phone", ""),
        },
    })


@app.route("/me", methods=["GET"])
def me():
    email = (request.args.get("email") or "").strip().lower()
    user = get_user_by_email(email)

    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "phone": user.get("phone", ""),
    })


@app.route("/history", methods=["GET"])
def history():
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    return jsonify({"history": get_receipt_history(email)})


@app.route("/receipt/<receipt_id>", methods=["GET"])
def receipt_detail(receipt_id):
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    receipt = get_receipt_by_id(email, receipt_id)
    if not receipt:
        return jsonify({"error": "Receipt not found"}), 404

    return jsonify({"receipt": receipt})

# Update this route inside your app.py file

@app.route("/receipt/<receipt_id>", methods=["DELETE"])
def delete_receipt(receipt_id):
    email = (request.args.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    from services.db import delete_receipt_from_db
    
    try:
        # Executes the clean database delete sequence operation
        success = delete_receipt_from_db(email, receipt_id)
        
        if success:
            return jsonify({"success": True, "message": "Receipt deleted successfully from database."})
        else:
            return jsonify({"error": "Receipt not found or unauthorized to delete"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-receipt", methods=["POST"])
def upload_receipt():
    if "receipt" not in request.files:
        return jsonify({"error": "No file"}), 400

    file = request.files["receipt"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    user_email = (request.form.get("email") or "").strip().lower()
    if not user_email:
        return jsonify({"error": "Email is required"}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    file.save(filepath)

    try:
        ocr_text = read_receipt(filepath)
        parsed = extract_receipt_data(ocr_text)

        receipt = parsed.get("receipt", {})
        items = parsed.get("items", [])

        purchase_date = (receipt.get("purchase_date") or "").strip()

        receipt_warning = ""
        if purchase_date:
            receipt_age = get_receipt_age_info(purchase_date)
            receipt["purchase_date"] = receipt_age["purchase_date"]
            if receipt_age["is_old"]:
                receipt_warning = receipt_age["message"]
        else:
            receipt["purchase_date"] = ""

        generated_items = []

        for item in items:
            name = item.get("name", "").strip() or "Unknown item"
            brand = item.get("brand", "").strip() or "Generic"
            price = item.get("price", "").strip()
            category = item.get("category_guess", "").strip() or "Unknown"
            confidence = item.get("confidence", 0.0)

            shelf = estimate_expiry_range(receipt["purchase_date"], name, category)

            # --- DYNAMIC CALENDAR STATUS & VISUAL COLOR CODING ---
            try:
                expiry_date = dt.strptime(shelf["expiry_end"], "%Y-%m-%d").date()
                today = dt.utcnow().date()
                days_left = (expiry_date - today).days
            except Exception:
                days_left = shelf["max_days"]  # Fallback to general shelf life days if error parsing

            if days_left < 0:
                current_status = "expired"
                color_tag = "red"
                display_label = "Expired"
            elif 0 <= days_left <= 2:
                current_status = "active"
                color_tag = "red"
                display_label = "High Priority"
            elif 3 <= days_left <= 7:
                current_status = "active"
                color_tag = "yellow"
                display_label = "Use Soon"
            else:
                current_status = "active"
                color_tag = "green"
                display_label = "Fresh"
            # -----------------------------------------------------

            api_data = search_product(item.get("search_query") or name)

            nutrition_value = ""
            if api_data and api_data.get("nutrition_value"):
                nutrition_value = api_data["nutrition_value"]

            if not nutrition_value:
                nutrition_value = shelf["nutrition"]

            generated_items.append({
                "name": name,
                "brand": api_data.get("brand", brand) if api_data else brand,
                "price": price,
                "category": api_data.get("category", category) if api_data else category,
                "nutrition_value": nutrition_value,
                "storage": shelf["storage"],
                "estimated_shelf_life": f"{shelf['min_days']}–{shelf['max_days']} days",
                "estimated_expiry_start": shelf["expiry_start"],
                "estimated_expiry_end": shelf["expiry_end"],
                "risk_label": display_label,
                "color_tag": color_tag,
                "confidence": confidence,
                "hide_expiry": shelf["receipt_is_old"],
                "reminder_sent": False,
                "status": current_status,
            })

        # Priority sorting sequence update to include 'Expired' sorting bucket
        priority = {"High Priority": 0, "Use Soon": 1, "Fresh": 2, "Expired": 3}
        generated_items.sort(key=lambda x: priority.get(x["risk_label"], 9))

        save_receipt(user_email, receipt, generated_items)

        return jsonify({
            "receipt": receipt,
            "items": generated_items,
            "receipt_warning": receipt_warning,
        })

    except Exception as e:
        return jsonify({
            "error": str(e),
            "receipt": {
                "store_name": "",
                "store_address": "",
                "purchase_date": "",
                "receipt_total": "",
                "payment_method": "",
            },
            "items": [],
            "receipt_warning": "",
        }), 500


if __name__ == "__main__":
    app.run(debug=False)