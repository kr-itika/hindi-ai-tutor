import sqlite3
import hashlib
import logging
import os
from datetime import date, datetime, timedelta

logger = logging.getLogger(__name__)

DB_NAME = "students.db"
OLD_DB_NAME = "tutor.db"


def _migrate_old_db():
    """Renames tutor.db to students.db if only the old file exists."""
    if os.path.exists(OLD_DB_NAME) and not os.path.exists(DB_NAME):
        os.rename(OLD_DB_NAME, DB_NAME)
        logger.info("Migrated %s → %s", OLD_DB_NAME, DB_NAME)


def _hash_password(password):
    """Returns a SHA-256 hash of the given password."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def init_db():
    """Initializes the database with the required tables."""
    _migrate_old_db()

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # 1. Students Table (The Profile)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Students (
                student_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                join_date TEXT NOT NULL
            )
        ''')

        # 2. Streaks Table (Daily Activity Tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS Streaks (
                student_id INTEGER PRIMARY KEY,
                last_active_date TEXT,
                current_streak INTEGER DEFAULT 0,
                highest_streak INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES Students(student_id)
            )
        ''')

        # 3. ConceptLogs Table (The "Memory" for Weak Topics)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ConceptLogs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                concept_name TEXT NOT NULL,
                status TEXT NOT NULL,  -- e.g., 'Mastered', 'Struggling', 'Learning'
                timestamp TEXT NOT NULL,
                next_review_date TEXT,
                interval_days INTEGER DEFAULT 0,
                FOREIGN KEY (student_id) REFERENCES Students(student_id)
            )
        ''')

        # 4. QuizLogs Table (Quiz Performance Tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS QuizLogs (
                quiz_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id INTEGER,
                topic TEXT NOT NULL,
                quiz_type TEXT NOT NULL,
                question TEXT NOT NULL,
                student_answer TEXT NOT NULL,
                correct_answer TEXT NOT NULL,
                is_correct INTEGER NOT NULL,  -- 1 = correct, 0 = wrong
                timestamp TEXT NOT NULL,
                FOREIGN KEY (student_id) REFERENCES Students(student_id)
            )
        ''')

        # Add password_hash column if upgrading from old schema
        try:
            cursor.execute("ALTER TABLE Students ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
            logger.info("Added password_hash column to Students table.")
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add next_review_date and interval_days if upgrading from old schema
        try:
            cursor.execute("ALTER TABLE ConceptLogs ADD COLUMN next_review_date TEXT")
            cursor.execute("ALTER TABLE ConceptLogs ADD COLUMN interval_days INTEGER DEFAULT 0")
            logger.info("Added next_review_date and interval_days columns to ConceptLogs table.")
        except sqlite3.OperationalError:
            pass  # Columns already exist

        conn.commit()
    logger.info("Database initialized successfully.")


def login_and_update_streak(student_name, password=""):
    """Logs the student in and calculates their current streak.

    Uses name + password to uniquely identify a student, so two
    students with the same name but different passwords get separate
    accounts.
    """
    pw_hash = _hash_password(password)

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        today = date.today()
        today_str = today.isoformat()

        cursor.execute("SELECT student_id, password_hash FROM Students WHERE name = ?", (student_name,))
        existing_students = cursor.fetchall()

        if not existing_students:
            # --- NEW STUDENT ROUTINE ---
            cursor.execute(
                "INSERT INTO Students (name, password_hash, join_date) VALUES (?, ?, ?)",
                (student_name, pw_hash, today_str),
            )
            student_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO Streaks (student_id, last_active_date, current_streak, highest_streak) 
                VALUES (?, ?, 1, 1)
            ''', 
            (student_id, today_str))
            conn.commit()
            logger.info("New student registered: %s (id=%d)", student_name, student_id)
            return student_id, 1
        else:
            # Name exists, check password
            student_id = None
            for row in existing_students:
                if row[1] == pw_hash:
                    student_id = row[0]
                    break
                elif row[1] == '':
                    # Migrate password
                    cursor.execute("UPDATE Students SET password_hash = ? WHERE student_id = ?", (pw_hash, row[0]))
                    student_id = row[0]
                    break
            
            if student_id is None:
                raise ValueError("Invalid password or name already taken")

            # --- RETURNING STUDENT ROUTINE ---
            cursor.execute(
                "SELECT last_active_date, current_streak, highest_streak FROM Streaks WHERE student_id = ?",
                (student_id,)
            )
            streak_data = cursor.fetchone()

            if not streak_data:
                cursor.execute('''
                    INSERT INTO Streaks (student_id, last_active_date, current_streak, highest_streak) 
                    VALUES (?, ?, 1, 1)
                ''', (student_id, today_str))
                conn.commit()
                return student_id, 1

            last_active = date.fromisoformat(streak_data[0])
            current_streak = streak_data[1]
            highest_streak = streak_data[2]

            delta_days = (today - last_active).days

            if delta_days == 1:
                current_streak += 1
                highest_streak = max(current_streak, highest_streak)
            elif delta_days > 1:
                current_streak = 1

            cursor.execute('''
                UPDATE Streaks 
                SET last_active_date = ?, current_streak = ?, highest_streak = ?
                WHERE student_id = ?
            ''', (today_str, current_streak, highest_streak, student_id))

            conn.commit()
            logger.info("Returning student: %s (id=%d, streak=%d)", student_name, student_id, current_streak)
            return student_id, current_streak


def _calculate_next_interval(status, prev_interval=0):
    if status == "Struggling" or status == "Learning":
        return 1
    elif status == "Mastered":
        if prev_interval == 0: return 3
        elif prev_interval == 3: return 7
        elif prev_interval == 7: return 14
        else: return 30
    return 1

def _get_latest_interval(cursor, student_id, concept_name):
    cursor.execute('''
        SELECT interval_days FROM ConceptLogs 
        WHERE student_id = ? AND concept_name = ? 
        ORDER BY timestamp DESC LIMIT 1
    ''', (student_id, concept_name))
    row = cursor.fetchone()
    return row[0] if row and row[0] is not None else 0


def log_concept(student_id, concept_name, status):
    """Saves a record of the topic the student is learning."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()
        
        prev_interval = _get_latest_interval(cursor, student_id, concept_name)
        new_interval = _calculate_next_interval(status, prev_interval)
        next_review_date = (date.today() + timedelta(days=new_interval)).isoformat()

        cursor.execute('''
            INSERT INTO ConceptLogs (student_id, concept_name, status, timestamp, next_review_date, interval_days)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, concept_name, status, timestamp, next_review_date, new_interval))

        conn.commit()
    logger.info("Logged concept: student=%d, topic=%s, status=%s, next_review=%s", student_id, concept_name, status, next_review_date)


def log_quiz_result(student_id, topic, quiz_type, question, student_answer, correct_answer, is_correct):
    """Logs a quiz attempt and updates mastery status based on the result.

    Args:
        student_id: The student's database ID.
        topic: The topic being quizzed.
        quiz_type: Type of quiz (mcq, spot_the_mistake, fill_blank).
        question: The quiz question text.
        student_answer: What the student chose.
        correct_answer: The correct answer.
        is_correct: Boolean — True if student got it right.
    """
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        # Log the quiz attempt
        cursor.execute('''
            INSERT INTO QuizLogs (student_id, topic, quiz_type, question, student_answer, correct_answer, is_correct, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (student_id, topic, quiz_type, question, student_answer, correct_answer, int(is_correct), timestamp))

        # Update mastery in ConceptLogs based on quiz result
        new_status = "Mastered" if is_correct else "Struggling"
        
        prev_interval = _get_latest_interval(cursor, student_id, topic)
        new_interval = _calculate_next_interval(new_status, prev_interval)
        next_review_date = (date.today() + timedelta(days=new_interval)).isoformat()
        
        cursor.execute('''
            INSERT INTO ConceptLogs (student_id, concept_name, status, timestamp, next_review_date, interval_days)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (student_id, topic, new_status, timestamp, next_review_date, new_interval))

        conn.commit()
    logger.info("Quiz logged: student=%d, topic=%s, correct=%s", student_id, topic, is_correct)


def get_student_progress(student_id):
    """Returns mastered/learning/struggling counts for a student."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT status, COUNT(*) as count
            FROM ConceptLogs
            WHERE student_id = ?
            GROUP BY status
        ''', (student_id,))
        rows = cursor.fetchall()
    return {row[0]: row[1] for row in rows}



def get_due_reviews(student_id):
    """Return concepts that are due for revision today or overdue."""
    today_str = date.today().isoformat()
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            WITH LatestLogs AS (
                SELECT concept_name, status, next_review_date,
                       ROW_NUMBER() OVER(PARTITION BY concept_name ORDER BY timestamp DESC) as rn
                FROM ConceptLogs
                WHERE student_id = ?
            )
            SELECT concept_name, next_review_date
            FROM LatestLogs
            WHERE rn = 1 AND (next_review_date IS NULL OR next_review_date <= ?)
        ''', (student_id, today_str))
        return cursor.fetchall()



def get_calendar_data(student_id):
    """Returns past daily activity and future revision dates for the calendar heatmap.
    
    Returns:
        past_data: dict mapping date_string -> {concept_name: final_status_for_day}
        future_data: dict mapping date_string -> [list of concepts due]
    """
    from collections import defaultdict
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        
        # 1. Past Data: Get the final status of each concept studied on each specific day
        cursor.execute('''
            SELECT date(timestamp) as log_date, concept_name, status
            FROM ConceptLogs
            WHERE student_id = ?
            ORDER BY timestamp ASC
        ''', (student_id,))
        
        daily_concepts = defaultdict(dict)
        for row in cursor.fetchall():
            d = row[0]
            c = row[1]
            s = row[2]
            daily_concepts[d][c] = s
            
        # 2. Future Data: Get all active future review dates
        # Use ROW_NUMBER to get the most recent log per concept
        cursor.execute('''
            SELECT concept_name, next_review_date
            FROM (
                SELECT concept_name, next_review_date,
                       ROW_NUMBER() OVER(PARTITION BY concept_name ORDER BY timestamp DESC) as rn
                FROM ConceptLogs
                WHERE student_id = ?
            ) WHERE rn = 1 AND next_review_date IS NOT NULL AND next_review_date > date('now')
        ''', (student_id,))
        
        future_reviews = defaultdict(list)
        for row in cursor.fetchall():
            concept = row[0]
            # Handle potential time parts in next_review_date if any
            rev_date = row[1][:10] 
            future_reviews[rev_date].append(concept)
            
        return dict(daily_concepts), dict(future_reviews)

