# Un mundo vivo — memoria del proyecto para Claude Code

Motor de simulación de un mundo vivo (inspiración declarada: Dwarf Fortress;
aspiración de riqueza narrativa: el legendarium de Tolkien, alcanzada por
emergencia algorítmica, nunca por autoría manual). Este documento resume las
decisiones y reglas que gobiernan el proyecto para que cualquier sesión nueva
de Claude Code parta del mismo entendimiento que las sesiones anteriores
(migradas desde Cowork el 24-08-2026). No sustituye a los informes de
`informes/` — es la capa de orientación rápida; para profundidad real, lee:

- `informes/informe_vision.docx` — qué es el proyecto y por qué, registro no
  técnico. Prácticamente intemporal, rara vez necesita tocarse.
- `informes/informe_tecnico.docx` — arquitectura completa, capa por capa, con
  sección 20 como lista consolidada de cuestiones abiertas.
- `informes/informe_implementacion_bosque.docx` — bitácora cronológica de
  implementación, sección 7.N por pieza construida, la fuente más fiable de
  "qué se probó y qué falló al probarlo contra el motor real".
- `informes/informe_funcionalidades_actuales.docx` — inventario por área
  funcional, clasificado en implementado completo / parcial / solo planteado
  en código. El más propenso a quedar desfasado; contrástalo contra el código
  antes de fiarte de él a ciegas si ha pasado tiempo desde su última revisión.
- `docs/historial_capa_visual.md` — historial archivado de la primera
  exploración de arte real (24 a 26-08-2026, PyxelSpace → Urizen → Mini
  Medieval → retirada de orillas), movido aquí el 2026-09-02 por tamaño
  (era el 37% de este documento) tras haber quedado superseded por el
  pivote al Códice Cartográfico. Solo relevante si se retoma ese tema.
- `docs/informe_codice_cartografico.md` — documentación completa (única
  que existe) del Códice Cartográfico, el frontend Canvas de
  pergamino/acuarela que sustituyó a la saga de arriba (27-08-2026) y que
  a su vez se retiró por completo el 2026-09-16 (ver "Estado actual" más
  abajo) sin haber encontrado nunca un estilo de arte definitivo. Solo
  relevante si se retoma esa vía (no ASCII) en el futuro.

## Los cinco principios de diseño — no son opcionales

1. **Reglas, no guiones.** Se definen leyes de comportamiento; nunca se
   decide a mano qué le pasa a un individuo, un pueblo o una civilización en
   un momento concreto. Una propuesta que describe un suceso concreto en vez
   de una regla que podría producir ese suceso entre otros no es aceptable
   tal cual — reformúlala como ley.
2. **Crecer en círculos pequeños.** Cada pieza nueva añade una sola fuente de
   complejidad, y se valida antes de sumar la siguiente. Desconfía de
   cualquier propuesta que resuelva varios problemas a la vez sin necesidad.
3. **El motor primero, la presentación después.** Cómo se muestra el mundo
   (hoy, visor terminal — estética CRT ámbar, único sistema visual desde
   2026-09-16 tras retirar el Códice Cartográfico, ver
   `docs/informe_codice_cartografico.md`) es una capa desacoplada y
   sustituible. No acoples la lógica de simulación a cómo se presenta.
   **CORREGIDO 2026-09-16, mismo día**: el pivote a "100% glifos/ASCII sin
   ningún asset de imagen" quedó desmentido por el propio código antes
   incluso de escribirse este párrafo (los commits del mismo merge ya
   añadían sprites reales de fauna y construcciones) — Diego confirmó
   después explícitamente que la decisión es un **híbrido**: base ASCII,
   con assets reales sustituyendo al glifo donde se vayan encontrando
   adecuados, introducidos gradualmente. Ver la entrada del "Estado
   actual" más abajo para el criterio real y su alcance actual.
4. **Honestidad sobre lo pendiente.** Ningún sistema se da por cerrado sin
   una necesidad real que lo reclame. Si algo no está resuelto, dilo con
   claridad — nunca improvises una respuesta que aparente más solidez de la
   que hay. Cuando el propio código trae un comentario que documenta un
   hueco, una regresión o una pieza provisional, cítalo tal cual: es la
   fuente más fiable de honestidad sobre lo pendiente de todo el repositorio.
5. **Las leyes son neutras, nunca teleológicas.** Se puede autorear reglas
   físicas, calendarios, rangos raciales, mapas o la existencia de una
   necesidad. No se puede autorear hacia dónde evoluciona moralmente o
   culturalmente una sociedad, ni qué le pasó en concreto a un individuo o a
   un pueblo — eso debe emerger de la ejecución, nunca escribirse de
   antemano.

## Mecanismos genéricos ya construidos — reutiliza antes de inventar

- **Modelo de disposición en tres capas** (racial / histórica / situacional).
- **Atributo con rango racial y sorteo individual**: un atributo se declara
  como rango por raza en `config/constantes.yaml`, cada individuo sortea su
  propio valor dentro de ese rango al nacer. Patrón reutilizado para
  dimensiones físicas, temperamento, capacidad mental — y candidato natural
  para cualquier atributo nuevo con variación entre individuos de la misma
  especie (incluida la paleta de color de un sprite, si algún día vuelve el
  arte: variantes de color fijas en catálogo cerrado sería *inventar* en vez
  de *reutilizar* este patrón).
- **Bus de eventos con severidad** (RUIDO / NOTABLE / HISTÓRICO), único canal
  de comunicación entre sistemas.
- **Cadencia por sistema**: cada tick (necesidades, decisión, movimiento),
  cada día (viajes, clima, desastres), cada estación (modificadores de
  bioma), cada año (envejecimiento).
- **Jerarquía Mundo → Territorio → Zona de bioma → Celda**, ECS con
  componentes como datos puros y sistemas sin conocer clases concretas de
  entidad, niveles de detalle por territorio (Completo / Abstraído /
  Latente), hilo individual para todo ser con nombre propio.

## Sobre el código

- Stack: Python (motor y reglas) + SQLite (persistencia y crónica), sin
  frameworks pesados ni librerías de ECS externas — implementación propia,
  con fines de aprendizaje además de funcionales.
- No optimices por anticipación. Orden ante un problema de rendimiento real:
  perfilar primero, intérpretes alternativos después, extensiones compiladas
  como último recurso.
- Sigue la arquitectura ya decidida en vez de proponer alternativas ya
  descartadas, salvo que Diego pida expresamente reabrir esa decisión.
