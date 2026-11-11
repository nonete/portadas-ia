"""
Portadas IA · la web
--------------------
Esta página solo ENSEÑA los datos. No llama a los periódicos ni a ChatGPT:
de eso se encarga actualizar.py, que GitHub ejecuta a las 8:00, 11:00,
14:00, 17:00 y 20:00 y deja el resultado en datos/<país>/ (datos/es, datos/fr…).
El selector de arriba decide de qué carpeta se lee.

Los colores generales (fondo claro, color principal…) están en
.streamlit/config.toml. El resto del diseño está en el bloque ESTILOS.
"""

import base64
import json
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

HORAS = [8, 11, 14, 17, 20]     # las mismas que en actualizar.py
CARPETA = Path(__file__).parent / "datos"

# Crispito, la mascota. Sus GIF se crean con crear_crispito.py.
CARPETA_CRISPITO = Path(__file__).parent / "crispito"
CARPETA_CARICATURAS = Path(__file__).parent / "caricaturas"
ESTADOS_CRISPITO = ["Zen", "Tranquilo", "Mosqueado", "Molesto", "Enfadado", "¡A punto de estallar!"]

# Los países del selector. La clave es el nombre de su carpeta en datos/
# y tiene que coincidir con PAISES de actualizar.py.
PAISES = {
    "es": "🇪🇸 España",
    "fr": "🇫🇷 Francia",
    "us": "🇺🇸 Estados Unidos",
    "gb": "🇬🇧 Reino Unido",
    "de": "🇩🇪 Alemania",
    "it": "🇮🇹 Italia",
    "ru": "🇷🇺 Rusia",
    "cn": "🇨🇳 China",
}

# Un color para distinguir cada periódico, por orden (es solo decorativo).
COLORES = ["#2563eb", "#0d9488", "#d97706", "#c026d3", "#4f46e5"]

# ----------------------------------------------------------------------
# ESTILOS (CSS)
# ----------------------------------------------------------------------

