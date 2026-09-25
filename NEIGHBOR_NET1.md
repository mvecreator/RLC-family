# NEIGHBOR-NET1 — repeated observed stimuli, households and intervention markers

NEIGHBOR-NET1 is a small-network calibration layer built on PERSON-TIME2,
MULTI-LINK1, LINK-SEMI1, CHANNEL-COUPLING1, PERSON-FAMILY-SAFETY1 and
LINK-THERM1.

It models a central person, several neighboring people or households, explicit
social links between source nodes, observed stimulus events, and an external
intervention marker.

It does **not** infer hostile intent, conspiracy, harassment, coordination, or
causality from timing alone.

## 1. First baseline: three solo neighbors

The simplest topology is:

```text
n1 ----- n2
 \       /
  \     /
    n3
   \|/
 central
```

Each neighbor may have:
- an environmental/observation channel toward `central`;
- direct social links to other neighbors.

Observed events excite the named source node and PERSON-TIME2 propagates the
response through the declared network.

## 2. Household-aware topology

NEIGHBOR-NET1 also supports different household compositions.

Canonical second example:

```text
household1_solo
  solo1

household2_family3
  husband
  wife
  adult son

household3_couple
  husband
  wife
```

Each household may contain explicit `household_internal` links.

Separate `cross_household_social` links may represent direct contact between
members of different households.

The existence of such links means only that the scenario declares a direct
communication path. It does not establish a shared motive.

## 3. Household-level observed event

When an event is observed at household level but the exact person is unknown,
the event may use:

```json
{
  "source_group_id": "household2_family3",
  "amplitude": 0.45,
  "duration_days": 0.20
}
```

The total amplitude is **not multiplied by household size**.

By default it is distributed equally:

```math
\sum_{m\in H} w_m = 1.
```

For three members:

```text
0.45 -> 0.15 + 0.15 + 0.15
```

Explicit `member_weights` may be supplied when there is evidence for a
different distribution.

This keeps comparisons between solo, couple and family households fair.

## 4. Repeated exposure and accumulation

Repeated observed stimuli can generate repeated branch currents and therefore
increase the central person's modeled:

```text
memory
accumulated_load
heat
recovery_debt
```

The core hypothesis is:

```text
small repeated inputs
can create a larger accumulated state
than one isolated input
```

without requiring a claim about why the events occurred.

## 5. Temporal alignment

NEIGHBOR-NET1 computes a timing-only alignment statistic.

An event is considered aligned when another **different household/source**
produces an event within the declared tolerance window.

The output includes:

```text
temporal_alignment_index
intent_inferred = false
```

High alignment is a waveform property, not proof of coordination.

A deterministic desynchronization counterfactual preserves:
- event count;
- amplitude;
- duration;
- total exposure area;

while spreading event times.

The model then measures how the central waveform changes.

No sign is precommitted: synchronized timing may increase, reduce or leave a
particular metric unchanged depending on the dynamics.

## 6. Intervention marker

An external intervention is represented by a dated marker:

```json
{
  "id": "external-support-contact",
  "at_day": 6.0
}
```

Optional central-person effects may be declared separately:

```text
central_memory_relief
central_drive_relief
```

These represent the modeled effect of obtaining external support on the central
person only.

The intervention marker **does not alter neighbor events automatically**.

Post-intervention behavior is whatever the observed stimulus record actually
contains.

Therefore these are separate questions:

1. Did the central person receive modeled relief?
2. Did the observed post-event regime differ from the pre-event regime?

## 7. Before/after analysis

For equal pre/post windows NEIGHBOR-NET1 reports:

```text
event_count
events_per_day
mean_amplitude
exposure_area
events_by_household
temporal_alignment_index
```

and central:

```text
peak/final accumulated_load
peak/final heat
peak/final recovery_debt
```

A before/after difference is an association with the intervention date.

It is not by itself proof that the intervention caused the behavioral change.

## 8. Counterfactuals

The first version computes four comparisons.

### No-relief counterfactual

Same observed events, but without declared central relief.

This isolates the modeled support effect on the central person.

### Continued-pre-pattern counterfactual

The pre-event pattern is repeated into the post window.

This compares:

```text
observed quieter/louder post regime
vs
continued previous regime
```

### Desynchronized timing counterfactual

Same pre exposure but redistributed in time.

This measures waveform/timing sensitivity.

### Removed-network-edge counterfactuals

Household-aware analysis can remove:
- `household_internal` links;
- `cross_household_social` links;

