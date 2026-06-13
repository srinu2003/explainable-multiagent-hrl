# EMARL-SAR Server-Side Validation Test Report

Programmatic validation of the **Explainable Multi-Agent Hierarchical Reinforcement Learning** search-and-rescue model.

## 1. Executive Summary

| Metric | Value |
|---|---|
| Test Episodes | 20 |
| **Full Success Rate (3/3 Saved)** | **`10.0%`** (2/20) |
| Avg Victims Rescued | `1.50 / 3` |
| Avg Debris Cleared | `2.55 / 10` |
| Avg Steps Per Episode | `136.4` |
| Fire Collisions | `0` |
| Battery Depleted Agents | `53` |

## 2. Episode Results

| Episode | Seed | Steps | Rescued | Debris | Avg Battery | Fire Hits | Status |
|---------|------|-------|---------|--------|-------------|-----------|--------|
| Ep 1 | 1001 | 150 | 1/3 | 1/10 | 44.0% | 0 | PARTIAL |
| Ep 2 | 1002 | 150 | 0/3 | 2/10 | 43.3% | 0 | PARTIAL |
| Ep 3 | 1003 | 150 | 2/3 | 1/10 | 68.3% | 0 | PARTIAL |
| Ep 4 | 1004 | 150 | 0/3 | 1/10 | 60.3% | 0 | PARTIAL |
| Ep 5 | 1005 | 150 | 0/3 | 5/10 | 70.0% | 0 | PARTIAL |
| Ep 6 | 1006 | 95 | 2/3 | 2/10 | 35.0% | 0 | PARTIAL |
| Ep 7 | 1007 | 150 | 2/3 | 3/10 | 39.3% | 0 | PARTIAL |
| Ep 8 | 1008 | 150 | 2/3 | 1/10 | 64.7% | 0 | PARTIAL |
| Ep 9 | 1009 | 150 | 2/3 | 2/10 | 62.3% | 0 | PARTIAL |
| Ep 10 | 1010 | 150 | 0/3 | 2/10 | 29.7% | 0 | PARTIAL |
| Ep 11 | 1011 | 55 | 3/3 | 1/10 | 46.7% | 0 | SUCCESS (All Saved) |
| Ep 12 | 1012 | 150 | 2/3 | 5/10 | 55.7% | 0 | PARTIAL |
| Ep 13 | 1013 | 150 | 2/3 | 4/10 | 52.7% | 0 | PARTIAL |
| Ep 14 | 1014 | 98 | 1/3 | 1/10 | 55.3% | 0 | PARTIAL |
| Ep 15 | 1015 | 150 | 2/3 | 5/10 | 41.3% | 0 | PARTIAL |
| Ep 16 | 1016 | 81 | 3/3 | 2/10 | 88.7% | 0 | SUCCESS (All Saved) |
| Ep 17 | 1017 | 150 | 2/3 | 4/10 | 43.3% | 0 | PARTIAL |
| Ep 18 | 1018 | 150 | 1/3 | 0/10 | 41.0% | 0 | PARTIAL |
| Ep 19 | 1019 | 150 | 2/3 | 4/10 | 54.0% | 0 | PARTIAL |
| Ep 20 | 1020 | 150 | 1/3 | 5/10 | 19.7% | 0 | PARTIAL |

## 3. XAI Decision Saliency Attributions

| Agent | Role | Target Proximity | Battery Status | Hazard Avoidance |
|-------|------|-----------------|----------------|------------------|
| **A1** | Drone Scout | 56.1% | 22.5% | 21.4% |
| **A2** | Drone Scout | 64.1% | 14.7% | 21.2% |
| **A3** | Rover Rescuer | 55.7% | 13.7% | 30.6% |

## 4. Episode 1 Simulation Trace

