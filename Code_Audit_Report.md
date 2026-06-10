# Code Audit Report — Explainable Multi-Agent HRL Search & Rescue System

**Files audited:** `environment.py`, `high_level_agent.py`, `low_level_agent.py`, `explain.py`, `main.py`, `server.py`, `requirements.txt`  
**Severity levels:** 🔴 Critical · 🟠 Major · 🟡 Minor · 🔵 Style/Hygiene

---

## Executive Summary

The codebase runs without crashing and implements the broad structure of the paper's framework correctly (HRL hierarchy, SMDP option accumulation, BFS navigation, XAI saliency). However, it contains **one critical architectural flaw** that invalidates the deep learning component entirely, **three major logic bugs** affecting agent correctness, and **several minor/hygiene issues**. None of the bugs are syntax errors — they are all silent, runtime-safe mistakes that corrupt the intended behaviour or research validity.

---

## 🔴 Critical Bugs

### BUG-01 — DQN Weights Are Trained But Never Used for Decision-Making
**Files:** `low_level_agent.py`, `main.py`, `server.py`

**Problem:**  
`select_action()` accepts `pos` and `obs` as optional parameters. In both the training loop (`main.py`) and the inference server (`server.py`), it is always called with all three: `pos`, `sub_goal`, and `obs`:

```python
# main.py — every call site looks like this:
action_ll = ll_agent.select_action(
    agent_id, state_ll,
    pos=agent["pos"],        # ← always provided
    sub_goal=agent["sub_goal"],
    obs=obs[agent_id],       # ← always provided
    epsilon=epsilon_ll       # ← IGNORED
)
```

The first line of `select_action()` is:

```python
def select_action(self, agent_id, state_vector, pos=None, sub_goal=None, obs=None, epsilon=None):
    if pos is not None and obs is not None:
        return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)  # ← ALWAYS taken
    # DQN code below is NEVER reached
    ...
```

Since `pos` and `obs` are never `None` at any call site, the BFS pathfinder is called unconditionally. The DQN branch — the `policy_net` forward pass and epsilon-greedy logic — is **dead code**. `train_step()` still runs every step (consuming CPU/memory), Q-values are computed and losses are backpropagated, but the resulting network weights have **zero influence on any agent's behaviour**. The saved `.pth` files are behavioural no-ops.

This means the system is, in practice, **tabular Q-learning (high-level) + deterministic BFS (low-level)** — not a Deep Q-Network.

**Fix:**  
Either fully commit to the BFS design (remove `train_step` and DQN code) or fix the action selector to consult the DQN when the episode is in exploitation mode:

```python
def select_action(self, agent_id, state_vector, pos=None, sub_goal=None, obs=None, epsilon=None):
    if epsilon is None:
        epsilon = self.epsilon

    # Use BFS only during exploration; use DQN during exploitation
    if pos is not None and obs is not None and random.random() < epsilon:
        return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

    # DQN exploitation path
    with torch.no_grad():
        policy_net = self.get_policy_net(agent_id)
        q_values = policy_net(state_vector.unsqueeze(0))
        return int(q_values.argmax().item())
```

---

## 🟠 Major Bugs

### BUG-02 — Off-by-One in Drone Recharge Threshold
**Files:** `high_level_agent.py`, `low_level_agent.py`

**Problem:**  
The high-level agent decides to send a drone to a charging station when `battery <= 40`:

```python
# high_level_agent.py — get_state()
battery_low = 1 if battery <= 40 else 0
```

But the low-level pathfinder only triggers the Interact (recharge) action at `battery < 40` (strictly less than):

```python
# low_level_agent.py — select_action_pathfinder()
if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] < 40:
    return 4
```

When `battery == 40` exactly: the high-level sends the drone to a charging station, the drone arrives and stands on it, but the low-level refuses to trigger Action 4. The drone idles on the charger for one step, depletes battery to 39, and then finally recharges. This is a one-step wasted charge cycle and a source of unnecessary battery depletion.

**Fix:**  
Align both thresholds to `<= 40` (or any consistent value):

```python
# low_level_agent.py
if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] <= 40:
    return 4
```

---

### BUG-03 — Rescue Action Suppressed by Adjacent Debris
**Files:** `environment.py`

**Problem:**  
In `env.step()`, the interact action (action 4) checks for debris clearance **before** victim rescue:

