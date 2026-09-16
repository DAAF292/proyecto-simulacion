# Historial — Hilo individual — nombre propio, relaciones, familia

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

## Hilo individual — arranque del arco, primer círculo (nombre propio
## real) cerrado (2026-09-04)

Diego pidió empezar a plantear el "hilo individual" (nombre propio,
desarrollo personal, relaciones interpersonales -- pareja, amistad,
familia) pidiendo explícitamente un INFORME de alternativas antes de
decidir nada, no un diseño cerrado de entrada. Investigado contra el
código real antes de escribir el informe (no contra el informe técnico
en abstracto): `Identidad.nombre` nunca contenía un nombre real
(siempre `especie_id`); `id_madre`/`id_padre` ya trackeados y
persistidos sin ningún consumidor; `Temperamento.empatia`/`lealtad` ya
declaraban en su propio docstring "esperan vínculos personales con
nombre propio"; `nucleo/conflicto.py` ya diseñado como resolutor
genérico con robo/agravio genérico como consumidores futuros
explícitos; y -- hallazgo clave que orientó el cimiento recomendado --
el propio `nucleo/disposicion.py` ya se auto-señalaba (comentario
preexistente, sin relación con esta conversación) como destinado a
reutilizarse "entre dos individuos con nombre", exactamente el problema
de relaciones interpersonales.

Informe entregado con seis piezas distinguibles (nombre propio,
biografía, pareja estable, amistad, familia extendida, rencor) más un
cimiento común propuesto (componente `Relaciones` genérico, afinidad
continua, reutilizando el modelo de disposición en tres capas) --
decisión de NO cerrar un diseño único de entrada, coherente con
"crecer en círculos pequeños".

**Decisiones cerradas con Diego, en orden, antes de tocar código**:
1. Hilo individual pleno (nombre, relaciones futuras) solo para
   conscientes -- hoy en la práctica solo gnomo
   (`decision.umbral_consciencia_agencia`). Fauna queda como círculo
   futuro APLAZADO, no descartado.
2. Familia como DOS capas separadas: linaje biológico (sangre, siempre
   presente, deriva de `id_madre`/`id_padre` ya existentes) y
   convivencia (asentamiento, puede no coincidir con el linaje) -- sin
   que una sustituya a la otra.
3. Orden de círculos: **nombre propio primero**, aislado del cimiento
   de `Relaciones` (que llega después, sin dependencias entre ambos).
4. El futuro componente `Relaciones` llevará tope duro de vínculos por
   individuo desde el principio, mismo criterio que `MemoriaEspacial`
   -- decidido antes de que exista una sola línea de código de esa
   pieza, para no heredar una estructura sin freno si se llega tarde a
   pensarlo (sobrepoblación ya tiene dos modos de fallo residuales sin
   resolver).

### Círculo 1 -- Nombre propio real, cerrado (spec, PR #13, mergeado)

Spec: `docs/superpowers/specs/2026-09-04-nombre-propio-design.md`.
Generación por sílabas fijas combinadas al azar (prefijo+sufijo,
concatenación directa) -- descartado tanto una lista plana de nombres
completos como un generador fonético completo con reglas de gramática,
decisión explícita de Diego tras comparar los tres. Nombre real gateado
por `CapacidadMental.consciencia >= decision.umbral_consciencia_agencia`
en las dos fábricas ECS (`crear_criatura`/`nacer_criatura`); sin
chequeo de unicidad entre vivos.

**El catálogo de nombres (`config/nombres.yaml`) se curó a mano por
Diego + Claude en la misma conversación, NO se delegó al pipeline** --
decisión explícita, coherente con la categoría ya documentada en
`.ai-pipeline/guia-tareas.md` ("calibración de estilo/juicio sin
criterio de éxito verificable mecánicamente", misma clase que la poda
de comentarios narrativos que ya falló 2/2 con `mini-swe-agent`). El
encargo al pipeline cubrió solo el mecanismo (asignación + narrador +
cableado de eventos), tratando el catálogo como dato de entrada
cerrado.

