#!/usr/bin/env python3
# voice_client.py - Wake word → record → base64 → /api/transcribe → /api/ask → speak

import json
import sys
import time
import requests
import os
import wave
import base64
import re
from dotenv import load_dotenv
import pyaudio
from vosk import Model, KaldiRecognizer, SetLogLevel
import pyttsx3
import tempfile
import uuid
import winsound

SetLogLevel(0)

# TTS setup (offline)
tts_engine = pyttsx3.init('sapi5')  # Use Windows SAPI5 directly
tts_engine.setProperty('volume', 0.9)

# Get available voices
available_voices = tts_engine.getProperty('voices')
print(f"[TTS] Available voices: {[v.name for v in available_voices]}")

import subprocess
import asyncio
import edge_tts
import pygame

# Initialize pygame mixer for audio playback
pygame.mixer.init()

# Edge TTS voice - British male for JARVIS-like sound
EDGE_VOICE = "en-GB-RyanNeural"  # British male voice

async def _edge_speak(text, voice=EDGE_VOICE):
    """Generate speech using Edge TTS and play it"""
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"atlas_tts_{uuid.uuid4().hex}.mp3")
    
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(tmp_path)
    
    return tmp_path

def speak(text):
    """Speak text using Edge TTS (JARVIS-like British voice)"""
    try:
        print(f"[TTS] Speaking: {text}")
        print(f"[TTS] Using Edge TTS voice: {EDGE_VOICE}")
        
        # Run async Edge TTS
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            audio_file = loop.run_until_complete(_edge_speak(text))
        finally:
            loop.close()
        
        print(f"[TTS] Audio file created: {audio_file}")
        
        # Play using pygame
        print(f"[TTS] Playing audio via pygame...")
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Wait for playback to finish
        while pygame.mixer.music.get_busy():
            pygame.time.wait(100)
        
        print(f"[TTS] Playback finished")
        
        # Clean up temp file
        try:
            pygame.mixer.music.unload()
            os.remove(audio_file)
        except:
            pass
            
    except Exception as e:
        print(f"[TTS] Edge TTS error: {e}, falling back to SAPI...")
        import traceback
        traceback.print_exc()
        # Fallback to Windows SAPI
        try:
            escaped_text = text.replace("'", "''").replace('"', '`"')
            ps_command = f'''
            Add-Type -AssemblyName System.Speech
            $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
            $synth.Rate = 1
            $synth.Speak("{escaped_text}")
            '''
            subprocess.run(["powershell", "-Command", ps_command], timeout=30)
        except Exception as e2:
            print(f"[TTS] Fallback also failed: {e2}")

# ────────────────────────────────────────────────
# CONFIG
# ────────────────────────────────────────────────

load_dotenv()

# Determine which Vosk model to use on the client side. Priority:
# 1. VOSK_MODEL_PATH (legacy)
# 2. VOSK_MODEL_PATH_EN / VOSK_MODEL_PATH_EL depending on VOSK_LANG
env_model = os.getenv("VOSK_MODEL_PATH")
model_en = os.getenv("VOSK_MODEL_PATH_EN")
model_el = os.getenv("VOSK_MODEL_PATH_EL")
# Force the client language to English only
client_lang = "en"

def choose_model_path():
    # If legacy env set and valid, prefer it
    if env_model and os.path.isdir(env_model):
        return env_model

    # If language explicitly set to Greek, prefer Greek model
    if client_lang in ("el", "greek", "gr"):
        if model_el and os.path.isdir(model_el):
            return model_el
        if model_en and os.path.isdir(model_en):
            return model_en

    # If language set to English, prefer English model
    if client_lang in ("en", "english"):
        if model_en and os.path.isdir(model_en):
            return model_en
        if model_el and os.path.isdir(model_el):
            return model_el

    # Fallback: prefer EN then EL
    if model_en and os.path.isdir(model_en):
        return model_en
    if model_el and os.path.isdir(model_el):
        return model_el

    return None

MODEL_PATH = choose_model_path()
if not MODEL_PATH:
    print("ERROR: No valid Vosk model found. Set VOSK_MODEL_PATH or VOSK_MODEL_PATH_EN/VOSK_MODEL_PATH_EL in .env")
    print(f"Checked values: VOSK_MODEL_PATH={env_model}, VOSK_MODEL_PATH_EN={model_en}, VOSK_MODEL_PATH_EL={model_el}, VOSK_LANG={client_lang}")
    sys.exit(1)

API_URL = "http://localhost:3000"

# Stop phrases checked while recording
STOP_PHRASES = [
    "ok that is all for today",
    "that's all for today",
    "ok that's all",
    "goodbye atlas",
    "goodbye"
]

# Recording settings
RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK = 1024
RECORD_SECONDS = 10          # max recording time – adjust as needed
SILENCE_THRESHOLD = 500      # energy level for silence detection
SILENCE_DURATION = 1.5       # seconds of silence to stop recording early
MIN_SPEECH_LENGTH = 2        # minimum characters for valid speech

# Words/phrases to ignore (noise artifacts)
NOISE_WORDS = {'', 'huh', 'uh', 'um', 'hmm', 'ah', 'oh', 'eh', 'a', 'the', 'i', 'it'}

# Conversation history (persists across interactions)
conversation_history = []

print(f"Vosk model: {MODEL_PATH}")
print("Ready to listen...\n")

# ────────────────────────────────────────────────
# RECORD FUNCTION
# ────────────────────────────────────────────────

