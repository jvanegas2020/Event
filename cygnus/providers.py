"""Proveedores del atacante simulado.

* ScriptedProvider: sin dependencias ni claves; usa los guiones del escenario.
* AnthropicProvider: redacta los mensajes del atacante con un LLM, dentro de
  límites estrictos. Si falla o no hay clave, vuelve al guion.

El LLM SOLO escribe lo que diría el atacante dentro del chat de entrenamiento.
La evaluación y el puntaje siguen siendo deterministas (evaluator.py).
"""
from __future__ import annotations

import os

import httpx

from .scenarios import Scenario

GUARDRAILS = (
    "Eres Cygnus, un simulador EDUCATIVO de ingeniería social para entrenar a personas. "
    "Interpretas al atacante dentro de un chat de entrenamiento controlado y consentido.\n"
    "Reglas inquebrantables:\n"
    "- Usa SOLO la entidad ficticia indicada. Nunca menciones bancos, empresas ni personas reales.\n"
    "- Todo enlace debe terminar en .example (p. ej. https://ejemplo-verifica.example). Nunca enlaces reales.\n"
    "- No generes malware, instrucciones técnicas de ataque ni material reutilizable fuera de la simulación.\n"
    "- Mensajes cortos (máx. 60 palabras), en español de Colombia, tono realista y creciente en presión.\n"
    "- Mantén el principio psicológico indicado. No rompas el personaje ni reveles que es una simulación.\n"
    "- Si el usuario pide algo ajeno al entrenamiento, responde en personaje con una excusa breve."
)


class ScriptedProvider:
    name = "guion"

    def attacker_message(self, sc: Scenario, history: list[tuple[str, str]], turn: int) -> str:
        if turn == 0:
            return sc.opening
        idx = min(turn - 1, len(sc.escalations) - 1)
        return sc.escalations[idx]


class AnthropicProvider(ScriptedProvider):
    name = "anthropic"
    URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str, model: str):
        self.api_key, self.model = api_key, model

    def attacker_message(self, sc, history, turn):
        if turn == 0:
            return sc.opening  # la apertura siempre es la del guion: controlada y revisada
        sys_prompt = (
            f"{GUARDRAILS}\n\nEscenario: {sc.title}. Entidad ficticia: {sc.entity}. Canal: {sc.channel}. "
            f"Principio de Cialdini: {sc.principle}. Técnica: {sc.technique}. Turno {turn}: aumenta la presión."
        )
        msgs = []
        for role, text in history:
            msgs.append({"role": "assistant" if role == "attacker" else "user", "content": text})
        try:
            r = httpx.post(
                self.URL,
                headers={"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
                json={"model": self.model, "max_tokens": 220, "system": sys_prompt, "messages": msgs},
                timeout=20,
            )
            r.raise_for_status()
            text = "".join(b.get("text", "") for b in r.json().get("content", [])).strip()
            if text and "http" in text and ".example" not in text:
                raise ValueError("enlace no permitido")
            if text:
                return text
        except Exception:
            pass
        return super().attacker_message(sc, history, turn)


def get_provider():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return AnthropicProvider(key, os.environ.get("CYGNUS_MODEL", "claude-sonnet-5-5"))
    return ScriptedProvider()
