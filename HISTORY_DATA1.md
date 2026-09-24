# HISTORY-DATA1 — provenance for real blind validation

HISTORY-DATA1 separates two very different evidence classes:

```text
retrospective reconstruction
vs
prospective blind-validation candidate
```

This distinction is required before OUTCOME-BLIND1 can support any claim about predictive value.

## Why this layer exists

A known historical story can still be useful.

It can help:

- define model variables;
- discover missing states;
- generate hypotheses;
- build qualitative trajectories;
- create sensitivity analyses.

But if the future outcome was already known when the history was reconstructed, it must not be counted as out-of-sample predictive evidence.

## Blind-eligibility requirements

A record is a candidate for blind validation only if all of the following hold:

1. `collection_mode = prospective`;
2. the future outcome was not already known when the record was logged;
3. no feature is derived from the future suffix;
4. a real time axis exists;
5. model SHA, cutoff and horizon are frozen before outcome evaluation;
6. observations are recorded contemporaneously;
7. both a prefix and a hidden suffix exist.

The checker returns:

```text
blind_out_of_sample_candidate
retrospective_hypothesis_record
not_blind_eligible
```

## Retrospective SOLO history

The current personal sleep/caffeine history is stored as:

```text
examples/history_solo_retrospective_sleep.json
```

It records the qualitative order:

```text
monophasic baseline
-> ~25 h wake-phase drift
-> gradual split
-> mature biphasic sleep
-> second bout resolves while temporal separation stretches
-> monophasic current state
```

Known qualitative caffeine history:

```text
earlier: roughly 1-2 coffees/day
later/current: up to 3-4 coffees/week
```

Unknown:

```text
exact dates
mg per historical cup
exact timing relative to each sleep episode
exact dates of sleep-stage transitions
total sleep duration per cycle
```

Therefore the record is explicitly allowed for:

- hypothesis generation;
- qualitative sleep trajectory;
- sensitivity analysis.

It is explicitly not allowed for:

- blind accuracy score;
- personal caffeine-effect estimate;
- causal claim.

## Prospective format

A future prospective record should freeze:

```json
{
  "model_ref": "<commit SHA>",
  "cutoff_day": 14,
  "horizon_days": 7,
  "frozen_before_outcome": true
}
```

before the hidden outcome window is evaluated.

Unknown observations remain:

```json
null
```

They must not be filled by model inference and then reused as if observed.

## Contemporaneous recording

Each observation includes:

```text
recorded_contemporaneously = true
```

This protects against reconstructing the prefix after the outcome is already known.

A retrospective reconstruction can still live in the project, but it receives a different evidence class.

## Executable check

```bash
python3 simulator/history_data.py \
  examples/history_solo_retrospective_sleep.json

python3 simulator/history_data.py \
  examples/history_prospective_demo.json

python3 simulator/history_data.py \
  examples/history_prospective_demo.json \
  --split

python3 -m unittest tests.test_history_data -v
```

Expected:

```text
solo retrospective:
  eligible = false
  evidence_class = retrospective_hypothesis_record

synthetic prospective demo:
  eligible = true
  evidence_class = blind_out_of_sample_candidate
```

## Scientific boundary

HISTORY-DATA1 checks provenance and no-lookahead eligibility.

It does not establish that:

- observations are accurate;
- model variables are valid measurements;
- RLC coefficients are correct;
- the model predicts real outcomes.

Those questions are answered only by later blind scoring across independent records.

## Next evidence step

After HISTORY-DATA1, the research sequence is:

```text
freeze model coefficients
-> preregister cutoff/horizon
-> collect prospective histories
-> freeze prefix
-> predict
-> reveal hidden suffix
-> OUTCOME-BLIND1 score
-> compare with persistence + linear trend
```

At that point the project can begin accumulating genuine out-of-sample evidence.
