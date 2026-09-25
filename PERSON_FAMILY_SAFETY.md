# PERSON-FAMILY-SAFETY1 — накопленный стресс семьи и риск разрыва связей

> Это инженерный safety-layer над PERSON-TIME2. Он не предсказывает развод, не оценивает совместимость и не является психологической диагностикой.

## Зачем

PERSON-TIME2 уже считает отдельные состояния людей и токи конкретных связей. Но мгновенного снимка недостаточно, чтобы отличить:

- единичную сильную ссору, после которой связь восстанавливается;
- длительную слабую перегрузку, которая день за днём разрушает канал;
- семейный стресс, пришедший извне — например, из финансового давления;
- устойчивое разъединение конкретной пары при относительно нормальном состоянии остальных связей.

Поэтому PERSON-FAMILY-SAFETY1 вводит два медленных уровня:

```text
person_load[p](t)
link_strain[p,q](t)
```

## Индивидуальная нагрузка

Для каждого человека мгновенный load собирается из:

```text
local excitation
individual memory
incident poor-link stress
financial stress
```

После этого он интегрируется с накоплением и восстановлением.

Смысл: один сильный день не обязан давать высокий accumulated load, но повторяющиеся события постепенно накапливаются.

## Нагрузка связи

Для каждой связи p↔q учитываются:

```text
communication_quality
hostility
interaction under relational friction
mean memory of both people
voltage/state gap
financial background
```

При LINK-SEM1 низкие `contact_frequency` и `availability` уменьшают транспорт, но сами по себе не считаются конфликтом.

Важно:

> большой ток связи сам по себе не является конфликтом.

Хороший канал может проводить большой ток именно потому, что люди активно взаимодействуют.

Стресс взаимодействия увеличивается прежде всего, когда интенсивный обмен идёт через деградировавший канал.

## Динамика накопления

Используется ограниченная медленная динамика вида:

```math
s(t+dt)
=
s(t)
+
dt * a * L(t) * (1-s(t))
-
dt * r * s(t)
```

где:

- L(t) — текущая нагрузка;
- a — скорость накопления;
- r — восстановление;
- s — accumulated load / strain.

Это позволяет наблюдать не только пик, но и:

```text
accumulation
plateau
recovery
failure to recover
```

## Уровни сигналов связи

### LINK_STRAIN

Связь входит в устойчивую накопленную нагрузку.

Это ещё не означает угрозу разрыва.

### RELATIONSHIP_REPAIR_REVIEW

Если accumulated strain держится выше рабочего диапазона, модель рекомендует осознанную repair-попытку:

- снизить необязательную внешнюю нагрузку;
- создать низкоконфликтное окно разговора;
- не повторять тот же спор сразу, если memory обоих высока;
- при повторяющемся цикле рассмотреть квалифицированного relationship counsellor.

### BREAKDOWN_RISK_REVIEW

Если strain продолжает накапливаться и остаётся высоким:

```text
BREAKDOWN_RISK_REVIEW
```

означает:

> связь находится в устойчивой высоконагруженной области и следует проверить, восстанавливается ли она вообще или постепенно размыкается.

Это НЕ:

```text
вероятность развода
предсказание расставания
оценка совместимости
```

Численная вероятность разрыва в модели прямо запрещена.

## Причины сигнала

Каждый link summary сохраняет средние компоненты:

```text
communication_quality
contact_frequency
availability
hostility
relational_friction
stressed_interaction
memory_mean
voltage_gap
financial_stress
```

Поэтому рекомендация должна объяснять происхождение нагрузки.

Например:

```text
основной вклад = financial_stress
-> сначала уменьшить общую внешнюю нагрузку

основной вклад = poor_communication
-> защищать качество коммуникационного канала

основной вклад = hostility
-> сначала снижать враждебность, а не просто увеличивать объём контакта

основной вклад = high memory
-> дать восстановление перед повторным конфликтом
```

## Отдельный safety override

Если явно сообщается:

```text
violence_or_threats = true
coercive_control = true
fear_for_safety = true
```

то включается:

```text
SAFETY_FIRST
```

Совместная оптимизация/repair-рекомендации не должны задерживать обращение за индивидуальной профессиональной или экстренной помощью.

Как и в PERSON-SAFETY1, отсутствующий flag означает UNKNOWN, а не автоматически FALSE.

## Chat / ProblemSpec

Запрос:

> Покажи, накапливается ли у нас стресс и есть ли связь, которая движется к разрыву.

LLM компилирует:

```json
{
  "type": "family_safety",
  "timeline": {
    "моделирование": {...},
    "события": [...]
  }
}
```

При необходимости:

```json
{
  "type": "family_safety",
  "relationship_flags": {
    "fear_for_safety": true
  },
  "timeline": {...}
}
```

Решение берётся из `simulator/person_family_safety.py`.

## Пример sustained stress

`examples/person_family_stress_timeline.json` содержит 30-дневный эксперимент:

1. оба партнёра получают длительную внешнюю нагрузку;
2. их канал на 20 дней деградирует;
3. затем на 9 дней включается repair-window с высоким quality.

