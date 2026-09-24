# PERSON-THERM1 / LINK-THERM1 / RECOVERY-SCENARIO1

This layer adds thermal memory to the existing PERSON-LOAD1 and LINK-SEM1 network.

It is an engineering analogy.

It does **not** measure body temperature, diagnose burnout, prescribe a holiday,
or calculate the probability of relationship rupture.

## 1. Link dissipation

For every PERSON2 relationship link:

```math
P_{pq}=I_{pq}^2R_{pq}.
```

This is the standard resistor dissipation form applied to the executable link
current and link resistance already present in the network.

It distinguishes useful regimes:

```text
low R + high I
  -> strong interaction through a good channel

high R + low I
  -> weak / partially disconnected interaction

high R + high I
  -> high dissipation; candidate overheating regime
```

The raw value is retained as:

```text
dissipation_power_proxy
```

and normalized by the current engineering reference:

```text
LINK_POWER_REF = 0.020
```

This reference is a model calibration convention, not a physical watt value.

## 2. Link thermal memory

The bounded thermal state obeys:

```math
\dot H_{pq}
=
a_h P_{pq}^{norm}(1-H_{pq})
-
b_h C_{pq}H_{pq}.
```

Current calibration:

```text
a_h = 0.50
b_h = 0.25
```

Cooling capacity depends on:

- communication quality;
- lower interaction intensity.

A good channel can therefore carry significant interaction without accumulating
the same heat as a high-resistance channel.

## 3. Link damage

Heat alone can recover quickly.

A second slow state represents accumulated damage:

```math
\dot D_{pq}
=
\gamma\max(0,H_{pq}-H_{overheat})(1-D_{pq})
-
\delta C_{pq}D_{pq}.
```

Current reference:

```text
H_overheat = 0.55
damage_gain = 0.25
damage_repair = 0.05
```

Bands:

```text
COMFORT
WARM
OVERHEATED
DAMAGE_ACCUMULATION
RUPTURE_RISK_REVIEW
```

`RUPTURE_RISK_REVIEW` is a project warning label, not a divorce/separation
prediction.

## 4. Person thermal memory

For a person, PERSON-LOAD1 `combined` is used as the heat-input proxy:

```math
\dot H_p
=
0.35L_p(1-H_p)
-
0.25C_pH_p.
```

Baseline cooling capacity is derived from the existing recovery-inertia input:

```math
C_p=1-recovery\_inertia_p.
```

Current person bands:

```text
COMFORT       H < 0.35
WARM          H >= 0.35
OVERHEATED    H >= 0.55
HIGH_HEAT     H >= 0.70
```

Again, these are internal model states rather than clinical cut-offs.

## 5. Recovery debt

Immediate heat and long recovery need not be the same thing.

The model therefore keeps:

```text
recovery_debt_heat_days
```

with:

```math
\dot B
=
\max(0,H-H_{comfort})
-
k C B.
```

A short rest can reduce current heat while leaving substantial accumulated
recovery debt.

This is the mechanism behind a scenario such as:

> "I had one free evening, but the model still has not returned to its
> comfortable region."

## 6. Recovery scenarios

`RECOVERY-SCENARIO1` does not assign a magical coefficient to "holiday",
"mountains", "sea", or any other destination.

Instead every profile is a bundle of mechanisms:

```text
person_load_multiplier
person_cooling_boost
link_power_multiplier
link_cooling_boost
```

Current built-in comparison profiles:

### continue_7d

No intervention.

### three_day_break_then_return

Three low-demand days followed by four baseline days.

### work_disconnect_7d

Strong reduction in direct demands plus improved recovery capacity.

### deep_recovery_7d

A stronger low-demand recovery hypothesis.

### mountain_style_7d

Uses the same person-side assumptions as `deep_recovery_7d`.

The only additional link-side assumption is lower heavy-interaction load and
slightly larger cooling opportunity.

Therefore:

```text
mountain_style != mountain physics
```

It is shorthand for a mechanism bundle such as:

- disconnect from work;
- fewer interruptions;
- better recovery opportunity;
- less forced heavy interaction.

### cool_then_shared_7d

Two stages:

1. two days with very low interaction load and strong cooling;
2. five days with moderate shared interaction under continued low demand.

This allows testing the hypothesis:

> first cool the people/link, then return to difficult interaction.

## 7. Example use

Thermal state:

```json
{
  "type": "family_thermal",
  "timeline": {
    "моделирование": {},
    "события": []
  }
}
```

Recovery comparison:

```json
{
  "type": "recovery_scenarios",
  "cutoff_day": 20,
  "profiles": [
    "continue_7d",
    "three_day_break_then_return",
    "work_disconnect_7d",
    "mountain_style_7d",
    "cool_then_shared_7d"
  ],
  "timeline": {
    "моделирование": {},
    "события": []
  }
}
```

Or directly:

```bash
python3 simulator/recovery_scenarios.py \
  examples/person_family_scenario.json \
  examples/person_family_stress_timeline.json \
  --cutoff-day 20
```

## 8. Calibration gates

```text
TH01 same current + higher R -> higher I^2R
TH02 double current -> 4x dissipation at same R
TH03 low person load stays comfortable
TH04 sustained high person load creates heat and recovery debt
TH05 low link power does not create damage
TH06 sustained high link power overheats and accumulates damage
TH07 deep recovery cools person more than continuation
TH08 deep recovery cools/damages link less than continuation
TH09 person heat bands remain ordered
TH10 high damage can raise RUPTURE_RISK_REVIEW
```

## 9. Reference synthetic values

Current calibration approximately gives:

```text
person load 0.10 for 14 d:
  heat ~0.21
  debt ~0

person load 0.50 for 14 d:
  heat ~0.58
  debt >1 heat-day

link power 0.10 for 14 d:
  heat ~0.27
  damage 0

link power 0.60 for 14 d:
  heat ~0.70
  damage ~0.26
```

Starting from a deliberately overheated calibration state:

```text
person:
  continue 7 d       heat ~0.59
  deep recovery 7 d  heat ~0.18

link:
  continue 7 d       heat ~0.75, damage ~0.42
  deep recovery 7 d  heat ~0.52, damage ~0.23
```

These are equation-calibration values, not predicted effects of a real holiday.

## 10. Product interpretation

A future application may translate the state into statements such as:

```text
Current heat is falling, but recovery debt remains high.

A 3-day break reduces heat but does not return the model to the comfort band.

A 7-day low-demand scenario produces substantially more cooling in the
current model.

The partner link remains overheated; consider testing a staged scenario with
less heavy interaction first.
```

It must not say:

```text
"You medically need a vacation."
"Your relationship has a 70% chance of breaking."
"Going to the mountains will cure the problem."
```

## 11. Executable verification

```bash
python3 simulator/thermal_calibration.py
python3 -m unittest tests.test_thermal_recovery -v
python3 -m unittest tests.test_recovery_scenarios -v
python3 -m unittest tests.test_thermal_problem_routing -v

# parent regressions
python3 simulator/outcome_benchmark.py
python3 -m unittest tests.test_outcome_benchmark -v
python3 -m unittest tests.test_person_load_family_cases -v
python3 -m unittest tests.test_family_validation_cases -v
```

Expected own gate:

```text
THERM-CAL1 10/10 PASS
```

No local WSL PASS is claimed until the executable gate is run.
