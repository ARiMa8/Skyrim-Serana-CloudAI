import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import onnxruntime as ort
from transformers import AutoTokenizer
import numpy as np
import json
import os
import re
import random
from thefuzz import process

# Disable Hugging Face symlink warnings and verbosity for production environment
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
app = FastAPI(title="Serana AI - NLU Brain Cloud", version="5.0")

# ==========================================
# CONFIGURATION & PATHS
# ==========================================
MODEL_DIR = "./model"
DICT_PATH = "papyrus_voicelines.json" 

# ==========================================
# 1. LOAD DICTIONARIES INTO MEMORY
# ==========================================
try:
    with open(f"{MODEL_DIR}/label_mapping.json", "r") as f:
        mapping_data = json.load(f)
        
    INTENT_LABELS = {int(k): v for k, v in mapping_data.get("intent", {}).items()}
    SENTIMENT_LABELS = {int(k): v for k, v in mapping_data.get("sentiment", {}).items()}
    NER_LABELS = {int(k): v for k, v in mapping_data.get("ner", {}).items()}
    print("[System] Label mapping dictionaries loaded successfully.")
except Exception as e:
    print(f"[Error] Failed to load label_mapping.json: {e}")
    INTENT_LABELS, SENTIMENT_LABELS, NER_LABELS = {}, {}, {}

try:
    with open("fuzzy_targets.json", "r") as f:
        fuzzy_data = json.load(f)
    
    VALID_ENTITIES = []
    for category, items in fuzzy_data.items():
        VALID_ENTITIES.extend(items)
    print(f"[System] FuzzyWuzzy dictionary loaded ({len(VALID_ENTITIES)} entities).")
except Exception as e:
    print(f"[Error] Failed to load fuzzy_targets.json: {e}")
    VALID_ENTITIES = []

try:
    with open("papyrus_formids.json", "r") as f:
        FORMID_DICT = json.load(f)
    print("[System] Papyrus FormID dictionary loaded successfully.")
except Exception as e:
    print(f"[Error] Failed to load papyrus_formids.json: {e}")
    FORMID_DICT = {}

# ==========================================
# HELPER FUNCTIONS: AUDIO & TELEMETRY
# ==========================================
def get_drs_tier(score: int) -> str:
    if score <= -50: return "Resentful"
    elif score <= -1: return "Distant"
    elif score <= 49: return "Neutral"
    elif score <= 89: return "Friend"
    else: return "Partner"

def determine_combat_condition(target_name: str) -> str:
    target_lower = str(target_name).lower()
    female_keywords = ["woman", "girl", "matron", "hagraven", "vampire fletchling", "witch"]
    creature_keywords = ["dragon", "bear", "wolf", "troll", "spider", "mudcrab", "draugr", "skeleton", "spriggan", "chaurus"]
    
    if any(word in target_lower for word in female_keywords):
        return "Female"
    elif any(word in target_lower for word in creature_keywords):
        return "Creature"
    else:
        return "Male"

def fetch_audio_formid(nlu_intent: str, target_name: str, score: int) -> str:
    try:
        with open(DICT_PATH, 'r') as f:
            voicelines = json.load(f)
    except FileNotFoundError:
        return "0x000000"

    tier = get_drs_tier(score)
    intent_mapping = {
        "Movement_Follow": "Follow",
        "Movement_Wait": "Wait",
        "Inventory_Trade": "Trade",
        "Movement_GoTo": "GoTo",
        "System_Dismiss": "Dismiss",
        "Social_Chat": "Chat",
        "Social_Status": "Status",
        "Quest_Objective": "Objective",
        "Interact_Environment": "IntEnv",
        "Combat_Attack": "Attack",
        "Combat_Tactical": "Tactical"
    }

    root_key = intent_mapping.get(nlu_intent, "")
    if not root_key:
        return "0x000000"

    if root_key in ["Attack", "Tactical"]:
        condition = determine_combat_condition(target_name)
    else:
        condition = "Normal"

    intent_dict = voicelines.get(root_key, {})
    if not intent_dict:
        return "0x000000"

    condition_dict = intent_dict.get(condition, {})
    if not condition_dict:
        if root_key in ["Attack", "Tactical"] and "Creature" in intent_dict:
            condition_dict = intent_dict["Creature"]
        else:
            return "0x000000"

    if tier in condition_dict and len(condition_dict[tier]) > 0:
        return random.choice(condition_dict[tier])
    elif "Neutral" in condition_dict and len(condition_dict["Neutral"]) > 0:
        return random.choice(condition_dict["Neutral"])
    
    return "0x000000"

