# SIM-TIME1 — Event-driven time-domain family model

SIM-TIME1 extends RLC-family from a static operating-point calculation to a dynamic trajectory.

The intended chat workflow is:

```text
family story with event order
→ LLM compiles FamilyScenario + TimelineSpec
→ time_solver.py assembles the dynamic equations
→ RK4 numerical integration
→ timeline_result.json + timeline.csv
→ LLM explains the trajectory in family language
```

## State vector

The first dynamic state is:

```text
x(t) = [q(t), i(t), m(t), Reserve(t), Debt(t)]
```

where:

- `q(t)` — normalized capacitor charge;
- `i(t)` — dynamic interaction current;
- `m(t)` — accumulated family-memory state;
- `Reserve(t)` — financial reserve;
- `Debt(t)` — mortgage debt.

## Equations

The solver exposes the equations used in every result:

```text
dq/dt = i

L di/dt = V(t) - R(t)i - q/C(t)

dm/dt =
    a |V(t)|
  + b |i(t)|
  - λ m(t)
  - k_rad P_rad(t)

dReserve/dt =
    (income(t) - load(t)) / days_per_month
    + discrete money impulses

dDebt/dt =
    annual_rate/365 * Debt
  - mortgage/days_per_month
```

The coefficients `R(t), L(t), C(t), V(t)` are recompiled from the current family-language scenario, including active events.

These are normalized RLC-family equations, not calibrated equations of human psychology.

## Event language

A `TimelineSpec` contains ordinary event concepts compiled into parameter changes.

Example:

```json
{
  "id": "argument",
  "день": 1,
  "длительность_дней": 0.5,
  "описание": "Ссора",
  "добавить": {
    "отношения.напряженность": 0.22,
    "связь.усиление_эмоций": 0.20
  },
  "импульс_памяти": 0.08
}
```

Supported event mechanics:

- `установить` / `set` — temporarily set model parameters;
- `добавить` / `add` — temporarily add to parameters;
- `денежный_импульс` — one-time reserve change;
- `импульс_памяти` — one-time memory change;
- `длительность_дней` — duration of a temporary condition.

Zero-duration events are impulses only. Their `set/add` fields do not persist.

## Example timeline

[examples/family_timeline.json](examples/family_timeline.json) includes:

1. a quarrel;
2. two days of weak communication;
3. a salary impulse;
4. an external-family call increasing background excitation;
5. a well-matched conversation producing stronger external dump.

## Run

```bash
python3 simulator/time_solver.py \
  examples/family_scenario.json \
  examples/family_timeline.json \
  --out out/time-demo
```

Outputs:

```text
out/time-demo/
├── timeline_result.json
├── timeline_report.md
└── timeline.csv
```

The CSV is intentionally dependency-free and can be plotted by any LLM, notebook, spreadsheet or future mobile client.

## Chat usage

The user should not write TimelineSpec manually.

They can say:

> В понедельник поссорились. Потом два дня почти не разговаривали. В четверг пришла зарплата. В пятницу позвонила мать, после чего напряжение выросло. В воскресенье я поговорил с другом и успокоился. Покажи, как прошла неделя.

The LLM should:

1. preserve the stated event order and durations;
2. distinguish facts from inferred numerical mappings;
3. expose those assumptions;
4. compile `TimelineSpec`;
5. run `time_solver.py`;
6. report the peak, recovery time, memory trajectory, reserve/debt trajectory and important event effects;
7. interpret the result back into RLC-family language.

## Numerical method

SIM-TIME1 uses deterministic fourth-order Runge-Kutta integration (RK4).

Default/allowed first-version behavior:

- `dt_days <= 0.25`;
- bounded run size;
- memory clamped to `[0,1]`;
- mortgage debt clamped at zero;
- no third-party Python dependency.

The timestep guard is deliberate: the engine should refuse obviously coarse integration instead of producing a deceptively precise result.

## Current dynamic observables

Each sampled point includes:

- day;
- capacitor charge;
- interaction current;
- memory;
- financial reserve;
- mortgage debt;
- total drive;
- current R/L/C;
- local phase tendency;
- radiated dump power;
- income/load equivalents;
- active event IDs.

The summary currently reports:

- peak interaction current and its day;
- half-recovery time after the peak;
- peak memory and its day;
- minimum reserve and its day;
- final reserve;
- final debt;
- event count.

## Validation

`tests/test_time_solver.py` covers:

- deterministic replay;
- money impulses;
- memory impulses;
- stronger dynamic response to a quarrel event;
- non-persistence of zero-duration set operations;
- timestep guard;
- output artifacts;
- explicit equation exposure.

Local development gate:

```text
8/8 SIM-TIME1 tests PASS
```

## Next gates

- **SIM-EVENT2** — richer event shapes: ramps, exponential decay, periodic forcing.
- **SIM-HYST1** — explicit hysteresis/memristive state rather than a single scalar memory.
- **SIM-COMPARE1** — run two timelines and calculate intervention deltas.
- **SIM-OPT-TIME1** — optimize timing of stabilizing actions.
- **SIM-NET-TIME1** — several families/households coupled in one time-dependent field.
- **SIM-PLOT1** — canonical plots for current, memory, reserve and debt.

## Core contract

> **Tell the story in time. The engine builds the differential equations, integrates them, and tells the story back with numbers.**
