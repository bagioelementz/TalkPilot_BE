import streamlit as st
import os
import json
import time
import glob
import datetime
from bland_call_agent import dispatch_call, get_call_details, save_call_data

# Page configurations
st.set_page_config(
    page_title="Bland AI Call Hub",
    page_icon="📞",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Glassmorphic Styling
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap');

/* Main Background */
.stApp {
    background: radial-gradient(circle at top right, #1a162b, #0c0b13);
    font-family: 'Outfit', sans-serif;
    color: #f3f4f6;
}

/* Titles and Headers */
.gradient-text {
    background: linear-gradient(135deg, #a78bfa 0%, #6366f1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-weight: 800;
    font-size: 2.8rem;
    margin-bottom: 0.2rem;
    letter-spacing: -0.05em;
}

.subtitle-text {
    color: #9ca3af;
    font-size: 1.1rem;
    margin-bottom: 2rem;
}

/* Glassmorphism Card styling */
.glass-card {
    background: rgba(255, 255, 255, 0.03);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
    margin-bottom: 20px;
}

.glass-header {
    font-size: 1.4rem;
    font-weight: 600;
    color: #ffffff;
    margin-bottom: 15px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    padding-bottom: 8px;
}

/* Custom Badges */
.badge {
    display: inline-block;
    padding: 4px 10px;
    border-radius: 9999px;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.badge-completed {
    background-color: rgba(16, 185, 129, 0.15);
    color: #10b981;
    border: 1px solid rgba(16, 185, 129, 0.3);
}

.badge-failed {
    background-color: rgba(239, 68, 68, 0.15);
    color: #ef4444;
    border: 1px solid rgba(239, 68, 68, 0.3);
}

.badge-progress {
    background-color: rgba(245, 158, 11, 0.15);
    color: #f59e0b;
    border: 1px solid rgba(245, 158, 11, 0.3);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0% { opacity: 0.6; }
    50% { opacity: 1; }
    100% { opacity: 0.6; }
}

/* Button overrides */
div.stButton > button {
    background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%) !important;
    color: white !important;
    border: none !important;
    padding: 10px 24px !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    transition: all 0.3s ease !important;
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.4) !important;
}

div.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.6) !important;
}

/* Styling native Streamlit inputs to look glassy */
.stTextInput input, .stTextArea textarea, .stSelectbox select {
    background-color: rgba(255, 255, 255, 0.02) !important;
    border: 1px solid rgba(255, 255, 255, 0.07) !important;
    color: #f3f4f6 !important;
    border-radius: 8px !important;
}

.stTextInput input:focus, .stTextArea textarea:focus {
    border-color: #6366f1 !important;
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.2) !important;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.01);
}
::-webkit-scrollbar-thumb {
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}
::-webkit-scrollbar-thumb:hover {
    background: rgba(255, 255, 255, 0.2);
}
</style>
""", unsafe_allow_html=True)

# Initialize Session States
if "active_call_id" not in st.session_state:
    st.session_state.active_call_id = None
if "polling_active" not in st.session_state:
    st.session_state.polling_active = False
if "call_status" not in st.session_state:
    st.session_state.call_status = ""
if "storage_dir" not in st.session_state:
    st.session_state.storage_dir = "storage"

if "call_purpose" not in st.session_state:
    st.session_state.call_purpose = "Bilingual outbound plumbing service request coordination (German/English)."
if "first_sentence_val" not in st.session_state:
    st.session_state.first_sentence_val = "Hallo! Hier spricht Avira von TaskMeister. Ich hoffe, Sie haben einen schönen Tag. Ich rufe bezüglich einer Klempner-Serviceanfrage in Berlin an. Hätten Sie kurz einen Moment Zeit?"
if "task_prompt_val" not in st.session_state:
    st.session_state.task_prompt_val = """You are calling about a plumbing service request. Always start in German. If the callee responds in German, continue in German. If they respond in English, switch to English.

--- GERMAN CONVERSATION FLOW ---
Unser Kunde Sam benötigt Hilfe bei einem undichten Rohr in seiner Küche. Der Service wird bis nächsten Montag um 10:00 Uhr benötigt, und das geschätzte Budget beträgt ca. 600 €.

Wären Sie verfügbar und interessiert, diesen Auftrag zu übernehmen?

Bei Interesse:
Großartig. Könnten Sie mir kurz Ihre Verfügbarkeit und eventuelle Anforderungen mitteilen, bevor ich Ihre Daten an den Kunden weitergebe?

