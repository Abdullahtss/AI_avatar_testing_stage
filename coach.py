import time
import json
import cv2
import numpy as np
import socket
import struct
from collections import deque

from utils import PoseEstimator
from audio_feedback import AudioFeedback
from fsm import SingleExerciseFSM, YogaFSM, BoxingFSM

FPS = 30
HOST = "0.0.0.0"
PORT = 5000

JOINTS = {
    "left_elbow": (11, 13, 15),
    "right_elbow": (12, 14, 16),
    "left_knee": (23, 25, 27),
    "right_knee": (24, 26, 28),
    "left_shoulder": (13, 11, 23),
    "right_shoulder": (14, 12, 24),
}


LOWER_BODY_JOINTS = ["left_knee", "right_knee"]
UPPER_BODY_JOINTS = ["left_elbow", "right_elbow", "left_shoulder", "right_shoulder"]


POSE_CONNECTIONS = [
    (11, 13), (13, 15), (15, 17),
    (12, 14), (14, 16), (16, 18),
    (11, 12),
    (23, 25), (25, 27),
    (24, 26), (26, 28),
    (23, 24),
    (11, 23), (12, 24)
]


def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    ba = a - b
    bc = c - b
    return np.degrees(
        np.arccos(
            np.clip(
                np.dot(ba, bc) /
                (np.linalg.norm(ba) * np.linalg.norm(bc)),
                -1.0, 1.0
            )
        )
    )


def draw_avatar_frame(landmarks, w, h):
    canvas = np.zeros((h, w, 3), dtype=np.uint8)
    pts = [(int(x * w), int(y * h)) for x, y in landmarks]

    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(canvas, pts[a], pts[b], (0, 255, 255), 2)

    for p in pts:
        cv2.circle(canvas, p, 4, (0, 255, 0), -1)

    return canvas