- **Tests automatizados (CORREGIDO 2026-09-16, la cifra "129" llevaba
  desactualizada desde el 2026-09-04 sin que nadie la revisara en las
  ~12 sesiones intermedias -- mismo patrón de honestidad que ya obligó a
  corregir 87→129 en su momento, esta vez con un salto mayor)**: `tests/`
  contiene 76 ficheros / 675 tests reales a esta fecha (verificado con
  `pytest --collect-only`, no de memoria). Los últimos 17 son de esta
  misma sesión (`test_control_partida.py`/`test_gestor_partidas.py`, ver
  servidor de control remoto más abajo) -- el resto del salto de 129 a
  658 corresponde a todas las sesiones intermedias, nunca actualizado
  aquí. Siguen escritos como "ley física" con docstring explicando el
  comportamiento que validan. La cobertura sigue siendo parcial (nada
  del bucle principal salvo el ciclo de vida del hilo de
  `GestorPartidas`, la mayoría de sistemas de comportamiento, ni la
  mayor parte de persistencia). CI/linting sigue sin configurar.

## Cómo comportarte al ayudar en este proyecto

- **Distingue el tipo de tarea**: diseño conceptual (se resuelve en
  conversación, proponer/justificar/invitar a la crítica/cerrar solo cuando
  Diego confirma), documentación (cuando algo se cierre, ofrece dejarlo por
  escrito en el informe correspondiente, no lo des por "recordado" sin más),
  calibración numérica (curvas de utilidad, umbrales, catálogo de eventos —
  se resuelve con código real corriendo contra el motor, no con más diseño
  sobre el papel; si hace falta un número antes de poder observar el motor
  en marcha, propón una hipótesis de partida marcada explícitamente como
  provisional).
- **Sé crítico, no complaciente.** Diego prefiere que le cuestionen una idea
  floja a que se la validen sin más — así se corrigieron el tamaño acotado a
  100, el criterio de "nombre propio" que no escalaba, el orden de la
  cascada gregario/territorio (invertido tras confirmarse que territorio
  debía ser el filtro primario), y la curva de muerte por vejez original
  (cuadrática, techo 0.3 — resultó catastrófica, 55-76% de todas las
  muertes; recalibrada a exponente configurable=8 con techo mucho más bajo).
- **Señala huecos activamente**, no solo cuando se te pregunten. Si detectas
  una inconsistencia con una decisión anterior, o una pieza que se dio por
  hecha sin estar realmente definida, dilo aunque no sea lo que se te ha
  preguntado.
- **No completes huecos por iniciativa propia sin avisar.** Si necesitas un
  valor que no está definido para poder avanzar, invéntalo con criterio
  razonado, pero dilo explícitamente y márcalo como provisional.
- **Verifica contra el motor real antes de afirmar, no contra la lectura del
  código en abstracto.** El patrón que más veces ha producido hallazgos en
  este proyecto es "esto parecía correcto sobre el papel y resultó
  catastrófico/inerte al correr el motor de verdad" (muerte por vejez,
  purga de memoria, sobrepoblación). Cuando la tarea lo permita, corre el
  motor (o un arnés equivalente) en vez de razonar solo desde el código.
- **Para funcionalidad nueva del motor de simulación, Claude diseña y
  especifica -- NO implementa la funcionalidad él mismo en la sesión.**
  Regla fija, ver la sección dedicada "Flujo de implementación: Claude
  diseña, el pipeline autónomo implementa" más abajo para el mecanismo
  exacto y las excepciones reales. Si acabas de cerrar un diseño en
  brainstorming, el siguiente paso NO es invocar `writing-plans` ni
  implementar -- es trocear el spec y entregarlo al pipeline.
- **Tono**: español, extenso/detallado/explicativo por defecto salvo que se
  pida lo contrario, nunca adulador ni condescendiente, crítico y
  contrastado en vez de solo confirmatorio. Diego es desarrollador
  profesional fullstack — usa terminología técnica sin explicarla de más,
  salvo en documentos explícitamente no técnicos (como el informe de
  visión), donde el registro se mantiene accesible.

## Flujo de implementación: Claude diseña, el pipeline autónomo implementa
## (regla fija desde el arco de flora, 2026-09-01/02 -- documentada aquí
## el 2026-09-03 tras un incidente real)

**Incidente que motivó documentar esto**: en la sesión del 2026-09-03,
tras cerrar en brainstorming el diseño de "cupo de espacio compartido por
celda" (pieza 3 de "poblar más el mundo") y escribir su spec, Claude
ofreció invocar la skill `writing-plans` para elaborar un plan de
implementación y ejecutarlo él mismo en la sesión -- saltándose sin darse
cuenta un flujo que ya llevaba en pie, verificado y usado con éxito desde
el arco de flora (varios días antes). Diego lo corrigió explícitamente:
*"no tengo que explicarte cuál es el flujo de implementación... Claude va
a hacer el diseño de la funcionalidad, elaborará un spec y esa spec se
dará al modelo externo que la usará para hacer la implementación"*.
Confirmado contra el propio historial de git antes de escribir esta
sección (no de memoria) -- ver los commits reales más abajo.

**El flujo real, verificado commit a commit**, para funcionalidad NUEVA
del motor de simulación (mecanismos, sistemas, config -- no para
infraestructura del propio pipeline, ver excepciones abajo):

1. Claude diseña la pieza en conversación (skill `superpowers:brainstorming`)
   y escribe el spec a `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`
   (ubicación por defecto de la propia skill).
2. Claude escribe un ENCARGO mínimo -- ruta a la spec completa más las
   restricciones específicas de esa tarea ("qué NO tocar"), sin
   boilerplate genérico (tests/smoke test/formato de commit ya viven en
   el `instance_template` de `mini-agente-obrero.yaml`, ver más abajo) --
   y lo COMITEA directamente dentro de `docs/superpowers/encargos/`. Ese
   commit ES la entrega real, no una llamada a ninguna skill de
   implementación. Patrón real en el log de git: `d982056`/`f884483`/
   `8696c91`/`cbd16bc`/`91bf85d`, todos titulados "chore: soltar plan X al
   centinela del pipeline" (commits históricos anteriores al reenfoque de
   nombres del 2026-09-03 -- en su momento la carpeta se llamaba
   `docs/superpowers/plans/`, ver la spec de ese reenfoque para el
   detalle completo:
   `docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`).
