const $ = (id) => document.getElementById(id);
const SECTIONS = ["consent", "diag", "plan", "chat", "simreport", "final"];
const STEPS = [["diagnostico_inicial", "1 Diagnóstico"], ["entrenamiento", "2 Entrenamiento"], ["diagnostico_final", "3 Evaluación final"], ["informe", "4 Informe"]];
let uid, pid, sid, turn = 0, S = null;
try { uid = localStorage.getItem("cygnus_uid"); } catch (e) {}
if (!uid) { uid = (crypto.randomUUID ? crypto.randomUUID() : String(Math.random()).slice(2) + Date.now()).replace(/[^A-Za-z0-9_-]/g, ""); try { localStorage.setItem("cygnus_uid", uid); } catch (e) {} }

async function api(path, opts) {
  const r = await fetch("/api" + path, opts && { headers: { "Content-Type": "application/json" }, ...opts });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || "Error");
  return j;
}
const post = (p, body) => api(p, { method: "POST", body: JSON.stringify(body || {}) });
function esc(s) { const d = document.createElement("div"); d.textContent = s; return d.innerHTML; }
function show(...ids) { SECTIONS.forEach(s => $(s).classList.toggle("hidden", !ids.includes(s))); }
const riskColor = (v) => `hsl(${Math.round(120 * (1 - v / 100))},62%,${v > 40 && v < 62 ? 40 : 44}%)`;
const lvl = (l) => `<span class="pill lvl-${l}">${l}</span>`;

function steps(stage) {
  const order = STEPS.map(s => s[0]); const cur = order.indexOf(stage);
  $("steps").innerHTML = STEPS.map(([k, label], i) => `<li class="${i < cur ? "done" : i === cur ? "on" : ""}">${label}</li>`).join("");
}
function heat(h) {
  if (!h) { $("heat").classList.add("hidden"); return; }
  const head = h.columns.map(c => `<th>${esc(c.label)}</th>`).join("");
  const rows = h.rows.map(r => `<tr><td>${esc(r.label)}</td>` + r.cells.map(v =>
    v == null ? `<td class="e">·</td>` : `<td class="c" style="background:${riskColor(v)}" title="Riesgo ${Math.round(v)}/100">${Math.round(v)}</td>`).join("") + `</tr>`).join("");
  $("heatgrid").innerHTML = `<table class="hm"><tr><th></th>${head}</tr>${rows}</table>`;
  $("heat").classList.remove("hidden");
}

/* ---------- enrutador por etapa ---------- */
async function route() {
  S = await api("/program/by-user/" + uid);
  if (S.stage === "sin_programa") { steps("diagnostico_inicial"); show("consent"); $("heat").classList.add("hidden"); return; }
  pid = S.program_id; steps(S.stage); heat(S.pre ? S.heatmap : null);
  if (S.stage === "diagnostico_inicial") return diagnostic("pre");
  if (S.stage === "entrenamiento") return showPlan();
  if (S.stage === "diagnostico_final") return diagnostic("post");
  return finalReport();
}

/* ---------- diagnóstico (pre / post) ---------- */
async function diagnostic(phase) {
  const { questions } = await api(`/program/${pid}/diagnostic/${phase}`);
  const answers = {}; let i = 0;
  const title = phase === "pre" ? "Diagnóstico de tu nivel de riesgo" : "Evaluación final (situaciones nuevas)";
  const intro = phase === "pre"
    ? "Responde con sinceridad lo que harías de verdad. No hay respuestas «buenas» para quedar bien: el plan se arma con lo que contestes."
    : "Situaciones distintas a las del inicio, para medir cuánto cambió tu criterio.";
  const draw = () => {
    const q = questions[i];
    $("diag").innerHTML = `<h2>${title}</h2><p class="hint">${intro}</p>
      <div class="progress"><i style="width:${(i / questions.length) * 100}%"></i></div>
      <p><strong>${i + 1}/${questions.length}.</strong> ${esc(q.text)}</p>` +
      q.options.map((o, k) => `<button class="opt" data-k="${k}">${esc(o)}</button>`).join("");
    $("diag").querySelectorAll(".opt").forEach(b => b.onclick = async () => {
      answers[q.id] = +b.dataset.k;
      if (++i < questions.length) return draw();
      try { const r = await post(`/program/${pid}/diagnostic/${phase}`, { answers }); S = r.state; await route(); }
      catch (e) { alert(e.message); }
    });
  };
  show("diag"); draw();
}

