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


---

## Query-driven problem solving

После описания ситуации пользователь может задавать вычислимые вопросы:

- «Что сильнее всего выводит схему из рабочего режима?»
- «Что будет, если улучшить качество общения?»
- «Какой доход нужен для безубыточности?»
- «Какой резерв нужен на 6 месяцев?»
- «При какой частоте событий фазовый сдвиг станет нулевым?»
- «Какие два изменения сильнее всего приблизят модель к устойчивому режиму?»

LLM должна компилировать такой вопрос в `ProblemSpec` по правилам [HARMONY_ENGINE.md](HARMONY_ENGINE.md), после чего численный ответ берётся из `simulator/problem_solver.py`.

Для `harmonize` LLM не должна превращать поиск в советы по контролю, изоляции, финансовому ущербу или намеренному раскачиванию реальных людей. Базовая цель — устойчивость, снижение перегрузки и улучшение качества каналов.


---

## Динамические запросы во времени

Если пользователь описывает последовательность событий, LLM должна использовать [TIME_ENGINE.md](TIME_ENGINE.md), а не сводить историю к одному статическому снимку.

Пример запроса:

> В понедельник мы поссорились, потом два дня почти не разговаривали. В четверг пришла зарплата, в пятницу позвонила мать и всё снова завелось, а в воскресенье я поговорил с другом. Что происходило с системой в течение недели?

Рабочий поток:

```text
естественный рассказ
→ факты + прозрачные допущения
→ FamilyScenario + TimelineSpec
→ simulator/time_solver.py
→ trajectory
→ пики / восстановление / память / финансы
→ семейная интерпретация
```

При наличии времени/порядка событий LLM не должна придумывать статический эквивалент, если динамический расчёт доступен.


---

## Запросы о конкретных персонажах

Если сценарий содержит блок `персонажи` и вопрос относится к конкретным членам семьи или связям между ними, LLM должна использовать PERSON2/PERSON-NET1 вместо сворачивания всей семьи в один legacy RLC.

Примеры:

- «У кого сейчас самая большая амплитуда?»
- «Какой канал между людьми несёт максимальный ток?»
- «Насколько расходятся фазы мужа и жены?»
- «Что изменится, если улучшится связь отца с сыном?»

Для общего сетевого снимка:

```json
{"type":"person_network"}
```

Численный ответ берётся из `simulator/person_network_solver.py`, а LLM только переводит его обратно в семейный язык.


---

## Адресная динамика PERSON-TIME2

Если пользователь называет конкретных людей и последовательность событий, LLM должна сохранять адресность.

Пример:

> Начальник позвонил жене. На следующий день отец поссорился с сыном, после чего именно их канал ухудшился. Потом они поговорили.

Компиляция:

```text
event -> target_person
или
event -> target_link
```

а не:

```text
event -> вся семья
```

Для расчёта используется:

```json
{
  "type": "person_timeline",
  "timeline": {
    "моделирование": {},
    "события": []
  }
}
```

Численный результат берётся из [PERSON-TIME2](PERSON_TIME.md). LLM должна отдельно показывать, какое событие к какому узлу/каналу было привязано.


---

## Накопленный семейный стресс и риск разрыва

Если пользователь спрашивает не только о текущем состоянии, но о том, **накапливается ли стресс, восстанавливаются ли конкретные связи и есть ли ранние признаки их разрыва**, LLM должна использовать [PERSON-FAMILY-SAFETY1](PERSON_FAMILY_SAFETY.md).

ProblemSpec:

```json
{
  "type": "family_safety",
  "timeline": {
    "моделирование": {},
    "события": []
  }
}
```

Ответ должен разделять:

1. accumulated load конкретных людей;
2. accumulated strain конкретных связей;
3. причины strain;
4. ранние repair-рекомендации;
5. `BREAKDOWN_RISK_REVIEW`, если конкретная связь длительно остаётся в высокой нагрузке.

Запрещено переводить этот сигнал в:

- «вероятность развода X%»;
- «вы обязательно расстанетесь»;
- оценку психологической совместимости.

Высокий ток хорошего канала сам по себе не является конфликтом.

Если пользователь явно сообщает угрозы, насилие, принуждение или страх за безопасность, LLM должна передать соответствующий `relationship_flags`; `SAFETY_FIRST` имеет приоритет над совместной repair/harmonize-рекомендацией.

Для семейного safety-ответа полезный порядок:

```text
что накопилось
-> в каких людях/связях
-> из каких компонентов
-> восстанавливается ли система
-> что можно попробовать снизить первым
-> нужен ли repair review / breakdown-risk review
```


---

## Нагрузка каждого члена семьи

Если вопрос относится к тому, **кто именно в семье сейчас перегружен**, LLM должна использовать PERSON-FAMILY-SAFETY1 + PERSON-LOAD-CAL1 и показывать отдельный результат для каждого PERSON2 node.

Минимальный ответ по человеку:

```text
person
band
peak/final load
dominant load component
first sustained crossing if any
recommendations
```

Компоненты:

```text
excitation
memory
incident_link_stress
financial_stress
forcing_exposure
```

Нельзя переносить warning одного человека на остальных без расчёта их собственных состояний.

Для ребёнка `RECOVERY_ATTENTION` и более сильные уровни должны переводиться в caregiver-facing рекомендацию.

Person-load является инженерным индексом проекта и не должен называться психологическим или медицинским диагнозом.


---

## Перегрев и сценарии восстановления

