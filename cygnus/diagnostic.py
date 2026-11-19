"""Diagnóstico del nivel de riesgo (pre y post).

Test de juicio situacional: una situación por principio de Cialdini, con 4
opciones cuyo riesgo va de 0 (conducta segura) a 100 (conducta de riesgo).
Hay dos formas PARALELAS (A: diagnóstico inicial, B: diagnóstico final) para
que el antes/después no mida simple memoria de las respuestas.
Los hábitos (solo forma A) se reportan aparte: no entran en el delta.
"""
from __future__ import annotations

import random
from dataclasses import dataclass

from .scenarios import PRINCIPLES

LEVELS = ((75, "crítico"), (50, "alto"), (25, "medio"), (0, "bajo"))


def risk_level(score: float) -> str:
    return next(name for floor, name in LEVELS if score >= floor)


@dataclass(frozen=True)
class Item:
    id: str
    form: str            # "A" | "B" | "H" (hábitos)
    principle: str       # principio de Cialdini o "habito"
    text: str
    options: tuple[tuple[str, int], ...]   # (texto, riesgo 0-100)


ITEMS: tuple[Item, ...] = (
    # ---------- Forma A (diagnóstico inicial) ----------
    Item("A1", "A", "autoridad",
         "Te llama alguien que dice ser del área de sistemas de tu empresa y te pide tu contraseña para «resolver un bloqueo». ¿Qué haces?",
         (("Le doy la contraseña: es de la empresa y no quiero que me bloqueen", 100),
          ("Le digo que no la comparto y lo verifico con TI por un canal oficial", 0),
          ("Le pido nombre y número de empleado y, si suenan bien, se la doy", 70),
          ("Le pido que me escriba por correo y decido después", 30))),
    Item("A2", "A", "urgencia",
         "Te llega un SMS: «Su cuenta será bloqueada en 20 minutos. Verifique aquí» con un enlace. ¿Qué haces?",
         (("Entro rápido al enlace para evitar el bloqueo", 100),
          ("Ignoro el enlace y reviso mi cuenta desde la app oficial o llamo al banco", 0),
          ("Entro al enlace pero no pongo mi clave hasta estar seguro", 70),
          ("Respondo el SMS preguntando si es real", 40))),
    Item("A3", "A", "reciprocidad",
         "Un desconocido te escribe: «Te regalamos un bono de 100.000 pesos». Para entregártelo te pide cédula y datos de tu cuenta. ¿Qué haces?",
         (("Le envío los datos: es un regalo y sería descortés no colaborar", 100),
          ("Busco si la empresa existe, pero igual le doy algunos datos", 60),
          ("No doy nada: un premio que no pedí y que exige mis datos es sospechoso", 0),
          ("Pregunto qué datos exactos necesita antes de decidir", 35))),
    Item("A4", "A", "simpatia",
         "Un compañero nuevo, muy amable, te pide por chat que le compartas tu acceso VPN porque «su jefe aún no se lo da». ¿Qué haces?",
         (("Se lo comparto: parece buena persona y quiero ayudar", 100),
          ("Le digo que lo pida por el canal oficial de TI y aviso a mi jefe", 0),
          ("Se lo comparto solo por hoy y le pido que no lo cuente", 85),
          ("Le pido que me llame para conversarlo", 40))),
    Item("A5", "A", "prueba_social",
         "En el grupo de WhatsApp de tu barrio dicen: «Ya 50 vecinos ganaron con esta inversión, entren al enlace». ¿Qué haces?",
         (("Entro y deposito: si tantos lo hicieron, debe ser confiable", 100),
          ("Verifico en fuentes oficiales y no invierto si no está autorizado", 0),
          ("Pregunto a otro vecino si realmente ganó antes de decidir", 40),
          ("Entro solo a mirar sin dar datos", 65))),
    Item("A6", "A", "compromiso",
         "Soporte técnico te llama sin que lo pidieras: primero te pide «un favor pequeño» (qué sistema operativo usas) y luego que instales una herramienta remota. ¿Qué haces?",
         (("Instalo la herramienta: ya les ayudé con lo anterior y sería incoherente parar ahora", 100),
          ("Cuelgo y contacto a TI por el canal oficial", 0),
          ("Instalo la herramienta pero no les doy mis claves", 75),
          ("Les digo que me envíen un correo formal y sigo mientras tanto", 45))),
    # ---------- Forma B (diagnóstico final, paralela) ----------
    Item("B1", "B", "autoridad",
         "Recibes un correo del «director financiero» pidiéndote aprobar hoy un pago a un proveedor nuevo, a una cuenta que no conoces. ¿Qué haces?",
         (("Hago el pago: lo pide un director y no quiero retrasarlo", 100),
          ("Llamo al director a su número conocido y sigo el proceso formal de pagos", 0),
          ("Respondo el mismo correo pidiendo confirmación", 55),
          ("Hago el pago pero aviso después a contabilidad", 80))),
    Item("B2", "B", "urgencia",
         "Por WhatsApp te dicen: «Su paquete está retenido; pague 8.500 en la próxima hora o será devuelto». Traen un enlace de pago. ¿Qué haces?",
         (("Pago de inmediato: es poco dinero y corre el tiempo", 100),
          ("Reviso el estado del envío en el sitio oficial de la transportadora", 0),
          ("Abro el enlace para ver de qué se trata, sin pagar", 60),
          ("Pregunto por el mismo chat si es real", 40))),
    Item("B3", "B", "reciprocidad",
         "Te llega una encuesta «con premio garantizado». Al final piden tu cédula y número de cuenta para enviarte el regalo. ¿Qué haces?",
         (("Los doy: ya les dediqué tiempo y el premio es mío", 100),
          ("Cierro la encuesta: nadie debería pedir datos bancarios para un premio", 0),
          ("Doy la cédula pero no la cuenta", 70),
          ("Busco opiniones del sorteo antes de decidir", 30))),
    Item("B4", "B", "simpatia",
         "Alguien con quien llevas semanas conversando en redes y con quien tienes mucho en común te pide dinero prestado por una «emergencia». ¿Qué haces?",
         (("Le envío el dinero: ya somos amigos y confío en esa persona", 100),
          ("No envío dinero a alguien que no he verificado en persona o por videollamada", 0),
          ("Le envío una parte pequeña por si es verdad", 75),
          ("Le pido más detalles y una videollamada", 25))),
    Item("B5", "B", "prueba_social",
         "Una app dice «Más de 2 millones de usuarios ya la instalaron» y te pide permiso para leer tus SMS y ver tu extracto bancario. ¿Qué haces?",
         (("La instalo: tantos usuarios no pueden estar equivocados", 100),
          ("Reviso que sea de mi banco en la tienda oficial y no concedo permisos innecesarios", 0),
          ("La instalo pero niego algunos permisos", 55),
          ("Leo reseñas y, si son buenas, la instalo", 70))),
    Item("B6", "B", "compromiso",
         "Una «encuesta telefónica» empieza con preguntas inocuas (tu ciudad, tu gusto musical) y termina pidiendo tu nombre completo, dirección y cédula. ¿Qué haces?",
         (("Respondo todo: ya contesté lo anterior y no quiero dejarla a medias", 100),
          ("Corto la llamada en cuanto piden datos personales", 0),
          ("Doy el nombre pero no la cédula", 55),
          ("Pregunto para qué empresa es y decido según la respuesta", 40))),
    # ---------- Hábitos (solo en el diagnóstico inicial) ----------
    Item("H1", "H", "habito", "¿Reutilizas la misma contraseña en varios sitios?",
         (("Nunca: uso una distinta en cada sitio", 0), ("En algunos", 50), ("En casi todos", 100))),
    Item("H2", "H", "habito", "¿Usas verificación en dos pasos (MFA) en tus cuentas importantes?",
         (("En todas", 0), ("Solo en algunas", 50), ("No la uso", 100))),
    Item("H3", "H", "habito", "¿Usas Wi-Fi público para banca o trabajo?",
         (("Nunca", 0), ("Solo con VPN", 20), ("A veces, sin protección", 70), ("Con frecuencia", 100))),
    Item("H4", "H", "habito", "¿Qué tan expuesto está tu perfil en redes sociales?",
         (("Privado y sin datos sensibles", 0), ("Público con algunos datos", 60),
          ("Público con cargo, teléfono o ubicación en tiempo real", 100))),
)

