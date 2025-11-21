import os
import csv
from datetime import datetime

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    session,
    send_file,
)
from openai import OpenAI

# -----------------------------------------
#  FLASK APP SETUP
# -----------------------------------------
app = Flask(
    __name__,
    static_folder="static",
    template_folder="templates",
)

# IMPORTANT: set a strong secret key in Render env vars:
# e.g. FLASK_SECRET_KEY = some-long-random-string
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-change-me")

# Where to log training interactions (simple CSV for now)
TRAINING_LOG_PATH = os.environ.get(
    "TRAINING_LOG_PATH",
    "training_log.csv"
)

# -----------------------------------------
#  OPENAI CLIENT
# -----------------------------------------
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))


# -----------------------------------------
#  SYSTEM PROMPT — OSHA TRAINING BOT
# -----------------------------------------
SYSTEM_PROMPT = """
You are the **Coastline Family Medicine New Hire / Safety Training Bot**.

Audience:
- New clinical and non-clinical staff with little or no prior safety training.

Tone:
- Clear, supportive, OSHA-aligned, professional.
- Use bullet points and short paragraphs.
- Avoid jargon, or explain it simply.

Your role:
1. Deliver a **complete OSHA-aligned safety training program**, including:
   • General orientation & safety expectations
   • Bloodborne Pathogens (1910.1030, using a generic ECP)
   • Hazard Communication (labels, SDS, chemicals)
   • Infection prevention & PPE
   • Sharps injury & needlestick prevention
   • Safe patient handling basics
   • Fire & emergency action plan (RACE / PASS basics)
   • Workplace violence awareness
   • Incident & exposure reporting procedures

2. For each module:
   • Begin with **Objective** (3–5 bullets)
   • Provide a clear, short explanation (6–10 sentences max)
   • End with a **quiz** (5 MCQs)
   • After user answers, give correct answers & brief explanation
   • Then confirm if they want to continue

3. Flow behavior:
   • “Start training” → begin at Module 1
   • “Next” / “Continue” → next module
   • Questions pause training, answer, then resume
   • Infer training module from context

4. Exposure / Incident rules:
   • For needlestick, splash, cut, or blood exposure:
       – Tell them to wash/flush the area
       – Notify supervisor
       – Follow Coastline exposure reporting procedures
   • No medical diagnosis or treatment advice

5. Boundaries:
   • Do NOT diagnose or treat medical issues
   • ONLY provide workplace safety guidance
   • For uncertain site-specific policies:
     “Follow your facility’s written policy or ask your supervisor.”

Stay structured, focused, and training-oriented.
"""


# -----------------------------------------
#  HELPER: LOG TRAINING INTERACTIONS
# -----------------------------------------
def log_training_interaction(emp_id, emp_name, role, user_msg, bot_reply):
    """
    Append a simple row to training_log.csv
    NOTE: Render’s disk is ephemeral; for long-term storage,
    attach a database later. This is fine for initial tracking
    and exports.
    """
    try:
        file_exists = os.path.exists(TRAINING_LOG_PATH)
        with open(TRAINING_LOG_PATH, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "timestamp",
                    "employee_id",
                    "employee_name",
                    "role",
                    "user_message",
                    "bot_reply"
                ])
            writer.writerow([
                datetime.utcnow().isoformat(),
                emp_id,
                emp_name,
                role,
                user_msg,
                bot_reply
            ])
    except Exception as e:
        # Don't break the app if logging fails; just print error
        print("Training log write error:", e)


# -----------------------------------------
#  ROUTES
# -----------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/login", methods=["POST"])
def login():
    """
    Lightweight 'login' for training:
    - employee_name
    - employee_id
    - role (e.g., MA, RN, Front Desk)
    No password for now, since this is an internal training portal.
    """
    data = request.get_json() or {}
    emp_name = (data.get("employee_name") or "").strip()
    emp_id = (data.get("employee_id") or "").strip()
    role = (data.get("role") or "").strip()

    if not emp_name or not emp_id:
        return jsonify({"ok": False, "error": "Name and Employee ID are required."}), 400

    # Store in session so /chat can use it
    session["employee_name"] = emp_name
    session["employee_id"] = emp_id
    session["role"] = role or "Unknown"

    return jsonify({"ok": True})


@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint for the AI bot."""
    try:
        # Require login first
        emp_name = session.get("employee_name")
        emp_id = session.get("employee_id")
        role = session.get("role", "Unknown")

        if not emp_name or not emp_id:
            return jsonify({
                "reply": (
                    "You’re not logged in. Please refresh the page and complete the "
                    "login form before starting training."
                )
            }), 200

        data = request.get_json() or {}
        user_message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not user_message:
            return jsonify({"reply": "I didn’t receive anything — try again?"}), 200

        # Build conversation list for the model
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Rebuild conversation history (last 6 turns)
        for turn in history[-6:]:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("assistant"):
                messages.append({"role": "assistant", "content": turn["assistant"]})

        # Add new user message (with name so the bot can greet personally if it wants)
        messages.append({
            "role": "user",
            "content": f"Employee: {emp_name} (ID: {emp_id}, Role: {role}). Message: {user_message}"
        })

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=900,
        )

        bot_reply = response.choices[0].message.content.strip()

        # Log this turn
        log_training_interaction(emp_id, emp_name, role, user_message, bot_reply)

        return jsonify({"reply": bot_reply}), 200

    except Exception as e:
        print("OpenAI / chat error:", e)
        return jsonify({
            "reply": (
                "I'm having trouble contacting the training engine. "
                "Try again in a moment. If it keeps happening, notify the Safety Officer."
            )
        }), 200

    return send_file(
        TRAINING_LOG_PATH,
        as_attachment=True,
        download_name="training_log.csv"
    )
    
@app.route("/admin/download-log", methods=["GET"])
def download_log():
    """
    Download the raw training_log.csv file.
    For now there is no authentication on this route,
    so only share the URL internally.
    """
    if not os.path.exists(TRAINING_LOG_PATH):
        return "No log file found yet.", 404

# -----------------------------------------
#  ENTRY POINT
# -----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))







