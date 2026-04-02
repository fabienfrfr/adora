# On-adora

[![Codeberg](https://img.shields.io/badge/Codeberg-2185d0?style=for-the-badge&logo=gitea&logoColor=white)](https://codeberg.org/fabienfrfr/adora)
[![GitHub](https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/fabienfrfr/adora)


**A**ccelerated **D**ynamics **O**rchestration for **R**obotic **A**utonomy.

**Learning :** https://dora-rs.ai/docs/guides/getting-started/conversation_py


## Setup


(WIP : change devbox to devpod)

```bash
# Setup
devbox init && devbox add python@3.11 uv curl gnumake
devbox shell

# Init Project
uv init --python 3.11
uv add dora-rs dora-rs-cli genesis-world numpy opencv-python
(mkdir -p nodes && cd nodes && uv run dora new --kind node simulator --lang python && uv run dora new --kind node vla-brain --lang python && uv run dora new --kind node visualizer --lang python && uv run dora new --kind node controller --lang python)

# Create Components in the correct directory
touch graph.yml

```

## Launch

```bash
#dora destroy && pkill -9 dora
uv run dora build dataflow.yml --uv
uv run dora run dataflow.yml --uv

```

## Architecture

* **`simulation_op.py`**: Physics engine (genesis-world). Handles torque, mass, and friction.
* **`vla_op.py`**: VLA (Vision-Language-Action) logic.
* **`graph.yml`**: Dataflow orchestration via dora-rs.

---

**Sources:** [dora-rs.ai](https://dora-rs.ai) | [genesis-embodied-ai](https://genesis-embodied-ai.github.io/)