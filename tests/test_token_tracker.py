import unittest
from core.analytics.token_tracker import TokenTracker
from core.models.model import Model

class TestTokenTrackerSerialization(unittest.TestCase):

    def test_serialization_deserialization(self):
        original_tracker = TokenTracker(total_prompt=100, total_candidates=50, model=Model.gemini_2_5_flash)
        
        # Test to_dict
        tracker_dict = original_tracker.to_dict()
        self.assertIsInstance(tracker_dict, dict)
        self.assertEqual(tracker_dict['total_prompt'], 100)
        self.assertEqual(tracker_dict['total_candidates'], 50)
        self.assertEqual(tracker_dict['model'], Model.gemini_2_5_flash.value)

        # Test from_dict
        reconstructed_tracker = TokenTracker.from_dict(tracker_dict)
        self.assertIsInstance(reconstructed_tracker, TokenTracker)
        self.assertEqual(reconstructed_tracker.total_prompt, original_tracker.total_prompt)
        self.assertEqual(reconstructed_tracker.total_candidates, original_tracker.total_candidates)
        self.assertEqual(reconstructed_tracker.model, original_tracker.model)
        
        # Ensure it's a new instance
        self.assertIsNot(original_tracker, reconstructed_tracker)

if __name__ == '__main__':
    unittest.main()
