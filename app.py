import streamlit as st
import requests
import speech_recognition as sr
import edge_tts
import asyncio
import os
from pydub import AudioSegment
from pydub.playback import play
import tempfile

# --- Page Setup ---
st.set_page_config(layout="wide", page_title="Voice Chatbot")

# --- Responsive CSS ---
st.markdown("""
    <style>
    /* Base responsive styles */
    html, body, .main {
        background-color: #1E90FF;
        color: white;
        font-family: Arial, sans-serif;
    }
    
    /* Responsive layout adjustments */
    @media (max-width: 768px) {
        /* Stack columns vertically on mobile */
        .column {
            width: 100% !important;
            padding: 5px !important;
        }
        
        /* Adjust avatar sizes */
        .avatar {
            max-width: 100px !important;
            margin-top: 10px !important;
        }
        
        /* Make chat bubbles full width */
        .chat-bubble {
            max-width: 90% !important;
            font-size: 14px !important;
            padding: 8px 12px !important;
        }
        
        /* Adjust input elements */
        .stTextInput>div>div>input {
            font-size: 14px !important;
        }
        
        /* Make buttons more touch-friendly */
        .stButton>button {
            padding: 8px 16px !important;
            font-size: 14px !important;
        }
    }
    
    /* Chat bubbles */
    .chat-bubble {
        padding: 10px 16px;
        margin: 10px 0;
        border-radius: 18px;
        max-width: 80%;
        font-size: 16px;
        line-height: 1.6;
        color: white;
        word-wrap: break-word;
    }
    .user-bubble {
        background-color: #006400;
        align-self: flex-end;
    }
    .bot-bubble {
        background-color: #1E90FF;
        align-self: flex-start;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #006400 !important;
        color: white !important;
        border: 1px solid #006400 !important;
    }
    .stButton>button:hover {
        background-color: #004d00 !important;
        border: 1px solid #004d00 !important;
    }
    
    /* Input field */
    .stTextInput>div>div>input {
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- Configuration ---
OPENROUTER_API_KEY = "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"
MODEL = "openai/gpt-3.5-turbo"

# --- State Init ---
if 'current_input' not in st.session_state:
    st.session_state.current_input = ""
if 'current_output' not in st.session_state:
    st.session_state.current_output = ""
if 'show_continue' not in st.session_state:
    st.session_state.show_continue = False
if 'urdu_mode' not in st.session_state:
    st.session_state.urdu_mode = True

# --- Language Settings ---
if st.session_state.urdu_mode:
    VOICE = "ur-PK-UzmaNeural"
    SYSTEM_PROMPT = "آپ ایک خاتون معاون ہیں جو صرف اردو میں مکمل جواب دیتی ہیں۔"
    INPUT_METHODS = ["مائیکروفون", "ٹیکسٹ درج کریں"]
    RECORD_BUTTON = "🎤 ریکارڈ کریں"
    SEND_BUTTON = "بھیجیں"
    INPUT_PROMPT = "اپنا سوال یہاں ٹائپ کریں:"
    PROCESSING = "جواب تیار ہو رہا ہے..."
    READY_TO_SPEAK = "بولنے کے لیے تیار..."
    NOT_UNDERSTOOD = "صاف آواز نہیں ملی، براہ کرم دوبارہ کوشش کریں"
    CONTINUE_YES = "ہاں، اگلا سوال پوچھیں"
    CONTINUE_NO = "نہیں، بات چیت ختم کریں"
    FAREWELL = "اللہ حافظ! آپ سے بات کر کے خوشی ہوئی۔"
else:
    VOICE = "en-US-JennyNeural"
    SYSTEM_PROMPT = "You are a helpful assistant that responds in complete English answers."
    INPUT_METHODS = ["Microphone", "Type text"]
    RECORD_BUTTON = "🎤 Record"
    SEND_BUTTON = "Send"
    INPUT_PROMPT = "Type your question here:"
    PROCESSING = "Generating response..."
    READY_TO_SPEAK = "Ready to speak..."
    NOT_UNDERSTOOD = "Audio not understood, please try again"
    CONTINUE_YES = "Yes, ask another question"
    CONTINUE_NO = "No, end conversation"
    FAREWELL = "Goodbye! It was nice talking to you."

# --- Responsive Layout ---
cols = st.columns([1, 2, 1])
with cols[0]:
    st.image("https://unlimitedchatbot.com/wp-content/uploads/2022/03/chatbot-marketing.gif", 
             use_container_width=True, caption="You")

with cols[1]:
    st.subheader("Dual Language Voice Chatbot")
    
    # Language toggle
    if st.button("Switch to English" if st.session_state.urdu_mode else "اردو میں تبدیل کریں"):
        st.session_state.urdu_mode = not st.session_state.urdu_mode
        st.session_state.current_input = ""
        st.session_state.current_output = ""
        st.session_state.show_continue = False
        st.rerun()

    # --- Input UI ---
    input_method = st.radio("Select input method:", INPUT_METHODS)

    def listen():
        r = sr.Recognizer()
        with sr.Microphone() as source:
            st.info(READY_TO_SPEAK)
            try:
                audio = r.listen(source, timeout=5, phrase_time_limit=10)
                language = "ur-PK" if st.session_state.urdu_mode else "en-US"
                return r.recognize_google(audio, language=language)
            except sr.UnknownValueError:
                st.warning(NOT_UNDERSTOOD)
                return ""
            except Exception as e:
                st.error(f"Listening error: {str(e)}")
                return ""

    async def speak_and_play(text):
        try:
            with st.spinner(PROCESSING):
                communicate = edge_tts.Communicate(text=text, voice=VOICE)
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                    tmp_path = tmp_file.name
                await communicate.save(tmp_path)
                sound = AudioSegment.from_mp3(tmp_path)
                play(sound)
                os.unlink(tmp_path)
        except Exception as e:
            st.error(f"Audio error: {str(e)}")

    def ask_ai(prompt):
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        try:
            response = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except Exception:
            return "Sorry, I couldn't process your request right now." if not st.session_state.urdu_mode else "معذرت، میں ابھی جواب نہیں دے پا رہی"

    if input_method == INPUT_METHODS[0]:
        if st.button(RECORD_BUTTON):
            user_input = listen()
            if user_input:
                st.session_state.current_input = user_input
    else:
        user_input = st.text_input(INPUT_PROMPT)
        if user_input and st.button(SEND_BUTTON):
            st.session_state.current_input = user_input

    # --- Chat Display ---
    if st.session_state.current_input and not st.session_state.show_continue:
        st.markdown(f'<div class="chat-bubble user-bubble">{st.session_state.current_input}</div>', unsafe_allow_html=True)
        ai_response = ask_ai(st.session_state.current_input)
        st.session_state.current_output = ai_response
        st.markdown(f'<div class="chat-bubble bot-bubble">{ai_response}</div>', unsafe_allow_html=True)
        asyncio.run(speak_and_play(ai_response))
        st.session_state.show_continue = True

    # --- Continue/End Buttons ---
    if st.session_state.show_continue:
        cols = st.columns(2)
        with cols[0]:
            if st.button(CONTINUE_YES):
                st.session_state.current_input = ""
                st.session_state.current_output = ""
                st.session_state.show_continue = False
                st.rerun()
        with cols[1]:
            if st.button(CONTINUE_NO):
                st.session_state.current_input = ""
                st.session_state.current_output = ""
                st.session_state.show_continue = False
                st.success(FAREWELL)
                st.rerun()