#!/usr/bin/env python3
"""RLC-family executable satire: family JSON -> AnalogIR -> solve -> family report."""

from __future__ import annotations
import argparse, cmath, json, math, sys
from pathlib import Path

VERSION = "RLC-FAMILY-SIM-0.1"


class ScenarioError(ValueError):
    pass


def clamp01(v, name):
    try:
        v = float(v)
    except (TypeError, ValueError) as e:
        raise ScenarioError(f"{name}: expected number") from e
    if not 0 <= v <= 1:
        raise ScenarioError(f"{name}: expected [0,1], got {v}")
    return v


def nonneg(v, name):
    try:
        v = float(v)
    except (TypeError, ValueError) as e:
        raise ScenarioError(f"{name}: expected number") from e
    if v < 0:
        raise ScenarioError(f"{name}: expected >=0, got {v}")
    return v


def positive(v, name):
    v = nonneg(v, name)
    if v == 0:
        raise ScenarioError(f"{name}: expected >0")
    return v


def child_resistance(raw, topology):
    values = raw if isinstance(raw, list) else [raw]
    if not values:
        values = [0.05]
    values = [max(0.02, nonneg(v, "отношения.сопротивление_детей")) for v in values]
    if topology == "последовательно":
        return sum(values)
    if topology == "параллельно":
        return 1 / sum(1 / v for v in values)
    raise ScenarioError("топология_детей: use 'последовательно' or 'параллельно'")


def load_text(text):
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ScenarioError(str(e)) from e
    if not isinstance(data, dict):
        raise ScenarioError("scenario root must be an object")
    return data


def load(path):
    if str(path) == "-":
        return load_text(sys.stdin.read())
    try:
        return load_text(Path(path).read_text(encoding="utf-8"))
    except OSError as e:
        raise ScenarioError(str(e)) from e


def compile_scenario(s):
    rel = s.get("отношения", {})
    link = s.get("связь", {})
    fin = s.get("финансы", {})
    if not all(isinstance(x, dict) for x in (rel, link, fin)):
        raise ScenarioError("отношения, связь, финансы must be objects")

    name = str(s.get("название", "Безымянная семейная система"))
    c_score = clamp01(rel.get("мужская_емкость", .5), "мужская_емкость")
    l_score = clamp01(rel.get("женская_индуктивность", .5), "женская_индуктивность")
    tension = clamp01(rel.get("напряженность", .5), "напряженность")
    omega = positive(rel.get("частота_событий", 1), "частота_событий")
    memory = clamp01(rel.get("накопленная_память", .2), "накопленная_память")
    nl = clamp01(rel.get("подростковая_нелинейность", 0), "подростковая_нелинейность")
    topology = rel.get("топология_детей", "последовательно")

    quality = clamp01(link.get("качество_проводника", .7), "качество_проводника")
    amp = nonneg(link.get("усиление_эмоций", 1), "усиление_эмоций")
    filt = clamp01(link.get("фильтр_критического_мышления", .7), "фильтр")
    ant = nonneg(link.get("усиление_антенны", .5), "усиление_антенны")
    bg = clamp01(link.get("внешний_фон", .2), "внешний_фон")
    dump = clamp01(link.get("сброс_через_антенну", .2), "сброс_через_антенну")
    match = clamp01(link.get("согласование_собеседника", .5), "согласование_собеседника")

    C = .35 + 2.65 * c_score
    L = .35 + 2.65 * l_score
    r_child = child_resistance(rel.get("сопротивление_детей", .5), topology)
    r_child *= 1 + nl * max(0, tension - .55) * 5
    r_channel = .10 + 2.40 * (1 - quality)
    r_rad = .05 + 1.75 * dump * match
    filter_tx = max(.05, 1 - .90 * filt)
    v_ext = bg * ant * filter_tx
    v_internal = tension + .30 * memory
    v_total = amp * (v_internal + v_ext)

    incomes = fin.get("доходы_в_месяц", [0])
    if not isinstance(incomes, list):
        raise ScenarioError("доходы_в_месяц must be list")
    income = sum(nonneg(x, "доходы_в_месяц") for x in incomes)

    finance = {
        "income": income,
        "mortgage": nonneg(fin.get("ипотека_в_месяц", 0), "ипотека_в_месяц"),
        "base": nonneg(fin.get("базовые_расходы_в_месяц", 0), "базовые_расходы_в_месяц"),
        "other": nonneg(fin.get("прочие_расходы_в_месяц", 0), "прочие_расходы_в_месяц"),
        "reserve": nonneg(fin.get("резерв", 0), "резерв"),
        "debt": nonneg(fin.get("долг_по_ипотеке", 0), "долг_по_ипотеке"),
        "annual_rate": nonneg(fin.get("ставка_годовая", 0), "ставка_годовая"),
        "light": clamp01(fin.get("свет_возможностей", 0), "свет_возможностей"),
        "coupling": clamp01(fin.get("сопряжение_денежного_луча", .5), "сопряжение_денежного_луча"),
        "loss": clamp01(fin.get("потери_оптики", .1), "потери_оптики"),
        "gain": nonneg(fin.get("усиление_бизнеса", 1), "усиление_бизнеса"),
        "market": nonneg(fin.get("доступный_рынок_в_месяц", 0), "доступный_рынок_в_месяц"),
    }

    components = [
        {"id":"V_REL","kind":"voltage_source","role":"семейная напряжённость","value":v_internal,"unit":"norm"},
        {"id":"V_EXT","kind":"voltage_source","role":"внешний фон после антенны/фильтра","value":v_ext,"unit":"norm"},
        {"id":"GAIN","kind":"gain","role":"эмоциональный усилитель","value":amp,"unit":"x"},
        {"id":"R_CHILD","kind":"resistor","role":"сопротивление детей","value":r_child,"unit":"R*"},
        {"id":"R_CHANNEL","kind":"resistor","role":"потери канала общения","value":r_channel,"unit":"R*"},
        {"id":"R_RAD","kind":"resistor","role":"радиационное демпфирование","value":r_rad,"unit":"R*"},
        {"id":"L_WOMAN","kind":"inductor","role":"женская индуктивность","value":L,"unit":"L*"},
        {"id":"C_MAN","kind":"capacitor","role":"мужская ёмкость","value":C,"unit":"C*"},
        {"id":"MEM","kind":"state","role":"накопленная память","value":memory,"unit":"0..1"},
        {"id":"NL_TEEN","kind":"nonlinearity","role":"подростковая нелинейность","value":nl,"unit":"0..1"},
    ]
    return {
        "model_version": VERSION, "scenario_name": name, "topology": topology,
        "analysis": {"omega_rad_s":omega,"source_voltage":v_internal,
                     "external_voltage":v_ext,"total_drive_voltage":v_total},
        "components": components, "finance": finance,
    }


