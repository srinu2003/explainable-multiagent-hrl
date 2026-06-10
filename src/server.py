import http.server
import socketserver
import json
import os
import random
import numpy as np
import torch
import threading
from urllib.parse import urlparse, parse_qs
from environment import SearchRescueEnv
from high_level_agent import HighLevelAgent
from low_level_agent import LowLevelAgent
from explain import ExplainabilityEngine
from main import train_hrl

# Global instances and synchronization lock (BUG-13)
_state_lock = threading.Lock()
env = SearchRescueEnv()
hl_agent = HighLevelAgent()
ll_agent = LowLevelAgent()
xai_engine = ExplainabilityEngine()

# Try loading existing weights
WEIGHTS_DIR = "src/weights"
hl_weights = os.path.join(WEIGHTS_DIR, "weights_high.pkl")
ll_drone_weights = os.path.join(WEIGHTS_DIR, "weights_low_drone.pth")
ll_rover_weights = os.path.join(WEIGHTS_DIR, "weights_low_rover.pth")

if os.path.exists(hl_weights):
    hl_agent.load(hl_weights)
if os.path.exists(ll_drone_weights) and os.path.exists(ll_rover_weights):
    ll_agent.load(ll_drone_weights, ll_rover_weights)

class SARServerHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS and Cache-Control headers to prevent caching issues
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200, "ok")
        self.end_headers()

    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        if path == "/api/reset":
            with _state_lock:
                obs = env.reset()
                response = {
                    "status": "success",
                    "grid_size": env.grid_size,
                    "agents": {k: {"pos": v["pos"], "battery": v["battery"], "role": v["role"], "active": v["active"], "score": v["score"]} for k, v in env.agents.items()},
                    "victims": {k: {"pos": v["pos"], "status": v["status"]} for k, v in env.victims.items()},
                    "debris": [list(p) for p in env.debris_locations],
                    "fires": [list(p) for p in env.fire_locations],
                    "charge_stations": [list(cs) for cs in env.charge_stations]
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            
        elif path == "/api/simulate":
            # Run N steps using trained models (default 1, supports ?steps=N for batching)
            query = parse_qs(parsed_path.query)
            num_steps = max(1, min(10, int(query.get("steps", [1])[0])))

            with _state_lock:
                all_logs = []
                saliency_logs = {}
                done = False
                step_rewards = {}

                for _step_i in range(num_steps):
                    if done:
                        break

                    obs = env.get_observations()
                    hl_logs = {}
                    ll_logs = {}
                    micro_actions = {}

                    # 1. Check if agents need a high-level target assignment
                    for agent_id, agent in env.agents.items():
                        if not agent["active"]:
                            continue
                        if agent["sub_goal"] is None:
                            action_hl, sub_goal, reason = hl_agent.select_macro_goal(agent_id, obs[agent_id], epsilon=0.0, all_agents=env.agents)
                            agent["sub_goal"] = sub_goal
                            hl_explanation = xai_engine.justify_high_level(agent_id, obs[agent_id], action_hl, sub_goal, reason, env.agents)
                            hl_logs[agent_id] = hl_explanation

                    # 2. Select low-level primitive actions & compute explanations + saliency
                    for agent_id, agent in env.agents.items():
                        if not agent["active"]:
                            continue
                        state_ll = ll_agent.get_state_vector(agent_id, agent["pos"], agent["sub_goal"], obs[agent_id])
                        action_ll = ll_agent.select_action(agent_id, state_ll, pos=agent["pos"], sub_goal=agent["sub_goal"], obs=obs[agent_id], epsilon=0.0)
                        micro_actions[agent_id] = action_ll
                        ll_explanation = xai_engine.justify_low_level(agent_id, agent["pos"], agent["sub_goal"], action_ll, ll_agent, obs[agent_id])
                        ll_logs[agent_id] = ll_explanation
                        # Saliency only needs last step (expensive, skip intermediate)
                        if _step_i == num_steps - 1:
                            sal = xai_engine.compute_saliency(agent_id, agent["pos"], agent["sub_goal"], obs[agent_id], ll_agent)
                            saliency_logs[agent_id] = sal

                    # Step the environment
                    next_obs, step_rewards, done, info = env.step(micro_actions)

                    # Merge environment xai logs
                    for k, val in info.get("xai_logs", {}).items():
                        ll_logs[k] = val

                    # Collect logs for this micro-step
                    for agent_id in ["A1", "A2", "A3"]:
                        if agent_id in hl_logs:
                            all_logs.append({"type": "high_level", "agent": agent_id, "text": hl_logs[agent_id]})
                        if agent_id in ll_logs:
                            all_logs.append({"type": "low_level", "agent": agent_id, "text": ll_logs[agent_id]})

                response = {
                    "status": "success",
                    "done": done,
                    "step": env.step_count,
                    "agents": {k: {"pos": v["pos"], "battery": v["battery"], "role": v["role"], "active": v["active"], "score": v["score"], "sub_goal": v["sub_goal"]} for k, v in env.agents.items()},
                    "victims": {k: {"pos": v["pos"], "status": v["status"]} for k, v in env.victims.items()},
                    "debris": [list(p) for p in env.debris_locations],
                    "fires": [list(p) for p in env.fire_locations],
                    "charge_stations": [list(cs) for cs in env.charge_stations],
                    "mapped_grid": env.mapped_grid.tolist(),
                    "logs": all_logs[-20:],  # cap log payload to last 20 entries
                    "saliency": saliency_logs,
                    "rewards": step_rewards
                }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode("utf-8"))
            
        elif path == "/api/train":
            # Stream live training metrics over Server-Sent Events (SSE)
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.end_headers()
            
            # Fetch parameters
            query = parse_qs(parsed_path.query)
            num_episodes = int(query.get("episodes", [50])[0])
            
            print(f"SSE: Commencing training run for {num_episodes} episodes...")
            
            def sse_callback(metrics):
                try:
                    self.wfile.write(f"data: {json.dumps(metrics)}\n\n".encode("utf-8"))
                    self.wfile.flush()
                except Exception as e:
                    # Occurs if the user closes the tab or stops the training midway
                    pass
                    
            with _state_lock:
                train_hrl(env, hl_agent, ll_agent, on_epoch_end=sse_callback, num_episodes=num_episodes)
            print("SSE: Training finished successfully. Weights saved.")
            
        else:
            # Fall back to standard simple HTTP handler for static dashboard files
            super().do_GET()

def run_server(port=8000):
    handler = SARServerHandler
    # Enable socket reuse to avoid "Address already in use" errors on restart
    socketserver.TCPServer.allow_reuse_address = True
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        print(f"HTTP Server started on http://localhost:{port}/")
        print(f"To open the dashboard, open in browser:")
        print(f"  http://localhost:{port}/HTML-DEMO/live_demo.html")
        print("-" * 60)
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server.")
            httpd.server_close()

if __name__ == "__main__":
    run_server()
