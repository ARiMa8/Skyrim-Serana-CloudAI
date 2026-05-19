import sounddevice as sd
import soundfile as sf
import keyboard
import numpy as np
import os
import re
import requests
import time
import json  # TAMBAHAN MUTLAK: Untuk menulis file JSON ke Skyrim

# Membungkam peringatan symlink dari Hugging Face
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1" 

from faster_whisper import WhisperModel

# ==========================================
# KONFIGURASI PATH MUTLAK SKYRIM (ATOMIC DROP)
# ==========================================
SKYRIM_MOD_DIR = r"G:\Modding Apps\Mod Organizer 2 - Game Instances\TES V - Skyrim - AE\mods\Serana AI - Brain Data\SKSE\Plugins\StorageUtilData"
TEMP_FILE_PATH = os.path.join(SKYRIM_MOD_DIR, "TempCommand.json")
FINAL_FILE_PATH = os.path.join(SKYRIM_MOD_DIR, "SeranaCommand.json")

# ==========================================
# 1. INISIALISASI MESIN STT
# ==========================================
print(" Membangunkan Telinga Serana (Loading Whisper Model)...")
model_size = "small.en" 
model = WhisperModel(model_size, device="cpu", compute_type="int8")
print(" Telinga Serana Siap Mendengar!")

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
        print(" Warning: vocabulary.txt tidak ditemukan. Menggunakan mode standar.")
        return ""

# Load kamus sekali saja saat startup
SKYRIM_PROMPT = load_skyrim_vocabulary()

def record_audio():
    print(f"\n[INFO] Tahan tombol '{PTT_KEY}' untuk bicara, lepaskan untuk memproses...")
    keyboard.wait(PTT_KEY)
    print(" Mendengarkan... (Sedang Merekam)")

    audio_data = []

    def callback(indata, frames, time, status):
        if status:
            pass 
        audio_data.append(indata.copy())

    with sd.InputStream(samplerate=RATE, channels=CHANNELS, callback=callback):
        while keyboard.is_pressed(PTT_KEY):
            sd.sleep(100) 

    print(" Memproses suara...")
    
    audio_np = np.concatenate(audio_data, axis=0)
    sf.write(WAVE_OUTPUT_FILENAME, audio_np, RATE)

if __name__ == "__main__":
    # Pastikan folder target Mod Organizer 2 benar-benar ada
    if not os.path.exists(SKYRIM_MOD_DIR):
        print(f"ERROR: Direktori Skyrim tidak ditemukan!\nCek path: {SKYRIM_MOD_DIR}")
        exit()

    try:
        while True:
            record_audio()

            # 1. MULAI STOPWATCH STT
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
            
            # 2. HENTIKAN STOPWATCH STT
            stt_latency = (time.time() - t_stt_start) * 1000 # Konversi ke ms
            
            # Jika Whisper halusinasi karena mikrofon sunyi
            if final_text.lower() in ["you", "thank you", ""]:
                print(" [Peringatan]: Suara tidak terdengar. Pastikan setting Microphone Windows sudah benar.")
            elif final_text:
                print(f" Dragonborn: \"{final_text}\"")
                
                # ==========================================
                # TAHAP 2: HTTP BRIDGE & LATENCY PROFILING
                # ==========================================
                print(" Mengirim ke Otak Serana (NLU) di Jakarta...")
                
                # 3. MULAI STOPWATCH NLU
                t_nlu_start = time.time() 
                
                try:
                    response = requests.post(
                        "http://202.155.91.237:8000/chat", 
                        json={"text": final_text},
                        timeout=3
                    )
                    
                    # 4. HENTIKAN STOPWATCH NLU & HITUNG TOTAL
                    nlu_latency = (time.time() - t_nlu_start) * 1000 
                    total_latency = stt_latency + nlu_latency
                    
                    if response.status_code == 200:
                        data = response.json()
                        print(f" NLU Sukses!")
                        
                        # CETAK LAPORAN PROFILING LENGKAP
                        print("-" * 30)
                        print(f"Breakdown Waktu:")
                        print(f"   - Waktu STT (Whisper) : {stt_latency:.2f} ms")
                        print(f"   - Waktu NLU (API)     : {nlu_latency:.2f} ms")
                        print(f" TOTAL TRUE LATENCY    : {total_latency:.2f} ms")
                        print("-" * 30)
                        
                        # ==========================================
                        # TAHAP 3: ATOMIC FILE DROP (THE FINAL BRIDGE)
                        # ==========================================
                        try:
                            # Tulis ke file sementara (mencegah Papyrus membaca file setengah matang)
                            with open(TEMP_FILE_PATH, "w", encoding="utf-8") as f:
                                json.dump(data, f, indent=4)
                            
                            # Tindih file asli secara instan (Atomic Swap)
                            os.replace(TEMP_FILE_PATH, FINAL_FILE_PATH)
                            print(f"Payload NLU berhasil ditembakkan ke Skyrim!")
                            print(f"Target: SeranaCommand.json")
                        except Exception as e:
                            print(f"GAGAL menulis ke folder Skyrim: {e}")

                    else:
                        print(f" NLU Gagal (Status {response.status_code}): {response.text}")
                except Exception as e:
                    print(f" GAGAL menyambung ke server NLU Cloud: {e}")
                    print(" Pastikan Container Docker di DomaiNesia sedang menyala!")
                
                print("=" * 50)
            
            if os.path.exists(WAVE_OUTPUT_FILENAME):
                os.remove(WAVE_OUTPUT_FILENAME)

    except KeyboardInterrupt:
        print("\n Mematikan Telinga Serana...")