3. El centinela (`.ai-pipeline/centinela.sh`, proceso en segundo plano,
   sondea `docs/superpowers/encargos/` cada 5s) recoge el primer `.md`
   que encuentra y lo pasa a `.ai-pipeline/ejecutar-encargo.sh`, que
   invoca `mini-swe-agent` (modelo barato, alias `agente-obrero`) contra
   él. **El modelo, antes de tocar código, sobrescribe el propio fichero
   de encargo (ya movido a `docs/plans/in_progress/<nombre>.md`) con su
   plan real de implementación y lo comitea aparte** (paso 0 del
   `instance_template`, 2026-09-03) -- el encargo se convierte en un plan
   real en ese momento, no antes. `ejecutar-encargo.sh` mueve el fichero
   a través de `docs/plans/{in_progress,in_review,failed,done}`, corre la
   suite de tests real, y abre el PR si pasa.
4. Una vez recogido por el centinela, Claude retira el fichero de
   `docs/superpowers/encargos/` con un commit "chore: retirar plan X de
   la cola tras ser recogido" (limpieza -- el contenido ya vive duplicado
   en `docs/plans/in_progress/`). Patrón real: `e3c3745`, `34087d4`,
   `040d298`.
5. Claude revisa el PR resultante cuando el pipeline lo abre (o audita
   manualmente si el disyuntor de 3 intentos salta sin converger, como en
   armas primitivas v2) -- pero el CÓDIGO (y ahora también el PLAN de
   implementación) lo escribe el pipeline, no Claude en la sesión de
   diseño.

**Requisito operativo, comprobar SIEMPRE antes de dar la entrega por
hecha**: el centinela debe estar corriendo de verdad
(`ps aux | grep centinela`) para que soltar un encargo en la carpeta
tenga efecto -- si no está activo, el fichero se queda ahí sin que nadie
lo recoja hasta que alguien arranque `.ai-pipeline/start-pipeline.sh` (o
`centinela.sh` directamente).

**Excepciones reales, ya confirmadas por la práctica -- aquí Claude SÍ
implementa directamente, sin pasar por el pipeline**:
- **Infraestructura del propio pipeline** (scripts de `.ai-pipeline/`,
  como el fix de timeout/reintentos de `ejecutar-encargo.sh` del
  2026-09-03, o el propio reenfoque de nombres de esta sección) -- el
  pipeline no se arregla a sí mismo.
- **Tareas de calibración de juicio/estilo sin criterio de éxito
  verificable mecánicamente** (p.ej. podar comentarios narrativos de
  docstrings) -- confirmado 2/2 fallos reales con `mini-swe-agent`, ver
  `.ai-pipeline/guia-tareas.md`, "Qué NO funciona todavía".
- **Auditoría/corrección de algo que el pipeline dejó a medio converger**
  tras agotar su disyuntor de 3 intentos (p.ej. armas primitivas v2,
  2026-09-03).
- **Documentación pura** (este mismo fichero, informes, specs).
- Diego lo pide explícitamente.

## Bitácora completa — historial por arco (podado de este documento el 2026-09-15)

Este documento creció hasta las ~600KB / 9944 líneas mezclando la capa de
orientación rápida (arriba) con una bitácora cronológica sesión a sesión
que ya no cabía aquí sin dejar de ser "orientación rápida". Podado
siguiendo el mismo criterio que ya se aplicó una vez a la capa visual
(`docs/historial_capa_visual.md`, 2026-09-02): nada se pierde, solo
cambia de sitio, sin reescribir ni resumir ninguna sesión — cada fichero
de abajo conserva la bitácora original, palabra por palabra, agrupada
por arco temático (no por fecha, para que un tema disperso en varias
sesiones quede junto).

- `docs/historial_estabilidad_poblacion.md` — el arco más grande e
  investigado del proyecto: sobrepoblación, fragilidad de lobo/gnomo/
  ardilla/conejo, parejas fundadoras, radio de caza en solitario, orillas
  vadeables, fecundidad por edad, calibración de caballo/agua, el
  primer harness completo de 15×12000. Empieza por los "Límites
  conocidos" de la migración original (24-08-2026).
- `docs/historial_construccion_social.md` — refugio construido,
  recolección, asentamiento, conflicto por refugio ocupado, capacidad de
  construcción por celda, robo/intercambio de recursos, salón común,
  cocinas comunes, comodidad (arco completo).
- `docs/historial_profundidad_geologica.md` — cuevas (Círculos 1-3),
  minería real, la auditoría de coherencia tras el merge del sistema de
  profundidad.
- `docs/historial_profesiones.md` — Agarre, fuego controlado, piedra
  suelta, armas primitivas v2, sistema de comidas / cómo cocinar,
  aptitud vocacional, fabricación de herramientas, minería y tala
  reales (todo el arco "fabricación y uso de herramientas").
- `docs/historial_pipeline_ia.md` — el pipeline autónomo de
  implementación: primeras pruebas con `aider`, migración a
  `mini-swe-agent`, incidentes reales de infraestructura, coste medido,
  el reenfoque de nombres del 2026-09-03.
- `docs/historial_flora_mundo.md` — la cola completa de "poblar más el
  mundo": distribución causal de flora, tipos de propagación, cupo de
  espacio compartido por celda, catálogo ampliado de especies,
  alimentos huérfanos.
- `docs/historial_hilo_individual.md` — nombre propio, el cimiento
  `Relaciones`, amistad por convivencia, afinidad por concepción, pareja
  estable derivada, parentesco derivado, biografía consultable (arco
  completo, 6/6 piezas).
- `docs/historial_capa_comunicacion.md` — conflicto verbal, memoria
  espacial compartida, ocio consciente (`SOCIALIZAR`), sonido físico,
  rumor y liderazgo con inercia real (arco completo, 5/5 piezas).
- `docs/historial_fauna_especies.md` — especie caballo, manada,
  madriguera física, venado, cabra montesa, zorro, y toda la
  investigación de ecología de caza (caza en manada, lobo en montaña).
- `docs/historial_rendimiento.md` — el índice espacial compartido, el
  harness de calibración (`herramientas/harness_calibracion.py`), y los
  tres paquetes de optimización del motor.
- `docs/historial_capa_visual.md` — ya existía desde el 2026-09-02
  (primera exploración de arte real, superseded); el 2026-09-15 se le
  añadió la reconstrucción real de la biblioteca de sprites (2026-09-04)
  y sus correcciones, que hasta ahora vivían sueltas en este documento.

