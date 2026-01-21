import socket
import json
import threading
import time
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models
from dotenv import load_dotenv

print("\n✅ RUNNING FINAL MULE (DIAGNOSTIC LOUD MODE | PORTS: 6008/6009)\n")
load_dotenv()

# --- CONFIG --- 
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_KEY = os.getenv("QDRANT_KEY")
UPLINK_COLLECTION = "disaster_reports"
DOWNLINK_COLLECTION = "courier_bag"

UDP_BEACON_PORT = 5005
UPLINK_PORT = 6008
REPLY_PORT = 6009

STORAGE_FILE = "mule_storage.json"
INBOX_FILE = "mule_inbox.json"

def get_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except: return "127.0.0.1"

def check_net():
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except: return False

# --- 🛡️ ROBUST SYNC ENGINE ---
def cloud_sync():
    first_run = True
    print("☁️ Cloud Sync Engine: STARTED")
    
    while True:
        time.sleep(5) # Breathe
        
        # 🔍 LOUD CHECK: Check internet every cycle
        if not check_net():
            print("⚠️ No Internet. Waiting...")
            continue

        try:
            # 1. Connect (Re-establish every cycle for stability)
            client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, timeout=60, prefer_grpc=False)
            
            # 2. Safety Check: Collection Exists?
            if first_run:
                try: 
                    if not client.collection_exists(UPLINK_COLLECTION):
                        client.create_collection(
                            collection_name=UPLINK_COLLECTION,
                            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                        )
                        print(f"✅ Created Collection: {UPLINK_COLLECTION}")
                except Exception as e:
                    print(f"⚠️ Collection Check Warning: {e}")
                first_run = False

            # --- 🚀 UPLINK SECTION (Local to Cloud) ---
            if os.path.exists(STORAGE_FILE) and os.path.getsize(STORAGE_FILE) > 0:
                with open(STORAGE_FILE, "r") as f: lines = f.readlines()
                points = []
                
                for i, line in enumerate(lines):
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        if i == 0: print(f"🔍 DEBUG PAYLOAD PREVIEW: {str(data)[:100]}...") 
                        
                        points.append(models.PointStruct(
                            id=int(time.time()*1000)+i, 
                            vector=[0.0]*384, 
                            payload=data
                        ))
                    except: pass
                
                if points:
                    success = False
                    for attempt in range(5):
                        try:
                            print(f"☁️ Uploading {len(points)} packets (Attempt {attempt+1}/5)...")
                            client.upsert(collection_name=UPLINK_COLLECTION, points=points)
                            success = True
                            print("✅ Upload Success! Database Updated.")
                            break 
                        except Exception as e:
                            print(f"❌ Upload Failed: {e}")
                            time.sleep(2)

                    if success:
                        open(STORAGE_FILE, 'w').close()

            # --- 📬 DOWNLINK SECTION (Cloud to Local) ---
            # Added "Loud" debugging to see exactly why orders might be missing
            print(f"🔍 Checking '{DOWNLINK_COLLECTION}' for orders...", end="\r")
            
            try:
                if client.collection_exists(DOWNLINK_COLLECTION):
                    orders_result = client.scroll(collection_name=DOWNLINK_COLLECTION, limit=50, with_payload=True)
                    orders = orders_result[0]
                    
                    if orders:
                        print(f"\n📬 FOUND {len(orders)} ORDERS IN CLOUD!")
                        mail = []
                        for p in orders:
                            payload = p.payload
                            target = payload.get('target_id', 'UNKNOWN')
                            print(f"   - 📦 Msg for {target} (ID: {p.id})")
                            mail.append(payload)
                            
                        with open(INBOX_FILE, "w") as f: json.dump(mail, f)
                        print(f"💾 Sync Complete: {len(mail)} orders saved to {INBOX_FILE}")
                else:
                    print(f"\n⚠️ Downlink Collection '{DOWNLINK_COLLECTION}' does not exist in Cloud.")
            except Exception as e_down:
                print(f"\n❌ Downlink Error: {e_down}")

        except Exception as e:
            print(f"\n❌ Critical Sync Error: {e}")

# --- UDP & TCP HANDLERS (UNCHANGED) ---
def beacon():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            ip = get_ip()
            msg_uplink = json.dumps({"role": "mule_uplink", "ip": ip, "port": UPLINK_PORT}).encode()
            msg_reply = json.dumps({"role": "mule_reply", "ip": ip, "port": REPLY_PORT}).encode()
            
            sock.sendto(msg_uplink, ('<broadcast>', UDP_BEACON_PORT))
            sock.sendto(msg_reply, ('<broadcast>', UDP_BEACON_PORT))
            time.sleep(2)
        except: time.sleep(5)

def uplink_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', UPLINK_PORT))
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                conn.settimeout(10)
                data = b""
                while True:
                    try:
                        chunk = conn.recv(4096)
                        if not chunk: break
                        data += chunk
                    except socket.timeout: break
                if data:
                    decoded = data.decode('utf-8', errors='ignore')
                    start, end = decoded.find('{'), decoded.rfind('}')
                    if start != -1 and end != -1:
                        clean = decoded[start:end+1]
                        parsed = json.loads(clean)
                        with open(STORAGE_FILE, "a") as f: f.write(json.dumps(parsed) + "\n")
                        print(f"📦 SOS Received from {addr}")
                        conn.sendall(b"ACK")
                conn.close()
            except: pass

def reply_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(('0.0.0.0', REPLY_PORT))
        s.listen()
        while True:
            try:
                conn, addr = s.accept()
                data = conn.recv(1024).decode()
                if "GET_MAIL:" in data:
                    tid = data.split(":")[1].strip()
                    print(f"📲 App {addr} requesting mail for: {tid}")
                    mail = []
                    if os.path.exists(INBOX_FILE):
                        with open(INBOX_FILE, 'r') as f:
                            all_mail = json.load(f)
                            mail = [m for m in all_mail if m.get('target_id') == tid]
                    
                    conn.sendall(json.dumps(mail).encode())
                    if mail: 
                        print(f"📤 Delivered {len(mail)} orders to {tid}")
                    else:
                        print(f"⚪ No mail found for {tid}")
                conn.close()
            except: pass

if __name__ == "__main__":
    os.system(f"lsof -ti:{UPLINK_PORT} | xargs kill -9 2>/dev/null")
    os.system(f"lsof -ti:{REPLY_PORT} | xargs kill -9 2>/dev/null")
    
    threading.Thread(target=cloud_sync, daemon=True).start()
    threading.Thread(target=beacon, daemon=True).start()
    threading.Thread(target=uplink_server, daemon=True).start()
    
    print(f"✅ MULE ACTIVE | Uplink: {UPLINK_PORT} | Reply: {REPLY_PORT}")
    reply_server()