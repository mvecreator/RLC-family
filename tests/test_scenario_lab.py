import unittest

from simulator import scenario_lab


class ScenarioLabTests(unittest.TestCase):
    def test_directional_sanity_suite(self):
        rows = scenario_lab.suite()
        checks = scenario_lab.checks(rows)
        failed = [name for name, ok in checks.items() if not ok]
        self.assertEqual(failed, [], failed)


if __name__ == "__main__":
    unittest.main()
