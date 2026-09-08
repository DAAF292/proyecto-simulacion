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

**Registro de celdas candidatas (2026-09-08)**: `sonido_mas_cercano`
escaneaba antes un cuadrado de radio^2 celdas por llamada -- perfilado
real (ver docs/superpowers/specs/2026-09-08-indice-espacial-design.md,
"fuera de alcance" de ese circulo, resuelto aqui aparte) mostro que la
inmensa mayoria de esas celdas nunca tienen sonido activo (dura solo
`duracion_sonido_ticks`). `ZonaBioma.sonidos_activos` (un `set` de
coordenadas) sustituye ese escaneo por una lista corta de "donde mirar" --
`emitir_sonido` la alimenta, `sonido_mas_cercano` la auto-poda (una
entrada expirada se descarta la primera vez que se consulta). Celda
sigue siendo la fuente real de tick/magnitud -- el set solo indica
coordenadas candidatas, evita duplicar el dato.

Historico de decisiones: spec 4a en docs/superpowers/specs/.
"""

# Contador de observacion para la verificacion obligatoria contra
# BOSQUE_AUTO_TICKS (spec 4a): cuantos sonidos se emitieron de verdad
# durante una tanda real. Solo observacion, ningun camino de juego lo lee
# -- mismo patron que los _stats_* de los sistemas.
SONIDOS_EMITIDOS_TOTALES: int = 0


def emitir_sonido(zona, pos_x: int, pos_y: int, tick_actual: int, magnitud: float) -> None:
    """Registra el evento sonoro mas reciente en la celda (pos_x, pos_y)
    de `zona` -- sobrescribe cualquier sonido anterior ahi, no se
    acumulan varios.

    zona/pos_x/pos_y (2026-09-08, antes solo recibia la Celda): hace
    falta la coordenada, no solo el objeto Celda, para poder registrarla
    en `zona.sonidos_activos` (ver docstring del modulo)."""
    global SONIDOS_EMITIDOS_TOTALES
    celda = zona.obtener_celda(pos_x, pos_y)
    celda.sonido_tick_emitido = tick_actual
    celda.sonido_magnitud = magnitud
    zona.sonidos_activos.add((pos_x, pos_y))
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
    if peso_referencia <= 0.0:
        # Config invalida (fix 2026-09-07): peso_referencia_sonido es
        # PROVISIONAL y se recalibra a menudo en este proyecto -- un valor
        # de 0 o negativo no debe tumbar el tick entero con
        # ZeroDivisionError, se trata como "nada audible".
        return 0.0
    factor_sensorial = 0.5 + 0.5 * agudeza_sensorial
    return radio_base * (magnitud / peso_referencia) * factor_sensorial


def sonido_mas_cercano(
    zona, pos_x: int, pos_y: int, radio_busqueda_maxima: int,
    tick_actual: int, agudeza_sensorial: float, config: dict,
) -> tuple[int, int] | None:
    """Busca en zona.sonidos_activos (registro pequeño de "donde mirar",
    ver docstring del modulo) en vez de escanear las radio_busqueda_maxima^2
    celdas del vecindario -- para cada candidato con sonido activo,
    calcula SU alcance audible real (segun su propia magnitud) y lo
    compara contra la distancia real (acotada a radio_busqueda_maxima,
    mismo techo de escaneo que antes). Devuelve la mas cercana que SI es
    audible, o None.

    Auto-poda: cualquier candidato ya expirado se descarta del registro
    en esta misma llamada -- no hace falta un barrido aparte."""
    cfg = config.get("sonido", {})
    duracion_ticks = int(cfg.get("duracion_sonido_ticks", 5))
    mejor = None
    mejor_dist = radio_busqueda_maxima + 1
    expirados = []
    for (cx, cy) in zona.sonidos_activos:
        celda = zona.obtener_celda(cx, cy)
        if not _sonido_activo(celda, tick_actual, duracion_ticks):
            expirados.append((cx, cy))
            continue
        dist = abs(cx - pos_x) + abs(cy - pos_y)
        if dist > radio_busqueda_maxima:
            continue
        alcance = _radio_audible(celda.sonido_magnitud, agudeza_sensorial, config)
        if dist <= alcance and dist < mejor_dist:
            mejor = (cx, cy)
            mejor_dist = dist
    for clave in expirados:
        zona.sonidos_activos.discard(clave)
    return mejor
