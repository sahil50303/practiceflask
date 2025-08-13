#!/usr/bin/env python
# coding: utf-8
 
import os
import json
import logging
from collections import deque
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
import pypyodbc
import pandas as pd
import requests
import google.generativeai as genai
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
 
# -------------------
# CONFIG
# -------------------
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
 
# Infobip config (set via environment variables for security)
INFOBIP_API_KEY = "e72f594b726f6a4fb208c23a33649442-455325c3-aa95-47c8-931f-9b96685e08bb"
INFOBIP_BASE_URL = "https://4eyzy8.api.infobip.com"
WHATSAPP_SENDER = os.getenv("WHATSAPP_SENDER", "919920393553")
 
# Gemini config
GEMINI_API_KEY = "AIzaSyB4eh0IQp63gkGOijYhhCeptQG0vXReLM0"
genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")
 
# Database config
server = '192.168.0.108,1433'
database = 'test_receipt'
username = 'PRIII'
password = 'Pri@1234'
 
PDF_FOLDER = "pdf_receipts"
if not os.path.exists(PDF_FOLDER):
    os.makedirs(PDF_FOLDER)
 
sessions = {}
 
# -------------------
# DB FUNCTIONS
# -------------------
def get_db_conn():
    conn_str = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
        f"TrustServerCertificate=yes;"
        f"KeepAlive=1;"
    )
    return pypyodbc.connect(conn_str)
 
def query_database(name, phone, year, month):
    try:
        connection = get_db_conn()
        cursor = connection.cursor()
        sql = """
        select Date, Amount from donations_dataset where Name = ? AND Phone = ? and Month(Date) = ? AND Year(Date) = ?
        """
        cursor.execute(sql, (name, phone, month, year))
        rows = cursor.fetchall()
        connection.close()
        return [{"date": r[0].strftime("%Y-%m-%d"), "amount": float(r[1])} for r in rows]
    except Exception as e:
        logging.error(f"Database query error: {e}")
        return [{"date": "2025-01-15", "amount": 1000.0}]
 
# -------------------
# PDF GENERATION
# -------------------
def generate_pdf(name, phone, donations, month, year, receipt_no):
    try:
        safe_name = name.replace(" ", "_")
        filename = f"{safe_name}_{year}_{month}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
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
        y = height - 150
        c.setFont("Helvetica", 10)
        c.drawString(50, y, f"Donor Name: {name}")
        y -= 20
        c.drawString(50, y, f"Phone: {phone}")
        y -= 20
        if donations:
            c.drawString(50, y, f"Donation Date: {donations[0]['date']}")
            y -= 20
            c.drawString(50, y, f"Amount: ₹ {donations[0]['amount']:,.0f}")
        c.showPage()
        c.save()
        return filepath
    except Exception as e:
        logging.error(f"PDF generation error: {e}")
        return None
 
# -------------------
# GEMINI LLM
# -------------------
def LLM_response(existing_parameters, last_message, user_message):
    prompt = (
        "You are an assistant that must extract structured parameters for a donation receipts API. "
        "Extract the following from the user message:\n"
        "- name: donor's full name\n"
        "- phone: phone number\n" 
        "- month: month number (1-12)\n"
        "- year: year (4 digits)\n"
        "- intent: 'receipt' if user wants a donation receipt, 'other' otherwise\n"
        "- follow_up: question to ask if missing required info, null if complete\n\n"
        "Return ONLY valid JSON format with these exact keys.\n"
        "If user wants receipt but info is missing, set follow_up to ask for missing details."
    )
    full_prompt = prompt + f"\n\nExisting parameters: {json.dumps(existing_parameters)}\nUser message: {user_message}"
    
    try:
        response = gemini_model.generate_content(full_prompt)
        response_text = response.text.strip()
        
        # Clean up response text - remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        logging.info(f"LLM raw response: {response_text}")
        data = json.loads(response_text)
        return data
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}, Response: {response_text}")
        return {"intent": "other", "follow_up": "I didn't understand. Could you please tell me your name and the month/year you want the receipt for?"}
    except Exception as e:
        logging.error(f"LLM error: {e}")
        return {"intent": "other", "follow_up": "Sorry, I'm having trouble processing your request. Please try again."}
 
# -------------------
# INFOBIP SENDING
# -------------------
def send_whatsapp_message(recipient, message_text):
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
        logging.info(f"Text send status: {r.status_code} {r.text}")
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logging.error(f"WhatsApp message send error: {e}")
        return None
 
def send_whatsapp_media(recipient, media_url, filename):
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
                "url": media_url,
                "filename": filename
            }
        }
    }
    url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/document"
    
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=10)
        logging.info(f"Media send status: {r.status_code} {r.text}")
        return r.json() if r.status_code == 200 else None
    except Exception as e:
        logging.error(f"WhatsApp media send error: {e}")
        return None
 
