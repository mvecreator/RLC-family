# RHYTHM-25H1 — per-person intrinsic-day dynamics

RHYTHM-25H1 adds a per-person internal cycle length to PERSON2.

The canonical personal profile is:

~~~text
central:
  intrinsic_day_hours = 25

comparison neighbors:
  intrinsic_day_hours = 24
~~~

This is an engineering timing model. It is not a medical diagnosis and does
not claim that a 25-hour lifestyle is pathological.

## 1. Core separation

The layer distinguishes:

~~~text
intrinsic rhythm
external schedule
initial accumulated state
~~~

These are independent variables.

A 25-hour intrinsic cycle does **not** automatically create load.

Extra model load appears only when:

~~~text
schedule_lock > 0
~~~

meaning the person is constrained by an external schedule whose period differs
from the declared internal cycle.

## 2. Rhythm parameters

Per person:

~~~json
{
  "rhythm": {
    "intrinsic_day_hours": 25.0,
    "schedule_lock": 0.70,
    "mismatch_load_gain": 0.20,
    "recovery_penalty_gain": 0.25,
    "phase_offset_hours": 0.0
  }
}
~~~

Global external schedule:

~~~json
{
  "rhythm_model": {
    "external_day_hours": 24.0
  }
}
~~~

Defaults preserve legacy behavior:

~~~text
intrinsic_day_hours = 24
external_day_hours  = 24
schedule_lock       = 0
~~~

## 3. Relative phase

For model time t days:

~~~math
\phi_{int}(t)
=
\frac{24t + \phi_0}{\tau_{int}}
~~~

~~~math
\phi_{ext}(t)
=
\frac{24t}{\tau_{ext}}
~~~

The relative phase is wrapped to:

~~~math
\Delta\phi \in [-1/2,1/2).
~~~

Mismatch:

~~~math
m(t)
=
\frac12
\left[
1-\cos(2\pi\Delta\phi)
\right].
~~~

Therefore:

~~~text
m = 0  phases aligned
m = 1  half-cycle opposition
~~~

## 4. 25h vs 24h reference drift

For:

~~~text
tau_int = 25 h
tau_ext = 24 h
~~~

the relative phase drift per external day is:

~~~math
24\left(\frac{24}{25}-1\right)
=
-0.96\;h/day.
~~~

So after one external day the internal cycle lags the external schedule by
about 0.96 external-clock hours in this model.

After 25 external days:

~~~text
internal cycles = 24
external cycles = 25
~~~

and the phases realign modulo one cycle.

This periodic realignment is a mathematical beat property of the two periods.

## 5. Free-running 25h mode

If:

~~~text
intrinsic_day_hours = 25
schedule_lock = 0
~~~

then:

~~~math
L_{schedule}(t)=0.
~~~

The internal phase still drifts relative to the external 24-hour clock, but
that drift produces no load term.

This is an important model invariant:

> a different rhythm is not treated as stress by itself.

## 6. Externally constrained mode

If schedule_lock > 0, mismatch contributes:

~~~math
L_{rhythm}
=
s\,g_L\,m(t)
~~~

where:
- s = schedule_lock;
- g_L = mismatch_load_gain.

The recovery-inertia addition is:

~~~math
\Delta I_{recovery}
=
s\,g_R\,m(t).
~~~

PERSON-TIME2 then uses:

~~~math
\dot M_p
=
...
+
L_{rhythm}
-
k_{rec}(1-I_{effective})M_p.
~~~

This gives two distinct consequences of schedule mismatch:
- additional accumulated-memory drive;
- temporarily reduced recovery efficiency.

## 7. Thermal coupling

PERSON-THERM1 uses the same phase state when calculating person cooling.

The base cooling capacity is:

~~~math
C_{cool}=1-I_{recovery}.
~~~

RHYTHM-25H1 changes only the effective recovery inertia at the current phase.

Again:

~~~text
schedule_lock = 0
~~~

means no thermal rhythm penalty.

## 8. Independent initial accumulated state

