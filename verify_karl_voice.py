import os
import json
from dotenv import load_dotenv
from bland_call_agent import list_inbound_numbers, update_inbound_number, dispatch_call, KARL_VOICE_ID, KARL_GERMAN_RULES

def main():
    load_dotenv()
    api_key = os.getenv("BLAND_API_KEY")
    if not api_key:
        print("[-] Error: BLAND_API_KEY not found in .env file.")
        return

    print("=== Bland AI Voice Configuration Verification ===")
    print(f"Target Voice ID (Karl): {KARL_VOICE_ID}")
    print("\n--- 1. Checking Outbound Defaults ---")
    print(f"Default Voice ID in code: {KARL_VOICE_ID}")
    print("Default System Rules / Persona:")
    print(KARL_GERMAN_RULES)
    print("Default Greeting / First Sentence:")
    print("Hallo! Hier spricht Avira von TaskMeister. Ich hoffe, Sie haben einen schönen Tag. Ich rufe bezüglich einer Klempner-Serviceanfrage in Berlin an. Hätten Sie kurz einen Moment Zeit?")

    print("\n--- 2. Checking Inbound Numbers from Bland AI API ---")
    inbound_res = list_inbound_numbers(api_key)
    if "status" in inbound_res and inbound_res["status"] == "error":
        print(f"[-] Error listing inbound numbers: {inbound_res.get('message')}")
    else:
        inbound_numbers = inbound_res.get("inbound_numbers", [])
        print(f"[+] Found {len(inbound_numbers)} registered inbound number(s) on the account.")
        
        for idx, num_info in enumerate(inbound_numbers, 1):
            phone = num_info.get("phone_number")
            voice = num_info.get("voice")
            prompt = num_info.get("prompt", "")
            first_sentence = num_info.get("first_sentence", "")
            prompt_str = prompt or ""
            print(f"\nNumber #{idx}: {phone}")
            print(f"  Current Voice ID: {voice}")
            print(f"  Current Greeting: '{first_sentence}'")
            print(f"  Prompt contains German Rules: {('Always speak German' in prompt_str or 'Karl' in prompt_str or 'German-speaking' in prompt_str)}")
            
            # Check if voice is correct, if not, update it
            if voice != KARL_VOICE_ID:
                print(f"  [!] Voice mismatch. Updating configuration for {phone} to use Karl...")
                update_res = update_inbound_number(phone_number=phone, api_key=api_key)
                if "status" in update_res and update_res["status"] == "error":
                    print(f"  [-] Failed to update {phone}: {update_res.get('message')}")
                else:
                    print(f"  [+] Successfully updated {phone} configuration.")
            else:
                print(f"  [+] Configuration is already correct (uses Karl).")

    print("\n=============================================")

if __name__ == "__main__":
    main()
