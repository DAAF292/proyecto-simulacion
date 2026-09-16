# Identidad persistente de asentamiento (2026-09-15)

Pieza 1 del arco "asentamiento como entidad propia" (brainstorming con
Diego, mismo día). Prerrequisito de cualquier necesidad/interacción que
el asentamiento deba acumular con el tiempo: hoy `Asentamiento.id` se
reasigna desde 1 cada día (`SistemaAsentamiento.ejecutar`), sin relación
con el id de ayer -- nada puede "pertenecerle" de un día para otro.

## Hallazgo que motiva esto, verificado contra el código

`_miembros_vistos_ayer: set[frozenset[int]]` (deduplicación del evento
`AsentamientoFundado`) compara el conjunto EXACTO de miembros de hoy
contra el de ayer. Cualquier cambio de población (una muerte, un refugio
nuevo cerca) cambia el `frozenset` y el evento HISTÓRICO se reemite como
si fuera un pueblo nuevo -- en juego real esto pasará casi cada día. Esta
pieza lo corrige como efecto colateral directo de darle identidad real.

## Diseño

**Continuidad por solape (Jaccard), no por coincidencia exacta.**
`nucleo/asentamiento.py:resolver_identidades_persistentes(grupos,
registro_anterior, umbral_continuidad) -> dict[id_resuelto, miembros]`,
función pura: para cada grupo de hoy, calcula el solape
(`|intersección| / |unión|`) contra cada id de `registro_anterior`;
si el mejor solape supera `umbral_continuidad`, reutiliza ese id
(entre varios candidatos válidos, gana el de mayor solape; empate por
id más bajo, determinista). Sin ningún candidato por encima del umbral,
asigna un id nuevo consecutivo. Cada id anterior y cada grupo de hoy se
usan como máximo una vez (greedy por solape descendente) -- si dos
clústeres de hoy compiten por el mismo id previo (fusión/división,
casos raros dado que los refugios no se mueven), gana el de mayor
solape; el otro recibe id nuevo -- simplificación deliberada, sin
tracking explícito de fusión/escisión.

**Dónde vive el registro**: `Mundo` gana dos atributos nuevos junto a
`self.asentamientos` ya existente -- `asentamiento_registro_identidad:
dict[int, frozenset[int]]` (miembros del id tal como quedó ayer) y
`asentamiento_tick_fundacion: dict[int, int]` (primer tick en que ese id
existió). A diferencia de `mundo.asentamientos` (recalculado íntegro,
nunca persistido), estos DOS sí se persisten -- son la única memoria
real entre días, y perderlos silenciosamente en un `BOSQUE_CONTINUAR`
reemitiría `AsentamientoFundado` para cada pueblo ya existente y
resetearía la continuidad de cualquier pieza futura que dependa del id.

**Persistencia**: reutiliza la tabla genérica `configuracion_ejecucion`
(clave/valor, ya usada para `rng_juego_state`/`semilla`) con dos claves
nuevas, JSON (dict de listas, no pickle -- son solo ids de entidad).
Sin cambio de esquema (ninguna tabla nueva, ninguna columna nueva) --
`VERSION_ESQUEMA` no sube.

**`Asentamiento` (dataclass)** gana `tick_fundacion: int = 0`, relleno
desde el registro al construir cada instancia del día -- disponible ya
para cualquier consumidor futuro (biografía, piece 5 del roadmap) sin
que este círculo la use todavía.

**`AsentamientoFundado`** se emite cuando el id resuelto NO estaba en
`registro_anterior` (genuinamente nuevo), sustituyendo la comparación de
conjunto exacto -- corrige el hallazgo de arriba.

**Config nueva**: `asentamiento.umbral_continuidad_identidad` (0.5,
PROVISIONAL) en `config/comportamiento.yaml`.

## Deliberadamente fuera de este círculo

Ninguna necesidad ni interacción nueva del asentamiento -- solo el id
estable que las piezas siguientes (necesidades agregadas, efecto de
vuelta, interacción entre pueblos) necesitarán para acumular algo real
con el tiempo. Sin tracking explícito de fusión/escisión de
asentamientos. Sin cambio en `Manada` (mismo problema, mismo patrón
reutilizable si se retoma aparte -- no se toca aquí sin que Diego lo
pida).

## Verificación esperada

Tests de la función pura (continuidad con churn parcial, sin
continuidad tras dispersión total, determinismo del desempate, un id
nunca reutilizado dos veces el mismo día). `BOSQUE_AUTO_TICKS` real
verificando que `AsentamientoFundado` no se reemite para el mismo pueblo
tras una muerte/nacimiento de un miembro. `BOSQUE_CONTINUAR` (roundtrip)
confirmando que el registro sobrevive a guardar/cargar y que el primer
día tras cargar no reemite el evento para pueblos ya existentes.
