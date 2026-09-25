# PERSON-TIME2 — адресная динамика сети персонажей

PERSON-TIME2 переводит PERSON2 из частотного снимка в динамическую событийную модель.

## Что теперь моделируется

Для каждого персонажа p интегрируются собственные состояния:

- v_p(t) — локальное узловое возбуждение;
- i_L,p(t) — ток индуктивной ветви;
- m_p(t) — индивидуальная память.

Параллельно продолжают считаться общий финансовый резерв и ипотечный долг.

Состояние семьи больше не сворачивается в одну переменную.

## Уравнения

Для каждого узла:

$$
C_p \frac{dv_p}{dt}
=
u_p(t)
-
\frac{v_p}{R_p}
-
i_{L,p}
-
\sum_q \frac{v_p-v_q}{R_{pq}},
$$

$$
L_p \frac{di_{L,p}}{dt}=v_p.
$$

Память:

```text
dm_p/dt
  = local excitation
  + link-flow contribution
  + poor-link stress
  + financial stress
  - local recovery
```

Финансы:

```text
dReserve/dt = (income-load)/days_per_month + impulses
dDebt/dt    = rate*Debt - mortgage_flow
```

## Адресные события

Событие может быть направлено на конкретного персонажа:

```json
{
  "id": "boss-call",
  "день": 1,
  "длительность_дней": 0.4,
  "персонаж": "wife",
  "добавить_возбуждение": 0.45,
  "импульс_памяти": 0.04
}
```

Тогда прямой источник получает только узел wife.

Другие персонажи реагируют только через каналы связи.

Событие может быть направлено на конкретную связь:

```json
{
  "id": "father-son-channel",
  "день": 2,
  "длительность_дней": 1,
  "связь": ["husband", "son"],
  "качество_связи": 0.25
}
```

Это меняет только данный R_pq.

## Важный физический выбор начального состояния

PERSON-NET1 возвращает комплексный frequency-domain phasor.

Его нельзя напрямую использовать как временное начальное состояние.

PERSON-TIME2 поэтому стартует из собственного равновесия постоянного входа:

```text
v_p(0) = 0
i_L,p(0) = baseline injected current
```

Это устраняет ложный стартовый transient.

Любой последующий пик создаётся событием или изменением системных параметров.

## Индивидуальная память

По умолчанию каждый персонаж получает начальную память из:

```text
отношения.накопленная_память
```

Но можно переопределить:

```json
{
  "id": "wife",
  "initial_memory": 0.55
}
```

Импульс памяти обязательно должен иметь target_person.

## Передача возмущения

В двухузловом калибровочном примере локальный импульс на A дал приблизительно:

```text
peak |v_A| ≈ 0.082
peak |v_B| ≈ 0.018
```

То есть источник остаётся локальным, но возмущение распространяется по сети.

При улучшении качества канала:

```text
quality = 0.20 -> receiver peak ≈ 0.010
quality = 0.90 -> receiver peak ≈ 0.027
```

Хороший канал передаёт больше взаимодействия.

Это не значит, что высокий ток связи автоматически плох: ток — интенсивность обмена.

## PERSON-TIME-CAL

Отдельный calibration layer фиксирует восемь направлений:

1. PTCAL01 — без событий нет самопроизвольного voltage transient;
2. PTCAL02 — адресный импульс сильнее всего возбуждает target node;
3. PTCAL03 — хороший канал передаёт больше сигнала receiver node;
4. PTCAL04 — memory impulse в t=0 меняет только target person;
5. PTCAL05 — временное изменение связи действует только на target link и затем откатывается;
6. PTCAL06 — при нулевом financial stress денежный импульс меняет reserve, но не person memory;
7. PTCAL07 — финансовый stress действует как общий фон;
8. PTCAL08 — повторный запуск детерминирован.

Запуск:

```bash
python3 simulator/person_time_calibration.py
```

## Пример

```bash
python3 simulator/person_time_solver.py \
  examples/person_family_scenario.json \
  examples/person_family_timeline.json \
  --out out/person-time
```

Выход:

```text
out/person-time/
├── person_timeline_result.json
├── person_timeline_report.md
├── person_nodes.csv
└── person_links.csv
```

CSV предназначены для графиков, ноутбуков, LLM и будущего мобильного клиента.

## Chat mode

LLM может собрать:

```json
{
  "type": "person_timeline",
  "timeline": {
    "моделирование": {...},
    "события": [...]
  }
}
```