### Episode 1 Initial Layout (Seed 1001)
- Grid Size: 15×15
- Fires: [[10, 12], [6, 10]]
- Debris: [[2, 13], [5, 2], [10, 7], [4, 7], [7, 10], [12, 13], [8, 13], [11, 4], [11, 1], [2, 12]]
- Charge Stations: [[0, 7], [14, 7]]
- Victims: {'V1': [12, 10], 'V2': [3, 1], 'V3': [10, 2]}

| Step | A1 Pos | A1 Goal | A2 Pos | A2 Goal | A3 Pos | A3 Goal | Saved | Fires |
|------|--------|---------|--------|---------|--------|---------|-------|-------|
| 1 | [0, 1] | [3,11] | [1, 14] | [3,11] | [13, 7] | [14,7] | 0/3 | 2 |
  *Step 1 Explanations:*
    - **A1 High-level**: [High-Level Plan for Drone 1 (Scout)] Reason: Prioritizing exploration of the North-East sector. | status: Agent battery is at 100%. (Coordinating search sectors with Drone 2 (Scout) heading to [3, 11], Rover 3 (Rescuer) heading to [14, 7])
    - **A2 High-level**: [High-Level Plan for Drone 2 (Scout)] Reason: Prioritizing exploration of the North-East sector. | status: Agent battery is at 100%. (Coordinating search sectors with Drone 1 (Scout) heading to [3, 11], Rover 3 (Rescuer) heading to [14, 7])
    - **A3 High-level**: [High-Level Plan for Rover 3 (Rescuer)] Reason: Battery at 100%. Retiring to charging pad at [14, 7]. | status: Agent battery is at 100%. (Coordinating search sectors with Drone 1 (Scout) heading to [3, 11], Drone 2 (Scout) heading to [3, 11])
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move North' to move NORTH, increasing distance (rerouting) to sub-goal at [14, 7].
| 2 | [0, 2] | [3,11] | [2, 14] | [3,11] | [13, 8] | [14,7] | 0/3 | 2 |
  *Step 2 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move East' to move EAST, increasing distance (rerouting) to sub-goal at [14, 7].
| 3 | [0, 3] | [3,11] | [3, 14] | [3,11] | [13, 9] | [14,7] | 0/3 | 2 |
  *Step 3 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move East' to move EAST, increasing distance (rerouting) to sub-goal at [14, 7].
| 4 | [0, 4] | [3,11] | [3, 13] | [3,11] | [14, 9] | [14,7] | 0/3 | 2 |
  *Step 4 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [14, 7].
| 5 | [0, 5] | [3,11] | [3, 12] | [3,11] | [13, 9] | [14,7] | 0/3 | 2 |
  *Step 5 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move North' to move NORTH, increasing distance (rerouting) to sub-goal at [14, 7].
| 6 | [0, 6] | [3,11] | [3, 11] | None | [14, 9] | [14,7] | 0/3 | 2 |
  *Step 6 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [3, 11].
    - **A3 Low-level**: Rover A3 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [14, 7].
| 7 | [0, 7] | [3,11] | [2, 11] | [0,7] | [13, 9] | [14,7] | 0/3 | 5 |
  *Step 7 Explanations:*
    - **A2 High-level**: [High-Level Plan for Drone 2 (Scout)] Reason: Battery at 94%. Retiring to charging pad at [0, 7]. | status: Agent battery is at 94%. (Coordinating search sectors with Drone 1 (Scout) heading to [3, 11], Rover 3 (Rescuer) heading to [14, 7])
    - **A1 Low-level**: Drone A1 selected action 'Move East' to move EAST, reducing horizontal distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move North' to move NORTH, reducing vertical distance to sub-goal at [0, 7].
    - **A3 Low-level**: Rover A3 selected action 'Move North' to move NORTH, increasing distance (rerouting) to sub-goal at [14, 7].
