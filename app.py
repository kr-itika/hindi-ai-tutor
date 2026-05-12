import streamlit as st
import base64
import io
from PIL import Image
from gemini_api import get_response
from db_manager import login_and_update_streak, log_concept, get_student_progress, log_quiz_result, get_due_reviews

def t(en_text, hi_text):
    return en_text if st.session_state.get("language", "Hindi") == "English" else hi_text

# --- Constants ---
MAX_IMAGES = 5
MAX_FILE_SIZE_MB = 10
ALLOWED_TYPES = ["png", "jpg", "jpeg", "webp"]

def render_tts_button(text):
    """Renders a small play button that uses the browser's TTS engine to read text."""
    # Escape quotes and newlines so they don't break the JS string
    safe_text = text.replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    btn_text = t("🔊 Listen", "🔊 Suno")
    lang_code = "en-IN" if st.session_state.get("language", "Hindi") == "English" else "hi-IN"
    err_msg = t("Sorry, your browser doesn\\'t support Text-to-Speech.", "Sorry, aapka browser Text-to-Speech support nahi karta.")
    
    html = f"""
    <div style="margin-top: 5px;">
        <button onclick="speakText()" style="
            background-color: #f0f2f6; border: 1px solid #ccc; border-radius: 15px;
            padding: 4px 12px; cursor: pointer; font-size: 14px; color: #333;
            display: inline-flex; align-items: center; gap: 6px; transition: background 0.2s;
        " onmouseover="this.style.background='#e0e2e6'" onmouseout="this.style.background='#f0f2f6'">
            {btn_text}
        </button>
    </div>
    <script>
    function speakText() {{
        if ('speechSynthesis' in window) {{
            window.speechSynthesis.cancel(); // Stop current speech if any
            const utterance = new SpeechSynthesisUtterance('{safe_text}');
            utterance.lang = '{lang_code}';
            window.speechSynthesis.speak(utterance);
        }} else {{
            alert("{err_msg}");
        }}
    }}
    </script>
    """
    st.components.v1.html(html, height=45)



st.set_page_config(
    page_title="AI Tutor 🌾",
    page_icon="🌾",
    layout="centered",
)

if "language" not in st.session_state:
    st.session_state["language"] = "Hindi"
if "mode" not in st.session_state:
    st.session_state["mode"] = "Fast Result"

col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.title(t("🌾 AI Tutor", "🌾 Hindi AI Tutor"))
with col2:
    st.selectbox("🌐 Language / भाषा", ["Hindi", "English"], key="language")
with col3:
    st.selectbox(t("⚡ Mode", "⚡ Mode"), ["Fast Result", "Long Think"], key="mode")