# -------------------
# FLASK APP
# -------------------
app = Flask(__name__)

@app.route("/webhook", methods=["GET"])
def webhook_verify():
    """Handle webhook verification"""
    return "Webhook is working!", 200

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    logging.info(f"Received webhook data: {json.dumps(data, indent=2)}")
    
    try:
        # Handle different webhook structures
        message_text = ""
        sender = ""
        
        # Try different possible webhook structures
        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            if "message" in result and "text" in result["message"]:
                message_text = result["message"]["text"]
            if "from" in result:
                sender = result["from"]
        elif "messages" in data and len(data["messages"]) > 0:
            message = data["messages"][0]
            if "text" in message and "body" in message["text"]:
                message_text = message["text"]["body"]
            if "from" in message:
                sender = message["from"]
        elif "message" in data:
            if "text" in data["message"]:
                message_text = data["message"]["text"]
            if "from" in data:
                sender = data["from"]
        
        if not message_text or not sender:
            logging.warning("Could not extract message or sender from webhook data")
            return jsonify({"status": "no_message"}), 200
        
        logging.info(f"Processing message: '{message_text}' from: {sender}")
 
        # Initialize session if needed
        if sender not in sessions:
            sessions[sender] = {"params": {}, "history": deque(maxlen=6)}
        sess = sessions[sender]
 
        sess["params"]["phone"] = sender
        sess["history"].append({"role": "user", "content": message_text})
 
        # Get LLM response
        llm_result = LLM_response(sess["params"], list(sess["history"]), message_text)
        logging.info(f"LLM result: {llm_result}")
        
        # Update session parameters
        for k, v in llm_result.items():
            if v is not None and k != "follow_up":
                sess["params"][k] = v
 
        # Handle response
        if llm_result.get("follow_up"):
            send_whatsapp_message(sender, llm_result["follow_up"])
        elif llm_result.get("intent") == "receipt":
            # Check if we have all required parameters
            required_params = ["name", "phone", "month", "year"]
            missing_params = [p for p in required_params if p not in sess["params"] or not sess["params"][p]]
            
            if missing_params:
                follow_up = f"I need some more information. Please provide: {', '.join(missing_params)}"
                send_whatsapp_message(sender, follow_up)
            else:
                try:
                    donations = query_database(
                        sess["params"]["name"], 
                        sess["params"]["phone"], 
                        int(sess["params"]["year"]), 
                        int(sess["params"]["month"])
                    )
                    receipt_no = f"REC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    pdf_path = generate_pdf(
                        sess["params"]["name"], 
                        sess["params"]["phone"], 
                        donations, 
                        sess["params"]["month"], 
                        sess["params"]["year"], 
                        receipt_no
                    )
                    
                    if pdf_path:
                        pdf_url = f"{request.host_url}download/{os.path.basename(pdf_path)}"
                        send_whatsapp_message(sender, f"Here is your donation receipt for {sess['params']['name']}:")
                        send_whatsapp_media(sender, pdf_url, os.path.basename(pdf_path))
                    else:
                        send_whatsapp_message(sender, "Sorry, I could not generate your receipt. Please try again later.")
                except Exception as e:
                    logging.error(f"Receipt generation error: {e}")
                    send_whatsapp_message(sender, "Sorry, there was an error generating your receipt. Please try again.")
        else:
            send_whatsapp_message(sender, "Hello! I can help you get donation receipts. Please provide your name and the month/year you need the receipt for.")
 
        sess["history"].append({"role": "assistant", "content": "Response sent"})
        return jsonify({"status": "success"}), 200
        
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        # Try to send error message to user if we have sender info
        if 'sender' in locals() and sender:
            send_whatsapp_message(sender, "Sorry, I'm experiencing technical difficulties. Please try again later.")
        return jsonify({"error": str(e)}), 500
 
@app.route('/download/<filename>')
def download_file(filename):
    try:
        return send_from_directory(os.path.abspath(PDF_FOLDER), filename, as_attachment=True, mimetype='application/pdf')
    except Exception as e:
        logging.error(f"File download error: {e}")
        return jsonify({"error": "File not found"}), 404

@app.route('/health')
def health_check():
    return jsonify({"status": "healthy", "timestamp": datetime.utcnow().isoformat()}), 200

if __name__ == "__main__":
    print("Starting WhatsApp bot server...")
    print(f"PDF folder: {os.path.abspath(PDF_FOLDER)}")
    print(f"WhatsApp sender: {WHATSAPP_SENDER}")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)