"""
Portadas IA · el "robot" de la sección Discapacidad
---------------------------------------------------
Lo ejecuta GitHub justo después de actualizar.py (ver
.github/workflows/actualizar.yml), a las 8:00 y a las 18:00.

Pasos que sigue:
  1. Buscar noticias sobre discapacidad en la prensa española. Usa tres vías,
     y si una falla las otras siguen:
       a) Google Noticias (edición de España): busca en todos los medios a la
          vez y permite pedir noticias de hoy, de hace un mes o de hace un año.
       b) Bing Noticias: lo mismo, como refuerzo.
       c) El RSS de cada periódico: de ahí solo se guardan las noticias que
          hablan de discapacidad (ver PALABRAS_CLAVE).
  2. Filtrar: fuera los medios que no son españoles, las webs de instituciones
     y los sorteos de la ONCE. Si el titular no deja claro que la noticia va
     de discapacidad, se le pregunta a ChatGPT.
  3. Juntarlas con las que ya había guardadas, quitar repetidas y las de hace
     más de un año.
  4. Pedir a ChatGPT, con LangChain, un resumen de qué se está hablando sobre
     discapacidad en España.
  5. Guardar todo en datos/discapacidad/ultimo.json, que es lo que enseña la web.
"""

import os
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qs, quote_plus, urlparse

import feedparser
import requests
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

# Reutilizamos las piezas que ya existen en actualizar.py.
from actualizar import (
    CABECERAS,
    CARPETA,
    MADRID,
    guardar_json,
    leer_json,
    leer_secreto,
    limpiar_html,
    turno_actual,
)

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

ARCHIVO = CARPETA / "discapacidad" / "ultimo.json"
# Titulares que ChatGPT ya ha descartado, para no volver a preguntarle por ellos.
ARCHIVO_DESCARTADAS = CARPETA / "discapacidad" / "descartadas.json"
MAX_DESCARTADAS = 3000

# Lo que se busca en Google Noticias y en Bing Noticias.
BUSQUEDAS = [
    "discapacidad",
    '"personas con discapacidad"',
    "discapacidad accesibilidad",
    "discapacidad dependencia",
    "discapacidad CERMI",
]

# Periódicos en los que además se busca uno a uno (en grupos), para que los
# grandes y los regionales no queden tapados por los medios especializados.
SITIOS = [
    "elpais.com", "elmundo.es", "abc.es", "lavanguardia.com", "elconfidencial.com",
    "eldiario.es", "20minutos.es", "larazon.es", "elespanol.com", "publico.es",
    "okdiario.com", "elperiodico.com", "europapress.es", "rtve.es", "infolibre.es",
    "huffingtonpost.es", "eldebate.com", "vozpopuli.com", "elindependiente.com",
    "theobjective.com", "lavozdegalicia.es", "elcorreo.com", "diariovasco.com",
    "heraldo.es", "levante-emv.com", "lasprovincias.es", "diariodesevilla.es",
    "ideal.es", "elnortedecastilla.es", "farodevigo.es", "lne.es",
    "diariodenavarra.es", "canarias7.es", "laverdad.es", "diariosur.es",
    "hoy.es", "elcomercio.es", "eldiariomontanes.es", "larioja.com",
    "diariodemallorca.es", "informacion.es", "laopiniondemurcia.es",
    "elperiodicodearagon.com", "elperiodicoextremadura.com", "eldia.es",
    "laprovincia.es", "ara.cat", "elnacional.cat", "deia.eus", "cadenaser.com",
    # Medios especializados en discapacidad y en el sector social
    "servimedia.es", "discapnet.es", "cermi.es", "solidaridaddigital.es",
    "plenainclusion.org", "cocemfe.es", "somospacientes.com", "tododisca.com",
]
SITIOS_POR_GRUPO = 8

