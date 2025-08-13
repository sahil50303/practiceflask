import pypyodbc
import pandas as pd
import os
import google.generativeai as genai
from flask import Flask, request, jsonify, send_from_directory, abort
from reportlab.pdfgen import canvas
import json
from collections import deque
import logging
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from datetime import datetime

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s:%(message)s')

server = '192.168.0.108,1433'
database = 'test_receipt'  
username = 'PRIII'
password = 'Pri@1234'
Gemini_APi_key = "AIzaSyB4eh0IQp63gkGOijYhhCeptQG0vXReLM0"
genai.configure(api_key=Gemini_APi_key)
model_name = "gemini-1.5-flash"
gemini_model = genai.GenerativeModel(model_name)

sessions = {}

conn_str = (
    f"DRIVER={{ODBC Driver 17 for SQL Server}};"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password};"
    f"TrustServerCertificate=yes;"
    f"KeepAlive=1;"
)

try:
    conn = pypyodbc.connect(conn_str)
    print("Connection successful!")
except Exception as e:
    print(f"Error: {e}")

PDF_FOLDER = "pdf_receipts"

def generate_pdf(name, phone, donations, month, year, receipt_no):
    """
    donations: list of dicts [{'date': 'YYYY-MM-DD', 'amount': 123.45}, ...]
    """
    try:
        
        if not os.path.exists(PDF_FOLDER):
            os.makedirs(PDF_FOLDER)
            logging.info(f"Created PDF folder: {PDF_FOLDER}")

        safe_name = name.replace(" ", "_")
        filename = f"{safe_name}_{year}_{month}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        filepath = os.path.join(PDF_FOLDER, filename)

        logging.info(f"Generating PDF at: {filepath}")

        c = canvas.Canvas(filepath, pagesize=A4)
        width, height = A4

        c.setFillColorRGB(0, 0.5, 0.8)
        c.rect(0, height - 80, width, 80, fill=1)

        c.setFillColor(colors.white)
        c.circle(50, height - 40, 20, fill=1)

        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 20)
        c.drawString(80, height - 40, "NARAYAN SEVA SANSTHAN")
        c.setFont("Helvetica-Oblique", 12)
        c.drawString(80, height - 60, "Nar Seva Narayan Seva")

        c.setFont("Helvetica", 10)
        c.drawRightString(width - 40, height - 40, f"Receipt #: {receipt_no}")

        c.setFillColorRGB(0, 0.8, 0.8)
        c.rect(0, height - 120, width, 25, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(width / 2, height - 115, "DONATION RECEIPT")

        text = (
            "We extend our heartfelt gratitude for your generous contribution to Narayan Seva Sansthan. "
            "Your donation will help us continue our mission of serving humanity and making a positive impact "
            "in the lives of those in need. Your compassion and support enable us to carry forward our work "
            "with renewed dedication and hope."
        )
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 10)
        text_obj = c.beginText(50, height - 150)
        text_obj.setLeading(14)
        text_obj.textLines(text)
        c.drawText(text_obj)

        y = height - 250
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Donor Name:")
        c.setFont("Helvetica", 10)
        c.drawString(200, y, name)

        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Phone Number:")
        c.setFont("Helvetica", 10)
        c.drawString(200, y, phone)

        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Donation Date:")
        c.setFont("Helvetica", 10)
        if donations:
            c.drawString(200, y, donations[0]['date'])

        y -= 20
        c.setFont("Helvetica-Bold", 10)
        c.drawString(50, y, "Amount Donated:")
        c.setFillColorRGB(0.4, 0, 0.8)
        c.roundRect(200, y - 5, 60, 18, 5, fill=1)
        c.setFillColor(colors.white)
        if donations:
            c.drawCentredString(230, y, f"₹ {donations[0]['amount']:,.0f}")

        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(width / 2, 80, "May your kindness return to you multiplied.")
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 65, "This receipt is computer generated and does not require signature.")

        c.setStrokeColor(colors.lightgrey)
        c.line(30, 50, width - 30, 50)
        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 35, "Narayan Seva Sansthan | PAN: AATN1234B")

        c.showPage()
        c.save()

        # Verify file was created
        if os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            logging.info(f"PDF successfully created: {filepath} (size: {file_size} bytes)")
            return filepath
        else:
            logging.error(f"PDF file was not created at: {filepath}")
            return None

    except Exception as e:
        logging.error(f"Error generating PDF: {e}")
        return None

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
        
        result = [{"date": r[0].strftime("%Y-%m-%d"), "amount": float(r[1])} for r in rows]
        logging.info(f"Database query returned {len(result)} records for {name}, {phone}")
        return result
    except Exception as e:
        logging.error(f"Database query error: {e}")
        # Return dummy data for testing if database fails
        return [{"date": "2025-01-15", "amount": 1000.0}]

