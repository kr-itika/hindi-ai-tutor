"""
Prajna — Lightweight Flask server
Serves the static frontend and proxies chat requests to Ollama.
Provides API endpoints for auth, progress tracking, and calendar data.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from backend.gemini_api import get_response, generate_title
from backend.db_manager import (
    init_db, login_and_update_streak, log_concept,
    log_quiz_result, get_student_progress, get_due_reviews, get_calendar_data,
    DB_NAME,
    create_conversation, get_conversations, get_messages, add_message,
    rename_conversation, delete_conversation
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
    raw_password = data.get("password") or ""

    if not name:
        return jsonify({"error": "Name is required"}), 400
    if not raw_password:
        return jsonify({"error": "Password is required"}), 400
    if raw_password != raw_password.strip():
        return jsonify({"error": "Password cannot have leading/trailing spaces"}), 400
    password = raw_password.strip()

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

    # Log concept discussed (no status — mastery is only determined by quiz results)
    if student_id and result.get("status") != "Error":
        action = result.get("action", "explain")
        if action not in ("quiz", "game"):
            try:
                log_concept(student_id, result.get("topic", "General"))
            except Exception:
                pass

    # Persist messages and generate AI title for new conversations
    conversation_id = data.get("conversation_id")
    if student_id and conversation_id:
        try:
            reply_text = result.get("tutor_response", "")
            if user_input:
                add_message(conversation_id, "user", user_input)
            add_message(conversation_id, "assistant", reply_text)

            # AI-generated title: only on the first exchange (title is still 'New Chat')
            convos = get_conversations(student_id)
            current = next((c for c in convos if c["conversation_id"] == conversation_id), None)
            if current and current["title"] == "New Chat" and user_input:
                # Run title generation in a background thread so it doesn't block the response
                import threading
                def _make_title():
                    try:
                        title = generate_title(user_input, language)
                        rename_conversation(conversation_id, title)
                    except Exception:
                        pass
                threading.Thread(target=_make_title, daemon=True).start()
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
        with sqlite3.connect(DB_NAME, timeout=10) as conn:
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
    """Returns the list of dates the student was active on the platform."""
    active_dates = get_calendar_data(student_id)
    return jsonify({"active_dates": active_dates})

# ─── Conversation History API ───
@app.route("/api/conversations", methods=["POST"])
def new_conversation():
    """Creates a new conversation. Expects: { student_id, title? }"""
    data = request.get_json(force=True)
    student_id = data.get("student_id")
    if not student_id:
        return jsonify({"error": "student_id required"}), 400
    cid = create_conversation(student_id, data.get("title", "New Chat"))
    return jsonify({"conversation_id": cid})


@app.route("/api/conversations/<int:student_id>")
def list_conversations(student_id):
    """Returns all conversations for a student."""
    return jsonify(get_conversations(student_id))


@app.route("/api/conversations/<int:conversation_id>/messages")
def conversation_messages(conversation_id):
    """Returns all messages in a conversation."""
    return jsonify(get_messages(conversation_id))


@app.route("/api/conversations/<int:conversation_id>", methods=["DELETE"])
def delete_convo(conversation_id):
    """Deletes a conversation and all its messages."""
    delete_conversation(conversation_id)
    return jsonify({"ok": True})


@app.route("/api/conversations/<int:conversation_id>", methods=["PATCH"])
def rename_convo(conversation_id):
    """Renames a conversation. Expects: { title }"""
    data = request.get_json(force=True)
    rename_conversation(conversation_id, data.get("title", "Chat"))
    return jsonify({"ok": True})


# ─── Health check ───
@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print(f"\n  Prajna server running on http://localhost:{port}/\n")
    app.run(host="0.0.0.0", port=port, debug=False)