# RSS de cada periódico. De estos solo se guardan las noticias que contienen
# alguna PALABRA_CLAVE. Si una dirección falla, se avisa y se sigue.
# (La Razón, Público, El Periódico, RTVE, El Debate, Vozpópuli, Diario de
# Navarra y Servimedia no tienen un RSS que responda desde GitHub: sus
# noticias llegan por Google Noticias.)
RSS_PERIODICOS = {
    # Nacionales
    "El País": [
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/sociedad/portada",
    ],
    "El Mundo": [
        "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
        "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
    ],
    "ABC": ["https://www.abc.es/rss/2.0/portada/", "https://www.abc.es/rss/2.0/sociedad/"],
    "La Vanguardia": [
        "https://www.lavanguardia.com/rss/home.xml",
        "https://www.lavanguardia.com/rss/vida.xml",
    ],
    "El Confidencial": ["https://rss.elconfidencial.com/espana/"],
    "elDiario.es": ["https://www.eldiario.es/rss/"],
    "20minutos": ["https://www.20minutos.es/rss/"],
    "El Español": ["https://www.elespanol.com/rss/"],
    "OKdiario": ["https://okdiario.com/feed"],
    "Europa Press": [
        "https://www.europapress.es/rss/rss.aspx",
        "https://www.europapress.es/rss/rss.aspx?ch=00313",   # Sociedad
    ],
    "infoLibre": ["https://www.infolibre.es/rss/"],
    "HuffPost": ["https://www.huffingtonpost.es/feeds/index.xml"],
    "El Independiente": ["https://www.elindependiente.com/feed/"],
    "The Objective": ["https://theobjective.com/feed/"],
    "Newtral": ["https://www.newtral.es/feed/"],
    "Libertad Digital": ["https://feeds2.feedburner.com/libertaddigital/portada"],
    # Regionales
    "La Voz de Galicia": ["https://www.lavozdegalicia.es/index.xml"],
    "El Correo": ["https://www.elcorreo.com/rss/2.0/portada"],
    "El Diario Vasco": ["https://www.diariovasco.com/rss/2.0/portada"],
    "Las Provincias": ["https://www.lasprovincias.es/rss/2.0/portada"],
    "Ideal": ["https://www.ideal.es/rss/2.0/portada"],
    "El Norte de Castilla": ["https://www.elnortedecastilla.es/rss/2.0/portada"],
    "Hoy": ["https://www.hoy.es/rss/2.0/portada"],
    "El Comercio": ["https://www.elcomercio.es/rss/2.0/portada"],
    "El Diario Montañés": ["https://www.eldiariomontanes.es/rss/2.0/portada"],
    "La Rioja": ["https://www.larioja.com/rss/2.0/portada"],
    "La Verdad": ["https://www.laverdad.es/rss/2.0/portada"],
    "Diario Sur": ["https://www.diariosur.es/rss/2.0/portada"],
    "Canarias7": ["https://www.canarias7.es/rss/2.0/portada"],
    "Heraldo de Aragón": ["https://www.heraldo.es/rss/"],
    "Diario de Sevilla": ["https://www.diariodesevilla.es/rss/"],
    "Levante-EMV": ["https://www.levante-emv.com/rss/"],
    "Faro de Vigo": ["https://www.farodevigo.es/rss/"],
    "La Nueva España": ["https://www.lne.es/rss/"],
    "Información": ["https://www.informacion.es/rss/"],
    "Diario de Mallorca": ["https://www.diariodemallorca.es/rss/"],
    "El Periódico de Aragón": ["https://www.elperiodicodearagon.com/rss/"],
}

# Medios dedicados por entero a la discapacidad: de estos se guarda todo.
RSS_ESPECIALIZADOS = {
    "Tododisca": ["https://www.tododisca.com/feed/"],
}
# Sus noticias se aceptan sin más comprobaciones, lleguen por donde lleguen.
DOMINIOS_ESPECIALIZADOS = {
    "tododisca.com", "discapnet.es", "cermi.es", "plenainclusion.org",
    "cocemfe.es", "solidaridaddigital.es",
}

# Palabras que indican que una noticia habla de discapacidad (sin distinguir
# mayúsculas ni tildes). Si están en el titular, la noticia se acepta. Si no,
# decide ChatGPT (ver filtrar_con_ia).
PALABRAS_CLAVE = re.compile(
    r"discapacidad|discapacitad|diversidad funcional|movilidad reducida|"
    r"silla de ruedas|sillas de ruedas|accesib|lengua de signos|braille|"
    r"sindrome de down|paralisis cerebral|autismo|autista|\btea\b|sordocegu|"
    r"\bsord[oa]s\b|persona sorda|familia sorda|sordera|personas ciegas|"
    r"ceguera|invidente|paralimpic|\bcermi\b|\bla once\b|"
    r"fundacion once|plena inclusion|\bdependencia|\bdependientes|"
    r"educacion especial|centros? especial(es)? de empleo|lectura facil|"
    r"capacitismo|vida independiente|atencion temprana|\bela\b|aspace|cocemfe"
)

