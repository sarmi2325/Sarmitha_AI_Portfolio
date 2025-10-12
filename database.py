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
        with self.app.app_context():
            # Check if admin credentials exist
            existing_admin = AdminCredential.query.first()
            if not existing_admin:
                # Create default admin credentials
                username = os.getenv('ADMIN_USERNAME')
                password = os.getenv('ADMIN_PASSWORD')
    
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                
                admin_cred = AdminCredential(
                    username=username,
                    password_hash=password_hash,
                    created_at=datetime.utcnow()
                )
                db.session.add(admin_cred)
                db.session.commit()
    
    def add_visitor(self, ip_address: str, user_agent: str, session_id: str):
        """Add visitor to database."""
        with self.app.app_context():
            visitor = Visitor(
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                visit_time=datetime.utcnow()
            )
            db.session.add(visitor)
            db.session.commit()
    
    def get_visitor_count(self) -> int:
        """Get total visitor count."""
        with self.app.app_context():
            return Visitor.query.count()
    
    def add_qa_log(self, question: str, answer: str, session_id: str, context_coverage: float):
        """Add Q&A log to database."""
        with self.app.app_context():
            qa_log = QALog(
                question=question,
                answer=answer,
                session_id=session_id,
                context_coverage=context_coverage,
                timestamp=datetime.utcnow()
            )
            db.session.add(qa_log)
            db.session.commit()
    
    def get_qa_logs(self, limit: int = 50) -> List[Dict]:
        """Get recent Q&A logs."""
        with self.app.app_context():
            logs = QALog.query.order_by(QALog.timestamp.desc()).limit(limit).all()
            return [
                {
                    'question': log.question,
                    'answer': log.answer,
                    'context_coverage': log.context_coverage,
                    'timestamp': log.timestamp.strftime('%Y-%m-%d %H:%M:%S')
                }
                for log in logs
            ]
    
    def toggle_like(self, session_id: str) -> bool:
        """Toggle like status for session."""
        with self.app.app_context():
            existing_like = Like.query.filter_by(session_id=session_id).first()
            
            if existing_like:
                # Toggle existing like
                existing_like.liked = not existing_like.liked
                new_status = existing_like.liked
            else:
                # Create new like
                new_like = Like(
                    session_id=session_id,
                    liked=True,
                    timestamp=datetime.utcnow()
                )
                db.session.add(new_like)
                new_status = True
            
            db.session.commit()
            return new_status
    
    def get_like_count(self) -> int:
        """Get total number of likes."""
        with self.app.app_context():
            return Like.query.filter_by(liked=True).count()
    
    def get_session_like_status(self, session_id: str) -> bool:
        """Get like status for specific session."""
        with self.app.app_context():
            like = Like.query.filter_by(session_id=session_id).first()
            return like.liked if like else False
    
    def cleanup_expired_sessions(self):
        """Clean up expired admin sessions."""
        with self.app.app_context():
            current_time = datetime.now().timestamp()
            AdminSession.query.filter(AdminSession.expires_at < current_time).delete()
            db.session.commit()
    
    def get_analytics(self) -> Dict:
        """Get comprehensive analytics data."""
        with self.app.app_context():
            # Visitor stats
            total_visitors = Visitor.query.count()
            
            # Unique visitors (by session_id)
            unique_visitors = db.session.query(Visitor.session_id).filter(Visitor.session_id.isnot(None)).distinct().count()
            
            # Q&A stats
            total_qa = QALog.query.count()
            
            # Like stats
            total_likes = Like.query.filter_by(liked=True).count()
            
            # Recent activity (24h)
            from datetime import timedelta
            yesterday = datetime.utcnow() - timedelta(hours=24)
            visitors_24h = Visitor.query.filter(Visitor.visit_time > yesterday).count()
            
            return {
                "total_visitors": total_visitors,
                "unique_visitors": unique_visitors,
                "total_qa": total_qa,
                "total_likes": total_likes,
                "visitors_24h": visitors_24h
            }
    
    def verify_admin_password(self, username: str, password: str) -> bool:
        """Verify admin credentials."""
        with self.app.app_context():
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            admin = AdminCredential.query.filter_by(username=username, password_hash=password_hash).first()
            return admin is not None
    
    def create_admin_session(self, username: str) -> str:
        """Create admin session token."""
        with self.app.app_context():
            session_token = secrets.token_urlsafe(32)
            expires_at = datetime.now().timestamp() + (24 * 60 * 60)  # 24 hours
            
            admin_session = AdminSession(
                username=username,
                session_token=session_token,
                expires_at=expires_at
            )
            db.session.add(admin_session)
            db.session.commit()
            
            return session_token
    
    def verify_admin_session(self, session_token: str) -> bool:
        """Verify admin session token."""
        with self.app.app_context():
            current_time = datetime.now().timestamp()
            session = AdminSession.query.filter_by(session_token=session_token).filter(AdminSession.expires_at > current_time).first()
            return session is not None
