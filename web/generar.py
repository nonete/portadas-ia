"""
Portadas IA · la web estática
-----------------------------
Este programa NO es Streamlit. Lee los mismos datos que app.py
(datos/<país>/ultimo.json e historial.json) y escribe páginas HTML normales
en la carpeta web/sitio/:

    web/sitio/index.html            → España
    web/sitio/francia/index.html    → Francia (y así cada país de PAISES)
    web/sitio/estilos.css, web.js   → el diseño y un poco de JavaScript
    web/sitio/img/                  → Crispito y las caricaturas
    web/sitio/404.html, sitemap.xml, robots.txt

La publicación en Cloudflare la hace .github/workflows/publicar-web.yml
usando web/wrangler.jsonc.

Al ser HTML "de verdad", Google puede leer todo el texto, y la carpeta
web/sitio/ se puede subir tal cual a cualquier hosting de páginas estáticas.

Cómo se usa (no necesita instalar nada, solo Python):

    python web/generar.py                  # crea web/sitio/
    python web/generar.py --vista-previa   # igual, pero los enlaces entre
                                           # países acaban en index.html para
                                           # poder abrir los archivos sin servidor

El diseño está en web/recursos/estilos.css y el JavaScript en
web/recursos/web.js. Este archivo solo construye el HTML.
"""

import json
import math
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

# ----------------------------------------------------------------------
# CONFIGURACIÓN
# ----------------------------------------------------------------------

RAIZ = Path(__file__).parent.parent          # la carpeta del repositorio
DATOS = RAIZ / "datos"
RECURSOS = Path(__file__).parent / "recursos"
SITIO = Path(__file__).parent / "sitio"      # aquí se escribe la web

# Dirección pública de la web, SIN barra al final. Con ella se escriben la
# dirección canónica de cada página, sitemap.xml y robots.txt.
# Si se deja vacía ("") esas tres cosas no se generan.
URL_BASE = "https://portadas-ia.com"

# Los países. 'carpeta' es dónde se guarda su página dentro de web/sitio/
# ("" = la portada). La clave tiene que coincidir con la carpeta de datos/.
def estrella(cx: float, cy: float, radio: float) -> str:
    """Los puntos de una estrella de cinco puntas, para las banderas."""
    puntos = []
    for paso in range(10):
        r = radio if paso % 2 == 0 else radio * 0.382      # punta, hueco, punta…
        angulo = math.radians(-90 + paso * 36)
        puntos.append(f"{cx + r * math.cos(angulo):.3f},{cy + r * math.sin(angulo):.3f}")
    return f'<polygon points="{" ".join(puntos)}"/>'


def franjas(colores: list, vertical: bool = False) -> str:
    """Una bandera de franjas iguales, horizontales o verticales."""
    trozo = (3 if vertical else 2) / len(colores)
    dibujo = ""
    for posicion, color in enumerate(colores):
        if vertical:
            dibujo += f'<rect x="{posicion * trozo:.3f}" width="{trozo:.3f}" height="2" fill="{color}"/>'
        else:
            dibujo += f'<rect y="{posicion * trozo:.3f}" width="3" height="{trozo:.3f}" fill="{color}"/>'
    return dibujo