class LiveCoach:
    def __init__(self, cfg):
        self.cfg = cfg
        self.pose = PoseEstimator()
        self.audio = AudioFeedback()
        self.body_region = "lower" if cfg.primary_angle in LOWER_BODY_JOINTS else "upper"


        with open(f"baselines/{cfg.name}_model.json", "r") as f:
            self.model = json.load(f)

        with open(f"baselines/{cfg.name}_motion.json", "r") as f:
            self.avatar_motion = json.load(f)

        self.avatar_idx = 0
        self.rep_count = 0
        self.last_feedback_text = ""
        self.current_stage = "ready"

        self.angle_history = deque(maxlen=20)

        # Yoga hold logic
        self.hold_start_time = None
        self.hold_completed = False
        self.HOLD_DURATION = 3.0

        # Rep quality tracking
        self.rep_min_angle = None
        self.rep_max_angle = None
        self.rep_speed_samples = []

        # FSM
        if cfg.type == "boxing":
            self.fsm = BoxingFSM()
        elif cfg.type == "yoga":
            self.fsm = YogaFSM()
        else:
            stats = self.model["joints"][cfg.primary_angle]
            self.fsm = SingleExerciseFSM(
                stats["min"],
                stats["max"],
                cfg.min_rom
            )

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.listen(1)

        print(f"[Coach] Listening on {HOST}:{PORT}")
        self.conn, addr = self.sock.accept()
        print(f"[Coach] Video sender connected from {addr}")

        self.buffer = b""

    def read_frame(self):
        while len(self.buffer) < 4:
            pkt = self.conn.recv(4096)
            if not pkt:
                return None
            self.buffer += pkt

        size = struct.unpack(">I", self.buffer[:4])[0]
        self.buffer = self.buffer[4:]

        while len(self.buffer) < size:
            pkt = self.conn.recv(4096)
            if not pkt:
                return None
            self.buffer += pkt

        data = self.buffer[:size]
        self.buffer = self.buffer[size:]

        return cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)

    # -------- REP QUALITY EVALUATION --------
    def evaluate_rep(self, stats):

        rom_total = stats["max"] - stats["min"]
        actual_rom = self.rep_max_angle - self.rep_min_angle

        avg_speed = np.mean(self.rep_speed_samples) if self.rep_speed_samples else 0

        # Normalize values
        rom_ratio = actual_rom / rom_total if rom_total > 0 else 0

        feedback_options = []

        # ---------------- ROM QUALITY ----------------
        if rom_ratio < 0.5:
            feedback_options.append("Very shallow movement")
        elif rom_ratio < 0.7:
            feedback_options.append("Increase your range")
        elif rom_ratio < 0.85:
            feedback_options.append("Good depth, go slightly deeper")
        else:
            feedback_options.append("Excellent depth")

        # ---------------- SPEED QUALITY ----------------
        if avg_speed < 8:
            feedback_options.append("Add more energy")
        elif avg_speed < 20:
            feedback_options.append("Good controlled pace")
        elif avg_speed < 100:
            feedback_options.append("Strong tempo")
        elif avg_speed < 160:
            feedback_options.append("Slow down slightly")
        else:
            feedback_options.append("Too fast, focus on control")

        # ---------------- BODY REGION TUNING ----------------
        if self.body_region == "lower":
            feedback_options.append("Keep your knees aligned")
        else:
            feedback_options.append("Control your upper body movement")

        # ---------------- FINAL SELECTION ----------------
        # Pick 1 ROM + 1 SPEED randomly
        selected = np.random.choice(feedback_options, size=2, replace=False)

        return f"{selected[0]}. {selected[1]}"



    # -------- MAIN LOOP --------
    def run(self):

        primary_joint = self.cfg.primary_angle
        stats = self.model["joints"][primary_joint]

        prev_angle = None
        rep_state = "top"

        print("[Coach] Coaching started")

        while True:
            frame = self.read_frame()
            if frame is None:
                continue

            h, w, _ = frame.shape

            avatar = draw_avatar_frame(
                self.avatar_motion[self.avatar_idx], w, h
            )
            self.avatar_idx = (self.avatar_idx + 1) % len(self.avatar_motion)

            user = frame.copy()
            pts = self.pose.process(frame)

            if not pts:
                continue

            self.pose.draw(user, pts)

            a, b, c = JOINTS[primary_joint]
            angle = calculate_angle(pts[a], pts[b], pts[c])

            speed = 0
            if prev_angle is not None:
                speed = abs(angle - prev_angle) * FPS
                self.rep_speed_samples.append(speed)

            prev_angle = angle

            # Track min/max per rep
            if self.rep_min_angle is None:
                self.rep_min_angle = angle
                self.rep_max_angle = angle

            self.rep_min_angle = min(self.rep_min_angle, angle)
            self.rep_max_angle = max(self.rep_max_angle, angle)

            # ---------------- YOGA LOGIC ----------------
            if self.cfg.type == "yoga":

                self.angle_history.append(angle)

                # Only compute STD when enough samples
                if len(self.angle_history) >= 5:
                    angle_std = np.std(self.angle_history)
                else:
                    angle_std = 999  # force unstable until enough data

                stable_threshold = self.fsm.STABLE_STD

                # Display STD
                cv2.putText(user,
                            f"STD: {round(angle_std,2)}",
                            (20, 140),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.7,
                            (0,255,255),
                            2)

                # STRICT STABILITY CHECK
                if angle_std < stable_threshold:

                    if self.hold_start_time is None:
                        self.hold_start_time = time.time()
                        self.hold_completed = False   # ensure new hold

                    hold_time = time.time() - self.hold_start_time

                    cv2.putText(user,
                                f"HOLD: {round(hold_time,1)}s",
                                (20, 170),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0,255,0),
                                2)

                    # Count rep once per hold
                    if hold_time >= self.HOLD_DURATION and not self.hold_completed:
                        self.rep_count += 1

                        feedback = f"Good hold rep {self.rep_count}"
                        self.audio.speak(feedback)
                        self.last_feedback_text = feedback

                        self.hold_completed = True

                else:
                    # Instability → reset EVERYTHING
                    self.hold_start_time = None
                    self.hold_completed = False

            # ---------------- SINGLE / BOXING ----------------
            else:

                if angle < stats["min"] + 10 and rep_state == "top":
                    rep_state = "bottom"

                elif angle > stats["max"] - 10 and rep_state == "bottom":

                    rep_state = "top"
                    self.rep_count += 1

                    feedback = f"{self.evaluate_rep(stats)} rep {self.rep_count}"


                    self.audio.speak(feedback)
                    self.last_feedback_text = feedback

                    # Reset tracking
                    self.rep_min_angle = None
                    self.rep_max_angle = None
                    self.rep_speed_samples = []

                    # Determine body region for feedback tuning
                    LOWER_BODY_JOINTS = ["left_knee", "right_knee"]
                    if self.cfg.primary_angle in LOWER_BODY_JOINTS:

                        self.body_region = "lower"
                    else:
                        self.body_region = "upper"


            cv2.putText(user, f"REPS: {self.rep_count}",
                        (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                        1, (0,255,0), 3)

            cv2.putText(user, f"FEEDBACK: {self.last_feedback_text}",
                        (20, 100), cv2.FONT_HERSHEY_SIMPLEX,
                        0.8, (0,0,255), 2)

            combined = np.hstack([avatar, user])
            cv2.imshow("AI Exercise Coach", combined)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

        cv2.destroyAllWindows()
        self.conn.close()
