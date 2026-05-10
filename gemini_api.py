import requests
import json

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "gemma4:e4b"

SYSTEM_PROMPT = """Tum ek friendly Hindi tutor ho jo students ko simple Hindi mein padhata hai.

Rules:
- Student ke question ka seedha jawab do. Topic se mat bhatko.
- Simple Hindi mein samjhao with relatable examples.
- Agar student ne pehle kuch pucha hai, toh uska context yaad rakho.
- End mein ek chhota sa follow-up question pucho taaki student engage rahe.

IMPORTANT: You must respond ONLY with a valid JSON object. No markdown, no code fences.
{
    "tutor_response": "Your Hindi response here",
    "topic": "The core concept in 1-2 words (e.g., Fractions, Photosynthesis)",
    "status": "Choose one: Struggling, Learning, or Mastered"
}"""


def get_response(user_input, chat_history=None):
    """Get a response from the AI tutor with conversation history for context."""

    # Build the full prompt with conversation history
    prompt_parts = [SYSTEM_PROMPT, ""]

    # Include previous conversation turns so the model has context
    if chat_history:
        prompt_parts.append("=== Pichli Baatcheet (Previous Conversation) ===")
        for msg in chat_history:
            if msg["role"] == "user":
                prompt_parts.append(f"Student: {msg['content']}")
            elif msg["role"] == "assistant":
                prompt_parts.append(f"Tutor: {msg['content']}")
        prompt_parts.append("=== End of Previous Conversation ===")
        prompt_parts.append("")

    prompt_parts.append(f"Student ka naya question: {user_input}")
    prompt_parts.append("JSON mein jawab do:")

    prompt = "\n".join(prompt_parts)

    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False,
        "format": "json"  # This Ollama flag forces JSON output
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()

        # Parse the JSON string returned by Ollama into a Python dictionary
        raw_output = response.json()["response"]

        # Clean up markdown formatting if the model wraps JSON in code fences
        raw_output = raw_output.strip()
        if raw_output.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            raw_output = raw_output.split("\n", 1)[-1]  # Remove first line (```json)
            if raw_output.endswith("```"):
                raw_output = raw_output[:-3]
            raw_output = raw_output.strip()

        parsed_data = json.loads(raw_output)

        return parsed_data

    except requests.exceptions.ConnectionError:
        return {"tutor_response": "⚠️ Ollama server se connect nahi ho paa raha.", "topic": "Error", "status": "Error"}
    except requests.exceptions.Timeout:
        return {"tutor_response": "⚠️ Server ne bahut der laga di. Phir se try karo.", "topic": "Error", "status": "Error"}
    except json.JSONDecodeError:
        return {"tutor_response": "⚠️ Model ne galat format diya. Phir se try karo.", "topic": "Error", "status": "Error"}
    except Exception as e:
        return {"tutor_response": f"⚠️ Kuch gadbad ho gayi: {e}", "topic": "Error", "status": "Error"}