# Resultados de los sorteos de la ONCE: aparecen al buscar, pero no son noticia.
SORTEOS = re.compile(r"sorteo|cupon|cuponazo|numero premiado|comprobar")

# Webs de instituciones, universidades, sindicatos… No son prensa.
INSTITUCIONES = re.compile(
    r"ayuntamiento|ajuntament|\bayto\b|concello|universidad|universitat|"
    r"ministerio|\bjunta de\b|xunta|generalitat|gobierno|govern\b|moncloa|"
    r"cabildo|diputacion|foru aldundia|sindicato|\bugt\b|\bccoo\b|\bcsif\b|"
    r"\banpe\b|\bfsie\b|federacion|colegio de|agencia tributaria|imserso|"
    r"\badif\b|\bcomunica gva\b|\.eus$|^www\.|carm\.es|navarra\.es|"
    r"aguimes\.es|fiscal\.es|aragon hoy|\bicam\b|\bfemp\b|diocesis|\bull\b|"
    r"\bupv\b|\bdkv\b|umivale|fidelitis|plan de recuperacion|talent24h"
)

# Nombre con el que se muestra cada medio, para que el mismo periódico no
# salga escrito de dos formas ("EL PAÍS" y "El País").
NOMBRES = {
    "elpais.com": "El País", "elmundo.es": "El Mundo", "abc.es": "ABC",
    "lavanguardia.com": "La Vanguardia", "elconfidencial.com": "El Confidencial",
    "eldiario.es": "elDiario.es", "20minutos.es": "20minutos",
    "larazon.es": "La Razón", "elespanol.com": "El Español",
    "publico.es": "Público", "okdiario.com": "OKdiario",
    "elperiodico.com": "El Periódico", "europapress.es": "Europa Press",
    "rtve.es": "RTVE", "heraldo.es": "Heraldo de Aragón", "eldia.es": "El Día",
    "marca.com": "Marca", "as.com": "AS", "lasexta.com": "laSexta",
    "elplural.com": "El Plural", "que.es": "Qué!", "ara.cat": "Ara",
    "discapnet.es": "Discapnet", "cope.es": "COPE", "ideal.es": "Ideal",
    "huffingtonpost.es": "HuffPost", "tododisca.com": "Tododisca",
}

# Solo interesa la prensa española. Un medio se acepta si su dirección acaba
# en .es, .cat, .eus o .gal, o si está en esta lista de medios españoles
# con otra terminación.
TERMINACIONES_ES = (".es", ".cat", ".eus", ".gal")
MEDIOS_ES_OTRA_TERMINACION = {
    "elpais.com", "lavanguardia.com", "elconfidencial.com", "elespanol.com",
    "okdiario.com", "elperiodico.com", "eldebate.com", "vozpopuli.com",
    "elindependiente.com", "theobjective.com", "elcorreo.com", "diariovasco.com",
    "levante-emv.com", "larioja.com", "elperiodicodearagon.com",
    "elperiodicoextremadura.com", "elperiodicomediterraneo.com", "marca.com",
    "as.com", "mundodeportivo.com", "sport.es", "libertaddigital.com",
    "periodistadigital.com", "elplural.com", "antena3.com", "lasexta.com",
    "cadenaser.com", "expansion.com", "lainformacion.com", "noticiasdenavarra.com",
    "segre.com", "diaridetarragona.com", "diariocordoba.com", "granadahoy.com",
    "eladelantado.com", "lavozdealmeria.com", "valenciaplaza.com",
    "alicanteplaza.es", "salamanca24horas.com", "leonoticias.com", "ileon.com",
    "elconfidencialdigital.com", "esdiario.com", "cronicaglobal.elespanol.com",
    "tododisca.com", "somospacientes.com", "plenainclusion.org", "cocemfe.es",
    "fundaciononce.es", "consalud.es", "redaccionmedica.com", "infosalus.com",
    "murcia.com", "elcierredigital.com", "diariosigloxxi.com", "lacerca.com",
    "gentedigital.es", "noticiasde.es", "telemadrid.es", "ccma.cat", "eitb.eus",
    "canalsur.es", "cope.es", "ondacero.es", "telecinco.es", "cuatro.com",
    "elmira.es", "eldiadecordoba.es", "elfarodeceuta.es", "elfarodemelilla.es",
    "diariodeavisos.elespanol.com", "atlanticohoy.com", "galiciapress.es",
    "elcorreogallego.es", "naiz.eus", "elcomerciodigital.com", "20minutos.com",
}

