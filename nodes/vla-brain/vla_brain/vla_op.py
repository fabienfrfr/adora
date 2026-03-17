"""Dora operator for SmolVLA inference with real-time text instructions."""

import os
import cv2
import torch
import numpy as np
from dora import DoraStatus
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors

# Force CPU if no CUDA is found to avoid library initialization crashes
if not torch.cuda.is_available():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

class Operator:
    """Dora operator for SmolVLA inference with auto-device detection."""

    def __init__(self):
        """Initialize model, processors and default instruction."""
        self.model_id = "lerobot/smolvla_base"
        self.current_instruction = "Drive safely"
        
        # Hardware detection
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if self.device.type == "cpu":
            torch.set_num_threads(8)

        # Load policy on detected device
        self.policy = SmolVLAPolicy.from_pretrained(self.model_id).to(self.device).eval()

        # Instantiate processors with device override
        device_str = str(self.device)
        self.preprocess, self.postprocess = make_pre_post_processors(
            self.policy.config,
            self.model_id,
            preprocessor_overrides={
                "device_processor": {"device": device_str}
            }
        )
        print(f"✅ SmolVLA loaded on {self.device}")

    def on_event(self, dora_event: dict, send_output) -> DoraStatus:
        """Handle image frames and instruction updates."""
        if dora_event["type"] != "INPUT":
            return DoraStatus.CONTINUE

        # Update instruction in real-time
        if dora_event["id"] == "instruction":
            self.current_instruction = dora_event["value"].to_string()
            print(f"📝 New Instruction: {self.current_instruction}")
            return DoraStatus.CONTINUE

        # Process image for inference
        if dora_event["id"] == "image":
            self._handle_inference(dora_event, send_output)

        return DoraStatus.CONTINUE

    def _handle_inference(self, event: dict, send_output) -> None:
        """Perform VLA inference and send motor actions."""
        # 1. Image decoding
        storage = event["value"]
        frame_raw = np.array(storage)
        
        # Decode if bytes, else use as is
        frame = cv2.imdecode(frame_raw, cv2.IMREAD_COLOR) if frame_raw.ndim == 1 else frame_raw
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 2. Prepare Data for SmolVLA
        image_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float()
        state_tensor = torch.zeros(6)  # Standard dummy state for SmolVLA

        data = {
            "observation.images.camera1": image_tensor,
            "observation.state": state_tensor,
            "task": self.current_instruction 
        }
        
        # 3. Preprocess & Device Transfer
        batch = self.preprocess(data)
        batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v 
                 for k, v in batch.items()}
        
        # 4. Inference
        with torch.inference_mode():
            predicted_action = self.policy.select_action(batch)
            action = self.postprocess(predicted_action)
        
        # 5. Send Action as float32 bytes
        action_np = action[0].cpu().numpy().astype(np.float32)
        
        print(f"🧠 Prompt: '{self.current_instruction}' | "
              f"Thr: {action_np[0]:.2f} | Str: {action_np[1]:.2f}")

        send_output("action", action_np.tobytes())