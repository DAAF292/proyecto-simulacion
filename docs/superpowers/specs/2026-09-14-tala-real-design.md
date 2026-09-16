# Tala real -- Círculo 2 del arco "asentamientos/profesiones" (madera de verdad, no ramas caídas)

## Contexto

Círculo 1 (minería real, 2026-09-12) exigió un `pico` fabricado para
extraer una veta de mineral -- antes de eso, extraer mineral era
indistinguible de recoger una rama caída. Diego, al cerrar minería,
pidió seguir con **tala**: "con una rama y una piedra podemos hacer un
martillo, pero para hacer un edificio necesitamos tablas de madera,
losas de piedra" -- recoger lo suelto no exige herramienta, producir de
verdad sí. Minería ya resolvió la mitad geológica (vetas finitas); tala
resuelve la mitad forestal, con una diferencia real: **por primera vez
en el motor, una acción del jugador destruye deliberadamente una
entidad `Planta`.**

Diego, en el mismo intercambio, defirió explícitamente el hallazgo de
"minería casi inalcanzable en juego libre" (el motivo causal es
puramente oportunista, sin ningún sesgo de movimiento hacia una veta
conocida): "más adelante desarrollaremos necesidades y flujos que
precisen de materiales y será el motivo de que un ser consciente vaya a
minar". Mismo criterio aplica aquí -- tala tampoco lleva sesgo de
movimiento propio en este círculo.

## Diseño

**Sin Accion nueva, sin nuevo flag `Intencion.recolectar_motivo_X`** --
mismo criterio que minería: la extracción de madera de un árbol en pie
es una prioridad más dentro del bloque genérico ya existente de
`_resolver_recolectar` (mineral > **tala** > material de flora a granel
> sustrato), no un motivo causal nuevo. RECOLECTAR ya gatea
genéricamente por "masa apta de construcción pendiente" -- para la
Utility AI, talar sigue siendo indistinguible de recoger sustrato.

**Gate: `hacha_primitiva` específica**, no `tiene_herramienta()`
genérico contra ningún catálogo -- un hacha tala, no cualquier
herramienta futura (mismo espíritu que distinguir `pico`/mineria de
`hacha_primitiva`/herramienta como catálogos separados, pero aquí ni
siquiera hace falta un catálogo nuevo: se reutiliza el objeto YA
existente, comprobando literalmente `"hacha_primitiva" in
objetos_totales`). Sin tala interrumpe la resolución de todos modos --
cae a material de flora a granel / sustrato, mismo criterio "no
bloqueante" que minería.

**`Planta` gana `masa_tronco_kg: float = 0.0`** -- cuánta madera queda
en el tronco en pie, análogo exacto a `Celda.masa_mineral_restante`.
Solo las 3 especies que ya declaran un recurso `madera`
(categoria=material) y `compite_espacio_fisico=true` -- `manzano`,
`roble`, `pino` -- reciben un valor > 0 en `config/flora.yaml`
(PROVISIONAL, escalado a ojo por `huella_m2` ya existente: manzano=80,
pino=90, roble=100). Deliberadamente **determinista, sin sorteo
individual** (a diferencia del patrón rango+sorteo que rige atributos
de criatura) -- introducir una tirada de `rng.uniform` nueva por cada
`crear_planta()` desplazaría la secuencia de aleatoriedad de TODO lo
demás para cualquier semilla ya en marcha, mismo riesgo ya documentado
repetidas veces en este proyecto; el valor por especie ya varía
(80/90/100), suficiente sin necesidad real de variar también por
individuo.

**Extracción**: mismo patrón de `min(tasa, espacio,
masa_restante)`, decrementa `Planta.masa_tronco_kg`; al llegar a 0,
`GestorEntidades.eliminar_entidad(planta_id)` -- primera destrucción
deliberada de una `Planta` en el motor. El cupo de espacio compartido
de la celda (`nucleo/espacio.py`) se libera solo, sin código adicional
-- `plantas_competidoras_en`/`espacio_disponible` consultan la ECS en
vivo cada vez, no cachean nada.

**Evento `ArbolTalado`** (NOTABLE, mismo criterio que
`HerramientaFabricada`/`PicoFabricado`), emitido en el tick que agota
el tronco -- `{x, y, zona_idx, especie}`.

**Deliberadamente fuera de este círculo**: sin "tabla" procesada (sigue
siendo el mismo material `madera` ya existente en el catálogo, solo una
fuente mucho mayor y de una vez); sin sesgo de movimiento hacia un
árbol conocido (mismo criterio que minería, deferido a "necesidades y
flujos" futuros); sin regeneración de la `Planta` talada -- la
propagación diaria ya causal (vector caída/viento/zoocoria, arco
cerrado 2026-09-02) es el único mecanismo de reposición, ninguno nuevo.

## Persistencia

`Planta.masa_tronco_kg` viaja en `plantas_estado` (nueva columna),
`VERSION_ESQUEMA` sube a `0.38-fase0` (DROP-and-recreate, sin
migración, mismo criterio ya establecido).

## Verificación

- Tests dirigidos: gate con/sin hacha, extracción real decrementando
  masa, destrucción de la entidad al agotar (incluida la liberación de
  espacio de celda confirmada tras destruir), evento `ArbolTalado`,
  regresión de especies no-talables (0.0 por defecto), roundtrip de
  persistencia.
- `BOSQUE_AUTO_TICKS=3000` + `BOSQUE_CONTINUAR=1` sin excepciones.
- Diagnóstico multi-semilla (mismo arnés que minería), con honestidad
  sobre si el ciclo hacha→tala se ejerce en juego libre o queda "raro"
  como minería -- sin corregirlo aquí si es el caso (mismo criterio
  deferido por Diego).
