import streamlit as st
from gemini_api import get_response

st.title("🌾 Hindi AI Tutor")

user_input = st.text_input("Apna doubt pucho...")

if user_input:
    st.write("👨‍🎓 Tum:", user_input)

    response = get_response(user_input)

    st.write("🤖 Tutor:", response)