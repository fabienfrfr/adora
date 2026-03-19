"""
Genesis simulation operator for the MIT Racecar.
Loads URDF/Xacro dynamically from GitHub and integrates with dora-rs.
"""

import io
import os
import requests
import xacro
import numpy as np
import genesis as gs
from PIL import Image
from dora import DoraStatus

class Operator:
    """Handles dynamic loading of Xacro models and Genesis physics simulation."""

    def __init__(self):
        """Initialize Genesis, download the Racecar model, and build the scene."""
        # Initialize Genesis (using GPU if available, fallback to CPU)
        gs.init(backend=gs.gpu)

        self.scene = gs.Scene(
            rigid_options=gs.options.RigidOptions(
                dt=0.01,
                constraint_solver=gs.constraint_solver.Newton,
            )
        )

        # --- MODEL LOADING (Dynamic Xacro to URDF) ---
        self.model_url = "https://raw.githubusercontent.com/mit-racecar/racecar_gazebo/master/racecar_description/urdf/racecar.xacro"
        self.urdf_path = "processed_racecar.urdf"
        
        self._prepare_model()

        # --- SCENE SETUP ---
        self.plane = self.scene.add_entity(gs.morphs.Plane())
        
        try:
            self.car = self.scene.add_entity(
                gs.morphs.URDF(file=self.urdf_path, pos=(0, 0, 0.1), fixed=False)
            )
        except Exception as e:
            print(f"⚠️ Error loading Racecar: {e}")
            # Fallback to a primitive or simpler model if needed
            self.car = self.scene.add_entity(gs.morphs.Box(pos=(0, 0, 0.5)))

        # --- CAMERA ---
        self.cam = self.scene.add_camera(res=(224, 224), fov=30)
        self.scene.build()

        # Joint mapping based on the provided Xacro structure
        self.drive_joints = ["left_rear_wheel_joint", "right_rear_wheel_joint"]
        self.steer_joints = ["left_steering_hinge_joint", "right_steering_hinge_joint"]

    def _prepare_model(self):
        """Downloads Xacro, patches ROS paths, and converts to pure URDF."""
        print(f"Fetching model from: {self.model_url}")
        response = requests.get(self.model_url)
        if response.status_code != 200:
            raise RuntimeError("Failed to download Xacro from GitHub.")

        # Patch 'package://' paths to relative local paths for Genesis
        raw_xacro = response.text.replace("package://racecar_description/", "./")
        
        # Convert Xacro string to URDF
        doc = xacro.process_utils.xml.dom.minidom.parseString(raw_xacro)
        xacro.process_doc(doc)
        
        with open(self.urdf_path, "w", encoding="utf-8") as f:
            f.write(doc.toprettyxml(indent='  '))
        print(f"✅ Model converted and saved to {self.urdf_path}")

    def on_event(self, dora_event: dict, send_output) -> DoraStatus:
        """Main event loop processing dora-rs inputs."""
        if dora_event["type"] == "INPUT":
            if dora_event["id"] == "tick":
                self._step_simulation(send_output)
            elif dora_event["id"] == "control":
                self._handle_control(dora_event)
        return DoraStatus.CONTINUE

    def _step_simulation(self, send_output):
        """Advances physics and renders the current frame."""
        self.scene.step()

        # Camera tracking
        car_pos = self.car.get_pos()
        self.cam.set_pose(
            lookat=car_pos,
            pos=car_pos + np.array([-1.5, 0, 0.8]),
        )

        # Rendering
        rgb, _, _, _ = self.cam.render()
        img = Image.fromarray(rgb)
        
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        send_output("image", buffer.getvalue())

    def _handle_control(self, event: dict):
        """Applies steering and velocity commands to the car joints."""
        # Expecting a numpy array [steer_angle, velocity]
        data = event["value"].to_numpy().view(np.float32)
        
        if data.size >= 2:
            steer_angle, velocity = data[0], data[1]
            
            # Position control for steering (Ackermann-ish)
            self.car.control_joint_position(
                [steer_angle, steer_angle], 
                joint_names=self.steer_joints
            )
            
            # Velocity control for rear-wheel drive
            self.car.control_joint_velocity(
                [velocity, velocity], 
                joint_names=self.drive_joints
            )