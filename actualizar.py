"""
Portadas IA · el "robot" que actualiza los datos
------------------------------------------------
Este programa NO es la web. Lo ejecuta GitHub automáticamente (ver
.github/workflows/actualizar.yml) a las 8:00, 11:00, 14:00, 17:00 y 20:00.

Pasos que sigue:
  1. Descargar los titulares de portada de cada periódico (por RSS).
  2. Pedir a ChatGPT, con LangChain, el resumen, el populismo y el sesgo de
     cada portada, el nivel de crispación del conjunto y la opinión de
     cinco personajes de distintas ideologías.
  3. Guardar todo en la carpeta datos/:
       - ultimo.json     → lo que enseña la web
       - historial.json  → un registro por día con la crispación
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import requests
from bs4 import BeautifulSoup
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

# Cada periódico tiene: su web, y una lista de direcciones RSS de portada.
# Si la primera dirección falla, se prueba la siguiente.
PERIODICOS = {
    "El País": {
        "web": "https://elpais.com",
        "rss": ["https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"],
    },
    "El Mundo": {
        "web": "https://www.elmundo.es",
        "rss": ["https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"],
    },
    "ABC": {
        "web": "https://www.abc.es",
        "rss": ["https://www.abc.es/rss/2.0/portada/"],
    },
    "Público": {
        "web": "https://www.publico.es",
        "rss": ["https://www.publico.es/rss/", "https://www.publico.es/rss"],
    },
    "OKdiario": {
        "web": "https://okdiario.com",
        "rss": ["https://okdiario.com/feed"],
    },
}

# Los cinco personajes de "¿Quién quieres que te dé la opinión?".
# 'perfil' es la descripción que se le da a ChatGPT para que escriba como ellos.
OPINADORES = [
    {
        "id": "comunista",
        "nombre": "Un comunista",
        "perfil": "una persona comunista: analiza la actualidad desde la lucha de "
        "clases y defiende a la clase trabajadora, los servicios públicos y la "
        "propiedad colectiva frente al gran capital",
    },
    {
        "id": "anarquista",
        "nombre": "Un anarquista",
        "perfil": "una persona anarquista: desconfía del Estado, de los partidos y "
        "de toda jerarquía, y defiende la autogestión, el apoyo mutuo y la libertad "
        "individual y colectiva",
    },
    {
        "id": "liberal",
        "nombre": "Un liberal",
        "perfil": "una persona liberal: defiende la libertad individual, el libre "
        "mercado, los impuestos bajos, un Estado limitado y la responsabilidad personal",
    },
    {
        "id": "extrema_derecha",
        "nombre": "Uno de extrema derecha",
        "perfil": "una persona de extrema derecha: nacionalista y muy conservadora, "
        "prioriza la soberanía nacional, la seguridad, el control estricto de la "
        "inmigración y las tradiciones, y desconfía de las élites políticas y mediáticas",
    },
    {
        "id": "centro",
        "nombre": "Una demócrata de centro",
        "perfil": "una persona demócrata de centro: moderada, defiende las "
        "instituciones, el consenso, las reformas graduales y el equilibrio entre "
        "el mercado y la protección social",
    },
]

HORAS = [8, 11, 14, 17, 20]     # horas (de Madrid) a las que se actualiza
MAX_TITULARES = 12              # noticias de cada portada que se envían a ChatGPT
MADRID = ZoneInfo("Europe/Madrid")

CARPETA = Path(__file__).parent / "datos"
ARCHIVO_ULTIMO = CARPETA / "ultimo.json"
ARCHIVO_HISTORIAL = CARPETA / "historial.json"

# Algunos periódicos rechazan peticiones que no parecen venir de un navegador.
CABECERAS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}


# ----------------------------------------------------------------------
# ¿TOCA ACTUALIZAR?
# ----------------------------------------------------------------------

def leer_json(archivo: Path, por_defecto):
    """Lee un archivo JSON; si no existe devuelve el valor por defecto."""
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    return por_defecto


def leer_secreto(nombre: str) -> str:
    """Lee un Secret y le quita espacios, saltos de línea y comillas sobrantes,
    que se cuelan con facilidad al copiar y pegar."""
    return os.environ[nombre].strip().strip("\"'").strip()


def turno_actual(ahora: datetime) -> int | None:
    """Devuelve la última hora de actualización ya cumplida hoy (8, 11, 14...).

    Antes de las 8:00 devuelve None: todavía no toca.
    GitHub puede arrancar con retraso, por eso no exigimos la hora exacta.
    """
    cumplidas = [hora for hora in HORAS if hora <= ahora.hour]
    return cumplidas[-1] if cumplidas else None


# ----------------------------------------------------------------------
# PASO 1 · LEER LAS PORTADAS
# ----------------------------------------------------------------------

def limpiar_html(texto: str) -> str:
    """Quita las etiquetas HTML y deja solo el texto."""
    return BeautifulSoup(texto or "", "html.parser").get_text(" ", strip=True)


def leer_rss(url: str) -> list[dict]:
    """Descarga un RSS y devuelve sus noticias como lista de diccionarios."""
    respuesta = requests.get(url, headers=CABECERAS, timeout=15)
    respuesta.raise_for_status()
    feed = feedparser.parse(respuesta.content)

    noticias = []
    for entrada in feed.entries[:MAX_TITULARES]:
        titulo = limpiar_html(entrada.get("title", ""))
        if not titulo:
            continue
        noticias.append(
            {
                "titulo": titulo,
                "entradilla": limpiar_html(entrada.get("summary", ""))[:300],
                "enlace": entrada.get("link", ""),
            }
        )
    return noticias


def leer_web(url: str) -> list[dict]:
    """Plan B: si no hay RSS, saca los titulares directamente de la portada web."""
    respuesta = requests.get(url, headers=CABECERAS, timeout=15)
    respuesta.raise_for_status()
    sopa = BeautifulSoup(respuesta.text, "html.parser")

    noticias, vistos = [], set()
    for cabecera in sopa.find_all(["h1", "h2", "h3"]):
        enlace = cabecera.find("a", href=True) or cabecera.find_parent("a", href=True)
        titulo = cabecera.get_text(" ", strip=True)
        # Nos quedamos con titulares "de verdad": con enlace y un mínimo de palabras.
        if not enlace or len(titulo.split()) < 5 or titulo in vistos:
            continue
        vistos.add(titulo)
        noticias.append(
            {
                "titulo": titulo,
                "entradilla": "",
                "enlace": requests.compat.urljoin(url, enlace["href"]),
            }
        )
        if len(noticias) >= MAX_TITULARES:
            break
    return noticias


def leer_portadas() -> dict[str, list[dict]]:
    """Lee la portada de todos los periódicos."""
    portadas = {}
    for nombre, datos in PERIODICOS.items():
        noticias = []
        for url in datos["rss"]:
            try:
                noticias = leer_rss(url)
            except Exception as error:
                print(f"  {nombre}: falló el RSS {url} ({error})")
                noticias = []
            if noticias:
                break
        if not noticias:
            try:
                noticias = leer_web(datos["web"])
            except Exception as error:
                print(f"  {nombre}: falló también la web ({error})")
                noticias = []
        print(f"  {nombre}: {len(noticias)} noticias")
        portadas[nombre] = noticias
    return portadas


# ----------------------------------------------------------------------
# PASO 2 · ANALIZAR CON LANGCHAIN + CHATGPT
# ----------------------------------------------------------------------

class Analisis(BaseModel):
    """Lo que le pedimos a ChatGPT para cada portada, con forma fija."""

    resumen: str = Field(
        description="Resumen de la portada en 4 o 5 viñetas cortas en Markdown, "
        "empezando por los temas más destacados."
    )
    populismo: int = Field(
        ge=0,
        le=100,
        description="Nivel de populismo de los titulares, de 0 (nada) a 100 (máximo).",
    )
    motivo_populismo: str = Field(
        description="Una frase que justifique la nota citando rasgos concretos de los titulares."
    )
    sesgo: str = Field(
        description="Una o dos frases sobre el sesgo o enfoque que muestra la selección "
        "y redacción de las noticias. Si no se aprecia, dilo."
    )


class AnalisisGeneral(BaseModel):
    """Lo que le pedimos a ChatGPT sobre el conjunto de las portadas."""

    temas: str = Field(
        description="Párrafo breve (máximo 90 palabras) con los temas que más se "
        "repiten entre periódicos, seguido de una frase que señale algún tema que "
        "solo destaque uno de ellos, diciendo cuál."
    )
    crispacion: int = Field(
        ge=0,
        le=100,
        description="Nivel de crispación del día, de 0 (calma) a 100 (máxima tensión).",
    )
    motivo_crispacion: str = Field(
        description="Resumen de 3 o 4 frases (entre 60 y 90 palabras) que explique "
        "por qué el día tiene ese nivel de crispación: qué asuntos concretos generan "
        "tensión, entre quiénes, y qué noticias más tranquilas la compensan, si las hay."
    )


PROMPT_PERIODICO = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un analista de medios que estudia portadas de prensa española. "
            "Escribes en español, de forma neutral y sin opinar de política. "
            "Usa solo la información que se te da: no inventes datos.\n\n"
            "Para medir el populismo fíjate únicamente en el texto: lenguaje "
            "emocional o alarmista, sensacionalismo, enfrentamiento 'nosotros "
            "contra ellos', apelaciones al pueblo frente a las élites, "
            "simplificación de temas complejos y descalificaciones. "
            "0 es un tono totalmente informativo y sobrio; 100 es el máximo. "
            "Aplica el mismo criterio a cualquier portada, sin tener en cuenta "
            "de qué medio pueda ser.",
        ),
        (
            "human",
            "Estas son las noticias de portada de un periódico ahora mismo:\n\n"
            "{noticias}\n\n"
            "Resume la portada, valora su nivel de populismo de 0 a 100 y "
            "describe el sesgo que se aprecia.",
        ),
    ]
)

PROMPT_GENERAL = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un analista de medios que compara portadas de prensa española. "
            "Escribes en español, de forma neutral y sin opinar de política. "
            "Usa solo la información que se te da: no inventes datos.\n\n"
            "Para medir la crispación fíjate en cuánta tensión y enfrentamiento "
            "político y social reflejan las noticias en conjunto: choques entre "
            "partidos o instituciones, acusaciones, insultos, protestas, "
            "escándalos y lenguaje polarizador. 0 es un día tranquilo, de "
            "noticias informativas sin conflicto; 100 es tensión máxima.",
        ),
        (
            "human",
            "Estas son las portadas de varios periódicos:\n\n{noticias}\n\n"
            "Di qué temas se repiten más y valora de 0 a 100 el nivel de "
            "crispación del día.",
        ),
    ]
)


PROMPT_OPINION = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Vas a escribir una columna de opinión muy breve, en primera persona y "
            "en español, desde el punto de vista de {perfil}.\n\n"
            "Representa esa forma de pensar con fidelidad y con sus mejores "
            "argumentos, como lo haría un columnista serio de esa corriente: no la "
            "ridiculices ni la suavices. Es un personaje inventado.\n\n"
            "Reglas: comenta solo las noticias que se te dan; no inventes hechos, "
            "datos ni citas; nada de insultos, de lenguaje de odio contra ningún "
            "colectivo ni de llamadas a la violencia. Entre 110 y 150 palabras, en "
            "uno o dos párrafos, sin título.",
        ),
        (
            "human",
            "Estas son las noticias de portada de hoy en varios periódicos:\n\n"
            "{noticias}\n\n¿Qué opinas del día?",
        ),
    ]
)


def noticias_a_texto(noticias: list[dict]) -> str:
    """Convierte la lista de noticias en un texto sencillo para el prompt."""
    lineas = []
    for noticia in noticias:
        linea = f"- {noticia['titulo']}"
        if noticia["entradilla"]:
            linea += f" — {noticia['entradilla']}"
        lineas.append(linea)
    return "\n".join(lineas)


def analizar(portadas: dict[str, list[dict]], nombre_modelo: str) -> tuple[dict, dict, list]:
    """Devuelve (análisis general, {periódico: análisis}, opiniones)."""
    clave = leer_secreto("OPENAI_API_KEY")
    modelo = ChatOpenAI(api_key=clave, model=nombre_modelo)

    # Una "cadena" de LangChain: prompt -> modelo -> resultado.
    # with_structured_output obliga a ChatGPT a responder con una forma fija
    # (los campos de Analisis y AnalisisGeneral) en lugar de con texto libre.
    cadena_periodico = PROMPT_PERIODICO | modelo.with_structured_output(Analisis)
    cadena_general = PROMPT_GENERAL | modelo.with_structured_output(AnalisisGeneral)

    con_noticias = {n: p for n, p in portadas.items() if p}

    # .batch lanza las cinco peticiones a la vez en lugar de una detrás de otra.
    # A propósito no le decimos el nombre del periódico, para que valore solo
    # lo que lee y no la fama del medio.
    resultados = cadena_periodico.batch(
        [{"noticias": noticias_a_texto(noticias)} for noticias in con_noticias.values()]
    )
    por_periodico = {
        nombre: resultado.model_dump()
        for nombre, resultado in zip(con_noticias.keys(), resultados)
    }

    todo = "\n\n".join(
        f"## {nombre}\n{noticias_a_texto(noticias)}"
        for nombre, noticias in con_noticias.items()
    )
    general = cadena_general.invoke({"noticias": todo}).model_dump()

    # La opinión de cada personaje: el mismo prompt, cambiando solo el perfil.
    cadena_opinion = PROMPT_OPINION | modelo | StrOutputParser()
    textos = cadena_opinion.batch(
        [{"perfil": opinador["perfil"], "noticias": todo} for opinador in OPINADORES]
    )
    opiniones = [
        {"id": opinador["id"], "nombre": opinador["nombre"], "texto": texto.strip()}
        for opinador, texto in zip(OPINADORES, textos)
    ]
    return general, por_periodico, opiniones


# ----------------------------------------------------------------------
# PASO 3 · GUARDAR
# ----------------------------------------------------------------------

def guardar_json(archivo: Path, datos) -> None:
    archivo.parent.mkdir(exist_ok=True)
    archivo.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def apuntar_en_historial(fecha: str, turno: int, general: dict) -> None:
    """Añade (o actualiza) el registro de hoy en historial.json.

    Hay un registro por día. Dentro guardamos la nota de cada actualización
    y la crispación del día es la media de todas ellas.
    """
    historial = leer_json(ARCHIVO_HISTORIAL, [])
    registro = next((r for r in historial if r["fecha"] == fecha), None)
    if registro is None:
        registro = {"fecha": fecha, "valores": {}}
        historial.append(registro)

    registro["valores"][f"{turno:02d}"] = general["crispacion"]
    notas = list(registro["valores"].values())
    registro["crispacion"] = round(sum(notas) / len(notas))
    registro["comentario"] = general["motivo_crispacion"]

    historial.sort(key=lambda r: r["fecha"])
    guardar_json(ARCHIVO_HISTORIAL, historial)


def main() -> None:
    ahora = datetime.now(MADRID)
    fecha = ahora.strftime("%Y-%m-%d")
    turno = turno_actual(ahora)
    forzar = os.environ.get("FORZAR") == "1"   # ejecución manual desde GitHub

    if forzar and turno is None:
        turno = HORAS[0]
    if turno is None:
        print("Todavía no son las 8:00 en Madrid: no toca actualizar.")
        return

    ultimo = leer_json(ARCHIVO_ULTIMO, {})
    ya_hecho = ultimo.get("fecha") == fecha and ultimo.get("turno") == turno
    if ya_hecho and not forzar:
        print(f"La actualización de las {turno}:00 ya está hecha.")
        return

    nombre_modelo = leer_secreto("OPENAI_MODEL")

    print("Leyendo portadas…")
    portadas = leer_portadas()
    if not any(portadas.values()):
        sys.exit("No se ha podido leer ninguna portada: no se guarda nada.")

    print(f"Analizando con {nombre_modelo}…")
    general, por_periodico, opiniones = analizar(portadas, nombre_modelo)

    guardar_json(
        ARCHIVO_ULTIMO,
        {
            "fecha": fecha,
            "turno": turno,
            "generado": ahora.strftime("%d/%m/%Y %H:%M"),
            "modelo": nombre_modelo,
            "general": general,
            "opiniones": opiniones,
            "periodicos": [
                {
                    "nombre": nombre,
                    "web": datos["web"],
                    "noticias": portadas[nombre],
                    "analisis": por_periodico.get(nombre),
                }
                for nombre, datos in PERIODICOS.items()
            ],
        },
    )
    apuntar_en_historial(fecha, turno, general)
    print(f"Guardado. Crispación: {general['crispacion']} / 100")


if __name__ == "__main__":
    main()
