#!/usr/bin/env python3
"""OUTCOME-BENCH1: first deterministic blind benchmark corpus.

The benchmark separates continuation regimes from hidden regime shifts and
scores three predictors:
- current RLC accumulator projection;
- persistence baseline;
- recent linear-trend baseline.

It is a benchmark of the current equations, not evidence about real families.
"""

from __future__ import annotations

import json

from simulator import outcome_blind as blind


CUTOFF_DAY = 7
HORIZON_DAYS = 5
LOOKBACK_DAYS = 3
TOTAL_INTERVALS = 13


def _series_constant(value, n=TOTAL_INTERVALS):
    return [float(value)] * n


def _simulate_single(loads, initial_state, accumulation, recovery):
    state = float(initial_state)
    rows = []
    for day, load in enumerate(loads):
        rows.append((float(day), state, float(load)))
        state = blind.project_accumulator(
            state, load, 1.0, accumulation, recovery
        )
    rows.append((float(len(loads)), state, float(loads[-1])))
    return rows


def _merge_person_link(person_rows, link_rows):
    out = []
    for p, l in zip(person_rows, link_rows):
        day = p[0]
        if abs(day - l[0]) > 1e-12:
            raise ValueError("person/link benchmark days differ")
        out.append({
            "day": day,
            "persons": {
                "p": {
                    "accumulated_load": p[1],
                    "combined": p[2],
                }
            },
            "links": {
                "p->q": {
                    "accumulated_strain": l[1],
                    "combined": l[2],
                }
            },
        })
    return out


def single_entity_cases():
    cases = []

    for load in (0.05, 0.10, 0.20, 0.35, 0.50, 0.70):
        for initial in (0.15, 0.35, 0.60, 0.80):
            loads = _series_constant(load)
            cases.append({
                "regime": "constant",
                "name": f"constant_L{load:.2f}_s{initial:.2f}",
                "loads": loads,
                "initial": initial,
            })

    for start, end in (
        (0.05, 0.70),
        (0.70, 0.05),
        (0.10, 0.50),
        (0.50, 0.10),
    ):
        loads = [
            start + (end - start) * i / (TOTAL_INTERVALS - 1)
            for i in range(TOTAL_INTERVALS)
        ]
        cases.append({
            "regime": "ramp_continuation",
            "name": f"ramp_{start:.2f}_{end:.2f}",
            "loads": loads,
            "initial": 0.30,
        })

    for prefix, hidden_future in (
        (0.65, 0.02),
        (0.05, 0.75),
        (0.50, 0.05),
        (0.10, 0.60),
    ):
        loads = (
            [prefix] * (CUTOFF_DAY + 1)
            + [hidden_future] * (
                TOTAL_INTERVALS - CUTOFF_DAY - 1
            )
        )
        cases.append({
            "regime": "hidden_shift",
            "name": f"hidden_{prefix:.2f}_{hidden_future:.2f}",
            "loads": loads,
            "initial": 0.30,
        })

    for start, at_cutoff, hidden_future in (
        (0.10, 0.60, 0.05),
        (0.60, 0.10, 0.70),
    ):
        prefix = [
            start + (at_cutoff - start) * i / CUTOFF_DAY
            for i in range(CUTOFF_DAY + 1)
        ]
        loads = prefix + [hidden_future] * (
            TOTAL_INTERVALS - CUTOFF_DAY - 1
        )
        cases.append({
            "regime": "trend_reversal",
            "name": (
                f"trend_reversal_{start:.2f}_{at_cutoff:.2f}"
                f"_{hidden_future:.2f}"
            ),
            "loads": loads,
            "initial": 0.30,
        })

    return cases


def _run_single_case(case):
    person_rows = _simulate_single(
        case["loads"],
        case["initial"],
        blind.PERSON_A,
        blind.PERSON_R,
    )
    link_rows = _simulate_single(
        case["loads"],
        case["initial"],
        blind.LINK_A,
        blind.LINK_R,
    )
    rows = _merge_person_link(person_rows, link_rows)
    result = blind.run_blind(
        rows,
        CUTOFF_DAY,
        HORIZON_DAYS,
        LOOKBACK_DAYS,
    )
    result["name"] = case["name"]
    result["regime"] = case["regime"]
    return result


def _score(results, predictor, group):
    key = f"{group}_direction_score"
    scores = [item[predictor][key] for item in results]
    correct = sum(item["correct"] for item in scores)
    total = sum(item["total"] for item in scores)
    return {
        "correct": correct,
        "total": total,
        "accuracy": correct / total if total else None,
    }


def _regime_scores(results, group="person"):
    regimes = sorted({item["regime"] for item in results})
    return {
        regime: {
            "n": len([x for x in results if x["regime"] == regime]),
            "model": _score(
                [x for x in results if x["regime"] == regime],
                "model",
                group,
            ),
            "persistence": _score(
                [x for x in results if x["regime"] == regime],
                "persistence_baseline",
                group,
            ),
            "linear_trend": _score(
                [x for x in results if x["regime"] == regime],
                "linear_trend_baseline",
                group,
            ),
        }
        for regime in regimes
    }


def _constant(value, days=12):
    return [float(value)] * days


