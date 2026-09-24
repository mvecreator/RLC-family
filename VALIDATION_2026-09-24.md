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