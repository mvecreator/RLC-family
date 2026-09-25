# RLC-family validation pack — 2026-09-24

## Scope

This pass checks PERSON2 / PERSON-TIME2, PERSON-SOLO1 / PERSON-SAFETY1, and PERSON-FAMILY-SAFETY1.
The result is internal/directional validation only. Normalized RLC variables are not validated measurements of people.

## 1. PERSON-TIME2 canonical gates

| Gate | Result | Key value |
|---|---|---|
| PTCAL01 equilibrium | PASS | max spontaneous voltage = 0 |
| PTCAL02 locality | PASS | target ≈ 0.08193; receiver ≈ 0.01804 |
| PTCAL03 transmission | PASS | receiver ≈ 0.00997 at q=0.20; ≈ 0.02687 at q=0.90 |
| PTCAL04 memory locality | PASS | target memory 0.40; receiver 0.20 |
| PTCAL05 temporary link | PASS | q=0.10 during; q=0.80 after |
| PTCAL06 financial negative control | PASS | reserve delta 1000; memory delta 0 |
| PTCAL07 financial background | PASS | stress 0 -> ≈0.521 and higher final memory |
| PTCAL08 replay | PASS | deterministic |

The base targeted network dynamics are internally coherent.

## 2. Directed family-safety scenarios

| Scenario | Highest link | Peak strain | Repair review | Breakdown review | Final strain |
|---|---|---:|---|---|---:|
| Calm baseline | son↔wife | 0.182 | no | no | 0.160 |
| High interaction, good channels | husband↔son | 0.402 | no | no | 0.353 |
| Short conflict + repair | husband↔wife | 0.331 | no | no | 0.176 |
| Persistent degraded partner channel | husband↔wife | 0.590 | day ≈6.4 | no | 0.353 after repair |
| Financial stress only | son↔wife | 0.368 | no | no | 0.368 |
| Isolated father–son conflict | husband↔son | 0.585 | day ≈5.8 | no | 0.341 after repair |
| Critical partner scenario | husband↔wife | 0.679 | day ≈3.1 | day ≈7.4 | 0.550 after stress ends |
| Very low communication, no events | husband↔wife | 0.581 | day ≈6.4 | no | 0.580 |

Negative controls behave as intended: calm systems do not self-trigger; high current on a good channel is not automatically conflict; financial pressure does not masquerade as breakdown; parent–child strain remains localized; a short conflict followed by repair decays strongly.

The original 20-day stressed-partner example reaches only about 0.59. It is a repair-review case, not a valid fixture for the 0.65 breakdown threshold. A separate critical scenario is now used.

## 3. Example trajectories

Short conflict + repair, husband↔wife strain:
- day 0: 0.150
- day 2: 0.173
- day 4: 0.330
- day 7: 0.279
- day 14: 0.206
- day 30: 0.176

Critical partner trajectory:
- day 0: 0.150
- day 1: 0.276
- day 3: 0.493
- day 7: 0.645
- day 14: 0.679
- day 21: 0.670
- day 28: 0.661
- day 35: 0.550

Isolated father–son trajectory:
- day 0: 0.150
- day 3: 0.370
- day 6: 0.507
- day 12: 0.580
- day 19: 0.583
- day 25: 0.422
- day 30: 0.341

## 4. Ensemble calibration

A deterministic ensemble check used 60 calm two-adult systems and 60 prolonged-stress systems.

Calm ensemble:
- N = 60
- mean peak strain ≈ 0.216
- median ≈ 0.207
- 90th percentile ≈ 0.286
- repair review = 0/60
- breakdown review = 0/60

Prolonged-stress ensemble:
- N = 60
- mean peak strain ≈ 0.640
- median ≈ 0.639
- 90th percentile ≈ 0.663
- repair review = 60/60
- breakdown review = 19/60 ≈ 31.7%

This is useful separation: 0.50 catches sustained stress broadly, while 0.65 reserves breakdown-review for the severe tail.

## 5. SOLO safety calibration

For the canonical 25-hour phase drift plus progressive biphasic sleep observation set:
- phase contribution = 0.125
- sleep-fragmentation contribution = 0.135
- financial contribution ≈ 0.056
- historical forcing contribution ≈ 0.173

