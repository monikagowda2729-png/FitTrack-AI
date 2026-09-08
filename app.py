import os
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from google import genai

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "fitness.db"

st.set_page_config(
    page_title="FitTrack AI",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------- Styling ----------
st.markdown("""
<style>
    .main { background: #f7f9fc; }
    .block-container { padding-top: 1.5rem; }
    .hero {
        padding: 1.4rem 1.6rem;
        border-radius: 20px;
        background: linear-gradient(135deg, #111827, #334155);
        color: white;
        margin-bottom: 1.2rem;
    }
    .hero h1 { margin: 0; font-size: 2.2rem; }
    .hero p { margin: .35rem 0 0; opacity: .88; }
    .metric-card {
        background: white;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 1rem;
        box-shadow: 0 4px 18px rgba(15,23,42,.05);
    }
    .small { color: #64748b; font-size: .88rem; }
    .ai-box {
        border-left: 5px solid #4f46e5;
        background: #eef2ff;
        padding: 1rem 1.2rem;
        border-radius: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ---------- Database ----------
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_date TEXT NOT NULL,
            activity_type TEXT NOT NULL,
            duration INTEGER DEFAULT 0,
            steps INTEGER DEFAULT 0,
            calories INTEGER DEFAULT 0,
            notes TEXT DEFAULT ''
        )
    """)
    conn.commit()
    return conn


def add_activity(activity_date, activity_type, duration, steps, calories, notes):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO activities
               (activity_date, activity_type, duration, steps, calories, notes)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (str(activity_date), activity_type, duration, steps, calories, notes),
        )
        conn.commit()


def load_activities():
    with get_conn() as conn:
        return pd.read_sql_query(
            "SELECT * FROM activities ORDER BY activity_date DESC, id DESC", conn
        )


def delete_activity(activity_id):
    with get_conn() as conn:
        conn.execute("DELETE FROM activities WHERE id = ?", (int(activity_id),))
        conn.commit()


# ---------- Metrics ----------
def calculate_streak(df):
    if df.empty:
        return 0
    active_dates = sorted(
        {pd.to_datetime(x).date() for x in df["activity_date"].tolist()},
        reverse=True,
    )
    today = date.today()
    if not active_dates or active_dates[0] < today - timedelta(days=1):
        return 0
    streak = 1
    current = active_dates[0]
    for d in active_dates[1:]:
        if d == current - timedelta(days=1):
            streak += 1
            current = d
        else:
            break
    return streak


def weekly_data(df):
    if df.empty:
        return pd.DataFrame()
    temp = df.copy()
    temp["activity_date"] = pd.to_datetime(temp["activity_date"])
    temp["day"] = temp["activity_date"].dt.date
    start = date.today() - timedelta(days=6)
    end = date.today()
    temp = temp[(temp["day"] >= start) & (temp["day"] <= end)]
    days = pd.DataFrame({"day": pd.date_range(start, end).date})
    grouped = temp.groupby("day", as_index=False)[["steps", "calories", "duration"]].sum()
    return days.merge(grouped, on="day", how="left").fillna(0)


# ---------- Gemini ----------
def get_gemini_client():
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return None
    return genai.Client(api_key=key)


def ai_coach(df):
    client = get_gemini_client()
    if client is None:
        return "Add your GEMINI_API_KEY in the environment variables to enable the AI Coach."
    if df.empty:
        context = "No activity has been logged yet."
    else:
        recent = df.head(12).to_dict("records")
        context = str(recent)
    prompt = f"""
You are FitTrack AI, a supportive fitness tracking assistant.
Analyze the user's logged activity data and give practical, non-medical guidance.
Do not diagnose conditions or prescribe treatment.
Give:
1. A two-sentence summary
2. Three achievable suggestions for the next 7 days
3. One encouraging message
Keep it concise and beginner-friendly.

Activity data:
{context}
"""
    try:
        response = client.interactions.create(
            model="gemini-3.8-flash",
            input=prompt,
        )
        return response.output_text
    except Exception as exc:
        return f"Gemini could not respond right now: {exc}"


# ---------- App ----------
df = load_activities()

