"""Publica cada día en Bluesky un resumen de las portadas, a horas aleatorias.

Cómo funciona:
- El workflow `difundir.yml` se ejecuta cada 30 minutos.
- La primera vez que se ejecuta cada día, este script sortea la hora (o las horas)
  de publicación de ese día y las guarda en `difusion/plan.json`.
- En las ejecuciones siguientes comprueba si ya ha llegado la hora sorteada y, si
  es así y aún no se ha publicado, publica.

Variables de entorno:
- BLUESKY_USUARIO         usuario completo, por ejemplo portadas-ia.bsky.social
- BLUESKY_CLAVE_APP       contraseña de aplicación (NO la contraseña de la cuenta)
- POSTS_AL_DIA            cuántas publicaciones al día (por defecto 1)
- PRUEBA=1                no publica: solo enseña el texto que publicaría
- AHORA=1                 publica ya, sin esperar a la hora sorteada
"""

import json
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

RAIZ = Path(__file__).parent
PLAN = RAIZ / "difusion" / "plan.json"
ZONA = ZoneInfo("Europe/Madrid")
URL_BASE = "https://portadas-ia.com"
SERVIDOR = "https://bsky.social"

# Horas (Madrid) entre las que se sortea la publicación.
HORA_MIN, HORA_MAX = 9, 22

# País → carpeta de la web (igual que en web/generar.py).
CARPETAS = {
    "es": "", "fr": "francia", "us": "estados-unidos", "gb": "reino-unido",
    "de": "alemania", "it": "italia", "ru": "rusia", "cn": "china",
    "br": "brasil", "eg": "egipto",
}

# Frases de apertura para que no todos los días suene igual.
APERTURAS = [
    "📰 Portadas de {pais} hoy: crispación {nota}/100.",
    "Así amanece la prensa de {pais}: crispación {nota}/100.",
    "{pais}: la IA lee las portadas y puntúa la crispación en {nota}/100.",
    "Lo más repetido en las portadas de {pais} (crispación {nota}/100):",
]

MAX_CARACTERES = 300  # límite de Bluesky


def hoy_y_ahora():
    ahora = datetime.now(ZONA)
    return ahora.strftime("%Y-%m-%d"), ahora


def cargar_plan():
    if PLAN.exists():
        return json.loads(PLAN.read_text(encoding="utf-8"))
    return {}


def guardar_plan(plan):
    PLAN.parent.mkdir(exist_ok=True)
    PLAN.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")


def sortear_horas(cuantas):
    """Devuelve `cuantas` horas "HH:MM" al azar, separadas al menos 2 horas."""
    for _ in range(200):
        minutos = sorted(random.randint(HORA_MIN * 60, HORA_MAX * 60) for _ in range(cuantas))
        if all(b - a >= 120 for a, b in zip(minutos, minutos[1:])):
            return [f"{m // 60:02d}:{m % 60:02d}" for m in minutos]
    paso = (HORA_MAX - HORA_MIN) * 60 // cuantas
    return [f"{(HORA_MIN * 60 + i * paso) // 60:02d}:{(HORA_MIN * 60 + i * paso) % 60:02d}" for i in range(cuantas)]


def elegir_pais(fecha, usados):
    """Elige al azar un país con datos de hoy que no se haya usado ya hoy."""
    candidatos = []
    for codigo in CARPETAS:
        ruta = RAIZ / "datos" / codigo / "ultimo.json"
        if not ruta.exists():
            continue
        datos = json.loads(ruta.read_text(encoding="utf-8"))
        if datos.get("fecha") == fecha and codigo not in usados:
            candidatos.append((codigo, datos))
    if not candidatos:
        return None, None
    return random.choice(candidatos)


def recortar(texto, maximo):
    if len(texto) <= maximo:
        return texto
    corte = texto[: maximo - 1].rsplit(" ", 1)[0].rstrip(" ,.;:")
    return corte + "…"


