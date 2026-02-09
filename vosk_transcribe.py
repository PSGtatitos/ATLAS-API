#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import wave
import json
import io
from vosk import Model, KaldiRecognizer

# Force UTF-8 output for Windows terminal
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

def transcribe(audio_file, model_path):
    # Load model
    model = Model(model_path)
    
    # Open audio file
    wf = wave.open(audio_file, "rb")
    
    # Check format
    if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() not in [8000, 16000, 32000, 48000]:
        print("Audio file must be WAV format mono PCM.", file=sys.stderr)
        sys.exit(1)
    
    # Create recognizer
    rec = KaldiRecognizer(model, wf.getframerate())
    rec.SetWords(True)
    
    # Transcribe
    while True:
        data = wf.readframes(4000)
        if len(data) == 0:
            break
        rec.AcceptWaveform(data)
    
    # Get final result
    result = json.loads(rec.FinalResult())
    
    # Print only the text (stdout) - now UTF-8 safe
    text = result.get('text', '')
    print(text)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python vosk_transcribe.py <audio_file> <model_path>", file=sys.stderr)
        sys.exit(1)
    
    audio_file = sys.argv[1]
    model_path = sys.argv[2]
    
    transcribe(audio_file, model_path)