"""
Crispito · la mascota de la crispación
--------------------------------------
Este programa DIBUJA a Crispito con código (librería Pillow) y guarda:

  crispito/crispito_0.gif … crispito_5.gif   → un GIF animado por estado
  crispito/estados.png                       → los seis estados en una imagen

Solo hay que ejecutarlo si quieres cambiar el dibujo:

    python crear_crispito.py

La web (app.py) no dibuja nada: solo enseña el GIF que toca.
"""

import math
from pathlib import Path

from PIL import Image, ImageDraw

CARPETA = Path(__file__).parent / "crispito"

TAM = 240            # tamaño final del GIF, en píxeles
ESCALA = 4           # se dibuja 4 veces más grande y luego se reduce: bordes suaves
FOTOGRAMAS = 16      # dibujos que forman la animación
MILISEGUNDOS = 70    # lo que dura cada dibujo

NOMBRES = ["Zen", "Tranquilo", "Mosqueado", "Molesto", "Enfadado", "¡A punto de estallar!"]

# Un color de cuerpo por estado: de verde agua (calma) a rojo (máxima crispación).
CUERPO = ["#5eead4", "#86efac", "#fde047", "#fdba74", "#f87171", "#dc2626"]
BORDE = ["#0f766e", "#15803d", "#a16207", "#c2410c", "#b91c1c", "#7f1d1d"]
BRILLO = ["#ccfbf1", "#dcfce7", "#fef9c3", "#ffedd5", "#fecaca", "#f87171"]

OSCURO = "#1e293b"
N_PELOS = [1, 2, 3, 4, 5, 7]            # cuantos más nervios, más pelos de punta
ALTO_PELO = [12, 16, 22, 30, 40, 54]
TEMBLOR = [0, 0, 0, 1.5, 3, 6]          # cuánto tiembla
CEJA = [0, 0, 0, 6, 11, 15]             # inclinación de las cejas


def e(valor: float) -> int:
    """Pasa una medida 'pequeña' a la medida ampliada con la que se dibuja."""
    return int(round(valor * ESCALA))


def elipse(d, cx, cy, rx, ry, relleno, borde=None, grosor=0):
    d.ellipse([e(cx - rx), e(cy - ry), e(cx + rx), e(cy + ry)],
              fill=relleno, outline=borde, width=e(grosor))


def linea(d, puntos, color=OSCURO, grosor=5):
    d.line([(e(x), e(y)) for x, y in puntos], fill=color, width=e(grosor), joint="curve")
    for x, y in (puntos[0], puntos[-1]):          # puntas redondeadas
        elipse(d, x, y, grosor / 2, grosor / 2, color)


def arco(d, cx, cy, rx, ry, inicio, fin, color=OSCURO, grosor=5):
    d.arc([e(cx - rx), e(cy - ry), e(cx + rx), e(cy + ry)],
          start=inicio, end=fin, fill=color, width=e(grosor))


def triangulo(d, puntos, relleno, borde=None, grosor=0):
    d.polygon([(e(x), e(y)) for x, y in puntos], fill=relleno)
    if borde:
        linea(d, puntos + [puntos[0]], borde, grosor)


