"""PyBullet simulation operator focused on physics and state output."""

import io
import time
import pybullet as p
import pybullet_data
import numpy as np
from PIL import Image
from dora import DoraStatus

class Operator:
    """Handles PyBullet physics and image generation."""

    def __init__(self):
        """Initialize headless physics engine and load assets."""
        # Headless connection for better performance and CI/CD compatibility
        p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)
        
        # Asset loading
        self.stadium_id = p.loadSDF("stadium.sdf")[0]
        self.car_id = p.loadURDF("racecar/racecar.urdf", [0, 0, 0.02])
        
        # Physics tuning
        for i in range(p.getNumJoints(self.car_id)):
            p.changeDynamics(self.car_id, i, lateralFriction=1.0, rollingFriction=0.01)

        self.width, self.height = 224, 224

    def on_event(self, dora_event: dict, send_output) -> DoraStatus:
        """Dispatcher for incoming dora events."""
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                self._handle_tick(dora_event, send_output)
            elif dora_event["id"] == "action":
                self._handle_action(dora_event)
        return DoraStatus.CONTINUE

    def _handle_tick(self, event: dict, send_output) -> None:
        """Step physics and broadcast camera frame."""
        p.stepSimulation()
        
        # Camera logic
        pos, orn = p.getBasePositionAndOrientation(self.car_id)
        mat = p.getMatrixFromQuaternion(orn)
        forward = [mat[0], mat[3], mat[6]]
        
        view_mat = p.computeViewMatrix(
            [pos[0], pos[1], pos[2] + 0.2],
            [pos[0] + forward[0], pos[1] + forward[1], pos[2]],
            [0, 0, 1]
        )
        proj_mat = p.computeProjectionMatrixFOV(60, 1, 0.1, 10)
        
        # Image capture
        _, _, rgb, _, _ = p.getCameraImage(
            self.width, self.height, view_mat, proj_mat,
            renderer=p.ER_TINY_RENDERER
        )
        
        # Efficient JPEG encoding
        frame = np.reshape(rgb, (self.height, self.width, 4))[:, :, :3]
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        
        # Output to both Brain and Visualizer nodes
        send_output("image", buffer.getvalue())

    def _handle_action(self, event: dict) -> None:
        """Apply motor control signals from VLA."""
        raw_data = event["value"].to_numpy()
        action = raw_data.view(np.float32)

        if action.size < 2:
            return

        throttle, steering = action[0], action[1]
        
        # Driving logic
        for joint in [2, 3, 5, 7]:
            p.setJointMotorControl2(
                self.car_id, joint, p.VELOCITY_CONTROL, 
                targetVelocity=float(throttle) * 20.0, force=1.0
            )
        
        # Steering logic
        for steering_joint in [0, 1]:
            p.setJointMotorControl2(
                self.car_id, steering_joint, p.POSITION_CONTROL, 
                targetPosition=float(steering), force=5.0
            )