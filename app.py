import streamlit as st
import base64
from PIL import Image
from gemini_api import get_response
from db_manager import login_and_update_streak, log_concept, get_student_progress, log_quiz_result

# --- Constants ---
MAX_IMAGES = 5
MAX_FILE_SIZE_MB = 10
ALLOWED_TYPES = ["png", "jpg", "jpeg", "webp"]

def render_tts_button(text):
    """Renders a small play button that uses the browser's TTS engine to read Hindi text."""
    # Escape quotes and newlines so they don't break the JS string
    safe_text = text.replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    html = f"""
    <div style="margin-top: 5px;">
        <button onclick="speakText()" style="
            background-color: #f0f2f6; border: 1px solid #ccc; border-radius: 15px;
            padding: 4px 12px; cursor: pointer; font-size: 14px; color: #333;
            display: inline-flex; align-items: center; gap: 6px; transition: background 0.2s;
        " onmouseover="this.style.background='#e0e2e6'" onmouseout="this.style.background='#f0f2f6'">
            🔊 Suno
        </button>
    </div>
    <script>
    function speakText() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop current speech if any
            const utterance = new SpeechSynthesisUtterance('{safe_text}');
            utterance.lang = 'hi-IN';
            window.speechSynthesis.speak(utterance);
        }} else {{
            alert("Sorry, aapka browser Text-to-Speech support nahi karta.");
        }}
    }}
    </script>
    """
    st.components.v1.html(html, height=45)



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
            st.error("⚠️ Naam toh daalo! (Please enter your name)")
            st.stop()

        elif not clean_password: 
            st.error("⚠️ Password khali nahi chhod sakte! (Please enter your password)")
            st.stop()
            
        elif clean_password != password_input:
            st.error("⚠️ Password ke end or start m space nahi ho sakta! (Password can't contain space in end or start)")
            st.stop()
            
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
            # Show images if this message had them
            if msg.get("images"):
                img_cols = st.columns(min(len(msg["images"]), 4))
                for idx, img_b64 in enumerate(msg["images"]):
                    with img_cols[idx % 4]:
                        st.image(
                            base64.b64decode(img_b64),
                            use_container_width=True,
                        )
            st.markdown(msg["content"])
            # Add play button to past assistant messages
            if msg["role"] == "assistant":
                render_tts_button(msg["content"])

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

    # --- 📷 Image Upload Section ---
    with st.expander("📷 Photo Attach Karo (Textbook, Handwriting, Diagram...)", expanded=False):
        st.caption("📸 Photo upload karo — textbook page, handwritten doubt, diagram, blackboard kuch bhi!")

        uploaded_files = st.file_uploader(
            "Choose images",
            type=ALLOWED_TYPES,
            accept_multiple_files=True,
            key="image_uploader",
            label_visibility="collapsed",
        )

        # Validate and show previews
        if uploaded_files:
            # Check max image count
            if len(uploaded_files) > MAX_IMAGES:
                st.warning(f"⚠️ Maximum {MAX_IMAGES} images allowed! Sirf pehli {MAX_IMAGES} use hongi.")
                uploaded_files = uploaded_files[:MAX_IMAGES]

            valid_files = []
            for f in uploaded_files:
                file_size_mb = f.size / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    st.error(f"❌ '{f.name}' bahut badi hai ({file_size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed.")
                else:
                    valid_files.append(f)

            if valid_files:
                st.markdown(f"**{len(valid_files)} photo(s) ready** ✅")

                # Show preview thumbnails
                preview_cols = st.columns(min(len(valid_files), 4))
                for idx, f in enumerate(valid_files):
                    with preview_cols[idx % 4]:
                        img = Image.open(f)
                        # Create thumbnail for preview
                        img.thumbnail((300, 300))
                        st.image(img, caption=f.name, use_container_width=True)
                        f.seek(0)  # Reset pointer after PIL reads it

                # Store valid files for sending
                st.session_state["pending_images"] = valid_files
            else:
                st.session_state.pop("pending_images", None)
        else:
            st.session_state.pop("pending_images", None)

    # Chat input
    user_input = st.chat_input("Apna doubt pucho... (photo ke saath ya bina)")

    if user_input or st.session_state.get("pending_images"):
        # Need at least text or images to proceed
        clean_input = user_input.strip() if user_input else ""

        if not clean_input and not st.session_state.get("pending_images"):
            st.toast("⚠️ Kuch toh likho ya photo upload karo!")
        else:
            # --- Process images ---
            image_b64_list = []
            pending = st.session_state.get("pending_images", [])

            for f in pending:
                f.seek(0)  # Reset file pointer
                image_bytes = f.read()
                b64_str = base64.b64encode(image_bytes).decode("utf-8")
                image_b64_list.append(b64_str)

            # Build display text
            display_text = clean_input if clean_input else "📷 (Photo sent for analysis)"

            # 1. Build the user message (append AFTER API call to avoid duplication)
            user_msg = {"role": "user", "content": display_text, "avatar": "👨‍🎓"}
            if image_b64_list:
                user_msg["images"] = image_b64_list

            with st.chat_message("user", avatar="👨‍🎓"):
                # Show uploaded images in the chat bubble
                if image_b64_list:
                    img_cols = st.columns(min(len(image_b64_list), 4))
                    for idx, img_b64 in enumerate(image_b64_list):
                        with img_cols[idx % 4]:
                            st.image(
                                base64.b64decode(img_b64),
                                use_container_width=True,
                            )
                st.markdown(display_text)

            # 2. Get AI response (with images if present)
            with st.chat_message("assistant", avatar="🤖"):
                spinner_text = "Tutor photo dekh raha hai... 🔍" if image_b64_list else "Tutor soch raha hai..."
                with st.spinner(spinner_text):
                    response_data = get_response(
                        clean_input,
                        chat_history=st.session_state.get("messages", []),
                        images=image_b64_list if image_b64_list else None,
                    )

                action = response_data.get("action", "explain")
                tutor_reply = response_data.get("tutor_response", "⚠️ Koi response nahi mila.")
                quiz_data = response_data.get("quiz_data")
                next_suggestion = response_data.get("next_action_suggestion")

                # --- Action Badge ---
                action_labels = {
                    "explain": "💡 Samjhao",
                    "quiz": "❓ Quiz Time",
                    "revise": "🔄 Revision",
                    "game": "🎮 Fun Game",
                    "clarify": "🤔 Clarification",
                }
                badge = action_labels.get(action, "💬 Response")
                st.caption(badge)

                # --- Tutor Response (always shown) ---
                st.markdown(tutor_reply)
                render_tts_button(tutor_reply)

                # --- Action-Specific UI ---
                if action == "explain":
                    st.info("💡 **Samajh aa gaya?** Agar haan toh aage badhte hain, warna phir se puchho!")

                elif action == "revise":
                    st.warning("🔄 **Ye topic phir se practice karo!** Revision se hi mastery aati hai.")

                elif action == "clarify":
                    st.info("❓ **Apna question thoda aur clearly batao** taaki main better help kar sakun.")

                elif action in ("quiz", "game"):
                    # --- Interactive Quiz/Game UI ---
                    if quiz_data and isinstance(quiz_data, dict):
                        question = quiz_data.get("question", "")
                        options = quiz_data.get("options", [])
                        correct = quiz_data.get("correct_answer", "")
                        explanation = quiz_data.get("explanation", "")
                        quiz_type = quiz_data.get("quiz_type", "mcq")

                        if question and options:
                            st.divider()

                            # Quiz type badge
                            type_labels = {
                                "mcq": "📝 Multiple Choice",
                                "spot_the_mistake": "🔍 Galat Kya Hai?",
                                "fill_blank": "✏️ Fill in the Blank",
                            }
                            emoji = "🎮" if action == "game" else type_labels.get(quiz_type, "📝 Quiz")
                            st.markdown(f"### {emoji}")
                            st.markdown(f"**{question}**")

                            # Use a unique key for each quiz based on message count
                            quiz_key = f"quiz_{len(st.session_state.get('messages', []))}"

                            selected = st.radio(
                                "Apna jawab chuno:",
                                options,
                                key=quiz_key,
                                index=None,
                            )

                            # Submit button instead of instant check
                            if st.button("✅ Jawab Submit Karo", key=f"submit_{quiz_key}", type="primary"):
                                if not selected:
                                    st.warning("⚠️ Pehle ek option chuno!")
                                else:
                                    is_correct = (selected == correct)

                                    if is_correct:
                                        st.success("🎉 **Bilkul sahi! Bahut badhiya!**")
                                        st.balloons()
                                    else:
                                        st.error(f"❌ **Galat!** Sahi jawab tha: **{correct}**")
                                        st.caption("Koi baat nahi — galtiyon se hi seekhte hain! 💪")

                                    # Show explanation
                                    if explanation:
                                        st.info(f"📖 **Samjho:** {explanation}")

                                    # Log quiz result to database
                                    topic = response_data.get("topic", "Unknown")
                                    log_quiz_result(
                                        student_id=st.session_state["student_id"],
                                        topic=topic,
                                        quiz_type=quiz_type,
                                        question=question,
                                        student_answer=selected,
                                        correct_answer=correct,
                                        is_correct=is_correct,
                                    )
                                    mastery = "Mastered ✅" if is_correct else "Struggling 📚"
                                    st.toast(f"📊 Quiz Result: {topic} → {mastery}")

            # Add user message to history AFTER API call (prevents sending it twice)
            st.session_state["messages"].append(user_msg)

            # Build assistant message for chat history
            assistant_content = tutor_reply
            if action in ("quiz", "game") and quiz_data:
                q = quiz_data.get("question", "")
                if q:
                    assistant_content += f"\n\n📝 Quiz: {q}"

            st.session_state["messages"].append({"role": "assistant", "content": assistant_content, "avatar": "🤖"})

            # 3. Silently log the weak topic in the background for the Teacher Panel
            # Skip if action is quiz/game — log_quiz_result() already logs to ConceptLogs
            topic = response_data.get("topic", "Unknown")
            status = response_data.get("status", "Unknown")

            if topic != "Error" and action not in ("quiz", "game"):
                log_concept(
                    student_id=st.session_state["student_id"],
                    concept_name=topic,
                    status=status,
                )
                # A tiny pop-up to show the system is tracking data
                st.toast(f"🧠 Tracked: {topic} ({status})")

            # Show next action suggestion hint
            if next_suggestion:
                suggestion_labels = {
                    "explain": "💡 Aage explanation milega",
                    "quiz": "❓ Aage quiz aayega",
                    "revise": "🔄 Revision hogi",
                    "game": "🎮 Aage game hoga",
                    "clarify": "🤔 Thoda aur batao",
                }
                hint = suggestion_labels.get(next_suggestion, "")
                if hint:
                    st.toast(hint)

            # 4. Clear pending images after sending
            st.session_state.pop("pending_images", None)