```python
elif agent["role"] == "Rescue":
    cleared = False
    for idx, d_pos in enumerate(self.debris_locations):
        dist = abs(d_pos[0] - agent["pos"][0]) + abs(d_pos[1] - agent["pos"][1])
        if dist <= 1:          # ← adjacent OR on same cell
            # ... clear debris
            cleared = True
            break

    if not cleared:
        # c) Rescue Victim
        for vic_id, vic in self.victims.items():
            if vic["status"] == "scanned" and vic["pos"] == agent["pos"]:
                # ... rescue
```

If a victim is located adjacent to any debris (which is very likely on a cluttered 15×15 grid), the rover will repeatedly clear debris instead of rescuing the victim even when it is **standing directly on the victim's cell**. The rescue branch is only reached after all adjacent debris is gone. This can cause indefinite rescue failure when debris regeneration is simulated or when the layout is unfavourable.

**Fix:**  
Check for rescue first (exact position match has higher priority than proximity-based debris):

```python
elif agent["role"] == "Rescue":
    # Priority 1: Rescue victim if standing on them
    rescued = False
    for vic_id, vic in self.victims.items():
        if vic["status"] == "scanned" and vic["pos"] == agent["pos"]:
            vic["status"] = "rescued"
            agent["score"] += 1
            rewards[agent_id] += 40.0
            rewards["A1"] += 15.0
            rewards["A2"] += 15.0
            info["xai_logs"][agent_id] = f"Rescued Victim {vic_id} at {vic['pos']}!"
            rescued = True
            break

    # Priority 2: Clear adjacent debris if no rescue
    if not rescued:
        for idx, d_pos in enumerate(self.debris_locations):
            dist = abs(d_pos[0] - agent["pos"][0]) + abs(d_pos[1] - agent["pos"][1])
            if dist <= 1:
                # ... clear debris
                break
```

---

### BUG-04 — Fabricated Validation Metrics
**Files:** `main.py`, `server.py`

**Problem:**  
The `val_acc` and `val_loss` metrics reported during training are not real validation metrics. They are the training metrics with synthetic random noise added:

```python
# main.py (and duplicated in server.py)
val_acc  = max(0.0, success_rate - (random.random() * 4.0))     # ← fake
val_loss = loss_val * (1.05 + (random.random() * 0.05))          # ← fake
```

There is no holdout environment or separate evaluation set. These values are streamed to the browser and plotted as "Validation Accuracy / Loss" curves, creating the visual impression of proper generalisation testing. In a research or demonstration context, this is misleading.

**Fix:**  
Either remove the validation metrics entirely and plot only training metrics, or implement a genuine evaluation by running a separate fixed-seed episode after each training episode with `epsilon=0.0`:

```python
# After each training episode, run one greedy eval episode
env_eval = SearchRescueEnv()  # separate instance
env_eval.reset()
# ... run with epsilon=0.0, no training, record rescue rate
val_acc = eval_success_rate
val_loss = eval_loss
```

---

## 🟡 Minor Bugs

### BUG-05 — Drone Coordination State Is Hardcoded to Zero
**File:** `high_level_agent.py`

The `overlap` feature in the drone's high-level state tuple is always `0`:

```python
def get_state(self, agent_id, agent_obs):
    ...
    overlap = 0   # ← never assigned; always 0
    return (battery_low, unexplored, overlap)
```

The intent is to detect when two drones are targeting the same quadrant. Since this is always 0, both drones will converge on the same quadrant whenever the Q-table recommends it, reducing search coverage. The third dimension of every state tuple is wasted, and the Q-table has half as many effective states as intended.

**Fix:**  
Populate `overlap` by comparing this agent's current sub-goal against the peer drone's sub-goal (accessible via a shared reference to `env.agents`). Pass `env.agents` as a parameter to `get_state`, or pre-compute a simple overlap flag in the training loop before calling `get_state`.

---

### BUG-06 — Epsilon Decay Is Too Slow and Resets Its Reference Each Call
**Files:** `main.py`, `server.py`

```python
epsilon_hl = max(0.05, hl_agent.epsilon * (0.95 ** (ep / 10)))
epsilon_ll = max(0.05, ll_agent.epsilon * (0.95 ** (ep / 10)))
```

