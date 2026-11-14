"""
Portadas IA · la web estática
-----------------------------
Este programa NO es Streamlit. Lee los mismos datos que app.py
(datos/<país>/ultimo.json e historial.json) y escribe páginas HTML normales
en la carpeta web/sitio/:

    web/sitio/index.html            → España
    web/sitio/francia/index.html    → Francia (y así cada país de PAISES)
    web/sitio/en/…, de/…, fr/…      → la misma web en cada idioma
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

IDIOMAS. La web se crea entera una vez por idioma (español, alemán, inglés,
portugués, francés, chino y ruso). Hay dos clases de textos:
  - los fijos (títulos, rótulos, avisos): están en web/textos.py y aquí se
    piden con t("clave");
  - los que escribe la IA (resúmenes, sesgo, crispación, opiniones): los
    traduce actualizar.py y los guarda en datos/<país>/traducciones/<idioma>/.
El español está en la raíz (/, /francia/) y los demás en su carpeta
(/en/, /en/france/). Las páginas fijas por día solo se hacen en español.
"""

import json
import math
import shutil
import sys
from datetime import datetime
from html import escape
from pathlib import Path

import textos                                # los textos fijos de la web, en cada idioma

try:                                         # Pillow solo hace falta para las imágenes de redes
    from PIL import Image, ImageDraw, ImageFont
except ImportError:                          # sin Pillow se usa la imagen genérica
    Image = None

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
#   nombre y carpeta → en español; los de los demás idiomas están en
#             web/textos.py (PAISES) y tienen que llevar los mismos países
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
    "br": {
        "nombre": "Brasil", "carpeta": "brasil", "idioma": "pt",
        # Fondo verde, rombo amarillo y círculo azul (sin la banda del lema).
        "bandera": '<rect width="3" height="2" fill="#009c3b"/>'
        '<polygon points="1.5,0.2 2.75,1 1.5,1.8 0.25,1" fill="#ffdf00"/>'
        '<circle cx="1.5" cy="1" r="0.42" fill="#002776"/>',
    },
    "eg": {
        "nombre": "Egipto", "carpeta": "egipto", "idioma": "ar",
        # Franjas roja, blanca y negra, con el águila dorada reducida a una
        # silueta sencilla (cuerpo y dos alas) en el centro.
        "bandera": franjas(["#ce1126", "#ffffff", "#000000"])
        + '<path d="M1.5,0.74 L1.62,0.86 L1.86,0.8 L1.68,1.0 L1.62,1.24 L1.38,1.24 L1.32,1.0 L1.14,0.8 L1.38,0.86 Z" fill="#c09300"/>',
    },
}

HORAS = [8, 18]                             # las mismas que en actualizar.py
DIAS_GRAFICO = 30                            # días que caben en el gráfico

# Con --vista-previa los enlaces entre páginas acaban en "index.html".
VISTA_PREVIA = "--vista-previa" in sys.argv

# El idioma de la página que se está escribiendo. main() lo va cambiando:
# primero crea toda la web en español y después en cada uno de los demás.
IDIOMA = "es"


# ----------------------------------------------------------------------
# IDIOMAS: TEXTOS Y DIRECCIONES
# ----------------------------------------------------------------------

def t(clave: str, **huecos) -> str:
    """El texto 'clave' en el idioma de la página (web/textos.py).
    Si a ese idioma le falta, se usa el español."""
    texto = textos.T[IDIOMA].get(clave)
    if texto is None:
        texto = textos.T["es"][clave]
    return texto.format(**huecos) if huecos else texto


def nombre_pais(codigo: str, idioma: str = "") -> str:
    return textos.PAISES[idioma or IDIOMA][codigo][0]


def enumerar(elementos: list) -> str:
    """'A, B y C', con la palabra 'y' del idioma de la página."""
    elementos = [str(elemento) for elemento in elementos]
    if len(elementos) < 2:
        return "".join(elementos)
    return ", ".join(elementos[:-1]) + textos.IDIOMAS[IDIOMA]["y"] + elementos[-1]


def lista_horas() -> str:
    """'8:00 y 18:00'"""
    return enumerar([f"{hora}:00" for hora in HORAS])


# Todas las direcciones se escriben primero como "camino desde la raíz de la
# web" (por ejemplo "en/france/") y después se convierten en un enlace
# relativo (enlace) o en una dirección completa (direccion).

def camino_idioma(idioma: str = "") -> str:
    """'' para el español (está en la raíz) y 'en/', 'de/'… para los demás."""
    idioma = idioma or IDIOMA
    return "" if idioma == "es" else idioma + "/"


def camino_pais(codigo: str, idioma: str = "") -> str:
    """Camino de la página de un país: '', 'francia/', 'en/', 'en/france/'…"""
    carpeta = textos.PAISES[idioma or IDIOMA][codigo][1]
    return camino_idioma(idioma) + (carpeta + "/" if carpeta else "")


def camino_metodologia(idioma: str = "") -> str:
    return camino_idioma(idioma) + textos.METODOLOGIA_CARPETA[idioma or IDIOMA] + "/"


def subir(camino: str) -> str:
    """Lo que hay que subir desde una página hasta la raíz: '', '../', '../../'…"""
    return "../" * camino.count("/")


