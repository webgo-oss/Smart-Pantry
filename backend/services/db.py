from datetime import datetime
from os import getenv
from uuid import uuid4

from bson.objectid import ObjectId
from dotenv import load_dotenv
from pymongo import ASCENDING, DESCENDING, MongoClient

load_dotenv()

MONGO_URI = getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = getenv("DB_NAME", "smartpantry")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_col = db["users"]
receipts_col = db["receipts"]


def init_db():
    users_col.create_index("email", unique=True)
    receipts_col.create_index([("user_email", ASCENDING), ("created_at", DESCENDING)])


def save_user(username, email, phone, password_hash):
    users_col.update_one(
        {"email": email},
        {
            "$set": {
                "username": username,
                "email": email,
                "phone": phone,
                "password_hash": password_hash,
                "updated_at": datetime.utcnow(),
            },
            "$setOnInsert": {"created_at": datetime.utcnow()},
        },
        upsert=True,
    )


def get_user_by_email(email):
    return users_col.find_one({"email": email})


def save_receipt(user_email, receipt, items):
    normalized_items = []

    for item in items:
        normalized_items.append({
            **item,
            "item_id": item.get("item_id") or str(uuid4()),
            "reminder_sent": item.get("reminder_sent", False),
            "reminder_sent_at": item.get("reminder_sent_at"),
        })

    doc = {
        "user_email": user_email,
        "store_name": receipt.get("store_name", ""),
        "store_address": receipt.get("store_address", ""),
        "purchase_date": receipt.get("purchase_date", ""),
        "receipt_total": receipt.get("receipt_total", ""),
        "payment_method": receipt.get("payment_method", ""),
        "items": normalized_items,
        "created_at": datetime.utcnow(),
    }
    result = receipts_col.insert_one(doc)
    return str(result.inserted_id)


def get_receipt_history(user_email):
    rows = receipts_col.find({"user_email": user_email}).sort("created_at", DESCENDING)

    history = []
    for r in rows:
        history.append({
            "id": str(r["_id"]),
            "store_name": r.get("store_name", ""),
            "store_address": r.get("store_address", ""),
            "purchase_date": r.get("purchase_date", ""),
            "receipt_total": r.get("receipt_total", ""),
            "payment_method": r.get("payment_method", ""),
            "created_at": r.get("created_at").isoformat() if r.get("created_at") else "",
            "items": r.get("items", []),
        })

    return history


def get_receipt_by_id(user_email, receipt_id):
    try:
        doc = receipts_col.find_one({
            "_id": ObjectId(receipt_id),
            "user_email": user_email,
        })
    except Exception:
        return None

    if not doc:
        return None

    return {
        "id": str(doc["_id"]),
        "store_name": doc.get("store_name", ""),
        "store_address": doc.get("store_address", ""),
        "purchase_date": doc.get("purchase_date", ""),
        "receipt_total": doc.get("receipt_total", ""),
        "payment_method": doc.get("payment_method", ""),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else "",
        "items": doc.get("items", []),
    }


def get_receipts_for_reminders():
    rows = receipts_col.find({}).sort("created_at", DESCENDING)

    receipts = []
    for r in rows:
        receipts.append({
            "id": str(r["_id"]),
            "user_email": r.get("user_email", ""),
            "store_name": r.get("store_name", ""),
            "store_address": r.get("store_address", ""),
            "purchase_date": r.get("purchase_date", ""),
            "receipt_total": r.get("receipt_total", ""),
            "payment_method": r.get("payment_method", ""),
            "items": r.get("items", []),
            "created_at": r.get("created_at").isoformat() if r.get("created_at") else "",
        })

    return receipts


def mark_item_reminded(receipt_id, item_id):
    try:
        oid = ObjectId(receipt_id)
    except Exception:
        return False

    result = receipts_col.update_one(
        {"_id": oid, "items.item_id": item_id},
        {
            "$set": {
                "items.$.reminder_sent": True,
                "items.$.reminder_sent_at": datetime.utcnow(),
            }
        },
    )
    return result.modified_count > 0

# Append this function to your services/db.py file

def update_item_status(receipt_id, item_id, new_status):
    """
    Finds a receipt by its unique ID and updates a specific nested item's status
    to 'expired' or 'consumed'.
    """
    from services.db import db # Ensure your global db connection object is accessible
    
    try:
        result = db.receipts.update_one(
            {"id": receipt_id, "items.item_id": item_id},
            {"$set": {"items.$.status": new_status}}
        )
        return result.modified_count > 0
    except Exception as e:
        print(f"Database error updating status for item {item_id}: {e}")
        return False

def delete_receipt_from_db(email, receipt_id):
    """
    Permanently deletes a specific receipt from the collection matching 
    the owner's email and unique receipt identifier.
    """
    from services.db import db # Ensure your global Mongo db connection is accessible
    
    try:
        # Build query filtering by user to ensure security boundaries
        query = {"user_email": email}
        
        # Check if matching standard string ID or a MongoDB native ObjectId
        if db.receipts.find_one({"_id": receipt_id}):
            query["_id"] = receipt_id
        else:
            try:
                query["_id"] = ObjectId(receipt_id)
            except Exception:
                query["id"] = receipt_id

        result = db.receipts.delete_one(query)
        return result.deleted_count > 0
    except Exception as e:
        print(f"Database execution error during receipt deletion: {e}")
        return False