Historical forcing:
- combined daily load ≈ 0.489
- stress day 7 ≈ 0.510
- stress day 14 ≈ 0.546
- stress day 30 ≈ 0.550

Current sparse-coffee forcing:
- combined daily load ≈ 0.481
- stress day 7 ≈ 0.506
- stress day 14 ≈ 0.541
- stress day 30 ≈ 0.546

The difference is small because generic project forcing dominates the event-drive area.

## 6. Limitations found

### L1 — caffeine is too generic
Coffee is currently another drive_add event. The model lacks half-life, dose, timing relative to sleep, nonlinear sleep disruption, and a circadian phase-response curve. It must not estimate how much coffee reduction changes sleep risk.

### L2 — link quality carries two meanings
A very low link quality (q≈0.10) can accumulate strain to about 0.58 even without interaction events. This is reasonable if quality means persistent inability to communicate, but can be a false positive if it merely means low contact frequency, travel, or shift work.
Future schema should split communication_quality, contact_frequency, hostility/conflict, and availability.

### L3 — family person-load thresholds are conservative
Several substantial relationship-stress scenarios push link strain above 0.50 while individual person_load remains below the current 0.45 self-monitor threshold. These thresholds need separate calibration.

### L4 — GP 14-day signal is a guardrail, not evidence
The SOLO medical-care ladder uses a conservative 14-day review guardrail for persistent unusual sleep. It is not an empirically fitted medical threshold.

### L5 — no external predictive validation yet
The justified claim is internal consistency across directed synthetic/calibration cases. The project cannot yet claim prediction of divorce, psychiatric illness, compatibility, or calibrated failure probabilities.

## 7. Project assessment

Strongest parts:
1. PERSON2 makes each person a real mixed RLC node.
2. PERSON-TIME2 has good locality, deterministic replay, and negative controls.
3. Link strain is better than treating current magnitude as conflict.
4. External financial pressure is separated from relationship deterioration.
5. Recovery is explicit; warnings are not treated as destiny.
6. Medical and relationship safety overrides are separated from numeric RLC scores.

Weakest parts:
1. coefficient/threshold calibration is still synthetic;
2. forcing semantics are too coarse;
3. sleep/caffeine dynamics are not physiological;
4. relationship-link semantics need decomposition;
5. no longitudinal external dataset has been used.

## 8. Recommended next gates

1. VALID-CAL1 — freeze the directed scenario suite as regression tests.
2. LINK-SEM1 — split communication quality / contact / hostility / availability.
3. PERSON-LOAD-CAL1 — calibrate individual-load thresholds separately from link strain.
4. CAFFEINE1 — optional stimulant state with dose, half-life and timing, without turning it into a medical predictor.
5. OUTCOME-BLIND1 — only later, test on blinded longitudinal synthetic or consented/anonymized records with future windows hidden.

The next scientific milestone is not another feature. It is calibration against held-out trajectories.

## 9. OUTCOME-BLIND1

The next validation layer is now implemented as a prefix-only blind evaluator.

It reports:

- person direction: ACCUMULATING / RECOVERING / STABLE;
- link direction: ACCUMULATING / RECOVERING / STABLE;
- first person to cross the recovery-attention threshold;
- first link to cross the repair-review threshold;
- persistence-baseline scores.

A strong no-leakage regression mutates only the hidden suffix and requires the prediction object to remain identical.

A hidden-reversal case is intentionally retained as an expected model miss.

The refined SOLO sleep trajectory currently provides an informative negative result: a cutoff inside the mature biphasic phase predicts STABLE from recent trend, while the hidden qualitative future contains disappearance of the secondary sleep bout. Because historical caffeine dose/timing are not identified, CAFFEINE1 assumptions are not allowed to rescue this prediction.

This establishes the evaluation machinery but does not establish external predictive validity.


## 10. OUTCOME-BENCH1

A first fixed blind benchmark corpus is now defined.

Reference synthetic results:

