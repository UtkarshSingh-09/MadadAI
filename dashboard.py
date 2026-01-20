import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.http import models 
import time
import json
import os
import datetime
from cryptography.fernet import Fernet
import base64
import folium
from folium.plugins import HeatMap, Fullscreen, MousePosition, MarkerCluster
from streamlit_folium import st_folium
import numpy as np

# --- LIBRARY CHECK ---
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    st.error("❌ Critical Error: AI Model Missing. Run: pip install sentence-transformers")
    st.stop()

ST_CONFIG = {
    "page_title": "MadadAI Command",
    "page_icon": "⛑️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}
st.set_page_config(**ST_CONFIG)

# 🛑 CLOUD KEYS
QDRANT_URL = "https://cb126147-b536-4963-bc80-5df16489d030.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.sWewvcj7k-GdQhPioomFrjtkVcJA9XjmEM4Bpd4CVCk"
COLLECTION_NAME = "disaster_reports"
DOWNLINK_COLLECTION = "courier_bag"

st.markdown("""
    <style>
    .stApp, .stMarkdown, p, div, span { color: #e0e0e0 !important; }
    h1, h2, h3, h4, h5, h6 { color: #ffffff !important; }
    h1 { color: #FF4B4B !important; }
    .report-card { background: #1e2126; border: 1px solid #444; padding: 15px; margin-bottom: 10px; border-radius: 8px; }
    .critical { border-left: 5px solid #ff2b2b; }
    .warning { border-left: 5px solid #ffa500; }
    .safe { border-left: 5px solid #00ff00; }
    </style>
""", unsafe_allow_html=True)

if not os.path.exists("secret.key"):
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file: key_file.write(key)
with open("secret.key", "rb") as k: cipher = Fernet(k.read())

@st.cache_resource
def load_ai_brain(): return SentenceTransformer('all-MiniLM-L6-v2')
ai_model = load_ai_brain()

try: client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY)
except: st.stop()

@st.cache_data(ttl=15)
def fetch_intelligence(min_score_threshold=0.0):
    if not client.collection_exists(COLLECTION_NAME): return []
    try:
        raw = client.scroll(collection_name=COLLECTION_NAME, limit=100, with_payload=True)[0]
        processed = []
        crit_concepts = ["Medical", "Trapped", "Fire", "Bleeding", "Collapse"]
        if ai_model: crit_embeds = ai_model.encode(crit_concepts, convert_to_tensor=True)

        for p in raw:
            try:
                enc = p.payload.get("secure_content")
                if not enc: continue
                dec = json.loads(cipher.decrypt(enc.encode()).decode())
                
                urgency = 0.0
                if ai_model:
                    msg_embed = ai_model.encode(dec.get("text", "Info"), convert_to_tensor=True)
                    scores = util.cos_sim(msg_embed, crit_embeds)
                    urgency = float(scores.max())

                if urgency < min_score_threshold: continue

                processed.append({
                    "id": p.payload.get("id"),
                    "text": dec.get("text", "No Content"),
                    "img": dec.get("image"),   
                    "audio": dec.get("audio"), 
                    "lat": p.payload.get("location", [28.61, 77.20])[0],
                    "lon": p.payload.get("location", [28.61, 77.20])[1],
                    "time": p.payload.get("timestamp", time.time()),
                    "score": urgency
                })
            except: continue
        return sorted(processed, key=lambda x: x['score'], reverse=True)
    except: return []

with st.sidebar:
    st.title("MadadAI 1.0")
    min_urgency = st.slider("Urgency Threshold", 0.0, 1.0, 0.1, 0.1)
    auto_refresh = st.toggle("Live Stream Mode", value=True)

data = fetch_intelligence(min_urgency)

c1, c2, c3, c4 = st.columns(4)
c1.metric("🆘 Active SOS", len(data))
c2.metric("🚨 Critical", sum(1 for d in data if d['score'] > 0.6))
c3.metric("🧠 AI Engine", "ACTIVE")
c4.metric("🕒 Last Sync", datetime.datetime.now().strftime("%H:%M:%S"))
st.markdown("---")