ESTILOS = """
<style>
/* Ancho y márgenes de la página */
.block-container { max-width: 820px; padding-top: 2.2rem; padding-bottom: 3rem; }

/* Cabecera con degradado */
.cabecera {
    background: linear-gradient(135deg, #1e3a8a 0%, #4f46e5 55%, #0d9488 100%);
    color: #ffffff; border-radius: 18px; padding: 28px 26px 22px;
    box-shadow: 0 10px 30px rgba(30, 58, 138, .25); margin-bottom: 18px;
}
.cabecera h1 { color: #ffffff; font-size: 2.1rem; margin: 0 0 6px; padding: 0; line-height: 1.15; }
.cabecera p { color: #e0e7ff; margin: 0; font-size: 1rem; line-height: 1.45; }
.chips { margin-top: 16px; display: flex; flex-wrap: wrap; gap: 8px; }
.chip {
    background: rgba(255, 255, 255, .16); border: 1px solid rgba(255, 255, 255, .28);
    color: #ffffff; border-radius: 999px; padding: 4px 12px; font-size: .8rem;
}

/* Tarjetas */
.tarjeta {
    background: #ffffff; border: 1px solid #e5e7eb; border-radius: 16px;
    padding: 20px 22px; box-shadow: 0 2px 10px rgba(15, 23, 42, .05); margin-bottom: 16px;
}
.etiqueta {
    font-size: .74rem; font-weight: 700; letter-spacing: .08em;
    text-transform: uppercase; color: #64748b; margin-bottom: 8px;
}
.tarjeta p { margin: 0; color: #1e293b; line-height: 1.6; }

/* Número grande con su barra (crispación de hoy) */
.dato { display: flex; align-items: baseline; gap: 8px; margin-bottom: 10px; }
.dato .numero { font-size: 2.8rem; font-weight: 800; line-height: 1; }
.dato .sobre { color: #94a3b8; font-size: 1.05rem; font-weight: 600; }
.dato .nivel {
    margin-left: auto; color: #ffffff; border-radius: 999px;
    padding: 4px 14px; font-size: .82rem; font-weight: 700;
}

/* Crispito junto a la nota */
.crispito { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
.crispito img { width: 128px; height: 128px; flex: none; }
.crispito .dato { margin-bottom: 4px; }
.crispito .nombre { color: #334155; font-size: 1rem; line-height: 1.35; }
.crispito .estado { color: #94a3b8; font-size: .8rem; margin-top: 2px; }

/* Opinión de un personaje */
.opinion { display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }
.opinion img { width: 96px; height: 96px; flex: none; border-radius: 50%; }
.opinion .quien { font-size: 1.25rem; font-weight: 800; color: #0f172a; line-height: 1.2; }
.opinion .aviso { color: #94a3b8; font-size: .8rem; margin-top: 3px; }
.tarjeta p.parrafo { margin-bottom: 10px; }

/* Barras de 0 a 100 */
.barra { background: #e9edf3; border-radius: 999px; height: 12px; overflow: hidden; }
.barra div { height: 100%; border-radius: 999px; }
.barra.fina { height: 8px; }

/* Cabecera de cada periódico */
.periodico {
    display: flex; align-items: center; gap: 10px;
    font-size: 1.45rem; font-weight: 800; color: #0f172a; margin: 2px 0 4px;
}
.periodico .punto { width: 14px; height: 14px; border-radius: 4px; flex: none; }
.raya { height: 4px; border-radius: 999px; margin-bottom: 6px; }

/* Bloque de populismo y sesgo */
.medidor { margin-top: 6px; }
.medidor .fila { display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px; }
.medidor .titulo { font-weight: 700; color: #0f172a; }
.medidor .valor { font-weight: 800; font-size: 1.15rem; }
.medidor .motivo { color: #64748b; font-size: .88rem; margin-top: 8px; line-height: 1.5; }
.sesgo {
    background: #f1f5f9; border-left: 4px solid #94a3b8; border-radius: 8px;
    padding: 10px 14px; margin-top: 12px; color: #334155; font-size: .93rem; line-height: 1.55;
}
.sesgo b { color: #0f172a; }

/* Tabla de crispación día a día */
.tabla { width: 100%; border-collapse: separate; border-spacing: 0; background: #ffffff;
    border: 1px solid #e5e7eb; border-radius: 16px; overflow: hidden;
    box-shadow: 0 2px 10px rgba(15, 23, 42, .05); }
.tabla th { background: #1e3a8a; color: #ffffff; text-align: left; font-size: .76rem;
    letter-spacing: .07em; text-transform: uppercase; padding: 11px 14px; border: none; }
.tabla td { padding: 14px; vertical-align: top; border: none; border-top: 1px solid #eef1f5;
    color: #1e293b; line-height: 1.55; font-size: .93rem; }
.tabla tr:nth-child(even) td { background: #f8fafc; }
.tabla .dia { white-space: nowrap; font-weight: 700; }
.tabla .nota { min-width: 86px; }
.tabla .nota span { font-weight: 800; font-size: 1.15rem; }
.tabla .nota small { color: #94a3b8; font-weight: 600; }

.pie { color: #64748b; font-size: .82rem; line-height: 1.55; margin-top: 22px; }
h3 { color: #0f172a; }
</style>
"""


# ----------------------------------------------------------------------
# FUNCIONES DE AYUDA
# ----------------------------------------------------------------------

def leer_json(pais: str, nombre: str, por_defecto):
    """Lee un archivo de datos/<país>/; si no existe devuelve el valor por defecto."""
    archivo = CARPETA / pais / nombre
    if archivo.exists():
        return json.loads(archivo.read_text(encoding="utf-8"))
    return por_defecto


def proxima_actualizacion() -> str:
    """Texto con la siguiente hora de actualización."""
    ahora = datetime.now(ZoneInfo("Europe/Madrid"))
    for hora in HORAS:
        if ahora.hour < hora:
            return f"hoy a las {hora}:00"
    manana = ahora + timedelta(days=1)
    return f"mañana ({manana.strftime('%d/%m')}) a las {HORAS[0]}:00"


def color_nivel(valor: int) -> str:
    """Verde si es bajo, ámbar si es medio y rojo si es alto."""
    if valor < 34:
        return "#16a34a"
    if valor < 67:
        return "#d97706"
    return "#dc2626"


def texto_nivel(valor: int) -> str:
    if valor < 34:
        return "Bajo"
    if valor < 67:
        return "Medio"
    return "Alto"


def barra(valor: int, fina: bool = False) -> str:
    """Devuelve el HTML de una barra de 0 a 100 pintada con el color de su nivel."""
    clase = "barra fina" if fina else "barra"
    return (
        f'<div class="{clase}"><div style="width:{valor}%;'
        f'background:{color_nivel(valor)}"></div></div>'
    )


def html(codigo: str) -> None:
    """Pinta un trozo de HTML en la página."""
    st.markdown(codigo, unsafe_allow_html=True)


@st.cache_data
def imagen_incrustada(ruta: str) -> str:
    """Convierte una imagen (GIF o PNG) en texto para meterla dentro del HTML."""
    archivo = Path(__file__).parent / ruta
    tipo = "gif" if archivo.suffix == ".gif" else "png"
    return f"data:image/{tipo};base64," + base64.b64encode(archivo.read_bytes()).decode()


