#!/usr/bin/env python3
"""Query-driven equation planner/solver for RLC-family.

Natural-language interpretation stays in the LLM. This module receives a
compiled ProblemSpec, selects the relevant equation family, solves it
numerically/deterministically, and returns inspectable results.
"""

from __future__ import annotations

import argparse
import copy
import itertools
import json
import math
import sys
from pathlib import Path

try:
    from simulator import rlc_family_sim as core
    from simulator import person_network_solver as person_net
except ModuleNotFoundError:  # direct: python3 simulator/problem_solver.py ...
    import rlc_family_sim as core
    import person_network_solver as person_net

VERSION = "RLC-FAMILY-PROBLEM-0.2"

SAFE_HARMONIZE_DIRECTIONS = {
    "связь.качество_проводника": "up",
    "связь.фильтр_критического_мышления": "up",
    "связь.сброс_через_антенну": "up",
    "связь.согласование_собеседника": "up",
    "связь.усиление_эмоций": "down",
}


def _read_json(path):
    if str(path) == "-":
        text = sys.stdin.read()
    else:
        text = Path(path).read_text(encoding="utf-8")
    data = json.loads(text)
    if not isinstance(data, dict):
        raise core.ScenarioError("ProblemSpec must be an object")
    return data


def _get(obj, path):
    cur = obj
    for key in path.split("."):
        cur = cur[key]
    return cur


def _set(obj, path, value):
    cur = obj
    parts = path.split(".")
    for key in parts[:-1]:
        if key not in cur or not isinstance(cur[key], dict):
            cur[key] = {}
        cur = cur[key]
    cur[parts[-1]] = value


def operating_envelope(result):
    """Return transparent model-operating criteria and total violation.

    Lower violation is better. These are RLC-family conventions, not measured
    psychological thresholds.
    """
    rr = result["relationship"]
    fr = result["finance"]
    criteria = []

    def band(name, value, lo, hi, scale=None):
        scale = scale or max(hi - lo, 1e-9)
        if value < lo:
            violation = (lo - value) / scale
            status = "low"
        elif value > hi:
            violation = (value - hi) / scale
            status = "high"
        else:
            violation = 0.0
            status = "inside"
        criteria.append({
            "name": name, "value": value, "target": [lo, hi],
            "status": status, "violation": violation
        })

    def upper(name, value, hi, scale=None):
        scale = scale or max(abs(hi), 1.0)
        violation = max(0.0, (value - hi) / scale)
        criteria.append({
            "name": name, "value": value, "target": f"<= {hi}",
            "status": "inside" if violation == 0 else "high",
            "violation": violation
        })

    def lower(name, value, lo, scale=None):
        scale = scale or max(abs(lo), 1.0)
        violation = max(0.0, (lo - value) / scale)
        criteria.append({
            "name": name, "value": value, "target": f">= {lo}",
            "status": "inside" if violation == 0 else "low",
            "violation": violation
        })

    band("interaction_current", rr["current_rms"], 0.20, 0.65, 0.45)
    upper("absolute_phase_deg", abs(rr["phase_deg"]), 20.0, 40.0)
    band("damping_ratio", rr["damping_ratio"], 0.35, 1.20, 0.85)
    upper("memory_after", rr["memory_after"], 0.70, 0.30)

    # Finance criteria are included only when there is an actual monetary load.
    if fr["total_load_monthly"] > 0:
        lower("net_monthly", fr["net_monthly"], 0.0, max(fr["total_load_monthly"], 1.0))
        runway = fr["runway_if_income_lost_months"]
        if math.isfinite(runway):
            lower("runway_months", runway, 3.0, 3.0)

    violation = sum(x["violation"] for x in criteria)
    passed = sum(1 for x in criteria if x["violation"] == 0)
    return {
        "criteria": criteria,
        "violation": violation,
        "criteria_passed": passed,
        "criteria_total": len(criteria),
    }


def _run(scenario):
    ir, result = core.simulate(scenario)
    return ir, result, operating_envelope(result)


def _baseline_summary(result, envelope):
    return {
        "relationship": result["relationship"],
        "finance": result["finance"],
        "warnings": result["warnings"],
        "operating_envelope": envelope,
    }


