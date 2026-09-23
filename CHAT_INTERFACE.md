# Chat interface for RLC-family

The preferred interface is now **natural-language chat**.

The user should not need to fill in R, L, C, impedances, normalized coefficients, or even JSON.

## Canonical pipeline

```text
user message in ordinary family language
        ↓
LLM semantic compiler
        ↓
explicit assumptions + normalized FamilyScenario JSON
        ↓
deterministic Python solver
        ↓
AnalogIR + pseudo-SPICE + numerical result
        ↓
LLM family-language interpretation
```

The semantic compiler and the numerical solver have different authority.

- The **LLM** may interpret words, extract facts and propose bounded normalized parameters.
- The **solver** is authoritative for all numerical quantities derived from those parameters.
- The LLM must not silently change the solver output to make the story funnier.
- Missing information must be surfaced as an assumption rather than presented as a fact.

## What the user can write

Examples:

> У нас двое детей. Один спокойный, второй подросток и на просьбы часто делает наоборот. Ипотека 1450 в месяц, общий доход около 5000, резерв 9000. В последнее время напряжение среднее, но мы нормально разговариваем. Жена долго отходит после ссор, я быстрее. Она часто обсуждает всё с подругой и после этого обычно становится спокойнее.

Or even:

> Вроде всё нормально, но денег после ипотеки почти не остаётся, ребёнок упирается, а после разговора с родителями жена обычно заводится сильнее. Что показывает ваша схема?

The assistant converts this into a scenario without requiring the user to know the internal model.

## Required chat response

Every simulated answer should contain four sections.

### 1. Как я понял ситуацию

Short factual restatement in family language.

Do not add invented events.

### 2. Допущения компилятора

Only the parameters that were not directly numeric in the user's message.

Example:

```text
"напряжение среднее" -> напряженность = 0.50
"нормально разговариваем" -> качество проводника = 0.75
"долго отходит" -> накопленная память = 0.70
"подруга помогает успокоиться" -> сброс через антенну = 0.65
                              согласование собеседника = 0.80
```

This section is important: it keeps the joke/model inspectable.

### 3. Расчёт

Show the most useful solver values, normally:

- total R;
- L and C;
- |Z|;
- interaction current;
- phase;
- resonance frequency;
- damping;
- antenna dump;
- memory state;
- monthly income;
- monthly load;
- monthly surplus/deficit;
- reserve/runway;
- mortgage debt trend;
- optofinancial contribution if present.

Do not dump every internal field unless asked.

### 4. Перевод обратно на семейный язык

Explain the computed result using RLC-family terminology.

Example:

> Контур устойчив, но индуктивный: реакция запаздывает. Основная проблема сейчас не в RLC-ядре, а в финансовой нагрузке. Антенна согласована хорошо и реально работает как демпфер: разговор с подругой выводит часть накопленной энергии наружу вместо возврата её в семейный контур.

## Qualitative normalization

When the user gives words instead of numbers, use this default scale.

| Phrase | Normalized value |
|---|---:|
| почти нет / очень низкое | 0.10 |
| низкое | 0.25 |
| ниже среднего | 0.40 |
| среднее / обычно | 0.50 |
| выше среднего | 0.65 |
| высокое | 0.75 |
| очень высокое | 0.90 |
| почти максимальное | 0.97 |

These are **compiler conventions**, not measured psychological quantities.

Context may reverse the meaning before normalization. For example:

- "хорошо разговариваем" means high `качество_проводника`;
- "плохо разговариваем" means low `качество_проводника`;
- "сильно фильтрует чужое мнение" means high `фильтр_критического_мышления`;
- "впитывает всё подряд" means low filter and/or high antenna gain.

## Default assumptions

Use defaults only when the quantity matters to the requested calculation.

Recommended neutral defaults:

```text
мужская_емкость = 0.50
женская_индуктивность = 0.50
напряженность = 0.50
частота_событий = 1.00
накопленная_память = 0.20
подростковая_нелинейность = 0.00

качество_проводника = 0.70
усиление_эмоций = 1.00
фильтр_критического_мышления = 0.70
усиление_антенны = 0.50
внешний_фон = 0.20
сброс_через_антенну = 0.20
согласование_собеседника = 0.50
```

For financial values, do **not** invent currency amounts. If income, mortgage, reserve or expenses materially matter and are absent, either:

1. omit the financial subsystem from the interpretation, or
2. state that a purely relational calculation is being performed.

## Confidence

Each inferred parameter should carry an informal confidence:

- **high** — explicitly stated or nearly numeric;
- **medium** — clear qualitative wording;
- **low** — interpretation required.

Low-confidence assumptions that materially affect the answer should be highlighted.

## Chat-to-solver transport

The assistant compiles the user's message into the same JSON accepted by the CLI and pipes it to the solver through stdin:

```bash
cat compiled_scenario.json | \
  python3 simulator/rlc_family_sim.py - --out out/chat-run --json
```

The dash means: read the compiled scenario from stdin.

This keeps the chat interface separate from the deterministic calculation engine.

## Example compiled scenario

User says:

> Двое детей, второй подросток. Общаемся нормально. После ссор жена отходит долго. Ипотека 1400, доход 5000, обязательные расходы ещё 2400, резерв 8000. Разговор с подругой обычно помогает ей успокоиться.

Compiler:

```json
{
  "название": "Chat scenario",
  "отношения": {
    "мужская_емкость": 0.50,
    "женская_индуктивность": 0.65,
    "сопротивление_детей": [0.45, 0.70],
    "топология_детей": "последовательно",
    "напряженность": 0.50,
    "частота_событий": 1.00,
    "накопленная_память": 0.75,
    "подростковая_нелинейность": 0.70
  },
  "связь": {
    "качество_проводника": 0.70,
    "усиление_эмоций": 1.00,
    "фильтр_критического_мышления": 0.70,
    "усиление_антенны": 0.50,
    "внешний_фон": 0.20,
    "сброс_через_антенну": 0.70,
    "согласование_собеседника": 0.80
  },
  "финансы": {
    "доходы_в_месяц": [5000],
    "ипотека_в_месяц": 1400,
    "базовые_расходы_в_месяц": 2400,
    "прочие_расходы_в_месяц": 0,
    "резерв": 8000
  },
  "моделирование": {
    "месяцев": 12
  }
}
```

The important part is not these exact numbers; the important part is that the assumptions are visible before calculation.

## Conversation rule

The normal workflow should now be:

> **User tells a story. RLC-family builds the circuit.**

The JSON and pseudo-SPICE layers remain available for inspection, but they are implementation details unless the user asks to see them.
