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
   (hoy, terminal + vista web — Códice Cartográfico, con biblioteca real de
   sprites en `presentacion/assets/` desde 2026-09-04, ver más abajo) es una
   capa desacoplada y sustituible. No acoples la lógica de simulación a cómo
   se presenta.
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
- **Tests automatizados (CORREGIDO 2026-09-04, la cifra "87" ya estaba
  desactualizada)**: `tests/` contiene 23 ficheros / 129 tests reales a
  esta fecha (verificado con `pytest`, no de memoria), escritos como
  "ley física" con docstring explicando el comportamiento que validan
  (mismo criterio declarativo que pide este documento para las reglas
  del motor). La cifra de 87 (fijada 2026-09-03) creció con armas
  primitivas v2, cupo de espacio compartido, catálogo ampliado de flora,
  y esta misma sesión (`test_narrador_genero.py`,
  `test_amenaza_agresividad.py` -- ver más abajo, dos módulos que hasta
  hoy no tenían ningún test dedicado). La cobertura sigue siendo parcial
  (nada del bucle principal, la mayoría de sistemas de comportamiento, ni
  la mayor parte de persistencia). CI/linting sigue sin configurar.

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

## Estado actual y pendientes reales (actualizado 2026-09-15, tras esta poda)

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