def cv(ir, cid):
    return next(x["value"] for x in ir["components"] if x["id"] == cid)


def solve_relationship(ir):
    R = cv(ir,"R_CHILD") + cv(ir,"R_CHANNEL") + cv(ir,"R_RAD")
    L, C = cv(ir,"L_WOMAN"), cv(ir,"C_MAN")
    omega = ir["analysis"]["omega_rad_s"]
    X = omega * L - 1/(omega*C)
    Z = complex(R, X)
    zabs = abs(Z)
    current = ir["analysis"]["total_drive_voltage"] / zabs
    phase = -math.degrees(cmath.phase(Z))
    omega0 = 1/math.sqrt(L*C)
    damping = (R/2)*math.sqrt(C/L)
    p_rad = current**2 * cv(ir,"R_RAD")
    memory = cv(ir,"MEM")
    memory_after = max(0,min(1,memory + min(1,.12*ir["analysis"]["total_drive_voltage"]+.08*current) - min(1,.10*p_rad)))
    return {"resistance":R,"inductance":L,"capacitance":C,"reactance":X,
            "impedance_abs":zabs,"current_rms":current,"phase_deg":phase,
            "resonance_omega":omega0,"damping_ratio":damping,
            "radiated_power":p_rad,"memory_after":memory_after}


