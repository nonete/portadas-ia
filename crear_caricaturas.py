"""
Caricaturas de los cinco opinadores
-----------------------------------
Este programa DIBUJA con código (librería Pillow) a los cinco personajes
de la sección "¿Quién quieres que te dé la opinión?" y guarda:

  caricaturas/comunista.png, anarquista.png, liberal.png,
  caricaturas/extrema_derecha.png, centro.png
  caricaturas/todos.png        → los cinco en una sola imagen

Son personajes inventados: no representan a ninguna persona real.
Solo hay que ejecutarlo si quieres cambiar los dibujos:

    python crear_caricaturas.py
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

CARPETA = Path(__file__).parent / "caricaturas"

TAM = 240        # tamaño final de cada dibujo, en píxeles
ESCALA = 4       # se dibuja 4 veces más grande y luego se reduce: bordes suaves
OSCURO = "#1e293b"


def e(valor: float) -> int:
    """Pasa una medida 'pequeña' a la medida ampliada con la que se dibuja."""
    return int(round(valor * ESCALA))


def elipse(d, cx, cy, rx, ry, relleno=None, borde=None, grosor=0):
    d.ellipse([e(cx - rx), e(cy - ry), e(cx + rx), e(cy + ry)],
              fill=relleno, outline=borde, width=e(grosor))


def linea(d, puntos, color=OSCURO, grosor=4):
    d.line([(e(x), e(y)) for x, y in puntos], fill=color, width=e(grosor), joint="curve")
    for x, y in (puntos[0], puntos[-1]):
        elipse(d, x, y, grosor / 2, grosor / 2, color)


def arco(d, cx, cy, rx, ry, inicio, fin, color=OSCURO, grosor=4):
    d.arc([e(cx - rx), e(cy - ry), e(cx + rx), e(cy + ry)],
          start=inicio, end=fin, fill=color, width=e(grosor))


def poligono(d, puntos, relleno):
    d.polygon([(e(x), e(y)) for x, y in puntos], fill=relleno)


def estrella(d, cx, cy, radio, color):
    puntos = []
    for i in range(10):
        r = radio if i % 2 == 0 else radio * 0.42
        angulo = math.radians(-90 + i * 36)
        puntos.append((cx + r * math.cos(angulo), cy + r * math.sin(angulo)))
    poligono(d, puntos, color)


# ----------------------------------------------------------------------
# PIEZAS COMUNES: todos comparten la misma cara amable
# ----------------------------------------------------------------------

def fondo_y_cuerpo(d, color_fondo, color_ropa):
    elipse(d, 120, 120, 114, 114, color_fondo)
    elipse(d, 120, 252, 92, 80, color_ropa)             # hombros


def cuello(d, piel, sombra):
    d.rectangle([e(104), e(140), e(136), e(180)], fill=piel)
    elipse(d, 120, 180, 16, 8, piel)
    arco(d, 120, 150, 18, 10, 20, 160, sombra, 3)       # sombra bajo la barbilla


def cara(d, piel, sombra, cy=112, rx=40, ry=46):
    for lado in (-1, 1):                                # orejas
        elipse(d, 120 + lado * (rx - 1), cy + 2, 8, 11, piel, sombra, 3)
    elipse(d, 120, cy, rx, ry, piel, sombra, 3)
    for lado in (-1, 1):                                # ojos y cejas
        elipse(d, 120 + lado * 16, cy - 4, 5, 5, OSCURO)
        elipse(d, 120 + lado * 16 - 2, cy - 6, 1.7, 1.7, "white")
        linea(d, [(120 + lado * 9, cy - 18), (120 + lado * 24, cy - 19)], OSCURO, 3.5)
    arco(d, 120, cy + 6, 6, 5, 30, 150, sombra, 3)      # nariz
    arco(d, 120, cy + 14, 16, 12, 20, 160, OSCURO, 4)   # sonrisa


def camisa_y_corbata(d, color_corbata):
    poligono(d, [(98, 176), (142, 176), (120, 222)], "white")
    poligono(d, [(114, 182), (126, 182), (124, 192), (116, 192)], color_corbata)
    poligono(d, [(116, 192), (124, 192), (128, 232), (120, 240), (112, 232)], color_corbata)


def solapas(d, color):
    linea(d, [(98, 176), (108, 214), (120, 226)], color, 4)
    linea(d, [(142, 176), (132, 214), (120, 226)], color, 4)


# ----------------------------------------------------------------------
# LOS CINCO PERSONAJES
# ----------------------------------------------------------------------

def comunista(d):
    piel, sombra = "#f2c9a5", "#d49a6a"
    fondo_y_cuerpo(d, "#fecaca", "#dc2626")
    cuello(d, piel, sombra)
    elipse(d, 120, 100, 44, 46, "#3f2a1d")              # pelo
    cara(d, piel, sombra)
    # Pañuelo al cuello
    poligono(d, [(92, 178), (148, 178), (120, 214)], "#991b1b")
    elipse(d, 120, 180, 9, 6, "#7f1d1d")
    # Gorra con estrella
    elipse(d, 120, 72, 50, 24, "#dc2626", "#991b1b", 3)
    elipse(d, 146, 86, 36, 9, "#991b1b")
    estrella(d, 108, 68, 11, "#fde047")


def anarquista(d):
    piel, sombra = "#e0ac84", "#b97f55"
    fondo_y_cuerpo(d, "#d1d5db", "#111827")
    elipse(d, 120, 176, 62, 26, "#1f2937")              # capucha bajada
    cuello(d, piel, sombra)
    for i, alto in enumerate((30, 40, 46, 40, 30)):     # cresta
        x = 96 + i * 12
        poligono(d, [(x - 9, 78), (x, 70 - alto), (x + 9, 78)], "#7c3aed")
    cara(d, piel, sombra)
    elipse(d, 79, 126, 3.5, 3.5, None, "#facc15", 2)    # pendiente
    linea(d, [(108, 190), (106, 216)], "#e5e7eb", 3)    # cordones de la sudadera
    linea(d, [(132, 190), (134, 216)], "#e5e7eb", 3)
    # Chapa con la A en un círculo
    elipse(d, 166, 208, 15, 15, "#dc2626")
    elipse(d, 166, 208, 10, 10, None, "white", 2.2)
    linea(d, [(159, 217), (166, 197), (173, 217)], "white", 2.5)
    linea(d, [(157, 211), (175, 209)], "white", 2.5)


def liberal(d):
    piel, sombra = "#f6d3b3", "#d9a57c"
    fondo_y_cuerpo(d, "#fef08a", "#1e3a8a")
    cuello(d, piel, sombra)
    elipse(d, 120, 98, 45, 46, "#92400e")               # pelo con raya al lado
    cara(d, piel, sombra)
    poligono(d, [(84, 84), (104, 66), (150, 68), (158, 88), (132, 76)], "#92400e")
    for lado in (-1, 1):                                # gafas
        elipse(d, 120 + lado * 16, 108, 12, 12, None, OSCURO, 3)
    linea(d, [(116, 108), (124, 108)], OSCURO, 3)
    camisa_y_corbata(d, "#eab308")
    solapas(d, "#172554")
    # Moneda
    elipse(d, 170, 208, 15, 15, "#facc15", "#ca8a04", 3)
    arco(d, 172, 208, 7, 8, 50, 310, "#854d0e", 2.5)
    linea(d, [(162, 205), (171, 205)], "#854d0e", 2)
    linea(d, [(162, 211), (171, 211)], "#854d0e", 2)


def extrema_derecha(d):
    piel, sombra = "#f2c9a5", "#d49a6a"
    fondo_y_cuerpo(d, "#cbd5e1", "#334155")
    cuello(d, piel, sombra)
    elipse(d, 120, 97, 44, 45, "#111827")               # pelo peinado hacia atrás
    cara(d, piel, sombra)
    arco(d, 120, 90, 30, 22, 200, 340, "#374151", 3)
    camisa_y_corbata(d, "#1e293b")
    solapas(d, "#1e293b")
    # Megáfono
    poligono(d, [(138, 200), (176, 182), (176, 232), (138, 216)], "#f8fafc")
    linea(d, [(138, 200), (176, 182), (176, 232), (138, 216), (138, 200)], "#475569", 3)
    d.rectangle([e(126), e(201), e(138), e(215)], fill="#f97316")
    elipse(d, 177, 207, 5, 25, "#f97316", "#c2410c", 2)
    for i, radio in enumerate((12, 20)):                # ondas de sonido
        arco(d, 184, 207, radio, radio + 6, -40, 40, "#64748b", 3)


def centro(d):
    piel, sombra = "#c98f66", "#a36b45"
    fondo_y_cuerpo(d, "#99f6e4", "#0d9488")
    elipse(d, 120, 116, 56, 62, "#57534e")              # media melena
    cuello(d, piel, sombra)
    cara(d, piel, sombra, rx=39, ry=45)
    poligono(d, [(82, 96), (92, 70), (120, 62), (148, 70), (158, 96), (138, 80), (104, 80)], "#57534e")
    # Camisa blanca bajo la chaqueta de punto
    poligono(d, [(100, 176), (140, 176), (120, 214)], "white")
    linea(d, [(100, 176), (120, 214), (140, 176)], "#0f766e", 4)
    for y in (224, 236):                                # botones
        elipse(d, 120, y, 3, 3, "#ccfbf1")
    # Chapa con una balanza
    elipse(d, 168, 208, 15, 15, "white", "#0f766e", 3)
    linea(d, [(168, 199), (168, 217)], "#0f766e", 2.2)
    linea(d, [(159, 202), (177, 202)], "#0f766e", 2.2)
    linea(d, [(163, 217), (173, 217)], "#0f766e", 2.2)
    for lado in (-1, 1):
        arco(d, 168 + lado * 9, 205, 4.5, 5, 0, 180, "#0f766e", 2.2)


PERSONAJES = {
    "comunista": comunista,
    "anarquista": anarquista,
    "liberal": liberal,
    "extrema_derecha": extrema_derecha,
    "centro": centro,
}


def dibujar(funcion) -> Image.Image:
    lado = TAM * ESCALA
    img = Image.new("RGB", (lado, lado), "white")
    funcion(ImageDraw.Draw(img))
    # Recortamos todo en forma de círculo, como una foto de perfil.
    mascara = Image.new("L", (lado, lado), 0)
    ImageDraw.Draw(mascara).ellipse([e(6), e(6), e(234), e(234)], fill=255)
    redondo = Image.composite(img, Image.new("RGB", (lado, lado), "white"), mascara)
    return redondo.resize((TAM, TAM), Image.LANCZOS)


def main() -> None:
    CARPETA.mkdir(exist_ok=True)
    tira = Image.new("RGB", (TAM * len(PERSONAJES), TAM), "white")
    for i, (nombre, funcion) in enumerate(PERSONAJES.items()):
        dibujo = dibujar(funcion)
        dibujo.save(CARPETA / f"{nombre}.png")
        tira.paste(dibujo, (i * TAM, 0))
    tira.save(CARPETA / "todos.png")
    print("Caricaturas creadas en", CARPETA)


if __name__ == "__main__":
    main()
