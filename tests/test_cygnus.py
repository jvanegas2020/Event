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


# ---------------- Programa: diagnóstico -> plan -> simulaciones -> informe ----------------
from cygnus import diagnostic, program


def _answers(phase, pick):
    """pick: 'safe' | 'risky' -> respuestas con menor / mayor riesgo en cada ítem."""
    out = {}
    for it in diagnostic.ITEMS:
        if it.form in (("A", "H") if phase == "pre" else ("B",)):
            risks = [r for _, r in it.options]
            out[it.id] = risks.index(min(risks) if pick == "safe" else max(risks))
    return out


def test_diagnostic_scoring_extremes():
    assert diagnostic.score("pre", _answers("pre", "safe"))["overall"] == 0
    r = diagnostic.score("pre", _answers("pre", "risky"))
    assert r["overall"] == 100 and r["level"] == "crítico"
    assert diagnostic.risk_level(24) == "bajo" and diagnostic.risk_level(50) == "alto"


def test_diagnostic_rejects_incomplete_or_invalid():
    with pytest.raises(ValueError):
        diagnostic.score("pre", {"A1": 0})
    bad = _answers("pre", "safe"); bad["A1"] = 99
    with pytest.raises(ValueError):
        diagnostic.score("pre", bad)


def test_questions_do_not_leak_risk_and_forms_are_parallel():
    qs = diagnostic.questions("pre")
    assert all("risk" not in str(q) for q in qs)
    a = {i.principle for i in diagnostic.ITEMS if i.form == "A"}
    b = {i.principle for i in diagnostic.ITEMS if i.form == "B"}
    assert a == b == set(PRINCIPLES)


def test_plan_is_dynamic():
    high = program.build_plan(diagnostic.score("pre", _answers("pre", "risky")))
    low_ans = _answers("pre", "safe"); low_ans["A2"] = [r for _, r in diagnostic.BY_ID["A2"].options].index(100)
    low = program.build_plan(diagnostic.score("pre", low_ans))
    assert high["n"] == 6 and low["n"] == 3
    assert low["items"][0]["principle"] == "urgencia"        # empieza por lo más débil
    # riesgo alto -> el escenario más básico disponible para ese principio
    for i in high["items"]:
        lowest = min(sc.level for sc in SCENARIOS if sc.principle == i["principle"])
        assert i["level"] == lowest


def test_full_program_flow_and_report():
    uid = "programa-flujo-01"
    st = client.post("/api/program", json={"user_id": uid, "consent": True}).json()
    pid = st["program_id"]; assert st["stage"] == "diagnostico_inicial"
    # no se puede simular sin diagnóstico
    assert client.post(f"/api/program/{pid}/session").status_code == 409
    qs = client.get(f"/api/program/{pid}/diagnostic/pre").json()["questions"]
    assert len(qs) == 10
    r = client.post(f"/api/program/{pid}/diagnostic/pre", json={"answers": _answers("pre", "risky")}).json()
    assert r["state"]["stage"] == "entrenamiento" and r["plan"]["n"] == 6
    # el diagnóstico inicial no se puede repetir
    assert client.post(f"/api/program/{pid}/diagnostic/pre", json={"answers": _answers("pre", "safe")}).status_code == 400
    # simulaciones del plan, con respuestas seguras
    for k in range(6):
        s = client.post(f"/api/program/{pid}/session").json()
        assert s["index"] == k + 1
        assert s["scenario"]["id"] == r["plan"]["items"][k]["scenario_id"]
        m = client.post(f"/api/session/{s['session_id']}/message",
                        json={"text": "no voy a dar nada, llamo al número oficial"}).json()
        assert m["finished"] and m["turn_score"] == 90
    st = client.get(f"/api/program/{pid}").json()
    assert st["stage"] == "diagnostico_final"
    assert client.get(f"/api/program/{pid}/report").status_code == 409   # aún no
    hm = st["heatmap"]
    assert len(hm["rows"]) == 6 and len(hm["columns"]) == 8
    assert any(v == 10 for row in hm["rows"] for v in row["cells"])      # sim con score 90 -> riesgo 10
    client.post(f"/api/program/{pid}/diagnostic/post", json={"answers": _answers("post", "safe")})
    rep = client.get(f"/api/program/{pid}/report").json()
    assert rep["before"]["level"] == "crítico" and rep["after"]["overall"] == 0
    assert rep["improved"] and rep["delta"] == -100
    assert len(rep["simulations"]) == 6 and rep["habit_findings"]


def test_post_diagnostic_requires_finished_training():
    uid = "programa-flujo-02"
    pid = client.post("/api/program", json={"user_id": uid, "consent": True}).json()["program_id"]
    client.post(f"/api/program/{pid}/diagnostic/pre", json={"answers": _answers("pre", "safe")})
    r = client.post(f"/api/program/{pid}/diagnostic/post", json={"answers": _answers("post", "safe")})
    assert r.status_code == 400


def test_live_turn_score_for_heatmap():
    sid, _ = None, None
    s = client.post("/api/session", json={"user_id": UID, "consent": True, "scenario_id": "fin-sms-bloqueo"}).json()
    m1 = client.post(f"/api/session/{s['session_id']}/message", json={"text": "hmm, quién es?"}).json()
    m2 = client.post(f"/api/session/{s['session_id']}/message", json={"text": "mi clave es 998877"}).json()
    assert m1["turn_score"] == 45 and m2["turn_score"] == 0


def test_ui_is_never_served_stale():
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/static/app.js").headers["cache-control"] == "no-cache"