st.markdown("""
<div class="hero">
    <h1>🏃 FitTrack AI</h1>
    <p>Track your movement. Understand your progress. Get smarter with AI.</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.header("⚙️ Quick actions")
    page = st.radio("Go to", ["Dashboard", "Log Activity", "History", "AI Coach"], label_visibility="collapsed")
    st.divider()
    st.caption("Internship Task 3 • Fitness Tracker App")
    st.caption("Streamlit + SQLite + Gemini API")

if page == "Dashboard":
    total_steps = int(df["steps"].sum()) if not df.empty else 0
    total_calories = int(df["calories"].sum()) if not df.empty else 0
    total_duration = int(df["duration"].sum()) if not df.empty else 0
    streak = calculate_streak(df)

    c1, c2, c3, c4 = st.columns(4)
    for col, title, value, suffix in [
        (c1, "Total steps", total_steps, ""),
        (c2, "Calories burned", total_calories, " kcal"),
        (c3, "Workout time", total_duration, " min"),
        (c4, "Current streak", streak, " days"),
    ]:
        col.markdown(f"""
        <div class="metric-card">
            <div class="small">{title}</div>
            <h2>{value:,}{suffix}</h2>
        </div>
        """, unsafe_allow_html=True)

    st.write("")
    st.subheader("📈 Last 7 days")
    w = weekly_data(df)
    if w.empty:
        st.info("Start logging activities to see your progress charts.")
    else:
        chart_df = w.set_index("day")[["steps", "calories", "duration"]]
        st.line_chart(chart_df, height=300)

    left, right = st.columns(2)
    with left:
        st.subheader("🏋️ Activity mix")
        if not df.empty:
            mix = df.groupby("activity_type").size().sort_values(ascending=False)
            st.bar_chart(mix)
        else:
            st.info("No activities yet.")
    with right:
        st.subheader("🎯 Recent activity")
        if not df.empty:
            show = df[["activity_date", "activity_type", "duration", "steps", "calories"]].head(6)
            st.dataframe(show, use_container_width=True, hide_index=True)
        else:
            st.info("Your recent activities will appear here.")

elif page == "Log Activity":
    st.subheader("➕ Log today's activity")
    with st.form("activity_form", clear_on_submit=True):
        d = st.date_input("Date", value=date.today())
        activity_type = st.selectbox(
            "Activity type",
            ["Walking", "Running", "Cycling", "Gym workout", "Yoga", "Sports", "Other"],
        )
        col1, col2, col3 = st.columns(3)
        duration = col1.number_input("Workout time (min)", min_value=0, max_value=1440, value=30)
        steps = col2.number_input("Steps", min_value=0, max_value=100000, value=0, step=100)
        calories = col3.number_input("Calories burned", min_value=0, max_value=10000, value=0, step=10)
        notes = st.text_area("Notes (optional)", placeholder="How did the workout feel?")
        submitted = st.form_submit_button("Save activity", type="primary", use_container_width=True)
        if submitted:
            if duration == 0 and steps == 0 and calories == 0:
                st.error("Please enter at least one fitness value.")
            else:
                add_activity(d, activity_type, duration, steps, calories, notes)
                st.success("Activity saved successfully! 🎉")
                st.rerun()

elif page == "History":
    st.subheader("📋 Activity history")
    if df.empty:
        st.info("No records yet. Use Log Activity to add your first workout.")
    else:
        for _, row in df.iterrows():
            with st.expander(f"{row['activity_date']} • {row['activity_type']}"):
                a, b, c, d = st.columns(4)
                a.metric("Time", f"{row['duration']} min")
                b.metric("Steps", f"{row['steps']:,}")
                c.metric("Calories", f"{row['calories']:,}")
                d.metric("ID", int(row["id"]))
                if row["notes"]:
                    st.write(row["notes"])
                if st.button("Delete", key=f"delete_{row['id']}"):
                    delete_activity(row["id"])
                    st.success("Deleted.")
                    st.rerun()

elif page == "AI Coach":
    st.subheader("🤖 Gemini AI Coach")
    st.write("Get a short, personalized review based on the activities you have logged.")
    if st.button("Analyze my progress", type="primary"):
        with st.spinner("Gemini is analyzing your activity..."):
            result = ai_coach(df)
        st.markdown(f'<div class="ai-box">{result.replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
    st.caption("AI guidance is for general wellness and is not medical advice.")
