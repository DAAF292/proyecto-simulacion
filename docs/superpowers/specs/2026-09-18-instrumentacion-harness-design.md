# Instrumentación completa del harness de calibración

Fecha: 2026-09-18. Origen: petición explícita de Diego tras notar que
el análisis del harness completo no podía responder nada sobre flora,
y que varios mecanismos del motor (colonización espontánea, taller/
mobiliario, minería, socialización por afinidad) tenían contadores
reales en su propio sistema que el harness nunca leía. "Si vamos a
invertir tiempo en pruebas largas de monitorización, lo lógico es
poder extraer todas las mediciones posibles... si no es desaprovechar
el tiempo y la capacidad de cómputo".

## Auditoría realizada antes de tocar nada

Se listaron todos los atributos `self._stats_*` definidos en
`sistemas/*.py` (48 en total) y se compararon contra lo que
`herramientas/harness_calibracion.py::correr_semilla` capturaba
realmente. Sin este paso, habría sido fácil arreglar solo los dos gaps
que motivaron la ronda (flora, colonización) y dejar el resto sin
tocar -- exactamente el tipo de instrumentación parcial que ya había
producido el problema original.

## Gaps reales encontrados y corregidos

- **Flora -- gap más importante, cero métricas antes de hoy**: nuevo
  helper `_contar_flora()` (mismo patrón que `_contar_poblacion()`),
  población de `Planta` por especie + `masa_tronco_kg` total en pie al
  cierre de cada semilla. Más `arboles_talados`/
  `arbol_bloqueado_sin_hacha` (`sistema_recursos.py`, ya existían, sin
  capturar).
- **Colonización espontánea**: el mecanismo ya se ejecutaba
  correctamente (el harness reutiliza `ejecutar_tick` de `main.py` sin
  cambios), pero no se contaba -- solo se podía inferir a mano mirando
  saltos en `trayectoria`. Ahora se cuenta el evento
  `ColonizacionEspontanea` del bus, total y por especie.
- **Minería**: `picos_fabricados`, `veta_bloqueada_sin_pico`,
  `piedra_sustrato_bloqueada_sin_pico`.
- **Taller/mobiliario y mejora de vivienda**: `muebles_fabricados`,
  `deposito_almacen_refugio`, `mejora_refugio_sustituciones`,
  `construir_mejora_elegido`.
- **Socialización/rumor/sonido, desglose**: `socializar_elegidas`,
  `socializar_afinidad_pares`, `rumor_terceros_nuevos`, desglose de
  `sonido_caza_fallback` en `_caza`/`_carrona`/`_nulo` (antes solo se
  veía el total agregado, sin saber si el fallback producía caza real,
  carroñeo, o una pista falsa).
- **Colocación comunal**: `comunal_creado_ancla`, `comunal_creado_satelite`.
- **Madriguera**: `madriguera_miembros_nuevos`.

## Corrección de tipo real encontrada al verificar (no solo al leer código)

Tres de los contadores nuevos NO son enteros simples, son `set()` que
el propio sistema usa para deduplicar dentro de la partida --
capturarlos tal cual rompía la serialización JSON y la suma agregada
del resumen (`TypeError: unsupported operand type(s) for +: 'int' and
'set'`, detectado en la primera corrida de prueba, no antes):

- `_stats_socializar_afinidad_pares` (`sistema_movimiento.py`): cada
  par se añade DOS VECES (ambas direcciones, `(a,b)` y `(b,a)`) -- se
  captura `len(...) // 2` (pares no dirigidos reales), no el set crudo
  (los ids de entidad no tienen sentido fuera del proceso de esa
  semilla, y JSON no serializa tuplas como valores de set).
- `_stats_rumor_terceros_nuevos` y `_stats_madriguera_miembros_nuevos`:
  se añaden UNA sola vez por evento real -- se captura `len(...)`
  directo.

## Qué NO se toca

- El propio motor de simulación -- este círculo es enteramente
  infraestructura de medición, sin ningún cambio de comportamiento del
  juego.
- Los 48 atributos `_stats_*` en sí -- ninguno se renombra ni se
  modifica, solo se leen desde el harness.

## Verificación

- Corrida corta real (2 semillas × 1200 ticks): confirmó el bug de
  tipo (set vs int) que la sola lectura de código no había revelado, y
  tras corregirlo, confirmó que las nuevas secciones del resumen
  (Flora, Minería, Colonización espontánea, Taller/mobiliario) se
  imprimen correctamente con datos reales no vacíos.
- Suite completa del proyecto: 759 passed (sin cambios, no se tocó el
  motor).
