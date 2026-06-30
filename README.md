# SmartPantry

SmartPantry is a receipt-based pantry tracker that scans grocery receipts, extracts store and item details, estimates expiry dates, and sends reminders for items that are about to expire.

## Features

- User registration and login
- Receipt upload and OCR text extraction
- AI-powered receipt parsing using Gemini
- Grocery item categorization and expiry estimation
- Receipt history with full receipt detail view
- Delete saved receipts from history
- Automated expiry reminder checks with scheduler
- Email and SMS notification support
- Product lookup from OpenFoodFacts

## Tech Stack

**Frontend**
- HTML
- CSS
- JavaScript

**Backend**
- Flask
- Flask-CORS
- APScheduler
- EasyOCR
- OpenCV
- Google Gemini API
- MongoDB / PyMongo
- Twilio
- SMTP email support

## Project Structure

```bash
recipt/
├── backend/
│   ├── app.py
│   ├── requirements.txt
│   ├── services/
│   │   ├── db.py
│   │   ├── expiry.py
│   │   ├── gemini_parser.py
│   │   ├── image_preprocess.py
│   │   ├── notification.py
│   │   ├── ocr.py
│   │   ├── product_lookup.py
│   │   ├── reminder.py
│   │   └── shelf_life.py
│   └── uploads/
└── frontend/
    ├── index.html
    ├── login.html
    ├── register.html
    ├── dashboard.html
    ├── receipt.html
    ├── style.css
    └── script.js
```

## How It Works

1. The user creates an account or logs in.
2. A grocery receipt is uploaded from the dashboard.
3. EasyOCR reads the receipt image.
4. Gemini converts OCR text into structured receipt data.
5. The app estimates item expiry dates based on purchase date and product type.
6. Receipt data is stored in MongoDB.
7. The dashboard shows receipt history and individual receipt details.
8. A background scheduler checks for expiring items and sends reminders.

## API Endpoints

- `POST /register` — create a new user
- `POST /login` — login user
- `GET /me?email=...` — get user profile
- `POST /upload-receipt` — upload and process a receipt
- `GET /history?email=...` — get receipt history
- `GET /receipt/<receipt_id>?email=...` — get one receipt
- `DELETE /receipt/<receipt_id>?email=...` — delete a receipt

## Environment Variables

Create a `.env` file inside `backend/` with:

```env
MONGO_URI=your_mongodb_connection_string
DB_NAME=smartpantry
GEMINI_API_KEY=your_gemini_api_key

SMTP_HOST=your_smtp_host
SMTP_PORT=587
SMTP_EMAIL=your_email
SMTP_PASSWORD=your_email_password

FAST2SMS_API_KEY=your_fast2sms_key
```

## Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/smartpantry.git
cd smartpantry
```

### 2. Install backend dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 3. Add environment variables
Create the `.env` file in the `backend` folder and add the values listed above.

### 4. Run the backend
```bash
python app.py
```

### 5. Open the frontend
Open `frontend/index.html` in your browser, or serve the frontend with a local server.
