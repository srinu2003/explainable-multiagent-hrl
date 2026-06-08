import math

class AgentState:
    def __init__(self, agent_id, pos, role):
        self.agent_id = agent_id
        self.pos = pos  # (x, y)
        self.role = role

class Environment:
    def __init__(self):
        self.grid_size = 5
        # Victim location
        self.victim_pos = (1, 5)
        # Debris/Hazard location
        self.hazard_pos = (3, 3)
        # Initialize two agents
        self.agents = {
            "A1_Drone": AgentState("A1_Drone", (1, 1), "Reconnaissance"),
            "A2_Robot": AgentState("A2_Robot", (4, 4), "Clear_Path")
        }

class HierarchicalPolicies:
    """Simulates the High-Level (strategic) and Low-Level (tactical) neural policies."""
    
    @staticmethod
    def get_high_level_policy(agent, env):
        # High-level policy assigns a macro task/destination based on agent role
        if agent.role == "Reconnaissance":
            sub_goal = env.victim_pos
            reason = "Victim detected at location. Prioritizing search/verification."
        else:
            sub_goal = env.hazard_pos
            reason = "Debris detected blocking coordinates. Prioritizing clearing path."
        return sub_goal, reason

    @staticmethod
    def get_low_level_policy(agent, sub_goal):
        # Low-level policy picks a spatial primitive action to get closer to the sub-goal
        curr_x, curr_y = agent.pos
        goal_x, goal_y = sub_goal
        
        # Determine movement priorities
        if curr_x < goal_x:
            action = "Move South"
            next_pos = (curr_x + 1, curr_y)
        elif curr_x > goal_x:
            action = "Move North"
            next_pos = (curr_x - 1, curr_y)
        elif curr_y < goal_y:
            action = "Move East"
            next_pos = (curr_x, curr_y + 1)
        elif curr_y > goal_y:
            action = "Move West"
            next_pos = (curr_x, curr_y - 1)
        else:
            action = "Stay / Interact"
            next_pos = (curr_x, curr_y)
            
        return action, next_pos

class ExplainabilityEngine:
    """Formats decision traces and justifications (Action Justification, Policy Traceability)."""
    
    @staticmethod
    def justify_action(agent, sub_goal, action, reason):
        dist = math.sqrt((agent.pos[0] - sub_goal[0])**2 + (agent.pos[1] - sub_goal[1])**2)
        print(f"\n[EXPLAINABILITY ENGINE - ACTION JUSTIFICATION FOR {agent.agent_id}]")
        print(f" ├─ Why this Sub-Goal? : {reason}")
        print(f" ├─ Target Coordinates : {sub_goal} (Current Distance: {dist:.2f} units)")
        print(f" ├─ Primitive Action   : '{action}'")
        print(f" └─ Rationale          : Selected '{action}' because it maximizes proximity progress towards {sub_goal}.")

    @staticmethod
    def print_trace(agent, sub_goal, action, next_pos):
        print(f" [TRACE LOG] {agent.agent_id} | Initial: {agent.pos} -> Goal: {sub_goal} -> Selected Action: {action} -> New Pos: {next_pos}")

# --- Execution Demonstration ---
if __name__ == "__main__":
    print("=" * 75)
    print("EXPLAINABLE MULTI-AGENT HRL FRAMEWORK DEMONSTRATION")
    print("=" * 75)
    
    # 1. Initialize environment
    env = Environment()
    print(f"System Status: Shared Environment Initialized.")
    print(f"  - Active Hazards detected at: {env.hazard_pos}")
    print(f"  - Target Mission Goal located at: {env.victim_pos}")
    print("-" * 75)
    
    # 2. Iterate through cooperative agents (Algorithm 1 loop)
    for agent_name, agent_state in env.agents.items():
        # High-Level Decision Layer
        sub_goal, hl_reason = HierarchicalPolicies.get_high_level_policy(agent_state, env)
        
        # Low-Level Action Layer
        action, next_pos = HierarchicalPolicies.get_low_level_policy(agent_state, sub_goal)
        
        # Explainability Engine Processing
        ExplainabilityEngine.justify_action(agent_state, sub_goal, action, hl_reason)
        ExplainabilityEngine.print_trace(agent_state, sub_goal, action, next_pos)
        print("-" * 75)