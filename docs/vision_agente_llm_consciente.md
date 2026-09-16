# Visión a futuro: agente consciente gobernado por un LLM viviendo en el mundo

**Estado: visión de diseño conceptual, sin spec, sin implementación.** Capturada
el 2026-09-14 en conversación con Diego para no perderla — explícitamente
situada por el propio Diego como algo para "cuando tengamos un mundo simulado
de forma más compleja, con una sociedad, distintos territorios, interacciones
sociales complejas", no para el ciclo de trabajo actual. Este documento no
sustituye a ningún informe existente en `informes/` — es una nota de visión,
mismo espíritu que las secciones de "horizontes lejanos" ya anotadas en
`CLAUDE.md` (leyendas/memoria oral, facciones entre asentamientos), solo que
con más detalle por la profundidad de la conversación que la originó.

## La idea, tal como la planteó Diego

Cuando el mundo tenga sociedad, territorios y vida social real (mucho de lo
cual ya existe hoy en forma embrionaria — asentamientos, manadas, relaciones,
vocación, liderazgo, conflicto), dar el control de **una criatura consciente**
a un modelo de lenguaje que reciba exactamente los mismos datos que hoy
recibe la Utility AI de un gnomo (necesidades, temperamento, percepción,
memoria, relaciones) pero que pueda **razonar** sobre ellos en vez de
resolverlos por una fórmula. Ese individuo podría decidir cómo cubrir sus
necesidades, si asociarse a un grupo, si explorar, si involucrarse en un
conflicto, si liderar un asentamiento, si desarrollar una vocación — y
llevaría un **cuaderno de bitácora en primera persona**, distinto y paralelo
a la crónica objetiva en tercera persona que ya produce `narrador.py`. La
ambición técnica declarada: un LLM local pequeño, posiblemente con un harness
propio, al que se le dé un catálogo claro de lo que puede hacer en el mundo
para que decida con esa información.

## Por qué esto es "visión a futuro" y no una pieza para implementar ya

Dos motivos reales, no solo prudencia genérica:

1. **Gran parte de lo que el agente podría "elegir" hoy no es una elección
   real todavía.** Liderar un asentamiento emerge hoy de `calcular_liderazgo`
   a partir de atributos ya sorteados (dominancia, agresividad, cohesión),
   sin ninguna decisión consciente de por medio. Desarrollar una vocación
   existe como tendencia pasiva (aptitud vocacional, Círculo 1, 2026-09-11)
   sobre atributos fijos, no como elección deliberada. "Meterse en una
   guerra" no existe en absoluto — facciones entre asentamientos sigue
   siendo, literalmente, el horizonte más lejano documentado en
   `CLAUDE.md`, sin una sola línea de diseño.
2. **El hallazgo de temperamento mutable (ver más abajo) es, en sí mismo,
   una pieza de calado que el proyecto ya ha aparcado dos veces de forma
   explícita** — no es sensato abrirla de golpe como requisito lateral de
   este experimento.

## Encaje arquitectónico discutido (sin implementar, para cuando se retome)

### Punto de inserción único, mínimo blast radius

Para una entidad marcada, sustituir la llamada a `SistemaDecision` por un
módulo nuevo (p.ej. `nucleo/agente_llm.py`) que arma el contexto y devuelve
una `Intencion` con la **misma forma exacta** (Accion + target) que ya
produce la Utility AI. Todo lo demás del pipeline — movimiento, recursos,
necesidades, capacidad física/mental, reproducción, persistencia — sigue
exactamente igual, sin tocar una línea. El LLM propone la intención, los
mismos resolutores deterministas de siempre disponen si tiene éxito
(validación de movimiento por pendiente/agua, `manos_libres`,
`umbral_consciencia_agencia`, etc.) — el modelo nunca narra un resultado
directamente, solo elige entre acciones cuyo efecto real sigue gobernado
por las leyes físicas/sociales existentes.

### Qué recibe

Lo mismo que ya lee `sistema_decision.py` para esa entidad — necesidades,
temperamento, capacidad mental, percepción de la celda + radio, memoria
espacial, relaciones, inventario/agarre, vocación — traducido a texto
legible en vez de números para una fórmula. No hace falta inventar ningún
dato nuevo del mundo.

### Cadencia

