from flask import Flask, request, render_template, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from smart_ai import SmartAIPortfolio
from database import PortfolioDatabase
import os
import re
import secrets
from dotenv import load_dotenv
from collections import deque
from datetime import datetime

# Load environment variables
load_dotenv()

# Flask Setup
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# SQLAlchemy Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize Database
try:
    db = PortfolioDatabase(app)
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"❌ Database initialization failed: {e}")
    db = None

# Initialize Smart AI Portfolio System
ai_system = SmartAIPortfolio()

# Session context - store last 5 messages (100/5 = 20% per message)
chat_context = deque(maxlen=5)

def preprocess(text):
    return re.sub(r'\b(she|her|sarmitha)\b', 'you', text, flags=re.IGNORECASE)

def get_session_id():
    """Get or create session ID."""
    if 'session_id' not in session:
        session['session_id'] = secrets.token_urlsafe(32)
    return session['session_id']

@app.route("/")
def home():
    # Track visitor
    session_id = get_session_id()
    if db:
        try:
            db.add_visitor(
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                session_id=session_id
            )
        except Exception as e:
            print(f"⚠️ Failed to track visitor: {e}")
    return render_template("home.html")

@app.route('/home')
def home1():
    # Track visitor
    session_id = get_session_id()
    if db:
        try:
            db.add_visitor(
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                session_id=session_id
            )
        except Exception as e:
            print(f"⚠️ Failed to track visitor: {e}")
    return render_template('home.html')

@app.route("/chat", methods=["POST"])
def chat():
    session_id = get_session_id()
    user_raw = request.json.get("message", "").strip()
    if not user_raw:
        return jsonify({"response": "❗ Please enter a valid message."})

    # Process with Smart AI System (pass current context)
    response, context_coverage = ai_system.process_query(
        user_raw, 
        list(chat_context)  # Pass all current context
    )
    
    # Store Q&A in database
    if db:
        try:
            db.add_qa_log(
                question=user_raw,
                answer=response,
                session_id=session_id,
                context_coverage=context_coverage
            )
        except Exception as e:
            print(f"⚠️ Failed to store Q&A log: {e}")
    
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
        print("Manual resume update requested...")
        ai_system._update_embeddings()
        return jsonify({"status": "success", "message": "Resume updated successfully"})
    except Exception as e:
        print(f"⚠️ Manual update failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/admin-data", methods=["GET"])
def get_admin_data():
    """Get visitor count and Q&A logs for admin interface."""
    if not db:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        # Clean up expired sessions
        db.cleanup_expired_sessions()
        
        analytics = db.get_analytics()
        qa_logs = db.get_qa_logs(limit=50)
        
        return jsonify({
            "visitor_count": analytics["total_visitors"],
            "unique_visitors": analytics["unique_visitors"],
            "total_qa": analytics["total_qa"],
            "total_likes": analytics["total_likes"],
            "visitors_24h": analytics["visitors_24h"],
            "qa_logs": qa_logs
        })
    except Exception as e:
        print(f"⚠️ Failed to get admin data: {e}")
        return jsonify({"error": "Failed to retrieve admin data"}), 500

@app.route("/like", methods=["POST"])
def toggle_like():
    """Toggle like status for current session."""
    if not db:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        session_id = get_session_id()
        new_status = db.toggle_like(session_id)
        total_likes = db.get_like_count()
        
        return jsonify({
            "liked": new_status,
            "total_likes": total_likes
        })
    except Exception as e:
        print(f"⚠️ Failed to toggle like: {e}")
        return jsonify({"error": "Failed to toggle like"}), 500

@app.route("/like-status", methods=["GET"])
def get_like_status():
    """Get like status for current session."""
    if not db:
        return jsonify({"error": "Database not available"}), 500
    
    try:
        session_id = get_session_id()
        liked = db.get_session_like_status(session_id)
        total_likes = db.get_like_count()
        
        return jsonify({
            "liked": liked,
            "total_likes": total_likes
        })
    except Exception as e:
        print(f"⚠️ Failed to get like status: {e}")
        return jsonify({"error": "Failed to get like status"}), 500

@app.route("/admin-auth", methods=["POST"])
def admin_auth():
    """Authenticate admin user."""
    if not db:
        return jsonify({"success": False, "message": "Database not available"}), 500
    
    try:
        data = request.json
        username = data.get("username", "").strip()
        password = data.get("password", "").strip()
        
        if not username or not password:
            return jsonify({"success": False, "message": "Username and password required"}), 400
        
        if db.verify_admin_password(username, password):
            session_token = db.create_admin_session(username)
            return jsonify({
                "success": True,
                "session_token": session_token,
                "message": "Authentication successful"
            })
        else:
            return jsonify({"success": False, "message": "Invalid credentials"}), 401
    except Exception as e:
        print(f"⚠️ Failed to authenticate admin: {e}")
        return jsonify({"success": False, "message": "Authentication failed"}), 500

@app.route("/admin-verify", methods=["POST"])
def verify_admin_session():
    """Verify admin session token."""
    if not db:
        return jsonify({"valid": False}), 500
    
    try:
        data = request.json
        session_token = data.get("session_token", "").strip()
        
        if db.verify_admin_session(session_token):
            return jsonify({"valid": True})
        else:
            return jsonify({"valid": False}), 401
    except Exception as e:
        print(f"⚠️ Failed to verify admin session: {e}")
        return jsonify({"valid": False}), 500

if __name__ == "__main__":
    app.run()
