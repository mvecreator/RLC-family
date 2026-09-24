# CAFFEINE1 — timed stimulant burden for SOLO trajectories

CAFFEINE1 separates caffeine from generic `drive_add`.

It is a research feature layer, not a dosing calculator, medical recommendation or causal diagnosis of the observed sleep pattern.

## Why generic forcing was insufficient

The earlier SOLO model represented coffee as a short excitation event.

That loses two important properties:

1. caffeine remains in the body for hours;
2. the same dose can leave very different residual burden at sleep depending on timing.

CAFFEINE1 therefore models an explicit burden state.

## Minimal pharmacokinetic model

For one bolus dose:

```math
C(t)=D\,2^{-t/t_{1/2}}
```

or equivalently:

```math
\dot C=-\frac{\ln2}{t_{1/2}}C.
```

Default reference:

```text
half_life_hours = 5.0
reference_dose_mg = 100
```

The half-life is configurable.

The default is only a central reference. Adult caffeine half-life varies substantially between people and circumstances.

## Reference sensitivity

With a 100 mg modeling dose and 5 h half-life:

```text
10 h before sleep -> 25.0 mg equivalent remains
 6 h before sleep -> 43.53 mg equivalent remains
 3 h before sleep -> 65.98 mg equivalent remains
```

The model does **not** convert these values directly into minutes of sleep lost.

That mapping must be learned/tested separately.

## Personal-history boundary

Known qualitatively:

```text
historical: roughly 1-2 coffees/day
current:    up to 3-4 coffees/week
```

Not known:

```text
actual caffeine mg per cup
exact timing relative to each sleep episode
individual caffeine half-life
```

Therefore the personal history is currently a sensitivity analysis, not identified pharmacokinetics.

## Sleep trajectory refinement

The observed qualitative sequence is now:

```text
MONOPHASIC_BASELINE
    ->
SPLIT_EMERGING
    ->
BIPHASIC_MATURE
    ->
SECONDARY_BOUT_RESOLVING
    ->
MONOPHASIC_RECOVERED
```

At the mature biphasic stage:

```text
sleep bout A ≈ sleep bout B
wake gap ≈ 2-3 h
```

Later:

```text
secondary bout weight decreases
secondary temporal separation/stretch increases
secondary bout eventually disappears
```

Because the exact late gap is not known, the model stores:

```text
secondary_temporal_stretch_index ∈ [0,1]
```

instead of inventing final hours.

## Causality boundary

CAFFEINE1 explicitly does **not** assert:

```text
caffeine caused the 25 h cycle
caffeine caused the split
reducing coffee caused the second bout to disappear
```

Those are hypotheses for OUTCOME-BLIND1.

## Executable gate

```bash
python3 simulator/caffeine_calibration.py
python3 -m unittest tests.test_caffeine_calibration -v
python3 -m unittest tests.test_person_solo_calibration -v
```

Expected:

```text
CAFFEINE1 8/8 checks PASS
```

## Evidence basis for the reference model

Published adult pharmacokinetic sources commonly place caffeine half-life on the order of several hours, with substantial person-to-person variability.

A controlled sleep study found measurable sleep disruption from a large 400 mg caffeine dose even when taken 6 hours before habitual bedtime.

These findings justify including dose/timing/residual burden as model inputs; they do not identify the effect size for this user's history.

## Next gate

```text
OUTCOME-BLIND1
```

The blind evaluator should hide future windows and ask whether prefix-only features predict:

- recovery vs accumulation;
- which person loads first;
- which relationship link strains first;
- whether sleep split strengthens, persists or resolves;
- whether caffeine burden adds signal beyond generic forcing.
