import time
import json
import cv2
import numpy as np
import socket
import struct
from collections import defaultdict, deque

from utils import PoseEstimator
from fsm import get_fsm

# ================= CONSTANTS =================
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

# ================= UTILS =================
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

# ================= TRAINER =================
class Trainer:
    def __init__(self, cfg, num_reps=None):
        """
        Initialize Trainer
        
        Args:
            cfg: Exercise configuration object with:
                - name: str (exercise name)
                - type: str ('single', 'boxing', 'yoga')
                - primary_angle: str (joint to track)
                - min_rom: int (minimum range of motion for single-stage)
            num_reps: int (optional, number of reps to train, None = manual stop)
        """
        self.cfg = cfg
        self.num_reps = num_reps  # ← NEW: Store num_reps
        self.pose = PoseEstimator()

        # ---------- FSM ----------
        # Multi-stage FSMs can be initialized immediately
        if cfg.type in ("boxing", "yoga"):
            self.fsm = get_fsm(cfg)
        else:
            self.fsm = None  # single-stage FSM initialized after training

        # ← NEW: Initialize stage tracking for multi-stage exercises
        if cfg.type in ("boxing", "yoga"):
            self.prev_stage = None
            self.stage_sequence_rep = []  # Track stages in current rep
            self.expected_rep_sequence = self._get_expected_rep_sequence()

        # ---------- SOCKET SERVER ----------
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((HOST, PORT))
        self.sock.listen(1)

        print(f"[Trainer] Listening on {HOST}:{PORT}")
        print("[Trainer] Waiting for video sender...")

        self.conn, addr = self.sock.accept()
        print(f"[Trainer] Video sender connected from {addr}")

        # Yoga stability buffer (ONLY used for yoga)
        self.data = b""  # ← THIS MUST EXIST

        # Yoga stability buffer
        self.angle_history = deque(maxlen=20)

        # Yoga hold tracking
        self.hold_start_time = None
        self.hold_completed = False
        self.HOLD_DURATION = 3.0  # seconds required for 1 yoga rep



    # ← NEW: Get expected rep sequence for multi-stage exercises
    def _get_expected_rep_sequence(self):
        """
        Get expected stage sequence for one complete rep
        """

        if self.cfg.type == "boxing":
            return ["guard", "punch", "recover"]

        elif self.cfg.type == "yoga":
            return ["entering", "hold", "exiting"]

        return []



    # ---------- FRAME RECEIVE ----------
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

        return cv2.imdecode(
            np.frombuffer(frame_data, dtype=np.uint8),
            cv2.IMREAD_COLOR
        )

    # ← NEW: Check if rep is complete for multi-stage exercises
    def _check_rep_complete_multistage(self, current_stage):
        """
        Check if a complete rep is done (all stages in sequence)
        """

        if current_stage != self.prev_stage:
            self.stage_sequence_rep.append(current_stage)
            self.prev_stage = current_stage

            if len(self.stage_sequence_rep) >= len(self.expected_rep_sequence):
                recent = self.stage_sequence_rep[-len(self.expected_rep_sequence):]

                if recent == self.expected_rep_sequence:
                    self.stage_sequence_rep = []
                    return True

        return False

    # ---------- MAIN TRAINING LOOP ----------
    def run(self, out_base=None):
        print(f"[Trainer] Training exercise: {self.cfg.name}")
        print(f"[Trainer] Exercise type: {self.cfg.type}")
        
        if self.num_reps:
            print(f"[Trainer] Target reps: {self.num_reps}")
            print("[Trainer] Training will stop automatically after target reps")
        else:
            print("[Trainer] Press 'q' to stop recording")

        joint_angles = defaultdict(list)
        joint_speeds = defaultdict(list)
        prev_angles = {}

        centroid_y = []
        timestamps = []

        motion_frames = []
        stage_sequence = []

        primary_joint = self.cfg.primary_angle

        rep_count = 0
        rep_state = "top"
        last_rep_time = 0
        top_angle = None
        bottom_angle = None

        MIN_REP_GAP = 0.8
        MIN_ANGLE_RANGE = self.cfg.min_rom

        t0 = time.time()

        # Yoga hold tracking
        hold_start_time = None
        hold_completed = False
        HOLD_DURATION = 3.0  # seconds required for 1 yoga rep

        # ================= LOOP =================
        while True:
            frame = self.read_frame()
            if frame is None:
                continue

            pts = self.pose.process(frame)
            overlay = frame.copy()
            

            if pts:
                h, w, _ = frame.shape

                motion_frames.append(
                    [(float(p[0]) / w, float(p[1]) / h) for p in pts]
                )

                self.pose.draw(overlay, pts)

                all_angles = []

                # ----- ANGLES & SPEED -----
                for j, (a, b, c) in JOINTS.items():
                    A, B, C = pts[a], pts[b], pts[c]
                    ang = calculate_angle(A, B, C)
                    joint_angles[j].append(ang)
                    all_angles.append(ang)

                    if j in prev_angles:
                        joint_speeds[j].append(abs(ang - prev_angles[j]) * FPS)

                    prev_angles[j] = ang

                # ================= FSM UPDATE =================
                if self.cfg.type == "single":

                    a, b, c = JOINTS[primary_joint]
                    angle = calculate_angle(pts[a], pts[b], pts[c])

                    stage = "move"
                    if self.fsm:
                        stage = self.fsm.update(
                            angle,
                            min(joint_angles[primary_joint]),
                            max(joint_angles[primary_joint])
                        )

                elif self.cfg.type == "boxing":

                    avg_speed = (
                        np.mean(joint_speeds[primary_joint][-5:])
                        if len(joint_speeds[primary_joint]) >= 5 else 0
                    )

                    stage = self.fsm.update(avg_speed)

                    if self._check_rep_complete_multistage(stage):
                        rep_count += 1
                        print(f"[Trainer] Rep {rep_count} / {self.num_reps if self.num_reps else '∞'}")

                else:  # YOGA (HOLD-BASED LOGIC)

                    a, b, c = JOINTS[primary_joint]
                    angle = calculate_angle(pts[a], pts[b], pts[c])

                    self.angle_history.append(angle)

                    if len(self.angle_history) >= 5:
                        angle_std = np.std(self.angle_history)
                    else:
                        angle_std = 0

                    stage = self.fsm.update(angle_std)

                    # Display stability
                    cv2.putText(
                        overlay,
                        f"Stability STD: {round(angle_std,2)}",
                        (30, 160),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.8,
                        (0,255,255),
                        2
                    )

                    # ---- HOLD-BASED REP COUNTING ----
                    if stage == "hold":

                        if hold_start_time is None:
                            hold_start_time = time.time()

                        hold_time = time.time() - hold_start_time

                        # ---- HOLD-BASED REP COUNTING (STRICT STABILITY) ----

                        stable_threshold = self.fsm.STABLE_STD

                        if angle_std < stable_threshold:

                            if hold_start_time is None:
                                hold_start_time = time.time()

                            hold_time = time.time() - hold_start_time

                            # Display hold timer
                            cv2.putText(
                                overlay,
                                f"HOLD TIME: {round(hold_time,1)}s",
                                (30, 200),
                                cv2.FONT_HERSHEY_SIMPLEX,
                                0.8,
                                (0,255,0),
                                2
                            )

                            if hold_time >= HOLD_DURATION and not hold_completed:
                                rep_count += 1
                                print(f"[Trainer] Yoga hold rep {rep_count}")
                                hold_completed = True

                        else:
                            # Instability detected → reset hold
                            hold_start_time = None
                            hold_completed = False


                stage_sequence.append(stage)

                # ----- REP COUNT (single only) -----
                if self.cfg.type == "single":

                    if top_angle is None:
                        top_angle = angle
                        bottom_angle = angle

                    top_angle = max(top_angle, angle)
                    bottom_angle = min(bottom_angle, angle)

                    if (top_angle - bottom_angle) > MIN_ANGLE_RANGE:
                        now = time.time()
                        if angle < bottom_angle + 10 and rep_state == "top":
                            rep_state = "bottom"
                        elif angle > top_angle - 10 and rep_state == "bottom":
                            if now - last_rep_time > MIN_REP_GAP:
                                rep_count += 1
                                last_rep_time = now
                                rep_state = "top"
                                print(f"[Trainer] Rep {rep_count} / {self.num_reps if self.num_reps else '∞'}")

                # ----- DISPLAY -----
                cv2.putText(
                    overlay, f"REPS: {rep_count}",
                    (30, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 3
                )
                cv2.putText(
                    overlay, f"STAGE: {stage}",
                    (30, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255,0,255), 2
                )

                if self.num_reps:
                    progress = f"{rep_count}/{self.num_reps}"
                    cv2.putText(
                        overlay, progress,
                        (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2
                    )

                centroid_y.append(np.mean([p[1] for p in pts]))
                timestamps.append(time.time() - t0)

            cv2.imshow("Trainer", overlay)

            if self.num_reps and rep_count >= self.num_reps:
                print(f"\n[Trainer] Target {self.num_reps} reps reached! Stopping.")
                break

            if not self.num_reps and cv2.waitKey(1) & 0xFF == ord("q"):
                break

            if cv2.waitKey(1) & 0xFF != 255:
                pass

        cv2.destroyAllWindows()

        # ================= HOLD TIME ANALYSIS (UNCHANGED) =================
        centroid_y = np.array(centroid_y)
        timestamps = np.array(timestamps)

        top_level = np.percentile(centroid_y, 10)
        bottom_level = np.percentile(centroid_y, 90)

        top_holds, bottom_holds = [], []
        state, enter_time = None, None

        for y, t in zip(centroid_y, timestamps):
            if y <= top_level:
                if state != "top":
                    state, enter_time = "top", t
            elif y >= bottom_level:
                if state != "bottom":
                    state, enter_time = "bottom", t
            else:
                if state == "top":
                    top_holds.append(t - enter_time)
                elif state == "bottom":
                    bottom_holds.append(t - enter_time)
                state = None

        # ================= MODEL =================
        model = {
            "exercise": self.cfg.name,
            "type": self.cfg.type,
            "reps_recorded": rep_count,
            "fsm_stages": stage_sequence,
            "hold_top_avg_s": float(np.mean(top_holds)) if top_holds else 0.0,
            "hold_bottom_avg_s": float(np.mean(bottom_holds)) if bottom_holds else 0.0,
            "joints": {}
        }

        for j in joint_angles:
            model["joints"][j] = {
                "min": float(np.min(joint_angles[j])),
                "max": float(np.max(joint_angles[j])),
                "avg": float(np.mean(joint_angles[j])),
                "std": float(np.std(joint_angles[j])),
                "speed_avg": float(np.mean(joint_speeds[j])) if joint_speeds[j] else 0.0,
                "speed_std": float(np.std(joint_speeds[j])) if joint_speeds[j] else 0.0,
            }

        if self.cfg.type == "single":
            joint_stats = model["joints"][primary_joint]
            self.fsm = get_fsm(self.cfg, joint_stats)

        with open(f"baselines/{self.cfg.name}_model.json", "w") as f:
            json.dump(model, f, indent=2)

        with open(f"baselines/{self.cfg.name}_motion.json", "w") as f:
            json.dump(motion_frames, f)

        print("[Trainer] Training complete")
        print(f"[Trainer] Total reps recorded: {rep_count}")
        print("[Trainer] Model + motion saved")

        self.conn.close()
        self.sock.close()