# --- LOGIN SYSTEM ---
# We check if the user is already stored in the session state.
if "student_id" not in st.session_state:
    st.subheader(t("Login / Sign Up", "Login / Sign Up"))
    st.caption(t("New here? Just enter your name and password — your account will be created automatically!", "Naye ho? Bas apna naam aur password daalo — account apne aap ban jayega!"))

    name_input = st.text_input(t("What is your name?", "Tumhara naam kya hai? (What is your name?)"))
    password_input = st.text_input(t("Password", "Password"), type="password")

    if st.button(t("Start Learning", "Start Learning")):
        # Input validation — strip whitespace
        clean_name = name_input.strip() if name_input else ""
        clean_password = password_input.strip() if password_input else ""

        if not clean_name:
            st.error(t("⚠️ Please enter your name!", "⚠️ Naam toh daalo! (Please enter your name)"))
            st.stop()

        elif clean_password != password_input:
            st.error(t("⚠️ Password cannot contain leading or trailing spaces!", "⚠️ Password ke end or start m space nahi ho sakta! (Password can't contain space in end or start)"))
            st.stop()
            
        elif not clean_password: 
            st.error(t("⚠️ Please enter your password!", "⚠️ Password khali nahi chhod sakte! (Please enter your password)"))
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
        st.header(t(f"🙏 Welcome, {st.session_state['student_name']}", f"🙏 {st.session_state['student_name']}"))

        streak = st.session_state["streak"]
        st.metric(t("🔥 Current Streak", "🔥 Current Streak"), t(f"{streak} Days", f"{streak} Days"))

        # Streak badges
        badges = []
        if streak >= 30:
            badges.append(t("🥇 30-Day Champion", "🥇 30-Day Champion"))
        if streak >= 7:
            badges.append(t("🥈 Week Warrior", "🥈 Week Warrior"))
        if streak >= 3:
            badges.append(t("🥉 3-Day Starter", "🥉 3-Day Starter"))
        if badges:
            st.subheader(t("🏅 Badges", "🏅 Badges"))
            for badge in badges:
                st.write(badge)
        else:
            st.caption(t("🏅 Keep learning daily to earn badges!", "🏅 Keep learning daily to earn badges!"))

        # Progress chart
        progress = get_student_progress(st.session_state["student_id"])
        if progress:
            st.subheader(t("📊 My Progress", "📊 My Progress"))
            st.bar_chart(progress)

        st.divider()
        if st.button(t("🚪 Logout", "🚪 Logout")):
            st.session_state.clear()
            st.rerun()

    # --- MAIN TUTOR INTERFACE (Chat UI) ---
    st.success(t(f"Hello, {st.session_state['student_name']}! 🙏 | 🔥 Streak: {st.session_state['streak']} Days", f"Namaste, {st.session_state['student_name']}! 🙏 | 🔥 Streak: {st.session_state['streak']} Days"))

    # Display chat history
    for msg in st.session_state.get("messages", []):
        with st.chat_message(msg["role"], avatar=msg.get("avatar")):
            # Show images if this message had them
            if msg.get("images"):
                img_cols = st.columns(4)
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
    btn_voice = t("🎤 Speak (Voice Input)", "🎤 Bolo (Voice Input)")
    err_voice = t("❌ Browser doesn\\'t support voice input", "❌ Browser mein voice support nahi hai")
    msg_listening = t("🔴 Listening...", "🔴 Sun raha hoon...")
    lang_voice = "en-US" if st.session_state.get("language", "Hindi") == "English" else "hi-IN"

    voice_component = f"""
    <div style="margin-bottom: 10px;">
        <button id="voiceBtn" onclick="startVoice()" style="
            background: linear-gradient(135deg, #FF9933, #FF6600);
            color: white; border: none; padding: 10px 20px;
            border-radius: 25px; cursor: pointer; font-size: 16px;
            box-shadow: 0 2px 8px rgba(255, 102, 0, 0.3);
            transition: transform 0.2s;
        " onmouseover="this.style.transform='scale(1.05)'" 
           onmouseout="this.style.transform='scale(1)'">
            {btn_voice}
        </button>
        <span id="voiceStatus" style="margin-left: 10px; color: #888;"></span>
    </div>
    <script>
    function startVoice() {{
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) {{
            document.getElementById('voiceStatus').innerText = '{err_voice}';
            return;
        }}
        const recognition = new SpeechRecognition();
        recognition.lang = '{lang_voice}';
        recognition.interimResults = false;
        
        document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #e74c3c, #c0392b)';
        document.getElementById('voiceStatus').innerText = '{msg_listening}';
        
        recognition.onresult = function(event) {{
            const text = event.results[0][0].transcript;
            // Find the Streamlit chat input and set its value
            const chatInput = parent.document.querySelector('textarea[data-testid="stChatInputTextArea"]');
            if (chatInput) {{
                const nativeInputValueSetter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
                nativeInputValueSetter.call(chatInput, text);
                chatInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                document.getElementById('voiceStatus').innerText = '✅ ' + text;
            }}
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        }};
        
        recognition.onerror = function(event) {{
            document.getElementById('voiceStatus').innerText = '❌ Error: ' + event.error;
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        }};
        
        recognition.onend = function() {{
            document.getElementById('voiceBtn').style.background = 'linear-gradient(135deg, #FF9933, #FF6600)';
        }};
        
        recognition.start();
    }}
    </script>
    """
    st.components.v1.html(voice_component, height=60)

    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = 0

    # --- 📷 Image Upload Section ---
    with st.expander(t("📷 Attach Photo (Textbook, Handwriting, Diagram...)", "📷 Photo Attach Karo (Textbook, Handwriting, Diagram...)"), expanded=False):
        st.caption(t("📸 Upload a photo — textbook page, handwritten doubt, diagram, or blackboard!", "📸 Photo upload karo — textbook page, handwritten doubt, diagram, blackboard kuch bhi!"))

        uploaded_files = st.file_uploader(
            t("Choose images", "Choose images"),
            type=ALLOWED_TYPES,
            accept_multiple_files=True,
            key=f"image_uploader_{st.session_state['uploader_key']}",
            label_visibility="collapsed",
        )

        # Validate and show previews
        if uploaded_files:
            # Check max image count
            if len(uploaded_files) > MAX_IMAGES:
                st.warning(t(f"⚠️ Maximum {MAX_IMAGES} images allowed! Only the first {MAX_IMAGES} will be used.", f"⚠️ Maximum {MAX_IMAGES} images allowed! Sirf pehli {MAX_IMAGES} use hongi."))
                uploaded_files = uploaded_files[:MAX_IMAGES]

            valid_files = []
            for f in uploaded_files:
                file_size_mb = f.size / (1024 * 1024)
                if file_size_mb > MAX_FILE_SIZE_MB:
                    st.error(t(f"❌ '{f.name}' is too large ({file_size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed.", f"❌ '{f.name}' bahut badi hai ({file_size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB allowed."))
                else:
                    valid_files.append(f)

            if valid_files:
                st.markdown(t(f"**{len(valid_files)} photo(s) ready** ✅", f"**{len(valid_files)} photo(s) ready** ✅"))

                # Show preview thumbnails
                preview_cols = st.columns(4)
                for idx, f in enumerate(valid_files):
                    with preview_cols[idx % 4]:
                        image_bytes = f.read()
                        f.seek(0)  # Reset pointer after reading
                        img = Image.open(io.BytesIO(image_bytes))
                        # Create thumbnail for preview
                        img.thumbnail((300, 300))
                        st.image(img, caption=f.name, use_container_width=True)

                # Store valid files for sending locally
                current_valid_images = valid_files
            else:
                current_valid_images = []
        else:
            current_valid_images = []

    # Chat input
    user_input = st.chat_input(t("Ask your doubt... (with or without photo)", "Apna doubt pucho... (photo ke saath ya bina)"))

    if user_input or current_valid_images:
        # Need at least text or images to proceed
        clean_input = user_input.strip() if user_input else ""

        if not clean_input and not current_valid_images:
            st.toast(t("⚠️ Please write something or upload a photo!", "⚠️ Kuch toh likho ya photo upload karo!"))
        else:
            # --- Process images ---
            image_b64_list = []

            for f in current_valid_images:
                f.seek(0)  # Reset file pointer
                image_bytes = f.read()
                b64_str = base64.b64encode(image_bytes).decode("utf-8")
                image_b64_list.append(b64_str)

            # Build display text
            display_text = clean_input if clean_input else t("📷 (Photo sent for analysis)", "📷 (Photo sent for analysis)")

            # 1. Build the user message (append AFTER API call to avoid duplication)
            user_msg = {"role": "user", "content": display_text, "avatar": "👨‍🎓"}
            if image_b64_list:
                user_msg["images"] = image_b64_list

            with st.chat_message("user", avatar="👨‍🎓"):
                # Show uploaded images in the chat bubble
                if image_b64_list:
                    img_cols = st.columns(4)
                    for idx, img_b64 in enumerate(image_b64_list):
                        with img_cols[idx % 4]:
                            st.image(
                                base64.b64decode(img_b64),
                                use_container_width=True,
                            )
                st.markdown(display_text)

            # 2. Get AI response (with images if present)
            with st.chat_message("assistant", avatar="🤖"):
                spinner_text = t("Tutor is looking at the photo... 🔍", "Tutor photo dekh raha hai... 🔍") if image_b64_list else t("Tutor is thinking...", "Tutor soch raha hai...")
                with st.spinner(spinner_text):
                    # Fetch weak topics for spaced repetition
                    due_topics_data = get_due_reviews(st.session_state["student_id"])
                    weak_topics = ", ".join([topic[0] for topic in due_topics_data]) if due_topics_data else None

                    response_data = get_response(
                        clean_input,
                        chat_history=st.session_state.get("messages", []),
                        images=image_b64_list if image_b64_list else None,
                        weak_topics=weak_topics,
                        language=st.session_state["language"],
                        mode=st.session_state["mode"]
                    )

                action = response_data.get("action", "explain")
                tutor_reply = response_data.get("tutor_response", "⚠️ Koi response nahi mila.")
                quiz_data = response_data.get("quiz_data")
                next_suggestion = response_data.get("next_action_suggestion")

                # --- Action Badge ---
                action_labels = {
                    "explain": t("💡 Explain", "💡 Samjhao"),
                    "quiz": t("❓ Quiz Time", "❓ Quiz Time"),
                    "revise": t("🔄 Revision", "🔄 Revision"),
                    "game": t("🎮 Fun Game", "🎮 Fun Game"),
                    "clarify": t("🤔 Clarification", "🤔 Clarification"),
                }
                badge = action_labels.get(action, t("💬 Response", "💬 Response"))
                st.caption(badge)

                # --- Tutor Response (always shown) ---
                st.markdown(tutor_reply)
                render_tts_button(tutor_reply)

                # --- Action-Specific UI ---
                if action == "explain":
                    st.info(t("💡 **Did you understand?** If yes, let's move on. If not, feel free to ask again!", "💡 **Samajh aa gaya?** Agar haan toh aage badhte hain, warna phir se puchho!"))

                elif action == "revise":
                    st.warning(t("🔄 **Practice this topic again!** Revision leads to mastery.", "🔄 **Ye topic phir se practice karo!** Revision se hi mastery aati hai."))

                elif action == "clarify":
                    st.info(t("❓ **Please explain your question more clearly** so I can help you better.", "❓ **Apna question thoda aur clearly batao** taaki main better help kar sakun."))

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
                                "mcq": t("📝 Multiple Choice", "📝 Multiple Choice"),
                                "spot_the_mistake": t("🔍 What is Wrong?", "🔍 Galat Kya Hai?"),
                                "fill_blank": t("✏️ Fill in the Blank", "✏️ Fill in the Blank"),
                            }
                            emoji = "🎮" if action == "game" else type_labels.get(quiz_type, "📝 Quiz")
                            st.markdown(f"### {emoji}")
                            st.markdown(f"**{question}**")

                            # Use a unique key for each quiz based on message count
                            quiz_key = f"quiz_{len(st.session_state.get('messages', []))}"

                            selected = st.radio(
                                t("Choose your answer:", "Apna jawab chuno:"),
                                options,
                                key=quiz_key,
                                index=None,
                            )

                            # Submit button instead of instant check
                            if st.button(t("✅ Submit Answer", "✅ Jawab Submit Karo"), key=f"submit_{quiz_key}", type="primary"):
                                if not selected:
                                    st.warning(t("⚠️ Please select an option first!", "⚠️ Pehle ek option chuno!"))
                                else:
                                    is_correct = (selected == correct)

                                    if is_correct:
                                        st.success(t("🎉 **Absolutely correct! Excellent!**", "🎉 **Bilkul sahi! Bahut badhiya!**"))
                                        st.balloons()
                                    else:
                                        st.error(t(f"❌ **Wrong!** The correct answer was: **{correct}**", f"❌ **Galat!** Sahi jawab tha: **{correct}**"))
                                        st.caption(t("No worries — we learn from our mistakes! 💪", "Koi baat nahi — galtiyon se hi seekhte hain! 💪"))

                                    # Show explanation
                                    if explanation:
                                        st.info(t(f"📖 **Explanation:** {explanation}", f"📖 **Samjho:** {explanation}"))

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
                    "explain": t("💡 Explanation coming next", "💡 Aage explanation milega"),
                    "quiz": t("❓ Quiz coming next", "❓ Aage quiz aayega"),
                    "revise": t("🔄 Revision time", "🔄 Revision hogi"),
                    "game": t("🎮 Game coming next", "🎮 Aage game hoga"),
                    "clarify": t("🤔 Tell me a bit more", "🤔 Thoda aur batao"),
                }
                hint = suggestion_labels.get(next_suggestion, "")
                if hint:
                    st.toast(hint)

            # 4. Clear pending images after sending by resetting the uploader key
            if current_valid_images:
                st.session_state["uploader_key"] += 1
                st.rerun()
