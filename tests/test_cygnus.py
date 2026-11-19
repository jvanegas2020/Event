import os
import tempfile

os.environ["CYGNUS_DB"] = os.path.join(tempfile.mkdtemp(), "t.db")
os.environ.pop("ANTHROPIC_API_KEY", None)

import pytest
from fastapi.testclient import TestClient

from cygnus import profile
from cygnus.api import app
from cygnus.evaluator import COMPLY, DISCLOSE, NEUTRAL, REPORT, SAFE, classify
from cygnus.scenarios import PRINCIPLES, SCENARIOS

client = TestClient(app)
UID = "usuario-prueba-001"


@pytest.mark.parametrize("text,expected", [
    ("mi clave es 4455", DISCLOSE),
    ("el código es 123456", DISCLOSE),
    ("te paso mi cédula", DISCLOSE),
    ("No voy a dar mi clave, llamo al banco", SAFE),
    ("Voy a llamar directamente al número oficial", SAFE),
    ("cuelgo, esto es una estafa", SAFE),
    ("voy a reportar este mensaje al área de seguridad", REPORT),
    ("hago clic en el enlace", COMPLY),
    ("ok, te ayudo", COMPLY),
    ("no te ayudo", SAFE),
    ("no hago clic", SAFE),
    ("¿quién eres?", NEUTRAL),
    ("", NEUTRAL),
])
def test_classify(text, expected):
    assert classify(text) == expected


def test_scenarios_are_safe_and_complete():
    for s in SCENARIOS:
        assert s.principle in PRINCIPLES
        text = " ".join((s.opening, *s.escalations))
        for token in text.split():
            if token.startswith("http"):
                assert ".example" in token, f"{s.id}: enlace no ficticio"
        assert s.red_flags and s.safe_actions and s.escalations


def test_consent_required():
    r = client.post("/api/session", json={"user_id": UID, "consent": False})
    assert r.status_code == 400


def test_invalid_user_id():
    r = client.post("/api/session", json={"user_id": "x y", "consent": True})
    assert r.status_code == 400


def _play(texts, scenario_id=None):
    r = client.post("/api/session", json={"user_id": UID, "consent": True, "scenario_id": scenario_id})
    assert r.status_code == 200
    sid = r.json()["session_id"]
    last = None
    for t in texts:
        last = client.post(f"/api/session/{sid}/message", json={"text": t}).json()
        if last["finished"]:
            break
    return sid, last


def test_resist_flow_and_profile():
    _, last = _play(["no voy a dar nada, llamo al banco"], "fin-sms-bloqueo")
    assert last["finished"] and last["report"]["outcome"] == "resistio"
    assert last["report"]["score"] == 90
    p = client.get(f"/api/profile/{UID}").json()
    assert p["simulations"] == 1 and p["susceptibility"]["urgencia"] < 50


def test_fall_flow():
    _, last = _play(["mi clave es 998877"], "fin-llamada-fraude")
    assert last["report"]["outcome"] == "cayo_dato" and last["report"]["score"] == 0
    assert any(c["id"] == "A.8.5" for c in last["report"]["iso_controls"])


def test_indecisive_after_max_turns_and_no_text_stored():
    secret = "hablemos mas sobre esto"
    _, last = _play([secret] * 6, "edu-correo-beca")
    assert last["finished"] and last["report"]["outcome"] == "indeciso"
    assert last["report"]["score"] == 0  # 40 - 4 turnos neutrales * 10
    import sqlite3
    dump = "".join(str(r) for r in sqlite3.connect(os.environ["CYGNUS_DB"]).execute("select * from results"))
    assert secret not in dump


def test_cannot_reply_after_finish():
    sid, _ = _play(["reporto esto"], "sal-correo-resultados")
    r = client.post(f"/api/session/{sid}/message", json={"text": "hola"})
    assert r.status_code == 409


def test_adaptive_selection_targets_weakest():
    uid = "adaptativo-0001"
    sc = next(s for s in SCENARIOS if s.principle == "autoridad" and s.level == 1)
    profile.record(uid, sc, "cayo_dato", 0)
    nxt, _ = profile.next_scenario(uid)
    assert nxt.principle == "autoridad"


def test_erase():
    _play(["reporto"], "fin-sms-bloqueo")
    assert client.delete(f"/api/profile/{UID}").json()["deleted"] >= 1
    assert client.get(f"/api/profile/{UID}").json()["simulations"] == 0


def test_frontend_served():
    assert client.get("/").status_code == 200
    assert client.get("/static/app.js").status_code == 200
