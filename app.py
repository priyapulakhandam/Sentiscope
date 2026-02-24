from flask import Flask, request, jsonify,render_template
from flask_cors import CORS
import json
import os
from database import db
from models import EmailAnalysis
from auth_routes import auth_bp

from services.tone_service import analyze_tone
from services.clarity_service import analyze_clarity
from services.rewrite_service import rewrite_text

app = Flask(__name__)
# ---------- FRONTEND ROUTES ----------

@app.route("/")
def landing_page():
    return render_template("index.html")

@app.route("/login-page")
def login_page():
    return render_template("login.html")

@app.route("/signup-page")
def signup_page():
    return render_template("signup.html")

@app.route("/compose-page")
def compose_page():
    return render_template("compose.html")

@app.route("/history-page")
def history_page():
    return render_template("history.html")

@app.route("/dashboard-page")
def dashboard_page():
    return render_template("dashboard.html")

app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
# ---------- DB CONFIG ----------

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

with app.app_context():
    db.create_all()

# ---------- REGISTER AUTH ----------
app.register_blueprint(auth_bp)

# ---------- ANALYZE ----------
@app.route("/analyze/realtime", methods=["POST"])
def realtime_analysis():
    data = request.json
    text = data.get("text", "").strip()
    user_id = data.get("user_id")   # ✅ FIX

    if not text or not user_id:
        return jsonify({"error": "Missing text or user"}), 400

    tone_result = analyze_tone(text)
    clarity_result = analyze_clarity(text)

    analysis = EmailAnalysis(
        user_id=user_id,
        email_text=text,
        tone=tone_result["label"],
        confidence=tone_result["confidence"],
        explanation=tone_result.get("explanation"),
        clarity_score=clarity_result.get("clarity_score"),
        clarity_issues=json.dumps(clarity_result.get("issues")),
        rewritten_text=None
    )

    db.session.add(analysis)
    db.session.commit()

    return jsonify({
        "tone": tone_result,
        "clarity": clarity_result
    })


# ---------- REWRITE ----------
@app.route("/rewrite", methods=["POST"])
def rewrite():
    data = request.get_json(force=True) or {}

    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"success": False, "rewritten_text": "", "error": "Text is required"}), 400

    # ✅ Take tone from frontend
    tone = (data.get("tone") or "neutral").lower()

    # ✅ Normalize tone into supported values
    if tone in ["harsh", "angry", "rude"]:
        tone = "harsh"
    elif tone in ["firm", "urgent"]:
        tone = "firm"
    elif tone in ["polite", "apologetic", "friendly"]:
        tone = "polite"
    else:
        tone = "neutral"

    clarity_issues = data.get("clarity_issues") or []

    result = rewrite_text(
        text=text,
        tone=tone,
        clarity_issues=clarity_issues
    )

    return jsonify(result), 200

# ---------- HISTORY ----------
@app.route("/history", methods=["GET"])
def history():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify([])

    analyses = EmailAnalysis.query.filter_by(user_id=user_id)\
        .order_by(EmailAnalysis.created_at.desc())\
        .all()

    return jsonify([
        {
            "text": a.email_text[:120] + ("..." if len(a.email_text) > 120 else ""),
            "tone": a.tone,
            "clarityIssues": json.loads(a.clarity_issues),
            "time": a.created_at.strftime("%Y-%m-%d %H:%M")
        }
        for a in analyses
    ])
# ---------- CLEAR HISTORY ----------
@app.route("/history/clear", methods=["DELETE"])
def clear_history():
    user_id = request.args.get("user_id")

    if not user_id:
        return jsonify({"error": "User ID required"}), 400

    EmailAnalysis.query.filter_by(user_id=user_id).delete()
    db.session.commit()

    return jsonify({"message": "History cleared successfully"})


# ---------- DASHBOARD ----------
@app.route("/dashboard", methods=["GET"])
def dashboard():
    user_id = request.args.get("user_id")

    analyses = EmailAnalysis.query.filter_by(user_id=user_id).all()

    return jsonify({
        "total": len(analyses),
        "polite": sum(a.tone == "polite" for a in analyses),
        "neutral": sum(a.tone == "neutral" for a in analyses),
        "harsh": sum(a.tone == "harsh" for a in analyses)
    })


if __name__ == "__main__":
    app.run(debug=True)
