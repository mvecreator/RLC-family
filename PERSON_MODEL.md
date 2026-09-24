# PERSON2 — смешанная RLC-модель персонажей

> Статус: PERSON2 compiler и PERSON-NET1 реализованы. PERSON-CAL зафиксирован отдельным gate; legacy CALIB1 остаётся обязательным.

## Зачем

Legacy-модель `мужчина=C`, `женщина=L`, `ребёнок=R` хороша как исходный мем, но слишком груба для смены ролей, разных детей и индивидуальных характеров.

Новый принцип:

> **каждый человек — собственный смешанный RLC-узел.**

## Электрическая архитектура

Для каждого персонажа `p` создаётся параллельный внутренний RLC:

```text
person p:
  Rp || Cp || Lp
```

Связь между двумя людьми задаётся отдельно через `R_pq` и при необходимости через дополнительные coupling/gain элементы.

В сетевой форме:

$$
C_p \dot v_p + \frac{v_p}{R_p} + i_{L,p} + \sum_q \frac{v_p-v_q}{R_{pq}} = u_p(t),
$$

$$
L_p \dot i_{L,p}=v_p.
$$

Так мы разделяем:

```text
R_p   = внутреннее демпфирование персонажа
R_pq  = качество конкретного канала между людьми
```

## Пол и роль — разные параметры

Пол/гендер не должен механически определять C или L. Он может быть только меткой и опциональным legacy comic prior, сохраняющим исходную шутку.

Главным становится `role_vector`:

```text
work_provider
decision_initiative
caregiver
domestic_load
external_activity
recovery_inertia
```

Все значения нормализованы в `[0,1]`.

Ролевой баланс можно задать как:

$$
b_p = \operatorname{clip}\left(\frac{work+decision-care-home}{2},-1,1\right).
$$

После чего:

$$
C_p=C_{base,p}(1+k_C b_p),
$$

$$
L_p=L_{base,p}(1-k_L b_p).
$$

Компоненты всегда ограничиваются положительным диапазоном.

### Муж больше сидит дома с детьми

Рост `caregiver` и `domestic_load` даёт:

```text
C_husband ↓
L_husband ↑
```

### Жена больше работает и ведёт решения

Рост `work_provider` и `decision_initiative` даёт:

```text
C_wife ↑
L_wife ↓
```

То есть роли способны перевернуть исходный гендерный C/L-перевес.

## Legacy gender prior

Вводится:

```text
gender_prior_strength ∈ [0,1]
```

- `0` — пол вообще не влияет, только роль/темперамент;
- около `0.15` — рекомендуемый сатирический default: лёгкий male-C / female-L prior;
- `1` — максимально legacy-режим, близкий к исходной шутке.

Ключевой принцип: **роль сильнее prior**.

## Темперамент

У каждого персонажа есть индивидуальный:

```text
temperament_bias ∈ [-1,1]
+ = C-oriented
- = L-oriented
```

Итоговый баланс:

$$
b_{effective}=b_{role}+g_{legacy}+b_{temperament}.
$$

Это позволяет конкретному человеку полностью переопределить гендерный prior.

## Дети тоже становятся RLC

Ребёнок:

```text
Child = R(age) || C(age, profile) || L(age, profile)
```

Возрастное сопротивление:

$$
m=\operatorname{clip}(age/18,0,1),
$$

$$
R_{child}=R_{min}+(R_{max}-R_{min})(1-m)^p.
$$

То есть по принятой внутри проекта гипотезе сопротивление падает с возрастом.

### Опциональный legacy-профиль ребёнка

Только при `legacy_gender_profile=true` допускается сатирическое правило:

```text
boy:  age ↑ -> C-strength ↑, L-strength ↓, R ↓
girl: age ↑ -> L-strength ↑, C-strength ↓, R ↓
```

Это **не эмпирическое утверждение о детях**, а опциональная внутренняя гипотеза RLC-family.

Темперамент должен иметь право перевернуть этот prior.

## Подростковая нелинейность

Возрастная C/L-эволюция не заменяет NONLIN1. Нелинейность остаётся отдельным параметром и позднее может получать возрастный default с пиком в подростковом диапазоне, но индивидуальное значение имеет приоритет.

## Семья становится сетью

Вместо:

```text
C_man - L_woman - R_children
```

переходим к:

```text
adult A ---- adult B
   |  \      /  |
 child1    child2
```

У каждого узла свой RLC, у каждой связи свой канал. Это позволит моделировать разные связи каждого родителя с каждым ребёнком и внешнее воздействие только на конкретного человека.

## Backward compatibility

Если блока `персонажи` нет, работает старый формат. Если есть `персонажи`, включается PERSON2. Старые CALIB1-тесты остаются обязательными.

## PERSON-CAL перед включением

1. `PCAL01 role beats gender`: муж с сильным caregiving становится более L-oriented относительно собственного baseline.
2. `PCAL02 reverse role`: жена с сильным provider/directive становится более C-oriented.
3. `PCAL03 neutral gender`: при `gender_prior_strength=0` одинаковые роли дают одинаковые RLC независимо от gender label.
4. `PCAL04 weak prior`: сильная роль может полностью перевернуть legacy prior.
5. `PCAL05 child R monotonic`: `R(3)>R(8)>R(13)>R(17)`.
6. `PCAL06 legacy boy`: только в legacy mode C/L ratio растёт с возрастом.
7. `PCAL07 legacy girl`: только в legacy mode L/C ratio растёт с возрастом.
8. `PCAL08 temperament override`: индивидуальный профиль способен перевернуть prior.
9. `PCAL09 positivity`: никакая роль не создаёт C<=0, L<=0 или R<=0.
10. `PCAL10 legacy preservation`: PERSON2 не ломает CALIB1 12/12 для старого формата.

## Рекомендуемый путь

```text
CALIB1
  -> PERSON2 compiler
  -> PERSON-CAL
  -> network / modified nodal analysis solver
  -> SIM-TIME2
```

Главное архитектурное решение:

> **не расширять старую цепь исключениями, а перейти от RLC семьи к сети RLC-персонажей.**

## Реализовано

- `simulator/person_model.py` — компилятор персонажей в смешанные RLC-узлы;
- `simulator/person_calibration.py` — PERSON-CAL;
- `simulator/person_network_solver.py` — комплексный узловой PERSON-NET1;
- `tests/test_person_model.py` и `tests/test_person_network_solver.py` — regression gates;
- `examples/person_family_scenario.json` — пример семьи со смешанными ролями.

Подробнее по калибровке: [PERSON_CALIBRATION.md](PERSON_CALIBRATION.md).
