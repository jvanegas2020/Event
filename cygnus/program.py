"""Programa de entrenamiento: diagnóstico -> plan dinámico -> simulaciones -> diagnóstico final -> informe."""
from __future__ import annotations

import uuid

from . import diagnostic, profile
from .diagnostic import HABIT_ADVICE, risk_level
from .scenarios import BY_ID, PRINCIPLE_LABELS, PRINCIPLES, SCENARIOS

SIMS_BY_LEVEL = {"bajo": 3, "medio": 4, "alto": 5, "crítico": 6}


def create(user_id: str) -> dict:
    pid = uuid.uuid4().hex
    profile.create_program(pid, user_id)
    return profile.get_program(pid)


def build_plan(pre: dict) -> dict:
    """Plan de entrenamiento a medida del diagnóstico inicial.

    - Cuántas simulaciones: según el nivel de riesgo global.
    - Qué principios: los de mayor riesgo, en ese orden.
    - Qué dificultad: riesgo alto -> escenario básico para construir el hábito;
      riesgo bajo -> escenario difícil para ponerlo a prueba.
    """
    n = SIMS_BY_LEVEL[pre["level"]]
    ranked = sorted(PRINCIPLES, key=lambda p: -pre["by_principle"][p])[:n]
    items = []
    for p in ranked:
        risk = pre["by_principle"][p]
        target = 1 if risk >= 60 else 2 if risk >= 30 else 3
        sc = min((s for s in SCENARIOS if s.principle == p), key=lambda s: (abs(s.level - target), s.level))
        how = {1: "empezamos con un escenario básico para construir el hábito",
               2: "un escenario de dificultad media para consolidar",
               3: "un escenario exigente para ponerte a prueba"}[target]
        items.append({"scenario_id": sc.id, "title": sc.title, "channel": sc.channel, "sector": sc.sector,
                      "principle": p, "principle_label": PRINCIPLE_LABELS[p], "level": sc.level,
                      "risk": risk, "reason": f"Riesgo {risk:.0f}/100 en «{PRINCIPLE_LABELS[p]}»: {how}."})
    return {"level": pre["level"], "n": n, "items": items,
            "summary": (f"Tu riesgo inicial es {pre['overall']:.0f}/100 (nivel {pre['level']}). "
                        f"Preparé {n} simulaciones que empiezan por tus principios más vulnerables.")}


def submit_diagnostic(pid: str, phase: str, answers: dict[str, int]) -> dict:
    prog = profile.get_program(pid)
    if not prog:
        raise KeyError("Programa no existe")
    if phase == "pre":
        if prog["pre"]:
            raise ValueError("El diagnóstico inicial ya fue respondido")
        res = diagnostic.score("pre", answers)
        plan = build_plan(res)
        profile.update_program(pid, pre=res, plan=plan)
        return {"result": res, "plan": plan}
    if phase == "post":
        st = state(pid)
        if st["stage"] != "diagnostico_final":
            raise ValueError("Aún no puedes hacer el diagnóstico final: termina todas las simulaciones del plan")
        res = diagnostic.score("post", answers)
        profile.update_program(pid, post=res)
        return {"result": res}
    raise ValueError("Fase inválida")


def next_scenario_id(pid: str) -> str | None:
    prog = profile.get_program(pid)
    if not prog or not prog["plan"]:
        return None
    done = len(profile.program_results(pid))
    items = prog["plan"]["items"]
    return items[done]["scenario_id"] if done < len(items) else None


def state(pid: str) -> dict:
    prog = profile.get_program(pid)
    if not prog:
        raise KeyError("Programa no existe")
    results = profile.program_results(pid)
    plan = prog["plan"]
    if not prog["pre"]:
        stage = "diagnostico_inicial"
    elif len(results) < len(plan["items"]):
        stage = "entrenamiento"
    elif not prog["post"]:
        stage = "diagnostico_final"
    else:
        stage = "informe"
    return {"program_id": pid, "stage": stage, "pre": prog["pre"], "plan": plan, "post": prog["post"],
            "completed": len(results), "total": len(plan["items"]) if plan else 0,
            "heatmap": heatmap(prog, results)}


