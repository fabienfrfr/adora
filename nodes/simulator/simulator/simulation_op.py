import io
import webbrowser
import time
import threading
import http.server
import pybullet as p
import pybullet_data
import numpy as np
from PIL import Image
from dora import DoraStatus

# Global shared buffer for the MJPEG stream
SHARED_FRAME = None
FRAME_LOCK = threading.Lock()

class MJPEGHandler(http.server.BaseHTTPRequestHandler):
    """Minimal MJPEG server using only Python standard libraries."""
    
    def do_GET(self):
        """Handle GET requests for the live stream."""
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            try:
                while True:
                    with FRAME_LOCK:
                        if SHARED_FRAME is None:
                            continue
                        frame = SHARED_FRAME
                    
                    self.wfile.write(b'--frame\r\n')
                    self.send_header('Content-type', 'image/jpeg')
                    self.send_header('Content-length', len(frame))
                    self.end_headers()
                    self.wfile.write(frame)
                    self.wfile.write(b'\r\n')
            except (ConnectionResetError, BrokenPipeError):
                pass

class Operator:
    """PyBullet simulation operator with integrated zero-dependency web viewer."""

    def __init__(self):
        """Initialize physics engine and start the local web server."""
        # 1. Start Web Server in a background thread (Port 8080)
        server = http.server.ThreadingHTTPServer(('0.0.0.0', 8080), MJPEGHandler)
        threading.Thread(target=server.serve_forever, daemon=True).start()

        # 2. Automatically open the browser after a short delay
        def open_browser():
            time.sleep(2)
            webbrowser.open("http://localhost:8080")
        
        threading.Thread(target=open_browser, daemon=True).start()
        # 3. PyBullet setup in DIRECT mode (Headless/Wayland compatible)
        p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        
        # 2. Load Stadium
        self.stadium_id = p.loadSDF("stadium.sdf")[0]
        
        # 3. Load Car
        self.car_id = p.loadURDF("racecar/racecar.urdf", [0, 0, 0.02])
        
        for i in range(p.getNumJoints(self.car_id)):
            p.changeDynamics(self.car_id, i, lateralFriction=1.0, rollingFriction=0.01)

        self.width, self.height = 224, 224

    def on_event(self, dora_event, send_output):
        """Handle Dora events (tick for physics, action for control)."""
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                self._handle_tick(dora_event, send_output)
            elif dora_event["id"] == "action":
                self._handle_action(dora_event)
        return DoraStatus.CONTINUE

    def _handle_tick(self, event, send_output):
        """Step simulation, capture frame, and update web buffer."""
        global SHARED_FRAME
        p.stepSimulation()
        
        # Camera Positioning
        pos, orn = p.getBasePositionAndOrientation(self.car_id)
        mat = p.getMatrixFromQuaternion(orn)
        forward = [mat[0], mat[3], mat[6]]
        
        view_mat = p.computeViewMatrix(
            [pos[0], pos[1], pos[2] + 0.2],
            [pos[0] + forward[0], pos[1] + forward[1], pos[2]],
            [0, 0, 1]
        )
        proj_mat = p.computeProjectionMatrixFOV(60, 1, 0.1, 10)
        
        # CPU-based rendering
        _, _, rgb, _, _ = p.getCameraImage(
            self.width, self.height, view_mat, proj_mat,
            renderer=p.ER_TINY_RENDERER
        )
        
        # Encode to JPEG using Pillow
        frame = np.reshape(rgb, (self.height, self.width, 4))[:, :, :3]
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        jpeg_bytes = buffer.getvalue()
        
        # Update shared buffer for the web server
        with FRAME_LOCK:
            SHARED_FRAME = jpeg_bytes
        
        # Clean metadata to avoid datetime conversion errors
        metadata = {
            "timestamp_utc": str(event["metadata"].get("timestamp_utc", time.time()))
        }
        
        # Send as bytes (since you're already encoding to JPEG)
        send_output("image", jpeg_bytes, metadata)

    def _handle_action(self, event):
        """Apply control signals from the VLA with explicit type handling."""
        # 1. Direct conversion from Arrow to Numpy (No copy, memory efficient)
        raw_data = event["value"].to_numpy()
        action = raw_data.view(np.float32)
        print(f"🚗 Simulator received action: {action}")
        # 2. Validation: Ensure we have at least [throttle, steering]
        if action.size < 2:
            return

        # VLA output is likely [0, 1], let's scale it gently
        throttle, steering = action[0], action[1]
        
        # 1. Drive joints
        for joint in [2, 3, 5, 7]:
            p.setJointMotorControl2(
                self.car_id, 
                joint, 
                p.VELOCITY_CONTROL, 
                targetVelocity=float(throttle) * 20.0, # Scaled down
                force=1.0 # Lower force = smoother acceleration
            )
        
        # 2. Steering joints (0 and 1)
        # We use a smaller force for steering to avoid 'snapping'
        for steering_joint in [0, 1]:
            p.setJointMotorControl2(
                self.car_id, 
                steering_joint, 
                p.POSITION_CONTROL, 
                targetPosition=float(steering), # Limit angle
                force=5.0
            )