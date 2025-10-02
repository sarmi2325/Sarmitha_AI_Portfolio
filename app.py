from flask import Flask, request, render_template, jsonify
from smart_ai import SmartAIPortfolio
import os
import re
from dotenv import load_dotenv
from collections import deque

# Load environment variables
load_dotenv()

# Flask Setup
app = Flask(__name__)

# Initialize Smart AI Portfolio System
ai_system = SmartAIPortfolio()

# Session context - store last 5 messages (100/5 = 20% per message)
chat_context = deque(maxlen=5)

def preprocess(text):
    return re.sub(r'\b(she|her|sarmitha)\b', 'you', text, flags=re.IGNORECASE)

@app.route("/")
def home():
    return render_template("home.html")

@app.route('/home')
def home1():
    return render_template('home.html')

@app.route("/chat", methods=["POST"])
def chat():
    user_raw = request.json.get("message", "").strip()
    if not user_raw:
        return jsonify({"response": "❗ Please enter a valid message."})

    # Process with Smart AI System (pass current context)
    response, context_coverage = ai_system.process_query(
        user_raw, 
        list(chat_context)  # Pass all current context
    )
    
    # Add both user message and AI response to context
    chat_context.append({"role": "user", "content": user_raw})
    chat_context.append({"role": "assistant", "content": response})
    
    return jsonify({
        "response": response,
        "context_coverage": context_coverage
    })

@app.route("/update-resume", methods=["POST"])
def update_resume():
    """Manually update resume from Notion."""
    try:
        print("🔄 Manual resume update requested...")
        ai_system._update_embeddings()
        return jsonify({"status": "success", "message": "Resume updated successfully"})
    except Exception as e:
        print(f"⚠️ Manual update failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)