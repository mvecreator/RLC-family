#!/usr/bin/env python3
"""Scenario laboratory for qualitative validation of RLC-family dynamics."""

from __future__ import annotations
import copy, json
from simulator import time_solver as ts


def family(name="base", **kw):
    return {
        "название": name,
        "отношения": {
            "мужская_емкость": kw.get("c", 0.60),
            "женская_индуктивность": kw.get("l", 0.60),
            "сопротивление_детей": kw.get("children", [0.35, 0.40]),
            "топология_детей": kw.get("topology", "последовательно"),
            "напряженность": kw.get("tension", 0.35),
            "частота_событий": kw.get("omega", 1.0),
            "накопленная_память": kw.get("memory", 0.20),
            "подростковая_нелинейность": kw.get("nonlinearity", 0.0),
        },
        "связь": {
            "качество_проводника": kw.get("quality", 0.80),
            "усиление_эмоций": kw.get("amp", 1.0),
            "фильтр_критического_мышления": kw.get("filter", 0.75),
            "усиление_антенны": kw.get("antenna", 0.40),
            "внешний_фон": kw.get("background", 0.20),
            "сброс_через_антенну": kw.get("dump", 0.30),
            "согласование_собеседника": kw.get("match", 0.70),
        },
        "финансы": {
            "доходы_в_месяц": kw.get("incomes", [5000]),
            "ипотека_в_месяц": kw.get("mortgage", 1400),
            "базовые_расходы_в_месяц": kw.get("base_expenses", 2200),
            "прочие_расходы_в_месяц": kw.get("other_expenses", 500),
            "резерв": kw.get("reserve", 9000),
            "долг_по_ипотеке": kw.get("debt", 220000),
            "ставка_годовая": kw.get("rate", 0.045),
            "свет_возможностей": 0,
            "сопряжение_денежного_луча": 0.50,
            "потери_оптики": 0.10,
            "усиление_бизнеса": 1.0,
            "доступный_рынок_в_месяц": 0,
        },
    }


def timeline(events, days=7):
    return {
        "моделирование": {"дней": days, "шаг_дней": 0.01, "выборка_дней": 0.05},
        "события": events,
    }


def run_case(name, scenario, tl):
    result = ts.simulate_timeline(scenario, tl)
    return {"name": name, "summary": result["summary"]}


def suite():
    rows = []

    calm = family(
        "Спокойная семья", tension=0.22, memory=0.12, quality=0.90,
        amp=0.85, background=0.10, dump=0.50, match=0.85,
        incomes=[5600], reserve=15000,
    )
    rows.append(run_case("calm", calm, timeline([], 14)))

    chronic = family(
        "Хроническое напряжение", tension=0.72, memory=0.65, quality=0.45,
        amp=1.40, background=0.45, dump=0.15, match=0.35,
        incomes=[5000], reserve=6000,
    )
    rows.append(run_case("chronic", chronic, timeline([], 14)))

    base = family(
        "После ссоры", tension=0.40, memory=0.25, quality=0.75,
        amp=1.05, background=0.20, dump=0.35, match=0.70,
    )
    argument = {
        "id": "argument", "день": 1, "длительность_дней": 0.4,
        "добавить": {"отношения.напряженность": 0.28, "связь.усиление_эмоций": 0.20},
        "импульс_памяти": 0.08,
    }
    silence = {
        "id": "silence", "день": 1.4, "длительность_дней": 2.0,
        "установить": {"связь.качество_проводника": 0.25},
    }
    talk = {
        "id": "talk", "день": 1.4, "длительность_дней": 0.5,
        "установить": {
            "связь.качество_проводника": 0.90,
            "связь.сброс_через_антенну": 0.80,
            "связь.согласование_собеседника": 0.90,
        },
    }
    rows.append(run_case("argument_silence", base, timeline([argument, silence])))
    rows.append(run_case("argument_talk", base, timeline([argument, talk])))

    ext = family(
        "Внешний фон", tension=0.35, memory=0.20, quality=0.75,
        amp=1.0, background=0.20, antenna=0.50, filter=0.50,
    )
    external = {
        "id": "external", "день": 2, "длительность_дней": 1.0,
        "добавить": {"связь.внешний_фон": 0.50, "связь.усиление_антенны": 0.20},
        "импульс_памяти": 0.03,
    }
    low_filter = copy.deepcopy(external)
    low_filter["установить"] = {"связь.фильтр_критического_мышления": 0.20}
    high_filter = copy.deepcopy(external)
    high_filter["установить"] = {"связь.фильтр_критического_мышления": 0.90}
    rows.append(run_case("external_low_filter", ext, timeline([low_filter])))
    rows.append(run_case("external_high_filter", ext, timeline([high_filter])))

    teen_low = family(
        "Высокое напряжение без нелинейности", tension=0.72, memory=0.35,
        nonlinearity=0.0, children=[0.40], quality=0.70, amp=1.15,
    )
    teen_high = copy.deepcopy(teen_low)
    teen_high["название"] = "Высокое напряжение + подростковая нелинейность"
    teen_high["отношения"]["подростковая_нелинейность"] = 0.90
    rows.append(run_case("teen_low_nonlinearity", teen_low, timeline([], 7)))
    rows.append(run_case("teen_high_nonlinearity", teen_high, timeline([], 7)))

    deficit = family(
        "Финансовый перегруз", tension=0.40, memory=0.25, quality=0.75,
        incomes=[3600], mortgage=1600, base_expenses=2200,
        other_expenses=700, reserve=5000, debt=230000,
    )
    rows.append(run_case("financial_overload", deficit, timeline([], 120)))

    return rows


def checks(rows):
    by = {r["name"]: r["summary"] for r in rows}
    return {
        "calm_memory_decays": by["calm"]["final_memory"] < 0.12,
        "chronic_memory_exceeds_calm": by["chronic"]["final_memory"] > by["calm"]["final_memory"],
        "talk_beats_silence_on_final_memory":
            by["argument_talk"]["final_memory"] < by["argument_silence"]["final_memory"],
        "filter_reduces_external_peak":
            abs(by["external_high_filter"]["peak_interaction_current"]) <
            abs(by["external_low_filter"]["peak_interaction_current"]),
        "nonlinearity_increases_memory_under_tension":
            by["teen_high_nonlinearity"]["final_memory"] >
            by["teen_low_nonlinearity"]["final_memory"],
        "financial_overload_consumes_reserve":
            by["financial_overload"]["final_reserve"] < 5000,
    }


def main():
    rows = suite()
    result = {"cases": rows, "checks": checks(rows)}
    result["all_checks_pass"] = all(result["checks"].values())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