def dibujar(nivel: int, f: int) -> Image.Image:
    """Dibuja a Crispito en el estado `nivel` (0-5) y el fotograma `f`."""
    img = Image.new("RGB", (TAM * ESCALA, TAM * ESCALA), "white")
    d = ImageDraw.Draw(img)

    # 'fase' da una vuelta completa a lo largo de la animación, así el GIF
    # empieza y acaba igual y se repite sin saltos.
    fase = 2 * math.pi * f / FOTOGRAMAS
    avance = f / FOTOGRAMAS

    # Movimiento: los estados tranquilos respiran, los crispados tiemblan.
    dx = TEMBLOR[nivel] * math.sin(fase * 4)
    dy = [3, 3, 2, 1, 0, 0][nivel] * math.sin(fase) + TEMBLOR[nivel] * 0.5 * math.cos(fase * 3)
    cx, cy, r = 120 + dx, 140 + dy, 64
    respira = [2.5, 2, 1, 0.5, 0, 0][nivel] * math.sin(fase)
    rx, ry = r - respira * 0.5, r + respira

    cuerpo, borde = CUERPO[nivel], BORDE[nivel]

    # Sombra en el suelo
    elipse(d, 120, 216, 58, 9, "#e2e8f0")

    # Vapor (estados 4 y 5): bolitas que suben a los lados
    if nivel >= 4:
        for lado in (-1, 1):
            for k in range(3):
                p = (avance + k / 3) % 1
                gris = ["#94a3b8", "#cbd5e1", "#e2e8f0"][min(2, int(p * 3))]
                elipse(d, 120 + lado * (r + 22 + p * 10), 120 - p * 62,
                       5 + p * (5 + nivel), 5 + p * (5 + nivel), "white", gris, 3)

    # Pelos de punta (detrás del cuerpo). En el estado 5 son llamas.
    n = N_PELOS[nivel]
    for i in range(n):
        angulo = 0 if n == 1 else math.radians(-50 + 100 * i / (n - 1))
        alto = ALTO_PELO[nivel] + (nivel >= 3) * 4 * math.sin(fase * 2 + i * 1.7)
        bx, by = cx + (r - 6) * math.sin(angulo), cy - (r - 6) * math.cos(angulo)
        px, py = cx + (r + alto) * math.sin(angulo), cy - (r + alto) * math.cos(angulo)
        ancho = 9 if nivel < 5 else 12
        ux, uy = math.cos(angulo) * ancho, math.sin(angulo) * ancho
        base = [(bx - ux, by - uy), (px, py), (bx + ux, by + uy)]
        if nivel == 5:
            triangulo(d, base, "#f59e0b", "#c2410c", 3)
            mx, my = (bx + px) / 2, (by + py) / 2
            triangulo(d, [(bx - ux * 0.45, by - uy * 0.45), (mx, my), (bx + ux * 0.45, by + uy * 0.45)], "#fde047")
        else:
            triangulo(d, base, borde, borde, 3)

    # Pies
    for lado in (-1, 1):
        elipse(d, cx + lado * 26, 140 + r + 4, 15, 9, borde)

    # Manos: a los lados, o en alto con los puños cerrados en el estado 5
    for lado in (-1, 1):
        if nivel == 5:
            elipse(d, cx + lado * (r + 6), cy - 26 + 3 * math.sin(fase * 4 + lado), 12, 12, cuerpo, borde, 4)
        else:
            elipse(d, cx + lado * (r - 1), cy + 20, 10, 12, cuerpo, borde, 4)

    # Cuerpo y brillo
    elipse(d, cx, cy, rx, ry, cuerpo, borde, 5)
    elipse(d, cx - 30, cy - 36, 14, 8, BRILLO[nivel])

    # Mofletes en los estados tranquilos
    if nivel <= 1:
        for lado in (-1, 1):
            elipse(d, cx + lado * 40, cy + 12, 9, 6, "#fda4af")

    # ---- Ojos ----
    oy = cy - 8
    parpadeo = nivel in (1, 2, 3) and f in (9, 10)
    for lado in (-1, 1):
        ox = cx + lado * 24
        if nivel == 0:
            arco(d, ox, oy - 4, 11, 9, 20, 160)                    # ojos cerrados
        elif parpadeo:
            linea(d, [(ox - 9, oy), (ox + 9, oy)])
        elif nivel == 5:
            elipse(d, ox, oy, 13, 13, "white", OSCURO, 4)           # ojos desorbitados
            elipse(d, ox + dx * 0.3, oy, 4, 4, OSCURO)
        else:
            tam = 9 if nivel < 4 else 8
            elipse(d, ox, oy, tam, tam, OSCURO)
            elipse(d, ox - 3, oy - 3, 3, 3, "white")

    # ---- Cejas ----
    if nivel == 2:                                                  # una ceja levantada
        linea(d, [(cx - 36, oy - 20), (cx - 13, oy - 20)])
        linea(d, [(cx + 13, oy - 24), (cx + 36, oy - 31)])
    elif nivel >= 3:                                                # ceño fruncido
        k = CEJA[nivel]
        grosor = 5 if nivel == 3 else 7
        alto = oy - (24 if nivel < 5 else 30)
        linea(d, [(cx - 38, alto), (cx - 11, alto + k)], grosor=grosor)
        linea(d, [(cx + 11, alto + k), (cx + 38, alto)], grosor=grosor)

    # ---- Boca ----
    by = cy + 26
    if nivel == 0:
        arco(d, cx, by - 8, 12, 9, 20, 160)                         # sonrisa pequeña
    elif nivel == 1:
        arco(d, cx, by - 12, 22, 16, 15, 165)                       # sonrisa grande
    elif nivel == 2:
        linea(d, [(cx - 14, by), (cx + 14, by - 2)])                # boca recta
    elif nivel == 3:
        arco(d, cx, by + 10, 18, 13, 200, 340)                      # boca hacia abajo
    elif nivel == 4:                                                # dientes apretados
        d.rounded_rectangle([e(cx - 22), e(by - 9), e(cx + 22), e(by + 9)],
                            radius=e(5), fill="white", outline=OSCURO, width=e(4))
        for x in (-11, 0, 11):
            linea(d, [(cx + x, by - 7), (cx + x, by + 7)], grosor=3)
        linea(d, [(cx - 20, by), (cx + 20, by)], grosor=3)
    else:                                                           # grito
        abre = 15 + 3 * math.sin(fase * 4)
        elipse(d, cx, by + 2, 20, abre, "#450a0a", OSCURO, 4)
        elipse(d, cx, by + abre - 5, 11, 5, "#fb7185")

    # ---- Detalles de cada estado ----
    if nivel == 0:                                                  # zzz: está dormido
        for k, tam in enumerate((6, 9, 12)):
            zx = 120 + 62 + k * 15
            zy = 82 - k * 20 - 3 * math.sin(fase + k)
            linea(d, [(zx, zy), (zx + tam, zy), (zx, zy + tam), (zx + tam, zy + tam)],
                  "#64748b", 3)
    if nivel == 3:                                                  # gota de sudor
        gx, gy = cx + 50, cy - 46 + avance * 16
        triangulo(d, [(gx - 6, gy), (gx, gy - 13), (gx + 6, gy)], "#38bdf8")
        elipse(d, gx, gy + 1, 6.5, 6.5, "#38bdf8")
        elipse(d, gx - 2, gy, 2, 2, "#e0f2fe")

    return img.resize((TAM, TAM), Image.LANCZOS)


