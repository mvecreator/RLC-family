# OUTCOME-BLIND1 — prefix-only predictive validation

OUTCOME-BLIND1 is the first gate whose primary purpose is **not** to add another mechanism.

Its job is to test whether the current model carries predictive signal when the future is hidden.

## Core rule

The predictor receives only:

```text
history <= cutoff
```

The evaluator separately owns:

```text
cutoff < hidden future <= horizon
```

Prediction is created before the hidden suffix is passed to evaluation.

A change to the hidden suffix must not change the prediction.

## What is predicted

For every person:

```text
ACCUMULATING
RECOVERING
STABLE
```

using `accumulated_load`.

For every relationship link:

```text
ACCUMULATING
RECOVERING
STABLE
```

using `accumulated_strain`.

The model also predicts, when applicable:

- first person to cross `RECOVERY_ATTENTION = 0.35`;
- first link to cross `RELATIONSHIP_REPAIR_REVIEW = 0.50`.

## Prefix-only model projection

At cutoff, the predictor uses only:

- current accumulated state;
- recent mean combined load from the prefix;
- the already-declared accumulator equation.

Person projection:

```math
\dot s = 0.45L(1-s)-0.14s.
```

Link projection:

```math
\dot r = 0.50L(1-r)-0.10r.
```

The future forcing/events are unknown to the predictor.

That is deliberate.

If a hidden future repair event reverses the trajectory, the predictor may fail.

The evaluator must report that failure rather than reinterpret the future.

## Baseline

Every case is scored against a trivial persistence baseline:

```text
future direction = STABLE
```

The project does not earn predictive-value claims merely by having a non-zero score.

A useful model must eventually outperform simple baselines on genuinely held-out records.

## Synthetic blindness gate

`simulator/outcome_blind_calibration.py` contains three synthetic cases:

1. load continues -> accumulation should be predicted;
2. already-loaded system with low ongoing load -> recovery should be predicted;
3. prefix looks like continued accumulation, but hidden future load reverses -> model should honestly miss.

The third case is important.

A calibration suite that requires every hidden future to be predicted correctly is not a blind test; it is a disguised self-fulfilling test.

Expected mechanics gate:

```text
OB01..OB08 = 8/8 PASS
```

This means the blindness/scoring machinery works.

It does **not** mean real-world predictive validity is established.

## Family blind cases

`examples/outcome_blind_family_cases.json` defines initial model-generated windows:

- continued partner stress;
- critical partner accumulation;
- a repair event hidden just after cutoff;
- a short ordinary family history.

Run:

```bash
python3 simulator/outcome_blind_family_runner.py --json
```

The runner reports:

- person direction accuracy;
- link direction accuracy;
- first-person localization;
- first-link localization;
- persistence-baseline accuracy.

These cases are useful regressions, but still use model-generated futures.

## SOLO sleep outcome

The refined observed qualitative history is:

```text
MONOPHASIC_BASELINE
-> SPLIT_EMERGING
-> BIPHASIC_MATURE
-> SECONDARY_BOUT_RESOLVING
-> MONOPHASIC_RECOVERED
```

A blind cutoff inside `BIPHASIC_MATURE` exposes a useful current limitation.

The recent secondary-bout trajectory is flat:

```text
secondary_bout_weight ≈ 1
```

so a prefix-only local trend predicts:

```text
STABLE
```

but the hidden qualitative future is:

```text
DECREASING
-> secondary bout disappears
```

This expected miss is retained as a regression result.

It tells us that the mature biphasic prefix by itself does not contain enough information to infer the later resolution.

## CAFFEINE1 and the personal sleep history

CAFFEINE1 can become a predictor feature only when its inputs are actually identified.

Current historical facts:

```text
frequency: approximately 1-2 coffees/day
later/current frequency: up to 3-4 coffees/week
```

Current missing values:

```text
mg per historical cup
exact time of each dose relative to sleep
personal caffeine half-life
dated transition points of the sleep stages
```

Therefore OUTCOME-BLIND1 explicitly refuses to fabricate a personal caffeine feature from the 100 mg reference sensitivity convention.

The current personal sleep blind result should remain:

```text
caffeine_feature_usable_without_assumption = false
```

until better data exist.

## Prospective data

For real predictive testing, the preferred next dataset is a dated log in which the future can genuinely be hidden.

Useful observations include:

### Per person

- direct workload / major forcing events;
- sleep timing and fragmentation;
- recovery/rest windows;
- caffeine event time and estimated/known dose if available;
- accumulated-load outcome.

### Per relationship link

- communication quality;
- contact frequency;
- availability;
- hostility;
- notable repair/conflict events;
- resulting strain trajectory.

### Shared family state

- financial pressure;
- major external events.

## Scientific acceptance rule

OUTCOME-BLIND1 itself does not define a flattering score threshold.

A future predictive claim should require at least:

1. preregistered cutoff/horizon rules;
2. genuinely held-out future windows;
3. comparison with persistence and simple trend baselines;
4. per-person and per-link metrics;
5. failure cases retained;
6. no parameter tuning on the hidden suffix;
7. preferably multiple independent histories, not one family narrative.

Only after that should the project claim predictive value rather than internal consistency.

## Executable gate

```bash
python3 simulator/outcome_blind_calibration.py
python3 -m unittest tests.test_outcome_blind -v

python3 simulator/outcome_blind_family_runner.py --json
python3 -m unittest tests.test_outcome_blind_integration -v
```

Parent regressions should also remain green:

```bash
python3 simulator/caffeine_calibration.py
python3 simulator/person_load_calibration.py
python3 simulator/link_semantic_calibration.py
```

## Gate interpretation

A future result such as:

```text
model person-direction accuracy > persistence baseline
model link-direction accuracy > persistence baseline
localization accuracy > baseline
```

would be interesting.

But the strongest evidence would come from repeating that advantage on records not used to choose the model coefficients.


## Stronger baseline: linear trend

OUTCOME-BENCH1 adds a second baseline beyond persistence.

`linear_trend_baseline` fits the recent slope of the accumulated person/link state using prefix data only and extrapolates it across the horizon.

This prevents a weak persistence baseline from making the mechanistic projection look artificially strong.

The benchmark and family runner now report all three predictors:

```text
RLC projection
persistence
linear trend
```

See [OUTCOME-BENCH1](OUTCOME_BENCH1.md).
