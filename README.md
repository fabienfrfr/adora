# ADORA

**A**ccelerated **D**ynamics **O**rchestration for **R**obotic **A**utonomy.

## Setup

```bash
# Setup
devbox init && devbox add python@3.13 uv curl
devbox shell

# Init Project
uv init --lib .
uv add dora-rs pybullet numpy opencv-python

# Create Components in the correct directory
touch src/adora/simulation_op.py src/adora/vla_op.py graph.yml

```

## Launch

```bash
dora up
dora start graph.yml

```

## Architecture

* **`simulation_op.py`**: Physics engine (PyBullet). Handles torque, mass, and friction.
* **`vla_op.py`**: VLA (Vision-Language-Action) logic.
* **`graph.yml`**: Dataflow orchestration via dora-rs.

---

**Sources:** [dora-rs.ai](https://dora-rs.ai) | [pybullet.org](https://pybullet.org)