# Cuántas noticias se guardan como máximo de cada periodo.
MAXIMO_POR_PERIODO = {"hoy": 80, "semanas": 120, "mes": 120, "anio": 300}
# Cuántos titulares de cada periodo se le pasan a ChatGPT para el resumen.
PARA_RESUMEN = {"hoy": 60, "semanas": 70, "mes": 40}

GOOGLE = "https://news.google.com/rss/search?q={consulta}&hl=es&gl=ES&ceid=ES:es"
BING = "https://www.bing.com/news/search?q={consulta}&format=rss&cc=es&setlang=es"


# ----------------------------------------------------------------------
# FUNCIONES DE AYUDA
# ----------------------------------------------------------------------

def sin_tildes(texto: str) -> str:
    """'Síndrome de Down' → 'sindrome de down'."""
    normal = unicodedata.normalize("NFD", texto.lower())
    return "".join(letra for letra in normal if unicodedata.category(letra) != "Mn")


def dominio(url: str) -> str:
    """'https://www.elpais.com/sociedad/…' → 'elpais.com'."""
    nombre = urlparse(url).netloc.lower()
    return nombre[4:] if nombre.startswith("www.") else nombre


def es_medio_espanol(nombre_dominio: str) -> bool:
    if not nombre_dominio:
        return False
    if nombre_dominio.endswith(TERMINACIONES_ES):
        return True
    return any(
        nombre_dominio == medio or nombre_dominio.endswith("." + medio)
        for medio in MEDIOS_ES_OTRA_TERMINACION
    )


def habla_de_discapacidad(noticia: dict, solo_titular: bool = False) -> bool:
    texto = noticia["titulo"] if solo_titular else noticia["titulo"] + " " + noticia["entradilla"]
    return bool(PALABRAS_CLAVE.search(sin_tildes(texto)))


def es_institucion(medio: str) -> bool:
    return bool(INSTITUCIONES.search(sin_tildes(medio)))


def nombre_medio(nombre_dominio: str, nombre: str) -> str:
    """El nombre de NOMBRES si el medio está en la lista; si no, el que traiga."""
    return NOMBRES.get(nombre_dominio) or nombre or nombre_dominio


def clave_titulo(titulo: str) -> str:
    """Titular simplificado, para reconocer la misma noticia repetida."""
    return re.sub(r"[^a-z0-9]+", " ", sin_tildes(titulo)).strip()[:90]


def periodo(fecha: datetime, ahora: datetime) -> str | None:
    """A qué bloque de la web pertenece una noticia según su antigüedad.
    Es la misma regla que usa seccion_discapacidad.py."""
    dias = (ahora - fecha).total_seconds() / 86400
    if dias < -1 or dias > 365:
        return None                      # fecha imposible o demasiado antigua
    if dias <= 1:
        return "hoy"
    if dias <= 14:
        return "semanas"
    if dias <= 30:
        return "mes"
    return "anio"


def descargar(url: str):
    """Descarga un RSS y lo devuelve ya leído por feedparser."""
    respuesta = requests.get(url, headers=CABECERAS, timeout=15)
    respuesta.raise_for_status()
    return feedparser.parse(respuesta.content)


def fecha_de(entrada) -> datetime | None:
    """Fecha de publicación de una entrada de RSS (en hora universal, UTC)."""
    partes = entrada.get("published_parsed") or entrada.get("updated_parsed")
    if not partes:
        return None
    return datetime(*partes[:6], tzinfo=timezone.utc)


def noticia_de(entrada, medio: str, enlace: str | None = None, segura: bool = False) -> dict | None:
    """Convierte una entrada de RSS en nuestro diccionario de noticia.
    'segura' marca las de medios dedicados a la discapacidad (no se filtran)."""
    titulo = limpiar_html(entrada.get("title", ""))
    fecha = fecha_de(entrada)
    enlace = enlace or entrada.get("link", "")
    if not titulo or not fecha or not enlace:
        return None
    return {
        "titulo": titulo,
        "medio": medio,
        "enlace": enlace,
        "fecha": fecha.isoformat(timespec="minutes"),
        "entradilla": limpiar_html(entrada.get("summary", ""))[:240],
        "segura": segura,
    }


# ----------------------------------------------------------------------
# PASO 1 · BUSCAR NOTICIAS
# ----------------------------------------------------------------------

