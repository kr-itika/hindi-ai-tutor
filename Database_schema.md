## Backend & Database Documentation (Part D)

This section covers the local SQLite database (`students.db`) and the structured LLM extraction engine. 

### 1. Database Schema
The app uses a local SQLite database to track student progress and streaks without requiring cloud storage. It consists of three tables:
* **`Students`**: Stores `student_id`, `name`, `password_hash`, and `join_date`.
* **`Streaks`**: Tracks the `last_active_date` and calculates the `current_streak`.
* **`ConceptLogs`**: The core memory engine. It logs every topic the student learns and their mastery status.

### 2. Available Backend Functions
The `db_manager.py` file exposes the following functions:

* `login_and_update_streak(student_name, password)`: Returns the `student_id` and their updated `current_streak`. Uses name + password to uniquely identify students.
* `log_concept(student_id, concept_name, status)`: Silently writes a new topic (e.g., "Fractions", "Struggling") to the database.
* `get_student_progress(student_id)`: Returns a dictionary of status counts (Mastered/Learning/Struggling) for progress charts.
* `get_teacher_dashboard_data()`: Returns a Pandas DataFrame of all concept logs joined with student names.
* `get_all_students()`: Returns a Pandas DataFrame of all registered students with streak info.

### 3. Teacher Dashboard
The Teacher Dashboard is available as a separate page at `pages/teacher_dashboard.py`. It uses Streamlit's multi-page app feature and is password-protected (default: `teacher123`).

It provides:
* A table of all student activity
* A list of all registered students
* Topic-wise status breakdown with charts
* Top struggling topics analysis