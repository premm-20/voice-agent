import streamlit as st
import io
import time
from google import genai
from google.genai import types
from gtts import gTTS
from elevenlabs.client import ElevenLabs

# Configure Gemini Client
# Try to fetch from streamlit secrets
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
except Exception:
    GEMINI_API_KEY = None

client = genai.Client(api_key=GEMINI_API_KEY)
MODEL = "gemini-2.5-flash-lite"

AGENT_NAME = "guru"
SYSTEM_PROMPT = """You are Pip, a voice to-do assistant for a busy student.
Everything you say is read aloud, so: one or two short sentences, no lists, no markdown, no emojis.
Use your tools to add, read and finish to-dos. Never say you did something unless a tool did it."""

# Initialize Session States
if "todos" not in st.session_state:
    st.session_state.todos = []
if "history" not in st.session_state:
    st.session_state.history = []

# Define Tools dynamically referencing session state
def add_todo(task: str) -> str:
    """Add a task to the user's to-do list."""
    st.session_state.todos.append({"task": task, "done": False})
    return f"Added: {task}. The list has {len(st.session_state.todos)} items."

def list_todos() -> str:
    """Read the user's to-do list: each item's number, the task, and whether it is done."""
    if not st.session_state.todos:
        return "The list is empty."
    return "\n".join(f"{i + 1}. {t['task']} ({'done' if t['done'] else 'open'})" for i, t in enumerate(st.session_state.todos))

def mark_done(number: int) -> str:
    """Mark a to-do as done, by its number in the list (the first item is 1)."""
    if not 1 <= number <= len(st.session_state.todos):
        return f"There is no item {number}. The list has {len(st.session_state.todos)} items."
    st.session_state.todos[number - 1]["done"] = True
    return f"Done: {st.session_state.todos[number - 1]['task']}."

TOOLS = [add_todo, list_todos, mark_done]

def speak(text):
    try:
        ELEVEN_API_KEY = st.secrets["ELEVEN_API_KEY"]
    except Exception:
        ELEVEN_API_KEY = None

    if ELEVEN_API_KEY:
        try:
            seven = ElevenLabs(api_key=ELEVEN_API_KEY)
            return b"".join(seven.text_to_speech.convert(voice_id="JBFqnCBsd6RMKjVDRZZD", text=text, model_id="eleven_flash_v2_5"))
        except Exception as e:
            st.warning(f"ElevenLabs error, falling back to gTTS: {e}")
            
    buf = io.BytesIO()
    gTTS(text).write_to_fp(buf)
    return buf.getvalue()

def process_chat(user_input):
    chat = client.chats.create(model=MODEL, history=st.session_state.history,
                               config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT,
                                                                  tools=TOOLS, max_output_tokens=300))
    response = chat.send_message(user_input)
    st.session_state.history = chat.get_history()
    return response.text

# Streamlit App Layout
st.title(f"🎙️ {AGENT_NAME.capitalize()} Voice Assistant")
st.subheader("Your personal voice to-do assistant")

# Left sidebar: display current items
with st.sidebar:
    st.header("📝 Current Tasks")
    if not st.session_state.todos:
        st.write("Your to-do list is empty!")
    for idx, todo in enumerate(st.session_state.todos):
        status = "✅" if todo["done"] else "⭕"
        st.write(f"{idx + 1}. {status} {todo['task']}")

# Interaction
user_input = st.chat_input("Say something or type a task...")

if user_input:
    st.chat_message("user").write(user_input)
    with st.spinner("Thinking..."):
        reply = process_chat(user_input)
        st.chat_message("assistant").write(reply)
        
        # Generate and play speech response
        audio_bytes = speak(reply)
        st.audio(audio_bytes, format="audio/mp3", autoplay=True)