## Estado actual y pendientes reales (actualizado 2026-09-16)

Lista corta de lo que sigue genuinamente abierto hoy — para el detalle de
cómo se llegó a cada punto, abre el historial correspondiente de arriba.

- **El criterio maestro de Diego (5 especies vivas a la vez, ≥50% de las
  semillas) sigue sin remedirse de forma agregada** desde el harness de
  15 semillas × 7 especies del 2026-09-12 (entonces: 0-7%, muy por
  debajo del objetivo). Desde esa medición se aplicaron varias mejoras
  reales (radio de caza en solitario, orillas vadeables, tasa de
  consumo por especie, especie zorro) pero ninguna se ha vuelto a medir
  contra el criterio agregado — es el pendiente más urgente si se quiere
  saber dónde está el ecosistema hoy, antes de calibrar nada más a
  ciegas.
- **CERRADO 2026-09-15, ver `docs/historial_estabilidad_poblacion.md`**:
  las 4 recomendaciones del informe de calibración del 2026-09-12 ya se
  investigaron con A/B reales — 3 (techo de manada, densidad de venado,
  desempate de reputación) quedan sin ningún cambio de config, los datos
  no respaldan tocar nada; la 4ª (sesgo de vocación hacia forrajero) se
  confirma real y estructural, no un bug, y queda como decisión de
  diseño pendiente de Diego (no una calibración numérica). De paso se
  corrigió una contradicción interna de este propio documento sobre la
  dirección de `factor_ampliacion_techo_manada`.
- **Arco nuevo "asentamiento como entidad propia" — Pieza 1 (identidad
  persistente) CERRADA 2026-09-15**, ver
  `docs/historial_construccion_social.md`: `Asentamiento` sigue siendo
  100% derivado (se recalcula cada día), pero ahora conserva un id
  estable entre recálculos por solape de Jaccard en vez de comparar el
  conjunto exacto de miembros — cierra de paso un bug real (reemisión
  de `AsentamientoFundado` ante cualquier fluctuación de población).
  Verificado con tests dirigidos y con un diagnóstico de 4 semillas
  nuevas en juego libre (ids estables durante miles de ticks pese a
  crecer/perder miembros, sin ninguna reemisión espuria). Corrección
  honesta: el commit `ad7b28b` dice "598/598 tests" en su mensaje —
  el conteo real verificado es **590 passed**, no amendado por ser un
  commit ya empujado. **Unificado con el roadmap "asentamientos/
  profesiones" (2026-09-12) el mismo día, a petición de Diego** —
  "conocimiento colectivo transmisible" (Pieza 3 de ese roadmap +
  Piezas 2-3 del informe de hoy) ya CERRADO también, ver
  `docs/historial_construccion_social.md`: valor agregado por
  asentamiento (sobrevive a la muerte de cualquier miembro, a
  diferencia de `Vocacion` individual) que modula la tasa de
  RECOLECTAR/CONSTRUIR/COCINAR — verificado con las mismas 4 semillas
  de la Pieza 1, acumulando niveles reales (hasta saturado a 1.0 en
  "forrajero") desde el primer momento en que existe un asentamiento,
  a diferencia de casi todas las piezas sociales anteriores de este
  proyecto que quedaron "correctas pero invisibles" semanas.
  **"Nombre propio + crónica de asentamiento" (Pieza 4-5 del informe
  original) CERRADO el mismo 2026-09-15**, ver
  `docs/historial_construccion_social.md`: nombre generado al fundarse
  (prefijo+sufijo silábico), con mix probabilístico hacia un catálogo
  temático si la celda-centro tiene un rasgo geográfico fuerte (agua o
  montaña — alcance deliberadamente acotado a esos dos, no los 5 biomas,
  tras feedback crítico de Diego de que un generador puramente silábico
  "no se diferencia mucho de una generación de nombres común"), más
  `Persistencia.cronica_de_asentamiento(id)` para consultar los eventos
  propios de un pueblo aislados de otros. **"Tipos de construcción
  nuevos" (taller de artesano → mobiliario → comodidad, más almacén
  personal en refugio) CERRADO 2026-09-16, mismo círculo, dos piezas
  unificadas a petición explícita de Diego** (contra el criterio
  habitual de "una complejidad a la vez"), ver
  `docs/historial_construccion_social.md`: taller como tercer paralelo
  comunal, gateado por conocimiento colectivo "artesano" del propio
  asentamiento, habilita FABRICAR "mobiliario" — el mueble se trata como
  un material más (kg, calidad alta), reutilizando SIN NINGÚN CAMBIO el
  mecanismo ya construido de mejora de vivienda por sustitución; en
  paralelo, dormir en el refugio propio ya completado deposita
  automáticamente el material a granel portado en un almacén personal
  (`Construccion.almacen`, solo depósito, sin retirada todavía).
  **Diagnóstico de 4 semillas × 10000 ticks, resultado dividido y
  honesto**: el almacén de refugio se ejerce con fuerza real en las 4
  (4 a 198 depósitos según semilla); el taller/mobiliario, en cambio,
  **0 muebles fabricados en las 4**, incluida la única semilla
  (402001) donde la cadena comunal SÍ avanzó lo bastante (salón común y
  cocina completos) — ni siquiera ahí llegó a construirse el taller
  dentro de la ventana de 10000 ticks. Mecanismo verificado correcto por
  16 tests dirigidos, pero **"correcto pero invisible" en juego libre**,
  mismo patrón que ya sufrieron salón común/minería/tala en su día —
  agravado aquí por el conflicto de capacidad ya documentado en
  `config/materiales.yaml` (huella_m2 de los 4 edificios comunales suma
  125, por encima de `capacidad_construccion_celda_m2=80`).
  **"Pertenencia explícita, colocación satélite y necesidad
  diferenciada de los comunales" CERRADO el mismo 2026-09-16, mismo
  día, tres cambios en un único círculo a petición explícita de
  Diego** ("todo junto"), ver `docs/historial_construccion_social.md`:
  a raíz de la crítica de Diego al conflicto de capacidad de arriba
  ("los edificios comunes deberían estar cada uno en celdas
  distintas") — `Construccion.asentamiento_id` (pertenencia explícita,
  reemplaza una búsqueda por proximidad que podía confundir dos
  pueblos vecinos — hallazgo aparte: `Asentamiento.almacen_id`, cacheado
  a diario desde 2026-09-08, nunca se leía en ningún consumidor real,
  cache muerta, retirada); solo `salon_comun` sigue anclado al centro
  exacto, almacén/cocina/taller pasan a "satélite" (celda vecina más
  próxima con cupo, excluyendo el propio centro para no competir con el
  ancla); y los 4 tipos comunales compiten AL MISMO NIVEL (se retira la
  jerarquía "almacén primero", accidente histórico) — cada uno gatea por
  su propia necesidad real (almacén/cocina: excedente de
  saciedad/hidratación; salón_común: sociabilidad+curiosidad; taller:
  déficit de comodidad), desempatando por progreso ya invertido.
  **Diagnóstico de 4 semillas nuevas (403001-403004) × 10000 ticks,
  resultado fuerte y consistente en las 4 — a diferencia de la mayoría
  de piezas sociales de este proyecto, que tardaron semanas en
  observarse**: en las 4, nacieron MÁS edificios comunales en celda
  satélite que en el ancla (1-2 ancla frente a 2-4 satélite según
  semilla) — la colocación satélite se ejerce con fuerza desde el
  primer momento en que hay más de un tipo comunal pendiente a la vez.
  Lo que este círculo NO resolvió, honesto: taller/mobiliario sigue en
  0 muebles fabricados en las 4 semillas (igual que el diagnóstico
  anterior) — quitarle la competencia directa por espacio no basta por
  sí solo para que su propio gate gane el argmax a tiempo; no se
  desglosó por tipo qué construcción concreta ocupó cada celda
  satélite, así que no se sabe si taller en particular llegó a
  crearse sin completarse, o ni siquiera eso. Pendiente real: el gate
  de cocina (excedente de solo saciedad) sigue PROVISIONAL, sin eje
  mejor identificado que no exigiera inventar un componente nuevo;
  interacción entre asentamientos (Pieza 4 restante del roadmap
  unificado) sigue sin empezar; remedir el criterio maestro de Diego
  contra el ecosistema sigue siendo el pendiente más urgente de todos
  (ver primer punto de esta lista), sin decidir el orden frente a lo
  anterior.