`presentacion/narrador.py` gana `sujeto`/`tiene_nombre_propio`: nombre
real como sujeto de las plantillas Muerte/Herida/CrisisMental/
Nacimiento cuando lo hay, con concordancia de participio
(herido/herida) por el SEXO REAL del individuo (`Reproduccion.sexo`) en
ese caso -- distinto del fallback (`"{articulo} {especie}"`), que sigue
concordando por el género gramatical de la especie exactamente como
antes (el fix de "un ardilla" -> "una ardilla" de la sesión anterior
queda intacto para quien no tiene nombre real). `Concepcion` y
`sistema_desastres.py` quedaron fuera a propósito.

**Hallazgo real del propio pipeline, no anticipado en el spec**: el
evento `Herida` de `sistema_depredacion.py` no llevaba `especie`/
`nombre` en absoluto desde que existe (gap preexistente, distinto del
ya conocido de `zona_idx` en el evento `Muerte` por incendio) -- sin
esos campos, el `sujeto` de fallback habría quedado vacío para toda
herida por depredación. El propio `mini-swe-agent` lo detectó y lo
corrigió como parte necesaria de la tarea, no como scope creep.

**Verificado por el propio pipeline contra el motor real, no solo con
tests**: tras generar una corrida con `BOSQUE_AUTO_TICKS`, el agente
notó que la base de datos mezclaba filas de una corrida anterior
(fallback `gnomo_3` residual), lo señaló explícitamente, borró la BD y
repitió limpio -- confirmó nombres reales (Krugun, Fennora, Grimora...)
en la crónica de Muerte/Herida/CrisisMental, fauna con fallback intacto.
140/140 tests en verde (12 nuevos: `tests/test_nombre_propio.py` +
extensión de `tests/test_narrador_genero.py`).

**Auditoría manual de Claude antes de mergear** (diff completo, no solo
el recuento de tests): sin bugs encontrados. Un efecto colateral real,
NO un bug -- el sorteo de sexo/consciencia se adelanta al principio de
ambas fábricas ECS (necesario para que el nombre exista antes de
`Identidad`), lo que cambia el orden de consumo del RNG por criatura:
para una misma semilla, los atributos concretos de cada individuo
(peso, temperamento...) difieren de antes de este merge -- mismo tipo
de efecto ya documentado con el RNG de reproducción, sin bloquear nada.

**Incidente operativo real, corregido en el momento**: Claude comiteó
localmente el spec + `config/nombres.yaml` + el encargo pero olvidó
`git push` antes de soltar la tarea al centinela -- el PR resultante
mostraba esos ficheros como "nuevos" en su diff porque `origin/master`
llevaba 3 commits de retraso respecto al `master` local. Corregido
empujando `master` (fast-forward puro) antes de mergear el PR --
lección para encargos futuros: comitear Y empujar antes de escribir el
encargo, no solo comitear.

**Coste real medido** (balance real de OpenRouter antes/después, no el
autoinformado por el modelo): **$0.155374**, un único intento de 3
posibles, sin reintentos.

**Pendiente real tras este círculo**: nombre para fauna (aplazado, no
descartado); el cimiento genérico `Relaciones` (afinidad continua, tope
de vínculos) es el siguiente círculo real de este arco, sin ninguna
dependencia de código de este círculo salvo `Identidad.nombre` ya real;
contenido del catálogo (`config/nombres.yaml`) PROVISIONAL, sin más
revisión que "sonar razonable".

### Círculo 2 -- Cimiento `Relaciones` + rencor, cerrado (spec, PR #14,
### mergeado, 2026-09-04, misma tarde)

