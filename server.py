import os
from flask import Flask, request, jsonify, render_template
from openai import OpenAI

# -----------------------------------------
#  FLASK APP SETUP
# -----------------------------------------
app = Flask(__name__, static_folder="static", template_folder="templates")

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
#  ROUTES
# -----------------------------------------

@app.route("/", methods=["GET"])
def index():
    """Serve the main UI."""
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    """Main chat endpoint for the AI bot."""
    try:
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

        # Add new user message
        messages.append({"role": "user", "content": user_message})

        # Call OpenAI
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=messages,
            temperature=0.3,
            max_tokens=900,
        )

        bot_reply = response.choices[0].message.content.strip()
        return jsonify({"reply": bot_reply}), 200

    except Exception as e:
        print("OpenAI / chat error:", e)
        return jsonify({
            "reply": (
                "I'm having trouble contacting the training engine. "
                "Try again in a moment. If it keeps happening, notify the Safety Officer."
            )
        }), 200


# -----------------------------------------
#  ENTRY POINT
# -----------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))