def heatmap(prog: dict, results: list[dict]) -> dict:
    """Matriz principio x momento. Valor = riesgo 0-100 (verde 0, rojo 100); None = sin medir."""
    cols = [{"key": "pre", "label": "Diagnóstico inicial"}]
    plan_items = prog["plan"]["items"] if prog["plan"] else []
    for i, it in enumerate(plan_items):
        cols.append({"key": f"sim{i + 1}", "label": f"Sim {i + 1}", "principle": it["principle"]})
    cols.append({"key": "post", "label": "Diagnóstico final"})
    rows = []
    for p in PRINCIPLES:
        cells = []
        for c in cols:
            v = None
            if c["key"] == "pre" and prog["pre"]:
                v = prog["pre"]["by_principle"].get(p)
            elif c["key"] == "post" and prog["post"]:
                v = prog["post"]["by_principle"].get(p)
            elif c["key"].startswith("sim"):
                k = int(c["key"][3:]) - 1
                if k < len(results) and results[k]["principle"] == p:
                    v = 100 - results[k]["score"]
            cells.append(v)
        rows.append({"principle": p, "label": PRINCIPLE_LABELS[p], "cells": cells})
    return {"columns": cols, "rows": rows}


def final_report(pid: str) -> dict:
    prog = profile.get_program(pid)
    st = state(pid)
    if st["stage"] != "informe":
        raise ValueError("El informe final está disponible al terminar el programa")
    pre, post = prog["pre"], prog["post"]
    results = profile.program_results(pid)
    rows = []
    for p in PRINCIPLES:
        b, a = pre["by_principle"][p], post["by_principle"][p]
        rows.append({"principle": p, "label": PRINCIPLE_LABELS[p], "before": b, "after": a, "delta": round(a - b, 1)})
    delta = round(post["overall"] - pre["overall"], 1)
    best = min(rows, key=lambda r: r["delta"])
    weakest = max(rows, key=lambda r: r["after"])
    verb = "bajó" if delta < 0 else "subió" if delta > 0 else "se mantuvo"
    narrative = (f"Tu riesgo global {verb}"
                 + (f" {abs(delta):.0f} puntos" if delta else "")
                 + f": de {pre['overall']:.0f} ({pre['level']}) a {post['overall']:.0f} ({post['level']}).")
    if best["delta"] < 0:
        narrative += f" Tu mayor mejora fue en «{best['label']}» ({best['before']:.0f} → {best['after']:.0f})."
    if weakest["after"] >= 30:
        narrative += f" Tu punto más débil ahora es «{weakest['label']}» ({weakest['after']:.0f}/100): conviene reforzarlo."
    habits = [{"id": k, "risk": v, "advice": HABIT_ADVICE[k]} for k, v in pre.get("habits", {}).items() if v >= 50]
    sims = [{"title": BY_ID[r["scenario_id"]].title, "principle": PRINCIPLE_LABELS[r["principle"]],
             "outcome": r["outcome"], "score": r["score"]} for r in results]
    sim_avg = round(sum(r["score"] for r in results) / len(results)) if results else None
    return {
        "program_id": pid,
        "before": {"overall": pre["overall"], "level": pre["level"]},
        "after": {"overall": post["overall"], "level": post["level"]},
        "delta": delta, "improved": delta < 0, "narrative": narrative,
        "by_principle": rows, "simulations": sims, "simulation_avg": sim_avg,
        "habit_findings": habits, "habits_score": pre.get("habits_score"),
        "heatmap": st["heatmap"],
        "iso_controls": [{"id": "A.6.3", "name": "Concienciación, educación y formación en seguridad de la información"},
                         {"id": "A.6.8", "name": "Reporte de eventos de seguridad de la información"}],
        "method_note": ("El diagnóstico inicial y el final usan formas paralelas del mismo test de juicio situacional "
                        "(situaciones distintas, mismos principios). Es una medición autoinformada: sirve para orientar "
                        "el entrenamiento y mostrar cambio, no sustituye una evaluación en entorno real."),
    }
