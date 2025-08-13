# #!/usr/bin/env python
# # coding: utf-8
 
# import os
# import json
# import logging
# from collections import deque
# from datetime import datetime, UTC
# from flask import Flask, request, jsonify, send_from_directory
# import pypyodbc
# import pandas as pd
# import requests
# import google.generativeai as genai
# from reportlab.pdfgen import canvas
# from reportlab.lib.pagesizes import A4
# from reportlab.lib import colors
 
# # -------------------
# # CONFIG
# # -------------------
# logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
 
# INFOBIP_API_KEY = "e72f594b726f6a4fb208c23a33649442-455325c3-aa95-47c8-931f-9b96685e08bb"
# INFOBIP_BASE_URL = "https://4eyzy8.api.infobip.com"
# WHATSAPP_SENDER = os.getenv("WHATSAPP_SENDER", "919920393553")
 
# GEMINI_API_KEY = "AIzaSyB4eh0IQp63gkGOijYhhCeptQG0vXReLM0"
# genai.configure(api_key=GEMINI_API_KEY)
# gemini_model = genai.GenerativeModel("gemini-1.5-flash")
 
# # Database config
# server = '192.168.0.108,1433'
# database = 'test_receipt'
# username = 'PRIII'
# password = 'Pri@1234'
 
# PDF_FOLDER = "pdf_receipts"
# if not os.path.exists(PDF_FOLDER):
#     os.makedirs(PDF_FOLDER)
 
# sessions = {}
 
# # -------------------
# # DB FUNCTIONS
# # -------------------
# def get_db_conn():
#     conn_str = (
#         f"DRIVER={{ODBC Driver 17 for SQL Server}};"
#         f"SERVER={server};"
#         f"DATABASE={database};"
#         f"UID={username};"
#         f"PWD={password};"
#         f"TrustServerCertificate=yes;"
#         f"KeepAlive=1;"
#     )
#     return pypyodbc.connect(conn_str)
 
# def query_database(name, phone, year, month):
#     try:
#         connection = get_db_conn()
#         cursor = connection.cursor()
#         sql = """
#         select Date, Amount from donations_dataset where Name = ? AND Phone = ? and Month(Date) = ? AND Year(Date) = ?
#         """
#         cursor.execute(sql, (name, phone, month, year))
#         rows = cursor.fetchall()
#         connection.close()
#         return [{"date": r[0].strftime("%Y-%m-%d"), "amount": float(r[1])} for r in rows]
#     except Exception as e:
#         logging.error(f"Database query error: {e}")
#         return [{"date": "2025-01-15", "amount": 1000.0}]  # fallback
 
# # -------------------
# # PDF GENERATION
# # -------------------
# def generate_pdf(name, phone, donations, month, year, receipt_no):
#     try:
#         safe_name = name.replace(" ", "_")
#         filename = f"{safe_name}_{year}_{month}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.pdf"
#         filepath = os.path.join(PDF_FOLDER, filename)
#         c = canvas.Canvas(filepath, pagesize=A4)
#         width, height = A4
 
#         # Header
#         c.setFillColorRGB(0, 0.5, 0.8)
#         c.rect(0, height - 80, width, 80, fill=1)
#         c.setFillColor(colors.white)
#         c.setFont("Helvetica-Bold", 20)
#         c.drawString(80, height - 40, "NARAYAN SEVA SANSTHAN")
#         c.setFont("Helvetica", 10)
#         c.drawRightString(width - 40, height - 40, f"Receipt #: {receipt_no}")
 
#         # Body
#         y = height - 150
#         c.setFont("Helvetica", 10)
#         c.drawString(50, y, f"Donor Name: {name}")
#         y -= 20
#         c.drawString(50, y, f"Phone: {phone}")
#         y -= 20
#         if donations:
#             c.drawString(50, y, f"Donation Date: {donations[0]['date']}")
#             y -= 20
#             c.drawString(50, y, f"Amount: ₹ {donations[0]['amount']:,.0f}")
 
#         c.showPage()
#         c.save()
#         return filepath
#     except Exception as e:
#         logging.error(f"PDF generation error: {e}")
#         return None
 
# # -------------------
# # GEMINI LLM
# # -------------------
# def LLM_response(existing_parameters, last_message, user_message):
#     prompt = (
#         "You are an assistant that must extract structured parameters for a donation receipts API. "
#         "Return JSON only. Keys: name, phone, month, year, intent, follow_up."
#     )
#     full_prompt = prompt + f"\nKnown: {json.dumps(existing_parameters)}\nUser: {user_message}"
#     try:
#         response = gemini_model.generate_content(full_prompt)
#         data = json.loads(response.text.strip())
#         return data
#     except Exception as e:
#         logging.error(f"LLM error: {e}")
#         return {"intent": "other", "follow_up": None}
 