`hl_agent.epsilon` is the fixed constructor default (0.15), not a running value. At episode 200 the epsilon is still ~0.054 — barely at the floor. Standard DQN schedules reach minimum epsilon within the first 10–20% of training. With 50 episodes (the default), epsilon barely moves:

| Episode | Effective ε |
|---------|------------|
| 1       | 0.149      |
| 10      | 0.143      |
| 25      | 0.132      |
| 50      | 0.116      |

**Fix:**  
Use a linear or exponential decay that reaches `epsilon_min` by ~50% of training:

```python
epsilon_hl = max(0.05, 1.0 * (0.95 ** ep))   # starts at 1.0, fast decay
epsilon_ll = max(0.05, 1.0 * (0.95 ** ep))
```

---

### BUG-07 — Fire Spread Blocked by Inactive (Dead) Agents
**File:** `environment.py`

The fire spread check iterates over all agents to prevent fire from spawning on an occupied cell, but it includes inactive agents:

```python
agent_on = False
for ag in self.agents.values():          # ← includes inactive agents
    if ag["pos"] == list(neighbor):
        agent_on = True
```

A destroyed drone or depleted rover still blocks fire from spreading to its last known position for the rest of the episode. This creates invisible ghost obstacles in the fire propagation model.

**Fix:**  
Filter to active agents only:

```python
if ag["active"] and ag["pos"] == list(neighbor):
    agent_on = True
```

---

### BUG-08 — `explain.py` Calls `backward()` Without `policy_net.eval()`
**File:** `explain.py`

`compute_saliency()` runs a forward and backward pass through the policy network to compute input gradients:

```python
policy_net = low_level_agent.get_policy_net(agent_id)
q_values = policy_net(state_var.unsqueeze(0))
q_values[0, action_idx].backward()
```

The network is not put into `eval()` mode first. While `QNetwork` has no `Dropout` or `BatchNorm` layers (so behaviour is identical in train/eval mode here), this is a correctness assumption that will break if the architecture is ever expanded. Additionally, `backward()` accumulates gradients in the policy network's parameter `.grad` buffers even though they are never used — creating spurious gradient state that could confuse a subsequent `optimizer.step()` call.

**Fix:**

```python
policy_net = low_level_agent.get_policy_net(agent_id)
policy_net.eval()
q_values = policy_net(state_var.unsqueeze(0))
q_values[0, action_idx].backward()
gradients = state_var.grad.cpu().numpy()
policy_net.train()   # restore training mode
# Also zero out network param grads to avoid interference:
policy_net.zero_grad()
```

---

### BUG-09 — Redundant `None` Check in SMDP Reward Accumulation
**Files:** `main.py`, `server.py`

```python
if option_accumulated_rewards[agent_id] is not None:
    option_accumulated_rewards[agent_id] += step_rewards[agent_id]
```

`option_accumulated_rewards` is initialised to `{k: 0.0 for k in env.agents}` — it is **never** `None`. This check is always `True` and is dead code. It also masks the intent (this should always accumulate).

**Fix:** Remove the guard and write the accumulation directly:

```python
option_accumulated_rewards[agent_id] += step_rewards[agent_id]
```

---

## 🔵 Style / Hygiene Issues

### BUG-10 — Massive Code Duplication: Training Loop
**Files:** `main.py`, `server.py`

