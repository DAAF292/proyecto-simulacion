"""Campo continuo: primitiva generica para generar una magnitud suave y
determinista sobre el grid (fase terreno 2, elevacion -- y reutilizada en
fase terreno 3 para lluvia y temperatura, mismo mecanismo, tres
instancias distintas en vez de tres tecnicas de generacion diferentes).

Los algoritmos de generacion que ya existian en zona_bioma.py
(_generar_rio: paseo aleatorio; _generar_manchas: flood-fill
probabilistico) son ambos DISCRETOS -- deciden, celda a celda, si
pertenece o no a un conjunto. Ninguno sirve para una magnitud que varia
de forma continua y suave por el espacio (una celda de elevacion 0.52
junto a una de 0.55, no un salto abrupto), que es justo lo que elevacion/
lluvia/temperatura necesitan como fundamento fisico para fase 3.

Tecnica elegida: "value noise" por interpolacion bilineal de un grid
grueso aleatorio -- no ruido Perlin/Simplex (mas suave y sin la ligera
direccionalidad de la retícula, pero bastante mas complejo de implementar
correctamente desde cero) ni diamond-square (exige un grid de lado
2^n+1, no encaja con un grid arbitrario como el actual 20x20 sin recortar
o rellenar). Value noise es la opcion mas simple que sigue dando colinas/
zonas suaves reales, coherente con "no optimices por anticipacion" y con
que esto es una implementacion propia con fines de aprendizaje (stack
decidido, informe tecnico): un algoritmo simple y correcto vale mas aqui
que uno sofisticado a medias.

Determinista: recibe siempre el rng ya sembrado de quien la llama (nunca
crea su propio Random()), mismo principio que el resto de
nucleo/zona_bioma.py -- la generacion del mundo entero cuelga de una
unica semilla.
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
