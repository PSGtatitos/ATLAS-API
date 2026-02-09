# 🤖 ATLAS - AI Voice Assistant

A voice-activated AI assistant powered by **Vosk** for speech recognition, **Claude** (via OpenRouter) for AI responses, and **Edge TTS** for natural-sounding speech synthesis.

![ATLAS Banner](https://img.shields.io/badge/ATLAS-Voice%20Assistant-blue?style=for-the-badge)
![Node.js](https://img.shields.io/badge/Node.js-18+-green?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10+-yellow?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

## ✨ Features

- 🎤 **Offline Speech Recognition** - Uses Vosk for fast, private transcription
- 🧠 **AI-Powered Responses** - Claude Sonnet via OpenRouter API
- 🗣️ **Natural Voice Output** - Edge TTS with British male voice (JARVIS-like)
- 💬 **Conversation Memory** - Maintains context across interactions
- 🔇 **Noise Filtering** - Automatically ignores keyboard sounds, breathing, etc.
- 🌍 **Multi-language Support** - English and Greek transcription models (coming soon!!!)

## 📋 Prerequisites

- **Node.js** 18+
- **Python** 3.10+
- **Vosk Model** (download from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models))
- **OpenRouter API Key** (get one at [openrouter.ai](https://openrouter.ai))

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/yourusername/atlas-api.git
cd atlas-api
```

### 2. Install dependencies

```bash
# Node.js dependencies
npm install

# Python dependencies
pip install vosk pyaudio pyttsx3 python-dotenv requests edge-tts pygame
```

### 3. Download a Vosk model

Download an English model (recommended: `vosk-model-small-en-us-0.15` for speed or `vosk-model-en-us-0.22` for accuracy):

```bash
# Example for small English model (~40MB)
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
```

### 4. Configure environment

Create a `.env` file:

```env
# OpenRouter API Key (required)
OPENROUTER_API_KEY=your_openrouter_api_key_here

# Vosk Model Paths (at least one required)
VOSK_MODEL_PATH_EN=C:/path/to/vosk-model-small-en-us-0.15
VOSK_MODEL_PATH_EL=C:/path/to/vosk-model-el-gr-0.7

# Optional
PORT=3000
DEBUG=false
```

### 5. Start the server

```bash
# Start the API server
node index.js

# In another terminal, start the voice client
python voice_client.py
```

## 🎙️ Usage

Once running, simply speak to ATLAS:

- **Ask questions**: "What time is it?" / "What's the weather like?"
- **Have conversations**: ATLAS remembers context within a session
- **Exit**: Say "goodbye" or "goodbye atlas"

### Console Output

```
🎤 Starting ATLAS voice assistant...
💡 Say 'goodbye' to exit

🎤 Recording...
✅ Recording finished
👤 You: what time is it
🤖 ATLAS: It is 10:46 PM.
📝 Conversation length: 3 messages

[TTS] Speaking: It is 10:46 PM.
[TTS] Using Edge TTS voice: en-GB-RyanNeural
[TTS] Playback finished
```

## 🔧 API Endpoints

### `POST /api/transcribe`

Transcribe audio to text using Vosk.

```json
{
  "audio": "<base64-encoded-wav>",
  "language": "en"  // optional: "en" or "el"
}
```

### `POST /api/ask`

Get an AI response from Claude.

```json
{
  "text": "What time is it?",
  "context": {
    "temperature": 23.5,
    "humidity": 65,
    "location": "Athens, Greece"
  },
  "conversationHistory": []
}
```

### `GET /health`

Health check endpoint.

## 🎨 Customization

### Change the TTS Voice

Edit `voice_client.py` and change the `EDGE_VOICE` variable:

```python
# British male (default - JARVIS-like)
EDGE_VOICE = "en-GB-RyanNeural"

# Other options:
# "en-GB-ThomasNeural"  - British male
# "en-US-GuyNeural"     - American male
# "en-AU-WilliamNeural" - Australian male
# "en-GB-SoniaNeural"   - British female
```

### Adjust Recording Settings

In `voice_client.py`:

```python
RECORD_SECONDS = 10      # Max recording time
SILENCE_THRESHOLD = 500  # Audio energy threshold
SILENCE_DURATION = 1.5   # Seconds of silence to stop
MIN_SPEECH_LENGTH = 2    # Minimum characters for valid speech
```

## 📁 Project Structure

```
atlas-api/
├── index.js              # Express API server
├── voice_client.py       # Voice interaction client
├── vosk_transcribe.py    # Vosk transcription helper
├── package.json          # Node.js dependencies
├── .env                  # Environment configuration
├── .gitignore           # Git ignore rules
└── README.md            # This file
```

## 🐛 Troubleshooting

### "No valid Vosk model found"
- Ensure `VOSK_MODEL_PATH_EN` or `VOSK_MODEL_PATH` is set correctly in `.env`
- The path should point to the extracted model folder (containing `am/`, `conf/`, etc.)

### No audio playback
- Ensure your speakers/headphones are connected
- Check that pygame is installed: `pip install pygame`
- Try running: `python -c "import pygame; pygame.mixer.init(); print('OK')"`

### "Connection error" on every request
- Make sure the API server is running: `node index.js`
- Check that port 3000 is not blocked

## 📄 License

MIT License - feel free to use and modify!

## 🙏 Credits

- [Vosk](https://alphacephei.com/vosk/) - Offline speech recognition
- [OpenRouter](https://openrouter.ai/) - AI model routing
- [Edge TTS](https://github.com/rany2/edge-tts) - Microsoft Edge text-to-speech
- [Claude](https://anthropic.com/) - AI assistant by Anthropic
