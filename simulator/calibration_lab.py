#!/usr/bin/env python3
"""CALIB1: explicit calibration scenarios for RLC-family dynamics.

These are directional calibration tests, not empirical claims about families.
They check that the equations respond in the intended model direction.
"""

from __future__ import annotations
import copy, json
from simulator import scenario_lab
from simulator import time_solver as ts


def run(scenario, events=None, days=7):
    return ts.simulate_timeline(
        scenario,
        scenario_lab.timeline(events or [], days),
    )["summary"]


def suite():
    rows = []

    base = scenario_lab.family(
        "Calibration baseline",
        tension=0.35, memory=0.20, quality=0.80,
        amp=1.00, background=0.20, dump=0.30, match=0.70,
        incomes=[5200], reserve=12000,
    )

    # CAL01 — tension monotonicity.
    low = copy.deepcopy(base)
    high = copy.deepcopy(base)
    low["отношения"]["напряженность"] = 0.35
    high["отношения"]["напряженность"] = 0.65
    rows.append({
        "id":"CAL01_TENSION",
        "a":run(low), "b":run(high),
        "expect":"higher tension -> higher peak current and higher final memory",
    })

    # Shared quarrel pulse.
    argument = {
        "id":"argument", "день":1, "длительность_дней":0.5,
        "добавить":{"отношения.напряженность":0.25},
        "импульс_памяти":0.08,
    }

    # CAL02 — communication quality.
    poor = {
        "id":"after", "день":1.5, "длительность_дней":2,
        "установить":{"связь.качество_проводника":0.25},
    }
    good = {
        "id":"after", "день":1.5, "длительность_дней":2,
        "установить":{"связь.качество_проводника":0.90},
    }
    rows.append({
        "id":"CAL02_COMMUNICATION",
        "a":run(base,[argument,poor]), "b":run(base,[argument,good]),
        "expect":"better communication -> lower final memory",
    })

    # CAL03 — matched support dump.
    weak_dump = {
        "id":"support", "день":1.5, "длительность_дней":1,
        "установить":{
            "связь.сброс_через_антенну":0.10,
            "связь.согласование_собеседника":0.80,
        },
    }
    strong_dump = {
        "id":"support", "день":1.5, "длительность_дней":1,
        "установить":{
            "связь.сброс_через_антенну":0.90,
            "связь.согласование_собеседника":0.90,
        },
    }
    rows.append({
        "id":"CAL03_SUPPORT_DUMP",
        "a":run(base,[argument,weak_dump]), "b":run(base,[argument,strong_dump]),
        "expect":"stronger matched support dump -> lower final memory",
    })

    # CAL04 — critical filtering of external excitation.
    external = {
        "id":"external", "день":2, "длительность_дней":1,
        "добавить":{"связь.внешний_фон":0.50,"связь.усиление_антенны":0.20},
    }
    low_filter = copy.deepcopy(external)
    low_filter["установить"]={"связь.фильтр_критического_мышления":0.20}
    high_filter = copy.deepcopy(external)
    high_filter["установить"]={"связь.фильтр_критического_мышления":0.90}
    rows.append({
        "id":"CAL04_FILTER",
        "a":run(base,[low_filter]), "b":run(base,[high_filter]),
        "expect":"stronger filter -> substantially lower external peak current",
    })

    # CAL05 — disturbance duration.
    short = {
        "id":"pulse", "день":1, "длительность_дней":0.25,
        "добавить":{"отношения.напряженность":0.30},
    }
    long = copy.deepcopy(short)
    long["длительность_дней"]=2.0
    rows.append({
        "id":"CAL05_DURATION",
        "a":run(base,[short]), "b":run(base,[long]),
        "expect":"longer equal disturbance -> larger peak and larger final memory",
    })

    # CAL06 — reserve buffer at equal monthly deficit.
    low_reserve = scenario_lab.family(
        "Low reserve",
        tension=0.40,memory=0.25,quality=0.75,
        incomes=[3500],mortgage=1500,base_expenses=2200,
        other_expenses=500,reserve=1000,
    )
    high_reserve = copy.deepcopy(low_reserve)
    high_reserve["финансы"]["резерв"]=15000
    rows.append({
        "id":"CAL06_RESERVE_BUFFER",
        "a":run(low_reserve,days=30), "b":run(high_reserve,days=30),
        "expect":"larger reserve -> lower financial stress and lower final memory",
    })

    # CAL07 — deficit coupling at equal starting reserve.
    balanced = scenario_lab.family(
        "Balanced",
        tension=0.40,memory=0.25,quality=0.75,
        incomes=[5000],mortgage=1300,base_expenses=2200,
        other_expenses=500,reserve=6000,
    )
    deficit = copy.deepcopy(balanced)
    deficit["финансы"]["доходы_в_месяц"]=[3000]
    rows.append({
        "id":"CAL07_DEFICIT_COUPLING",
        "a":run(balanced,days=30), "b":run(deficit,days=30),
        "expect":"larger deficit -> higher financial stress and higher final memory",
    })

    # CAL08 — a bonus should not change relationship dynamics when financial
    # stress is already zero; it should only change reserve.
    comfortable = scenario_lab.family(
        "Comfortable",
        tension=0.40,memory=0.25,quality=0.75,
        incomes=[6000],mortgage=1200,base_expenses=1800,
        other_expenses=400,reserve=20000,
    )
    bonus = {"id":"bonus","день":2,"денежный_импульс":5000}
    rows.append({
        "id":"CAL08_BONUS_DECOUPLING",
        "a":run(comfortable,days=14), "b":run(comfortable,[bonus],14),
        "expect":"with zero financial stress, bonus changes reserve but not family memory",
    })

    # CAL09 — adolescent nonlinearity should be gated by tension threshold.
    low_t0 = scenario_lab.family(
        "Low tension no NL", tension=0.40,memory=0.25,
        nonlinearity=0.0,children=[0.40],quality=0.70,
    )
    low_t9 = copy.deepcopy(low_t0)
    low_t9["отношения"]["подростковая_нелинейность"]=0.90
    high_t0 = scenario_lab.family(
        "High tension no NL", tension=0.72,memory=0.25,
        nonlinearity=0.0,children=[0.40],quality=0.70,
    )
    high_t9 = copy.deepcopy(high_t0)
    high_t9["отношения"]["подростковая_нелинейность"]=0.90
    rows.append({
        "id":"CAL09_NONLINEARITY_THRESHOLD_LOW",
        "a":run(low_t0), "b":run(low_t9),
        "expect":"below threshold, nonlinearity has negligible memory effect",
    })
    rows.append({
        "id":"CAL10_NONLINEARITY_THRESHOLD_HIGH",
        "a":run(high_t0), "b":run(high_t9),
        "expect":"above threshold, stronger nonlinearity increases final memory",
    })

    # CAL11 — helpful vs stoking external support.
    support_base = scenario_lab.family(
        "Support calibration",
        tension=0.45,memory=0.28,quality=0.72,
        amp=1.05,background=0.18,dump=0.25,match=0.50,
    )
    support_argument = {
        "id":"argument-2","день":1,"длительность_дней":0.4,
        "добавить":{
            "отношения.напряженность":0.28,
            "связь.усиление_эмоций":0.20,
        },
        "импульс_памяти":0.07,
    }
    helpful = {
        "id":"helpful","день":1.5,"длительность_дней":0.7,
        "установить":{
            "связь.сброс_через_антенну":0.90,
            "связь.согласование_собеседника":0.95,
            "связь.качество_проводника":0.82,
        },
    }
    stoking = {
        "id":"stoking","день":1.5,"длительность_дней":0.7,
        "добавить":{
            "связь.внешний_фон":0.45,
            "связь.усиление_антенны":0.25,
            "связь.усиление_эмоций":0.25,
        },
        "установить":{"связь.фильтр_критического_мышления":0.20},
    }
    rows.append({
        "id":"CAL11_SUPPORT_VALENCE",
        "a":run(support_base,[support_argument,helpful]),
        "b":run(support_base,[support_argument,stoking]),
        "expect":"helpful support -> lower peak current and lower final memory",
    })

    # CAL12 — optofinancial channel.
    dark = scenario_lab.family(
        "Weak money light",
        tension=0.40,memory=0.25,quality=0.75,
        incomes=[3500],mortgage=1500,base_expenses=2200,
        other_expenses=500,reserve=2500,
    )
    dark["финансы"].update({
        "свет_возможностей":0.05,
        "сопряжение_денежного_луча":0.30,
        "потери_оптики":0.20,
        "усиление_бизнеса":1.10,
        "доступный_рынок_в_месяц":1500,
    })
    bright = copy.deepcopy(dark)
    bright["финансы"].update({
        "свет_возможностей":0.85,
        "сопряжение_денежного_луча":0.85,
        "усиление_бизнеса":1.20,
    })
    rows.append({
        "id":"CAL12_MONEY_LIGHT",
        "a":run(dark,days=30), "b":run(bright,days=30),
        "expect":"better money-light coupling -> larger reserve and lower final memory",
    })

    return rows