Spec: `docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md`.
Decisiones cerradas con Diego antes de escribir el spec: círculo
empaquetado con su primer consumidor real (no cimiento aislado, mismo
criterio que `Agarre`, para poder verificar contra el motor real);
primer consumidor **rencor**, no amistad (único disparador claro ya
existente: `nucleo/conflicto.py:resolver_disputa` vía
`_resolver_posible_intruso`, refugio ocupado); tope de capacidad
**reutiliza `CapacidadMental.memoria`** (mismo atributo que ya gobierna
`MemoriaEspacial`, un individuo con buena memoria recuerda tanto sitios
como personas). **Hallazgo real de paso, corregido**: el docstring de
`componentes/capacidad_mental.py` decía "memoria... espera el hilo
individual de nombres propios... sin consumidor todavía" -- desfasado,
`nucleo/memoria.py:capacidad_memoria()` ya la consumía activamente desde
antes de esta sesión (memoria espacial); corregido para documentar sus
DOS consumidores reales.

**Implementado**: `componentes/relaciones.py` (`Vinculo`/`Relaciones`,
universal en las 4 especies, mismo patrón que `Agarre`/`Semillas`);
`nucleo/relaciones.py` (`capacidad_vinculos()`, `ajustar_afinidad()` con
purga FIFO por `ultima_actualizacion_tick` más antiguo, no por
antigüedad de creación); consumidor en
`sistema_movimiento.py:_resolver_posible_intruso` -- los cuatro
desenlaces de `resolver_disputa` (CEDE_A/CEDE_B/ENFRENTAMIENTO/COMPARTE)
escriben afinidad negativa sobre la parte CONSCIENTE, adicional al
drenaje de `seguridad` ya existente, sin leer la afinidad en ningún
punto de decisión todavía; persistencia (`VERSION_ESQUEMA` a
`0.33-fase0`, mismo molde JSON que `Agarre.objetos`). 154/154 tests
(14 nuevos, `tests/test_relaciones.py`).

**Hallazgo real del propio proceso del pipeline, no del código**: a
diferencia del círculo anterior (nombre propio), esta vez el agente
**se saltó por completo la verificación contra el motor real
(`BOSQUE_AUTO_TICKS`)** que el spec pedía explícitamente -- solo corrió
`pytest` y declaró la tarea terminada. No se detectó como fallo del
disyuntor (los tests SÍ pasaban), así que hizo falta la auditoría manual
de Claude para notarlo. **Lección para encargos futuros**: el spec por
sí solo no basta para garantizar que el agente ejecute el paso de
verificación real -- conviene que el propio encargo (`docs/superpowers/
encargos/`) lo nombre como paso explícito y obligatorio, no solo como
parte de una sección de spec que el agente puede decidir omitir.

**Auditoría manual de Claude antes de mergear, dos niveles**: (1) diff
completo revisado línea a línea -- sin bugs, wiring correcto
(`tick_actual` plumbing a través de `main.py` → `SistemaMovimiento.
ejecutar(gestor, mundo, reloj)` → `_calcular_dormir` →
`_resolver_posible_intruso`, `self.umbral_consciencia_agencia`
reutilizado correctamente, no inventado). (2) Corrida real
(`BOSQUE_AUTO_TICKS`, 2000 y 4000 ticks, dos veces): **0 filas de
`Relaciones` no vacías en ambas** -- diagnosticado, NO es un bug: la
población de gnomos colapsó en ambas corridas (1 vivo a los 2000 ticks,
0 a los 4000 -- mismo problema de fragilidad/colapso ya documentado en
"Sobrepoblación...", no una regresión de este círculo) antes de que dos
conscientes coincidieran en el refugio completado exacto de uno de
ellos. Para no dejarlo en "probablemente funciona", se construyó un
arnés dirigido que fuerza el escenario a través del despacho REAL
(`Accion.DORMIR` con memoria de refugio ya registrada, no llamando al
método interno a mano como sí hacen los tests del PR) -- confirmó
rencor escrito correctamente con el `tick_actual` real del reloj. Mismo
patrón de verificación que el commit original de `conflicto.py`
(`2640a82`) ya había aplicado en su día. **Pendiente real, ya conocido
desde el propio `conflicto.py` original, no nuevo de este círculo**: si
el disparador de refugio ocupado llega a ocurrir con población real
corriendo sola sin intervención sigue sin confirmarse -- ahora aún menos
observable en la práctica por la fragilidad de gnomo, no resuelto aquí.