def a_numero(valor) -> int:
    """Asegura que una nota es un entero entre 0 y 100."""
    return max(0, min(100, int(valor)))


# ----------------------------------------------------------------------
# LA PÁGINA
# ----------------------------------------------------------------------

st.set_page_config(page_title="Portadas IA", page_icon="📰", layout="centered")
html(ESTILOS)

# --- Selector de país --------------------------------------------------

# El país elegido se guarda también en la dirección (…/?pais=fr), así se puede
# compartir un enlace que abra directamente un país.
pais_inicial = st.query_params.get("pais", "es")
if pais_inicial not in PAISES:
    pais_inicial = "es"

pais = st.radio(
    "País",
    list(PAISES),
    index=list(PAISES).index(pais_inicial),
    format_func=lambda codigo: PAISES[codigo],
    horizontal=True,
)
st.query_params["pais"] = pais
nombre_pais = PAISES[pais].split(" ", 1)[1]          # "España", sin la bandera

# Todo lo que viene después sale de la carpeta de ese país.
ultimo = leer_json(pais, "ultimo.json", None)
historial = leer_json(pais, "historial.json", [])

chips = ""
portadas_de = f"de {nombre_pais}"
if ultimo:
    nombres = [periodico["nombre"] for periodico in ultimo["periodicos"]]
    portadas_de = f"de {nombre_pais}: " + ", ".join(nombres[:-1]) + f" y {nombres[-1]}"
    chips = (
        '<div class="chips">'
        f'<span class="chip">🕒 Actualizado el {escape(ultimo["generado"])}</span>'
        f'<span class="chip">⏭️ Próxima: {proxima_actualizacion()}</span>'
        f'<span class="chip">🤖 {escape(ultimo["modelo"])}</span>'
        "</div>"
    )

html(
    '<div class="cabecera">'
    "<h1>📰 Portadas IA</h1>"
    f"<p>El día en cinco portadas {escape(portadas_de)}. "
    "ChatGPT las resume, mide su populismo y su sesgo, toma el pulso a la "
    "crispación con Crispito y te cuenta cómo lo ven cinco ideologías.</p>"
    f"{chips}</div>"
)

if ultimo is None:
    st.info(
        f"Todavía no hay datos de {nombre_pais}. La primera actualización automática será "
        f"{proxima_actualizacion()}."
    )
    st.stop()

# --- Crispación de hoy -------------------------------------------------

general = ultimo["general"]
crispacion = a_numero(general["crispacion"])

