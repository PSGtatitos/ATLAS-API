import pyaudio
import wave
import base64

# Settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 5
OUTPUT_FILE = "test_audio.wav"

print("Recording for 5 seconds...")
print("Say something in Greek!")

p = pyaudio.PyAudio()

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

frames = []

for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("Recording finished!")

stream.stop_stream()
stream.close()
p.terminate()

# Save to WAV file
wf = wave.open(OUTPUT_FILE, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

print(f"Saved as {OUTPUT_FILE}")

# Convert to base64
with open(OUTPUT_FILE, "rb") as f:
    audio_base64 = base64.b64encode(f.read()).decode('utf-8')
    
# Save base64 to file for easy copying
with open("audio_base64.txt", "w") as f:
    f.write(audio_base64)

print("\nBase64 audio saved to audio_base64.txt")
print("Copy the contents and use in Postman!")
print(f"\nFirst 100 characters: {audio_base64[:100]}...")