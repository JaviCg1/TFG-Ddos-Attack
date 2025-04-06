# utils.py

import socket

# Función para enviar un mensaje a un bot específico
def send_message(message, ip, port):
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, int(port)))
            s.sendall(message.encode())
    except Exception as e:
        print(f"Failed to send message to {ip}:{port}. Error: {e}")