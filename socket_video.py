# =============================================================================
# Copyright (c) 2024 Abdullah (GitHub: Abdullahtss)
# All Rights Reserved.
#
# PROPRIETARY AND CONFIDENTIAL
# This file is part of the AI Avatar Exercise Correction System.
#
# UNAUTHORIZED COPYING, MODIFICATION, DISTRIBUTION, OR USE OF THIS FILE,
# VIA ANY MEDIUM, IS STRICTLY PROHIBITED WITHOUT PRIOR WRITTEN PERMISSION
# FROM THE AUTHOR. Submitting this code as your own work constitutes
# plagiarism and may result in academic and/or legal consequences.
#
# For permissions: https://github.com/Abdullahtss
# =============================================================================
import socket
import struct
import cv2
import numpy as np

# ================= SERVER =================
class SocketVideoServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.host, self.port))
        self.sock.listen(1)
        print(f"[SocketVideo] Listening on {self.host}:{self.port}")
        self.conn = None
        self.data = b""

    def accept(self):
        self.conn, addr = self.sock.accept()
        print(f"[SocketVideo] Connected by {addr}")

    def read_frame(self):
        while len(self.data) < 4:
            packet = self.conn.recv(4096)
            if not packet:
                return None
            self.data += packet

        msg_len = struct.unpack(">I", self.data[:4])[0]
        self.data = self.data[4:]

        while len(self.data) < msg_len:
            packet = self.conn.recv(4096)
            if not packet:
                return None
            self.data += packet

        frame_data = self.data[:msg_len]
        self.data = self.data[msg_len:]

        frame = cv2.imdecode(
            np.frombuffer(frame_data, dtype=np.uint8),
            cv2.IMREAD_COLOR
        )
        return frame


# ================= CLIENT =================
class SocketVideoClient:
    def __init__(self, host="127.0.0.1", port=5000):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def connect(self):
        print(f"[Sender] Connecting to {self.host}:{self.port} ...")
        self.sock.connect((self.host, self.port))
        print("[Sender] Connected")

    def send_frame(self, frame):
        encoded = cv2.imencode(".jpg", frame)[1].tobytes()
        self.sock.sendall(struct.pack(">I", len(encoded)) + encoded)