# ==========================================
# 2. MODEL INITIALIZATION (ONNX & TOKENIZER)
# ==========================================
print("[System] Initializing RoBERTa-based NLU Engine...")
try:
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    # Enforcing CPUExecutionProvider for cost-effective cloud deployment
    session = ort.InferenceSession(f"{MODEL_DIR}/Serana_RoBERTa_INT8.onnx", providers=['CPUExecutionProvider'])
    print("[System] NLU Engine ready for inference.")
except Exception as e:
    print(f"[Error] Failed to initialize model: {e}")

# Client Payload Schema
class ChatRequest(BaseModel):
    text: str
    affinity_score: int = 0  # Supplied by Edge STT client to calculate DRS momentum

# ==========================================
# 3. MULTI-TASK INFERENCE & FUZZY MATCHING
# ==========================================
@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    input_text = request.text
    current_affinity = request.affinity_score
    
    # 1. Tokenization
    inputs = tokenizer(input_text, return_tensors="np", padding="max_length", truncation=True, max_length=128)
    ort_inputs = {
        "input_ids": inputs["input_ids"].astype(np.int64),
        "attention_mask": inputs["attention_mask"].astype(np.int64)
    }
    
    # 2. ONNX Inference
    outputs = session.run(None, ort_inputs)
    
    intent_logits = outputs[0]
    intent_id = int(np.argmax(intent_logits, axis=-1)[0])
    intent_name = INTENT_LABELS.get(intent_id, f"Unknown_Intent_{intent_id}")
    intent_confidence = float(np.max(np.exp(intent_logits) / np.sum(np.exp(intent_logits))))

    # ========================================================
    # [PHASE 4]: DETERMINISTIC ROUTING (LEXICAL BIAS MITIGATION)
    # ========================================================
    text_lower = input_text.lower()
    tactical_mode = "" 
    
    tactical_magic_keywords = ["use your magic", "cast spells", "magic only", "use magic", "spell", "magic"]
    tactical_melee_keywords = ["use your sword", "use your blade", "melee", "close combat", "use your dagger", "sword", "blade"]
    tactical_default_keywords = ["back to your style", "go back to default", "normal style", "default style", "default"]

    if any(k in text_lower for k in tactical_magic_keywords):
        intent_name = "Combat_Tactical"
        intent_confidence = 1.0
        tactical_mode = "magic"
        print(f"[Deterministic] Tactic detected -> MAGIC")
    elif any(k in text_lower for k in tactical_melee_keywords):
        intent_name = "Combat_Tactical"
        intent_confidence = 1.0
        tactical_mode = "melee"
        print(f"[Deterministic] Tactic detected -> MELEE")
    elif any(k in text_lower for k in tactical_default_keywords):
        intent_name = "Combat_Tactical"
        intent_confidence = 1.0
        tactical_mode = "default"
        print(f"[Deterministic] Tactic detected -> DEFAULT")
    
    env_keywords = ["door", "barrel", "lever", "chest", "button", "chain", "switch", "gate", "pull", "open", "harvest"]
    if intent_name == "Inventory_Trade" and any(k in text_lower for k in env_keywords):
        intent_name = "Interact_Environment"
        intent_confidence = 1.0 
        print(f"[Deterministic Routing] Environment object detected. Overriding intent -> {intent_name}")

    trade_keywords = ["let's trade", "to trade", "trade some", "trade items", "exchange", "barter", "swap", "carry this"]
    if any(k in text_lower for k in trade_keywords) and intent_name != "Interact_Environment":
        intent_name = "Inventory_Trade"
        intent_confidence = 1.0  
        print(f"[Deterministic Routing] Trade keyword detected. Overriding intent -> {intent_name}")

    goto_keywords = ["go to", "head to", "travel to", "move to", "lead the way to"]
    if any(k in text_lower for k in goto_keywords):
        intent_name = "Movement_GoTo"
        intent_confidence = 1.0
        print(f"[Deterministic Routing] Navigation keyword detected. Overriding intent -> {intent_name}")

    dismiss_keywords = ["part ways", "dismissed", "leave my service", "go home", "we are done", "leave me alone"]
    if any(k in text_lower for k in dismiss_keywords):
        intent_name = "System_Dismiss"
        intent_confidence = 1.0
        print(f"[Deterministic Routing] Dismiss keyword detected. Overriding intent -> {intent_name}")
        
    combat_keywords = ["kill", "attack", "destroy", "eliminate", "slaughter", "focus on"]
    if any(k in text_lower for k in combat_keywords) and intent_name != "Combat_Attack":
        intent_name = "Combat_Attack"
        intent_confidence = 1.0
        print(f"[Deterministic Routing] Combat override detected. Overriding intent -> {intent_name}")
    # ========================================================
    
    sentiment_logits = outputs[1]
    sentiment_id = int(np.argmax(sentiment_logits, axis=-1)[0])
    sentiment_name = SENTIMENT_LABELS.get(sentiment_id, f"Unknown_Sentiment_{sentiment_id}")
    
    ner_logits = outputs[2][0]
    ner_predictions = np.argmax(ner_logits, axis=-1)
    tokens = tokenizer.convert_ids_to_tokens(inputs["input_ids"][0])
    
    extracted_entities = []
    current_entity_word = ""
    
    for token, pred_id in zip(tokens, ner_predictions):
        if token in ["<s>", "</s>", "<pad>"]:
            continue
            
        tag = NER_LABELS.get(int(pred_id), "O")
        is_new_word = token.startswith("Ġ")
        clean_token = token.replace("Ġ", "")
        
        if not is_new_word and current_entity_word:
            current_entity_word += clean_token
        elif tag != "O":
            if current_entity_word:
                extracted_entities.append(current_entity_word)
            current_entity_word = clean_token
        else:
            if current_entity_word:
                extracted_entities.append(current_entity_word)
                current_entity_word = ""

    if current_entity_word:
        extracted_entities.append(current_entity_word)
        
    cleaned_entities = []
    for ent in extracted_entities:
        clean_str = re.sub(r"[^a-zA-Z0-9\s'-]", '', ent).strip()
        if clean_str: 
            cleaned_entities.append(clean_str)

    # ==========================================
    # 4. FUZZY MATCHING & FALLBACK PROTOCOLS
    # ==========================================
    final_entities = []
    response_status = "success"
    
    combined_raw_entity = " ".join(cleaned_entities).strip().lower()
    
    if combined_raw_entity:
        if VALID_ENTITIES:
            best_match, score = process.extractOne(combined_raw_entity, VALID_ENTITIES)
            if score >= 85:
                final_entities.append(best_match)
            else:
                print(f"[Filter] Entity '{combined_raw_entity}' rejected. Score: {score}%")
        else:
            final_entities.append(combined_raw_entity)

    if "serana" in final_entities:
        final_entities.remove("serana")
        print("[Filter] Self-referential entity 'serana' purged from target list.")

    if intent_confidence < 0.5:
        intent_name = "Out_Of_Domain"
        response_status = "fallback"
        
    if intent_name == "Combat_Attack" and not final_entities:
        final_entities.append("nearest_enemy")
        print("[Failsafe] Combat intent missing target. Routing to -> 'nearest_enemy'")

    elif intent_name in [
        "Movement_GoTo", "Combat_Attack", "Quest_Objective"
    ] and not final_entities:
        intent_name = "Out_Of_Domain"
        response_status = "fallback"
        print(f"[Validation Failed] Intent '{intent_name}' requires an entity. Operation aborted.")

    target_plugin = ""
    target_formid_int = 0
    target_name = ""

    if final_entities:
        target_entity = final_entities[0]
        dict_value = FORMID_DICT.get(target_entity)

        if dict_value == "GENERIC":
            target_plugin = "GENERIC"
            target_name = target_entity
        elif target_entity == "nearest_enemy":
            target_plugin = "nearest_enemy"
        elif isinstance(dict_value, str) and "|" in dict_value:
            parts = dict_value.split("|")
            target_plugin = parts[0].strip()
            try:
                target_formid_int = int(parts[1].strip(), 16)
            except ValueError:
                target_formid_int = 0

    # Affection Momentum Calculation
    sentiment_shift = 0
    if sentiment_name == "Positive":
        sentiment_shift = 5
    elif sentiment_name == "Negative":
        sentiment_shift = -5

    # Fetch corresponding Voice FormID based on intent and local affinity score
    audio_formid_str = fetch_audio_formid(intent_name, target_name, current_affinity)
    audio_formid_int = int(audio_formid_str, 16) if audio_formid_str != "0x000000" else 0

    # ==========================================================
    # COMPILE JSON PAYLOAD (NATIVE PAPYRUSUTIL SCHEMA)
    # ==========================================================
    final_output = {
        "string": {
            "intent": intent_name,
            "sentiment": sentiment_name,
            "target_plugin": target_plugin,
            "target_name": target_name,
            "status": response_status,
            "tactical_mode": tactical_mode 
        },
        "int": {
            "target_formid": target_formid_int,
            "sentiment_shift": sentiment_shift,
            "audio_formid": audio_formid_int 
        }
    }
    
    print(f"[API Response] Intent: {intent_name} | Audio FormID: {audio_formid_str} | Affection Shift: {sentiment_shift}")
             
    return final_output

if __name__ == "__main__":
    # Exposing the API to the public internet for Edge Client access
    uvicorn.run(app, host="0.0.0.0", port=8000)