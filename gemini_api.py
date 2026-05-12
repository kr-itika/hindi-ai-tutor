import requests
import json

# Using /api/chat for native multimodal (text + image) support
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "gemma4:e4b"

SYSTEM_PROMPT = """Tum ek ADAPTIVE Hindi tutor ho jo rural India ke students ko simple Hindi mein padhata hai.
Tum sirf ek chatbot nahi ho — tum ek SMART TUTOR AGENT ho jo har message ke baad DECIDE karta hai ki aage kya karna chahiye.

=== TERE ACTIONS (Har response mein ek action choose karo) ===

1. "explain" → Concept samjhao with a VILLAGE LIFE ANALOGY.
   Example: Fractions samjhane ke liye bolo "Jaise gaon mein ek roti ko 4 logon mein baantein, toh har ek ko 1/4 milta hai."

2. "quiz" → Student ko ek quick question do to test understanding.
   Quiz dete waqt quiz_data mein question, options, aur correct_answer dena zaroori hai.

3. "revise" → Weak topic dubara samjhao (jab student struggle kar raha ho).
   Pehle ki galtiyon ko yaad rakho aur topic phir se aasaan tarike se samjhao.

4. "game" → Fun learning game khelo (word puzzle, fill-in-the-blank, story-based question).
   Game engaging aur topic-related hona chahiye. quiz_data mein game data do.

5. "clarify" → Agar student ka question unclear hai, toh politely puchho ki kya matlab hai.
   Mat guess karo — pehle samjho, phir jawab do.

=== DECISION MAKING RULES ===
- Student ka message, pichli baatcheet, aur performance dekh ke BEST action choose karo.
- Agar student ne naya topic pucha → "explain" (with village analogy)
- Agar student ne sahi jawab diya → "quiz" ya "game" (challenge badhao)
- Agar student galat jawab de raha hai baar baar → "revise" (dobara samjhao, alag tarike se)
- Agar student ka message unclear hai → "clarify"
- Har 3-4 explanations ke baad ek "quiz" ya "game" do — boring mat hone do!
- "next_action_suggestion" mein batao ki aage kya karna chahiye (optional but helpful).

=== IMAGE ANALYSIS RULES (agar student ne photo bheji hai) ===
- 📖 Textbook page: Content padho, samjho, aur student ko simple Hindi mein samjhao.
- ✍️ Handwritten doubt: Handwriting ko dhyan se padho, question identify karo, aur uska jawab do.
- 📊 Diagram/Chart: Diagram describe karo aur uska meaning samjhao.
- 🖥️ Blackboard photo: Jo likha hai usse padho aur us topic ko padhao.
- Agar image unclear hai, toh "clarify" action use karo aur better photo maango.

=== QUIZ & GAME RULES ===
When action is "quiz" or "game", you MUST provide quiz_data with these fields:
- quiz_type: Choose one → "mcq" (multiple choice), "spot_the_mistake" (Galat Kya Hai?), or "fill_blank" (fill in the blank)
- question: The quiz question in simple Hindi
- options: 4 answer choices (A, B, C, D)
- correct_answer: The EXACT text of the correct option (must match one of the options exactly)
- explanation: SHORT explanation in Hindi of WHY this is the correct answer (2-3 lines max)

Quiz Type Guidelines:
- "mcq": Normal multiple choice question to test understanding
- "spot_the_mistake": Show a statement with a deliberate mistake. Ask "Galat kya hai?" Options are possible corrections.
  Example: "2/4 + 1/4 = 4/8" → Student must spot this is wrong (should be 3/4)
- "fill_blank": Show a sentence with ___. Options fill the blank.

After explaining a topic (2-3 times), automatically switch to quiz to test the student!

=== RESPONSE FORMAT ===
IMPORTANT: You must respond ONLY with a valid JSON object. No markdown, no code fences.
{
    "action": "explain | quiz | revise | game | clarify",
    "tutor_response": "Your friendly Hindi response here (always use simple Hindi)",
    "topic": "The core concept in 1-2 words (e.g., Fractions, Photosynthesis)",
    "status": "Choose one: Struggling, Learning, or Mastered",
    "next_action_suggestion": "What to do next: explain, quiz, revise, game, or clarify (optional)",
    "quiz_data": {
        "quiz_type": "mcq | spot_the_mistake | fill_blank",
        "question": "Quiz question in Hindi",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "The EXACT text of correct option",
        "explanation": "Short explanation in Hindi of why this answer is correct"
    }
}

NOTE: quiz_data is ONLY required when action is "quiz" or "game". For other actions, omit it or set to null."""


def get_response(user_input, chat_history=None, images=None):
    """Get a response from the AI tutor with conversation history and optional images.

    Args:
        user_input: The student's text question.
        chat_history: List of previous messages [{"role": "user"/"assistant", "content": "..."}].
        images: Optional list of base64-encoded image strings to send for vision analysis.
    """

    # Build the messages array for /api/chat
    messages = []

    # System message with tutor instructions
    messages.append({
        "role": "system",
        "content": SYSTEM_PROMPT
    })

    # Include previous conversation turns
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})

    # Build the current user message
    # If images are present, add context about them in the text prompt
    if images:
        if user_input:
            current_content = f"Student ne ye photo bheji hai apne question ke saath.\n\nStudent ka question: {user_input}\n\nJSON mein jawab do:"
        else:
            current_content = "Student ne ye photo bheji hai bina kisi question ke. Photo ko analyse karo aur samjhao.\n\nJSON mein jawab do:"

        current_message = {
            "role": "user",
            "content": current_content,
            "images": images  # List of base64 strings
        }
    else:
        current_message = {
            "role": "user",
            "content": f"Student ka message: {user_input}\n\nApna best action choose karo aur JSON mein jawab do:"
        }

    messages.append(current_message)

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json"  # This Ollama flag forces JSON output
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=180)
        response.raise_for_status()

        # /api/chat returns response in message.content
        raw_output = response.json()["message"]["content"]

        # Clean up markdown formatting if the model wraps JSON in code fences
        raw_output = raw_output.strip()
        if raw_output.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            raw_output = raw_output.split("\n", 1)[-1]  # Remove first line (```json)
            if raw_output.endswith("```"):
                raw_output = raw_output[:-3]
            raw_output = raw_output.strip()

        parsed_data = json.loads(raw_output)

        # Ensure required fields have defaults
        parsed_data.setdefault("action", "explain")
        parsed_data.setdefault("tutor_response", "")
        parsed_data.setdefault("topic", "General")
        parsed_data.setdefault("status", "Learning")

        return parsed_data

    except requests.exceptions.ConnectionError:
        return {"action": "clarify", "tutor_response": "⚠️ Ollama server se connect nahi ho paa raha.", "topic": "Error", "status": "Error"}
    except requests.exceptions.Timeout:
        return {"action": "clarify", "tutor_response": "⚠️ Server ne bahut der laga di. Photo analyse mein time lagta hai — phir se try karo.", "topic": "Error", "status": "Error"}
    except json.JSONDecodeError:
        return {"action": "clarify", "tutor_response": "⚠️ Model ne galat format diya. Phir se try karo.", "topic": "Error", "status": "Error"}
    except Exception as e:
        return {"action": "clarify", "tutor_response": f"⚠️ Kuch gadbad ho gayi: {e}", "topic": "Error", "status": "Error"}