**Coste real medido**: **$0.189459**, un único intento de 3 posibles,
sin reintentos.

**Pendiente real tras este círculo**: amistad (afinidad positiva, mismo
cimiento, círculo futuro); ningún consumidor LEE `Relaciones` todavía
para cambiar comportamiento (p.ej. modular `indice_asertividad_social`
por rencor previo); decaimiento del rencor con el tiempo, sin resolver;
`relaciones.min_vinculos_por_individuo`/`max_vinculos_por_individuo`/
`delta_rencor_disputa` PROVISIONALES sin calibrar; fauna sigue sin
`Relaciones` real, aplazado, no descartado.

### Círculo 3 -- Amistad por convivencia, cerrado (spec, PR #15,
### mergeado, 2026-09-04, misma tarde)

Spec: `docs/superpowers/specs/2026-09-04-amistad-convivencia-design.md`.
Decisión real de Diego, contra mi propia recomendación: en vez del
disparador más pequeño posible (reutilizar la rama `COMPARTE` de
`_resolver_posible_intruso`, ya wireada, cero disparador nuevo), eligió
el mecanismo más fiel a "amistad emerge de tiempo compartido" -- acreción
DIARIA de afinidad positiva entre todo par de miembros CONSCIENTES del
mismo asentamiento (`sistemas/sistema_asentamiento.py`, misma cadencia
que ya recalcula membresía/liderazgo/almacén), sin excluir parentesco
(un padre y su hijo adulto conviviendo SÍ acumulan amistad además de su
vínculo de sangre ya existente por separado -- capas distintas por
diseño, decisión ya cerrada). O(N²) por asentamiento y día, aceptado a
la escala actual.

**Implementado**: `_acrecion_amistad_convivencia`/`_ajustar_amistad` en
`SistemaAsentamiento`, reutilizando `ajustar_afinidad`/
`capacidad_vinculos` de `nucleo/relaciones.py` sin ningún cambio --
mismo cimiento, segundo consumidor real, sin tocar
`sistema_movimiento.py` ni el rencor ya existente.
`config/relaciones.yaml` gana `delta_amistad_convivencia_dia` (0.05,
PROVISIONAL -- 20 días de convivencia para llegar al tope). 160/160
tests (6 nuevos), incluida la interacción con rencor ya existente
(afinidad que ya era negativa sube hacia positivo sin ningún caso
especial en el código) y el respeto al mismo tope/purga FIFO.

**La lección del círculo anterior funcionó**: esta vez el encargo pedía
`BOSQUE_AUTO_TICKS` como paso OBLIGATORIO, no solo el spec -- el agente
sí lo ejecutó (15000 ticks, ~445 días simulados) y reportó con
precisión un hallazgo honesto: **0 asentamientos con 2+ miembros
conscientes llegaron a formarse en juego libre** con la semilla por
defecto -- la población de 18 gnomos se extinguió (depredación +
inanición + vejez) antes de que 3+ refugios quedaran lo bastante cerca
para fundar un asentamiento (11 refugios construidos, todos dispersos).
Causa ecológica ya conocida (mismo problema de fragilidad de gnomo /
colapso de población documentado en "Sobrepoblación..."), no un defecto
de este círculo -- el propio mecanismo está verificado correcto por los
6 tests unitarios (que sí construyen asentamientos reales y confirman
la física), simplemente no llegó a dispararse solo en esta corrida.
Coste real: **$0.078748**, un único intento -- el más barato de los tres
círculos de este arco hasta ahora.