def solve_finance(ir, months):
    f=ir["finance"]
    optical_eff=f["light"]*f["coupling"]*(1-f["loss"])
    photo=min(f["market"], f["market"]*optical_eff*f["gain"])
    total_income=f["income"]+photo
    load=f["mortgage"]+f["base"]+f["other"]
    net=total_income-load
    reserve_end=f["reserve"]+net*months
    debt=f["debt"]; debt0=debt; interest_paid=principal_paid=0
    mr=f["annual_rate"]/12
    for _ in range(months):
        if debt<=0 or f["mortgage"]<=0: break
        interest=debt*mr
        principal=max(0,min(debt,f["mortgage"]-interest))
        debt=max(0,debt+interest-f["mortgage"])
        interest_paid+=interest; principal_paid+=principal
    runway=f["reserve"]/load if load>0 else math.inf
    return {"explicit_income_monthly":f["income"],"photo_income_monthly":photo,
            "total_income_monthly":total_income,"total_load_monthly":load,
            "net_monthly":net,"reserve_start":f["reserve"],"reserve_end":reserve_end,
            "runway_if_income_lost_months":runway,"mortgage_debt_start":debt0,
            "mortgage_debt_end":debt,"mortgage_interest_paid":interest_paid,
            "mortgage_principal_paid":principal_paid,"beam_coupling_efficiency":optical_eff}


def interpret(rr, fr):
    out=[]; warnings=[]
    i=rr["current_rms"]
    out.append("Ток взаимодействия низкий: схема скорее разомкнута или сильно заторможена." if i<.20
               else "Ток взаимодействия умеренный: обмен идёт без выраженного перегруза." if i<.65
               else "Ток взаимодействия высокий: внутри контура много событий и передачи энергии.")
    p=rr["phase_deg"]
    out.append("Фазовый сдвиг мал: участники близки к согласованному режиму." if abs(p)<12
               else "Контур смещён в индуктивную область: реакция заметно запаздывает относительно возбуждения." if p<0
               else "Контур смещён в ёмкостную область: реакция опережает основной цикл возбуждения.")
    d=rr["damping_ratio"]
    if d<.35: out.append("Демпфирование слабое: одно возмущение может долго звенеть внутри системы."); warnings.append("LOW_DAMPING")
    elif d>1.2: out.append("Демпфирование сильное: система спокойная, но может реагировать тяжеловесно.")
    else: out.append("Демпфирование рабочее: возмущения должны затухать без чрезмерного зависания.")
    out.append("Антенна заметно сбрасывает энергию наружу; внешний канал участвует в стабилизации."
               if rr["radiated_power"]>.15 else
               "Внешний сброс слабый: большая часть энергии остаётся внутри контура.")
    m=rr["memory_after"]
    if m>.70: out.append("Память системы высокая: текущая реакция сильно зависит от предыстории."); warnings.append("HIGH_MEMORY")
    elif m>.35: out.append("Память заметна: одинаковые входы в разные дни могут давать разные ответы.")
    else: out.append("Память невелика: система близка к безынерционному бытовому режиму.")
    n=fr["net_monthly"]
    if n>0: out.append(f"Финансовая шина в профиците: после нагрузок остаётся примерно {n:.2f} в месяц.")
    elif n<0: out.append(f"Финансовая шина в дефиците: резерв уменьшается примерно на {abs(n):.2f} в месяц."); warnings.append("FINANCIAL_DEFICIT")
    else: out.append("Финансовая шина сбалансирована: входной поток почти равен нагрузке.")
    runway=fr["runway_if_income_lost_months"]
    if math.isfinite(runway):
        if runway<3: out.append(f"Финансовый буфер короткий: при пропадании дохода нагрузки хватит примерно на {runway:.1f} мес."); warnings.append("LOW_RUNWAY")
        else: out.append(f"Резерв даёт около {runway:.1f} мес. автономии при полном исчезновении дохода.")
    if fr["photo_income_monthly"]>0:
        out.append(f"Оптофинансовый канал добавляет около {fr['photo_income_monthly']:.2f} в месяц; сопряжение луча {fr['beam_coupling_efficiency']:.2f}.")
    else: out.append("Оптофинансовый канал сейчас не даёт заметного денежного потока.")
    if fr["mortgage_debt_end"]<fr["mortgage_debt_start"]:
        out.append(f"Ипотечная нагрузка обслуживается: долг снижается с {fr['mortgage_debt_start']:.2f} до {fr['mortgage_debt_end']:.2f}.")
    elif fr["mortgage_debt_end"]>fr["mortgage_debt_start"]:
        out.append("Ипотечный долг растёт: текущий платёж не перекрывает начисляемую динамику долга."); warnings.append("MORTGAGE_GROWING")
    return out,warnings


