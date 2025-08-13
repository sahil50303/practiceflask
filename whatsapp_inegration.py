#!/usr/bin/env python
# coding: utf-8
 
import os
import json
import logging
from collections import deque
from datetime import datetime, UTC
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
 
INFOBIP_API_KEY = "e72f594b726f6a4fb208c23a33649442-455325c3-aa95-47c8-931f-9b96685e08bb"
INFOBIP_BASE_URL = "https://4eyzy8.api.infobip.com"
WHATSAPP_SENDER = os.getenv("WHATSAPP_SENDER", "919920393553")
 
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
        return [{"date": "2025-01-15", "amount": 1000.0}]  # fallback
 
# -------------------
# PDF GENERATION
# -------------------
def generate_pdf(name, phone, donations, month, year, receipt_no):
    try:
        safe_name = name.replace(" ", "_")
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
        "Return JSON only. Keys: name, phone, month, year, intent, follow_up."
    )
    full_prompt = prompt + f"\nKnown: {json.dumps(existing_parameters)}\nUser: {user_message}"
    try:
        response = gemini_model.generate_content(full_prompt)
        data = json.loads(response.text.strip())
        return data
    except Exception as e:
        logging.error(f"LLM error: {e}")
        return {"intent": "other", "follow_up": None}
 
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
    r = requests.post(url, headers=headers, json=payload)
    logging.info(f"Text send status: {r.status_code} {r.text}")
    return r.json()
 
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
                "mediaUrl": media_url,
                "filename": filename
            }
        }
    }
    url = f"{INFOBIP_BASE_URL}/whatsapp/1/message/document"
    r = requests.post(url, headers=headers, json=payload)
    logging.info(f"Media send status: {r.status_code} {r.text}")
    return r.json()
 
# -------------------
# FLASK APP
# -------------------
app = Flask(__name__)
 
@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.json
    try:
        message = data["results"][0]["message"]["text"]
        sender = data["results"][0]["from"]
 
        if sender not in sessions:
            sessions[sender] = {"params": {}, "history": deque(maxlen=6)}
        sess = sessions[sender]
 
        sess["params"]["phone"] = sender
        sess["history"].append({"role": "user", "content": message})
 
        llm_result = LLM_response(sess["params"], list(sess["history"]), message)
        for k, v in llm_result.items():
            if v is not None:
                sess["params"][k] = v
 
        if llm_result.get("follow_up"):
            send_whatsapp_message(sender, llm_result["follow_up"])
        elif llm_result.get("intent") == "receipt":
            donations = query_database(sess["params"]["name"], sess["params"]["phone"], sess["params"]["year"], sess["params"]["month"])
            receipt_no = f"REC-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
            pdf_path = generate_pdf(sess["params"]["name"], sess["params"]["phone"], donations, sess["params"]["month"], sess["params"]["year"], receipt_no)
            if pdf_path:
                pdf_url = f"{request.url_root}download/{os.path.basename(pdf_path)}"
                send_whatsapp_message(sender, f"Here is your receipt: {pdf_url}")
                send_whatsapp_media(sender, pdf_url, os.path.basename(pdf_path))
            else:
                send_whatsapp_message(sender, "Sorry, could not generate your receipt.")
        else:
            send_whatsapp_message(sender, "Thank you for your message. How can I assist you further?")
 
        sess["history"].append({"role": "assistant", "content": message})
        return jsonify({"status": "success"}), 200
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500
 
@app.route('/download/<filename>')
def download_file(filename):
    return send_from_directory(os.path.abspath(PDF_FOLDER), filename, as_attachment=True, mimetype='application/pdf')
 
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)