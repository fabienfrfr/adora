FROM mcr.microsoft.com/devcontainers/python:3.11

# Install system dependencies for OpenCV and AMD GPU rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    xterm \
    libxcb1 \
    libx11-6 \
    libglx-mesa0 \
    libgl1-mesa-dri \
    libglapi-mesa \
    libosmesa6 \
    libexif12 \
    libvulkan1 \
    mesa-utils \
    pciutils \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install uv (modern python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/bin/uv

# Create directory for DRM device identification
RUN mkdir -p /usr/share/libdrm

# Set library path for hardware rendering
ENV LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu