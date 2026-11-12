"""
Portadas IA · el "robot" que actualiza los datos
------------------------------------------------
Este programa NO es la web. Lo ejecuta GitHub automáticamente (ver
.github/workflows/actualizar.yml) a las 8:00 y a las 18:00.

Pasos que sigue:
  1. Descargar los titulares de portada de cada periódico (por RSS).
  2. Pedir a ChatGPT, con LangChain, el resumen, el populismo y el sesgo de
     cada portada, el nivel de crispación del conjunto y la opinión de
     cinco personajes de distintas ideologías.
  3. Guardar todo en datos/<país>/ (datos/es, datos/fr…):
       - ultimo.json     → lo que enseña la web
       - historial.json  → un registro por día con la crispación

Los pasos se repiten para cada país de la lista PAISES.
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

import prompts

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

# Cada periódico tiene: su web, y una lista de direcciones RSS de portada.
# Si la primera dirección falla, se prueba la siguiente.
PERIODICOS_ES = {
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

PERIODICOS_FR = {
    "Le Monde": {
        "web": "https://www.lemonde.fr",
        "rss": ["https://www.lemonde.fr/rss/une.xml"],
    },
    "Le Figaro": {
        "web": "https://www.lefigaro.fr",
        "rss": ["https://www.lefigaro.fr/rss/figaro_actualites.xml"],
    },
    "Libération": {
        "web": "https://www.liberation.fr",
        "rss": [
            "https://www.liberation.fr/arc/outboundfeeds/rss-all/collection/accueil-une/?outputType=xml"
        ],
    },
    "Le Parisien": {
        "web": "https://www.leparisien.fr",
        "rss": ["https://feeds.leparisien.fr/leparisien/rss"],
    },
    "Ouest-France": {
        "web": "https://www.ouest-france.fr",
        "rss": ["https://www.ouest-france.fr/rss/une", "https://www.ouest-france.fr/rss-en-continu.xml"],
    },
}

# --- Países añadidos el 11/11/2026 -------------------------------------
# Las direcciones se probaron desde GitHub. Un periódico con "rss": [] no
# tiene RSS que funcione: sus titulares se sacan de la portada web (plan B).

PERIODICOS_US = {
    "The New York Times": {
        "web": "https://www.nytimes.com",
        "rss": ["https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"],
    },
    "The Washington Post": {
        "web": "https://www.washingtonpost.com",
        "rss": [
            "https://feeds.washingtonpost.com/rss/national",
            "https://feeds.washingtonpost.com/rss/politics",
        ],
    },
    "The Wall Street Journal": {
        "web": "https://www.wsj.com",
        "rss": [
            "https://feeds.content.dowjones.io/public/rss/RSSUSnews",
            "https://feeds.content.dowjones.io/public/rss/RSSWorldNews",
        ],
    },
    "Los Angeles Times": {
        "web": "https://www.latimes.com",
        "rss": ["https://www.latimes.com/rss2.0.xml", "https://www.latimes.com/index.rss"],
    },
    "New York Post": {
        "web": "https://nypost.com",
        "rss": ["https://nypost.com/feed/"],
    },
}

PERIODICOS_GB = {
    "The Guardian": {
        "web": "https://www.theguardian.com/uk",
        "rss": ["https://www.theguardian.com/uk/rss"],
    },
    "The Telegraph": {
        "web": "https://www.telegraph.co.uk",
        "rss": ["https://www.telegraph.co.uk/news/rss.xml", "https://www.telegraph.co.uk/rss.xml"],
    },
    "The Independent": {
        "web": "https://www.independent.co.uk",
        "rss": ["https://www.independent.co.uk/rss"],
    },
    "Daily Mail": {
        "web": "https://www.dailymail.co.uk",
        "rss": ["https://www.dailymail.co.uk/news/index.rss", "https://www.dailymail.co.uk/home/index.rss"],
    },
    "Daily Mirror": {
        "web": "https://www.mirror.co.uk",
        "rss": ["https://www.mirror.co.uk/news/?service=rss", "https://www.mirror.co.uk/?service=rss"],
    },
}

PERIODICOS_DE = {
    "Süddeutsche Zeitung": {
        "web": "https://www.sueddeutsche.de",
        "rss": ["https://rss.sueddeutsche.de/rss/Topthemen"],
    },
    "Die Welt": {
        "web": "https://www.welt.de",
        "rss": ["https://www.welt.de/feeds/topnews.rss", "https://www.welt.de/feeds/latest.rss"],
    },
    "Der Spiegel": {
        "web": "https://www.spiegel.de",
        "rss": ["https://www.spiegel.de/schlagzeilen/tops/index.rss"],
    },
    "Bild": {
        "web": "https://www.bild.de",
        "rss": ["https://www.bild.de/feed/alles.xml"],
    },
    "taz": {
        "web": "https://taz.de",
        "rss": ["https://taz.de/!p4608;rss/", "https://taz.de/rss.xml"],
    },
}

PERIODICOS_IT = {
    "Corriere della Sera": {
        "web": "https://www.corriere.it",
        "rss": ["https://xml2.corriereobjects.it/rss/homepage.xml", "https://www.corriere.it/rss/homepage.xml"],
    },
    "la Repubblica": {
        "web": "https://www.repubblica.it",
        "rss": ["https://www.repubblica.it/rss/homepage/rss2.0.xml"],
    },
    "La Stampa": {
        "web": "https://www.lastampa.it",
        "rss": ["https://www.lastampa.it/rss/copertina.xml"],
    },
    "Il Giornale": {
        "web": "https://www.ilgiornale.it",
        "rss": [],
    },
    "Il Fatto Quotidiano": {
        "web": "https://www.ilfattoquotidiano.it",
        "rss": ["https://www.ilfattoquotidiano.it/feed/"],
    },
}

# Rusia: cuatro medios editados en Rusia y Meduza, independiente, que se
# publica desde el exilio (Letonia).
PERIODICOS_RU = {
    "Kommersant": {
        "web": "https://www.kommersant.ru",
        "rss": ["https://www.kommersant.ru/RSS/main.xml", "https://www.kommersant.ru/RSS/news.xml"],
    },
    "Rossíiskaya Gazeta": {
        "web": "https://rg.ru",
        "rss": ["https://rg.ru/xml/index.xml"],
    },
    "Komsomólskaya Pravda": {
        "web": "https://www.kp.ru",
        "rss": ["https://www.kp.ru/rss/allsections.xml"],
    },
    # Moskovski Komsomólets se descartó: desde GitHub unas veces responde y otras no.
    "Védomosti": {
        "web": "https://www.vedomosti.ru",
        "rss": ["https://www.vedomosti.ru/rss/articles", "https://www.vedomosti.ru/rss/news"],
    },
    "Meduza": {
        "web": "https://meduza.io",
        "rss": ["https://meduza.io/rss/all"],
    },
}

# China: cuatro medios estatales (dos en chino y dos en inglés) y el
# South China Morning Post, de Hong Kong.
PERIODICOS_CN = {
    "Diario del Pueblo": {
        "web": "http://www.people.com.cn",
        "rss": ["http://www.people.com.cn/rss/politics.xml", "http://en.people.cn/rss/90000.xml"],
    },
    "Xinhua": {
        "web": "https://www.news.cn",
        "rss": [
            "http://www.xinhuanet.com/politics/news_politics.xml",
            "https://english.news.cn/rss/chinarss.xml",
        ],
    },
    "Global Times": {
        "web": "https://www.globaltimes.cn",
        "rss": ["https://www.globaltimes.cn/rss/outbrain.xml"],
    },
    "CGTN": {
        "web": "https://www.cgtn.com",
        "rss": ["https://www.cgtn.com/subscribe/rss/section/china.xml"],
    },
    "South China Morning Post": {
        "web": "https://www.scmp.com",
        "rss": ["https://www.scmp.com/rss/4/feed", "https://www.scmp.com/rss/91/feed"],
    },
}

# Brasil, añadido el 11/11/2026.
PERIODICOS_BR = {
    "Folha de S.Paulo": {
        "web": "https://www.folha.uol.com.br",
        "rss": [
            "https://feeds.folha.uol.com.br/emcimadahora/rss091.xml",
            "https://feeds.folha.uol.com.br/poder/rss091.xml",
        ],
    },
    "O Globo": {
        "web": "https://oglobo.globo.com",
        "rss": ["https://oglobo.globo.com/rss/oglobo"],
    },
    "O Estado de S. Paulo": {
        "web": "https://www.estadao.com.br",
        "rss": [
            "https://www.estadao.com.br/arc/outboundfeeds/rss/?outputType=xml",
            "https://www.estadao.com.br/arc/outboundfeeds/feeds/rss/sections/politica/",
        ],
    },
    "Gazeta do Povo": {
        "web": "https://www.gazetadopovo.com.br",
        "rss": ["https://www.gazetadopovo.com.br/feed/rss/ultimas-noticias.xml"],
    },
    "CartaCapital": {
        "web": "https://www.cartacapital.com.br",
        "rss": ["https://www.cartacapital.com.br/feed/"],
    },
}

# Egipto, añadido el 11/11/2026. Titulares en árabe. Al-Ahram (el gran diario
# estatal), Al-Wafd y Al-Dostor responden 403 desde GitHub, así que el diario
# estatal elegido es Akhbar El-Yom. Tres de los cinco no tienen RSS que
# funcione: se leen de la portada web con el plan B.
PERIODICOS_EG = {
    "Al-Masry Al-Youm": {
        "web": "https://www.almasryalyoum.com",
        "rss": ["https://www.almasryalyoum.com/rss/rssfeeds"],
    },
    "Youm7": {
        "web": "https://www.youm7.com",
        "rss": [
            "https://www.youm7.com/rss/SectionRss?SectionID=65",
            "https://www.youm7.com/rss/SectionRss?SectionID=97",
        ],
    },
    "Akhbar El-Yom": {
        "web": "https://akhbarelyom.com",
        "rss": [],
    },
    "Al-Shorouk": {
        "web": "https://www.shorouknews.com",
        "rss": [],
    },
    "Mada Masr": {
        "web": "https://www.madamasr.com/ar/",
        "rss": ["https://www.madamasr.com/ar/feed/", "https://www.madamasr.com/en/feed/"],
    },
}

# Los países de la web. La clave ("es", "fr"…) es también el nombre de su carpeta
# dentro de datos/. Para añadir un país basta con añadir una entrada aquí
# (y otra en PAISES de app.py y de web/generar.py para que salga en las webs).
PAISES = {
    "es": {"nombre": "España", "periodicos": PERIODICOS_ES},
    "fr": {"nombre": "Francia", "periodicos": PERIODICOS_FR},
    "us": {"nombre": "Estados Unidos", "periodicos": PERIODICOS_US},
    "gb": {"nombre": "Reino Unido", "periodicos": PERIODICOS_GB},
    "de": {"nombre": "Alemania", "periodicos": PERIODICOS_DE},
    "it": {"nombre": "Italia", "periodicos": PERIODICOS_IT},
    "ru": {"nombre": "Rusia", "periodicos": PERIODICOS_RU},
    "cn": {"nombre": "China", "periodicos": PERIODICOS_CN},
    "br": {"nombre": "Brasil", "periodicos": PERIODICOS_BR},
    "eg": {"nombre": "Egipto", "periodicos": PERIODICOS_EG},
}

# Los cinco personajes de "¿Quién quieres que te dé la opinión?".
# La descripción de cada uno (su "perfil", lo que se le dice a ChatGPT para
# que escriba como ellos) está en config/, con el nombre perfil_<id>.
OPINADORES = [
    {"id": "comunista", "nombre": "Un comunista"},
    {"id": "anarquista", "nombre": "Un anarquista"},
    {"id": "liberal", "nombre": "Un liberal"},
    {"id": "extrema_derecha", "nombre": "Uno de extrema derecha"},
    {"id": "centro", "nombre": "Una demócrata de centro"},
]

HORAS = [8, 18]                # horas (de Madrid) a las que se actualiza
MAX_TITULARES = 12              # noticias de cada portada que se envían a ChatGPT
MADRID = ZoneInfo("Europe/Madrid")

CARPETA = Path(__file__).parent / "datos"


def archivo_ultimo(codigo: str) -> Path:
    """datos/es/ultimo.json, datos/fr/ultimo.json…"""
    return CARPETA / codigo / "ultimo.json"


def archivo_historial(codigo: str) -> Path:
    return CARPETA / codigo / "historial.json"


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
    """Devuelve la última hora de actualización ya cumplida hoy (8 o 18).

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