RHYTHM-25H1 also adds explicit person-specific initial conditions:

~~~text
initial_accumulated_load
initial_heat
initial_recovery_debt
~~~

Example:

~~~json
{
  "initial_accumulated_load": 0.38,
  "initial_heat": 0.28,
  "initial_recovery_debt": 0.12
}
~~~

These values are independent of the person's rhythm.

Therefore a 24-hour person may begin a simulation with more accumulated load
than a 25-hour person.

This is exactly the intended separation:

~~~text
rhythm != prior accumulated state
~~~

## 9. Smoking / alcohol boundary

The current model does **not** contain rules such as:

~~~text
smoking -> higher load
alcohol -> higher load
~~~

If a scenario has evidence that a person already begins in a higher-load state,
that state may be represented directly through the initial conditions.

The cause remains:

~~~text
unknown / externally supplied hypothesis
~~~

unless a separate calibrated covariate model is introduced later.

A future layer could be:

~~~text
RECOVERY-COVARIATE1
~~~

where smoking, alcohol, shift work, exercise, sleep schedule or other observed
covariates are tested individually against prospective data rather than assumed
to have fixed social-model effects.

## 10. Canonical 25h personal scenario

See:

~~~text
examples/rhythm_25h_personal_scenario.json
examples/rhythm_25h_personal_timeline.json
~~~

It contains:

~~~text
central:
  25-hour intrinsic cycle
  initial accumulated load = 0.20
  initial heat = 0.15

n1:
  24-hour cycle
  initial accumulated load = 0.34

n2:
  24-hour cycle
  initial accumulated load = 0.38

n3:
  24-hour cycle
  initial accumulated load = 0.32
~~~

The elevated neighbor initial states are deliberately labelled:

~~~text
unknown_prior_state_hypothesis
~~~

and are not assigned a behavioral cause.

## 11. Observability

Every PERSON-TIME2 node sample now exposes:

~~~text
rhythm.intrinsic_day_hours
rhythm.external_day_hours
rhythm.schedule_lock
rhythm.relative_phase_cycles
rhythm.relative_phase_hours_external
rhythm.phase_mismatch
rhythm.schedule_mismatch_load
rhythm.recovery_inertia_add
rhythm.daily_phase_drift_hours
~~~

PERSON-FAMILY-SAFETY1 propagates the rhythm state into its person components.

## 12. Calibration gates

RHYTHM-25H-CAL1 defines 15 gates:

~~~text
R25_01 central intrinsic period is 25h
R25_02 comparison neighbor period is 24h
R25_03 25h relative phase drifts about -0.96h/day
R25_04 25h and 24h phases realign after 25 external days
R25_05 free-running 25h has zero schedule-load
R25_06 matched 24h has zero phase mismatch
R25_07 free 25h and free 24h have identical dynamics
R25_08 locked 25h accumulates more memory than matched 24h
R25_09 locked 25h reaches strong phase mismatch by day 12
R25_10 initial accumulated load is person-specific
R25_11 initial heat/debt are person-specific
R25_12 elevated neighbor prior state is independent of rhythm mismatch
R25_13 rhythm state is exposed in PERSON-TIME2
R25_14 rhythm state is exposed in Family Safety
R25_15 legacy no-rhythm scenario equals explicit 24h free-running scenario
~~~

## 13. Scientific boundary

RHYTHM-25H1 establishes only the mechanics of two competing clocks and explicit
initial state.

It does not establish:
- that a real person's biological circadian period is exactly 25 hours;
- that a 25-hour lifestyle causes distress;
- that another person's load was caused by smoking or alcohol;
- that rhythm differences explain a particular interpersonal event.

Those are empirical hypotheses requiring separate data.

## 14. Executable gate

~~~bash
python3 simulator/rhythm_25h_calibration.py
python3 -m unittest tests.test_rhythm_25h -v
~~~

Expected own gate:

~~~text
RHYTHM-25H-CAL1 15/15 PASS
~~~

No founder/local WSL PASS is claimed until executable verification is supplied.
