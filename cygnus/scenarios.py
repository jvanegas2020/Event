"""Biblioteca de escenarios.

Cada escenario combina sector x canal x principio de Cialdini x etapa del ataque
(ver Tabla 2 y sección 8.4.3 del proyecto). Todas las entidades, enlaces y
teléfonos son FICTICIOS (dominios .example): nunca se suplantan marcas reales.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class Scenario:
    id: str
    title: str
    sector: str            # finanzas | salud | tecnologia | educacion
    channel: str           # correo | sms | whatsapp | llamada
    principle: str         # principio de Cialdini explotado
    stage: str             # etapa del ataque que ilustra
    level: int             # 1 (fácil) a 3 (difícil)
    entity: str            # entidad ficticia
    opening: str
    escalations: tuple[str, ...]
    red_flags: tuple[str, ...]
    safe_actions: tuple[str, ...]
    lesson: str
    technique: str = ""

    def public(self) -> dict:
        d = asdict(self)
        for k in ("opening", "escalations", "red_flags", "safe_actions", "lesson"):
            d.pop(k)
        return d


PRINCIPLES = ("autoridad", "urgencia", "reciprocidad", "simpatia", "prueba_social", "compromiso")

PRINCIPLE_LABELS = {
    "autoridad": "Autoridad",
    "urgencia": "Urgencia / escasez",
    "reciprocidad": "Reciprocidad",
    "simpatia": "Simpatía",
    "prueba_social": "Prueba social",
    "compromiso": "Compromiso y coherencia",
}

SCENARIOS: tuple[Scenario, ...] = (
    Scenario(
        id="fin-sms-bloqueo",
        title="Bloqueo de cuenta por SMS",
        sector="finanzas", channel="sms", principle="urgencia", stage="engano_pretexto",
        level=1, entity="Banco Andino Seguro", technique="smishing",
        opening=("[Banco Andino Seguro] ALERTA: detectamos un acceso inusual y su cuenta será "
                 "BLOQUEADA en 30 minutos. Verifique ahora: https://andino-verifica.example/acceso"),
        escalations=(
            "Su cuenta sigue en riesgo. Quedan 10 minutos. Confirme su usuario y clave en el enlace para evitar el bloqueo.",
            "Último aviso: si no responde, perderá el acceso y los fondos quedarán retenidos. Envíe el código que le llegará por SMS.",
            "Cuenta bloqueada. Para reactivarla responda con su número de cédula y el código de verificación.",
        ),
        red_flags=("Plazo extremadamente corto para presionar la decisión",
                   "Enlace con dominio que no es el oficial del banco",
                   "Pide clave o códigos OTP, que un banco legítimo nunca solicita"),
        safe_actions=("No abrir el enlace", "Llamar al número impreso en la tarjeta o usar la app oficial",
                      "Reportar el SMS al banco y borrarlo"),
        lesson="La urgencia busca que actúes antes de pensar. Frena y verifica por un canal que tú controlas.",
    ),
    Scenario(
        id="fin-llamada-fraude",
        title="Llamada del 'área antifraude'",
        sector="finanzas", channel="llamada", principle="autoridad", stage="engano_pretexto",
        level=2, entity="Banco Andino Seguro", technique="vishing",
        opening=("Buenas tardes, le habla Camilo Rojas del área antifraude de Banco Andino Seguro. "
                 "Estamos viendo dos compras sospechosas en su tarjeta por 3.200.000 pesos. "
                 "¿Usted las reconoce?"),
        escalations=(
            "Entiendo su preocupación. Para cancelar esas compras necesito validar que usted es el titular: confirme los últimos 8 dígitos de su tarjeta.",
            "Está bien, también le llegará un código por mensaje. Léamelo para reversar el cargo de inmediato; yo soy funcionario del banco.",
            "Si no me colabora ahora, el banco no se hace responsable de la pérdida. ¿Me da el código y su clave virtual?",
        ),
        red_flags=("Se presenta con un cargo para generar autoridad",
                   "Pide datos de la tarjeta y códigos OTP por teléfono",
                   "Te asusta con una pérdida para que cooperes"),
        safe_actions=("Colgar y llamar tú mismo al número oficial", "No leer nunca códigos de un SMS a nadie",
                      "Avisar al banco del intento de fraude"),
        lesson="Un funcionario real nunca te pide códigos. Cuelga y devuelve la llamada al número oficial.",
    ),
    Scenario(
        id="sal-correo-resultados",
        title="Resultados de exámenes por correo",
        sector="salud", channel="correo", principle="autoridad", stage="reconocimiento",
        level=1, entity="Clínica Salud Norte", technique="phishing",
        opening=("Asunto: Resultados de laboratorio disponibles\n\nEstimado paciente, la Clínica Salud Norte "
                 "le informa que sus resultados están listos. Descárguelos con su cédula y fecha de nacimiento: "
                 "https://saludnorte-resultados.example/paciente"),
        escalations=(
            "Recordatorio: sus resultados vencen hoy. Ingrese su número de documento, EPS y contraseña del portal para verlos.",
            "Por políticas de privacidad debemos validar su identidad. Responda este correo con foto de su cédula por ambos lados.",
            "No hemos recibido su validación. Adjunte su cédula o sus resultados se eliminarán.",
        ),
        red_flags=("Correo genérico que no menciona examen ni fecha concretos",
                   "Dominio que no corresponde a la clínica",
                   "Pide documento de identidad por correo"),
        safe_actions=("No abrir el enlace", "Consultar resultados desde el portal oficial que ya conoces",
                      "Llamar a la clínica para confirmar"),
        lesson="Los datos de salud son muy valiosos. Confirma siempre con la entidad por un canal conocido.",
    ),
    Scenario(
        id="tec-whatsapp-jefe",
        title="El 'gerente' pide un favor urgente",
        sector="tecnologia", channel="whatsapp", principle="simpatia", stage="engano_pretexto",
        level=2, entity="Nubetek S.A.S.", technique="pretexting (suplantación de jefe)",
        opening=("Hola, soy Laura, la gerente general. Cambié de número, guárdalo. Estoy en una reunión y no "
                 "puedo hablar. ¿Me puedes ayudar con algo rápido y confidencial?"),
        escalations=(
            "Gracias, eres de mi total confianza. Necesito que compres 5 tarjetas de regalo de 200.000 y me envíes los códigos por aquí. Te lo reembolso hoy.",
            "Sé que es raro, pero es una sorpresa para un cliente importante. No le comentes a nadie, por favor. Mándame los códigos ya.",
            "Contaba contigo y me estás quedando mal. Haz la transferencia a esta cuenta 0123456789 y luego te explico.",
        ),
        red_flags=("Número nuevo que pide ser guardado",
                   "Petición de secreto y de saltarse el proceso normal de pagos",
                   "Usa halagos y la relación personal para presionar"),
        safe_actions=("Llamar a la gerente por su número conocido", "No comprar ni transferir sin autorización formal",
                      "Reportar al área de seguridad"),
        lesson="La simpatía y la confianza se usan como arma. Todo pago fuera del proceso se verifica por voz.",
    ),
    Scenario(
        id="edu-correo-beca",
        title="Beca que 'solo hoy' puedes reclamar",
        sector="educacion", channel="correo", principle="reciprocidad", stage="reconocimiento",
        level=2, entity="Universidad del Caribe Digital", technique="baiting",
        opening=("Asunto: ¡Felicitaciones! Beca del 70% preaprobada\n\nHemos revisado tu perfil y te regalamos una beca "
                 "como reconocimiento a tu esfuerzo. Solo falta que completes tus datos aquí: "
                 "https://ucd-becas.example/reclamar"),
        escalations=(
            "Ya hicimos un favor especial por ti; ahora ayúdanos completando tu cédula, dirección y datos bancarios para el desembolso.",
            "Quedan solo 3 cupos. Para asegurarlo paga una tarifa de legalización de 80.000 pesos a esta cuenta.",
            "Tu cupo será entregado a otro aspirante si no confirmas ahora con tus datos y el pago.",
        ),
        red_flags=("Premio que no solicitaste", "Te hace sentir en deuda para que devuelvas el favor",
                   "Cobra una tarifa por entregar un beneficio"),
        safe_actions=("Verificar la beca en el sitio oficial de la universidad", "No pagar por 'legalización'",
                      "Reportar el correo"),
        lesson="Si te regalan algo que no pediste y luego te piden datos o dinero, es una trampa de reciprocidad.",
    ),
    Scenario(
        id="tec-llamada-soporte",
        title="Soporte técnico que 've virus' en tu equipo",
        sector="tecnologia", channel="llamada", principle="compromiso", stage="explotacion",
        level=3, entity="Nubetek S.A.S.", technique="quid pro quo",
        opening=("Hola, le habla Andrés del soporte técnico de Nubetek. Su equipo está enviando alertas de virus a "
                 "nuestros servidores. Solo le pido un favor pequeño: ¿puede decirme qué sistema operativo usa?"),
        escalations=(
            "Perfecto, gracias. Ya que me ayudó con eso, ahora abra la herramienta de asistencia remota en https://nubetek-soporte.example/ayuda y dígame el código que aparece.",
            "Ya estamos casi listos; no se detenga ahora. Necesito que instale el parche y me confirme su usuario y contraseña de red.",
            "Si corta ahora el proceso, el virus se propagará por toda la empresa. Dígame la contraseña para terminar.",
        ),
        red_flags=("Empieza con un favor mínimo para ir escalando (compromiso y coherencia)",
                   "Soporte que te llama sin que lo hayas pedido",
                   "Pide acceso remoto y contraseñas"),
        safe_actions=("Colgar y contactar a TI por el canal oficial", "No instalar nada ni dar acceso remoto",
                      "Reportar el intento a seguridad"),
        lesson="Cada 'sí' pequeño te empuja al siguiente. Puedes parar en cualquier momento.",
    ),
)

BY_ID = {s.id: s for s in SCENARIOS}
