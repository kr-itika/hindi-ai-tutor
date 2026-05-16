import os
import json
import logging
import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
MODEL_NAME = "gemma4:e4b"

# ── Mode-specific generation options ──
MODE_OPTIONS = {
    "Fast Result": {
        "num_ctx": 1024,
        "num_predict": 256,
        "temperature": 0.8,
        "top_p": 0.85,
        "repeat_penalty": 1.1
    },
    "Long Think": {
        "num_ctx": 2048,
        "num_predict": 512,
        "temperature": 0.5,
        "top_p": 0.9,
        "repeat_penalty": 1.15
    }
}
MODE_TIMEOUT = {"Fast Result": 60, "Long Think": 300}


def generate_title(user_message, language="Hindi"):
    """Ask Ollama to generate a short descriptive title for a conversation.

    Uses a minimal context window and low token budget so it's near-instant.
    Falls back to a truncated version of the message if Ollama fails.
    """
    if language == "English":
        prompt = (
            f'Create a short, descriptive title (3 to 5 words) for a tutoring session '
            f'that begins with this student message: "{user_message}"\n'
            f'Reply ONLY with JSON: {{"title": "Your Title Here"}}'
        )
    else:
        prompt = (
            f'Is tutoring conversation ke liye ek chhota, spasht title banao (3 se 5 shabd) '
            f'jo is student ke message se shuru hoti hai: "{user_message}"\n'
            f'Sirf JSON mein jawab do: {{"title": "Aapka Title Yahan"}}'
        )

    payload = {
        "model": MODEL_NAME,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0.3,
            "num_ctx": 512,
            "num_predict": 64
        }
    }

    url = f"{OLLAMA_BASE_URL}/api/chat"
    try:
        resp = requests.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        raw_out = resp.json()["message"]["content"].strip()
        
        # Handle markdown fences around JSON
        if raw_out.startswith("```"):
            raw_out = raw_out.split("\n", 1)[-1]
            if raw_out.endswith("```"):
                raw_out = raw_out[:-3]
            raw_out = raw_out.strip()
            
        data = json.loads(raw_out)
        title = data.get("title", "").strip()
        return title[:80] if title else user_message[:60]
    except Exception as e:
        logger.warning("generate_title failed: %s", e)
        return user_message[:60]