Bei Nichtverfügbarkeit:
Kein Problem. Vielen Dank für Ihre Zeit. Einen schönen Tag noch.

Bei Rückfragen:
Gerne helfe ich weiter. Es handelt sich um ein undichtes Küchenrohr in Berlin, der Service wird bis nächsten Montag um 10:00 Uhr benötigt, und das geschätzte Budget beträgt ca. 600 €.

--- ENGLISH CONVERSATION FLOW ---
Our client, Sam, needs help with a leaking pipe in their kitchen. The service is needed by next Monday at 10:00 AM, and the estimated budget is around €600.

Would you be available and interested in taking on this job?

If interested:
Great. Could you briefly tell me about your availability and any requirements before I share your details with the client?

If unavailable:
No problem. Thank you for your time. Have a great day.

If the provider asks for more details:
I'd be happy to help. The request is for a leaking kitchen pipe in Berlin, with service needed by next Monday at 10:00 AM and an estimated budget of €600."""



# Sidebar Settings
with st.sidebar:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("⚙️ Settings")
    storage_dir_input = st.text_input("Storage Directory", value="storage")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.session_state.storage_dir = storage_dir_input
        
    st.markdown("---")
    st.markdown("### Summary Info")
    # Quick count of stored files
    os.makedirs(st.session_state.storage_dir, exist_ok=True)
    stored_count = len(glob.glob(os.path.join(st.session_state.storage_dir, "call_*.json")))
    st.write(f"📁 **Transcripts in vault:** {stored_count}")

# Load saved call logs
def load_saved_calls(storage_dir):
    calls = []
    if not os.path.exists(storage_dir):
        return calls
    
    files = glob.glob(os.path.join(storage_dir, "call_*.json"))
    for file_path in files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                call_id = data.get("call_id")
                created_at = data.get("created_at", "")
                to = data.get("to") or data.get("phone_number") or "Unknown"
                length = data.get("call_length", 0)
                summary = data.get("summary", "No summary")
                
                # Setup sorting date
                sort_time = created_at
                try:
                    if created_at:
                        clean_time = created_at.split('.')[0].replace('Z', '').split('+')[0]
                        sort_time = datetime.datetime.strptime(clean_time, "%Y-%m-%dT%H:%M:%S")
                except Exception:
                    pass
                
                calls.append({
                    "file_path": file_path,
                    "call_id": call_id,
                    "created_at": created_at,
                    "sort_time": sort_time,
                    "to": to,
                    "length": length,
                    "summary": summary,
                    "data": data
                })
        except Exception:
            pass
            
    # Sort calls newest first
    calls.sort(key=lambda x: str(x.get("sort_time")), reverse=True)
    return calls

# Header section
st.markdown('<div class="gradient-text">BLAND AI CALL HUB</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle-text">Initiate outbound AI agent voice calls, monitor call status in real-time, and store conversations.</div>', unsafe_allow_html=True)

# Main Dashboard Layout
col1, col2 = st.columns([1, 1.2])

with col1:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown('<div class="glass-header">📞 Dispatch New Call</div>', unsafe_allow_html=True)
    
    phone_number = st.text_input("Recipient Phone Number", placeholder="+14155552620")
    
    first_sentence = st.text_input(
        "First Sentence (Greeting)",
        value=st.session_state.first_sentence_val,
        placeholder="Enter outbound greeting spoken by the agent..."
    )
    
    task_prompt = st.text_area(
        "Agent Persona & Instructions",
        height=200,
        placeholder="E.g., You are calling a client on behalf of Acme Corp to verify details...",
        value=st.session_state.task_prompt_val
    )
    
    voice_option = st.selectbox(
        "Voice Model",
        ["karl (German - Professional)", "june (Female - Warm)", "mason (Male - Professional)", "victoria (Female - Direct)", "lucas (Male - Energetic)", "custom"]
    )
    
    voice_id = "a24c43d3-f448-4fea-a498-a9287f7cabf3"
    if voice_option == "custom":
        voice_id = st.text_input("Custom Voice ID / Name", placeholder="e.g. 5e18239...")
    elif voice_option.startswith("karl"):
        voice_id = "a24c43d3-f448-4fea-a498-a9287f7cabf3"
    else:
        voice_id = voice_option.split(" ")[0]
        
    st.markdown("<br>", unsafe_allow_html=True)
    dispatch_btn = st.button("Initiate Call ⚡")
    st.markdown('</div>', unsafe_allow_html=True)
    
    if dispatch_btn:
        if not phone_number:
            st.error("Please enter a valid phone number.")
        elif not task_prompt:
            st.error("Please enter instructions for the agent.")
        else:
            with st.spinner("Initiating connection..."):
                res = dispatch_call(phone_number, task_prompt, voice_id, first_sentence=first_sentence)
                if res.get("status") == "error":
                    st.error(f"Failed to dispatch: {res.get('message')}")
                elif "call_id" in res:
                    st.session_state.active_call_id = res["call_id"]
                    st.session_state.polling_active = True
                    st.session_state.call_status = "queued"
                    st.success(f"Call successfully queued! ID: {res['call_id']}")
                    st.rerun()
                else:
                    st.error(f"Unexpected response: {res}")