# Crispito tiene 6 estados (0 a 5). Repartimos la nota de 0 a 100 entre ellos:
# 0-16 → 0, 17-33 → 1, 34-49 → 2, 50-66 → 3, 67-83 → 4, 84-100 → 5.
estado = min(5, crispacion * 6 // 100)

html(
    '<div class="tarjeta">'
    '<div class="etiqueta">Crispación ahora</div>'
    '<div class="crispito">'
    f'<img src="{imagen_incrustada(f"crispito/crispito_{estado}.gif")}" '
    f'alt="Crispito: {ESTADOS_CRISPITO[estado]}">'
    '<div class="lado">'
    '<div class="dato">'
    f'<span class="numero" style="color:{color_nivel(crispacion)}">{crispacion}</span>'
    '<span class="sobre">/ 100</span>'
    "</div>"
    f'<div class="nombre">Crispito está: <b style="color:{color_nivel(crispacion)}">'
    f"{ESTADOS_CRISPITO[estado]}</b></div>"
    f'<div class="estado">Estado {estado} de 5</div>'
    "</div></div>"
    f"{barra(crispacion)}"
    f'<p style="margin-top:14px">{escape(general["motivo_crispacion"])}</p>'
    "</div>"
)

with st.expander("Conoce a Crispito y sus 6 estados"):
    st.image(str(CARPETA_CRISPITO / "estados.png"))
    st.caption(
        "De izquierda a derecha y de arriba abajo: "
        + " · ".join(f"{n} – {nombre}" for n, nombre in enumerate(ESTADOS_CRISPITO))
    )

# --- ¿Quién quieres que te dé la opinión? -------------------------------

st.subheader("¿Quién quieres que te dé la opinión?")

opiniones = ultimo.get("opiniones", [])

if opiniones:
    st.image(str(CARPETA_CARICATURAS / "todos.png"))

    # st.radio devuelve la opción elegida. Con index=None no hay ninguna marcada
    # al entrar. format_func decide el texto que se ve en cada opción.
    elegida = st.radio(
        "Elige un personaje",
        opiniones,
        index=None,
        format_func=lambda opinion: opinion["nombre"],
        horizontal=True,
        label_visibility="collapsed",
        key=f"opinion_{pais}",      # una elección distinta por país
    )

    if elegida is None:
        st.caption("Elige un personaje para leer qué opina de las noticias de hoy.")
    else:
        parrafos = "".join(
            f'<p class="parrafo">{escape(parrafo)}</p>'
            for parrafo in elegida["texto"].split("\n")
            if parrafo.strip()
        )
        html(
            '<div class="tarjeta">'
            '<div class="opinion">'
            f'<img src="{imagen_incrustada("caricaturas/" + elegida["id"] + ".png")}" alt="">'
            f'<div><div class="quien">{escape(elegida["nombre"])} opina</div>'
            '<div class="aviso">Personaje inventado · texto escrito por ChatGPT</div></div>'
            "</div>"
            f"{parrafos}"
            "</div>"
        )
    st.caption(
        "Son opiniones simuladas por una IA para mostrar cómo vería el día cada "
        "corriente de pensamiento. No son de ninguna persona real ni reflejan la "
        "opinión de esta web."
    )
else:
    st.write("Las opiniones estarán disponibles en la próxima actualización.")

# --- Resumen general ---------------------------------------------------

html(
    '<div class="tarjeta">'
    '<div class="etiqueta">Lo más repetido hoy</div>'
    f'<p>{escape(general["temas"])}</p>'
    "</div>"
)

# --- Cada periódico ----------------------------------------------------

st.subheader("Periódico a periódico")

for posicion, periodico in enumerate(ultimo["periodicos"]):
    nombre = periodico["nombre"]
    color = COLORES[posicion % len(COLORES)]
    noticias = periodico["noticias"]
    analisis = periodico["analisis"]

    # st.container(border=True) dibuja una tarjeta con todo lo que metamos dentro.
    with st.container(border=True):
        html(
            f'<div class="raya" style="background:{color}"></div>'
            f'<div class="periodico"><span class="punto" style="background:{color}">'
            f"</span>{escape(nombre)}</div>"
        )

        if not noticias or not analisis:
            st.warning(f"No se ha podido leer la portada de {nombre}.")
            st.markdown(f"[Abrir {nombre}]({periodico['web']})")
            continue

        st.markdown(analisis["resumen"])

        with st.expander(f"Ver los {len(noticias)} titulares originales"):
            for noticia in noticias:
                if noticia["enlace"]:
                    st.markdown(f"- [{noticia['titulo']}]({noticia['enlace']})")
                else:
                    st.markdown(f"- {noticia['titulo']}")

        populismo = a_numero(analisis["populismo"])
        html(
            '<div class="medidor">'
            '<div class="fila"><span class="titulo">Nivel de populismo</span>'
            f'<span class="valor" style="color:{color_nivel(populismo)}">'
            f"{populismo} / 100</span></div>"
            f"{barra(populismo)}"
            f'<div class="motivo">{escape(analisis["motivo_populismo"])}</div>'
            f'<div class="sesgo"><b>Sesgo:</b> {escape(analisis["sesgo"])}</div>'
            "</div>"
        )

# --- Crispación día a día ----------------------------------------------

st.subheader("Crispación día a día")

if historial:
    filas = ""
    for registro in reversed(historial):            # el día más reciente arriba
        dia = datetime.strptime(registro["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y")
        nota = a_numero(registro["crispacion"])
        filas += (
            "<tr>"
            f'<td class="dia">{dia}</td>'
            f'<td class="nota"><span style="color:{color_nivel(nota)}">{nota}</span>'
            f"<small> / 100</small>{barra(nota, fina=True)}</td>"
            f'<td>{escape(registro["comentario"])}</td>'
            "</tr>"
        )
    html(
        '<table class="tabla"><thead><tr>'
        "<th>Día</th><th>Nivel</th><th>Resumen del día</th>"
        f"</tr></thead><tbody>{filas}</tbody></table>"
    )
    st.caption(
        "Un registro por día. La nota es la media de las actualizaciones de ese "
        "día (0 = día tranquilo, 100 = tensión máxima)."
    )
else:
    st.write("Aún no hay ningún día registrado.")

html(
    '<div class="pie">Los resúmenes, el populismo, el sesgo y la crispación son una '
    "estimación de una IA a partir de los titulares: pueden contener errores y no "
    "son una medición objetiva. Pulsa en cada titular para leer la noticia "
    "completa en su periódico.</div>"
)
