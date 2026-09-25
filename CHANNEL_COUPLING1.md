# CHANNEL-COUPLING1 — explicit modulation between relationship channels

CHANNEL-COUPLING1 adds declared branch-to-branch influence on top of MULTI-LINK1.

It answers a new structural question:

> Can activity in one relationship channel alter the transport properties of another channel?

Example:

\`\`\`text
employer <-> employee

personal branch:
  RESISTIVE

work branch:
  MOSFET

work power
  -> temporarily lowers personal communication quality

personal communication quality
  -> modestly increases work reverse transmission
\`\`\`

The project does **not** assume these effects automatically.

Every coupling must be explicitly declared.

---

## 1. Why this is separate from MULTI-LINK1

MULTI-LINK1 creates independent parallel branches:

\`\`\`text
R_personal || MOSFET_work
\`\`\`

Without CHANNEL-COUPLING1:

\`\`\`text
personal branch affects node dynamics
work branch affects node dynamics
but the branches do not directly modify one another
\`\`\`

CHANNEL-COUPLING1 adds an explicit directed rule:

\`\`\`text
source_link_id
  -> source_signal
  -> threshold/gain
  -> target_link_id.target_field
\`\`\`

This keeps channel interaction inspectable rather than hiding it inside the
link equations.

---

## 2. Rule schema

Example:

\`\`\`json
{
  "coupling_id": "work-power-degrades-personal-quality",
  "source_link_id": "employer-employee.work",
  "source_signal": "power",
  "source_scale": 0.020,
  "threshold": 0.20,

  "target_link_id": "employer-employee.personal",
  "target_field": "communication_quality",

  "gain": -0.30,
  "max_abs_effect": 0.25
}
\`\`\`

Every rule has a stable \`coupling_id\`.

Source and target links must already exist in the compiled MULTI-LINK1 graph.

Self-coupling of a branch to itself is rejected.

---

## 3. Supported source signals

Current source signals are:

\`\`\`text
current_abs
power
conductance
communication_quality
effective_transmission
hostility
gate
\`\`\`

### current_abs

\`\`\`math
|I_b|
\`\`\`

### power

\`\`\`math
P_b = |\Delta V_b I_b|
\`\`\`

This is instantaneous LINK-SEMI1 electrical dissipation.

It is **not** accumulated LINK-THERM1 heat.

### conductance

Instantaneous branch conductance after LINK-SEMI1 element evaluation.

### semantic signals

\`\`\`text
communication_quality
effective_transmission
hostility
gate
\`\`\`

are read directly from the event-adjusted source branch before any coupling
rule is applied at that instant.

\`gate\` as a source is permitted only for a MOSFET branch.

---

## 4. Supported target fields

Current target fields are:

\`\`\`text
communication_quality
contact_frequency
availability
hostility
gate
reverse_ratio
\`\`\`

Semantic fields automatically refresh LINK-SEM1 transport:

\`\`\`text
communication_quality
contact_frequency
availability
hostility
  -> effective_transmission
  -> R_link
\`\`\`

A \`gate\` target requires a MOSFET.

A \`reverse_ratio\` target requires:

\`\`\`text
DIODE
MOSFET
BREAKDOWN_DIODE
\`\`\`

---

## 5. Coupling equation

For source value \`x\` and source scale \`s_0\`:

\`\`\`math
z = \operatorname{clip}_{[0,1]}\left(\frac{x}{s_0}\right)
\`\`\`

Activation above threshold:

\`\`\`math
a = \max(0,z-\theta)
\`\`\`

Raw effect:

\`\`\`math
\Delta f = g\,a
\`\`\`

bounded per rule by:

\`\`\`math
|\Delta f| \le m.
\`\`\`

If several rules target the same field:

\`\`\`math
f'
=
\operatorname{clip}_{[0,1]}
\left(
f + \sum_k \Delta f_k
\right).
\`\`\`

Parameters:

\`\`\`text
source_scale > 0
threshold in [0,1]
gain in [-1,1]
max_abs_effect in [0,1]
\`\`\`

Invalid values are rejected rather than silently normalized.

---

## 6. Simultaneous base-read semantics

All source signals are captured first from the uncoupled branch set at the
current PERSON-TIME2 state.

Only after all source signals are frozen are target deltas applied.

Therefore:

\`\`\`text
A -> B
B -> A
\`\`\`

is deterministic.

Rule order in JSON cannot change the result.

Example:

\`\`\`text
personal quality = 0.82

rule 1:
work power -> personal quality -0.24

rule 2:
personal quality -> work reverse_ratio
\`\`\`

Rule 2 still reads the base \`0.82\` during this solver instant.

It does not read the already modified \`0.58\`.

This prevents hidden algebraic iteration and order dependence.

---

## 7. Event precedence

PERSON-TIME2 applies direct timeline events first.

Then CHANNEL-COUPLING1 reads the resulting event-adjusted branch state.

The order is:

\`\`\`text
base compiled branch
-> TimelineSpec event mutations
-> freeze source signals
-> CHANNEL-COUPLING1 simultaneous target modulation
-> evaluate branch currents
-> integrate PERSON2 state
\`\`\`

This means a direct event such as:

\`\`\`json
{
  "target_link_id": "employer-employee.work",
  "gate_set": 0.95
}
\`\`\`

can increase the source work current/power and thereby activate a coupling rule
during the same integration interval.

---

## 8. Same-pair default

By default a coupling may connect only channels belonging to the same pair.

Example:

\`\`\`text
work(employer, employee)
  -> personal(employer, employee)
\`\`\`

is allowed.

A cross-pair rule such as:

\`\`\`text
work(employer, employee)
  -> personal(employee, spouse)
\`\`\`

is a much stronger network hypothesis.

It is rejected unless the rule explicitly declares:

\`\`\`json
{
  "allow_cross_pair": true
}
\`\`\`

This prevents an incorrect \`link_id\` from silently creating remote influence.

---

## 9. Canonical first example

See:

\`\`\`text
examples/channel_coupling1_work_personal_scenario.json
examples/channel_coupling1_work_personal_timeline.json
\`\`\`

It declares two rules.

### Work spillover hypothesis

\`\`\`text
source:
  employer-employee.work
  signal = power

target:
  employer-employee.personal
  field = communication_quality

gain < 0
\`\`\`

Interpretation:

> High instantaneous work-channel dissipation is hypothesized to make the
> personal communication channel temporarily less efficient.

This is a model hypothesis, not an established human causal law.

### Personal support hypothesis

\`\`\`text
source:
  employer-employee.personal
  signal = communication_quality

target:
  employer-employee.work
  field = reverse_ratio

gain > 0
\`\`\`

Interpretation:

> A high-quality personal channel is hypothesized to modestly increase reverse
> transmission through the institutional work channel.

Again, this is a declared hypothesis, not a validated social effect.

---

## 10. Solver boundary

PERSON-NET1 rejects every scenario containing CHANNEL-COUPLING1 rules.

Even if all physical branches are RESISTIVE, the coupling source signals depend
on the current state.

Use:

\`\`\`text
PERSON-TIME2
\`\`\`

for coupled-channel simulations.

This keeps the frequency-domain solver linear and honest.

---

## 11. Explainability / provenance

Every PERSON-TIME2 sample contains:

\`\`\`text
channel_coupling_effects
\`\`\`

Each effect records:

\`\`\`text
coupling_id
source_link_id
target_link_id
source_signal
source_value
normalized_source
threshold
activation_excess
gain
target_field
delta
\`\`\`

Therefore the UI can explain:

\`\`\`text
personal communication quality changed by -0.08

because:
  work-power-degrades-personal-quality

source work power:
  ...

threshold:
  ...

applied delta:
  -0.08
\`\`\`

rather than exposing only the final link state.

---

## 12. Family Safety integration

PERSON-FAMILY-SAFETY1 preserves coupling provenance in every trajectory row.

Its summary exposes, per coupling:

\`\`\`text
source_link_id
target_link_id
target_field
peak_abs_delta
mean_abs_delta
first_active_day
\`\`\`

This allows the family/work report to distinguish:

> The personal channel is strained.

from:

> In this declared scenario, part of the personal-channel degradation came
> through the work-power spillover rule.

No causal claim should be made beyond the declared simulation hypothesis.

---

## 13. Thermal interaction

Coupling-modified branches are evaluated before sample currents and power are
reported.

Therefore LINK-THERM1 receives:

\`\`\`text
post-coupling current
post-coupling |VI| power
post-coupling semantic state
\`\`\`

However:

\`\`\`text
LINK-THERM1 heat
LINK-THERM1 damage
recovery debt
\`\`\`

are currently downstream post-processing states.

They are **not** fed back into PERSON-TIME2 through CHANNEL-COUPLING1.

A future explicit gate is required for that:

\`\`\`text
THERMAL-FEEDBACK1
\`\`\`

---

## 14. No automatic social rules

The project must not silently create rules such as:

\`\`\`text
work stress always damages marriage
friendship always improves work communication
authority always creates hostility
financial pressure always closes a personal channel
\`\`\`

A coupling exists only when the scenario declares it.

Future empirical work may determine whether particular classes of rules have
predictive value.

Until then they remain scenario hypotheses.

---

## 15. Calibration gates

CHANNEL-COUPLING-CAL1 defines:

\`\`\`text
CC01 empty ruleset is exact identity
CC02 coupling rules compile with stable ids
CC03 high work power lowers personal communication quality
CC04 semantic coupling refreshes target R_link
CC05 personal quality can increase work reverse_ratio
CC06 reciprocal rules read the same base instant
CC07 rule ordering cannot change the result
CC08 target values remain bounded
CC09 unknown source/target link is rejected
CC10 self-coupling is rejected
CC11 cross-pair coupling requires explicit opt-in
CC12 gate target requires MOSFET
CC13 PERSON-NET1 rejects dynamic channel coupling
CC14 PERSON-TIME2 exposes effect provenance
CC15 Family Safety summarizes effect provenance
\`\`\`

Reference static calibration for:

\`\`\`text
V_employer = +0.20
V_employee = -0.20
\`\`\`

gives approximately:

\`\`\`text
personal communication quality:
  0.82 -> 0.58

work reverse_ratio:
  0.15 -> 0.186
\`\`\`

The second value is deliberately computed from the base personal quality
\`0.82\`, proving simultaneous base-read semantics.

---

## 16. Executable gate

Run:

\`\`\`bash
python3 simulator/channel_coupling_calibration.py
python3 -m unittest tests.test_channel_coupling -v

# MULTI-LINK1 parent
python3 simulator/multi_link_calibration.py
python3 -m unittest tests.test_multi_link -v

# LINK-SEMI1 parent
python3 simulator/link_semiconductor_calibration.py
python3 -m unittest tests.test_link_semiconductor -v
python3 -m unittest tests.test_link_semiconductor_integration -v

# THERM-RECOVERY1 parent
python3 simulator/thermal_calibration.py
python3 -m unittest tests.test_thermal_recovery -v
python3 -m unittest tests.test_recovery_scenarios -v
python3 -m unittest tests.test_thermal_problem_routing -v

# legacy
python3 -m unittest tests.test_link_semantics -v
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_person_load_family_cases -v
python3 -m unittest tests.test_family_validation_cases -v
\`\`\`

Expected own gate:

\`\`\`text
CHANNEL-COUPLING-CAL1 15/15 PASS
\`\`\`

No founder/local WSL PASS is claimed until executed.

---

## 17. Next frontiers

CHANNEL-COUPLING1 is intentionally memoryless at the coupling-rule level.

Two richer mechanisms should remain separate gates.

### COUPLING-MEM1

Add lag/hysteresis to branch-to-branch effects:

\`\`\`text
work pressure today
  -> personal-channel effect persists for several days
\`\`\`

### THERMAL-FEEDBACK1

Feed accumulated LINK-THERM heat/damage back into branch semantics:

\`\`\`text
link heat
  -> target quality/gate/reverse path
\`\`\`

Those mechanisms should not be hidden inside CHANNEL-COUPLING1 before the
memoryless coupling layer itself is executable and stable.