def solve_finance(scenario, problem):
    _, result, envelope = _run(scenario)
    f = result["finance"]
    target = problem.get("target", "break_even_income")

    equations = []
    if target == "break_even_income":
        # explicit_income + photo_income - total_load = 0
        value = max(0.0, f["total_load_monthly"] - f["photo_income_monthly"])
        equations.append("explicit_income + photo_income - total_load = 0")
        label = "required_explicit_income_monthly"
    elif target == "max_mortgage":
        # income + photo - mortgage - base - other = 0
        current_mortgage = scenario.get("финансы", {}).get("ипотека_в_месяц", 0)
        nonmort = f["total_load_monthly"] - float(current_mortgage)
        value = max(0.0, f["total_income_monthly"] - nonmort)
        equations.append("total_income - mortgage - nonmortgage_load = 0")
        label = "maximum_break_even_mortgage_monthly"
    elif target == "required_reserve_for_runway":
        months = float(problem.get("months", 6))
        if months < 0:
            raise core.ScenarioError("months must be >= 0")
        value = f["total_load_monthly"] * months
        equations.append("reserve_required = total_load * target_runway_months")
        label = "required_reserve"
    else:
        raise core.ScenarioError(f"unknown finance target: {target}")

    return {
        "solver_version": VERSION,
        "problem_type": "solve_finance",
        "equations": equations,
        "baseline": _baseline_summary(result, envelope),
        "solution": {label: value},
    }


def solve_resonance(scenario, problem):
    _, result, envelope = _run(scenario)
    rr = result["relationship"]
    omega0 = rr["resonance_omega"]
    return {
        "solver_version": VERSION,
        "problem_type": "solve_resonance",
        "equations": [
            "X(omega) = omega*L - 1/(omega*C)",
            "X(omega0) = 0",
            "omega0 = 1/sqrt(L*C)",
        ],
        "baseline": _baseline_summary(result, envelope),
        "solution": {
            "omega0_rad_s": omega0,
            "frequency_hz_equivalent": omega0 / (2 * math.pi),
        },
    }


def solve_what_if(scenario, problem):
    changes = problem.get("changes")
    if not isinstance(changes, dict) or not changes:
        raise core.ScenarioError("what_if requires non-empty changes object")

    _, base_result, base_env = _run(scenario)
    candidate = copy.deepcopy(scenario)
    for path, value in changes.items():
        _set(candidate, path, value)
    ir, result, env = _run(candidate)

    return {
        "solver_version": VERSION,
        "problem_type": "what_if",
        "equations": [
            "candidate = solve(compile(scenario + requested_changes))",
            "delta = candidate - baseline",
        ],
        "changes": changes,
        "baseline": _baseline_summary(base_result, base_env),
        "solution": {
            "analog_ir": ir,
            "result": result,
            "operating_envelope": env,
            "violation_delta": env["violation"] - base_env["violation"],
        },
    }


def _default_actions(scenario):
    """Safe, system-level actions only; no money amounts are invented."""
    actions = []
    defaults = [
        ("связь.качество_проводника", +0.10),
        ("связь.качество_проводника", +0.20),
        ("связь.фильтр_критического_мышления", +0.10),
        ("связь.фильтр_критического_мышления", +0.20),
        ("связь.сброс_через_антенну", +0.10),
        ("связь.сброс_через_антенну", +0.20),
        ("связь.согласование_собеседника", +0.10),
        ("связь.согласование_собеседника", +0.20),
        ("связь.усиление_эмоций", -0.10),
        ("связь.усиление_эмоций", -0.20),
    ]
    for path, delta in defaults:
        try:
            current = float(_get(scenario, path))
        except (KeyError, TypeError, ValueError):
            continue
        if path == "связь.усиление_эмоций":
            value = max(0.0, current + delta)
        else:
            value = max(0.0, min(1.0, current + delta))
        if value != current:
            actions.append({"path": path, "value": value, "cost": abs(delta)})
    return actions


def _actions_from_problem(scenario, problem):
    raw = problem.get("actions")
    if raw is None:
        return _default_actions(scenario)
    if not isinstance(raw, list):
        raise core.ScenarioError("actions must be a list")
    actions = []
    for item in raw:
        if not isinstance(item, dict) or "path" not in item:
            raise core.ScenarioError("each action requires path")
        path = str(item["path"])
        if "values" in item:
            values = item["values"]
        elif "value" in item:
            values = [item["value"]]
        else:
            raise core.ScenarioError("each action requires value or values")
        if path not in SAFE_HARMONIZE_DIRECTIONS:
            raise core.ScenarioError(
                f"harmonize action not in safe actionable set: {path}"
            )
        try:
            baseline = float(_get(scenario, path))
        except (KeyError, TypeError, ValueError) as e:
            raise core.ScenarioError(
                f"harmonize action path is not available: {path}"
            ) from e
        direction = SAFE_HARMONIZE_DIRECTIONS[path]
        for value in values:
            value = float(value)
            if direction == "up" and value < baseline:
                raise core.ScenarioError(
                    f"harmonize refuses destabilizing direction for {path}"
                )
            if direction == "down" and value > baseline:
                raise core.ScenarioError(
                    f"harmonize refuses destabilizing direction for {path}"
                )
            actions.append({
                "path": path,
                "value": value,
                "cost": float(item.get("cost", 1.0)),
            })
    return actions