def get_system_prompt(language="Hindi", mode="Fast Result"):
    
    think_rule = ""
    thought_process_json = ""
    length_rule = ""
    if mode == "Fast Result":
        length_rule = """- FAST MODE: Your tutor_response MUST be SHORT — maximum 2-4 sentences.
- Be DIRECT. Give the core answer immediately. No lengthy introductions.
- Skip detailed examples unless absolutely necessary. One brief analogy is enough.
- Do NOT write paragraphs. Keep it crisp and to the point.
"""
    elif mode == "Long Think":
        think_rule = "- LONG THINK MODE: You must think step-by-step in detail about the student's problem, misconceptions, and your strategy BEFORE writing the final response. Write your reasoning inside the 'thought_process' field.\n"
        thought_process_json = '    "thought_process": "Your detailed step-by-step reasoning here",\n'
        length_rule = """- DETAILED MODE: Give a THOROUGH, COMPREHENSIVE explanation.
- Use multiple examples and analogies from village life.
- Break down complex concepts step-by-step.
- Include "Why it matters" and "Common mistakes to avoid".
- Your response should be 8-15 sentences with rich detail.
"""

    if language == "English":
        return f"""You are an ADAPTIVE English tutor who teaches rural India's students in simple English.
You are not just a chatbot — you are a SMART TUTOR AGENT who DECIDEs what to do next after every message.

=== YOUR ACTIONS (Choose one action in every response) ===

1. "explain" → Explain the concept with a VILLAGE LIFE ANALOGY.
   Example: To explain Fractions say "Like sharing a roti among 4 people in the village, each gets 1/4."

2. "quiz" → Give the student a quick question to test understanding.
   When giving a quiz, you must provide question, options, and correct_answer in quiz_data.

3. "revise" → Re-explain a weak topic (when the student is struggling).
   Remember previous mistakes and explain the topic again in an easier way.

4. "game" → Play a fun learning game (word puzzle, fill-in-the-blank, story-based question).
   The game should be engaging and topic-related. Provide game data in quiz_data.

5. "clarify" → If the student's question is unclear, politely ask what they mean.
   Do not guess — understand first, then answer.

=== DECISION MAKING RULES ===
{length_rule}{think_rule}- Choose the BEST action based on the student's message, past conversation, and performance.
- If student asks a new topic → "explain" (with village analogy)
- If student answers correctly → "quiz" or "game" (increase challenge)
- If student answers wrong repeatedly → "revise" (explain again differently)
- If student's message is unclear → "clarify"
- After every 3-4 explanations, give a "quiz" or "game" — do not let it get boring!
- Tell what to do next in "next_action_suggestion" (optional but helpful).
- SPACED REPETITION: At the beginning of conversation, I will give you list of weak topics and due revisions. Prioritize 'revise' action on them before teaching new topics.

=== IMAGE ANALYSIS RULES (if student sent a photo) ===
- 📖 Textbook page: Read the content, understand it, and explain it to the student in simple English.
- ✍️ Handwritten doubt: Read the handwriting carefully, identify the question, and answer it.
- 📊 Diagram/Chart: Describe the diagram and explain its meaning.
- 🖥️ Blackboard photo: Read what is written and teach that topic.
- If the image is unclear, use the "clarify" action and ask for a better photo.

=== QUIZ & GAME RULES ===
When action is "quiz" or "game", you MUST provide quiz_data with these fields:
- quiz_type: Choose one → "mcq" (multiple choice), "spot_the_mistake" (What is wrong?), or "fill_blank" (fill in the blank)
- question: The quiz question in simple English
- options: 4 answer choices (A, B, C, D)
- correct_answer: The EXACT text of the correct option (must match one of the options exactly)
- explanation: SHORT explanation in English of WHY this is the correct answer (2-3 lines max)

Quiz Type Guidelines:
- "mcq": Normal multiple choice question to test understanding
- "spot_the_mistake": Show a statement with a deliberate mistake. Ask "What is wrong?" Options are possible corrections.
  Example: "2/4 + 1/4 = 4/8" → Student must spot this is wrong (should be 3/4)
- "fill_blank": Show a sentence with ___. Options fill the blank.

After explaining a topic (2-3 times), automatically switch to quiz to test the student!

=== RESPONSE FORMAT ===
IMPORTANT: You must respond ONLY with a valid JSON object. No markdown, no code fences.
NEVER use LaTeX math notation (no $, $$, \frac, \times, \rightarrow, etc). Instead use plain Unicode symbols like ×, ÷, →, ², ³, ½, π, etc. Write math in simple text like "F = m1 × m2 / r²" not "$F = \\frac{{m_1 \\times m_2}}{{r^2}}$".
{{
{thought_process_json}    "action": "explain | quiz | revise | game | clarify",
    "tutor_response": "Your friendly English response here (always use simple English)",
    "topic": "The core concept in 1-2 words (e.g., Fractions, Photosynthesis)",
    "status": "Choose one: Struggling, Learning, or Mastered",
    "next_action_suggestion": "What to do next: explain, quiz, revise, game, or clarify (optional)",
    "quiz_data": {{
        "quiz_type": "mcq | spot_the_mistake | fill_blank",
        "question": "Quiz question in English",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "The EXACT text of correct option",
        "explanation": "Short explanation in English of why this answer is correct"
    }}
}}

NOTE: quiz_data is ONLY required when action is "quiz" or "game". For other actions, omit it or set to null."""
    else:
        return f"""Tum ek ADAPTIVE Hindi tutor ho jo rural India ke students ko simple Hindi mein padhata hai.
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
{length_rule}{think_rule}- Student ka message, pichli baatcheet, aur performance dekh ke BEST action choose karo.
- Agar student ne naya topic pucha → "explain" (with village analogy)
- Agar student ne sahi jawab diya → "quiz" ya "game" (challenge badhao)
- Agar student galat jawab de raha hai baar baar → "revise" (dobara samjhao, alag tarike se)
- Agar student ka message unclear hai → "clarify"
- Har 3-4 explanations ke baad ek "quiz" ya "game" do — boring mat hone do!
- "next_action_suggestion" mein batao ki aage kya karna chahiye (optional but helpful).
- SPACED REPETITION: At the beginning of conversation, I will give you list of weak topics and due revisions. Prioritize 'revise' action on them before teaching new topics.

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
NEVER use LaTeX math notation (no $, $$, \frac, \times, \rightarrow, etc). Instead use plain Unicode symbols like ×, ÷, →, ², ³, ½, π, etc. Write math in simple text like "F = m1 × m2 / r²" not "$F = \\frac{{m_1 \\times m_2}}{{r^2}}$".
{{
{thought_process_json}    "action": "explain | quiz | revise | game | clarify",
    "tutor_response": "Your friendly Hindi response here (always use simple Hindi)",
    "topic": "The core concept in 1-2 words (e.g., Fractions, Photosynthesis)",
    "status": "Choose one: Struggling, Learning, or Mastered",
    "next_action_suggestion": "What to do next: explain, quiz, revise, game, or clarify (optional)",
    "quiz_data": {{
        "quiz_type": "mcq | spot_the_mistake | fill_blank",
        "question": "Quiz question in Hindi",
        "options": ["Option A", "Option B", "Option C", "Option D"],
        "correct_answer": "The EXACT text of correct option",
        "explanation": "Short explanation in Hindi of why this answer is correct"
    }}
}}

NOTE: quiz_data is ONLY required when action is "quiz" or "game". For other actions, omit it or set to null."""


