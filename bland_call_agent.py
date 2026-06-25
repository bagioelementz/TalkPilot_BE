import os
import json
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BLAND_API_KEY = os.getenv("BLAND_API_KEY")
API_URL = "https://api.bland.ai/v1"

def get_headers(api_key=None):
    key = api_key or BLAND_API_KEY
    return {
        "authorization": key,
        "Content-Type": "application/json"
    }

KARL_VOICE_ID = "a24c43d3-f448-4fea-a498-a9287f7cabf3"

KARL_GERMAN_RULES = """You are Avira, a polite, professional, and friendly representative from TaskMeister.

IMPORTANT RULES:
- You are fully bilingual (German and English). You MUST always start the conversation in German.
- After your German greeting, listen carefully to the callee's response and detect their language.
- If the callee responds in German, continue the ENTIRE conversation in fluent German. Understand their German fully and respond naturally in German.
- If the callee responds in English, immediately switch to English and continue the ENTIRE conversation in fluent English.
- Never mix languages mid-sentence. Once the callee's language is established, stick with it consistently.
- Use natural, fluent, and polite language in whichever language you are speaking.
- Speak clearly and at a moderate pace suitable for phone conversations.
- Keep responses concise and conversational.
- Ask clarifying questions when needed.
- Be friendly, professional, and helpful.

OUTBOUND GREETING (always in German):
"Hallo! Hier spricht Avira von TaskMeister. Ich hoffe, Sie haben einen schönen Tag. Ich rufe bezüglich einer Klempner-Serviceanfrage in Berlin an. Hätten Sie kurz einen Moment Zeit?"

INBOUND GREETING (German):
"Guten Tag! Vielen Dank für Ihren Anruf. Wie kann ich Ihnen heute helfen?"

CONVERSATION ENDING (German):
"Vielen Dank für Ihre Zeit und einen schönen Tag noch. Auf Wiederhören."

CONVERSATION ENDING (English):
"Thank you for your time and have a nice day. Goodbye." """

def dispatch_call(phone_number: str, task: str, voice: str = KARL_VOICE_ID, first_sentence: str = None, api_key: str = None) -> dict:
    """
    Dispatches an AI call via Bland AI.
    """
    url = f"{API_URL}/calls"
    headers = get_headers(api_key)
    
    # Default to German outbound greeting (agent always greets in German first)
    if first_sentence is None:
        first_sentence = "Hallo! Hier spricht Avira von TaskMeister. Ich hoffe, Sie haben einen schönen Tag. Ich rufe bezüglich einer Klempner-Serviceanfrage in Berlin an. Hätten Sie kurz einen Moment Zeit?"
            
    # Augment specific instructions with Karl's professional German rules and behavior
    augmented_task = f"{KARL_GERMAN_RULES}\n\nSPECIFIC CALL INSTRUCTIONS & CONTEXT:\n{task}"
    
    # Handle the mapping of 'karl' name to the voice_id
    if voice == "karl":
        voice = KARL_VOICE_ID

    payload = {
        "phone_number": phone_number,
        "task": augmented_task,
        "voice": voice,
        "language": "fluent",
        "record": False,
        "wait": False,
        "first_sentence": first_sentence,
        "speed": 0.88,  # Slower speed for a natural, unhurried human pace
        "temperature": 0.6  # Natural variation in speech generation
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        try:
            err_data = response.json()
            return {"status": "error", "message": err_data.get("message") or err_data.get("error") or str(e)}
        except Exception:
            return {"status": "error", "message": str(e)}

def list_inbound_numbers(api_key: str = None) -> dict:
    """
    Lists all inbound numbers associated with the Bland AI account.
    """
    url = f"{API_URL}/inbound"
    headers = get_headers(api_key)
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        try:
            err_data = response.json()
            return {"status": "error", "message": err_data.get("message") or err_data.get("error") or str(e)}
        except Exception:
            return {"status": "error", "message": str(e)}

def update_inbound_number(phone_number: str, prompt: str = KARL_GERMAN_RULES, voice: str = "a24c43d3-f448-4fea-a498-a9287f7cabf3", first_sentence: str = "Guten Tag! Vielen Dank für Ihren Anruf. Wie kann ich Ihnen heute helfen?", api_key: str = None) -> dict:
    """
    Configures an inbound number to use a specific prompt, voice, and first sentence on Bland AI.
    """
    clean_num = phone_number.strip().replace(" ", "")
    url = f"{API_URL}/inbound/{clean_num}"
    headers = get_headers(api_key)
    payload = {
        "prompt": prompt,
        "voice": voice,
        "first_sentence": first_sentence
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        try:
            err_data = response.json()
            return {"status": "error", "message": err_data.get("message") or err_data.get("error") or str(e)}
        except Exception:
            return {"status": "error", "message": str(e)}

def get_call_details(call_id: str, api_key: str = None) -> dict:
    """
    Retrieves the metadata, status, summary, and transcript for a specific call_id.
    """
    url = f"{API_URL}/calls/{call_id}"
    headers = get_headers(api_key)
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        try:
            err_data = response.json()
            return {"status": "error", "message": err_data.get("message") or err_data.get("error") or str(e)}
        except Exception:
            return {"status": "error", "message": str(e)}

def stop_call(call_id: str, api_key: str = None) -> dict:
    """
    Stops an active Bland AI call by call_id.
    """
    url = f"{API_URL}/calls/{call_id}/stop"
    headers = get_headers(api_key)

    try:
        response = requests.post(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        try:
            err_data = response.json()
            return {"status": "error", "message": err_data.get("message") or err_data.get("error") or str(e)}
        except Exception:
            return {"status": "error", "message": str(e)}

def save_call_data(call_id: str, call_data: dict, storage_dir: str = "storage") -> tuple:
    """
    Saves the call details JSON and formatted text transcript to the storage folder.
    Returns (json_path, txt_path)
    """
    os.makedirs(storage_dir, exist_ok=True)
    
    json_path = os.path.join(storage_dir, f"call_{call_id}.json")
    txt_path = os.path.join(storage_dir, f"call_{call_id}_transcript.txt")
    
    # Save the raw JSON data
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(call_data, f, indent=4, ensure_ascii=False)
        
    # Generate and save formatted transcript
    with open(txt_path, 'w', encoding='utf-8') as f:
        f.write(f"=== CALL TRANSCRIPT ===\n")
        f.write(f"Call ID: {call_id}\n")
        f.write(f"To: {call_data.get('to', 'N/A')}\n")
        f.write(f"Date: {call_data.get('created_at', 'N/A')}\n")
        f.write(f"Duration: {call_data.get('call_length', 0)} mins\n")
        f.write(f"Summary: {call_data.get('summary', 'No summary available.')}\n")
        f.write(f"========================\n\n")
        
        # Check for different transcript representations
        transcripts = call_data.get('transcripts')
        concatenated = call_data.get('concatenated_transcript')
        
        if transcripts and isinstance(transcripts, list):
            for entry in transcripts:
                speaker = entry.get('user', 'unknown').capitalize()
                text = entry.get('text', '')
                f.write(f"{speaker}: {text}\n")
        elif concatenated:
            f.write(concatenated)
        else:
            f.write("No transcript contents available yet.")
            
    return json_path, txt_path
