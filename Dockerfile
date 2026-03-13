# 1. Use the official ultra-light uv-python image
FROM astral-sh/uv:python3.11-slim

# 2. Minimum system deps for OpenCV and PyBullet (No junk)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgl1-mesa-glx libglew-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 3. Hardware switch (Build-time only)
ARG ACCELERATOR=cuda
RUN if [ "$ACCELERATOR" = "rocm" ] ; then \
    uv pip install --system torch torchvision --index-url https://download.pytorch.org/whl/rocm6.2 ; \
    else \
    uv pip install --system torch torchvision ; \
    fi

# 4. Install only the essentials
# Using --no-cache to keep the image slim
RUN uv pip install --system --no-cache \
    "lerobot[smolvla]" \
    dora-rs \
    pybullet \
    opencv-python

# 5. Copy only the source code
COPY src/ ./src/
COPY graph.yml .

# 6. Run
CMD ["sh", "-c", "dora up && dora start graph.yml"]