# Satisfacción de vivienda (habituación/adaptación hedónica)

Fecha: 2026-09-17. Segundo círculo de la sesión, tras "vida familiar:
emancipación gateada por adultez + parto dirigido a refugio" (mismo día,
ya en master). Diseñado en conversación con Diego a partir de "comodidad
como motor de desarrollo" (lista original de temas).

## Motivación

`Necesidades.comodidad` (Pieza C del arco "comodidad", 2026-09-14) deriva
hacia `calidad_media_construccion` del refugio propio ya completado, y
ahí se estabiliza para siempre mientras el material no cambie -- incluso
con el material de máxima calidad posible, una vez alcanzado no queda
ninguna presión a seguir desarrollando. Diego: la naturaleza es que uno
se acostumbra a su nivel de comodidad (alto o bajo, según temperamento) y
eso incita a desarrollar más -- planteado en positivo, un "medidor de
satisfacción" que modula la comodidad en vez de un "hastío" que se resta.

## Alcance de este círculo (trocear explícito, decisión de Diego)

Se cierran DOS piezas relacionadas en la conversación:

1. **Satisfacción de vivienda que decae con el tiempo, modulada por
   temperamento**, y su efecto sobre el objetivo de comodidad ya
   existente (mejora de vivienda). Esto es lo que se implementa aquí.
2. **Efecto alternativo de baja satisfacción** ("empujar a salir a
   explorar/descubrir mundo" para individuos curiosos/valientes) --
   **deliberadamente FUERA de alcance**, decisión explícita de Diego
   ("troceamos, cerramos la pieza 1 ya"). Depende además de una pieza
   que no existe: hoy solo hay un `Territorio` activo (ver el
   relevamiento del primer círculo de esta sesión), así que "descubrir
   mundo" no tiene destino real todavía. Pendiente real para un círculo
   futuro, con dos caminos posibles a decidir entonces: una versión
   modesta (alejarse de celdas ya memorizadas dentro del territorio
   actual, reutilizando `MemoriaEspacial`) o esperar a que el tema de
   biomas/territorios múltiples se aborde.

## Por qué NO es una instancia del modelo de disposición en tres capas

Se investigó explícitamente si esto encajaba con el patrón ya existente
"disposición en tres capas (racial/histórica/situacional)"
(`nucleo/disposicion.py`) -- no encaja: ese patrón modela cómo se
relaciona un individuo CON OTRO (peso relativo para depredación,
reputación para liderazgo), no cómo un individuo se relaciona con su
propio nivel de confort. Se descarta la analogía en vez de forzarla.

## Diseño

Nuevo componente `componentes/satisfaccion.py`:

```python
@dataclass
class Satisfaccion:
    vivienda: float = 1.0
    referencia_vivienda: float = 0.0
```

Universal (mismo criterio que Agarre/Semillas/Relaciones/Vocacion):
toda criatura lo recibe al nacer (`crear_criatura` y `nacer_criatura`,
`nucleo/entidad.py`), vacío de efecto real para quien nunca completa un
refugio propio. `vivienda` es la primera y única instancia real -- el
propio nombre del componente queda abierto a futuras fuentes (arte,
vocación, estudio, fe, objetos materiales -- mencionadas por Diego en
conversación) que se añadirán cuando su sistema base exista, no antes.

Mecanismo (`sistemas/sistema_necesidades.py`, bloque 4b, mismo bloque
que ya deriva `Necesidades.comodidad`), solo mientras hay refugio propio
`completado_alguna_vez`:

- Si `calidad_actual` (calidad_media_construccion del refugio ya
  completado) supera `satisfaccion.referencia_vivienda` (comparación
  simple tick a tick, no récord histórico): mejora real detectada,
  `satisfaccion.vivienda = 1.0` (reposición completa).
- Si no (igual, o menor -- incluido deterioro): decae hacia
  `piso_satisfaccion_vivienda` a una tasa modulada por temperamento:
  `tasa = tasa_base * (1 + peso_temperamento * (curiosidad + valentia) / 2)`
  -- mismo patrón de combinar dos rasgos al 50% que ya usa
  `utilidad_socializar` con sociabilidad+curiosidad. Curiosidad/valentía
  altas se habitúan antes (se aburren del mismo nivel más rápido);
  bajas decaen a la tasa base, nunca más lento que ella.
- `satisfaccion.referencia_vivienda` se actualiza a `calidad_actual` en
  cualquier caso.
- El objetivo de comodidad pasa de `calidad_actual` a
  `calidad_actual * satisfaccion.vivienda`.

`piso_satisfaccion_vivienda` (PROVISIONAL 0.2): satisfacción nunca cae
del todo a 0 -- ni con el material más humilde deja de haber algo de
disfrute. Con esto, la presión de habituación NO es un "piso sin fondo":
en régimen estacionario con el material máximo del catálogo, el
objetivo de comodidad se estabiliza en `calidad_max * 0.2`, no en 0 --
sigue habiendo una utilidad de mejora real, pero acotada, coherente con
"sin techo autorado, se satura sola" (el freno real sigue siendo la
disponibilidad de material mejor, mecanismo ya existente en
`sistema_decision.py`, no tocado aquí).

## Config nueva (todas PROVISIONALES, `config/fisiologia.yaml`,
sección `necesidades.defecto`)

- `tasa_decaimiento_satisfaccion_base: 0.005` -- muy por debajo de
  `tasa_deriva_comodidad` (0.02): la habituación es un proceso mucho
  más lento que la propia deriva de confort.
- `peso_temperamento_satisfaccion: 1.0` -- ambos rasgos al máximo dobla
  la tasa base; ambos en 0.0 deja la tasa base sin amplificar.
- `piso_satisfaccion_vivienda: 0.2`.

## Correcciones de documentación de paso

`componentes/necesidades.py` (docstring de `comodidad`) seguía diciendo
"sin ningún consumidor todavía" -- desactualizado desde el círculo de
mejora de vivienda (Pieza D). Corregido junto con esta pieza, ya que se
estaba tocando el mismo docstring de todas formas.
