# LINK-SEM1 calibration note

## Purpose

LINK-SEM1 removes the ambiguity found by the 2026-09-24 validation pass:

```text
low quality
```

previously mixed:

- poor communication;
- low contact frequency;
- low practical availability;
- hostility.

The gate must preserve legacy transport while separating those meanings for new scenarios.

## Reference calculations

### Legacy compatibility

Input:

```json
{"quality":0.20}
```

Compiled:

```text
communication_quality = 0.20
contact_frequency     = 1.00
availability          = 1.00
hostility             = 0.80
effective_transmission= 0.20
R_link                = 2.03
```

Because:

```math
R=0.15+2.35(1-0.20)=2.03.
```

The family-safety friction is also unchanged:

```math
0.65(1-q)+0.35(1-q)=1-q.
```

Therefore old scenarios keep the previous transport and stress semantics.

### Rare but good contact

Input:

```text
communication_quality = 0.95
contact_frequency     = 0.10
availability          = 0.80
hostility             = 0.02
```

Derived:

```text
effective_transmission ≈ 0.2687006
R_link                 ≈ 1.8685536
relational_friction    ≈ 0.0395
reference instantaneous strain ≈ 0.19475
```

The transport is weak because the channel is rarely available, but the relationship friction remains low.

### Frequent hostile contact

Input:

```text
communication_quality = 0.95
contact_frequency     = 1.00
availability          = 1.00
hostility             = 0.90
```

Derived:

```text
effective_transmission = 0.95
R_link                 = 0.2675
relational_friction    ≈ 0.3475
reference instantaneous strain ≈ 0.34875
```

This case has strong transport and substantially higher relational strain.

## Dynamic availability example

Baseline:

```text
communication_quality = 0.90
contact_frequency     = 1.00
availability          = 1.00
hostility             = 0.05
T_before              = 0.90
```

A temporary event:

```json
{
  "связь":["a","b"],
  "availability_set":0.10
}
```

gives:

```text
T_after ≈ 0.284605
```

while communication quality and hostility remain unchanged.

That is the intended meaning of temporary absence/travel/shift-work.

## Executable gate

Run:

```bash
python3 simulator/link_semantic_calibration.py
python3 -m unittest tests.test_link_semantics -v
python3 -m unittest tests.test_link_semantic_events -v
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_family_validation_cases -v
```

Expected LINK-SEM-CAL:

```text
6/6 checks PASS
```

The final two test suites are regression checks: legacy PERSON-TIME and family-safety behavior should remain unchanged.

## Current verification status

The code and formulas were statically checked in the development session.

A full local Python execution could not be performed in the assistant container because DNS access to `github.com` is unavailable there.

Therefore this note records expected/calculated values, not a claimed founder/local unittest PASS.

## Gate decision

LINK-SEM1 is constructively specified and implemented.

Merge should require the executable WSL gate above.

After PASS, the next research gate is:

```text
PERSON-LOAD-CAL1
```

whose job is to calibrate person-level accumulated-load thresholds separately from relationship-link strain.