```text
person direction
  RLC projection     26/34 = 76.47%
  persistence        15/34 = 44.12%
  linear trend       17/34 = 50.00%

link direction
  RLC projection     26/34 = 76.47%
  persistence        14/34 = 41.18%
  linear trend       17/34 = 50.00%

first-crossing localization
  RLC projection      2/4  = 50%
  persistence         0/4  = 0%
  linear trend        2/4  = 50%
```

The aggregate advantage is mostly a continuation-regime result.

For hidden future regime changes:

```text
hidden shifts:   RLC 0/4
trend reversals: RLC 0/2
```

Therefore the current model should be described as a conditional dynamic continuation predictor, not a predictor of unobserved future shocks.

The benchmark also found and fixed a localization evaluator mismatch: already-crossed entities are now excluded from "first future crossing" predictions, matching the hidden-suffix evaluator contract.

These are synthetic results and do not establish external predictive validity.


## 11. HISTORY-DATA1

A provenance gate now separates retrospective reconstruction from prospective blind-validation candidates.

The current personal SOLO sleep/caffeine history is retained as a useful retrospective hypothesis record, but is explicitly ineligible for a blind accuracy score because:

- the outcome trajectory is already known;
- exact dates are not available;
- historical caffeine dose and timing are unknown;
- no model/cutoff/horizon was preregistered before the outcome.

A synthetic prospective demo is included to exercise the correct contract:

```text
model SHA frozen
cutoff frozen
horizon frozen
observations recorded contemporaneously
prefix available to predictor
hidden suffix withheld until evaluation
```

This closes a major methodological loophole: known anecdotes can no longer inflate out-of-sample evidence.


## 12. THERMAL-RECOVERY1

A thermal-memory layer is now implemented over the calibrated person/link dynamics.

Key additions:

```text
PERSON-THERM1
LINK-THERM1
RECOVERY-DEBT1
RECOVERY-SCENARIO1
```

Relationship heating uses the executable electrical dissipation proxy:

```math
P_{pq}=I_{pq}^2R_{pq}.
```

This separates high interaction through a good channel from high interaction through a high-resistance channel.

A slow damage state accumulates only when link heat remains above the engineering overheat threshold.

For people, PERSON-LOAD1 combined load is used as the heat-input proxy and existing recovery inertia defines baseline cooling capacity.

Recovery scenarios compare declared mechanism bundles. They do not assert that a holiday, mountain trip, or other destination has a validated causal effect.

The own executable calibration is THERM-CAL1 with 10 directional gates.

No external clinical or relationship-outcome validation is claimed.


## 13. LINK-SEMI1

The relationship graph now supports nonlinear directed/gated link hypotheses:

```text
RESISTIVE
DIODE
MOSFET
BREAKDOWN_DIODE
```

Legacy links remain RESISTIVE.

The first mixed example uses:

```text
employer -> employee : MOSFET
employee <-> coworker: RESISTIVE
friend -> employee   : DIODE
```

The social label does not determine the element automatically; the element encodes an explicitly declared structural hypothesis.

The MOSFET gate is an external/institutional channel factor, not a personality score.

PERSON-NET1 rejects nonlinear links because its frequency-domain matrix is linear. PERSON-TIME2 executes the nonlinear currents directly.

LINK-THERM1 now uses the universal dissipation proxy:

```math
P=|\Delta V I|
```

which reduces exactly to `I^2R` for RESISTIVE links.

LINK-SEMI-CAL1 contains 10 directional/backward-compatibility gates.

A current limitation remains: PERSON2 permits one link branch per pair. Explicit parallel personal/institutional branches are deferred to MULTI-LINK1.


## 14. MULTI-LINK1

PERSON2 now supports multiple explicit relationship branches between the same pair of people.

Key invariants:

```text
legacy one-link scenarios retain old a->b identity
parallel branches require explicit unique link_id
pair-only event targeting is rejected when ambiguous
target_link_id mutates exactly one branch
all branch currents contribute to the endpoint node equations
branch strain and thermal state remain independent
pair-level current/dissipation aggregates are also reported
```

The first canonical example is:

```text
R_personal || MOSFET_work
```

between employer and employee.

Incident person load no longer averages across parallel branches. It uses the bounded monotone union `1-prod(1-x_b)`, preserving the single-link value while preventing dilution when new channels are added.

