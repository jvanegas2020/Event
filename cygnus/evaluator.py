"""Evaluador determinista de las respuestas del usuario.

Es deliberadamente basado en reglas: es auditable, reproducible y no depende
de un LLM (que solo se usa para redactar los mensajes del atacante simulado).
"""
from __future__ import annotations

import re
import unicodedata

SAFE = "seguro"
REPORT = "reporto"
DISCLOSE = "revelo_dato"
COMPLY = "ejecuto_accion"
NEUTRAL = "neutral"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", text).strip()


# Entrega explícita de datos (se evalúa primero: es lo más grave).
_DISCLOSE = [
    r"\bmi (clave|contrasena|password|pin|usuario|cedula|documento)( es| son|:)",
    r"\b(el )?(codigo|otp|token)( es|:)? ?\d{3,}",
    r"\b\d{6,}\b",                                  # secuencias largas: OTP, cédula, tarjeta
    r"\bte (paso|doy|envio|mando) (mi|el|la|los|las) (clave|contrasena|codigo|cedula|datos|tarjeta)",
    r"\b(aqui (esta|tiene)|ahi va) (mi|el|la)",
    r"\bsoy (el|la) titular\b.*\b(dato|clave|codigo)",
    r"\badjunto (mi )?(cedula|documento)",
]

# Rechazo / verificación por canal oficial.
_SAFE = [
    r"\bno (voy a|pienso|quiero|puedo|debo|te voy a|le voy a) (dar|compartir|enviar|pasar|hacer|abrir|instalar|decir|entregar|pagar|transferir|comprar)",
    r"\bno (hare|hago|abrire|abro|doy|dare|compartire|comparto|enviare|envio|instalare|pagare|pago|transferire) ",
    r"\b(llamo|llamare|voy a llamar|contacto|contactare|consulto|verifico|verificare|confirmo|confirmare) ?(directamente )?(al|a la|con|por|en)\b",
    r"\bcanal(es)? oficial(es)?\b", r"\bnumero (oficial|de la tarjeta|impreso)\b",
    r"\b(es|parece|suena a|esto es) (un |una )?(phishing|estafa|fraude|engano|intento de)",
    r"\bcuelgo\b", r"\b(voy a )?colgar\b", r"\bbloqueo (el|este) (numero|contacto)",
    r"\bno (confio|caigo)\b", r"\bnunca (comparto|doy|pido)",
    r"\bno (te |le )?(ayudo|colaboro|creo|voy)\b",
]

# Denuncia / aviso a la organización.
_REPORT = [
    r"\b(reporto|reportare|voy a reportar|reportar|denuncio|denunciare|avisare|aviso|notifico|notificare|informare) ",
    r"\b(area|equipo) de (seguridad|ti|sistemas)\b", r"\bsoc\b",
]

# Cumplimiento de la acción pedida por el atacante.
_COMPLY = [
    r"\b(hago|hice|abro|abri|abrire|di|doy|doy el|ya di|pulso|pulse|presiono) (clic|click|el enlace|al enlace|en el enlace)",
    r"\bya (entre|ingrese|abri|instale|pague|transferi|compre|descargue|complete|envie)\b",
    r"\b(descargo|instalo|instalare|pago|pagare|transfiero|transferire|compro|comprare|ingreso|ingresare|completo|completare) ",
    r"\b(ok|vale|claro|listo|de acuerdo|esta bien|con gusto|por supuesto|si)[,. ]+(te |le )?(ayudo|colaboro|envio|mando|hago|paso|doy)",
    r"\b(ayudo|colaboro|te ayudo|le ayudo|con gusto)\b",
]


def _any(patterns: list[str], text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


def classify(user_text: str) -> str:
    """Devuelve una de: DISCLOSE, REPORT, SAFE, COMPLY, NEUTRAL."""
    t = normalize(user_text)
    if not t:
        return NEUTRAL
    safe = _any(_SAFE, t)
    if _any(_DISCLOSE, t) and not safe:
        return DISCLOSE
    if _any(_REPORT, t):
        return REPORT
    if safe:
        return SAFE
    if _any(_DISCLOSE, t):
        return DISCLOSE
    if _any(_COMPLY, t):
        return COMPLY
    return NEUTRAL
