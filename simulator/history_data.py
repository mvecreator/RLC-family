#!/usr/bin/env python3
"""HISTORY-DATA1: provenance and blind-validation eligibility for longitudinal records.

The purpose of this layer is methodological:
- distinguish prospective records from retrospective reconstruction;
- freeze cutoff/horizon before outcome evaluation;
- prevent known-future anecdotes from being counted as out-of-sample evidence.

It does not score health, relationships, or clinical risk.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

VERSION = "RLC-FAMILY-HISTORY-DATA1-0.1"
SCHEMA = "HISTORY-DATA1-0.1"


class HistoryDataError(ValueError):
    pass


def _bool(value, name):
    if not isinstance(value, bool):
        raise HistoryDataError(f"{name} must be boolean")
    return value


def _num(value, name):
    if isinstance(value, bool):
        raise HistoryDataError(f"{name} must be number")
    try:
        return float(value)
    except (TypeError, ValueError) as e:
        raise HistoryDataError(f"{name} must be number") from e


def load_json(path):
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise HistoryDataError(str(e)) from e
    if not isinstance(value, dict):
        raise HistoryDataError("record root must be object")
    return value


def _validate_date(value, name):
    if value is None:
        return None
    if not isinstance(value, str):
        raise HistoryDataError(f"{name} must be ISO date string or null")
    try:
        date.fromisoformat(value)
    except ValueError as e:
        raise HistoryDataError(f"{name} must be YYYY-MM-DD") from e
    return value


def _validate_observations(record):
    observations = record.get("observations", [])
    if not isinstance(observations, list):
        raise HistoryDataError("observations must be array")

    days = []
    dates = []
    for idx, item in enumerate(observations):
        if not isinstance(item, dict):
            raise HistoryDataError(f"observations[{idx}] must be object")
        if "day" in item and item["day"] is not None:
            day_value = _num(item["day"], f"observations[{idx}].day")
            days.append(day_value)
        if "date" in item:
            d = _validate_date(item.get("date"), f"observations[{idx}].date")
            if d is not None:
                dates.append(d)
        if "recorded_contemporaneously" in item:
            _bool(
                item["recorded_contemporaneously"],
                f"observations[{idx}].recorded_contemporaneously",
            )

    if days and any(b <= a for a, b in zip(days, days[1:])):
        raise HistoryDataError("observation days must be strictly increasing")
    if dates and any(b <= a for a, b in zip(dates, dates[1:])):
        raise HistoryDataError("observation dates must be strictly increasing")

    return observations


def validate_record(record):
    if not isinstance(record, dict):
        raise HistoryDataError("record must be object")
    if record.get("schema") != SCHEMA:
        raise HistoryDataError(f"schema must be {SCHEMA}")

    record_id = record.get("record_id")
    if not isinstance(record_id, str) or not record_id.strip():
        raise HistoryDataError("record_id must be non-empty string")

    mode = record.get("collection_mode")
    if mode not in {"prospective", "retrospective"}:
        raise HistoryDataError(
            "collection_mode must be prospective or retrospective"
        )

    if "template" in record:
        _bool(record["template"], "template")

    time_axis = record.get("time_axis")
    if not isinstance(time_axis, dict):
        raise HistoryDataError("time_axis must be object")
    for key in (
        "exact_calendar_dates_known",
        "relative_day_observed",
        "phase_order_known",
    ):
        if key not in time_axis:
            raise HistoryDataError(f"time_axis.{key} is required")
        _bool(time_axis[key], f"time_axis.{key}")

    if "future_outcome_known_when_logged" not in record:
        raise HistoryDataError(
            "future_outcome_known_when_logged is required"
        )
    _bool(
        record["future_outcome_known_when_logged"],
        "future_outcome_known_when_logged",
    )

    if "future_derived_features_present" in record:
        _bool(
            record["future_derived_features_present"],
            "future_derived_features_present",
        )

    observations = _validate_observations(record)

    phases = record.get("phases", [])
    if not isinstance(phases, list):
        raise HistoryDataError("phases must be array")
    for idx, phase in enumerate(phases):
        if not isinstance(phase, dict):
            raise HistoryDataError(f"phases[{idx}] must be object")
        if not isinstance(phase.get("id"), str) or not phase["id"].strip():
            raise HistoryDataError(f"phases[{idx}].id required")

    prereg = record.get("preregistration")
    if prereg is not None and not isinstance(prereg, dict):
        raise HistoryDataError("preregistration must be object or null")

    return {
        "record_id": record_id,
        "collection_mode": mode,
        "observation_count": len(observations),
        "phase_count": len(phases),
    }


def _preregistration_info(record):
    prereg = record.get("preregistration")
    if not isinstance(prereg, dict):
        return None

    cutoff = prereg.get("cutoff_day")
    horizon = prereg.get("horizon_days")
    frozen = prereg.get("frozen_before_outcome")
    model_ref = prereg.get("model_ref")

    try:
        cutoff = _num(cutoff, "preregistration.cutoff_day")
        horizon = _num(horizon, "preregistration.horizon_days")
    except HistoryDataError:
        return None

    if horizon <= 0:
        return None
    if frozen is not True:
        return None
    if not isinstance(model_ref, str) or not model_ref.strip():
        return None

    return {
        "cutoff_day": cutoff,
        "horizon_days": horizon,
        "frozen_before_outcome": True,
        "model_ref": model_ref,
    }


def blind_eligibility(record):
    validate_record(record)
    reasons = []

    if record.get("template") is True:
        reasons.append("template_record")

    if record["collection_mode"] != "prospective":
        reasons.append("not_prospective")

    if record["future_outcome_known_when_logged"] is True:
        reasons.append("future_outcome_already_known")

    if record.get("future_derived_features_present") is True:
        reasons.append("future_derived_features_present")

    time_axis = record["time_axis"]
    if not (
        time_axis["exact_calendar_dates_known"]
        or time_axis["relative_day_observed"]
    ):
        reasons.append("no_observed_time_axis")

    prereg = _preregistration_info(record)
    if prereg is None:
        reasons.append("missing_or_invalid_preregistration")

    observations = record.get("observations", [])
    if len(observations) < 2:
        reasons.append("insufficient_observations")

    if observations and any(
        item.get("recorded_contemporaneously") is not True
        for item in observations
    ):
        reasons.append("noncontemporaneous_observations")

    if prereg is not None and observations:
        cutoff = prereg["cutoff_day"]
        horizon_end = cutoff + prereg["horizon_days"]
        observed_days = [
            float(item["day"])
            for item in observations
            if item.get("day") is not None
        ]
        if not observed_days:
            reasons.append("no_relative_day_values")
        else:
            if not any(day <= cutoff for day in observed_days):
                reasons.append("empty_prefix")
            if not any(cutoff < day <= horizon_end for day in observed_days):
                reasons.append("empty_hidden_suffix")

    return {
        "record_id": record["record_id"],
        "eligible": not reasons,
        "reasons": reasons,
        "preregistration": prereg,
        "evidence_class": (
            "blind_out_of_sample_candidate"
            if not reasons
            else (
                "retrospective_hypothesis_record"
                if record["collection_mode"] == "retrospective"
                else "not_blind_eligible"
            )
        ),
    }


def split_blind_record(record):
    eligibility = blind_eligibility(record)
    if not eligibility["eligible"]:
        raise HistoryDataError(
            "record is not blind-eligible: "
            + ", ".join(eligibility["reasons"])
        )

    prereg = eligibility["preregistration"]
    cutoff = prereg["cutoff_day"]
    end = cutoff + prereg["horizon_days"]
    observations = record["observations"]

    prefix = [
        item for item in observations
        if float(item["day"]) <= cutoff
    ]
    hidden = [
        item for item in observations
        if cutoff < float(item["day"]) <= end
    ]

    return {
        "record_id": record["record_id"],
        "model_ref": prereg["model_ref"],
        "cutoff_day": cutoff,
        "horizon_days": prereg["horizon_days"],
        "prefix": prefix,
        "hidden_suffix": hidden,
        "contract": {
            "prefix_available_to_predictor": True,
            "hidden_suffix_available_to_predictor": False,
            "hidden_suffix_available_to_evaluator_after_prediction": True,
        },
    }


def report(record):
    status = blind_eligibility(record)
    return {
        "history_data_version": VERSION,
        "record_id": record["record_id"],
        "collection_mode": record["collection_mode"],
        "blind_eligibility": status,
        "boundary": (
            "Eligibility checks provenance and no-lookahead structure only. "
            "It does not validate the truth or predictive value of the observations."
        ),
    }


def main():
    p = argparse.ArgumentParser(
        description="Check HISTORY-DATA1 blind-validation eligibility"
    )
    p.add_argument("record")
    p.add_argument("--split", action="store_true")
    args = p.parse_args()

    record = load_json(args.record)
    result = split_blind_record(record) if args.split else report(record)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
