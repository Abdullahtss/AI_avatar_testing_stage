import pyttsx3
import threading
import time


class AudioFeedback:
    def __init__(self):
        self.engine = pyttsx3.init()

        # Faster voice
        rate = self.engine.getProperty('rate')
        self.engine.setProperty('rate', rate - 10)

        # Keep engine event loop alive
        self.engine.startLoop(False)

        # Background thread to pump engine
        self.thread = threading.Thread(target=self._pump_loop, daemon=True)
        self.thread.start()

    def _pump_loop(self):
        while True:
            self.engine.iterate()
            time.sleep(0.01)  # small sleep to reduce CPU usage

    def speak(self, message):
        try:
            self.engine.say(message)
        except Exception as e:
            print("Audio error:", e)
