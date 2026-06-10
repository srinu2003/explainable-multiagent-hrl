import numpy as np
import random

class SearchRescueEnv:
    def __init__(self, grid_size=15, num_victims=3, num_debris=10, num_fires=2):
        self.grid_size = grid_size
        self.num_victims = num_victims
        self.num_debris = num_debris
        self.num_fires_initial = num_fires
        
        # Grid layers:
        # 0 = Empty, 1 = Debris/Obstacle, 2 = Fire, 3 = Charge Station
        self.grid = np.zeros((grid_size, grid_size), dtype=np.int32)
        self.charge_stations = [(0, grid_size // 2), (grid_size - 1, grid_size // 2)]
        for cs in self.charge_stations:
            self.grid[cs] = 3
            
        self.reset()
        
    def reset(self):
        self.step_count = 0
        self.max_steps = 150
        
        # Clear grid (except charge stations)
        self.grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int32)
        for cs in self.charge_stations:
            self.grid[cs] = 3
            
        # Spawn agents:
        # Drone A1 (Reconnaissance) - Top Left
        # Drone A2 (Reconnaissance) - Top Right
        # Rover A3 (Rescue & Clear Path) - Bottom Center
        self.agents = {
            "A1": {"pos": [0, 0], "battery": 100, "role": "Reconnaissance", "active": True, "score": 0, "sub_goal": None},
            "A2": {"pos": [0, self.grid_size - 1], "battery": 100, "role": "Reconnaissance", "active": True, "score": 0, "sub_goal": None},
            "A3": {"pos": [self.grid_size - 1, self.grid_size // 2], "battery": 100, "role": "Rescue", "active": True, "score": 0, "sub_goal": None}
        }
        
        # Placement helpers
        occupied = set(self.charge_stations + [tuple(self.agents["A1"]["pos"]), tuple(self.agents["A2"]["pos"]), tuple(self.agents["A3"]["pos"])])
        
        # Spawn Debris
        self.debris_locations = []
        while len(self.debris_locations) < self.num_debris:
            pos = (random.randint(2, self.grid_size - 3), random.randint(1, self.grid_size - 2))
            if pos not in occupied:
                self.debris_locations.append(pos)
                self.grid[pos] = 1
                occupied.add(pos)
                
        # Spawn Fire Seeds
        self.fire_locations = []
        while len(self.fire_locations) < self.num_fires_initial:
            pos = (random.randint(3, self.grid_size - 4), random.randint(2, self.grid_size - 3))
            if pos not in occupied:
                self.fire_locations.append(pos)
                self.grid[pos] = 2
                occupied.add(pos)
                
        # Spawn Victims (hidden from agents at start)
        self.victims = {}
        idx = 1
        while len(self.victims) < self.num_victims:
            pos = (random.randint(1, self.grid_size - 2), random.randint(1, self.grid_size - 2))
            if pos not in occupied:
                self.victims[f"V{idx}"] = {
                    "pos": list(pos),
                    "status": "hidden"  # hidden, scanned, rescued
                }
                occupied.add(pos)
                idx += 1
                
        # Shared mapped grid (0 = unexplored, 1 = explored/scanned)
        # Charge stations are known initially
        self.mapped_grid = np.zeros((self.grid_size, self.grid_size), dtype=np.int32)
        for cs in self.charge_stations:
            self.mapped_grid[cs] = 1
            
        self.update_mapping()
        return self.get_observations()
        
    def update_mapping(self):
        # Drones have a 3x3 FOV, Rover has a 3x3 FOV
        for agent_id, agent in self.agents.items():
            if not agent["active"]:
                continue
            ax, ay = agent["pos"]
            fov = 3 if agent["role"] == "Reconnaissance" else 3
            
            # Map cells within FOV
            for x in range(max(0, ax - fov // 2), min(self.grid_size, ax + fov // 2 + 1)):
                for y in range(max(0, ay - fov // 2), min(self.grid_size, ay + fov // 2 + 1)):
                    self.mapped_grid[x, y] = 1
                    
                    # If this cell contains a victim, it gets scanned
                    for vic_id, vic in self.victims.items():
                        if vic["pos"] == [x, y] and vic["status"] == "hidden":
                            vic["status"] = "scanned"
                            
    def get_observations(self):
        # Return state vectors suitable for agents
        obs = {}
        for agent_id, agent in self.agents.items():
            obs[agent_id] = {
                "pos": list(agent["pos"]),
                "battery": agent["battery"],
                "active": agent["active"],
                "mapped_grid": self.mapped_grid.copy(),
                # Agents can see coordinates of known victims and debris in mapped cells
                "scanned_victims": {k: v["pos"] for k, v in self.victims.items() if v["status"] == "scanned"},
                "rescued_victims": {k: v["pos"] for k, v in self.victims.items() if v["status"] == "rescued"},
                "debris": [list(pos) for pos in self.debris_locations if self.mapped_grid[pos] == 1],
                "fires": [list(pos) for pos in self.fire_locations if self.mapped_grid[pos] == 1],
                "charge_stations": [list(cs) for cs in self.charge_stations]
            }
        return obs
        
    def step(self, actions):
        """
        actions: dict of agent actions, e.g. {"A1": 0, "A2": 3, "A3": 4}
        Actions definition:
        0: Move North (x-1)
        1: Move South (x+1)
        2: Move East (y+1)
        3: Move West (y-1)
        4: Interact (Recharge if on CS, Clear Debris if adjacent to debris, Rescue if on scanned victim)
        """
        self.step_count += 1
        rewards = {"A1": 0.0, "A2": 0.0, "A3": 0.0}
        info = {"xai_logs": {}}
        
        # 1. Process agent actions
        for agent_id in ["A1", "A2", "A3"]:
            agent = self.agents[agent_id]
            if not agent["active"]:
                continue
                
            action = actions.get(agent_id, 4)  # Default is Interact
            curr_pos = list(agent["pos"])
            
            # Deplete battery
            battery_cost = 1
            
            # Action logic
            if action in [0, 1, 2, 3]:
                # Move
                delta = [[-1, 0], [1, 0], [0, 1], [0, -1]][action]
                next_pos = [curr_pos[0] + delta[0], curr_pos[1] + delta[1]]
                
                # Check grid boundaries
                if 0 <= next_pos[0] < self.grid_size and 0 <= next_pos[1] < self.grid_size:
                    cell_type = self.grid[next_pos[0], next_pos[1]]
                    
                    if agent["role"] == "Reconnaissance":
                        # Drones can fly over debris, but not hit fire or boundaries
                        if cell_type == 2:  # Fire
                            agent["active"] = False
                            rewards[agent_id] -= 25.0  # Big penalty for crashing in fire
                            info["xai_logs"][agent_id] = f"Crashed into fire at {next_pos}."
                        else:
                            agent["pos"] = next_pos
                            
                    elif agent["role"] == "Rescue":
                        # Rover cannot cross debris or fire
                        if cell_type == 1:  # Debris
                            rewards[agent_id] -= 2.0  # Minor path blocked penalty
                        elif cell_type == 2:  # Fire
                            agent["active"] = False
                            rewards[agent_id] -= 25.0
                            info["xai_logs"][agent_id] = f"Destroyed by fire at {next_pos}."
                        else:
                            agent["pos"] = next_pos
                else:
                    rewards[agent_id] -= 1.0  # Out of bounds collision penalty
                    
            elif action == 4:
                # Interact
                # a) Recharge
                if tuple(agent["pos"]) in self.charge_stations:
                    if agent["battery"] < 95:
                        agent["battery"] = 100
                        battery_cost = 0  # No cost to charge
                        rewards[agent_id] += 5.0
                        info["xai_logs"][agent_id] = f"Recharged battery to 100%."
                    else:
                        battery_cost = 1  # Wasting a step costs normal battery/time
                        rewards[agent_id] -= 1.0  # Time wasting penalty
                        info["xai_logs"][agent_id] = f"Wasted step on charging station with full battery."
                
                # b) Clear debris (Rover only)
                elif agent["role"] == "Rescue":
                    # Priority 1: Rescue Victim (Rover only)
                    rescued = False
                    for vic_id, vic in self.victims.items():
                        if vic["status"] == "scanned" and vic["pos"] == agent["pos"]:
                            # Check if the victim is adjacent to any fire cell (high-risk rescue)
                            is_high_risk = False
                            for f_pos in self.fire_locations:
                                if abs(f_pos[0] - vic["pos"][0]) + abs(f_pos[1] - vic["pos"][1]) <= 1:
                                    is_high_risk = True
                                    break
                            
                            vic["status"] = "rescued"
                            agent["score"] += 1
                            
                            if is_high_risk:
                                rewards[agent_id] += 60.0  # 40.0 base + 20.0 high-risk bonus
                                rewards["A1"] += 20.0      # 15.0 base + 5.0 high-risk bonus
                                rewards["A2"] += 20.0
                                info["xai_logs"][agent_id] = f"Rescued High-Risk Victim {vic_id} near fire at {vic['pos']}!"
                            else:
                                rewards[agent_id] += 40.0
                                rewards["A1"] += 15.0
                                rewards["A2"] += 15.0
                                info["xai_logs"][agent_id] = f"Rescued Victim {vic_id} at {vic['pos']}!"
                                
                            rescued = True
                            break
                            
                    if not rescued:
                        # Priority 2: Clear debris (Rover only)
                        cleared = False
                        for idx, d_pos in enumerate(self.debris_locations):
                            dist = abs(d_pos[0] - agent["pos"][0]) + abs(d_pos[1] - agent["pos"][1])
                            if dist <= 1:  # Adjacent or on debris
                                self.debris_locations.pop(idx)
                                self.grid[d_pos] = 0  # Clear cell
                                battery_cost = 4  # Heavy battery cost to clear path
                                rewards[agent_id] += 12.0
                                rewards["A1"] += 4.0  # Shared reward for clearing path
                                rewards["A2"] += 4.0
                                info["xai_logs"][agent_id] = f"Cleared debris at {d_pos}."
                                cleared = True
                                break
                                
                        if not cleared:
                            rewards[agent_id] -= 0.5  # Idle penalty
                            
            # c) Fire proximity penalty
            if agent["active"]:
                is_near_fire = False
                for f_pos in self.fire_locations:
                    if abs(f_pos[0] - agent["pos"][0]) + abs(f_pos[1] - agent["pos"][1]) <= 1:
                        is_near_fire = True
                        break
                if is_near_fire:
                    rewards[agent_id] -= 1.0  # safety penalty for proximity to fire
                            
            # Update battery depletion
            agent["battery"] = max(0, agent["battery"] - battery_cost)
            if agent["battery"] == 0:
                agent["active"] = False
                rewards[agent_id] -= 20.0
                info["xai_logs"][agent_id] = f"Ran out of battery at {agent['pos']}."
                
            # Sub-goal check (if agent reached its target, clear sub-goal at the end of the step)
            if agent["active"] and agent["sub_goal"] and agent["pos"] == agent["sub_goal"]:
                agent["sub_goal"] = None
                
        # 2. Update mapping
        self.update_mapping()
        
        # 3. Dynamic Hazard: Spreading Fire (every 7 steps, fire expands)
        if self.step_count % 7 == 0 and len(self.fire_locations) > 0:
            new_fires = []
            for fire in self.fire_locations:
                for delta in [[-1,0], [1,0], [0,-1], [0,1]]:
                    neighbor = (fire[0] + delta[0], fire[1] + delta[1])
                    if (0 <= neighbor[0] < self.grid_size and 
                        0 <= neighbor[1] < self.grid_size and 
                        self.grid[neighbor] == 0 and
                        neighbor not in self.charge_stations):
                        
                        # Check agents aren't occupying it (active only)
                        agent_on = False
                        for ag in self.agents.values():
                            if ag["active"] and ag["pos"] == list(neighbor):
                                agent_on = True
                        if not agent_on and random.random() < 0.18: # 18% spread probability
                            new_fires.append(neighbor)
                            
            for nf in set(new_fires):
                self.fire_locations.append(nf)
                self.grid[nf] = 2
                
        # 4. Check terminal states
        done = False
        all_rescued = all(vic["status"] == "rescued" for vic in self.victims.values())
        all_dead = all(not ag["active"] for ag in self.agents.values())
        
        if all_rescued:
            done = True
            for k in rewards:
                rewards[k] += 30.0  # Large final completion reward
        elif all_dead or self.step_count >= self.max_steps:
            done = True
            
        # Time step penalty
        for k in rewards:
            rewards[k] -= 0.1
            
        return self.get_observations(), rewards, done, info
