# Pertenencia explícita, colocación satélite y necesidad diferenciada de los edificios comunales

Fecha: 2026-09-16 (mismo día que taller/mobiliario/almacén de refugio,
círculo separado). Diseñado en conversación con Diego, en tres pasadas:
crítica al conflicto de capacidad de taller (125m² > 80m² en una sola
celda), propuesta de colocación satélite, y dos peticiones adicionales
de Diego confirmadas explícitamente ("todo junto"):

1. Los edificios comunales deberían poder estar en celdas distintas, no
   todos compitiendo por la celda centro exacta.
2. El orden de prioridad entre ellos (hoy almacén antes que los otros
   tres) debería desaparecer -- los cuatro al mismo nivel, decidido por
   la necesidad real del individuo, no por una cascada fija.
3. Ahora que `Asentamiento` tiene identidad estable (Pieza 1,
   2026-09-15), los edificios comunales deberían pertenecer
   explícitamente a esa entidad, no resolverse por proximidad.

Los tres puntos se entrelazan: sin pertenencia explícita, colocar
edificios fuera de la celda centro exacta agravaría una ambigüedad ya
latente (dos asentamientos cercanos podrían "verse" edificios el uno al
otro por pura proximidad -- ver más abajo). Se implementan en el mismo
círculo, contra el criterio habitual de "una complejidad a la vez", a
petición explícita de Diego (igual que taller+almacén el mismo día).

## 1. Pertenencia explícita (`Construccion.asentamiento_id`)

**Hallazgo real que motiva esto, no solo "quedaría más limpio"**:
`nucleo/asentamiento.py:almacen_cercano` (la función que hoy resuelve
"¿ya existe un X de mi pueblo?") busca por PURA PROXIMIDAD -- radio
`radio_cluster_celdas` (6 celdas) alrededor de `Asentamiento.centro`,
filtrado solo por `tipo` y `zona_idx`, sin comprobar en ningún momento
que el edificio encontrado pertenezca a ESTE asentamiento y no a un
vecino. Con dos poblados cuyos centros terminen a menos de 6 celdas
entre sí (posible, ya que `centro` deriva del centroide de refugios y
se recalcula cada día), un miembro del asentamiento A podría tratar
como propio el salón común que construyó el asentamiento B. Hoy este
bug está agazapado (todo anclado a la celda exacta del centro
minimiza la superficie real), pero colocar edificios en celdas vecinas
lo haría mucho más fácil de disparar.

**Diseño**: `Construccion` gana `asentamiento_id: int | None = None`
(mismo rol que `propietario_id` para refugio individual, pero para
comunales). Se asigna en el momento de creación
(`nucleo/entidad.py:crear_construccion` gana el parámetro). Toda
función que hoy resuelve "¿existe ya un X de mi pueblo?" pasa a
filtrar por `asentamiento_id == asen.id` en vez de por posición:

- Nueva `nucleo/construccion.py:construccion_comunal_de_tipo(gestor,
  asentamiento_id, tipo, indice=None) -> int | None` -- reemplaza el
  rol de "existe" de `almacen_cercano`/
  `construccion_completada_de_asentamiento` para los 3 consumidores
  reales (CONSTRUIR/RECOLECTAR, imán social de respaldo salón/cocina,
  alacena de forrajeo). Escaneo lineal por atributo (`entidades_con
  (Construccion)`, filtro en Python), mismo límite ya aceptado en
  `construccion_propia`.
- `almacen_cercano` (posición pura) se retira -- sin consumidor real
  tras la migración (verificado: solo se usaba para "existe" en los
  puntos ya migrados, y para cachear `Asentamiento.almacen_id`, que a
  su vez **nunca se lee en ningún sitio del código** -- hallazgo
  aparte, cache muerta desde que se introdujo. Se retira también
  `Asentamiento.almacen_id` completo, sin sustituto: ya no aporta nada
  que `construccion_comunal_de_tipo` no resuelva bajo demanda).
  `construccion_completada_de_asentamiento` igual: se retira, sus 2
  consumidores migran a `construccion_comunal_de_tipo` + comprobación
  de `completado_alguna_vez`.

