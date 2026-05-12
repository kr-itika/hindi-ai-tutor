import os
import requests
import json

# Using /api/chat for native multimodal (text + image) support
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")
MODEL_NAME = "gemma4:e4b"

# ── Mode-specific Ollama generation options ──
# Fast: tiny context, very few tokens → snappy 2-4 sentence replies
# Slow: large context, many tokens → detailed step-by-step explanations
MODE_OPTIONS = {
    "Fast Result": {
        "num_ctx": 1024,      # small context window
        "num_predict": 256,   # very short output
        "temperature": 0.8,   # slightly creative
        "top_p": 0.85,
        "repeat_penalty": 1.2,
    },
    "Long Think": {
        "num_ctx": 8192,      # large context for full history
        "num_predict": 4096,  # room for chain-of-thought + detailed answer
        "temperature": 0.5,   # more focused
        "top_p": 0.95,
        "repeat_penalty": 1.1,
    },
}
MODE_TIMEOUT = {
    "Fast Result": 60,   # seconds
    "Long Think": 300,
}

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
    """Get a response from the AI tutor with conversation history and optional images.

    Args:
        user_input: The student's text question.
        chat_history: List of previous messages [{"role": "user"/"assistant", "content": "..."}].
        images: Optional list of base64-encoded image strings to send for vision analysis.
        weak_topics: Optional string listing topics the student needs to revise today.
        language: The preferred language ("Hindi" or "English").
    """

    # Build the messages array for /api/chat
    messages = []

    # System message with tutor instructions
    messages.append({
        "role": "system",
        "content": get_system_prompt(language, mode)
    })

    # Include previous conversation turns
    if chat_history:
        for msg in chat_history:
            if msg["role"] == "user":
                messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                messages.append({"role": "assistant", "content": msg["content"]})

    # Build the current user message
    # Inject weak topics if they exist and this is likely the first or a general message
    weak_topic_context = ""
    if weak_topics:
        weak_topic_context = f"\n\n[SYSTEM NOTE - SPACED REPETITION: Student is weak at these topics: {weak_topics}. Please prioritize revising these topics by using action='revise'!]\n"

    # Set up localized strings based on language
    if language == "English":
        prefix_msg = "Student's message: "
        json_req = "Choose your best action and reply in JSON:"
        photo_with_q = "The student sent this photo along with their question.\n\nStudent's question: "
        photo_without_q = "The student sent this photo without a question. Analyze the photo and explain it."
    else:
        prefix_msg = "Student ka message: "
        json_req = "Apna best action choose karo aur JSON mein jawab do:"
        photo_with_q = "Student ne ye photo bheji hai apne question ke saath.\n\nStudent ka question: "
        photo_without_q = "Student ne ye photo bheji hai bina kisi question ke. Photo ko analyse karo aur samjhao."

    # If images are present, add context about them in the text prompt
    if images:
        if user_input:
            current_content = f"{photo_with_q}{user_input}{weak_topic_context}\n\n{json_req}"
        else:
            current_content = f"{photo_without_q}{weak_topic_context}\n\n{json_req}"

        current_message = {
            "role": "user",
            "content": current_content,
            "images": images  # List of base64 strings
        }
    else:
        current_message = {
            "role": "user",
            "content": f"{prefix_msg}{user_input}{weak_topic_context}\n\n{json_req}"
        }

    messages.append(current_message)

    # Select mode-appropriate generation options and timeout
    options = MODE_OPTIONS.get(mode, MODE_OPTIONS["Fast Result"])
    timeout = MODE_TIMEOUT.get(mode, 60)

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "format": "json",  # This Ollama flag forces JSON output
        "options": options,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
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
        error_msg = "⚠️ Unable to connect to Ollama server." if language == "English" else "⚠️ Ollama server se connect nahi ho paa raha."
        return {"action": "clarify", "tutor_response": error_msg, "topic": "Error", "status": "Error"}
    except requests.exceptions.Timeout:
        error_msg = "⚠️ Server took too long. Photo analysis takes time — please try again." if language == "English" else "⚠️ Server ne bahut der laga di. Photo analyse mein time lagta hai — phir se try karo."
        return {"action": "clarify", "tutor_response": error_msg, "topic": "Error", "status": "Error"}
    except json.JSONDecodeError:
        error_msg = "⚠️ Model returned invalid format. Please try again." if language == "English" else "⚠️ Model ne galat format diya. Phir se try karo."
        return {"action": "clarify", "tutor_response": error_msg, "topic": "Error", "status": "Error"}
    except Exception as e:
        error_msg = f"⚠️ Something went wrong: {e}" if language == "English" else f"⚠️ Kuch gadbad ho gayi: {e}"
        return {"action": "clarify", "tutor_response": error_msg, "topic": "Error", "status": "Error"}
