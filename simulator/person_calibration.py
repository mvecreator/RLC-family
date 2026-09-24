#!/usr/bin/env python3
"""PERSON-CAL: directional calibration gates for PERSON2."""

from __future__ import annotations

import copy
import json

from simulator import calibration_lab
from simulator import person_model as pm


def adult(pid, gender, **role):
    return {
        "id": pid,
        "type": "adult",
        "gender": gender,
        "age": 35,
        "role": {
            "work_provider": role.get("work_provider", 0.5),
            "decision_initiative": role.get("decision_initiative", 0.5),
            "external_activity": role.get("external_activity", 0.5),
            "caregiver": role.get("caregiver", 0.5),
            "domestic_load": role.get("domestic_load", 0.5),
        },
        "temperament_bias": role.get("temperament_bias", 0.0),
        "recovery_inertia": role.get("recovery_inertia", 0.5),
    }


def child(pid, gender, age, temperament=0.0):
    return {
        "id": pid,
        "type": "child",
        "gender": gender,
        "age": age,
        "temperament_bias": temperament,
    }


def compile_one(person, **cfg):
    scenario = {"персонажи":[person], "person_model":cfg}
    return pm.compile_person_network(scenario)["nodes"][0]


def suite():
    rows=[]

    # PCAL01: male caregiving role shifts toward L relative to neutral baseline.
    neutral_m = compile_one(adult("m","male"))
    care_m = compile_one(adult(
        "m","male",
        work_provider=0.10,
        decision_initiative=0.20,
        external_activity=0.20,
        caregiver=0.95,
        domestic_load=0.90,
    ))
    rows.append({"id":"PCAL01_ROLE_BEATS_MALE_PRIOR","a":neutral_m,"b":care_m})

    # PCAL02: female provider/directive role shifts toward C.
    neutral_f = compile_one(adult("f","female"))
    provider_f = compile_one(adult(
        "f","female",
        work_provider=0.95,
        decision_initiative=0.90,
        external_activity=0.80,
        caregiver=0.20,
        domestic_load=0.20,
    ))
    rows.append({"id":"PCAL02_PROVIDER_SHIFTS_FEMALE","a":neutral_f,"b":provider_f})

    # PCAL03: with gender prior zero, labels do not alter equal roles.
    m0 = compile_one(adult("x","male"), gender_prior_strength=0.0)
    f0 = compile_one(adult("x","female"), gender_prior_strength=0.0)
    rows.append({"id":"PCAL03_GENDER_NEUTRAL_MODE","a":m0,"b":f0})

    # PCAL04: strong role can invert both weak legacy priors.
    rows.append({
        "id":"PCAL04_ROLE_CAN_INVERT_PRIOR",
        "male_caregiver":care_m,
        "female_provider":provider_f,
    })

    # PCAL05: child resistance falls with age.
    ages=[3,8,13,17]
    child_r=[
        compile_one(child(f"c{age}","male",age), legacy_gender_profile=False)["R"]
        for age in ages
    ]
    rows.append({"id":"PCAL05_CHILD_R_MONOTONIC","ages":ages,"R":child_r})

    # PCAL06: legacy boy C/L rises with age.
    boys=[
        compile_one(
            child(f"b{age}","male",age),
            legacy_gender_profile=True,
        )
        for age in ages
    ]
    rows.append({"id":"PCAL06_LEGACY_BOY","nodes":boys})

    # PCAL07: legacy girl L/C rises with age.
    girls=[
        compile_one(
            child(f"g{age}","female",age),
            legacy_gender_profile=True,
        )
        for age in ages
    ]
    rows.append({"id":"PCAL07_LEGACY_GIRL","nodes":girls})

    # PCAL08: temperament can override child legacy prior.
    boy_override = compile_one(
        child("boy-override","male",17,temperament=-1.0),
        legacy_gender_profile=True,
    )
    girl_override = compile_one(
        child("girl-override","female",17,temperament=1.0),
        legacy_gender_profile=True,
    )
    rows.append({
        "id":"PCAL08_TEMPERAMENT_OVERRIDE",
        "boy":boy_override,
        "girl":girl_override,
    })

    # PCAL09: positivity across extreme adult/child profiles.
    extremes=[
        compile_one(adult(
            "a1","male",
            work_provider=1,decision_initiative=1,external_activity=1,
            caregiver=0,domestic_load=0,temperament_bias=1,
        )),
        compile_one(adult(
            "a2","female",
            work_provider=0,decision_initiative=0,external_activity=0,
            caregiver=1,domestic_load=1,temperament_bias=-1,
        )),
        compile_one(child("c1","male",0,temperament=1),legacy_gender_profile=True),
        compile_one(child("c2","female",18,temperament=-1),legacy_gender_profile=True),
    ]
    rows.append({"id":"PCAL09_POSITIVITY","nodes":extremes})

    # PCAL10: legacy CALIB1 must still pass unchanged.
    legacy_rows=calibration_lab.suite()
    legacy_checks=calibration_lab.checks(legacy_rows)
    rows.append({
        "id":"PCAL10_LEGACY_PRESERVATION",
        "checks":legacy_checks,
    })

    return rows


def checks(rows):
    by={row["id"]:row for row in rows}
    p1=by["PCAL01_ROLE_BEATS_MALE_PRIOR"]
    p2=by["PCAL02_PROVIDER_SHIFTS_FEMALE"]
    p3=by["PCAL03_GENDER_NEUTRAL_MODE"]
    p4=by["PCAL04_ROLE_CAN_INVERT_PRIOR"]
    p5=by["PCAL05_CHILD_R_MONOTONIC"]
    p6=by["PCAL06_LEGACY_BOY"]["nodes"]
    p7=by["PCAL07_LEGACY_GIRL"]["nodes"]
    p8=by["PCAL08_TEMPERAMENT_OVERRIDE"]
    p9=by["PCAL09_POSITIVITY"]["nodes"]
    p10=by["PCAL10_LEGACY_PRESERVATION"]["checks"]

    return {
        "PCAL01": (
            p1["b"]["l_to_c_ratio"] > p1["a"]["l_to_c_ratio"]
            and p1["b"]["L"] > p1["b"]["C"]
        ),
        "PCAL02": (
            p2["b"]["c_to_l_ratio"] > p2["a"]["c_to_l_ratio"]
            and p2["b"]["C"] > p2["b"]["L"]
        ),
        "PCAL03": (
            abs(p3["a"]["R"]-p3["b"]["R"]) < 1e-12
            and abs(p3["a"]["C"]-p3["b"]["C"]) < 1e-12
            and abs(p3["a"]["L"]-p3["b"]["L"]) < 1e-12
        ),
        "PCAL04": (
            p4["male_caregiver"]["L"] > p4["male_caregiver"]["C"]
            and p4["female_provider"]["C"] > p4["female_provider"]["L"]
        ),
        "PCAL05": all(a>b for a,b in zip(p5["R"],p5["R"][1:])),
        "PCAL06": all(
            a["c_to_l_ratio"] < b["c_to_l_ratio"]
            for a,b in zip(p6,p6[1:])
        ),
        "PCAL07": all(
            a["l_to_c_ratio"] < b["l_to_c_ratio"]
            for a,b in zip(p7,p7[1:])
        ),
        "PCAL08": (
            p8["boy"]["L"] > p8["boy"]["C"]
            and p8["girl"]["C"] > p8["girl"]["L"]
        ),
        "PCAL09": all(
            node["R"]>0 and node["C"]>0 and node["L"]>0
            for node in p9
        ),
        "PCAL10": all(p10.values()) and len(p10)==12,
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
