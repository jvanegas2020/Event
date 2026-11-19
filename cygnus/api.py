"""API HTTP (FastAPI) + frontend estático."""
from __future__ import annotations

import os
import re

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import engine, profile
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
