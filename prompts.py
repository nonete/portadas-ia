"""
Portadas IA · los prompts (las instrucciones que se le dan a ChatGPT)
--------------------------------------------------------------------
Los prompts ya no están escritos dentro de actualizar.py. Están en dos
archivos de la carpeta config/:

  - config/prompts_originales.json → los textos "de fábrica", con su título,
    su explicación y las variables que deben llevar. No se toca.
  - config/prompts.json            → solo los textos que se han cambiado desde
    la página de configuración de la web. Al principio está vacío: {}

Este módulo junta los dos: usa el texto cambiado si existe y es válido, y si
no, el original. Así un error al editar nunca deja la web sin actualizar.

Las variables van entre llaves, por ejemplo {noticias}. LangChain las
sustituye por su valor antes de enviar el prompt.
"""

import json
import re
from pathlib import Path

CARPETA = Path(__file__).parent / "config"


def errores_de(texto: str, variables: list[str]) -> list[str]:
    """Comprueba un prompt. Devuelve la lista de problemas (vacía si está bien)."""
    errores = []
    if not texto.strip():
        errores.append("está vacío")
    for variable in variables:
        if "{" + variable + "}" not in texto:
            errores.append("falta {" + variable + "}")
    # Quitamos las variables permitidas; si queda alguna llave, sobra.
    resto = texto
    for variable in variables:
        resto = resto.replace("{" + variable + "}", "")
    if re.search(r"[{}]", resto):
        errores.append("tiene llaves { } que no son de una variable permitida")
    return errores


def cargar() -> dict[str, str]:
    """Devuelve {identificador: texto} con el prompt que hay que usar en cada caso."""
    originales = json.loads((CARPETA / "prompts_originales.json").read_text(encoding="utf-8"))
    archivo = CARPETA / "prompts.json"
    try:
        cambiados = json.loads(archivo.read_text(encoding="utf-8")) if archivo.exists() else {}
    except json.JSONDecodeError:
        print("Aviso: config/prompts.json no se puede leer; se usan los prompts originales.")
        cambiados = {}

    textos = {}
    for prompt in originales:
        texto = cambiados.get(prompt["id"])
        if isinstance(texto, str):
            errores = errores_de(texto, prompt["variables"])
            if errores:
                print(f"Aviso: el prompt '{prompt['id']}' cambiado no vale "
                      f"({'; '.join(errores)}). Se usa el original.")
                texto = None
        else:
            texto = None
        textos[prompt["id"]] = texto if texto is not None else prompt["texto"]
    return textos