def _multi_rows(person_loads, link_loads, days=11):
    person_state = {key: 0.10 for key in person_loads}
    link_state = {key: 0.15 for key in link_loads}
    rows = []

    for day in range(days + 1):
        persons = {
            key: {
                "accumulated_load": person_state[key],
                "combined": float(person_loads[key][day]),
            }
            for key in person_loads
        }
        links = {
            key: {
                "accumulated_strain": link_state[key],
                "combined": float(link_loads[key][day]),
            }
            for key in link_loads
        }
        rows.append({"day": float(day), "persons": persons, "links": links})

        if day >= days:
            break
        for key in person_loads:
            person_state[key] = blind.project_accumulator(
                person_state[key],
                float(person_loads[key][day]),
                1.0,
                blind.PERSON_A,
                blind.PERSON_R,
            )
        for key in link_loads:
            link_state[key] = blind.project_accumulator(
                link_state[key],
                float(link_loads[key][day]),
                1.0,
                blind.LINK_A,
                blind.LINK_R,
            )

    return rows


def localization_cases():
    days = 12
    low_links = {
        "a->b": _constant(0.05, days),
        "a->c": _constant(0.05, days),
        "b->c": _constant(0.05, days),
    }
    low_people = {
        "a": _constant(0.05, days),
        "b": _constant(0.05, days),
        "c": _constant(0.05, days),
    }

    return [
        {
            "name": "person_continuation",
            "target_group": "person",
            "rows": _multi_rows(
                {
                    "a": _constant(0.25, days),
                    "b": _constant(0.12, days),
                    "c": _constant(0.08, days),
                },
                low_links,
            ),
        },
        {
            "name": "link_continuation",
            "target_group": "link",
            "rows": _multi_rows(
                low_people,
                {
                    "a->b": _constant(0.25, days),
                    "a->c": _constant(0.12, days),
                    "b->c": _constant(0.08, days),
                },
            ),
        },
        {
            "name": "person_hidden_switch",
            "target_group": "person",
            "rows": _multi_rows(
                {
                    "a": [0.22] * 6 + [0.02] * 6,
                    "b": [0.08] * 6 + [0.50] * 6,
                    "c": _constant(0.05, days),
                },
                low_links,
            ),
        },
        {
            "name": "link_hidden_switch",
            "target_group": "link",
            "rows": _multi_rows(
                low_people,
                {
                    "a->b": [0.25] * 6 + [0.02] * 6,
                    "a->c": [0.08] * 6 + [0.60] * 6,
                    "b->c": _constant(0.05, days),
                },
            ),
        },
    ]


def _localization_value(result, predictor, target_group):
    if target_group == "person":
        predicted = result[predictor]["prediction"].get(
            "predicted_first_person_attention"
        )
        actual = result[predictor]["actual"][
            "actual_first_person_attention"
        ]
    else:
        predicted = result[predictor]["prediction"].get(
            "predicted_first_link_repair"
        )
        actual = result[predictor]["actual"]["actual_first_link_repair"]
    return predicted, actual, predicted == actual


def run_benchmark():
    direction_results = [
        _run_single_case(case) for case in single_entity_cases()
    ]

    localization_results = []
    for case in localization_cases():
        result = blind.run_blind(
            case["rows"],
            cutoff_day=5,
            horizon_days=5,
            lookback_days=3,
        )
        row = {
            "name": case["name"],
            "target_group": case["target_group"],
        }
        for predictor in (
            "model",
            "persistence_baseline",
            "linear_trend_baseline",
        ):
            predicted, actual, correct = _localization_value(
                result, predictor, case["target_group"]
            )
            row[predictor] = {
                "predicted": predicted,
                "actual": actual,
                "correct": correct,
            }
        localization_results.append(row)

    def loc_score(predictor):
        correct = sum(
            row[predictor]["correct"]
            for row in localization_results
        )
        return {
            "correct": correct,
            "total": len(localization_results),
            "accuracy": correct / len(localization_results),
        }

    return {
        "benchmark": "OUTCOME-BENCH1",
        "direction_case_count": len(direction_results),
        "direction_scores": {
            "person": {
                "model": _score(direction_results, "model", "person"),
                "persistence": _score(
                    direction_results,
                    "persistence_baseline",
                    "person",
                ),
                "linear_trend": _score(
                    direction_results,
                    "linear_trend_baseline",
                    "person",
                ),
            },
            "link": {
                "model": _score(direction_results, "model", "link"),
                "persistence": _score(
                    direction_results,
                    "persistence_baseline",
                    "link",
                ),
                "linear_trend": _score(
                    direction_results,
                    "linear_trend_baseline",
                    "link",
                ),
            },
        },
        "person_regime_scores": _regime_scores(
            direction_results, "person"
        ),
        "link_regime_scores": _regime_scores(
            direction_results, "link"
        ),
        "localization_cases": localization_results,
        "localization_scores": {
            "model": loc_score("model"),
            "persistence": loc_score("persistence_baseline"),
            "linear_trend": loc_score("linear_trend_baseline"),
        },
        "claim_boundary": (
            "All OUTCOME-BENCH1 trajectories are synthetic. Scores measure "
            "behavior of the current blind-evaluation equations and do not "
            "establish prediction of real human outcomes."
        ),
    }


def main():
    print(json.dumps(run_benchmark(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