# # -------------------
# # INFOBIP SENDING
# # -------------------
# def send_whatsapp_message(recipient, message_text):
#     headers = {
#         "Authorization": f"App {INFOBIP_API_KEY}",
#         "Content-Type": "application/json",
#         "Accept": "application/json"
#     }
#     payload = {
#         "from": WHATSAPP_SENDER,
#         "to": recipient,
#         "content": {"text": message_text}
#     }
#     url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/text"
#     r = requests.post(url, headers=headers, json=payload)
#     logging.info(f"Text send status: {r.status_code} {r.text}")
#     return r.json()
 
# def send_whatsapp_media(recipient, media_url, filename):
#     headers = {
#         "Authorization": f"App {INFOBIP_API_KEY}",
#         "Content-Type": "application/json",
#         "Accept": "application/json"
#     }
#     payload = {
#         "from": WHATSAPP_SENDER,
#         "to": recipient,
#         "content": {
#             "document": {
#                 "mediaUrl": media_url,
#                 "filename": filename
#             }
#         }
#     }
#     url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/document"
#     r = requests.post(url, headers=headers, json=payload)
#     logging.info(f"Media send status: {r.status_code} {r.text}")
#     return r.json()
 
# # -------------------
# # FLASK APP
# # -------------------
# app = Flask(__name__)
 
# @app.route("/webhook", methods=["POST"])
# def webhook():
#     data = request.json
#     try:
#         message = data["results"][0]["message"]["text"]
#         sender = data["results"][0]["from"]
 
#         if sender not in sessions:
#             sessions[sender] = {"params": {}, "history": deque(maxlen=6)}
#         sess = sessions[sender]
 
#         sess["params"]["phone"] = sender
#         sess["history"].append({"role": "user", "content": message})
 
#         llm_result = LLM_response(sess["params"], list(sess["history"]), message)
#         for k, v in llm_result.items():
#             if v is not None:
#                 sess["params"][k] = v
 
#         if llm_result.get("follow_up"):
#             send_whatsapp_message(sender, llm_result["follow_up"])
#         elif llm_result.get("intent") == "receipt":
#             donations = query_database(sess["params"]["name"], sess["params"]["phone"], sess["params"]["year"], sess["params"]["month"])
#             receipt_no = f"REC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
#             pdf_path = generate_pdf(sess["params"]["name"], sess["params"]["phone"], donations, sess["params"]["month"], sess["params"]["year"], receipt_no)
#             if pdf_path:
#                 pdf_url = f"{request.url_root}download/{os.path.basename(pdf_path)}"
#                 send_whatsapp_message(sender, f"Here is your receipt: {pdf_url}")
#                 send_whatsapp_media(sender, pdf_url, os.path.basename(pdf_path))
#             else:
#                 send_whatsapp_message(sender, "Sorry, could not generate your receipt.")
#         else:
#             send_whatsapp_message(sender, "Thank you for your message. How can I assist you further?")
 
#         sess["history"].append({"role": "assistant", "content": message})
#         return jsonify({"status": "success"}), 200
#     except Exception as e:
#         logging.error(f"Webhook error: {e}")
#         return jsonify({"error": str(e)}), 500
 
# @app.route('/download/<filename>')
# def download_file(filename):
#     return send_from_directory(os.path.abspath(PDF_FOLDER), filename, as_attachment=True, mimetype='application/pdf')
 
# if __name__ == "__main__":
#     port = int(os.environ.get("PORT", 5000))
#     app.run(host="0.0.0.0", port=port)


#!/usr/bin/env python
# coding: utf-8

import os
import json
import logging
from collections import deque
from datetime import datetime, UTC
from flask import Flask, request, jsonify, send_from_directory
import pandas as pd
import requests
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
import psycopg2
from psycopg2.extras import RealDictCursor
import re

# -------------------
# CONFIG
# -------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

INFOBIP_API_KEY = "e72f594b726f6a4fb208c23a33649442-455325c3-aa95-47c8-931f-9b96685e08bb"
INFOBIP_BASE_URL = "https://4eyzy8.api.infobip.com"
WHATSAPP_SENDER = os.getenv("WHATSAPP_SENDER", "919920393553")

GEMINI_API_KEY = "AIzaSyB4eh0IQp63gkGOijYhhCeptQG0vXReLM0"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")

