# RLC-family executable simulator

`simulator/rlc_family_sim.py` turns a scenario written in **family-language terms** into a deterministic normalized analog model, solves it, and translates the result back into family language.

This is an executable satire / systems-model toy. It is **not** a psychological, medical, or financial forecasting model.

## Pipeline

```text
family_scenario.json
        ↓
family-language compiler
        ↓
AnalogIR
        ↓
normalized RLC/RLCM + communication + financial/optical solver
        ↓
result.json + circuit.net
        ↓
family-language interpreter
        ↓
report.md
```

The user does not enter R, L, C, impedance, phase, or a netlist directly.

## Run

```bash
python3 simulator/rlc_family_sim.py examples/family_scenario.json --out out/demo
```

The command prints the family-language report and creates:

```text
out/demo/
├── analog_ir.json
├── circuit.net
├── report.md
└── result.json
```

For machine-readable stdout:

```bash
python3 simulator/rlc_family_sim.py examples/family_scenario.json --out out/demo --json
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

No third-party Python packages are required.

## Input language

The MVP uses structured JSON, but the keys are family concepts rather than circuit parameters.

```json
{
  "отношения": {
    "мужская_емкость": 0.72,
    "женская_индуктивность": 0.81,
    "сопротивление_детей": [0.42, 0.58],
    "напряженность": 0.56,
    "накопленная_память": 0.34
  },
  "связь": {
    "качество_проводника": 0.74,
    "внешний_фон": 0.37,
    "сброс_через_антенну": 0.52
  },
  "финансы": {
    "доходы_в_месяц": [3200, 1850],
    "ипотека_в_месяц": 1450,
    "резерв": 9200,
    "свет_возможностей": 0.43
  }
}
```

Most normalized family parameters are in `[0, 1]`.

## Compiler mapping

| Family term | Internal analog element |
|---|---|
| мужская ёмкость | `C_MAN` |
| женская индуктивность | `L_WOMAN` |
| сопротивление детей | `R_CHILD` |
| качество проводника | `R_CHANNEL` |
| сброс через антенну | `R_RAD` |
| накопленная память | `MEM` |
| подростковая нелинейность | `NL_TEEN` |
| семейная напряжённость | `V_REL` |
| внешний фон | `V_EXT` |
| эмоциональное усиление | `GAIN` |

Finance is compiled into a parallel financial subsystem rather than being mixed with relationship current.

## What is solved

The relationship core is a normalized series RLC equivalent with communication and radiative damping:

```text
VREL + VEXT → R_CHILD → R_CHANNEL → R_RAD → L_WOMAN → C_MAN
```

The solver calculates total resistance, reactance, impedance, interaction current, phase shift, resonance frequency, damping, antenna dump power, and updated memory.

The finance solver separately calculates explicit income, optofinancial income opened by `свет_возможностей`, mortgage/base/other load, net monthly cash flow, reserve, runway, and mortgage-debt evolution.

## Output contract

The intended contract is:

```text
family language in
→ explicit AnalogIR
→ deterministic calculation
→ family language out
```

The same run exposes both sides:

- `analog_ir.json` — the compiled analog representation;
- `circuit.net` — normalized pseudo-SPICE view;
- `result.json` — machine result;
- `report.md` — interpretation back in family language.

No result should be produced solely by prose interpretation if it can first be represented in `AnalogIR`.

## Current simulator gates

Implemented in SIM-0.1:

- family-language JSON compiler;
- RLC frequency-domain relationship core;
- child series/parallel resistance;
- communication-channel losses;
- external field/filter/amplifier path;
- antenna dump damping;
- memory state;
- adolescent nonlinearity;
- mortgage/debt dynamics;
- reserve/runway;
- optofinancial light/coupling/gain path;
- deterministic reports;
- regression tests.

## Next extensions

1. **SIM-TIME1** — time-domain integration rather than one-frequency analysis.
2. **SIM-HYST1** — explicit hysteresis loops and state history.
3. **SIM-NET1** — several families connected into a house/city graph.
4. **SIM-OPT1** — richer laser/fiber/resonator financial network.
5. **SIM-NL1** — piecewise nonlinear child/adolescent I–V curves.
6. **SIM-DSL1** — compact natural family-language DSL above JSON.
7. **SIM-PLOT1** — phase, spectrum, reserve, debt, and hysteresis plots.
