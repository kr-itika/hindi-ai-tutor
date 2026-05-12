# 🌾 Prajna — Hindi AI Tutor

An AI-powered Hindi tutor that explains concepts in simple Hindi using local LLMs via [Ollama](https://ollama.ai). Built with a Flask backend and a modern vanilla HTML/CSS/JS frontend for an interactive, chat-based learning experience.

## ✨ Features

- **Chat-based tutoring** — Ask questions in Hindi or English and get simple, village-style explanations
- **Dual response modes** — ⚡ Fast (2-4 sentence answers) and 🧠 Deep (detailed step-by-step explanations)
- **Multi-language support** — Switch between Hindi and English with a single click
- **Image analysis** — Upload textbook pages, handwritten doubts, or diagrams for AI explanation
- **Quizzes & games** — Interactive MCQs, spot-the-mistake, and fill-in-the-blank challenges
- **Spaced repetition** — Smart review scheduling based on mastery level
- **Learning calendar** — Visual heatmap showing past study activity and upcoming reviews
- **Streak tracking** — Daily login streaks with 🥉🥈🥇 badges
- **Progress tracking** — See what topics you've covered and your mastery level
- **Concept logging** — Every topic is silently tracked with status (Struggling / Learning / Mastered)
- **Text-to-speech** — Listen to responses using the browser's Speech API
- **Custom dark theme** — India-inspired saffron & dark palette

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend  | HTML5 + CSS3 + Vanilla JS |
| Backend   | Flask (Python) |
| LLM       | Ollama (gemma4:e4b) |
| Database  | SQLite |
| Auth      | SHA-256 hashed passwords |
| TTS       | Web Speech API (browser-native) |

## 📁 Project Structure

```
prajna/
├── server.py                   # Flask entry point
├── requirements.txt            # Python dependencies
├── run.bat                     # Windows launcher
├── run.sh                      # Linux/Mac launcher
│
├── frontend/                   # Static frontend assets
│   ├── index.html              # Main chat interface
│   ├── login.html              # Auth page (sign in / sign up)
│   ├── css/
│   │   └── style.css           # Full design system & styles
│   └── js/
│       └── app.js              # Client-side application logic
│
├── backend/                    # Python backend package
│   ├── __init__.py
│   ├── gemini_api.py           # Ollama LLM integration & prompts
│   └── db_manager.py           # SQLite database manager
│
├── docs/                       # Documentation
│   └── database_schema.md      # DB schema reference
│
├── students.db                 # SQLite database (auto-created)
└── README.md
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
# Windows
run.bat

# Linux/Mac
./run.sh
```

Or manually:

```bash
ollama serve &
python server.py
```

Then open **http://localhost:8080/login.html** in your browser.

## 📊 Database

The app uses SQLite (`students.db`) with four tables:

- **Students** — Name, hashed password, join date
- **Streaks** — Daily activity tracking with current & highest streak
- **ConceptLogs** — Every topic discussed, tagged as Struggling/Learning/Mastered, with spaced repetition scheduling
- **QuizLogs** — Quiz attempts with questions, answers, and correctness

See [docs/database_schema.md](docs/database_schema.md) for full schema details.

## 🤝 Contributing

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is open source and available under the [MIT License](LICENSE).