Bump de esquema (`nucleo/persistencia.py`): columna
`asentamiento_id INTEGER` en `construccion_estado`.

## 2. Colocación: ancla (salón común) + satélite (el resto)

**Regla**: un único tipo, **`salon_comun`**, es "ancla" -- se construye
EXACTAMENTE en `asen.centro`, igual que hoy (si no cabe, simplemente no
se crea este tick, mismo bloqueo ya existente, sin búsqueda alternativa
-- es la referencia espacial fija del pueblo, coherente con ser el
edificio de reunión). Los otros tres (**almacén, cocina, taller**) son
"satélite": **nunca compiten por la celda centro** -- buscan la celda
habitable más próxima con cupo suficiente, empezando en el anillo 1
(vecinos inmediatos, distancia Manhattan 1) y expandiendo anillo a
anillo hasta `radio_cluster_celdas` (6, ya existente, sin constante
nueva). Orden determinista dentro de cada anillo (ordenado por
`(dx, dy)`) para que el resultado no dependa de qué individuo llegó
primero a intentarlo, solo del estado real de ocupación del mundo en
ese instante.

**Por qué el centro queda deliberadamente FUERA de la búsqueda
satélite, no como primera opción antes de expandir**: si un satélite
pudiera ocupar el centro cuando está libre, una carrera de creación
(p.ej. almacén(40) + cocina(35) llegando ambos al centro antes que
salón_común) dejaría el centro con menos cupo del que salón_común
necesita (35), bloqueándolo PERMANENTEMENTE pese a ser el tipo que
Diego quiere garantizado ahí. Excluir el anillo 0 de la búsqueda
satélite es la forma más simple de proteger esa garantía sin inventar
un mecanismo de reserva de espacio.

Nueva función, `nucleo/espacio.py` (mismo módulo que ya calcula cupo):

```
celda_satelite_con_cupo(mundo, centro, zona_idx, tipo, config,
                         radio_maximo) -> tuple[int, int] | None
```

Itera anillos Manhattan 1..radio_maximo alrededor de `centro`, dentro
de los límites reales del grid de la zona, devolviendo la primera celda
(orden determinista) cuyo `espacio_disponible_para_construir` cubra
`huella_m2_para(tipo, ...)`. `None` si ninguna celda del radio tiene
cupo -- mismo criterio de "no resuelto, señalado" que ya se aceptó para
el almacén el 31-08 (sin búsqueda de celda vecina en su momento; ahora
sí hay búsqueda, pero sigue habiendo un límite: agotado el radio,
sencillamente no se construye, sin plan B).

Fuera de alcance, explícito: comprobación de terreno transitable
(agua profunda, etc.) en la celda candidata -- ya tampoco se comprueba
hoy para el refugio individual (se crea donde el individuo esté parado,
sin validar el terreno), así que no es una regresión, es el mismo
criterio ya aceptado extendido a un caso nuevo.

## 3. Aplanar el orden: los 4 comunales al mismo nivel

**Alcance explícito**: esto aplana SOLO la relación entre los cuatro
tipos comunales entre sí (almacén/cocina/salón_común/taller). NO toca
la prioridad refugio-individual-antes-que-comunal (Maslow: seguridad
básica antes que cualquier necesidad comunal) -- eso sigue exactamente
igual que hoy. Si Diego quisiera aplanar también esa relación, sería
una conversación aparte.

Antes: `tipos_paralelos = ["salon_comun", "cocina", "taller"]`,
resueltos DESPUÉS de almacén (que no era paralelo, se resolvía primero,
sin ningún criterio de diseño detrás -- simple accidente de que
"almacén" fue el primer edificio comunal implementado, 31-08). Ahora:
los 4 son "paralelos" a la vez, sin ningún tipo con prioridad mecánica
sobre otro.

Nueva función, `nucleo/construccion.py:candidatos_comunales_pendientes`:

```
candidatos_comunales_pendientes(gestor, mundo, id_entidad, config,
                                 indice=None)
    -> list[tuple[str, int | None, tuple[int, int]]]
```