# Los países. La clave tiene que coincidir con la carpeta de datos/.
#   carpeta → dónde se guarda su página dentro de web/sitio/ ("" = la portada)
#   idioma  → idioma de los titulares originales ("" si hay varios mezclados)
#   bandera → dibujo SVG sobre un lienzo de 3 x 2. Se dibujan así, y no con
#             emojis, porque Windows no enseña los emojis de banderas.
PAISES = {
    "es": {
        "nombre": "España", "carpeta": "", "idioma": "es",
        "bandera": '<rect width="3" height="2" fill="#c60b1e"/><rect y="0.5" width="3" height="1" fill="#ffc400"/>',
    },
    "fr": {
        "nombre": "Francia", "carpeta": "francia", "idioma": "fr",
        "bandera": franjas(["#0055a4", "#ffffff", "#ef4135"], vertical=True),
    },
    "us": {
        "nombre": "Estados Unidos", "carpeta": "estados-unidos", "idioma": "en",
        # 13 franjas, el cuadro azul y unas cuantas estrellas (no caben las 50).
        "bandera": franjas(["#b22234", "#ffffff"] * 6 + ["#b22234"])
        + '<rect width="1.3" height="1.077" fill="#3c3b6e"/><g fill="#ffffff">'
        + "".join(estrella(0.22 + 0.29 * columna, 0.2 + 0.23 * fila, 0.075)
                  for fila in range(4) for columna in range(4))
        + "</g>",
    },
    "gb": {
        "nombre": "Reino Unido", "carpeta": "reino-unido", "idioma": "en",
        "bandera": '<rect width="3" height="2" fill="#012169"/>'
        '<path d="M0,0 L3,2 M3,0 L0,2" stroke="#ffffff" stroke-width="0.4"/>'
        '<path d="M0,0 L3,2 M3,0 L0,2" stroke="#c8102e" stroke-width="0.14"/>'
        '<path d="M1.5,0 V2 M0,1 H3" stroke="#ffffff" stroke-width="0.66"/>'
        '<path d="M1.5,0 V2 M0,1 H3" stroke="#c8102e" stroke-width="0.4"/>',
    },
    "de": {
        "nombre": "Alemania", "carpeta": "alemania", "idioma": "de",
        "bandera": franjas(["#000000", "#dd0000", "#ffce00"]),
    },
    "it": {
        "nombre": "Italia", "carpeta": "italia", "idioma": "it",
        "bandera": franjas(["#009246", "#ffffff", "#ce2b37"], vertical=True),
    },
    "ru": {
        "nombre": "Rusia", "carpeta": "rusia", "idioma": "ru",
        "bandera": franjas(["#ffffff", "#0039a6", "#d52b1e"]),
    },
    "cn": {
        "nombre": "China", "carpeta": "china", "idioma": "",      # chino e inglés
        "bandera": '<rect width="3" height="2" fill="#de2910"/><g fill="#ffde00">'
        + estrella(0.55, 0.55, 0.32)
        + "".join(estrella(x, y, 0.11) for x, y in [(1.05, 0.2), (1.28, 0.42), (1.28, 0.75), (1.05, 0.97)])
        + "</g>",
    },
}

HORAS = [8, 11, 14, 17, 20]                  # las mismas que en actualizar.py
ESTADOS_CRISPITO = ["Zen", "Tranquilo", "Mosqueado", "Molesto", "Enfadado", "¡A punto de estallar!"]
DIAS_GRAFICO = 30                            # días que caben en el gráfico

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

# Con --vista-previa los enlaces entre páginas acaban en "index.html".
VISTA_PREVIA = "--vista-previa" in sys.argv


# ----------------------------------------------------------------------
# FUNCIONES DE AYUDA
# ----------------------------------------------------------------------

def leer_json(pais: str, nombre: str, por_defecto):
    """Lee un archivo de datos/<país>/; si no existe devuelve el valor por defecto."""
    archivo = DATOS / pais / nombre
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    return por_defecto


def a_numero(valor) -> int:
    """Asegura que una nota es un entero entre 0 y 100."""
    return max(0, min(100, int(valor)))


def nivel(valor: int) -> str:
    """'bajo', 'medio' o 'alto'. Se usa como texto y como clase de CSS."""
    if valor < 34:
        return "bajo"
    if valor < 67:
        return "medio"
    return "alto"


def fecha_larga(fecha: datetime) -> str:
    """miércoles, 11 de noviembre de 2026"""
    return f"{DIAS[fecha.weekday()]}, {fecha.day} de {MESES[fecha.month - 1]} de {fecha.year}"


def recortar(texto: str, largo: int) -> str:
    """Corta un texto por una palabra entera, para la descripción de Google."""
    if len(texto) <= largo:
        return texto
    return texto[:largo].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def prefijo(codigo: str) -> str:
    """Camino desde la página de un país hasta la raíz de la web ('' o '../')."""
    return "../" if PAISES[codigo]["carpeta"] else ""


def enlace_pais(destino: str, desde: str) -> str:
    """Enlace a la página de otro país, escrito desde la página 'desde'."""
    carpeta = PAISES[destino]["carpeta"]
    camino = prefijo(desde) + (carpeta + "/" if carpeta else "")
    if VISTA_PREVIA:
        return camino + "index.html"
    return camino or "./"


def direccion_publica(codigo: str) -> str:
    """Dirección completa de la página de un país (solo si hay URL_BASE)."""
    carpeta = PAISES[codigo]["carpeta"]
    return URL_BASE + "/" + (carpeta + "/" if carpeta else "")


