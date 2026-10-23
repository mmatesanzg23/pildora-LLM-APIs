# 🔗 Relación entre MeteoAsistente y n8n

Documento de apoyo para la exposición: explica **en qué se parece** este proyecto
a [n8n](https://n8n.io), **en qué se diferencia** y **qué caminos existen** para
conectar ambos mundos.

---

## 1. La tesis en una frase

> **MeteoAsistente es un n8n escrito a mano.**

n8n es un motor de orquestación visual: en lugar de escribir un bucle `for` que
llame a las APIs, tú arrastras **nodos** a un lienzo y los cableas. Pero el
concepto que hay por debajo es exactamente el mismo que explica este proyecto:

> **El LLM decide; el motor ejecuta la petición HTTP.**

En tu proyecto, el motor es el bucle de *function calling* de `assistant.py`.
En n8n, el motor es el runtime de workflows. Cambia el entorno, no la
arquitectura.

---

## 2. Tabla de equivalencias

Cada pieza de tu proyecto tiene una contraparte casi literal en n8n:

| Tu proyecto (código) | En n8n |
|---|---|
| `app.py` — interfaz de chat con `st.chat_input` | **Chat Trigger** (n8n trae su propio chat) o **Webhook** |
| `assistant.py:56` — bucle de *function calling* | **AI Agent** node (con memoria opcional) |
| `assistant.py:20` — `SYSTEM_PROMPT` | campo *Instructions* del AI Agent |
| `weather.py:60` — esquema `TOOLS` (JSON de funciones) | Tools conectadas al agente (nodos usados como herramientas) |
| `weather.py:108` — `buscar_ciudad()` | nodo **HTTP Request** → `geocoding-api.open-meteo.com/v1/search` |
| `weather.py:138` — `get_weather()` | nodo **HTTP Request** → `api.open-meteo.com/v1/forecast` |
| `weather.py:20` — diccionario `WMO_CODES` | **Code node** que traduce el código WMO a texto |
| `assistant.py:18` — `MAX_RONDAS = 5` | límite de iteraciones del agente / nodos **Loop** |
| `.streamlit/secrets.toml` | **Credentials** de n8n (Groq API Key) |
| `temperature`, `max_tokens` (`assistant.py:61-62`) | opciones del nodo *Chat Model* |

**Detalle útil:** Groq es **nodo nativo** en n8n (`Groq Chat Model` + credencial
`Groq`), así que el mismo modelo que usas (`openai/gpt-oss-120b`) se configura
en el dropdown del nodo, sin código.

---

## 3. El mismo asistente en n8n, paso a paso

```
┌────────────┐   ┌───────────────────────┐   ┌──────────────────┐
│ Chat       │──▶│ AI Agent              │──▶│ Groq Chat Model  │
│ Trigger    │   │ (Instructions =       │   │ (openai/gpt-oss- │
│ (chat de   │   │  SYSTEM_PROMPT)       │   │  120b)           │
│  n8n)      │   └───────────┬───────────┘   └──────────────────┘
└────────────┘               │ tool call
                             ▼
                ┌──────────────────────────────┐
                │ HTTP Request: /v1/search      │  ← buscar_ciudad
                │ HTTP Request: /v1/forecast     │  ← get_weather
                │ Code: traducir código WMO     │  ← WMO_CODES
                └──────────────────────────────┘
```

Traducción de tu código a nodos:

| Paso | En Python (tu proyecto) | En n8n |
|---|---|---|
| 1 | El usuario escribe en el chat | Nodo **Chat Trigger** (o Webhook + nodo **Respond**) |
| 2 | `responder()` añade el `SYSTEM_PROMPT` al historial | Campo *Instructions* del **AI Agent** |
| 3 | `cliente.chat.completions.create(..., tools=TOOLS)` | Sub-nodo **Groq Chat Model** conectado al Agent |
| 4 | `ejecutar_herramienta()` despacha a la función pedida | El Agent invoca el **nodo tool** que corresponda |
| 5 | `requests.get(...)` a Open-Meteo | Nodos **HTTP Request** (con *Parameters* en URL y *Timeout* 10 s) |
| 6 | `_descripcion_codigo()` traduce el WMO | **Code node** con el mismo diccionario |
| 7 | `historial.append({"role": "tool", ...})` | El runtime reinyecta el resultado de la tool al Agent |
| 8 | `st.markdown(respuesta)` | El Chat Trigger devuelve la respuesta al chat |

**Estructura del workflow (5 nodos):**

1. `Chat Trigger` → modo *Response: When Last Node Finishes* (o *Streaming response*).
2. `AI Agent` → *Instructions* = el `SYSTEM_PROMPT` de `assistant.py`.
3. `Groq Chat Model` → sub-nodo del Agent, credencial Groq, modelo `openai/gpt-oss-120b`.
4. `HTTP Request` (geocoding) + `HTTP Request` (forecast) → conectados como **tools** del Agent.
5. `Code` → normaliza la respuesta de la API (aquí va `WMO_CODES`).

> Nota práctica: el nodo *Code* de n8n es JavaScript, así que el diccionario
> `WMO_CODES` se traduce tal cual (las claves numéricas se escriben `"0"`,
> `"61"`, etc. porque en JS los objetos indexan por string).

---

## 4. Qué coincide y qué aporta cada uno

### Coinciden (mismo modelo mental)

- **Function calling**: el LLM pide una herramienta, el runtime la ejecuta y le
  devuelve el resultado. Exactamente lo de la *Diapositiva 5*.
- **System prompt** como límite de comportamiento (regla 3: *"No tengo acceso a
  ese tipo de información."*).
- **Credenciales fuera del código**: `secrets.toml` ↔ Credentials de n8n.
- **Integrar APIs sin tocar la API**: ambos *consumen* servicios de terceros.

### n8n aporta (lo que tú no tienes)

| Capacidad | Detalle |
|---|---|
| **Triggers** | Programación (cron), webhook, email, Slack, base de datos… cada mensaje tuyo era "a mano"; n8n dispara solo |
| **Editor visual** | El flujo se ve y se modifica sin escribir código |
| **Reintentos y errores** | Backoff, *Retry On Fail*, workflows de error |
| **Credenciales centralizadas** | Una key de Groq reutilizable en todos los workflows |
| **Memoria del agente** | Conversaciones persistentes sin `st.session_state` |
| **Human-in-the-loop** | Pausar el flujo y pedir confirmación humana |
| **Sub-workflows** | Reutilizar partes de tus flujos |
| **MCP** | Cliente y servidor MCP nativos |
| **Despliegue** | Cloud gestionado o self-hosted con Docker |

### Tu proyecto aporta (lo que n8n no te da)

- **Control fino del código**: controlas exactamente el *timeout*, el `raise_for_status`, el formato del JSON y los mensajes de error en español (`weather.py:118-122`).
- **UI a medida**: el `st.selectbox` de modelo, la barra lateral explicativa, la persists del historial.
- **El filtro anti-alucinaciones** está escrito, testeado y es auditable; en n8n es un *prompt* que alguien puede reescribir sin que nadie lo note.
- **Coste cero y sin dependencias** (n8n = Node + Docker o instancia cloud).
- **Valor didáctico**: aquí no hay nodos que escondean la magia. Sabes exactamente qué pasa en cada línea, y eso es justo lo que se explica en la charla.

---

## 5. Tres caminos para conectar ambos mundos

### Camino A — Recrear el asistente en n8n (sin Python)

**Qué:** el workflow de la sección 3, tal cual.

**Cuándo tiene sentido:** para una demo de *integración low-code*, para encadenar el
chat con otros servicios (mandar el parte a Slack, guardarlo en una BD, avisar
si llueve) o para personas del equipo que no programan.

**Qué se pierde:** el control fino del `Code` node (JavaScript), el `WMO_CODES`
limpio, el manejo de errores a medida y el hecho de que sea open-source para
leer. **Qué se gana:** disparadores, memoria, reintentos y reutilización.

**Esfuerzo:** ~30 minutos para el flujo básico.

### Camino B — n8n orquesta tu código (o al revés)

**Dirección 1 — tu API es el "tool":**

1. Expones `weather.py` como servicio: `FastAPI` con `GET /buscar_ciudad` y
   `GET /weather`, más `GET /openapi.json` (que además te da *agent-readiness*
   documentada, como ya hacías con GymFlow).
2. En n8n: un nodo **HTTP Request** a `http://localhost:8000/weather` conectado
   como tool del Agent.

**Dirección 2 — tu asistente consume un workflow de n8n:**

1. En n8n publicas un workflow como **Workflow Tool** (lo invoca otro flujo).
2. `assistant.py` lo llama con `requests.post(...)` como si fuera una tool más
   del array `TOOLS`.

**Cuándo tiene sentido:** cuando la lógica meteorológica es tuya y la
orquestación es genérica; o al revés.

### Camino C — Tus herramientas como MCP

La idea más elegante de las tres:

1. Tu array `TOOLS` (`weather.py:60`) ya es, casi literalmente, un **manifiesto
   MCP**: nombre, descripción y esquema de parámetros en JSON. Solo habría que
   envolver las dos funciones con FastMCP y añadir `lugar` al esquema.
2. Sirves ese servidor MCP y lo conectas con el nodo **MCP Client Tool** de n8n:
   el Agent de n8n gana `buscar_ciudad` y `get_weather` sin tocar el workflow.
3. Al revés: expones un workflow tuyo con **MCP Server Trigger** y lo consumes
   desde `assistant.py` (o desde Claude Desktop, Cursor, opencode…).

**Cuándo tiene sentido:** cuando quieras que *cualquier* cliente MCP (no solo
n8n) pueda usar tus herramientas. Es el mismo diseño, con un estándar encima.

---

## 6. Ángulo para la charla

**Frase gancho:**

> "n8n es la versión no-code de lo que escribimos en Python: el mismo LLM decide
> qué herramienta usar; lo único que cambia es quién hace la petición HTTP —
> el motor de n8n o nuestro código."

**Desarrollo (30 segundos):**

> "Nuestro bucle de *function calling* es, en esencia, un motor de workflows
> escrito a mano. En n8n ese bucle es un nodo: el AI Agent con el Groq Chat
> Model. Nuestras dos funciones Python serían dos HTTP Request. Y nuestro
> `SYSTEM_PROMPT` es el campo de instrucciones del agente. La diferencia no es
> de arquitectura, es de entorno: en n8n se arrastra y se cablea; nosotros lo
> escribimos para entender qué hay por debajo."

**Preguntas que te pueden hacer:**

| Pregunta | Respuesta corta |
|---|---|
| "¿Es lo mismo n8n que tu proyecto?" | El mismo patrón (LLM + tools + APIs), distinto entorno: visual y genérico n8n; código y específico nuestro |
| "¿Cuándo uso n8n y cuándo Python?" | n8n cuando el flujo es de integración y quieres dispararlo/reutilizarlo sin código; Python cuando necesitas control fino del comportamiento o lógica propia |
| "¿Se puede usar n8n sin saber programar?" | Sí, ese es su objetivo; el coste es que cuando algo falla, sin código, el diagnóstico es más opaco |
| "¿MCP y n8n son lo mismo?" | No: MCP es un estándar para exponer herramientas a modelos; n8n es un motor de workflows que, además, ya habla MCP |
| "¿Por qué no rehaces la píldora en n8n?" | Precisamente porque aquí se ve el mecanismo: si lo montamos con nodos, nadie ve el `tool_call` por dentro |

---

## 7. Referencias

- n8n · Groq Chat Model: <https://docs.n8n.io/integrations/builtin/cluster-nodes/sub-nodes/n8n-nodes-langchain.lmchatgroq/>
- n8n · Chat Trigger: <https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.chattrigger>
- n8n · MCP Server Trigger: <https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-langchain.mcptrigger>
- n8n · credencial Groq: <https://docs.n8n.io/integrations/builtin/credentials/groq>
- Groq · compatibilidad con la API de OpenAI (`base_url`): <https://console.groq.com/docs/openai>
- Documentos del propio proyecto: [README.md](README.md) · [GUIA.md](GUIA.md) · [DIAPOSITIVAS.md](DIAPOSITIVAS.md)
