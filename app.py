import streamlit as st
import base64
import io
import re
import calendar as cal_module
from datetime import date, timedelta
from PIL import Image
from gemini_api import get_response
from db_manager import login_and_update_streak, log_concept, log_quiz_result, get_due_reviews, get_calendar_data
from chat_component import inject_chat_css, render_chat_input_box, clear_chat_input, get_api_mode

def t(en_text, hi_text):
    return en_text if st.session_state.get("language", "Hindi") == "English" else hi_text

def clean_latex(text):
    """Converts LaTeX math notation to readable Unicode text.
    Streamlit's KaTeX renderer breaks certain LaTeX into vertical
    single-character lines, so we strip it out entirely."""

    # Remove display math blocks $$...$$ first, then inline $...$
    def _replace_math(match):
        inner = match.group(1)
        # Common LaTeX command → Unicode replacements
        replacements = [
            (r'\\rightarrow', '→'), (r'\\leftarrow', '←'),
            (r'\\Rightarrow', '⇒'), (r'\\Leftarrow', '⇐'),
            (r'\\times', '×'), (r'\\div', '÷'),
            (r'\\pm', '±'), (r'\\mp', '∓'),
            (r'\\leq', '≤'), (r'\\geq', '≥'),
            (r'\\neq', '≠'), (r'\\approx', '≈'),
            (r'\\infty', '∞'), (r'\\pi', 'π'),
            (r'\\theta', 'θ'), (r'\\alpha', 'α'),
            (r'\\beta', 'β'), (r'\\gamma', 'γ'),
            (r'\\delta', 'δ'), (r'\\lambda', 'λ'),
            (r'\\mu', 'μ'), (r'\\sigma', 'σ'),
            (r'\\omega', 'ω'), (r'\\phi', 'φ'),
            (r'\\sqrt', '√'), (r'\\sum', 'Σ'),
            (r'\\prod', 'Π'), (r'\\int', '∫'),
            (r'\\partial', '∂'), (r'\\nabla', '∇'),
            (r'\\cdot', '·'), (r'\\ldots', '…'),
            (r'\\dots', '…'), (r'\\quad', ' '),
            (r'\\qquad', '  '), (r'\\,', ' '),
            (r'\\;', ' '), (r'\\!', ''),
            (r'\\text', ''), (r'\\mathrm', ''),
            (r'\\mathbf', ''), (r'\\frac', ''),
        ]
        for pattern, repl in replacements:
            inner = re.sub(pattern, repl, inner)

        # Handle subscripts: _{...} or _X → subscript chars
        sub_map = str.maketrans('0123456789ijknm', '₀₁₂₃₄₅₆₇₈₉ᵢⱼₖₙₘ')
        def sub_repl(m):
            content = m.group(1) or m.group(2)
            return content.translate(sub_map)
        inner = re.sub(r'_\{([^}]*)\}|_([a-zA-Z0-9])', sub_repl, inner)

        # Handle superscripts: ^{...} or ^X
        sup_map = str.maketrans('0123456789n+-', '⁰¹²³⁴⁵⁶⁷⁸⁹ⁿ⁺⁻')
        def sup_repl(m):
            content = m.group(1) or m.group(2)
            return content.translate(sup_map)
        inner = re.sub(r'\^\{([^}]*)\}|\^([a-zA-Z0-9+-])', sup_repl, inner)

        # Handle \frac{a}{b} → a/b
        inner = re.sub(r'\{([^}]*)\}\s*\{([^}]*)\}', r'\1/\2', inner)

        # Remove remaining braces
        inner = inner.replace('{', '').replace('}', '')

        # Clean up leftover backslashes from unknown commands
        inner = re.sub(r'\\([a-zA-Z]+)', r'\1', inner)

        return inner.strip()

    # Process $$...$$ (display math) and $...$ (inline math)
    text = re.sub(r'\$\$(.+?)\$\$', _replace_math, text, flags=re.DOTALL)
    text = re.sub(r'\$(.+?)\$', _replace_math, text, flags=re.DOTALL)

    # Also handle \(...\) and \[...\] delimiters
    text = re.sub(r'\\\((.+?)\\\)', _replace_math, text, flags=re.DOTALL)
    text = re.sub(r'\\\[(.+?)\\\]', _replace_math, text, flags=re.DOTALL)

    return text

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
    st.session_state["mode"] = "Fast"

