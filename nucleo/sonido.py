"""Sonido fisico: buffer persistente fuera del BusEventos (2026-09-06,
circulo 4a -- ver docs/superpowers/specs/2026-09-06-sonido-fisico-amenaza-design.md).

El sonido necesita sobrevivir a `bus_eventos.limpiar()` (que se ejecuta al
cierre de cada tick), asi que vive en el mundo -- dos campos efimeros en
`nucleo/celda.py:Celda` (`sonido_tick_emitido`, `sonido_magnitud`), mismo
patron que `en_llamas`. La API que se expone es generica y no sabe nada de
amenaza ni de caza: la reutilizara el circulo 4b (pista de caza para
depredadores) sin tocar este modulo.

Simplificaciones aceptadas explicitamente en el diseno:
- Ventana binaria (`duracion_sonido_ticks`): dentro de la ventana el sonido
  es audible a su alcance completo; fuera, deja de existir. Sin decaimiento
  gradual.
- `emitir_sonido` SOBRESCRIBE cualquier sonido anterior en esa celda -- no
  se acumulan varios sonidos superpuestos por celda.

Historico de decisiones: spec 4a en docs/superpowers/specs/.
"""

# Contador de observacion para la verificacion obligatoria contra
# BOSQUE_AUTO_TICKS (spec 4a): cuantos sonidos se emitieron de verdad
# durante una tanda real. Solo observacion, ningun camino de juego lo lee
# -- mismo patron que los _stats_* de los sistemas.
SONIDOS_EMITIDOS_TOTALES: int = 0


def emitir_sonido(celda, tick_actual: int, magnitud: float) -> None:
    """Registra el evento sonoro mas reciente en la celda -- sobrescribe
    cualquier sonido anterior ahi, no se acumulan varios.

    La celda es la Celda fisica del encuentro (el buffer de sonido vive en
    el mundo, no en el bus de eventos: ver docstring del modulo).
    """
    global SONIDOS_EMITIDOS_TOTALES
    celda.sonido_tick_emitido = tick_actual
    celda.sonido_magnitud = magnitud
    SONIDOS_EMITIDOS_TOTALES += 1


def _sonido_activo(celda, tick_actual: int, duracion_ticks: int) -> bool:
    return (
        celda.sonido_tick_emitido >= 0
        and (tick_actual - celda.sonido_tick_emitido) <= duracion_ticks
    )


def _radio_audible(magnitud: float, agudeza_sensorial: float, config: dict) -> float:
    """Alcance dinamico: escala linealmente con la magnitud del evento
    relativa a peso_referencia_sonido, modulado por la agudeza sensorial
    propia de quien escucha (0.5x-1.0x, nunca cero: incluso con agudeza
    minima algo se percibe si el evento es lo bastante grande)."""
    cfg = config.get("sonido", {})
    radio_base = float(cfg.get("radio_sonido_base", 3))
    peso_referencia = float(cfg.get("peso_referencia_sonido", 90.0))
    factor_sensorial = 0.5 + 0.5 * agudeza_sensorial
    return radio_base * (magnitud / peso_referencia) * factor_sensorial


def sonido_mas_cercano(
    zona, pos_x: int, pos_y: int, radio_busqueda_maxima: int,
    tick_actual: int, agudeza_sensorial: float, config: dict,
) -> tuple[int, int] | None:
    """Escanea celdas dentro de radio_busqueda_maxima (techo de
    escaneo, no el alcance real); para cada celda con sonido activo,
    calcula SU alcance audible real (segun su propia magnitud) y lo
    compara contra la distancia real. Devuelve la mas cercana que SI es
    audible, o None."""
    cfg = config.get("sonido", {})
    duracion_ticks = int(cfg.get("duracion_sonido_ticks", 5))
    mejor = None
    mejor_dist = radio_busqueda_maxima + 1
    for dy in range(-radio_busqueda_maxima, radio_busqueda_maxima + 1):
        for dx in range(-radio_busqueda_maxima, radio_busqueda_maxima + 1):
            nx, ny = pos_x + dx, pos_y + dy
            if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
                continue
            celda = zona.obtener_celda(nx, ny)
            if not _sonido_activo(celda, tick_actual, duracion_ticks):
                continue
            dist = abs(dx) + abs(dy)
            alcance = _radio_audible(celda.sonido_magnitud, agudeza_sensorial, config)
            if dist <= alcance and dist < mejor_dist:
                mejor = (nx, ny)
                mejor_dist = dist
    return mejor
