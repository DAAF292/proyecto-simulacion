# Sonido físico — infraestructura y detección temprana de amenaza (4a) — diseño

Fecha: 2026-09-06. Círculo 4a de la cuarta pieza descompuesta del
informe externo de "capa de comunicación" (ver
`docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md` para el
contexto completo de la descomposición). Partida en dos círculos por
decisión explícita de Diego, dado el tamaño real de la pieza completa
(comparable a "armas primitivas v2", la única pieza del proyecto que
agotó los 3 intentos del pipeline por timeout) — mismo criterio ya
usado con "pareja estable" (4a escritura / 4b lectura). Este círculo
(4a) es la infraestructura de sonido en sí + su primer consumidor
(detección temprana de amenaza, el objetivo central del informe
original). El círculo 4b (pista de caza para depredadores, idea de
Diego) depende de que `nucleo/sonido.py` ya exista, y se diseña/entrega
por separado — ver
`docs/superpowers/specs/2026-09-06-sonido-fisico-caza-design.md`.

Sin dependencia de conflicto verbal / memoria espacial compartida /
ocio consciente (ya cerradas, PR #20/#21/#22), ni de reputación-rumor
(pieza futura del mismo informe).

## Motivación y hallazgo de diseño clave

El informe original proponía sonido como `Evento(severidad=RUIDO)` del
`BusEventos` existente — **descartado en la auditoría inicial**:
`bus_eventos.limpiar()` se ejecuta al cierre de cada tick, así que un
`Evento` normal nunca sobrevive para influir una decisión del tick
siguiente. El sonido necesita su propio buffer persistente, fuera del
bus de eventos.

**Hallazgo real al explorar el código**: `nucleo/amenaza.py:
posicion_amenaza_mas_cercana` ya generaliza "de qué huye un individuo"
combinando dos fuentes (amenaza por criatura, amenaza ambiental —hoy
solo fuego—), con **tres consumidores reales ya conectados**: drenaje
de `Necesidades.seguridad`, dirección de HUIR, y deseo de empuñar arma.
El propio docstring del módulo anticipa esta extensión ("un futuro
segundo tipo de desastre... solo añade un término más al `or`"). El
sonido puede ser una TERCERA fuente ahí, heredando gratis los tres
consumidores sin cablear nada nuevo.

**Ampliación pedida por Diego, en conversación**: (1) el alcance debe
ser dinámico (la magnitud del evento escala el radio de forma continua,
no un umbral binario "se oye o no"); (2) el sonido debe ser ÚTIL más
allá de la huida — un depredador debería poder usarlo como pista de
caza. El punto (1) se resuelve en este mismo círculo (4a), porque la
fórmula de alcance es parte de la infraestructura base. El punto (2)
es exactamente el círculo 4b (ver spec aparte) — depende de que
`nucleo/sonido.py` ya exista con su función `sonido_mas_cercano`,
reutilizada tal cual por el fallback de caza sin cambios aquí.

## Decisiones ya cerradas con Diego

- **Disparo: solo eventos violentos ya existentes en el motor** —
  intento de depredación (`sistema_depredacion.py:_resolver_ataque`,
  éxito o no) y `ResultadoDisputa.ENFRENTAMIENTO` de conflicto verbal
  (`sistema_movimiento.py:_resolver_conflicto_entre`) — nunca CEDE/
  COMPARTE, ahí no hay pelea real. Nada de "cualquier acción física"
  genérica del informe original — evita inventar una fórmula de "cuán
  ruidoso es caminar", y evita un coste de emisión por entidad por tick.
- **Magnitud = peso combinado** de los participantes
  (`DimensionesFisicas.peso`, sin atributo nuevo).
- **Alcance dinámico y continuo**: el radio audible de un evento escala
  linealmente con su magnitud, y se modula además por la
  `agudeza_sensorial` propia de quien escucha — fórmula propia (ver
  Arquitectura), no reutiliza `radio_individual`/`radio_efectivo_por_peso`
  tal cual (esas dos tienen forma fija a un rango min/max de config,
  no a una magnitud dinámica por evento).
- **Duración fija y corta, sin decaimiento gradual** —
  `duracion_sonido_ticks` (PROVISIONAL): dentro de la ventana el sonido
  es audible a su alcance completo; fuera, deja de existir. Una fuente
  de complejidad por incremento (alcance dinámico), no dos (alcance Y
  duración dinámicos a la vez).
- **Buffer sin componente ECS nuevo**: dos campos en `Celda` (mismo
  patrón que `en_llamas`) — sobrevive a `bus_eventos.limpiar()` porque
  vive en el mundo, no en el bus.
- **Sin gating por consciencia**: la amenaza ya aplica a las 4 especies
  hoy (un conejo huye de un lobo sin ser consciente) — el sonido es
  físico, no comunicación, así que aplica igual de neutral.
- **`nucleo/sonido.py` se diseña ya pensando en su segundo consumidor**
  (círculo 4b, pista de caza) — `sonido_mas_cercano` es genérica
  (recibe zona/posición/radio/agudeza, no sabe nada de amenaza ni de
  caza), para que 4b la reutilice sin tocarla.

## Alcance

**Dentro:**

1. `nucleo/celda.py`: dos campos nuevos en `Celda` — `sonido_tick_emitido:
   int = -1` (sentinel "nunca"), `sonido_magnitud: float = 0.0`.
2. `nucleo/sonido.py` (nuevo módulo, mismo criterio de aislamiento que
   `nucleo/amenaza.py`/`nucleo/percepcion.py`): `emitir_sonido(celda,
   tick_actual, magnitud)`, `sonido_mas_cercano(zona, pos_x, pos_y,
   radio_busqueda_maxima, tick_actual, agudeza_sensorial, config) ->
   tuple[int,int] | None`.
3. Disparo de emisión:
   - `sistemas/sistema_depredacion.py`: `SistemaDepredacion.ejecutar`
     gana `mundo` y `reloj` en su firma (hoy solo recibe `gestor,
     bus_eventos`) para poder acceder a la `Celda` del encuentro;
     `_resolver_ataque` llama a `emitir_sonido` con la celda del
     encuentro y `dims_cazador.peso + dims_presa.peso`.
   - `sistemas/sistema_movimiento.py:_resolver_conflicto_entre`: en la
     rama `ENFRENTAMIENTO` (no en CEDE_A/CEDE_B/COMPARTE), llama a
     `emitir_sonido` con la celda del encuentro y la suma de pesos de
     ambas partes (requiere obtener `DimensionesFisicas` de `a_id`/
     `b_id`, no se consulta hoy en esta función).
4. Consumidor 1 (amenaza): `nucleo/amenaza.py:
   posicion_amenaza_mas_cercana` gana parámetros opcionales (`zona=None,
   tick_actual=0, agudeza_sensorial=0.0, radio_busqueda_sonido=0` —
   default sin efecto, backward-compatible) que, si se pasan, añaden
   `sonido_mas_cercano(...)` como TERCERA candidata a la búsqueda de
   "más cercana entre las fuentes de amenaza". Los 3 call sites reales
   (`sistema_necesidades.py`, `sistema_decision.py`, `sistema_movimiento.py:
   _calcular_huida`) pasan los parámetros nuevos — ya tienen `zona`,
   `tick_actual` (o accesible) y `dims.agudeza_sensorial` en scope.
5. `config/combate.yaml`, sección nueva `sonido:` — ver más abajo.
6. Tests dirigidos + verificación obligatoria contra el motor real.

**Fuera de alcance, explícito:**

- **Pista de caza para depredadores — círculo 4b, spec aparte**: no se
  toca `_calcular_caza` en este círculo. `nucleo/sonido.py` se diseña
  genérica precisamente para que 4b la consuma sin reabrir este spec.
- Cualquier emisión de sonido por locomoción normal, construcción,
  fuego u otra acción no violenta — solo depredación y `ENFRENTAMIENTO`.
- Cualquier cambio a `_calcular_forrajeo`/carroñeo — sin relación con
  este círculo (lo consumirá 4b, no 4a).
- Reputación/rumor sobre liderazgo — pieza restante del informe
  original, círculo futuro aparte.
- Decaimiento gradual de la señal (solo binario: dentro o fuera de la
  ventana de `duracion_sonido_ticks`).
- Múltiples sonidos simultáneos por celda — `emitir_sonido` SOBRESCRIBE
  cualquier sonido anterior en esa celda (el más reciente/dominante
  basta; no se necesita una cola de eventos superpuestos para esta
  pieza).

## Arquitectura

### Buffer (`nucleo/celda.py`)

```python
@dataclass
class Celda:
    ...
    sonido_tick_emitido: int = -1  # -1 = nunca hubo sonido aqui
    sonido_magnitud: float = 0.0
```

### `nucleo/sonido.py` (nuevo)

```python
def emitir_sonido(celda, tick_actual: int, magnitud: float) -> None:
    """Registra el evento sonoro mas reciente en la celda -- sobrescribe
    cualquier sonido anterior ahi, no se acumulan varios."""
    celda.sonido_tick_emitido = tick_actual
    celda.sonido_magnitud = magnitud


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
```

### Disparo — depredación

`SistemaDepredacion.ejecutar(self, gestor, mundo, reloj, bus_eventos)`
(firma ampliada; `main.py` actualiza la llamada
`sistemas["depredacion"].ejecutar(gestor, mundo, reloj, bus_eventos)`).
`_resolver_ataque` gana `mundo`/`tick_actual`, obtiene
`zona = mundo.territorio.zonas[zona_idx]`, `celda =
zona.obtener_celda(pos_x, pos_y)`, y llama a `emitir_sonido(celda,
tick_actual, dims_cazador.peso + dims_presa.peso)` — en TODO intento de
ataque, éxito o no (los fallidos son más frecuentes; también generan
sonido real, y serán la base de las "pistas falsas" reales que 4b
explota deliberadamente).

### Disparo — conflicto verbal

En `_resolver_conflicto_entre`, justo en la rama final de
`ENFRENTAMIENTO` (después de aplicar los drenajes de seguridad ya
existentes): obtener `DimensionesFisicas` de `a_id`/`b_id`, calcular la
celda vía `mundo.territorio.zonas[...]` y llamar `emitir_sonido` con la
suma de pesos. Esto exige ampliar la firma de `_resolver_conflicto_entre`
con `pos_x, pos_y, zona_idx` (hoy no los recibe, solo `gestor, mundo,
a_id, b_id, temperamento_a, temperamento_b, tick_actual`) — y por tanto
actualizar sus TRES call sites ya existentes
(`_resolver_posible_intruso` para refugio ocupado, `_procesar_roce_social`
para roce social, `_calcular_crisis_violenta` para contacto de crisis
violenta) para pasar la posición de contacto, que los tres ya conocen
en su propio scope.

### Consumidor 1 — amenaza (`nucleo/amenaza.py`)

```python
def posicion_amenaza_mas_cercana(
    gestor, zona, id_propio, x, y, radio, peso_propio, umbral_disposicion,
    zona_idx=0, peso_agresividad_candidato=0.0, valentia_propia=0.0,
    factor_valentia_amenaza=0.0,
    tick_actual=0, agudeza_sensorial=0.0, radio_busqueda_sonido=0, config=None,
):
    ...  # candidatos por criatura y ambiental, sin cambios
    candidato_sonido = None
    if radio_busqueda_sonido > 0 and config is not None:
        candidato_sonido = sonido_mas_cercano(
            zona, x, y, radio_busqueda_sonido, tick_actual, agudeza_sensorial, config,
        )
    # combinar los TRES candidatos por distancia Manhattan, mismo
    # criterio de desempate ya documentado (criatura > ambiental en
    # empate exacto; sonido se trata como ambiental a efectos de
    # desempate, sin prioridad especial).
```

Los 3 call sites reales pasan `tick_actual`, `dims.agudeza_sensorial`,
`radio_busqueda_sonido=self.radio_busqueda_maxima_sonido` (constante de
config cacheada, PROVISIONAL, ver más abajo) y `config=self.config`.

## Config nueva (`config/combate.yaml`, sección `sonido:`, PROVISIONAL)

```yaml
sonido:
  radio_sonido_base: 3  # PROVISIONAL -- alcance en celdas a peso_referencia_sonido exacto y agudeza sensorial media (factor 0.75)
  peso_referencia_sonido: 90.0  # PROVISIONAL -- mismo orden que la referencia visual de 90kg ya usada en el visor; NO reutilizar peso_referencia_deteccion_plena (0.1kg), que sirve para el proposito opuesto (floor de detectabilidad de presas diminutas)
  duracion_sonido_ticks: 5  # PROVISIONAL -- ventana corta, sobrevive al menos un ciclo de decision del tick siguiente
  radio_busqueda_maxima_sonido: 12  # PROVISIONAL -- techo de escaneo (no el alcance real), generoso para no recortar eventos grandes
```

## Testing

- `emitir_sonido`/`_sonido_activo`: escribe y expira correctamente según
  `duracion_sonido_ticks`.
- `_radio_audible`: escala linealmente con magnitud; sube con agudeza
  sensorial sin llegar nunca a 0 con agudeza mínima.
- `sonido_mas_cercano`: encuentra la celda más cercana con sonido
  activo Y dentro de su propio alcance calculado; ignora sonido
  expirado; ignora sonido fuera de su propio alcance aunque esté dentro
  del radio de búsqueda (evento pequeño lejano no debe "oírse").
- Depredación: un intento de ataque (éxito o fallo) emite sonido en la
  celda correcta con la magnitud correcta.
- `ENFRENTAMIENTO`: emite sonido; CEDE_A/CEDE_B/COMPARTE no emiten nada.
- Amenaza: un sonido reciente y suficientemente fuerte hace que
  `posicion_amenaza_mas_cercana` lo devuelva como amenaza incluso sin
  ninguna criatura visible (detección sin línea de visión, el objetivo
  central del informe original); sin sonido activo, comportamiento
  idéntico a antes de esta pieza.
- **Verificación obligatoria contra `BOSQUE_AUTO_TICKS`, no opcional**:
  medir cuántos sonidos se emitieron de verdad, y cuántas veces la
  amenaza detectada por cualquiera de los tres consumidores reales fue
  ESPECÍFICAMENTE por sonido (no por criatura/ambiental) — evidencia
  directa de "detección sin línea de visión", el objetivo central del
  informe original. Reportar la cifra con honestidad aunque sea baja,
  mismo criterio que las tres piezas anteriores de este arco.

## Pendiente real tras esta pieza

- `radio_sonido_base`/`peso_referencia_sonido`/`duracion_sonido_ticks`/
  `radio_busqueda_maxima_sonido` PROVISIONALES, sin calibrar contra el
  harness completo.
- **Círculo 4b (pista de caza) es el siguiente paso inmediato** — ya
  puede diseñarse/entregarse en cuanto este círculo esté mergeado,
  reutilizando `nucleo/sonido.py` tal cual.
- Reputación/rumor sobre liderazgo — última pieza restante del informe
  original tras cerrar 4a y 4b.
- Sin decaimiento gradual ni múltiples sonidos superpuestos por celda —
  aceptado explícitamente como simplificación de este círculo.
