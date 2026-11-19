const $ = (id) => document.getElementById(id);
const LABELS = {autoridad:"Autoridad",urgencia:"Urgencia",reciprocidad:"Reciprocidad",simpatia:"Simpatía",prueba_social:"Prueba social",compromiso:"Compromiso"};
let uid, sid, turn = 0;
try { uid = localStorage.getItem("cygnus_uid"); } catch (e) {}
if (!uid) { uid = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now()).replace(/[^A-Za-z0-9_-]/g, ""); try { localStorage.setItem("cygnus_uid", uid); } catch (e) {} }

async function api(path, opts) {
  const r = await fetch("/api" + path, opts && {headers:{"Content-Type":"application/json"}, ...opts});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || "Error");
  return j;
}
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
function bubble(cls, text) { const d = document.createElement("div"); d.className = "bubble " + cls; d.textContent = text; $("log").appendChild(d); $("log").scrollTop = 1e6; }
function note(text) { const d = document.createElement("div"); d.className = "fb"; d.textContent = text; $("log").appendChild(d); $("log").scrollTop = 1e6; }

async function loadProfile() {
  const p = await api("/profile/" + uid);
  $("iris").textContent = p.iris == null ? "(sin datos aún)" : `· Índice de resistencia: ${p.iris}/100 · nivel ${p.level}`;
  $("bars").innerHTML = Object.entries(p.susceptibility).map(([k, v]) =>
    `<div class="bar"><span>${LABELS[k]}</span><div class="track"><div class="fill" style="width:${v}%"></div></div><span>${Math.round(v)}</span></div>`).join("")
    + `<p class="hint">Barra más larga = más vulnerable (50 = aún sin medir).</p>`;
}

async function begin() {
  $("report").classList.add("hidden"); $("again").classList.add("hidden");
  $("log").innerHTML = ""; turn = 0;
  const s = await api("/session", {method:"POST", body: JSON.stringify({user_id: uid, consent: true})});
  sid = s.session_id;
  $("consent").classList.add("hidden"); $("chat").classList.remove("hidden");
  $("channel").textContent = s.scenario.channel; $("title").textContent = s.scenario.title;
  $("why").textContent = s.why; $("max").textContent = s.max_turns; $("turn").textContent = 0;
  $("form").classList.remove("hidden");
  bubble("attacker", s.attacker); $("msg").focus();
}

function showReport(r) {
  $("form").classList.add("hidden");
  const cls = r.score >= 80 ? "good" : r.score >= 40 ? "mid" : "bad";
  $("report").innerHTML = `
    <h2>Reporte de la simulación</h2>
    <div class="score ${cls}">${r.score}/100</div><strong>${esc(r.outcome_label)}</strong>
    <p>Escenario: ${esc(r.scenario.title)} · principio explotado: <strong>${esc(r.principle_label)}</strong> · técnica: ${esc(r.scenario.technique)}</p>
    <p class="hint">${esc(r.lesson)}</p>
    <h3>Señales de alerta que debías notar</h3><ul>${r.red_flags.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    <h3>Qué hacer</h3><ul>${r.recommendations.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    <h3>Controles ISO/IEC 27001:2022 relacionados</h3>
    <div class="chips">${r.iso_controls.map(c => `<span class="chip" title="${esc(c.name)}">${c.id} · ${esc(c.name)}</span>`).join("")}</div>`;
  $("report").classList.remove("hidden"); $("again").classList.remove("hidden");
  loadProfile();
}

$("ok").onchange = (e) => $("start").disabled = !e.target.checked;
$("start").onclick = () => begin().catch(e => alert(e.message));
$("again").onclick = () => begin().catch(e => alert(e.message));
$("form").onsubmit = async (e) => {
  e.preventDefault();
  const text = $("msg").value.trim(); if (!text) return;
  $("msg").value = ""; bubble("user", text); $("turn").textContent = ++turn;
  try {
    const r = await api(`/session/${sid}/message`, {method:"POST", body: JSON.stringify({text})});
    note(r.feedback);
    if (r.finished) showReport(r.report); else bubble("attacker", r.attacker);
  } catch (err) { note(err.message); }
};
$("erase").onclick = async () => {
  if (!confirm("¿Borrar todos tus resultados guardados?")) return;
  await api("/profile/" + uid, {method:"DELETE"}); loadProfile();
};
loadProfile();
