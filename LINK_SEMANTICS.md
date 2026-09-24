# LINK-SEM1 — semantic relationship channels

LINK-SEM1 splits the old one-dimensional relationship field `quality` into four independent meanings.

## Problem

Before LINK-SEM1 a link such as:

```json
{"from":"a","to":"b","quality":0.10}
```

could mean several very different things:

- the people communicate badly;
- they rarely talk;
- one person is often unavailable;
- interaction is openly hostile.

Those cases should not produce the same relationship-strain interpretation.

## New fields

A link may now define:

```json
{
  "from": "a",
  "to": "b",
  "communication_quality": 0.90,
  "contact_frequency": 0.20,
  "availability": 0.80,
  "hostility": 0.05
}
```

All four values are normalized to `[0,1]`.

### communication_quality

How well communication works when it occurs.

High value means clearer / more functional communication.

### contact_frequency

How much contact actually occurs.

Low value means little interaction volume, not automatically poor relations.

### availability

How available the channel is.

Low availability can represent travel, work shifts or other practical absence.

It is not automatically hostility.

### hostility

Explicit relational friction / adversarial tone.

This is separate from contact volume.

## Electrical transport

LINK-SEM1 defines:

```math
c_{pq}
=
\sqrt{f_{pq}a_{pq}}
```

where `f` is contact frequency and `a` is availability.

Effective transmission:

```math
T_{pq}
=
q_{pq} c_{pq}
```

where `q` is communication quality.

The existing resistor mapping remains:

```math
R_{pq}
=
0.15 + 2.35(1-T_{pq})
```

So low contact or low availability reduces transport.

## Family-safety semantics

Relationship strain does **not** use `1-T` as conflict.

Instead:

```math
F_{pq}
=
0.65(1-q_{pq})
+
0.35h_{pq}
```

where `h` is hostility.

This `relational_friction` drives the stress interpretation.

Therefore:

```text
rare contact + good communication + low hostility
!=
frequent hostile contact
```

even if the electrical transport magnitude is similar.

## Backward compatibility

Legacy input remains accepted:

```json
{"quality": 0.20}
```

For a legacy link:

```text
communication_quality = 0.20
contact_frequency     = 1.00
availability          = 1.00
hostility             = 0.80
effective_transmission= 0.20
```

This preserves the old `R_link` exactly.

The compatibility output field:

```text
quality
```

now equals `effective_transmission`.

New code should prefer the explicit LINK-SEM1 fields.

## Dynamic events

PERSON-TIME2 supports semantic mutations of one target link.

Examples:

```json
{
  "id": "travel",
  "день": 2,
  "длительность_дней": 5,
  "связь": ["a","b"],
  "availability_set": 0.20
}
```

```json
{
  "id": "argument",
  "день": 4,
  "длительность_дней": 0.5,
  "связь": ["a","b"],
  "hostility_set": 0.85,
  "communication_quality_set": 0.35
}
```

Supported fields:

```text
communication_quality_set / _add
contact_frequency_set / _add
availability_set / _add
hostility_set / _add
```

A semantic link mutation without `target_link` is rejected.

## Calibration gates

```text
LSEM01 legacy quality preserves old transport exactly
LSEM02 low contact reduces transport
LSEM03 low contact alone does not create high relational friction
LSEM04 hostility raises strain independently of contact volume
LSEM05 low availability reduces transport but not hostility
LSEM06 semantic events require an explicit target link
LSEM07 old PERSON2 scenarios remain readable
```

## Example

See:

```text
examples/person_link_semantics_scenario.json
```

It contrasts:

- a rare but good/non-hostile relationship;
- a frequent but hostile/low-quality relationship.

## Boundary

LINK-SEM1 still does not model desired contact.

Therefore low availability is treated as reduced transport, not as distress.

A future layer may add:

```text
desired_contact
support_expectation
unmet_contact_need
```

if real calibration shows that they are needed.