def simulate(s):
    ir=compile_scenario(s)
    cfg=s.get("моделирование",{})
    if not isinstance(cfg,dict): raise ScenarioError("моделирование must be object")
    months=int(positive(cfg.get("месяцев",12),"месяцев"))
    rr=solve_relationship(ir); fr=solve_finance(ir,months)
    text,warnings=interpret(rr,fr)
    return ir, {"model_version":VERSION,"scenario_name":ir["scenario_name"],
                "relationship":rr,"finance":fr,"family_interpretation":text,
                "warnings":warnings}


def pseudo_spice(ir):
    return f"""* {ir['scenario_name']}
* normalized pseudo-SPICE, not calibrated SI family measurements
VREL src 0 AC {ir['analysis']['total_drive_voltage']:.8g}
RCHILD src n1 {cv(ir,'R_CHILD'):.8g}
RCHAN n1 n2 {cv(ir,'R_CHANNEL'):.8g}
RRAD n2 n3 {cv(ir,'R_RAD'):.8g}
LWOMAN n3 n4 {cv(ir,'L_WOMAN'):.8g}
CMAN n4 0 {cv(ir,'C_MAN'):.8g}
.AC LIN 1 {ir['analysis']['omega_rad_s']:.8g} {ir['analysis']['omega_rad_s']:.8g}
.END
"""


def report(result):
    rr=result["relationship"]; fr=result["finance"]
    bullets="\n".join("- "+x for x in result["family_interpretation"])
    warns=", ".join(result["warnings"]) if result["warnings"] else "нет"
    return f"""# Отчёт RLC-family simulator

**Сценарий:** {result['scenario_name']}  
**Модель:** {result['model_version']}

## Семейная интерпретация

{bullets}

## Внутренняя аналоговая схема

| Параметр | Значение |
|---|---:|
| R суммарное | {rr['resistance']:.4f} |
| L | {rr['inductance']:.4f} |
| C | {rr['capacitance']:.4f} |
| Реактивность X | {rr['reactance']:.4f} |
| |Z| | {rr['impedance_abs']:.4f} |
| Ток взаимодействия | {rr['current_rms']:.4f} |
| Фаза, град | {rr['phase_deg']:.2f} |
| ω₀ | {rr['resonance_omega']:.4f} |
| Демпфирование | {rr['damping_ratio']:.4f} |
| Сброс через антенну | {rr['radiated_power']:.4f} |
| Память после шага | {rr['memory_after']:.4f} |

## Финансовая шина

| Параметр | Значение |
|---|---:|
| Явный доход / месяц | {fr['explicit_income_monthly']:.2f} |
| Оптофинансовый доход / месяц | {fr['photo_income_monthly']:.2f} |
| Общий доход / месяц | {fr['total_income_monthly']:.2f} |
| Общая нагрузка / месяц | {fr['total_load_monthly']:.2f} |
| Чистый поток / месяц | {fr['net_monthly']:.2f} |
| Резерв в начале | {fr['reserve_start']:.2f} |
| Резерв в конце | {fr['reserve_end']:.2f} |
| Runway без дохода, мес. | {fr['runway_if_income_lost_months']:.2f} |
| Ипотечный долг в начале | {fr['mortgage_debt_start']:.2f} |
| Ипотечный долг в конце | {fr['mortgage_debt_end']:.2f} |
| Сопряжение денежного луча | {fr['beam_coupling_efficiency']:.4f} |

## Диагностика

Предупреждения: **{warns}**

> Это сатирическая исполняемая аналогия, а не психологический или финансовый прогноз.
"""


def write_outputs(out,ir,result):
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    (out/"analog_ir.json").write_text(json.dumps(ir,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"result.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    (out/"circuit.net").write_text(pseudo_spice(ir),encoding="utf-8")
    (out/"report.md").write_text(report(result),encoding="utf-8")


def main():
    p=argparse.ArgumentParser(description="Family terms -> analog model -> family interpretation")
    p.add_argument("scenario", help="JSON file path, or '-' to read compiled chat scenario from stdin")
    p.add_argument("--out",type=Path,default=Path("out"))
    p.add_argument("--json",action="store_true")
    a=p.parse_args()
    try:
        ir,res=simulate(load(a.scenario)); write_outputs(a.out,ir,res)
    except ScenarioError as e:
        p.error(str(e))
    print(json.dumps(res,ensure_ascii=False,indent=2) if a.json else report(res))


if __name__=="__main__":
    main()
