# Historial — Herramientas, armas, fuego y profesiones emergentes

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

## Agarre -- primera pieza de "capacidad de sostener/usar objetos",
## cimiento del arco de herramientas/fuego/comida elaborada (2026-08-31)

Diego, tras cerrar la capacidad de construcción por celda, retomó
herramientas/fuego/comida elaborada -- pero reencuadró por dónde empezar:
no "herramientas" como bloque monolítico, sino la capacidad física más
básica que las sostiene a todas: "la base es usar herramientas, o mejor
aún la capacidad de usar cosas, sostenerlas, un palo para defenderse, o
una roca, después de eso usar dos rocas para hacer un fuego, herramientas
básicas, hachas utensilios". Fuego (dos piedras) y hachas/utensilios
quedan como consumidores FUTUROS de este mismo cimiento, no piezas
paralelas -- este círculo es solo "poder tener un objeto sujeto, con un
efecto real".

**Primer nombre propuesto y rechazado, con razón**: "Empuñadura" --
centrado en manos. Diego lo corrigió de inmediato: "si creamos una raza
que tenga 4 manos que, o una con dos manos y una cola prensil. las
ardillas tambn sujetan objetos, o los lobos con la boca... es parte de la
criatura, una capacidad que tiene como tiene la de andar o comer". Mismo
error de fondo que categorizar cuevas por tamaño/bioma en el arco de
profundidad (documentado más arriba) -- autorear una forma concreta en
vez de una ley general. Corregido a `Agarre`, con `puntos_agarre` como
hecho FIJO por especie (no un rango sorteado por individuo como
fuerza/agilidad -- cuántos puntos de agarre tiene un individuo no varía
razonablemente dentro de la misma especie), mismo patrón que
`fraccion_madurez`/`factor_base_concepcion` en `rangos_raciales`.

**Implementado**:
- `componentes/agarre.py`: `Agarre.objetos: list[str]` -- objetos
  discretos sujetos ahora mismo, SIN campo de capacidad propio (se
  consulta `rangos_raciales[especie]['puntos_agarre']`, no se duplica el
  dato). Añadido a las CUATRO especies por igual en `crear_criatura` Y
  `nacer_criatura` (dos fábricas separadas, ver hallazgo de más abajo),
  vacío al nacer -- mismo criterio que `Inventario`: el componente es
  universal, su uso real depende de la especie.
- `config/poblacion.yaml`: `puntos_agarre` PROVISIONAL por especie --
  gnomo=2 (manos), lobo=1 (boca), ardilla=2 (patas delanteras, el propio
  ejemplo de Diego), conejo=0 (un conejo real no sujeta objetos de forma
  activa, a diferencia de una ardilla -- el valor menos seguro de los
  cuatro, señalado explícitamente a Diego antes de fijarlo, sin objeción).
- `sistemas/sistema_recursos.py:_resolver_recolectar`: antes de tocar el
  `Inventario` a granel, si queda algún punto de agarre libre, se llena
  UNO con el mismo material que ya sería elegible (flora > sustrato,
  mismo orden que el resto de la función, salvo mineral -- minar una veta
  es un acto deliberado con coste real, distinto de agarrar un palo o una
  piedra sueltos del suelo). Deliberadamente GRATUITO y simbólico: no
  descuenta nada del Inventario, la capacidad de carga ni el recurso
  finito de la celda -- el tope de 1-2 puntos por individuo (sin ninguna
  acción de soltar todavía) hace que el efecto total sobre la economía
  del mundo sea insignificante. Automático al recolectar, sin ninguna
  Accion nueva de la Utility AI -- mismo criterio que el resto del arco de
  interacción física (reutilizar RECOLECTAR en vez de inventar una acción
  con su propia curva de utilidad sin calibrar).
- `sistemas/sistema_depredacion.py`: primer efecto real, en
  `_resolver_ataque` -- si la PRESA tiene algún objeto sujeto,
  `reduccion_prob_captura_por_agarre` (`config/combate.yaml`, PROVISIONAL
  0.1) se resta de `prob_exito` antes de aplicar los topes min/max ya
  existentes. Efecto binario por ahora (tener algo agarrado cuenta igual
  que tener dos, sin diferenciar por material) -- primera pasada
  deliberadamente simple, revisable cuando haga falta distinguir un palo
  de una roca de verdad. Conflicto social (`nucleo/conflicto.py`) queda
  como consumidor futuro del mismo componente, sin lógica nueva -- mismo
  patrón que ya se usó con el resolutor de disputas.
- `nucleo/persistencia.py`: `Agarre.objetos` persistido como columna JSON
  nueva (`agarre`) al final de `componentes_estado`, `VERSION_ESQUEMA`
  subida a `0.29-fase0` (DROP-and-recreate, mismo criterio ya establecido
  -- sin campañas reales que conservar). Se hizo explícitamente, no se
  dejó como estado transitorio: a diferencia de otros campos transitorios
  del motor (p.ej. `dias_agotada_consecutivos`, inofensivos si se pierden
  un día), perder `Agarre.objetos` al recargar sería una regresión
  silenciosa y evitable en un mecanismo que ya tiene un efecto de combate
  real conectado.

**Hallazgo propio, no señalado por Diego**: `nacer_criatura` (nacimientos
por reproducción) es una fábrica ECS SEPARADA de `crear_criatura`
(población fundadora) -- no la reutiliza, construye sus 12 componentes de
forma paralela. `Agarre()` tuvo que añadirse en ambas por separado; un
descuido aquí habría dejado a toda cría nacida en partida sin el
componente, un `AttributeError` la primera vez que `sistema_recursos.py`
intentara leerlo. Detectado leyendo el código antes de escribir, no al
fallar en caliente.

**Verificado contra el motor real, cinco comprobaciones** (arnés
dirigido, `verificar_agarre.py`, scratchpad): (1) `puntos_agarre`
correcto por especie; (2) recolección real llena `Agarre` antes que
`Inventario`, respeta el tope (2 puntos en gnomo: se llena en 2 ticks,
el 3º ya cae a `Inventario`), conejo (0 puntos) nunca lo usa; (3)
persistencia -- roundtrip guardar/cargar preserva `Agarre.objetos` exacto
para dos entidades distintas; (4) efecto de defensa medido
ESTADÍSTICAMENTE, no solo leído del config -- 1000 ataques simulados con
presa desarmada vs. 1000 con presa armada (mismos temperamentos, misma
disposición de tamaño): tasa de éxito del cazador 0.779 sin agarre, 0.684
con agarre, diferencia 0.095 -- coincide con el `reduccion_prob_captura_
por_agarre=0.1` configurado, confirmando que el efecto se aplica
correctamente en el camino de ejecución real, no solo en teoría; (5) 4
semillas × 3000 ticks del pipeline completo sin intervención: el
mecanismo se ejerce de verdad en juego normal (2 de 4 semillas terminan
con gnomos con `Agarre` lleno, tope de 2 objetos), las otras 2 no tienen
gnomos vivos a esos 3000 ticks (fragilidad de gnomo ya documentada en el
círculo de sobrepoblación, no un fallo de esta pieza). 3000 ticks de
`BOSQUE_AUTO_TICKS` sin ninguna excepción. 22/22 tests en verde.

**Pendiente real, explícito**: ningún mecanismo para SOLTAR o GASTAR un
objeto sujeto todavía -- una vez lleno, un punto de agarre se queda lleno
para siempre (sin impacto práctico hoy, dado el tope de 1-2 por
individuo, pero bloquea cualquier consumidor futuro que necesite
"cambiar" de objeto, como fabricar una herramienta a partir de lo
agarrado); efecto de defensa binario, sin diferenciar por material o
cantidad; `puntos_agarre`/`reduccion_prob_captura_por_agarre`
PROVISIONALES sin calibrar contra el harness completo; conflicto social
como consumidor futuro sin disparador todavía (mismo hueco ya señalado
para robo/agravio genérico). El propio arco que Diego pidió -- fuego con
dos piedras, luego hachas/utensilios -- sigue sin empezar, este círculo
es solo su cimiento.
## Fuego controlado (Fogata) -- implementado y verificado, con un hallazgo
## real de que la precondición es casi inalcanzable en juego normal (2026-08-31)

Segundo círculo del arco herramientas/fuego/comida elaborada, sobre el
cimiento de `Agarre` de más arriba. Dos decisiones de diseño previas,
cerradas en conversación con Diego antes de escribir código:

1. **Confort térmico ya no era un campo inerte** -- hallazgo propio al
   investigar antes de proponer nada: `nucleo/clima.py`/
   `sistema_necesidades.py` ya mueven `Necesidades.confort_termico` de
   verdad cada tick hacia un objetivo que depende de estación+clima del
   día (implementado en una sesión anterior, la nota de "declarado pero
   sin mecánica" en este mismo documento estaba desactualizada). Esto
   evitó inventar un payoff nuevo para el fuego -- ya había uno
   funcionando y sin consumidor real que lo completara del todo.
2. **Bono ADITIVO, no sustitutivo, tras la pregunta de Diego** ("otoño 15
   grados, estoy en mi cabaña... invierno 3 grados, ¿es suficiente, o
   debo encender un fuego?"): refugio y fogata SUMAN al objetivo
   ambiental de estación+clima en vez de fijarlo a un valor fijo -- la
   severidad real del frío importa. Con los números reales de
   `config/clima.yaml` (otoño=0.45, invierno=0.15, brecha de 0.3) y
   `bono_confort_refugio`/`bono_confort_fogata`=+0.3 cada uno
   (PROVISIONAL): otoño+refugio≈0.75 (suficiente, sin necesidad real de
   fuego), invierno+refugio≈0.45 (todavía frío, la utilidad de
   `ENCENDER_FUEGO` sigue siendo real), invierno+refugio+fogata≈0.75
   (equivalente al confort de un otoño con refugio) -- emergente de la
   estación/clima real del día, no un umbral fijo por estación.

**Implementado**:
- `componentes/fogata.py`: `Fogata.combustible_restante` -- mismo molde
  que `Necromasa`/`Construccion` (Posición + dato puro, sin Identidad ni
  Intención). Distinta del incendio (`Celda.en_llamas`,
  `sistema_desastres.py`): esa es un peligro estocástico que se propaga y
  daña a quien esté encima; una Fogata es deliberada, no se propaga, no
  daña a nadie.
- `nucleo/fuego.py`: funciones puras -- `fogata_en`/`hay_refugio_en`
  (búsqueda lineal por celda+zona, mismo criterio de escala que
  `construccion_propia`) y `celda_tiene_combustible` (mismo catálogo
  apto_construccion+combustibilidad>0 que ya usa RECOLECTAR).
- `Accion.ENCENDER_FUEGO` nueva: utilidad = `1.0 - confort_termico`
  (responde a una necesidad real, a diferencia de CONSTRUIR/RECOLECTAR
  que usan una utilidad base fija), gateada a 0.0 si falta consciencia,
  menos de `piedras_necesarias`=2 en `Agarre.objetos`, sin combustible en
  la celda actual, o ya hay una Fogata ahí. Sin desplazamiento, igual que
  RECOLECTAR/ALIVIARSE -- se resuelve donde ya se está.
- `sistema_recursos.py:_resolver_encender_fuego`: tirada de éxito
  (`probabilidad_encender_fuego`=0.4, PROVISIONAL -- golpear piedra
  contra piedra no siempre prende), consume yesca de `Celda.recursos` (NO
  las piedras del `Agarre` -- son herramientas de percusión, se quedan
  sujetas). `_consumir_fogatas`: cada Fogata quema su propio combustible
  cada tick con independencia de quién la encendió, se elimina sola al
  agotarse -- mismo patrón que la descomposición de Necromasa, sin acción
  de avivar/alimentar todavía.
- `nucleo/persistencia.py`: `Fogata` persistida (tabla `fogata_estado`,
  mismo molde que `construccion_estado`), `VERSION_ESQUEMA` →
  `0.30-fase0`.

**HALLAZGO REAL, no resuelto -- la precondición de "dos piedras" resultó
casi inalcanzable en juego normal**. Verificado con arnés dirigido (6
comprobaciones: gate sin piedras, utilidad gana con piedras+frío, gate
con Fogata ya presente, tirada+consumo real, extinción tras agotar
combustible, bono aditivo confirmado numéricamente -- 0.6 sin nada, 0.9
con refugio, 1.0 con ambos topado) -- todo correcto en aislamiento. Pero
en 4 semillas × 3000 ticks de motor real sin intervención, **ningún gnomo
encendió fuego ni una sola vez**. Diagnóstico: `piedra` como
`tipo_sustrato` es rara en el mapa (52-198 celdas de ~1600, frente a
1281-1547 de `arcilla`) -- un gnomo solo agarra piedra si está de pie
sobre una celda cuyo sustrato es literalmente piedra en el instante
exacto en que le queda un punto de agarre libre, y como
RECOLECTAR/`Agarre` son puramente oportunistas (sin búsqueda de sitio),
en las 4 semillas los gnomos terminaron agarrando `arcilla` (o nada),
nunca piedra. Posible error de modelo de fondo, no solo de calibración:
`tipo_sustrato` describe el terreno bajo los pies (relevante para
infiltración de agua), no necesariamente "hay piedras sueltas para
recoger aquí" -- en la realidad se encuentra una piedra de mano en
cualquier bioma sin que el suelo entero sea rocoso.

**Tres vías planteadas a Diego, ninguna implementada, decisión
pendiente**: (a) aflojar el gate de ENCENDER_FUEGO a cualquier material
duro/mineral en vez de exigir literalmente "piedra" -- resuelve el
problema pero diluye la especificidad de "dos piedras"; (b) sesgar el
movimiento de un gnomo frío sin piedras hacia terreno con piedra --
resuelve de raíz pero es una pieza de comportamiento nueva, más grande
de lo que pide este círculo; (c) separar "piedra suelta" de
`tipo_sustrato` como un recurso propio, independiente del terreno base,
presente con cierta probabilidad en cualquier bioma -- mismo patrón que
`deposito_mineral`/materiales de flora ya son capas independientes del
terreno, más fiel a la realidad pero es una pieza nueva, no un ajuste.

**Verificado, además**: 3000 ticks de `BOSQUE_AUTO_TICKS` sin ninguna
excepción. 22/22 tests en verde. El bono térmico de refugio SÍ es
alcanzable y se confirmó en el arnés dirigido (no depende de la
precondición de piedra) -- el hallazgo afecta específicamente a
ENCENDER_FUEGO, no a todo el círculo.

**Pendiente real, explícito (CORREGIDO -- ver "Piedra suelta" más abajo
para la precondición de piedra, ya resuelta el mismo día)**: sin acción
de avivar/alimentar una Fogata existente;
`probabilidad_encender_fuego`/`masa_yesca_consumida_kg`/
`combustible_inicial_fogata_kg`/`tasa_consumo_combustible_fogata_kg_tick`
PROVISIONALES sin calibrar; el efecto social del fuego (punto de unión,
historias) y el cimiento de cocina que Diego mencionó como usos futuros
del mismo recurso, documentados en `componentes/fogata.py` pero sin una
sola línea de código.
## Piedra suelta -- corrección de modelo de recursos y de causalidad para
## que ENCENDER_FUEGO sea alcanzable de verdad (2026-08-31, mismo día)

El hallazgo de arriba ("la precondición de piedra, sin resolver") se
investigó a fondo el mismo día, con Diego, y llevó a dos correcciones de
diseño reales -- no solo una calibración numérica.

**Corrección 1 -- modelo de recursos**. `piedra` como `tipo_sustrato` era
la fuente equivocada: `tipo_sustrato` describe el TERRENO (relevante para
infiltración de agua, generación del mundo), nunca fue pensado como
catálogo de recursos recolectables. Diego lo conectó directamente con la
conversación de esa misma tarde sobre "qué es una celda" ("en una celda
de 100 metros cuadrados puede haber muchos recursos, árboles, hierba,
piedras, setas, raíces... lo lógico es enfocarlo en este punto como un
recurso más"). Solución: `piedra_suelta` como recurso propio en
`Celda.recursos`, independiente de `tipo_sustrato` y del bioma --
presente con `probabilidad_piedra_suelta_por_celda` (PROVISIONAL 0.2) en
CUALQUIER celda (superficie Y cuevas, `nucleo/zona_bioma.py` y
`nucleo/cueva.py`), no depletable al agarrar (mismo criterio "gratuito y
simbólico" que ya regía `Agarre`). `tipo_sustrato` sigue existiendo
exactamente igual para su propósito original (infiltración, recolección a
granel de arcilla/tierra/piedra para construcción) -- no se tocó nada de
esa vía, solo se dejó de usarla como fuente de piedra agarrable.

**Corrección 2 -- causalidad, no solo disponibilidad**. Con `piedra_suelta`
ya como recurso real, la primera propuesta seguía siendo defectuosa:
hacer que `RECOLECTAR` ganara utilidad "si `confort_termico` está bajo Y
faltan piedras" -- Diego lo rechazó con precisión: "¿tiene sentido que un
ser consciente que jamás ha experimentado el frío antes necesite hacerse
con dos piedras para hacer fuego más adelante? [...] si no sería una
norma, los seres conscientes desde que existen recogen dos piedras para
hacer fuego". Leer `confort_termico` directamente en la fórmula de
`RECOLECTAR` es una causa PARALELA a la de `ENCENDER_FUEGO`, no una
cadena -- exactamente el tipo de regla universal-sin-experiencia que el
principio 5 (leyes neutras) prohíbe. Corrección: la utilidad de
`RECOLECTAR` por piedra HEREDA el valor que `ENCENDER_FUEGO` tendría SI YA
tuviera las piedras (`1.0 - confort_termico`, la misma fórmula, propagada
hacia abajo desde el eslabón padre, no recalculada de forma independiente
desde la causa raíz) -- un individuo que jamás ha pasado frío real nunca
llega a esta rama con utilidad significativa, así que nunca desarrolla
interés en piedra tampoco. Diego describió esto como parte de un árbol de
decisión general (frío→fuego→piedra+combustible; hambre→cocinar→fuego→
piedra+combustible→si no hay, como fruta cruda) -- confirmado que el
patrón es correcto, pero NO se reescribió el motor a un planificador
jerárquico explícito (cambio de arquitectura desproporcionado): el propio
argmax de la Utility AI plana ya produce el mismo resultado (RECOLECTAR
compite con hambre/sed/sueño de siempre; si no hay piedra que agarrar, la
utilidad simplemente no crece y otra necesidad gana cuando pesa más --
"¿merece la pena seguir buscando, o como manzanas crudas?" emerge solo,
sin ninguna señal explícita de "abandono" que construir).

**Implementado**:
- `nucleo/zona_bioma.py:generar_zona_bioma` y `nucleo/cueva.py:
  generar_zona_cueva` ganan `probabilidad_piedra_suelta` (por defecto
  0.0, sin romper compatibilidad con otros llamadores) -- sembrado
  independiente del resto de recursos, mismo patrón de capas
  independientes que ya usan flora y `deposito_mineral`.
- `sistemas/sistema_decision.py`: el gate de `ENCENDER_FUEGO` pasa de
  contar `"piedra"` a contar `"piedra_suelta"` en `Agarre.objetos`. Si
  faltan piedras, `utilidad_recolectar = max(utilidad_recolectar, 1.0 -
  confort_termico)` -- el eslabón heredado, no una utilidad propia.
- `sistemas/sistema_recursos.py:_resolver_recolectar`: DOS vías
  distintas y documentadas, no una sola mezclada -- Vía 1 (piedra_suelta
  CON CAUSA: consciente + piedras faltantes + celda con `piedra_suelta`)
  se comprueba PRIMERO; Vía 2 (agarre genérico sin causa concreta,
  diseño original de `Agarre`, sin cambios) se mantiene intacta para el
  resto de materiales -- `piedra_suelta` queda automáticamente excluida
  de la Vía 2 porque no está en el catálogo de materiales
  (`apto_construccion` la filtra sin comprobación aparte).

**Verificado contra el motor real, dos pasadas**: (1) arnés dirigido
aislando la causalidad -- un gnomo con refugio ya terminado (sin ningún
otro motivo para que `RECOLECTAR` tenga utilidad) y `confort_termico=1.0`
elige `DEAMBULAR`, nunca `RECOLECTAR`; el mismo individuo con
`confort_termico=0.1` sí elige `RECOLECTAR`, heredando la utilidad de
fuego -- confirmado que la causa nunca se activa sin frío real. (2) Las
mismas 4 semillas del hallazgo original (42, 1, 7, 99; 3000 ticks cada
una): **3, 37, 38 y 2 fuegos encendidos respectivamente** (frente a 0 en
las cuatro con el diseño anterior), ninguna fogata quedó activa
indefinidamente en ninguna semilla (todas se extinguen solas, confirmando
que `_consumir_fogatas` funciona en juego real). 3000 ticks de
`BOSQUE_AUTO_TICKS` sin ninguna excepción. 22/22 tests en verde.

**Pendiente real, explícito**: `probabilidad_piedra_suelta_por_celda=0.2`
sigue PROVISIONAL, sin calibrar; sin acción de avivar/alimentar una
Fogata existente (sigue igual que antes de esta corrección); efecto
social y cocina siguen sin una sola línea de código; la Vía 2 (agarre
genérico) todavía puede coger `"piedra"` de `tipo_sustrato` para fines de
defensa general -- deliberadamente distinto de `"piedra_suelta"`
(propósito de fuego), sin que esto sea confuso en la práctica porque son
claves de cadena distintas, pero merece quedar anotado por si una sesión
futura confunde ambos conceptos de "piedra".
## Armas primitivas v2 -- rediseño de Agarre/Inventario, mergeado tras
## auditoría manual; banco de pruebas real de coste/eficiencia con una
## tarea compleja (2026-09-03)

Diego revisó el código de `feature/2026-09-01-armas-fabricadas` (PR
#1, nunca mergeado) y encontró problemas de fondo, no de detalle:
subir `puntos_agarre` de 2 a 3 fue un parche (el problema real es que
nada sale nunca de `Agarre`); el modelo de `Inventario`/`Agarre` no
tenía causalidad real (una criatura acumulaba recursos sin motivo);
fabricar solo podía usar lo que estaba literalmente en `Agarre`, nunca
lo que ya se portaba; la "Vía 2" de `_resolver_recolectar` (agarrar
cualquier cosa "porque se lo encuentra") viola el principio 5 (leyes
neutras). PR #1 cerrado, rama borrada por completo -- ver más abajo.

**Rediseño en brainstorming** (spec completa:
`docs/superpowers/specs/2026-09-03-armas-primitivas-v2-design.md`,
supersede a la de 2026-09-01, conservada como registro histórico):

- **Sin norma fija por especie** (corrección real de Diego a mi primera
  propuesta): el efecto de un arma no lo decide la especie, lo decide
  el temperamento y la situación de cada individuo -- un gnomo poco
  agresivo la usa a la defensiva, un futuro individuo agresivo
  atacaría con la misma arma y la misma ley.
- **El arma modula `nucleo/conflicto.py:indice_asertividad_social`**
  (primer consumidor real de "robo/agravio genérico" que ese
  resolutor ya esperaba desde su diseño original), no una lógica de
  combate nueva.
- **`Inventario` gana objetos discretos** (`objetos: list[str]`, un
  palo, una piedra, un arma fabricada, cada uno con su propio peso)
  junto a `contenidos` (kg a granel, sin cambios, sigue para
  construcción). Corrección real de Diego sobre mi primera propuesta
  ("no guardo kilos en mis bolsillos, llevo objetos").
- **`Agarre` cambia de semántica, no de forma**: de "lo que agarré
  alguna vez" (solo crecía) a "lo que empuño AHORA" -- subconjunto
  decidido y reversible de `Inventario.objetos`, recalculado cada
  tick por una fórmula continua (`Necesidades.seguridad` +
  `Temperamento.valentia` + amenaza real presente), **sin regla de
  zona** -- otra corrección real de Diego ("no debemos plantear que
  estar fuera del asentamiento signifique estar inseguro"). Primer
  consumidor real de `Temperamento.valentia`, sin ninguno hasta ahora.
- **"Todo es un arma"**: un material crudo `apto_arma` empuñado ya
  tiene efecto (nivel 1). Fabricar combina materiales por receta de
  catálogo (`config/armas.yaml`, madera=lanza nivel 2, piedra=hacha_mano
  nivel 2, madera+piedra=hacha_primitiva nivel 3) -- sin nombres de
  arma hardcodeados en Python.
- **Sin Accion nueva para empuñar/guardar** -- ajuste automático
  recalculado cada tick, no una decisión que compite por turno.

**Deliberadamente sin plan de código pre-escrito** -- a diferencia de
los arcos de flora (código completo en varios de los 5 planes), esta
spec se entregó como blueprint puro: el objetivo explícito era medir
coste/eficiencia real del modelo barato (`agente-obrero`/
`deepseek-v4-flash-0731` vía `mini-swe-agent`) ante una tarea de
complejidad real, no una pieza mínima.

### Resultado del pipeline: 3/3 intentos agotaron el timeout, disyuntor
### activado -- pero el trabajo acumulado era sustancial y correcto

Los tres intentos (900s cada uno) terminaron en código de salida 124
(timeout), nunca en una convergencia propia del modelo a un commit
final. El disyuntor de 3 intentos se activó exactamente como se
diseñó, dejando el plan en `docs/plans/failed/`. **Esto NO significa
que el modelo se quedara atascado sin avanzar**: el diff acumulado en
los tres commits de seguridad (`c3657da`/`5a3038b`/`48c0b95`) suma
1245 inserciones en 16 ficheros, incluido un fichero de tests nuevo de
363 líneas (`tests/test_armas_primitivas_v2.py`) con la misma
disciplina de "ley física" que el resto del proyecto -- la última
franja visible del log (paso 117 del tercer intento) muestra al modelo
todavía verificando cuidadosamente detalles reales contra `master`
(confirmando que `puntos_agarre` de gnomo ya estaba en 2, revisando
`sistema_depredacion.py`/`sistema_movimiento.py`), no dando vueltas en
un bucle improductivo. La hipótesis más probable, no confirmada con
más profundidad: cada uno de los 3 intentos reinicia el CONTEXTO de
razonamiento del modelo desde cero (solo hereda el estado del código
de intentos anteriores, nunca el razonamiento), así que buena parte de
cada intento se gastó re-explorando/re-verificando trabajo que un
intento previo ya había dejado casi completo, en vez de partir de
"esto ya está verificado, sigue desde aquí".

**Auditoría manual completa antes de mergear** (pedida explícitamente
por Diego: "audítalo, deja todo corregido si algo falla"). Revisión
línea a línea de los 16 ficheros contra la spec -- **no se encontró
nada que corregir**, la implementación es fiel, causal, y en un punto
mejora la propia spec: `_resolver_fabricar_arma` busca material tanto
en `Inventario` como en `Agarre` (no solo donde la spec decía) --
hallazgo real y documentado por el propio modelo, con test dedicado
(`test_ley_ciclo_completo_recolectar_fabricar_empunyar`): sin mirar
`Agarre`, una criatura asustada que ya empuñó su único palo (por el
reflejo de empuñar) nunca llegaría a fabricar nada, quedándose en un
ciclo de recolectar/huir sin cerrar. También excluyó a propósito
`piedra_suelta` (la piedra de percusión del fuego) del reflejo
empuñar/guardar genérico -- moverla cada tick habría roto el ciclo
causal frío→recoger→encender (un individuo seguro con frío soltaría
las piedras antes de acumular las dos necesarias), documentado en el
propio `componentes/agarre.py` con la misma disciplina causal que el
resto del proyecto exige.

**Verificación contra el motor real, más allá de los tests** (99/99
tests en verde tras el merge, antes 87): 5 semillas (42, 7, 1, 99, 3,
12) × 3000-6000 ticks sin ninguna excepción. Semillas 42 y 7 llegaron a
extinción total hacia el final de la ventana -- **ya documentado como
comportamiento conocido y preexistente** (semilla 42 en la sección de
"Sobrepoblación..." de este mismo documento, semilla 7 con fragilidad
de gnomo ya señalada en la verificación de `Agarre`), no una regresión
de esta pieza. **Semilla 3 confirmó el mecanismo completo en juego real
sin intervención**: 2 eventos `ArmaFabricada`, un gnomo con
`hacha_mano` real en `Inventario.objetos` a los 3000 ticks.

**Hallazgo honesto, no corregido (fuera de alcance real, no un
fallo)**: las piedras de percusión retiradas al encender una fogata se
depositan en `Inventario.objetos` para siempre (nunca se reutilizan ni
se descartan) -- observado en juego real (varios gnomos con 2
`piedra_suelta` "muertas" en Inventario más 2 activas en Agarre para
la próxima fogata). Ninguna spec, ni la de 2026-08-31 ni esta, definió
qué hacer con piedras de fuego ya usadas -- ni bug ni regresión, un
hueco honesto más para la lista de pendientes de "soltar/gastar" un
objeto.

### Coste y eficiencia real medidos

`.ai-pipeline/costes/costes.jsonl`: **$0.619407 reales** (balance de
OpenRouter antes/después) para las 3 intentos completos, 429 pasos de
modelo en total (151+161+117 por intento). Comparado con el coste
autoinformado por el propio `mini-swe-agent` en el último paso visible
de cada intento (~$0.18/$0.20/$0.12, suma ~$0.50): **discrepancia real
de ~24%, no el ~3x del hallazgo de zoocoria** (sección "Coste real del
pipeline" más arriba) -- indicio de que el fix de precio de caché de
prompt (`300b093`) cerró la mayor parte del hueco, aunque no todo.

Para poder correr esta tarea sin que el disyuntor de coste la cortara
a mitad de camino, se subió temporalmente `-l` (0.30→1.50 en
`run-plan.sh`) y `max_budget` (1.00→6.00 USD/día en
`litellm_config.yaml`), cada uno en su propio commit explícito
(`74ef8b1`) y revertido a los valores originales tras el experimento
(`aea9b84`) -- el proxy se reinició dos veces (subida y bajada) para
que el proceso en memoria coincidiera con el fichero.

**Balance del experimento**: el modelo barato SÍ es capaz de diseñar e
implementar correctamente una tarea de complejidad real (rediseño de
dos componentes existentes, una acción nueva, dos consumidores
conectados, causalidad completa, tests de "ley física") trabajando
solo desde una spec -- pero no dentro del presupuesto de tiempo de un
único intento de 900s, ni tampoco de tres intentos con contexto de
razonamiento reiniciado en cada uno. El coste real total ($0.62) sigue
siendo bajo en términos absolutos, pero el proceso no fue autónomo de
principio a fin -- requirió una auditoría humana (o de Claude) para
cerrar lo que el pipeline dejó a medio converger. **Pendiente,
señalado por Diego para una conversación futura** (ver memoria de
sesión): el propio flujo del pipeline (nombres de script, carpetas
`docs/plans/*` vs `docs/superpowers/specs/`) sigue pensado para
"planes escritos por Claude", no para el flujo real de hoy
("spec → el modelo diseña e implementa") -- candidato a revisar antes
de repetir un experimento de esta escala.

Commits: `00eb475` (spec), `9b52037`/`74ef8b1` (puesta al día de este
documento + subida temporal de presupuesto), merge `--no-ff` de
`feature/2026-09-03-armas-primitivas-v2` a `master`, `aea9b84`
(revert del presupuesto).
## Sistema de comidas -- dieta real de gnomo + catálogo de toxicidad,
## precede a "cómo cocinar" (spec, implementado directamente por Claude,
## 2026-09-08)

Diego pidió separar explícitamente "qué es la comida" de "cómo se
cocina" antes de diseñar las cocinas comunes -- dos conversaciones, no
una. Arranque real: preguntó qué come gnomo hoy, y al ver los 13
recursos completos del catálogo (herencia del círculo de "alimentos
huérfanos", 2026-09-07) reaccionó: "no tiene sentido que un gnomo coma
hierba".

**Dieta de gnomo reducida a 6 claves reales**: `raices`+
`raices_deserticas` (raíces), `manzanas`, `bayas_espinosas`+
`bayas_montanas` (bayas), `nectar_semillas` (néctar) -- una dieta de
forrajero humanoide plausible en vez de "come literalmente todo el
catálogo". Se cae `hierba`/`fruto_de_cactus`/`liquen`/`musgo`/
`bellotas`/`brotes_helecho`/`brotes_articos` de la dieta de gnomo --
siguen existiendo en el mundo para otras especies (ardilla ya come
bellotas), solo dejan de ser comestibles para gnomo.

**Hallazgo real que surgió de la propia pregunta**: ¿qué de esa dieta
podría ser tóxico en crudo? Diego: "las raíces y las bayas pueden llegar
a ser tóxicas" -- primer caso REAL para
`DimensionesFisicas.resistencia_enfermedad`, sorteado por individuo
desde hace tiempo sin ningún consumidor (mismo patrón que valentía/
empatía antes de su primer uso). Corrección real de diseño en el
camino: la primera propuesta de Claude sugería el riesgo específicamente
para carne cruda (razonable dado que ningún consciente come carne hoy)
-- Diego corrigió: "ahora no hay razas conscientes que consuman carne,
pero las habrá... el proceso de cocinado tiene que ser un poco
universal". El mecanismo no excluye la carne por diseño, simplemente
hoy nadie consciente la come -- el día que exista una raza carnívora
consciente, usaría el mismo campo y el mismo mecanismo sin ningún caso
especial.

**Visión a futuro, anotada, sin diseñar**: Diego conecta esto con una
futura alquimia -- un sistema de procesado genérico compartido entre
comida, refinamiento de metales (ya existe minería de vetas), y un
futuro sistema de magia. El multiplicador universal de mejora (sin
tabla de recetas por alimento) que se decidió para "comida elaborada"
es justo lo que dejaría esa puerta abierta más adelante, sin
comprometerse a nada de eso ahora.

Spec: `docs/superpowers/specs/2026-09-08-sistema-comidas-design.md`.
**Secuenciación deliberada, para no soltar un riesgo sin cura**: este
círculo solo añade el CATÁLOGO -- `toxico_crudo: true` en las 4 claves
de raíces/bayas (`config/flora.yaml`, mismo patrón que
`apto_construccion`/`compite_espacio_fisico`) -- como dato inerte, sin
ningún código que lo lea todavía. Activar la probabilidad real de
intoxicación (modulada por `resistencia_enfermedad`) y el multiplicador
`factor_mejora_elaboracion` quedan explícitamente para cuando se diseñe
"cómo cocinar" (círculo siguiente), implementados JUNTOS -- introducir
el riesgo ahora sin ninguna cura disponible habría sido una regresión
real para gnomo.

**Verificado**: 348/348 tests (4 nuevos, `tests/test_sistema_comidas.py`
-- dieta exacta, `toxico_crudo` marcado exactamente donde corresponde,
regresión del resto del catálogo). `BOSQUE_AUTO_TICKS=3000` sin
excepciones. Diagnóstico dirigido adicional (Diego: "testea qué provoca
en el mundo", 3 semillas nuevas, arnés en scratchpad no comiteado, con
salvaguarda de tiempo real de 40s/corrida tras un primer intento que
tardó demasiado): la dieta reducida no muestra evidencia de perjudicar
la supervivencia de gnomo frente a la dieta vieja de 13 recursos (9→10,
12→13, 11→15 individuos vivos en las 3 semillas) -- muestra pequeña,
reportada con la misma cautela metodológica ya establecida en este
proyecto sobre comparaciones semilla-a-semilla (el cambio puede desviar
la secuencia de aleatoriedad aguas abajo).

**Pendiente real, explícito**: el círculo de "cómo cocinar" (acción de
elaborar, activación real de toxicidad + `resistencia_enfermedad`,
`factor_mejora_elaboracion`, y solo entonces las cocinas comunes como
edificio) es el siguiente paso inmediato de este mismo arco; dieta de
conejo/ardilla/caballo no revisada (Diego solo pidió corregir la de
gnomo); alquimia como sistema de procesado genérico compartido con
metalurgia/magia, mencionada, sin ningún diseño todavía.
## Cómo cocinar -- Accion.COCINAR, comida elaborada, toxicidad real
## activada (spec, implementado directamente por Claude, 2026-09-08)

Cierra el círculo de "sistema de comidas" abierto el mismo día,
activando el catálogo `toxico_crudo` que había quedado deliberadamente
inerte. Spec: `docs/superpowers/specs/2026-09-08-como-cocinar-design.md`.

**Decisión de Diego contra la recomendación inicial de Claude**:
`Accion.COCINAR` dedicada, no un efecto pasivo en la Fogata (Claude
prefería lo pasivo para no repetir el patrón de curvas de utilidad
casi inalcanzables ya visto con `ENCENDER_FUEGO`/"piedra suelta").
Mitigado con utilidad BASE FIJA (mismo patrón que `CONSTRUIR`), no una
fórmula nueva que calibrar.

**Decisión de Diego sobre severidad, tras plantearle el riesgo real**:
intoxicación = muerte probabilística, mismo molde que las demás
`probabilidad_muerte_*` ya existentes -- aceptado explícitamente el
riesgo de un vector de muerte nuevo para gnomo (la especie más frágil
del catálogo), mitigado con una probabilidad base deliberadamente muy
baja (`0.001`, muy por debajo de las demás) y verificación obligatoria
antes de confiar en ella.

**Hallazgo real del propio auto-repaso del spec, con consecuencias
serias evitadas antes de escribir código**: la primera versión del
chequeo de toxicidad no llevaba gate de consciencia. Conejo y caballo
también comen `raices`/`bayas_espinosas` (ahora tóxicas) en su dieta --
sin el gate, ambas especies habrían quedado expuestas a un vector de
muerte permanente sin ninguna forma de cocinar jamás (fauna no puede
construir Fogata ni tiene `Accion.COCINAR`). Corregido: el chequeo
completo (forraje de celda y salida de provisiones) exige
`cap_mental.consciencia >= umbral_consciencia_agencia`, mismo umbral
que el resto del arco -- fauna aplazada, no descartada.

**Mejora dirigida real, encontrada al diseñar**: la lógica de morir
(instanciar `Necromasa`, emitir `Muerte`, purgar la entidad) vivía solo
dentro de `sistema_necesidades.py:_resolver_deceso`, sin ser invocable
desde otro sistema. Extraída a `nucleo/entidad.py:procesar_deceso(...)`
-- `_resolver_deceso` pasa a ser un wrapper de una línea, comportamiento
idéntico (regresión verificada). Permite que `sistema_recursos.py` mate
por intoxicación sin duplicar esa lógica.

**Arquitectura real**:
- `nucleo/comida.py` (nuevo): `elaborar_recurso`/`es_elaborado`/
  `recurso_base` -- funciones puras, mismo patrón que
  `nucleo/intercambio.py`. Comida elaborada = clave con sufijo
  `_elaborada` DENTRO del mismo `Inventario.provisiones` (no una
  transferencia entre entidades, una transformación del propio
  recurso), con `factor_mejora_elaboracion` (multiplicador único y
  universal, sin tabla de recetas) sobre `valor_nutricional`/
  `valor_hidratacion`.
- `_resolver_cocinar` transforma hasta `tasa_cocinar_kg_tick` del
  primer recurso crudo no vacío por tick.
- La versión `_elaborada` **elimina la toxicidad por completo**, no la
  reduce -- binario, "cocinar es la cura".
- Con ambas versiones guardadas, se prefiere comer la `_elaborada`
  (orden de búsqueda explícito por cada alimento de la dieta, no una
  búsqueda global "cualquier elaborada del inventario").
- El mecanismo no excluye la carne por diseño -- hoy ningún consciente
  la come, pero el día que exista una raza consciente carnívora usaría
  exactamente el mismo `toxico_crudo`/`Accion.COCINAR`, sin ningún caso
  especial que escribir (universal, tal como pidió Diego).

**Verificado**: 368/368 tests (20 nuevos,
`tests/test_como_cocinar.py` -- extracción de `procesar_deceso`,
funciones puras de `nucleo/comida.py`, `_resolver_cocinar`, valores
nutricionales efectivos, toxicidad con tirada forzada matando al
consciente y NUNCA a la versión elaborada, `resistencia_enfermedad`
alta reduciendo la probabilidad efectiva, **fauna exenta confirmada
explícitamente** (conejo comiendo `raices` tóxicas con tirada forzada
nunca muere), preferencia por lo elaborado, utilidad de `COCINAR` en
sus tres condiciones, roundtrip de persistencia). `BOSQUE_AUTO_TICKS=3000`
sin excepciones: `cocinar` se resolvió 37 veces, **0 muertes por
intoxicación**.

**Verificación reforzada, honesta sobre sus límites**: la corrida de
`BOSQUE_AUTO_TICKS` de esa semilla tardó ~10 minutos en vez de los 5-15
segundos habituales -- investigado antes de dar la pieza por buena:
**697 conejos vivos al final**, la explosión de población de conejo ya
documentada en este proyecto (boom-bust conocido, disparada esta vez
por el desplazamiento de la secuencia de `rng` que cualquier código
nuevo introduce, mismo fenómeno metodológico ya explicado varias veces
en este documento) -- sin relación causal con "cómo cocinar" en sí. Un
arnés dirigido aparte (6 semillas nuevas, scratchpad, con salvaguarda
de tiempo de 45s/semilla) confirmó **0 muertes por intoxicación de 36
muertes de gnomo totales**, con `cocinar` disparándose de forma
consistente (9-22 veces por semilla) -- probabilidad verificada segura
para gnomo. Honestidad explícita: con una probabilidad tan
conservadora, no se ha observado matar a nadie todavía en ~9000 ticks
combinados de juego libre -- el mecanismo en sí ya está probado
correcto por los tests con tirada forzada, lo que falta observar es su
disparo real bajo esta probabilidad, mismo patrón "correcto pero raro"
ya visto varias veces en este proyecto.

**Pendiente real, explícito**: las cuatro constantes nuevas
(`utilidad_cocinar_base`, `tasa_cocinar_kg_tick`,
`probabilidad_muerte_intoxicacion_base`, `factor_mejora_elaboracion`)
PROVISIONALES, sin calibrar contra el harness completo; **cocinas
comunes (edificio) es el siguiente círculo real del arco** "dinámicas
internas de asentamiento"; toxicidad para fauna, memoria de "sitio
donde algo me hizo daño", y variación de toxicidad por atributo más
allá de `resistencia_enfermedad` quedan fuera, sin necesidad real
todavía; la explosión de conejo sigue siendo el mismo problema conocido
de siempre, sin tocar en este círculo.
## Aptitud vocacional -- Círculo 1 del arco "fabricación y uso de
## herramientas", implementado directamente por Claude (2026-09-11)

Diego arrancó el arco pidiendo plantear "fabricación y uso de
herramientas", con una intención de fondo explícita: que las
herramientas sean la base de profesiones que emerjan solas, "no un
catálogo de profesiones que se asignen con un guion, si no que de las
necesidades de un individuo o grupo junto a las habilidades y
temperamento del individuo nazcan una serie de profesiones". Tres
decisiones cerradas con Diego antes de diseñar (`AskUserQuestion`):
alcance del primer círculo (solo tendencia + observabilidad, sin mejora
por práctica -- evita reabrir "mutación causal de rasgos", ya aplazada
una vez en el arco de hilo individual -- ni reconocimiento social);
cubetas vocacionales (las 4 acciones YA existentes: forrajero/minero
-> RECOLECTAR, constructor -> CONSTRUIR, artesano -> FABRICAR,
cocinero -> COCINAR, sin ningún verbo nuevo); orden (aptitud derivada
primero, herramientas físicas vía FABRICAR quedan para el círculo
siguiente).

**Por qué no es un catálogo autorado (principio 5)**: dos piezas
deliberadamente separadas, ninguna escribe jamás un string de
profesión. (1) **Aptitud** (`nucleo/vocacion.py:aptitud_forrajero/
aptitud_constructor/aptitud_artesano/aptitud_cocinero`): función PURA
de atributos que YA se sortean al nacer (`DimensionesFisicas`,
`Temperamento`, `CapacidadMental`) -- nada nuevo que sortear, nada que
persistir. Reparto fijo 60/40 por cubeta (atributo principal/secundario,
decisión de diseño en código, no magnitud de calibración en config):
forrajero = agudeza_sensorial+fuerza; constructor = fuerza+voluntad
(**primer consumidor real de `CapacidadMental.voluntad`**, cuyo propio
docstring esperaba justo esto: "necesidades superiores -- propósito,
trabajo"); artesano = inteligencia+curiosidad (**primer consumidor real
de `CapacidadMental.inteligencia`**, cuyo docstring decía literalmente
"espera... profesión emergente"); cocinero = inteligencia+agudeza_
sensorial. (2) **Vocación practicada** (`componentes/vocacion.py:
Vocacion`, mismo molde universal que Agarre/Semillas/Relaciones):
contador de ticks despachados por cubeta, `nucleo/vocacion.py:
vocacion_dominante()` la deriva por lectura (mismo criterio que
`biografia_de()`), puede DIVERGIR de la aptitud -- esa divergencia es
la parte genuinamente emergente.

**Mecanismo real**: `factor_aptitud(aptitud, peso) = 1.0 + peso *
(aptitud-0.5) * 2.0`, multiplicador centrado en 1.0, aplicado al valor
FINAL de cada una de las 4 utilidades en `sistema_decision.py` (tras
cualquier eslabón heredado -- RECOLECTAR por fuego/arma) y SOLO si esa
utilidad ya es >0.0 -- multiplicativo, nunca crea utilidad donde no la
había, misma causalidad que ya exige el resto del motor. Gateado a
consciente (mismo `umbral_consciencia_agencia` de siempre).
`vocacion.peso_aptitud_vocacional=0.3` (PROVISIONAL,
`config/comportamiento.yaml`). Contador incrementado en el DESPACHO de
cada acción (`sistemas/sistema_recursos.py:_incrementar_vocacion`, no
tras confirmar éxito) -- representa "ticks dedicados a esta labor".
Persistido (`componentes_estado.vocacion`, JSON, mismo molde que
agarre/relaciones), `VERSION_ESQUEMA` sube a `0.37-fase0`.

**Del "necesidades de un individuo o grupo" que mencionaba Diego, solo
se modela hoy lo que ya existía** (`objetivo_construccion_actual` ya
hace depender CONSTRUIR/RECOLECTAR de qué necesita el asentamiento) --
ninguna señal nueva de escasez de vocación a nivel de grupo (p.ej.
"nadie cocina, sube la utilidad de COCINAR para todos"). Señalado como
pendiente real, explícitamente fuera de este primer círculo
(reconocimiento social, declinado por Diego).

Spec: `docs/superpowers/specs/2026-09-11-aptitud-vocacional-design.md`.
**Implementado directamente por Claude** -- mismo escenario ya
documentado repetidas veces esta semana: centinela parado desde el
incidente de madriguera-física-A, este contenedor cloud tampoco tiene
`OPENROUTER_API_KEY`/`mini-swe-agent`.

**Verificado**: 485/485 tests en verde (14 nuevos,
`tests/test_vocacion.py` -- las 4 fórmulas de aptitud, `factor_aptitud`
en sus tres zonas, `vocacion_dominante` con empate/vacío/ganador claro,
un test de integración real contra `sistema_decision.py` que calibra un
competidor exacto -- SOCIALIZAR -- al punto medio entre el factor
mínimo y máximo de aptitud, y confirma que RECOLECTAR gana con aptitud
alta y pierde con aptitud baja, no solo que el número interno cambia;
gate del contador solo consciente; roundtrip de persistencia).
`BOSQUE_AUTO_TICKS=3000` sin excepciones, `BOSQUE_CONTINUAR=1` con 200
ticks más sin excepciones (roundtrip real, no solo de test). El
mecanismo se ejerce de verdad en juego libre: 23-24 gnomos vivos con
"forrajero" como vocación dominante en ambas corridas -- coherente con
que RECOLECTAR ya era, por frecuencia, la cubeta más disputada antes de
esta pieza (13831 disparos del gate de manos libres en RECOLECTAR
frente a 9 resoluciones de COCINAR en la misma corrida de 3000 ticks).

**Pendiente real, explícito**: `peso_aptitud_vocacional=0.3` y el
reparto 60/40 por cubeta son PROVISIONALES, sin calibrar contra el
harness completo; en ninguna de las dos corridas de verificación
llegó a dominar constructor/artesano/cocinero (solo forrajero) --
correcto por los tests dirigidos, pero no confirmado que las otras 3
cubetas lleguen a ser dominantes en juego libre con una ventana más
larga; reconocimiento social y necesidad de grupo como señal de
escasez, fuera de este círculo; mejora por práctica, fuera de este
círculo (abriría mutación causal de rasgos); sin ninguna herramienta
física todavía -- el círculo 2 real de este arco, ya acordado con
Diego, es fabricación de herramientas vía `Accion.FABRICAR` (categoría
"herramienta", el resolutor `candidatos_fabricar` ya preparado para un
segundo candidato desde el rename `FABRICAR_ARMA -> FABRICAR` del
2026-09-11); sin ningún consumidor de `vocacion_dominante` en narrador/
vista_web todavía -- presentación, deliberadamente sin tocar (motor
primero).
## Fabricación de herramientas -- Círculo 2 del arco "fabricación y uso
## de herramientas", implementado directamente por Claude, hallazgo real
## sobre por qué nunca se ejerce en juego libre (2026-09-11, mismo día)

Diego dio la señal de continuar ("sigue") tras cerrar Círculo 1
(aptitud vocacional, arriba). Spec:
`docs/superpowers/specs/2026-09-11-fabricacion-herramientas-design.md`.
Reutiliza sin inventar nada nuevo: los mismos materiales crudos
madera/piedra de "armas primitivas v2" (2026-09-03), el mismo
mecanismo de recolección causal (`_via_material_crudo`, ya extraído y
compartido en la sesión de Bloque A del mismo día), y el resolutor
`candidatos_fabricar` que el rename `Accion.FABRICAR_ARMA ->
Accion.FABRICAR` (Bloque A, mismo día) ya había dejado preparado para
un segundo candidato.

**Implementado**: `nucleo/herramientas.py:tiene_herramienta` (función
pura, deliberadamente SIN "todo es una herramienta" -- a diferencia de
armas, material crudo sin fabricar no tiene ningún efecto de
herramienta); `config/herramientas.yaml` con una única receta
(`hacha_primitiva`, madera+piedra, nivel 1 -- deliberadamente pequeño
para este primer círculo) y los dos bonos multiplicativos de velocidad
(recolección a granel, aporte a construcción), ambos PROVISIONALES;
`sistema_decision.py` gana el bloque `utilidad_categoria_herramienta`
(mismo molde que "arma": RECOLECTAR hereda `necesidad_trabajo =
max(utilidad_recolectar, utilidad_construir)` cuando no hay receta
completable con lo que ya se porta y la celda ofrece material crudo);
`componentes/intencion.py:recolectar_motivo_herramienta`;
`sistema_recursos.py` gana la Vía 3 de `_resolver_recolectar`
(comparte `_via_material_crudo` con la Vía 2 de arma, gateada por
`tiene_herramienta` en vez de `tiene_arma_nivel2_o_mas`) y la rama
"herramienta" de `_resolver_fabricar` (emite `Evento(tipo=
"HerramientaFabricada", severidad=NOTABLE)`).

**Bug de diseño real, encontrado y corregido ANTES de comitear, no al
fallar en caliente**: el primer intento descontaba la utilidad heredada
(`necesidad_trabajo * factor_urgencia_herramienta`, 0.5) -- igual que
un error ya evitado una vez con "arma" en su día, este descuento deja a
FABRICAR-herramienta matemáticamente incapaz de ganarle nunca a la
propia necesidad de RECOLECTAR/CONSTRUIR que lo origina, así que nunca
llegaría a fabricarse nada. Detectado por dos tests de
`sistema_decision.py` fallando antes de comitear, corregido eliminando
el descuento por completo (mismo patrón sin descuento que ya usa
"arma": `1.0 - seguridad` sin multiplicador) -- `factor_urgencia_
herramienta` retirado de `config/herramientas.yaml`, sustituido por un
comentario documentando por qué se descartó. Efecto colateral real,
también corregido: la interacción con el Círculo 1 (aptitud
vocacional, mismo día) rompía la comparación numérica exacta que un
test de decisión asumía -- los atributos de aptitud se sortean por
individuo, así que dos utilidades que "deberían" empatar quedaban
moduladas por factores distintos. Corregido neutralizando los 5
atributos relevantes de aptitud a 0.5 en el fixture del test
(`factor_aptitud=1.0` para las 4 cubetas), aislando el comportamiento
bajo prueba del ruido de otro círculo cerrado el mismo día.

**Verificado**: 497/497 tests en verde (12 nuevos,
`tests/test_fabricacion_herramientas.py`), `BOSQUE_AUTO_TICKS=3000` y
`BOSQUE_CONTINUAR=1` (roundtrip) sin ninguna excepción.

**Hallazgo real del diagnóstico multi-semilla, no anticipado en el
spec -- el mecanismo nunca se ejerce en juego libre, y se identificó
por qué**. Arnés de sesión (scratchpad, no en el repo, reutilizando
`main.py:ejecutar_tick` tal cual con una `Persistencia` no-op): 10
semillas nuevas combinadas (70101-70105, 80201-80203, 80301-80302),
entre 2200 y 6500 ticks cada una según el presupuesto de tiempo real
disponible en este entorno de cómputo limitado. **`HerramientaFabricada`
nunca se disparó en ninguna de las 10** -- ni un solo gnomo llegó a
portar madera+piedra simultáneamente, y `con_hacha_en_inventario_o_
agarre` fue 0 en todas.

Instrumentado el propio arnés (monkeypatch en memoria, sin tocar el
repo) para distinguir "el mecanismo nunca se activa" de "se activa
pero algo bloquea la recolección real" -- resultado inequívoco:
`Intencion.recolectar_motivo_herramienta` se activó con mucha
frecuencia (245 a 1620 veces por semilla en las últimas 5 semillas
medidas, 4583 en total) -- el eslabón causal de `sistema_decision.py`
está lejos de ser "correcto pero invisible", se ejerce con fuerza real.
El bloqueo real está en la resolución física: de 1152 llamadas a
`_via_material_crudo` bajo motivo activo (últimas 2 semillas
instrumentadas), **882 y 270 fallaron por falta de espacio de carga**
(`via_sin_espacio`, `espacio_disponible_kg` insuficiente) -- un gnomo
que ya porta cargas de material a granel (arcilla, hierba_seca... para
CONSTRUIR) casi siempre tiene su `Inventario` lleno hasta el límite de
peso, sin sitio para un objeto discreto adicional (madera o piedra
enteras). Solo 13 de esas 1152 llamadas (`via_exito`) lograron recoger
material con éxito -- y ninguno de esos 13 casos sobrevivió hasta el
final de su corrida (el gnomo murió, o el material se perdió por otra
vía como robo, antes de completar el par madera+piedra necesario para
fabricar).

**Conclusión honesta**: el círculo está mecánicamente correcto (12
tests dirigidos lo confirman, incluido el ciclo completo recolectar→
fabricar en aislamiento) y el eslabón causal de decisión se activa con
fuerza real en juego libre -- pero la fabricación de herramientas en sí
es, en la práctica, casi inalcanzable con la configuración actual, por
una causa estructural distinta y más sutil que cualquiera de los casos
previos de "correcto pero invisible" de este proyecto (ENCENDER_FUEGO
original, salón común, pareja estable...): no falta motivo, ni
material en el mundo, ni tiempo -- falta espacio de carga libre en el
momento exacto en que el motivo está activo, porque el mismo individuo
que necesita una herramienta para trabajar suele estar ya cargado de
lo que esa misma necesidad de trabajo le hizo recolectar a granel.
Señalado con honestidad, sin corregir en este círculo -- ninguna
decisión de diseño tomada sobre si merece su propio círculo de
corrección (candidatos sin explorar: reservar un margen de carga para
objetos discretos, o que el motivo de "necesidad de trabajo" primero
vacíe/deposite la carga a granel antes de intentar portar material de
herramienta).

**Pendiente real, explícito**: `factor_bono_tasa_recolectar_con_
herramienta=1.5`/`factor_bono_tasa_aporte_construccion_con_
herramienta=1.3` PROVISIONALES, sin calibrar, y sin haberse observado
nunca en juego libre (ningún gnomo llegó a fabricar una herramienta en
la muestra medida); el hallazgo de competencia por capacidad de carga
queda señalado, pendiente de que Diego decida si abrir un círculo de
corrección dedicado o dejarlo así por ahora; con esto, el arco
"fabricación y uso de herramientas" tiene sus dos círculos planteados
originalmente implementados (aptitud vocacional, fabricación de
herramientas) -- ningún círculo nuevo de este arco decidido todavía.
## Prioridad consciente -- corrección real al hallazgo de "sin espacio"
## de arriba, más un SEGUNDO hallazgo distinto sin resolver (2026-09-11,
## mismo día)

Diego, leyendo el hallazgo de "sin corregir en este círculo" de arriba,
lo cuestionó con precisión: *"esto es un problema, y no tiene sentido,
el ser consciente debería poder decidir qué carga, si quiere fabricar
un arma pero no tiene espacio en el inventario para recolectar los
materiales necesarios, lo lógico es que se desprenda de algo que tenga
para liberar el espacio y lograr su intención"*. Corrección real, no
una calibración numérica -- una ley nueva pequeña y bien acotada:

**Implementado**: `nucleo/inventario.py:descartar_contenidos_para_
liberar(contenidos, peso_a_liberar) -> float` -- función pura. Descarta
bulto de `Inventario.contenidos` (empezando por el material del que más
se porta -- el sacrificio más eficiente, menos materiales distintos
tocados, sin ninguna noción de "valor" entre materiales que el motor no
tiene), nunca más de lo pedido. El material descartado se pierde sin
más -- mismo criterio ya establecido el mismo día en la sesión de
Bloque A para la piedra de percusión del fuego una vez gastada: un
descarte deliberado y simbólico, no un sistema nuevo de "tirar al
suelo" con su propia física. Conectado en
`sistema_recursos.py:_via_material_crudo` (compartido por Vía 2 arma y
Vía 3 herramienta): si la intención causal YA GANADORA este tick
(`recolectar_arma`/`recolectar_herramienta`, ambas motivadas por
`sistema_decision.py` antes de llegar aquí -- nunca una intención
inventada en este punto) no tiene sitio para el material que necesita,
se descarta justo lo necesario de `contenidos` antes de reintentar.
Nunca toca `inv.objetos` -- ni armas ya fabricadas ni material ya
recolectado para la misma intención se sacrifican por esto. Contador de
observación `_stats_material_descartado_por_prioridad_kg`, impreso en
`BOSQUE_AUTO_TICKS`.

**Verificado**: 6 tests nuevos (la función pura en sus tres casos --
libera lo mínimo empezando por el mayor, agota sin pasarse si no
alcanza, no-op si no hace falta nada -- más 3 de integración real en
`_via_material_crudo`), 503/503 tests en verde con el resto de la
suite, `BOSQUE_AUTO_TICKS=3000` (6.00 kg descartados) y
`BOSQUE_CONTINUAR=1` (1.00 kg descartado, roundtrip sin excepciones) --
el mecanismo se ejerce de verdad en juego libre, no solo en tests
dirigidos.

**Segundo hallazgo real, distinto, encontrado al repetir el diagnóstico
multi-semilla tras el fix -- NO resuelto en este círculo**. La falta de
espacio no era el único bloqueo: repetido el mismo arnés (semillas
80301/80302, ~5000-5300 ticks cada una tras el fix), `con_madera`
empieza a aparecer con más frecuencia que antes del fix, pero
`con_piedra` sigue en 0 en TODAS las semillas probadas, antes y después
-- ningún gnomo llegó a portar madera+piedra simultáneamente en
ninguna corrida, y `herramientas fabricadas` sigue en 0 en todas.
Causa real, distinta de "sin espacio": `_resolver_recolectar` corre la
Vía 1 (piedra_suelta para fuego) SIEMPRE PRIMERO, sin comprobar si el
motivo real que trajo a esta entidad a RECOLECTAR este tick fue
realmente fuego -- mientras al individuo le falten sus 2 piedras para
encender fuego y la celda tenga piedra_suelta, Vía 1 la agarra e
interrumpe la resolución (`return`) antes de que la Vía 2/3
(arma/herramienta) llegue a considerar esa misma piedra_suelta como
material "piedra". El resultado: aunque `Intencion.recolectar_motivo_
herramienta`/`recolectar_motivo_arma` se activa con fuerza real (decenas
a miles de veces por semilla, confirmado por instrumentación), casi
nunca se traduce en portar "piedra" -- Vía 1 se la queda primero casi
siempre. `madera` no sufre esta competencia (Vía 1 solo mira
`piedra_suelta`, nunca materiales de flora), lo que explica la asimetría
observada (madera empieza a aparecer, piedra no).

**Deliberadamente NO corregido en este círculo** -- es una decisión de
diseño real sobre PRECEDENCIA entre dos motivos causales que compiten
por el mismo recurso físico (piedra_suelta), no una calibración
numérica ni un bug mecánico como el de espacio de arriba. Candidatos sin
explorar, ninguno decidido: (a) que Vía 1 solo dispare cuando el motivo
real de RECOLECTAR este tick fue efectivamente el heredado de fuego
(exigiría que `sistema_decision.py` marque también ese motivo, hoy solo
implícito en la utilidad elevada de RECOLECTAR, sin su propio flag como
sí tienen arma/herramienta); (b) que el propio ser consciente priorice
cuál necesidad (fuego vs. arma/herramienta) es más urgente antes de que
RECOLECTAR decida cuál piedra agarrar, en vez de que gane siempre quien
comprueba primero en el código. Pendiente de que Diego decida el
enfoque antes de tocar `_resolver_recolectar` otra vez.

**Pendiente real, explícito**: el segundo hallazgo de arriba (Vía 1
interceptando piedra_suelta antes que arma/herramienta) sigue bloqueando
la fabricación real de cualquier herramienta/arma que necesite piedra en
juego libre -- `herramientas fabricadas` y `armas fabricadas` siguen sin
observarse en ninguna semilla probada hasta ahora, con o sin el fix de
espacio. Nada más nuevo PROVISIONAL en este círculo (reutiliza toda la
config ya existente, sin ninguna constante numérica nueva).
## Vía 1 requiere motivo real -- cierra el segundo hallazgo, primera vez
## que se observa una herramienta fabricada en juego libre (2026-09-12)

Diego, ante los dos enfoques planteados arriba, pidió recomendación
("tiene que ser lo más natural posible"). Recomendado y cerrado el
mismo día: **(a)**, retrofit del patrón `recolectar_motivo_X` (ya
usado por arma/herramienta desde su diseño original) al eslabón de
fuego -- cronológicamente anterior (piedra suelta, 30-08) y nunca
adoptado. No son dos alternativas independientes: (b) -- "que el
consciente priorice qué necesidad es más urgente" -- ya lo hace la
capa de decisión (el `max()` entre los tres eslabones heredados); lo
que faltaba era propagar esa arbitración a la resolución física en vez
de que Vía 1 hiciera su propio chequeo ciego a qué motivo ganó
realmente. (a) es la implementación concreta de (b), y la más
"reutiliza antes de inventar": conecta con la arbitración que ya
existía, sin inventar una segunda.

**Implementado**: `Intencion.recolectar_motivo_fuego` nuevo, mismo
molde que `recolectar_motivo_arma`/`recolectar_motivo_herramienta`.
`sistema_recursos.py:_resolver_recolectar` gana `recolectar_fuego:
bool = False`; Vía 1 (agarrar piedra_suelta para fuego) solo se
dispara con ese flag activo -- antes se disparaba siempre que hubiera
hueco en Agarre y faltaran piedras, con independencia de cuál fue el
motivo real que ganó el RECOLECTAR de este tick.

**Bug real encontrado y corregido ANTES de comitear, no al fallar en
caliente**: la primera versión de los tres flags (fuego/arma/
herramienta) seguía el patrón secuencial ya existente -- cada eslabón
se comparaba contra `utilidad_recolectar` "hasta ese punto" de la
cascada. Esto deja un motivo temprano (fuego) marcado `True` aunque un
eslabón posterior (arma/herramienta) lo superase después en la misma
cascada -- dos motivos simultáneamente verdaderos para un mismo
RECOLECTAR, sin sentido físico (un individuo no recolecta por dos
razones incompatibles a la vez). Detectado por un test propio antes de
comitear (un escenario con frío casi irrelevante pero con la necesidad
implícita de trabajo -- `utilidad_recolectar_base=0.35`, todo gnomo sin
refugio la tiene -- superándolo). **Mismo bug latente que ya tenían
arma/herramienta entre sí, preexistente, nunca disparado en la
práctica** -- cerrado de paso para los tres a la vez, no solo para
fuego: los tres eslabones ahora guardan su valor CRUDO
(`valor_heredado_fuego/arma/herramienta`), y los tres flags se
resuelven en un único punto al final de la cascada, comparando cada
valor crudo contra el resultado YA cerrado de `utilidad_recolectar`
(precedencia fuego > arma > herramienta en empate exacto -- mismo
criterio de "el primero que se comprueba gana" ya usado en el resto
del módulo).

**Verificado**: 5 tests nuevos
(`tests/test_prioridad_consciente_fuego.py` -- Vía 1 nunca dispara sin
motivo, no intercepta piedra_suelta motivada por arma/herramienta, y
dos tests de integración en la capa de decisión confirmando que fuego
gana cuando es la mayor necesidad y pierde frente a la necesidad de
trabajo implícita cuando su propio déficit es menor), 508/508 tests en
verde con el resto de la suite, `BOSQUE_AUTO_TICKS=3000` (312.18 kg
descartados por prioridad, frente a 6 kg antes -- Vía 2/3 se ejercen
mucho más ahora que Vía 1 ya no les intercepta el recurso) y roundtrip
sin excepciones.

**Resultado real, el bloqueo queda desbloqueado**: repetido el mismo
arnés multi-semilla con 4 semillas NUEVAS (80301/80302/90401/90402,
las últimas dos nunca vistas antes de este fix): **3 de 4 produjeron
`HerramientaFabricada` real** (`hacha_primitiva`, con `con_piedra` ya
no en 0 en ninguna de las 3), frente a **0 de 10 en toda la
investigación previa a este fix** (círculo 2, corrección de espacio, y
ahora esta corrección de precedencia). La única semilla sin
fabricación (90401) terminó con solo 2 gnomos vivos -- fragilidad de
población ya conocida, no un fallo del mecanismo. Con esto, el arco
"fabricación y uso de herramientas" tiene su Círculo 2 genuinamente
verificado de punta a punta en juego libre, no solo por tests
dirigidos.

**Pendiente real, explícito**: `factor_bono_tasa_recolectar_con_
herramienta`/`factor_bono_tasa_aporte_construccion_con_herramienta`
ahora sí tienen ocasión de observarse en juego libre (herramientas
reales existen), pero su efecto sobre la velocidad real no se ha
medido todavía, solo su existencia funcional; solo 4 semillas
verificadas (3/4 con fabricación real) -- direccional, no una
calibración cerrada, el harness completo (15×12000) sigue pendiente
para cualquier cifra de frecuencia real; con el arco "fabricación y
uso de herramientas" ya cerrado en sus dos círculos planteados y
verificado en juego libre, ningún círculo nuevo de este arco decidido
todavía.
## `hacha_primitiva` -- colisión de nombre entre armas.yaml y
## herramientas.yaml, aceptada como decisión de diseño, no como
## accidente sin resolver (2026-09-12, mismo día)

Al preguntar Diego qué hace un `hacha_primitiva` una vez fabricado, se
encontró que el objeto tiene DOS efectos reales simultáneos, sin que
nadie lo hubiera decidido explícitamente al escribir
`config/herramientas.yaml` (Círculo 2, 2026-09-11/12): es arma nivel 3
(`config/armas.yaml`, "armas primitivas v2", 2026-09-03 --
`nucleo/armas.py:nivel_arma()` la reconoce por nombre, alimentando
`bono_defensivo_arma`/`indice_asertividad_social` en cualquier
`resolver_disputa`) Y es herramienta nivel 1 (`config/herramientas.yaml`
-- `nucleo/herramientas.py:tiene_herramienta()` la reconoce por el
MISMO nombre, activando `factor_bono_tasa_recolectar_con_herramienta`
=1.5x y `factor_bono_tasa_aporte_construccion_con_herramienta`=1.3x).
Los dos catálogos usan la misma receta de materiales (madera+piedra)
con el mismo nombre -- coincidencia entre dos piezas de diseño
separadas, nunca cruzadas entre sí antes de esta pregunta.

**Decisión de Diego: aceptado como comportamiento correcto, no como
colisión a corregir** -- "es factible, un hacha primitiva cumple ambas
funciones". Razonamiento explícito que lo sostiene, con una condición
real para el futuro: hoy es la única receta en cada catálogo, así que
funciona sin conflicto -- pero **el día que un catálogo crezca, la
coincidencia de nombre deja de ser automáticamente correcta**. Ejemplo
propio de Diego: un hipotético `hacha_de_guerra` (arma real, pensada
para combate) NO debería heredar ningún bono de construcción solo por
compartir nombre con una entrada de `herramientas.yaml` -- cada receta
nueva de cualquiera de los dos catálogos necesita una decisión
DELIBERADA (mismo nombre a propósito si el objeto es de verdad
dual-purpose, nombre distinto si no lo es), nunca una coincidencia sin
verificar cruzada entre los dos ficheros. Sin cambios de código en este
círculo -- decisión de diseño pura, documentada para que ninguna sesión
futura la trate como un bug latente ni añada una receta nueva sin
cruzar ambos catálogos primero.
## Cómo desarrollar asentamientos/profesiones -- brainstorming de arco,
## corrección real de Diego sobre "minería ya existe", Círculo 1
## (minería real) cerrado (2026-09-12, misma sesión)

Diego pidió plantear cómo desarrollar el arco recién cerrado de
profesiones (aptitud vocacional + fabricación de herramientas) hacia
"asentamientos primitivos" -- intención explícita: que el desarrollo de
un asentamiento sea GRADUAL, a medida que la población crece y mejora,
mejorando construcciones y sociedad en consecuencia. Investigado antes
de proponer nada (mismo criterio de siempre): el riesgo real es que
"mejora gradual" se convierta en un guion disfrazado de regla (un "nivel
de aldea" autorado, tipo videojuego de estrategia) -- exactamente el
tipo de error que el principio 5 (leyes neutras) prohíbe y que este
proyecto ya corrigió una vez (categorizar cuevas por tamaño/bioma).

**Alcance real, confirmado por Diego, mucho más grande que un círculo**:
(1) tipos de construcción NUEVOS desbloqueables por materiales+
habilidades reales; (2) upgrade de construcciones YA existentes
(refugio → cabaña → casa); (3) driver combinado de población+materiales+
vocación+**conocimiento** -- este último, explícitamente "hay que
pensar", un mecanismo genuinamente nuevo (transmisible y mejorable, no
solo un stat que muere con el individuo). Roadmap propuesto y aceptado:
(1) diferenciación de calidad de materiales, (2) niveles de construcción,
(3) conocimiento como componente propio -- su propia sesión de diseño
dedicada, reutilizando el patrón de transferencia por contacto ya
construido (memoria espacial compartida/rumor social, 2026-09-06), (4)
tipos de construcción nuevos. Edificio de liderazgo confirmado aparcado
(sin decisión mecánica real que habilitar todavía).

**Corrección real de Diego sobre mi propia afirmación, antes de tocar
nada**: dije "minería ya existe" -- Diego señaló que no, y verificado
contra el código (`sistema_recursos.py:780`, antes de este círculo) tenía
razón: la parte GEOLÓGICA (vetas finitas, `masa_mineral_restante`) existe
desde el arco de profundidad, pero la ACCIÓN de extraerlas era
literalmente la misma `RECOLECTAR` genérica que agarra una rama caída,
sin ningún requisito de herramienta. Distinción real de Diego: "con una
rama y una piedra podemos hacer un martillo, pero para hacer un edificio
necesitamos tablas de madera, losas de piedra" -- recoger lo suelto no
exige herramienta, producir de verdad sí. Tres sistemas de producción
identificados, ninguno equivalente: minería (geología real, acción sin
gate -- el más barato de arreglar, reutiliza el 100% de FABRICAR ya
construido), tala real (no existe -- recoger ramas caídas nunca destruye
la `Planta`, decisión deliberada del 30-08; talar un árbol de verdad
exigiría destruir una entidad por primera vez en el motor, círculo
propio, mayor alcance), agricultura/ganadería (arco completo, grande,
aparcado, confirmado por Diego "todo un sistema nuevo que hay que
desarrollar, igual que la ganadería").

### Círculo 1 -- Minería real, cerrado (spec, implementado directamente
### por Claude)

Spec: `docs/superpowers/specs/2026-09-12-mineria-real-design.md`. Un
`pico` fabricado gatea la extracción de veta -- reutiliza el 100% de
"fabricación de herramientas" (2026-09-11): `Accion.FABRICAR`,
`candidatos_fabricar`, `mejor_receta_completable`/`tiene_herramienta`,
`_via_material_crudo`. Cero mecanismo nuevo, solo una TERCERA categoría
FABRICAR ("mineria") y un gate nuevo en la extracción.

**Catálogo separado** (`config/herramientas.yaml:recetas_mineria`,
distinto de `recetas`): `pico` reutiliza los mismos materiales crudos
que `hacha_primitiva` (madera+piedra) -- deliberado, evita que
`mejor_receta_completable` tenga que elegir entre pico y hacha_primitiva
con el mismo inventario (cada categoría FABRICAR resuelve solo contra su
propio catálogo, sin ambigüedad posible aunque compartan materiales).
Alternativa descartada: diferenciar materiales -- no funciona,
`mejor_receta_completable` usa `set(objetos)` sin conteo, "2x piedra" no
se puede exigir con el mecanismo actual.

**Motivo causal, mismo patrón exacto que "herramienta"** (utilidad =
`necesidad_trabajo`, sin descuento), con un disparador MÁS ESPECÍFICO:
solo se activa si la celda actual tiene de verdad una veta sin explotar
-- un individuo que nunca ha estado junto a una veta sin pico nunca
desarrolla interés en fabricar uno (principio 5). RECOLECTAR hereda el
motivo para juntar madera/piedra crudos -- cuarto flag
`Intencion.recolectar_motivo_mineria`, extendiendo el resolutor de
precedencia corregido ayer ("prioridad consciente") a CUATRO eslabones:
fuego > arma > herramienta > mineria. Vía 4 en `_resolver_recolectar`,
comparte `_via_material_crudo` con Vía 2/3.

**Gate de extracción**: `celda.deposito_mineral` con masa restante ahora
exige `tiene_herramienta(objetos_totales, recetas_mineria)`. Sin pico, la
extracción se SALTA (no interrumpe la resolución) y cae al siguiente
nivel de prioridad ya existente (flora, luego `tipo_sustrato`) -- un
consciente sin pico junto a una veta sigue recolectando lo que sí puede.

**Deliberadamente fuera de este círculo**: el pico NO se suma al bono
genérico de velocidad (`factor_bono_tasa_recolectar_con_herramienta`)
que ya da `hacha_primitiva` -- su único efecto es destrabar la
extracción de veta, sin inventar un segundo efecto no pedido.
`tipo_sustrato` (piedra/arcilla/tierra a granel) sigue sin gate.

**Verificado**: 521/521 tests en verde (13 nuevos,
`tests/test_mineria_real.py` -- gate de extracción con/sin pico, caída a
sustrato sin pico, agotamiento real de veta, FABRICAR-mineria produce
`pico` real sin confundirse con `hacha_primitiva` pese a compartir
materiales, Vía 4 requiere motivo real, causalidad en
`sistema_decision.py` -- mineria exige veta real, no basta necesidad de
trabajo genérica --, precedencia herramienta>mineria en empate exacto).
`BOSQUE_AUTO_TICKS=3000` con la semilla por defecto, sin ninguna
excepción: el gate se ejerció de verdad (**1 bloqueo real de extracción
sin pico**), aunque 0 picos fabricados en esa semilla concreta -- mismo
patrón "correcto pero raro en una sola semilla" ya visto varias veces en
este proyecto (fabricación de herramientas, salón común...).
`BOSQUE_CONTINUAR=1` (200 ticks más tras recargar desde SQLite) sin
excepciones -- roundtrip limpio (aunque `pico` no añade estado nuevo
persistido, viaja en `Inventario.objetos`, campo JSON ya existente).

**Diagnóstico multi-semilla, resultado real (2026-09-12, mismo día,
completado tras cerrar el círculo)**: 6 semillas NUEVAS (101-106) × hasta
8000 ticks (cortadas entre 2691-3164 por el límite de tiempo real del
arnés, 60s/semilla) -- **0 picos fabricados en las 6**, mismo resultado
que la semilla por defecto. El gate SÍ se ejerció de verdad en 2 de las 6
(`vetas_bloqueadas_sin_pico=1` en semillas 105/106) -- confirma que el
mecanismo se dispara en juego libre (3/7 semillas totales con al menos un
bloqueo real), pero el ciclo completo (fabricar pico → extraer veta)
nunca llegó a cerrarse en ninguna de las 7 semillas probadas hasta ahora.

**Hipótesis real sobre la causa, verificada parcialmente, no confirmada
del todo**: se descartó una hipótesis inicial antes de escribirla aquí
como si fuera cierta -- "madera nunca está disponible en una celda de
veta (terreno de montaña)" resultó FALSA, verificado contra
`config/flora.yaml`: `pino` (bioma montaña) sí produce `madera` real. La
hipótesis que queda en pie, sin confirmar con instrumentación dedicada
todavía: el motivo de mineria es puramente OPORTUNISTA (solo se activa
estando YA de pie sobre la veta, sin ningún sesgo de movimiento que
lleve a un gnomo hacia una veta conocida) -- mismo patrón causal exacto
que ya volvió casi inalcanzable `ENCENDER_FUEGO`/piedra_suelta en su
momento (30-08), antes de la corrección de "piedra suelta". Con
`_stats_veta_bloqueada_sin_pico` disparándose solo 2 veces en ~18000
ticks combinados de las 6 semillas nuevas, simplemente PISAR una celda
de veta sin pico ya parece ser el cuello de botella dominante, antes
incluso de si esa misma celda ofrece o no material crudo para tallar.

**Pendiente real, explícito, decisión de Diego, ninguna implementada
todavía**: si se quiere que el ciclo se cierre de verdad en juego libre,
candidatos sin decidir (mismo menú de opciones que ya se planteó una vez
para piedra_suelta, ninguna implementada sin que Diego elija): (a) sesgo
de movimiento hacia una veta ya conocida en memoria (mismo patrón que ya
tira hacia refugio/manada); (b) ampliar el disparador del motivo más
allá de "de pie exactamente sobre la veta"; (c) aceptar que minar es,
narrativamente, un suceso poco frecuente y no perseguir más esto ahora,
centrando el esfuerzo en el resto del roadmap (tala real, niveles de
construcción, conocimiento). Reparto de Círculo 2 (tala real, destruye
una `Planta` por primera vez en el motor) y Círculo 3+ (niveles de
construcción, conocimiento transmisible, tipos nuevos) sin empezar --
agricultura/ganadería aparcada como arco propio.
## Tala real -- Círculo 2 del arco "asentamientos/profesiones", cerrado
## (spec, implementado directamente por Claude, 2026-09-14)

Diego, al cerrar minería (Círculo 1), dio el siguiente paso explícito:
"vayamos con la tala, más adelante desarrollaremos necesidades y flujos
que precisen de materiales y será el motivo de que un ser consciente
vaya a minar" -- confirma que el hallazgo de minería ("motivo puramente
oportunista, casi inalcanzable en juego libre", sección anterior)
**queda deliberadamente DEFERIDO, no corregido en este círculo** --
mismo criterio aplicado también a tala: sin sesgo de movimiento hacia
un árbol conocido, sin motivo causal propio nuevo.

Spec: `docs/superpowers/specs/2026-09-14-tala-real-design.md`. Mismo
patrón exacto que minería -- ninguna Accion nueva, ningún
`Intencion.recolectar_motivo_X` nuevo: la extracción de madera de un
árbol EN PIE es una prioridad más dentro del bloque genérico ya
existente de `_resolver_recolectar` (mineral > **tala** > material de
flora a granel > sustrato). Diferencia real frente a minería: **por
primera vez en el motor, una acción del jugador destruye deliberadamente
una entidad `Planta`** -- hasta hoy, ninguna flora moría nunca (ni de
vieja, ni por ninguna acción).

**`Planta` gana `masa_tronco_kg: float = 0.0`** -- análogo exacto a
`Celda.masa_mineral_restante`, fijado UNA VEZ al crear la planta
(`nucleo/entidad.py:crear_planta`, nuevo parámetro opcional, sin
acoplar la fábrica a `config`) vía `nucleo/flora.py:
masa_tronco_inicial_kg(especie_cfg)` (nuevo, pura). Solo las 3 especies
que ya declaraban un recurso `madera` real (`categoria: material`) y
`compite_espacio_fisico: true` -- `manzano`, `roble`, `pino` -- reciben
un valor > 0 en `config/flora.yaml` (PROVISIONAL, escalado a ojo por
`huella_m2` ya existente: manzano=80kg, pino=90kg, roble=100kg).
**Deliberadamente determinista, sin sorteo individual** -- a diferencia
del patrón rango+sorteo que rige atributos de criatura, introducir una
tirada de `rng` nueva por cada `crear_planta()` desplazaría la secuencia
de aleatoriedad de TODO lo demás para cualquier semilla ya en marcha
(mismo riesgo documentado repetidas veces en este proyecto) -- el valor
ya varía por especie, suficiente sin necesidad real de variar también
por individuo.

**Gate: `"hacha_primitiva" in objetos_totales`, comprobación específica**
-- no `tiene_herramienta()` genérico contra ningún catálogo (un hacha
tala, no cualquier herramienta futura). Sin hacha, la tala no bloquea la
resolución -- cae a material de flora a granel / sustrato, mismo
criterio "no bloqueante" que minería. Solo talable una `Planta` MADURA
(`etapa>=1.0`, mismo criterio que "solo una planta madura produce
recurso" ya rige el resto de flora) con tronco real
(`nucleo/flora.py:_planta_talable_en`, nuevo helper en
`SistemaRecursos`, reutiliza `plantas_competidoras_en` de
`nucleo/espacio.py`).

**Extracción**: mismo patrón `min(tasa, espacio, masa_restante)` que
veta, decrementa `Planta.masa_tronco_kg`; al llegar a 0,
`GestorEntidades.eliminar_entidad(planta_id)`. **El cupo de espacio
compartido de la celda se libera solo, sin código adicional** --
confirmado por diseño y por test: `nucleo/espacio.py:
plantas_competidoras_en`/`espacio_disponible` consultan la ECS en vivo
cada vez, nunca cachean nada, así que destruir la entidad libera su
`huella_m2` en la siguiente consulta. Evento `ArbolTalado` (NOTABLE,
mismo criterio que `HerramientaFabricada`/`PicoFabricado`) al agotar el
tronco -- `{x, y, zona_idx, especie}`.

**Deliberadamente fuera de este círculo**: sin "tabla" procesada (sigue
siendo el mismo material `madera` ya existente en el catálogo, solo una
fuente mucho mayor y de una vez); sin regeneración de la `Planta`
talada -- la propagación diaria ya causal (arco "tipos de propagación de
flora", cerrado 2026-09-02) es el único mecanismo de reposición.

**Persistencia**: `Planta.masa_tronco_kg` viaja en `plantas_estado`
(nueva columna), `VERSION_ESQUEMA` sube a `0.38-fase0`
(DROP-and-recreate, sin migración, mismo criterio ya establecido).

**Verificado**: 533/533 tests en verde (12 nuevos,
`tests/test_tala_real.py` -- catálogo de masa inicial, gate con/sin
hacha (Inventario y Agarre), caída a sustrato sin hacha, sin motivo
causal nuevo (RECOLECTAR activo por cualquier razón basta), extracción
real con destrucción de la entidad al agotar / sin destruir en
extracción parcial, liberación real de espacio de celda tras destruir
-- medida con `nucleo/espacio.py:espacio_disponible` antes/después, no
solo razonada --, prioridad mineral>tala en la misma celda, roundtrip
de persistencia con masa parcial y agotada). `BOSQUE_AUTO_TICKS=3000`
sin ninguna excepción: **152 bloqueos reales por falta de hacha, 0
árboles talados** en esa semilla concreta -- el gate se ejerce con
fuerza real desde el primer día (mismo patrón que minería: "correcto y
verificado, pero el ciclo completo hacha→tala puede resultar raro en
una sola semilla", confirmar con diagnóstico multi-semilla antes de
concluir nada sobre frecuencia real). `BOSQUE_CONTINUAR=1` (200 ticks
más tras recargar desde SQLite) sin excepciones -- roundtrip real con
17 madrigueras físicas y el resto del estado social intactos, confirma
que la columna `masa_tronco_kg` nueva no rompe nada del resto del
snapshot.

**Pendiente real, explícito**: `masa_tronco_kg` por especie
PROVISIONAL, sin calibrar contra el harness completo; sin ningún
consumidor de `ArbolTalado` en narrador/vista_web todavía --
presentación, deliberadamente sin tocar (motor primero).

### Diagnóstico multi-semilla real -- mismo hallazgo que minería, 0
### árboles talados pese a hachas ya fabricadas (2026-09-14, mismo día)

Mismo arnés que minería (`main.py:ejecutar_tick` con
`Persistencia` no-op, sin SQLite), 6 semillas NUEVAS (201-206) × hasta
8000 ticks, tope real de 60s/semilla (las 6 se cortaron por tiempo
entre 1979 y 2481 ticks -- ninguna llegó al término completo, mismo
criterio de honestidad ya aplicado a diagnósticos anteriores de esta
sesión sobre qué cuenta como dato válido).

| Semilla | Ticks | Talados | Bloqueados sin hacha | Herramientas fabricadas |
|---|---|---|---|---|
| 201 | 2127 | 0 | 226 | 2 |
| 202 | 2203 | 0 | 101 | 3 |
| 203 | 2159 | 0 | 95 | 1 |
| 204 | 2341 | 0 | 163 | 1 |
| 205 | 2481 | 0 | 117 | 1 |
| 206 | 1979 | 0 | 100 | 1 |

**0 árboles talados en las 6 semillas** -- mismo resultado que minería
(0 picos-con-extracción en 6/6 también). El gate se ejerce con fuerza
real (95-226 bloqueos por falta de hacha por semilla) y **sí se
fabrican hachas de verdad** (1-3 `hacha_primitiva` por semilla,
confirmando que el ciclo RECOLECTAR-material→FABRICAR-herramienta
funciona) -- pero ninguna de esas hachas llegó a coincidir con "estar
de pie junto a un árbol maduro talable" en el mismo tick con RECOLECTAR
como acción ganadora, dentro de la ventana medida. Mismo diagnóstico
que minería: el disparador es puramente oportunista (sin ningún sesgo
de movimiento hacia un árbol conocido), y **deferido explícitamente por
Diego** a las mismas "necesidades y flujos futuros que precisen de
materiales" que resolverán ambos casos a la vez -- no se investiga ni
se corrige más aquí, documentado con la misma honestidad que el resto
del proyecto.