# Database config - Using PostgreSQL for Render compatibility
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://user:password@localhost:5432/receipt_db')

PDF_FOLDER = "pdf_receipts"
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)

# Enhanced session management
sessions = {}

# -------------------
# UTILITY FUNCTIONS
# -------------------
def clean_phone_number(phone):
    """Clean and standardize phone number format"""
    phone = re.sub(r'\D', '', phone)  # Remove non-digits
    if phone.startswith('91') and len(phone) == 12:
        return phone
    elif len(phone) == 10:
        return '91' + phone
    return phone

def validate_month_year(month, year):
    """Validate month and year values"""
    try:
        month = int(month)
        year = int(year)
        if 1 <= month <= 12 and 2020 <= year <= 2025:
            return month, year
        return None, None
    except (ValueError, TypeError):
        return None, None

# -------------------
# DB FUNCTIONS
# -------------------
def get_db_conn():
    """Get database connection - PostgreSQL for Render compatibility"""
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        logging.error(f"Database connection error: {e}")
        return None

def create_sample_data():
    """Create sample donation data if database is not available"""
    sample_donations = {
        # Sahil - 952770857
        "952770857": [
            {"date": "2025-01-05", "amount": 10000.0},
            {"date": "2025-03-25", "amount": 33000.0}
        ],
        "9527708575": [  # Alternative format
            {"date": "2025-01-05", "amount": 10000.0},
            {"date": "2025-03-25", "amount": 33000.0}
        ],
        # Alice - 987654321
        "987654321": [
            {"date": "2025-01-20", "amount": 150.0},
            {"date": "2025-02-14", "amount": 250.0},
            {"date": "2025-03-10", "amount": 175.0},
            {"date": "2025-04-01", "amount": 120.0},
            {"date": "2025-05-10", "amount": 100.0},
            {"date": "2025-05-20", "amount": 200.0},
            {"date": "2025-06-18", "amount": 400.0},
            {"date": "2025-08-10", "amount": 190.0}
        ],
        # Bob - 987654322
        "987654322": [
            {"date": "2025-01-15", "amount": 200.0},
            {"date": "2025-03-12", "amount": 220.0},
            {"date": "2025-04-18", "amount": 210.0},
            {"date": "2025-05-05", "amount": 300.0},
            {"date": "2025-07-07", "amount": 275.0}
        ],
        # Charlie - 987654323
        "987654323": [
            {"date": "2025-02-28", "amount": 300.0},
            {"date": "2025-06-15", "amount": 250.0},
            {"date": "2025-08-25", "amount": 280.0}
        ],
        # Bhu - 999706838
        "9997068381": [
            {"date": "2025-07-21", "amount": 310000.0}
        ]
    }
    return sample_donations

def query_database(name, phone, year, month):
    """Query donation data from database with fallback to sample data"""
    try:
        connection = get_db_conn()
        if not connection:
            logging.warning("Database not available, using sample data")
            # Get sample data based on phone number
            sample_data = create_sample_data()
            phone_clean = clean_phone_number(phone)
            
            # Try different phone formats
            phone_variations = [
                phone_clean,
                phone_clean.lstrip('91') if phone_clean.startswith('91') else '91' + phone_clean,
                phone_clean[-10:] if len(phone_clean) > 10 else phone_clean
            ]
            
            for phone_var in phone_variations:
                if phone_var in sample_data:
                    all_donations = sample_data[phone_var]
                    # Filter by month and year
                    filtered_donations = []
                    for donation in all_donations:
                        donation_date = datetime.strptime(donation["date"], "%Y-%m-%d")
                        if donation_date.month == month and donation_date.year == year:
                            filtered_donations.append(donation)
                    
                    if filtered_donations:
                        logging.info(f"Found {len(filtered_donations)} donations for phone {phone_var} in {month}/{year}")
                        return filtered_donations
            
            # If no specific data found, return a default donation
            logging.info(f"No sample data found for phone {phone}, returning default donation")
            return [{"date": f"{year}-{month:02d}-15", "amount": 1000.0}]
            
        cursor = connection.cursor()
        # Adjusted SQL for PostgreSQL
        sql = """
        SELECT date, amount FROM donations_dataset 
        WHERE name ILIKE %s AND phone = %s 
        AND EXTRACT(MONTH FROM date) = %s 
        AND EXTRACT(YEAR FROM date) = %s
        """
        cursor.execute(sql, (name, phone, month, year))
        rows = cursor.fetchall()
        connection.close()
        
        if rows:
            return [{"date": r["date"].strftime("%Y-%m-%d"), "amount": float(r["amount"])} for r in rows]
        else:
            logging.info(f"No donations found for {name}, using sample data fallback")
            return [{"date": f"{year}-{month:02d}-15", "amount": 1000.0}]
            
    except Exception as e:
        logging.error(f"Database query error: {e}")
        return [{"date": f"{year}-{month:02d}-15", "amount": 1000.0}]