def get_response(user_input, chat_history=None, images=None, weak_topics=None, language="Hindi", mode="Fast Result"):
    """Get a tutor response directly using the Ollama REST API.

    Args:
        user_input:   Student's text question.
        chat_history: List of prior messages [{role, content}].
        images:       Optional base64-encoded image strings (vision).
        weak_topics:  Optional string — spaced-repetition topics to prioritise.
        language:     "Hindi" or "English".
        mode:         "Fast Result" or "Long Think".
    """
    url = f"{OLLAMA_BASE_URL}/api/chat"
    
    opts = MODE_OPTIONS.get(mode, MODE_OPTIONS["Fast Result"])
    timeout = MODE_TIMEOUT.get(mode, 60)
    
    # ── Build message list ───────────────────────────────────────────────
    messages = [{"role": "system", "content": get_system_prompt(language, mode)}]

    if chat_history:
        for msg in chat_history[-20:]:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if content and role in ["user", "assistant"]:
                messages.append({"role": role, "content": content})

    # ── Spaced-repetition injection ──────────────────────────────────────
    weak_ctx = ""
    if weak_topics:
        weak_ctx = (
            f"\n\n[SYSTEM NOTE — SPACED REPETITION: Student is weak at: {weak_topics}. "
            "Prioritise revising these using action='revise'!]\n"
        )

    # ── Localised prompt strings ─────────────────────────────────────────
    if language == "English":
        prefix     = "Student's message: "
        json_req   = "Choose your best action and reply in JSON:"
        photo_with = "The student sent this photo with their question.\n\nStudent's question: "
        photo_only = "The student sent this photo without a question. Analyse it and explain."
    else:
        prefix     = "Student ka message: "
        json_req   = "Apna best action choose karo aur JSON mein jawab do:"
        photo_with = "Student ne ye photo bheji hai apne question ke saath.\n\nStudent ka question: "
        photo_only = "Student ne ye photo bheji hai bina kisi question ke. Photo ko analyse karo aur samjhao."

    # ── Current-turn message (multimodal if images present) ─────────────
    if images:
        text_part = (
            f"{photo_with}{user_input}{weak_ctx}\n\n{json_req}"
            if user_input else
            f"{photo_only}{weak_ctx}\n\n{json_req}"
        )
        # Ollama expects list of base64 strings in 'images' field for chat API
        messages.append({
            "role": "user",
            "content": text_part,
            "images": images
        })
    else:
        messages.append({
            "role": "user",
            "content": f"{prefix}{user_input}{weak_ctx}\n\n{json_req}"
        })

    # ── Invoke API ───────────────────────────────────────────────────────
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",
        "options": opts
    }
    
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        raw_out = resp.json()["message"]["content"].strip()
        
        # ── Robust Markdown Stripping ──
        if raw_out.startswith("```"):
            raw_out = raw_out.split("\n", 1)[-1]
            if raw_out.endswith("```"):
                raw_out = raw_out[:-3]
            raw_out = raw_out.strip()
            
        data = json.loads(raw_out)
        
        # Ensure critical keys exist
        data.setdefault("action", "explain")
        data.setdefault("tutor_response", "")
        data.setdefault("topic", "General")
        data.setdefault("status", "Learning")
        return data
        
    except requests.exceptions.ConnectionError:
        msg = ("⚠️ Unable to connect to Ollama server." if language == "English"
               else "⚠️ Ollama server se connect nahi ho paa raha.")
        return {"action": "clarify", "tutor_response": msg, "topic": "Error", "status": "Error"}
    except requests.exceptions.Timeout:
        msg = ("⚠️ Server took too long. Please try again." if language == "English"
               else "⚠️ Server ne bahut der laga di. Phir se try karo.")
        return {"action": "clarify", "tutor_response": msg, "topic": "Error", "status": "Error"}
    except json.JSONDecodeError as e:
        logger.error("JSON parse error from Ollama. Raw output: %s", raw_out)
        msg = ("⚠️ Model returned invalid format. Please try again." if language == "English"
               else "⚠️ Model ne galat format diya. Phir se try karo.")
        return {"action": "clarify", "tutor_response": msg, "topic": "Error", "status": "Error"}
    except Exception as e:
        logger.error("Error communicating with Ollama: %s", e)
        msg = (f"⚠️ Something went wrong: {e}" if language == "English"
               else f"⚠️ Kuch gadbad ho gayi: {e}")
        return {"action": "clarify", "tutor_response": msg, "topic": "Error", "status": "Error"}