/* ---------- plan dinámico ---------- */
function showPlan() {
  const p = S.plan, pre = S.pre, done = S.completed;
  $("plan").innerHTML = `<h2>Tu plan de entrenamiento</h2>
    <div class="big"><div><div class="hint">Riesgo inicial</div><div class="n">${Math.round(pre.overall)}<small>/100</small></div></div><div>${lvl(pre.level)}</div></div>
    <p>${esc(p.summary)}</p>` +
    p.items.map((it, k) => `<div class="planitem"><strong>${k + 1}. ${esc(it.title)}</strong>
      <span class="badge">${esc(it.channel)}</span> ${k < done ? "✅" : ""}<div class="hint">${esc(it.reason)}</div></div>`).join("") +
    (pre.habits_score != null ? `<p class="hint">Factor de hábitos: ${Math.round(pre.habits_score)}/100 (se incluye en tu informe final).</p>` : "") +
    `<button id="go">${done ? "Continuar con la simulación " + (done + 1) : "Comenzar entrenamiento"}</button>`;
  show("plan"); $("go").onclick = () => beginSim().catch(e => alert(e.message));
}


/* ---------- modo voz (Web Speech API del navegador) ---------- */
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const TTS = "speechSynthesis" in window;
let voiceOn = false, rec = null, listening = false, channelNow = "", busy = false;

function pickVoice() {
  const vs = speechSynthesis.getVoices();
  return vs.find(v => /es-CO|es-MX|es-US/i.test(v.lang)) || vs.find(v => /^es/i.test(v.lang)) || null;
}
function speakable(t) {
  return t.replace(/https?:\/\/\S+/g, "un enlace").replace(/\[|\]/g, "").replace(/^Asunto:\s*/i, "Asunto. ").replace(/\n+/g, ". ");
}
function speak(text, { coach = false, onend = () => {} } = {}) {
  if (!voiceOn || !TTS) return onend();
  let done = false; const fin = () => { if (!done) { done = true; onend(); } };
  try {
    speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(speakable(text));
    const v = pickVoice(); if (v) u.voice = v;
    u.lang = v ? v.lang : "es-CO"; u.rate = coach ? 1.0 : 1.05; u.pitch = coach ? 1.0 : 0.85;
    u.onend = fin; u.onerror = fin;
    setTimeout(fin, Math.min(30000, 2500 + text.length * 90));   // por si el navegador no dispara onend
    speechSynthesis.speak(u);
  } catch (e) { fin(); }
}
function vstatus(t) { const el = $("voicestatus"); el.textContent = t || ""; el.classList.toggle("hidden", !t); }

