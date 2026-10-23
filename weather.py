"""Herramientas meteorológicas basadas en la API gratuita Open-Meteo.

Este módulo contiene:
  - TOOLS: el esquema JSON que se le envía al LLM de Groq para que sepa
    qué funciones puede llamar (function calling).
  - buscar_ciudad(): geocodificación (nombre -> coordenadas).
  - get_weather(): previsión del tiempo (coordenadas -> datos actuales + 7 días).

Open-Meteo no necesita API key: https://open-meteo.com/en/docs
"""

import json

import requests

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# Códigos WMO (World Meteorological Organization) -> descripción en español
WMO_CODES = {
    0: "Despejado",
    1: "Mayormente despejado",
    2: "Parcialmente nublado",
    3: "Nublado",
    45: "Niebla",
    48: "Niebla con escarcha",
    51: "Llovizna ligera",
    53: "Llovizna moderada",
    55: "Llovizna intensa",
    56: "Llovizna helada",
    57: "Llovizna helada intensa",
    61: "Lluvia ligera",
    63: "Lluvia moderada",
    65: "Lluvia intensa",
    66: "Lluvia helada",
    67: "Lluvia helada intensa",
    71: "Nieve ligera",
    73: "Nieve moderada",
    75: "Nieve intensa",
    77: "Granos de nieve",
    80: "Chubascos ligeros",
    81: "Chubascos moderados",
    82: "Chubascos violentos",
    85: "Chubascos de nieve ligeros",
    86: "Chubascos de nieve intensos",
    95: "Tormenta eléctrica",
    96: "Tormenta eléctrica con granizo",
    99: "Tormenta eléctrica con granizo intensa",
}


def _descripcion_codigo(codigo):
    return WMO_CODES.get(codigo, f"Código meteorológico {codigo}")


# ---------------------------------------------------------------------------
# Esquema de herramientas: esto es lo que le "contamos" al LLM para que sepa
# qué funciones puede invocar y con qué parámetros.
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "buscar_ciudad",
            "description": (
                "Convierte el nombre de una ciudad o lugar en coordenadas "
                "(latitud y longitud). Úsala SIEMPRE antes de get_weather si el "
                "usuario menciona un lugar y aún no tienes sus coordenadas."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": "Nombre del lugar, ej. 'Madrid', 'Barcelona', 'Ciudad de México'",
                    }
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Devuelve la previsión del tiempo real para unas coordenadas: "
                "condiciones actuales y previsión de los próximos 7 días. "
                "Úsala para responder cualquier pregunta meteorológica."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "latitude": {"type": "number", "description": "Latitud en grados decimales"},
                    "longitude": {"type": "number", "description": "Longitud en grados decimales"},
                    "lugar": {
                        "type": "string",
                        "description": "Nombre legible del lugar para mostrar en la respuesta, ej. 'Madrid, España'",
                    },
                },
                "required": ["latitude", "longitude", "lugar"],
            },
        },
    },
]


def buscar_ciudad(nombre):
    """Busca un lugar por nombre y devuelve sus coordenadas (o un error)."""
    try:
        respuesta = requests.get(
            GEOCODING_URL,
            params={"name": nombre, "count": 1, "language": "es", "format": "json"},
            timeout=10,
        )
        respuesta.raise_for_status()
        resultados = respuesta.json().get("results", [])
    except requests.RequestException as error:
        return {"error": f"No se pudo consultar la geolocalización: {error}"}

    if not resultados:
        return {"error": f"No encontré ningún lugar llamado '{nombre}'."}

    lugar = resultados[0]
    partes = [lugar.get("name")]
    if lugar.get("admin1"):
        partes.append(lugar["admin1"])
    if lugar.get("country"):
        partes.append(lugar["country"])

    return {
        "latitude": lugar["latitude"],
        "longitude": lugar["longitude"],
        "lugar": ", ".join(p for p in partes if p),
    }


def get_weather(latitude, longitude, lugar):
    """Devuelve condiciones actuales y previsión de 7 días para unas coordenadas."""
    try:
        respuesta = requests.get(
            FORECAST_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": (
                    "temperature_2m,relative_humidity_2m,apparent_temperature,"
                    "precipitation,weather_code,wind_speed_10m"
                ),
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_probability_max"
                ),
                "forecast_days": 7,
                "timezone": "auto",
            },
            timeout=10,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
    except requests.RequestException as error:
        return {"error": f"No se pudo consultar la previsión del tiempo: {error}"}

    actual = datos.get("current", {})
    diario = datos.get("daily", {})

    ahora = {
        "lugar": lugar,
        "hora_local": datos.get("current", {}).get("time", ""),
        "temperatura_c": actual.get("temperature_2m"),
        "sensacion_termica_c": actual.get("apparent_temperature"),
        "humedad_relativa_pct": actual.get("relative_humidity_2m"),
        "viento_km_h": actual.get("wind_speed_10m"),
        "precipitacion_mm": actual.get("precipitation"),
        "estado": _descripcion_codigo(actual.get("weather_code")),
    }

    dias = []
    for i, fecha in enumerate(diario.get("time", [])):
        dias.append(
            {
                "fecha": fecha,
                "estado": _descripcion_codigo(diario.get("weather_code", [])[i]),
                "temp_max_c": diario.get("temperature_2m_max", [])[i],
                "temp_min_c": diario.get("temperature_2m_min", [])[i],
                "prob_lluvia_pct": diario.get("precipitation_probability_max", [])[i],
            }
        )

    return {"ahora": ahora, "proximos_7_dias": dias}


def ejecutar_herramienta(nombre, argumentos):
    """Ejecuta la herramienta que pidió el LLM y devuelve un JSON como string."""
    if nombre == "buscar_ciudad":
        resultado = buscar_ciudad(**argumentos)
    elif nombre == "get_weather":
        resultado = get_weather(**argumentos)
    else:
        resultado = {"error": f"Herramienta desconocida: {nombre}"}
    return json.dumps(resultado, ensure_ascii=False)