и передать это через problem_solver.

Пример естественного запроса:

> В понедельник начальник позвонил жене. Во вторник отец поссорился с сыном, потом они почти сутки плохо разговаривали. На третий день они спокойно поговорили. Покажи, как возмущение прошло через семью.

LLM должна:

1. определить target_person и target_link;
2. явно показать численные допущения;
3. не возбуждать всю семью напрямую;
4. запустить PERSON-TIME2;
5. вернуть пики каждого человека, динамику памяти и токи связей;
6. перевести результат обратно в семейный язык.

## Следующие gates

- PERSON-TIME3 — постоянные/затухающие/периодические формы событий;
- PERSON-HYST1 — индивидуальные hysteresis/memristive memories;
- PERSON-SUPPORT1 — адресные внешние support/antenna nodes;
- PERSON-COMPARE1 — сравнение двух временных стратегий;
- PERSON-OPT1 — поиск стабилизирующих действий по узлам и каналам;
- PERSON-PLOT1 — канонические графики распространения по сети.

## Главный контракт

> **Событие происходит с конкретным человеком. Сеть решает, кто почувствует его дальше.**


## LINK-SEM1 dynamic events

Помимо legacy `качество_связи`, PERSON-TIME2 умеет временно менять отдельные семантики канала:

```text
communication_quality_set / _add
contact_frequency_set / _add
availability_set / _add
hostility_set / _add
```

Пример временной недоступности без конфликта:

```json
{
  "id": "work-trip",
  "день": 2,
  "длительность_дней": 5,
  "связь": ["husband","wife"],
  "availability_set": 0.20
}
```

Пример конфликтного окна:

```json
{
  "id": "argument",
  "день": 4,
  "длительность_дней": 0.5,
  "связь": ["husband","wife"],
  "communication_quality_set": 0.35,
  "hostility_set": 0.80
}
```

Mutation semantic-link без явного `target_link` отклоняется.


## LINK-SEMI1 gate events

PERSON-TIME2 executes nonlinear link currents through LINK-SEMI1.

Supported nonlinear link types:

```text
DIODE
MOSFET
BREAKDOWN_DIODE
```

For MOSFET links, timeline events may change:

```text
gate_set
gate_add
```

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

Gate mutation on non-MOSFET links is rejected.

Each sampled link now exposes:

```text
element_type
gate
delta_v
instantaneous_conductance
current
power_vi_proxy = |delta_v * current|
```


## MULTI-LINK1 branch addressing

PERSON-TIME2 supports multiple branches between the same endpoints.

Every sampled branch exposes:

```text
link_id
pair_id
channel_kind
parallel_branch_count
```

When a pair has exactly one branch, legacy `target_link` addressing remains valid.

When a pair has multiple branches, pair-only addressing is rejected as ambiguous and the event must use:

```text
target_link_id
```

All branch currents are summed into the PERSON2 node equation.


## CHANNEL-COUPLING1 execution

PERSON-TIME2 is the authoritative solver for coupled channels.

At each RK4 evaluation:

```text
1. compile event-adjusted links;
2. freeze all CHANNEL-COUPLING1 source signals;
3. accumulate target deltas simultaneously;
4. refresh LINK-SEM1 semantics where needed;
5. evaluate LINK-SEMI1 currents;
6. integrate PERSON2 node states.
```

Every sample exposes:

```text
channel_coupling_effects
```

with source, target, activation and signed delta provenance.

Rule ordering in scenario JSON cannot change same-instant results.


## RHYTHM-25H1 intrinsic-day phase

PERSON-TIME2 now carries per-person rhythm metadata.

At every derivative evaluation, the solver computes the phase mismatch between the person's declared intrinsic cycle and the external schedule.

With `schedule_lock=0`, rhythm does not alter the dynamics.

With non-zero schedule locking, the mismatch contributes:
- an explicit memory-load term;
- an additional recovery-inertia term.

Every node sample exposes the full rhythm state, including relative phase and daily drift.


## ACOUSTIC-INDUCTION1 environmental forcing

PERSON-TIME2 can compile `acoustic_induction.couplings` from the scenario and `acoustic_sources` from the timeline.

At every RK4 evaluation:

```math
u_p = u_{base,p} + u_{event,p} + T s(t) + M_a \dot{s}(t)
```

Node samples expose:
- acoustic_direct_drive;
- acoustic_inductive_drive;
- acoustic_total_drive.

Sample-level `acoustic_effects` keeps source/coupling provenance.