def Create_full_prompt(existing_parameters, last_message, user_message):
    system = (
        "You are an assistant that must extract structured parameters for a donation receipts API. "
        "Return JSON only (no explanation). Keys: name, phone, month, year, intent, follow_up. "
        "- name: string or null\n"
        "- phone: string or null\n"
        "- month: integer (1-12) or null\n"
        "- year: integer (YYYY) or null\n"
        "- intent: either 'receipt' or 'faq' or 'other'\n"
        "- follow_up: if any required param (month/year) is missing, put a short natural-language question; otherwise null.\n\n"
        "Behavior rules:\n"
        "1) Use the provided existing known fields when possible (do not drop them).\n"
        "2) If the user said 'last month', 'last february', 'three months ago', compute concrete month/year values based on today's date.\n"
        "3) If the user's message is clearly a receipt request, set intent='receipt'.\n"
        "4) If you cannot determine month/year, set them to null and set follow_up to a short clarifying question.\n"
        "5) Respond ONLY with a single valid JSON object."
    )
   
    # Build the prompt as a single string for Gemini
    full_prompt_text = system + "\n\n"
    
    if last_message:
        full_prompt_text += "Conversation history:\n"
        for m in last_message:
            full_prompt_text += f"{m['role'].upper()}: {m['content']}\n"
        full_prompt_text += "\n"

    if existing_parameters:
        full_prompt_text += f"Known info so far: {json.dumps(existing_parameters)}\n\n"
       
    full_prompt_text += f"Current user message: {user_message}\n\n"
    full_prompt_text += "Extract parameters and return JSON only:"
    
    return full_prompt_text

def LLM_response(existing_parameters, last_message, user_message):
    full_prompt_text = Create_full_prompt(existing_parameters, last_message, user_message)
    logging.debug(f"Full prompt to Gemini: {full_prompt_text}")
    required_element = None

    try:
        response = gemini_model.generate_content(
            full_prompt_text,  
            generation_config=genai.types.GenerationConfig(
                temperature=0.3,
                max_output_tokens=200,
                top_p=0.8,
                top_k=40
            )
        )
        required_element = response.text.strip()
        logging.debug(f"Raw LLM response: {required_element}")
        
        
        json_start = required_element.find('{')
        json_end = required_element.rfind('}') + 1
        if json_start != -1 and json_end != 0:
            json_text = required_element[json_start:json_end]
            data = json.loads(json_text)
        else:
            data = json.loads(required_element)
        
        return data

    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error from LLM response: {e}")
        logging.error(f"LLM raw response: {required_element}")
        return {
            "error": "LLM responded with non-JSON output",
            "raw": required_element,
            "detail": str(e)
        }
    except Exception as e:
        logging.error(f"Error calling LLM: {e}")
        logging.error(f"LLM raw response: {required_element}")
        return {
            "error": "Error calling LLM",
            "raw": required_element,
            "detail": str(e)
        }

def call_llm_reply(last_message, user_message, known_params, pdf_url=None):

    if pdf_url:

        reply = f"Here is your receipt: {pdf_url}"
    else:
        reply = "Thank you for your message, but your receipt doesn't exist in our Database, is there anthing further I can assist you with ?"
    return reply

app = Flask(__name__)

@app.route("/ask", methods=["POST"])
def ask():
    payload = request.get_json(force=True)
    message = payload.get("message", "").strip()
    phone = payload.get("phone")
    name = payload.get("name")

    if not phone:
        return jsonify({"error": "phone number is required"}), 400

    if phone not in sessions:
        sessions[phone] = {
            "params": {},
            "history": deque(maxlen=6)
        }
    sess = sessions[phone]

    if name:
        sess["params"]["name"] = name
    sess["params"]["phone"] = phone

    sess["history"].append({"role": "user", "content": message})
    last_message = list(sess["history"])[-4:]

    llm_result = LLM_response(sess["params"], last_message, message)

    logging.debug(f"LLM extracted parameters: {llm_result}")

    if "error" in llm_result:
        reply_text = (
            "Sorry, I am having trouble understanding your request.\n"
            f"LLM error detail: {llm_result.get('detail')}\n"
            f"LLM raw response: {llm_result.get('raw')}"
        )
        logging.error(reply_text)
        return jsonify({"reply": reply_text})

    for key in ["name", "phone", "month", "year", "intent", "follow_up"]:
        if key in llm_result and llm_result[key] is not None:
            sess["params"][key] = llm_result[key]

    if llm_result.get("follow_up"):
        reply_text = llm_result["follow_up"]
    else:
        if llm_result.get("intent") == "receipt":
            try:
                donations = query_database(
                    sess["params"]["name"],
                    sess["params"]["phone"],
                    sess["params"]["year"],
                    sess["params"]["month"],
                )
                
                if donations:
                    receipt_no = f"REC-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
                    pdf_path = generate_pdf(
                        sess["params"]["name"],
                        sess["params"]["phone"],
                        donations,
                        sess["params"]["month"],
                        sess["params"]["year"],
                        receipt_no
                    )
                    
                    if pdf_path and os.path.exists(pdf_path):
                        pdf_url = f"{request.host_url}download/{os.path.basename(pdf_path)}"
                        logging.info(f"Generated PDF URL: {pdf_url}")
                    else:
                        pdf_url = None
                        logging.error("PDF generation failed")
                else:
                    pdf_url = None
                    logging.warning("No donations found in database")
                    
            except Exception as e:
                logging.error(f"Error generating PDF or querying DB: {e}")
                pdf_url = None

            reply_text = call_llm_reply(last_message, message, sess["params"], pdf_url)

        else:
            reply_text = call_llm_reply(last_message, message, sess["params"])

    sess["history"].append({"role": "assistant", "content": reply_text})

    return jsonify({"reply": reply_text})

