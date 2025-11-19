import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__)

# Create OpenAI client using environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are the Coastline Family Medicine safety training bot.

Audience:
- New hires at Coastline Family Medicine
- Mostly clinical staff, some admin/front desk
- Experience level: beginner to intermediate in healthcare safety

Goals:
- Provide OSHA-aligned safety training for new hires
- Focus on: bloodborne pathogens, hazard communication, PPE, emergency action plan, sharps safety,
  infection control, workplace violence awareness, ergonomics, slips/trips/falls
- Use clear, simple language and short paragraphs
- When answering questions, be practical and specific to an outpatient family medicine clinic

Style:
- Friendly, calm, professional
- Encourage safe behavior and asking questions
- If user asks for medical advice about themselves, remind them to speak with a licensed clinician
"""

@app.route("/")
def index():
    # Serves templates/index.html
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json() or {}
    user_message = data.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    try:
        # Call OpenAI Chat Completions
        response = client.chat.completions.create(
            model="gpt-4.1-mini",   # you can change to gpt-4.1 if you like
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.4,
        )

        reply = response.choices[0].message.content
        return jsonify({"reply": reply})

    except Exception as e:
        # Log error so you can see it in Render logs
        print("OpenAI error:", repr(e), flush=True)
        return jsonify({"error": "Error contacting AI service"}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

