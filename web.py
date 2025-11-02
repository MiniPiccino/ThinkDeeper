import streamlit as st
import time
import json
import datetime
from openai import OpenAI

# Initialize OpenAI (replace with your own key or env variable)
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Helper: daily question loader ---
def get_daily_question():
    with open("questions.json", "r", encoding="utf-8") as f:
        data = json.load(f)["questions"]
    day_index = datetime.date.today().timetuple().tm_yday % len(data)
    return data[day_index]

# --- Helper: AI evaluation ---
def evaluate_answer(question, user_answer):
    prompt = f"""
    You are a reasoning coach. 
    The user answered this deep question: "{question}"
    Their answer: "{user_answer}"

    1. Give short feedback (1 sentence).
    2. Assign an XP score (1-20) based on depth of reasoning.
    Return in JSON: {{ "feedback": "...", "xp": ... }}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    result = json.loads(response.choices[0].message.content)
    return result["feedback"], result["xp"]

# --- Helper: Wordle-style XP animation ---
def show_score_animation(current_xp, gained_xp, feedback, level_xp=100):
    st.markdown("## 💭 **Thinkle Score**")

    total_blocks = 10
    new_total = min(current_xp + gained_xp, level_xp)
    filled_blocks = int(new_total / level_xp * total_blocks)

    # Animate tiles one by one
    bar = ""
    for i in range(total_blocks + 1):
        bar = "🟩" * min(i, filled_blocks) + "⬜" * (total_blocks - i)
        st.markdown(f"### {bar}")
        time.sleep(0.1)

    # Show XP gain and feedback
    st.markdown(f"<h3 style='color:#32CD32;'>+{gained_xp} XP ⚡️</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:18px; color:#999;'>🧠 {feedback}</p>", unsafe_allow_html=True)

    # Little celebration 🎉
    st.balloons()

# --- CSS Glow for level-up ---
st.markdown("""
    <style>
    @keyframes pulse {
        0% { text-shadow: 0 0 5px #7DF9FF; }
        50% { text-shadow: 0 0 20px #00FFFF; }
        100% { text-shadow: 0 0 5px #7DF9FF; }
    }
    .glow-text {
        animation: pulse 1.5s infinite;
        color: #00FFFF;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

# --- Session State Setup ---
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "streak" not in st.session_state:
    st.session_state.streak = 0

# --- Main UI ---
st.title("🧩 Thinkle: Train Your Reasoning")
question = get_daily_question()
st.subheader(f"💭 Today’s Question:")
st.markdown(f"### “{question}”")

user_answer = st.text_area("✍️ Your answer:", placeholder="Write your thoughts here...")

if st.button("📤 Submit"):
    if user_answer.strip():
        feedback, gained_xp = evaluate_answer(question, user_answer)

        # Update XP and streak
        st.session_state.xp += gained_xp
        st.session_state.streak += 1

        # Show animated XP reveal
        show_score_animation(st.session_state.xp, gained_xp, feedback)

        # Optional: store result (e.g. Google Sheets)
        # sheet.append_row([...])  # if integrated

    else:
        st.warning("Please write your answer first! 💬")

# Show current streak
st.sidebar.markdown(f"🔥 **Streak:** {st.session_state.streak} days")
st.sidebar.markdown(f"⚡ **Total XP:** {st.session_state.xp}")
