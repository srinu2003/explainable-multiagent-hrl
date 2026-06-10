import numpy as np
import random
import pickle


class HighLevelAgent:
    def __init__(self, alpha=0.25, gamma=0.9, epsilon=0.15):
        # Higher alpha (0.15→0.25) for faster Q-table convergence
        self.alpha = alpha
        self.gamma = gamma
        self.epsilon = epsilon

        # Drone action space (0–4):
        # 0: NW (3,3), 1: NE (3,11), 2: SW (11,3), 3: SE (11,11), 4: Charge Pad
        self.q_table_drone = {}

        # Rover action space (0–6):
        # 0: NW, 1: NE, 2: SW, 3: SE, 4: Charge Pad, 5: Rescue Victim, 6: Clear Debris
        self.q_table_rover = {}

        self.quadrants = {
            0: [3, 3],    # NW
            1: [3, 11],   # NE
            2: [11, 3],   # SW
            3: [11, 11]   # SE
        }

    def get_state(self, agent_id, agent_obs, all_agents=None):
        """
        Discretizes observation into a compact state tuple.

        Drone state (6-bit):
            (battery_low, any_unexplored, overlap_with_peer, scanned_victim_exists, rover_has_target, fire_in_grid)
        Rover state (3-bit):
            (battery_low, scanned_victim_exists, debris_exists)
        """
        battery = agent_obs["battery"]
        battery_low = 1 if battery <= 40 else 0

        if agent_id in ["A1", "A2"]:
            mapped = agent_obs["mapped_grid"]

            # Is there any unexplored area?
            unexplored = 1 if np.mean(mapped) < 0.9 else 0

            # Is the peer drone targeting the same quadrant?
            overlap = 0
            if all_agents is not None:
                peer_id = "A2" if agent_id == "A1" else "A1"
                peer = all_agents.get(peer_id)
                self_agent = all_agents.get(agent_id)
                if peer and self_agent:
                    if self_agent.get("sub_goal") is not None and self_agent.get("sub_goal") == peer.get("sub_goal"):
                        overlap = 1

            # Are there scanned victims waiting for rescue? (Drone can signal rover)
            scanned_waiting = 1 if len(agent_obs.get("scanned_victims", {})) > 0 else 0

            # Does the rover already have a target?
            rover_busy = 0
            if all_agents is not None:
                rover = all_agents.get("A3")
                if rover and rover.get("sub_goal") is not None:
                    rover_busy = 1

            # Is there fire somewhere in the grid? (affects patrol strategy)
            fire_present = 1 if len(agent_obs.get("fires", [])) > 0 else 0

            return (battery_low, unexplored, overlap, scanned_waiting, rover_busy, fire_present)

        else:
            # Rover state (unchanged — 3-bit is sufficient for the rover's simpler decision)
            scanned_victims = len(agent_obs.get("scanned_victims", {})) > 0
            debris_exists   = len(agent_obs.get("debris", [])) > 0
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

    def select_macro_goal(self, agent_id, obs, epsilon=None, all_agents=None):
        """
        Selects a macro-goal using epsilon-greedy with safety coordination overrides.
        Returns: (macro_action_idx, coordinates_list, explanation_reason)
        """
        if epsilon is None:
            epsilon = self.epsilon

        state = self.get_state(agent_id, obs, all_agents)
        num_actions = self.get_num_actions(agent_id)
        pos = obs["pos"]

        # ── ROVER PRIORITY OVERRIDE ──────────────────────────────────────────────
        # Rover ALWAYS rescues scanned victims before clearing debris (when battery OK)
        if agent_id == "A3":
            # Priority 1: Battery critical → charge first
            if obs["battery"] <= 30:
                action = 4
                coords, reason = self.translate_action_to_goal(agent_id, action, obs)
                return action, coords, reason

            # Priority 2: Scanned victim waiting → rescue immediately
            if len(obs.get("scanned_victims", {})) > 0:
                action = 5
                coords, reason = self.translate_action_to_goal(agent_id, action, obs)
                return action, coords, reason

            # Priority 3: Debris blocking → clear it
            if len(obs.get("debris", [])) > 0:
                action = 6
                coords, reason = self.translate_action_to_goal(agent_id, action, obs)
                return action, coords, reason

        # ── DRONE CHARGE OVERRIDE ────────────────────────────────────────────────
        if agent_id in ["A1", "A2"] and obs["battery"] <= 35:
            action = 4
            coords, reason = self.translate_action_to_goal(agent_id, action, obs)
            return action, coords, reason

        # ── EPSILON-GREEDY SELECTION ─────────────────────────────────────────────
        if random.random() < epsilon:
            action = random.randint(0, num_actions - 1)
        else:
            q_table = self.get_q_table(agent_id)
            q_values = q_table.get(state, np.zeros(num_actions)).copy()

            # Drone masking: avoid already-explored quadrants or positions already at quadrant center
            if agent_id in ["A1", "A2"]:
                mapped = obs["mapped_grid"]
                h, w = mapped.shape
                quad_slices = {
                    0: (slice(0, h // 2), slice(0, w // 2)),
                    1: (slice(0, h // 2), slice(w // 2, w)),
                    2: (slice(h // 2, h), slice(0, w // 2)),
                    3: (slice(h // 2, h), slice(w // 2, w))
                }
                for a in range(4):
                    if pos == self.quadrants[a]:
                        q_values[a] = -9999.0
                        continue
                    slices = quad_slices[a]
                    quad_map = mapped[slices[0], slices[1]]
                    if np.mean(quad_map) > 0.92:
                        q_values[a] = -9999.0

            # Mask current position quadrant centers
            for a in range(4):
                if pos == self.quadrants[a]:
                    q_values[a] = -9999.0

            # Break ties randomly
            action = int(np.random.choice(np.flatnonzero(q_values == q_values.max())))

        coords, reason = self.translate_action_to_goal(agent_id, action, obs)
        return action, coords, reason

    def translate_action_to_goal(self, agent_id, action, obs):
        """Converts a macro-action index to concrete grid coordinates and rationale."""
        pos = obs["pos"]

        if action in [0, 1, 2, 3]:
            target_coords = self.quadrants[action]
            names = ["North-West", "North-East", "South-West", "South-East"]
            return target_coords, f"Prioritizing exploration of the {names[action]} sector."

        elif action == 4:
            stations = obs["charge_stations"]
            dists = [abs(cs[0] - pos[0]) + abs(cs[1] - pos[1]) for cs in stations]
            nearest = stations[int(np.argmin(dists))]
            return nearest, f"Battery at {obs['battery']}%. Retiring to charging pad at {nearest}."

        elif action == 5:
            victims = obs.get("scanned_victims", {})
            if victims:
                closest_id, closest_dist, closest_pos = None, 9999, None
                for v_id, v_pos in victims.items():
                    d = abs(v_pos[0] - pos[0]) + abs(v_pos[1] - pos[1])
                    if d < closest_dist:
                        closest_dist, closest_id, closest_pos = d, v_id, v_pos
                return closest_pos, f"Victim {closest_id} at {closest_pos} (dist: {closest_dist}). Initiating rescue."
            else:
                stations = obs["charge_stations"]
                return stations[0], "No scanned victims. Patrolling near charge pads."

        elif action == 6:
            debris = obs.get("debris", [])
            if debris:
                closest_pos, closest_dist = None, 9999
                for d_pos in debris:
                    d = abs(d_pos[0] - pos[0]) + abs(d_pos[1] - pos[1])
                    if d < closest_dist:
                        closest_dist, closest_pos = d, d_pos
                return closest_pos, f"Debris at {closest_pos}. Proceeding to clear path."
            else:
                return self.quadrants[0], "No debris obstacles. Initiating search pattern."

        return pos, "Maintaining current holding position."

    def update(self, agent_id, state, action, reward, next_state, done):
        """Bellman Q-value update."""
        q_table = self.get_q_table(agent_id)
        num_actions = self.get_num_actions(agent_id)

        if state not in q_table:
            q_table[state] = np.zeros(num_actions, dtype=np.float32)
        if next_state not in q_table:
            q_table[next_state] = np.zeros(num_actions, dtype=np.float32)

        current_q = q_table[state][action]
        max_future_q = 0.0 if done else float(np.max(q_table[next_state]))
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
