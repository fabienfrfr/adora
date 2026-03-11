import torch
import numpy as np
import cv2
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from dora import DoraStatus

class Operator:
    def __init__(self):
        # SmolVLA (450M) is the most efficient choice for real-time control
        self.model_id = "lerobot/smolvla_base"
        
        # AMD GPU (ROCm) is identified as 'cuda' by PyTorch
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Load the policy and processors for normalization
        self.policy = SmolVLAPolicy.from_pretrained(self.model_id).to(self.device).eval()
        self.preprocess, self.postprocess = make_pre_post_processors(
            self.policy.config, 
            self.model_id
        )
        print(f"SmolVLA successfully loaded on {self.device}")

    def on_event(self, dora_event, send_output):
        if dora_event["type"] == "INPUT" and dora_event["id"] == "image":
            # 1. Decode bytes to OpenCV image
            raw_bytes = np.frombuffer(dora_event["value"], np.uint8)
            frame = cv2.imdecode(raw_bytes, cv2.IMREAD_COLOR)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # 2. Prepare observation dictionary for LeRobot
            # Note: SmolVLA expects 'observation.image' in (C, H, W)
            data = {
                "observation.image": torch.tensor(frame_rgb).permute(2, 0, 1)
            }
            
            # Apply preprocessing (resize, normalization)
            batch = self.preprocess(data)
            
            # 3. Predict action using Flow-Matching
            with torch.inference_mode():
                # select_action returns the predicted action chunk
                predicted_action = self.policy.select_action(batch)
                # Unnormalize back to physical units
                action = self.postprocess(predicted_action)
            
            # Output: [linear_velocity, angular_velocity] as bytes
            # Flatten to take the first action of the predicted chunk
            action_payload = action[0].cpu().numpy().astype(np.float32).tobytes()
            send_output("action", action_payload)

        return DoraStatus.CONTINUE