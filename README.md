# EMARL-SAR: Explainable Multi-Agent Hierarchical Reinforcement Learning

This repository implements an explainable multi-agent hierarchical reinforcement learning (HRL) framework optimized for cooperative search-and-rescue operations in dynamic grid environments.

The system features high-level tabular option-critic planning (Manager) coordinated with low-level Deep Q-Network navigation policies (Worker) in PyTorch, accompanied by an explainability module (XAI) that computes real-time decision attributions and Q-value saliency gradients.

---

## 🚀 Getting Started

### 1. Installation & Setup

Clone this repository and install the required Python dependencies:

```bash
# Clone the repository (or navigate to the workspace root)
cd explainable-multiagent-hrl

# Install dependencies (requires PyTorch and NumPy)
pip install -r requirements.txt
```

### 2. Running the Interactive Dashboard & API Server

Start the local HTTP API and web server:

```bash
python src/server.py
```

By default, the server runs on `http://localhost:8000`. 

To open the interactive dashboard, open your web browser and navigate to:
👉 **[http://localhost:8000/HTML-DEMO/live_demo.html](http://localhost:8000/HTML-DEMO/live_demo.html)**

### 3. Running Training and Baseline Evaluation via Command Line

If you prefer to run the training workflow directly from the command line:

```bash
python src/main.py
```

This will run the training episodes, update the neural network policy weights under `src/weights/`, and print accuracy and policy loss convergence logs to the terminal.

---

## 📊 Dashboard Modules

The Neobrutalist interactive dashboard is divided into four main sections:

1. **Live Simulation**:
   - **Interactive Controls**: Click **Start** to run the simulation loop, **Step** for incremental ticks, or **Reset** to generate a new grid.
   - **Live Grid Canvas**: Centered 15×15 grid featuring coordinates tracking, scout drones fields of view, path debris blockages, charging pads, fire hazards, and victim rescue statuses.
   - **XAI Explanation Feed**: Monochrome typewriter terminal showing exact logical rules and policy rationales for high-level macro sub-goals and low-level directional steps.
   - **Saliency Scores**: Real-time attribution bars demonstrating how much target proximity, battery state, and hazards influenced the current steps.
   - **Performance scoreboards**: Dynamic tracking of exploration %, rescued victims, debris cleared, and average battery.

2. **Model Training**:
   - Configure training iteration length directly from the UI.
   - Stream Server-Sent Events (SSE) training statistics showing policy losses, training accuracy, and validation curves dynamically drawn on a dotted Neobrutalist graph canvas.

3. **Architecture & Algorithm**:
   - Explanation cards outlining policy decomposition between the Manager ($\pi_H$) and Worker ($\pi_L$).
   - Formulations of semi-Markov decision updates, Bellman errors, and gradient saliencies.

4. **Baselines & Metrics**:
   - Benchmarking comparison table illustrating the coordination success, path overlaps, and transparency of EMARL-SAR compared to traditional MARL.