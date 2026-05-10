import sqlite3
import hashlib
import logging
import os
from datetime import date, datetime

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
                FOREIGN KEY (student_id) REFERENCES Students(student_id)
            )
        ''')

        # Add password_hash column if upgrading from old schema
        try:
            cursor.execute("ALTER TABLE Students ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
            logger.info("Added password_hash column to Students table.")
        except sqlite3.OperationalError:
            pass  # Column already exists

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

        cursor.execute(
            "SELECT student_id FROM Students WHERE name = ? AND password_hash = ?",
            (student_name, pw_hash),
        )
        student_row = cursor.fetchone()

        if not student_row:
            # --- NEW STUDENT ROUTINE ---
            cursor.execute(
                "INSERT INTO Students (name, password_hash, join_date) VALUES (?, ?, ?)",
                (student_name, pw_hash, today_str),
            )
            student_id = cursor.lastrowid

            cursor.execute('''
                INSERT INTO Streaks (student_id, last_active_date, current_streak, highest_streak) 
                VALUES (?, ?, 1, 1)
            ''', (student_id, today_str))
            conn.commit()
            logger.info("New student registered: %s (id=%d)", student_name, student_id)
            return student_id, 1

        else:
            # --- RETURNING STUDENT ROUTINE ---
            student_id = student_row[0]
            cursor.execute(
                "SELECT last_active_date, current_streak, highest_streak FROM Streaks WHERE student_id = ?",
                (student_id,),
            )
            streak_data = cursor.fetchone()

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


def log_concept(student_id, concept_name, status):
    """Saves a record of the topic the student is learning."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        timestamp = datetime.now().isoformat()

        cursor.execute('''
            INSERT INTO ConceptLogs (student_id, concept_name, status, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (student_id, concept_name, status, timestamp))

        conn.commit()
    logger.info("Logged concept: student=%d, topic=%s, status=%s", student_id, concept_name, status)


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


def get_teacher_dashboard_data():
    """Returns all concept logs joined with student names for the teacher panel."""
    import pandas as pd

    with sqlite3.connect(DB_NAME) as conn:
        query = '''
            SELECT Students.name, ConceptLogs.concept_name, ConceptLogs.status, ConceptLogs.timestamp 
            FROM ConceptLogs
            JOIN Students ON ConceptLogs.student_id = Students.student_id
            ORDER BY ConceptLogs.timestamp DESC
        '''
        df = pd.read_sql_query(query, conn)
    return df


def get_all_students():
    """Returns a list of all students with their streak info."""
    import pandas as pd

    with sqlite3.connect(DB_NAME) as conn:
        query = '''
            SELECT Students.name, Students.join_date,
                   Streaks.current_streak, Streaks.highest_streak
            FROM Students
            JOIN Streaks ON Students.student_id = Streaks.student_id
            ORDER BY Students.name
        '''
        df = pd.read_sql_query(query, conn)
    return df


# Always ensure tables exist when this module is imported
init_db()