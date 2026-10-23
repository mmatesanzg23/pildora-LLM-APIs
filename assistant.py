"""Cliente del LLM de Groq y bucle de function calling.

Este módulo no habla con Streamlit: recibe la lista de mensajes del chat y
devuelve la respuesta final del asistente como texto.
"""

import json

from groq import Groq

from weather import TOOLS, ejecutar_herramienta

MODELOS = {
    "GPT-OSS 120B (recomendado)": "openai/gpt-oss-120b",
    "GPT-OSS 20B (más rápido)": "openai/gpt-oss-20b",
}

MAX_RONDAS = 5  # llamadas máximas a Groq por pregunta (geocodificar, prever, responder)

SYSTEM_PROMPT = """\
Eres "MeteoAsistente", un asistente especializado EXCLUSIVAMENTE en meteorología.

REGLAS OBLIGATORIAS:
1. Solo tratas temas de meteorología: estado del tiempo, previsión, temperatura,
   lluvia, nieve, viento, humedad, oleajes, climas y fenómenos atmosféricos.
2. Para responder datos reales de un lugar usas las herramientas disponibles:
   primero "buscar_ciudad" si aún no tienes coordenadas y después "get_weather".
   NUNCA inventes temperaturas ni previsiones: si no tienes datos de la
   herramienta, dilo claramente.
3. Ante cualquier pregunta que NO sea de meteorología (deportes, política,
   historia, matemáticas, programación, salud, ocio, curiosidades...), respondes
   EXACTAMENTE esta frase y nada más:
   "No tengo acceso a ese tipo de información."
4. Solo se permite responder a un saludo breve presentándote en una línea como
   asistente de meteorología y ofreciéndote a consultar el tiempo. Cualquier
   otra cosa fuera de tema aplica la regla 3.
5. Respondes siempre en español, de forma breve, clara y con los datos a los que
   tienes acceso. Indica la unidad (°C, km/h, mm...).
"""


def crear_cliente(api_key):
    """Crea el cliente de Groq a partir de la API key."""
    return Groq(api_key=api_key)


def responder(cliente, modelo, mensajes):
    """Devuelve la respuesta final del asistente para una pregunta del usuario.

    Ejecuta el bucle de function calling:
      Groq decide -> ¿pide herramienta? -> la ejecutamos y le devolvemos el
      resultado -> Groq responde con texto final (o vuelve a pedir otra herramienta).
    """
    historial = [{"role": "system", "content": SYSTEM_PROMPT}, *mensajes]

    for _ in range(MAX_RONDAS):
        completacion = cliente.chat.completions.create(
            model=modelo,
            messages=historial,
            tools=TOOLS,
            temperature=0.3,
            max_tokens=1024,
        )
        mensaje = completacion.choices[0].message

        # No pidió herramientas: ya tiene la respuesta final
        if not mensaje.tool_calls:
            if mensaje.content:
                return mensaje.content
            return "No he podido generar una respuesta. ¿Puedes reformular la pregunta?"

        # Registramos su petición y ejecutamos cada herramienta pedida
        historial.append(
            {
                "role": "assistant",
                "content": mensaje.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        },
                    }
                    for tc in mensaje.tool_calls
                ],
            }
        )
        for tc in mensaje.tool_calls:
            try:
                argumentos = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                argumentos = {}
            resultado = ejecutar_herramienta(tc.function.name, argumentos)
            historial.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "name": tc.function.name,
                    "content": resultado,
                }
            )

    return (
        "He necesitado demasiados pasos para responder y he cortado la consulta. "
        "¿Puedes reformularla?"
    )
