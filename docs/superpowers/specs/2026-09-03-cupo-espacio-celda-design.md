# Cupo de espacio compartido por celda — diseño

Fecha: 2026-09-03. Pieza 3 de la cola "poblar más el mundo" (piezas 1 y 2,
distribución causal y tipos de propagación de flora, ya cerradas — ver
CLAUDE.md). Pieza 4 (catálogo ampliado de especies) queda deliberadamente
fuera de este spec, como círculo aparte una vez esta pieza esté verificada
contra el motor real.

## Motivación

Hoy la ocupación física de una celda (100 m² reales, `metros_por_celda:
10`) es una mezcla inconsistente entre sistemas:

- **Construcción** ya tiene un presupuesto real en m²
  (`config/materiales.yaml:construccion.capacidad_construccion_celda_m2=80.0`,
  `nucleo/construccion.py:espacio_disponible_para_construir`) que resta la
  huella de cada `Construccion` presente, filtrado por `zona_idx`.
- **Flora** sigue con un límite duro de exactamente 1 `Planta` por celda
  (`Celda.tiene_recurso`/`tipo_recurso`, un escalar único), sin relación
  alguna con cuánto ocupa esa especie en la realidad ni con lo que ya haya
  construido ahí.
- **Fauna** no tiene ningún límite de ocupación — explícitamente fuera de
  este spec (ver "Fuera de alcance").

Consecuencia real: un árbol bloquea sin razón física un refugio en su
misma celda (o viceversa), y una celda cubierta de hierba se comporta
igual que una celda con un manzano maduro a efectos de ocupación, pese a
que sean físicamente muy distintos.

## Alcance

**Dentro de esta pieza:**
1. Categorizar cada especie de flora como `compite_espacio_fisico: true`
   (estructura física real — tronco, tallo rígido) o `false` (cobertura de
   suelo, sin obstáculo físico real).
2. Las especies que compiten (hoy: `manzano`, `cactus`) dejan de estar
   limitadas a 1 por celda — pueden coexistir varias, sujetas a un cupo de
   espacio compartido con `Construccion`, mismo presupuesto
   (`capacidad_construccion_celda_m2`) que construcción ya usa.
3. Las especies que NO compiten (hoy: `hierba_silvestre`, `liquen`,
   `musgo`) siguen el mismo límite de "como mucho 1 dominante por celda"
   que tienen hoy, PERO en una pista completamente independiente de la
   competidora — nunca se bloquean entre sí. Un manzano y hierba cohabitan
   la misma celda sin fricción.
4. `sistema_recursos.py` (COMER/RECOLECTAR) migra, solo para la pista
   competidora, de leer `Celda.tipo_recurso` a consultar las entidades
   `Planta` reales presentes en esa posición.

**Fuera de alcance, explícito:**
- Densidad de criaturas al aire libre (decisión de Diego, 2026-09-03):
  queda fuera del todo. Mezclar ocupación de flora/construcción con
  densidad de fauna sería una segunda fuente de complejidad en el mismo
  círculo, y la densidad de fauna ya tiene su propio mecanismo (fertilidad
  por nutrición, ver CLAUDE.md "Sobrepoblación...").
