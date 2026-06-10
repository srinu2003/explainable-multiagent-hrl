import numpy as np
import random
import pickle

class HighLevelAgent:
    def __init__(self, alpha=0.15, gamma=0.9, epsilon=0.15):
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon
        
        # Q-tables: dictionary of states to q-value arrays
        # Action space for Drones (0-4):
        # 0: NW (3,3), 1: NE (3,11), 2: SW (11,3), 3: SE (11,11), 4: Charge Pad
        self.q_table_drone = {}
        
        # Action space for Rover (0-6):
        # 0: NW, 1: NE, 2: SW, 3: SE, 4: Charge Pad, 5: Closest Scanned Victim, 6: Closest Debris
        self.q_table_rover = {}
        
        self.quadrants = {
            0: [3, 3],     # NW
            1: [3, 11],    # NE
            2: [11, 3],    # SW
            3: [11, 11]    # SE
        }
        
    def get_state(self, agent_id, agent_obs):
        """
        Discretizes the observation to a compact state tuple.
        Drones state: (battery_low, victim_unscanned_exists, overlap_active)
        Rover state: (battery_low, scanned_victim_exists, debris_blocking_exists)
        """
        battery = agent_obs["battery"]
        battery_low = 1 if battery <= 40 else 0
        
        if agent_id in ["A1", "A2"]:
            # Check if there are unscanned quadrants
            # We look at mapped grid quadrants: if average exploration in a quadrant is < 0.8
            unexplored = 0
            mapped = agent_obs["mapped_grid"]
            h, w = mapped.shape
            
            # Simple heuristic: is there any unseen cell?
            if np.mean(mapped) < 0.9:
                unexplored = 1
                
            # Check if another drone is close to this agent's target (simplified coordination state)
            overlap = 0
            return (battery_low, unexplored, overlap)
        else:
            # Rover state
            scanned_victims = len(agent_obs["scanned_victims"]) > 0
            debris_exists = len(agent_obs["debris"]) > 0
            return (battery_low, 1 if scanned_victims else 0, 1 if debris_exists else 0)
            
    def get_q_table(self, agent_id):
        return self.q_table_drone if agent_id in ["A1", "A2"] else self.q_table_rover
        
    def get_num_actions(self, agent_id):
        return 5 if agent_id in ["A1", "A2"] else 7
        
    def get_action_values(self, agent_id, state):
        q_table = self.get_q_table(agent_id)
        num_actions = self.get_num_actions(agent_id)
        if state not in q_table:
            q_table[state] = np.zeros(num_actions, dtype=np.float32)
        return q_table[state]
        
    def select_macro_goal(self, agent_id, obs, epsilon=None):
        """
        Selects a macro-goal coordinate using epsilon-greedy policy.
        Returns: (macro_action_idx, coordinates_list, explanation_reason)
        """
        if epsilon is None:
            epsilon = self.epsilon
            
        state = self.get_state(agent_id, obs)
        num_actions = self.get_num_actions(agent_id)
        
        # Epsilon-greedy selection
        if random.random() < epsilon:
            action = random.randint(0, num_actions - 1)
        else:
            q_values = self.get_q_table(agent_id).get(state, np.zeros(num_actions))
            # Break ties randomly
            action = np.random.choice(np.flatnonzero(q_values == q_values.max()))
            
        # Translate macro-action index to coordinates and dynamic text explanation
        coords, reason = self.translate_action_to_goal(agent_id, action, obs)
        return action, coords, reason
        
    def translate_action_to_goal(self, agent_id, action, obs):
        """
        Converts a macro-action index to concrete grid coordinates [x, y] and a textual rationale.
        """
        pos = obs["pos"]
        
        if action in [0, 1, 2, 3]:
            # Target Quadrant Center
            target_coords = self.quadrants[action]
            quadrant_names = ["North-West", "North-East", "South-West", "South-East"]
            reason = f"Prioritizing exploration of the {quadrant_names[action]} sector."
            return target_coords, reason
            
        elif action == 4:
            # Target Nearest Charging Station
            stations = obs["charge_stations"]
            dists = [abs(cs[0] - pos[0]) + abs(cs[1] - pos[1]) for cs in stations]
            nearest_idx = np.argmin(dists)
            target_coords = stations[nearest_idx]
            reason = f"Battery status is critical ({obs['battery']}%). Retiring to charging pad at {target_coords}."
            return target_coords, reason
            
        elif action == 5:
            # Target Closest Scanned Victim (Rover only)
            victims = obs["scanned_victims"]
            if len(victims) > 0:
                # Find closest
                closest_id = None
                closest_dist = 9999
                for v_id, v_pos in victims.items():
                    dist = abs(v_pos[0] - pos[0]) + abs(v_pos[1] - pos[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_id = v_id
                target_coords = victims[closest_id]
                reason = f"Victim {closest_id} scanned at {target_coords}. Initiating rescue transit (Distance: {closest_dist} blocks)."
                return target_coords, reason
            else:
                # Fallback to nearest charge station
                stations = obs["charge_stations"]
                target_coords = stations[0]
                reason = "No scanned victims available. Patrolling near charge pads."
                return target_coords, reason
                
        elif action == 6:
            # Target Closest Debris (Rover only)
            debris = obs["debris"]
            if len(debris) > 0:
                closest_pos = None
                closest_dist = 9999
                for d_pos in debris:
                    dist = abs(d_pos[0] - pos[0]) + abs(d_pos[1] - pos[1])
                    if dist < closest_dist:
                        closest_dist = dist
                        closest_pos = d_pos
                target_coords = closest_pos
                reason = f"Debris obstacle detected at {target_coords}. Proceeding to clear path."
                return target_coords, reason
            else:
                # Fallback to random quadrant
                target_coords = self.quadrants[0]
                reason = "No debris obstacles scanned. Initiating search pattern."
                return target_coords, reason
                
        # Default fallback
        return pos, "Maintaining current holding position."
        
    def update(self, agent_id, state, action, reward, next_state, done):
        """
        Bellman Q-value update.
        """
        q_table = self.get_q_table(agent_id)
        num_actions = self.get_num_actions(agent_id)
        
        if state not in q_table:
            q_table[state] = np.zeros(num_actions, dtype=np.float32)
        if next_state not in q_table:
            q_table[next_state] = np.zeros(num_actions, dtype=np.float32)
            
        current_q = q_table[state][action]
        max_future_q = 0.0 if done else np.max(q_table[next_state])
        
        # Temporal difference target
        td_target = reward + self.gamma * max_future_q
        q_table[state][action] = current_q + self.alpha * (td_target - current_q)
        
    def save(self, filepath):
        with open(filepath, 'wb') as f:
            pickle.dump((self.q_table_drone, self.q_table_rover), f)
            
    def load(self, filepath):
        try:
            with open(filepath, 'rb') as f:
                self.q_table_drone, self.q_table_rover = pickle.load(f)
        except Exception as e:
            print(f"No high-level weights loaded. Starting fresh. Error: {e}")
