"""
Portadas IA · la web
--------------------
Esta página solo ENSEÑA los datos. No llama a los periódicos ni a ChatGPT:
de eso se encarga actualizar.py, que GitHub ejecuta a las 8:00, 11:00,
14:00, 17:00 y 20:00 y deja el resultado en la carpeta datos/.

Los colores generales (fondo claro, color principal…) están en
.streamlit/config.toml. El resto del diseño está en el bloque ESTILOS.
"""

import json
from datetime import datetime, timedelta
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

HORAS = [8, 11, 14, 17, 20]     # las mismas que en actualizar.py
CARPETA = Path(__file__).parent / "datos"

# Un color para distinguir cada periódico (es solo decorativo).
COLORES = {
    "El País": "#2563eb",
    "El Mundo": "#0d9488",
    "ABC": "#d97706",
    "Público": "#c026d3",
    "OKdiario": "#4f46e5",
}
COLOR_POR_DEFECTO = "#475569"

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

def leer_json(nombre: str, por_defecto):
    """Lee un archivo de la carpeta datos/; si no existe devuelve el valor por defecto."""
    archivo = CARPETA / nombre
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


def a_numero(valor) -> int:
    """Asegura que una nota es un entero entre 0 y 100."""
    return max(0, min(100, int(valor)))


# ----------------------------------------------------------------------
# LA PÁGINA
# ----------------------------------------------------------------------

st.set_page_config(page_title="Portadas IA", page_icon="📰", layout="centered")
html(ESTILOS)

ultimo = leer_json("ultimo.json", None)
historial = leer_json("historial.json", [])

chips = ""
if ultimo:
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
    "<p>Las portadas de El País, El Mundo, ABC, Público y OKdiario, resumidas y "
    "analizadas con LangChain y ChatGPT.</p>"
    f"{chips}</div>"
)

if ultimo is None:
    st.info(
        "Todavía no hay datos. La primera actualización automática será "
        f"{proxima_actualizacion()}."
    )
    st.stop()

# --- Crispación de hoy -------------------------------------------------

general = ultimo["general"]
crispacion = a_numero(general["crispacion"])

html(
    '<div class="tarjeta">'
    '<div class="etiqueta">Crispación ahora</div>'
    '<div class="dato">'
    f'<span class="numero" style="color:{color_nivel(crispacion)}">{crispacion}</span>'
    '<span class="sobre">/ 100</span>'
    f'<span class="nivel" style="background:{color_nivel(crispacion)}">'
    f"{texto_nivel(crispacion)}</span>"
    "</div>"
    f"{barra(crispacion)}"
    f'<p style="margin-top:14px">{escape(general["motivo_crispacion"])}</p>'
    "</div>"
)

# --- Resumen general ---------------------------------------------------

html(
    '<div class="tarjeta">'
    '<div class="etiqueta">Lo más repetido hoy</div>'
    f'<p>{escape(general["temas"])}</p>'
    "</div>"
)

# --- Cada periódico ----------------------------------------------------

st.subheader("Periódico a periódico")

for periodico in ultimo["periodicos"]:
    nombre = periodico["nombre"]
    color = COLORES.get(nombre, COLOR_POR_DEFECTO)
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
