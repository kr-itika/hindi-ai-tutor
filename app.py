import streamlit as st
from gemini_api import get_response
from db_manager import login_and_update_streak, log_concept, get_student_progress

st.set_page_config(
    page_title="Hindi AI Tutor 🌾",
    page_icon="🌾",
    layout="centered",
)

st.title("🌾 Hindi AI Tutor")

# --- LOGIN SYSTEM ---
# We check if the user is already stored in the session state.
if "student_id" not in st.session_state:
    st.subheader("Login / Sign Up")
    st.caption("Naye ho? Bas apna naam aur password daalo — account apne aap ban jayega!")

    name_input = st.text_input("Tumhara naam kya hai? (What is your name?)")
    password_input = st.text_input("Password", type="password")

    if st.button("Start Learning"):
        # Input validation — strip whitespace
        clean_name = name_input.strip() if name_input else ""
        clean_password = password_input.strip() if password_input else ""

        if not clean_name:
            st.warning("⚠️ Naam toh daalo! (Please enter your name)")
        elif not clean_password:
            st.warning("⚠️ Password bhi zaroori hai! (Password is required)")
        else:
            # Call our SQLite DB function to get ID and calculate streak
            s_id, streak = login_and_update_streak(clean_name, clean_password)

            # Save to Streamlit's permanent memory box
            st.session_state["student_id"] = s_id
            st.session_state["student_name"] = clean_name
            st.session_state["streak"] = streak
            st.session_state["messages"] = []  # Initialize chat history

            # Refresh the page to hide the login screen and show the tutor
            st.rerun()
else:
    # --- SIDEBAR: Gamification & Stats ---
    with st.sidebar:
        st.header(f"🙏 {st.session_state['student_name']}")

        streak = st.session_state["streak"]
        st.metric("🔥 Current Streak", f"{streak} Days")

        # Streak badges
        badges = []
        if streak >= 30:
            badges.append("🥇 30-Day Champion")
        if streak >= 7:
            badges.append("🥈 Week Warrior")
        if streak >= 3:
            badges.append("🥉 3-Day Starter")
        if badges:
            st.subheader("🏅 Badges")
            for badge in badges:
                st.write(badge)
        else:
            st.caption("🏅 Keep learning daily to earn badges!")

        # Progress chart
        progress = get_student_progress(st.session_state["student_id"])
        if progress:
            st.subheader("📊 My Progress")
            st.bar_chart(progress)

        st.divider()
        if st.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

    # --- MAIN TUTOR INTERFACE (Chat UI) ---
    st.success(f"Namaste, {st.session_state['student_name']}! 🙏 | 🔥 Streak: {st.session_state['streak']} Days")

    # Display chat history
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            st.markdown(msg["content"])

    # --- Voice Input (Browser Speech API) ---
    voice_component = """
    <div style="margin-bottom: 10px;">
        <button id="voiceBtn" onclick="startVoice()" style="
            background: linear-gradient(135deg, #FF9933, #FF6600);
            color: white; border: none; padding: 10px 20px;
            border-radius: 25px; cursor: pointer; font-size: 16px;
            box-shadow: 0 2px 8px rgba(255, 102, 0, 0.3);
            transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.05)'" 
           onmouseout="this.style.transform='scale(1)'">
            🎤 Bolo (Voice Input)
        </button>
        <span id="voiceStatus" style="margin-left: 10px; color: #888;"></span>
    </div>
    <script>
    function startVoice() {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {
            document.getElementById('voiceStatus').innerText = '❌ Browser mein voice support nahi hai';
            return;
        }
        const recognition = new SpeechRecognition();
        recognition.lang = 'hi-IN';
        recognition.interimResults = false;
        
        document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
        document.getElementById('voiceStatus').innerText = '🔴 Sun raha hoon...';
        
        recognition.onresult = function(event) {
            const text = event.results[0][0].transcript;
            // Find the Streamlit chat input and set its value
            const chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                nativeInputValueSetter.call(chatInput, text);
                chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                document.getElementById('voiceStatus').innerText = '✅ ' + text;
            }
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        };
        
        recognition.onerror = function(event) {
            document.getElementById('voiceStatus').innerText = '❌ Error: ' + event.error;
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        };
        
        recognition.onend = function() {
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        };
        
        recognition.start();
    }
    </script>
    """
    st.components.v1.html(voice_component, height=60)

    # Chat input
    user_input = st.chat_input("Apna doubt pucho...")

    if user_input:
        # Input validation
        clean_input = user_input.strip()
        if not clean_input:
            st.toast("⚠️ Kuch toh likho! (Please type something)")
        else:
            # 1. Show the student's question
            st.session_state["messages"].append({"role": "user", "content": clean_input, "avatar": "👨‍🎓"})
            with st.chat_message("user", avatar="👨‍🎓"):
                st.markdown(clean_input)

            # 2. Get AI response
            with st.chat_message("assistant", avatar="🤖"):
                with st.spinner("Tutor soch raha hai..."):
                    response_data = get_response(clean_input, chat_history=st.session_state.get("messages", []))

                tutor_reply = response_data.get("tutor_response", "⚠️ Koi response nahi mila.")
                st.markdown(tutor_reply)

            st.session_state["messages"].append({"role": "assistant", "content": tutor_reply, "avatar": "🤖"})

            # 3. Silently log the weak topic in the background for the Teacher Panel
            topic = response_data.get("topic", "Unknown")
            status = response_data.get("status", "Unknown")

            if topic != "Error":
                log_concept(
                    student_id=st.session_state["student_id"],
                    concept_name=topic,
                    status=status,
                )
                # A tiny pop-up to show the system is tracking data
                st.toast(f"🧠 Tracked: {topic} ({status})")