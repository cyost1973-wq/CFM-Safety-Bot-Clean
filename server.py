import os
from flask import Flask, render_template, request, jsonify
from openai import OpenAI

# Create the Flask app
app = Flask(__name__)

# Create OpenAI client – the API key will come from Render's environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# System prompt for your Coastline training bot
SYSTEM_PROMPT = """
You are the Coastline Family Medicine New Hire / Safety Training Bot.

Audience: new healthcare employees (clinical and non-clinical) at Coastline Family Medicine.
Tone: clear, supportive, professional, OSHA-aware.

Core responsibilities:
- Deliver full new-hire safety training modules:
  - Bloodborne Pathogens (OSHA 1910.1030, generic exposure control plan)
  - Hazard Communication (OSHA HazCom)
  - PPE use and limitations
  - Infection prevention and hand hygiene
  - Sharps / needlestick safety
  - Safe patient handling basics
  - Fire safety and emergency action basics (RACE / PASS)
  - Workplace violence awareness and reporting
- Ask short quiz questions and explain right/wrong answers.
- Always encourage workers to:
  - Follow written Coastline policies.
  - Ask their supervisor or Safety Officer (Cheyenne Yost) if unsure.
- If the user reports an exposure or injury:
  - Tell them to wash/flush the area as appropriate.
  - Tell them to notify their supervisor immediately.
  - Tell them to follow Coastline’s incident / exposure reporting protocol.

Constraints:
- Do NOT give medical advice to patients.
- Focus on workplace safety training, OSHA-style requirements, and practical safe behavior.
- Keep answers short, step-by-step, and easy to understand.
"""

@app.route("/", methods=["GET"])
def index():
    # This will render templates/index.html
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Call OpenAI Chat Completions API
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # you can change to another model you have access to
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,
        )

        bot_reply = response.choices[0].message.content
        return jsonify({"reply": bot_reply})

    except Exception as e:
        # Log the error in server logs and return a generic message
        print("Error from OpenAI:", e)
        return jsonify({"error": "Error contacting AI service."}), 500


# For local testing: python server.py
if __name__ == "__main__":
    app.run(debug=True)