def consultas_google(hoy: datetime) -> list[str]:
    """La lista de búsquedas para Google Noticias.

    'when:1d' pide las últimas 24 horas; 'after:' y 'before:' piden un tramo
    de fechas. Así hay noticias de todos los periodos, no solo las recientes.
    """
    def tramo(dias_desde: int, dias_hasta: int) -> str:
        desde = (hoy - timedelta(days=dias_desde)).strftime("%Y-%m-%d")
        hasta = (hoy - timedelta(days=dias_hasta)).strftime("%Y-%m-%d")
        return f"after:{desde} before:{hasta}"

    consultas = []
    for busqueda in BUSQUEDAS:
        consultas.append(f"{busqueda} when:1d")
        consultas.append(f"{busqueda} when:7d")
        consultas.append(f"{busqueda} {tramo(15, 6)}")
        consultas.append(f"{busqueda} {tramo(31, 14)}")
    # Un tramo por cada mes del último año, con las dos búsquedas principales.
    for mes in range(1, 12):
        for busqueda in BUSQUEDAS[:2]:
            consultas.append(f"{busqueda} {tramo(30 * (mes + 1) + 1, 30 * mes)}")
    # Periódico a periódico, en grupos, en el último mes.
    for inicio in range(0, len(SITIOS), SITIOS_POR_GRUPO):
        grupo = " OR ".join(f"site:{sitio}" for sitio in SITIOS[inicio:inicio + SITIOS_POR_GRUPO])
        consultas.append(f"discapacidad ({grupo}) when:30d")
    return consultas


def buscar_en_google(hoy: datetime) -> list[dict]:
    noticias, fallos_seguidos = [], 0
    for consulta in consultas_google(hoy):
        try:
            feed = descargar(GOOGLE.format(consulta=quote_plus(consulta)))
            fallos_seguidos = 0
        except Exception as error:
            print(f"  Google: falló «{consulta}» ({error})")
            fallos_seguidos += 1
            if fallos_seguidos >= 3:
                print("  Google: tres fallos seguidos, se deja de intentar.")
                break
            continue

        for entrada in feed.entries:
            fuente = entrada.get("source", {})
            medio = fuente.get("title", "")
            web = dominio(fuente.get("href", ""))
            if not es_medio_espanol(web) or es_institucion(medio):
                continue
            noticia = noticia_de(
                entrada, nombre_medio(web, medio), segura=web in DOMINIOS_ESPECIALIZADOS
            )
            if noticia is None:
                continue
            # Google escribe "Titular - Medio": quitamos el final.
            if medio and noticia["titulo"].endswith(" - " + medio):
                noticia["titulo"] = noticia["titulo"][: -len(" - " + medio)]
            noticia["entradilla"] = ""      # la de Google solo repite el titular
            noticias.append(noticia)
        time.sleep(0.5)                     # sin prisas, para no molestar a Google
    print(f"  Google Noticias: {len(noticias)} noticias")
    return noticias


def buscar_en_bing() -> list[dict]:
    noticias = []
    for busqueda in BUSQUEDAS:
        try:
            feed = descargar(BING.format(consulta=quote_plus(busqueda)))
        except Exception as error:
            print(f"  Bing: falló «{busqueda}» ({error})")
            continue
        for entrada in feed.entries:
            # El enlace de Bing es una redirección; la dirección real va en "url=".
            enlace = entrada.get("link", "")
            real = parse_qs(urlparse(enlace).query).get("url", [enlace])[0]
            web = dominio(real)
            medio = entrada.get("news_source", "")
            if not es_medio_espanol(web) or es_institucion(medio):
                continue
            noticia = noticia_de(
                entrada, nombre_medio(web, medio), real, segura=web in DOMINIOS_ESPECIALIZADOS
            )
            if noticia:
                noticias.append(noticia)
    print(f"  Bing Noticias: {len(noticias)} noticias")
    return noticias


def leer_un_medio(medio: str, direcciones: list[str], todo: bool) -> tuple[list[dict], int]:
    """Lee los RSS de un medio. Devuelve (noticias, cuántos RSS han respondido).
    Con todo=False solo se queda con las que hablan de discapacidad."""
    noticias, respondieron = [], 0
    for url in direcciones:
        try:
            feed = descargar(url)
        except Exception:
            continue
        if not feed.entries:
            continue
        respondieron += 1
        for entrada in feed.entries:
            noticia = noticia_de(entrada, medio, segura=todo)
            if noticia and (todo or habla_de_discapacidad(noticia)):
                noticias.append(noticia)
    return noticias, respondieron


