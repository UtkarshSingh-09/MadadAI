import socket
import json
import threading
import time
import os
from qdrant_client import QdrantClient
from qdrant_client.http import models

print("\n✅ RUNNING FINAL MULE (CUSTOM PORTS: 6008/6009)\n")

# --- CONFIG ---
QDRANT_URL = "https://cb126147-b536-4963-bc80-5df16489d030.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.sWewvcj7k-GdQhPioomFrjtkVcJA9XjmEM4Bpd4CVCk"
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

def cloud_sync():
    first_run = True
    while True:
        time.sleep(5)
        if os.path.exists(STORAGE_FILE) and check_net():
            try:
                client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_KEY, prefer_grpc=False)
                if first_run:
                    try: client.get_collection(UPLINK_COLLECTION)
                    except: 
                        client.recreate_collection(
                            collection_name=UPLINK_COLLECTION,
                            vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
                        )
                    first_run = False

                with open(STORAGE_FILE, "r") as f: lines = f.readlines()
                points = []
                for i, line in enumerate(lines):
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        points.append(models.PointStruct(id=int(time.time()*1000)+i, vector=[0.0]*384, payload=data))
                    except: pass
                
                if points:
                    print(f"☁️ Uploading {len(points)} packets...")
                    client.upsert(collection_name=UPLINK_COLLECTION, points=points)
                    print("✅ Upload Success!")
                    open(STORAGE_FILE, 'w').close()
                elif lines:
                     open(STORAGE_FILE, 'w').close()

                if client.collection_exists(DOWNLINK_COLLECTION):
                    orders = client.scroll(collection_name=DOWNLINK_COLLECTION, limit=100, with_payload=True)[0]
                    if orders:
                        mail = [p.payload for p in orders]
                        with open(INBOX_FILE, "w") as f: json.dump(mail, f)
            except Exception as e:
                print(f"❌ Sync Error: {e}")

def beacon():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    while True:
        try:
            ip = get_ip()
            sock.sendto(json.dumps({"role": "mule_uplink", "ip": ip, "port": UPLINK_PORT}).encode(), ('<broadcast>', UDP_BEACON_PORT))
            sock.sendto(json.dumps({"role": "mule_reply", "ip": ip, "port": REPLY_PORT}).encode(), ('<broadcast>', UDP_BEACON_PORT))
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
                        print("📦 SOS Received")
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
                    mail = []
                    if os.path.exists(INBOX_FILE):
                        with open(INBOX_FILE, 'r') as f:
                            mail = [m for m in json.load(f) if m.get('target_id') == tid]
                    conn.sendall(json.dumps(mail).encode())
                    if mail: print(f"📤 Delivered mail to {tid}")
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