def checks(rows):
    by={r["id"]:r for r in rows}
    a=lambda cid:by[cid]["a"]
    b=lambda cid:by[cid]["b"]
    return {
        "CAL01": (
            abs(b("CAL01_TENSION")["peak_interaction_current"]) >
            abs(a("CAL01_TENSION")["peak_interaction_current"])
            and b("CAL01_TENSION")["final_memory"] >
            a("CAL01_TENSION")["final_memory"] + 0.05
        ),
        "CAL02": (
            b("CAL02_COMMUNICATION")["final_memory"] <
            a("CAL02_COMMUNICATION")["final_memory"] - 0.015
        ),
        "CAL03": (
            b("CAL03_SUPPORT_DUMP")["final_memory"] <
            a("CAL03_SUPPORT_DUMP")["final_memory"] - 0.005
        ),
        "CAL04": (
            abs(b("CAL04_FILTER")["peak_interaction_current"]) <
            0.50 * abs(a("CAL04_FILTER")["peak_interaction_current"])
        ),
        "CAL05": (
            abs(b("CAL05_DURATION")["peak_interaction_current"]) >
            2.0 * abs(a("CAL05_DURATION")["peak_interaction_current"])
            and b("CAL05_DURATION")["final_memory"] >
            a("CAL05_DURATION")["final_memory"]
        ),
        "CAL06": (
            b("CAL06_RESERVE_BUFFER")["peak_financial_stress"] <
            a("CAL06_RESERVE_BUFFER")["peak_financial_stress"]
            and b("CAL06_RESERVE_BUFFER")["final_memory"] <
            a("CAL06_RESERVE_BUFFER")["final_memory"] - 0.05
        ),
        "CAL07": (
            b("CAL07_DEFICIT_COUPLING")["peak_financial_stress"] >
            a("CAL07_DEFICIT_COUPLING")["peak_financial_stress"]
            and b("CAL07_DEFICIT_COUPLING")["final_memory"] >
            a("CAL07_DEFICIT_COUPLING")["final_memory"] + 0.05
        ),
        "CAL08": (
            abs(b("CAL08_BONUS_DECOUPLING")["final_memory"] -
                a("CAL08_BONUS_DECOUPLING")["final_memory"]) < 1e-9
            and abs((b("CAL08_BONUS_DECOUPLING")["final_reserve"] -
                     a("CAL08_BONUS_DECOUPLING")["final_reserve"]) - 5000) < 1e-6
        ),
        "CAL09": (
            abs(b("CAL09_NONLINEARITY_THRESHOLD_LOW")["final_memory"] -
                a("CAL09_NONLINEARITY_THRESHOLD_LOW")["final_memory"]) < 1e-9
        ),
        "CAL10": (
            b("CAL10_NONLINEARITY_THRESHOLD_HIGH")["final_memory"] >
            a("CAL10_NONLINEARITY_THRESHOLD_HIGH")["final_memory"] + 0.02
        ),
        "CAL11": (
            abs(a("CAL11_SUPPORT_VALENCE")["peak_interaction_current"]) <
            abs(b("CAL11_SUPPORT_VALENCE")["peak_interaction_current"])
            and a("CAL11_SUPPORT_VALENCE")["final_memory"] <
            b("CAL11_SUPPORT_VALENCE")["final_memory"]
        ),
        "CAL12": (
            b("CAL12_MONEY_LIGHT")["final_reserve"] >
            a("CAL12_MONEY_LIGHT")["final_reserve"]
            and b("CAL12_MONEY_LIGHT")["final_memory"] <
            a("CAL12_MONEY_LIGHT")["final_memory"] - 0.03
        ),
    }


def main():
    rows=suite()
    result={"cases":rows,"checks":checks(rows)}
    result["passed"]=sum(result["checks"].values())
    result["total"]=len(result["checks"])
    result["all_pass"]=result["passed"]==result["total"]
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
