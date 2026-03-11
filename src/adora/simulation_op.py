import pybullet as p
import pybullet_data
import numpy as np
import cv2
from dora import DoraStatus

class Operator:
    def __init__(self):
        # Connect to PyBullet (GUI for visualization, DIRECT for headless)
        p.connect(p.GUI)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        
        # Setup environment
        p.loadURDF("plane.urdf")
        self.car_id = p.loadURDF("racecar/racecar.urdf", [0, 0, 0.05])
        
        # SmolVLA standard input size
        self.width, self.height = 224, 224

    def on_event(self, dora_event, send_output):
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                # 1. Update Physics
                p.stepSimulation()
                
                # 2. Capture POV Camera
                # Get car position/orientation for camera placement
                pos, orn = p.getBasePositionAndOrientation(self.car_id)
                mat = p.getMatrixFromOrn(orn)
                forward_vec = [mat[0], mat[3], mat[6]]
                
                cam_eye = [pos[0], pos[1], pos[2] + 0.2]
                cam_target = [pos[0] + forward_vec[0], pos[1] + forward_vec[1], pos[2]]
                
                view_matrix = p.computeViewMatrix(cam_eye, cam_target, [0, 0, 1])
                proj_matrix = p.computeProjectionMatrixFOV(60, 1, 0.1, 10)
                
                # Render image
                _, _, rgb, _, _ = p.getCameraImage(self.width, self.height, view_matrix, proj_matrix)
                
                # 3. Extract RGB and send to VLA
                frame = np.reshape(rgb, (self.height, self.width, 4))[:, :, :3]
                img_bytes = cv2.imencode(".jpg", frame)[1].tobytes()
                send_output("image", img_bytes)

            elif dora_event["id"] == "action":
                # 4. Apply Action from VLA
                action = np.frombuffer(dora_event["value"], np.uint8 if len(dora_event["value"]) == 0 else np.float32)
                if action.size >= 2:
                    throttle, steering = action[0], action[1]
                    
                    # Racecar indices: 2, 3, 5, 7 are driving wheels; 0 is steering
                    for joint in [2, 3, 5, 7]:
                        p.setJointMotorControl2(self.car_id, joint, p.VELOCITY_CONTROL, targetVelocity=throttle * 15)
                    p.setJointMotorControl2(self.car_id, 0, p.POSITION_CONTROL, targetPosition=steering)

        return DoraStatus.CONTINUE