# Inject Claude-style chat CSS
inject_chat_css()

col1, col2 = st.columns([3, 1])
with col1:
    st.title(t("🌾 AI Tutor", "🌾 Hindi AI Tutor"))
with col2:
    st.selectbox("🌐 Language / भाषा", ["Hindi", "English"], key="language")

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

        elif not clean_password:
            st.error(t("⚠️ Please enter your password!", "⚠️ Password khali nahi chhod sakte! (Please enter your password)"))
            st.stop()

        elif clean_password != password_input:
            st.error(t("⚠️ Password cannot contain leading or trailing spaces!", "⚠️ Password ke end or start m space nahi ho sakta! (Password can't contain space in end or start)"))
            st.stop()
            
        else:
            # Call our SQLite DB function to get ID and calculate streak
            try:
                s_id, streak = login_and_update_streak(clean_name, clean_password)
            except ValueError:
                st.error(t("⚠️ Wrong password or name already taken!", "⚠️ Galat password ya naam pehle se maujood hai!"))
                st.stop()

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

        # --- Mini Calendar in Sidebar ---
        st.divider()
        st.subheader(t("📅 Learning Calendar", "📅 Learning Calendar"))

        past_data, future_data = get_calendar_data(st.session_state["student_id"])
        active_dates = set(past_data.keys())  # dates with learning activity

        today = date.today()
        year = today.year
        month = today.month

        # Month/year header
        month_name = cal_module.month_name[month]
        st.markdown(f"**{month_name} {year}**")

        # Build the calendar grid as HTML
        cal_obj = cal_module.Calendar(firstweekday=6)  # Sunday first
        month_days = cal_obj.monthdayscalendar(year, month)

        # Day headers
        day_headers = ["Su", "Mo", "Tu", "We", "Th", "Fr", "Sa"]
        header_html = "".join([f"<th style='text-align:center;padding:2px 6px;font-size:11px;color:#888;'>{d}</th>" for d in day_headers])

        rows_html = ""
        for week in month_days:
            row = ""
            for day_num in week:
                if day_num == 0:
                    row += "<td style='padding:3px;'></td>"
                else:
                    day_date = date(year, month, day_num)
                    date_str = day_date.isoformat()
                    is_today = (day_date == today)
                    is_active = (date_str in active_dates)

                    # Determine circle style
                    if is_active:
                        bg = "#2ea043"  # green
                        text_color = "white"
                    elif is_today:
                        bg = "#58a6ff"  # blue for today
                        text_color = "white"
                    else:
                        bg = "#3a3a3a"  # neutral dark
                        text_color = "#aaa"

                    border = "2px solid #58a6ff" if is_today else "none"

                    row += f"""<td style='text-align:center;padding:3px;'>
                        <div style='width:28px;height:28px;border-radius:50%;background:{bg};
                        display:inline-flex;align-items:center;justify-content:center;
                        font-size:11px;color:{text_color};border:{border};'
                        title='{date_str}'>{day_num}</div></td>"""
            rows_html += f"<tr>{row}</tr>"

        calendar_html = f"""
        <table style='border-collapse:collapse;margin:0 auto;'>
            <tr>{header_html}</tr>
            {rows_html}
        </table>
        <div style='margin-top:8px;font-size:11px;color:#aaa;text-align:center;'>
            <span style='color:#2ea043;'>●</span> Active &nbsp;
            <span style='color:#58a6ff;'>●</span> Today &nbsp;
            <span style='color:#3a3a3a;'>●</span> No activity
        </div>
        """
        st.markdown(calendar_html, unsafe_allow_html=True)

        st.divider()
        if st.button(t("🚪 Logout", "🚪 Logout")):
            st.session_state.clear()
            st.rerun()

    # --- MAIN TUTOR INTERFACE (Chat UI) ---
    st.success(t(f"Hello, {st.session_state['student_name']}! 🙏 | 🔥 Streak: {st.session_state['streak']} Days", f"Namaste, {st.session_state['student_name']}! 🙏 | 🔥 Streak: {st.session_state['streak']} Days"))

    # Display chat history
    for msg_idx, msg in enumerate(st.session_state.get("messages", [])):
        if msg["role"] == "quiz":
            with st.chat_message("assistant", avatar="🎮"):
                quiz_data = msg.get("quiz_data", {})
                question = quiz_data.get("question", "")
                options = quiz_data.get("options", [])
                correct = quiz_data.get("correct_answer", "")
                explanation = quiz_data.get("explanation", "")
                quiz_type = quiz_data.get("quiz_type", "mcq")

                if question and options:
                    st.divider()
                    type_labels = {
                        "mcq": t("📝 Multiple Choice", "📝 Multiple Choice"),
                        "spot_the_mistake": t("🔍 What is Wrong?", "🔍 Galat Kya Hai?"),
                        "fill_blank": t("✏️ Fill in the Blank", "✏️ Fill in the Blank"),
                    }
                    emoji = "🎮" if msg.get("action") == "game" else type_labels.get(quiz_type, "📝 Quiz")
                    st.markdown(f"### {emoji}")
                    st.markdown(f"**{question}**")

                    if msg.get("answered"):
                        st.markdown(f"**Your Answer:** {msg['selected_option']} " + ("✅" if msg['is_correct'] else "❌"))
                        if not msg['is_correct']:
                            st.markdown(f"**Correct Answer:** {correct}")
                        if explanation:
                            st.info(t(f"📖 **Explanation:** {explanation}", f"📖 **Samjho:** {explanation}"))
                    else:
                        quiz_key = f"quiz_history_{msg_idx}"
                        selected = st.radio(
                            t("Choose your answer:", "Apna jawab chuno:"),
                            options,
                            key=quiz_key,
                            index=None,
                        )

                        if st.button(t("✅ Submit Answer", "✅ Jawab Submit Karo"), key=f"submit_{quiz_key}", type="primary"):
                            if not selected:
                                st.warning(t("⚠️ Please select an option first!", "⚠️ Pehle ek option chuno!"))
                            else:
                                is_correct = (selected == correct)
                                msg["answered"] = True
                                msg["selected_option"] = selected
                                msg["is_correct"] = is_correct

                                if is_correct:
                                    st.success(t("🎉 **Absolutely correct! Excellent!**", "🎉 **Bilkul sahi! Bahut badhiya!**"))
                                    st.balloons()
                                else:
                                    st.error(t(f"❌ **Wrong!** The correct answer was: **{correct}**", f"❌ **Galat!** Sahi jawab tha: **{correct}**"))

                                log_quiz_result(
                                    student_id=st.session_state["student_id"],
                                    topic=msg.get("topic", "Unknown"),
                                    quiz_type=quiz_type,
                                    question=question,
                                    student_answer=selected,
                                    correct_answer=correct,
                                    is_correct=is_correct,
                                )
                                st.rerun()
        else:
            with st.chat_message(msg["role"], avatar=msg.get("avatar")):
                # Show images if this message had them
                if msg.get("images"):
                    img_cols = st.columns(4)
                    for i, img_b64 in enumerate(msg["images"]):
                        with img_cols[i % 4]:
                            st.image(
                                base64.b64decode(img_b64),
                                use_container_width=True,
                            )
                st.markdown(clean_latex(msg["content"]))
                # Add play button to past assistant messages
                if msg["role"] == "assistant":
                    render_tts_button(clean_latex(msg["content"]))

    # --- Claude-style Chat Input ---
    user_input, uploaded_images, should_send = render_chat_input_box()

    if should_send:
        clean_input = user_input.strip() if user_input else ""

        # --- Process images from the chat component ---
        image_b64_list = [img["b64_full"] for img in uploaded_images]

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
                    mode=get_api_mode(st.session_state.get("mode", "Fast")),
                )

            action = response_data.get("action", "explain")
            tutor_reply = clean_latex(response_data.get("tutor_response", "⚠️ Koi response nahi mila."))
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
                st.info(t("👇 Please answer the quiz below!", "👇 Niche diye gaye quiz ka jawab do!"))

        # Add user message to history AFTER API call (prevents sending it twice)
        st.session_state["messages"].append(user_msg)

        # Build assistant message for chat history
        st.session_state["messages"].append({"role": "assistant", "content": tutor_reply, "avatar": "🤖"})

        if action in ("quiz", "game") and quiz_data:
            st.session_state["messages"].append({
                "role": "quiz",
                "quiz_data": quiz_data,
                "topic": response_data.get("topic", "Unknown"),
                "action": action,
                "answered": False,
                "selected_option": None,
                "is_correct": None
            })

        # 3. Silently log the weak topic in the background for progress tracking
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

        # 4. Clear the input after sending
        clear_chat_input()
        st.rerun()