**Pendiente real tras esta pieza**: ningún consumidor lee la afinidad
(positiva o negativa) todavía para cambiar comportamiento; decaimiento
de amistad/rencor con el tiempo, sin resolver; `delta_amistad_
convivencia_dia` PROVISIONAL sin calibrar; pareja estable, familia
derivada, biografía -- círculos futuros del mismo arco, sin empezar;
**el hallazgo de fondo (asentamientos que casi nunca llegan a formarse
en juego libre por el colapso de población) afecta a CUALQUIER
mecanismo futuro basado en asentamiento, no solo a amistad** -- candidato
real a investigar antes de construir más piezas que dependan de que un
asentamiento exista de verdad en una partida.

### Círculo 4a -- Afinidad por concepción, cerrado (spec, PR #16,
### mergeado, 2026-09-04, misma tarde) -- primera mitad de "pareja
### estable"

Spec: `docs/superpowers/specs/2026-09-04-afinidad-concepcion-design.md`.
Diego pidió partir "pareja estable" en dos círculos, mismo criterio ya
aplicado tres veces en este arco: 4a (este, escritor mínimo -- la
concepción exitosa también escribe afinidad positiva mutua entre
progenitores, reutilizando `ajustar_afinidad` tal cual, cero función
nueva en `nucleo/relaciones.py`) y 4b (lector -- derivar "¿son pareja?"
de la afinidad acumulada + un efecto de comportamiento, spec propia
futura, sin empezar). `sistemas/sistema_reproduccion.py` gana
`_escribir_afinidad_concepcion`, llamada en ambas direcciones justo tras
construir `Gestacion`, antes de emitir `Concepcion` (sin tocar ese
evento ni la lógica de reproducción). `config/relaciones.yaml` gana
`delta_afinidad_concepcion` (0.15, PROVISIONAL). 163/163 tests (9
nuevos).

**Primera vez en este arco que el motor real SÍ produjo el caso en vivo
sin intervención**: a diferencia de los círculos 2 y 3 (rencor, amistad
-- ambos verificados solo por arnés dirigido o tests unitarios porque la
población colapsó antes de disparar el mecanismo en juego libre), esta
corrida de `BOSQUE_AUTO_TICKS` confirmó dos gnomos reales, ambos
conscientes (0.78 y 0.70), con afinidad `0.15` real en
`Relaciones.vinculos` tras una concepción real -- coherente con que la
concepción es un evento mucho más frecuente en juego normal que un
conflicto de refugio ocupado o la formación de un asentamiento de 2+
conscientes.

**Coste real**: **$0.114074**, un único intento.

**Pendiente real tras esta pieza**: círculo 4b (pareja estable derivada
+ efecto de comportamiento -- qué efecto exacto, PENDIENTE DE DECIDIR
con Diego, no autorado aquí) es la siguiente pieza real de este arco;
`delta_afinidad_concepcion` PROVISIONAL sin calibrar; familia derivada y
biografía consultable, círculos futuros sin empezar; el hallazgo de
fondo de asentamientos casi nunca formándose en juego libre (señalado en
el círculo 3) sigue pendiente de investigar, y afecta directamente a
cómo de observable será el círculo 4b si su efecto depende de
asentamiento.

### Círculo 4b -- Pareja estable derivada + bono de cercanía, cerrado
### (spec, PR #17, mergeado, 2026-09-04, misma tarde)

Spec: `docs/superpowers/specs/2026-09-04-pareja-estable-design.md`.
Primer consumidor de todo el arco que LEE `Relaciones` para decidir
algo (los anteriores solo escribían). Decisiones cerradas con Diego:
derivación MUTUA (afinidad >= `relaciones.umbral_pareja` en AMBAS
direcciones, no basta una); efecto mínimo -- bono aditivo de
confort/seguridad por estar en la misma celda EXACTA que la pareja,
mismo patrón que `bono_confort_refugio`/`bono_confort_fogata`
(`sistema_necesidades.py`), sin radio de percepción, sin monogamia, sin
refugio compartido ni aporte a almacén.

