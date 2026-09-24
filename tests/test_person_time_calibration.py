import unittest

from simulator import person_time_calibration


class PersonTimeCalibrationTests(unittest.TestCase):
    def test_person_time_calibration(self):
        rows = person_time_calibration.suite()
        checks = person_time_calibration.checks(rows)
        failed = [name for name, ok in checks.items() if not ok]
        self.assertEqual(failed, [], failed)
        self.assertEqual(len(checks), 8)


if __name__ == "__main__":
    unittest.main()
