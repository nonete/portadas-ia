"""
Portadas IA · la sección Discapacidad de la web
-----------------------------------------------
app.py llama a mostrar() cuando se elige "Discapacidad" en el selector de arriba.
Igual que el resto de la web, solo ENSEÑA datos: los prepara
actualizar_discapacidad.py y los deja en datos/discapacidad/ultimo.json.

Las noticias se reparten en cuatro bloques según su antigüedad, sin repetirse:
hoy (últimas 24 horas), últimas dos semanas, último mes y último año.
"""

import json
from datetime import datetime
from html import escape
from pathlib import Path
from zoneinfo import ZoneInfo

import streamlit as st

ARCHIVO = Path(__file__).parent / "datos" / "discapacidad" / "ultimo.json"
MADRID = ZoneInfo("Europe/Madrid")

# Los cuatro bloques, en el orden en que salen: (clave, título, explicación).
BLOQUES = [
    ("hoy", "Noticias de hoy", "Publicadas en las últimas 24 horas."),
    ("semanas", "Últimas semanas", "De las dos últimas semanas, sin contar las de hoy."),
    ("mes", "Último mes", "De hace entre dos semanas y un mes."),
    ("anio", "Último año", "De hace entre un mes y un año."),
]
VISIBLES = 8        # noticias que se ven sin desplegar en cada bloque


def periodo(fecha: datetime, ahora: datetime) -> str | None:
    """A qué bloque pertenece una noticia según su antigüedad.
    Es la misma regla que usa actualizar_discapacidad.py."""
    dias = (ahora - fecha).total_seconds() / 86400
    if dias < -1 or dias > 365:
        return None
    if dias <= 1:
        return "hoy"
    if dias <= 14:
        return "semanas"
    if dias <= 30:
        return "mes"
    return "anio"


def html(codigo: str) -> None:
    st.markdown(codigo, unsafe_allow_html=True)


def lista_de_noticias(noticias: list[dict]) -> str:
    """HTML de una lista de noticias: titular con enlace, medio y fecha."""
    filas = ""
    for noticia in noticias:
        fecha = datetime.fromisoformat(noticia["fecha"]).astimezone(MADRID)
        filas += (
            "<li>"
            f'<a href="{escape(noticia["enlace"], quote=True)}" target="_blank" '
            f'rel="noopener">{escape(noticia["titulo"])}</a>'
            f'<div class="meta"><b>{escape(noticia["medio"])}</b> · '
            f"{fecha:%d/%m/%Y}</div>"
            "</li>"
        )
    return f'<ul class="noticias">{filas}</ul>'


def mostrar(proxima: str) -> None:
    """Pinta la sección. 'proxima' es el texto de la próxima actualización."""
    datos = json.loads(ARCHIVO.read_text(encoding="utf-8")) if ARCHIVO.exists() else None

    chips = ""
    if datos:
        chips = (
            '<div class="chips">'
            f'<span class="chip">🕒 Actualizado el {escape(datos["generado"])}</span>'
            f'<span class="chip">⏭️ Próxima: {proxima}</span>'
            f'<span class="chip">📰 {len(datos["noticias"])} noticias de '
            f'{len(datos["medios"])} medios</span>'
            "</div>"
        )
    html(
        '<div class="cabecera">'
        "<h1>♿ Discapacidad en la prensa</h1>"
        "<p>Lo que publican los medios españoles sobre discapacidad: hoy, en las "
        "últimas semanas, en el último mes y en el último año. ChatGPT resume de "
        "qué se está hablando.</p>"
        f"{chips}</div>"
    )

    if datos is None:
        st.info(f"Todavía no hay datos de esta sección. La primera actualización será {proxima}.")
        return

    # Se reparten las noticias en los cuatro bloques según la hora actual, así
    # una noticia de "hoy" pasa sola a "últimas semanas" al día siguiente.
    ahora = datetime.now(MADRID)
    por_bloque = {clave: [] for clave, _, _ in BLOQUES}
    for noticia in datos["noticias"]:
        clave = periodo(datetime.fromisoformat(noticia["fecha"]), ahora)
        if clave:
            por_bloque[clave].append(noticia)

    def bloque(clave: str, titulo: str, explicacion: str) -> None:
        noticias = por_bloque[clave]
        st.subheader(f"{titulo} ({len(noticias)})")
        st.caption(explicacion)
        if not noticias:
            st.write("No hay noticias en este periodo.")
            return
        html(lista_de_noticias(noticias[:VISIBLES]))
        if len(noticias) > VISIBLES:
            with st.expander(f"Ver {len(noticias) - VISIBLES} noticias más"):
                html(lista_de_noticias(noticias[VISIBLES:]))

    # --- Noticias de hoy ---
    bloque(*BLOQUES[0])

    # --- Resumen de la IA ---
    resumen = datos.get("resumen")
    if resumen:
        parrafos = "".join(
            f'<p class="parrafo">{escape(parrafo)}</p>'
            for parrafo in resumen["resumen"].split("\n")
            if parrafo.strip()
        )
        temas = "".join(
            f"<li><b>{escape(tema['titulo'])}.</b> {escape(tema['explicacion'])}</li>"
            for tema in resumen.get("temas", [])
        )
        html(
            '<div class="tarjeta">'
            '<div class="etiqueta">De qué se está hablando en España · resumen de la IA</div>'
            f"{parrafos}"
            f'<ul class="temas">{temas}</ul>'
            "</div>"
        )
    else:
        st.info("El resumen de la IA estará disponible en la próxima actualización.")

    # --- Últimas semanas, último mes y último año ---
    for datos_bloque in BLOQUES[1:]:
        bloque(*datos_bloque)

    # --- Medios ---
    with st.expander(f"Los {len(datos['medios'])} medios de los que hay noticias"):
        st.write(" · ".join(datos["medios"]))

    html(
        '<div class="pie">Las noticias se buscan automáticamente en Google Noticias, '
        "Bing Noticias y el RSS de los periódicos, y se quedan solo las de medios "
        "españoles. El resumen lo escribe una IA a partir de los titulares: puede "
        "contener errores. Pulsa en cada titular para leer la noticia en su medio "
        "(se abre en otra pestaña).</div>"
    )
