import unittest

from simulator import calibration_lab


class CalibrationLabTests(unittest.TestCase):
    def test_calibration_suite(self):
        rows=calibration_lab.suite()
        checks=calibration_lab.checks(rows)
        failed=[name for name, ok in checks.items() if not ok]
        self.assertEqual(failed, [], failed)
        self.assertEqual(len(checks), 12)


if __name__=="__main__":
    unittest.main()
