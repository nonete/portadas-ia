"""
Portadas IA
-----------
Al entrar en la web se leen las portadas de cinco periódicos españoles
y ChatGPT (a través de LangChain) escribe un resumen de cada una.

Pasos que sigue el programa:
  1. Descargar los titulares de portada de cada periódico (por RSS).
  2. Pasarle esos titulares a ChatGPT con LangChain para que los resuma.
  3. Pintar el resultado con Streamlit.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests
import streamlit as st
from bs4 import BeautifulSoup
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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

MAX_TITULARES = 12          # cuántas noticias de cada portada se envían a ChatGPT
MINUTOS_CACHE = 30          # cada cuánto se vuelve a leer y resumir
SEGUNDOS_CACHE = MINUTOS_CACHE * 60

# Algunos periódicos rechazan peticiones que no parecen venir de un navegador.
CABECERAS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9",
}


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


@st.cache_data(ttl=SEGUNDOS_CACHE, show_spinner=False)
def leer_portadas() -> dict[str, list[dict]]:
    """Lee la portada de todos los periódicos. El resultado se guarda 30 minutos."""
    portadas = {}
    for nombre, datos in PERIODICOS.items():
        noticias = []
        for url in datos["rss"]:
            try:
                noticias = leer_rss(url)
            except Exception:
                noticias = []
            if noticias:
                break
        if not noticias:
            try:
                noticias = leer_web(datos["web"])
            except Exception:
                noticias = []
        portadas[nombre] = noticias
    return portadas


# ----------------------------------------------------------------------
# PASO 2 · RESUMIR CON LANGCHAIN + CHATGPT
# ----------------------------------------------------------------------

PROMPT_PERIODICO = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un periodista que resume portadas de prensa española. "
            "Escribes en español, de forma neutral y sin opinar. "
            "Usa solo la información que se te da: no inventes datos.",
        ),
        (
            "human",
            "Estas son las noticias de portada de {periodico} ahora mismo:\n\n"
            "{noticias}\n\n"
            "Escribe un resumen de la portada en 4 o 5 viñetas cortas en Markdown, "
            "empezando por los temas más destacados.",
        ),
    ]
)

PROMPT_GENERAL = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un periodista que compara portadas de prensa española. "
            "Escribes en español, de forma neutral y sin opinar. "
            "Usa solo la información que se te da: no inventes datos.",
        ),
        (
            "human",
            "Estas son las portadas de varios periódicos:\n\n{noticias}\n\n"
            "Escribe un párrafo breve (máximo 90 palabras) con los temas del día "
            "que más se repiten entre periódicos. Después, en una sola frase, "
            "señala algún tema que solo destaque uno de ellos, diciendo cuál.",
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


@st.cache_data(ttl=SEGUNDOS_CACHE, show_spinner=False)
def resumir(portadas: dict[str, list[dict]]) -> tuple[str, dict[str, str]]:
    """Devuelve (resumen general, {periódico: resumen}). Se guarda 30 minutos."""
    modelo = ChatOpenAI(
        api_key=st.secrets["OPENAI_API_KEY"],
        model=st.secrets["OPENAI_MODEL"],
    )

    # Una "cadena" de LangChain: prompt -> modelo -> texto.
    cadena_periodico = PROMPT_PERIODICO | modelo | StrOutputParser()
    cadena_general = PROMPT_GENERAL | modelo | StrOutputParser()

    con_noticias = {n: p for n, p in portadas.items() if p}

    # .batch lanza las cinco peticiones a la vez en lugar de una detrás de otra.
    textos = cadena_periodico.batch(
        [
            {"periodico": nombre, "noticias": noticias_a_texto(noticias)}
            for nombre, noticias in con_noticias.items()
        ]
    )
    resumenes = dict(zip(con_noticias.keys(), textos))

    todo = "\n\n".join(
        f"## {nombre}\n{noticias_a_texto(noticias)}"
        for nombre, noticias in con_noticias.items()
    )
    general = cadena_general.invoke({"noticias": todo})
    return general, resumenes


# ----------------------------------------------------------------------
# PASO 3 · LA PÁGINA
# ----------------------------------------------------------------------

st.set_page_config(page_title="Portadas IA", page_icon="📰", layout="centered")

st.title("📰 Portadas IA")
st.caption(
    "Resumen automático de las portadas de El País, El Mundo, ABC, Público y "
    "OKdiario, hecho con LangChain y ChatGPT."
)

# Comprobamos que las claves están en Secrets antes de hacer nada.
try:
    faltan = [c for c in ("OPENAI_API_KEY", "OPENAI_MODEL") if c not in st.secrets]
except Exception:  # todavía no existe ningún Secret
    faltan = ["OPENAI_API_KEY", "OPENAI_MODEL"]
if faltan:
    st.error(
        "Faltan estos valores en los Secrets de Streamlit: "
        + ", ".join(f"`{c}`" for c in faltan)
    )
    st.code('OPENAI_API_KEY = "sk-..."\nOPENAI_MODEL = "gpt-4o-mini"', language="toml")
    st.stop()

if st.button("🔄 Actualizar ahora"):
    st.cache_data.clear()
    st.rerun()

with st.spinner("Leyendo las portadas…"):
    portadas = leer_portadas()

if not any(portadas.values()):
    st.error("No se ha podido leer ninguna portada. Prueba de nuevo en unos minutos.")
    st.stop()

try:
    with st.spinner("ChatGPT está resumiendo las noticias…"):
        general, resumenes = resumir(portadas)
except Exception as error:
    st.error(f"No se ha podido generar el resumen con OpenAI: {error}")
    st.stop()

ahora = datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d/%m/%Y %H:%M")
st.caption(
    f"Consultado el {ahora} · se renueva cada {MINUTOS_CACHE} minutos · "
    f"modelo: {st.secrets['OPENAI_MODEL']}"
)

st.subheader("Lo más repetido hoy")
st.write(general)

for nombre, datos in PERIODICOS.items():
    st.divider()
    st.subheader(nombre)
    noticias = portadas[nombre]
    if not noticias:
        st.warning(f"No se ha podido leer la portada de {nombre}.")
        st.markdown(f"[Abrir {nombre}]({datos['web']})")
        continue

    st.markdown(resumenes[nombre])
    with st.expander(f"Ver los {len(noticias)} titulares originales"):
        for noticia in noticias:
            if noticia["enlace"]:
                st.markdown(f"- [{noticia['titulo']}]({noticia['enlace']})")
            else:
                st.markdown(f"- {noticia['titulo']}")

st.divider()
st.caption(
    "Los resúmenes los genera una IA a partir de los titulares y pueden contener "
    "errores. Pulsa en cada titular para leer la noticia completa en su periódico."
)
