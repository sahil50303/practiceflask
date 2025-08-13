from app import app
from flask import render_template, request
from model_files.LLM_model import (
    set_system_prompt,
    get_system_prompt,
    startup_prompt,
    LLM_responder,
    LLM_startup
)

# ---------------------- Warm up Gemini model at startup ----------------------
print("🔄 Warming up Gemini model with FAQ data...")
try:
    response = LLM_startup(startup_prompt)
    print("✅ Gemini model is ready to chat!")
except Exception as e:
    print(f"⚠️ Warmup failed: {e}")
# -----------------------------------------------------------------------------


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
            # Response handling will come here later
            

    if request.method == "GET":
        return render_template(
            "bot.html",
            system_prompt=get_system_prompt(),
            status_message=status_message,
            greeting="Jai Shree Krishna, how can I help you?"
        )

    # Fallback render
    return render_template(
        "bot.html",
        system_prompt=get_system_prompt(),
        status_message=status_message
    )
