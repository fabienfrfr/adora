"""Genesis simulation operator with procedural terrain and a modern Tesla Model 3."""

import io

import genesis as gs
import numpy as np
from dora import DoraStatus
from PIL import Image


class Operator:
    """Handles the Genesis physics simulation, camera rendering, and car control."""

    def __init__(self):
        """Initialize the scene, terrain, vehicle, and lighting."""
        # Initialize Genesis with CPU backend for maximum stability
        gs.init(backend=gs.cpu)

        self.scene = gs.Scene(
            rigid_options=gs.options.RigidOptions(
                dt=0.01,
                constraint_solver=gs.constraint_solver.Newton,
            )
        )

        # --- PROCEDURAL TERRAIN ---
        self.grid_size = 128
        x = np.linspace(-15, 15, self.grid_size)
        y = np.linspace(-15, 15, self.grid_size)
        xv, yv = np.meshgrid(x, y)
        dist = np.sqrt(xv**2 + yv**2)
        z = 0.5 * np.sin(dist * 0.5) + (dist * 0.1)

        self.terrain = self.scene.add_entity(
            gs.morphs.Terrain(
                height_field=z,
                pos=(0, 0, 0),
                horizontal_scale=0.4,
                vertical_scale=1.5,
            ),
            surface=gs.surfaces.Rough(color=(0.2, 0.2, 0.2)),
        )

        # --- VEHICLE SETUP ---
        car_model = "xml/tesla_model_3/tesla_model_3.xml"
        try:
            self.car = self.scene.add_entity(
                gs.morphs.MJCF(file=car_model, pos=(0, 0, 1.0)),
            )
        except Exception as e:
            print(f"⚠️ Could not load {car_model}: {e}")
            print("🔄 Falling back to Panda robot arm.")
            self.car = self.scene.add_entity(
                gs.morphs.MJCF(
                    file="xml/franka_emika_panda/panda.xml", pos=(0, 0, 1.0)),
            )
        # --- CAMERA ---
        # Fixed 224x224 for VLA, FOV 50 for closer zoom
        self.cam = self.scene.add_camera(res=(224, 224), fov=25)

        # Finalize the scene
        self.scene.build()

        # Control indices for the Tesla Model 3
        self.drive_joints = [0, 1, 2, 3]  # All-wheel drive
        self.steer_joints = [4, 5]        # Front steering

    def on_event(self, dora_event: dict, send_output) -> DoraStatus:
        """Main event loop for the dora node."""
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                self._handle_tick(send_output)
            elif dora_event["id"] == "action":
                self._handle_action(dora_event)
        return DoraStatus.CONTINUE

    def _handle_tick(self, send_output) -> None:
        """Steps the physics and sends a high-contrast rendered frame."""
        self.scene.step()

        # Update camera to follow the car closely
        car_pos = self.car.get_pos()
        # Offset moved from -3.5 to -2.5 to be physically closer to the trunk
        self.cam.set_pose(
            lookat=car_pos,
            pos=car_pos + np.array([-2.5, 0, 1.2]),
        )

        # Render RGB frame
        rgb, _, _, _ = self.cam.render()
        img = Image.fromarray(rgb, "RGB")

        # Export as JPEG bytes
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        send_output("image", buffer.getvalue())

    def _handle_action(self, event: dict) -> None:
        """Processes incoming steering and throttle actions."""
        # Convert arrow array to numpy
        action = event["value"].to_numpy().view(np.float32)

        if action.size >= 2:
            # action[0]: Throttle, action[1]: Steering
            self.car.control_dofs_velocity(action[0] * 30.0, self.drive_joints)
            self.car.control_dofs_position(action[1] * 0.5, self.steer_joints)