def medidor(valor: int, texto: str, fino: bool = False) -> str:
    """Barra de 0 a 100. El color sale de la clase nivel-bajo/medio/alto."""
    clase = "medidor fino" if fino else "medidor"
    return (
        f'<div class="{clase} nivel-{nivel(valor)}" role="meter" aria-valuemin="0" '
        f'aria-valuemax="100" aria-valuenow="{valor}" aria-label="{escape(texto)}">'
        f'<span style="width:{valor}%"></span></div>'
    )


def pastilla(valor: int) -> str:
    """Etiqueta 'Bajo', 'Medio' o 'Alto' con su punto de color."""
    return f'<span class="pastilla nivel-{nivel(valor)}">{nivel(valor).capitalize()}</span>'


def parrafos(texto: str) -> str:
    """Convierte un texto con saltos de línea en párrafos <p>."""
    return "".join(f"<p>{escape(linea.strip())}</p>" for linea in texto.split("\n") if linea.strip())


def lista_resumen(texto: str) -> str:
    """El resumen de ChatGPT viene como líneas que empiezan por '- '."""
    puntos = [linea.strip().lstrip("-•* ").strip() for linea in texto.split("\n") if linea.strip()]
    return "<ul>" + "".join(f"<li>{escape(punto)}</li>" for punto in puntos) + "</ul>"


# ----------------------------------------------------------------------
# LOS TROZOS DE LA PÁGINA
# ----------------------------------------------------------------------

