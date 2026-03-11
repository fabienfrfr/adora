from dora import DoraStatus
import numpy as np
import cv2

class Operator:
    def on_event(self, dora_event, send_output):
        if dora_event["type"] == "INPUT":
            # Simulation d'une image de caméra (bruit aléatoire)
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            send_output("image", cv2.imencode(".jpg", frame)[1].tobytes())
        
        return DoraStatus.CONTINUE