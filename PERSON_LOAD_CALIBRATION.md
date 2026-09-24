# PERSON-LOAD-CAL1 — calibrated load for each family member

PERSON-LOAD-CAL1 calibrates the slow accumulated-load state of every PERSON2 node.

It is an internal engineering layer, not a clinical stress scale and not a psychological diagnosis.

## Why this gate was needed

The first family-safety implementation tracked:

```text
excitation
memory
incident_link_stress
financial_stress
```

but used only instantaneous node voltage for local excitation.

That misses an important RLC case:

> a sustained source can be carried increasingly by the inductor branch while node voltage falls back toward equilibrium.

Therefore a person can remain under direct demand even when transient `v_p(t)` is small.

PERSON-LOAD-CAL1 adds:

```text
forcing_exposure
```

from the addressable PERSON-TIME2 `event_drive`.

## Instantaneous combined load

Current synthetic weights:

```math
L_p =
0.20 E_p
+0.25 M_p
+0.15 R_p
+0.15 F_p
+0.25 U_p
```

where:

- `E_p` = normalized transient excitation;
- `M_p` = person memory;
- `R_p` = incident relationship/link stress;
- `F_p` = shared financial stress;
- `U_p` = sustained direct forcing exposure.

The forcing normalization is currently:

```text
forcing_scale = 0.35
```

This is a calibration convention, not an empirical human unit.

## Accumulation

The slow state remains:

```math
s_{t+dt}
=
s_t
+
dt * 0.45 L_t(1-s_t)
-
dt * 0.14 s_t.
```

For constant load:

```math
s_* =
\frac{0.45L}{0.45L+0.14}.
```

Reference equilibria:

| constant combined load | equilibrium accumulated load |
|---:|---:|
| 0.10 | 0.243 |
| 0.30 | 0.491 |
| 0.50 | 0.616 |
| 0.75 | 0.707 |

## Calibrated bands

```text
STABLE
  s < 0.35

RECOVERY_ATTENTION
  s >= 0.35

SUSTAINED_LOAD_REVIEW
  s >= 0.50 continuously for about 5 days

HIGH_LOAD_REVIEW
  s >= 0.65 continuously for about 3 days
```

The dwell rule is important.

A short strong event may temporarily cross 0.50 and still recover quickly. It should not be labeled chronic merely because of a peak.

## Synthetic calibration profiles

Expected reference behavior:

| profile | peak/final behavior | band |
|---|---|---|
| 30 d at load 0.10 | settles near 0.243 | STABLE |
| 3 d at 0.65 then recovery | peak ≈0.593, final ≈0.246 | RECOVERY_ATTENTION |
| 30 d at 0.30 | settles near 0.491 | RECOVERY_ATTENTION |
| 30 d at 0.50 | settles near 0.616 | SUSTAINED_LOAD_REVIEW |
| 30 d at 0.75 | settles near 0.707 | HIGH_LOAD_REVIEW |

A separate forcing-only case checks that sustained direct demand becomes visible even when transient excitation is small.

## Applying the result to each family member

PERSON-FAMILY-SAFETY1 now returns for every PERSON2 node:

```text
kind
age
band
peak_load
final_load
first_recovery_attention_day
first_sustained_load_review_day
first_high_load_review_day
mean_components
peak_components
dominant_mean_component
recommendations
```

A convenience report is available:

```bash
python3 simulator/family_member_load_report.py \
  examples/person_family_scenario.json \
  examples/person_family_timeline.json \
  --out out/member-loads
```

## Adult vs child recommendations

The numeric accumulation is the same model state.

The language/action boundary differs.

Adults may receive:

```text
RECOVERY_ATTENTION
SUSTAINED_LOAD_REVIEW
HIGH_LOAD_REVIEW
```

Children use caregiver-facing actions:

```text
CAREGIVER_RECOVERY_ATTENTION
CAREGIVER_LOAD_REVIEW
CAREGIVER_HIGH_LOAD_REVIEW
```

The model must not place responsibility for correcting family load on the child.

## First family reference applications

These are reference calculations from the current equations and should be confirmed by the executable WSL gate.