function stopListening() { listening = false; $("mic").classList.remove("on"); if (rec) { try { rec.abort(); } catch (e) {} rec = null; } }
function listen() {
  if (!voiceOn || !SR || listening || busy || rec) return;
  rec = new SR(); rec.lang = "es-CO"; rec.interimResults = true; rec.continuous = false; rec.maxAlternatives = 1;
  let finalText = "";
  rec.onstart = () => { listening = true; $("mic").classList.add("on"); vstatus("🎙️ Te escucho… habla ahora"); };
  rec.onresult = (e) => {
    let interim = "";
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const tr = e.results[i][0].transcript;
      if (e.results[i].isFinal) finalText += tr; else interim += tr;
    }
    $("msg").value = (finalText + interim).trim();
  };
  rec.onerror = (e) => {
    listening = false; $("mic").classList.remove("on");
    if (e.error === "not-allowed" || e.error === "service-not-allowed") vstatus("⚠️ El navegador bloqueó el micrófono. Permítelo en el candado de la barra de direcciones o escribe tu respuesta.");
    else if (e.error === "no-speech") vstatus("No te escuché. Toca 🎙️ para intentarlo de nuevo.");
    else if (e.error !== "aborted") vstatus("No pude usar la voz (" + e.error + "). Puedes escribir.");
  };
  rec.onend = () => {
    rec = null; listening = false; $("mic").classList.remove("on");
    const t = (finalText || $("msg").value).trim();
    if (t && !busy) { vstatus("Enviando: «" + t + "»"); sendText(t); }
  };
  try { rec.start(); } catch (e) { vstatus("No pude iniciar el micrófono."); }
}
function setVoice(on) {
  voiceOn = on && (SR || TTS);
  try { localStorage.setItem("cygnus_voice", voiceOn ? "1" : "0"); } catch (e) {}
  $("voice").checked = voiceOn;
  $("mic").classList.toggle("hidden", !(voiceOn && SR));
  if (!voiceOn) { stopListening(); if (TTS) speechSynthesis.cancel(); vstatus(""); }
  else if (!SR) vstatus("Tu navegador puede hablar pero no escuchar. Para responder con la voz usa Chrome o Edge; por ahora escribe tu respuesta.");
}
function voiceUI(channel) {
  channelNow = channel;
  const supported = !!(SR || TTS);
  $("voicewrap").classList.toggle("hidden", !supported);
  $("callbar").classList.toggle("hidden", channel !== "llamada");
  $("hangup").classList.toggle("hidden", channel !== "llamada");
  let saved = null; try { saved = localStorage.getItem("cygnus_voice"); } catch (e) {}
  setVoice(supported && (saved === "1" || (saved === null && channel === "llamada")));
}
function attackerSays(text) {
  const b = document.createElement("div"); b.className = "bubble attacker"; b.textContent = text;
  $("log").appendChild(b); $("log").scrollTop = 1e6;
  b.classList.add("speaking");
  speak(text, { onend: () => { b.classList.remove("speaking"); if (!$("form").classList.contains("hidden")) listen(); } });
}
$("voice").onchange = (e) => setVoice(e.target.checked);
$("mic").onclick = () => { if (listening) { try { rec.stop(); } catch (e) {} } else { if (TTS) speechSynthesis.cancel(); listen(); } };
$("hangup").onclick = () => sendText("Cuelgo la llamada.");
if (TTS) speechSynthesis.onvoiceschanged = () => {};

/* ---------- simulación con mapa de calor en vivo ---------- */
function bubble(cls, text) { const d = document.createElement("div"); d.className = "bubble " + cls; d.textContent = text; $("log").appendChild(d); $("log").scrollTop = 1e6; }
function note(text) { const d = document.createElement("div"); d.className = "fb"; d.textContent = text; $("log").appendChild(d); $("log").scrollTop = 1e6; }

async function beginSim() {
  const s = await post(`/program/${pid}/session`);
  sid = s.session_id; turn = 0; $("log").innerHTML = ""; $("strip").innerHTML = "";
  show("chat");
  $("channel").textContent = s.scenario.channel; $("title").textContent = s.scenario.title;
  $("idx").textContent = `· simulación ${s.index} de ${s.total}`;
  $("why").textContent = s.why; $("max").textContent = s.max_turns; $("turn").textContent = 0;
  $("form").classList.remove("hidden"); voiceUI(s.scenario.channel); attackerSays(s.attacker); $("msg").focus();
}
function addStrip(score) { const i = document.createElement("i"); i.style.background = riskColor(100 - score); i.title = `Calidad de la respuesta: ${score}/100`; $("strip").appendChild(i); }

async function sendText(text) {
  text = (text || "").trim(); if (!text || busy) return;
  busy = true; stopListening(); if (TTS) speechSynthesis.cancel();
  $("msg").value = ""; vstatus(""); bubble("user", text); $("turn").textContent = ++turn;
  try {
    const r = await post(`/session/${sid}/message`, { text });
    addStrip(r.turn_score); note(r.feedback);
    busy = false;
    if (r.finished) { stopListening(); simReport(r.report); speak(`${r.report.outcome_label}. ${r.report.lesson}`, { coach: true }); }
    else attackerSays(r.attacker);
  } catch (err) { busy = false; note(err.message); }
}
$("form").onsubmit = (e) => { e.preventDefault(); sendText($("msg").value); };

