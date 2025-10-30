import streamlit as st
import json
import datetime
import time
import os
import gspread
from google.oauth2 import service_account
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import streamlit.components.v1 as components


load_dotenv()
# ----------------------------
# APP CONFIG
# ----------------------------
st.set_page_config(page_title="Thinkle - Daily Deep Thinking", layout="centered")

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ----------------------------
# GOOGLE SHEETS CONNECTION
# ----------------------------
try:
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = service_account.Credentials.from_service_account_info(
        st.secrets["google_service_account"], scopes=scope
    )
    client_sheets = gspread.authorize(creds)
    
    # Replace with your actual Sheet ID
    SHEET_ID = "1t7YlpY8JsMrLvfB-wM7URaT1l6C4TlVa5bRC2VAfdHc"
    sheet = client_sheets.open_by_key(SHEET_ID).sheet1
except Exception as e:
    st.error(f"Failed to connect to Google Sheets: {str(e)}")
    sheet = None

# ----------------------------
# DAILY QUESTION LOADING
# ----------------------------
QUESTIONS_PATH = Path(__file__).parent / "questions.json"
if QUESTIONS_PATH.exists():
    with open(QUESTIONS_PATH, "r", encoding="utf-8") as f:
        QUESTIONS_DATA = json.load(f)

def get_daily_question_and_theme():
    weeks = QUESTIONS_DATA.get("weeks", [])
    # For now we use week 1 (index 0). You can extend logic to rotate weeks by date.
    current_week_index = 0
    if not weeks or current_week_index >= len(weeks):
        return "No question available", "No theme available"
    week = weeks[current_week_index]
    questions = week.get("questions", [])
    if not questions:
        return "No question available", week.get("theme", "No theme available")
    # choose question by day of year mod questions length
    day_index = datetime.date.today().timetuple().tm_yday % len(questions)
    return questions[day_index], week.get("theme", "Theme")


# ----------------------------
# XP + FEEDBACK LOGIC
# ----------------------------
def evaluate_answer(answer, question):
    prompt = f"""
You are a critical thinking coach. Evaluate the following answer for depth, clarity, and originality.
Question: {question}
Answer: {answer}
Provide:
1. A short feedback sentence.
2. A numerical XP score between 1 and 20.
Respond in JSON like this:
{{"feedback": "...", "xp": 12}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.choices[0].message.content
        data = json.loads(text)
        return data["feedback"], int(data["xp"])
    except Exception as e:
        return f"Error: {e}", 0

# ----------------------------
# TIMER FUNCTIONS
# ----------------------------
TIMER_DURATION = 300  # 5 minutes in seconds

def start_timer():
    st.session_state["start_time"] = datetime.datetime.now().timestamp()

def get_remaining_time():
    if "start_time" not in st.session_state:
        return TIMER_DURATION
    elapsed = datetime.datetime.now().timestamp() - st.session_state["start_time"]
    remaining = TIMER_DURATION - elapsed
    return max(0, remaining)

# ----------------------------
# SESSION STATE
# ----------------------------
if "xp_total" not in st.session_state:
    st.session_state["xp_total"] = 0
if "streak" not in st.session_state:
    st.session_state["streak"] = 0
if "feedback" not in st.session_state:
    st.session_state["feedback"] = ""
if "question" not in st.session_state or "week_theme" not in st.session_state:
    q, theme = get_daily_question_and_theme()
    st.session_state["question"] = q
    st.session_state["week_theme"] = theme
# new flag to indicate the user started the session
if "started" not in st.session_state:
    st.session_state["started"] = False
# persist the user's answer across reruns
if "user_answer" not in st.session_state:
    st.session_state["user_answer"] = ""

# ----------------------------
# UI
# ----------------------------
st.title("🧠 Thinkle")
st.subheader("Train your reasoning every day")

st.markdown(f"#### Theme — {st.session_state['week_theme']}")

def _start_session():
    st.session_state["started"] = True
    st.session_state["start_time"] = datetime.datetime.now().timestamp()
    st.session_state["user_answer"] = ""

if not st.session_state["started"]:
    st.info("Press Start when you're ready. The question will appear and the timer will begin.")
    st.button("🚀 Start Thinking", on_click=_start_session)
else:
    # Once started: show question and keep Start button gone
    question = st.session_state["question"]
    st.markdown(f"### 🗓️ Today’s Question:\n**{question}**")

    # Timer display and auto-refresh while running
    TIMER_CONTAINER = st.empty()
    remaining = get_remaining_time()
    minutes, seconds = divmod(int(remaining), 60)
    TIMER_CONTAINER.markdown(f"### ⏳ Time Remaining: {minutes:02d}:{seconds:02d}")
    if remaining == 0:
        st.warning("⏰ Time’s up! You can still submit your answer.")
    else:
        # Client-side reload every 10 seconds to update the timer (no time.sleep, no deprecated APIs)
        components.html(
            """
            <script>
              (function(){
                try {
                  const params = new URLSearchParams(window.location.search);
                  params.set('_timer', Date.now());
                  const newUrl = window.location.pathname + '?' + params.toString();
                  window.history.replaceState(null, '', newUrl);
                  // reload after 10 seconds to trigger Streamlit rerun and update the timer
                  setTimeout(function(){ location.reload(); }, 10000);
                } catch(e) {
                  // fallback: still reload after 10s
                  setTimeout(function(){ location.reload(); }, 10000);
                }
              })();
            </script>
            """,
            height=0,
        )
    # Answer input + submission — persist using key tied to session_state
    user_answer = st.text_area("💬 Your Answer", height=150, placeholder="Type your thoughts here...", key="user_answer")

    if st.button("📤 Submit Answer"):
        if st.session_state["user_answer"].strip() == "":
            st.warning("Please write something before submitting.")
        else:
            feedback, xp = evaluate_answer(st.session_state["user_answer"], question)
            st.session_state["feedback"] = feedback
            st.session_state["xp_total"] += xp
            st.session_state["streak"] += 1

            # Save to Google Sheets
            sheet.append_row([
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "user_1",
                question,
                st.session_state["user_answer"],
                xp,
                feedback,
                st.session_state["streak"]
            ])

            st.success(f"✅ Feedback: {feedback}")
            st.info(f"🌟 You earned {xp} XP! Total: {st.session_state['xp_total']} XP")

# ----------------------------
# Footer
# ----------------------------
st.divider()
st.caption("Thinkle © 2025 — Grow your mind, one question at a time.")
