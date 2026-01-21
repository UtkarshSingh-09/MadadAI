# 🆘 Madad AI: The Resilient Offline Mesh Network

> **"When the grid goes down, Madad AI wakes up."**

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-%23EE4C2C.svg?style=for-the-badge&logo=PyTorch&logoColor=white)
![Qdrant](https://img.shields.io/badge/Qdrant-red?style=for-the-badge&logo=qdrant&logoColor=white)
![Socket.io](https://img.shields.io/badge/Socket.io-black?style=for-the-badge&logo=socket.io&logoColor=white)
![AES](https://img.shields.io/badge/Security-AES--128-green?style=for-the-badge)

## 📖 What is Madad AI?
**Madad AI** (meaning "Help" in Hindi/Urdu) is a next-generation disaster communication system designed for **zero-connectivity zones**.

In the aftermath of an earthquake, flood, or war, cellular towers and internet infrastructure are often the first to fail. **Madad AI** solves this by turning standard smartphones into an **offline mesh network**. It allows survivors to send encrypted SOS signals (text, voice, images, GPS) to nearby "Mule" devices, which physically carry the data to an internet-connected zone and sync it to the cloud, and receive rescue orders from HQ, even without a cellular signal.

It utilizes a **Tri-Link Adaptive Architecture**, intelligently switching between **Wi-Fi**, **Bluetooth**, and **LoRa** to ensure the signal always finds a way out.

---

## 🌍 Real-Life Example
Imagine a massive flood hits a region. Power is out, and **Alice** is trapped on her roof.

1.  **The Uplink (SOS):** Alice opens the **Madad AI** app. She has no signal, but records a voice note: *"Trapped on roof, water rising."* She clicks "Broadcast."
2.  **The Mule (Bob):** Bob, a volunteer in a boat, passes nearby. His phone (**The Mule**) automatically detects Alice's Wi-Fi signal and downloads her encrypted packet—without needing internet.
3.  **The Sync:** Bob reaches a safe zone with Satellite Internet. Madad AI auto-uploads Alice's SOS to **Command HQ**.
4.  **The Decision:** HQ sees Alice's location and replies: *"Helicopter en route. Light a flare."*
5.  **The Downlink (The Reply):** Bob's phone downloads this encrypted order into his "Courier Bag" and he heads back into the flood zone.
6.  **The Delivery:** As Bob's boat gets close to Alice again, her phone automatically detects his "Reply Signal" and downloads the message.
7.  **The Result:** Alice sees **"HQ: Helicopter en route"** on her screen, confirming help is coming.

---

## 🔄 The Workflow (Store-and-Forward)
The system follows a "Ferry-Based" **DTN (Delay-Tolerant Networking)** architecture.

### ⬆️ Phase 1: Uplink (Survivor → HQ)
* **Signal Generation:** Survivor App encrypts data (AES/Fernet) and broadcasts via UDP beacons.
* **Handshake:** A nearby Mule detects the beacon (`mule_uplink`) and establishes a TCP connection.
* **Offline Transfer:** The encrypted packet is transferred from Survivor → Mule.
* **Cloud Sync:** When the Mule finds Internet, it pushes the packet to the **Qdrant Vector Database**.

### ⬇️ Phase 2: Downlink (HQ → Survivor)
* **Command Issue:** HQ sends a JSON order targeting a specific Survivor ID.
* **Mule Loading:** The Mule polls the Cloud for "Mail" targeting its region and stores it offline in `mule_inbox.json`.
* **Zone Return:** The Mule returns to the offline zone and switches to `mule_reply` beacon mode.
* **Mail Delivery:** The Survivor App periodically scans for a Reply Mule. If found, it queries `GET_MAIL:{My_ID}` and decrypts the orders.

---

## 🏗️ 3-Layer Architecture
Madad AI operates on three distinct layers to ensure reliability.

### 1️⃣ The Application Layer (Survivor)
* **File:** `app.py`
* **Tech:** Streamlit, Folium, Fernet Encryption.
* **Role:** The interface for victims. Captures GPS/Audio/Photos, encrypts them, and scans for Mules using the **Tri-Link Protocol** (Wi-Fi, BLE, LoRa).

### 2️⃣ The Transport Layer (Mule)
* **File:** `mule.py`
* **Tech:** Raw Socket Programming (TCP/UDP), Python Async.
* **Role:** The "Digital Pigeon." It acts as a moving router that physically ferries data between the danger zone and the internet. It manages dual ports:
    * **Port 6008:** Uplink (Listening for SOS).
    * **Port 6009:** Downlink (Delivering Replies).

### 3️⃣ The Cloud Layer (HQ Dashboard)
* **File:** `dashboard.py`
* **Tech:** Qdrant (Vector DB), Streamlit, Plotly.
* **Role:** The Command Center. Visualizes SOS clusters on a heat map, allows semantic search (e.g., "Find medical emergencies"), and issues reply orders.

---

## 🚀 Installation & Usage
You need Python 3.8+ installed.

### 1. Clone the Repository
```bash
git clone [https://github.com/UtkarshSingh-09/MadadAI.git](https://github.com/UtkarshSingh-09/MadadAI.git)
cd MadadAI
pip install -r requirements.txt
```

### 2. Configure Security (Crucial)

Madad AI uses Qdrant Cloud for storage. You must set up your API keys securely.



For the Dashboard: Create a file .streamlit/secrets.toml:



```Ini, TOML

    QDRANT_URL = "your_qdrant_url"

    QDRANT_KEY = "your_qdrant_api_key"    

```



For the Mule: Create a file .env:



```Plaintext

    QDRANT_URL = "your_qdrant_url"

    QDRANT_KEY = "your_qdrant_api_key"    

```



### 3. Run the System (3 Terminals)



 #### Terminal 1: The Mule (The Router) Run this on a laptop or       Raspberry Pi acting as the bridge.



```bash

python mule.py

```



Status: ✅ MULE ACTIVE | Uplink: 6008 | Reply: 6009



#### Terminal 2: The Survivor (The User) Run this to simulate a victim.



```bash

streamlit run app.py

```



Go to "Write Report" to send an SOS.



Go to "Inbox" to check for replies from the Mule.



#### Terminal 3: Command HQ (The Admin) Run this to view data on the map.



```bash

streamlit run dashboard.py

```

    

## 🛡️ Security & Privacy

End-to-End Encryption: All messages are encrypted with AES-128 (Fernet) before leaving the survivor's device.



Blind Courier: The Mule carries the data blindly; it cannot read the content of the SOS or the Reply.



Anonymity: Packets are ID-based. Real identities are only revealed to authorized HQ personnel with the decryption key.

## 🤝 Contributing

Madad AI is an open-source humanitarian project. We welcome contributions, especially in:



LoRa Hardware Integration (Meshtastic).



Bluetooth Mesh optimization.



AI-based Triage classification.



Fork the Project



Create your Feature Branch (git checkout -b feature/NewFeature)



Commit your Changes (git commit -m 'Add NewFeature')



Push to the Branch (git push origin feature/NewFeature)



Open a Pull Request

<p align="center">
  <img src="images/architecture_diagram.png" width="600" alt="MadadAI Architecture">
</p>

## 📬 Contact

## Developer :- Utkarsh Singh

### Email:- utkarsh_singh@srmap.edu.in / thakurutkarsh2212@gmail.com
