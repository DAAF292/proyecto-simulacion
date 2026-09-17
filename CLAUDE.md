# Un mundo vivo — memoria del proyecto para Claude Code

Motor de simulación de un mundo vivo (inspiración declarada: Dwarf Fortress;
aspiración de riqueza narrativa: el legendarium de Tolkien, alcanzada por
emergencia algorítmica, nunca por autoría manual). Este documento resume las
decisiones y reglas que gobiernan el proyecto para que cualquier sesión nueva
de Claude Code parta del mismo entendimiento que las sesiones anteriores
(migradas desde Cowork el 24-08-2026). Este documento, junto con
`docs/historial_*.md`, es la única capa de referencia viva del proyecto —
para profundidad real, lee esos historiales por arco temático (ver la
sección "Bitácora completa" más abajo).

**Retirados los 6 informes `.docx` de `informes/` (2026-09-17)**: existieron
como capa de "profundidad técnica" separada de este documento desde la
migración original, pero llevaban desde el 2026-09-10 sin tocarse mientras
se cerraban de verdad varios arcos grandes (estabilidad de población,
construcción social completa, todo el pivote de capa visual, renombrado
`BOSQUE_*→SIMULACION_*`, servidor de control remoto) — 7 días de desfase
frente a un ritmo de cambio real muy alto. Auditado antes de retirarlos, no
solo por fecha: `informe_funcionalidades_actuales.docx` no estaba
simplemente desactualizado, estaba activamente equivocado — dedicaba una
sección entera al Códice Cartográfico como sistema de presentación vigente
(retirado por completo ese mismo 2026-09-16), citaba `BOSQUE_CONTINUAR`/
`BOSQUE_AUTO_TICKS`/`BOSQUE_MODO_VISUAL`/`datos/bosque.db` (renombrados a
`SIMULACION_*`/`datos/simulacion.db` el mismo día), reportaba "3 archivos
con 22 tests" frente a los 76/675 reales, y no mencionaba en absoluto el
arco completo de "asentamiento como entidad propia". El resto de informes
no se auditó con el mismo nivel de detalle antes de retirarlos junto con
el que sí se verificó mal, a petición explícita de Diego. Las 3 fichas PDF
de `informes/` (`ficha_gnomo.pdf`, `ficha_lobo.pdf`,
`ficha_criatura_vacia.pdf`) se conservan — no son informes narrativos sobre
el estado del sistema y no se auditaron por el mismo motivo. Nada de su
contenido se migró a ningún historial antes de borrarlos: a diferencia de
la poda de `docs/historial_*.md` (que preserva texto palabra por palabra),
aquí se decidió que un informe demostrablemente incorrecto no merecía
conservarse ni archivado.

