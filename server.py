"""
Prajna — Lightweight Flask server
Serves the static frontend and proxies chat requests to Ollama.
Provides API endpoints for auth, progress tracking, and calendar data.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from backend.gemini_api import get_response
from backend.db_manager import (
    init_db, login_and_update_streak, log_concept,
    log_quiz_result, get_student_progress, get_due_reviews, get_calendar_data
)
import os
import sqlite3

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

app = Flask(__name__, static_folder=None)
CORS(app)

# Ensure DB is ready
init_db()

# ─── Static file serving ───
@app.route("/")
def index():
    return send_from_directory(FRONTEND_DIR, "login.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(FRONTEND_DIR, path)

# ─── Auth API ───
@app.route("/api/login", methods=["POST"])
def login():
    """
    Expects JSON: { "name": "...", "password": "..." }
    Returns: { "student_id": int, "streak": int, "name": "..." }
    """
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    password = (data.get("password") or "").strip()

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not password:
        return jsonify({"error": "Password is required"}), 400
    if password != data.get("password", ""):
        return jsonify({"error": "Password cannot have leading/trailing spaces"}), 400

    try:
        student_id, streak = login_and_update_streak(name, password)
        return jsonify({
            "student_id": student_id,
            "streak": streak,
            "name": name
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

# ─── Chat API ───
@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Expects JSON:
    {
        "message": "user text",
        "history": [ {"role":"user","content":"..."}, ... ],
        "images": [ "base64string", ... ],
        "mode": "fast" | "deep",
        "language": "Hindi" | "English",
        "student_id": int
    }
    """
    data = request.get_json(force=True)

    user_input = data.get("message", "").strip()
    history    = data.get("history", [])
    images     = data.get("images", None)
    language   = data.get("language", "Hindi")
    student_id = data.get("student_id")

    mode_map = {"fast": "Fast Result", "deep": "Long Think"}
    mode = mode_map.get(data.get("mode", "fast"), "Fast Result")

    if not user_input and not images:
        return jsonify({"error": "Empty message"}), 400

    # Fetch weak topics for spaced repetition
    weak_topics = None
    if student_id:
        due = get_due_reviews(student_id)
        if due:
            weak_topics = ", ".join([t[0] for t in due])

    result = get_response(
        user_input=user_input,
        chat_history=history if history else None,
        images=images if images else None,
        weak_topics=weak_topics,
        language=language,
        mode=mode,
    )

    # Log concept if not a quiz/game action
    if student_id and result.get("topic") != "Error":
        action = result.get("action", "explain")
        if action not in ("quiz", "game"):
            try:
                log_concept(student_id, result.get("topic", "General"), result.get("status", "Learning"))
            except Exception:
                pass

    return jsonify(result)

# ─── Quiz Result API ───
@app.route("/api/quiz-result", methods=["POST"])
def quiz_result():
    """
    Expects JSON:
    {
        "student_id": int,
        "topic": "...",
        "quiz_type": "mcq|spot_the_mistake|fill_blank",
        "question": "...",
        "student_answer": "...",
        "correct_answer": "...",
        "is_correct": bool
    }
    """
    data = request.get_json(force=True)
    student_id = data.get("student_id")
    if not student_id:
        return jsonify({"error": "student_id required"}), 400

    log_quiz_result(
        student_id=student_id,
        topic=data.get("topic", "Unknown"),
        quiz_type=data.get("quiz_type", "mcq"),
        question=data.get("question", ""),
        student_answer=data.get("student_answer", ""),
        correct_answer=data.get("correct_answer", ""),
        is_correct=data.get("is_correct", False),
    )
    return jsonify({"ok": True})

# ─── Progress API ───
@app.route("/api/progress/<int:student_id>")
def progress(student_id):
    """Returns mastered/learning/struggling counts + streak + badges."""
    counts = get_student_progress(student_id)

    # Get streak
    try:
        with sqlite3.connect("students.db") as conn:
            cur = conn.cursor()
            cur.execute("SELECT current_streak, highest_streak FROM Streaks WHERE student_id = ?", (student_id,))
            row = cur.fetchone()
            streak = row[0] if row else 0
            highest = row[1] if row else 0
    except Exception:
        streak, highest = 0, 0

    badges = []
    if streak >= 30:
        badges.append("🥇 30-Day Champion")
    if streak >= 7:
        badges.append("🥈 Week Warrior")
    if streak >= 3:
        badges.append("🥉 3-Day Starter")

    return jsonify({
        "mastered": counts.get("Mastered", 0),
        "learning": counts.get("Learning", 0),
        "struggling": counts.get("Struggling", 0),
        "streak": streak,
        "highest_streak": highest,
        "badges": badges,
    })

# ─── Calendar API ───
@app.route("/api/calendar/<int:student_id>")
def calendar(student_id):
    """Returns calendar data: active days + future review dates."""
    past_data, future_data = get_calendar_data(student_id)
    # Convert active dates to a simple list of date strings
    active_dates = list(past_data.keys())
    return jsonify({
        "active_dates": active_dates,
        "future_reviews": future_data,
    })

# ─── Health check ───
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  Prajna server running on http://localhost:{port}/login.html\n")
    app.run(host="0.0.0.0", port=port, debug=False)
