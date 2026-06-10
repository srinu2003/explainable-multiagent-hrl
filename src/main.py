import os
import numpy as np
import torch
import random
from environment import SearchRescueEnv
from high_level_agent import HighLevelAgent
from low_level_agent import LowLevelAgent
from explain import ExplainabilityEngine


def train_hrl(env, hl_agent, ll_agent, on_epoch_end=None, num_episodes=300,
              update_target_every=10, best_val_path=None):
    """
    Hierarchical Reinforcement Learning training following SMDP/Options framework.

    Improvements:
    - Slower epsilon decay (0.97^ep, min 0.03) for more stable learning
    - Option timeout 60 steps
    - Target network updated every 10 episodes
    - Stronger distance shaping reward (±3.0 vs ±1.5)
    - +15 rescue bonus injected into low-level reward signal
    - 2 gradient updates/step once replay buffer is full
    - Best model checkpointing based on validation accuracy
    - Curriculum: first 30 eps use 0 fires to bootstrap exploration learning
    - Capped max_steps = 400 for speed
    - Early termination when Rover (A3) is inactive
    - Validate every 10 episodes (instead of every episode) to double training speed
    - Critical battery overrides at every step (aborts current sub-goal to charge)
    """
    print(f"Starting HRL Training for {num_episodes} episodes...")
    metrics_history = []
    os.makedirs("src/weights", exist_ok=True)

    best_val_acc = -1.0

    # Ensure max steps is capped at 400 for speed
    env.max_steps = 400

    for ep in range(1, num_episodes + 1):
        # ── CURRICULUM: no fires for first 30 episodes to bootstrap exploration ──
        if ep <= 30:
            cur_env = SearchRescueEnv(grid_size=env.grid_size,
                                      num_victims=env.num_victims,
                                      num_debris=env.num_debris,
                                      num_fires=0)
        else:
            cur_env = env

        cur_env.max_steps = 400
        obs = cur_env.reset()
        done = False
        ep_rewards = {"A1": 0.0, "A2": 0.0, "A3": 0.0}

        # SMDP option tracking
        option_start_states        = {k: None for k in cur_env.agents}
        option_actions             = {k: None for k in cur_env.agents}
        option_accumulated_rewards = {k: 0.0  for k in cur_env.agents}
        option_durations           = {k: 0    for k in cur_env.agents}

        # Epsilon decay
        epsilon_hl = max(0.03, 1.0 * (0.97 ** ep))
        epsilon_ll = max(0.03, 1.0 * (0.97 ** ep))

        buffer_warm = (len(ll_agent.memory_drone) >= ll_agent.batch_size or
                       len(ll_agent.memory_rover) >= ll_agent.batch_size)
        num_updates = 2 if buffer_warm else 1

        steps = 0
        total_loss = 0.0

        while not done:
            steps += 1
            micro_actions = {}

            # Early termination if Rover (A3) is dead
            if not cur_env.agents["A3"]["active"]:
                done = True
                break

            # ── Battery checks & Option timeout ───────────────────────────────
            for agent_id, agent in cur_env.agents.items():
                if not agent["active"]:
                    continue
                
                # Check for critical battery
                battery_critical = False
                if agent_id in ["A1", "A2"] and agent["battery"] <= 35:
                    battery_critical = True
                elif agent_id == "A3" and agent["battery"] <= 30:
                    battery_critical = True

                # If battery critical and not already heading to a charge pad, abort sub_goal
                is_charging_goal = False
                if agent["sub_goal"] is not None:
                    if tuple(agent["sub_goal"]) in cur_env.charge_stations:
                        is_charging_goal = True

                if battery_critical and not is_charging_goal:
                    agent["sub_goal"] = None

                # Option timeout check
                if agent["sub_goal"] is not None:
                    option_durations[agent_id] += 1
                    if option_durations[agent_id] >= 60:
                        agent["sub_goal"] = None

            # ── High-level decisions ─────────────────────────────────────────────
            for agent_id, agent in cur_env.agents.items():
                if not agent["active"]:
                    continue

                if agent["sub_goal"] is None:
                    if option_start_states[agent_id] is not None:
                        next_state_hl = hl_agent.get_state(agent_id, obs[agent_id], cur_env.agents)
                        hl_agent.update(
                            agent_id,
                            option_start_states[agent_id],
                            option_actions[agent_id],
                            option_accumulated_rewards[agent_id],
                            next_state_hl,
                            done=False
                        )

                    state_hl = hl_agent.get_state(agent_id, obs[agent_id], cur_env.agents)
                    action_hl, sub_goal, reason = hl_agent.select_macro_goal(
                        agent_id, obs[agent_id], epsilon=epsilon_hl, all_agents=cur_env.agents)

                    agent["sub_goal"] = sub_goal
                    option_start_states[agent_id]        = state_hl
                    option_actions[agent_id]             = action_hl
                    option_accumulated_rewards[agent_id] = 0.0
                    option_durations[agent_id]           = 0

            # ── Low-level decisions ──────────────────────────────────────────────
            low_level_states = {}
            for agent_id, agent in cur_env.agents.items():
                if not agent["active"]:
                    continue
                state_ll = ll_agent.get_state_vector(agent_id, agent["pos"], agent["sub_goal"], obs[agent_id])
                low_level_states[agent_id] = state_ll
                action_ll = ll_agent.select_action(
                    agent_id, state_ll, pos=agent["pos"],
                    sub_goal=agent["sub_goal"], obs=obs[agent_id], epsilon=epsilon_ll)
                micro_actions[agent_id] = action_ll

            # ── Environment step ─────────────────────────────────────────────────
            next_obs, step_rewards, done, info = cur_env.step(micro_actions)

            # ── Store transitions with enriched reward shaping ───────────────────
            for agent_id, agent in cur_env.agents.items():
                if not agent["active"] and agent_id not in micro_actions:
                    continue

                option_accumulated_rewards[agent_id] += step_rewards[agent_id]
                ep_rewards[agent_id] += step_rewards[agent_id]

                state_ll = low_level_states.get(agent_id)
                if state_ll is not None:
                    next_state_ll = ll_agent.get_state_vector(
                        agent_id, agent["pos"], agent["sub_goal"], next_obs[agent_id])

                    # Distance-based shaping: ±3.0
                    pos_before = obs[agent_id]["pos"]
                    pos_after  = next_obs[agent_id]["pos"]
                    goal       = agent["sub_goal"]
                    distance_reward = 0.0
                    if goal is not None:
                        dist_before = abs(goal[0] - pos_before[0]) + abs(goal[1] - pos_before[1])
                        dist_after  = abs(goal[0] - pos_after[0])  + abs(goal[1] - pos_after[1])
                        if dist_after < dist_before:
                            distance_reward = 3.0
                        elif dist_after > dist_before:
                            distance_reward = -3.0
                        if pos_after == goal:
                            distance_reward += 8.0

                    # Rescue bonus
                    rescue_bonus = 0.0
                    if agent_id == "A3":
                        for v in cur_env.victims.values():
                            if v["status"] == "rescued" and v["pos"] == agent["pos"]:
                                rescue_bonus = 15.0
                                break

                    ll_reward = step_rewards[agent_id] + distance_reward + rescue_bonus

                    ll_agent.store_transition(
                        agent_id,
                        state_ll,
                        micro_actions[agent_id],
                        ll_reward,
                        next_state_ll,
                        float(not agent["active"] or done)
                    )

            # ── Gradient update ──────────────────────────────────────────────────
            loss = ll_agent.train_step(num_updates=num_updates)
            total_loss += loss

            obs = next_obs

        # ── End of episode: finalize high-level Q-updates ────────────────────────
        for agent_id, agent in cur_env.agents.items():
            if option_start_states[agent_id] is not None:
                next_state_hl = hl_agent.get_state(agent_id, obs[agent_id], cur_env.agents)
                hl_agent.update(
                    agent_id,
                    option_start_states[agent_id],
                    option_actions[agent_id],
                    option_accumulated_rewards[agent_id],
                    next_state_hl,
                    done=True
                )

        # ── Target network update ──────────────────────
        if ep % update_target_every == 0:
            ll_agent.update_target_networks()

        # ── Training metrics ──────────────────────────────────────────────────────
        victims_saved = sum(1 for v in cur_env.victims.values() if v["status"] == "rescued")
        success_rate  = (victims_saved / cur_env.num_victims) * 100.0
        avg_reward    = float(np.mean(list(ep_rewards.values())))
        loss_val      = total_loss / max(1, steps)

        # ── Validation episode ───────────────────────
        # Run validation only every 10 episodes (and on episode 1) to speed up training by 2x
        if ep % 10 == 0 or ep == 1:
            env_val = SearchRescueEnv(
                grid_size=env.grid_size,
                num_victims=env.num_victims,
                num_debris=env.num_debris,
                num_fires=env.num_fires_initial
            )
            env_val.max_steps = 400
            random.seed(42 + ep)
            np.random.seed(42 + ep)
            obs_val = env_val.reset()
            done_val    = False
            val_steps   = 0
            val_total_loss = 0.0

            # Validation SMDP option tracking
            val_option_durations = {k: 0 for k in env_val.agents}

            while not done_val and val_steps < env_val.max_steps:
                val_steps += 1
                micro_actions_val = {}

                # Early termination if Rover (A3) is dead
                if not env_val.agents["A3"]["active"]:
                    done_val = True
                    break

                # ── Validation Battery checks & Option timeout ───────────────────────────────
                for agent_id, agent in env_val.agents.items():
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
                        if tuple(agent["sub_goal"]) in env_val.charge_stations:
                            is_charging_goal = True

                    if battery_critical and not is_charging_goal:
                        agent["sub_goal"] = None

                    # Option timeout check
                    if agent["sub_goal"] is not None:
                        val_option_durations[agent_id] += 1
                        if val_option_durations[agent_id] >= 60:
                            agent["sub_goal"] = None

                # ── Validation High-level decisions ─────────────────────────────────────────────
                for agent_id, agent in env_val.agents.items():
                    if not agent["active"]:
                        continue
                    if agent["sub_goal"] is None:
                        _, sub_goal, _ = hl_agent.select_macro_goal(
                            agent_id, obs_val[agent_id], epsilon=0.0, all_agents=env_val.agents)
                        agent["sub_goal"] = sub_goal
                        val_option_durations[agent_id] = 0

                # ── Validation Low-level decisions ──────────────────────────────────────────────
                low_level_states_val = {}
                for agent_id, agent in env_val.agents.items():
                    if not agent["active"]:
                        continue
                    state_ll = ll_agent.get_state_vector(
                        agent_id, agent["pos"], agent["sub_goal"], obs_val[agent_id])
                    low_level_states_val[agent_id] = state_ll
                    action_ll = ll_agent.select_action(
                        agent_id, state_ll, pos=agent["pos"],
                        sub_goal=agent["sub_goal"], obs=obs_val[agent_id], epsilon=0.0)
                    micro_actions_val[agent_id] = action_ll

                next_obs_val, step_rewards_val, done_val, _ = env_val.step(micro_actions_val)

                for agent_id, agent in env_val.agents.items():
                    if not agent["active"] and agent_id not in micro_actions_val:
                        continue
                    state_ll = low_level_states_val.get(agent_id)
                    if state_ll is not None:
                        next_state_ll = ll_agent.get_state_vector(
                            agent_id, agent["pos"], agent["sub_goal"], next_obs_val[agent_id])
                        policy_net = ll_agent.get_policy_net(agent_id)
                        target_net = ll_agent.get_target_net(agent_id)
                        with torch.no_grad():
                            q_val = policy_net(state_ll.unsqueeze(0))[0, micro_actions_val[agent_id]].item()
                            next_q = target_net(next_state_ll.unsqueeze(0)).max(1)[0].item()
                            target_q = step_rewards_val[agent_id] + ll_agent.gamma * next_q * (
                                1.0 - float(not agent["active"] or done_val))
                            val_total_loss += (q_val - target_q) ** 2

                obs_val = next_obs_val

            val_victims_saved = sum(1 for v in env_val.victims.values() if v["status"] == "rescued")
            val_acc  = (val_victims_saved / env_val.num_victims) * 100.0
            val_loss = val_total_loss / max(1, val_steps)
        else:
            # Re-use previous validation metrics if we didn't validate this episode
            val_acc = metrics_history[-1]["val_acc"] if metrics_history else 0.0
            val_loss = metrics_history[-1]["val_loss"] if metrics_history else 0.0

        random.seed(None)
        np.random.seed(None)

        metrics = {
            "epoch":      ep,
            "train_acc":  round(success_rate, 2),
            "val_acc":    round(val_acc, 2),
            "train_loss": round(loss_val, 4),
            "val_loss":   round(val_loss, 4),
            "reward":     round(avg_reward, 2),
            "epsilon":    round(epsilon_ll, 4)
        }
        metrics_history.append(metrics)

        if on_epoch_end is not None:
            on_epoch_end(metrics)

        if ep % 10 == 0 or ep == 1:
            print(f"Ep {ep:03d}/{num_episodes} | Train: {metrics['train_acc']:5.1f}% | "
                  f"Val: {metrics['val_acc']:5.1f}% | Loss: {metrics['train_loss']:.4f} | "
                  f"eps={metrics['epsilon']:.3f}")

        # ── Best-model checkpoint ─────────────────────────────────────────────────
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            hl_agent.save("src/weights/weights_high_best.pkl")
            ll_agent.save("src/weights/weights_low_drone_best.pth",
                          "src/weights/weights_low_rover_best.pth")

    # ── Save final weights ────────────────────────────────────────────────────────
    hl_agent.save("src/weights/weights_high.pkl")
    ll_agent.save("src/weights/weights_low_drone.pth", "src/weights/weights_low_rover.pth")
    print(f"Training finished! Best val acc: {best_val_acc:.1f}%")
    print("Weights saved to src/weights/")

    return metrics_history


if __name__ == "__main__":
    print("=" * 80)
    print("EXPLAINABLE MULTI-AGENT HIERARCHICAL REINFORCEMENT LEARNING FOR SEARCH & RESCUE")
    print("=" * 80)

    env = SearchRescueEnv()
    hl_agent = HighLevelAgent()
    ll_agent = LowLevelAgent()

    obs = env.reset()
    print(f"Grid: {env.grid_size}x{env.grid_size} | Agents: {list(env.agents.keys())} | "
          f"Victims: {list(env.victims.keys())} | Debris: {len(env.debris_locations)}")
    print("-" * 80)

    train_hrl(env, hl_agent, ll_agent, on_epoch_end=None, num_episodes=5)
    print("=" * 80)