@app.route('/download/<filename>')
def download_file(filename):
    try:
        if '..' in filename or '/' in filename or '\\' in filename:
            logging.warning(f"Invalid filename attempt: {filename}")
            return jsonify({"error": "Invalid filename"}), 400
        
        abs_pdf_folder = os.path.abspath(PDF_FOLDER)
        file_path = os.path.join(abs_pdf_folder, filename)
        
        logging.info(f"Attempting to serve file: {file_path}")
        logging.info(f"PDF folder: {abs_pdf_folder}")
        logging.info(f"File exists: {os.path.exists(file_path)}")
        
        if not os.path.exists(file_path):
            logging.error(f"File not found: {file_path}")
            if os.path.exists(abs_pdf_folder):
                available_files = os.listdir(abs_pdf_folder)
                logging.info(f"Available files: {available_files}")
            return jsonify({"error": "File not found"}), 404
            
        file_size = os.path.getsize(file_path)
        logging.info(f"File size: {file_size} bytes")
        
        if file_size == 0:
            logging.error(f"File is empty: {file_path}")
            return jsonify({"error": "File is empty"}), 500
            
        return send_from_directory(abs_pdf_folder, filename, 
                                 as_attachment=True,
                                 mimetype='application/pdf')
                                 
    except Exception as e:
        logging.error(f"Error downloading file {filename}: {e}")
        return jsonify({"error": "File download failed"}), 500

@app.route('/debug/files', methods=["GET"])
def debug_files():
    """Debug route to see what files exist"""
    try:
        abs_pdf_folder = os.path.abspath(PDF_FOLDER)
        if os.path.exists(abs_pdf_folder):
            files = []
            for f in os.listdir(abs_pdf_folder):
                file_path = os.path.join(abs_pdf_folder, f)
                file_info = {
                    "name": f,
                    "size": os.path.getsize(file_path),
                    "modified": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                }
                files.append(file_info)
            
            return jsonify({
                "pdf_folder": abs_pdf_folder,
                "files": files,
                "folder_exists": True,
                "total_files": len(files)
            })
        else:
            return jsonify({
                "pdf_folder": abs_pdf_folder,
                "files": [],
                "folder_exists": False
            })
    except Exception as e:
        return jsonify({"error": str(e)})

# Test route to generate a sample PDF
@app.route('/debug/test-pdf', methods=["GET"])
def test_pdf():
    """Generate a test PDF to verify PDF generation works"""
    try:
        test_donations = [{"date": "2025-01-15", "amount": 1000.0}]
        receipt_no = f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        pdf_path = generate_pdf(
            "Test User",
            "1234567890", 
            test_donations,
            1,  # January
            2025,
            receipt_no
        )
        
        if pdf_path and os.path.exists(pdf_path):
            pdf_url = f"{request.host_url}download/{os.path.basename(pdf_path)}"
            return jsonify({
                "success": True,
                "pdf_path": pdf_path,
                "pdf_url": pdf_url,
                "file_exists": os.path.exists(pdf_path),
                "file_size": os.path.getsize(pdf_path)
            })
        else:
            return jsonify({"success": False, "error": "PDF generation failed"})
            
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == "__main__":
    # Create PDF folder on startup
    if not os.path.exists(PDF_FOLDER):
        os.makedirs(PDF_FOLDER)
        print(f"Created PDF folder: {os.path.abspath(PDF_FOLDER)}")
    
    app.run(debug=True, host="0.0.0.0")