def record_command():
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    print("🎤 Recording...")

    frames = []
    start_time = time.time()
    last_text = ""
    stop_detected = False

    # Create a Vosk recognizer to detect stop phrases in real-time
    model = Model(MODEL_PATH)
    rec = KaldiRecognizer(model, RATE)

    while time.time() - start_time < RECORD_SECONDS:
        data = stream.read(CHUNK, exception_on_overflow=False)
        frames.append(data)

        # Feed data to Vosk recognizer to detect stop phrase
        if rec.AcceptWaveform(data):
            result = json.loads(rec.Result())
            text = result.get("text", "").strip().lower()
            if text:
                last_text = text
                print(f"[Real-time] You said: {text}")
                # Check for stop phrase
                if any(phrase.lower() in text.lower() for phrase in STOP_PHRASES):
                    print("⛔ Stop phrase detected → stopping recording")
                    stop_detected = True
                    break
        else:
            # Check partial results too for faster detection
            partial = json.loads(rec.PartialResult())
            ptext = partial.get("partial", "").strip().lower()
            if ptext:
                last_text = ptext
            if ptext and any(phrase.lower() in ptext.lower() for phrase in STOP_PHRASES):
                print(f"⛔ Stop phrase detected in partial: {ptext}")
                stop_detected = True
                break

    print("✅ Recording finished")

    stream.stop_stream()
    stream.close()
    p.terminate()

    if not frames:
        return None, None, False

    # Save to in-memory WAV → base64
    wf_data = b''.join(frames)
    with wave.open("temp_in_memory.wav", 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(wf_data)

    with open("temp_in_memory.wav", "rb") as f:
        audio_base64 = base64.b64encode(f.read()).decode('utf-8')

    try:
        os.remove("temp_in_memory.wav")  # cleanup
    except:
        pass

    return audio_base64, last_text, stop_detected

# ────────────────────────────────────────────────
# MAIN LOOP
# ────────────────────────────────────────────────

def main():
    global conversation_history
    
    print("🎤 Starting ATLAS voice assistant...\n")
    print("💡 Say 'goodbye' or 'αντίο' to exit\n")

    try:
        while True:
            # Record until stop phrase detected
            audio_b64, last_text, stop_detected = record_command()
            
            # Check if user wants to exit
            if stop_detected and last_text:
                if any(phrase.lower() in last_text.lower() for phrase in STOP_PHRASES):
                    speak("Goodbye! Shutting down.")
                    print("👋 Stop phrase detected. Exiting.\n")
                    break
            
            if not audio_b64:
                # Silently restart - don't announce noise
                print("[Noise] No valid audio captured, restarting...")
                continue
            
            # Skip if Vosk didn't detect any speech (just noise)
            if not last_text or last_text.strip() in NOISE_WORDS:
                print(f"[Noise] Detected noise only: '{last_text}', skipping...")
                continue

            # Send to /api/transcribe
            try:
                # Build payload and force English transcription on the server
                payload = {"audio": audio_b64, "language": "en"}

                r = requests.post(
                    f"{API_URL}/api/transcribe",
                    json=payload,
                    timeout=20,
                )
                r.raise_for_status()
                trans_data = r.json()
                transcription = trans_data.get("transcription", "").strip()

                # Filter out noise/gibberish
                if not transcription or len(transcription) < MIN_SPEECH_LENGTH:
                    print(f"[Noise] Transcription too short: '{transcription}', skipping...")
                    continue
                
                # Filter out common noise words
                if transcription.lower() in NOISE_WORDS:
                    print(f"[Noise] Detected noise word: '{transcription}', skipping...")
                    continue

                print(f"👤 You: {transcription}")

                # Send to /api/ask with conversation history
                # Build a copy of the conversation history and prepend a system instruction
                send_history = list(conversation_history) if conversation_history else []
                if not any(isinstance(m, dict) and m.get("role") == "system" and "english" in m.get("content", "").lower() for m in send_history):
                    send_history.insert(0, {"role": "system", "content": "You are ATLAS assistant. Please respond ONLY in English."})

                payload = {
                    "text": transcription,
                    "context": {
                        "temperature": 23.5,
                        "humidity": 65,
                        "location": "New Philadelphia, Greece",
                        "forceResponseLanguage": "en"
                    },
                    "conversationHistory": send_history,  # send copy with system instruction
                    "responseLanguage": "en",
                    "systemPrompt": "Please respond only in English."
                }

                r2 = requests.post(f"{API_URL}/api/ask", json=payload, timeout=40)
                r2.raise_for_status()
                resp_data = r2.json()

                answer = resp_data.get("response", "No response.")
                conversation_history = resp_data.get("conversationHistory", [])  # ← Update history
                
                print(f"🤖 ATLAS: {answer}")
                print(f"📝 Conversation length: {len(conversation_history)} messages\n")
                
                speak(answer)

            except requests.exceptions.RequestException as e:
                print(f"❌ API error: {e}")
                # Only speak error if it's a real connection issue, not noise
                if "timeout" in str(e).lower() or "connection" in str(e).lower():
                    speak("Something went wrong with the connection.")
                else:
                    print("[Noise] API rejected input, likely noise - skipping...")
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                import traceback
                traceback.print_exc()
                speak("An unexpected error occurred.")

    except KeyboardInterrupt:
        speak("Goodbye!")
        print("\n👋 Shutting down via Ctrl+C.\n")

if __name__ == "__main__":
    main()