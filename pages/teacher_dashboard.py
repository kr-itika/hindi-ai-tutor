import os
import streamlit as st
import pandas as pd
from db_manager import get_teacher_dashboard_data, get_all_students, get_quiz_dashboard_data, DB_NAME

st.set_page_config(
    page_title="Teacher Dashboard 📊",
    page_icon="📊",
    layout="wide",
)

st.title("📊 Teacher Dashboard")

# Password from environment variable or Streamlit secrets (never hardcoded)
try:
    _default = st.secrets.get("teacher_password", "teacher123")
except Exception:
    _default = "teacher123"
TEACHER_PASSWORD = os.environ.get("TEACHER_PASSWORD", _default)

if "teacher_auth" not in st.session_state:
    st.session_state["teacher_auth"] = False

if not st.session_state["teacher_auth"]:
    st.subheader("🔒 Teacher Login")
    pwd = st.text_input("Enter teacher password", type="password")
    if st.button("Login"):
        if pwd == TEACHER_PASSWORD:
            st.session_state["teacher_auth"] = True
            st.rerun()
        else:
            st.error("❌ Galat password! (Wrong password)")
else:
    # --- Dashboard Content ---
    st.success("✅ Teacher mode active")

    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Activity", "👥 Students", "📈 Topic Analysis", "📝 Quiz Performance"])

    with tab1:
        st.subheader("Recent Student Activity")
        df = get_teacher_dashboard_data()
        if df.empty:
            st.info("Abhi tak koi data nahi hai. Students ko pehle kuch questions puchne do!")
        else:
            st.dataframe(df, use_container_width=True)

    with tab2:
        st.subheader("Registered Students")
        students_df = get_all_students()
        if students_df.empty:
            st.info("Koi student registered nahi hai abhi.")
        else:
            st.dataframe(students_df, use_container_width=True)

    with tab3:
        st.subheader("Topic-wise Status Breakdown")
        df = get_teacher_dashboard_data()
        if df.empty:
            st.info("Abhi tak koi data nahi hai.")
        else:
            # Status distribution
            status_counts = df["status"].value_counts()
            st.bar_chart(status_counts)

            # Top struggling topics
            struggling = df[df["status"].str.lower() == "struggling"]
            if not struggling.empty:
                st.subheader("⚠️ Most Struggled Topics")
                topic_counts = struggling["concept_name"].value_counts().head(10)
                st.bar_chart(topic_counts)

    with tab4:
        st.subheader("Quiz Performance")
        quiz_df = get_quiz_dashboard_data()
        if quiz_df.empty:
            st.info("Abhi tak koi quiz data nahi hai. Students ko pehle quiz dene do!")
        else:
            st.dataframe(quiz_df, use_container_width=True)

            # Quiz accuracy chart
            result_counts = quiz_df["result"].value_counts()
            st.subheader("📊 Quiz Accuracy")
            st.bar_chart(result_counts)

            # Topics with most wrong answers
            wrong = quiz_df[quiz_df["result"] == "Wrong ❌"]
            if not wrong.empty:
                st.subheader("⚠️ Topics Needing More Practice")
                weak_topics = wrong["topic"].value_counts().head(10)
                st.bar_chart(weak_topics)

    st.divider()
    if st.button("🚪 Logout"):
        st.session_state["teacher_auth"] = False
        st.rerun()
