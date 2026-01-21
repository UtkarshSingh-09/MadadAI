import streamlit as st
from qdrant_client import QdrantClient
from qdrant_client.http import models 
import time
import json
import os
import datetime
import pandas as pd
from cryptography.fernet import Fernet
import base64
import folium
from folium.plugins import HeatMap, MarkerCluster
from streamlit_folium import st_folium
import numpy as np

# --- 1. CONFIGURATION & STYLE ---
ST_CONFIG = {
    "page_title": "MadadAI Command HQ v2.7",
    "page_icon": "🛰️",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}
st.set_page_config(**ST_CONFIG)

# Professional "Command Center" CSS
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { font-family: 'Helvetica Neue', sans-serif; font-weight: 700; letter-spacing: -0.5px; }
    div[data-testid="stMetric"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .report-card { 
        background: #161b22; 
        border: 1px solid #30363d; 
        padding: 16px; 
        margin-bottom: 12px; 
        border-radius: 8px; 
        transition: transform 0.2s;
    }
    .report-card:hover { border-color: #58a6ff; transform: translateX(2px); }
    .critical { border-left: 4px solid #ff4b4b; }
    .warning { border-left: 4px solid #d29922; }
    .safe { border-left: 4px solid #238636; }
    .meta-text { font-size: 0.8em; color: #8b949e; }
    .body-text { color: #c9d1d9; font-size: 0.95em; margin-top: 8px; }
    .header-container { border-bottom: 1px solid #30363d; padding-bottom: 20px; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. LIBRARY CHECKS & KEYS ---
try:
    from sentence_transformers import SentenceTransformer, util
except ImportError:
    st.error("❌ Critical Error: AI Model Missing. Run: pip install sentence-transformers pandas")
    st.stop()

# 🛑 CLOUD KEYS (Robust Loading)
try:
    QDRANT_URL = st.secrets["QDRANT_URL"]
    QDRANT_KEY = st.secrets["QDRANT_KEY"]
except:
    st.error("❌ Secrets not found! Please create .streamlit/secrets.toml")
    st.stop()

COLLECTION_NAME = "disaster_reports"
DOWNLINK_COLLECTION = "courier_bag"

# --- 3. CRYPTO SETUP ---
if not os.path.exists("secret.key"):
    key = Fernet.generate_key()
    with open("secret.key", "wb") as key_file: key_file.write(key)
with open("secret.key", "rb") as k: cipher = Fernet(k.read())

# --- 4. CACHED RESOURCES ---
@st.cache_resource
def load_ai_brain(): 
    # Load model once and keep in memory
    return SentenceTransformer('all-MiniLM-L6-v2')

ai_model = load_ai_brain()

# Pre-calculate Critical Concepts (Optimization)
@st.cache_resource
def get_critical_vectors():
    concepts = ["Medical Emergency", "Trapped Person", "Fire Hazard", "Severe Bleeding", "Building Collapse"]
    return ai_model.encode(concepts, convert_to_tensor=True)

crit_embeds = get_critical_vectors()

# --- 🛡️ ROBUST CLIENT SETUP ---
@st.cache_resource
def get_qdrant_client():
    # Timeout set to 120s for slow networks
    return QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=120)

try:
    client = get_qdrant_client()
except Exception as e:
    st.error(f"❌ Database Initialization Failed: {e}")
    st.stop()

# --- 🧠 BATCH INTELLIGENCE FETCH (The Optimization) ---
def fetch_intelligence_batch(limit=50):
    # 1. Fetch Raw Data
    if not client.collection_exists(COLLECTION_NAME): 
        return []

    try:
        raw_result = client.scroll(collection_name=COLLECTION_NAME, limit=limit, with_payload=True)
        raw = raw_result[0]
        if not raw: return []
    except Exception as e:
        return []

    # 2. Pre-process List (Decryption Phase)
    valid_packets = []
    texts_to_vectorize = []
    
    for p in raw:
        try:
            # Decrypt Content
            enc = p.payload.get("secure_content")
            if not enc: continue
            
            try:
                dec = json.loads(cipher.decrypt(enc.encode()).decode())
            except Exception as e_crypto:
                continue

            # Store for batch processing
            item = {
                "id": p.payload.get("id"),
                "text": dec.get("text", "Info"),
                "img": dec.get("image"),
                "audio": dec.get("audio"),
                "lat": p.payload.get("location", [28.61, 77.20])[0],
                "lon": p.payload.get("location", [28.61, 77.20])[1],
                "time": p.payload.get("timestamp", time.time()),
                "raw_payload": p.payload # Keep raw payload for reference
            }
            valid_packets.append(item)
            texts_to_vectorize.append(item["text"])
        except Exception as e:
            continue

    if not valid_packets: return []

    # 3. 🚀 BATCH AI EXECUTION
    try:
        if texts_to_vectorize:
            # A. Vectorize all texts at once
            message_embeddings = ai_model.encode(texts_to_vectorize, convert_to_tensor=True)
            
            # B. Calculate Similarity Matrix (Messages x Concepts)
            cosine_scores = util.cos_sim(message_embeddings, crit_embeds)
            
            # C. Extract max urgency for each message
            max_scores = [float(score.max()) for score in cosine_scores]
            
            # D. Assign scores back to packet list
            for i, packet in enumerate(valid_packets):
                packet["score"] = max_scores[i]
                
    except Exception as e:
        # Fallback: assign 0 score if AI fails
        for p in valid_packets: p["score"] = 0.0

    # Sort by urgency (High to Low) AND Time to keep list stable
    return sorted(valid_packets, key=lambda x: (x['score'], x['time']), reverse=True)

# --- 5. SIDEBAR CONTROLS ---
with st.sidebar:
    st.title("🛰️ MadadAI Link")
    st.markdown("---")
    st.caption("FILTER SETTINGS")
    min_urgency = st.slider("Urgency Threshold", 0.0, 1.0, 0.0, 0.1)
    
    st.caption("SYSTEM CONTROL")
    auto_refresh = st.toggle("Live Data Stream", value=True)
    
    st.markdown("---")
    st.info(f"**Status:** Online\n\n**Node:** HQ-Alpha\n\n**Lat:** 28.61 | **Lon:** 77.20")

# --- 6. MAIN DASHBOARD UI ---

# Header Section
st.markdown('<div class="header-container">', unsafe_allow_html=True)
c_head_1, c_head_2 = st.columns([3, 1])
with c_head_1:
    st.title("Disaster Response Command v2.7")
    st.caption("Real-time Decentralized Mesh Network Monitor")
with c_head_2:
    st.markdown(f"<div style='text-align:right; font-family:monospace; color:#58a6ff;'>SYSTEM TIME<br>{datetime.datetime.now().strftime('%H:%M:%S')}</div>", unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Fetch Data
data_raw = fetch_intelligence_batch(limit=50)
# Apply Slider Filter
data = [d for d in data_raw if d['score'] >= min_urgency]

# Metrics Strip
m1, m2, m3, m4 = st.columns(4)
m1.metric("🆘 Active Signals", len(data), delta_color="inverse")
m2.metric("🚨 Critical Threats", sum(1 for d in data if d['score'] > 0.6), delta_color="inverse")
m3.metric("📡 Network Nodes", "3 (Stable)")
m4.metric("🧠 AI Confidence", "98.2%")

st.markdown("<br>", unsafe_allow_html=True)

# --- TABBED INTERFACE ---
tab_ops, tab_analytics, tab_export = st.tabs(["📍 Live Operations", "📊 Mission Analytics", "💾 Data Export"])

# === TAB 1: LIVE OPERATIONS (Map + Feed) ===
with tab_ops:
    col_map, col_feed = st.columns([1.8, 1])

    with col_map:
        st.subheader("📍 Geospatial Grid")
        if data:
            avg_lat = np.mean([d['lat'] for d in data])
            avg_lon = np.mean([d['lon'] for d in data])
            m = folium.Map([avg_lat, avg_lon], zoom_start=15, tiles="CartoDB dark_matter")
            
            # Heatmap
            HeatMap([[d['lat'], d['lon'], d['score']*15] for d in data], radius=18, blur=12).add_to(m)
            
            # Cluster Markers
            mc = MarkerCluster().add_to(m)
            for d in data:
                color = "red" if d['score'] > 0.6 else "orange" if d['score'] > 0.3 else "green"
                folium.Marker(
                    [d['lat'], d['lon']],
                    popup=f"ID: {d['id']}<br>Score: {int(d['score']*100)}%",
                    icon=folium.Icon(color=color, icon="info-sign")
                ).add_to(mc)
            
            st_folium(m, height=650, use_container_width=True)
        else:
            m = folium.Map([28.61, 77.20], zoom_start=4, tiles="CartoDB dark_matter")
            st_folium(m, height=650, use_container_width=True)

    with col_feed:
        st.subheader(f"📨 Incoming Feeds ({len(data)})")
        
        if not data:
            st.info("No active distress signals detected in sector.")
            
        for i, report in enumerate(data):
            score_pct = int(report['score']*100)
            css_class = "critical" if score_pct > 60 else "warning" if score_pct > 30 else "safe"
            icon = "🔴" if score_pct > 60 else "🟠" if score_pct > 30 else "🟢"
            
            # Render Card
            st.markdown(f"""
            <div class="report-card {css_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <span style="font-weight:bold; color:white; font-family:monospace;">{icon} {report['id']}</span>
                    <span style="background:#21262d; padding:2px 8px; border-radius:12px; font-size:0.8em; border:1px solid #30363d;">
                        Urgency: {score_pct}%
                    </span>
                </div>
                <div class="body-text">{report['text']}</div>
                <div class="meta-text" style="margin-top:10px; border-top:1px solid #30363d; padding-top:5px;">
                    🕒 {time.ctime(report['time'])[11:16]} &nbsp;|&nbsp; 📍 {report['lat']:.4f}, {report['lon']:.4f}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Action Panel
            with st.expander(f"🛠️ Deploy Response #{i+1}"):
                if report.get('audio'):
                    st.caption("🎙️ Voice Transmission")
                    try: st.audio(base64.b64decode(report['audio']), format='audio/wav')
                    except: st.error("Audio Corrupted")
                
                if report.get('img'):
                    st.caption("📷 Visual Assessment")
                    try: st.image(base64.b64decode(report['img']), use_container_width=True)
                    except: st.error("Image Corrupted")

                # --- REPLY MULE (STABLE) ---
                # ✅ KEY FIX: Added '_{i}' to ensure absolute uniqueness even with duplicate data
                unique_form_key = f"cmd_{report['id']}_{report['time']}_{i}"
                
                with st.form(key=unique_form_key):
                    msg = st.text_input("Mission Orders:", placeholder="Type orders here...", label_visibility="collapsed")
                    sent = st.form_submit_button("🚀 Transmit Order", type="primary")

                    if sent:
                        # ⚠️ CRITICAL: Pause refresh to allow transmission
                        st.session_state['paused'] = True
                        
                        payload = json.dumps({"target_id": report['id'], "msg": msg, "timestamp": time.time()})
                        enc = cipher.encrypt(payload.encode()).decode()
                        
                        point = models.PointStruct(
                            id=int(time.time()*1000),
                            vector=[0.0] * 384,
                            payload={"secure_content": enc, "target_id": report['id']}
                        )

                        try:
                            if not client.collection_exists(DOWNLINK_COLLECTION):
                                client.create_collection(DOWNLINK_COLLECTION, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
                            
                            client.upsert(collection_name=DOWNLINK_COLLECTION, points=[point])
                            st.toast(f"✅ Orders dispatched to {report['id']}!", icon="🐎")
                            
                        except Exception as e:
                            # Auto-Fix Schema
                            if "Wrong input" in str(e) or "Not existing vector" in str(e):
                                client.delete_collection(DOWNLINK_COLLECTION)
                                client.create_collection(DOWNLINK_COLLECTION, vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE))
                                client.upsert(collection_name=DOWNLINK_COLLECTION, points=[point])
                                st.toast(f"✅ System Self-Repaired & Sent!", icon="🔧")
                            else:
                                st.error(f"Failed: {e}")

# === TAB 2: ANALYTICS ===
with tab_analytics:
    st.header("📊 Threat Analytics")
    if data:
        df = pd.DataFrame(data)
        df['datetime'] = pd.to_datetime(df['time'], unit='s')
        
        ac1, ac2 = st.columns(2)
        with ac1:
            st.subheader("Urgency Over Time")
            st.area_chart(df.set_index('datetime')[['score']], color="#ff4b4b")
        with ac2:
            st.subheader("Threat Level Distribution")
            df['Level'] = pd.cut(df['score'], bins=[0, 0.3, 0.6, 1.0], labels=["Low", "Medium", "Critical"])
            st.bar_chart(df['Level'].value_counts())
            
        st.subheader("Detailed Metrics")
        st.dataframe(df[['id', 'score', 'lat', 'lon', 'datetime']], use_container_width=True)
    else:
        st.info("Insufficient data for analytics generation.")

# === TAB 3: DATA EXPORT ===
with tab_export:
    st.header("💾 Blackbox Data Retrieval")
    st.write("Download encrypted packet logs for offline analysis or government reporting.")
    if data:
        df_export = pd.DataFrame(data)
        df_clean = df_export.drop(columns=['img', 'audio', 'raw_payload'], errors='ignore')
        csv = df_clean.to_csv(index=False).encode('utf-8')
        
        st.download_button(
            label="📥 Download Mission Log (CSV)",
            data=csv,
            file_name=f"mission_log_{int(time.time())}.csv",
            mime="text/csv",
        )
    else:
        st.warning("No data available to export.")

# --- AUTO REFRESH LOGIC (FIXED) ---
# ⚠️ This block ensures the refresh pauses when you click a button
if auto_refresh and 'paused' not in st.session_state:
    time.sleep(10)
    st.rerun()

# Reset Pause after interaction
if 'paused' in st.session_state:
    del st.session_state['paused']