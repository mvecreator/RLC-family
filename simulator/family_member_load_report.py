#!/usr/bin/env python3
"""Per-member PERSON-LOAD1 report for a PERSON2 family timeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from simulator import person_family_safety as family_safety
from simulator import rlc_family_sim as core


def load_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise core.ScenarioError(str(e)) from e
    if not isinstance(value, dict):
        raise core.ScenarioError(f"{path}: root must be object")
    return value


def member_report(scenario, timeline):
    result = family_safety.assess(scenario, timeline)
    members = []
    for pid, item in result["summary"]["persons"].items():
        members.append({
            "id": pid,
            "kind": item.get("kind"),
            "age": item.get("age"),
            "band": item["band"],
            "peak_load": item["peak_load"],
            "final_load": item["final_load"],
            "first_recovery_attention_day": item[
                "first_recovery_attention_day"
            ],
            "first_sustained_load_review_day": item[
                "first_sustained_load_review_day"
            ],
            "first_high_load_review_day": item[
                "first_high_load_review_day"
            ],
            "dominant_mean_component": item[
                "dominant_mean_component"
            ],
            "mean_components": item["mean_components"],
            "peak_components": item["peak_components"],
            "recommendations": item["recommendations"],
        })
    members.sort(key=lambda x: (-x["peak_load"]["value"], x["id"]))
    return {
        "scenario_name": result["scenario_name"],
        "highest_load_person": result["summary"]["highest_load_person"],
        "members": members,
        "note": (
            "PERSON-LOAD1 bands are project engineering guardrails, not "
            "medical or psychological diagnoses."
        ),
    }


def render_text(result):
    lines = [
        "# Family member load report",
        "",
        f"Scenario: {result['scenario_name']}",
        f"Highest-load person: {result['highest_load_person']}",
        "",
    ]
    for item in result["members"]:
        lines += [
            f"## {item['id']}",
            "",
            f"- kind: {item['kind']}",
            f"- age: {item['age']}",
            f"- band: {item['band']}",
            f"- peak load: {item['peak_load']['value']:.4f} at day {item['peak_load']['day']:.2f}",
            f"- final load: {item['final_load']:.4f}",
            f"- dominant mean component: {item['dominant_mean_component']}",
            f"- recovery attention day: {item['first_recovery_attention_day']}",
            f"- sustained review day: {item['first_sustained_load_review_day']}",
            f"- high review day: {item['first_high_load_review_day']}",
            "",
            "Recommendations:",
        ]
        if item["recommendations"]:
            lines.extend(
                f"- {x['action']}: {x['message']}"
                for x in item["recommendations"]
            )
        else:
            lines.append("- none")
        lines.append("")
    lines += [
        "## Boundary",
        "",
        result["note"],
        "",
    ]
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser(
        description="Render calibrated load for every PERSON2 family member"
    )
    p.add_argument("scenario")
    p.add_argument("timeline")
    p.add_argument("--out", type=Path)
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    result = member_report(
        load_json(args.scenario),
        load_json(args.timeline),
    )

    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "family_member_loads.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (args.out / "family_member_loads.md").write_text(
            render_text(result),
            encoding="utf-8",
        )

    print(
        json.dumps(result, ensure_ascii=False, indent=2)
        if args.json
        else render_text(result)
    )


if __name__ == "__main__":
    main()
