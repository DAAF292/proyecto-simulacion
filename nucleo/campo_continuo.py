"""Campo continuo: primitiva genérica para generar una magnitud suave y
determinista sobre el grid -- usada para elevación, lluvia y
temperatura, mismo mecanismo, tres instancias distintas en vez de tres
técnicas de generación diferentes.

A diferencia de los algoritmos DISCRETOS de generación (paseo aleatorio,
flood-fill probabilístico -- deciden, celda a celda, si pertenece o no
a un conjunto), esto sirve para una magnitud que varía de forma
continua y suave por el espacio (una celda de elevación 0.52 junto a
una de 0.55, no un salto abrupto).

Técnica: "value noise" por interpolación bilineal de un grid grueso
aleatorio -- más simple que Perlin/Simplex o diamond-square, sigue
dando colinas/zonas suaves reales sin la complejidad de implementarlos
correctamente desde cero.

Determinista: recibe siempre el rng ya sembrado de quien la llama
(nunca crea su propio Random()) -- la generación del mundo entero
cuelga de una única semilla.

Historial de diseño y decisiones: docs/historial_nucleo.md.
"""
import random


def generar_campo(rng: random.Random, ancho: int, alto: int, escala_celdas: int) -> list:
    """Devuelve una matriz campo[x][y] -> float en [0, 1], continua y
    determinista.

    escala_celdas: separacion (en celdas del grid fino) entre los puntos
    del grid grueso sobre el que se sortean valores aleatorios -- cuanto
    mayor, mas suaves y extensas las colinas resultantes (menos "ruido",
    mas "paisaje"). Un grid grueso de solo 1x1 punto (mapas mas pequenos
    que escala_celdas) degenera a un unico valor uniforme en todo el
    mapa -- caso limite valido, no un error.
    """
    puntos_x = max(2, ancho // escala_celdas + 2)
    puntos_y = max(2, alto // escala_celdas + 2)
    grueso = [[rng.random() for _ in range(puntos_y)] for _ in range(puntos_x)]

    def _suavizar(t: float) -> float:
        # interpolacion suave (smoothstep, 3t^2 - 2t^3) en vez de lineal
        # pura -- evita el efecto "rombos" caracteristico de interpolar
        # bilinealmente sin suavizado, a coste minimo.
        return t * t * (3 - 2 * t)

    campo = [[0.0] * alto for _ in range(ancho)]
    for x in range(ancho):
        gx = x / escala_celdas
        ix = int(gx)
        fx = _suavizar(gx - ix)
        for y in range(alto):
            gy = y / escala_celdas
            iy = int(gy)
            fy = _suavizar(gy - iy)

            v00 = grueso[ix][iy]
            v10 = grueso[ix + 1][iy]
            v01 = grueso[ix][iy + 1]
            v11 = grueso[ix + 1][iy + 1]

            arriba = v00 * (1 - fx) + v10 * fx
            abajo = v01 * (1 - fx) + v11 * fx
            campo[x][y] = arriba * (1 - fy) + abajo * fy

    return campo