def harmonize(scenario, problem):
    _, base_result, base_env = _run(scenario)
    actions = _actions_from_problem(scenario, problem)
    max_changes = int(problem.get("max_changes", 2))
    max_results = int(problem.get("max_results", 5))
    if max_changes < 1 or max_changes > 3:
        raise core.ScenarioError("max_changes must be 1..3")

    candidates = []
    # Avoid contradictory combinations that set the same path twice.
    for n in range(1, max_changes + 1):
        for combo in itertools.combinations(actions, n):
            paths = [a["path"] for a in combo]
            if len(set(paths)) != len(paths):
                continue
            candidate = copy.deepcopy(scenario)
            for action in combo:
                _set(candidate, action["path"], action["value"])
            try:
                _, result, env = _run(candidate)
            except (core.ScenarioError, ZeroDivisionError, OverflowError):
                continue
            improvement = base_env["violation"] - env["violation"]
            total_cost = sum(max(float(a.get("cost", 1.0)), 1e-9) for a in combo)
            efficiency = improvement / total_cost
            candidates.append({
                "changes": {a["path"]: a["value"] for a in combo},
                "cost": total_cost,
                "violation_before": base_env["violation"],
                "violation_after": env["violation"],
                "improvement": improvement,
                "improvement_per_cost": efficiency,
                "operating_envelope": env,
                "warnings": result["warnings"],
                "family_interpretation": result["family_interpretation"],
            })

    candidates.sort(
        key=lambda x: (-x["improvement"], -x["improvement_per_cost"], x["cost"])
    )
    useful = [x for x in candidates if x["improvement"] > 1e-12][:max_results]

    return {
        "solver_version": VERSION,
        "problem_type": "harmonize",
        "equations": [
            "minimize V(x) = sum(normalized operating-envelope violations)",
            "subject to x in requested safe/actionable parameter set",
            "candidate_result = solve(compile(scenario + delta_x))",
            "improvement = V(baseline) - V(candidate)",
        ],
        "objective_note": (
            "V is an internal RLC-family engineering score, not a psychological "
            "measurement or clinical family rating."
        ),
        "baseline": _baseline_summary(base_result, base_env),
        "solution": {
            "best_interventions": useful,
            "tested_candidates": len(candidates),
        },
    }


def solve_problem(scenario, problem):
    ptype = problem.get("type", "diagnose")
    if ptype == "person_network":
        return person_net.solve_network(scenario)
    if ptype == "diagnose":
        ir, result, env = _run(scenario)
        return {
            "solver_version": VERSION,
            "problem_type": "diagnose",
            "equations": [
                "Z = R + j*(omega*L - 1/(omega*C))",
                "I = V/|Z|",
                "omega0 = 1/sqrt(L*C)",
                "financial_net = income - load",
            ],
            "solution": {
                "analog_ir": ir,
                "result": result,
                "operating_envelope": env,
            },
        }
    if ptype == "solve_finance":
        return solve_finance(scenario, problem)
    if ptype == "solve_resonance":
        return solve_resonance(scenario, problem)
    if ptype == "what_if":
        return solve_what_if(scenario, problem)
    if ptype == "harmonize":
        return harmonize(scenario, problem)
    raise core.ScenarioError(f"unknown problem type: {ptype}")


def main():
    p = argparse.ArgumentParser(description="RLC-family query-driven equation solver")
    p.add_argument("scenario", help="FamilyScenario JSON")
    p.add_argument("problem", help="ProblemSpec JSON, or '-' for stdin")
    p.add_argument("--out", type=Path)
    args = p.parse_args()

    scenario = core.load(args.scenario)
    problem = _read_json(args.problem)
    answer = solve_problem(scenario, problem)
    text = json.dumps(answer, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    print(text, end="")


if __name__ == "__main__":
    main()
