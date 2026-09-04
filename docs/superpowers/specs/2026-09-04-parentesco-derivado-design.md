# Parentesco derivado (familia, linaje biológico) — diseño

Fecha: 2026-09-04. Círculo 5 del arco "hilo individual" (círculos 1-4b,
ya cerrados — ver CLAUDE.md). Capa de linaje biológico; la capa de
convivencia como "familia" NO se toca aquí — ya está cubierta de facto
por la amistad por convivencia del círculo 3, que no distingue
parentesco a propósito (decisión ya cerrada: familia son dos capas
separadas, esta pieza es solo la de sangre).

## Motivación

`Identidad.id_madre`/`id_padre` se trackean desde el arco de
reproducción pero nunca se han consumido para nada — ningún sistema los
lee. Este círculo los convierte en la base de un módulo de derivación de
parentesco, con un primer consumidor real: el resolutor de conflicto ya
existente trata a la familia directa con más cohesión, igual que ya
hace con "mismo asentamiento".

## Decisiones ya cerradas con Diego

- **Hermanos = comparten `id_madre` O `id_padre`** (no `None`) — incluye
  medio-hermanos por parte de un solo progenitor, más completo
  biológicamente que exigir ambos.
- **Alcance: solo núcleo directo** (madre, padre, hijos, hermanos) —
  SIN abuelos ni tíos. **Hallazgo real que motivó esta decisión**:
  `GestorEntidades.eliminar_entidad` purga TODOS los componentes de una
  entidad al morir, incluida `Identidad` (`nucleo/entidad.py:77-80`) — no
  solo un flag "no viva". Esto significa que derivar abuelos/tíos solo
  funcionaría mientras el progenitor intermedio siga vivo en memoria; el
  dato persiste en SQLite pero no es consultable desde dentro de un tick
  sin una capacidad nueva bastante mayor (consulta a la BD en pleno
  bucle de simulación). Dada la fragilidad de población ya documentada
  varias veces en este arco, un abuelo (generación anterior a un
  progenitor ya de por sí frágil) probablemente ya no existiría en
  memoria cuando se le buscara. Se aparca como extensión futura, con
  esta limitación técnica documentada, no por falta de interés.
- **Primer consumidor: `nucleo/conflicto.py:resolver_disputa` trata a la
  familia directa con más cohesión**, mismo mecanismo que ya usa
  `mismo_grupo` — NO un resultado garantizado, un bono que aumenta la
  probabilidad de `COMPARTE` (coherente con leyes neutras: un hermano
  muy agresivo puede, en principio, seguir llegando a `ENFRENTAMIENTO`).

## Alcance

**Dentro:**
1. `nucleo/parentesco.py` (nuevo): `son_hermanos()`, `es_padre_o_madre()`,
   `es_familia_directa()`.
2. `nucleo/conflicto.py:resolver_disputa` gana el parámetro `son_familia`
   y el bono de cohesión correspondiente.
3. `sistemas/sistema_movimiento.py:_resolver_posible_intruso` calcula
   `es_familia_directa(propietario_id, intruso_id, gestor)` y lo pasa a
   `resolver_disputa`.
4. Nueva constante `bono_cohesion_familia` en la sección `conflicto` de
   config (misma sección que `umbral_cohesion_comparte`).

**Fuera de alcance, explícito:**
- Abuelos, tíos, primos — extensión futura, ver limitación técnica
  documentada arriba.
- Cualquier árbol genealógico persistido — sigue siendo aspiración
  futura, no se construye aquí (mismo criterio que `mundo.asentamientos`,
  100% derivable, sin estado nuevo).
- Familia como capa de convivencia — ya cubierta de facto por amistad
  por convivencia (círculo 3), sin relación con este círculo.
- Rencor entre familiares que YA existiera antes de este círculo (p.ej.
  si un padre y un hijo ya tuvieran rencor acumulado de un conflicto
  previo) — `resolver_disputa` no consulta `Relaciones`/afinidad, y este
  círculo tampoco lo introduce; son mecanismos independientes que pueden
  coexistir sin conflicto (ambos actúan sobre la misma disputa, en
  puntos distintos: cohesión por familia aquí, afinidad en un círculo
  futuro que aún no lee `Relaciones` para conflicto).