Llamar al LLM cada tick es inviable en coste y poco fiel a cómo razona una
mente real. El motor ya tiene el patrón necesario: intenciones comprometidas
de varios ticks (CONSTRUIR, DORMIR no se re-deciden cada tick). El LLM
fijaría un objetivo/intención que persiste hasta que algo relevante cambie
(amenaza nueva, objetivo cumplido, necesidad crítica) — baja el número de
llamadas reales de "cada tick" a "cada vez que hace falta decidir algo
nuevo de verdad".

### Bitácora en primera persona vs. narrador objetivo

Diseño limpio, sin fricción: la salida del LLM no sería solo la acción —
un campo de pensamiento libre, logueado aparte de la crónica de
`narrador.py`. Son productos distintos del mismo mundo: uno describe en
tercera persona hechos que las leyes neutras produjeron (ya existe); el
otro sería la experiencia subjetiva en primera persona de un participante
(nuevo). Ninguno sustituye al otro.

## Riesgos y tensiones identificados críticamente

### "Decida lo que quiera" tiene que seguir significando "elija entre lo
### que el mundo permite", no "narre lo que le dé la gana"

Si el harness expone solo herramientas que mapean a mecanismos reales
(moverse, recolectar, construir, socializar, unirse a un grupo...), el LLM
sigue "proponiendo, el mundo dispone" — la propiedad de seguridad que evita
que esto viole el principio 5 (leyes neutras). Si en algún momento se le
diera al modelo capacidad de narrar directamente un resultado ("gano la
guerra", "soy el líder") sin pasar por un resolutor real, eso sí sería
autoría disfrazada de libertad.

### Modelo local pequeño: riesgo real, con precedente ya medido en este
### mismo proyecto

El pipeline de implementación (`mini-swe-agent` sobre `deepseek-v4-flash-0731`)
lleva semanas documentando, con evidencia real y no supuesta, lo frágil que
es un modelo barato/pequeño incluso en tareas mucho más acotadas que "vivir
una vida": bucles de repetición sin converger, alucinación de menciones de
fichero, fragilidad de formatos de texto libre — mitigado en gran parte
cambiando de `aider` (diffs de texto libre) a tool-calling estructurado, y
aun con recaídas (el intento de "parentesco derivado", 2026-09-04, volvió a
fallar 3/3 con el mismo tipo de bucle). "Vivir en un mundo, decidir
libremente, llevar un diario coherente" es un orden de magnitud más abierto
que "edita estos dos ficheros según esta spec". La lección más aplicable de
la propia experiencia del proyecto: tool-calling estructurado, menú de
acciones pequeño y explícito por turno, re-anclar el contexto real del
mundo en cada decisión — nada de texto libre sin restricción.

### Aislamiento del determinismo y de la calibración

Toda la metodología de calibración del proyecto (comparaciones A/B por
semilla, el harness de 15×12000, el bisect tick a tick usado para depurar
el índice espacial) depende de reproducibilidad total por semilla. Un
individuo gobernado por un LLM es, por definición, no determinista — esto
es aceptable si el experimento corre aislado (mundo dedicado, nunca
mezclado con las semillas de calibración), inaceptable si algún día se
plantea generalizar esto a más de un individuo dentro de la población que
se usa para calibrar.

## El hallazgo clave: temperamento mutable como precondición real, no
## exclusiva del LLM

### Por qué se descarta la auto-modulación directa

Primera propuesta discutida: que el individuo gobernado por el LLM pudiera
modular su propio temperamento (p.ej. subir su propia dominancia) para
lograr un objetivo elegido (liderar), como excepción deliberada y acotada.
**Se descarta, incluso como excepción.** El motivo: esto no es tocar una
acción externa que el mundo luego juzga — es editar directamente el
**input** de la fórmula que ya existe para decidir liderazgo de forma
emergente (`calcular_liderazgo`, que lee dominancia + agresividad +
cohesión). Si el individuo puede subir su propia dominancia a voluntad, la
fórmula sigue "corriendo" pero deja de significar nada — es equivalente a
editar `Temperamento.dominancia` a mano para asegurar un resultado
concreto. El proyecto ha sido consistentemente disciplinado rechazando
exactamente este tipo de atajo en otros sitios (categorización de cuevas
por tamaño rechazada por autoría de forma; un contador de densidad
"a medida para conejo" rechazado a favor de un mecanismo natural) — abrir
esta puerta, aunque sea "solo para el LLM", sienta un precedente que
erosiona esa disciplina.

### La síntesis: ley general de temperamento como consecuencia de
### experiencia vivida

La alternativa que sí se sostiene, y que resuelve el problema sin ninguna
excepción: que el temperamento deje de ser fijo-al-nacer para TODO
consciente (no solo el individuo LLM) y se desplace lentamente como
consecuencia real de lo que le pasa a cada individuo — mismo patrón
arquitectónico ya usado con éxito en el proyecto para `Relaciones`
(decaimiento + acumulación por eventos reales, cerrado 2026-09-11) y para
`Necesidades` (desplazamiento continuo hacia un objetivo). Ejemplos
razonados, no decididos: presenciar una crisis violenta o una muerte podría
bajar sociabilidad/valentía temporalmente; liderar con éxito de forma
sostenida (vía `resolver_disputa` ya existente) podría desplazar dominancia
al alza; un individuo con `Relaciones` mayoritariamente de rencor podría
ver bajar su empatía. Con esta ley general en marcha, un individuo
gobernado por un LLM que actúa con intención deliberada hacia liderar vería
su dominancia desplazarse **como efecto secundario real de sus actos**, no
porque la edite — mismo resultado narrativo que la primera propuesta, sin
ningún agujero en el principio 5. El LLM no necesita ningún mecanismo
propio: hereda la misma ley que cualquier otro consciente, y su ventaja es
que razona con intención sobre cómo aprovecharla.

### Esto ya estaba aparcado dos veces en el proyecto, con la misma razón

No es una idea nueva — el proyecto la ha aplazado explícitamente al menos
dos veces, precisamente porque tocar un atributo que hoy se trata como
hecho biológico fijo sorteado al nacer y convertirlo en mutable es una
fuente de complejidad real y nueva (reabre supuestos de calibración de
`config/poblacion.yaml`, interactúa con todos los sistemas que hoy leen
temperamento como constante — amenaza, liderazgo, conflicto, aportación a
almacén, disposición a compartir):

- Al cerrar el Círculo 1 de aptitud vocacional (2026-09-11): *"mejora por
  práctica, fuera de este círculo (abriría mutación causal de rasgos)"*.
- Al arrancar el arco "hilo individual" (2026-09-04): *"desarrollo
  personal con mutación causal de rasgos queda deliberadamente aplazado,
  decisión ya tomada al inicio del arco"*.

Coherente con el principio 2 (una sola fuente de complejidad por
incremento), esta pieza merece su propio círculo de diseño — brainstorming
dedicado, spec propia — no colarse como requisito lateral del experimento
del LLM.

## Orden de dependencias recomendado

1. **Mundo con más sociedad/territorios/interacción social compleja** — en
   curso de forma natural con los arcos ya cerrados (asentamiento, manada,
   relaciones, comunicación, robo/intercambio, dinámicas internas de
   asentamiento).
2. **Temperamento como consecuencia de experiencia vivida** — ley general
   para todo consciente, su propio círculo de brainstorming + spec +
   verificación contra el motor real, con el mismo rigor que el resto del
   proyecto. No exclusiva ni motivada primariamente por el LLM.
3. **Solo entonces, el agente LLM** como participante que hereda esa ley
   sin necesitar ninguna excepción — su "auto-modelado" emerge gratis de
   un mecanismo ya general.

## Decisiones explícitamente sin resolver

- **"Pi agent"**: sin aclarar si se refiere a un framework de orquestación
  de agentes (p.ej. algo tipo PydanticAI) o a ejecutar el proceso en
  hardware dedicado (una Raspberry Pi) separado de la máquina principal —
  implicaciones de diseño distintas, pendiente de que Diego lo precise
  cuando se retome.
- **Mundo dedicado y pequeño vs. inyectado en una partida con población
  real** — el primero es más barato y limpio de auditar; el segundo es más
  rico pero más caro y contamina la reproducibilidad de esa partida.
- **Un solo individuo LLM o varios simultáneos** — con varios se obtiene
  interacción social genuina entre mentes razonando (lo más interesante
  del experimento), pero multiplica coste y dificultad de lectura.
- **Reflexión periódica tipo diario (con continuidad narrativa propia,
  patrón de "agentes generativos" con memoria/reflexión) vs. puramente
  reactivo tick a tick** — sin resolver.
- **Elección de modelo local concreto** y dimensionamiento del harness de
  herramientas — sin explorar todavía.

## Estado

Documento de visión, no un spec. Ningún componente, sistema, ni línea de
config nueva se ha creado a partir de esta conversación. El siguiente paso
real, si se retoma esta línea, es abrir su propio círculo de brainstorming
para "temperamento como consecuencia de experiencia vivida" — con Diego,
con spec propia, verificado contra el motor real — antes de plantear
ninguna pieza específica del agente LLM en sí.