def buscar_en_rss() -> list[dict]:
    tareas = [(medio, urls, False) for medio, urls in RSS_PERIODICOS.items()]
    tareas += [(medio, urls, True) for medio, urls in RSS_ESPECIALIZADOS.items()]

    # ThreadPoolExecutor lee varios periódicos a la vez en lugar de uno a uno.
    with ThreadPoolExecutor(max_workers=10) as grupo:
        resultados = list(grupo.map(lambda tarea: leer_un_medio(*tarea), tareas))

    noticias, sin_respuesta = [], []
    for (medio, _, _), (encontradas, respondieron) in zip(tareas, resultados):
        noticias += encontradas
        if not respondieron:
            sin_respuesta.append(medio)
    print(f"  RSS de periódicos: {len(noticias)} noticias de {len(tareas)} medios")
    if sin_respuesta:
        print("  No han respondido: " + ", ".join(sin_respuesta))
    return noticias


# ----------------------------------------------------------------------
# PASO 2 · FILTRAR (CON AYUDA DE CHATGPT)
# ----------------------------------------------------------------------

class Seleccion(BaseModel):
    """Respuesta de ChatGPT al filtro: los números de los titulares válidos."""

    numeros: list[int] = Field(
        description="Números de los titulares que SÍ tratan sobre discapacidad."
    )


PROMPT_FILTRO = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Clasificas titulares de prensa española. Devuelve solo los números de "
            "los que tratan sobre discapacidad: personas con discapacidad física, "
            "intelectual, sensorial o psicosocial y sus familias, accesibilidad, "
            "dependencia, sus derechos, leyes, ayudas, empleo, educación, deporte "
            "adaptado o paralímpico, y las entidades del sector (ONCE, CERMI, Plena "
            "inclusión, Cocemfe, Aspace y similares).\n\n"
            "No incluyas sorteos ni cupones, ni noticias generales que no dejen ver "
            "en el titular su relación con la discapacidad. En caso de duda, no lo incluyas.",
        ),
        ("human", "{titulares}"),
    ]
)

TITULARES_POR_PREGUNTA = 80


def filtrar_con_ia(dudosas: list[dict], nombre_modelo: str) -> list[dict]:
    """Pregunta a ChatGPT cuáles de las noticias dudosas van de discapacidad."""
    modelo = ChatOpenAI(api_key=leer_secreto("OPENAI_API_KEY"), model=nombre_modelo)
    cadena = PROMPT_FILTRO | modelo.with_structured_output(Seleccion)

    # Se pregunta por tandas de 80 titulares, numerados desde el 1.
    tandas = [
        dudosas[inicio:inicio + TITULARES_POR_PREGUNTA]
        for inicio in range(0, len(dudosas), TITULARES_POR_PREGUNTA)
    ]
    respuestas = cadena.batch(
        [
            {
                "titulares": "\n".join(
                    f"{numero}. {noticia['titulo']}"
                    + (f" — {noticia['entradilla']}" if noticia["entradilla"] else "")
                    for numero, noticia in enumerate(tanda, start=1)
                )
            }
            for tanda in tandas
        ]
    )
    aceptadas = []
    for tanda, respuesta in zip(tandas, respuestas):
        aceptadas += [tanda[n - 1] for n in set(respuesta.numeros) if 1 <= n <= len(tanda)]
    return aceptadas


