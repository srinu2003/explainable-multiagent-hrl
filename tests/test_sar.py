import unittest
import torch
import numpy as np
import sys
import os

# Set paths
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from environment import SearchRescueEnv
from high_level_agent import HighLevelAgent
from low_level_agent import LowLevelAgent
from explain import ExplainabilityEngine

class TestSearchRescueFramework(unittest.TestCase):
    def setUp(self):
        self.env = SearchRescueEnv(grid_size=15, num_victims=2, num_debris=3, num_fires=1)
        self.hl_agent = HighLevelAgent()
        self.ll_agent = LowLevelAgent()
        self.xai = ExplainabilityEngine()
        
    def test_env_init(self):
        obs = self.env.get_observations()
        self.assertEqual(len(self.env.agents), 3)
        self.assertEqual(len(self.env.victims), 2)
        self.assertEqual(len(self.env.debris_locations), 3)
        self.assertEqual(len(self.env.fire_locations), 1)
        self.assertEqual(self.env.grid_size, 15)
        
        # Check starting coordinates
        self.assertEqual(self.env.agents["A1"]["pos"], [0, 0])
        self.assertEqual(self.env.agents["A2"]["pos"], [0, 14])
        self.assertEqual(self.env.agents["A3"]["pos"], [14, 7])
        
    def test_env_step_movement(self):
        # Reset env
        self.env.reset()
        
        # Test Drone A1 moving South (action 1)
        actions = {"A1": 1, "A2": 4, "A3": 4} # Drone moves South, others interact
        obs, rewards, done, info = self.env.step(actions)
        
        # Check new coordinates
        self.assertEqual(self.env.agents["A1"]["pos"], [1, 0])
        # Check battery depletion
        self.assertEqual(self.env.agents["A1"]["battery"], 99)
        self.assertEqual(self.env.agents["A2"]["battery"], 99) # Interact costs 1 battery
        
    def test_hl_agent_goal_translation(self):
        obs = self.env.get_observations()
        
        # Test quadrant goal translations
        coords_nw, _ = self.hl_agent.translate_action_to_goal("A1", 0, obs["A1"])
        self.assertEqual(coords_nw, [3, 3])
        
        coords_se, _ = self.hl_agent.translate_action_to_goal("A1", 3, obs["A1"])
        self.assertEqual(coords_se, [11, 11])
        
        # Test charge pad target
        coords_charge, _ = self.hl_agent.translate_action_to_goal("A1", 4, obs["A1"])
        # Charging pads are located at (0, 7) and (14, 7)
        self.assertTrue(coords_charge in [[0, 7], [14, 7]])
        
    def test_ll_agent_state_features(self):
        obs = self.env.get_observations()
        pos = self.env.agents["A1"]["pos"]
        sub_goal = [3, 3]
        
        state_vec = self.ll_agent.get_state_vector("A1", pos, sub_goal, obs["A1"], grid_size=15)
        
        # State vector should be a torch.Tensor of shape (12,)
        self.assertIsInstance(state_vec, torch.Tensor)
        self.assertEqual(state_vec.shape, (12,))
        
        # Check normalized vector components dx and dy
        self.assertAlmostEqual(state_vec[0].item(), 3.0 / 15.0)
        self.assertAlmostEqual(state_vec[1].item(), 3.0 / 15.0)
        
        # Check battery component
        self.assertAlmostEqual(state_vec[2].item(), 1.0) # Battery is 100%
        
    def test_explain_saliency(self):
        self.env.reset()
        obs = self.env.get_observations()
        
        sal = self.xai.compute_saliency("A1", [0, 0], [3, 3], obs["A1"], self.ll_agent)
        
        self.assertIn("target_proximity", sal)
        self.assertIn("battery_status", sal)
        self.assertIn("hazard_avoidance", sal)
        
        # Check if values sum to 100%
        total = sal["target_proximity"] + sal["battery_status"] + sal["hazard_avoidance"]
        self.assertAlmostEqual(total, 100.0, places=1)

if __name__ == '__main__':
    unittest.main()
