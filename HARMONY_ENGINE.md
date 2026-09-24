# HARMONY1 — Query-driven equation and harmonization engine

The RLC-family chat interface is not limited to one fixed calculation.

A user can ask a **question**, and the LLM compiles that question into a `ProblemSpec`. The deterministic engine then selects the relevant equation family and solves the requested problem.

## Pipeline

```text
family story + user question
        ↓
LLM semantic compiler
        ↓
FamilyScenario + ProblemSpec
        ↓
equation planner / deterministic solver
        ↓
equations used + numerical solution
        ↓
family-language interpretation
```

The LLM decides **what problem the user is asking**.  
The Python engine decides **what the numbers are**.

## Supported ProblemSpec types

### diagnose

General state calculation.

```json
{
  "type": "diagnose"
}
```

Uses, among others:

```text
Z = R + j(ωL - 1/(ωC))
I = V / |Z|
ω₀ = 1 / sqrt(LC)
financial_net = income - load
```

### solve_resonance

Find the event-frequency analogue at which the RLC reactance crosses zero.

```json
{
  "type": "solve_resonance"
}
```

The engine explicitly solves:

```text
X(ω) = ωL - 1/(ωC)
X(ω₀) = 0
ω₀ = 1/sqrt(LC)
```

### solve_finance

Solve a specific financial equation instead of merely reporting current state.

Break-even explicit income:

```json
{
  "type": "solve_finance",
  "target": "break_even_income"
}
```

Maximum break-even mortgage:

```json
{
  "type": "solve_finance",
  "target": "max_mortgage"
}
```

Required reserve for a target runway:

```json
{
  "type": "solve_finance",
  "target": "required_reserve_for_runway",
  "months": 6
}
```

### what_if

Recalculate the whole system after requested parameter changes.

```json
{
  "type": "what_if",
  "changes": {
    "связь.качество_проводника": 0.80,
    "связь.сброс_через_антенну": 0.65
  }
}
```

The solver returns both the new result and the difference in model violation relative to baseline.

### harmonize

Search for parameter changes that move the modeled system toward the defined operating envelope.

```json
{
  "type": "harmonize",
  "max_changes": 2,
  "max_results": 5
}
```

The engine solves an optimization problem of the form:

```text
minimize V(x)

V(x) = sum(normalized operating-envelope violations)

subject to:
x belongs to the explicitly allowed safe/actionable parameter set
```

By default, only system-level actions are explored:

- improve communication-channel quality;
- improve critical filtering of external noise;
- improve safe antenna dump;
- improve matching of the external support channel;
- reduce emotional amplification.

The default optimizer does **not** invent salary, mortgage, spending, medical, legal, or other real-world interventions.

If the user explicitly wants a different action space, the LLM can compile it as a list of allowed values:

```json
{
  "type": "harmonize",
  "max_changes": 2,
  "actions": [
    {
      "path": "связь.качество_проводника",
      "values": [0.70, 0.80, 0.90],
      "cost": 1.0
    },
    {
      "path": "связь.сброс_через_антенну",
      "values": [0.50, 0.65, 0.80],
      "cost": 1.5
    }
  ]
}
```

## Operating envelope

The first implementation uses transparent internal conventions rather than a hidden "happiness score".

The solver checks:

- interaction current inside a working band;
- absolute phase not excessively displaced;
- damping inside a working band;
- memory not above the high-memory threshold;
- non-negative monthly cash flow when a financial subsystem exists;
- at least three months of runway when a finite runway can be calculated.

It returns:

```text
criteria_passed
criteria_total
violation
```

Lower `violation` is better **inside the RLC-family model only**.

These numbers are not measurements of relationship quality, mental health, compatibility, or family worth.

## Safety / anti-destruction rule

HARMONY1 is intended to search for stabilizing or load-reducing changes.

The default engine must not optimize for goals such as:

- maximize conflict;
- maximize memory of grievances;
- maximize financial damage;
- destabilize another person;
- isolate a partner from support;
- increase coercive control.

A request to explore instability can still be handled as a descriptive `what_if` analysis of a hypothetical system, but it should not be turned into an intervention plan for harming or manipulating real people.

## CLI

```bash
python3 simulator/problem_solver.py \
  examples/family_scenario.json \
  examples/problem_harmonize.json
```

## Chat examples

User:

> Что сейчас сильнее всего раскачивает наш контур?

LLM:

```text
ProblemSpec = {"type":"diagnose"}
```

Then it inspects which operating-envelope terms contribute most to violation.

User:

> При какой частоте событий у нас будет нулевой фазовый сдвиг?

LLM:

```text
ProblemSpec = {"type":"solve_resonance"}
```

User:

> Какой доход нужен, чтобы хотя бы не уходить в минус?

LLM:

```text
ProblemSpec = {
  "type":"solve_finance",
  "target":"break_even_income"
}
```

User:

> Что будет, если мы улучшим общение и я перестану так резко усиливать реакцию?

LLM compiles the concrete changes into `what_if`.

User:

> Какие два изменения сильнее всего приблизят схему к рабочему режиму?

LLM compiles `harmonize`, the solver tests the candidate action set, and the LLM explains the ranked numerical results.

## Design rule

The equation system is assembled **per question**.

RLC-family should therefore behave less like a questionnaire and more like an engineering conversation:

> **describe the situation → ask a question → assemble the equations → solve → interpret.**


### person_network

Если сценарий содержит `персонажи` и вопрос относится к конкретным людям или связям, используется PERSON-NET1:

```json
{"type":"person_network"}
```

Решатель строит комплексную узловую матрицу `Y V = I` и возвращает отдельные напряжения/фазы персонажей и токи каналов. Подробнее: [PERSON_NETWORK.md](PERSON_NETWORK.md).


### person_timeline

Для адресной истории по конкретным PERSON2-узлам:

```json
{
  "type": "person_timeline",
  "timeline": {
    "моделирование": {},
    "события": []
  }
}
```

Используется [PERSON_TIME.md](PERSON_TIME.md). Solver собирает и интегрирует систему дифференциальных уравнений по всем персонажам и связям.
