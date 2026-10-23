"""Interfaz de chat del MeteoAsistente (Streamlit).

Ejecutar con:  streamlit run app.py
"""

import os

import streamlit as st

from assistant import MODELOS, crear_cliente, responder

st.set_page_config(
    page_title="MeteoAsistente",
    page_icon="⛅",
    layout="centered",
)


def obtener_api_key():
    """Lee la API key de Groq: primero de secrets.toml, si no de la variable de entorno."""
    try:
        clave = st.secrets.get("GROQ_API_KEY")
        if clave:
            return clave
    except Exception:
        # No existe .streamlit/secrets.toml o no es válido
        pass
    return os.environ.get("GROQ_API_KEY")


api_key = obtener_api_key()

if not api_key or api_key.strip() in ("", "gsk_..."):
    st.error(
        "Falta la **API key de Groq**.\n\n"
        "1. Consíguela gratis en https://console.groq.com/keys\n"
        "2. Copia `.streamlit/secrets.toml.example` como "
        "`.streamlit/secrets.toml` y pega la clave ahí.\n\n"
        "También puedes usar la variable de entorno `GROQ_API_KEY`."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Barra lateral
# ---------------------------------------------------------------------------
with st.sidebar:
    st.title("⛅ MeteoAsistente")
    st.caption("Asistente de LLM conectado a la API de Groq + Open-Meteo")
    modelo_legible = st.selectbox("Modelo de Groq", list(MODELOS))
    modelo = MODELOS[modelo_legible]
    st.divider()
    st.markdown(
        """
**¿Cómo funciona?**

1. Escribes una pregunta en el chat.
2. El LLM de **Groq** decide si necesita datos reales.
3. Si es meteorológico, llama a la herramienta `get_weather`,
   que consulta la API gratuita **Open-Meteo**.
4. Con esos datos redacta la respuesta.

Si preguntas otra cosa, responderá:
> No tengo acceso a ese tipo de información.
"""
    )
    st.caption("Datos meteorológicos: open-meteo.com (uso no comercial)")

# ---------------------------------------------------------------------------
# Historial del chat
# ---------------------------------------------------------------------------
if "mensajes" not in st.session_state:
    st.session_state.mensajes = []

for mensaje in st.session_state.mensajes:
    with st.chat_message(mensaje["role"]):
        st.markdown(mensaje["content"])

pregunta = st.chat_input(
    "Pregunta por la previsión del tiempo, ej.: ¿Qué tiempo hace en Madrid?"
)

if pregunta:
    st.session_state.mensajes.append({"role": "user", "content": pregunta})
    with st.chat_message("user"):
        st.markdown(pregunta)

    with st.chat_message("assistant"):
        with st.spinner("Consultando el tiempo..."):
            try:
                cliente = crear_cliente(api_key)
                respuesta = responder(cliente, modelo, st.session_state.mensajes)
            except Exception as error:
                if "Invalid API Key" in str(error) or "401" in str(error):
                    respuesta = (
                        "La API key de Groq no es válida. Revísala en "
                        "`.streamlit/secrets.toml`."
                    )
                else:
                    respuesta = f"Se produjo un error al contactar con Groq: {error}"
        st.markdown(respuesta)

    st.session_state.mensajes.append({"role": "assistant", "content": respuesta})
