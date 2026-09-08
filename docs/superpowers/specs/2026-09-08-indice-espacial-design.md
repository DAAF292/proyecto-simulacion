# Índice espacial compartido -- diseño (2026-09-08)

## Contexto y motivación

Diego planteó la pregunta de fondo tras verificar que la explosión de
población de conejo (documentada en `CLAUDE.md`, sección "Cómo cocinar")
seguía dándose incluso con el recorte de camada ya aplicado: "me empieza
a preocupar la eficiencia, ¿cómo vamos a hacer cuando existan muchas más
funcionalidades simultáneamente y además más fauna, flora, razas, etc?
¿es viable?"

Medido con `cProfile` sobre la misma semilla (60004) en dos escalas de
población de la misma partida:

| | Población | ms/tick |
|---|---|---|
| Escala 1 | 93 | 102 ms |
| Escala 2 | 208 | 319 ms |

Población x2.2, tiempo x3.1 -- peor que lineal. El 60-65% del tiempo de
tick se concentra en `nucleo/amenaza.py:posicion_amenaza_mas_cercana` →
`nucleo/disposicion.py:posicion_mas_cercana_por_disposicion`, que se
llama **una vez por entidad por tick** y en cada llamada escanea
`gestor.entidades_con(Posicion, DimensionesFisicas)` -- la población
mundial entera -- filtrando después por distancia. El mismo patrón se
repite, a menor escala, en `nucleo/construccion.py:hay_construccion_de_tipo_en`/
`construccion_propia`, `nucleo/madriguera.py:madriguera_en`,
`nucleo/fuego.py:fogata_en` y `nucleo/asentamiento.py:almacen_cercano` --
todos escanean TODAS las entidades de un tipo dado en cada llamada, sin
ningún filtrado espacial previo. Es el mismo defecto que
`_buscar_conspecifico_mas_cercano` ya documentaba como O(N²) desde hace
semanas ("aceptable a la escala actual, conocido, no corregido") --
resulta ser un patrón repetido en casi todos los sistemas de "percepción
de algo cercano" añadidos esta semana (manada, madriguera, salón común,
sonido, robo/compartir por confianza vía `_agrupar_conscientes_por_celda`,
que en cambio SÍ ya construye su agrupación una vez por tick -- ver más
abajo, es el precedente directo de este diseño).

Cada mecanismo nuevo que añade "mira si hay X cerca" multiplica el
número de escaneos O(N) por entidad por tick. El coste total no crece
solo con la población -- crece con (población) × (número de mecanismos
de percepción), y ese segundo factor solo va a subir con más fauna,
flora, razas y funcionalidades.

## Decisiones cerradas con Diego

1. **Alcance: barrido completo.** Un único índice espacial genérico
   adoptado por TODOS los consumidores identificados (no solo el mayor).
2. **Semántica: índice "congelado", no vivo.** Se reconstruye una vez
   por fase relevante (ver más abajo), no se mantiene sincronizado
   incrementalmente cuando una `Posicion` cambia. Esto corrige, como
   efecto colateral aceptado explícitamente, un artefacto de orden que
   existe hoy sin haber sido nunca una decisión de diseño: dentro del
   bucle de `sistema_movimiento.py` (`for eid in sorted(entidades):`),
   una entidad procesada más tarde puede ver la posición YA actualizada
   de otra procesada antes en el mismo tick (quien tiene id más bajo se
   mueve "antes"). Con el índice congelado, todas las entidades ven la
   misma foto -- la del cierre del tick anterior -- durante todo el
   cálculo de intención/movimiento de este tick.

## Arquitectura

### `nucleo/indice_espacial.py` (nuevo)

```python
class IndiceEspacial:
    def __init__(self, gestor: GestorEntidades) -> None:
        # bucket por (x, y, zona_idx) -> list[entidad_id], construido a
        # partir de gestor.entidades_con(Posicion) -- TODAS las
        # entidades con posicion, sin filtrar por ningun otro
        # componente. Cada consumidor sigue filtrando por su propio
        # componente requerido DESPUES de obtener la lista local, igual
        # que ya hace hoy dentro de su bucle -- un unico primitivo
        # compartido, no uno especializado por tipo.
        ...

    def en_celda(self, x: int, y: int, zona_idx: int) -> list[int]:
        """Entidades en esa celda exacta. O(1) medio."""

    def en_radio(self, x: int, y: int, zona_idx: int, radio: int) -> list[int]:
        """Entidades dentro de radio Manhattan -- recorre solo las
        celdas del rombo (2*radio^2 + 2*radio + 1 celdas), nunca la
        poblacion entera. Sin orden garantizado; quien llama sigue
        calculando la distancia exacta de cada candidato para
        desempatar "el mas cercano", igual que hoy, pero sobre una
        lista ya local."""


def construir_indice_espacial(gestor: GestorEntidades) -> IndiceEspacial:
    """Punto de entrada unico -- construye el indice desde cero. O(N)."""
```