| 8 | [0, 7] | [3,11] | [2, 10] | [0,7] | [14, 9] | [14,7] | 0/3 | 5 |
  *Step 8 Explanations:*
    - **A1 Low-level**: Drone A1 initiated charging sequence at station [0, 7] due to low battery.
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [0, 7].
    - **A3 Low-level**: Rover A3 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [14, 7].
| 9 | [1, 7] | [3,11] | [2, 9] | [0,7] | [14, 8] | [14,7] | 0/3 | 5 |
  *Step 9 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move South' to move SOUTH, reducing vertical distance to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [0, 7].
    - **A3 Low-level**: Rover A3 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [14, 7].
| 10 | [0, 7] | [3,11] | [2, 8] | [0,7] | [13, 8] | [14,7] | 0/3 | 5 |
  *Step 10 Explanations:*
    - **A1 Low-level**: Drone A1 selected action 'Move North' to move NORTH, increasing distance (rerouting) to sub-goal at [3, 11].
    - **A2 Low-level**: Drone A2 selected action 'Move West' to move WEST, reducing horizontal distance to sub-goal at [0, 7].
    - **A3 Low-level**: Rover A3 selected action 'Move North' to move NORTH, increasing distance (rerouting) to sub-goal at [14, 7].
| 11 | [1, 7] | [3,11] | [1, 8] | [0,7] | [13, 9] | [14,7] | 0/3 | 5 |
| 12 | [0, 7] | [3,11] | [0, 8] | [0,7] | [14, 9] | [14,7] | 0/3 | 5 |
| 13 | [0, 7] | [3,11] | [0, 7] | None | [13, 9] | [14,7] | 0/3 | 5 |
| 14 | [0, 7] | [3,11] | [0, 7] | None | [13, 8] | [14,7] | 0/3 | 6 |
| 15 | [0, 7] | [3,11] | [1, 7] | [0,7] | [13, 9] | [14,7] | 0/3 | 6 |
| 16 | [1, 7] | [3,11] | [1, 8] | [0,7] | [13, 8] | [14,7] | 0/3 | 6 |
| 17 | [0, 7] | [3,11] | [0, 8] | [0,7] | [13, 9] | [14,7] | 0/3 | 6 |
| 18 | [1, 7] | [3,11] | [0, 8] | [0,7] | [13, 8] | [14,7] | 0/3 | 6 |
| 19 | [0, 7] | [3,11] | [0, 8] | [0,7] | [13, 7] | [14,7] | 0/3 | 6 |
| 20 | [0, 7] | [3,11] | [0, 8] | [0,7] | [12, 7] | [14,7] | 0/3 | 6 |
| 21 | [0, 7] | [3,11] | [0, 8] | [0,7] | [13, 7] | [14,7] | 0/3 | 9 |
| 22 | [0, 7] | [3,11] | [0, 8] | [0,7] | [12, 7] | [14,7] | 0/3 | 9 |
| 23 | [1, 7] | [3,11] | [0, 7] | None | [13, 7] | [14,7] | 0/3 | 9 |
| 24 | [0, 7] | [3,11] | [0, 7] | None | [12, 7] | [14,7] | 0/3 | 9 |
| 25 | [1, 7] | [3,11] | [1, 7] | [0,7] | [13, 7] | [14,7] | 0/3 | 9 |
| 26 | [0, 7] | [3,11] | [1, 8] | [0,7] | [14, 7] | None | 0/3 | 9 |
| 27 | [0, 7] | [3,11] | [0, 8] | [0,7] | [13, 7] | [12,10] | 0/3 | 9 |
| 28 | [0, 7] | [3,11] | [0, 8] | [0,7] | [13, 8] | [12,10] | 0/3 | 11 |
| 29 | [0, 7] | [3,11] | [0, 8] | [0,7] | [12, 8] | [12,10] | 0/3 | 11 |
| 30 | [1, 7] | [3,11] | [0, 8] | [0,7] | [12, 9] | [12,10] | 0/3 | 11 |
| 31 | [0, 7] | [3,11] | [0, 8] | [0,7] | [12, 10] | None | 0/3 | 11 |
| 32 | [1, 7] | [3,11] | [0, 8] | [0,7] | [12, 10] | None | 1/3 | 11 |
| 33 | [0, 7] | [3,11] | [0, 7] | None | [11, 10] | [2,12] | 1/3 | 11 |
| 34 | [0, 7] | [3,11] | [0, 7] | None | [11, 9] | [2,12] | 1/3 | 11 |
| 35 | [0, 7] | [3,11] | [1, 7] | [0,7] | [10, 9] | [2,12] | 1/3 | 15 |
| 36 | [0, 7] | [3,11] | [1, 8] | [0,7] | [9, 9] | [2,12] | 1/3 | 15 |
| 37 | [1, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 15 |
| 38 | [0, 7] | [3,11] | [0, 8] | [0,7] | [7, 9] | [2,12] | 1/3 | 15 |
| 39 | [1, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 15 |
| 40 | [0, 7] | [3,11] | [0, 8] | [0,7] | [7, 9] | [2,12] | 1/3 | 15 |
| 41 | [0, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 15 |
| 42 | [0, 7] | [3,11] | [0, 8] | [0,7] | [7, 9] | [2,12] | 1/3 | 19 |
| 43 | [0, 7] | [3,11] | [0, 7] | None | [8, 9] | [2,12] | 1/3 | 19 |
| 44 | [1, 7] | [3,11] | [0, 7] | None | [8, 10] | [2,12] | 1/3 | 19 |
| 45 | [0, 7] | [3,11] | [1, 7] | [0,7] | [8, 9] | [2,12] | 1/3 | 19 |
| 46 | [1, 7] | [3,11] | [1, 8] | [0,7] | [7, 9] | [2,12] | 1/3 | 19 |
| 47 | [0, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 19 |
| 48 | [0, 7] | [3,11] | [0, 8] | [0,7] | [7, 9] | [2,12] | 1/3 | 19 |
| 49 | [0, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 22 |
| 50 | [0, 7] | [3,11] | [0, 8] | [0,7] | [8, 8] | [2,12] | 1/3 | 22 |
| 51 | [1, 7] | [3,11] | [0, 8] | [0,7] | [8, 9] | [2,12] | 1/3 | 22 |
| 52 | [0, 7] | [3,11] | [0, 8] | [0,7] | [8, 8] | [2,12] | 1/3 | 22 |
| 53 | [1, 7] | [3,11] | [0, 7] | None | [8, 9] | [2,12] | 1/3 | 22 |
| 54 | [0, 7] | [3,11] | [0, 7] | None | [8, 8] | [2,12] | 1/3 | 22 |
| 55 | [0, 7] | [3,11] | [1, 7] | [0,7] | [8, 7] | [2,12] | 1/3 | 22 |
| 56 | [0, 7] | [3,11] | [1, 8] | [0,7] | [7, 7] | [2,12] | 1/3 | 27 |
| 57 | [0, 7] | [3,11] | [0, 8] | [0,7] | [7, 6] | [2,12] | 1/3 | 27 |
| 58 | [1, 7] | [3,11] | [0, 8] | [0,7] | [6, 6] | [2,12] | 1/3 | 27 |
| 59 | [0, 7] | [3,11] | [0, 8] | [0,7] | [5, 6] | [2,12] | 1/3 | 27 |
| 60 | [1, 7] | [3,11] | [0, 8] | [0,7] | [4, 6] | [2,12] | 1/3 | 27 |
| 61 | [0, 7] | None | [0, 8] | [0,7] | [3, 6] | [2,12] | 1/3 | 27 |
| 62 | [0, 7] | None | [0, 8] | [0,7] | [4, 6] | [2,12] | 1/3 | 27 |
| 63 | [0, 7] | None | [0, 7] | None | [3, 6] | [2,12] | 1/3 | 33 |
| 64 | [0, 7] | None | [0, 7] | None | [4, 6] | [2,12] | 1/3 | 33 |
| 65 | [1, 7] | [0,7] | [1, 7] | [0,7] | [3, 6] | [2,12] | 1/3 | 33 |
| 66 | [1, 8] | [0,7] | [1, 8] | [0,7] | [2, 6] | [2,12] | 1/3 | 33 |
| 67 | [0, 8] | [0,7] | [0, 8] | [0,7] | [2, 7] | [2,12] | 1/3 | 33 |
| 68 | [0, 8] | [0,7] | [0, 8] | [0,7] | [3, 7] | [2,12] | 1/3 | 33 |
| 69 | [0, 8] | [0,7] | [0, 8] | [0,7] | [2, 7] | [2,12] | 1/3 | 33 |
| 70 | [0, 8] | [0,7] | [0, 8] | [0,7] | [3, 7] | [2,12] | 1/3 | 37 |
| 71 | [0, 8] | [0,7] | [0, 8] | [0,7] | [2, 7] | [0,7] | 1/3 | 37 |
| 72 | [0, 8] | [0,7] | [0, 8] | [0,7] | [1, 7] | [0,7] | 1/3 | 37 |
| 73 | [0, 7] | None | [0, 7] | None | [0, 7] | None | 1/3 | 37 |
| 74 | [0, 7] | [11,11] | [0, 7] | [11,11] | [0, 7] | None | 1/3 | 37 |
| 75 | [1, 7] | [11,11] | [1, 7] | [11,11] | [1, 7] | [4,7] | 1/3 | 37 |
| 76 | [1, 8] | [11,11] | [1, 8] | [11,11] | [2, 7] | [4,7] | 1/3 | 37 |
| 77 | [2, 8] | [11,11] | [2, 8] | [11,11] | [3, 7] | [4,7] | 1/3 | 45 |
| 78 | [3, 8] | [11,11] | [3, 8] | [11,11] | [3, 7] | [4,7] | 1/3 | 45 |
| 79 | [4, 8] | [11,11] | [4, 8] | [11,11] | [4, 7] | None | 1/3 | 45 |
| 80 | [3, 8] | [11,11] | [3, 8] | [11,11] | [4, 8] | [7,10] | 1/3 | 45 |
| 81 | [4, 8] | [11,11] | [4, 8] | [11,11] | [3, 8] | [7,10] | 1/3 | 45 |
| 82 | [3, 8] | [11,11] | [3, 8] | [11,11] | [2, 8] | [7,10] | 1/3 | 45 |
| 83 | [4, 8] | [11,11] | [4, 8] | [11,11] | [2, 9] | [7,10] | 1/3 | 45 |
| 84 | [4, 7] | [11,11] | [3, 8] | [11,11] | [2, 10] | [7,10] | 1/3 | 51 |
| 85 | [4, 6] | [11,11] | [2, 8] | [11,11] | [3, 10] | [7,10] | 1/3 | 51 |
| 86 | [5, 6] | [11,11] | [2, 9] | [11,11] | [2, 10] | [7,10] | 1/3 | 51 |
| 87 | [6, 6] | [11,11] | [2, 10] | [11,11] | [3, 10] | [7,10] | 1/3 | 51 |
| 88 | [7, 6] | [11,11] | [3, 10] | [11,11] | [2, 10] | [7,10] | 1/3 | 51 |
| 89 | [8, 6] | [11,11] | [2, 10] | [11,11] | [3, 10] | [7,10] | 1/3 | 51 |
| 90 | [8, 5] | [11,11] | [2, 11] | [11,11] | [3, 11] | [7,10] | 1/3 | 51 |
| 91 | [8, 6] | [11,11] | [3, 11] | [11,11] | [4, 11] | [7,10] | 1/3 | 53 |
| 92 | [9, 6] | [11,11] | [3, 12] | [11,11] | [3, 11] | [7,10] | 1/3 | 53 |
| 93 | [10, 6] | [11,11] | [4, 12] | [11,11] | [4, 11] | [7,10] | 1/3 | 53 |
| 94 | [10, 7] | [11,11] | [4, 11] | [11,11] | [3, 11] | [7,10] | 1/3 | 53 |
| 95 | [11, 7] | [11,11] | [4, 12] | [11,11] | [4, 11] | [7,10] | 1/3 | 53 |
| 96 | [11, 8] | [11,11] | [4, 11] | [11,11] | [4, 12] | [7,10] | 1/3 | 53 |
| 97 | [11, 7] | [11,11] | [4, 12] | [11,11] | [3, 12] | [7,10] | 1/3 | 53 |
| 98 | [11, 8] | [11,11] | [3, 12] | [11,11] | [3, 11] | [7,10] | 1/3 | 59 |
| 99 | [12, 8] | [11,11] | [4, 12] | [11,11] | [4, 11] | [7,10] | 1/3 | 59 |
| 100 | [12, 9] | [11,11] | [4, 13] | [11,11] | [3, 11] | [7,10] | 1/3 | 59 |
| 101 | [12, 8] | [11,11] | [4, 14] | [11,11] | [4, 11] | [7,10] | 1/3 | 59 |
| 102 | [12, 9] | [11,11] | [5, 14] | [11,11] | [3, 11] | [7,10] | 1/3 | 59 |
| 103 | [13, 9] | [11,11] | [6, 14] | [11,11] | [4, 11] | [7,10] | 1/3 | 59 |
| 104 | [13, 8] | [11,11] | [7, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 59 |
| 105 | [13, 9] | [11,11] | [6, 14] | [11,11] | [3, 12] | [7,10] | 1/3 | 68 |
| 106 | [13, 8] | [11,11] | [7, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 68 |
| 107 | [13, 9] | [11,11] | [6, 14] | [11,11] | [3, 12] | [7,10] | 1/3 | 68 |
| 108 | [13, 8] | [11,11] | [7, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 68 |
| 109 | [13, 9] | [11,11] | [6, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 68 |
| 110 | [13, 10] | [11,11] | [7, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 68 |
| 111 | [13, 11] | [11,11] | [6, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 68 |
| 112 | [13, 10] | [11,11] | [5, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 81 |
| 113 | [13, 9] | [11,11] | [6, 14] | [11,11] | [3, 12] | [7,10] | 1/3 | 81 |
| 114 | [13, 8] | [11,11] | [7, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 81 |
| 115 | [13, 9] | [11,11] | [6, 14] | [11,11] | [3, 12] | [7,10] | 1/3 | 81 |
| 116 | [13, 10] | [11,11] | [5, 14] | [11,11] | [4, 12] | [7,10] | 1/3 | 81 |
| 117 | [13, 9] | [11,11] | [6, 14] | [11,11] | [3, 12] | [7,10] | 1/3 | 81 |
| 118 | [13, 10] | [11,11] | [5, 14] | [11,11] | [3, 13] | [7,10] | 1/3 | 81 |
| 119 | [13, 9] | [11,11] | [6, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 90 |
| 120 | [13, 8] | [11,11] | [5, 14] | [11,11] | [4, 14] | [7,10] | 1/3 | 90 |
| 121 | [13, 9] | [11,11] | [4, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 90 |
| 122 | [14, 9] | [11,11] | [4, 13] | [11,11] | [3, 13] | [7,10] | 1/3 | 90 |
| 123 | [13, 9] | [11,11] | [3, 13] | [11,11] | [4, 13] | [7,10] | 1/3 | 90 |
| 124 | [13, 8] | [11,11] | [4, 13] | [11,11] | [3, 13] | [7,10] | 1/3 | 90 |
| 125 | [13, 9] | [11,11] | [3, 13] | [11,11] | [4, 13] | [7,10] | 1/3 | 90 |
| 126 | [13, 10] | [11,11] | [4, 13] | [11,11] | [4, 14] | [7,10] | 1/3 | 97 |
| 127 | [13, 9] | [11,11] | [3, 13] | [11,11] | [4, 13] | [7,10] | 1/3 | 97 |
| 128 | [13, 10] | [11,11] | [3, 12] | [11,11] | [4, 14] | [7,10] | 1/3 | 97 |
| 129 | [13, 9] | [11,11] | [3, 13] | [11,11] | [4, 13] | [7,10] | 1/3 | 97 |
| 130 | [13, 10] | [11,11] | [4, 13] | [11,11] | [3, 13] | [7,10] | 1/3 | 97 |
| 131 | [13, 9] | [11,11] | [4, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 97 |
| 132 | [13, 8] | [11,11] | [4, 13] | [11,11] | [4, 14] | [7,10] | 1/3 | 97 |
| 133 | [13, 9] | [11,11] | [4, 14] | [11,11] | [4, 13] | [7,10] | 1/3 | 104 |
| 134 | [13, 8] | [14,7] | [4, 13] | [0,7] | [3, 13] | [7,10] | 1/3 | 104 |
| 135 | [14, 8] | [14,7] | [4, 14] | [0,7] | [4, 13] | [7,10] | 1/3 | 104 |
| 136 | [14, 7] | None | [3, 14] | [0,7] | [3, 13] | [7,10] | 1/3 | 104 |
| 137 | [14, 7] | [3,3] | [3, 13] | [0,7] | [4, 13] | [7,10] | 1/3 | 104 |
| 138 | [13, 7] | [3,3] | [3, 12] | [0,7] | [4, 14] | [7,10] | 1/3 | 104 |
| 139 | [12, 7] | [3,3] | [3, 11] | [0,7] | [4, 13] | [7,10] | 1/3 | 104 |
| 140 | [12, 6] | [3,3] | [2, 11] | [0,7] | [3, 13] | [2,13] | 1/3 | 110 |
| 141 | [11, 6] | [3,3] | [1, 11] | [0,7] | [3, 14] | [2,13] | 1/3 | 110 |
| 142 | [10, 6] | [3,3] | [1, 10] | [0,7] | [2, 14] | [0,7] | 1/3 | 110 |
| 143 | [11, 6] | [3,3] | [2, 10] | [0,7] | [1, 14] | [0,7] | 1/3 | 110 |
| 144 | [10, 6] | [3,3] | [1, 10] | [0,7] | [1, 13] | [0,7] | 1/3 | 110 |
| 145 | [11, 6] | [3,3] | [0, 10] | [0,7] | [1, 12] | [0,7] | 1/3 | 110 |
| 146 | [10, 6] | [3,3] | [0, 11] | [0,7] | [0, 12] | [0,7] | 1/3 | 110 |
| 147 | [11, 6] | [3,3] | [0, 10] | [0,7] | [0, 11] | [0,7] | 1/3 | 116 |
| 148 | [11, 5] | [3,3] | [1, 10] | [0,7] | [0, 10] | [0,7] | 1/3 | 116 |
| 149 | [10, 5] | [3,3] | [0, 10] | [0,7] | [0, 11] | [0,7] | 1/3 | 116 |
| 150 | [10, 4] | [3,3] | [0, 11] | [0,7] | [0, 10] | [0,7] | 1/3 | 116 |

## 5. Verification Assessment
1. **Fire Safety**: Dijkstra routing + safety layer ensures agents avoid fire cells.
2. **Debris Coordination**: Rover prioritises victim rescue over debris clearing.
3. **Battery Management**: Agents charge proactively at ≤35% battery.
4. **Curriculum Training**: Episodes 1–30 had no fires for stable exploration bootstrapping.
