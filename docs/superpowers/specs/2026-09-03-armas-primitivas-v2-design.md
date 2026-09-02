# Armas primitivas v2 — rediseño de Agarre/Inventario como cimiento, primer círculo real del arco herramientas/utensilios/armas

Fecha: 2026-09-03
Estado: aprobado por Diego (2026-09-03), pendiente de implementación
Supersede a: `docs/superpowers/specs/2026-09-01-armas-fabricadas-design.md`
  (marcado como SUPERSEDIDO en su propio fichero, conservado como
  registro histórico de qué se diseñó primero y por qué se descartó).

## Contexto y por qué se descarta la spec anterior

La spec anterior (2026-09-01) se implementó en
`feature/2026-09-01-armas-fabricadas` (PR #1, GitHub) pero Diego, al
revisar el diseño y el código ya escrito, encontró varios problemas de
fondo que invalidan ese enfoque completo, no solo detalles:

1. `puntos_agarre` se subió de 2 a 3 como parche — un gnomo tiene dos
   manos, el problema real es que nada sale nunca de `Agarre.objetos`.
2. El modelo de `Inventario`/`Agarre` no tenía sentido: una criatura
   acumulaba recursos sin ningún motivo concreto para tenerlos.
3. Fabricar solo podía usar lo que estaba literalmente en `Agarre` en
   ese instante, nunca lo que ya se porta en `Inventario`.
4. La "Vía 2" de `_resolver_recolectar` (agarrar cualquier material
   "porque se lo encuentra", sin causa — el propio comentario del
   código ya lo admitía así) viola el principio 5 del proyecto (leyes
   neutras, nunca teleológicas): ninguna acción debería ocurrir sin un
   motivo real que la desencadene.

**Esta spec no es un ajuste de la anterior — rediseña `Agarre` e
`Inventario` desde su semántica de fondo**, con las armas como primer
caso de uso real que lo valida (evitando construir infraestructura
genérica sin consumidor real, mismo criterio que ya sigue el
proyecto). El PR #1 y su rama se descartan por completo, incluidos los
cambios de infraestructura del pipeline autónomo que arrastraba (no
tienen relación con esta pieza y ya están superados por la migración a
`mini-swe-agent` documentada en `CLAUDE.md`).

Esta spec se usará además como banco de pruebas real para medir
eficiencia y coste del pipeline autónomo (modelo barato,
`agente-obrero`/`deepseek-v4-flash-0731` vía `mini-swe-agent`) en una
tarea de complejidad real, no en una pieza mínima — ver la nota final.

## Decisiones de diseño cerradas con Diego (brainstorming, 2026-09-03)

1. **Alcance funcional: sin norma fija por especie.** El efecto de un
   arma (defensivo u ofensivo) no lo decide la especie que la porta,
   sino el temperamento y la situación de cada individuo — un gnomo
   poco agresivo la usa a la defensiva, un futuro individuo agresivo la
   usaría para atacar, con la misma arma y la misma ley (principio 5:
   leyes neutras, nunca teleológicas).
2. **El arma modula `nucleo/conflicto.py:indice_asertividad_social`**,
   no una lógica de combate nueva — es el primer consumidor real de
   "robo/agravio genérico" que ese resolutor ya esperaba desde su
   diseño original (ver `CLAUDE.md`, sección "Conflicto por refugio
   ocupado").
3. **El efecto escala con temperamento**, no es binario (tener/no
   tener el objeto).
4. **Material crudo para fabricar vive en `Inventario`, no en
   `Agarre`** — mismo patrón causal que ya usa `CONSTRUIR`: hay un
   objetivo real (fabricar un arma), se recolecta hasta tener lo
   necesario, se consume al completar.
5. **Se retira la "Vía 2" de `_resolver_recolectar`** (agarre genérico
   sin causa) por completo — el único bonus defensivo por objeto crudo
   pasa a depender de una decisión causal de empuñar (punto 8), no de
   agarrar cualquier cosa del suelo sin motivo.
6. **"Todo es un arma"**: un material crudo `apto_arma` empuñado ya
   tiene algún efecto (nivel 1). Fabricar combina uno o más materiales
   según receta de catálogo para producir algo mejor (niveles 2 y 3) —
   sin nombres de arma hardcodeados en Python, todo vía config.
7. **Sin Accion nueva para empuñar/guardar** — es un ajuste automático
   recalculado cada tick junto a la Accion elegida por la Utility AI,
   no una decisión que compita por turno en el argmax.
8. **La decisión de empuñar es una fórmula continua, no una regla de
   zona.** Explícitamente rechazado: "fuera del asentamiento = se
   arma". En su lugar: `Necesidades.seguridad` (integra ya mucho
   contexto real) + `Temperamento.valentia` (modula el umbral
   individual — cierra su primer consumidor real, hoy sin ninguno) +
   detección real de amenaza presente (`posicion_amenaza_mas_cercana`,
   señal objetiva del entorno, no una etiqueta de zona).
9. **Este círculo cubre solo madera y piedra** — metales quedan
   reservados para un círculo futuro (mismo criterio que ya declaraba
   la spec anterior).

## Diseño técnico

### 1. `componentes/inventario.py` — objetos discretos junto a lo fungible

`Inventario` gana un campo nuevo, `objetos: list[str]` (mismo patrón
de dato puro que `Agarre.objetos` hoy), para material NO fungible que
la criatura porta consigo: un palo o una piedra concretos, o un arma ya
fabricada. `contenidos: dict[str, float]` (kg a granel) no cambia — se
sigue usando para materiales de construcción donde un puñado concreto
no importa (arcilla, tierra...).

Cada entrada discreta tiene un peso propio (nuevo mapa en
`config/materiales.yaml`, p.ej. `peso_objeto_kg` por material o
sección dedicada) que cuenta hacia la MISMA capacidad de carga por
peso que ya existe (`nucleo/inventario.py:capacidad_carga_kg`/
`espacio_disponible_kg`) — no un límite de "número de objetos" aparte.
Un objeto discreto representa una unidad física completa (un palo
entero, una piedra entera), no una fracción de kg — coherente con la
corrección de Diego ("no guardo kilos en mis bolsillos, llevo
objetos").

### 2. `componentes/agarre.py` — redefinido: "lo que empuño AHORA", no un histórico

`Agarre.objetos: list[str]` no cambia de forma, pero cambia de
semántica por completo: deja de ser un registro que solo crece y pasa
a ser un **subconjunto decidido y reversible de `Inventario.objetos`**
— lo que la criatura tiene activamente en la mano en este tick,
recalculado cada tick (ver punto 5). Nada persiste "para siempre" en
`Agarre` salvo mientras la decisión de empuñar siga siendo verdadera.

`puntos_agarre` (rango racial, `config/poblacion.yaml`) vuelve a su
valor previo a la rama descartada (gnomo=2, "dos manos") — ya no hace
falta ningún ajuste, porque el material crudo para fabricar ya no vive
aquí y las piedras de fuego dejan de quedarse fijas para siempre (se
guardan de vuelta a `Inventario` en cuanto la fogata se enciende con
éxito, mismo mecanismo genérico de empuñar/guardar, sin lógica
especial para el fuego).

### 3. Catálogo de materiales y recetas — `config/materiales.yaml` (o
    un fichero nuevo `config/armas.yaml`, a decidir en implementación)

- `apto_arma: bool` por material (madera, piedra) — mismo patrón que
  `apto_construccion`. Cualquier material `apto_arma` empuñado en
  crudo (sin fabricar) es un arma de **nivel 1**, con nombre igual al
  material.
- `recetas`: lista de combinaciones que producen un arma con nombre y
  nivel propios, sin lógica de nombres hardcodeada en Python:
  - `{materiales: [madera], nombre: lanza, nivel: 2}`
  - `{materiales: [piedra], nombre: hacha_mano, nivel: 2}`
  - `{materiales: [madera, piedra], nombre: hacha_primitiva, nivel: 3}`
  Añadir una receta nueva en el futuro (hueso, metal...) es solo
  config, sin código nuevo.
- `efecto_base_por_nivel` y `efecto_ofensivo_por_nivel` (PROVISIONAL,
  ver sección 6) — mapas `{nivel: valor}` para 1, 2 y 3.

### 4. Causalidad de recolección — `sistema_decision.py` +
    `sistema_recursos.py:_resolver_recolectar`

- Se retira la "Vía 2" actual (agarre genérico sin causa) por completo.
- Mismo "eslabón heredado" que ya usa `ENCENDER_FUEGO`/`piedra_suelta`:
  mientras el individuo no tenga NINGÚN arma de nivel ≥2 fabricada (ni
  en `Inventario` ni en `Agarre`), `utilidad_recolectar` hereda
  `max(utilidad_recolectar, 1.0 - necesidades.seguridad)` cuando la
  celda actual ofrece un recurso `apto_arma` (piedra vía `piedra_suelta`
  ya existente, madera vía el recurso `madera` que `sistema_flora.py`
  ya deposita bajo el manzano — ambos recursos ya existen, sin crear
  ninguno nuevo). El material recolectado va a `Inventario.objetos`, no
  a `Agarre`.
- Un individuo que nunca ha sentido inseguridad real nunca desarrolla
  interés en buscar un palo o una piedra para esto — mismo principio
  causal ya validado con el fuego.

### 5. `Accion.FABRICAR_ARMA` — `componentes/intencion.py` +
    `sistemas/sistema_decision.py` + `sistema_recursos.py`

- Gate: consciencia ≥ `umbral_consciencia_agencia`
  (`config/fisiologia.yaml`), sin arma de nivel ≥2 ya fabricada, al
  menos un material `apto_arma` en crudo en `Inventario.objetos`.
- Utilidad: `1.0 - necesidades.seguridad` (mismo patrón que
  `ENCENDER_FUEGO`).
- **Cuidado con el orden en `candidatas`** (mismo bug real que ya
  apareció en la spec anterior: `FABRICAR_ARMA` y `HUIR` comparten
  literalmente la fórmula `1.0 - seguridad`, y `max()` conserva el
  primer máximo en un empate). Colocar `FABRICAR_ARMA` con la misma
  cautela que ya exigió `HUIR` en la implementación anterior —
  documentado ahí como hallazgo real, no repetir el error de origen.
- Resolución, determinista (sin tirada de éxito, tallar no es un
  suceso de azar): busca en `Inventario.objetos` la mejor receta
  completable AHORA con lo que ya se porta (prioriza nivel más alto
  alcanzable con el material disponible en este instante — no espera
  a conseguir un material mejor, reacciona al presente, coherente con
  que el resto de la Utility AI no planifica a futuro), consume los
  materiales crudos de esa receta, añade el nombre del arma resultante
  a `Inventario.objetos`. Emite un Evento (`ArmaFabricada`, severidad
  NOTABLE) con `{x, y, zona_idx, arma, nivel}`.
- Una vez fabricada CUALQUIER arma de nivel ≥2, el gate se cierra para
  siempre en este círculo — no se persigue mejorar a un arma de nivel
  3 automáticamente si luego aparece el material que faltaba (fuera de
  alcance, ver sección "Fuera de alcance").

### 6. Empuñar / guardar — ajuste automático, sin Accion nueva

Cada tick, recalculado junto a la Accion elegida (no compite por
turno): decide qué de `Inventario.objetos` pasa a `Agarre.objetos` (y
qué vuelve de `Agarre` a `Inventario`), a partir de:

```
amenaza_ahora = posicion_amenaza_mas_cercana(...) is not None  # ya existe, reutilizar
deseo_empunar = amenaza_ahora or (1.0 - necesidades.seguridad) > (
    umbral_base_empunar + temperamento.valentia * margen_valentia_empunar
)
```

`umbral_base_empunar` y `margen_valentia_empunar`: constantes nuevas
PROVISIONALES (p.ej. `config/comportamiento.yaml`, sección `decision`
o una sección `armas` nueva) — sin calibrar contra el motor en marcha,
valores de partida razonados, no medidos.

Si `deseo_empunar` es verdadero y hay algo empuñable en `Inventario`
(el arma fabricada si existe, o si no el mejor material crudo
`apto_arma` disponible, respetando `puntos_agarre` como tope de cuántas
cosas distintas puede tener en la mano a la vez), se mueve a `Agarre`.
Si es falso, cualquier objeto `apto_arma`/arma que esté en `Agarre` se
guarda de vuelta a `Inventario`. Esto sustituye también el
comportamiento actual de las piedras de percusión del fuego (hoy
quedan en `Agarre` para siempre) sin ninguna lógica especial para
ellas — el mismo reflejo genérico decide cuándo se sueltan.

### 7. Efecto real — nivel del arma empuñada × temperamento

Dos componentes, para que un individuo poco agresivo siga obteniendo
un beneficio defensivo real sin volverse un atacante:

- **`efecto_base_por_nivel[nivel]`**: igual para cualquiera que empuñe
  algo de ese nivel — el obstáculo físico de tener algo en la mano.
- **`efecto_ofensivo_por_nivel[nivel] * temperamento.agresividad`**:
  cuanto más agresivo el portador, mayor el salto — un individuo poco
  agresivo apenas lo nota.

Consumidores:
- **`sistemas/sistema_depredacion.py:_resolver_ataque`** (ser cazado):
  sustituye `reduccion_prob_captura_por_agarre`/
  `_por_arma_fabricada` actuales (binarias) por
  `efecto_base_por_nivel[nivel] + efecto_ofensivo_por_nivel[nivel] * agresividad_presa`
  según el nivel de lo que la presa tenga empuñado (0 si nada).
  `Temperamento.agresividad` ya modula un ajuste de evasión distinto en
  este mismo módulo (ver docstring de `componentes/temperamento.py`) —
  revisar en implementación que ambos efectos no se solapen de forma
  redundante sobre la misma tirada.
- **`nucleo/conflicto.py:indice_asertividad_social`**: el componente
  ofensivo (`efecto_ofensivo_por_nivel[nivel] * agresividad`) se suma
  al índice de quien porte un arma empuñada — primer consumidor real
  de "robo/agravio genérico" para ese resolutor, sin lógica de combate
  nueva. El componente base no participa aquí (asertividad social ya
  tiene su propia lectura de agresividad/dominancia/valentía; sumar el
  componente base encima duplicaría esa lectura sin necesidad).

### 8. Persistencia

`Inventario` gana `objetos: list[str]` — extender la columna JSON ya
existente (o añadir una columna nueva, a decidir en implementación) en
`componentes_estado`. `Agarre.objetos` no cambia de forma, solo de
semántica (nada que migrar). Subir `VERSION_ESQUEMA` desde
`0.31-fase0` — DROP-and-recreate, mismo criterio ya establecido en el
proyecto (sin campañas reales que conservar).

## Fuera de alcance, explícito

- Metales (hierro/cobre) como material de arma.
- Mejorar automáticamente un arma ya fabricada a un nivel superior.
- Perder/romper un arma, o que se la roben (robo/agravio genérico como
  disparador aparte de `conflicto.py` — esta spec solo conecta el
  EFECTO del arma al índice existente, no añade un disparador nuevo de
  disputa).
- Empuñar cualquier objeto que no sea arma (antorchas u otros usos del
  mismo reflejo de empuñar/guardar) — el mecanismo queda genérico,
  pero solo se conecta a armas en este círculo.
- Herramientas de trabajo y utensilios de cocina (ya fuera de alcance
  en la spec anterior, sigue igual).
- Revisar otros atributos de `Temperamento` sin consumidor
  (`empatia`/`lealtad`/`fe`/`curiosidad`) — anotado como auditoría
  transversal futura, no parte de esta pieza (ver memoria de sesión).

## Criterios de verificación esperados

1. **Causalidad**: un individuo con `seguridad` siempre alta nunca
   recolecta material de arma ni fabrica nada, en ningún tick de un
   arnés dirigido. Uno con `seguridad` baja y material disponible en
   la celda sí lo hace.
2. **Recetas**: con solo madera disponible, se fabrica `lanza` (nivel
   2); con solo piedra, `hacha_mano` (nivel 2); con ambas disponibles
   a la vez en `Inventario` en el momento de fabricar, `hacha_primitiva`
   (nivel 3) — nunca nivel 2 si el nivel 3 era alcanzable ya.
3. **Empuñar/guardar reversible**: mismo individuo, misma arma ya
   fabricada — con amenaza real presente o seguridad muy baja se
   empuña (aparece en `Agarre`); sin amenaza y con seguridad alta se
   guarda (`Agarre` vacío, el arma sigue en `Inventario`). Repetir el
   ciclo varias veces confirma reversibilidad, no un evento de un solo
   sentido.
4. **Escalado por temperamento**, medido estadísticamente (misma
   metodología que ya usó la verificación de `Agarre` original: N
   simulaciones con distintos valores de `agresividad`/`valentia`,
   confirmando que el efecto observado varía como se espera, no un
   valor fijo igual para todos).
5. **Persistencia**: roundtrip guardar/cargar preserva
   `Inventario.objetos` exacto, incluidos casos con arma fabricada y
   con material crudo sin fabricar todavía.
6. **Motor real sin intervención**: varias semillas × varios miles de
   ticks (`BOSQUE_AUTO_TICKS` + pipeline completo) sin excepciones,
   confirmando que se fabrican armas y se empuñan/guardan de verdad en
   juego normal — no solo en arneses dirigidos.
7. Suite de tests existente (87 a fecha de esta spec) sigue en verde.

## Nota sobre el propósito de esta pieza como banco de pruebas del pipeline

A diferencia de las piezas de flora (troceadas en varios planes
pequeños, algunos con código completo pre-escrito por Claude), esta
spec se entrega deliberadamente SIN plan de implementación con código
ya escrito — el objetivo explícito de Diego es medir cómo se
comporta/cuánto cuesta el modelo barato (`agente-obrero` vía
`mini-swe-agent`) resolviendo una tarea de complejidad real por su
cuenta (explorar el repo, diseñar la implementación concreta,
escribirla, verificarla), no una tarea mínima de una o dos líneas. La
forma exacta de entregarle esta spec al pipeline (de una sola vez como
blueprint único, o troceada en sub-tareas secuenciales) queda pendiente
de decidir con Diego antes de soltarla — ver conversación en curso.
