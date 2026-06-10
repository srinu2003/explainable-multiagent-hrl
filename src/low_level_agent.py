import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import random
from collections import deque

class QNetwork(nn.Module):
    def __init__(self, input_dim=12, output_dim=5):
        super(QNetwork, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
            nn.Linear(64, output_dim)
        )
        
    def forward(self, x):
        return self.fc(x)

class LowLevelAgent:
    def __init__(self, lr=1e-3, gamma=0.95, epsilon=0.15, memory_size=5000, batch_size=64):
        self.gamma = gamma
        self.epsilon = epsilon
        self.batch_size = batch_size
        
        # Experience replay buffer
        self.memory = deque(maxlen=memory_size)
        
        # PyTorch device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Active networks (Drones and Rover share the same architecture, but train separate weights)
        self.policy_net_drone = QNetwork().to(self.device)
        self.target_net_drone = QNetwork().to(self.device)
        self.target_net_drone.load_state_dict(self.policy_net_drone.state_dict())
        self.optimizer_drone = optim.Adam(self.policy_net_drone.parameters(), lr=lr)
        
        self.policy_net_rover = QNetwork().to(self.device)
        self.target_net_rover = QNetwork().to(self.device)
        self.target_net_rover.load_state_dict(self.policy_net_rover.state_dict())
        self.optimizer_rover = optim.Adam(self.policy_net_rover.parameters(), lr=lr)
        
        self.loss_fn = nn.MSELoss()
        
    def get_state_vector(self, agent_id, pos, sub_goal, obs, grid_size=15):
        """
        Extracts features and returns a 12-dimensional vector.
        Features:
        - 2 elements: Relative normalized vector to sub-goal (dx, dy)
        - 1 element: Battery status (normalized)
        - 9 elements: 3x3 local grid surroundings (0 = safe/clear, 1 = obstacle/debris/boundary, 2 = fire, 3 = charge)
        """
        if sub_goal is None:
            sub_goal = pos  # If no goal, target is current position
            
        dx = (sub_goal[0] - pos[0]) / grid_size
        dy = (sub_goal[1] - pos[1]) / grid_size
        battery = obs["battery"] / 100.0
        
        # Local surroundings (3x3 grid)
        surroundings = []
        ax, ay = pos
        
        # We look up local mapped state. If cell is unexplored, agent assumes it is empty (0)
        # We can compile local grid representation by querying mapped features
        local_grid = np.zeros((3, 3))
        
        # Load debris, fires, charge stations, and boundaries
        debris_set = set(tuple(p) for p in obs["debris"])
        fire_set = set(tuple(p) for p in obs["fires"])
        cs_set = set(tuple(p) for p in obs["charge_stations"])
        
        for idx_x, x in enumerate(range(ax - 1, ax + 2)):
            for idx_y, y in enumerate(range(ay - 1, ay + 2)):
                if not (0 <= x < grid_size and 0 <= y < grid_size):
                    # Boundary counts as obstacle
                    local_grid[idx_x, idx_y] = 1.0
                else:
                    pos_tuple = (x, y)
                    if pos_tuple in fire_set:
                        local_grid[idx_x, idx_y] = 2.0
                    elif pos_tuple in debris_set:
                        local_grid[idx_x, idx_y] = 1.0
                    elif pos_tuple in cs_set:
                        local_grid[idx_x, idx_y] = 3.0
                    else:
                        local_grid[idx_x, idx_y] = 0.0
                        
        surroundings = local_grid.flatten()
        
        state_vec = np.concatenate(([dx, dy, battery], surroundings))
        return torch.tensor(state_vec, dtype=torch.float32).to(self.device)
        
    def get_policy_net(self, agent_id):
        return self.policy_net_drone if agent_id in ["A1", "A2"] else self.policy_net_rover
        
    def get_optimizer(self, agent_id):
        return self.optimizer_drone if agent_id in ["A1", "A2"] else self.optimizer_rover
        
    def select_action(self, agent_id, state_vector, pos=None, sub_goal=None, obs=None, epsilon=None):
        # If navigation coordinates and observations are provided, use the BFS pathfinder
        if pos is not None and obs is not None:
            return self.select_action_pathfinder(agent_id, pos, sub_goal, obs)

        # Fallback to DQN
        if epsilon is None:
            epsilon = self.epsilon
            
        if random.random() < epsilon:
            return random.randint(0, 4)
            
        with torch.no_grad():
            policy_net = self.get_policy_net(agent_id)
            q_values = policy_net(state_vector.unsqueeze(0))
            return int(q_values.argmax().item())

    def select_action_pathfinder(self, agent_id, pos, sub_goal, obs, grid_size=15):
        if sub_goal is None:
            return 4  # Interact/Idle
            
        # 1. Immediate interactions
        if pos == sub_goal:
            return 4  # Reach target / Interact
            
        # Rover interactions
        if agent_id == "A3":
            # If on charge station and battery is low
            if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] < 70:
                return 4
            # If on scanned victim, rescue it
            for v_pos in obs["scanned_victims"].values():
                if v_pos == pos:
                    return 4
                    
        # Drone interactions
        if agent_id in ["A1", "A2"]:
            if tuple(pos) in [tuple(cs) for cs in obs["charge_stations"]] and obs["battery"] < 40:
                return 4
                
        # 2. Find path using BFS
        next_step = self.find_path(pos, sub_goal, obs, agent_id, grid_size)
        if next_step is not None:
            # If next step contains debris and agent is Rover, it must clear it first
            if agent_id == "A3" and tuple(next_step) in set(tuple(p) for p in obs["debris"]):
                return 4
                
            dx = next_step[0] - pos[0]
            dy = next_step[1] - pos[1]
            if dx == -1: return 0  # North
            if dx == 1: return 1   # South
            if dy == 1: return 2   # East
            if dy == -1: return 3  # West
            
        # 3. Fallback: random safe move to avoid getting stuck
        directions = {0: [-1, 0], 1: [1, 0], 2: [0, 1], 3: [0, -1]}
        safe_actions = []
        fire_set = set(tuple(p) for p in obs["fires"])
        debris_set = set(tuple(p) for p in obs["debris"])
        
        for act, delta in directions.items():
            nx = pos[0] + delta[0]
            ny = pos[1] + delta[1]
            if 0 <= nx < grid_size and 0 <= ny < grid_size:
                neighbor = (nx, ny)
                if neighbor not in fire_set:
                    if agent_id != "A3" or neighbor not in debris_set:
                        safe_actions.append(act)
                        
        if safe_actions:
            return random.choice(safe_actions)
        return 4  # Idle if completely trapped

    def find_path(self, start, goal, obs, agent_id, grid_size=15):
        if start == goal:
            return None
            
        start_tuple = tuple(start)
        goal_tuple = tuple(goal)
        
        queue = deque([start_tuple])
        visited = {start_tuple: None}
        
        debris_set = set(tuple(p) for p in obs["debris"])
        fire_set = set(tuple(p) for p in obs["fires"])
        
        while queue:
            curr = queue.popleft()
            if curr == goal_tuple:
                break
                
            cx, cy = curr
            for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                nx, ny = cx + dx, cy + dy
                neighbor = (nx, ny)
                
                if 0 <= nx < grid_size and 0 <= ny < grid_size:
                    if neighbor in visited:
                        continue
                        
                    # Rover cannot cross debris (unless it is the goal itself!) or fire
                    # Drones cannot cross fire
                    is_blocked = False
                    if neighbor in fire_set:
                        is_blocked = True
                    if neighbor in debris_set and agent_id == "A3":
                        if neighbor != goal_tuple:
                            is_blocked = True
                            
                    if not is_blocked:
                        queue.append(neighbor)
                        visited[neighbor] = curr
                        
        if goal_tuple not in visited:
            # Fallback pathfinding allowing debris for Rover (she will clear it)
            if agent_id == "A3":
                queue = deque([start_tuple])
                visited = {start_tuple: None}
                while queue:
                    curr = queue.popleft()
                    if curr == goal_tuple:
                        break
                    cx, cy = curr
                    for dx, dy in [[-1, 0], [1, 0], [0, -1], [0, 1]]:
                        nx, ny = cx + dx, cy + dy
                        neighbor = (nx, ny)
                        if 0 <= nx < grid_size and 0 <= ny < grid_size:
                            if neighbor in visited:
                                continue
                            if neighbor not in fire_set:
                                queue.append(neighbor)
                                visited[neighbor] = curr
            
            if goal_tuple not in visited:
                return None
                
        # Backtrace
        curr = goal_tuple
        path = []
        while curr is not None:
            path.append(curr)
            curr = visited[curr]
            
        path.reverse()
        if len(path) > 1:
            return list(path[1])
        return None
            
    def store_transition(self, agent_id, state, action, reward, next_state, done):
        self.memory.append((agent_id, state, action, reward, next_state, done))
        
    def train_step(self):
        """
        Performs one batch gradient descent step for policy networks.
        """
        if len(self.memory) < self.batch_size:
            return 0.0
            
        batch = random.sample(self.memory, self.batch_size)
        
        # Split drone and rover experiences
        drone_batch = [exp for exp in batch if exp[0] in ["A1", "A2"]]
        rover_batch = [exp for exp in batch if exp[0] == "A3"]
        
        total_loss = 0.0
        
        for batch_data, net_name in [(drone_batch, "drone"), (rover_batch, "rover")]:
            if len(batch_data) == 0:
                continue
                
            states = torch.stack([exp[1] for exp in batch_data])
            actions = torch.tensor([exp[2] for exp in batch_data], dtype=torch.long).to(self.device)
            rewards = torch.tensor([exp[3] for exp in batch_data], dtype=torch.float32).to(self.device)
            next_states = torch.stack([exp[4] for exp in batch_data])
            dones = torch.tensor([exp[5] for exp in batch_data], dtype=torch.float32).to(self.device)
            
            policy_net = self.policy_net_drone if net_name == "drone" else self.policy_net_rover
            target_net = self.target_net_drone if net_name == "drone" else self.target_net_rover
            optimizer = self.optimizer_drone if net_name == "drone" else self.optimizer_rover
            
            # Current Q values
            q_values = policy_net(states).gather(1, actions.unsqueeze(1)).squeeze(1)
            
            # Next Q values
            with torch.no_grad():
                next_q_values = target_net(next_states).max(1)[0]
                expected_q_values = rewards + self.gamma * next_q_values * (1.0 - dones)
                
            loss = self.loss_fn(q_values, expected_q_values)
            
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
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
