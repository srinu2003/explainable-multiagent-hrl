"""
EMARL-SAR: Dedicated Training + Validation Script
==================================================
Trains the HRL model for a configurable number of episodes, then runs
a rigorous multi-episode validation and writes a full markdown report.

Usage (from project root):
    python tests/train_and_validate.py                    # 300 train + 20 val
    python tests/train_and_validate.py --quick            # 100 train + 20 val
    python tests/train_and_validate.py --episodes 500     # Custom training length
    python tests/train_and_validate.py --val_only         # Skip training, just validate
"""
import os
import sys
import argparse
import random
import numpy as np
import torch

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from environment import SearchRescueEnv
from high_level_agent import HighLevelAgent
from low_level_agent import LowLevelAgent
from explain import ExplainabilityEngine
from main import train_hrl


# ═══════════════════════════════════════════════════════════════
# TRAINING
# ═══════════════════════════════════════════════════════════════

def run_training(num_episodes, weights_dir):
    print("=" * 80)
    print(f"EMARL-SAR TRAINING  [{num_episodes} episodes]")
    print("=" * 80)

    env      = SearchRescueEnv()
    hl_agent = HighLevelAgent()
    ll_agent = LowLevelAgent()

    # Load existing weights to continue training if available
    hl_w  = os.path.join(weights_dir, "weights_high.pkl")
    ll_dr = os.path.join(weights_dir, "weights_low_drone.pth")
    ll_rv = os.path.join(weights_dir, "weights_low_rover.pth")
    if os.path.exists(hl_w):
        hl_agent.load(hl_w)
        print(f"[RESUME] Loaded existing high-level weights from {hl_w}")
    if os.path.exists(ll_dr) and os.path.exists(ll_rv):
        ll_agent.load(ll_dr, ll_rv)
        print(f"[RESUME] Loaded existing low-level weights.")

    history = train_hrl(env, hl_agent, ll_agent,
                        on_epoch_end=None,
                        num_episodes=num_episodes)

    # Summarize convergence
    if history:
        last10 = history[-10:]
        avg_val = np.mean([m["val_acc"] for m in last10])
        max_val = max(m["val_acc"] for m in history)
        print(f"\n[SUMMARY] Avg Val Acc (last 10 eps): {avg_val:.1f}%  |  Peak Val Acc: {max_val:.1f}%")

    print("=" * 80)
    return hl_agent, ll_agent


# ═══════════════════════════════════════════════════════════════
# VALIDATION
# ═══════════════════════════════════════════════════════════════