The complete training loop (approx. 90 lines) is copy-pasted verbatim between `train_hrl()` in `main.py` and the `/api/train` SSE handler in `server.py`. Any future fix to the training logic must be applied twice or the two diverge silently. This is a direct violation of the DRY (Don't Repeat Yourself) principle.

**Fix:**  
Move the training loop into a shared function in `main.py` (or a new `trainer.py`) that accepts a callback for per-epoch metrics:

```python
def train_hrl(env, hl_agent, ll_agent, on_epoch_end=None, num_episodes=50):
    for ep in range(1, num_episodes + 1):
        ...  # single copy of training logic
        if on_epoch_end:
            on_epoch_end(metrics)

# server.py
def sse_callback(metrics):
    self.wfile.write(f"data: {json.dumps(metrics)}\n\n".encode())
    self.wfile.flush()

train_hrl(env, hl_agent, ll_agent, on_epoch_end=sse_callback, num_episodes=num_episodes)
```

---

### BUG-11 — Unused Imports
**Files:** `main.py`, `server.py`

```python
# main.py
import sys    # never used

# server.py
import time   # never used
```

These should be removed.

---

### BUG-12 — `requirements.txt` Lists Packages That Are Never Imported

| Package | Imported in codebase? |
|---------|----------------------|
| `torch` | ✅ Yes |
| `numpy` | ✅ Yes |
| `gymnasium` | ❌ No — the env is custom, not a Gym subclass |
| `matplotlib` | ❌ No — charts are rendered in the browser |
| `seaborn` | ❌ No |
| `tensorboard` | ❌ No |

`gymnasium` is particularly misleading — a reader would expect the environment to extend `gym.Env`, but `SearchRescueEnv` is a standalone class with no Gym interface (`reset()` returns a dict, `step()` returns 4 values, no `observation_space` or `action_space`). This also means the environment cannot be used with any standard MARL library (RLlib, PettingZoo, SB3) without a wrapper.

**Fix:**  
Clean up `requirements.txt` to only list what is actually used:

```
torch
numpy
```

---

### BUG-13 — No Thread Safety in `server.py`
**File:** `server.py`

`env`, `hl_agent`, and `ll_agent` are module-level globals shared by all incoming HTTP requests. If a browser calls `/api/simulate` and `/api/train` simultaneously (e.g., in two tabs), both handlers mutate `env.agents`, `env.victims`, and the Q-tables concurrently. Python's GIL prevents true parallel execution for pure Python, but interleaved execution across `env.step()` calls can still corrupt state.

**Fix:**  
Add a threading lock around all handler state modifications:

```python
import threading
_state_lock = threading.Lock()

# In do_GET:
with _state_lock:
    next_obs, rewards, done, info = env.step(micro_actions)
```

Or switch to a proper async framework (FastAPI + asyncio) with a single event loop.

---

## Summary Table

| ID | Severity | File(s) | Short Description |
|----|----------|---------|-------------------|
| BUG-01 | 🔴 Critical | `low_level_agent.py`, `main.py`, `server.py` | DQN never used — pathfinder always takes over; neural net weights are behavioural no-ops |
| BUG-02 | 🟠 Major | `high_level_agent.py`, `low_level_agent.py` | Drone recharge threshold off-by-one (`<=40` vs `<40`); drone idles on charger at exactly 40% battery |
| BUG-03 | 🟠 Major | `environment.py` | Debris-clear takes priority over rescue; rover cannot rescue a victim if any debris is adjacent |
| BUG-04 | 🟠 Major | `main.py`, `server.py` | `val_acc`/`val_loss` are fabricated with random noise; no real validation set exists |
| BUG-05 | 🟡 Minor | `high_level_agent.py` | `overlap` coordinate state is always `0`; drone-drone coordination is never encoded |
| BUG-06 | 🟡 Minor | `main.py`, `server.py` | Epsilon decay too slow and anchored to fixed default rather than a running variable |
| BUG-07 | 🟡 Minor | `environment.py` | Fire spread checks inactive agents as obstacles, creating ghost blockers |
| BUG-08 | 🟡 Minor | `explain.py` | `backward()` called without `eval()` mode; leaves spurious `.grad` state on policy net params |
| BUG-09 | 🟡 Minor | `main.py`, `server.py` | Redundant `is not None` check on reward accumulator that is always `0.0` |
| BUG-10 | 🔵 Style | `main.py`, `server.py` | ~90-line training loop duplicated verbatim; DRY violation |
| BUG-11 | 🔵 Style | `main.py`, `server.py` | `sys` and `time` imported but never used |
| BUG-12 | 🔵 Style | `requirements.txt` | `gymnasium`, `matplotlib`, `seaborn`, `tensorboard` listed but never imported |
| BUG-13 | 🔵 Style | `server.py` | No thread safety on shared global state across concurrent HTTP requests |

---

## Priority Fix Order

If you have limited time, address bugs in this order:

1. **BUG-01** — The DQN architecture is the whole point of the low-level agent. Fix `select_action()` to actually use the trained network.
2. **BUG-04** — Remove or properly implement validation metrics before any demo or submission.
3. **BUG-03** — Rescue blocking by debris will silently prevent victims from being saved in many layouts.
4. **BUG-02** — One-step recharge delay is a minor inefficiency but is easy to fix.
5. **BUG-05** — Implement overlap detection to enable real drone coordination.
6. **BUG-10** — Refactor duplicated training loop before extending the code further.
