import json
import cv2
import numpy as np
import time
import argparse

# ================= CONSTANTS =================
FPS = 30

POSE_CONNECTIONS = [
    (11,13),(13,15),(15,17),
    (12,14),(14,16),(16,18),
    (11,12),
    (23,25),(25,27),
    (24,26),(26,28),
    (23,24),
    (11,23),(12,24)
]

# ================= DRAW AVATAR =================
def draw_avatar_frame(landmarks, width=640, height=480):
    """
    landmarks: list of (x,y) normalized coordinates
    """
    canvas = np.zeros((height, width, 3), dtype=np.uint8)

    # convert normalized → pixel
    pts = [(int(x * width), int(y * height)) for x, y in landmarks]

    # draw skeleton
    for a, b in POSE_CONNECTIONS:
        if a < len(pts) and b < len(pts):
            cv2.line(canvas, pts[a], pts[b], (0, 255, 255), 2)

    # draw joints
    for p in pts:
        cv2.circle(canvas, p, 4, (0, 255, 0), -1)

    # label
    cv2.putText(
        canvas,
        "AI AVATAR DEMO",
        (20, 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        1,
        (255, 255, 255),
        2
    )

    return canvas

# ================= PLAY AVATAR =================
def play_avatar(exercise):
    motion_path = f"baselines/{exercise}_motion.json"

    with open(motion_path, "r") as f:
        motion = json.load(f)

    print(f"[Avatar] Playing demo for '{exercise}'")
    print("[Avatar] Press ESC to exit")

    idx = 0

    while True:
        landmarks = motion[idx]
        frame = draw_avatar_frame(landmarks)

        cv2.imshow("Avatar Demo", frame)

        idx = (idx + 1) % len(motion)

        if cv2.waitKey(int(1000 / FPS)) & 0xFF == 27:
            break

    cv2.destroyAllWindows()

# ================= MAIN =================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Play trained avatar demo")
    parser.add_argument("--exercise", "-e", required=True,
                        help="Exercise name (e.g. squat, boxing, yoga)")
    args = parser.parse_args()

    play_avatar(args.exercise)