**Implementado**: `nucleo/relaciones.py` gana `son_pareja()` (pura) y
`pareja_presente()` (búsqueda por celda exacta, mismo patrón que
`hay_refugio_en`/`fogata_en` de `nucleo/fuego.py`); `sistema_necesidades.py`
suma `bono_confort_pareja` al objetivo de confort térmico y
`bono_seguridad_pareja` a la recuperación de seguridad (capado a 1.0),
ambos solo para consciente con pareja realmente presente.
`relaciones.umbral_pareja` (0.3) y los dos bonos (0.15/0.05) nuevos,
todos PROVISIONALES. 179/179 tests (16 nuevos).

**Mismo patrón de honestidad que el círculo 3, misma causa raíz**: el
motor real (`BOSQUE_AUTO_TICKS=4000`) no confirmó ningún caso real de
pareja cruzando el umbral -- la población de gnomos volvió a
extinguirse (0 vivos al final, últimos rastros en tick ~2422) antes de
que las 5 concepciones registradas pudieran acumular afinidad suficiente
o coincidir de nuevo en la misma celda. El mecanismo está verificado
correcto por los 16 tests unitarios; lo que falta observar en vivo es,
otra vez, una consecuencia del colapso de población ya conocido, no un
defecto de este círculo. **Tercera vez que el mismo problema de fondo
bloquea la verificación en vivo de un consumidor de este arco**
(asentamientos en el círculo 3, pareja aquí) -- refuerza que investigar
la fragilidad de gnomo es ahora una prioridad real antes de construir
más piezas que dependan de que la población sobreviva lo suficiente.

**Coste real**: **$0.140223**, un único intento.

**Pendiente real tras esta pieza**: con esto, **5 de las 6 piezas del
arco "hilo individual" quedan cerradas** (nombre propio, cimiento
`Relaciones`+rencor, amistad, afinidad por concepción, pareja estable)
-- solo faltan familia derivada y biografía consultable, ninguna
empezada. `umbral_pareja`/`bono_confort_pareja`/`bono_seguridad_pareja`
PROVISIONALES sin calibrar; decaimiento de afinidad sigue sin resolver
(limitación honesta ya señalada: hoy una pareja no puede "diluirse" solo
por dejar de convivir); pequeña ineficiencia sin importancia real
detectada en revisión -- `pareja_presente()` se calcula dos veces por
tick por entidad (confort y seguridad por separado) en vez de
reutilizar el resultado, no corregido por no ser un bug ni afectar el
resultado. **La investigación de por qué los gnomos colapsan/no forman
asentamientos ni parejas persistentes en juego libre, aplazada por
Diego hasta terminar de implementar todo lo ya diseñado de este arco,
sigue siendo el candidato más urgente para la siguiente sesión de
calibración.**

### Círculo 5 -- Parentesco derivado, cerrado (spec, IMPLEMENTADO
### DIRECTAMENTE POR CLAUDE, no por el pipeline, 2026-09-04, misma tarde)

Spec: `docs/superpowers/specs/2026-09-04-parentesco-derivado-design.md`.
Decisiones cerradas con Diego: hermanos = comparten `id_madre` O
`id_padre` (medio-hermanos incluidos); solo núcleo directo (madre,
padre, hijos, hermanos) -- **hallazgo real que descartó abuelos/tíos
antes de escribir código**: `GestorEntidades.eliminar_entidad` purga
TODOS los componentes al morir, incluida `Identidad`
(`nucleo/entidad.py:77-80`), así que un nivel más de ascendencia solo
sería derivable mientras el progenitor intermedio siguiera vivo en
memoria -- inviable dada la fragilidad de población ya conocida;
primer consumidor: `resolver_disputa` trata a la familia directa con
más cohesión, mismo mecanismo que `mismo_grupo` (bono aditivo, no
resultado garantizado).