Если пользователь спрашивает:

- «мы перегреваемся?»;
- «какая связь сейчас горячая?»;
- «хватит ли выходных?»;
- «что изменится, если взять неделю отпуска?»;
- «лучше сразу всё обсуждать или сначала остыть?»,

LLM должна использовать:

```text
family_thermal
recovery_scenarios
```

`family_thermal` возвращает:

```text
person heat
person recovery debt
link I^2R dissipation
link heat
link damage
thermal bands
```

`recovery_scenarios` сравнивает только заявленные гипотетические mechanism bundles.

Рекомендуемый формат ответа:

```text
что нагрето
-> почему
-> остывает ли уже
-> сколько recovery debt осталось
-> какие сценарии дают больше/меньше охлаждения
-> какие допущения были использованы
```

Нельзя переводить внутренние thermal-state в медицинские утверждения или вероятность разрыва отношений.

Фраза «нужен отпуск» допустима только в инженерном смысле вроде:

> В текущей модели короткая разгрузка не возвращает состояние в комфортный диапазон; имеет смысл сравнить более длительный low-demand сценарий.

Нельзя утверждать, что конкретное место отдыха само по себе имеет доказанный коэффициент восстановления.


---

## Нелинейные социальные каналы LINK-SEMI1

Нельзя выбирать электрический элемент только по названию социальной роли.

Не:

```text
работодатель = MOSFET всегда
друг = DIODE всегда
коллега = RESISTOR всегда
```

Вместо этого LLM должна определить структуру канала:

```text
симметричный пассивный обмен
  -> RESISTIVE

сильно направленный обмен
  -> DIODE

канал управляется внешним разрешением/властью/контрактом
  -> MOSFET

обратная реакция подавлена до порога
  -> BREAKDOWN_DIODE
```

Для employer→employee MOSFET является первым калибровочным примером, когда пользователь явно задаёт внешний gate, например:

```text
authority
contract obligation
job dependency
institutional permission
```

`gate` нельзя описывать как «послушность» или скрытую характеристику личности.

Для нелинейных каналов использовать PERSON-TIME2, а не PERSON-NET1.

При объяснении нагрева использовать:

```math
P=|\Delta V I|
```

и только для RESISTIVE можно эквивалентно писать `I^2R`.


---

## Параллельные каналы MULTI-LINK1

Если между двумя людьми существует несколько существенно разных взаимодействий, не сводить их автоматически к одной "связи".

Пример:

```text
работодатель <-> сотрудник

personal
institutional_work
```

Для нескольких ветвей использовать явные `link_id`.

Старый pair-target:

```text
target_link = ["a","b"]
```

разрешён только когда между `a` и `b` одна ветвь.

Если ветвей несколько, LLM должна использовать:

```text
target_link_id = "employer-employee.work"
```

и объяснять результат на двух уровнях:

```text
branch:
  какой конкретный канал нагрет/напряжён

pair:
  каков суммарный ток/диссипация между людьми
```

Нельзя говорить "отношения плохие", если, например:

```text
personal channel = COMFORT
work channel = OVERHEATED
```

Нужно назвать именно канал.


---

## Межканальное влияние CHANNEL-COUPLING1

Если пользователь хочет моделировать влияние одного канала на другой, LLM не должна автоматически связывать их по социальной роли.

Нужно объявить явное правило:

```text
source_link_id
source_signal
threshold
gain
target_link_id
target_field
```

Пример:

```text
work |VI| power
  -> personal communication_quality
```

В ответе всегда различать:

```text
наблюдаемое состояние канала
vs
гипотетический coupling rule
```

Если coupling дал вклад, объяснять:

```text
какое правило
какой source signal
какой threshold
какой signed delta
какое target field
```

Не говорить «работа разрушает личные отношения» как факт.

Корректнее:

> В этом сценарии объявлено правило, по которому высокий work-channel power снижает personal communication quality; на данном участке оно дало delta = ...

Cross-pair coupling между разными парами людей должен использовать явное `allow_cross_pair=true`.

Накопленный LINK-THERM heat/damage пока не является source CHANNEL-COUPLING1. Для этого нужен отдельный THERMAL-FEEDBACK1.


---

## Соседские/household сети NEIGHBOR-NET1

Для повторяющихся внешних событий вокруг одного центрального человека использовать `neighbor_network`.

Разделять:

```text
наблюдаемое событие
внутренняя структура household
меж-household связи
центральный накопительный отклик
intervention marker
```

Можно моделировать household как:

```text
solo
couple
couple + adult child
другая явно заданная группа
```

Если событие наблюдается на уровне квартиры/household, но неизвестен конкретный человек, использовать `source_group_id`.

Суммарная amplitude не умножается на число жильцов; она распределяется по членам группы с весами, сумма которых равна 1.

В отчёте отдельно показывать:

```text
event rate / exposure
temporal alignment
central accumulated load / heat / recovery debt
household equal-input probe
effect of household_internal links
effect of cross_household_social links
pre/post intervention association
counterfactual continuation / no-relief / desynchronization
```

Нельзя превращать temporal alignment или наличие social links в утверждение о согласованном намерении.

Корректно:

> В модели события имеют более высокую временную согласованность и связанная топология меняет центральный отклик.

Некорректно:

> Модель доказала, что люди координировались против центрального человека.

Intervention marker не переписывает post-events автоматически; снижение post activity должно быть задано наблюдаемыми данными.
