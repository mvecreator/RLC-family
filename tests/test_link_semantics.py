import math
import unittest

from simulator import person_family_safety as family_safety
from simulator import person_model as pm


def two_adults(link):
    return {
        "person_model": {"gender_prior_strength": 0},
        "персонажи": [
            {"id": "a", "type": "adult", "gender": "male"},
            {"id": "b", "type": "adult", "gender": "female"},
        ],
        "связи_персонажей": [dict({"from": "a", "to": "b"}, **link)],
    }


def safety_sample(link):
    return {
        "financial_stress": 0.0,
        "active_events": [],
        "nodes": [
            {"id": "a", "voltage": 0.10, "memory": 0.10},
            {"id": "b", "voltage": -0.10, "memory": 0.10},
        ],
        "links": [dict({
            "from": "a",
            "to": "b",
            "current_abs": 0.15,
        }, **link)],
    }


class LinkSemanticsTests(unittest.TestCase):
    def test_legacy_quality_preserves_transport_exactly(self):
        ir = pm.compile_person_network(two_adults({"quality": 0.20}))
        link = ir["links"][0]
        self.assertEqual(link["semantic_source"], "legacy-quality")
        self.assertAlmostEqual(link["communication_quality"], 0.20, places=12)
        self.assertAlmostEqual(link["contact_frequency"], 1.0, places=12)
        self.assertAlmostEqual(link["availability"], 1.0, places=12)
        self.assertAlmostEqual(link["hostility"], 0.80, places=12)
        self.assertAlmostEqual(link["effective_transmission"], 0.20, places=12)
        self.assertAlmostEqual(link["quality"], 0.20, places=12)
        self.assertAlmostEqual(
            link["R_link"],
            pm.link_resistance(0.20),
            places=12,
        )

    def test_explicit_semantics_separate_contact_from_quality(self):
        ir = pm.compile_person_network(two_adults({
            "communication_quality": 0.95,
            "contact_frequency": 0.10,
            "availability": 0.80,
            "hostility": 0.02,
        }))
        link = ir["links"][0]
        expected = 0.95 * math.sqrt(0.10 * 0.80)
        self.assertEqual(link["semantic_source"], "LINK-SEM1")
        self.assertAlmostEqual(
            link["effective_transmission"], expected, places=12
        )
        self.assertAlmostEqual(
            link["R_link"], pm.link_resistance(expected), places=12
        )
        self.assertAlmostEqual(link["communication_quality"], 0.95, places=12)
        self.assertAlmostEqual(link["hostility"], 0.02, places=12)

    def test_rare_but_good_contact_is_not_high_strain(self):
        link = {
            "quality": 0.95 * math.sqrt(0.10 * 0.80),
            "effective_transmission": 0.95 * math.sqrt(0.10 * 0.80),
            "communication_quality": 0.95,
            "contact_frequency": 0.10,
            "availability": 0.80,
            "hostility": 0.02,
        }
        out = family_safety.instantaneous_components(
            safety_sample(link)
        )["links"]["a->b"]
        self.assertLess(out["relational_friction"], 0.05)
        self.assertLess(out["combined"], 0.22)

    def test_hostility_matters_even_when_contact_is_available(self):
        good = {
            "quality": 0.95,
            "effective_transmission": 0.95,
            "communication_quality": 0.95,
            "contact_frequency": 1.0,
            "availability": 1.0,
            "hostility": 0.02,
        }
        hostile = dict(good)
        hostile["hostility"] = 0.90

        a = family_safety.instantaneous_components(
            safety_sample(good)
        )["links"]["a->b"]
        b = family_safety.instantaneous_components(
            safety_sample(hostile)
        )["links"]["a->b"]

        self.assertGreater(b["relational_friction"], a["relational_friction"] + 0.25)
        self.assertGreater(b["combined"], a["combined"] + 0.10)

    def test_low_availability_reduces_transport_not_relational_friction(self):
        base = pm.compile_link_semantics({
            "communication_quality": 0.90,
            "contact_frequency": 1.0,
            "availability": 1.0,
            "hostility": 0.05,
        }, 0.70, "test", "explicit")
        low = pm.compile_link_semantics({
            "communication_quality": 0.90,
            "contact_frequency": 1.0,
            "availability": 0.10,
            "hostility": 0.05,
        }, 0.70, "test", "explicit")

        self.assertLess(low["effective_transmission"], base["effective_transmission"])
        self.assertGreater(low["R_link"], base["R_link"])

        a = family_safety.instantaneous_components(
            safety_sample(base)
        )["links"]["a->b"]
        b = family_safety.instantaneous_components(
            safety_sample(low)
        )["links"]["a->b"]
        self.assertAlmostEqual(
            a["relational_friction"],
            b["relational_friction"],
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