Para el asentamiento de `id_entidad` (None si no pertenece a ninguno:
lista vacía), recorre los 4 tipos; para cada uno sin completar,
resuelve `construccion_comunal_de_tipo` (cid o None) y, si no existe,
su posición de creación (ancla o satélite, según el punto 2). Devuelve
TODOS los pendientes -- **no elige ganador aquí** (eso exige
temperamento/necesidades, que esta función no recibe -- se resuelve en
`sistema_decision.py`, ver punto 4).

## 4. Necesidad diferenciada por tipo, no una utilidad plana

**Antes**: `utilidad_construir` para la cadena comunal era una
constante fija (`utilidad_construir_base=0.3`) aplicada por igual a
CUALQUIER tipo, con una única excepción -- almacén exigía superar
`disposicion_a_aportar` (excedente de saciedad/hidratación por encima
de un umbral de carácter) antes de estar "dispuesto"; salón_común,
cocina y taller no tenían ningún gate, siempre `dispuesto=True`. "Qué
se construye primero" lo decidía el desempate mecánico (quien llevara
más progreso ya invertido ganaba, empate resuelto por orden de lista) --
las necesidades del individuo apenas entraban.

**Ahora**: cada tipo tiene su propio **gate binario** (no una fórmula
continua -- generalizar el patrón ya existente de almacén sin inventar
4 curvas nuevas de golpe, alcance deliberadamente acotado):

| Tipo         | Gate                                                          | Criterio |
|--------------|----------------------------------------------------------------|----------|
| almacén      | `min(saciedad, hidratación) - umbral_individual >= 0` (idéntico a hoy, `disposicion_a_aportar`) | ya existía |
| cocina       | `saciedad - umbral_individual >= 0` (mismo umbral de carácter, pero solo saciedad, no hidratación -- cocinar es sobre comida) | **PROVISIONAL**, nuevo |
| salón_común  | `(sociabilidad + curiosidad) / 2 >= umbral_prosocial_comunal` (reutiliza el umbral YA existente de la Pieza D de comodidad, sin inventar uno nuevo) | nuevo |
| taller       | `deficit_comodidad > 0.0` (casi siempre cierto pronto en la partida, ya que comodidad empieza en 0.0) | nuevo |

Cuando el gate de un tipo pasa, su utilidad es `utilidad_construir_base`
(mismo valor de siempre, sin inventar magnitudes nuevas); si no pasa,
0.0. **Desempate entre los que pasan su gate**: se conserva el mismo
criterio ya validado (quien lleve más progreso ya invertido gana --
"la ley física de que el esfuerzo de la población converge en uno solo
sin que nadie lo planifique" ya la documentó el propio código el
2026-09-08). El ganador final es `max(candidatos, key=(utilidad,
progreso))`.

**Riesgo real, señalado explícitamente antes de implementar, a
verificar con el diagnóstico posterior**: hoy salón_común/cocina/taller
SIEMPRE tenían utilidad > 0 mientras hubiera objetivo pendiente (sin
gate). Con gates reales para los 4, es posible que en un tick dado
NINGÚN individuo tenga ningún gate activo (sin excedente de comida/agua,
sin sociabilidad suficiente, comodidad ya satisfecha) -- la cadena
comunal simplemente no avanza ese tick, cosa que antes no podía pasar.
Dado que el diagnóstico de ayer (taller/mobiliario) ya mostró que la
cadena comunal es lenta incluso SIN este cambio (la mayoría de semillas
ni completan salón_común/cocina en 10000 ticks), existe un riesgo real
de que este cambio la ralentice todavía más. Es la hipótesis a
verificar, no algo que se pueda decidir sobre el papel.

`sistema_decision.py` guarda el ganador en `Intencion.
construir_tipo_objetivo: str = ""` (mismo patrón transitorio por tick
que `fabricar_categoria`) -- valor: `"refugio"`, uno de los 4 tipos
comunales, o `""` si no hay nada pendiente. `cadena_comunal_pendiente`
(usada por la prioridad de mejora de vivienda, Pieza D) pasa a ser
simplemente `len(candidatos_comunales_pendientes(...)) > 0`, ya no
depende de qué tipo concreto sea.