No hay noción de "tipo de entidad" en el índice mismo -- `en_celda`/
`en_radio` devuelven ids crudos. `IndiceEspacial` no sabe qué es un
depredador, un refugio o una madriguera; solo sabe dónde está cada cosa
con `Posicion`. Mismo criterio de neutralidad que ya rige
`nucleo/disposicion.py` (principio 5, leyes neutras) aplicado a
infraestructura en vez de a comportamiento.

### Cuándo se construye -- dos índices por tick, no uno por entidad

`main.py:ejecutar_tick` construye:

- **Índice A**, al principio (antes de `sistemas["decision"].ejecutar`)
  -- refleja el cierre del tick anterior. Se pasa a `decision` y a
  `movimiento` (todo el cálculo de intención y de a dónde moverse ocurre
  sobre esta misma foto, sin importar el orden interno del bucle).
- **Índice B**, reconstruido justo después de que `movimiento.ejecutar()`
  termine (posiciones ya actualizadas este tick) -- se pasa a
  `depredacion` (contacto real), `recursos` (gating de
  ENCENDER_FUEGO/COCINAR), `necesidades` (drenaje de seguridad por
  amenaza, bonos de confort/seguridad de refugio/fogata/madriguera/salón
  común) y `reproduccion` (contacto para concepción).

Ambas construcciones son O(N), ejecutadas dos veces por tick -- no N
veces. Los sistemas de cadencia diaria (`asentamiento`, `manada`) NO
reciben un índice desde `main.py`: construyen el suyo propio localmente
cuando lo necesitan (una vez al día, coste despreciable frente a
construirlo dos veces por tick) -- evita tener que enhebrar el parámetro
también por el bloque de cadencia diaria de `ejecutar_tick` sin ganancia
real medible.

### Compatibilidad -- parámetro opcional en todas partes, sin romper nada existente

Tanto los métodos `ejecutar()` de los sistemas como las funciones puras
de `nucleo/*.py` ganan un parámetro `indice: IndiceEspacial | None =
None`. Si es `None`, la función/sistema construye su propio índice
internamente (mismo patrón ya usado por `por_celda: dict | None = None`
en los cinco procesadores de `sistema_movimiento.py`) -- **cero cambios
necesarios en la batería de tests existente** (300+ tests que llaman a
estos métodos/funciones directamente sin índice siguen funcionando
exactamente igual, solo que ahora construyen uno de usar-y-tirar en vez
de escanear la población a mano).

**Regla de disciplina, no solo de compatibilidad**: cuando un sistema SÍ
recibe un índice desde `main.py` (el caso caliente, per-tick), DEBE
reenviarlo a cada función de `nucleo/*.py` que llame dentro de su bucle
por entidad -- el fallback `None` existe para quien no tiene un índice
compartido a mano (tests, scripts aislados, sistemas de cadencia diaria),
nunca como excusa para dejar de enhebrarlo en el camino caliente. Si un
sistema per-tick recibe el índice pero no lo reenvía a un `nucleo/*.py`
que llama dentro de un bucle por entidad, el problema original reaparece
en silencio -- este es el riesgo real a vigilar en la implementación, no
la construcción del índice en sí.

## Consumidores exactos a migrar

Confirmado por grep contra el código real, no supuesto:

**Círculo 1 -- el índice + el 60-65% del coste medido:**
- `nucleo/disposicion.py`: `posicion_mas_cercana_por_disposicion`,
  `contar_conspecificos_cercanos`, `id_en_contacto_por_disposicion`.
- `nucleo/amenaza.py`: `posicion_amenaza_mas_cercana` (propaga el índice
  a `posicion_mas_cercana_por_disposicion`, sin lógica propia nueva --
  la fuente ambiental y la de sonido no escanean entidades, quedan
  igual).
- Sistemas que ganan el parámetro y lo reenvían: `SistemaDecision.ejecutar`
  (amenaza para deseo de empuñar arma), `SistemaMovimiento.ejecutar`
  (amenaza para HUIR, `contar_conspecificos_cercanos` para caza en
  manada y bono de defensa), `SistemaDepredacion.ejecutar`
  (`contar_conspecificos_cercanos` para aliados cazando),
  `SistemaNecesidades.ejecutar` (amenaza para drenaje de seguridad,
  `contar_conspecificos_cercanos` para bono de defensa en grupo),
  `SistemaReproduccion.ejecutar` (`id_en_contacto_por_disposicion` para
  contacto de concepción).
