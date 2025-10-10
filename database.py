import hashlib
import secrets
import os
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text

# Initialize SQLAlchemy
db = SQLAlchemy()

# SQLAlchemy Models
class Visitor(db.Model):
    __tablename__ = 'visitors'
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    user_agent = db.Column(db.Text)
    session_id = db.Column(db.String(255))
    visit_time = db.Column(db.DateTime, default=datetime.utcnow)

class QALog(db.Model):
    __tablename__ = 'qa_logs'
    id = db.Column(db.Integer, primary_key=True)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text, nullable=False)
    session_id = db.Column(db.String(255))
    context_coverage = db.Column(db.Float)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(255), unique=True, nullable=False)
    liked = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class AdminCredential(db.Model):
    __tablename__ = 'admin_credentials'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AdminSession(db.Model):
    __tablename__ = 'admin_sessions'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    session_token = db.Column(db.String(255), unique=True, nullable=False)
    expires_at = db.Column(db.Float, nullable=False)

class PortfolioDatabase:
    def __init__(self, app=None):
        if app:
            db.init_app(app)
            self.app = app
        else:
            # For backward compatibility
            self.app = None
        self.init_database()
    
    def _execute_sql(self, sql: str, params: tuple = (), fetch: bool = False):
        """Execute SQL query using SQLAlchemy."""
        if not self.app:
            raise ValueError("Database not properly initialized with Flask app!")
        
        with self.app.app_context():
            if fetch:
                result = db.session.execute(text(sql), params)
                return [dict(row._mapping) for row in result]
            else:
                db.session.execute(text(sql), params)
                db.session.commit()
    
    def init_database(self):
        """Initialize database with required tables."""
        if not self.app:
            return  # Skip if not initialized with app
        
        with self.app.app_context():
            # Create all tables
            db.create_all()
            
            # Initialize admin credentials if not exists
            self._init_admin_credentials()
    
    def _init_admin_credentials(self):
        """Initialize admin credentials."""
        result = self._execute_sql("SELECT COUNT(*) FROM admin_credentials", fetch=True)
        if result[0]['count'] == 0:
            # Default admin credentials
            username = "admin"
            password = "sarmi2024"
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            self._execute_sql('''
                INSERT INTO admin_credentials (username, password_hash, created_at)
                VALUES (%s, %s, %s)
            ''', (username, password_hash, datetime.now()))
    
    def add_visitor(self, ip_address: str, user_agent: str, session_id: str):
        """Add visitor to database."""
        self._execute_sql('''
            INSERT INTO visitors (ip_address, user_agent, session_id, visit_time)
            VALUES (%s, %s, %s, %s)
        ''', (ip_address, user_agent, session_id, datetime.now()))
    
    def get_visitor_count(self) -> int:
        """Get total visitor count."""
        result = self._execute_sql("SELECT COUNT(*) as count FROM visitors", fetch=True)
        return result[0]['count']
    
    def add_qa_log(self, question: str, answer: str, session_id: str, context_coverage: float):
        """Add Q&A log to database."""
        self._execute_sql('''
            INSERT INTO qa_logs (question, answer, session_id, context_coverage, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        ''', (question, answer, session_id, context_coverage, datetime.now()))
    
    def get_qa_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent Q&A logs."""
        return self._execute_sql('''
            SELECT question, answer, context_coverage, timestamp
            FROM qa_logs
            ORDER BY timestamp DESC
            LIMIT %s
        ''', (limit,), fetch=True)
    
    def toggle_like(self, session_id: str) -> bool:
        """Toggle like status for session."""
        # Check current status
        result = self._execute_sql(
            "SELECT liked FROM likes WHERE session_id = %s",
            (session_id,),
            fetch=True
        )
        
        if result:
            current_status = result[0]['liked']
            new_status = not current_status
            self._execute_sql(
                "UPDATE likes SET liked = %s WHERE session_id = %s",
                (new_status, session_id)
            )
        else:
            new_status = True
            self._execute_sql('''
                INSERT INTO likes (session_id, liked, timestamp)
                VALUES (%s, %s, %s)
            ''', (session_id, new_status, datetime.now()))
        
        return new_status
    
    def get_like_count(self) -> int:
        """Get total number of likes."""
        result = self._execute_sql("SELECT COUNT(*) as count FROM likes WHERE liked = true", fetch=True)
        return result[0]['count']
    
    def get_session_like_status(self, session_id: str) -> bool:
        """Get like status for specific session."""
        result = self._execute_sql(
            "SELECT liked FROM likes WHERE session_id = %s",
            (session_id,),
            fetch=True
        )
        return result[0]['liked'] if result else False
    
    def cleanup_expired_sessions(self):
        """Clean up expired admin sessions."""
        self._execute_sql('''
            DELETE FROM admin_sessions 
            WHERE expires_at < %s
        ''', (datetime.now().timestamp(),))
    
    def get_analytics(self) -> Dict:
        """Get comprehensive analytics data."""
        # Visitor stats
        total_visitors = self.get_visitor_count()
        
        # Unique visitors (by session_id)
        result = self._execute_sql(
            "SELECT COUNT(DISTINCT session_id) as count FROM visitors WHERE session_id IS NOT NULL",
            fetch=True
        )
        unique_visitors = result[0]['count']
        
        # Q&A stats
        result = self._execute_sql("SELECT COUNT(*) as count FROM qa_logs", fetch=True)
        total_qa = result[0]['count']
        
        # Like stats
        total_likes = self.get_like_count()
        
        # Recent activity
        result = self._execute_sql('''
            SELECT COUNT(*) as count FROM visitors 
            WHERE visit_time > CURRENT_TIMESTAMP - INTERVAL '24 hours'
        ''', fetch=True)
        visitors_24h = result[0]['count']
        
        return {
            "total_visitors": total_visitors,
            "unique_visitors": unique_visitors,
            "total_qa": total_qa,
            "total_likes": total_likes,
            "visitors_24h": visitors_24h
        }
    
    def verify_admin_password(self, username: str, password: str) -> bool:
        """Verify admin credentials."""
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        result = self._execute_sql('''
            SELECT id FROM admin_credentials 
            WHERE username = %s AND password_hash = %s
        ''', (username, password_hash), fetch=True)
        
        return len(result) > 0
    
    def create_admin_session(self, username: str) -> str:
        """Create admin session token."""
        session_token = secrets.token_urlsafe(32)
        expires_at = datetime.now().timestamp() + (24 * 60 * 60)  # 24 hours
        
        self._execute_sql('''
            INSERT INTO admin_sessions (username, session_token, expires_at)
            VALUES (%s, %s, %s)
        ''', (username, session_token, expires_at))
        
        return session_token
    
    def verify_admin_session(self, session_token: str) -> bool:
        """Verify admin session token."""
        result = self._execute_sql('''
            SELECT id FROM admin_sessions 
            WHERE session_token = %s AND expires_at > %s
        ''', (session_token, datetime.now().timestamp()), fetch=True)
        
        return len(result) > 0
