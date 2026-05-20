# 🦇 SERANA CLOUD AI - Natural Language Voice Follower (BETA)

**Version:** 1.0 (BETA) | **Architecture:** Hybrid Edge-Cloud NLP

Say goodbye to dialogue menus. **Serana Cloud AI** is an experimental, next-generation follower overhaul that allows you to command Serana using your real voice via a Push-to-Talk system.

Instead of typing or selecting options, simply hold the 'X' key, say _"Let's go to Whiterun"_ or _"Kill that Draugr"_, and watch her execute the action in real-time.

---

## PRIVACY FIRST: ZERO AUDIO RECORDING

We know "Cloud AI" sounds intimidating. Here is our absolute guarantee:

- **Your voice is NEVER recorded or uploaded.**
- The Speech-to-Text (STT) transcription happens **100% locally** on your PC using the Whisper AI model.
- Only the transcribed text string (e.g., the words _"Follow me"_) is sent to our private research cloud to extract the intent. No audio data ever leaves your computer.

---

## KEY FEATURES

### 1. True Natural Language Understanding (NLU)

You don't need to speak like a robot. Powered by a custom-trained RoBERTa model hosted on a private Cloud VPS, the AI understands context. You can say _"Wait here"_, _"Hold your position"_, or _"Don't move"_-and the engine will process it as the exact same command.

### 2. Smart Threat Lock & Tactical Combat

Vanilla Skyrim AI often suffers from "lobotomy" (freezing mid-combat when changing targets). This mod injects a custom Papyrus router that bypasses this limitation. Command her to _"Switch to magic"_ or _"Attack that Draugr"_, and she will execute tactical maneuvers without breaking the Havok physics engine.

### 3. Dual-Engine Pathfinding

Command Serana to navigate anywhere. Look at a chair and say _"Sit there"_, or look at the empty ground and say _"Move to that spot"_. The mod uses mathematical trigonometric projections to create invisible markers, forcing Serana's AI package to navigate even in areas with poor NavMesh.

### 4. Dynamic Relationship System (DRS)

Serana has a memory. Compliment her (_"You look great today"_) or insult her, and her internal Affinity Score (-100 to +100) will shift. This dictates her mood, unlocking 424 fully lip-synced dialogues-covering all 5 affinity tiers and major intent categories-produced via ElevenLabs and voice-converted to match Laura Bailey's original performance.

---

## HOW IT WORKS (UNDER THE HOOD)

Why use a Cloud Server? Why not run everything locally?

Running a multi-task NLP inference pipeline (Intent + Entity + Sentiment simultaneously) on a quantized RoBERTa model requires dedicated CPU resources that would compete with Skyrim's own thread pool. By offloading this AI logic to a dedicated **Ubuntu VPS (Cloud)** and keeping only the lightweight Whisper STT transcription on your **PC (Edge)**, this mod prevents severe gameplay stuttering. Even players with older CPUs can run this mod smoothly!

1. **You Speak (Edge):** Python script transcribes your voice to text locally.
2. **Brain Processes (Cloud):** Text is sent to our FastAPI server in Jakarta. _(Note: Latency may vary by region. Best experienced from Southeast Asia, but functionally seamless globally for conversational commands)._
3. **Engine Executes (Skyrim):** The intent is dropped asynchronously into Skyrim via PapyrusUtil JSON bridge.

---

## INSTALLATION & USAGE

**Please read the included `README.txt` inside the mod folder for the full step-by-step guide and troubleshooting!**

**Quick Summary:**

1. Install this mod via **Mod Organizer 2** (Requires SKSE & PapyrusUtil SE).
2. Install **Python 3.10 or newer** on your PC (Make sure to check "Add Python to PATH" during installation).
3. Open the `Voice_Client` folder, launch `cmd`, and run these two commands in order:
   `python -m pip install --upgrade pip`
   `python -m pip install -r requirements.txt`
4. **CRITICAL:** Launch Command Prompt **AS ADMINISTRATOR**, navigate to the `Voice_Client` folder, and run `python stt_client.py`. Keep it open in the background.
5. Launch Skyrim, hold **'X'** to speak, and enjoy!

---

## COMPATIBILITY & LIMITATIONS

- **Serana Overhauls:** Incompatible with mods that drastically alter Serana's base AI package and mental model (e.g., Serana Dialogue Add-on / SDA). Visual replacers are 100% fine.
- **Hardware & Latency (CPU Bottleneck):** By default, the local STT transcription relies on your CPU. Transcription may take 2-5 seconds on older processors. For true real-time instant processing, manual configuration of CUDA/cuDNN for NVIDIA GPUs is required.
- **Language:** The STT is currently optimized for English voice commands.
- **Beta Server:** The Cloud VPS is a private research server. Occasional downtime for maintenance may occur.

---

### Developer Note

This project is also my very first Skyrim mod ever created.

What began as an Informatics Engineering thesis project at the Polytechnic State of Jakarta (PNJ) eventually evolved into a large-scale experiment in hybrid AI systems, natural language interaction, and Creation Engine behavior design.

The goal of this project is not only to create a more immersive follower experience, but also to explore how modern AI architectures can interact with legacy game engines in real-time gameplay scenarios without sacrificing performance. It is provided "as is" to gather qualitative user feedback (UAT). Constructive feedback, bug reports, and GitHub pull requests are highly appreciated!
