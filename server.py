import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

app = Flask(__name__, template_folder="templates")

# Load API key
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# ---------------------------------------------------------
#  SYSTEM PROMPT — HIGH-QUALITY TRAINING VERSION
# ---------------------------------------------------------

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
   • Begin with **Objective** (3-5 bullets)  
   • Provide a clear, short explanation (6–10 sentences max)  
   • End with a **quiz**: 5 short multiple choice questions  
   • After user answers, give correct answers and short explanations  
   • Then ask if they want to continue

3. Flow behavior:
   • If user says “Start” or “Begin training,” start at Module 1  
   • If they say “Next” or “Continue,” move to next module  
   • If they ask a question, pause training, answer, then resume  
   • Track where you are in the training based on conversation context

4. Exposure / Incident rules:
   • If the user describes a needlestick, splash, cut, or blood/body fluid exposure:
     – Tell them to IMMEDIATELY wash the exposed area (or flush eyes)  
     – Tell them to notify supervisor at once  
     – Tell them to follow Coastline exposure reporting procedures  
   • Do not provide medical care instructions beyond initial first steps

5. Boundaries:
   • Do NOT diagnose medical conditions  
   • Do NOT give treatment advice for patients  
   • Stay entirely within workplace safety and OSHA topics  
   • If unsure about a site-specific rule, say:  
     “Please follow your facility’s written policy or ask your supervisor.”

Always stay structured, focused, and training-oriented.
"""

# ---------------------------------------------------------
#  ROUTES
# ---------------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    try:
        data = request.get_json()
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"reply": "I didn’t receive a message. Please try again."}), 200

        # Build messages list with system + user
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]

        # OpenAI call
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=800,
        )

        bot_reply = response.choices[0].message.content
        return jsonify({"reply": bot_reply}), 200

    except Exception as e:
        print("Error contacting OpenAI:", e)
        return jsonify({
            "reply": (
                "I'm having temporary trouble reaching the training engine. "
                "Please try again shortly. If this keeps happening, notify the Safety Officer."
            )
        }), 200


# ---------------------------------------------------------
#  ENTRY POINT
# ---------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)