Модель должна показать:

```text
link strain grows gradually
-> RELATIONSHIP_REPAIR_REVIEW
-> repair window lowers strain from its peak
```

Текущая калибровка этого умеренно тяжёлого сценария даёт peak strain около `0.59`, то есть он **не обязан** пересекать breakdown-порог `0.65`.

Для отдельного критического gate используются:

```text
examples/person_family_breakdown_scenario.json
examples/person_family_breakdown_timeline.json
```

В нём длительная деградация канала сочетается с высокой накопленной памятью, финансовым фоном и асимметричной внешней нагрузкой. Этот сценарий должен пересечь `0.65` и поднять `BREAKDOWN_RISK_REVIEW`.

То есть разрыв не должен быть однонаправленной судьбой: recovery тоже является частью модели, а breakdown-signal резервируется для более тяжёлого режима.

## Gates

```text
FSAFE01 accumulated link strain grows gradually
FSAFE02 persistent high strain raises RELATIONSHIP_REPAIR_REVIEW
FSAFE03 sustained critical strain can raise BREAKDOWN_RISK_REVIEW
FSAFE04 repair window lowers strain from peak
FSAFE05 high current on a good channel is not conflict
FSAFE06 explicit safety concern overrides joint repair advice
FSAFE07 no relationship-breakdown probability is computed
FSAFE08 deterministic replay
```

## Связь с SOLO safety

Архитектура теперь симметрична:

```text
PERSON-SOLO:
individual RLC
-> sleep / forcing / finance
-> accumulated stress
-> care ladder

FAMILY:
PERSON2 network
-> person loads + link dynamics
-> accumulated person load
-> accumulated relationship strain
-> repair / breakdown-risk guardrails
```

В будущем PERSON-OPT1 должен уметь сравнивать две стратегии не только по мгновенной амплитуде, но и по тому, насколько они уменьшают accumulated person/link state.


## LINK-SEM1

Слой safety использует [LINK-SEM1](LINK_SEMANTICS.md).

Ключевое изменение:

```text
low contact != bad relationship
```

`contact_frequency` и `availability` управляют объёмом/доступностью канала.

`communication_quality` и `hostility` управляют `relational_friction`.

Таким образом редкий, но спокойный контакт не должен сам поднимать repair/breakdown warning.


## PERSON-LOAD-CAL1

Индивидуальный `person_load[p](t)` теперь проходит отдельную калибровку по [PERSON-LOAD-CAL1](PERSON_LOAD_CALIBRATION.md).

Для каждого члена семьи summary содержит:

```text
band
peak_load
final_load
first_recovery_attention_day
first_sustained_load_review_day
first_high_load_review_day
dominant_mean_component
mean_components
recommendations
```

Текущая лестница:

```text
STABLE
RECOVERY_ATTENTION
SUSTAINED_LOAD_REVIEW
HIGH_LOAD_REVIEW
```

Сильные уровни требуют не только пересечения порога, но и dwell-time.

Отдельно учитывается `forcing_exposure`: длительная адресная нагрузка не должна исчезать из person-load только потому, что RLC voltage успел адаптироваться.

Для детей действия формулируются через caregiver-review, а не как требование к ребёнку самостоятельно исправлять семейную нагрузку.

Отчёт по всем членам семьи:

```bash
python3 simulator/family_member_load_report.py \
  examples/person_family_scenario.json \
  examples/person_family_timeline.json \
  --out out/member-loads
```


## MULTI-LINK1 branch and pair summaries

When two people have several parallel channels, PERSON-FAMILY-SAFETY1 keeps accumulated strain independently for each `link_id`.

It also exposes pair-level aggregates:

```text
branches
branch_count
peak_total_current_abs
peak_total_dissipation_power_proxy
peak_max_branch_strain
highest_strain_branch
```

Incident person load combines parallel branch contributions with:

```math
1-prod_b(1-x_b)
```

which preserves the old single-link value exactly and prevents additional channels from artificially diluting stress by averaging.


## CHANNEL-COUPLING1 provenance

PERSON-FAMILY-SAFETY1 carries `channel_coupling_effects` from PERSON-TIME2 into the accumulated trajectory.

The summary reports per coupling:

```text
source_link_id
target_link_id
target_field
peak_abs_delta
mean_abs_delta
first_active_day
```

This is explanatory provenance for the declared simulation rule, not evidence of real-world causality.


## RHYTHM-25H1 and initial load

PERSON-FAMILY-SAFETY1 propagates the current rhythm state from PERSON-TIME2.

It also supports person-specific:

```text
initial_accumulated_load
```

instead of forcing every person to start from the same PERSON-LOAD1 baseline.

This is independent of intrinsic-day period. A 24h person may start with more accumulated load than a 25h person.


## ACOUSTIC-INDUCTION1 forcing exposure

Family Safety includes `acoustic_total_drive` in forcing exposure while preserving event/acoustic provenance separately.

This allows repeated audible environmental input to contribute to accumulated-load dynamics without inventing a direct social interaction link.
