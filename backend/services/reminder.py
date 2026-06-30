from datetime import datetime, datetime as dt
from services.db import get_receipts_for_reminders, get_user_by_email, mark_item_reminded, update_item_status
from services.notification import send_email, send_sms, create_email, create_sms

def check_and_send_reminders():
    print(f"[{datetime.now()}] Running automated expiry check...")
    
    # 1. Fetch all active receipts across users
    receipts = get_receipts_for_reminders()
    
    for receipt in receipts:
        user_email = receipt.get("user_email")
        receipt_id = receipt.get("id") or receipt.get("_id") # Handles standard or MongoDB IDs
        
        if not user_email:
            continue
            
        expiring_items = []
        
        for item in receipt.get("items", []):
            # Skip if the user already manually marked it as consumed or it's already expired
            if item.get("status") in ["consumed", "expired"]:
                continue
                
            expiry_end_str = item.get("estimated_expiry_end")
            if not expiry_end_str:
                continue
                
            try:
                # Parse expiration date (assumed format: YYYY-MM-DD)
                expiry_date = dt.strptime(expiry_end_str.strip(), "%Y-%m-%d").date()
                today = dt.utcnow().date()
                
                # Calculate days remaining until expiry
                days_left = (expiry_date - today).days
                
                # --- AUTO-ARCHIVE IF PASSED EXPIRY ---
                if days_left < 0:
                    item_id = item.get("item_id")
                    if item_id:
                        update_item_status(receipt_id, item_id, "expired")
                        print(f"-> Auto-archived '{item.get('name')}'. Expired on {expiry_end_str} ({abs(days_left)} days ago).")
                    continue
                # -------------------------------------
                
                # Threshold: Send reminder if item is expiring today or within the next 2 days
                if 0 <= days_left <= 2 and not item.get("reminder_sent"):
                    expiring_items.append(item)
                    
            except Exception as e:
                print(f"Error parsing date for item {item.get('name')}: {e}")
                continue
        
        # 2. Send alerts if items are expiring soon
        if expiring_items:
            user = get_user_by_email(user_email)
            if not user:
                continue
                
            phone = user.get("phone")
            
            # Send Email
            email_subject = f"SmartPantry Alert: Items expiring soon from {receipt.get('store_name', 'Pantry')}"
            email_body = create_email(receipt, expiring_items)
            email_result = send_email(user_email, email_subject, email_body)
            
            # Send SMS
            sms_message = create_sms(receipt, expiring_items)
            sms_result = send_sms(phone, sms_message) if phone else {"success": False}
            
            # 3. Mark items as 'reminded' in DB if notification succeeded
            if email_result.get("success") or sms_result.get("success"):
                for item in expiring_items:
                    item_id = item.get("item_id")
                    if item_id:
                        mark_item_reminded(receipt_id, item_id)
                        print(f"Successfully sent reminder for '{item.get('name')}'.")