async function simReport(r) {
  $("form").classList.add("hidden"); $("callbar").classList.add("hidden"); vstatus("");
  const cls = r.score >= 80 ? "good" : r.score >= 40 ? "mid" : "bad";
  $("simreport").innerHTML = `<h2>Resultado de la simulación</h2>
    <div class="score ${cls}">${r.score}/100</div><strong>${esc(r.outcome_label)}</strong>
    <p>Principio explotado: <strong>${esc(r.principle_label)}</strong> · técnica: ${esc(r.scenario.technique)}</p>
    <p class="hint">${esc(r.lesson)}</p>
    <h3>Señales de alerta que debías notar</h3><ul>${r.red_flags.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    <h3>Qué hacer</h3><ul>${r.recommendations.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
    <button id="nextstep">Continuar</button>`;
  S = await api("/program/" + pid); heat(S.heatmap); steps(S.stage);
  $("nextstep").textContent = S.stage === "entrenamiento" ? "Siguiente simulación" : "Ir a la evaluación final";
  $("nextstep").onclick = () => route();
  show("chat", "simreport"); $("simreport").scrollIntoView({ behavior: "smooth" });
}

/* ---------- informe final antes / después ---------- */
async function finalReport() {
  const r = await api(`/program/${pid}/report`);
  const sign = r.delta > 0 ? "+" : "";
  $("final").innerHTML = `<h2>Informe final: tu perfil de riesgo antes y después</h2>
    <div class="big">
      <div><div class="hint">Antes</div><div class="n">${Math.round(r.before.overall)}</div>${lvl(r.before.level)}</div>
      <div class="n">→</div>
      <div><div class="hint">Después</div><div class="n">${Math.round(r.after.overall)}</div>${lvl(r.after.level)}</div>
      <div class="${r.improved ? "good" : r.delta > 0 ? "bad" : "mid"} n">${sign}${Math.round(r.delta)}</div>
    </div>
    <p>${esc(r.narrative)}</p>
    <h3>Por principio de influencia</h3>` +
    r.by_principle.map(x => `<div class="cmp"><span>${esc(x.label)}</span>
      <div class="pair"><div class="track"><div class="fill b" style="width:${x.before}%"></div></div><div class="track"><div class="fill a" style="width:${x.after}%"></div></div></div>
      <span class="${x.delta < 0 ? "good" : x.delta > 0 ? "bad" : ""}">${Math.round(x.before)}→${Math.round(x.after)}</span></div>`).join("") +
    `<p class="hint"><span style="color:var(--bad)">■</span> antes · <span style="color:hsl(210,70%,55%)">■</span> después (más corto = menos riesgo)</p>
    <h3>Simulaciones realizadas</h3><ul>${r.simulations.map(s => `<li>${esc(s.title)} · ${esc(s.principle)}: <strong>${s.score}/100</strong> (${esc(s.outcome)})</li>`).join("")}</ul>` +
    (r.habit_findings.length ? `<h3>Hábitos por mejorar</h3><ul>${r.habit_findings.map(h => `<li>${esc(h.advice)}</li>`).join("")}</ul>` : "") +
    `<h3>Controles ISO/IEC 27001:2022</h3><div class="chips">${r.iso_controls.map(c => `<span class="chip">${c.id} · ${esc(c.name)}</span>`).join("")}</div>
    <p class="hint">${esc(r.method_note)}</p>
    <button id="again">Iniciar un nuevo programa</button>`;
  show("final"); heat(r.heatmap);
  $("again").onclick = async () => { await post("/program", { user_id: uid, consent: true, restart: true }); route(); };
}

$("ok").onchange = (e) => $("start").disabled = !e.target.checked;
$("start").onclick = async () => { try { await post("/program", { user_id: uid, consent: true }); route(); } catch (e) { alert(e.message); } };
$("erase").onclick = async () => {
  if (!confirm("¿Borrar todos tus resultados y tu programa?")) return;
  await api("/profile/" + uid, { method: "DELETE" }); route();
};
route();
