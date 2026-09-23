import json, math, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from simulator import rlc_family_sim as sim
from simulator import problem_solver as ps


class RLCFamilySimulatorTests(unittest.TestCase):
    def setUp(self):
        self.scenario = json.loads((ROOT/"examples"/"family_scenario.json").read_text(encoding="utf-8"))

    def test_compile_components(self):
        ir = sim.compile_scenario(self.scenario)
        ids = {c["id"] for c in ir["components"]}
        self.assertTrue({"R_CHILD","R_CHANNEL","R_RAD","L_WOMAN","C_MAN","MEM","NL_TEEN"} <= ids)

    def test_parallel_children_lower_resistance(self):
        a=json.loads(json.dumps(self.scenario)); b=json.loads(json.dumps(self.scenario))
        a["отношения"]["топология_детей"]="последовательно"
        b["отношения"]["топология_детей"]="параллельно"
        ia,ib=sim.compile_scenario(a),sim.compile_scenario(b)
        self.assertLess(sim.cv(ib,"R_CHILD"),sim.cv(ia,"R_CHILD"))

    def test_filter_reduces_external_drive(self):
        a=json.loads(json.dumps(self.scenario)); b=json.loads(json.dumps(self.scenario))
        a["связь"]["фильтр_критического_мышления"]=0
        b["связь"]["фильтр_критического_мышления"]=1
        self.assertLess(sim.compile_scenario(b)["analysis"]["external_voltage"],
                        sim.compile_scenario(a)["analysis"]["external_voltage"])

    def test_deterministic_and_finite(self):
        _,r1=sim.simulate(self.scenario); _,r2=sim.simulate(self.scenario)
        self.assertEqual(r1,r2)
        self.assertTrue(math.isfinite(r1["relationship"]["current_rms"]))

    def test_mortgage_decreases(self):
        _,r=sim.simulate(self.scenario)
        self.assertLess(r["finance"]["mortgage_debt_end"],r["finance"]["mortgage_debt_start"])

    def test_deficit_warning(self):
        s=json.loads(json.dumps(self.scenario))
        s["финансы"]["доходы_в_месяц"]=[100]
        s["финансы"]["доступный_рынок_в_месяц"]=0
        _,r=sim.simulate(s)
        self.assertIn("FINANCIAL_DEFICIT",r["warnings"])

    def test_outputs(self):
        ir,r=sim.simulate(self.scenario)
        with tempfile.TemporaryDirectory() as td:
            sim.write_outputs(td,ir,r)
            for name in ("analog_ir.json","result.json","circuit.net","report.md"):
                self.assertTrue((Path(td)/name).exists())

    def test_load_text_for_chat(self):
        raw = json.dumps(self.scenario, ensure_ascii=False)
        loaded = sim.load_text(raw)
        self.assertEqual(loaded["название"], self.scenario["название"])

    def test_problem_solver_resonance(self):
        ans = ps.solve_problem(self.scenario, {"type": "solve_resonance"})
        self.assertGreater(ans["solution"]["omega0_rad_s"], 0)

    def test_problem_solver_break_even(self):
        ans = ps.solve_problem(
            self.scenario,
            {"type": "solve_finance", "target": "break_even_income"},
        )
        required = ans["solution"]["required_explicit_income_monthly"]
        self.assertGreaterEqual(required, 0)

    def test_problem_solver_what_if(self):
        ans = ps.solve_problem(
            self.scenario,
            {
                "type": "what_if",
                "changes": {"связь.качество_проводника": 0.90},
            },
        )
        self.assertIn("violation_delta", ans["solution"])

    def test_problem_solver_harmonize_never_returns_negative_improvement(self):
        ans = ps.solve_problem(
            self.scenario,
            {"type": "harmonize", "max_changes": 2, "max_results": 5},
        )
        for item in ans["solution"]["best_interventions"]:
            self.assertGreater(item["improvement"], 0)

    def test_invalid_probability(self):
        s=json.loads(json.dumps(self.scenario))
        s["связь"]["внешний_фон"]=1.5
        with self.assertRaises(sim.ScenarioError): sim.compile_scenario(s)


if __name__=="__main__":
    unittest.main()