### Canonical 7-day family timeline

Approximate peak accumulated load:

| member | peak | expected band |
|---|---:|---|
| husband | 0.229 | STABLE |
| wife | 0.238 | STABLE |
| son | 0.232 | STABLE |
| daughter | 0.200 | STABLE |

A work call and one father-son conflict do not create chronic-person warnings.

### 20-day partner-load scenario

Approximate peaks:

| member | peak | expected band |
|---|---:|---|
| husband | 0.500 | RECOVERY_ATTENTION |
| wife | 0.495 | RECOVERY_ATTENTION |
| son | 0.221 | STABLE |
| daughter | 0.224 | STABLE |

The relationship itself may require repair while the children remain outside the person-load warning bands.

### Critical partner scenario

Approximate peaks:

| member | peak | expected band |
|---|---:|---|
| husband | 0.577 | SUSTAINED_LOAD_REVIEW |
| wife | 0.448 | RECOVERY_ATTENTION |
| son | 0.337 | STABLE |
| daughter | 0.336 | STABLE |

This demonstrates asymmetric load despite a shared relationship crisis.

### Localized son-load scenario

With sustained direct forcing on the son plus a degraded father-son link:

```text
son peak ≈ 0.500 -> RECOVERY_ATTENTION
husband peak ≈ 0.212 -> STABLE
wife peak ≈ 0.213 -> STABLE
daughter peak ≈ 0.213 -> STABLE
```

The load remains localized instead of being copied to every family member.

## Recommendations by dominant cause

The member summary can distinguish:

```text
forcing_exposure
financial_stress
incident_link_stress
memory
excitation
```

and attach cause-specific actions before the generic band action.

Examples:

- direct forcing -> reduce/redistribute avoidable demands;
- financial stress -> treat finances as shared external load;
- incident link stress -> protect lower-conflict interaction around this person;
- memory -> protect recovery before replaying the stressor;
- transient excitation -> reduce additional stimulation during recovery.

## Gates

```text
PLCAL01 calm profile stays STABLE
PLCAL02 short strong stress is not classified as chronic
PLCAL03 moderate sustained load raises recovery attention only
PLCAL04 high sustained load becomes SUSTAINED_LOAD_REVIEW
PLCAL05 severe sustained load becomes HIGH_LOAD_REVIEW
PLCAL06 child review uses caregiver-facing language
PLCAL07 thresholds are ordered
PLCAL08 equilibrium mapping is monotone
PLCAL09 direct forcing remains visible even after voltage adaptation
PLCAL10 every family member receives its own calibrated summary
PLCAL11 targeted child forcing remains localized
```

## Boundary

The thresholds, weights and dwell durations are still synthetic calibration conventions.

The next scientific stage must not treat them as validated human cut-offs.

They are useful if they preserve directional properties and survive later blind trajectory tests.

## Next gate

After PERSON-LOAD-CAL1 executable PASS, the planned sequence is:

```text
CAFFEINE1
-> OUTCOME-BLIND1
```

CAFFEINE1 should remain optional and separated from generic person load because stimulant timing/dose needs its own dynamics.


## Executable verification

Run after LINK-SEM1 passes:

```bash
python3 simulator/person_load_calibration.py

python3 -m unittest tests.test_person_load_calibration -v
python3 -m unittest tests.test_family_member_load_report -v
python3 -m unittest tests.test_person_load_family_cases -v

# parent-gate regressions
python3 simulator/link_semantic_calibration.py
python3 -m unittest tests.test_link_semantics -v
python3 -m unittest tests.test_link_semantic_events -v
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_family_validation_cases -v
```

Expected PERSON-LOAD-CAL1 executable gate:

```text
PLCAL01..PLCAL09 = 9/9 PASS
family member report tests = PASS
family member scenario tests = PASS
LINK-SEM1 parent gate remains PASS
PERSON-TIME-CAL parent gate remains PASS
```

The assistant development container cannot perform the repository checkout because DNS access to `github.com` is unavailable there. Therefore no local unittest PASS is claimed until the WSL run is supplied.