MULTI-LINK-CAL1 defines 12 compatibility/mechanics gates.

External social interpretation remains unvalidated; this gate establishes multigraph execution semantics only.


## 15. CHANNEL-COUPLING1

Explicit branch-to-branch modulation is implemented on top of MULTI-LINK1.

Current source signals:

```text
current_abs
power = |deltaV * I|
conductance
communication_quality
effective_transmission
hostility
gate
```

Current target fields:

```text
communication_quality
contact_frequency
availability
hostility
gate
reverse_ratio
```

All source signals are frozen before any target modification at that solver instant, so reciprocal rules are deterministic and order-independent.

Same-pair coupling is allowed by default. Cross-pair coupling requires `allow_cross_pair=true`.

PERSON-NET1 rejects all coupled-channel scenarios; PERSON-TIME2 is authoritative.

The first example declares:

```text
work power -> personal communication quality
personal communication quality -> work reverse_ratio
```

as explicit hypotheses.

CHANNEL-COUPLING-CAL1 defines 15 mechanics/provenance gates.

Accumulated LINK-THERM heat/damage are not yet feedback sources; THERMAL-FEEDBACK1 is deferred.


## 16. NEIGHBOR-NET1

A household-aware small-network signal layer is implemented above PERSON-TIME2.

Canonical topologies:

```text
three solo neighbor nodes

and

household1: solo
household2: couple + adult son
household3: couple
```

Observed events may target an explicit member or an entire household.

Household-level amplitude is normalized across members so a larger household does not receive a larger injected input merely because it has more nodes.

The model distinguishes:
- household_internal links;
- cross_household_social links;
- environmental_observation links toward the central node.

Equal-input household probes compare central waveform response for different household topologies while preserving total amplitude and exposure.

Separate counterfactuals remove household-internal links and cross-household links without changing event history.

Pre/post intervention analysis separates:
- declared central relief;
- observed change in event regime;
- continued-prepattern counterfactual;
- desynchronized timing counterfactual.

Temporal alignment is a signal statistic only. `intent_inferred=false` is explicit.

NEIGHBOR-NET-CAL1 defines 20 mechanics/accounting/causal-boundary gates.

Explicit mutual inductance is deferred until it demonstrates value beyond this ordinary-network baseline.


## 17. PERCEPTION-ID1

A brief-observation RLC identifiability benchmark is implemented.

The layer separates:

```text
actual theta = (R,C,L)
observer-selected theta_hat
```

from the same synthetic target trace.

The canonical synthetic target is deliberately:
- lower C than adult nominal;
- higher R than adult nominal;
- higher L than adult nominal.

With a short observation window and explicit noise floor, many R/L candidates remain compatible while C is much more constrained.

Two different priors select different apparent models from the same brief trace:
- low-R/L prior underestimates persistence;
- high-R/L prior overestimates persistence.

The benchmark then compares residual-state prediction and repeated-input response.

Longer observation collapses the candidate set.

PERCEPTION-ID-CAL1 defines 14 gates.

The output explicitly sets:

```text
synthetic_ground_truth_known = true
real_world_belief_inference = false
```

so identifiability analysis cannot be confused with a claim about the thoughts or motives of real people.


## 18. RHYTHM-25H1

PERSON2 now supports an explicit intrinsic-day period per person.

Canonical reference:
- central = 25h;
- comparison neighbors = 24h;
- external schedule = 24h.

The exact relative drift for 25h vs 24h is about -0.96 external-clock hours per external day, with modulo-phase realignment after 25 external days.

A free-running 25h profile has zero schedule-mismatch load.

Only explicit `schedule_lock` converts phase mismatch into memory-load and recovery-inertia effects.

Person-specific initial conditions are independently supported:
- initial_accumulated_load;
- initial_heat;
- initial_recovery_debt.

The canonical 25h example gives neighboring 24h nodes higher initial states under the label `unknown_prior_state_hypothesis`, without attributing those states to smoking, alcohol, or any other cause.

RHYTHM-25H-CAL1 defines 15 mechanics/backward-compatibility gates.
