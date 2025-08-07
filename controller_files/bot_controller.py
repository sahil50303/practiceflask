from app import app
from flask import render_template, request
from model_files.LLM_model import set_system_prompt, get_system_prompt

@app.route("/bot", methods=["GET", "POST"])
def Ai_bot():
    status_message = None  # default

    if request.method == "POST":
        form_type = request.form.get("form_type")

        if form_type == "system":
            new_prompt = request.form.get("system_message")
            set_system_prompt(new_prompt)
            status_message = "✅ System prompt updated successfully!"
        

        else:
            user_msg = request.form.get("user_input") 
            

    if request.method == "GET":
        render_template("bot.html",system_prompt=get_system_prompt(),status_message=status_message)
        


    # Always use the latest system prompt
    return render_template(
        "bot.html",
        system_prompt=get_system_prompt(),
        status_message=status_message
    )

