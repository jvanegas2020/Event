# Cygnus 2.0 · Entrenador de resistencia a la ingeniería social

MVP del agente **Cygnus** del proyecto de grado *"Desarrollo de un marco metodológico integral para la protección de la información personal frente a técnicas de ingeniería social"* (Esp. en Seguridad Informática, Corporación Universitaria Americana).

Es una simulación **educativa y defensiva**: el atacante simulado solo existe dentro del chat de entrenamiento, con entidades, enlaces (`.example`) y teléfonos **ficticios**.

## Flujo del programa
1. **Diagnóstico inicial** (10 preguntas): test de juicio situacional con una situación por principio de Cialdini + 4 hábitos (contraseñas, MFA, Wi-Fi público, redes sociales). Resultado: riesgo 0-100 por principio y global (bajo / medio / alto / crítico).
2. **Plan de entrenamiento dinámico**: el nivel de riesgo define cuántas simulaciones (3 a 6); los principios más vulnerables van primero; riesgo alto = escenario básico para construir el hábito, riesgo bajo = escenario exigente.
3. **Simulaciones con mapa de calor**: cada respuesta se colorea en vivo (verde = correcta, rojo = incorrecta) y una matriz principio × momento muestra tu riesgo a lo largo del programa.
4. **Diagnóstico final**: forma paralela del test (situaciones distintas, mismos principios) para que el antes/después no mida memoria.
5. **Informe final**: perfil de riesgo antes vs después por principio, narrativa, simulaciones, hábitos por mejorar y controles ISO/IEC 27001:2022.

## Otras características
- **9 escenarios** (finanzas, salud, tecnología, educación; SMS, correo, WhatsApp, llamada) con entidades y enlaces ficticios (`.example`).
- **Evaluador determinista** (auditable, sin LLM) de las respuestas en cada simulación.
- **Privacidad por diseño (Ley 1581/2012)**: consentimiento previo, id aleatorio, se guardan resultados y **nunca el texto de los mensajes**; borrado de datos con un clic.
- **LLM opcional**: con `ANTHROPIC_API_KEY` el atacante redacta sus mensajes con un modelo (reglas estrictas, enlaces solo `.example`); sin clave usa guiones. `CYGNUS_MODEL` elige el modelo.

## Ejecutar
```bash
pip install -r requirements.txt
python -m uvicorn cygnus.api:app --reload      # http://localhost:8000
python -m pytest -q                             # 30 pruebas
```

## Estructura
```
cygnus/scenarios.py   biblioteca de escenarios (datos)
cygnus/evaluator.py   clasificador de respuestas (reglas)
cygnus/diagnostic.py  test de diagnóstico (formas A/B paralelas) y niveles de riesgo
cygnus/program.py     plan dinámico, mapa de calor e informe antes/después
cygnus/profile.py     almacenamiento SQLite y perfil adaptativo
cygnus/providers.py   atacante: guion o LLM
cygnus/engine.py      sesiones, puntaje y reporte
cygnus/api.py         API FastAPI + frontend en cygnus/static
tests/                pruebas
```

## Próximas entregas
1. **Guardián**: analizar un mensaje sospechoso real y explicarlo (principio, etapa, qué hacer).
2. **Medidor**: tablero por sector/área y experimento con grupo de control (hoy el antes/después es individual).
3. Canal WhatsApp, más escenarios y evaluación semántica de respuestas.
