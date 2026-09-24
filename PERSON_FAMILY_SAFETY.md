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
poor_quality
interaction under poor quality
mean memory of both people
voltage/state gap
financial background
```

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
poor_quality
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

основной вклад = poor_quality
-> защищать коммуникационный канал

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
-> repair review
-> possible breakdown-risk review
-> repair window lowers strain from its peak
```

То есть разрыв не должен быть однонаправленной судьбой: recovery тоже является частью модели.

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
