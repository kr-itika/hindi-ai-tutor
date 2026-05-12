"""
Claude-style chat input component for Streamlit.
Renders a full-width rounded input container fixed at the bottom with:
- Auto-resize textarea
- Image attachment chips
- Fast/Slow mode toggle
- Send button
"""
import streamlit as st
import base64

# ---------------------------------------------------------------------------
# CSS injection  (call once per page load)
# ---------------------------------------------------------------------------

def inject_chat_css():
    """Inject all custom CSS for the Claude-style chat box."""
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap');

/* ── Hide default Streamlit chat input & file uploader ── */
div[data-testid="stChatInput"] { display: none !important; }
section[data-testid="stFileUploader"].hidden-uploader,
.hidden-uploader { display: none !important; }

/* ── Root variables ── */
:root {
    --chat-bg: #ffffff;
    --chat-border: #e0e0e0;
    --chat-shadow: 0 -2px 16px rgba(0,0,0,0.06);
    --chat-text: #1a1a1a;
    --chat-placeholder: #999;
    --chip-bg: #f3f4f6;
    --chip-border: #e0e0e0;
    --chip-text: #333;
    --pill-inactive-bg: transparent;
    --pill-inactive-border: #d0d0d0;
    --pill-inactive-text: #666;
    --pill-active-bg: #FF9933;
    --pill-active-text: #fff;
    --send-disabled: #ccc;
    --send-enabled: #FF9933;
    --toolbar-divider: #eee;
}

/* Dark mode overrides */
@media (prefers-color-scheme: dark) {
    :root {
        --chat-bg: #1e1e1e;
        --chat-border: #333;
        --chat-shadow: 0 -2px 16px rgba(0,0,0,0.3);
        --chat-text: #e8e8e8;
        --chat-placeholder: #777;
        --chip-bg: #2a2a2a;
        --chip-border: #444;
        --chip-text: #ccc;
        --pill-inactive-border: #555;
        --pill-inactive-text: #aaa;
        --toolbar-divider: #333;
    }
}

/* Streamlit dark theme detection */
[data-testid="stAppViewContainer"][data-theme="dark"],
.stApp[data-theme="dark"] {
    --chat-bg: #1e1e1e;
    --chat-border: #333;
    --chat-shadow: 0 -2px 16px rgba(0,0,0,0.3);
    --chat-text: #e8e8e8;
    --chat-placeholder: #777;
    --chip-bg: #2a2a2a;
    --chip-border: #444;
    --chip-text: #ccc;
    --pill-inactive-border: #555;
    --pill-inactive-text: #aaa;
    --toolbar-divider: #333;
}

/* ── Bottom spacer so chat history doesn't hide behind input ── */
.chat-bottom-spacer { height: 140px; }

/* ── Container ── */
.claude-chat-container {
    position: fixed; bottom: 0; left: 50%;
    transform: translateX(-50%);
    width: min(720px, calc(100% - 2rem));
    background: var(--chat-bg);
    border: 1px solid var(--chat-border);
    border-bottom: none;
    border-radius: 20px 20px 0 0;
    box-shadow: var(--chat-shadow);
    padding: 0;
    z-index: 9999;
    font-family: 'DM Sans', sans-serif;
    display: flex; flex-direction: column;
}

