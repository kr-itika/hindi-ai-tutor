import google.generativeai as genai

# 🔑 Put your NEW API key here
genai.configure(api_key="YAIzaSyD-keQHD1YZYovw4ZpRVot7d6PRdjpkyDM")

def get_response(user_input):
    prompt = f"""
    Tum ek friendly Hindi tutor ho.

    Student ka question:
    {user_input}

    Simple Hindi mein samjhao.
    Gaon example use karo.
    End mein ek chhota sa question pucho.
    """

    model = genai.GenerativeModel("gemini-1.5-flash")

    response = model.generate_content(prompt)

    return response.text