"""API HTTP (FastAPI) + frontend estático."""
from __future__ import annotations

import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import diagnostic, engine, profile, program
from .scenarios import PRINCIPLE_LABELS, SCENARIOS

app = FastAPI(title="Cygnus 2.0", version="0.1.0")
STATIC = os.path.join(os.path.dirname(__file__), "static")
UID = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


def _uid(v: str) -> str:
    if not UID.match(v):
        raise HTTPException(400, "user_id inválido")
    return v


class StartIn(BaseModel):
    user_id: str
    consent: bool
    scenario_id: str | None = None


class MsgIn(BaseModel):
    text: str = Field(min_length=1, max_length=engine.MAX_LEN)


@app.get("/api/health")
def health():
    return {"ok": True, "provider": engine._provider.name}


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": [s.public() for s in SCENARIOS], "principles": PRINCIPLE_LABELS}


@app.post("/api/session")
def start(body: StartIn):
    if not body.consent:
        raise HTTPException(400, "Se requiere consentimiento informado para entrenar.")
    uid = _uid(body.user_id)
    if body.scenario_id and body.scenario_id not in {s.id for s in SCENARIOS}:
        raise HTTPException(404, "Escenario no existe")
    s, why = engine.start(uid, body.scenario_id)
    return {"session_id": s.id, "why": why, "scenario": s.scenario.public(),
            "attacker": s.history[0][1], "max_turns": engine.MAX_TURNS}


@app.post("/api/session/{session_id}/message")
def message(session_id: str, body: MsgIn):
    s = engine.get(session_id)
    if not s:
        raise HTTPException(404, "Sesión no encontrada o expirada")
    try:
        return engine.reply(s, body.text)
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/profile/{user_id}")
def get_profile(user_id: str):
    return profile.summary(_uid(user_id))


@app.delete("/api/profile/{user_id}")
def erase(user_id: str):
    return {"deleted": profile.delete_user(_uid(user_id))}


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------- Programa: diagnóstico -> plan -> simulaciones -> informe ----------------
class ProgramIn(BaseModel):
    user_id: str
    consent: bool
    restart: bool = False


class DiagIn(BaseModel):
    answers: dict[str, int]


def _prog_or_404(pid: str):
    try:
        return program.state(pid)
    except KeyError:
        raise HTTPException(404, "Programa no encontrado")


@app.post("/api/program")
def program_start(body: ProgramIn):
    if not body.consent:
        raise HTTPException(400, "Se requiere consentimiento informado.")
    uid = _uid(body.user_id)
    prog = None if body.restart else profile.latest_program(uid)
    if prog and program.state(prog["id"])["stage"] == "informe":
        prog = None   # el anterior ya terminó: se abre uno nuevo
    if not prog:
        prog = program.create(uid)
    return program.state(prog["id"])


@app.get("/api/program/by-user/{user_id}")
def program_by_user(user_id: str):
    prog = profile.latest_program(_uid(user_id))
    return program.state(prog["id"]) if prog else {"stage": "sin_programa"}


@app.get("/api/program/{pid}")
def program_get(pid: str):
    return _prog_or_404(pid)


@app.get("/api/program/{pid}/diagnostic/{phase}")
def diagnostic_questions(pid: str, phase: str):
    _prog_or_404(pid)
    if phase not in ("pre", "post"):
        raise HTTPException(404, "Fase inválida")
    return {"phase": phase, "questions": diagnostic.questions(phase)}


@app.post("/api/program/{pid}/diagnostic/{phase}")
def diagnostic_submit(pid: str, phase: str, body: DiagIn):
    _prog_or_404(pid)
    try:
        return {**program.submit_diagnostic(pid, phase, body.answers), "state": program.state(pid)}
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post("/api/program/{pid}/session")
def program_session(pid: str):
    st = _prog_or_404(pid)
    if st["stage"] != "entrenamiento":
        raise HTTPException(409, "No hay simulaciones pendientes en este momento")
    prog = profile.get_program(pid)
    sid = program.next_scenario_id(pid)
    s, why = engine.start(prog["user_id"], sid, program_id=pid)
    item = st["plan"]["items"][st["completed"]]
    return {"session_id": s.id, "why": item["reason"], "scenario": s.scenario.public(),
            "attacker": s.history[0][1], "max_turns": engine.MAX_TURNS,
            "index": st["completed"] + 1, "total": st["total"]}


@app.get("/api/program/{pid}/report")
def program_report(pid: str):
    _prog_or_404(pid)
    try:
        return program.final_report(pid)
    except ValueError as e:
        raise HTTPException(409, str(e))
