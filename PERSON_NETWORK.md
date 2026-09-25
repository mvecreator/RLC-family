# PERSON-NET1 — узловой решатель сети персонажей

PERSON-NET1 — первый вычислительный слой поверх PERSON2.

Вместо свёртки семьи в один общий RLC каждый человек остаётся отдельным узлом со своим `R_p || C_p || L_p`, а каждая связь — отдельным сопротивлением `R_pq`.

## Уравнения

Для частоты `omega` персонаж имеет комплексную проводимость:

$$
Y_p(\omega)=\frac1{R_p}+j\omega C_p+\frac1{j\omega L_p}.
$$

Для каждой связи:

$$
G_{pq}=\frac1{R_{pq}}.
$$

Узловая система:

$$
Y_pV_p+\sum_q G_{pq}(V_p-V_q)=I_p.
$$

В матричной форме:

$$
\mathbf Y\mathbf V=\mathbf I.
$$

После решения ток связи:

$$
I_{pq}=\frac{V_p-V_q}{R_{pq}}.
$$

## Что означает ток связи

`I_pq` не является «уровнем конфликта». Это количество нормализованного взаимодействия, проходящего через конкретный канал при текущей разности состояний и проводимости канала.

Поэтому хороший канал может иметь большой ток именно потому, что связь хорошо проводит.

Конфликт/стресс должен определяться отдельными состояниями, нелинейностью, памятью и знаком/характером возбуждения, а не просто абсолютным током.

## Источник возбуждения

Общий семейный drive из legacy-слоя распределяется между PERSON2-узлами через `source_weight`.

По умолчанию все персонажи получают одинаковую долю суммарного источника. При необходимости LLM может задать:

```json
{"id":"husband","source_weight":1.0}
```

или, например, временно направить возмущение в один узел в будущей динамической PERSON-TIME2 модели.

## Пример

```bash
python3 simulator/person_network_solver.py \
  examples/person_family_scenario.json \
  --out out/person-net
```

Для текущего примера смешанных ролей компилятор даёт примерно:

| Персонаж | C | L | Ориентация |
|---|---:|---:|---:|
| husband | 1.197 | 1.803 | L-oriented |
| wife | 1.789 | 1.211 | C-oriented |
| son | 1.219 | 0.781 | C-oriented legacy+temperament |
| daughter | 0.919 | 1.081 | L-oriented legacy+temperament |

Первый сетевой расчёт при `omega=1` и текущем семейном drive даёт ориентировочно:

| Персонаж | |V| | phase |
|---|---:|---:|
| husband | 0.1195 | -20.65° |
| wife | 0.1190 | -25.03° |
| son | 0.1162 | -15.72° |
| daughter | 0.1272 | -16.90° |

То есть PERSON2 уже позволяет различать фазу каждого человека вместо одной общей семейной фазы.

## Каналы примера

Для примера рассчитываются отдельно:

```text
husband <-> wife
husband <-> son
husband <-> daughter
wife    <-> son
wife    <-> daughter
son     <-> daughter
```

У каждого канала есть:

- `communication_quality`;
- `contact_frequency`;
- `availability`;
- `hostility`;
- derived `effective_transmission` (compatibility alias `quality`);
- `R_link`;
- комплексный ток;
- амплитуда тока;
- phase;
- `dissipation_proxy`.

## Регрессионные проверки

`tests/test_person_network_solver.py` фиксирует:

1. инвертированные взрослые роли сохраняются в сетевом решении;
2. два идентичных симметрично питаемых узла получают одинаковое напряжение;
3. улучшение качества канала уменьшает разность узловых напряжений;
4. результаты конечны.

## Chat routing

Для вопроса о конкретных людях:

```json
{"type":"person_network"}
```

используется через `simulator/problem_solver.py`.

## Следующий шаг

PERSON-NET1 пока является frequency-domain snapshot.

Следующий слой:

```text
PERSON-TIME2
```

должен интегрировать собственные состояния каждого человека во времени, направлять события в конкретные узлы и отслеживать токи конкретных связей после каждого события.

## Динамическое продолжение

Frequency-domain PERSON-NET1 продолжен моделью [PERSON-TIME2](PERSON_TIME.md), где локальные события адресуются конкретным узлам и связям, а распространение рассчитывается во времени.


## LINK-SEM1 transport

Новые semantic-links компилируются по:

```math
T_{pq}=q_{pq}\sqrt{f_{pq}a_{pq}}
```

и уже `T_pq` задаёт `R_link`.

`hostility` не меняет проводимость напрямую; она используется safety-layer как отдельная семантика.

Legacy `quality` сохраняет старое электрическое поведение.


## Nonlinear LINK-SEMI1 boundary

PERSON-NET1 is a linear frequency-domain nodal solver.

Therefore it accepts `RESISTIVE` links only.

If the PERSON2 graph contains:

```text
DIODE
MOSFET
BREAKDOWN_DIODE
```

PERSON-NET1 rejects the solve and directs the caller to PERSON-TIME2.

This avoids silently linearizing directed/gated social-channel hypotheses into an ordinary resistor network.


## MULTI-LINK1 parallel resistive branches

PERSON-NET1 supports multiple RESISTIVE branches between the same pair.

Each branch contributes its conductance independently:

```math
G_{eq} = sum_b 1/R_b.
```

Every output branch retains its own `link_id`.

If any parallel branch is nonlinear, PERSON-NET1 rejects the solve and the whole network must be evaluated with PERSON-TIME2.
