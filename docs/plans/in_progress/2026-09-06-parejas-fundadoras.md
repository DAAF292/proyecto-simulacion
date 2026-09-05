# Plan: parejas fundadoras en la siembra de población inicial

## Objetivo

Reducir la distancia de partida a cero para una fracción de la población
fundadora sembrando parejas (macho + hembra) en la misma celda desde tick 0.
Los dos únicos cambios son los que fija el spec (ver
`docs/superpowers/specs/2026-09-06-parejas-fundadoras-design.md`):
la firma de `crear_criatura` y el bucle de `sembrar_poblacion_inicial`.
No se toca ningún sistema del motor ni ninguna tasa de
`config/fisiologia.yaml`.

## Ficheros a modificar

### 1. `nucleo/entidad.py` — `crear_criatura`

- Añadir parámetro opcional al final de la firma:
  `sexo_forzado: Sexo | None = None`.
- Sustituir la línea
  `sexo = rng.choice([Sexo.MACHO, Sexo.HEMBRA])` por
  `sexo = sexo_forzado if sexo_forzado is not None else rng.choice([Sexo.MACHO, Sexo.HEMBRA])`.
- Con `sexo_forzado=None` (todo llamador existente) el comportamiento es
  bit-a-bit idéntico: la línea de sorteo sigue ejecutándose igual, solo se
  usa su resultado cuando no hay valor forzado.
- No tocar `nacer_criatura` (el otro `rng.choice([Sexo.MACHO, Sexo.HEMBRA])`
  del fichero, línea ~493): los nacimientos en partida siguen sorteando
  sexo 50/50, explícitamente fuera de alcance.

### 2. `main.py` — `sembrar_poblacion_inicial`

- Importar `Sexo` desde `componentes.reproduccion`.
- Reestructurar el bucle por especie (hoy `for _ in range(cantidad)`):
  - `cantidad // 2` parejas: por cada pareja, UNA sola celda sorteada con
    `rng_juego.choice(celdas_candidatas)` (mismo mecanismo que hoy), y dos
    llamadas a `crear_criatura` con esa misma `(pos_x, pos_y)` —
    `sexo_forzado=Sexo.MACHO` la primera, `sexo_forzado=Sexo.HEMBRA` la
    segunda.
  - Si `cantidad` es impar: el sobrante se siembra exactamente como hoy
    (celda propia sorteada de forma independiente, `sexo_forzado=None`).
- El resto de la función no cambia: registro en
  `persistencia.registrar_entidad_nueva`, filtro de celdas, fallback
  bosque→pradera, `techo_fraccion_edad_inicial_longevidad`.

## Orden de implementación

1. `nucleo/entidad.py` (firma + línea de sexo).
2. `main.py` (import + bucle de parejas).
3. Tests dirigidos de los ficheros afectados
   (`tests/test_especie_caballo.py`, `tests/test_nombre_propio.py`,
   `tests/test_parentesco.py`, `tests/test_relaciones.py`).
4. Verificación completa (ver abajo).

## Verificación

1. `pytest` — suite completa en verde (216/216 esperados).
2. `BOSQUE_AUTO_TICKS=3000` sin intervención, sin excepción.
3. Comparación dirigida pequeña contra el motor real: 5 semillas NUEVAS ×
   4000 ticks, sin persistencia SQLite (arnés directo con
   `cargar_configuracion`/`instanciar_sistemas`/
   `sembrar_poblacion_inicial`/`sembrar_flora_inicial`/`ejecutar_tick`,
   `bus.limpiar()` cada tick), midiendo población final y extinción por
   especie (gnomo, lobo, conejo, ardilla, caballo) CON el cambio. Reportar
   los números tal cual en el resumen final.

## Fuera de alcance

Sistemas del motor, `fisiologia.yaml`, `nacer_criatura`, tests existentes,
`CLAUDE.md`.
