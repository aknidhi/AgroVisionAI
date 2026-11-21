import unittest
from core.district_service import get_districts, find_nearest_reporting_district

class DistrictCoverageTests(unittest.TestCase):
    def test_bihar_contains_38_districts(self):
        self.assertEqual(len(get_districts("Bihar")), 38)

    def test_nearest_district_is_same_state(self):
        result = find_nearest_reporting_district(
            "Bihar", "Sheikhpura", ["Nalanda", "Patna"], max_distance_km=300
        )
        self.assertIsNotNone(result)
        self.assertIn(result["district"], {"Nalanda", "Patna"})

if __name__ == "__main__":
    unittest.main()
