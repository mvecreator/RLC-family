#!/usr/bin/env python3
"""PERSON-NET1: frequency-domain nodal solver for PERSON2 networks."""

from __future__ import annotations

import argparse
import cmath
import json
import math
from pathlib import Path

try:
    from simulator import person_model as pm
    from simulator import link_semiconductor as semi
    from simulator import rlc_family_sim as core
except ModuleNotFoundError:
    import person_model as pm
    import link_semiconductor as semi
    import rlc_family_sim as core

VERSION = "RLC-FAMILY-PERSON-NET1-0.1"


def solve_complex(matrix, rhs):
    n=len(rhs)
    a=[list(row)+[rhs[i]] for i,row in enumerate(matrix)]
    for col in range(n):
        pivot=max(range(col,n),key=lambda r:abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-14:
            raise core.ScenarioError("PERSON-NET1 singular admittance matrix")
        if pivot != col:
            a[col],a[pivot]=a[pivot],a[col]
        p=a[col][col]
        a[col]=[x/p for x in a[col]]
        for row in range(n):
            if row==col:
                continue
            factor=a[row][col]
            if factor==0:
                continue
            a[row]=[
                x-factor*y for x,y in zip(a[row],a[col])
            ]
    return [a[i][-1] for i in range(n)]


def _source_weights(scenario, nodes):
    raw_by_id={
        str(p.get("id")):p
        for p in scenario.get("персонажи",[])
        if isinstance(p,dict)
    }
    weights=[]
    for node in nodes:
        raw=raw_by_id.get(node["id"],{})
        w=core.nonneg(raw.get("source_weight",1.0),f"{node['id']}.source_weight")
        weights.append(w)
    total=sum(weights)
    if total<=0:
        raise core.ScenarioError("at least one PERSON2 source_weight must be > 0")
    return [w/total for w in weights]


def solve_network(scenario):
    pir=pm.compile_person_network(scenario)
    if pir["mode"]!="PERSON2":
        raise core.ScenarioError("PERSON-NET1 requires персонажи")

    legacy_ir=core.compile_scenario(scenario)
    omega=legacy_ir["analysis"]["omega_rad_s"]
    drive=legacy_ir["analysis"]["total_drive_voltage"]

    nodes=pir["nodes"]
    links=pir["links"]
    nonlinear = [
        f"{link.get('link_id', link['from'] + '->' + link['to'])}:"
        f"{link.get('element_type')}"
        for link in links
        if semi.is_nonlinear(link)
    ]
    if nonlinear:
        raise core.ScenarioError(
            "PERSON-NET1 is a linear frequency-domain solver and cannot "
            "solve LINK-SEMI1 nonlinear links; use PERSON-TIME2 instead. "
            "Nonlinear links: " + ", ".join(nonlinear)
        )
    n=len(nodes)
    index={node["id"]:i for i,node in enumerate(nodes)}
    matrix=[[0j for _ in range(n)] for _ in range(n)]

    for i,node in enumerate(nodes):
        R,C,L=node["R"],node["C"],node["L"]
        y=1/R + 1j*omega*C + 1/(1j*omega*L)
        matrix[i][i]+=y

    for link in links:
        i=index[link["from"]]
        j=index[link["to"]]
        g=1/link["R_link"]
        matrix[i][i]+=g
        matrix[j][j]+=g
        matrix[i][j]-=g
        matrix[j][i]-=g

    shares=_source_weights(scenario,nodes)
    rhs=[drive*share+0j for share in shares]
    voltages=solve_complex(matrix,rhs)

    node_results=[]
    for i,(node,v) in enumerate(zip(nodes,voltages)):
        omega_c=1j*omega*node["C"]
        omega_l=1/(1j*omega*node["L"])
        i_r=v/node["R"]
        i_c=v*omega_c
        i_l=v*omega_l
        node_results.append({
            "id":node["id"],
            "kind":node["kind"],
            "gender_label":node["gender_label"],
            "R":node["R"],"C":node["C"],"L":node["L"],
            "role_balance":node.get("role_balance"),
            "effective_orientation":node["effective_orientation"],
            "voltage_re":v.real,
            "voltage_im":v.imag,
            "voltage_abs":abs(v),
            "phase_deg":math.degrees(cmath.phase(v)),
            "source_share":shares[i],
            "current_R_abs":abs(i_r),
            "current_C_abs":abs(i_c),
            "current_L_abs":abs(i_l),
        })

    link_results=[]
    for link in links:
        va=voltages[index[link["from"]]]
        vb=voltages[index[link["to"]]]
        current=(va-vb)/link["R_link"]
        link_results.append({
            "link_id":link["link_id"],
            "pair_id":link["pair_id"],
            "channel_kind":link.get("channel_kind","generic"),
            "parallel_branch_count":link.get("parallel_branch_count",1),
            "from":link["from"],
            "to":link["to"],
            "element_type":link.get("element_type","RESISTIVE"),
            "quality":link["quality"],
            "effective_transmission":link.get(
                "effective_transmission", link["quality"]
            ),
            "communication_quality":link.get(
                "communication_quality", link["quality"]
            ),
            "contact_frequency":link.get("contact_frequency", 1.0),
            "availability":link.get("availability", 1.0),
            "hostility":link.get(
                "hostility",
                1.0 - link.get("communication_quality", link["quality"]),
            ),
            "semantic_source":link.get("semantic_source", "legacy-quality"),
            "R_link":link["R_link"],
            "current_re":current.real,
            "current_im":current.imag,
            "current_abs":abs(current),
            "phase_deg":math.degrees(cmath.phase(current)) if current else 0.0,
            "dissipation_proxy":abs(va-vb)**2/link["R_link"],
            "power_model":"I^2R = |deltaV|^2/R for RESISTIVE links only",
        })

    max_node=max(node_results,key=lambda x:x["voltage_abs"])
    max_link=max(link_results,key=lambda x:x["current_abs"]) if link_results else None
    phases=[x["phase_deg"] for x in node_results]
    summary={
        "node_count":n,
        "link_count":len(link_results),
        "omega_rad_s":omega,
        "total_drive":drive,
        "max_excited_person":max_node["id"],
        "max_person_voltage":max_node["voltage_abs"],
        "phase_span_deg":max(phases)-min(phases) if phases else 0.0,
        "strongest_link":(
            max_link["link_id"] if max_link else None
        ),
        "max_link_current":max_link["current_abs"] if max_link else 0.0,
        "total_link_dissipation_proxy":sum(x["dissipation_proxy"] for x in link_results),
    }

    interpretations=[]
    for node in nodes:
        if node["kind"]=="adult":
            if node["C"]>node["L"]:
                interpretations.append(
                    f"{node['id']}: профиль смещён в C-сторону (C>L)."
                )
            elif node["L"]>node["C"]:
                interpretations.append(
                    f"{node['id']}: профиль смещён в L-сторону (L>C)."
                )
            else:
                interpretations.append(
                    f"{node['id']}: реактивный профиль близок к симметричному."
                )
    interpretations.append(
        f"Максимальная амплитуда PERSON-NET1 сейчас у {summary['max_excited_person']}."
    )
    if max_link:
        interpretations.append(
            f"Наибольший ток связи проходит по каналу {summary['strongest_link']}."
        )

    return {
        "model_version":VERSION,
        "scenario_name":scenario.get("название","PERSON2 family"),
        "person_ir":pir,
        "equations":{
            "node":"Y_person(omega)*V_p + sum_branch((V_p-V_q)/R_branch) = I_p",
            "person_admittance":"1/R_p + j*omega*C_p + 1/(j*omega*L_p)",
            "link_current":"I_pq = (V_p-V_q)/R_pq",
        },
        "nodes":node_results,
        "links":link_results,
        "summary":summary,
        "family_interpretation":interpretations,
    }


def report(result):
    s=result["summary"]
    lines="\n".join("- "+x for x in result["family_interpretation"])
    node_rows="\n".join(
        f"| {x['id']} | {x['R']:.3f} | {x['C']:.3f} | {x['L']:.3f} | {x['voltage_abs']:.5f} | {x['phase_deg']:.2f} |"
        for x in result["nodes"]
    )
    return f"""# PERSON-NET1 report

**Сценарий:** {result['scenario_name']}

## Интерпретация

{lines}

## Персонажи

| person | R | C | L | |V| | phase deg |
|---|---:|---:|---:|---:|---:|
{node_rows}

## Сеть

- Узлов: {s['node_count']}
- Каналов: {s['link_count']}
- Phase span: {s['phase_span_deg']:.3f}°
- Максимальный ток связи: {s['max_link_current']:.6f}
- Link dissipation proxy: {s['total_link_dissipation_proxy']:.6f}

> PERSON-NET1 — нормализованная сатирическая схема, не измерение личности или семейной совместимости.
"""


def main():
    p=argparse.ArgumentParser(description="PERSON2 frequency-domain network solver")
    p.add_argument("scenario")
    p.add_argument("--out",type=Path)
    p.add_argument("--json",action="store_true")
    args=p.parse_args()
    scenario=core.load(args.scenario)
    result=solve_network(scenario)
    if args.out:
        args.out.mkdir(parents=True,exist_ok=True)
        (args.out/"person_ir.json").write_text(
            json.dumps(result["person_ir"],ensure_ascii=False,indent=2)+"\n",
            encoding="utf-8",
        )
        (args.out/"person_network_result.json").write_text(
            json.dumps(result,ensure_ascii=False,indent=2)+"\n",
            encoding="utf-8",
        )
        (args.out/"person_network_report.md").write_text(
            report(result),encoding="utf-8"
        )
    print(json.dumps(result,ensure_ascii=False,indent=2) if args.json else report(result))


if __name__=="__main__":
    main()
