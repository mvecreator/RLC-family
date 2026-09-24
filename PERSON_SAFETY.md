# PERSON-SAFETY1 — накопление нагрузки и медицинские guardrails

> Этот слой не диагностирует психическое расстройство и не вычисляет вероятность психоза.

## Зачем

PERSON-SOLO1 уже фиксирует:

- эффективный 25-часовой фазовый дрейф;
- постепенный переход от одного сна к двум примерно равным фазам;
- 2–3 часа бодрствования между ними;
- внешний forcing от кофе/проектной нагрузки;
- минимальный break-even бюджет с малым резервом.

Но одного мгновенного RLC-отклика недостаточно. Нужна отдельная медленная переменная:

```text
stress_load(t) ∈ [0,1]
```

которая показывает накопление нагрузки во времени.

## Не медицинская шкала

`stress_load` — внутренний engineering index.

Он НЕ означает:

```text
0.7 = 70% psychosis
0.8 = psychiatric diagnosis
```

Такие интерпретации запрещены контрактом слоя.

## Компоненты

Текущий прототип использует четыре независимых вклада:

```text
phase_instability
sleep_fragmentation
financial_load
forcing_load
```

и собирает:

```text
combined_daily_load
  = 0.25*phase
  + 0.30*fragmentation
  + 0.20*financial
  + 0.25*forcing
```

Коэффициенты пока являются калибровочными гипотезами проекта.

## Накопление

Дискретная медленная динамика:

```math
s_{t+1}
=
s_t
+
aL(1-s_t)
-
rs_t.
```

Здесь:

- `L` — суммарная ежедневная нагрузка;
- `a` — накопление;
- `r` — восстановление;
- `(1-s)` — насыщение.

Это позволяет получить не мгновенный warning, а последовательность:

```text
normal
 -> accumulating
 -> sustained elevated load
 -> care signal
```

## Care ladder

### SELF_MONITOR

Численный индекс показывает устойчивое накопление.

Модель рекомендует:

- уменьшить необязательный forcing;
- защитить восстановление;
- наблюдать сон и повседневное функционирование.

### GP_REVIEW

Для длительно сохраняющейся необычной архитектуры сна плюс устойчивой нагрузки слой поднимает плановый сигнал обращения к врачу/GP.

Важно: внутренний 14-дневный guardrail — консервативное инженерное правило проекта, а не медицинский диагностический порог.

### URGENT_MEDICAL_REVIEW

Этот уровень НЕ выводится из RLC.

Он включается только при явно сообщённых clinical red flags, например:

```text
hallucinations = true
delusions = true
confused_or_disordered_thinking = true
```

Тогда numeric score игнорируется как основание для задержки медицинской оценки.

### EMERGENCY

Отдельный override:

```text
cannot_keep_self_safe = true
risk_of_harm_to_self_or_others = true
```

Тогда модель рекомендует немедленную экстренную помощь.

## Очень важный принцип

Отсутствующий clinical flag означает:

```text
UNKNOWN
```

а не:

```text
FALSE
```

Поэтому модель не имеет права писать «признаков психоза нет» только потому, что пользователь их не вводил.

## Текущая историческая калибровка

При текущих гипотезах исторический daily-coffee + project forcing даёт ориентировочно:

```text
stress_load day 0  ≈ 0.20
stress_load day 7  ≈ 0.51
stress_load day 14 ≈ 0.546
long-run plateau   ≈ 0.55
```

Редкий текущий кофе при той же гипотетической project load даёт немного меньшую forcing-компоненту.

Эти числа показывают только поведение внутренней динамики.

## Gates

```text
SAFE01 stress accumulates gradually under sustained load
SAFE02 sparse coffee forcing < daily coffee forcing, all else equal
SAFE03 persistent sleep disruption can raise GP_REVIEW guardrail
SAFE04 explicit psychosis-type red flag overrides numeric score
SAFE05 emergency safety flag overrides all other states
SAFE06 missing red flags remain UNKNOWN, never auto-FALSE
SAFE07 psychosis probability is never computed
SAFE08 deterministic replay
```

## Связь с SOLO2

PERSON-SOLO2 должен передавать в SAFETY1 динамический split-state:

```text
phase oscillator
    +
sleep split-state
    +
forcing
    +
finance
        ↓
PERSON-SAFETY1
        ↓
accumulated load + care ladder
```

То есть следующий шаг — заменить текущий статический fragmentation proxy на реальную траекторию возникновения второго sleep-window.