**Segunda ronda de limpieza de repositorio, mismo día (2026-09-17), a
continuación de la retirada de informes/ de arriba** — mismo criterio que
ya se aplicó una vez a `inspiracion/` (127MB sin consumidores, ver Bitácora
completa): activo sin usar o proceso muerto, no solo "código feo".
Verificado consumidor por consumidor antes de tocar nada, no por bulto:
- `oldschool_pc_font_pack_v2.2_web/` (5.8MB, 361 variantes `.woff` del
  paquete "The Ultimate Oldschool PC Font Pack") retirado del repositorio —
  de las 361 variantes, una sola (`Web437_IBM_VGA_9x16.woff`) tenía uso
  real, ya extraída a `presentacion/terminal_prototipo/fonts/` desde el
  2026-09-16. De paso se resuelve un crédito de licencia que llevaba
  "pendiente" desde que se adoptó la fuente (comentario propio en
  `terminal.html`: "atribucion pendiente en el mismo lugar que las de
  PyxelSpace") — ahora vive en
  `presentacion/terminal_prototipo/fonts/CREDITS.txt` (CC BY-SA 4.0, VileR,
  int10h.org). Esto NO resuelve el crédito de PyxelSpace de la lista de
  pendientes más abajo — son paquetes distintos.
- `docs/superpowers/plans/` (3 ficheros, 2026-09-03: caballera-rotación,
  hachurado de relieve, alzado por elevación) retirada por completo —
  doble relic: es la carpeta con el nombre anterior al reenfoque
  `plans/→encargos/` del propio 2026-09-03 (ver spec de esa fecha), Y su
  contenido son planes de implementación para el visor Canvas del Códice
  Cartográfico, sistema retirado por completo el 2026-09-16. Ningún
  consumidor posible para ninguna de las dos razones por separado.
- `docs/superpowers/encargos/pendientes/2026-09-02-propagacion-05-zoocoria.md`
  retirado — encargo que sí se recogió en su momento (cabecera idéntica al
  plan real, hoy en `docs/plans/done/2026-09-02-propagacion-05-zoocoria.md`,
  que sí siguió el flujo completo), pero al que nunca se le aplicó el paso
  4 del flujo de implementación ("retirar plan X de la cola tras ser
  recogido") — quince días de cola muerta sin que nadie lo notara.
- `harness_v2_log.txt`, `resultados_harness_completo.json`,
  `resultados_harness_completo_v2.json` (raíz del repo, ~144KB, comiteados
  el 2026-09-13 junto con "assets" sin relación aparente) retirados — datos
  crudos de una corrida de harness, sin ningún consumidor en código ni
  documentación, exactamente la categoría que `.gitignore` ya declara
  ignorar para `herramientas/resultados_harness_*.json` pero que aquí
  colaron por vivir en la raíz en vez de esa carpeta.

**Deliberadamente NO tocado en esta ronda, con motivo**: `docs/plans/failed/`
(evidencia histórica real, dos de sus casos —armas primitivas v2, madriguera
física A— ya citados en la Bitácora completa de este documento como ejemplos
concretos de auditoría tras disyuntor de 3 intentos); `docs/superpowers/specs/`
(52 ficheros — son el entregable real de diseño de cada pieza, no un residuo).

**`docs/plans/in_review/` reclasificado el 2026-09-17** (los mismos 14
ficheros de arriba): verificado pieza por pieza contra su historial
correspondiente, no en bloque — las piezas de flora (`flora-01` a
`flora-05`, `fix-flora-sobre-agua`, `propagacion-03-caida-dispatch`,
`propagacion-05-zoocoria`) confirman en `docs/historial_flora_mundo.md`;
las de hilo individual (`cimiento-relaciones`, `amistad-convivencia`,
`afinidad-concepcion`, `nombre-propio`, `pareja-estable`) confirman en
`docs/historial_hilo_individual.md`; `parejas-fundadoras` confirma en
`docs/historial_estabilidad_poblacion.md`. Las 14 estaban implementadas
de verdad, solo les faltaba el movimiento `in_review→done` que el propio
pipeline debía hacer y nunca hizo — movidas a `docs/plans/done/`,
carpeta `in_review/` ahora vacía.

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
- `docs/historial_servidor_control.md` — renombrado `BOSQUE_*→SIMULACION_*`
  y el servidor de control remoto (arranque/pausa/velocidad por web),
  ambos del 2026-09-16, movidos aquí el 2026-09-17 en la segunda poda de
  este documento (ver más abajo).

## Estado actual y pendientes reales (actualizado 2026-09-17)

Lista corta de lo que sigue genuinamente abierto hoy — para el detalle de
cómo se llegó a cada punto, abre el historial correspondiente de arriba.

**Podada esta sección el 2026-09-17** (venía de las ~465 líneas leídas
arriba en versiones anteriores de este documento, mezclando pendientes
genuinos con crónica detallada de piezas ya cerradas — el mismo patrón
que ya obligó a podar la Bitácora completa el 2026-09-15, esta vez
dentro de la propia sección de pendientes). Todo el contenido cerrado que
había aquí ya vivía duplicado, con más detalle, en
`docs/historial_construccion_social.md` y `docs/historial_capa_visual.md`
(verificado antes de recortar, no asumido); lo que no tenía hogar
todavía (renombrado `BOSQUE_*→SIMULACION_*`, servidor de control remoto)
se migró a `docs/historial_servidor_control.md`, nuevo. Nada se perdió.

- **El criterio maestro de Diego (5 especies vivas a la vez, ≥50% de las
  semillas) sigue sin remedirse de forma agregada**, ni el harness de
  referencia completo (15 semillas × 12000 ticks sin cortar por límite
  de tiempo) se ha corrido nunca de principio a fin — cada medición del
  proyecto hasta hoy usó ventanas truncadas. Desde la última medición
  agregada (15×7 especies, 2026-09-12: 0-7%, muy por debajo del
  objetivo) se aplicaron varias mejoras reales (radio de caza en
  solitario, orillas vadeables, tasa de consumo por especie, especie
  zorro, arco de comodidad) pero ninguna se ha vuelto a medir contra el
  criterio agregado — sigue siendo el pendiente más urgente del
  proyecto, antes de calibrar nada más a ciegas.
- Sesgo de vocación hacia forrajero (`docs/historial_estabilidad_poblacion.md`):
  confirmado real y estructural, no un bug — queda como decisión de
  diseño pendiente de Diego, no una calibración numérica.
- Arco "asentamiento como entidad propia" (`docs/historial_construccion_social.md`,
  6 piezas cerradas a esta fecha): taller/mobiliario sigue en **0
  muebles fabricados** en todas las semillas probadas pese a que el
  resto de la cadena comunal (almacén, salón común, cocina) sí se
  ejerce con fuerza — su propio gate no gana el argmax a tiempo; el
  gate de cocina (excedente de solo saciedad) sigue PROVISIONAL, sin
  eje mejor identificado; interacción entre asentamientos (Pieza 4 del
  roadmap unificado) sigue sin empezar.
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
  real más allá de un `SIMULACION_AUTO_TICKS` de humo.
- El ciclo minería/tala (fabricar herramienta → extraer veta/talar
  árbol) ya se cierra de verdad en juego libre desde el fix de
  "Vía 1 requiere motivo real" (2026-09-12), pero sin medir su
  frecuencia real a escala de población.
- **Centinela del pipeline sigue parado** desde el incidente de
  cancelación de "madriguera-física-A" (2026-09-07) — necesita reinicio
  manual en la máquina de Diego. Este entorno de sesión en la nube no
  tiene `OPENROUTER_API_KEY` ni `mini-swe-agent` instalados, así que
  toda la funcionalidad de las últimas sesiones se implementó
  directamente por Claude (excepción ya prevista, ver "Flujo de
  implementación" arriba).
- **Ciudad enana**: aparcada explícitamente por Diego hasta que se
  plantee la raza enana — no retomar el tema hasta entonces.
- Capa visual (`docs/historial_capa_visual.md`, único sistema visual
  desde la retirada del Códice Cartográfico el 2026-09-16, ahora híbrido
  ASCII+sprite): confirmación visual de Diego sobre la elección concreta
  de glifos/colores sigue pendiente (primera propuesta razonada, no
  calibración cerrada); catálogo de eventos filtrable (panel
  "EVENTOS://LOG") sigue con el placeholder de siempre; liquen y musgo
  siguen sin sprite (únicas 2 especies de flora sin icono aportado);
  `FACTOR_TAMANO_ARBUSTO=0.72` sigue PROVISIONAL; z-index sin transición
  al cruzar de fila mientras se camina, aceptado como límite conocido de
  Y-sorting simple. **El `@font-face` de VGA437
  (`fonts/Web437_IBM_VGA_9x16.woff`) sigue devolviendo 404 real al
  servirse vía `ServidorWeb`** — verificado de nuevo el 2026-09-17,
  `ManejadorWeb` sigue sin ninguna ruta `/fonts/*` (solo tiene
  `/sprites_criaturas/`, `/sprites_construcciones/`, `/sprites_flora/`);
  fix trivial, mismo patrón que las rutas de sprites, no aplicado. La
  leyenda desplegable tampoco se actualizó: para fauna/construcciones/
  flora con sprite real sigue mostrando el glifo/emoji de respaldo del
  catálogo en vez de una miniatura del sprite.
- Servidor de control remoto (`docs/historial_servidor_control.md`):
  Diego no lo ha desplegado en ninguna máquina remota todavía, solo
  verificado en local — sigue sin probarse el caso de uso real que lo
  motivó. Sin autenticación ni TLS (aceptado por ahora, hueco real si se
  comparte la URL).
- Selector de zona real en el visor web: nunca añadido, el visor solo
  dibuja superficie (`zona_idx == 0`).
- Créditos de licencia de los paquetes PyxelSpace: pendiente desde la
  migración original (24-08-2026), nunca resuelto — nota aparte, no
  confundir con el crédito de la fuente VGA437, resuelto el 2026-09-17
  (ver segunda ronda de limpieza más arriba).
- Estructuras multi-celda (muralla, castillo), abuelos/tíos en
  parentesco (bloqueados por la purga de `Identidad` al morir), y
  comodidad como motor general más allá de vivienda (herramienta,
  comida, conexión con ocio→"arte") — visión declarada por Diego, sin
  ningún diseño todavía.
- Todo el catálogo de constantes numéricas nuevas introducidas en las
  últimas sesiones sigue marcado PROVISIONAL en su propio fichero de
  config, sin calibrar contra el harness completo.

## Comentarios técnicos vs narrativa histórica (2026-09-02)

Convención decidida con Diego, vigente para todo el código del
repositorio (no solo al que se toque por otro motivo):

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

Aplicada ya a todo el repositorio el mismo día que se decidió (no solo
a los ficheros que la motivaron) -- crónica completa, incluido el
hallazgo real de que delegarla a `mini-swe-agent` falló 2/2 (tareas de
calibración de juicio/estilo sin criterio de éxito verificable
mecánicamente, ver también ".ai-pipeline/guia-tareas.md"), en
`docs/historial_pipeline_ia.md` (movida ahí el 2026-09-17, era la
última crónica cerrada que quedaba suelta en este documento).

