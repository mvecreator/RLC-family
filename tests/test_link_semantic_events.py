import unittest

from simulator import person_model as pm
from simulator import person_time_solver as pts
from simulator import rlc_family_sim as core


def scenario():
    return {
        "person_model": {"gender_prior_strength": 0},
        "персонажи": [
            {"id": "a", "type": "adult", "gender": "male"},
            {"id": "b", "type": "adult", "gender": "female"},
        ],
        "связи_персонажей": [{
            "from": "a",
            "to": "b",
            "communication_quality": 0.90,
            "contact_frequency": 1.0,
            "availability": 1.0,
            "hostility": 0.05,
        }],
    }


class LinkSemanticEventTests(unittest.TestCase):
    def test_availability_event_changes_transport_only(self):
        s = scenario()
        ir = pm.compile_person_network(s)
        before = ir["links"][0]
        events = pts._compile_events({
            "события": [{
                "id": "travel",
                "день": 0,
                "длительность_дней": 1,
                "связь": ["a", "b"],
                "availability_set": 0.10,
            }]
        }, {"a", "b"}, {("a", "b")})
        _, links, _ = pts._network_at(s, ir, events, 0.5)
        after = links[0]

        self.assertAlmostEqual(after["availability"], 0.10, places=12)
        self.assertAlmostEqual(
            after["communication_quality"], before["communication_quality"],
            places=12,
        )
        self.assertAlmostEqual(
            after["hostility"], before["hostility"], places=12,
        )
        self.assertLess(
            after["effective_transmission"],
            before["effective_transmission"],
        )

    def test_hostility_event_does_not_change_transport(self):
        s = scenario()
        ir = pm.compile_person_network(s)
        before = ir["links"][0]
        events = pts._compile_events({
            "события": [{
                "id": "argument-tone",
                "день": 0,
                "длительность_дней": 1,
                "связь": ["a", "b"],
                "hostility_set": 0.90,
            }]
        }, {"a", "b"}, {("a", "b")})
        _, links, _ = pts._network_at(s, ir, events, 0.5)
        after = links[0]

        self.assertAlmostEqual(after["hostility"], 0.90, places=12)
        self.assertAlmostEqual(
            after["effective_transmission"],
            before["effective_transmission"],
            places=12,
        )

    def test_semantic_mutation_without_target_link_rejected(self):
        with self.assertRaises(core.ScenarioError):
            pts._compile_events({
                "события": [{
                    "id": "bad",
                    "hostility_set": 0.90,
                }]
            }, {"a", "b"}, {("a", "b")})


if __name__ == "__main__":
    unittest.main()