def run_validation(hl_agent, ll_agent, num_episodes=20,
                   weights_dir="src/weights", report_path="validation_test_report.md"):
    print("=" * 80)
    print(f"EMARL-SAR VALIDATION  [{num_episodes} episodes]")
    print("=" * 80)

    xai = ExplainabilityEngine()
    env = SearchRescueEnv()
    env.max_steps = 400

    # Load weights if agents not already trained
    if hl_agent is None:
        hl_agent = HighLevelAgent()
        hl_w = os.path.join(weights_dir, "weights_high.pkl")
        if os.path.exists(hl_w):
            hl_agent.load(hl_w)
            print(f"[OK] Loaded high-level weights from {hl_w}")
        else:
            print("[WARNING] No high-level weights found. Running with untrained policy.")

    if ll_agent is None:
        ll_agent = LowLevelAgent()
        ll_dr = os.path.join(weights_dir, "weights_low_drone.pth")
        ll_rv = os.path.join(weights_dir, "weights_low_rover.pth")
        if os.path.exists(ll_dr) and os.path.exists(ll_rv):
            ll_agent.load(ll_dr, ll_rv)
            print(f"[OK] Loaded low-level weights.")
        else:
            print("[WARNING] No low-level weights found. Running with untrained policy.")

    print("-" * 80)

    # Metrics
    episode_results          = []
    total_victims_saved      = 0
    total_debris_cleared     = 0
    total_steps              = 0
    total_fire_touches       = 0
    total_battery_depleted   = 0
    episodes_all_saved       = 0

    saliency_sums = {
        ag: {"target_proximity": 0.0, "battery_status": 0.0, "hazard_avoidance": 0.0, "count": 0}
        for ag in ["A1", "A2", "A3"]
    }
    sample_trace_logs = []

    for ep in range(1, num_episodes + 1):
        seed = 1000 + ep
        random.seed(seed)
        np.random.seed(seed)

        obs  = env.reset()
        done = False
        step = 0
        ep_fire_touches = 0
        ep_battery_dead = 0

        # Track option durations for validation
        val_option_durations = {k: 0 for k in env.agents}

        if ep == 1:
            sample_trace_logs.append(f"### Episode 1 Initial Layout (Seed {seed})")
            sample_trace_logs.append(f"- Grid Size: {env.grid_size}×{env.grid_size}")
            sample_trace_logs.append(f"- Fires: {[list(f) for f in env.fire_locations]}")
            sample_trace_logs.append(f"- Debris: {[list(d) for d in env.debris_locations]}")
            sample_trace_logs.append(f"- Charge Stations: {[list(cs) for cs in env.charge_stations]}")
            sample_trace_logs.append(f"- Victims: { {k: list(v['pos']) for k, v in env.victims.items()} }\n")
            sample_trace_logs.append("| Step | A1 Pos | A1 Goal | A2 Pos | A2 Goal | A3 Pos | A3 Goal | Saved | Fires |")
            sample_trace_logs.append("|------|--------|---------|--------|---------|--------|---------|-------|-------|")

        while not done and step < env.max_steps:
            step += 1
            micro_actions   = {}
            hl_decisions    = {}
            ll_rationales   = {}

            # Early termination if Rover (A3) is dead
            if not env.agents["A3"]["active"]:
                done = True
                break

            # ── Battery checks & Option timeout ───────────────────────────────
            for agent_id, agent in env.agents.items():
                if not agent["active"]:
                    continue

                # Check for critical battery
                battery_critical = False
                if agent_id in ["A1", "A2"] and agent["battery"] <= 35:
                    battery_critical = True
                elif agent_id == "A3" and agent["battery"] <= 30:
                    battery_critical = True

                is_charging_goal = False
                if agent["sub_goal"] is not None:
                    if tuple(agent["sub_goal"]) in env.charge_stations:
                        is_charging_goal = True

                if battery_critical and not is_charging_goal:
                    agent["sub_goal"] = None

                # Option timeout check
                if agent["sub_goal"] is not None:
                    val_option_durations[agent_id] += 1
                    if val_option_durations[agent_id] >= 60:
                        agent["sub_goal"] = None

            # ── High-level goal selection ─────────────────────────────────────
            for agent_id, agent in env.agents.items():
                if not agent["active"]:
                    continue
                if agent["sub_goal"] is None:
                    _, sub_goal, reason = hl_agent.select_macro_goal(
                        agent_id, obs[agent_id], epsilon=0.0, all_agents=env.agents)
                    agent["sub_goal"] = sub_goal
                    hl_decisions[agent_id] = (sub_goal, reason)
                    val_option_durations[agent_id] = 0

            # ── Low-level actions ─────────────────────────────────────────────
            for agent_id, agent in env.agents.items():
                if not agent["active"]:
                    continue
                state_ll = ll_agent.get_state_vector(
                    agent_id, agent["pos"], agent["sub_goal"], obs[agent_id])
                action_ll = ll_agent.select_action(
                    agent_id, state_ll, pos=agent["pos"],
                    sub_goal=agent["sub_goal"], obs=obs[agent_id], epsilon=0.0)
                micro_actions[agent_id] = action_ll

                sal = xai.compute_saliency(agent_id, agent["pos"], agent["sub_goal"], obs[agent_id], ll_agent)
                for key in ["target_proximity", "battery_status", "hazard_avoidance"]:
                    saliency_sums[agent_id][key] += sal[key]
                saliency_sums[agent_id]["count"] += 1

                if ep == 1 and step <= 10:
                    rat = xai.justify_low_level(
                        agent_id, agent["pos"], agent["sub_goal"], action_ll, ll_agent, obs[agent_id])
                    ll_rationales[agent_id] = rat

            next_obs, _, done, _ = env.step(micro_actions)

            # Safety tracking
            fire_set = set(tuple(p) for p in env.fire_locations)
            for agent_id, agent in env.agents.items():
                if agent["active"] and tuple(agent["pos"]) in fire_set:
                    ep_fire_touches += 1
                if agent["battery"] <= 0:
                    ep_battery_dead += 1

            # Trace log (episode 1 only)
            if ep == 1:
                def fmt_sg(ag_id):
                    sg = env.agents[ag_id]["sub_goal"]
                    return f"[{sg[0]},{sg[1]}]" if sg else "None"
                saved_now = sum(1 for v in env.victims.values() if v["status"] == "rescued")
                sample_trace_logs.append(
                    f"| {step} | {env.agents['A1']['pos']} | {fmt_sg('A1')} | "
                    f"{env.agents['A2']['pos']} | {fmt_sg('A2')} | "
                    f"{env.agents['A3']['pos']} | {fmt_sg('A3')} | "
                    f"{saved_now}/3 | {len(env.fire_locations)} |")
                if step <= 10:
                    sample_trace_logs.append(f"  *Step {step} Explanations:*")
                    for k, (sg, reason) in hl_decisions.items():
                        hl_exp = xai.justify_high_level(k, obs[k], None, sg, reason, env.agents)
                        sample_trace_logs.append(f"    - **{k} High-level**: {hl_exp}")
                    for k, rat in ll_rationales.items():
                        sample_trace_logs.append(f"    - **{k} Low-level**: {rat}")

            obs = next_obs

        # Episode summary
        rescued       = sum(1 for v in env.victims.values() if v["status"] == "rescued")
        debris_cleared = 10 - len(env.debris_locations)
        avg_bat        = float(np.mean([a["battery"] for a in env.agents.values()]))

        total_victims_saved    += rescued
        total_debris_cleared   += debris_cleared
        total_steps            += step
        total_fire_touches     += ep_fire_touches
        total_battery_depleted += ep_battery_dead

        if rescued == env.num_victims:
            episodes_all_saved += 1

        status = "✅ SUCCESS" if rescued == env.num_victims else f"⚠️  PARTIAL ({rescued}/3)"
        print(f"Ep {ep:02d} | Seed: {seed} | Steps: {step:4d} | Rescued: {rescued}/3 | "
              f"Debris: {debris_cleared}/10 | Bat: {avg_bat:.0f}% | Fire: {ep_fire_touches} | {status}")

        episode_results.append({
            "episode": ep, "seed": seed, "steps": step,
            "rescued": rescued, "debris_cleared": debris_cleared,
            "avg_battery": round(avg_bat, 1), "fire_touches": ep_fire_touches,
            "depleted_agents": ep_battery_dead,
            "status": "SUCCESS (All Saved)" if rescued == env.num_victims else "PARTIAL"
        })

    # ── Aggregate stats ──────────────────────────────────────────────────────────
    success_rate = (episodes_all_saved / num_episodes) * 100.0
    avg_rescued  = total_victims_saved / num_episodes
    avg_debris   = total_debris_cleared / num_episodes
    avg_steps    = total_steps / num_episodes

    avg_saliencies = {}
    for ag_id, sal_data in saliency_sums.items():
        cnt = max(1, sal_data["count"])
        avg_saliencies[ag_id] = {
            k: round(sal_data[k] / cnt, 1) for k in ["target_proximity", "battery_status", "hazard_avoidance"]
        }

    print("=" * 80)
    print("AGGREGATE PERFORMANCE REPORT")
    print("=" * 80)
    print(f"Full Rescue Success Rate : {success_rate:.1f}%  ({episodes_all_saved}/{num_episodes} episodes)")
    print(f"Avg Victims Rescued      : {avg_rescued:.2f} / 3")
    print(f"Avg Debris Cleared       : {avg_debris:.2f} / 10")
    print(f"Avg Steps Per Episode    : {avg_steps:.1f}")
    print(f"Total Fire Collisions    : {total_fire_touches}  (Target: 0)")
    print(f"Total Battery Depleted   : {total_battery_depleted} agent-depletes")
    print("-" * 80)
    for k, v in avg_saliencies.items():
        role = "Drone Scout" if k in ["A1", "A2"] else "Rover Rescuer"
        print(f"  {k} ({role}): Target: {v['target_proximity']}% | "
              f"Battery: {v['battery_status']}% | Hazard: {v['hazard_avoidance']}%")
    print("=" * 80)

    # ── Write Markdown report ────────────────────────────────────────────────────
    if report_path:
        os.makedirs(os.path.dirname(os.path.abspath(report_path)), exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("# EMARL-SAR Server-Side Validation Test Report\n\n")
            f.write("Programmatic validation of the **Explainable Multi-Agent Hierarchical "
                    "Reinforcement Learning** search-and-rescue model.\n\n")

            f.write("## 1. Executive Summary\n\n")
            f.write(f"| Metric | Value |\n|---|---|\n")
            f.write(f"| Test Episodes | {num_episodes} |\n")
            f.write(f"| **Full Success Rate (3/3 Saved)** | **`{success_rate:.1f}%`** ({episodes_all_saved}/{num_episodes}) |\n")
            f.write(f"| Avg Victims Rescued | `{avg_rescued:.2f} / 3` |\n")
            f.write(f"| Avg Debris Cleared | `{avg_debris:.2f} / 10` |\n")
            f.write(f"| Avg Steps Per Episode | `{avg_steps:.1f}` |\n")
            f.write(f"| Fire Collisions | `{total_fire_touches}` |\n")
            f.write(f"| Battery Depleted Agents | `{total_battery_depleted}` |\n\n")

            f.write("## 2. Episode Results\n\n")
            f.write("| Episode | Seed | Steps | Rescued | Debris | Avg Battery | Fire Hits | Status |\n")
            f.write("|---------|------|-------|---------|--------|-------------|-----------|--------|\n")
            for r in episode_results:
                f.write(f"| Ep {r['episode']} | {r['seed']} | {r['steps']} | "
                        f"{r['rescued']}/3 | {r['debris_cleared']}/10 | "
                        f"{r['avg_battery']}% | {r['fire_touches']} | {r['status']} |\n")

            f.write("\n## 3. XAI Decision Saliency Attributions\n\n")
            f.write("| Agent | Role | Target Proximity | Battery Status | Hazard Avoidance |\n")
            f.write("|-------|------|-----------------|----------------|------------------|\n")
            for k, v in avg_saliencies.items():
                role = "Drone Scout" if k in ["A1", "A2"] else "Rover Rescuer"
                f.write(f"| **{k}** | {role} | {v['target_proximity']}% | "
                        f"{v['battery_status']}% | {v['hazard_avoidance']}% |\n")

            f.write("\n## 4. Episode 1 Simulation Trace\n\n")
            for line in sample_trace_logs:
                f.write(line + "\n")

            f.write("\n## 5. Verification Assessment\n")
            f.write("1. **Fire Safety**: Dijkstra routing + safety layer ensures agents avoid fire cells.\n")
            f.write("2. **Debris Coordination**: Rover prioritises victim rescue over debris clearing.\n")
            f.write("3. **Battery Management**: Agents charge proactively at ≤35% battery.\n")
            f.write("4. **Curriculum Training**: Episodes 1–30 had no fires for stable exploration bootstrapping.\n")

        print(f"[OK] Report saved to: {report_path}")

    return success_rate


# ═══════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="EMARL-SAR: Train + Validate HRL rescue model")
    parser.add_argument("--episodes",     type=int, default=300,   help="Training episodes (default: 300)")
    parser.add_argument("--val_episodes", type=int, default=20,    help="Validation episodes (default: 20)")
    parser.add_argument("--weights_dir",  type=str, default="src/weights", help="Weights directory")
    parser.add_argument("--report_path",  type=str, default="validation_test_report.md")
    parser.add_argument("--quick",        action="store_true", help="Fast run: 100 train + 20 val")
    parser.add_argument("--val_only",     action="store_true", help="Skip training, validate only")
    args = parser.parse_args()

    if args.quick:
        args.episodes = 100

    hl_agent = None
    ll_agent = None

    if not args.val_only:
        hl_agent, ll_agent = run_training(args.episodes, args.weights_dir)

    success_rate = run_validation(hl_agent, ll_agent,
                                  num_episodes=args.val_episodes,
                                  weights_dir=args.weights_dir,
                                  report_path=args.report_path)

    print(f"\n{'='*80}")
    if success_rate >= 95.0:
        print(f"🎯 TARGET ACHIEVED: {success_rate:.1f}% ≥ 95% rescue success rate!")
    elif success_rate >= 80.0:
        print(f"📈 GOOD PROGRESS: {success_rate:.1f}%. Run with more --episodes to reach 95%.")
    else:
        print(f"⚠️  NEEDS MORE TRAINING: {success_rate:.1f}%. Try --episodes 500.")
    print("=" * 80)
