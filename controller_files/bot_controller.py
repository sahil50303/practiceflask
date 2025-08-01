from app import app
from flask import render_template,request

@app.route("/bot",methods=["GET","POST"])
def Ai_bot():
    if request.method=="GET":
        return render_template("bot.html")
    else:
        form_type = request.form.get("form_type")
        if request.method=="POST" and form_type == "system":
            return "system button"
        else:
            return "AI button"

