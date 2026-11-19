# Cygnus 2.0 · Entrenador de resistencia a la ingeniería social

MVP del agente **Cygnus** del proyecto de grado *"Desarrollo de un marco metodológico integral para la protección de la información personal frente a técnicas de ingeniería social"* (Esp. en Seguridad Informática, Corporación Universitaria Americana).

Es una simulación **educativa y defensiva**: el atacante simulado solo existe dentro del chat de entrenamiento, con entidades, enlaces (`.example`) y teléfonos **ficticios**.

## Qué hace el MVP
- **6 escenarios** (finanzas, salud, tecnología, educación; SMS, correo, WhatsApp, llamada) que combinan sector × canal × principio de Cialdini × etapa del ataque.
- **Conversación multi-turno** con presión creciente del atacante.
- **Evaluador determinista** (auditable, sin LLM): detecta si entregaste datos, ejecutaste la acción, te negaste, verificaste o reportaste.
- **Perfil adaptativo**: susceptibilidad por principio de Cialdini y nivel 1-3; el siguiente escenario apunta a tu punto más débil.
- **Índice de resistencia (IRIS)** y **reporte** con señales de alerta, acciones recomendadas y controles ISO/IEC 27001:2022 (A.6.3, A.6.8, A.8.5, A.5.34).
- **Privacidad por diseño (Ley 1581/2012)**: consentimiento previo, id aleatorio, se guardan resultados y **nunca el texto de los mensajes**; borrado de datos con un clic.
- **LLM opcional**: con `ANTHROPIC_API_KEY` el atacante redacta sus mensajes con un modelo (con reglas estrictas y enlaces solo `.example`); sin clave usa guiones. Variable `CYGNUS_MODEL` para elegir modelo.

## Ejecutar
```bash
pip install -r requirements.txt
python -m uvicorn cygnus.api:app --reload      # http://localhost:8000
python -m pytest -q                             # 23 pruebas
```

## Estructura
```
cygnus/scenarios.py   biblioteca de escenarios (datos)
cygnus/evaluator.py   clasificador de respuestas (reglas)
cygnus/profile.py     perfil adaptativo + IRIS (SQLite)
cygnus/providers.py   atacante: guion o LLM
cygnus/engine.py      sesiones, puntaje y reporte
cygnus/api.py         API FastAPI + frontend en cygnus/static
tests/                pruebas
```

## Próximas entregas
1. **Guardián**: analizar un mensaje sospechoso real y explicarlo (principio, etapa, qué hacer).
2. **Medidor**: tablero por sector/área y módulo de experimento antes/después con grupo de control.
3. Canal WhatsApp, más escenarios y evaluación semántica de respuestas.