/* ── Image chips area ── */
.claude-chips {
    display: flex; flex-wrap: wrap; gap: 8px;
    padding: 10px 16px 0 16px;
}
.claude-chip {
    display: inline-flex; align-items: center; gap: 6px;
    background: var(--chip-bg);
    border: 1px solid var(--chip-border);
    border-radius: 10px;
    padding: 4px 10px 4px 4px;
    font-size: 12px; color: var(--chip-text);
    max-width: 180px;
}
.claude-chip img {
    width: 36px; height: 36px;
    border-radius: 8px; object-fit: cover;
}
.claude-chip-name {
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    max-width: 90px;
}
.claude-chip-x {
    cursor: pointer; font-size: 14px; color: #999;
    margin-left: auto; padding: 2px;
    border-radius: 50%; transition: color 0.15s;
}
.claude-chip-x:hover { color: #e74c3c; }

/* ── Toolbar ── */
.claude-toolbar {
    display: flex; align-items: center;
    padding: 8px 12px;
    border-top: 1px solid var(--toolbar-divider);
    gap: 6px;
}
.claude-toolbar-left {
    display: flex; align-items: center; gap: 6px; flex: 1;
}

/* Attach button */
.claude-attach-btn {
    background: none; border: 1px solid var(--pill-inactive-border);
    border-radius: 20px; padding: 5px 12px;
    cursor: pointer; font-size: 14px;
    color: var(--pill-inactive-text);
    transition: all 0.15s;
    display: inline-flex; align-items: center; gap: 4px;
}
.claude-attach-btn:hover {
    border-color: var(--send-enabled);
    color: var(--send-enabled);
}

/* Mode pill toggle */
.claude-mode-pill {
    display: inline-flex; border-radius: 20px;
    border: 1px solid var(--pill-inactive-border);
    overflow: hidden;
}
.claude-mode-opt {
    padding: 5px 14px; font-size: 13px; font-weight: 500;
    cursor: pointer; border: none; background: var(--pill-inactive-bg);
    color: var(--pill-inactive-text);
    transition: all 0.2s;
    display: inline-flex; align-items: center; gap: 4px;
}
.claude-mode-opt.active {
    background: var(--pill-active-bg);
    color: var(--pill-active-text);
}
.claude-mode-opt:first-child { border-right: 1px solid var(--pill-inactive-border); }

/* Send button */
.claude-send-btn {
    width: 36px; height: 36px;
    border-radius: 50%; border: none;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; cursor: pointer;
    transition: all 0.2s;
}
.claude-send-btn.disabled {
    background: var(--send-disabled); color: #fff; cursor: default;
    opacity: 0.5;
}
.claude-send-btn.enabled {
    background: var(--send-enabled); color: #fff;
    box-shadow: 0 2px 8px rgba(255,153,51,0.35);
}
.claude-send-btn.enabled:hover {
    transform: scale(1.08);
}

/* ── Streamlit element hiding helpers ── */
/* Make Streamlit buttons used as triggers invisible */
.stButton.hidden-trigger { display: none !important; }
.hidden-uploader-wrap > div { display: none !important; }

/* Fix bottom padding of main content */
.main .block-container { padding-bottom: 160px !important; }

/* Style the Streamlit text_area we use as the real input */
div[data-testid="stTextArea"].claude-textarea-wrap textarea {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    resize: none !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 15px !important;
    color: var(--chat-text) !important;
    padding: 14px 16px 6px 16px !important;
    min-height: 40px !important;
    max-height: 180px !important;
    outline: none !important;
}
div[data-testid="stTextArea"].claude-textarea-wrap textarea:focus {
    border: none !important;
    box-shadow: none !important;
    outline: none !important;
}
div[data-testid="stTextArea"].claude-textarea-wrap label,
div[data-testid="stTextArea"].claude-textarea-wrap .stTextArea-instructions {
    display: none !important;
}
div[data-testid="stTextArea"].claude-textarea-wrap {
    border: none !important;
    margin: 0 !important; padding: 0 !important;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Image chip HTML
# ---------------------------------------------------------------------------

def render_image_chips(uploaded_images):
    """Return HTML for thumbnail chips of uploaded images."""
    if not uploaded_images:
        return ""
    chips = []
    for idx, img_info in enumerate(uploaded_images):
        name = img_info["name"]
        b64 = img_info["b64_thumb"]
        chips.append(f"""
        <div class="claude-chip" id="chip-{idx}">
            <img src="data:image/png;base64,{b64}" alt="{name}">
            <span class="claude-chip-name" title="{name}">{name}</span>
        </div>""")
    return f'<div class="claude-chips">{"".join(chips)}</div>'


# ---------------------------------------------------------------------------
# Mode toggle HTML
# ---------------------------------------------------------------------------

def render_mode_toggle(current_mode):
    """Return HTML for the Fast/Slow pill toggle (display only — actual toggle via Streamlit)."""
    fast_cls = "active" if current_mode == "Fast" else ""
    slow_cls = "active" if current_mode == "Slow" else ""
    return f"""
    <div class="claude-mode-pill">
        <span class="claude-mode-opt {fast_cls}" id="mode-fast">⚡ Fast</span>
        <span class="claude-mode-opt {slow_cls}" id="mode-slow">🧠 Slow</span>
    </div>"""


# ---------------------------------------------------------------------------
# Full chat box rendering
# ---------------------------------------------------------------------------

def render_chat_input_box():
    """
    Render the Claude-style chat input container.
    Returns (user_text, image_list, should_send) tuple.
    
    Uses real Streamlit widgets (text_area, file_uploader, buttons)
    positioned and styled to look like the Claude chat box.
    """
    # ── Initialize session state ──
    if "chat_input_text" not in st.session_state:
        st.session_state["chat_input_text"] = ""
    if "uploaded_images" not in st.session_state:
        st.session_state["uploaded_images"] = []
    if "mode" not in st.session_state:
        st.session_state["mode"] = "Fast"
    if "send_pressed" not in st.session_state:
        st.session_state["send_pressed"] = False
    if "img_uploader_key" not in st.session_state:
        st.session_state["img_uploader_key"] = 0
    if "clear_input" not in st.session_state:
        st.session_state["clear_input"] = False

    # Check if we need to clear after a send
    default_text = ""
    if st.session_state.get("clear_input"):
        default_text = ""
        st.session_state["clear_input"] = False
    else:
        default_text = st.session_state.get("chat_input_text", "")

    # ── Image chips display (above input) ──
    if st.session_state["uploaded_images"]:
        chips_html = render_image_chips(st.session_state["uploaded_images"])
    else:
        chips_html = ""

    # ── Mode toggle display ──
    mode_html = render_mode_toggle(st.session_state.get("mode", "Fast"))

    has_content = bool(default_text.strip()) or bool(st.session_state["uploaded_images"])
    send_cls = "enabled" if has_content else "disabled"

    # ── Build the visual overlay container ──
    container_html = f"""
    <div class="claude-chat-container" id="claudeChatBox">
        {chips_html}
        <div id="claude-textarea-slot"></div>
        <div class="claude-toolbar">
            <div class="claude-toolbar-left">
                <div id="claude-attach-slot"></div>
                <div id="claude-mode-slot"></div>
            </div>
            <div id="claude-send-slot"></div>
        </div>
    </div>
    """

    # We render the container HTML first for structure context
    # Then place real Streamlit widgets that CSS will position

    # ── Bottom spacer ──
    st.markdown('<div class="chat-bottom-spacer"></div>', unsafe_allow_html=True)

    # ── The actual input container using Streamlit columns ──
    chat_box = st.container()

    with chat_box:
        # Display image chips if any
        if st.session_state["uploaded_images"]:
            st.markdown(chips_html, unsafe_allow_html=True)

            # Remove buttons for each image
            if len(st.session_state["uploaded_images"]) > 0:
                remove_cols = st.columns(len(st.session_state["uploaded_images"]) + 2)
                for idx, img_info in enumerate(st.session_state["uploaded_images"]):
                    with remove_cols[idx]:
                        if st.button(f"✕ {img_info['name'][:12]}", key=f"rm_img_{idx}",
                                     help=f"Remove {img_info['name']}"):
                            st.session_state["uploaded_images"].pop(idx)
                            st.rerun()

        # Text area
        user_text = st.text_area(
            "Message Shiksha...",
            value=default_text,
            placeholder="Message Shiksha...",
            key="claude_text_input",
            label_visibility="collapsed",
            height=68,
            max_chars=4000,
        )
        st.session_state["chat_input_text"] = user_text or ""

        # Toolbar row
        tool_cols = st.columns([1, 1, 3, 1])

        # Attach button
        with tool_cols[0]:
            attach_clicked = st.button("📎 Attach", key="attach_btn", type="secondary")

        # Mode toggle
        with tool_cols[1]:
            current_mode = st.session_state.get("mode", "Fast")
            if current_mode == "Fast":
                if st.button("⚡ Fast", key="mode_toggle_btn", type="primary"):
                    st.session_state["mode"] = "Slow"
                    st.rerun()
            else:
                if st.button("🧠 Slow", key="mode_toggle_btn", type="primary"):
                    st.session_state["mode"] = "Fast"
                    st.rerun()

        # Send button
        with tool_cols[3]:
            has_content = bool((user_text or "").strip()) or bool(st.session_state["uploaded_images"])
            send_clicked = st.button(
                "➤ Send", key="send_btn",
                type="primary" if has_content else "secondary",
                disabled=not has_content,
            )

    # ── Hidden file uploader (shown when attach is clicked) ──
    if attach_clicked or st.session_state.get("show_uploader", False):
        st.session_state["show_uploader"] = True
        uploaded = st.file_uploader(
            "Upload images",
            type=["jpg", "jpeg", "png", "webp", "gif"],
            accept_multiple_files=True,
            key=f"hidden_uploader_{st.session_state['img_uploader_key']}",
            label_visibility="collapsed",
        )
        if uploaded:
            from PIL import Image
            import io
            for f in uploaded:
                # Check if already added
                existing_names = [img["name"] for img in st.session_state["uploaded_images"]]
                if f.name not in existing_names:
                    f.seek(0)
                    raw_bytes = f.read()
                    # Create thumbnail
                    img = Image.open(io.BytesIO(raw_bytes))
                    img.thumbnail((80, 80))
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    thumb_b64 = base64.b64encode(buf.getvalue()).decode()
                    full_b64 = base64.b64encode(raw_bytes).decode()
                    st.session_state["uploaded_images"].append({
                        "name": f.name,
                        "b64_thumb": thumb_b64,
                        "b64_full": full_b64,
                    })
            st.session_state["show_uploader"] = False
            st.session_state["img_uploader_key"] += 1
            st.rerun()

    # ── Handle send ──
    should_send = False
    if send_clicked and has_content:
        should_send = True

    return user_text, st.session_state["uploaded_images"], should_send


def clear_chat_input():
    """Call after processing a message to clear the input state."""
    st.session_state["chat_input_text"] = ""
    st.session_state["uploaded_images"] = []
    st.session_state["clear_input"] = True
    st.session_state["show_uploader"] = False
    st.session_state["img_uploader_key"] = st.session_state.get("img_uploader_key", 0) + 1


def get_api_mode(ui_mode):
    """Convert UI mode label to the API mode parameter."""
    if ui_mode == "Slow":
        return "Long Think"
    return "Fast Result"
