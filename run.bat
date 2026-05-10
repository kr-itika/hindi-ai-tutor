@echo off
echo ============================================
echo    Hindi AI Tutor - Starting Up...
echo ============================================

:: Activate virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo [1/4] Activating virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo [!] No virtual environment found. Using system Python.
)

:: Install dependencies if needed
echo [2/4] Checking dependencies...
pip install -r requirements.txt --quiet 2>NUL

:: Check if Ollama is running, start it if not
echo [3/4] Checking Ollama server...
tasklist /FI "IMAGENAME eq ollama.exe" 2>NUL | find /I "ollama.exe" >NUL
if %ERRORLEVEL% NEQ 0 (
    echo      Starting Ollama server...
    start /B ollama serve
    timeout /t 5 /nobreak >NUL
) else (
    echo      Ollama is already running.
)

:: Pull the model if not already downloaded
echo [4/4] Ensuring model is available...
ollama pull gemma4:e4b

:: Launch the app
echo ============================================
echo    Launching Hindi AI Tutor...
echo    Open http://localhost:8501 in your browser
echo ============================================
python -m streamlit run app.py

pause