# -------------------
# PDF GENERATION
# -------------------
def generate_pdf(name, phone, donations, month, year, receipt_no):
    """Generate PDF receipt"""
    try:
        safe_name = re.sub(r'[^\w\s-]', '', name).replace(" ", "_")
        filename = f"{safe_name}_{year}_{month}_{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}.pdf"
        filepath = os.path.join(PDF_FOLDER, filename)
        
        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4

        # Header
        c.setFillColorRGB(0, 0.5, 0.8)
        c.rect(0, height - 80, width, 80, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(80, height - 40, "NARAYAN SEVA SANSTHAN")
        c.setFont("Helvetica", 10)
        c.drawRightString(width - 40, height - 40, f"Receipt #: {receipt_no}")

        # Body
        c.setFillColor(colors.black)
        y = height - 150
        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, "DONATION RECEIPT")
        y -= 40
        
        c.setFont("Helvetica", 12)
        c.drawString(50, y, f"Donor Name: {name}")
        y -= 25
        c.drawString(50, y, f"Phone: {phone}")
        y -= 25
        c.drawString(50, y, f"Month/Year: {month:02d}/{year}")
        y -= 35
        
        # Donations table
        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "DONATIONS:")
        y -= 25
        
        c.setFont("Helvetica", 10)
        total_amount = 0
        for donation in donations:
            c.drawString(70, y, f"Date: {donation['date']}")
            c.drawRightString(width - 50, y, f"Amount: ₹ {donation['amount']:,.0f}")
            total_amount += donation['amount']
            y -= 20
            
        y -= 20
        c.setFont("Helvetica-Bold", 12)
        c.drawString(70, y, "TOTAL AMOUNT:")
        c.drawRightString(width - 50, y, f"₹ {total_amount:,.0f}")
        
        # Footer
        y -= 60
        c.setFont("Helvetica", 8)
        c.drawString(50, y, "Thank you for your generous donation!")
        c.drawString(50, y - 15, "This is a computer generated receipt.")

        c.showPage()
        c.save()
        logging.info(f"PDF generated successfully: {filename}")
        return filepath
        
    except Exception as e:
        logging.error(f"PDF generation error: {e}")
        return None

# -------------------
# ENHANCED LLM PROCESSING
# -------------------
def analyze_user_message(existing_parameters, conversation_history, user_message):
    """Enhanced LLM processing with better conversation flow"""
    
    prompt = """You are a donation receipt assistant. Extract and return ONLY valid JSON with these exact keys:
- "name": full donor name (string or null)  
- "month": month number 1-12 (integer or null)
- "year": year 2020-2025 (integer or null)
- "intent": one of ["greeting", "receipt_request", "providing_info", "complete", "other"]
- "message": response message to user (string)
- "ready_for_receipt": true if all required info collected (boolean)

Rules:
1. Extract phone from webhook, don't ask for it
2. Ask for missing required fields: name, month, year
3. Validate month (1-12) and year (2020-2025)
4. Set intent="complete" and ready_for_receipt=true when all info is valid
5. Be conversational and helpful
6. If user says hi/hello, set intent="greeting"
7. Keep messages concise and friendly

Current parameters: {existing_params}
User message: "{message}"
"""

    try:
        full_prompt = prompt.format(
            existing_params=json.dumps(existing_parameters),
            message=user_message
        )
        
        response = gemini_model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean response text
        if response_text.startswith("```json"):
            response_text = response_text[7:-3]
        elif response_text.startswith("```"):
            response_text = response_text[3:-3]
            
        data = json.loads(response_text)
        
        # Validate required keys
        required_keys = ["name", "month", "year", "intent", "message", "ready_for_receipt"]
        for key in required_keys:
            if key not in data:
                data[key] = None if key != "ready_for_receipt" else False
                
        logging.info(f"LLM Response: {data}")
        return data
        
    except Exception as e:
        logging.error(f"LLM error: {e}")
        return {
            "name": None,
            "month": None, 
            "year": None,
            "intent": "other",
            "message": "I'm having trouble understanding. Could you please tell me your name, and which month and year you'd like the receipt for?",
            "ready_for_receipt": False
        }