col_map, col_feed = st.columns([1.8, 1])

with col_map:
    if data:
        avg_lat = np.mean([d['lat'] for d in data])
        avg_lon = np.mean([d['lon'] for d in data])
        m = folium.Map([avg_lat, avg_lon], zoom_start=15, tiles="CartoDB dark_matter")
        HeatMap([[d['lat'], d['lon'], d['score']*15] for d in data], radius=18, blur=12).add_to(m)
        st_folium(m, height=650, use_container_width=True)

with col_feed:
    st.subheader(f"📨 Live Feed ({len(data)})")
    for i, report in enumerate(data):
        score_pct = int(report['score']*100)
        css_class = "critical" if score_pct > 60 else "warning" if score_pct > 30 else "safe"
        icon = "🔴" if score_pct > 60 else "🟠" if score_pct > 30 else "🟢"
        
        st.markdown(f"""
        <div class="report-card {css_class}">
            <div style="display:flex; justify-content:space-between;">
                <span style="font-weight:bold;">{icon} {report['id']}</span>
                <span style="background:#000; padding:2px 6px; border-radius:4px;">{score_pct}%</span>
            </div>
            <div style="margin-top:5px; color:#ccc;">{report['text']}</div>
            <div style="font-size:0.7em; color:#888; text-align:right;">{time.ctime(report['time'])[11:16]}</div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.expander("👉 Response Actions & Media"):
            # --- 🔊 AUDIO PLAYER ---
            if report.get('audio'):
                st.caption("🎙️ Voice Note Received")
                try:
                    audio_bytes = base64.b64decode(report['audio'])
                    st.audio(audio_bytes, format='audio/wav')
                except: st.error("Audio Corrupted")
            
            # --- 📷 IMAGE VIEWER ---
            if report.get('img'):
                st.caption("📷 Damage Assessment")
                try:
                    img_bytes = base64.b64decode(report['img'])
                    st.image(img_bytes, use_container_width=True)
                except: st.error("Image Corrupted")

            # --- 📝 REPLY FORM (UPDATED WITH SELF-HEALING) ---
            with st.form(key=f"cmd_{report['id']}_{report['time']}_{i}"):
                msg = st.text_input("Reply:", placeholder="Sending rescue team...", label_visibility="collapsed")
                if st.form_submit_button("🚀 Send Order"):
                    payload = json.dumps({"target_id": report['id'], "msg": msg, "timestamp": time.time()})
                    enc = cipher.encrypt(payload.encode()).decode()
                    
                    # Define Point
                    point = models.PointStruct(
                        id=int(time.time()*1000),
                        vector=[0.0] * 384,
                        payload={"secure_content": enc, "target_id": report['id']}
                    )

                    try:
                        # 1. Try to Send Normally
                        if not client.collection_exists(DOWNLINK_COLLECTION):
                            client.create_collection(DOWNLINK_COLLECTION, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
                        client.upsert(collection_name=DOWNLINK_COLLECTION, points=[point])
                        st.toast(f"✅ Orders Sent to {report['id']}")
                        
                    except Exception as e:
                        # 2. IF ERROR 400 HAPPENS (Schema Mismatch), FIX IT AUTOMATICALLY
                        if "Wrong input" in str(e) or "Not existing vector" in str(e) or "status" in str(e):
                            st.warning("⚠️ Fixing Cloud Schema... Retrying.")
                            try:
                                client.delete_collection(DOWNLINK_COLLECTION)
                                client.create_collection(DOWNLINK_COLLECTION, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
                                client.upsert(collection_name=DOWNLINK_COLLECTION, points=[point])
                                st.toast(f"✅ Orders Sent (Schema Fixed)")
                            except Exception as e2:
                                st.error(f"Failed after fix: {e2}")
                        else:
                            st.error(f"Failed: {e}")

if auto_refresh:
    time.sleep(10)
    st.rerun()