def main() -> None:
    CARPETA.mkdir(exist_ok=True)

    for nivel in range(6):
        dibujos = [dibujar(nivel, f) for f in range(FOTOGRAMAS)]
        # Un GIF solo admite 256 colores: usamos la misma paleta en todos los dibujos.
        paleta = dibujos[0].quantize(colors=64)
        dibujos = [dibujo.quantize(palette=paleta, dither=Image.Dither.NONE) for dibujo in dibujos]
        # Al reducir colores el blanco queda algo grisáceo: lo dejamos blanco puro
        # para que el fondo del GIF no se note sobre la tarjeta blanca.
        for dibujo in dibujos:
            colores = dibujo.getpalette()
            for i in range(0, len(colores), 3):
                if min(colores[i:i + 3]) >= 248:          # casi blanco → blanco
                    colores[i:i + 3] = [255, 255, 255]
            dibujo.putpalette(colores)
        dibujos[0].save(
            CARPETA / f"crispito_{nivel}.gif",
            save_all=True,
            append_images=dibujos[1:],
            duration=MILISEGUNDOS,
            loop=0,              # 0 = se repite sin parar
            optimize=True,
        )

    # Una sola imagen con los seis estados, uno al lado del otro.
    tira = Image.new("RGB", (TAM * 3, TAM * 2), "white")
    for nivel in range(6):
        tira.paste(dibujar(nivel, 4), ((nivel % 3) * TAM, (nivel // 3) * TAM))
    tira.save(CARPETA / "estados.png")

    print("Crispito creado en", CARPETA)


if __name__ == "__main__":
    main()
