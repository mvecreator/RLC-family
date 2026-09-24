# PERSON-SOLO1 — один RLC-персонаж и калибровка режима

> Экспериментальный слой над PERSON2/PERSON-TIME2. Это системная модель, а не медицинская модель сна и не психологическая диагностика.

## 1. Предельный случай сети

PERSON-SOLO1 рассматривает одного человека без межличностных каналов:

```text
solo
└── R || C || L
    ├── external forcing
    ├── individual memory
    ├── finance background
    └── sleep-phase readout
```

То есть PERSON2 остаётся без изменений: человек является полноценным параллельным RLC-узлом.

Для первого baseline используется `gender_prior_strength=0`, чтобы не подгонять персональные параметры под пол.

Текущий baseline компилятора:

```text
R ≈ 0.900
C ≈ 1.690
L ≈ 1.310
C/L ≈ 1.29
```

## 2. Минимальный бюджет

Бюджет намеренно задан в нормализованных единицах:

```text
monthly income                 = 1.00
housing + food                 = 0.90
two entertainment outings     = 0.10
monthly net                    = 0.00
reserve                        = 0.20 month
```

То есть доход покрывает только текущую жизнь и небольшой досуг, но не формирует профицит.

При текущей формуле financial-stress:

```text
runway = 0.20 month
financial_stress ≈ 0.28
```

Это важное различие: break-even денежный поток не равен финансовой устойчивости, если резерв мал.

## 3. Наблюдение A: 25-часовой фазовый дрейф

Исторический режим описан как:

```text
каждый следующий календарный день пробуждение ≈ на 1 час позже
```

В unwrapped-фазе:

```text
day 0 -> +0 h
day 1 -> +1 h
...
day 7 -> +7 h
```

Линейная оценка даёт:

```text
wake drift = +1 h/calendar-day
effective period = 24 h + 1 h = 25 h
```

PERSON-SOLO1 использует это как наблюдаемую эффективную длительность цикла.

## 4. Наблюдение B: постепенное расщепление сна

Дополнительное наблюдение принципиально меняет sleep-layer.

Сон не просто сдвигался целиком. Он:

1. сначала был одним эпизодом;
2. постепенно начал делиться;
3. в дальнейшем образовал две примерно равные части;
4. между двумя частями сформировался промежуток бодрствования примерно 2–3 часа.

Финальное ограничение:

```text
sleep bout A : sleep bout B ≈ 1 : 1
wake gap = 2..3 h
```

При 25-часовом цикле gap занимает:

```text
2/25 = 8%
3/25 = 12%
midpoint = 2.5/25 = 10%
```

Суммарная длительность сна пока неизвестна. Поэтому абсолютная длительность каждой половины не выводится.

## 5. Почему одного фазового синуса недостаточно

Один RLC-осциллятор может задавать общую фазу и переходный отклик.

Но простой threshold одного синусоидального readout обычно даёт один непрерывный sleep-window за цикл. Он не объясняет наблюдаемое:

```text
one sleep bout
    ↓ gradual transition
two approximately equal sleep bouts
    separated by a waking notch
```

Поэтому архитектура разделяется:

```text
RLC core
  -> phase theta(t)

sleep readout
  -> split_state s(t)
  -> sleep/wake mask
```

или эквивалентно через постепенно возникающую вторую гармонику readout.

Ключевой принцип: **25-часовой phase oscillator и расщепление сна — не одна и та же переменная.**

## 6. Следующий конструктивный gate

PERSON-SOLO2 должен реализовать минимальный нелинейный sleep-readout, например:

```math
D(\theta,t)
=
\cos\theta
+
a_2(t)\cos(2\theta+\phi_2)
-
h.
```

где:

- `theta(t)` — фаза 25-часового RLC-цикла;
- `a2(t)` — медленно растущий split-state;
- `h` — sleep threshold;
- финальный режим должен иметь два одинаковых sleep-window;
- центральный wake-notch должен быть 2–3 h;
- при `a2≈0` должен оставаться один sleep-window.

Это даёт проверяемый gate:

```text
SOLO2-01  initial readout is monophasic
SOLO2-02  split emerges continuously, not by manual schedule switch
SOLO2-03  final two sleep bouts are equal within tolerance
SOLO2-04  final waking gap is 2..3 h for T=25 h
SOLO2-05  total sleep duration remains an explicit free parameter until observed
SOLO2-06  coffee/project forcing cannot silently redefine the fitted 25 h period
SOLO2-07  replay is deterministic
```

## 7. Кофе и проекты

Coffee и project intensity остаются внешними forcing-events PERSON-TIME2.

Историческая калибровка пока сравнивает:

```text
old:     effective coffee event every day
current: up to four coffee events per week
```

Это проверяет реакцию одного и того же RLC-узла на различную плотность forcing.

Никакой причинный вывод «кофе создал 25-часовой цикл» из этого не делается.

## 8. Что уже идентифицировано

```text
effective cycle period       ≈ 25 h
final sleep bout count       = 2
final bout ratio             ≈ 1:1
inter-bout wake gap          = 2..3 h
gap fraction of cycle        = 8..12%
budget net                   = 0
reserve/runway               = thin
PERSON2 node                 = R,C,L > 0
```

Не идентифицировано:

```text
total sleep hours per cycle
duration of each sleep bout in hours
rate at which the split emerged
causal contribution of caffeine
causal contribution of project work
physiological interpretation
```

Это и определяет границу следующего исследования.
