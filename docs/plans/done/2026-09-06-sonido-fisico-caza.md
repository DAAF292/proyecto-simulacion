# Plan — Sonido físico: pista de caza para depredadores (4b)

## Objetivo

Añadir un fallback DENTRO de `_calcular_caza`: cuando el cazador no
tiene ninguna presa válida en su percepción normal, en vez de caer
directo a `_paso_aleatorio()`, intenta primero `sonido_mas_cercano`
(consumido tal cual desde `nucleo/sonido.py`) y, si hay un sonido
audible dentro de `radio_busqueda_maxima_sonido`, avanza hacia él con
`_acercarse_a`. Si no hay sonido, cae a `_paso_aleatorio()` como hoy.

## Ficheros a tocar (en orden)

### 1. `sistemas/sistema_movimiento.py`

- Ampliar el import de `nucleo.sonido`: `from nucleo.sonido import
  emitir_sonido, sonido_mas_cercano`.
- Añadir 4 contadores de observación en `__init__` (patrón `_stats_*`,
  solo observación, ninguno lo lee en el camino de juego):
  - `_stats_sonido_caza_fallback_usos`
  - `_stats_sonido_caza_fallback_caza`
  - `_stats_sonido_caza_fallback_carroña`
  - `_stats_sonido_caza_fallback_nulo`
- Ampliar la firma de `_calcular_caza` con `zona=None`,
  `tick_actual=0`, `agudeza_sensorial=0.0` (defaults → backward
  compatible con las llamadas existentes de los tests).
- En el bloque `if not presas:`:
  - si `zona is not None`, llamar a `sonido_mas_cercano(zona, pos_x,
    pos_y, self.radio_busqueda_maxima_sonido, tick_actual,
    agudeza_sensorial, self.config)`;
  - si devuelve posición, incrementar `_stats_sonido_caza_fallback_usos`,
    clasificar el destino con un helper nuevo (`_clasificar_destino_sonido`)
    e incrementar el contador correspondiente (`_caza` / `_carroña` /
    `_nulo`);
  - devolver `self._acercarse_a(pos_x, pos_y, *objetivo_sonido)`;
  - si no hay sonido, `return self._paso_aleatorio()`.
- Nuevo helper privado `_clasificar_destino_sonido(gestor, cazador_id,
  especie, tx, ty, radio, zona_idx, peso_minimo_viable,
  peso_maximo_presa) -> str`: devuelve `"caza"` si hay una presa válida
  (mismos filtros de peso y zona que `_calcular_caza`) dentro del radio
  de percepción efectivo respecto al destino del sonido; `"carroña"` si
  hay una `Necromasa` con `tejido_blando > 0.05` dentro de `radio` del
  destino; `"nada"` si no hay ninguna. Solo medición honesta en el
  momento en que se decide seguir el sonido.
- Actualizar el despacho en `ejecutar()` (rama `Accion.CAZAR`) para
  pasar `zona`, `tick_actual` y `dims.agudeza_sensorial`.

### 2. `main.py`

En el bloque final de `BOSQUE_AUTO_TICKS`, imprimir los 4 contadores
nuevos (uso total del fallback y desglose caza/carroña/nada), igual que
ya se imprimen `sonido emitido` y `amenaza por sonido` del círculo 4a.

### 3. `tests/test_sonido_fisico_caza.py` (nuevo)

- Sin presa válida + sonido reciente audible → el cazador se dirige
  hacia la celda del sonido (`_acercarse_a`), NO `_paso_aleatorio()`.
- Sin presa válida + sin sonido activo → `_paso_aleatorio()`, idéntico
  a antes.
- Sin presa válida + sonido expirado → `_paso_aleatorio()`.
- Con presa válida disponible → `sonido_mas_cercano` NO se consulta
  (aunque exista un sonido más cercano que la presa): presa real > sonido.
- Aplica a cualquier especie con `medio_alimentacion == "cazar"` (el
  filtro ya es agnóstico; el test usa lobo, que es el único hoy).

## Verificación obligatoria (BOSQUE_AUTO_TICKS)

Correr `BOSQUE_AUTO_TICKS` (unos miles de ticks) con población real y
reportar explícitamente en el commit: usos del fallback, y de esos,
cuántos a caza real, cuántos a carroñeo real, cuántos a nada (pista
falsa). Se reporta el resultado real, sea bajo o nulo.

## Qué NO tocar

`nucleo/sonido.py`, `_calcular_forrajeo`, `Necromasa`, mecanismo de
carroñeo, `sistema_decision.py`, config (reutiliza
`radio_busqueda_maxima_sonido`), esquemas SQLite, `CLAUDE.md`,
`informes/`, `docs/historial_*.md`.
