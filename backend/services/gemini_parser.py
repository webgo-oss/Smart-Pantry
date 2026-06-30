import os
import json
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Note: In your main app, ensure your environment variable name matches (GEMINI_API_KEY vs os.getenv)
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

PROMPT = """
You are an AI receipt parser for a food expiry app.

Your task:
1. Extract store details from the receipt.
2. Extract all grocery or food items.
3. Correct OCR mistakes.
4. Detect the purchase date. Look closely for fields like "DATE", "INV DATE", "25/06/2026", "06-25-2026", etc. 
5. CRITICAL DATE RULE: Format the 'purchase_date' strictly as "YYYY-MM-DD". If the purchase date cannot be definitively identified, leave it as an empty string "".
6. Ignore card expiry, authorization dates, statement dates, and clubcard dates.
"""

def extract_receipt_data(ocr_text: str) -> dict:
    try:
        # Define the exact JSON schema using the SDK's type system to guarantee response format
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=PROMPT + "\n\nReceipt text:\n" + ocr_text,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "receipt": {
                            "type": "OBJECT",
                            "properties": {
                                "store_name": {"type": "STRING"},
                                "store_address": {"type": "STRING"},
                                "purchase_date": {"type": "STRING", "description": "Strictly formatted as YYYY-MM-DD or left blank"},
                                "receipt_total": {"type": "STRING"},
                                "payment_method": {"type": "STRING"}
                            },
                            "required": ["store_name", "store_address", "purchase_date", "receipt_total", "payment_method"]
                        },
                        "items": {
                            "type": "ARRAY",
                            "items": {
                                "type": "OBJECT",
                                "properties": {
                                    "name": {"type": "STRING"},
                                    "brand": {"type": "STRING"},
                                    "price": {"type": "STRING"},
                                    "category_guess": {"type": "STRING"},
                                    "search_query": {"type": "STRING"},
                                    "confidence": {"type": "NUMBER"}
                                },
                                "required": ["name", "brand", "price", "category_guess", "search_query", "confidence"]
                            }
                        }
                    },
                    "required": ["receipt", "items"]
                }
            )
        )
        
        # With response_mime_type="application/json", response.text is guaranteed valid raw JSON
        return json.loads(response.text)

    except Exception as e:
        print(f"Error calling Gemini API or parsing response: {e}")
        # Graceful fallback data structure so app.py doesn't crash
        return {
            "receipt": {
                "store_name": "",
                "store_address": "",
                "purchase_date": "",
                "receipt_total": "",
                "payment_method": ""
            },
            "items": []
        }