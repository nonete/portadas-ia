"""
Portadas IA · la web
--------------------
Esta página solo ENSEÑA los datos. No llama a los periódicos ni a ChatGPT:
de eso se encarga actualizar.py, que GitHub ejecuta a las 8:00, 11:00,
14:00, 17:00 y 20:00 y deja el resultado en la carpeta datos/.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

HORAS = [8, 11, 14, 17, 20]     # las mismas que en actualizar.py
CARPETA = Path(__file__).parent / "datos"


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


st.set_page_config(page_title="Portadas IA", page_icon="📰", layout="centered")

st.title("📰 Portadas IA")
st.caption(
    "Resumen automático de las portadas de El País, El Mundo, ABC, Público y "
    "OKdiario, hecho con LangChain y ChatGPT."
)

ultimo = leer_json("ultimo.json", None)
historial = leer_json("historial.json", [])

if ultimo is None:
    st.info(
        "Todavía no hay datos. La primera actualización automática será "
        f"{proxima_actualizacion()}."
    )
    st.stop()

st.caption(
    f"Actualizado el {ultimo['generado']} · próxima actualización: "
    f"{proxima_actualizacion()} · modelo: {ultimo['modelo']}"
)

# ----------------------------------------------------------------------
# RESUMEN GENERAL
# ----------------------------------------------------------------------

general = ultimo["general"]
st.subheader("Lo más repetido hoy")
st.write(general["temas"])

# ----------------------------------------------------------------------
# CADA PERIÓDICO
# ----------------------------------------------------------------------

for periodico in ultimo["periodicos"]:
    st.divider()
    st.subheader(periodico["nombre"])
    noticias = periodico["noticias"]
    analisis = periodico["analisis"]
    if not noticias or not analisis:
        st.warning(f"No se ha podido leer la portada de {periodico['nombre']}.")
        st.markdown(f"[Abrir {periodico['nombre']}]({periodico['web']})")
        continue

    st.markdown(analisis["resumen"])
    with st.expander(f"Ver los {len(noticias)} titulares originales"):
        for noticia in noticias:
            if noticia["enlace"]:
                st.markdown(f"- [{noticia['titulo']}]({noticia['enlace']})")
            else:
                st.markdown(f"- {noticia['titulo']}")

    # Barra de populismo: st.progress acepta un número de 0 a 100.
    populismo = max(0, min(100, int(analisis["populismo"])))
    st.markdown(f"**Nivel de populismo: {populismo} / 100**")
    st.progress(populismo)
    st.caption(analisis["motivo_populismo"])
    st.markdown(f"**Sesgo:** {analisis['sesgo']}")

# ----------------------------------------------------------------------
# CRISPACIÓN DÍA A DÍA
# ----------------------------------------------------------------------

st.divider()
st.subheader("Crispación día a día")

if historial:
    tabla = pd.DataFrame(
        [
            {
                "Día": datetime.strptime(registro["fecha"], "%Y-%m-%d").strftime("%d/%m/%Y"),
                "Crispación": registro["crispacion"],
                "Resumen": registro["comentario"],
            }
            for registro in reversed(historial)      # el día más reciente arriba
        ]
    )
    st.dataframe(
        tabla,
        hide_index=True,
        column_config={
            "Crispación": st.column_config.ProgressColumn(
                "Crispación", min_value=0, max_value=100, format="%d"
            ),
            "Resumen": st.column_config.TextColumn("Resumen", width="large"),
        },
    )
    st.caption(
        "Un registro por día. La nota es la media de las actualizaciones de ese "
        "día (0 = día tranquilo, 100 = tensión máxima)."
    )
else:
    st.write("Aún no hay ningún día registrado.")

st.divider()
st.caption(
    "Los resúmenes, el populismo, el sesgo y la crispación son una estimación de "
    "una IA a partir de los titulares: pueden contener errores y no son una "
    "medición objetiva. Pulsa en cada titular para leer la noticia completa en "
    "su periódico."
)