def _shuffled(items):
    """Orden de opciones estable pero variado, para que la respuesta segura no caiga siempre en el mismo lugar."""
    out = []
    for it in items:
        opts = list(it.options)
        random.Random(it.id).shuffle(opts)
        out.append(Item(it.id, it.form, it.principle, it.text, tuple(opts)))
    return tuple(out)


ITEMS = _shuffled(ITEMS)
BY_ID = {i.id: i for i in ITEMS}
HABIT_ADVICE = {
    "H1": "Usa un gestor de contraseñas y una clave única por sitio.",
    "H2": "Activa MFA (preferible app autenticadora) en correo, banca y redes.",
    "H3": "Evita Wi-Fi público para banca o trabajo; usa datos móviles o VPN.",
    "H4": "Pon tu perfil en privado y retira cargo, teléfono y ubicación en tiempo real.",
}


def questions(phase: str) -> list[dict]:
    """Preguntas sin revelar el riesgo de cada opción."""
    forms = {"pre": ("A", "H"), "post": ("B",)}[phase]
    return [{"id": i.id, "principle_hidden": True, "text": i.text,
             "options": [o for o, _ in i.options], "kind": "habito" if i.form == "H" else "situacion"}
            for i in ITEMS if i.form in forms]


def score(phase: str, answers: dict[str, int]) -> dict:
    """answers: {item_id: índice de opción}. Devuelve perfil de riesgo 0-100."""
    forms = {"pre": ("A", "H"), "post": ("B",)}[phase]
    expected = [i for i in ITEMS if i.form in forms]
    missing = [i.id for i in expected if i.id not in answers]
    if missing:
        raise ValueError(f"Faltan respuestas: {', '.join(missing)}")
    by_principle: dict[str, float] = {}
    habits: dict[str, int] = {}
    for it in expected:
        idx = answers[it.id]
        if not isinstance(idx, int) or not 0 <= idx < len(it.options):
            raise ValueError(f"Respuesta inválida en {it.id}")
        risk = it.options[idx][1]
        if it.form == "H":
            habits[it.id] = risk
        else:
            by_principle[it.principle] = float(risk)
    overall = round(sum(by_principle[p] for p in PRINCIPLES) / len(PRINCIPLES), 1)
    out = {"phase": phase, "by_principle": by_principle, "overall": overall, "level": risk_level(overall)}
    if habits:
        out["habits"] = habits
        out["habits_score"] = round(sum(habits.values()) / len(habits), 1)
    return out