def bloque_crispacion(codigo: str, ultimo: dict, historial: list) -> str:
    """La portada: titular, Crispito con la nota y los temas del día."""
    pais = PAISES[codigo]["nombre"]
    general = ultimo["general"]
    nota = a_numero(general["crispacion"])
    estado = min(5, nota * 6 // 100)         # 6 estados de Crispito, de 0 a 5
    raiz = prefijo(codigo)

    # Comparación con la media del día anterior, si lo hay.
    anteriores = [dia for dia in historial if dia["fecha"] < ultimo["fecha"]]
    cambio = ""
    if anteriores:
        diferencia = nota - a_numero(anteriores[-1]["crispacion"])
        if diferencia > 0:
            cambio = f"▲ {diferencia} puntos más que el día anterior"
        elif diferencia < 0:
            cambio = f"▼ {-diferencia} puntos menos que el día anterior"
        else:
            cambio = "Igual que el día anterior"
        cambio = f'<p class="cambio">{cambio}</p>'

    nombres = [periodico["nombre"] for periodico in ultimo["periodicos"]]
    cabeceras = ", ".join(nombres[:-1]) + f" y {nombres[-1]}"
    momento = datetime.strptime(ultimo["generado"], "%d/%m/%Y %H:%M")

    return f"""
<section class="portada" id="crispacion" aria-labelledby="titulo-portada">
  <div class="portada-texto">
    <p class="antetitulo">Edición {escape(pais)}</p>
    <h1 id="titulo-portada">El día en cinco portadas</h1>
    <p class="entrada">Una IA lee las portadas de {escape(cabeceras)}, las resume,
    mide su populismo y su sesgo y toma el pulso a la crispación.</p>

    <h2 class="rotulo">Lo más repetido hoy</h2>
    <p class="temas">{escape(general["temas"])}</p>

    <dl class="ficha">
      <div><dt>Actualizado</dt>
        <dd><time datetime="{momento.isoformat()}">{escape(ultimo["generado"])}</time></dd></div>
      <div><dt>Próxima lectura</dt>
        <dd id="proxima">A las {", ".join(f"{hora}:00" for hora in HORAS[:-1])} y {HORAS[-1]}:00</dd></div>
      <div><dt>Modelo</dt><dd>{escape(ultimo["modelo"])}</dd></div>
    </dl>
  </div>

  <aside class="termometro" aria-labelledby="titulo-termometro">
    <h2 class="rotulo" id="titulo-termometro">Crispación ahora</h2>
    <div class="termometro-dato">
      <img src="{raiz}img/crispito_{estado}.gif" width="120" height="120"
           alt="Crispito, la mascota, en estado {escape(ESTADOS_CRISPITO[estado])}">
      <div>
        <p class="cifra"><b>{nota}</b><span>/ 100</span></p>
        {pastilla(nota)}
        {cambio}
      </div>
    </div>
    {medidor(nota, "Crispación")}
    <p class="escala" aria-hidden="true"><span>0 · calma</span><span>100 · tensión máxima</span></p>
    <p class="estado">Crispito está <b>{escape(ESTADOS_CRISPITO[estado])}</b> · estado {estado} de 5</p>
    <p class="motivo">{escape(general["motivo_crispacion"])}</p>
    <details>
      <summary>Conoce a Crispito y sus 6 estados</summary>
      <img src="{raiz}img/estados.png" width="720" height="480" loading="lazy"
           alt="Los seis estados de Crispito: {escape(", ".join(ESTADOS_CRISPITO))}">
    </details>
  </aside>
</section>"""


def bloque_populismo(ultimo: dict) -> str:
    """Ranking de populismo: los periódicos ordenados de más a menos."""
    filas = []
    con_nota = [p for p in ultimo["periodicos"] if p.get("analisis")]
    for periodico in sorted(con_nota, key=lambda p: -a_numero(p["analisis"]["populismo"])):
        nota = a_numero(periodico["analisis"]["populismo"])
        filas.append(
            f'<li><span class="nombre">{escape(periodico["nombre"])}</span>'
            f'{medidor(nota, "Populismo de " + periodico["nombre"])}'
            f'<span class="valor">{nota}</span>{pastilla(nota)}</li>'
        )
    if not filas:
        return ""
    return f"""
<section id="populismo" aria-labelledby="titulo-populismo">
  <header class="cabecera-seccion">
    <h2 id="titulo-populismo">Populismo, portada a portada</h2>
    <p>De 0 a 100. Sube con el lenguaje alarmista, el «nosotros contra ellos»
    y las descalificaciones. La IA puntúa sin saber de qué periódico es cada portada.</p>
  </header>
  <ol class="ranking">{"".join(filas)}</ol>
</section>"""


def bloque_periodicos(codigo: str, ultimo: dict) -> str:
    """Una ficha por periódico: resumen, populismo, sesgo y titulares."""
    fichas = []
    # lang="…" le dice al navegador en qué idioma están los titulares originales.
    idioma = f' lang="{PAISES[codigo]["idioma"]}"' if PAISES[codigo]["idioma"] else ""
    for periodico in ultimo["periodicos"]:
        nombre = escape(periodico["nombre"])
        web = escape(periodico["web"])
        analisis = periodico.get("analisis")
        noticias = periodico.get("noticias") or []

        if not analisis or not noticias:
            fichas.append(
                f'<article class="periodico"><h3>{nombre}</h3>'
                f'<p class="aviso">Hoy no se ha podido leer esta portada. '
                f'<a href="{web}" rel="noopener">Abrir {nombre}</a></p></article>'
            )
            continue

        nota = a_numero(analisis["populismo"])
        titulares = ""
        for noticia in noticias:
            titulo = escape(noticia["titulo"])
            if noticia.get("enlace"):
                titulo = f'<a href="{escape(noticia["enlace"])}" rel="noopener">{titulo}</a>'
            titulares += f"<li>{titulo}</li>"

        fichas.append(f"""
<article class="periodico">
  <header>
    <h3>{nombre}</h3>
    <a class="fuente" href="{web}" rel="noopener">{web.split("//")[-1].removeprefix("www.")}</a>
  </header>
  {lista_resumen(analisis["resumen"])}
  <div class="populismo">
    <p class="linea"><span>Populismo</span><b>{nota}</b>{pastilla(nota)}</p>
    {medidor(nota, "Populismo de " + periodico["nombre"], fino=True)}
    <p class="nota">{escape(analisis["motivo_populismo"])}</p>
  </div>
  <p class="sesgo"><b>Sesgo.</b> {escape(analisis["sesgo"])}</p>
  <details>
    <summary>Ver los {len(noticias)} titulares originales</summary>
    <ol{idioma}>{titulares}</ol>
  </details>
</article>""")

    return f"""
<section id="periodicos" aria-labelledby="titulo-periodicos">
  <header class="cabecera-seccion">
    <h2 id="titulo-periodicos">Periódico a periódico</h2>
    <p>Qué cuenta cada portada y cómo lo cuenta.</p>
  </header>
  <div class="rejilla-periodicos">{"".join(fichas)}</div>
</section>"""


def bloque_opiniones(codigo: str, ultimo: dict) -> str:
    """Las cinco opiniones. Sin JavaScript se ven todas; con él, por pestañas."""
    opiniones = ultimo.get("opiniones") or []
    if not opiniones:
        return ""
    raiz = prefijo(codigo)
    pestanas, paneles = "", ""
    for opinion in opiniones:
        ident = escape(opinion["id"])
        nombre = escape(opinion["nombre"])
        imagen = f'<img src="{raiz}img/{ident}.png" width="72" height="72" alt="">'
        pestanas += (
            f'<button type="button" role="tab" id="pestana-{ident}" '
            f'aria-controls="panel-{ident}" aria-selected="false">{imagen}<span>{nombre}</span></button>'
        )
        paneles += (
            f'<article class="opinion" role="tabpanel" id="panel-{ident}" '
            f'aria-labelledby="pestana-{ident}">'
            f'<header>{imagen}<h3>{nombre} opina</h3></header>'
            f'{parrafos(opinion["texto"])}</article>'
        )
    return f"""
<section id="opiniones" aria-labelledby="titulo-opiniones">
  <header class="cabecera-seccion">
    <h2 id="titulo-opiniones">Cinco miradas sobre el día</h2>
    <p>Personajes inventados. Los textos los escribe una IA para mostrar cómo
    vería las noticias cada corriente de pensamiento; no son de ninguna persona
    real ni la opinión de esta web.</p>
  </header>
  <div class="pestanas" role="tablist" aria-label="Elige un personaje">{pestanas}</div>
  <div class="paneles">{paneles}</div>
</section>"""


def grafico_historial(dias: list) -> str:
    """Dibuja con SVG una columna por día (los últimos DIAS_GRAFICO días)."""
    ancho, alto = 720, 230
    izq, der, arriba, abajo = 34, 14, 22, 30
    zona_ancho, zona_alto = ancho - izq - der, alto - arriba - abajo
    hueco = min(56, zona_ancho / len(dias))          # sitio para cada día
    grosor = min(22, hueco * 0.6)                    # grosor de la columna

    def y(valor):                                    # de nota (0-100) a píxeles
        return arriba + zona_alto * (1 - valor / 100)

    dibujo = ""
    for marca in (0, 50, 100):                       # líneas de referencia
        dibujo += (
            f'<line class="guia" x1="{izq}" x2="{ancho - der}" y1="{y(marca):.1f}" y2="{y(marca):.1f}"/>'
            f'<text class="eje" x="{izq - 8}" y="{y(marca) + 4:.1f}" text-anchor="end">{marca}</text>'
        )

    # Con muchos días solo se rotulan algunos, para que las fechas no se pisen.
    salto = max(1, round(len(dias) / 6))
    for posicion, dia in enumerate(dias):
        nota = a_numero(dia["crispacion"])
        fecha = datetime.strptime(dia["fecha"], "%Y-%m-%d")
        centro = izq + hueco * (posicion + 0.5)
        x0, x1 = centro - grosor / 2, centro + grosor / 2
        cima, base = y(nota), y(0)
        radio = min(4, grosor / 2, max(0, base - cima))
        ultimo = posicion == len(dias) - 1
        # Columna con las esquinas de arriba redondeadas.
        camino = (f"M{x0:.1f},{base:.1f} V{cima + radio:.1f} Q{x0:.1f},{cima:.1f} {x0 + radio:.1f},{cima:.1f} "
                  f"H{x1 - radio:.1f} Q{x1:.1f},{cima:.1f} {x1:.1f},{cima + radio:.1f} V{base:.1f} Z")
        dibujo += (
            f'<g class="columna{" hoy" if ultimo else ""}">'
            f'<title>{fecha.strftime("%d/%m/%Y")}: {nota} de 100 ({nivel(nota)})</title>'
            f'<rect class="zona" x="{centro - hueco / 2:.1f}" y="{arriba}" width="{hueco:.1f}" height="{zona_alto}"/>'
            f'<path d="{camino}"/>'
        )
        if ultimo:
            dibujo += f'<text class="valor" x="{centro:.1f}" y="{cima - 7:.1f}" text-anchor="middle">{nota}</text>'
        dibujo += "</g>"
        if ultimo or (posicion % salto == 0 and len(dias) - 1 - posicion >= salto):
            dibujo += (f'<text class="eje" x="{centro:.1f}" y="{alto - 9}" text-anchor="middle">'
                       f'{fecha.strftime("%d/%m")}</text>')

    return (
        f'<svg class="grafico" viewBox="0 0 {ancho} {alto}" role="img" '
        f'aria-label="Crispación de los últimos {len(dias)} días. Los valores están en la tabla.">'
        f"{dibujo}</svg>"
    )


def bloque_historial(historial: list) -> str:
    """Crispación día a día: gráfico y tabla."""
    if not historial:
        return ""
    filas = ""
    for dia in reversed(historial):                  # el más reciente arriba
        fecha = datetime.strptime(dia["fecha"], "%Y-%m-%d")
        nota = a_numero(dia["crispacion"])
        filas += (
            f'<tr><th scope="row"><time datetime="{dia["fecha"]}">{fecha.strftime("%d/%m/%Y")}</time></th>'
            f'<td class="celda-nota"><b>{nota}</b>{pastilla(nota)}</td>'
            f'<td>{escape(dia["comentario"])}</td></tr>'
        )
    return f"""
<section id="historico" aria-labelledby="titulo-historico">
  <header class="cabecera-seccion">
    <h2 id="titulo-historico">Crispación día a día</h2>
    <p>Un registro por día. La nota es la media de las lecturas de ese día.</p>
  </header>
  <figure class="figura">{grafico_historial(historial[-DIAS_GRAFICO:])}</figure>
  <div class="tabla-rueda">
    <table>
      <thead><tr><th scope="col">Día</th><th scope="col">Nivel</th><th scope="col">Resumen del día</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>
  </div>
</section>"""


# ----------------------------------------------------------------------
# LA PÁGINA COMPLETA
# ----------------------------------------------------------------------

def pagina(codigo: str) -> str:
    """Devuelve el HTML completo de la página de un país."""
    pais = PAISES[codigo]["nombre"]
    raiz = prefijo(codigo)
    ultimo = leer_json(codigo, "ultimo.json", None)
    historial = leer_json(codigo, "historial.json", [])

    # Menú de países: enlaces normales, cada país es una página distinta.
    menu_paises = ""
    for otro, datos in PAISES.items():
        actual = ' aria-current="page"' if otro == codigo else ""
        # El nombre no se ve, pero lo leen los lectores de pantalla y sale al
        # dejar el ratón encima (title).
        menu_paises += (
            f'<a href="{enlace_pais(otro, codigo)}"{actual} title="{escape(datos["nombre"])}" '
            f'aria-label="{escape(datos["nombre"])}">'
            f'<svg viewBox="0 0 3 2" width="42" height="28" aria-hidden="true">{datos["bandera"]}</svg></a>'
        )

    if ultimo:
        fecha = datetime.strptime(ultimo["fecha"], "%Y-%m-%d")
        nota = a_numero(ultimo["general"]["crispacion"])
        titulo = f"Portadas de hoy en {pais}: crispación {nota}/100 y populismo en la prensa | Portadas IA"
        descripcion = recortar(ultimo["general"]["temas"], 155)
        cuerpo = (
            bloque_crispacion(codigo, ultimo, historial)
            + bloque_populismo(ultimo)
            + bloque_periodicos(codigo, ultimo)
            + bloque_opiniones(codigo, ultimo)
            + bloque_historial(historial)
        )
        modificado = datetime.strptime(ultimo["generado"], "%d/%m/%Y %H:%M").isoformat()
    else:
        fecha = datetime.now()
        titulo = f"Portadas IA · {pais}"
        descripcion = f"Las portadas de la prensa de {pais}, resumidas y medidas por una IA."
        cuerpo = (f'<section class="portada"><div class="portada-texto"><h1>Todavía no hay datos de '
                  f'{escape(pais)}</h1><p class="entrada">Llegarán con la próxima lectura de portadas.</p></div></section>')
        modificado = fecha.isoformat(timespec="minutes")

    # Lo que solo se puede poner cuando la web tiene dirección pública.
    extras = ""
    if URL_BASE:
        url = direccion_publica(codigo)
        extras = (
            f'<link rel="canonical" href="{url}">\n'
            f'<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{URL_BASE}/img/estados.png">'
        )

    # Datos estructurados: le explican a Google qué es esta página.
    esquema = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": titulo,
        "description": descripcion,
        "inLanguage": "es",
        "dateModified": modificado,
        "isPartOf": {"@type": "WebSite", "name": "Portadas IA"},
    }, ensure_ascii=False)

    secciones = [("crispacion", "Crispación"), ("populismo", "Populismo"),
                 ("periodicos", "Periódicos"), ("opiniones", "Opiniones"), ("historico", "Día a día")]
    menu_secciones = "".join(f'<a href="#{ancla}">{texto}</a>' for ancla, texto in secciones)

    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)}</title>
