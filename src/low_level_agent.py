import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque


class QNetwork(nn.Module):
    """
    Deeper 3-layer DQN with LayerNorm for stable training.
    Input: 12-dim state vector
    Hidden: 128 → 128 → 128 with LayerNorm and ReLU
    Output: 5 Q-values (N, S, E, W, Interact)
    """
    def __init__(self, input_dim=12, output_dim=5, hidden=128):
        super(QNetwork, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden),
            nn.LayerNorm(hidden),
            nn.ReLU(),
            nn.Linear(hidden, output_dim)
        )

    def forward(self, x):
        return self.fc(x)


class LowLevelAgent:
    def __init__(self, lr=5e-4, gamma=0.95, epsilon=0.15, memory_size=20000, batch_size=128):
        self.gamma = gamma
        self.epsilon = epsilon
        self.batch_size = batch_size

        # Separate experience replay buffers (larger for better coverage)
        self.memory_drone = deque(maxlen=memory_size)
        self.memory_rover = deque(maxlen=memory_size)

        # PyTorch device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        # Policy and target networks — Drones and Rover share architecture, separate weights
        self.policy_net_drone = QNetwork().to(self.device)
        self.target_net_drone = QNetwork().to(self.device)
        self.target_net_drone.load_state_dict(self.policy_net_drone.state_dict())
        self.optimizer_drone = optim.Adam(self.policy_net_drone.parameters(), lr=lr)

        self.policy_net_rover = QNetwork().to(self.device)
        self.target_net_rover = QNetwork().to(self.device)
        self.target_net_rover.load_state_dict(self.policy_net_rover.state_dict())
        self.optimizer_rover = optim.Adam(self.policy_net_rover.parameters(), lr=lr)

        # Huber loss — more robust to outlier Q-value errors than MSE
        self.loss_fn = nn.SmoothL1Loss()

        # Position history to detect oscillation/stuck states
        self.pos_history = {
            "A1": deque(maxlen=6),
            "A2": deque(maxlen=6),
            "A3": deque(maxlen=6)
        }

    def get_state_vector(self, agent_id, pos, sub_goal, obs, grid_size=15):
        """
        Extracts features and returns a 12-dimensional state vector.
        Features:
        - 2: Relative normalized vector to sub-goal (dx, dy)
        - 1: Battery status (normalized 0–1)
        - 9: 3×3 local grid (0=safe, 1=obstacle/debris/boundary, 2=fire, 3=charge)
        """
        if sub_goal is None:
            sub_goal = pos  # No goal → target current position

        dx = (sub_goal[0] - pos[0]) / grid_size
        dy = (sub_goal[1] - pos[1]) / grid_size
        battery = obs["battery"] / 100.0

        # Local 3×3 surroundings
        debris_set = set(tuple(p) for p in obs["debris"])
        fire_set   = set(tuple(p) for p in obs["fires"])
        cs_set     = set(tuple(p) for p in obs["charge_stations"])

        ax, ay = pos
        local_grid = np.zeros((3, 3))
        for idx_x, x in enumerate(range(ax - 1, ax + 2)):
            for idx_y, y in enumerate(range(ay - 1, ay + 2)):
                if not (0 <= x < grid_size and 0 <= y < grid_size):
                    local_grid[idx_x, idx_y] = 1.0  # boundary
                else:
                    pt = (x, y)
                    if pt in fire_set:
                        local_grid[idx_x, idx_y] = 2.0
                    elif pt in debris_set:
                        local_grid[idx_x, idx_y] = 1.0
                    elif pt in cs_set:
                        local_grid[idx_x, idx_y] = 3.0

        state_vec = np.concatenate(([dx, dy, battery], local_grid.flatten()))
        return torch.tensor(state_vec, dtype=torch.float32).to(self.device)

    def get_policy_net(self, agent_id):
        return self.policy_net_drone if agent_id in ["A1", "A2"] else self.policy_net_rover

    def get_target_net(self, agent_id):
        return self.target_net_drone if agent_id in ["A1", "A2"] else self.target_net_rover

    def get_optimizer(self, agent_id):
        return self.optimizer_drone if agent_id in ["A1", "A2"] else self.optimizer_rover

    def select_action(self, agent_id, state_vector, pos=None, sub_goal=None, obs=None, epsilon=None):
        if epsilon is None:
            epsilon = self.epsilon

        # Track position history
        if pos is not None:
            self.pos_history[agent_id].append(tuple(pos))

        # Detect stuck / oscillation states
        is_stuck = False
        history = list(self.pos_history[agent_id])
        if len(history) >= 4:
            if all(p == history[0] for p in history):
                is_stuck = True
            elif len(history) >= 6 and history[0] == history[2] == history[4] and history[1] == history[3] == history[5]:
                is_stuck = True

        # Use pathfinder for exploration or when stuck
        if pos is not None and obs is not None:
            if random.random() < epsilon or is_stuck:
                return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

        # Double DQN: policy net selects action, target net evaluates value
        with torch.no_grad():
            policy_net = self.get_policy_net(agent_id)
            q_values = policy_net(state_vector.unsqueeze(0))
            action = int(q_values.argmax().item())

        # Safety layer: override unsafe actions (fire, bounds, rover-debris)
        if pos is not None and obs is not None:
            delta_map = {0: [-1, 0], 1: [1, 0], 2: [0, 1], 3: [0, -1]}
            if action in delta_map:
                delta = delta_map[action]
                next_pos = [pos[0] + delta[0], pos[1] + delta[1]]
                grid_size = 15

                if not (0 <= next_pos[0] < grid_size and 0 <= next_pos[1] < grid_size):
                    return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

                fire_set = set(tuple(p) for p in obs["fires"])
                if tuple(next_pos) in fire_set:
                    return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

                if agent_id == "A3":
                    debris_set = set(tuple(p) for p in obs["debris"])
                    if tuple(next_pos) in debris_set:
                        return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

        return action

    def select_action_pathfinder(self, agent_id, pos, sub_goal, obs, grid_size=15):
        if sub_goal is None:
            return 4  # Interact/Idle

        if pos == sub_goal:
            return 4  # Reached target → interact

        # Rover: charging and victim interactions
        if agent_id == "A3":
            if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] < 70:
                return 4
            for v_pos in obs["scanned_victims"].values():
                if v_pos == pos:
                    return 4

        # Drone: charging interactions
        if agent_id in ["A1", "A2"]:
            if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] <= 40:
                return 4

        # BFS/Dijkstra pathfinder
        next_step = self.find_path(pos, sub_goal, obs, agent_id, grid_size)
        if next_step is not None:
            if agent_id == "A3" and tuple(next_step) in set(tuple(p) for p in obs["debris"]):
                return 4  # Clear debris

            dx = next_step[0] - pos[0]
            dy = next_step[1] - pos[1]
            if dx == -1: return 0  # North
            if dx == 1:  return 1  # South
            if dy == 1:  return 2  # East
            if dy == -1: return 3  # West

        # Fallback: random safe move
        directions = {0: [-1, 0], 1: [1, 0], 2: [0, 1], 3: [0, -1]}
        fire_set = set(tuple(p) for p in obs["fires"])
        debris_set = set(tuple(p) for p in obs["debris"])
        safe_actions = []
        for act, delta in directions.items():
            nx = pos[0] + delta[0]
            ny = pos[1] + delta[1]
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                neighbor = (nx, ny)
                if neighbor not in fire_set:
                    if agent_id != "A3" or neighbor not in debris_set:
                        safe_actions.append(act)

        return random.choice(safe_actions) if safe_actions else 4

    def find_path(self, start, goal, obs, agent_id, grid_size=15):
        if start == goal:
            return None

        import heapq

        start_tuple = tuple(start)
        goal_tuple  = tuple(goal)

        debris_set = set(tuple(p) for p in obs["debris"])
        fire_set   = set(tuple(p) for p in obs["fires"])

        # Pre-compute fire-adjacent buffer zone
        fire_adjacent = set()
        for fx, fy in fire_set:
            for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                nx, ny = fx + dx, fy + dy
                if 0 <= nx < grid_size and 0 <= ny < grid_size:
                    fire_adjacent.add((nx, ny))

        pq = [(0, start_tuple, [])]
        visited = {}

        while pq:
            cost, curr, path = heapq.heappop(pq)

            if curr == goal_tuple:
                return list(path[0]) if path else None

            if curr in visited and visited[curr] <= cost:
                continue
            visited[curr] = cost

            cx, cy = curr
            for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)

                if not (0 <= nx < grid_size and 0 <= ny < grid_size):
                    continue
                if neighbor in fire_set:
                    continue

                step_cost = 1
                if agent_id == "A3":
                    if neighbor in debris_set:
                        step_cost = 10 if neighbor != goal_tuple else 2
                if neighbor in fire_adjacent:
                    step_cost += 4  # safety buffer cost

                new_cost = cost + step_cost
                if neighbor not in visited or new_cost < visited[neighbor]:
                    heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))

        # Rover fallback: allow crossing debris if completely blocked
        if agent_id == "A3":
            pq = [(0, start_tuple, [])]
            visited = {}
            while pq:
                cost, curr, path = heapq.heappop(pq)
                if curr == goal_tuple:
                    return list(path[0]) if path else None
                if curr in visited and visited[curr] <= cost:
                    continue
                visited[curr] = cost
                cx, cy = curr
                for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                    nx, ny = cx + dx, cy + dy
                    neighbor = (nx, ny)
                    if not (0 <= nx < grid_size and 0 <= ny < grid_size):
                        continue
                    if neighbor in fire_set:
                        continue
                    step_cost = 1 + (4 if neighbor in fire_adjacent else 0)
                    new_cost = cost + step_cost
                    if neighbor not in visited or new_cost < visited[neighbor]:
                        heapq.heappush(pq, (new_cost, neighbor, path + [neighbor]))

        return None

    def store_transition(self, agent_id, state, action, reward, next_state, done):
        entry = (agent_id, state, action, reward, next_state, done)
        if agent_id in ["A1", "A2"]:
            self.memory_drone.append(entry)
        else:
            self.memory_rover.append(entry)

    def train_step(self, num_updates=1):
        """
        Performs batch gradient descent for both drone and rover policy networks.
        Uses Double DQN to reduce overestimation bias.
        num_updates: number of gradient steps to take (curriculum warm-up uses 2)
        """
        total_loss = 0.0

        for _ in range(num_updates):
            # --- Drone network ---
            if len(self.memory_drone) >= self.batch_size:
                batch = random.sample(self.memory_drone, self.batch_size)
                states      = torch.stack([e[1] for e in batch])
                actions     = torch.tensor([e[2] for e in batch], dtype=torch.long).to(self.device)
                rewards     = torch.tensor([e[3] for e in batch], dtype=torch.float32).to(self.device)
                next_states = torch.stack([e[4] for e in batch])
                dones       = torch.tensor([e[5] for e in batch], dtype=torch.float32).to(self.device)

                # Current Q-values
                q_values = self.policy_net_drone(states).gather(1, actions.unsqueeze(1)).squeeze(1)

                # Double DQN target: policy net picks action, target net evaluates
                with torch.no_grad():
                    next_actions = self.policy_net_drone(next_states).argmax(1)
                    next_q = self.target_net_drone(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
                    target_q = rewards + self.gamma * next_q * (1.0 - dones)

                loss = self.loss_fn(q_values, target_q)
                self.optimizer_drone.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy_net_drone.parameters(), max_norm=10.0)
                self.optimizer_drone.step()
                total_loss += loss.item()

            # --- Rover network ---
            if len(self.memory_rover) >= self.batch_size:
                batch = random.sample(self.memory_rover, self.batch_size)
                states      = torch.stack([e[1] for e in batch])
                actions     = torch.tensor([e[2] for e in batch], dtype=torch.long).to(self.device)
                rewards     = torch.tensor([e[3] for e in batch], dtype=torch.float32).to(self.device)
                next_states = torch.stack([e[4] for e in batch])
                dones       = torch.tensor([e[5] for e in batch], dtype=torch.float32).to(self.device)

                q_values = self.policy_net_rover(states).gather(1, actions.unsqueeze(1)).squeeze(1)

                with torch.no_grad():
                    next_actions = self.policy_net_rover(next_states).argmax(1)
                    next_q = self.target_net_rover(next_states).gather(1, next_actions.unsqueeze(1)).squeeze(1)
                    target_q = rewards + self.gamma * next_q * (1.0 - dones)

                loss = self.loss_fn(q_values, target_q)
                self.optimizer_rover.zero_grad()
                loss.backward()
                nn.utils.clip_grad_norm_(self.policy_net_rover.parameters(), max_norm=10.0)
                self.optimizer_rover.step()
                total_loss += loss.item()

        return total_loss

    def update_target_networks(self):
        self.target_net_drone.load_state_dict(self.policy_net_drone.state_dict())
        self.target_net_rover.load_state_dict(self.policy_net_rover.state_dict())

    def save(self, filepath_drone, filepath_rover):
        torch.save(self.policy_net_drone.state_dict(), filepath_drone)
        torch.save(self.policy_net_rover.state_dict(), filepath_rover)

    def load(self, filepath_drone, filepath_rover):
        try:
            self.policy_net_drone.load_state_dict(torch.load(filepath_drone, map_location=self.device))
            self.target_net_drone.load_state_dict(self.policy_net_drone.state_dict())
            self.policy_net_rover.load_state_dict(torch.load(filepath_rover, map_location=self.device))
            self.target_net_rover.load_state_dict(self.policy_net_rover.state_dict())
        except Exception as e:
            print(f"No low-level weights loaded. Starting fresh. Error: {e}")
