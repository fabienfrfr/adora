"""PyBullet simulation operator with textured relief and track markings."""

import io
import pybullet as p
import pybullet_data
import numpy as np
from PIL import Image
from dora import DoraStatus

class Operator:
    def __init__(self):
        p.connect(p.DIRECT)
        p.setAdditionalSearchPath(pybullet_data.getDataPath())
        p.setGravity(0, 0, -9.81)

        # --- PROCEDURAL RELIEF TRACK ---
        self.grid_size = 128
        x = np.linspace(-15, 15, self.grid_size)
        y = np.linspace(-15, 15, self.grid_size)
        xv, yv = np.meshgrid(x, y)
        
        # Create a "Bowl" shape with hills on the sides
        # The center is flatter for the "track"
        dist = np.sqrt(xv**2 + yv**2)
        z = 0.5 * np.sin(dist * 0.5) + (dist * 0.1) # Hills and valleys
        
        height_data = z.flatten().tolist()

        terrain_shape = p.createCollisionShape(
            shapeType=p.GEOM_HEIGHTFIELD,
            meshScale=[0.4, 0.4, 1.5],
            heightfieldData=height_data,
            numHeightfieldRows=self.grid_size,
            numHeightfieldColumns=self.grid_size
        )
        self.terrain_id = p.createMultiBody(0, terrain_shape)
        
        # Visual color for terrain visibility
        p.changeVisualShape(self.terrain_id, -1, rgbaColor=[0.4, 0.4, 0.4, 1]) # Grey rock

        # --- ADDING VISUAL TRACK MARKERS (BUMPERS) ---
        # We place some red/white blocks to define a path in the relief
        for i in range(12):
            angle = (i / 12) * 2 * np.pi
            px, py = 6 * np.cos(angle), 6 * np.sin(angle)
            # Find height at this point (approx)
            pz = 0.5 * np.sin(6 * 0.5) + (6 * 0.1)
            marker = p.createVisualShape(p.GEOM_SPHERE, radius=0.3, rgbaColor=[1, 0, 0, 1])
            p.createMultiBody(0, -1, marker, [px, py, pz + 0.5])

        # --- ROBOT ---
        # Spawn higher to land on the relief safely
        self.car_id = p.loadURDF("racecar/racecar.urdf", [0, 0, 2.0])
        
        for i in range(p.getNumJoints(self.car_id)):
            p.changeDynamics(self.car_id, i, lateralFriction=2.0, rollingFriction=0.02)

        self.width, self.height = 224, 224

    def on_event(self, dora_event: dict, send_output) -> DoraStatus:
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                self._handle_tick(send_output)
            elif dora_event["id"] == "action":
                self._handle_action(dora_event)
        return DoraStatus.CONTINUE

    def _handle_tick(self, send_output) -> None:
        p.stepSimulation()
        
        pos, orn = p.getBasePositionAndOrientation(self.car_id)
        mat = p.getMatrixFromQuaternion(orn)
        forward = [mat[0], mat[3], mat[6]]
        
        # REAR-HIGH CAMERA (Third Person View)
        # 2.0m behind, 1.2m above the car
        view_mat = p.computeViewMatrix(
            [pos[0] - forward[0] * 2.0, pos[1] - forward[1] * 2.0, pos[2] + 1.2],
            [pos[0] + forward[0] * 3, pos[1] + forward[1] * 3, pos[2]],
            [0, 0, 1]
        )
        proj_mat = p.computeProjectionMatrixFOV(75, 1, 0.1, 30)
        
        _, _, rgb, _, _ = p.getCameraImage(self.width, self.height, view_mat, proj_mat, renderer=p.ER_TINY_RENDERER)
        
        frame = np.reshape(rgb, (self.height, self.width, 4))[:, :, :3]
        img = Image.fromarray(frame.astype('uint8'), 'RGB')
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        send_output("image", buffer.getvalue())

    def _handle_action(self, event: dict) -> None:
        action = event["value"].to_numpy().view(np.float32)
        if action.size < 2: return
        
        # Increase force to climb the hills
        for joint in [2, 3, 5, 7]:
            p.setJointMotorControl2(self.car_id, joint, p.VELOCITY_CONTROL, 
                                    targetVelocity=float(action[0]) * 20.0, force=5.0)
        for sj in [0, 1]:
            p.setJointMotorControl2(self.car_id, sj, p.POSITION_CONTROL, 
                                    targetPosition=float(action[1]) * 0.6, force=10.0)