while leaving observed events unchanged.

This measures topology effects separately from event exposure.

## 9. Equal-input household transfer probe

To compare household structures fairly, NEIGHBOR-NET1 applies the same total
synthetic impulse separately to every household.

Example:

```text
same amplitude A
same duration T
same exposure A*T
```

For:
- solo household;
- family of three adults;
- couple.

For larger households the amplitude is normalized across members.

The output reports central response deltas relative to a no-probe baseline:

```text
peak_abs_load_delta
peak_abs_heat_delta
final_load_delta
final_heat_delta
```

The ranking is descriptive only.

The model does **not** assume that a larger household must produce a larger
response.

## 10. Internal household topology counterfactual

For the same equal-input probe the model also removes all
`household_internal` links and reruns it.

For every household:

```text
with_internal_links_peak_abs_load_delta
without_internal_links_peak_abs_load_delta
difference
```

For a solo household this difference should be zero.

For a family/couple the sign is not precommitted.

## 11. Cross-household social topology counterfactual

The household example also declares explicit:

```text
cross_household_social
```

links.

The main pre-period analysis is rerun with those links removed while keeping
the observed events unchanged.

The resulting difference answers:

> Does the declared inter-household network topology change the central
> response under the same event history?

It does not answer:

> Were the households intentionally coordinating?

## 12. Why mutual inductance is deferred

NEIGHBOR-NET1 deliberately starts without explicit mutual inductance
`M dI/dt`.

First we test whether:

```text
ordinary PERSON2 RLC dynamics
+ directed environmental channels
+ household/internal social topology
+ repeated forcing
```

already explain the waveform.

Only if derivative coupling adds reproducible predictive value should a separate
gate be introduced:

```text
MUTUAL-INDUCTANCE1
```

## 13. Canonical examples

Three solo neighbors:

```text
examples/neighbor_net1_synthetic_scenario.json
examples/neighbor_net1_synthetic_spec.json
```

Mixed household composition:

```text
examples/neighbor_net1_households_scenario.json
examples/neighbor_net1_households_spec.json
```

The second example contains:

```text
1 solo
1 couple + adult son
1 couple
household_internal links
cross_household_social links
environmental_observation links to central
```

## 14. Calibration gates

NEIGHBOR-NET-CAL1 currently defines 20 gates:

```text
NN01 observed events reach central through declared observation links
NN02 repeated events accumulate central load
NN03 pre timing is more aligned than the synthetic post example
NN04 desynchronization preserves count and exposure
NN05 timing counterfactual has no precommitted direction
NN06 observed post event rate/exposure are lower in the synthetic example
NN07 declared central relief does not increase final post load
NN08 continued pre-pattern is not lighter than observed synthetic post
NN09 intervention marker does not rewrite observed post events
NN10 continuation exists only as explicit counterfactual
NN11 temporal alignment does not infer intent
NN12 causal boundary remains explicit
NN13 household composition 1/3/2 compiles
NN14 household group input is conserved when distributed
NN15 household probe uses equal total input
NN16 every household response is computed
NN17 solo response is invariant to removing household-internal links
NN18 family/couple internal-topology counterfactuals are computed
NN19 cross-household social links are explicit
NN20 cross-household topology effect has no precommitted sign
```

These gates validate mechanics and accounting, not claims about real people.

## 15. Problem solver route

The generic solver accepts:

```json
{
  "type": "neighbor_network",
  "neighbor_spec": {}
}
```

and routes to NEIGHBOR-NET1.

## 16. Executable gate

```bash
python3 simulator/neighbor_network_calibration.py
python3 -m unittest tests.test_neighbor_network -v

# stacked parents
python3 simulator/channel_coupling_calibration.py
python3 -m unittest tests.test_channel_coupling -v

python3 simulator/multi_link_calibration.py
python3 -m unittest tests.test_multi_link -v

python3 simulator/link_semiconductor_calibration.py
python3 -m unittest tests.test_link_semiconductor -v
python3 -m unittest tests.test_link_semiconductor_integration -v

python3 simulator/thermal_calibration.py
python3 -m unittest tests.test_thermal_recovery -v
python3 -m unittest tests.test_recovery_scenarios -v

# legacy
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_link_semantics -v
python3 -m unittest tests.test_person_load_family_cases -v
python3 -m unittest tests.test_family_validation_cases -v
```

Expected own gate:

```text
NEIGHBOR-NET-CAL1 20/20 PASS
```

No founder/local WSL PASS is claimed until executable verification is supplied.