- **Tala** (destruir una `Planta` para liberar su hueco): señalada
  explícitamente como una acción consciente futura, con su propia
  utilidad ("¿merece la pena destruir el recurso para construir aquí, o
  busco otro sitio?"). No se construye aquí. Cuando un gnomo no encuentra
  sitio para construir por culpa de flora, el comportamiento es el mismo
  que ya existe hoy cuando el cupo está lleno de otras construcciones: no
  se crea la `Construccion` ese tick, sin búsqueda de celda vecina — el
  resto del comportamiento normal del individuo lo acaba llevando a otro
  sitio con el tiempo (patrón ya documentado y aceptado en el círculo de
  "Capacidad de construcción por celda", 2026-08-31).
- Cohabitación entre DOS especies no-competidoras a la vez en la misma
  celda (p.ej. hierba y liquen juntas) — el solapamiento actual de biomas
  lo hace casi imposible en la práctica, no se resuelve aquí.
- Huella escalada por `etapa` de crecimiento — huella fija por especie,
  decisión explícita de Diego para mantener esta pieza acotada (YAGNI: la
  etapa ya afecta producción/recolección, no hace falta que también mueva
  el cupo de espacio).
- Pieza 4 (catálogo ampliado de especies) — círculo aparte, después.

## Arquitectura

### Catálogo (`config/flora.yaml`)

Cada especie gana un campo nuevo, `compite_espacio_fisico: bool`. Las que
sean `true` ganan además `huella_m2` (PROVISIONAL, sin calibrar contra el
harness completo — mismo criterio que el resto de constantes del
proyecto):

| Especie          | compite_espacio_fisico | huella_m2 (PROVISIONAL) |
|-------------------|------------------------|--------------------------|
| hierba_silvestre  | false                   | (no aplica)              |
| manzano           | true                    | 4.0                      |
| cactus            | true                    | 1.5                      |
| liquen            | false                   | (no aplica)              |
| musgo             | false                   | (no aplica)              |

### Módulo de espacio compartido

`nucleo/construccion.py:espacio_disponible_para_construir` se generaliza
a un módulo neutral (`nucleo/espacio.py`, nombre a confirmar en el plan de
implementación) con una función que suma, para una celda+zona dadas:

- La huella de cada `Construccion` presente (comportamiento ya existente,
  sin cambios).
- La huella de cada `Planta` con `compite_espacio_fisico=true` presente en
  esa misma posición+zona (consulta real de entidades, mismo patrón que
  `disposicion.py`/`sistema_depredacion.py` ya usan para buscar por
  posición — sin filtro espacial optimizado, aceptable a esta escala,
  mismo criterio ya asumido en el resto del motor).

Espacio disponible = `capacidad_construccion_celda_m2` menos esa suma.
Reutilizado por:
- `sistema_movimiento.py:_calcular_construir` (sin cambios de
  comportamiento, solo la fuente del cálculo).
- `nucleo/flora.py:intentar_colonizar_celda`, únicamente cuando la especie
  entrante tiene `compite_espacio_fisico=true` — rechaza la colonización
  si su `huella_m2` no cabe en el espacio disponible.
- `nucleo/flora.py:colonizar_por_idoneidad` (generación inicial), mismo
  criterio: una celda puede recibir más de una especie competidora si el
  cupo lo permite, sorteando entre las candidatas igual que hoy pero sin
  detenerse tras la primera.

### Dos pistas independientes en `Celda`

- **Pista no-competidora**: `Celda.tiene_recurso`/`tipo_recurso` se
  mantienen exactamente como están HOY, pero quedan reservados en
  exclusiva a especies con `compite_espacio_fisico=false`. Colonizar con
  una especie competidora no lee ni escribe estos campos.
- **Pista competidora**: sin espejo en `Celda`. La fuente de verdad es
  exclusivamente la entidad `Planta` (con `Posicion`), consultada
  directamente donde haga falta — igual que ya hace `sistema_flora.py`
  para producción/crecimiento/propagación.

`intentar_colonizar_celda` se bifurca según `compite_espacio_fisico` de la
especie entrante:
- `false` → comportamiento actual sin cambios (gate por
  `celda_dest.tiene_recurso`, ignora por completo cualquier `Planta`
  competidora presente).
- `true` → gate por espacio disponible (ver arriba), ignora por completo
  `celda_dest.tiene_recurso`. Al colonizar, NO toca `tiene_recurso`/
  `tipo_recurso` — solo crea la entidad `Planta` real (mismo
  `crear_planta` ya usado hoy).

### `sistema_recursos.py` — COMER y RECOLECTAR

Ambas acciones, para el caso de recursos de una especie competidora,
migran de leer `Celda.tipo_recurso`/`Celda.recursos` a:

1. Consultar las entidades `Planta` con `compite_espacio_fisico=true` en
   la posición+zona actual de la criatura.
2. Si hay más de una con el recurso buscado disponible, se usa la primera
   encontrada por orden de iteración — sin lógica de selección "óptima",
   coherente con el resto del motor (determinista por semilla, no
   optimizado a propósito).
3. El resto del mecanismo (consumo del recurso, actualización de
   `Necesidades.saciedad` para COMER, transferencia a `Inventario`/
   `Agarre` para RECOLECTAR) no cambia.

Para especies no-competidoras, ambas acciones siguen leyendo
`Celda.tipo_recurso`/`Celda.recursos` exactamente como hoy — sin cambios.

## Persistencia

- `celdas_estado`: sin cambios de esquema — `tiene_recurso`/`tipo_recurso`
  siguen representando únicamente la pista no-competidora.
- `plantas_estado`: sin cambios de esquema — ya persiste cada `Planta`
  como entidad individual con su `Posicion`; varias plantas competidoras
  en la misma celda ya se representan de forma natural (varias filas con
  el mismo x,y,zona_idx), sin necesitar ningún campo nuevo.
- `config/flora.yaml`: no es persistencia de partida, es catálogo — sin
  migración de esquema SQLite.

## Testing

Mismo criterio de "ley física" que el resto de tests del proyecto
(docstring explicando el comportamiento validado):

- Dos `Planta` competidoras (p.ej. dos manzanos) coexisten en la misma
  celda cuando su huella conjunta cabe en el cupo; la tercera es
  rechazada cuando ya no cabe.
- Una `Planta` no-competidora coloniza con normalidad una celda que ya
  tiene una `Planta` competidora (y viceversa) — cohabitación real,
  ninguna de las dos pistas bloquea a la otra.
- `espacio_disponible_para_construir`/el módulo generalizado excluye
  correctamente una celda cuando la huella de flora competidora +
  construcción ya presente supera el cupo — un refugio no se crea ese
  tick, mismo comportamiento que hoy cuando el cupo lo llenan otras
  construcciones.
- `sistema_recursos.py`: COMER y RECOLECTAR de una especie competidora
  funcionan correctamente cuando hay más de una `Planta` competidora en la
  misma celda (toma la primera con recurso disponible).
- Aislamiento por `zona_idx`: dos celdas en zonas distintas con
  coordenadas numéricamente coincidentes no comparten cupo (mismo patrón
  de verificación ya aplicado en construcción/asentamiento).
- Persistencia: roundtrip de guardado/carga con varias `Planta`
  competidoras en la misma celda conserva el estado exacto (sin necesitar
  cambio de esquema).

Verificación contra el motor real, no solo tests unitarios: varias
semillas × varios miles de ticks de `BOSQUE_AUTO_TICKS` sin excepciones,
más inspección de al menos una celda real con más de una `Planta`
competidora coexistiendo tras una corrida sin intervención.

## Pendiente real tras esta pieza (explícito, no resuelto aquí)

- `huella_m2` de manzano/cactus y la reutilización de
  `capacidad_construccion_celda_m2` como cupo compartido: PROVISIONAL,
  sin calibrar contra el harness completo (15 semillas × 12000 ticks).
- Tala como acción consciente con utilidad propia — candidato a círculo
  futuro, solo si el motor real muestra que el bloqueo silencioso (sin
  búsqueda de celda vecina) es un problema práctico de verdad.
- Densidad de fauna al aire libre como parte del cupo de espacio —
  explícitamente descartado para esta pieza, no solo aplazado.
- Cohabitación entre dos especies no-competidoras en la misma celda —
  sin resolver, impacto práctico hoy nulo por el solapamiento de biomas.
- Pieza 4 (catálogo ampliado de especies) — círculo aparte, después de
  verificar esta pieza contra el motor real.
