#!/usr/bin/env python3
"""ACOUSTIC-INDUCTION1: wall-transmitted and derivative acoustic forcing.

For every acoustic source signal s(t), the target drive is

    u(t) = T * s(t) + M_a * ds/dt

where:
- T is dimensionless direct acoustic transmission;
- M_a has units of days and scales the transient/derivative term.

This is an engineering signal layer. It does not infer intent, hostility,
coordination, or psychological state from sound.
"""

from __future__ import annotations

import math


VERSION = "RLC-FAMILY-ACOUSTIC-INDUCTION1-0.1"


def _num(value, name, lo=None, hi=None):
    value = float(value)
    if lo is not None and value < lo:
        raise ValueError(f"{name} must be >= {lo}")
    if hi is not None and value > hi:
        raise ValueError(f"{name} must be <= {hi}")
    return value


def _smoothstep(x):
    x = max(0.0, min(1.0, float(x)))
    return x * x * (3.0 - 2.0 * x)


def _smoothstep_derivative(x):
    x = max(0.0, min(1.0, float(x)))
    return 6.0 * x * (1.0 - x)


def compile_acoustic(scenario, timeline, node_ids):
    model = scenario.get("acoustic_induction") or {}
    if not isinstance(model, dict):
        raise ValueError("acoustic_induction must be object")

    raw_couplings = model.get("couplings", [])
    if not isinstance(raw_couplings, list):
        raise ValueError("acoustic_induction.couplings must be list")

    couplings = []
    seen_ids = set()
    zones = set()
    for idx, raw in enumerate(raw_couplings):
        if not isinstance(raw, dict):
            raise ValueError(f"acoustic coupling {idx} must be object")
        cid = str(raw.get("id", f"acoustic-coupling-{idx+1}")).strip()
        if not cid or cid in seen_ids:
            raise ValueError("acoustic coupling ids must be unique and non-empty")
        seen_ids.add(cid)

        zone = str(raw.get("source_zone", "")).strip()
        target = str(raw.get("target_person", "")).strip()
        if not zone:
            raise ValueError(f"{cid}.source_zone required")
        if target not in node_ids:
            raise ValueError(f"{cid}.target_person unknown: {target}")

        transmission = _num(
            raw.get("transmission", 0.0),
            f"{cid}.transmission",
            0.0,
            1.0,
        )
        derivative_days = _num(
            raw.get("derivative_coupling_days", 0.0),
            f"{cid}.derivative_coupling_days",
            0.0,
        )

        couplings.append({
            "id": cid,
            "source_zone": zone,
            "target_person": target,
            "transmission": transmission,
            "derivative_coupling_days": derivative_days,
        })
        zones.add(zone)

    raw_sources = timeline.get("acoustic_sources", [])
    if not isinstance(raw_sources, list):
        raise ValueError("timeline.acoustic_sources must be list")

    sources = []
    seen_source_ids = set()
    for idx, raw in enumerate(raw_sources):
        if not isinstance(raw, dict):
            raise ValueError(f"acoustic source {idx} must be object")
        sid = str(raw.get("id", f"acoustic-source-{idx+1}")).strip()
        if not sid or sid in seen_source_ids:
            raise ValueError("acoustic source ids must be unique and non-empty")
        seen_source_ids.add(sid)

        zone = str(raw.get("source_zone", "")).strip()
        if zone not in zones:
            raise ValueError(
                f"{sid}.source_zone has no declared acoustic coupling: {zone}"
            )

        waveform = str(raw.get("waveform", "pulse")).strip().lower()
        if waveform not in {"constant", "step", "pulse", "burst", "sine"}:
            raise ValueError(f"{sid}.waveform unsupported: {waveform}")

        start = _num(raw.get("at_day", 0.0), f"{sid}.at_day", 0.0)
        duration = _num(
            raw.get("duration_days", 0.10),
            f"{sid}.duration_days",
            0.0,
        )
        amplitude = _num(
            raw.get("amplitude", 0.0),
            f"{sid}.amplitude",
            0.0,
        )
        edge = _num(
            raw.get("edge_days", min(0.01, duration / 4.0 if duration else 0.01)),
            f"{sid}.edge_days",
            1e-9,
        )
        if waveform == "pulse" and duration <= 2.0 * edge:
            raise ValueError(f"{sid}: pulse duration must exceed 2*edge_days")
        if waveform == "burst" and duration <= 2.0 * edge:
            raise ValueError(f"{sid}: burst duration must exceed 2*edge_days")

        period = _num(
            raw.get("period_days", 0.05),
            f"{sid}.period_days",
            1e-9,
        )
        phase = float(raw.get("phase_rad", 0.0))

        sources.append({
            "id": sid,
            "source_zone": zone,
            "waveform": waveform,
            "at_day": start,
            "duration_days": duration,
            "amplitude": amplitude,
            "edge_days": edge,
            "period_days": period,
            "phase_rad": phase,
        })

    by_zone = {}
    for coupling in couplings:
        by_zone.setdefault(coupling["source_zone"], []).append(coupling)

    return {
        "model_version": VERSION,
        "couplings": couplings,
        "sources": sources,
        "couplings_by_zone": by_zone,
    }