**Excepción real al flujo fijo del proyecto**: los 3 intentos del
pipeline autónomo fallaron con el MISMO error exacto
(`RepeatedFormatError` -- el modelo entra en un bucle de respuestas
vacías `<response> response` sin ninguna llamada a herramienta, en un
punto distinto cada vez: paso ~7 el primer intento, paso 41 el
segundo), sin tocar ni una línea de código en ningún intento. Coste
total: $0.059093 (barato, no llegó a generar diffs). Diagnosticado
como inestabilidad genuina del modelo, no relacionado con el contenido
de la spec (ya se había visto esta clase de fallo con `aider` antes de
la migración a `mini-swe-agent`, se creía resuelto con el ajuste de
temperatura del proxy -- esta es la primera recurrencia real desde
entonces). Disyuntor agotado, plan movido a `docs/plans/failed/`. Diego
pidió explícitamente implementarlo directamente (excepción ya prevista
en la sección "Flujo de implementación" de este documento: "Diego lo
pide explícitamente") y anotar el patrón de fallo para evaluaciones
futuras de modelo -- guardado en memoria persistente
(`project_evaluar_modelos_pipeline.md`), no solo aquí.

**Implementado**: `nucleo/parentesco.py` nuevo
(`son_hermanos`/`es_padre_o_madre`/`es_familia_directa`, puras, sin
persistir nada); `resolver_disputa` gana `son_familia: bool = False`
(entra en la rama de cohesión igual que `mismo_grupo`, suma
`bono_cohesion_familia` PROVISIONAL); `sistema_movimiento.py` calcula y
propaga. 12 tests nuevos (`tests/test_parentesco.py`), 191/191 en
total.

**Hallazgo real MÁS SERIO de lo anticipado en el spec, verificado con
dos corridas reales (4000 y 8000 ticks)**: la spec esperaba que
parentesco fuera "mucho más fácil de observar" que asentamiento/pareja
porque "existe desde el nacimiento" -- **resultó ser al revés**. En
ninguna de las dos corridas nació un solo gnomo nuevo, pese a 3
concepciones reales de gnomo (ticks 243, 495, 620). Causa raíz
identificada con precisión: la gestación de gnomo son 200-260 DÍAS
(`config/poblacion.yaml`) × `Reloj.TICKS_POR_DIA=24` = **4800-6240
ticks** -- las 3 madres murieron (población fundadora completa, 18/18
muertas al final) antes de completar ese plazo, así que `Gestacion` (un
componente sobre la propia madre) se purgó con ellas sin llegar a
`nacer_criatura`. **Esto es una escalada real del problema de
fragilidad de gnomo ya señalado tres veces en este arco** (círculos 3,
4b): no es solo que la segunda generación no sobreviva ni conviva lo
bastante -- en las corridas de hoy, con la semilla por defecto, **la
segunda generación de gnomo no llega ni a NACER**. El mecanismo de
parentesco en sí está verificado correcto por los 12 tests (que sí
construyen madre/hijo reales y confirman la física); lo que no se pudo
observar en juego libre es la EXISTENCIA de un caso real de parentesco
completo, un peldaño más grave que "no se disparó el consumidor"
(círculos 3/4b) -- aquí ni siquiera se completó el nacimiento que lo
originaría.

**Pendiente real tras esta pieza**: `bono_cohesion_familia`
PROVISIONAL sin calibrar; abuelos/tíos bloqueados por la limitación
técnica ya documentada; otros consumidores de parentesco (narrador,
memoria de agravios) sin construir; **la investigación de fragilidad de
gnomo, ya la prioridad más urgente tras los círculos 3/4b, gana ahora
evidencia más grave y concreta -- la gestación (4800-6240 ticks) parece
exceder sistemáticamente la supervivencia real de una madre gnomo en la
semilla por defecto**, dato nuevo y específico para cuando se aborde
esa investigación (no es ya "la población colapsa en general", es "el
ciclo reproductivo de gnomo no completa una generación completa").
Con este círculo, quedan 5 de las 6 piezas originalmente numeradas del
arco cerradas o implementadas -- solo falta biografía consultable
(círculo 6 original); desarrollo personal sigue aplazado, decisión ya
tomada.

### Círculo 6 -- Biografía consultable, cierra el arco "hilo
### individual" (implementado directamente por Claude, 2026-09-04)

Diego confirmó explícitamente que esta pieza no encaja en la regla fija
"Claude diseña, el pipeline implementa" -- no es funcionalidad nueva del
MOTOR de simulación, es una consulta de solo lectura sobre
`cronica_eventos` (ya persistida con `entidad_id` por fila desde el
principio del proyecto), sin componente, sistema, ni efecto en ninguna
decisión o tick. `Persistencia.biografia_de(entidad_id) -> list[Evento]`
(`nucleo/persistencia.py`) reconstruye la crónica de un individuo en
orden cronológico; RUIDO nunca aparece porque `persistir_eventos` ya lo
descartaba desde antes de esta pieza. El resultado es directamente
consumible por `presentacion/narrador.py:narrar(eventos, gestor=None)`
YA EXISTENTE -- sin ningún wrapper nuevo, confirmado con un test
dedicado y con una consulta real contra `datos/bosque.db` de una corrida
de hoy ("Tick 422: Dorneld ha muerto por inanición."). 4 tests nuevos,
195/195 en total. Sin coste de pipeline (implementación directa).

**Con esto, el arco "hilo individual" completo queda cerrado**: nombre
propio real, cimiento `Relaciones` + rencor, amistad por convivencia,
afinidad por concepción, pareja estable derivada, parentesco derivado, y
ahora biografía consultable -- 6 de 6 piezas originalmente planteadas en
el informe de alternativas del 2026-09-04 (desarrollo personal con
mutación causal de rasgos queda deliberadamente aplazado, decisión ya
tomada al inicio del arco). Coste total medido del arco:
`0.155374+0.189459+0.078748+0.114074+0.140223+0(círculo 5, implementado
directamente)+0(círculo 6, implementado directamente) = $0.677878` de
pipeline, más el trabajo directo de Claude en los círculos 5 y 6.

**Pendiente real que el arco entero deja abierto, explícito**: ningún
consumidor lee `Relaciones` salvo pareja estable (círculo 4b) todavía;
decaimiento de afinidad sin resolver; fauna sin nombre/relaciones reales
(aplazado, no descartado); abuelos/tíos bloqueados por limitación
técnica real (purga de `Identidad` al morir); desarrollo personal con
mutación causal, aplazado. **El hallazgo más importante que deja este
arco no es sobre el hilo individual en sí, sino sobre la simulación de
base**: tres círculos distintos (amistad/asentamiento, pareja,
parentesco) no pudieron verificarse en juego libre por la misma causa de
fondo -- la población de gnomo colapsa antes de tiempo, y en el círculo
5 se descubrió que ni siquiera el ciclo reproductivo básico
(concepción→nacimiento) se está completando con la semilla por defecto,
porque la gestación (4800-6240 ticks) parece exceder sistemáticamente la
supervivencia de una madre. **Esta es ahora la investigación prioritaria
real**, según lo acordado con Diego ("primero implementamos todo lo
definido, luego depuramos todo lo que hemos encontrado") -- empezar por
el hallazgo más concreto y accionable (gestación vs. supervivencia de
gnomo) antes de la pregunta más general de sobrepoblación/colapso ya
documentada en su propia sección de este archivo.