def filtrar(nuevas: list[dict], anterior: list[dict], nombre_modelo: str | None) -> list[dict]:
    """Se queda con las noticias nuevas que hablan de discapacidad.

    - Las de medios especializados y las que llevan una palabra clave en el
      titular se aceptan directamente.
    - Las demás son "dudosas": decide ChatGPT. Las que descarta se apuntan en
      descartadas.json para no preguntarle otra vez por ellas.
    """
    ya_guardadas = {clave_titulo(noticia["titulo"]) for noticia in anterior}
    descartadas = leer_json(ARCHIVO_DESCARTADAS, [])
    ya_descartadas = set(descartadas)

    aceptadas, dudosas, vistas = [], [], set()
    for noticia in nuevas:
        clave = clave_titulo(noticia["titulo"])
        if not clave or clave in vistas or clave in ya_descartadas:
            continue
        if SORTEOS.search(sin_tildes(noticia["titulo"])):
            continue
        vistas.add(clave)
        if noticia["segura"] or clave in ya_guardadas or habla_de_discapacidad(noticia, True):
            aceptadas.append(noticia)
        else:
            dudosas.append(noticia)

    print(f"  Filtro: {len(aceptadas)} claras y {len(dudosas)} dudosas")
    if dudosas and nombre_modelo:
        try:
            rescatadas = filtrar_con_ia(dudosas, nombre_modelo)
            claves_rescatadas = {clave_titulo(noticia["titulo"]) for noticia in rescatadas}
            descartadas += [
                clave
                for clave in (clave_titulo(noticia["titulo"]) for noticia in dudosas)
                if clave not in claves_rescatadas
            ]
            guardar_json(ARCHIVO_DESCARTADAS, descartadas[-MAX_DESCARTADAS:])
            print(f"  Filtro: ChatGPT rescata {len(rescatadas)} de las dudosas")
            aceptadas += rescatadas
        except Exception as error:
            # Sin ChatGPT nos quedamos solo con las claras.
            print(f"  Filtro: ChatGPT no ha respondido ({error}); se descartan las dudosas")
    return aceptadas


# ----------------------------------------------------------------------
# PASO 3 · JUNTAR, QUITAR REPETIDAS Y RECORTAR
# ----------------------------------------------------------------------

def juntar(noticias: list[dict], ahora: datetime) -> list[dict]:
    """Deja una sola vez cada noticia, de la más nueva a la más antigua,
    sin las de hace más de un año y con un máximo por periodo."""
    noticias = sorted(noticias, key=lambda noticia: noticia["fecha"], reverse=True)

    vistas, cuenta, resultado = set(), {}, []
    nombres = {}        # "ideal" → "Ideal": el mismo medio, escrito siempre igual
    for noticia in noticias:
        bloque = periodo(datetime.fromisoformat(noticia["fecha"]), ahora)
        clave = clave_titulo(noticia["titulo"])
        if bloque is None or not clave or clave in vistas:
            continue
        if cuenta.get(bloque, 0) >= MAXIMO_POR_PERIODO[bloque]:
            continue
        vistas.add(clave)
        cuenta[bloque] = cuenta.get(bloque, 0) + 1
        # "segura" solo servía para el filtro: no se guarda.
        noticia = {k: v for k, v in noticia.items() if k != "segura"}
        noticia["medio"] = nombres.setdefault(sin_tildes(noticia["medio"]), noticia["medio"])
        resultado.append(noticia)
    return resultado


# ----------------------------------------------------------------------
# PASO 4 · RESUMEN CON LANGCHAIN + CHATGPT
# ----------------------------------------------------------------------

class Tema(BaseModel):
    titulo: str = Field(description="Nombre del tema en 3 a 6 palabras.")
    explicacion: str = Field(
        description="Una o dos frases que expliquen qué se está contando sobre ese tema."
    )


class ResumenDiscapacidad(BaseModel):
    """Lo que le pedimos a ChatGPT, con forma fija."""

    resumen: str = Field(
        description="Entre 110 y 160 palabras, en dos párrafos separados por un salto "
        "de línea, que expliquen de qué se está hablando sobre discapacidad en España: "
        "primero lo más reciente y después el contexto de las últimas semanas y del mes."
    )
    temas: list[Tema] = Field(
        description="Los 4 a 6 temas que más se repiten, del más al menos presente."
    )


PROMPT_RESUMEN = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "Eres un periodista especializado en discapacidad que hace un repaso de "
            "prensa en España. Escribes en español, claro y sencillo, de forma neutral "
            "y sin opinar de política.\n\n"
            "Reglas: usa solo los titulares que se te dan; no inventes datos, cifras "
            "ni citas; si un tema aparece en un solo titular, no lo presentes como "
            "tendencia; no comentes cuántos titulares hay ni de qué fechas son. "
            "Usa un lenguaje respetuoso: di «personas con discapacidad», "
            "no «discapacitados» ni «minusválidos», y evita el tono de lástima o de "
            "heroísmo.",
        ),
        (
            "human",
            "Hoy es {hoy}. Estos son titulares sobre discapacidad publicados en medios "
            "españoles en el último mes, con su fecha y su medio, agrupados por "
            "antigüedad:\n\n{titulares}\n\n"
            "Resume de qué se está hablando sobre discapacidad en España y señala "
            "los temas que más se repiten.",
        ),
    ]
)