<meta name="description" content="{escape(descripcion)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Portadas IA">
<meta property="og:title" content="{escape(titulo)}">
<meta property="og:description" content="{escape(descripcion)}">
<meta property="og:locale" content="es_ES">
<meta name="twitter:card" content="summary">
{extras}
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23142a5c'/%3E%3Cpath d='M8 10h16M8 16h16M8 22h10' stroke='%23fff' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=Public+Sans:wght@400;600;700&display=swap">
<link rel="stylesheet" href="{raiz}estilos.css">
<script type="application/ld+json">{esquema}</script>
</head>
<body>
<a class="saltar" href="#contenido">Saltar al contenido</a>

<header class="mancheta">
  <div class="ancho">
    <p class="fecha"><time datetime="{fecha.strftime("%Y-%m-%d")}">{fecha_larga(fecha).capitalize()}</time></p>
    <a class="marca" href="{enlace_pais("es", codigo)}">Portadas <i>IA</i></a>
    <p class="lema">La prensa del día, leída y medida por una inteligencia artificial</p>
    <nav class="paises" aria-label="Países">{menu_paises}</nav>
  </div>
</header>
<nav class="secciones" aria-label="Secciones de la página"><div class="ancho">{menu_secciones}</div></nav>

<main id="contenido" class="ancho">
{cuerpo}
</main>

