"""Motor de simulación: sesiones, puntaje y reporte."""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from . import profile
from .evaluator import COMPLY, DISCLOSE, NEUTRAL, REPORT, SAFE, classify
from .providers import get_provider
from .scenarios import BY_ID, PRINCIPLE_LABELS, Scenario

MAX_TURNS = 4          # intervenciones del usuario antes de cerrar como "indeciso"
MAX_LEN = 1000
SESSION_TTL = 3600

OUTCOME_LABEL = {
    "reporto": "Resististe y reportaste",
    "resistio": "Resististe el ataque",
    "cayo_dato": "Entregaste información sensible",
    "cayo_accion": "Ejecutaste la acción del atacante",
    "indeciso": "No tomaste una decisión segura",
}
BASE_SCORE = {"reporto": 100, "resistio": 90, "indeciso": 40, "cayo_accion": 20, "cayo_dato": 0}

FEEDBACK = {
    DISCLOSE: "Compartiste un dato sensible (clave, código, documento o tarjeta). Ninguna entidad legítima lo pide por este medio.",
    COMPLY: "Seguiste la instrucción del atacante (abrir enlace, instalar, pagar o colaborar).",
    SAFE: "Bien: te negaste o decidiste verificar por un canal oficial.",
    REPORT: "Excelente: avisaste o decidiste reportar el intento.",
    NEUTRAL: "No rechazaste ni verificaste. Seguir la conversación le da tiempo al atacante para presionar.",
}

# Controles ISO/IEC 27001:2022 (Anexo A) vinculados a cada resultado.
ISO = {
    "A.6.3": "Concienciación, educación y formación en seguridad de la información",
    "A.6.8": "Reporte de eventos de seguridad de la información",
    "A.8.5": "Autenticación segura",
    "A.5.34": "Privacidad y protección de datos personales (PII)",
}


@dataclass
class Session:
    id: str
    user_id: str
    scenario: Scenario
    history: list = field(default_factory=list)   # (rol, texto)
    events: list = field(default_factory=list)
    user_turns: int = 0
    neutral_turns: int = 0
    finished: bool = False
    report: dict | None = None
    created: float = field(default_factory=time.time)


_SESSIONS: dict[str, Session] = {}
_provider = get_provider()


def _purge() -> None:
    now = time.time()
    for sid in [k for k, s in _SESSIONS.items() if now - s.created > SESSION_TTL]:
        _SESSIONS.pop(sid, None)


def start(user_id: str, scenario_id: str | None = None) -> tuple[Session, str]:
    _purge()
    if scenario_id:
        sc, why = BY_ID[scenario_id], "Escenario elegido por ti."
    else:
        sc, why = profile.next_scenario(user_id)
    s = Session(id=uuid.uuid4().hex, user_id=user_id, scenario=sc)
    s.history.append(("attacker", _provider.attacker_message(sc, s.history, 0)))
    _SESSIONS[s.id] = s
    return s, why


def get(session_id: str) -> Session | None:
    return _SESSIONS.get(session_id)


def reply(s: Session, text: str) -> dict:
    if s.finished:
        raise ValueError("La simulación ya terminó")
    text = text.strip()[:MAX_LEN]
    s.user_turns += 1
    s.history.append(("user", text))
    verdict = classify(text)
    s.events.append({"turn": s.user_turns, "verdict": verdict, "feedback": FEEDBACK[verdict]})

    outcome = None
    if verdict == DISCLOSE:
        outcome = "cayo_dato"
    elif verdict == COMPLY:
        outcome = "cayo_accion"
    elif verdict == REPORT:
        outcome = "reporto"
    elif verdict == SAFE:
        outcome = "resistio"
    else:
        s.neutral_turns += 1
        if s.user_turns >= MAX_TURNS:
            outcome = "indeciso"

    if outcome:
        s.finished = True
        s.report = _build_report(s, outcome)
        profile.record(s.user_id, s.scenario, outcome, s.report["score"])
        return {"finished": True, "verdict": verdict, "feedback": FEEDBACK[verdict], "report": s.report}

    msg = _provider.attacker_message(s.scenario, s.history, s.user_turns)
    s.history.append(("attacker", msg))
    return {"finished": False, "verdict": verdict, "feedback": FEEDBACK[verdict], "attacker": msg}


def _build_report(s: Session, outcome: str) -> dict:
    sc = s.scenario
    score = max(0, BASE_SCORE[outcome] - 10 * s.neutral_turns)
    controls = ["A.6.3"]
    if outcome == "reporto":
        controls.append("A.6.8")
    if outcome == "cayo_dato":
        controls += ["A.8.5", "A.5.34"]
    if outcome == "cayo_accion":
        controls.append("A.8.5")
    if outcome in ("indeciso", "resistio"):
        controls.append("A.6.8")
    recs = list(sc.safe_actions)
    if outcome in ("cayo_dato", "cayo_accion"):
        recs.insert(0, "Si esto fuera real: cambia tus claves, avisa a la entidad y reporta el incidente de inmediato.")
    return {
        "outcome": outcome,
        "outcome_label": OUTCOME_LABEL[outcome],
        "score": score,
        "scenario": {"id": sc.id, "title": sc.title, "entity": sc.entity, "channel": sc.channel,
                     "technique": sc.technique, "stage": sc.stage},
        "principle": sc.principle,
        "principle_label": PRINCIPLE_LABELS[sc.principle],
        "red_flags": list(sc.red_flags),
        "recommendations": recs,
        "lesson": sc.lesson,
        "events": s.events,
        "iso_controls": [{"id": c, "name": ISO[c]} for c in controls],
        "provider": _provider.name,
    }
