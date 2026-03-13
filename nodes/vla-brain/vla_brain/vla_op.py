import torch
import numpy as np
import cv2
import os
from lerobot.policies.smolvla.modeling_smolvla import SmolVLAPolicy
from lerobot.policies.factory import make_pre_post_processors
from dora import DoraStatus

# Force CPU if no CUDA is found to avoid library initialization crashes
if not torch.cuda.is_available():
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

class Operator:
    """Dora operator for SmolVLA inference with auto-device detection."""

    def __init__(self):
        self.model_id = "lerobot/smolvla_base"
        
        # Hardware detection
        self.device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")
        
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

    def on_event(self, dora_event, send_output) -> DoraStatus:
        if dora_event["type"] == "INPUT" and dora_event["id"] == "image":
            # 1. Image handling (assuming it's fixed from previous step)
            try:
                storage = dora_event["value"]
                frame_raw = np.array(storage)
                
                # Handling compressed JPEG or raw buffer
                if frame_raw.ndim == 1:
                    frame = cv2.imdecode(frame_raw, cv2.IMREAD_COLOR)
                else:
                    frame = frame_raw
                
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            except Exception as e:
                return DoraStatus.CONTINUE

            # 2. Prepare Data with ALL required keys
            image_tensor = torch.from_numpy(frame_rgb).permute(2, 0, 1).float()
            
            # Create a dummy state vector (usually size 6 or 7 for robot arm)
            # SmolVLA will crash without this key
            state_tensor = torch.zeros(6) 

            data = {
                "observation.images.camera1": image_tensor,
                "observation.state": state_tensor, # <--- FIX: Missing key added
                "task": "Perform the task." 
            }
            
            # 3. Preprocess & Device Transfer
            batch = self.preprocess(data)
            batch = {k: v.to(self.device) if isinstance(v, torch.Tensor) else v for k, v in batch.items()}
            
            # 4. Inference
            with torch.inference_mode():
                predicted_action = self.policy.select_action(batch)
                action = self.postprocess(predicted_action)
            
            # 5. Send Action
            action_np = action[0].cpu().numpy().astype(np.float32)

            print(f"🧠 VLA Prediction -> Throttle: {action_np[0]:.4f} | Steering: {action_np[1]:.4f}")

            send_output("action", action_np.tobytes())

        return DoraStatus.CONTINUE