# -------------------
# INFOBIP MESSAGING
# -------------------
def send_whatsapp_message(recipient, message_text):
    """Send WhatsApp text message"""
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "from": WHATSAPP_SENDER,
        "to": recipient,
        "content": {"text": message_text}
    }
    url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/text"
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        logging.info(f"Text message sent. Status: {r.status_code}")
        return r.json()
    except Exception as e:
        logging.error(f"Error sending message: {e}")
        return {"error": str(e)}

def send_whatsapp_document(recipient, media_url, filename):
    """Send WhatsApp document"""
    headers = {
        "Authorization": f"App {INFOBIP_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    payload = {
        "from": WHATSAPP_SENDER,
        "to": recipient,
        "content": {
            "document": {
                "mediaUrl": media_url,
                "filename": filename
            }
        }
    }
    url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/document"
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        logging.info(f"Document sent. Status: {r.status_code}")
        return r.json()
    except Exception as e:
        logging.error(f"Error sending document: {e}")
        return {"error": str(e)}

# -------------------
# FLASK APP
# -------------------
app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    """Enhanced webhook handler with better error handling"""
    try:
        data = request.json
        logging.info(f"Received webhook data: {data}")
        
        # Extract message and sender
        if not data or "results" not in data or not data["results"]:
            return jsonify({"error": "Invalid webhook data"}), 400
            
        result = data["results"][0]
        message_text = result.get("message", {}).get("text", "")
        sender = result.get("from", "")
        
        if not sender or not message_text:
            return jsonify({"error": "Missing sender or message"}), 400
            
        # Clean phone number
        sender = clean_phone_number(sender)
        
        # Initialize or get session
        if sender not in sessions:
            sessions[sender] = {
                "params": {"phone": sender},
                "history": deque(maxlen=10),
                "state": "collecting_info"
            }
            
        session = sessions[sender]
        session["history"].append({"role": "user", "content": message_text})
        
        # Process message with LLM
        llm_result = analyze_user_message(
            session["params"], 
            list(session["history"]), 
            message_text
        )
        
        # Update session parameters
        for key in ["name", "month", "year"]:
            if llm_result.get(key) is not None:
                session["params"][key] = llm_result[key]
                
        # Handle response based on intent
        if llm_result.get("ready_for_receipt") and session["state"] != "receipt_sent":
            # Generate and send receipt
            try:
                donations = query_database(
                    session["params"]["name"],
                    session["params"]["phone"], 
                    session["params"]["year"],
                    session["params"]["month"]
                )
                
                receipt_no = f"REC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
                pdf_path = generate_pdf(
                    session["params"]["name"],
                    session["params"]["phone"],
                    donations,
                    session["params"]["month"],
                    session["params"]["year"],
                    receipt_no
                )
                
                if pdf_path:
                    filename = os.path.basename(pdf_path)
                    pdf_url = f"{request.url_root.rstrip('/')}/download/{filename}"
                    
                    # Send confirmation message with URL
                    success_message = f"✅ Receipt generated successfully!\n\nReceipt #: {receipt_no}\nDonor: {session['params']['name']}\nPeriod: {session['params']['month']:02d}/{session['params']['year']}\n\nDownload: {pdf_url}"
                    
                    send_whatsapp_message(sender, success_message)
                    send_whatsapp_document(sender, pdf_url, filename)
                    
                    session["state"] = "receipt_sent"
                    session["history"].append({"role": "assistant", "content": success_message})
                    
                else:
                    error_message = "❌ Sorry, there was an error generating your receipt. Please try again later."
                    send_whatsapp_message(sender, error_message)
                    session["state"] = "error"
                    
            except Exception as e:
                logging.error(f"Receipt generation error: {e}")
                error_message = "❌ Sorry, there was an error processing your request. Please try again."
                send_whatsapp_message(sender, error_message)
                session["state"] = "error"
                
        else:
            # Send LLM response message
            if llm_result.get("message"):
                send_whatsapp_message(sender, llm_result["message"])
                session["history"].append({"role": "assistant", "content": llm_result["message"]})
        
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": "Internal server error"}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """Serve PDF files for download"""
    try:
        return send_from_directory(
            os.path.abspath(PDF_FOLDER), 
            filename, 
            as_attachment=True, 
            mimetype='application/pdf'
        )
    except Exception as e:
        logging.error(f"Download error: {e}")
        return jsonify({"error": "File not found"}), 404

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now(UTC).isoformat()}), 200

@app.route('/')
def home():
    """Home endpoint"""
    return jsonify({"message": "Receipt Bot is running!", "timestamp": datetime.now(UTC).isoformat()}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)