def enlace(camino: str, raiz: str) -> str:
    """Enlace a 'camino' escrito desde una página que está a 'raiz' de la portada."""
    destino = raiz + camino
    if VISTA_PREVIA:
        return destino + "index.html"
    return destino or "./"


def direccion(camino: str) -> str:
    """Dirección completa (solo tiene sentido si hay URL_BASE)."""
    return f"{URL_BASE}/{camino}"


# Las páginas fijas por día solo existen en español.

def carpeta_dias(codigo: str) -> str:
    """Carpeta de las páginas por día de un país: la del país, o 'espana' para la portada."""
    return PAISES[codigo]["carpeta"] or "espana"


def dias_archivados(codigo: str) -> list:
    """Fechas (AAAA-MM-DD) de los días guardados en datos/<país>/dias/, de más antigua a más reciente."""
    return sorted(archivo.stem for archivo in (DATOS / codigo / "dias").glob("*.json"))


def camino_dia(codigo: str, fecha: str) -> str:
    return f"{carpeta_dias(codigo)}/{fecha}/"


# ----------------------------------------------------------------------
# FUNCIONES DE AYUDA
# ----------------------------------------------------------------------

def leer_json(pais: str, nombre: str, por_defecto):
    """Lee un archivo de datos/<país>/; si no existe devuelve el valor por defecto."""
    archivo = DATOS / pais / nombre
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    return por_defecto


def en_idioma(codigo: str, ultimo: dict) -> dict:
    """Devuelve los datos de un país con los textos de la IA en el idioma de la página.

    actualizar.py guarda la traducción en datos/<país>/traducciones/<idioma>/ultimo.json
    con una marca ("origen") que dice de qué lectura es. Si no hay traducción,
    o es de una lectura anterior, se dejan los textos en español: mejor un
    texto sin traducir que uno que no corresponde a las notas que se ven.
    """
    if IDIOMA == "es" or not ultimo:
        return ultimo
    traduccion = leer_json(codigo, f"traducciones/{IDIOMA}/ultimo.json", None)
    if not traduccion or traduccion.get("origen") != [ultimo["fecha"], ultimo["turno"], ultimo["generado"]]:
        return ultimo
    copia = json.loads(json.dumps(ultimo))               # copia completa, para no tocar el original
    copia["general"].update(traduccion.get("general", {}))
    for periodico in copia["periodicos"]:
        traducido = traduccion.get("periodicos", {}).get(periodico["nombre"])
        if periodico.get("analisis") and traducido:
            periodico["analisis"].update(traducido)
    for opinion in copia.get("opiniones") or []:
        texto = traduccion.get("opiniones", {}).get(opinion["id"])
        if texto:
            opinion["texto"] = texto
    return copia


def comentarios_traducidos(codigo: str) -> dict:
    """{fecha: comentario del día} en el idioma de la página (vacío en español)."""
    if IDIOMA == "es":
        return {}
    return leer_json(codigo, f"traducciones/{IDIOMA}/historial.json", {})


def a_numero(valor) -> int:
    """Asegura que una nota es un entero entre 0 y 100."""
    return max(0, min(100, int(valor)))


def nivel(valor: int) -> str:
    """'bajo', 'medio' o 'alto'. Es la clase de CSS; el texto visible sale de t("nivel_…")."""
    if valor < 34:
        return "bajo"
    if valor < 67:
        return "medio"
    return "alto"


def fecha_larga(fecha: datetime) -> str:
    """Miércoles, 11 de noviembre de 2026 (escrita como toca en cada idioma)."""
    return textos.fecha_larga(fecha, IDIOMA)


def recortar(texto: str, largo: int) -> str:
    """Corta un texto por una palabra entera, para la descripción de Google."""
    if len(texto) <= largo:
        return texto
    return texto[:largo].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


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
    return f'<span class="pastilla nivel-{nivel(valor)}">{t("nivel_" + nivel(valor))}</span>'


def parrafos(texto: str) -> str:
    """Convierte un texto con saltos de línea en párrafos <p>."""
    return "".join(f"<p>{escape(linea.strip())}</p>" for linea in texto.split("\n") if linea.strip())


def lista_resumen(texto: str) -> str:
    """El resumen de ChatGPT viene como líneas que empiezan por '- '."""
    puntos = [linea.strip().lstrip("-•* ").strip() for linea in texto.split("\n") if linea.strip()]
    return "<ul>" + "".join(f"<li>{escape(punto)}</li>" for punto in puntos) + "</ul>"


def menu_idiomas(caminos: dict, raiz: str) -> str:
    """El selector de idioma: un enlace por idioma a la misma página en ese idioma.
    'caminos' es {idioma: camino de esta página en ese idioma}."""
    enlaces = ""
    for idioma, datos in textos.IDIOMAS.items():
        actual = ' aria-current="true"' if idioma == IDIOMA else ""
        enlaces += (
            f'<a href="{enlace(caminos[idioma], raiz)}" lang="{datos["html"]}" hreflang="{datos["html"]}" '
            f'title="{datos["nombre"]}"{actual}>{datos["corto"]}</a>'
        )
    return f'<nav class="idiomas" aria-label="{t("aria_idiomas")}">{enlaces}</nav>'


