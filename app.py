import streamlit as st
import json
import time
import os
import base64
import socket
import io
from cryptography.fernet import Fernet
from PIL import Image
from streamlit_js_eval import get_geolocation

# --- SETUP CRYPTO ---
if not os.path.exists("secret.key"):
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file:
        key_file.write(key)

with open("secret.key", "rb") as key_file:
    cipher_suite = Fernet(key_file.read())

# --- CONFIG ---
UDP_PORT = 5005

# --- HELPER: FIND MULE ---
def find_mule(role_needed):
    """Scans for a Mule broadcasting the specific role"""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(3)
        try:
            s.bind(('', UDP_PORT))
        except: return None, None # Port busy

        start_t = time.time()
        while time.time() - start_t < 3:
            try:
                msg, addr = s.recvfrom(1024)
                data = json.loads(msg.decode())
                # Match the specific role (uplink or reply)
                if data.get('role') == role_needed:
                    return data.get('ip'), data.get('port')
            except: pass
    return None, None

# --- UI SETUP ---
st.set_page_config(page_title="ResilientRoute", page_icon="📡", layout="centered", initial_sidebar_state="collapsed")
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div.stButton > button { width: 100%; height: 60px; font-size: 18px; font-weight: bold; border-radius: 12px; margin-top: 10px; }
    div.stButton > button:first-child { border: 2px solid #ff4b4b; }
    .status-badge { padding: 8px 12px; border-radius: 8px; font-weight: bold; margin-right: 5px; font-size: 0.9em; }
    .badge-ok { background-color: #1c83e1; color: white; }
    .badge-warn { background-color: #ffa421; color: black; }
    </style>
""", unsafe_allow_html=True)

st.title("📡 SURVIVOR LINK")

# --- GPS ---
c1, c2 = st.columns([1, 2])
with c1:
    st.caption("SYSTEM STATUS")
    st.markdown('<span class="status-badge badge-ok">🛡️ SECURE</span>', unsafe_allow_html=True)
with c2:
    st.caption("GEOLOCATION")
    loc = get_geolocation()
    lat, lon = (loc['coords']['latitude'], loc['coords']['longitude']) if loc else (28.61, 77.20)
    st.markdown(f'<span class="status-badge badge-ok">✅ GPS LOCKED</span>', unsafe_allow_html=True)
    st.caption(f"{lat:.4f}, {lon:.4f}")

st.markdown("---")

tab1, tab2 = st.tabs(["📝 WRITE REPORT", "📬 INBOX"])

# ==========================================
# TAB 1: UPLINK (SEND SOS)
# ==========================================
with tab1:
    st.write("### 🆘 Send Distress Signal")
    with st.form("sos_form"):
        name = st.text_input("Name / ID", "Survivor-01")
        msg_text = st.text_area("Situation Report", "Structure damaged.")
        c1, c2 = st.columns(2)
        audio_val = c1.audio_input("🎙️ Record Voice")
        img_val = c2.file_uploader("📷 Attach Photo", type=['png', 'jpg'])
        
        if st.form_submit_button("💾 SAVE ENCRYPTED PACKET"):
            # Prepare Media
            audio_str = base64.b64encode(audio_val.read()).decode() if audio_val else None
            img_str = None
            if img_val:
                img = Image.open(img_val).convert("RGB")
                img.thumbnail((800, 800))
                buf = io.BytesIO()
                img.save(buf, format='JPEG')
                img_str = base64.b64encode(buf.getvalue()).decode()

            # Encrypt
            payload = json.dumps({"text": msg_text, "audio": audio_str, "image": img_str})
            secure_payload = cipher_suite.encrypt(payload.encode()).decode()

            # Save
            packet = {
                "id": name, "type": "sos", "location": [lat, lon],
                "timestamp": time.time(), "secure_content": secure_payload
            }
            with open("local_storage.json", "a") as f:
                f.write(json.dumps(packet) + "\n")
            st.toast("Packet Encrypted & Saved!", icon="🔒")

    st.write("#### 📡 Uplink Control")
    if st.button("🚀 BROADCAST SIGNAL (UPLOAD)", type="primary"):
        if not os.path.exists("local_storage.json"):
            st.warning("⚠️ No reports to send.")
        else:
            with st.status("📡 Connecting to Mesh Network...") as status:
                st.write("🔍 Scanning for Mule...")
                ip, port = find_mule("mule_uplink")
                
                if ip:
                    st.write(f"✅ Found Mule at {ip}:{port}")
                    
                    try:
                        with open("local_storage.json", "r") as f:
                            lines = f.readlines()
                        
                        success_count = 0
                        total = len(lines)
                        
                        # --- RETRY LOGIC WITH EXTENDED TIMEOUT ---
                        for idx, line in enumerate(lines):
                            sent = False
                            attempts = 0
                            while not sent and attempts < 3:
                                try:
                                    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                                    s.settimeout(15) # <--- INCREASED TO 15 SECONDS
                                    s.connect((ip, port))
                                    s.sendall(line.encode('utf-8'))
                                    
                                    # Wait for ACK
                                    resp = s.recv(1024)
                                    if b"ACK" in resp:
                                        sent = True
                                        success_count += 1
                                    s.close()
                                except:
                                    attempts += 1
                                    time.sleep(2) # <--- Wait longer between retries
                            
                            if not sent:
                                st.write(f"⚠️ Packet {idx+1} failed after 3 retries.")

                        if success_count > 0:
                            status.update(label=f"✅ Upload Complete ({success_count}/{total})!", state="complete")
                            st.balloons()
                            os.remove("local_storage.json")
                        else:
                            status.update(label="❌ Transfer Failed (Mule busy)", state="error")
                    except Exception as e:
                        status.update(label=f"❌ Error: {e}", state="error")
                else:
                    status.update(label="❌ No Mule Found. Move Closer.", state="error")

# ==========================================
# TAB 2: DOWNLINK (CHECK MAIL)
# ==========================================
with tab2:
    st.write("### 📬 Command Orders")
    mail_id = st.text_input("Receiver ID:", value=name)

    if st.button(f"🔄 CHECK MAIL"):
        st.toast("Scanning for Reply Mule...", icon="📡")
        ip, port = find_mule("mule_reply")

        if ip:
            try:
                # --- RETRY LOGIC FOR MAIL ---
                data = b""
                attempts = 0
                connected = False
                
                while not connected and attempts < 3:
                    try:
                        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        s.settimeout(15) # <--- INCREASED TO 15 SECONDS
                        s.connect((ip, port))
                        s.sendall(f"GET_MAIL:{mail_id}".encode())
                        
                        while True:
                            chunk = s.recv(4096)
                            if not chunk: break
                            data += chunk
                        s.close()
                        connected = True
                    except:
                        attempts += 1
                        time.sleep(2)

                if data:
                    orders = json.loads(data.decode())
                    if orders:
                        st.success(f"📨 {len(orders)} New Orders!")
                        for o in orders:
                            try:
                                decrypted = cipher_suite.decrypt(o['secure_content'].encode()).decode()
                                content = json.loads(decrypted)
                                st.info(f"**HQ:** {content.get('msg')}")
                            except: st.error("⚠️ Decryption Failed")
                    else:
                        st.info("📭 No mail found.")
                else:
                    st.error("❌ Failed to connect to Mule.")
            except Exception as e:
                st.error(f"❌ Connection Error: {e}")
        else:
            st.warning("⚠️ No 'Reply Mule' found nearby.")