- **Caza en manada de lobo contra caballo**: mecanismo verificado
  correcto, pero la coincidencia temporal que exige (~4-6 aliados
  cazando a la vez, dentro de `radio_apoyo_grupal`) es estructuralmente
  rara — 0 casos en más de 80 corridas acumuladas de varias sesiones,
  incluido un A/B con el factor de manada al triple (6.0) que tampoco
  produjo ninguna captura.
- `sonidos_emitidos_totales` del harness de calibración reporta 0 pese a
  que la amenaza por sonido sí se ejerce en la misma corrida — sospecha
  de bug de instrumentación, nunca verificado a fondo.
- Robo de arma (`nucleo/conflicto.py` vía `_intentar_robo_arma`): sin
  observar en juego libre en ninguna semilla probada — correcto por
  tests dirigidos, exige una combinación de condiciones poco frecuente.
- Decaimiento de afinidad en `Relaciones` (rencor/amistad/pareja):
  introducido el 2026-09-11, sin ninguna calibración contra el motor
  real más allá de un `BOSQUE_AUTO_TICKS` de humo.
- El ciclo minería/tala (fabricar herramienta → extraer veta/talar
  árbol) ya se cierra de verdad en juego libre desde el fix de
  "Vía 1 requiere motivo real" (2026-09-12), pero sin medir su
  frecuencia real a escala de población.
- Arco de comodidad (Pieza D, mejora de vivienda) cerrado el
  2026-09-14 sin que el criterio maestro se haya remedido con el
  cambio ya aplicado — mismo pendiente que el primer punto.
- **Centinela del pipeline sigue parado** desde el incidente de
  cancelación de "madriguera-física-A" (2026-09-07) — necesita reinicio
  manual en la máquina de Diego. Este entorno de sesión en la nube no
  tiene `OPENROUTER_API_KEY` ni `mini-swe-agent` instalados, así que
  toda la funcionalidad de las últimas ~15 sesiones se implementó
  directamente por Claude (excepción ya prevista y usada
  sistemáticamente, ver "Flujo de implementación" arriba).
- **Ciudad enana**: aparcada explícitamente por Diego hasta que se
  plantee la raza enana — no retomar el tema hasta entonces.
- **Retirada completa del Códice Cartográfico y pivote a mapa 100% ASCII
  (2026-09-16, decisión de Diego)**: varias sesiones sin encontrar un
  estilo de arte definitivo (ver `docs/historial_capa_visual.md` y
  `docs/informe_codice_cartografico.md`) estaban restando foco al
  desarrollo del motor. `presentacion/vista_web.py` quedó reducido a
  servidor + contrato JSON (`construir_instantanea`, sin tocar); el
  visor terminal (`presentacion/terminal_prototipo/`) pasa a ser el
  ÚNICO sistema visual — en el momento de escribir este párrafo, sin
  ningún asset de imagen: todo (terreno, agua, relieve, flora por
  categoría árbol/arbusto/cobertura, fauna, construcciones, recursos en
  el suelo) se representa con glifo+color de texto desde un catálogo
  único (`CATALOGO_GLIFOS` en `terminal.html`), con leyenda desplegable
  generada desde ese mismo catálogo, zoom centrado en el cursor y paneo
  por arrastre. Los ~83MB de sprites del prototipo anterior se retiraron
  del repositorio (recuperables por git history si algún día se retoma
  una vía gráfica). **Esta afirmación de "sin ningún asset de imagen"
  quedó desmentida el mismo día, ver la entrada "Híbrido ASCII+sprite"
  más abajo** — se documenta aquí tal cual porque fue la decisión real
  en ese momento del día, no se reescribe con retroactividad.
  **Segunda pasada de limpieza el mismo día, a raíz de que Diego preguntó
  explícitamente "¿has eliminado todo el código muerto y los assets que
  no se usan?"** (la primera pasada solo tocó lo directamente enredado
  con el cambio, no fue una auditoría completa): `inspiracion/` (127MB,
  fotos de referencia + su versión procesada, sin ningún consumidor ya
  que el pipeline de sprites que las usaba desapareció entero) y los 6
  scripts de un solo uso en `presentacion/arnes/` que la generaban o la
  consumían (`extraer_sprites_definitivos.py`,
  `adaptar_especies_faltantes.py`, `quitar_fondo_inspiracion.py`,
  `integrar_inspiracion_terminal.py`, más `arreglar_utf8.py`/
  `empalmar_marco.py`/`empalmar_marco_v2.py`, ligados al HTML del
  Códice ya retirado); y la dependencia `rich>=13.0` de
  `requirements.txt`, declarada sin un solo `import rich` en todo el
  repositorio (hallazgo que ya constaba en una auditoría previa sin que
  nadie lo hubiera corregido). Lección honesta: la primera pasada de
  limpieza de este mismo círculo no fue exhaustiva por defecto — hizo
  falta que Diego preguntase explícitamente para completarla.
  Pendiente real: confirmación visual de Diego sobre la elección de
  glifos/colores concreta — es una primera propuesta razonada, no una
  calibración cerrada; catálogo de eventos filtrable (panel
  "EVENTOS://LOG") sigue con el placeholder de siempre, sin implementar.
