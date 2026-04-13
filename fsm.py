# fsm.py
import time
import numpy as np

# ================= BASE FSM =================
class BaseFSM:
    def __init__(self):
        self.state = None
        self.prev_state = None
        self.state_enter_time = time.time()

    def transition(self, new_state):
        if new_state != self.state:
            self.prev_state = self.state
            self.state = new_state
            self.state_enter_time = time.time()

    def time_in_state(self):
        return time.time() - self.state_enter_time

    def update(self, metric):
        raise NotImplementedError


# ================= SINGLE STAGE FSM =================
class SingleExerciseFSM(BaseFSM):
    """
    FSM for single-joint repetitive exercises:
    Squats, Pushups, Bicep Curls, etc.

    States: top → down → bottom → up → top
    """

    def __init__(self, min_angle, max_angle, min_rom):
        super().__init__()
        self.min_angle = min_angle
        self.max_angle = max_angle
        self.min_rom = min_rom
        self.state = "top"

    def update(self, angle):
        rom = self.max_angle - self.min_angle

        if rom < self.min_rom:
            return self.state

        if self.state == "top" and angle < self.max_angle - 10:
            self.transition("down")

        elif self.state == "down" and angle <= self.min_angle + 5:
            self.transition("bottom")

        elif self.state == "bottom" and angle > self.min_angle + 10:
            self.transition("up")

        elif self.state == "up" and angle >= self.max_angle - 5:
            self.transition("top")

        return self.state


# ================= BOXING FSM =================
class BoxingFSM(BaseFSM):
    """
    FSM for boxing motions
    States: guard → punch → recover → guard
    Metric: average arm speed
    """

    def __init__(self):
        super().__init__()
        self.state = "guard"

        self.PUNCH_SPEED = 120
        self.RECOVER_SPEED = 40
        self.MIN_PUNCH_TIME = 0.15

    def update(self, speed):
        if self.state == "guard":
            if speed > self.PUNCH_SPEED:
                self.transition("punch")

        elif self.state == "punch":
            if self.time_in_state() > self.MIN_PUNCH_TIME:
                self.transition("recover")

        elif self.state == "recover":
            if speed < self.RECOVER_SPEED:
                self.transition("guard")

        return self.state


# ================= YOGA FSM =================
class YogaFSM(BaseFSM):
    """
    FSM for yoga stability tracking
    States: entering → hold → exiting
    Metric: angle standard deviation
    """

    def __init__(self):
        super().__init__()
        self.state = "entering"

        self.STABLE_STD = 3.0
        self.UNSTABLE_STD = 6.0
        self.MIN_HOLD_TIME = 1.0

    def update(self, angle_std):
        if self.state == "entering":
            if angle_std < self.STABLE_STD:
                self.transition("hold")

        elif self.state == "hold":
            if angle_std > self.UNSTABLE_STD:
                self.transition("exiting")

        elif self.state == "exiting":
            if angle_std < self.STABLE_STD:
                self.transition("hold")

        return self.state

# ================= FSM FACTORY =================
def get_fsm(cfg, joint_stats=None):
    """
    Factory that returns correct FSM based on exercise type.
    Used by trainer.
    """

    if cfg.type == "single":
        if joint_stats is None:
            raise ValueError("joint_stats required for single exercise FSM")

        return SingleExerciseFSM(
            joint_stats["min"],
            joint_stats["max"],
            cfg.min_rom
        )

    if cfg.type == "boxing":
        return BoxingFSM()

    if cfg.type == "yoga":
        return YogaFSM()

    raise ValueError(f"Unknown exercise type: {cfg.type}")