def leer_portadas(periodicos: dict) -> dict[str, list[dict]]:
    """Lee la portada de todos los periódicos de un país."""
    portadas = {}
    for nombre, datos in periodicos.items():
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


# Los prompts (las instrucciones para ChatGPT) están en config/ y se pueden
# cambiar desde la página de configuración de la web. Ver prompts.py.
TEXTOS = prompts.cargar()

# Cada prompt tiene dos mensajes: "system" (cómo debe comportarse ChatGPT)
# y "human" (lo que le pedimos, con las noticias).
PROMPT_PERIODICO = ChatPromptTemplate.from_messages(
    [("system", TEXTOS["periodico_sistema"]), ("human", TEXTOS["periodico_usuario"])]
)

PROMPT_GENERAL = ChatPromptTemplate.from_messages(
    [("system", TEXTOS["general_sistema"]), ("human", TEXTOS["general_usuario"])]
)

PROMPT_OPINION = ChatPromptTemplate.from_messages(
    [("system", TEXTOS["opinion_sistema"]), ("human", TEXTOS["opinion_usuario"])]
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


def analizar(
    portadas: dict[str, list[dict]], nombre_modelo: str, pais: str
) -> tuple[dict, dict, list]:
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
        [
            {"pais": pais, "noticias": noticias_a_texto(noticias)}
            for noticias in con_noticias.values()
        ]
    )
    por_periodico = {
        nombre: resultado.model_dump()
        for nombre, resultado in zip(con_noticias.keys(), resultados)
    }

    todo = "\n\n".join(
        f"## {nombre}\n{noticias_a_texto(noticias)}"
        for nombre, noticias in con_noticias.items()
    )
    general = cadena_general.invoke({"pais": pais, "noticias": todo}).model_dump()

    # La opinión de cada personaje: el mismo prompt, cambiando solo el perfil.
    cadena_opinion = PROMPT_OPINION | modelo | StrOutputParser()
    textos = cadena_opinion.batch(
        [
            {"perfil": TEXTOS["perfil_" + opinador["id"]], "pais": pais, "noticias": todo}
            for opinador in OPINADORES
        ]
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
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(
        json.dumps(datos, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def archivar_dia(codigo: str, ultimo: dict) -> None:
    """Guarda una copia del día en datos/<país>/dias/<fecha>.json.

    La web estática crea con ella una página fija por día (por ejemplo
    /francia/2026-11-12/). Se sobrescribe en cada lectura, así que al acabar el
    día queda la última (la de las 18:00). Se omiten las opiniones de los
    personajes para que los archivos pesen menos.
    """
    dia = {clave: valor for clave, valor in ultimo.items() if clave != "opiniones"}
    archivo = CARPETA / codigo / "dias" / f"{ultimo['fecha']}.json"
    archivo.parent.mkdir(parents=True, exist_ok=True)
    archivo.write_text(json.dumps(dia, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")


def apuntar_en_historial(codigo: str, fecha: str, turno: int, general: dict) -> None:
    """Añade (o actualiza) el registro de hoy en el historial de un país.

    Hay un registro por día. Dentro guardamos la nota de cada actualización
    y la crispación del día es la media de todas ellas.
    """
    historial = leer_json(archivo_historial(codigo), [])
    registro = next((r for r in historial if r["fecha"] == fecha), None)
    if registro is None:
        registro = {"fecha": fecha, "valores": {}}
        historial.append(registro)

    registro["valores"][f"{turno:02d}"] = general["crispacion"]
    notas = list(registro["valores"].values())
    registro["crispacion"] = round(sum(notas) / len(notas))
    registro["comentario"] = general["motivo_crispacion"]

    historial.sort(key=lambda r: r["fecha"])
    guardar_json(archivo_historial(codigo), historial)


def actualizar_pais(codigo: str, ahora: datetime, turno: int, forzar: bool) -> None:
    """Lee, analiza y guarda las portadas de un país."""
    pais = PAISES[codigo]
    fecha = ahora.strftime("%Y-%m-%d")

    ultimo = leer_json(archivo_ultimo(codigo), {})
    ya_hecho = ultimo.get("fecha") == fecha and ultimo.get("turno") == turno
    if ya_hecho and not forzar:
        print(f"{pais['nombre']}: la actualización de las {turno}:00 ya está hecha.")
        return

    nombre_modelo = leer_secreto("OPENAI_MODEL")

    print(f"{pais['nombre']}: leyendo portadas…")
    portadas = leer_portadas(pais["periodicos"])
    if not any(portadas.values()):
        raise RuntimeError("no se ha podido leer ninguna portada: no se guarda nada")

    print(f"{pais['nombre']}: analizando con {nombre_modelo}…")
    general, por_periodico, opiniones = analizar(portadas, nombre_modelo, pais["nombre"])

    resultado = (
        {
            "pais": pais["nombre"],
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
                for nombre, datos in pais["periodicos"].items()
            ],
        }
    )
    guardar_json(archivo_ultimo(codigo), resultado)
    archivar_dia(codigo, resultado)
    apuntar_en_historial(codigo, fecha, turno, general)
    print(f"{pais['nombre']}: guardado. Crispación: {general['crispacion']} / 100")


def main() -> None:
    ahora = datetime.now(MADRID)
    turno = turno_actual(ahora)
    forzar = os.environ.get("FORZAR") == "1"   # ejecución manual desde GitHub

    if forzar and turno is None:
        # Lanzada a mano antes de las 8:00: se apunta como turno 0, para que
        # la automática de las 8:00 se haga igualmente.
        turno = 0
    if turno is None:
        print("Todavía no son las 8:00 en Madrid: no toca actualizar.")
        return

    # PAIS: si se lanza a mano para un solo país (por ejemplo "br"), solo se
    # hace ese. Vacío = todos.
    solo = os.environ.get("PAIS", "").strip().lower()
    if solo and solo not in PAISES:
        sys.exit(f"No existe el país '{solo}'. Los que hay: {', '.join(PAISES)}")

    # Cada país va por separado: si uno falla, los demás se guardan igual.
    fallos = []
    for codigo in PAISES:
        if solo and codigo != solo:
            continue
        try:
            actualizar_pais(codigo, ahora, turno, forzar)
        except Exception as error:
            print(f"{PAISES[codigo]['nombre']}: ERROR: {error}")
            fallos.append(PAISES[codigo]["nombre"])

    if fallos:
        sys.exit("Ha fallado la actualización de: " + ", ".join(fallos))


if __name__ == "__main__":
    main()