- `main.py:ejecutar_tick` construye Índice A/B y los distribuye.

**Círculo 2 -- extender el mismo índice ya construido en el Círculo 1:**
- `nucleo/construccion.py`: `construccion_propia`,
  `hay_construccion_de_tipo_en`.
- `nucleo/madriguera.py`: `madriguera_en`.
- `nucleo/fuego.py`: `fogata_en` (`hay_refugio_en` hereda el fix gratis
  por ser alias de `hay_construccion_de_tipo_en`).
- `nucleo/asentamiento.py`: `almacen_cercano` (consumido por
  `sistema_asentamiento.py`, cadencia diaria -- construye su propio
  índice local, no recibe Índice A/B).
- Sistemas que ganan el uso (parámetro ya existe desde el Círculo 1,
  solo se añaden más llamadas internas que lo reenvían):
  `SistemaDecision` (`fogata_en` para gating de
  ENCENDER_FUEGO/COCINAR), `SistemaMovimiento` (`almacen_cercano`,
  `construccion_propia` para objetivos de construcción/refugio),
  `SistemaNecesidades` (`hay_refugio_en`, `fogata_en`, `madriguera_en`,
  `hay_construccion_de_tipo_en` para los cuatro bonos de
  confort/seguridad), `SistemaRecursos` (`fogata_en`, parámetro nuevo en
  este círculo ya que no lo necesitaba en el Círculo 1), `SistemaManada`
  (`madriguera_en`, construye su propio índice local).

## Testing

- `tests/test_indice_espacial.py` (nuevo): `en_celda` exacto,
  `en_radio` respeta el borde Manhattan (inclusive/exclusive en los
  límites), aislamiento por `zona_idx` (misma `(x,y)` en dos zonas no se
  mezcla), mundo vacío, entidad propia incluida en su propia celda (la
  exclusión de "uno mismo" sigue siendo responsabilidad de quien llama,
  documentado explícitamente en el test), radio 0 equivale a
  `en_celda`.
- Regresión: la batería completa de tests existente (368 al momento de
  escribir este spec) debe seguir en verde sin modificaciones -- el
  parámetro opcional con fallback interno garantiza compatibilidad
  binaria de comportamiento salvo la excepción explícita del punto
  siguiente.
- **Excepción a verificar explícitamente**: si algún test existente
  depende del efecto de orden dentro del bucle de `sistema_movimiento.py`
  (una entidad viendo la posición ya movida de otra procesada antes en
  el mismo tick), ese test necesitará actualizarse -- se audita durante
  la implementación, no se anticipa aquí sin evidencia.
- Verificación contra el motor real: repetir el mismo arnés de
  `cProfile` (semilla 60004, escalas 93 y 208 de población) tras cada
  círculo, comparando ms/tick antes/después -- objetivo real: que el
  factor tiempo deje de superar claramente al factor población (hoy
  x3.1 tiempo frente a x2.2 población). `BOSQUE_AUTO_TICKS` con varias
  semillas nuevas sin excepciones, mismo criterio de siempre.

## Fuera de alcance, explícito

- No se optimiza `nucleo/sonido.py:sonido_mas_cercano` -- su coste es
  O(radio²) celdas por llamada, no O(N) entidades; no es el mismo
  defecto y no lo soluciona un índice de entidades.
- No se toca `sistema_movimiento.py:_agrupar_conscientes_por_celda` --
  ya construye su agrupación una vez por tick (no es un punto caliente
  hoy). Podría derivarse en el futuro del mismo `IndiceEspacial` filtrado
  por consciente, pero no es necesario para el objetivo de este círculo
  y no se fuerza aquí.
- No se persigue la reducción del volumen de llamadas a
  `obtener_componente`/`entidades_con` en sí (aparecían muy arriba en el
  perfil, pero como CONSECUENCIA de los escaneos O(N) que este círculo
  elimina, no como causa propia) -- se remide después de este círculo
  para confirmar que baja proporcionalmente, sin optimizar el propio
  `GestorEntidades` de antemano.
- No se cambia ninguna curva de utilidad, umbral, ni comportamiento de
  ninguna especie -- este círculo es puramente de rendimiento, sin
  ningún efecto de diseño pretendido más allá de la corrección de orden
  ya señalada como aceptada.
