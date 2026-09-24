# LINK-SEMI1 — nonlinear directed and gated relationship links

LINK-SEMI1 extends the original passive relationship resistor with normalized
nonlinear link elements.

This is an engineering analogy for network structure.

It does **not** assert that employers, friends or coworkers literally behave
like electronic components.

The element type must be chosen because the observed relationship structure
matches the intended mathematical behavior.

## Supported elements

```text
RESISTIVE
DIODE
MOSFET
BREAKDOWN_DIODE
```

Legacy links remain `RESISTIVE`.

## 1. RESISTIVE

The original symmetric link:

```math
I_{pq}=\frac{V_p-V_q}{R_{pq}}.
```

Use when the channel is approximately passive and symmetric.

Typical first-use example:

```text
coworker <-> coworker
```

when neither direction has an explicit structural gate.

This is a modeling choice, not a universal rule about coworkers.

## 2. DIODE

A directed channel with a small reverse conductance.

The current is implemented as:

```math
I=\Delta V\,G(\Delta V)
```

where `G` smoothly changes from a reverse conductance to the normal forward
conductance after a forward threshold.

Parameters:

```text
forward_threshold
softness
reverse_ratio
```

Example:

```json
{
  "from": "friend",
  "to": "employee",
  "element_type": "DIODE",
  "reverse_ratio": 0.08,
  "forward_threshold": 0.04
}
```

This can represent a relationship in which support/information is much easier
in one direction than the other.

Do not assign DIODE merely because a relationship is called "friendship".

## 3. MOSFET

A channel whose effective conductance is controlled by an external normalized
gate:

```text
gate in [0,1]
```

The channel factor is approximately:

```math
g_{gate}
=
g_{off}
+
(1-g_{off})
\sigma\left(
\frac{gate-gate_{th}}{s_g}
\right).
```

A separate direction factor can reduce reverse transmission.

Parameters:

```text
gate
gate_threshold
gate_softness
off_ratio
reverse_ratio
gate_semantics
```

### Employer -> employee example

The first calibration example uses:

```text
from = employer
to = employee
element_type = MOSFET
gate_semantics = authority_contract_dependency
```

The gate can represent an explicitly declared mixture such as:

- formal authority;
- contractual obligation;
- dependency on the job;
- institutional permission to issue work demands.

It must not be interpreted as a personality trait or "obedience score".

An open gate means the institutional channel can carry more interaction for the
same node-state difference.

## 4. BREAKDOWN_DIODE

This adds an avalanche-like reverse path.

Below the reverse threshold the channel is mostly closed.

After:

```text
reverse |delta V| > breakdown_threshold
```

the reverse conductance rises sharply.

Possible modeling use:

```text
boundary holds
-> pressure accumulates
-> threshold is exceeded
-> previously suppressed reverse response becomes large
```

The project should describe this as a threshold/boundary-breach regime, not as
a psychiatric "breakdown".

## 5. Direction convention

For nonlinear links:

```text
from -> to
```

defines the forward direction.

This matters for DIODE, MOSFET with reduced reverse conductance, and
BREAKDOWN_DIODE.

Legacy RESISTIVE links remain symmetric.

## 6. Dynamic gate events

PERSON-TIME2 supports:

```text
gate_set
gate_add
```

for a target MOSFET link.

Example:

```json
{
  "id": "authority-relief",
  "день": 6,
  "длительность_дней": 5,
  "связь": ["employer","employee"],
  "gate_set": 0.20
}
```

This changes the gate only during the event window.

Gate mutation on a non-MOSFET link is rejected.

## 7. Nonlinear solver boundary

`PERSON-NET1` is a linear frequency-domain nodal solver.

It therefore refuses LINK-SEMI1 nonlinear elements rather than pretending that
a nonlinear directed device is an ordinary admittance.

Use:

```text
PERSON-TIME2
```

for DIODE / MOSFET / BREAKDOWN_DIODE networks.

This preserves an honest solver boundary.

## 8. Universal thermal power

For any LINK-SEMI1 element:

```math
P_{pq}=|\Delta V_{pq} I_{pq}|.
```

LINK-THERM1 uses this universal expression.

For a RESISTIVE link:

```math
|VI|=I^2R=\frac{V^2}{R}.
```

Therefore the previous thermal model is recovered exactly.

For nonlinear elements, the model does not invent a fictitious constant
resistance.

## 9. First mixed social example

See:

```text
examples/link_semi1_work_social_scenario.json
examples/link_semi1_work_social_timeline.json
```

The example contains:

```text
employer -> employee : MOSFET
employee <-> coworker: RESISTIVE
friend -> employee   : DIODE
```

and a timeline that opens the employer channel during a work-pressure window
then lowers its gate during a relief/leave window.

## 10. Calibration gates

```text
SEMI01 resistor remains symmetric
SEMI02 diode is directionally asymmetric
SEMI03 zero bias gives zero current
SEMI04 MOSFET gate controls channel conductance
SEMI05 MOSFET reverse current is reduced
SEMI06 breakdown diode opens a reverse path above threshold
SEMI07 resistor |VI| equals I^2R exactly
SEMI08 legacy links compile as RESISTIVE
SEMI09 MOSFET metadata compiles
SEMI10 gate events are targeted and non-MOSFET gate mutation is rejected
```

Reference probe with normalized `R_link=1` and `delta V=0.20` approximately
gives:

```text
DIODE:
  forward current ~ +0.200
  reverse current ~ -0.010

MOSFET:
  gate 0.10 current ~ +0.0053
  gate 0.90 current ~ +0.199
  gate 0.90 reverse ~ -0.0397
```

These values validate the equation shape, not social behavior.

## 11. Current limitation: one branch per pair

PERSON2 currently permits one link object for each pair of nodes.

Therefore the following richer model is **not yet represented explicitly**:

```text
coworker relationship
=
R_personal
parallel
MOSFET_institutional
```

That should be a separate future gate:

```text
MULTI-LINK1
```

rather than silently approximated inside LINK-SEMI1.

## 12. Executable verification

```bash
python3 simulator/link_semiconductor_calibration.py
python3 -m unittest tests.test_link_semiconductor -v
python3 -m unittest tests.test_link_semiconductor_integration -v

# stacked parent
python3 simulator/thermal_calibration.py
python3 -m unittest tests.test_thermal_recovery -v
python3 -m unittest tests.test_recovery_scenarios -v

# legacy regressions
python3 -m unittest tests.test_person_time_calibration -v
python3 -m unittest tests.test_link_semantics -v
```

Expected own gate:

```text
LINK-SEMI-CAL1 10/10 PASS
```

No local WSL PASS is claimed until executed.