- Cualquier otro consumidor de parentesco (narrador contando "murió su
  hermano", memoria de agravios entre parientes, etc.) — círculos
  futuros si se necesitan.

## Arquitectura

### `nucleo/parentesco.py` (nuevo)

```python
def son_hermanos(id_a: int, id_b: int, gestor) -> bool:
    """True si id_a e id_b comparten id_madre o id_padre (no None).
    False si son la misma entidad, o si alguna Identidad no existe."""

def es_padre_o_madre(id_progenitor: int, id_hijo: int, gestor) -> bool:
    """True si Identidad(id_hijo).id_madre == id_progenitor o
    .id_padre == id_progenitor."""

def es_familia_directa(id_a: int, id_b: int, gestor) -> bool:
    """son_hermanos(a,b) OR es_padre_o_madre(a,b) OR es_padre_o_madre(b,a)."""
```

Todas puras, sin persistir nada — leen `Identidad` directamente del
`gestor` en vivo. Si alguna entidad ya no existe (murió, purgada), la
función correspondiente devuelve `False`, mismo criterio permisivo que
el resto del proyecto.

### `nucleo/conflicto.py:resolver_disputa`

Nuevo parámetro `son_familia: bool = False`. La condición de entrada a
la rama de cohesión pasa de `if mismo_grupo:` a
`if mismo_grupo or son_familia:`. Dentro, si `son_familia` es `True`, se
suma `bono_cohesion_familia` (PROVISIONAL) a la `cohesion` calculada
antes de compararla con `umbral_cohesion_comparte` — un sumando más,
no un resultado garantizado. El resto de la función no cambia.

### `sistemas/sistema_movimiento.py:_resolver_posible_intruso`

Calcula `son_familia = es_familia_directa(propietario_id, intruso_id, gestor)`
y lo pasa a `resolver_disputa`. Sin ningún otro cambio de comportamiento.

### Config

```yaml
# config/comportamiento.yaml, sección conflicto, junto a
# umbral_cohesion_comparte
conflicto:
  bono_cohesion_familia: 0.2  # PROVISIONAL, sin calibrar
```

## Persistencia

Sin cambios — todo derivado bajo demanda desde `Identidad` ya persistida.

## Testing

- `son_hermanos()`: verdadero si comparten SOLO `id_madre`, verdadero si
  comparten SOLO `id_padre`, falso si no comparten ninguno, falso si es
  la misma entidad, falso si alguna Identidad no existe en el gestor.
- `es_padre_o_madre()`: verdadero en ambas direcciones de parentesco
  (madre→hijo, padre→hijo), falso si no hay relación.
- `es_familia_directa()`: combina correctamente los dos casos anteriores.
- `resolver_disputa()`: con `son_familia=True` y una cohesión que sin el
  bono NO alcanzaría `umbral_cohesion_comparte`, el resultado pasa a
  `COMPARTE` gracias al bono; con temperamentos muy poco cohesivos
  incluso con el bono, sigue pudiendo llegar a `ENFRENTAMIENTO` o
  `CEDE_A`/`CEDE_B` (el bono no garantiza nada). Verificar también que
  `son_familia=False` reproduce EXACTAMENTE el comportamiento actual (sin
  regresión).
- `sistema_movimiento.py`: `_resolver_posible_intruso` calcula
  `es_familia_directa` correctamente y lo propaga a `resolver_disputa`.

**Verificación contra el motor real, OBLIGATORIA, no opcional** —
expectativa razonada, no certeza: a diferencia de asentamiento/pareja
(círculos 3 y 4b, que dependen de que la población sobreviva y conviva
tiempo), el parentesco madre-hijo existe DESDE EL NACIMIENTO, así que
debería ser mucho más fácil de observar al menos la EXISTENCIA de pares
con parentesco real en una corrida de `BOSQUE_AUTO_TICKS` (cualquier
nacimiento ya genera un caso). Confirmar esto explícitamente
inspeccionando la BD (`id_madre`/`id_padre` de crías reales). El efecto
del CONSUMIDOR (`resolver_disputa` con `son_familia=True` cambiando un
desenlace real) puede seguir siendo raro en juego libre por la misma
razón que el rencor (círculo 2): requiere que dos familiares directos
disputen un refugio ocupado concreto — si no se observa, señalarlo
explícitamente como en los círculos anteriores, sin forzar un escenario
artificial.

## Pendiente real tras esta pieza

- `bono_cohesion_familia` PROVISIONAL, sin calibrar.
- Abuelos/tíos — extensión futura, bloqueada por la purga completa de
  componentes al morir (limitación técnica real, documentada arriba).
- Otros consumidores de parentesco (narrador, memoria de agravios entre
  parientes) — círculos futuros si se necesitan.
- Con esto, 6 de las 6 piezas originalmente numeradas del arco "hilo
  individual" quedarían iniciadas o cerradas salvo biografía consultable
  (círculo 6 original) y desarrollo personal (aplazado desde el
  informe inicial, decisión ya tomada de no abordarlo todavía).
