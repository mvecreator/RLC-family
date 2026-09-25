# UNIFIED-ENGINE1 — canonical RLC-family runtime façade

UNIFIED-ENGINE1 is the canonical orchestration layer over the merged RLC-family stack.

It does not replace the individual modules. It gives them one deterministic compile/run contract.

## 1. Why this layer exists

Before UNIFIED-ENGINE1 the repository had multiple executable layers:

~~~text
PERSON2 compiler
MULTI-LINK1
LINK-SEMI1
CHANNEL-COUPLING1
PERSON-TIME2
RHYTHM-25H1
ACOUSTIC-INDUCTION1
PERSON-FAMILY-SAFETY1
PERSON-THERM1 / RECOVERY-DEBT1
NEIGHBOR-NET1
PERCEPTION-ID1
~~~

They were individually callable, but composition was fragmented.

UNIFIED-ENGINE1 turns them into one runtime pipeline:

~~~text
scenario
  |
  v
PERSON2 compile
  |
  +--> nonlinear / parallel / coupled links
  +--> rhythm metadata
  +--> acoustic contract
  |
  v
PERSON-TIME2 trajectory
  |
  +--> Family Safety projection
  |       |
  |       +--> Thermal / Recovery projection
  |
  +--> optional Neighbor projection
  +--> optional Perception projection
  |
  v
one result bundle + reproducibility metadata
~~~

## 2. Single timeline authority

The main execution invariant is:

> PERSON-TIME2 is run once for the primary timeline.

Family Safety consumes that trajectory directly.

Thermal/Recovery consumes the Family Safety trajectory directly.

This removes orchestration-level duplication where the same timeline could be recomputed by separate entry points.

## 3. Compile API

~~~python
from simulator import unified_engine

compiled = unified_engine.compile_engine(
    scenario,
    engine_spec,
)
~~~

The compiled contract contains:

~~~text
engine_version
component_versions
capabilities
person_ir
acoustic_ir
features_present
timeline_present
neighbor_spec_present
perception_analysis_ids
~~~

## 4. Run API

~~~python
result = unified_engine.run_engine(
    scenario,
    engine_spec,
)
~~~

CLI:

~~~bash
python3 simulator/unified_engine.py \
  examples/acoustic_induction1_households_scenario.json \
  examples/unified_engine1_spec.json \
  --out out/unified_engine_result.json
~~~

Problem solver:

~~~json
{
  "type": "unified_engine",
  "engine_spec": {
    "timeline": {},
    "neighbor_spec": {},
    "perception_specs": []
  }
}
~~~

Canonical problem example:

~~~text
examples/unified_engine1_problem.json
~~~

## 5. Engine spec

The base engine spec may contain:

~~~text
timeline
relationship_flags
neighbor_spec
perception_specs
~~~

Only requested optional projections are run.

A scenario may also be compiled without a timeline:

~~~python
run_engine(scenario, {})
~~~

This produces the PERSON2 IR and feature manifest without inventing trajectories.

## 6. Capability manifest

UNIFIED-ENGINE1 currently declares:

~~~text
PERSON2_RLC_NODES
MULTI_LINK_PARALLEL_CHANNELS
NONLINEAR_LINK_DEVICES
CHANNEL_COUPLING
PERSON_TIME2_RK4
RHYTHM_25H1
ACOUSTIC_INDUCTION1
PERSON_FAMILY_SAFETY1
PERSON_THERM1
RECOVERY_DEBT1
NEIGHBOR_NET1_OPTIONAL
PERCEPTION_ID1_OPTIONAL
~~~

The capability list means the engine can orchestrate these mechanisms.

features_present separately records what the current scenario actually uses.

## 7. Feature manifest

For each compiled scenario the engine records:

~~~text
parallel_link_pairs
nonlinear_link_ids
channel_coupling_count
rhythm_node_ids
acoustic_coupling_count
acoustic_source_count
channel_kinds
element_types
neighbor_projection_requested
perception_projection_count
~~~

This prevents a capability from being confused with an active mechanism.

## 8. Reproducibility

UNIFIED-ENGINE1 computes:

~~~text
input_digest
compiled_contract_digest
engine_version
component_versions
~~~

input_digest is SHA-256 over the canonical JSON representation of:

~~~text
scenario + engine_spec
~~~

compiled_contract_digest is SHA-256 over the compiled engine contract.

Changing an input parameter changes the input digest.

## 9. Result bundle

A normal timeline run produces:

~~~text
outputs.person_ir
outputs.timeline
outputs.family_safety
outputs.thermal_recovery
~~~

Optional:

~~~text
outputs.neighbor_network
outputs.perception_identification
~~~

The top-level summary points back to these downstream results; it does not recompute independent scores.

## 10. Rhythm + acoustic coexistence

The canonical engine example uses:

~~~text
central intrinsic period = 25 h
external schedule = 24 h
acoustic wall couplings = 3
acoustic sources = 5
~~~

The same PERSON-TIME2 trajectory therefore contains:

~~~text
RLC voltage/current
memory
link currents
channel coupling
rhythm phase mismatch
acoustic direct drive
acoustic derivative drive
~~~

Family Safety and Thermal/Recovery consume the resulting trajectory.

## 11. Optional Neighbor projection

neighbor_spec runs NEIGHBOR-NET1 over the same scenario.

It remains a separate counterfactual analysis because it intentionally executes:

~~~text
actual
no relief
continued pre-pattern
desynchronized timing
removed household-internal links
removed cross-household links
~~~

Those are separate model worlds and are not folded into the one primary PERSON-TIME2 trajectory.

## 12. Optional Perception projection

perception_specs is a list:

~~~json
[
  {
    "id": "central-brief-observer",
    "spec": {
      "target_person_id": "central"
    }
  }
]
~~~

Each analysis remains synthetic parameter-identification work.

UNIFIED-ENGINE1 preserves:

~~~text
real_world_belief_inference = false
~~~

from PERCEPTION-ID1.

## 13. Scientific boundary

The unified engine composes engineering models. It does not upgrade their epistemic status.

~~~text
accumulated_load != clinical stress measurement
heat != body temperature
damage != relationship-break probability
temporal alignment != intent
network coupling != coordination
perceived_theta != real person's belief
acoustic transmission != targeted behavior
~~~

The engine's value is reproducible composition, not mind-reading.

## 14. Canonical examples

~~~text
examples/acoustic_induction1_households_scenario.json
examples/unified_engine1_spec.json
examples/unified_engine1_full_spec.json
examples/unified_engine1_problem.json
~~~

## 15. Calibration

UNIFIED-ENGINE-CAL1 defines 16 gates:

~~~text
UE01 input digest deterministic
UE02 compiled-contract digest deterministic
UE03 merged capability manifest present
UE04 full household PERSON2 graph compiles
UE05 25h rhythm visible
UE06 acoustic contract compiled once
UE07 primary 12-day timeline present
UE08 Family Safety reuses timeline sample grid
UE09 Thermal reuses Family trajectory grid
UE10 rhythm/acoustic provenance survives unified run
UE11 Perception projection preserves boundary
UE12 Neighbor projection is explicit and optional
UE13 top-level summary references downstream outputs
UE14 input change changes reproducibility digest
UE15 compile-only mode invents no trajectory
UE16 interpretation boundary remains nonclinical/noncausal
~~~

Executable gate:

~~~bash
python3 simulator/unified_engine_calibration.py
python3 -m unittest tests.test_unified_engine -v
~~~

Expected own gate:

~~~text
UNIFIED-ENGINE-CAL1 16/16 PASS
~~~

No founder/local WSL PASS is claimed until executable verification is supplied.
