# MULTI-LINK1 — parallel social channels between the same people

MULTI-LINK1 upgrades the PERSON2 relationship graph from a simple graph to a
multigraph.

Two people may now be connected by several independent relationship channels.

Example:

\`\`\`text
                   R_personal
employer o---------/\/\/\/---------o employee
         \                         /
          \------ MOSFET_work -----/
                     ^
                     |
              authority / contract
\`\`\`

The branches share the same endpoint node states, but each branch has its own:

\`\`\`text
link_id
channel_kind
LINK-SEM1 semantics
LINK-SEMI1 element type
current
thermal power
heat
damage
accumulated strain
events
\`\`\`

This is the first explicit "social circuitry" multigraph layer.

---

## 1. Stable identity

Every compiled link now has:

\`\`\`text
pair_id
link_id
channel_kind
parallel_branch_count
is_parallel_branch
\`\`\`

### pair_id

The unordered pair identity:

\`\`\`text
employee->employer
\`\`\`

It groups every branch connecting the same two people.

### link_id

The unique branch identity.

For a single legacy link the project automatically preserves the old key:

\`\`\`text
a->b
\`\`\`

No migration is required.

For two or more branches between the same pair, every branch must declare an
explicit canonical ASCII \`link_id\`.

Example:

\`\`\`json
{
  "link_id": "employer-employee.personal",
  "channel_kind": "personal",
  "from": "employer",
  "to": "employee",
  "element_type": "RESISTIVE"
}
\`\`\`

and:

\`\`\`json
{
  "link_id": "employer-employee.work",
  "channel_kind": "institutional_work",
  "from": "employer",
  "to": "employee",
  "element_type": "MOSFET",
  "gate": 0.85
}
\`\`\`

Duplicate \`link_id\` values are rejected.

---

## 2. Parallel current

Every branch sees the endpoint node-state difference.

For two linear resistor branches:

\`\`\`math
I_1 = \frac{V_p-V_q}{R_1},
\qquad
I_2 = \frac{V_p-V_q}{R_2}.
\`\`\`

The total coupling current appearing in the PERSON2 node equation is:

\`\`\`math
I_{pq}^{total}
=
\sum_b I_{pq}^{(b)}.
\`\`\`

Therefore the node equation becomes:

\`\`\`math
C_p\dot V_p
=
u_p
-
\frac{V_p}{R_p}
-
i_{L,p}
-
\sum_{\text{incident branches }b} I_b.
\`\`\`

For linear parallel resistors this recovers the ordinary equivalent
conductance:

\`\`\`math
G_{eq}
=
\sum_b \frac1{R_b}.
\`\`\`

For nonlinear LINK-SEMI1 branches the same node equation is used, but each
branch computes its own nonlinear:

\`\`\`math
I_b = I_b(\Delta V, gate_b, \ldots).
\`\`\`

No fictitious equivalent resistance is required.

---

## 3. Example: personal || institutional work

The canonical first example is:

\`\`\`text
examples/multi_link1_work_personal_scenario.json
examples/multi_link1_work_personal_timeline.json
\`\`\`

It contains:

\`\`\`text
employer-employee.personal
  channel_kind = personal
  element      = RESISTIVE

employer-employee.work
  channel_kind = institutional_work
  element      = MOSFET
  gate         = authority_contract_dependency
\`\`\`

This allows states such as:

\`\`\`text
personal channel:
  low contact
  low hostility
  moderate quality

work channel:
  high contact
  high institutional gate
  high work current
\`\`\`

or the reverse.

A single scalar "relationship quality" cannot represent these two channels.

---

## 4. Timeline addressing

With one branch between a pair, the existing syntax remains valid:

\`\`\`json
{
  "target_link": ["a", "b"],
  "communication_quality_set": 0.8
}
\`\`\`

With multiple branches that syntax is ambiguous and is rejected.

The event must specify:

\`\`\`json
{
  "target_link_id": "employer-employee.work",
  "gate_set": 0.20
}
\`\`\`

or:

\`\`\`json
{
  "target_link_id": "employer-employee.personal",
  "communication_quality_set": 0.92
}
\`\`\`

This is a hard safety property:

> an event intended for the work channel must never silently mutate the
> personal channel.

If both \`target_link\` and \`target_link_id\` are supplied, they must identify
the same pair.

---

## 5. PERSON-NET1

Multiple RESISTIVE branches are valid in the linear frequency-domain solver.

Their conductances are accumulated independently in the nodal matrix.

The solver reports every branch separately by \`link_id\`.

If any branch is nonlinear:

\`\`\`text
DIODE
MOSFET
BREAKDOWN_DIODE
\`\`\`

PERSON-NET1 still refuses the solve and directs the caller to PERSON-TIME2.

---

## 6. PERSON-TIME2

PERSON-TIME2 executes every branch independently.

Sampled link rows expose:

\`\`\`text
link_id
pair_id
channel_kind
parallel_branch_count
element_type
gate
delta_v
instantaneous_conductance
current
current_abs
power_vi_proxy
\`\`\`

The currents from all incident branches are then summed in the node equation.

Timeline summaries use \`link_id\`, so two channels between the same people are
not overwritten.

---

## 7. Family Safety: branch state and pair state

PERSON-FAMILY-SAFETY1 keeps accumulated strain separately for every branch.

Example:

\`\`\`text
employer-employee.personal -> strain_personal(t)
employer-employee.work     -> strain_work(t)
\`\`\`

It also creates a pair-level summary:

\`\`\`text
pairs["employee->employer"]
\`\`\`

with:

\`\`\`text
branches
branch_count
peak_total_current_abs
peak_total_dissipation_power_proxy
peak_max_branch_strain
highest_strain_branch
\`\`\`

This separates two questions:

> Which particular channel is strained?

from:

> How much total interaction/dissipation is crossing this pair of people?

---

## 8. Person incident load does not dilute

The old model averaged incident-link stress.

That would create a MULTI-LINK1 artifact:

> adding a second low-load branch could numerically reduce the person's
> incident stress.

MULTI-LINK1 replaces that aggregation with the bounded monotone union:

\`\`\`math
L_{\text{incident}}
=
1-\prod_b(1-x_b).
\`\`\`

Properties:

\`\`\`text
one branch:
  L = x_1
  -> exact legacy value

additional positive branch:
  L cannot decrease

all branches:
  0 <= L <= 1
\`\`\`

Thus adding another real interaction channel cannot reduce incident load merely
through averaging.

---

## 9. Thermal state

LINK-THERM1 remains branch-specific.

For every branch:

\`\`\`math
P_b=|\Delta V\,I_b|.
\`\`\`

Each branch receives its own:

\`\`\`text
heat_b
damage_b
recovery_debt_b
\`\`\`

Thermal rows preserve:

\`\`\`text
link_id
pair_id
channel_kind
\`\`\`

so an application can distinguish:

\`\`\`text
personal channel: COMFORT
work channel: OVERHEATED
\`\`\`

between the same two people.

The pair-level family summary also retains total dissipation across branches.

---

## 10. Relationship labels do not define channels automatically

MULTI-LINK1 does not assume:

\`\`\`text
employer/employee always has exactly two channels
marriage always has personal + financial
coworkers always have work + personal
\`\`\`

The channels must correspond to explicitly declared model hypotheses.

Possible \`channel_kind\` labels include:

\`\`\`text
personal
institutional_work
financial
caregiving
household
friendship
project
generic
\`\`\`

The field is descriptive metadata; the equations come from the branch's
LINK-SEM1 and LINK-SEMI1 parameters.

---

## 11. Calibration gates

MULTI-LINK-CAL1 defines:

\`\`\`text
ML01 legacy single link keeps its old id
ML02 parallel branches compile independently
ML03 parallel branches require explicit ids
ML04 link ids are globally unique
ML05 pair-target event is rejected when ambiguous
ML06 target_link_id mutates only the selected branch
ML07 parallel resistors share the same voltage drop
ML08 R || MOSFET mixed network runs in PERSON-TIME2
ML09 Family Safety preserves branch state and pair aggregate
ML10 extra branch cannot dilute incident person load
ML11 Thermal state remains separate per branch
\`\`\`

Passing these gates establishes multigraph mechanics and backward compatibility.

It does not validate the social interpretation of a particular channel.

---

## 12. Executable gate

Run:

\`\`\`bash
python3 simulator/multi_link_calibration.py
python3 -m unittest tests.test_multi_link -v

# LINK-SEMI1 parent regression
python3 simulator/link_semiconductor_calibration.py
python3 -m unittest tests.test_link_semiconductor -v
python3 -m unittest tests.test_link_semiconductor_integration -v

# thermal parent regression
python3 simulator/thermal_calibration.py
python3 -m unittest tests.test_thermal_recovery -v
python3 -m unittest tests.test_recovery_scenarios -v

# legacy / semantics / time regressions
python3 -m unittest tests.test_link_semantics -v
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_family_validation_cases -v
\`\`\`

Expected own gate:

\`\`\`text
MULTI-LINK-CAL1 12/12 PASS
\`\`\`

No founder/local WSL PASS is claimed until this executable gate is run.

---

## 13. Next frontier

MULTI-LINK1 currently treats parallel channels as independent branches sharing
the same endpoint states.

It does not yet model direct branch-to-branch modulation such as:

\`\`\`text
work conflict degrades personal channel quality
financial pressure opens/closes another channel
personal trust changes the institutional reverse path
\`\`\`

That should be a separate explicit gate rather than hidden coupling:

\`\`\`text
CHANNEL-COUPLING1
\`\`\`

Such coupling would make the circuit substantially richer, but it should only
be added after MULTI-LINK1 itself is executable and stable.


## CHANNEL-COUPLING1 extension

MULTI-LINK1 defines independent branches.

[CHANNEL-COUPLING1](CHANNEL_COUPLING1.md) optionally adds explicit directed modulation between them.

The execution order is:

```text
base branch
-> timeline event mutation
-> freeze source signals
-> simultaneous channel coupling
-> branch current/power
```

Coupling does not change MULTI-LINK1 branch identity. Every target remains the same stable `link_id`.
