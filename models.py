from database import db
from datetime import datetime

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    analyses = db.relationship("EmailAnalysis", backref="user", lazy=True)


class EmailAnalysis(db.Model):
    __tablename__ = "email_analyses"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    email_text = db.Column(db.Text, nullable=False)
    tone = db.Column(db.String(20))
    confidence = db.Column(db.Float)
    explanation = db.Column(db.Text)

    clarity_score = db.Column(db.Integer)
    clarity_issues = db.Column(db.Text)  # JSON string
    rewritten_text = db.Column(db.Text)
    

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