def enlaces_alternativos(caminos: dict) -> str:
    """Le dicen a Google que la misma página existe en otros idiomas (hreflang)."""
    if not URL_BASE:
        return ""
    lineas = [f'<link rel="alternate" hreflang="{textos.IDIOMAS[idioma]["html"]}" href="{direccion(camino)}">'
              for idioma, camino in caminos.items()]
    lineas.append(f'<link rel="alternate" hreflang="x-default" href="{direccion(caminos["es"])}">')
    return "\n".join(lineas) + "\n"


# ----------------------------------------------------------------------
# IMAGEN PARA REDES SOCIALES (Open Graph)
# ----------------------------------------------------------------------

FUENTES_NEGRITA = ["/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
                   "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf"]
FUENTES_TEXTO = ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]
COLORES_NIVEL = {"bajo": "#3ecf3e", "medio": "#fab219", "alto": "#ff6b6b"}


def cargar_fuente(rutas: list, tamano: int):
    for ruta in rutas:
        if Path(ruta).exists():
            return ImageFont.truetype(ruta, tamano)
    return ImageFont.load_default()


def nombre_imagen_social(codigo: str) -> str:
    """og-fr.png en español, og-fr-en.png en inglés…"""
    return f"og-{codigo}.png" if IDIOMA == "es" else f"og-{codigo}-{IDIOMA}.png"


