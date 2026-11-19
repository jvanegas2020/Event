"""Perfil adaptativo seudonimizado (SQLite).

Privacidad por diseño (Ley 1581 de 2012): solo se guarda un identificador
aleatorio y los RESULTADOS de cada simulación. Nunca el texto de los mensajes.
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from contextlib import contextmanager

from .scenarios import PRINCIPLES, SCENARIOS, Scenario

DB_PATH = os.environ.get("CYGNUS_DB", os.path.join(os.path.dirname(__file__), "..", "cygnus.db"))
_lock = threading.Lock()
PRIOR = 50.0  # susceptibilidad asumida para un principio aún no probado


@contextmanager
def _conn():
    con = sqlite3.connect(DB_PATH)
    try:
        con.execute(
            """CREATE TABLE IF NOT EXISTS results(
                 id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL,
                 scenario_id TEXT NOT NULL, principle TEXT NOT NULL, sector TEXT NOT NULL,
                 channel TEXT NOT NULL, outcome TEXT NOT NULL, score INTEGER NOT NULL,
                 ts REAL NOT NULL)"""
        )
        yield con
        con.commit()
    finally:
        con.close()


def record(user_id: str, sc: Scenario, outcome: str, score: int) -> None:
    with _lock, _conn() as con:
        con.execute(
            "INSERT INTO results(user_id,scenario_id,principle,sector,channel,outcome,score,ts) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, sc.id, sc.principle, sc.sector, sc.channel, outcome, score, time.time()),
        )


def history(user_id: str) -> list[dict]:
    with _lock, _conn() as con:
        rows = con.execute(
            "SELECT scenario_id,principle,sector,channel,outcome,score,ts FROM results WHERE user_id=? ORDER BY ts",
            (user_id,),
        ).fetchall()
    keys = ("scenario_id", "principle", "sector", "channel", "outcome", "score", "ts")
    return [dict(zip(keys, r)) for r in rows]


def delete_user(user_id: str) -> int:
    """Derecho de supresión: borra todo lo asociado al identificador."""
    with _lock, _conn() as con:
        return con.execute("DELETE FROM results WHERE user_id=?", (user_id,)).rowcount


def susceptibility(rows: list[dict]) -> dict[str, float]:
    """Susceptibilidad 0-100 por principio (100 = muy vulnerable).

    Media móvil exponencial: las simulaciones recientes pesan más.
    """
    out = {}
    for p in PRINCIPLES:
        vals = [100 - r["score"] for r in rows if r["principle"] == p]
        if not vals:
            out[p] = PRIOR
            continue
        s = vals[0]
        for v in vals[1:]:
            s = 0.4 * s + 0.6 * v
        out[p] = round(s, 1)
    return out


def current_level(rows: list[dict]) -> int:
    """Nivel de dificultad 1-3 según el desempeño reciente."""
    recent = [r["score"] for r in rows[-5:]]
    if len(recent) < 2:
        return 1
    avg = sum(recent) / len(recent)
    return 3 if avg >= 85 and len(recent) >= 4 else 2 if avg >= 65 else 1


def resistance_index(rows: list[dict]) -> int | None:
    """Índice de resistencia (IRIS): promedio ponderado, reciente pesa más."""
    if not rows:
        return None
    w_sum = total = 0.0
    for i, r in enumerate(rows):
        w = 1 + i * 0.25
        total += w * r["score"]
        w_sum += w
    return round(total / w_sum)


def next_scenario(user_id: str) -> tuple[Scenario, str]:
    """Elige el siguiente escenario y explica por qué."""
    rows = history(user_id)
    susc = susceptibility(rows)
    level = current_level(rows)
    weakest = sorted(PRINCIPLES, key=lambda p: -susc[p])
    played = [r["scenario_id"] for r in rows]
    for p in weakest:
        cands = [s for s in SCENARIOS if s.principle == p and s.level <= level]
        if not cands:
            continue
        cands.sort(key=lambda s: (played.count(s.id), -s.level))
        sc = cands[0]
        why = (f"Tu punto más débil estimado es «{p.replace('_', ' ')}» "
               f"({susc[p]:.0f}/100) y tu nivel actual es {level}.")
        if not rows:
            why = "Es tu primera simulación: empezamos con un escenario básico."
        return sc, why
    sc = SCENARIOS[0]
    return sc, "Escenario por defecto."


def summary(user_id: str) -> dict:
    rows = history(user_id)
    return {
        "user_id": user_id,
        "simulations": len(rows),
        "iris": resistance_index(rows),
        "level": current_level(rows),
        "susceptibility": susceptibility(rows),
        "recent": rows[-10:],
    }
