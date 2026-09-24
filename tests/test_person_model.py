import unittest

from simulator import person_calibration
from simulator import person_model as pm


class PersonModelTests(unittest.TestCase):
    def test_person_calibration(self):
        rows=person_calibration.suite()
        checks=person_calibration.checks(rows)
        failed=[name for name, ok in checks.items() if not ok]
        self.assertEqual(failed, [], failed)
        self.assertEqual(len(checks), 10)

    def test_duplicate_person_ids_rejected(self):
        scenario={
            "персонажи":[
                {"id":"x","type":"adult","gender":"male"},
                {"id":"x","type":"adult","gender":"female"},
            ]
        }
        with self.assertRaises(Exception):
            pm.compile_person_network(scenario)

    def test_default_network_is_complete(self):
        scenario={
            "персонажи":[
                {"id":"a","type":"adult","gender":"male"},
                {"id":"b","type":"adult","gender":"female"},
                {"id":"c","type":"child","gender":"male","age":10},
            ]
        }
        ir=pm.compile_person_network(scenario)
        self.assertEqual(len(ir["nodes"]),3)
        self.assertEqual(len(ir["links"]),3)


if __name__=="__main__":
    unittest.main()
