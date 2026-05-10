# 🌾 Hindi AI Tutor

An AI-powered Hindi tutor that explains concepts in simple Hindi using local LLMs via [Ollama](https://ollama.ai). Built with Streamlit for an interactive, chat-based learning experience.

## ✨ Features

- **Chat-based tutoring** — Ask questions in Hindi or English and get simple, village-style explanations
- **Voice input** — Click 🎤 and speak your question (uses browser's Speech API)
- **Streak tracking** — Daily login streaks with 🥉🥈🥇 badges
- **Progress tracking** — See what topics you've covered and your mastery level
- **Teacher dashboard** — A separate panel for teachers to monitor student progress
- **Concept logging** — Every topic is silently tracked with status (Struggling / Learning / Mastered)
- **Custom dark theme** — India-inspired saffron & dark palette

## 🛠️ Tech Stack

| Component | Technology |
|-----------|-----------|
| Frontend | Streamlit |
| LLM Backend | Ollama (gemma4:e4b) |
| Database | SQLite |
| Auth | SHA-256 hashed passwords |
| Voice | Web Speech API (browser-native) |

## 📁 Project Structure

```
hindi-ai-tutor/
├── app.py                  # Main student-facing tutor app
├── gemini_api.py           # Ollama LLM integration
├── db_manager.py           # SQLite database manager
├── requirements.txt        # Python dependencies
├── run.sh                  # Linux/Mac launcher
├── run.bat                 # Windows launcher
├── students.db             # SQLite database (auto-created)
├── .streamlit/
│   └── config.toml         # Custom Streamlit theme
├── pages/
│   └── teacher_dashboard.py  # Teacher analytics panel
├── Database_schema.md      # Schema documentation
└── README.md               # This file
```

## 🚀 Setup & Run

### Prerequisites

1. **Python 3.8+**
2. **Ollama** — Install from [ollama.ai](https://ollama.ai)

### Installation

```bash
# Clone the repo
git clone https://github.com/KhushiJ08/hindi-ai-tutor.git
cd hindi-ai-tutor

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Pull the LLM model
ollama pull gemma4:e4b
```

### Running

```bash
# Linux/Mac
./run.sh

# Windows
run.bat
```

Or manually:

```bash
ollama serve &
streamlit run app.py
```

### Teacher Dashboard

Navigate to the **Teacher Dashboard** page in the sidebar. Set the password via environment variable:

```bash
# Linux/Mac
export TEACHER_PASSWORD="your_secure_password"

# Windows
set TEACHER_PASSWORD=your_secure_password
```

Or add it to `.streamlit/secrets.toml` (gitignored):
```toml
teacher_password = "your_secure_password"
```

Fallback default: `teacher123`

## 📊 Database

The app uses SQLite (`students.db`) with three tables:

- **Students** — Name, hashed password, join date
- **Streaks** — Daily activity tracking with current & highest streak
- **ConceptLogs** — Every topic discussed, tagged as Struggling/Learning/Mastered

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