def componer(codigo, datos):
    """Devuelve (texto, enlace). El texto no incluye el enlace; se añade al final."""
    pais = datos["pais"]
    general = datos.get("general", {})
    nota = general.get("crispacion", "?")
    temas = (general.get("temas") or "").strip()
    carpeta = CARPETAS[codigo]
    enlace = f"{URL_BASE}/{carpeta + '/' if carpeta else ''}?utm_source=bluesky"
    apertura = random.choice(APERTURAS).format(pais=pais, nota=nota)
    # Hueco para el enlace (se enseña acortado) + saltos de línea.
    texto_enlace = enlace.replace("https://", "")
    reservado = len(apertura) + len(texto_enlace) + 4
    cuerpo = recortar(temas, MAX_CARACTERES - reservado)
    texto = f"{apertura}\n{cuerpo}\n\n{texto_enlace}"
    return texto, enlace, texto_enlace


def publicar_bluesky(texto, enlace, texto_enlace):
    usuario = os.environ["BLUESKY_USUARIO"].strip()
    clave = os.environ["BLUESKY_CLAVE_APP"].strip()
    sesion = requests.post(
        f"{SERVIDOR}/xrpc/com.atproto.server.createSession",
        json={"identifier": usuario, "password": clave}, timeout=30,
    )
    sesion.raise_for_status()
    sesion = sesion.json()

    # El enlace solo es pinchable si se marca con un "facet" (posiciones en bytes).
    bytes_texto = texto.encode("utf-8")
    inicio = bytes_texto.rfind(texto_enlace.encode("utf-8"))
    facetas = [{
        "index": {"byteStart": inicio, "byteEnd": inicio + len(texto_enlace.encode("utf-8"))},
        "features": [{"$type": "app.bsky.richtext.facet#link", "uri": enlace}],
    }]
    registro = {
        "$type": "app.bsky.feed.post",
        "text": texto,
        "facets": facetas,
        "langs": ["es"],
        "createdAt": datetime.now(ZoneInfo("UTC")).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
    }
    r = requests.post(
        f"{SERVIDOR}/xrpc/com.atproto.repo.createRecord",
        headers={"Authorization": f"Bearer {sesion['accessJwt']}"},
        json={"repo": sesion["did"], "collection": "app.bsky.feed.post", "record": registro},
        timeout=30,
    )
    r.raise_for_status()
    return r.json().get("uri", "")


def main():
    fecha, ahora = hoy_y_ahora()
    prueba = os.environ.get("PRUEBA") == "1"
    ya = os.environ.get("AHORA") == "1"
    por_dia = int(os.environ.get("POSTS_AL_DIA") or 1)

    if not prueba and not (os.environ.get("BLUESKY_USUARIO", "").strip() and os.environ.get("BLUESKY_CLAVE_APP", "").strip()):
        print("Faltan los Secrets BLUESKY_USUARIO y BLUESKY_CLAVE_APP en GitHub. No se publica.")
        return

    plan = cargar_plan()
    if plan.get("fecha") != fecha:
        plan = {"fecha": fecha, "horas": sortear_horas(por_dia), "hechas": [], "paises": []}
        guardar_plan(plan)
        print(f"Plan de hoy: {plan['horas']}")

    pendientes = [h for h in plan["horas"] if h not in plan["hechas"]]
    toca = [h for h in pendientes if ahora.strftime("%H:%M") >= h]
    if ya and pendientes:
        toca = pendientes[:1]
    if not toca:
        print(f"Aún no toca (hora {ahora:%H:%M}; plan {plan['horas']}; hechas {plan['hechas']}).")
        return

    codigo, datos = elegir_pais(fecha, plan["paises"])
    if not datos:
        print("Todavía no hay datos de hoy para publicar. Se reintentará en la próxima ejecución.")
        return

    texto, enlace, texto_enlace = componer(codigo, datos)
    print("----- Texto -----")
    print(texto)
    print(f"----- {len(texto)} caracteres -----")
    if prueba:
        print("PRUEBA=1: no se publica.")
        return

    uri = publicar_bluesky(texto, enlace, texto_enlace)
    print(f"Publicado: {uri}")
    plan["hechas"].append(toca[0])
    plan["paises"].append(codigo)
    guardar_plan(plan)


if __name__ == "__main__":
    try:
        main()
    except requests.HTTPError as error:
        print(f"Error de Bluesky: {error.response.status_code} {error.response.text[:300]}")
        sys.exit(1)