def muestra(noticias: list[dict], cuantas: int) -> list[dict]:
    """Elige 'cuantas' noticias repartidas por toda la lista (no solo las primeras)."""
    if len(noticias) <= cuantas:
        return noticias
    paso = len(noticias) / cuantas
    return [noticias[int(posicion * paso)] for posicion in range(cuantas)]


def resumir(noticias: list[dict], ahora: datetime, nombre_modelo: str) -> dict:
    nombres = {"hoy": "ÚLTIMAS 24 HORAS", "semanas": "ÚLTIMAS DOS SEMANAS", "mes": "ÚLTIMO MES"}
    partes = []
    for bloque, cuantas in PARA_RESUMEN.items():
        del_bloque = [
            noticia
            for noticia in noticias
            if periodo(datetime.fromisoformat(noticia["fecha"]), ahora) == bloque
        ]
        if del_bloque:
            lineas = "\n".join(
                f"- [{datetime.fromisoformat(n['fecha']).astimezone(MADRID):%d/%m}] "
                f"{n['titulo']} ({n['medio']})"
                for n in muestra(del_bloque, cuantas)
            )
            partes.append(f"## {nombres[bloque]}\n{lineas}")
    if not partes:
        raise RuntimeError("no hay noticias del último mes que resumir")
    titulares = "\n\n".join(partes)

    modelo = ChatOpenAI(api_key=leer_secreto("OPENAI_API_KEY"), model=nombre_modelo)
    cadena = PROMPT_RESUMEN | modelo.with_structured_output(ResumenDiscapacidad)
    resultado = cadena.invoke({"hoy": f"{ahora:%d/%m/%Y}", "titulares": titulares})
    return resultado.model_dump()


# ----------------------------------------------------------------------
# PASO 5 · GUARDAR
# ----------------------------------------------------------------------

def main() -> None:
    ahora = datetime.now(MADRID)
    turno = turno_actual(ahora)
    forzar = os.environ.get("FORZAR") == "1"
    if forzar and turno is None:
        turno = 0
    if turno is None:
        print("Todavía no son las 8:00 en Madrid: no toca actualizar.")
        return

    fecha = ahora.strftime("%Y-%m-%d")
    anterior = leer_json(ARCHIVO, {})
    if anterior.get("fecha") == fecha and anterior.get("turno") == turno and not forzar:
        print(f"Discapacidad: la actualización de las {turno}:00 ya está hecha.")
        return

    # Sin las claves de OpenAI se guardan las noticias claras, sin filtro de IA ni resumen nuevo.
    try:
        nombre_modelo = leer_secreto("OPENAI_MODEL")
    except KeyError:
        nombre_modelo = None

    print("Discapacidad: buscando noticias…")
    encontradas = buscar_en_google(ahora) + buscar_en_bing() + buscar_en_rss()
    if not encontradas:
        sys.exit("Discapacidad: ninguna fuente ha dado noticias: no se guarda nada.")

    guardadas = anterior.get("noticias", [])
    nuevas = filtrar(encontradas, guardadas, nombre_modelo)

    # Las nuevas van delante: si una noticia ya estaba, se queda la versión nueva.
    noticias = juntar(nuevas + guardadas, ahora)
    if not noticias:
        sys.exit("Discapacidad: no ha quedado ninguna noticia: no se guarda nada.")
    medios = sorted({noticia["medio"] for noticia in noticias}, key=sin_tildes)
    print(f"Discapacidad: {len(noticias)} noticias de {len(medios)} medios.")

    # Si el resumen falla, se guardan igualmente las noticias con el resumen anterior.
    resumen, modelo, error_resumen = anterior.get("resumen"), anterior.get("modelo", ""), None
    try:
        if nombre_modelo is None:
            raise RuntimeError("falta el Secret OPENAI_MODEL")
        print(f"Discapacidad: resumiendo con {nombre_modelo}…")
        resumen, modelo = resumir(noticias, ahora, nombre_modelo), nombre_modelo
    except Exception as error:
        error_resumen = error

    guardar_json(
        ARCHIVO,
        {
            "fecha": fecha,
            "turno": turno,
            "generado": ahora.strftime("%d/%m/%Y %H:%M"),
            "modelo": modelo,
            "resumen": resumen,
            "medios": medios,
            "noticias": noticias,
        },
    )
    print("Discapacidad: guardado.")
    if error_resumen:
        sys.exit(f"Discapacidad: no se ha podido hacer el resumen ({error_resumen}).")


if __name__ == "__main__":
    main()
