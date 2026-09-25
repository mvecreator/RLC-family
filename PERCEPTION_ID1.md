# PERCEPTION-ID1 — brief-observation parameter identification

PERCEPTION-ID1 studies a narrow question:

> What can a short visible response reveal about another PERSON2 RLC system?

It separates:

```text
actual theta = (R, C, L)
observer-selected theta_hat = (R_hat, C_hat, L_hat)
```

and keeps the identification uncertainty explicit.

It does not infer what any real person believed, intended, noticed, or consciously selected.

## 1. Synthetic ground truth

The first benchmark uses a synthetic adult PERSON2 target with:

```text
C below adult nominal
R above adult nominal
L above adult nominal
```

This deliberately represents the case:

```text
fast visible initial response
+
stronger-than-apparent persistence / inertia
```

The target is synthetic. It is not an estimate of any real individual.

## 2. Brief pulse response

A short probe drives:

```math
C\dot v = u(t) - v/R - i_L
```

```math
L\dot i_L = v.
```

For a sufficiently short pulse, the initial voltage slope is dominated by:

```math
\dot v(0) \approx u/C.
```

Therefore C may become identifiable earlier than R and L.

R and L appear more strongly in the later decay / inertial part of the waveform.

## 3. Grid identifiability

PERCEPTION-ID1 generates a synthetic ground-truth trace and evaluates a grid of candidate:

```text
R
C
L
```

models.

Candidates are retained when their RMSE lies below an explicit observation-noise floor.

The output reports:

```text
candidate_count
R_span
C_span
L_span
```

for:
- a brief observation window;
- a longer observation window.

The first calibration is designed so that the brief window leaves many R/L alternatives while C is much more constrained.

## 4. Prior-dependent apparent model

A short trace may support several nearly indistinguishable RLC models.

PERCEPTION-ID1 therefore allows an observer prior:

```json
{
  "R": 0.9,
  "C": 1.5,
  "L": 1.5
}
```

Among candidates inside the noise floor, the apparent model is the one nearest that prior in log-parameter space.

Thus the same short trace can yield different apparent models under different priors.

Canonical pair:

```text
low-R/L prior
high-R/L prior
```

The actual target remains identical.

This is a demonstration of under-identification, not mind-reading.

## 5. Apparent low C with hidden stronger R/L

The canonical low-prior case demonstrates:

```text
C_hat ≈ C_actual

R_hat < R_actual
L_hat < L_actual
```

That means the short visible response may correctly suggest a relatively small C while still underestimating longer persistence / inertia.

A high-R/L prior can produce the opposite:

```text
R_hat > R_actual
L_hat > L_actual
```

from the same brief trace.

## 6. Strategy-probe

PERCEPTION-ID1 also asks a purely synthetic control question.

For a fixed repeat interval, compute:

```text
perceived residual fraction
actual residual fraction
```

If the perceived model predicts that the response has mostly decayed, it may select:

```text
repeat_short_input_assuming_decay
```

while the actual model still retains substantial state.

The benchmark compares that policy with the policy that would be selected if the true RLC parameters were known.

This is not a claim that any real observer used that policy.

## 7. Repeated-input prediction error

The same repeated input train is simulated under:
- the perceived model;
- the actual model.

The output compares:

```text
predicted_peak_abs_voltage
actual_peak_abs_voltage
```

A low-R/L estimate can underpredict accumulation.

## 8. Canonical examples

Synthetic target:

```text
examples/perception_id1_synthetic_target.json
```

Low-R/L observer prior:

```text
examples/perception_id1_low_prior_spec.json
```

High-R/L observer prior:

```text
examples/perception_id1_high_prior_spec.json
```

## 9. Calibration gates

PERCEPTION-ID-CAL1 defines 14 gates:

```text
PI01 synthetic target is low-C / high-RL versus nominal
PI02 brief window remains ambiguous
PI03 brief window identifies C better than R/L
PI04 long window collapses ambiguity
PI05 low-RL prior underestimates R and L
PI06 high-RL prior overestimates R and L
PI07 same trace supports opposite prior biases
PI08 low prior predicts faster decay than actual
PI09 high prior predicts slower decay than actual
PI10 low prior selects a different repeat policy
PI11 high prior does not share that policy error
PI12 low prior underpredicts repeated-input peak
PI13 output explicitly rejects real-world belief inference
PI14 ground truth is explicitly synthetic
```

## 10. Problem solver route

```json
{
  "type": "perception_identification",
  "perception_spec": {}
}
```

routes to PERCEPTION-ID1.

## 11. Scientific boundary

PERCEPTION-ID1 can demonstrate:

```text
short observations are insufficient to determine R/L uniquely
different priors can select different apparent models
a wrong apparent model can lead to a wrong synthetic interaction policy
```

It cannot demonstrate:

```text
what a real neighbor thought
whether a real person consciously assessed R/C/L
whether a real person selected a strategy toward another person
why a real person later behaved in a particular way
```

Those would require independent behavioral data and a separate prospective validation design.

## 12. Executable gate

```bash
python3 simulator/perception_identification_calibration.py
python3 -m unittest tests.test_perception_identification -v
```

Expected own gate:

```text
PERCEPTION-ID-CAL1 14/14 PASS
```

No founder/local WSL PASS is claimed until executed.
