# MeteoAsistente: Groq + Streamlit + código

## Diapositiva 1 — Portada

**MeteoAsistente: un chat con IA que consulta el tiempo real**

- Asistente de meteorología con LLM (Groq) + API real (Open-Meteo)
- Interfaz web con Streamlit
- Ejemplo de *function calling*: el LLM decide, el código ejecuta

---

## Diapositiva 2 — Los 3 elementos y para qué sirve cada uno

**Streamlit — la cara**
- Convierte código Python en una interfaz web (chat) sin tocar HTML/CSS
- Muestra el historial, el input del chat y el selector de modelo
- Al escribir una pregunta, lanza el resto del proceso

**Groq — el cerebro**
- API que ejecuta modelos de lenguaje (LLM) a gran velocidad
- Recibe la pregunta + instrucciones (system prompt) + herramientas
- Decide: responder directamente o pedir datos reales con una *tool call*

**Open-Meteo — los datos**
- API meteorológica real y gratuita (sin API key)
- Geocodificación: nombre de ciudad → coordenadas
- Previsión: condiciones actuales + 7 días para esas coordenadas

---

## Diapositiva 3 — Cómo se conectan

**Arquitectura de la aplicación**

1. **Usuario** escribe en el chat → `app.py` (Streamlit)
2. `app.py` envía historial + system prompt + herramientas → **Groq API**
3. **Groq** responde con una *tool call* (p. ej. `buscar_ciudad("Madrid")`)
4. **Python** (`weather.py`) ejecuta la herramienta → llama a **Open-Meteo**
5. El JSON con los datos reales vuelve como mensaje del chat → **Groq**
6. **Groq** redacta la respuesta final en español → el usuario la ve en Streamlit

> El LLM no navega por la web: decide qué función llamar y **el código Python hace las peticiones HTTP reales**

---

## Diapositiva 4 — El código: 3 archivos, 3 responsabilidades

**`app.py` — la interfaz (Streamlit)**
- Lee la API key, pinta el chat, gestiona el botón de enviar

**`assistant.py` — el cerebro (Groq)**
- System prompt: "solo meteorología" + límites del asistente
- El bucle de *function calling*: preguntar → ejecutar herramientas → responder

**`weather.py` — las herramientas (Open-Meteo)**
- `buscar_ciudad(nombre)` → coordenadas (geocodificación)
- `get_weather(lat, lon)` → datos actuales + previsión de 7 días
- `TOOLS`: esquema JSON que se le envía a Groq para que sepa qué funciones existen

---

## Diapositiva 5 — Function calling, paso a paso

**Ejemplo: "¿Qué tiempo hace en Madrid?"**

1. Groq recibe la pregunta y ve las herramientas disponibles
2. Groq no sabe el tiempo → devuelve `tool_call: buscar_ciudad("Madrid")`
3. Nuestro código llama a Open-Meteo → devuelve `{latitude: 40.41, longitude: -3.70, ...}`
4. Groq recibe eso y pide: `tool_call: get_weather(40.41, -3.70, "Madrid")`
5. Nuestro código llama a Open-Meteo otra vez → JSON con temperatura, humedad, 7 días...
6. Con esos datos, Groq redacta la respuesta final: "En Madrid hay 14 °C, nublado..."

**Regla clave:** Groq **nunca inventa temperaturas**: o usa datos de la herramienta o lo dice

---

## Diapositiva 6 — Conexión en la práctica

**Configuración (una sola vez)**

1. Cuenta gratis en `console.groq.com` → crear API key (`gsk_...`)
2. La clave se guarda en `.streamlit/secrets.toml` (en `.gitignore`: nunca se sube a GitHub)
3. `pip install streamlit groq requests`
4. Arranque: `streamlit run app.py` → se abre el chat en el navegador

**Barra lateral**
- Selector de modelo (GPT-OSS 120B / 20B)
- Nota: Groq retira modelos antiguos de vez en cuando (por eso los IDs se actualizan)

---

## Diapositiva 7 — La demo (2 minutos)

**Qué voy a mostrar**

1. **Pregunta con datos reales**: "¿Qué tiempo hace en Madrid?" → respuesta con temperatura y previsión de hoy y 7 días (datos actuales de Open-Meteo)
2. **Ciudad distinta**: "¿Lloverá esta semana en Barcelona?" → geocodificación + previsión real
3. **Filtro de tema**: "¿Quién ganó el partido de ayer?" → "No tengo acceso a ese tipo de información" (el system prompt lo impide)
4. **En vivo**: cambiar la pregunta y ver cómo el LLM elige las herramientas en cada caso

**Idea a destacar**: el LLM no tiene internet ni memoria del tiempo; los datos salen de Open-Meteo en el momento porque nuestro código los pide