def imagen_social(codigo: str, ultimo: dict) -> bool:
    """Crea la imagen (1200x630) con la nota de crispación del día, en el idioma de la página.
    Devuelve False si no se pudo: entonces se usa la imagen genérica. Pasa sin
    Pillow y en chino, porque las letras instaladas no tienen caracteres chinos."""
    if Image is None or IDIOMA == "zh":
        return False
    nota = a_numero(ultimo["general"]["crispacion"])
    estado = min(5, nota * 6 // 100)
    lienzo = Image.new("RGB", (1200, 630), "#142a5c")
    pincel = ImageDraw.Draw(lienzo)
    pincel.rectangle([0, 0, 1200, 12], fill="#ffffff")
    pincel.text((70, 70), "Portadas IA", font=cargar_fuente(FUENTES_NEGRITA, 64), fill="#ffffff")
    pincel.text((70, 160), t("edicion", pais=nombre_pais(codigo)), font=cargar_fuente(FUENTES_TEXTO, 34), fill="#b9c4de")
    pincel.text((70, 250), str(nota), font=cargar_fuente(FUENTES_NEGRITA, 200), fill=COLORES_NIVEL[nivel(nota)])
    ancho_nota = pincel.textlength(str(nota), font=cargar_fuente(FUENTES_NEGRITA, 200))
    pincel.text((70 + ancho_nota + 16, 380), "/ 100", font=cargar_fuente(FUENTES_TEXTO, 48), fill="#b9c4de")
    pincel.text((70, 490), t("imagen_rotulo"), font=cargar_fuente(FUENTES_TEXTO, 38), fill="#ffffff")
    fecha = datetime.strptime(ultimo["fecha"], "%Y-%m-%d")
    pincel.text((70, 548), fecha_larga(fecha), font=cargar_fuente(FUENTES_TEXTO, 28), fill="#b9c4de")
    # Crispito en su estado de hoy (primer fotograma del GIF).
    gif = RAIZ / "crispito" / f"crispito_{estado}.gif"
    if gif.exists():
        mascota = Image.open(gif).convert("RGBA").resize((340, 340))
        lienzo.paste(mascota, (790, 150), mascota)
    lienzo.save(SITIO / "img" / nombre_imagen_social(codigo), optimize=True)
    return True


def enlaces_texto_paises(raiz: str) -> str:
    """Enlaces con texto a cada país (para el pie): los buscadores entienden mejor
    un texto que una bandera."""
    enlaces = ""
    for codigo in PAISES:
        enlaces += (f'<a href="{enlace(camino_pais(codigo), raiz)}">'
                    f'{escape(t("portadas_de", pais=nombre_pais(codigo)))}</a>')
    return enlaces


def pie(raiz: str, hora_texto: str) -> str:
    """El pie de página, igual en todas las páginas."""
    aviso = f"\n    <p>{t('aviso_traduccion')}</p>" if t("aviso_traduccion") else ""
    return f"""<footer class="pie">
  <div class="ancho">
    <p><b>{t("pie_titulo")}</b> {t("pie_texto")} <a href="{enlace(camino_metodologia(), raiz)}">{t("como_se_calcula")}</a>.</p>
    <p>{hora_texto}</p>{aviso}
    <nav class="pie-paises" aria-label="{t("aria_pie_paises")}">{enlaces_texto_paises(raiz)}</nav>
  </div>
</footer>"""


# ----------------------------------------------------------------------
# LOS TROZOS DE LA PÁGINA
# ----------------------------------------------------------------------

def bloque_crispacion(codigo: str, ultimo: dict, historial: list, raiz: str, archivo: bool = False) -> str:
    """La portada: titular, Crispito con la nota y los temas del día."""
    pais = nombre_pais(codigo)
    general = ultimo["general"]
    nota = a_numero(general["crispacion"])
    estado = min(5, nota * 6 // 100)         # 6 estados de Crispito, de 0 a 5
    estados = textos.ESTADOS_CRISPITO[IDIOMA]

    # Comparación con la media del día anterior, si lo hay.
    anteriores = [dia for dia in historial if dia["fecha"] < ultimo["fecha"]]
    cambio = ""
    if anteriores:
        diferencia = nota - a_numero(anteriores[-1]["crispacion"])
        if diferencia > 0:
            cambio = t("cambio_mas", puntos=diferencia)
        elif diferencia < 0:
            cambio = t("cambio_menos", puntos=-diferencia)
        else:
            cambio = t("cambio_igual")
        cambio = f'<p class="cambio">{cambio}</p>'

    cabeceras = enumerar([periodico["nombre"] for periodico in ultimo["periodicos"]])
    momento = datetime.strptime(ultimo["generado"], "%d/%m/%Y %H:%M")
    fecha_dia = datetime.strptime(ultimo["fecha"], "%Y-%m-%d")
    if archivo:                              # las páginas de archivo solo existen en español
        h1 = f"Portadas de {pais} del {fecha_dia.day} de {textos.MESES['es'][fecha_dia.month - 1]} de {fecha_dia.year}"
        proxima = ""                         # en una página de archivo no hay "próxima lectura"
    else:
        h1 = t("titular")
        proxima = (f'''<div><dt>{t("proxima")}</dt>
        <dd id="proxima">{t("a_las", horas=lista_horas())}</dd></div>''')

    linea_estado = t("estado_crispito", estado=f"<b>{escape(estados[estado])}</b>", numero=estado)

    return f"""
<section class="portada" id="crispacion" aria-labelledby="titulo-portada">
  <div class="portada-texto">
    <p class="antetitulo">{escape(t("edicion", pais=pais))}</p>
    <h1 id="titulo-portada">{h1}</h1>
    <p class="entrada">{escape(t("entrada", cabeceras=cabeceras))}</p>

    <h2 class="rotulo">{t("mas_repetido")}</h2>
    <p class="temas">{escape(general["temas"])}</p>

    <dl class="ficha">
      <div><dt>{t("actualizado")}</dt>
        <dd><time datetime="{momento.isoformat()}">{escape(ultimo["generado"])}</time></dd></div>
      {proxima}
      <div><dt>{t("modelo")}</dt><dd>{escape(ultimo["modelo"])}</dd></div>
    </dl>
  </div>

  <aside class="termometro" aria-labelledby="titulo-termometro">
    <h2 class="rotulo" id="titulo-termometro">{t("crispacion_ahora")}</h2>
    <div class="termometro-dato">
      <img src="{raiz}img/crispito_{estado}.gif" width="120" height="120"
           alt="{escape(t("alt_crispito", estado=estados[estado]))}">
      <div>
        <p class="cifra"><b>{nota}</b><span>/ 100</span></p>
        {pastilla(nota)}
        {cambio}
      </div>
    </div>
    {medidor(nota, t("crispacion"))}
    <p class="escala" aria-hidden="true"><span>{t("escala_0")}</span><span>{t("escala_100")}</span></p>
    <p class="estado">{linea_estado}</p>
    <p class="motivo">{escape(general["motivo_crispacion"])}</p>
    <details>
      <summary>{t("conoce_crispito")}</summary>
      <img src="{raiz}img/estados.png" width="720" height="480" loading="lazy"
           alt="{escape(t("alt_estados", lista=", ".join(estados)))}">
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
            f'{medidor(nota, t("populismo_de", periodico=periodico["nombre"]))}'
            f'<span class="valor">{nota}</span>{pastilla(nota)}</li>'
        )
    if not filas:
        return ""
    return f"""
<section id="populismo" aria-labelledby="titulo-populismo">
  <header class="cabecera-seccion">
    <h2 id="titulo-populismo">{t("populismo_titulo")}</h2>
    <p>{t("populismo_texto")}</p>
  </header>
  <ol class="ranking">{"".join(filas)}</ol>
</section>"""


def bloque_periodicos(codigo: str, ultimo: dict) -> str:
    """Una ficha por periódico: resumen, populismo, sesgo y titulares."""
    fichas = []
    # lang="…" le dice al navegador en qué idioma están los titulares originales.
    idioma = f' lang="{PAISES[codigo]["idioma"]}"' if PAISES[codigo]["idioma"] else ""
    if PAISES[codigo]["idioma"] == "ar":
        idioma += ' dir="rtl"'          # el árabe se escribe de derecha a izquierda
    for periodico in ultimo["periodicos"]:
        nombre = escape(periodico["nombre"])
        web = escape(periodico["web"])
        analisis = periodico.get("analisis")
        noticias = periodico.get("noticias") or []

        if not analisis or not noticias:
            fichas.append(
                f'<article class="periodico"><h3>{nombre}</h3>'
                f'<p class="aviso">{t("no_leida")} '
                f'<a href="{web}" rel="noopener">{escape(t("abrir", periodico=periodico["nombre"]))}</a></p></article>'
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
    <p class="linea"><span>{t("populismo")}</span><b>{nota}</b>{pastilla(nota)}</p>
    {medidor(nota, t("populismo_de", periodico=periodico["nombre"]), fino=True)}
    <p class="nota">{escape(analisis["motivo_populismo"])}</p>
  </div>
  <p class="sesgo"><b>{t("sesgo")}</b> {escape(analisis["sesgo"])}</p>
  <details>
    <summary>{t("ver_titulares", numero=len(noticias))}</summary>
    <ol{idioma}>{titulares}</ol>
  </details>
</article>""")

    return f"""
<section id="periodicos" aria-labelledby="titulo-periodicos">
  <header class="cabecera-seccion">
    <h2 id="titulo-periodicos">{t("periodicos_titulo")}</h2>
    <p>{t("periodicos_texto")}</p>
  </header>
  <div class="rejilla-periodicos">{"".join(fichas)}</div>
</section>"""


def bloque_opiniones(ultimo: dict, raiz: str) -> str:
    """Las cinco opiniones. Sin JavaScript se ven todas; con él, por pestañas."""
    opiniones = ultimo.get("opiniones") or []
    if not opiniones:
        return ""
    pestanas, paneles = "", ""
    for opinion in opiniones:
        ident = escape(opinion["id"])
        # El nombre del personaje sale de web/textos.py; si es un personaje
        # nuevo que aún no está allí, se usa el que viene en los datos.
        nombre = escape(textos.PERSONAJES[IDIOMA].get(opinion["id"], opinion["nombre"]))
        imagen = f'<img src="{raiz}img/{ident}.png" width="72" height="72" alt="">'
        pestanas += (
            f'<button type="button" role="tab" id="pestana-{ident}" '
            f'aria-controls="panel-{ident}" aria-selected="false">{imagen}<span>{nombre}</span></button>'
        )
        paneles += (
            f'<article class="opinion" role="tabpanel" id="panel-{ident}" '
            f'aria-labelledby="pestana-{ident}">'
            f'<header>{imagen}<h3>{t("opina", personaje=nombre)}</h3></header>'
            f'{parrafos(opinion["texto"])}</article>'
        )
    return f"""
<section id="opiniones" aria-labelledby="titulo-opiniones">
  <header class="cabecera-seccion">
    <h2 id="titulo-opiniones">{t("opiniones_titulo")}</h2>
    <p>{t("opiniones_texto")}</p>
  </header>
  <div class="pestanas" role="tablist" aria-label="{t("elige_personaje")}">{pestanas}</div>
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
        rotulo = t("punto_grafico", fecha=fecha.strftime("%d/%m/%Y"), nota=nota,
                   nivel=t("nivel_" + nivel(nota)).lower())
        dibujo += (
            f'<g class="columna{" hoy" if ultimo else ""}">'
            f'<title>{rotulo}</title>'
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
        f'aria-label="{t("aria_grafico", numero=len(dias))}">'
        f"{dibujo}</svg>"
    )


def bloque_historial(historial: list, codigo: str = "", raiz: str = "") -> str:
    """Crispación día a día: gráfico y tabla."""
    if not historial:
        return ""
    filas = ""
    # Las páginas de cada día solo existen en español: solo allí se enlazan.
    archivados = set(dias_archivados(codigo)) if codigo and IDIOMA == "es" else set()
    traducidos = comentarios_traducidos(codigo) if codigo else {}
    for dia in reversed(historial):                  # el más reciente arriba
        fecha = datetime.strptime(dia["fecha"], "%Y-%m-%d")
        nota = a_numero(dia["crispacion"])
        texto_fecha = fecha.strftime("%d/%m/%Y")
        if dia["fecha"] in archivados:               # si hay página de ese día, se enlaza
            texto_fecha = f'<a href="{enlace(camino_dia(codigo, dia["fecha"]), raiz)}">{texto_fecha}</a>'
        comentario = traducidos.get(dia["fecha"]) or dia["comentario"]
        filas += (
            f'<tr><th scope="row"><time datetime="{dia["fecha"]}">{texto_fecha}</time></th>'
            f'<td class="celda-nota"><b>{nota}</b>{pastilla(nota)}</td>'
            f'<td>{escape(comentario)}</td></tr>'
        )
    return f"""
<section id="historico" aria-labelledby="titulo-historico">
  <header class="cabecera-seccion">
    <h2 id="titulo-historico">{t("historico_titulo")}</h2>
    <p>{t("historico_texto")}</p>
  </header>
  <figure class="figura">{grafico_historial(historial[-DIAS_GRAFICO:])}</figure>
  <div class="tabla-rueda">
    <table>
      <thead><tr><th scope="col">{t("col_dia")}</th><th scope="col">{t("col_nivel")}</th><th scope="col">{t("col_resumen")}</th></tr></thead>
      <tbody>{filas}</tbody>
    </table>
  </div>
</section>"""


# ----------------------------------------------------------------------
# LA PÁGINA COMPLETA
# ----------------------------------------------------------------------

def navegacion_dias(codigo: str, dia: str, raiz: str) -> str:
    """Enlaces al día anterior, al siguiente y a la portada de hoy (solo en español)."""
    fechas = dias_archivados(codigo)
    posicion = fechas.index(dia)
    def etiqueta(fecha: str) -> str:
        f = datetime.strptime(fecha, "%Y-%m-%d")
        return f"{f.day} de {textos.MESES['es'][f.month - 1]}"
    enlaces = ""
    if posicion > 0:
        enlaces += f'<a rel="prev" href="{enlace(camino_dia(codigo, fechas[posicion - 1]), raiz)}">← {etiqueta(fechas[posicion - 1])}</a>'
    enlaces += f'<a href="{enlace(camino_pais(codigo), raiz)}">Portadas de hoy en {escape(nombre_pais(codigo))}</a>'
    if posicion < len(fechas) - 1:
        enlaces += f'<a rel="next" href="{enlace(camino_dia(codigo, fechas[posicion + 1]), raiz)}">{etiqueta(fechas[posicion + 1])} →</a>'
    return f'<nav class="dias-vecinos" aria-label="Otros días">{enlaces}</nav>'


def pagina(codigo: str, dia: str = "") -> str:
    """Devuelve el HTML completo de la página de un país, en el idioma IDIOMA.

    Con 'dia' (AAAA-MM-DD) es la página fija de ese día, por ejemplo
    /francia/2026-11-12/, hecha con la copia guardada en datos/<país>/dias/.
    Las páginas por día solo se hacen en español.
    """
    pais = nombre_pais(codigo)
    idioma_html = textos.IDIOMAS[IDIOMA]["html"]
    historial = leer_json(codigo, "historial.json", [])
    if dia:
        camino = camino_dia(codigo, dia)      # carpeta del país + carpeta del día
        ultimo = json.loads((DATOS / codigo / "dias" / f"{dia}.json").read_text(encoding="utf-8"))
        historial = [registro for registro in historial if registro["fecha"] <= dia]
    else:
        camino = camino_pais(codigo)
        ultimo = en_idioma(codigo, leer_json(codigo, "ultimo.json", None))
    raiz = subir(camino)

    # Esta misma página en cada idioma (desde una página de día se va a la de
    # hoy de ese país, porque los días pasados solo están en español).
    en_otros_idiomas = {idioma: camino_pais(codigo, idioma) for idioma in textos.IDIOMAS}
    if dia:
        en_otros_idiomas["es"] = camino

    # Menú de países: enlaces normales, cada país es una página distinta.
    menu_paises = ""
    for otro, datos in PAISES.items():
        actual = ' aria-current="page"' if otro == codigo else ""
        # El nombre no se ve, pero lo leen los lectores de pantalla y sale al
        # dejar el ratón encima (title).
        menu_paises += (
            f'<a href="{enlace(camino_pais(otro), raiz)}"{actual} title="{escape(nombre_pais(otro))}" '
            f'aria-label="{escape(nombre_pais(otro))}">'
            f'<svg viewBox="0 0 3 2" width="42" height="28" aria-hidden="true">{datos["bandera"]}</svg></a>'
        )

    if ultimo:
        fecha = datetime.strptime(ultimo["fecha"], "%Y-%m-%d")
        nota = a_numero(ultimo["general"]["crispacion"])
        descripcion = recortar(ultimo["general"]["temas"], 155)
        if dia:
            titulo = (f"Portadas de {pais} del {fecha.day} de {textos.MESES['es'][fecha.month - 1]} de {fecha.year}: "
                      f"crispación {nota}/100 | Portadas IA")
            cuerpo = (
                navegacion_dias(codigo, dia, raiz)
                + bloque_crispacion(codigo, ultimo, historial, raiz, archivo=True)
                + bloque_populismo(ultimo)
                + bloque_periodicos(codigo, ultimo)
                + bloque_historial(historial, codigo, raiz)
            )
        else:
            titulo = t("titulo_hoy", pais=pais, nota=nota)
            cuerpo = (
                bloque_crispacion(codigo, ultimo, historial, raiz)
                + bloque_populismo(ultimo)
                + bloque_periodicos(codigo, ultimo)
                + bloque_opiniones(ultimo, raiz)
                + bloque_historial(historial, codigo, raiz)
            )
        modificado = datetime.strptime(ultimo["generado"], "%d/%m/%Y %H:%M").isoformat()
    else:
        fecha = datetime.now()
        nota = 0
        titulo = t("titulo_sin_datos", pais=pais)
        descripcion = t("descripcion_sin_datos", pais=pais)
        cuerpo = (f'<section class="portada"><div class="portada-texto"><h1>{escape(t("sin_datos", pais=pais))}'
                  f'</h1><p class="entrada">{t("sin_datos_texto")}</p></div></section>')
        modificado = fecha.isoformat(timespec="minutes")

    # Lo que solo se puede poner cuando la web tiene dirección pública.
    extras = ""
    if URL_BASE:
        url = direccion(camino)
        # Imagen para redes: la del país con la nota del día, o la genérica
        # (las páginas de días pasados usan la genérica para no llenar la web de imágenes).
        if ultimo and not dia and imagen_social(codigo, ultimo):
            imagen = f"{URL_BASE}/img/{nombre_imagen_social(codigo)}"
            medidas = ('\n<meta property="og:image:width" content="1200">'
                       '\n<meta property="og:image:height" content="630">')
            alt_imagen = t("alt_imagen", nota=nota, pais=pais)
        else:
            imagen, medidas = f"{URL_BASE}/img/estados.png", ""
            alt_imagen = t("alt_imagen_generica")
        extras = (
            f'<link rel="canonical" href="{url}">\n'
            + ("" if dia else enlaces_alternativos(en_otros_idiomas))
            + f'<meta property="og:url" content="{url}">\n'
            f'<meta property="og:image" content="{imagen}">{medidas}\n'
            f'<meta property="og:image:alt" content="{escape(alt_imagen)}">\n'
            f'<meta name="twitter:image" content="{imagen}">'
        )

    # Datos estructurados: le explican a Google qué es esta página.
    pagina_url = direccion(camino) if URL_BASE else ""
    esquema = json.dumps({
        "@context": "https://schema.org",
        "@graph": [
            {"@type": "WebSite", "@id": f"{URL_BASE}/#sitio", "name": "Portadas IA",
             "url": f"{URL_BASE}/", "inLanguage": "es",
             "description": textos.T["es"]["sitio_descripcion"]},
            {"@type": "WebPage", "name": titulo, "description": descripcion, "url": pagina_url,
             "inLanguage": idioma_html, "dateModified": modificado,
             "isPartOf": {"@id": f"{URL_BASE}/#sitio"},
             "about": t("sobre", pais=pais)},
        ] + ([{"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Portadas IA", "item": f"{URL_BASE}/"},
            {"@type": "ListItem", "position": 2, "name": f"Portadas de {pais}", "item": direccion(camino_pais(codigo))},
            {"@type": "ListItem", "position": 3, "name": fecha_larga(fecha), "item": pagina_url},
        ]}] if dia and URL_BASE else []),
    }, ensure_ascii=False)

    secciones = [("crispacion", t("sec_crispacion")), ("populismo", t("sec_populismo")),
                 ("periodicos", t("sec_periodicos")), ("opiniones", t("sec_opiniones")),
                 ("historico", t("sec_historico"))]
    if dia:                                   # las páginas de día no llevan opiniones
        secciones = [seccion for seccion in secciones if seccion[0] != "opiniones"]
    menu_secciones = "".join(f'<a href="#{ancla}">{texto}</a>' for ancla, texto in secciones)

    horario = t("horario", horas=lista_horas())
    textos_js = json.dumps({"hoy": t("hoy_a_las"), "manana": t("manana_a_las")}, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="{idioma_html}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)}</title>
<meta name="description" content="{escape(descripcion)}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="Portadas IA">
<meta property="og:title" content="{escape(titulo)}">
<meta property="og:description" content="{escape(descripcion)}">
<meta property="og:locale" content="{textos.IDIOMAS[IDIOMA]["locale"]}">
<meta name="twitter:card" content="summary_large_image">
{extras}
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' rx='6' fill='%23142a5c'/%3E%3Cpath d='M8 10h16M8 16h16M8 22h10' stroke='%23fff' stroke-width='3' stroke-linecap='round'/%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=Public+Sans:wght@400;600;700&display=swap">
<link rel="stylesheet" href="{raiz}estilos.css">
<script type="application/ld+json">{esquema}</script>
</head>
<body>
<a class="saltar" href="#contenido">{t("saltar")}</a>

<header class="mancheta">
  <div class="ancho">
    {menu_idiomas(en_otros_idiomas, raiz)}
    <p class="fecha"><time datetime="{fecha.strftime("%Y-%m-%d")}">{fecha_larga(fecha)}</time></p>
    <a class="marca" href="{enlace(camino_pais("es"), raiz)}">Portadas <i>IA</i></a>
    <p class="lema">{t("lema")}</p>
    <nav class="paises" aria-label="{t("aria_paises")}">{menu_paises}</nav>
  </div>
</header>
<nav class="secciones" aria-label="{t("aria_secciones")}"><div class="ancho">{menu_secciones}</div></nav>

<main id="contenido" class="ancho">
{cuerpo}
</main>

{pie(raiz, horario)}

<script>window.HORAS_LECTURA = {json.dumps(HORAS)}; window.TEXTOS_LECTURA = {textos_js};</script>
<script src="{raiz}web.js" defer></script>
</body>
</html>
"""


def pagina_metodologia() -> str:
    """Página 'Cómo se calcula': explica el método, los periódicos y los límites."""
    m = textos.METODOLOGIA[IDIOMA]
    idioma_html = textos.IDIOMAS[IDIOMA]["html"]
    camino = camino_metodologia()
    raiz = subir(camino)
    por_pais = ""
    for codigo in PAISES:
        ultimo = leer_json(codigo, "ultimo.json", None)
        if not ultimo:
            continue
        nombres = ", ".join(p["nombre"] for p in ultimo["periodicos"])
        por_pais += f"<li><b>{escape(nombre_pais(codigo))}:</b> {escape(nombres)}.</li>"
    en_otros_idiomas = {idioma: camino_metodologia(idioma) for idioma in textos.IDIOMAS}
    url = direccion(camino) if URL_BASE else ""
    canonical = (f'<link rel="canonical" href="{url}">\n{enlaces_alternativos(en_otros_idiomas)}'
                 f'<meta property="og:url" content="{url}">\n') if url else ""
    imagen = f'<meta property="og:image" content="{URL_BASE}/img/estados.png">\n<meta name="twitter:image" content="{URL_BASE}/img/estados.png">\n' if url else ""
    horario = t("horario", horas=lista_horas())
    inicio = enlace(camino_pais("es"), raiz)
    estados = enumerar(textos.ESTADOS_CRISPITO[IDIOMA])
    apartados = "".join(
        f"\n  <h2>{escape(titulo)}</h2>\n  <p>{escape(texto.format(estados=estados))}</p>\n"
        for titulo, texto in m["apartados"]
    )
    limites = "".join(f"\n    <li>{escape(limite)}</li>" for limite in m["limites"])
    return f"""<!DOCTYPE html>
<html lang="{idioma_html}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(m["titulo"])}</title>
<meta name="description" content="{escape(m["descripcion"])}">
<meta property="og:type" content="article">
<meta property="og:site_name" content="Portadas IA">
<meta property="og:title" content="{escape(m["titulo"])}">
<meta property="og:description" content="{escape(m["descripcion"])}">
<meta property="og:locale" content="{textos.IDIOMAS[IDIOMA]["locale"]}">
<meta name="twitter:card" content="summary_large_image">
{canonical}{imagen}<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:opsz,wght@6..72,400;6..72,600;6..72,700&family=Public+Sans:wght@400;600;700&display=swap">
<link rel="stylesheet" href="{raiz}estilos.css">
</head>
<body>
<a class="saltar" href="#contenido">{t("saltar")}</a>
<header class="mancheta">
  <div class="ancho">
    {menu_idiomas(en_otros_idiomas, raiz)}
    <a class="marca" href="{inicio}">Portadas <i>IA</i></a>
    <p class="lema">{t("lema")}</p>
  </div>
</header>
<main id="contenido" class="ancho texto-largo">
<section>
  <header class="cabecera-seccion">
    <h1>{escape(m["h1"])}</h1>
    <p>{escape(m["entrada"])}</p>
  </header>
{apartados}
  <h2>{escape(m["periodicos_titulo"])}</h2>
  <p>{escape(m["periodicos_texto"])}</p>
  <ul>{por_pais}</ul>

  <h2>{escape(m["cuando_titulo"])}</h2>
  <p>{escape(horario)}</p>

  <h2>{escape(m["limites_titulo"])}</h2>
  <ul>{limites}
  </ul>
  <p><a href="{inicio}">{escape(m["volver"])}</a></p>
</section>
</main>
{pie(raiz, horario)}
</body>
</html>
"""


# ----------------------------------------------------------------------
# PROGRAMA PRINCIPAL
# ----------------------------------------------------------------------

def comprobar_textos() -> None:
    """Avisa pronto si a web/textos.py le falta algo (por ejemplo, tras añadir un país)."""
    for codigo, datos in PAISES.items():
        if textos.PAISES["es"].get(codigo) != (datos["nombre"], datos["carpeta"]):
            sys.exit(f"web/textos.py: el país '{codigo}' no coincide con PAISES de web/generar.py.")
    for idioma in textos.IDIOMAS:
        faltan = [codigo for codigo in PAISES if codigo not in textos.PAISES.get(idioma, {})]
        if faltan:
            sys.exit(f"web/textos.py: en el idioma '{idioma}' faltan los países {', '.join(faltan)}.")
        carpetas = [textos.PAISES[idioma][codigo][1] for codigo in PAISES] + [textos.METODOLOGIA_CARPETA[idioma]]
        if len(set(carpetas)) != len(carpetas):
            sys.exit(f"web/textos.py: en el idioma '{idioma}' hay dos páginas con la misma dirección.")


def escribir(camino: str, contenido: str) -> None:
    """Guarda una página en web/sitio/<camino>index.html."""
    carpeta = SITIO / camino
    carpeta.mkdir(parents=True, exist_ok=True)
    (carpeta / "index.html").write_text(contenido, encoding="utf-8")


def main() -> None:
    global IDIOMA
    comprobar_textos()

    # 1. Se empieza siempre con la carpeta vacía.
    if SITIO.exists():
        shutil.rmtree(SITIO)
    (SITIO / "img").mkdir(parents=True)

    # 2. Diseño, JavaScript e imágenes.
    for archivo in RECURSOS.iterdir():
        shutil.copy(archivo, SITIO / archivo.name)
    for imagen in list((RAIZ / "crispito").glob("*.*")) + list((RAIZ / "caricaturas").glob("*.png")):
        shutil.copy(imagen, SITIO / "img" / imagen.name)

    # 3. La web entera, una vez por idioma: una página por país y la del método.
    #    El español va en la raíz y los demás en su carpeta (/en/, /de/…).
    direcciones = ""                          # para sitemap.xml
    hoy = datetime.now().strftime("%Y-%m-%d")
    for IDIOMA in textos.IDIOMAS:
        for codigo in PAISES:
            escribir(camino_pais(codigo), pagina(codigo))
            ultimo = leer_json(codigo, "ultimo.json", None)
            # lastmod = el día de la última lectura de ese país.
            fecha = f"<lastmod>{ultimo['fecha']}</lastmod>" if ultimo else ""
            direcciones += f"<url><loc>{direccion(camino_pais(codigo))}</loc>{fecha}</url>"
        escribir(camino_metodologia(), pagina_metodologia())
        direcciones += f"<url><loc>{direccion(camino_metodologia())}</loc><lastmod>{hoy}</lastmod></url>"
        print(f"{textos.IDIOMAS[IDIOMA]['nombre']}: {len(PAISES)} países en web/sitio/{camino_idioma()}")

    # Una página fija por cada día guardado: /<país>/<AAAA-MM-DD>/ (solo en español).
    IDIOMA = "es"
    for codigo in PAISES:
        for dia in dias_archivados(codigo):
            escribir(camino_dia(codigo, dia), pagina(codigo, dia))
            direcciones += f"<url><loc>{direccion(camino_dia(codigo, dia))}</loc><lastmod>{dia}</lastmod></url>"

    # La lista de países, para el desplegable de la página de configuración.
    (SITIO / "paises.json").write_text(
        json.dumps([{"codigo": codigo, "nombre": datos["nombre"]} for codigo, datos in PAISES.items()],
                   ensure_ascii=False),
        encoding="utf-8",
    )

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