## Arquitectura: por qué el resultado NO se resuelve una sola vez y se
## cachea, sino que `sistema_movimiento.py`/`sistema_recursos.py` vuelven
## a resolver cid/posición en vivo

`sistema_decision.py` decide QUÉ TIPO perseguir (usando temperamento/
necesidades, que solo él tiene a mano) y lo guarda en Intencion -- pero
NO resuelve cid/posición ahí (eso exigiría saber si ya lo creó otro
miembro este mismo tick, y decision corre ANTES que movimiento sobre
TODAS las entidades, así que congelar ahí "existe/no existe" reabriría
el bug real ya corregido el 2026-09-09 ("BUG REAL... este bloque creaba
SIEMPRE tipo=almacen hardcodeado", commit histórico de esa fecha) donde
dos miembros creaban duplicados por no ver la construcción que el otro
acababa de crear el mismo tick.

Así que `sistema_movimiento.py` (crear/caminar) y `sistema_recursos.py`
(transferir materiales) leen `Intencion.construir_tipo_objetivo` (el
TIPO ya decidido) pero vuelven a llamar a
`nucleo/construccion.py:objetivo_construccion_actual` (firma nueva,
recibe el tipo ya decidido en vez de resolverlo internamente) con
`indice=None` -- búsqueda en vivo, exactamente como ya se hace hoy --
para resolver cid/posición frescos. Se mueve SOLO la decisión de "qué
tipo", nunca la resolución de "existe/dónde".

## Consumidores migrados (verificado contra el código real, no de
## memoria)

- `sistema_decision.py` (línea ~738, cascada CONSTRUIR/RECOLECTAR).
- `sistema_movimiento.py`: `_calcular_construir` (creación/
  desplazamiento), robo de materiales (`_intentar_robo_material` o
  equivalente, línea ~1171), `_salon_comun_de`/`_cocina_de` (imán
  social de respaldo, líneas ~886-923).
- `sistema_recursos.py`: `_resolver_construir`, rama no-mejora (línea
  ~716).
- `sistema_asentamiento.py`: retira el cálculo de `almacen_id` muerto;
  pasa `asentamiento_id=asen.id` al crear cualquier comunal.

## Fuera de alcance, explícito

- Aplanar refugio-individual frente a comunal (Maslow entre esos dos
  niveles no se toca).
- Validación de terreno transitable en la celda satélite candidata.
- Convertir los gates binarios en utilidades continuas (posible
  refinamiento futuro, no este círculo).
- Mecanismo de reserva de espacio para el ancla -- se resuelve
  excluyendo el anillo 0 de la búsqueda satélite, más simple.

## Verificación esperada

- Tests dirigidos: `celda_satelite_con_cupo` (encuentra vecino con
  cupo, respeta el radio máximo, nunca devuelve el propio centro,
  determinismo del orden); `construccion_comunal_de_tipo` (aislamiento
  real entre dos asentamientos con centros a menos de
  `radio_cluster_celdas` de distancia -- el escenario que motivó todo
  esto); `candidatos_comunales_pendientes` (los 4 tipos sin jerarquía,
  posiciones ancla/satélite correctas); gates diferenciados por tipo en
  `sistema_decision.py` (cada uno gana cuando y solo cuando su propio
  driver lo justifica); migración limpia de los tests existentes que
  dependían de la firma vieja.
- `BOSQUE_AUTO_TICKS`/`BOSQUE_CONTINUAR` (roundtrip con la columna
  `asentamiento_id` nueva) sin excepciones.
- Diagnóstico de juego libre: confirmar que al menos un edificio
  satélite termina en una celda DISTINTA del centro exacto en alguna
  semilla (la colocación satélite se ejerce de verdad, no solo existe
  en el código); medir si la cadena comunal se ralentiza frente al
  diagnóstico de ayer (riesgo ya señalado arriba).