with col2:
    # Check if we are actively polling a call
    if st.session_state.polling_active and st.session_state.active_call_id:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="glass-header">⚡ Live Call Monitoring</div>', unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="background: rgba(99, 102, 241, 0.05); border: 1px solid rgba(99, 102, 241, 0.2); border-radius: 12px; padding: 20px; text-align: center; margin-bottom: 20px;">
            <div style="font-size: 3rem; margin-bottom: 10px;">📞</div>
            <div style="font-weight: 600; font-size: 1.1rem; color: #a78bfa;">Call in Progress</div>
            <div style="font-family: monospace; font-size: 0.85rem; color: #9ca3af; margin: 8px 0;">ID: {st.session_state.active_call_id}</div>
            <div style="margin-top: 15px;">
                <span class="badge badge-progress">Status: {st.session_state.call_status.upper()}</span>
            </div>
            <p style="font-size: 0.85rem; color: #9ca3af; margin-top: 15px;">We are polling the Bland AI API to monitor connection status and download the transcript as soon as the call ends.</p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("Stop Live Tracking"):
            st.session_state.polling_active = False
            st.session_state.active_call_id = None
            st.warning("Stopped live tracking. You can retrieve the call data later using its Call ID.")
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Executing the Polling Loop step
        call_id = st.session_state.active_call_id
        
        with st.spinner("Polling status from Bland AI..."):
            time.sleep(3.5)
            details = get_call_details(call_id)
            
            if details.get("status") == "error":
                st.error(f"Error fetching call details: {details.get('message')}")
                st.session_state.polling_active = False
                st.session_state.active_call_id = None
            else:
                completed = details.get("completed", False)
                queue_status = details.get("queue_status", "")
                
                # Check for completion states
                if completed or queue_status in ["completed", "failed", "no-answer", "busy"]:
                    save_call_data(call_id, details, storage_dir=st.session_state.storage_dir)
                    st.session_state.polling_active = False
                    st.session_state.active_call_id = None
                    st.success("🎉 Call finished! Transcript captured and stored successfully.")
                    st.balloons()
                    st.rerun()
                else:
                    st.session_state.call_status = queue_status or "in-progress"
                    st.rerun()
    else:
        # History Transcripts Vault Dashboard
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown('<div class="glass-header">📂 Transcript Vault</div>', unsafe_allow_html=True)
        
        tab_vault, tab_retrieve = st.tabs(["Browse Vault", "Manual Import"])
        
        with tab_vault:
            saved_calls = load_saved_calls(st.session_state.storage_dir)
            
            if not saved_calls:
                st.info("No saved call transcripts found in storage. Dispatched calls will automatically be saved here.")
            else:
                search_query = st.text_input("🔍 Search History", placeholder="Search by number, summary or transcript...")
                
                filtered_calls = []
                for call in saved_calls:
                    call_data = call["data"]
                    text_to_search = (
                        str(call.get("to", "")) + " " +
                        str(call.get("summary", "")) + " " +
                        str(call_data.get("concatenated_transcript", "")) + " " +
                        str(call.get("call_id", ""))
                    ).lower()
                    
                    if not search_query or search_query.lower() in text_to_search:
                        filtered_calls.append(call)
                        
                if not filtered_calls:
                    st.warning("No matches found for your search query.")
                else:
                    call_options = [
                        f"{c['to']} | {c['created_at'].split('.')[0].replace('T', ' ') if c['created_at'] else 'N/A'} | ID: {c['call_id'][:8]}..."
                        for c in filtered_calls
                    ]
                    
                    selected_idx = st.selectbox(
                        "Select a call record to view details:",
                        range(len(filtered_calls)),
                        format_func=lambda i: call_options[i]
                    )
                    
                    selected_call = filtered_calls[selected_idx]
                    sc_data = selected_call["data"]
                    
                    st.markdown("---")
                    
                    col_details_1, col_details_2 = st.columns(2)
                    with col_details_1:
                        st.markdown(f"**Call ID:** `{selected_call['call_id']}`")
                        st.markdown(f"**Recipient:** `{selected_call['to']}`")
                        st.markdown(f"**Date/Time:** `{selected_call['created_at']}`")
                    with col_details_2:
                        duration = sc_data.get("call_length", 0)
                        st.markdown(f"**Duration:** `{duration} mins`")
                        st.markdown(f"**Answered By:** `{sc_data.get('answered_by', 'N/A')}`")
                        
                        comp = sc_data.get("completed", True)
                        if comp:
                            st.markdown('**Status:** <span class="badge badge-completed">COMPLETED</span>', unsafe_allow_html=True)
                        else:
                            st.markdown('**Status:** <span class="badge badge-failed">FAILED / INCOMPLETE</span>', unsafe_allow_html=True)
                    
                    # AI Summary Display
                    summary_text = sc_data.get("summary") or "No AI summary generated."
                    st.markdown(f"""
                    <div style="background: rgba(255, 255, 255, 0.02); border-left: 4px solid #6366f1; padding: 12px 16px; border-radius: 4px; margin: 15px 0;">
                        <div style="font-weight: 600; font-size: 0.9rem; text-transform: uppercase; color: #a78bfa; margin-bottom: 5px;">AI Summary</div>
                        <div style="font-size: 0.9rem; color: #d1d5db; line-height: 1.4;">{summary_text}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    # Transcript Dialog Bubble View
                    st.markdown("**Conversation Transcript:**")
                    transcripts = sc_data.get('transcripts', [])
                    
                    # Parse from concatenated_transcript if needed
                    if not transcripts and sc_data.get('concatenated_transcript'):
                        lines = sc_data['concatenated_transcript'].split('\n')
                        for line in lines:
                            if ':' in line:
                                parts = line.split(':', 1)
                                speaker = parts[0].strip().lower()
                                text = parts[1].strip()
                                transcripts.append({'user': speaker, 'text': text})
                                
                    if transcripts:
                        html_str = '<div style="display: flex; flex-direction: column; gap: 12px; margin-top: 15px;">'
                        for entry in transcripts:
                            speaker = entry.get('user', 'unknown')
                            text = entry.get('text', '')
                            is_agent = speaker in ['assistant', 'agent']
                            
                            bubble_style = "background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%); color: #ffffff; align-self: flex-start; border-bottom-left-radius: 4px;" if is_agent else "background: rgba(255, 255, 255, 0.08); color: #f3f4f6; align-self: flex-end; border-bottom-right-radius: 4px; border: 1px solid rgba(255, 255, 255, 0.05);"
                            sender_name = "Agent" if is_agent else "User"
                            
                            html_str += f'<div style="padding: 12px 16px; border-radius: 16px; max-width: 75%; line-height: 1.5; font-size: 0.95rem; box-shadow: 0 4px 12px rgba(0,0,0,0.15); {bubble_style}"><div style="font-size: 0.75rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px; opacity: 0.8;">{sender_name}</div>{text}</div>'
                        html_str += '</div>'
                        st.markdown(html_str, unsafe_allow_html=True)
                    else:
                        st.info("No detailed transcript turns available.")
                        
        with tab_retrieve:
            st.markdown("### Import Call Manually")
            st.write("Archive a call details record by specifying its Call ID directly.")
            manual_call_id = st.text_input("Enter Call ID", placeholder="e.g. 12345678-abcd-1234-abcd-1234567890ab")
            fetch_btn = st.button("Fetch & Archive 📥")
            
            if fetch_btn:
                if not manual_call_id:
                    st.error("Please enter a valid call ID.")
                else:
                    with st.spinner("Fetching from Bland AI..."):
                        details = get_call_details(manual_call_id)
                        if details.get("status") == "error":
                            st.error(f"Failed to fetch call details: {details.get('message')}")
                        else:
                            save_call_data(manual_call_id, details, storage_dir=st.session_state.storage_dir)
                            st.success("🎉 Call transcript successfully retrieved and archived!")
                            st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