def _pulse_envelope(source, t):
    start = source["at_day"]
    duration = source["duration_days"]
    edge = source["edge_days"]
    end = start + duration

    if t < start or t >= end:
        return 0.0, 0.0

    if t < start + edge:
        x = (t - start) / edge
        return _smoothstep(x), _smoothstep_derivative(x) / edge

    if t >= end - edge:
        x = (end - t) / edge
        return _smoothstep(x), -_smoothstep_derivative(x) / edge

    return 1.0, 0.0


def source_value_and_derivative(source, t):
    waveform = source["waveform"]
    amp = source["amplitude"]
    start = source["at_day"]

    if waveform == "constant":
        return amp, 0.0

    if waveform == "step":
        if t < start:
            return 0.0, 0.0
        edge = source["edge_days"]
        if t < start + edge:
            x = (t - start) / edge
            return (
                amp * _smoothstep(x),
                amp * _smoothstep_derivative(x) / edge,
            )
        return amp, 0.0

    if waveform == "pulse":
        env, denv = _pulse_envelope(source, t)
        return amp * env, amp * denv

    omega = 2.0 * math.pi / source["period_days"]
    phase = omega * (t - start) + source["phase_rad"]

    if waveform == "sine":
        if t < start:
            return 0.0, 0.0
        return (
            amp * math.sin(phase),
            amp * omega * math.cos(phase),
        )

    # burst
    env, denv = _pulse_envelope(source, t)
    carrier = math.sin(phase)
    dcarrier = omega * math.cos(phase)
    return (
        amp * env * carrier,
        amp * (denv * carrier + env * dcarrier),
    )


def drive_at(compiled, t, node_ids):
    direct = {pid: 0.0 for pid in node_ids}
    inductive = {pid: 0.0 for pid in node_ids}
    details = []

    by_zone = compiled.get("couplings_by_zone", {})
    for source in compiled.get("sources", []):
        s, dsdt = source_value_and_derivative(source, t)
        if abs(s) < 1e-18 and abs(dsdt) < 1e-18:
            continue

        for coupling in by_zone.get(source["source_zone"], []):
            target = coupling["target_person"]
            u_direct = coupling["transmission"] * s
            u_inductive = (
                coupling["derivative_coupling_days"] * dsdt
            )
            direct[target] += u_direct
            inductive[target] += u_inductive
            details.append({
                "source_id": source["id"],
                "coupling_id": coupling["id"],
                "source_zone": source["source_zone"],
                "target_person": target,
                "source_value": s,
                "source_derivative_per_day": dsdt,
                "direct_drive": u_direct,
                "inductive_drive": u_inductive,
                "total_drive": u_direct + u_inductive,
            })

    return {
        "direct": direct,
        "inductive": inductive,
        "total": {
            pid: direct[pid] + inductive[pid]
            for pid in node_ids
        },
        "details": details,
    }


def acoustic_energy_proxy(compiled, start, end, dt, node_ids):
    t = float(start)
    acc = {pid: 0.0 for pid in node_ids}
    while t < end - 1e-15:
        step = min(dt, end - t)
        drive = drive_at(compiled, t, node_ids)["total"]
        for pid in node_ids:
            acc[pid] += abs(drive[pid]) * step
        t += step
    return acc
