import sounddevice as sd
import soundfile as sf
import keyboard
import numpy as np
import os
import re
import requests
import time
import json 

# Suppress Hugging Face symlink warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1" 

from faster_whisper import WhisperModel

# DYNAMIC SKYRIM PATH CONFIGURATION (ATOMIC DROP)
current_dir = os.path.dirname(os.path.abspath(__file__))
SKYRIM_MOD_DIR = os.path.join(current_dir, "..", "SKSE", "Plugins", "StorageUtilData")

if not os.path.exists(SKYRIM_MOD_DIR):
    os.makedirs(SKYRIM_MOD_DIR)

TEMP_FILE_PATH = os.path.join(SKYRIM_MOD_DIR, "TempCommand.json")
FINAL_FILE_PATH = os.path.join(SKYRIM_MOD_DIR, "SeranaCommand.json")

# STT ENGINE INITIALIZATION
print(" [SYSTEM] Initializing Local STT Engine (Loading Whisper Model)...")
model_size = "small.en" 
model = WhisperModel(model_size, device="cpu", compute_type="int8")
print(" [SYSTEM] Audio input ready. Awaiting voice command.")

RATE = 16000
CHANNELS = 1
WAVE_OUTPUT_FILENAME = "temp_voice.wav"
PTT_KEY = 'x' 

def load_skyrim_vocabulary(filepath="vocabulary.txt"):
    if os.path.exists(filepath):
        with open(filepath, "r") as f:
            content = f.read().replace('\n', ' ')
            return content
    else:
        print(" [WARNING] vocabulary.txt not found. Proceeding with standard recognition mode.")
        return ""

# Load dictionary once during startup
SKYRIM_PROMPT = load_skyrim_vocabulary()

def record_audio():
    print(f"\n[INFO] Hold the '{PTT_KEY}' key to speak, release to process...")
    keyboard.wait(PTT_KEY)
    print(" [RECORDING] Listening...")

    audio_data = []

    def callback(indata, frames, time, status):
        if status:
            pass 
        audio_data.append(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CHANNELS, callback=callback):
        while keyboard.is_pressed(PTT_KEY):
            sd.sleep(100) 

    print(" [PROCESSING] Transcribing audio data...")
    
    audio_np = np.concatenate(audio_data, axis=0)
    sf.write(WAVE_OUTPUT_FILENAME, audio_np, RATE)

if __name__ == "__main__":
    # Ensure the Target Mod Organizer 2 directory actually exists
    if not os.path.exists(SKYRIM_MOD_DIR):
        print(f" [FATAL ERROR] Skyrim target directory not found!\n Please check the path: {SKYRIM_MOD_DIR}")
        exit()

    try:
        while True:
            record_audio()

            # START STT PROFILING TIMER
            t_stt_start = time.time()
            
            segments, info = model.transcribe(
                WAVE_OUTPUT_FILENAME, 
                beam_size=1, 
                initial_prompt=SKYRIM_PROMPT 
            )
            
            transcription = ""
            for segment in segments:
                transcription += segment.text + " "
            
            final_text = transcription.strip()
            final_text = re.sub(r'[^\w\s\']', '', final_text) 
            
            # STOP STT PROFILING TIMER
            stt_latency = (time.time() - t_stt_start) * 1000
            
            # Whisper hallucination mitigation (silent microphone)
            if final_text.lower() in ["you", "thank you", ""]:
                print(" [WARNING] No voice detected. Please verify Windows Microphone settings.")
            elif final_text:
                print(f" Dragonborn: \"{final_text}\"")
                
                # HTTP BRIDGE & LATENCY PROFILING
                print(" [NETWORK] Transmitting string to Cloud NLU Server...")
                
                # START NLU PROFILING TIMER
                t_nlu_start = time.time() 
                
                try:
                    response = requests.post(
                        "http://202.155.91.237:8000/chat", 
                        json={"text": final_text},
                        timeout=3
                    )
                    
                    # STOP NLU PROFILING TIMER & CALCULATE TOTAL
                    nlu_latency = (time.time() - t_nlu_start) * 1000 
                    total_latency = stt_latency + nlu_latency
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f" [NETWORK] Cloud NLU Response: SUCCESS 200 OK")
                        
                        # PRINT COMPLETE PROFILING REPORT
                        print("-" * 40)
                        print(f" Latency Profiling Breakdown:")
                        print(f"   - Edge STT Time (Whisper) : {stt_latency:.2f} ms")
                        print(f"   - Cloud NLU Time (API)    : {nlu_latency:.2f} ms")
                        print(f"   TOTAL ROUND-TRIP LATENCY  : {total_latency:.2f} ms")
                        print("-" * 40)
                        
                        # ATOMIC FILE DROP (THE FINAL BRIDGE)
                        try:
                            with open(TEMP_FILE_PATH, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4)
                            
                            os.replace(TEMP_FILE_PATH, FINAL_FILE_PATH)
                            print(f" [FILE SYSTEM] NLU Payload successfully injected into Skyrim VFS!")
                            print(f" Target: SeranaCommand.json")
                        except Exception as e:
                            print(f" [FATAL ERROR] Failed to write to Skyrim directory: {e}")

                    else:
                        print(f" [NETWORK ERROR] NLU Failed (Status {response.status_code}): {response.text}")
                except Exception as e:
                    print(f" [NETWORK ERROR] Failed to connect to Cloud NLU Server: {e}")
                    print(" Please ensure the VPS Docker Container is currently active.")
                
                print("=" * 60)
            
            if os.path.exists(WAVE_OUTPUT_FILENAME):
                os.remove(WAVE_OUTPUT_FILENAME)

    except KeyboardInterrupt:
        print("\n [SYSTEM] Shutting down Local STT Engine...")