<footer class="pie">
  <div class="ancho">
    <p><b>Cómo leer esta página.</b> Los resúmenes, el populismo, el sesgo y la
    crispación son una estimación de una IA a partir de los titulares: pueden
    contener errores y no son una medición objetiva. Pulsa en cada titular para
    leer la noticia completa en su periódico.</p>
    <p>Las portadas se leen cada día a las {", ".join(f"{hora}:00" for hora in HORAS[:-1])} y {HORAS[-1]}:00 (hora de Madrid).
    Código abierto en <a href="https://github.com/nonete/portadas-ia" rel="noopener">GitHub</a>.</p>
  </div>
</footer>

<script>window.HORAS_LECTURA = {json.dumps(HORAS)};</script>
<script src="{raiz}web.js" defer></script>
</body>
</html>
"""


# ----------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------

def main() -> None:
    # 1. Se empieza siempre con la carpeta vacía.
    if SITIO.exists():
        shutil.rmtree(SITIO)
    (SITIO / "img").mkdir(parents=True)

    # 2. Diseño, JavaScript e imágenes.
    for archivo in RECURSOS.iterdir():
        shutil.copy(archivo, SITIO / archivo.name)
    for imagen in list((RAIZ / "crispito").glob("*.*")) + list((RAIZ / "caricaturas").glob("*.png")):
        shutil.copy(imagen, SITIO / "img" / imagen.name)

    # 3. Una página por país.
    for codigo, datos in PAISES.items():
        carpeta = SITIO / datos["carpeta"]
        carpeta.mkdir(parents=True, exist_ok=True)
        (carpeta / "index.html").write_text(pagina(codigo), encoding="utf-8")
        print(f"Página de {datos['nombre']}: {(carpeta / 'index.html').relative_to(RAIZ)}")

    # 4. Página de error: se enseña cuando alguien pide una dirección que no existe.
    (SITIO / "404.html").write_text(
        '<!DOCTYPE html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="robots" content="noindex"><title>Página no encontrada | Portadas IA</title>'
        '<link rel="stylesheet" href="/estilos.css"></head><body>'
        '<header class="mancheta"><div class="ancho"><a class="marca" href="/">Portadas <i>IA</i></a>'
        '<p class="lema">Esta página no existe.</p>'
        '<nav class="paises"><a href="/">Volver a la portada</a></nav></div></header></body></html>',
        encoding="utf-8",
    )

    # 5. Archivos para los buscadores (solo cuando la web tenga dirección).
    if URL_BASE:
        direcciones = "".join(f"<url><loc>{direccion_publica(codigo)}</loc></url>" for codigo in PAISES)
        (SITIO / "sitemap.xml").write_text(
            '<?xml version="1.0" encoding="UTF-8"?>'
            f'<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{direcciones}</urlset>',
            encoding="utf-8",
        )
        (SITIO / "robots.txt").write_text(
            f"User-agent: *\nAllow: /\nSitemap: {URL_BASE}/sitemap.xml\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