- **Pictogramas reales para fauna y construcciones (2026-09-16, sesión
  posterior a la retirada del Códice, mismo día)**: segunda excepción
  deliberada a "mapa 100% glifos" tras el propio pivote de arriba —
  Diego pidió pictogramas reales para las criaturas ("no convence del
  todo, los iconos son demasiado pequeños" con emoji nativos), generó
  8 sprites de fauna con IA en estilo pixel-art (referencia: un lobo
  que subió como imagen) y 5 de construcciones (estilo "cabaña musgosa"
  con 3 referencias propias), todos committeados en bruto a `iconos/` y
  procesados por Claude (flood-fill de fondo desde los bordes —
  ver histórico de por qué no un color-key global — recorte a bbox,
  downscale `NEAREST`) hacia
  `presentacion/terminal_prototipo/sprites_{criaturas,construcciones}/`,
  servidos por rutas nuevas en `vista_web.py`
  (`_servir_sprite(subcarpeta, ruta)`, mismo guardia anti path-traversal
  reutilizado). Tamaño de sprite ya NO es fijo: fauna escala por
  `DimensionesFisicas.altura_m` real del individuo, construcciones por
  `masa_minima_<tipo>` real de `config/materiales.yaml` (no por
  `huella_m2`, que es el área de suelo — desliz real corregido tras dos
  rondas de feedback de Diego, ver commits `c939e2e`/`7cb8f90`) — ambas
  con raíz N-ésima (0.5 fauna, 1/3 construcciones, la relación
  físicamente correcta entre una MASA y un tamaño lineal) para comprimir
  el rango real sin desbordar. Bug real de apilamiento encontrado y
  corregido (commit `4a58e45`): un sprite más ancho que su celda quedaba
  tapado por la celda vecina con el mismo z-index — construcciones pasan
  a su propio nivel (500+fila) por encima de todo el suelo. El
  resplandor de "consciente" (drop-shadow blanco heredado del sistema de
  glifos) se retiró por completo a petición de Diego ("por que el gnomo
  tiene un reborde blanco" → "quitalo") — se leía como un borde de
  recorte mal hecho sobre una silueta de pixel-art real, no como señal
  deliberada. **Tensión de diseño señalada en esta sesión, RESUELTA en
  la sesión siguiente, mismo día — ver "Híbrido ASCII+sprite" justo
  abajo**: con fauna y construcciones ya en sprite, el suelo desnudo
  (glifo puro) pasaba a ser la única excepción, y Diego había subido
  además 8 JPGs de flora sin procesar (`iconos/flora/`) sin decidir
  todavía si integrarlos. Diego zanjó la disyuntiva: híbrido
  deliberado, sprite donde se encuentre arte adecuado, introducido
  gradualmente — flora ya integrada bajo ese criterio, ver más abajo.
  **Hallazgo aparte sin corregir, sigue vigente**: el `@font-face` de
  VGA437 (`fonts/Web437_IBM_VGA_9x16.woff`) devuelve 404 real al
  servirse vía `ServidorWeb` — `ManejadorWeb` nunca tuvo una ruta para
  `/fonts/*`, así que el visor lleva toda la sesión (y probablemente
  desde que se conectó en vivo) cayendo a la fuente monospace del
  navegador en vez de la bitmap CRT prevista. Fix trivial (una ruta más,
  mismo patrón que `/sprites_*`), no aplicado por estar fuera del
  encargo del momento en que se encontró. La leyenda desplegable
  tampoco se actualizó tras esto: para fauna/construcciones con sprite
  real sigue mostrando el glifo/emoji de respaldo del catálogo en vez
  de una miniatura del sprite, inconsistente con lo que se ve en el
  mapa — mismo hueco real para los sprites de flora añadidos después.
- **Híbrido ASCII+sprite (2026-09-16, mismo día que la retirada de
  arriba, decisión de Diego que la corrige)**: el "mapa 100% ASCII sin
  ningún asset de imagen" de la entrada anterior no llegó a sostenerse
  ni un día completo — los commits `c6af86b` (fauna) y `c939e2e`
  (construcciones) del mismo merge ya reintroducían sprites reales antes
  de que se escribiera esta memoria, dejando tanto este documento como
  un comentario de cabecera del propio `terminal.html` afirmando "CERO
  imagenes en el mapa" mientras el código un poco más abajo ya las
  usaba — contradicción real, encontrada auditando el código, no
  reportada por nadie hasta entonces. Diego, preguntado explícitamente,
  confirmó el criterio: **base ASCII, con sprites sustituyendo al glifo
  donde se vaya encontrando arte adecuado, introducidos gradualmente**
  (no una lista cerrada de categorías) — todos los assets ya
  disponibles son de uso gratuito según confirmación de Diego (no se
  investigó licencia individual más allá de eso).
  Estado real a esta fecha (**CORREGIDO, ver los cinco círculos
  completos en `docs/historial_capa_visual.md`, este párrafo es el
  resumen final, no la crónica**): fauna (8 especies) y las 5
  construcciones comunales ya tenían sprite desde antes de esta sesión;
  en esta sesión se añadió **flora** — 13 de las 15 especies del
  catálogo tienen sprite, **mapeo CONFIRMADO por Diego tras dos rondas
  de aclaración** (un primer mapeo interpretado por Claude fue
  rechazado dos veces antes de llegar al criterio real: no exige que el
  nombre de fichero coincida 1:1 con la clave de especie, sino que el
  arte corresponda al `bioma` real de `config/flora.yaml` — un mismo
  fichero puede cubrir varias especies con clima afín,
  `arbustoMontañaTundra.jpg`→montano+ártico,
  `hierba.jpg`→sus 3 variantes). Solo quedan sin sprite **liquen y
  musgo**, las 2 especies para las que Diego no aportó ningún icono.
  Los 10 iconos JPEG viven en `iconos/flora/` (2048×2048, fondo de
  tablero de ajedrez "quemado" en el propio JPEG, no alfa real —
  limpiado con verificación visual manual por icono, NO con una
  heurística de color automática: una heurística de bimodalidad/fase de
  cuadrícula estuvo a punto de agujerear pétalos reales de una flor,
  descartada), procesados a
  `presentacion/terminal_prototipo/sprites_flora/` (10 PNG RGBA,
  resolución proporcional a `huella_m2` real por especie). Tamaño en
  pantalla de árbol/arbusto escalado por `huella_m2` real de
  `config/flora.yaml` por ÁREA visual real (no solo altura — un primer
  intento escalaba solo `img.style.height` dejando el ancho a merced
  del aspect ratio nativo de cada PNG, y el pino, con el doble de
  huella que cualquier arbusto pero un arte muy vertical, salía más
  ESTRECHO que todos ellos; corregido con `ASPECT_FLORA` real medido
  por especie), más `FACTOR_TAMANO_ARBUSTO=0.72` (reducción adicional
  solo para arbusto, pedido explícito de Diego, PROVISIONAL); cobertura
  (sin `huella_m2` real, no compite por espacio físico) usa un tamaño
  FIJO en vez de inventar un dato que el motor no tiene. Los recursos
  sueltos del suelo (madera/piedra) ya NO compiten por el mosaico de
  cuadrantes con el árbol/construcción de su misma celda — pasan a ser
  un badge pequeño superpuesto; el 94% de las celdas con árbol también
  tenían madera, así que antes de este fix la inmensa mayoría de los
  árboles del mapa se veían reducidos a una miniatura de icono
  compartido en vez del sprite grande calibrado ("por qué hay árboles
  en las celdas pequeñas", Diego). De paso se encontró y corrigió un
  bug real preexistente (desde que se añadieron sprites de fauna/
  construcciones): `presentacion/vista_web.py` solo servía
  `/sprites_criaturas/` y `/sprites_construcciones/` por HTTP —
  cualquier sprite servido a través de `ServidorWeb` (no abierto por
  `file://` directamente) que viviera en otra subcarpeta habría
  devuelto 404 sin que nadie lo hubiera notado hasta abrir el visor así.
- **Profundidad real, dirección, paso natural y jitter de posición en el
  visor (mismo día — "círculo final" al escribirse esta entrada, luego
  corregido: hubo un círculo más justo debajo)**: hasta este círculo,
  fauna tenía un z-index con
  offset fijo (`1000+y`) que la ponía SIEMPRE por encima de todo el
  suelo/flora/construcción sin importar su posición real — decidido
  así en un círculo anterior del mismo día para resolver un bug real de
  desborde de sprite entre celdas vecinas, con el efecto secundario de
  que fauna nunca podía quedar oculta por nada. Diego pidió profundidad
  real ("si pasan por detrás que queden ocultos, no flotando encima");
  sustituido por un esquema único `zIndexPorFila(y, capa) = y*10 +
  prioridad` que aplica por igual a terreno/flora/construcción/fauna —
  la fila real decide siempre primero, la prioridad por tipo (terreno
  0, flora 2, construcción 4, fauna 6) solo desempata en la misma fila
  exacta. Verificado con Playwright: un zorro en una fila anterior a un
  árbol grande queda visiblemente tapado por su follaje. Además: el
  sprite de fauna ahora se invierte (`scaleX(-1)`) según la dirección
  real de desplazamiento (inferida comparando la X actual contra la
  última conocida, persistida en el propio elemento DOM — el motor no
  expone "dirección" como dato; convención asumida sin poder
  verificarla contra las 8 especies reales: el arte mira a la derecha
  de base); y el sondeo de `estado.json` bajó de 1000ms a 400ms
  (igualando `segundos_por_tick` real del motor, `config/visual.yaml`)
  con la transición CSS de `0.9s linear` a `0.35s ease-in-out` — a
  1000ms el motor podía avanzar 2-3 ticks (y una criatura 2-3 celdas)
  entre dos sondeos, y ninguna curva de animación arregla que un salto
  de varias celdas en línea recta se lea como caminar en vez de saltar.
  Pendiente real: el z-index cambia de golpe (sin transición, CSS no
  anima esa propiedad) en el instante en que una criatura cruza de fila
  mientras camina — aceptado como límite conocido de Y-sorting simple,
  no se abordó un mecanismo de interpolación de profundidad que no se
  pidió.
  **Añadido justo después, mismo día**: Diego señaló que los sprites
  "se sitúan siempre en el centro de la celda... parecen líneas rectas"
  — cierto, `left:50%` fijo (construcción/flora) y `cx+CELDA/2` exacto
  (fauna) sin ninguna variación. Corregido con `jitterPx`/`jitterPxPorId`
  (mismo `hashDet` ya usado para variar tono/textura, sal propia):
  desplazamiento horizontal de hasta ±25% de `CELDA`, determinista por
  celda para elementos estáticos y por ID de entidad (no por celda
  actual) para fauna — con semilla de celda el sesgo lateral de un
  animal "saltaría" en cada cambio de celda, viéndose peor que sin
  jitter. Sin jitter, deliberadamente: el mosaico de cuadrantes (sprite
  ya confinado a un cuarto de celda) y el fallback de emoji/glifo de
  fauna sin sprite (centrado por flex, no por `left` absoluto).
- **Renombrado `BOSQUE_* -> SIMULACION_*` (2026-09-16)**: Diego, sobre la
  spec de abajo: "lo de que aparezca bosque en todos los comandos de
  test... deberíamos cambiarlo por simulación, que es lo que es, ya no
  es un solo bosque". `SIMULACION_MODO_VISUAL`/`SIMULACION_AUTO_TICKS`/
  `SIMULACION_CONTINUAR` (las 3 únicas lecturas reales de `os.environ`
  del proyecto) y `datos/bosque.db` → `datos/simulacion.db`. Alcance
  acotado a código y documentación VIVA (`main.py`, comentarios en
  `sistemas/`/`nucleo/` que citan el nombre, `COMANDOS.md`, README del
  visor) — la bitácora histórica ya cerrada (`docs/historial_*.md`,
  `docs/plans/*`, las specs de sesiones anteriores) conserva el nombre
  real usado en su momento a propósito, no se reescribió.
- **Servidor de control remoto (2026-09-16, ver
  `docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md`,
  implementado directamente por Claude el mismo día — infraestructura de
  control/presentación, no una regla nueva del motor)**: Diego preguntó
  si podía alojarse el programa y lanzar/controlar una partida remota
  por web, con la queja explícita de que el arranque actual por env vars
  "debería ser un comando". `python3 servidor.py` (nuevo, raíz) arranca
  `ServidorWeb`+`GestorPartidas` sin lanzar ninguna partida; desde el
  navegador (barra de control nueva en `terminal.html`): NUEVA PARTIDA
  (semilla aleatoria u opcional), PAUSAR/REANUDAR, velocidad (0.25x-8x,
  límites sin calibrar), FINALIZAR — 5 endpoints `POST /partida/*`
  nuevos en `vista_web.py`, 501 si el servidor no tiene
  `GestorPartidas` inyectado (modo CLI de `main.py` de siempre, sin
  cambios de comportamiento, condición de aceptación verificada con los
  658 tests previos intactos). `main.py` se refactorizó en
  `preparar_partida()`/`avanzar_un_tick()` reutilizables entre el modo
  CLI y el nuevo `ejecutar_partida_controlada()` (hilo de fondo,
  `nucleo/control_partida.py:ControlPartida` con pausado/detener/
  velocidad thread-safe). **Bug real encontrado en verificación manual
  contra el servidor real, no en tests**: `pausada` quedaba hardcodeada
  a `False` en el payload, y aunque se leyera bien de `control`, el
  hilo se queda bloqueado dentro de la espera de pausa y NUNCA vuelve a
  publicar mientras dura — `GestorPartidas.pausar()/reanudar()` parchean
  ahora directamente el último JSON servido. Verificado con Playwright
  contra el servidor real (no solo tests): ciclo completo pantalla de
  espera → nueva partida → mapa real → pausa (tick congelado, confirmado
  con dos lecturas) → reanudar → velocidad → finalizar → vuelta a
  pantalla de espera. Sin autenticación ni TLS (aceptado por ahora,
  "solo quiero verlo yo"; hueco real si se comparte la URL); una partida
  nueva sobreescribe `datos/simulacion.db` sin histórico de partidas
  anteriores. **Pendiente real**: Diego no ha desplegado esto en ninguna
  máquina remota todavía, solo verificado en local dentro de esta
  sesión — sigue sin probarse el caso de uso real que lo motivó.
- Selector de zona real en el visor web: nunca añadido, el visor solo
  dibuja superficie (`zona_idx == 0`).
- Créditos de licencia de los paquetes PyxelSpace: pendiente desde la
  migración original (24-08-2026), nunca resuelto.
- **El harness de referencia completo (15 semillas × 12000 ticks sin
  cortar por límite de tiempo) sigue sin correrse nunca de principio a
  fin** — cada medición del proyecto hasta hoy ha usado ventanas
  truncadas por el cómputo real disponible en cada sesión. Sigue siendo
  la referencia de rigor pendiente para dar cualquier calibración por
  cerrada de verdad.
- Estructuras multi-celda (muralla, castillo), abuelos/tíos en
  parentesco (bloqueados por la purga de `Identidad` al morir), y
  comodidad como motor general más allá de vivienda (herramienta,
  comida, conexión con ocio→"arte") — visión declarada por Diego, sin
  ningún diseño todavía.
- Todo el catálogo de constantes numéricas nuevas introducidas en las
  últimas ~15 sesiones sigue marcado PROVISIONAL en su propio fichero
  de config, sin calibrar contra el harness completo.

## Comentarios técnicos vs narrativa histórica (2026-09-02)

Convención nueva, decidida con Diego, aplicable a partir de ahora a
todo el código del repositorio (no solo al que se toque por otro
motivo -- ver `.ai-pipeline/guia-tareas.md` para cómo delegar esta
poda, con los resultados reales de intentarlo).

- **Se queda en el código, corto**: qué hace una función/campo, y el
  "por qué" que hace falta para no romperlo al tocarlo -- invariantes
  reales (p.ej. "NO se persiste, se regenera desde la semilla"),
  relaciones entre campos, gotchas.
- **Sale del código, va a `docs/historial_<módulo>.md`** (un documento
  por módulo/área, mismo patrón que `docs/historial_capa_visual.md`
  ya sentó de precedente): incidentes ya resueltos, calibraciones
  descartadas, el recorrido de cómo se llegó a esta decisión frente a
  otras, fechas, nombres de "Círculo", citas a conversaciones con
  Diego, referencias a specs por ruta completa. Nada se pierde, solo
  cambia de sitio.

**ACTUALIZACIÓN (2026-09-02, mismo día): la poda se completó en todo el
repositorio**, no solo en los tres ficheros originales -- `nucleo/flora.py`,
`sistemas/sistema_flora.py`, `nucleo/celda.py` (`docs/historial_flora.md`/
`historial_celda.md`), y a continuación el resto de `nucleo/`
(`construccion.py`, `disposicion.py`, `territorio.py`, `orografia.py`,
`asentamiento.py`, `cueva.py`, `materiales.py`, `entidad.py`, `agua.py`,
`persistencia.py`, `zona_bioma.py`), todo `componentes/`, y todos los
sistemas (`sistema_movimiento.py`, `sistema_recursos.py`,
`sistema_decision.py`, `sistema_necesidades.py`, `sistema_reproduccion.py`,
`sistema_desastres.py`, `sistema_depredacion.py`,
`sistema_descomposicion.py`, `sistema_clima.py`,
`sistema_capacidad_fisica.py`, `sistema_ciclo_vital.py`,
`sistema_capacidad_mental.py`, `sistema_asentamiento.py`) más `main.py`.
Cada módulo grande generó su propio `docs/historial_<módulo>.md`, mismo
patrón que los tres originales.

**Hallazgo real sobre CÓMO se hizo, no solo que se hizo**: `dc64f30`
documenta que delegar esta poda a `mini-swe-agent` falló 2/2 -- tareas
de calibración de juicio/estilo (qué comentario es "narrativa histórica"
frente a "invariante que hace falta para no romper el código al
tocarlo") no tienen un criterio de éxito objetivo que el modelo pueda
verificar por su cuenta, a diferencia de una implementación con tests.
Toda la poda del resto del repositorio se hizo directamente por Claude
en la sesión de esa tarde, no vía pipeline -- decisión consistente con
ese hallazgo, no una elección arbitraria de herramienta.

