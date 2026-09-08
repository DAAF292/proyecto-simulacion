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

## Límites conocidos y pendientes abiertos a fecha de esta migración (24-08-2026)

- ~~**Sobrepoblación sin techo aparente**~~ (informe técnico, sección 20;
  informe de implementación, 7.52) -- INVESTIGADO Y MITIGADO 2026-08-31,
  ver la sección "Sobrepoblación sin techo aparente -- investigado y
  mitigado con un mecanismo natural de fertilidad por nutrición" más
  abajo (gate de concepción + tamaño de camada por saciedad materna).
  10/14 semillas se comportan razonablemente tras el fix; quedan 2 modos
  de fallo residuales (colapso/extinción, overshoot lento) sin resolver,
  documentados en esa misma sección -- no es "no investigado todavía",
  esta entrada quedó desactualizada sin corregir hasta esta nota
  (2026-09-04).
- Calibraciones explícitamente provisionales sin validar contra el harness
  completo (15 semillas × 12000 ticks): probabilidad de muerte por vejez
  (techo y exponente), probabilidad de muerte por deshidratación, tasas de
  charco efímero, `fraccion_minima_peso_presa` y `peso_referencia_deteccion_plena`
  (viabilidad energética y detectabilidad por tamaño en depredación).
- Búsqueda de pareja (`_buscar_conspecifico_mas_cercano`) es O(N²) sin
  filtrado espacial — aceptable a la escala de población actual, conocido y
  autodocumentado, no corregido.
- Lista completa y consolidada de cuestiones abiertas de diseño (materiales
  físicos, inventario, propiedad de recursos, magia real, enfermedad,
  comunicación entre razas sin idioma común, mejora de atributos en vida,
  manada/asentamiento como concepto genérico, y más): informe técnico,
  sección 20.
- **Capa visual con arte real — historial archivado (24-08-2026 a
  26-08-2026)**: primera exploración completa de arte real para el
  proyecto (PyxelSpace → Urizen → Mini Medieval → retirada del sistema
  de orillas), con hallazgos técnicos genuinos (grid nativo real de cada
  pack, bugs de orientación/tinte, limitaciones de licencia) que merece
  la pena no repetir si el tema se retoma. Movido a
  `docs/historial_capa_visual.md` el 2026-09-02 porque, con 59.000
  caracteres, era el 37% de este documento pese a NO ser ya la
  referencia vigente — superseded por el pivote al Códice Cartográfico
  (ver la Nota de cierre justo debajo). **Pendiente real que ese
  historial contiene y no debe perderse**: falta añadir en algún lugar
  visible del proyecto (informe de visión o README) los créditos de
  nombre+email que exige la licencia comercial de los paquetes de
  PyxelSpace usados en esa exploración.

## Nota de cierre (29-08-2026): toda la narrativa de "Capa visual con arte
## real" de arriba quedó supersedida por un pivote posterior sin documentar aquí

Auditoría completa del código realizada el 29-08-2026 (informe
`informes/informe_funcionalidades_actuales.docx`, tercera edición) encontró
que **toda la sección "Capa visual con arte real" de este documento
(PyxelSpace → Urizen → Mini Medieval → retirada del sistema de orillas,
arriba) describe un estado del visor que ya no es el que corre**. En algún
punto entre el 26-08 y el 28-08 el proyecto pivotó por completo a un
sistema nuevo — el **"Códice Cartográfico"**: canvas de pergamino/acuarela,
generación causal de terreno (cordilleras, escorrentía, clima orográfico —
`nucleo/orografia.py`), sellos de imagen reales estampados por celda o por
cluster de bioma (`presentacion/assets/`, biblioteca curada desde
`nuevosAssetsDefinitivos/`), poses de criatura por estado del ECS
(`criaturas_poses/`), tres modos de mapa (códice/relieve/hidro), cámara
pan/zoom con frustum culling y panel de inspección ECS. Ninguna sesión
documentó este pivote en este archivo ni en la bitácora de implementación
en su momento — se reconstruyó por lectura directa del código
(`presentacion/vista_web.py`, ~2900 líneas) para la auditoría del 29-08.

**No se ha reescrito la narrativa histórica de arriba** (principio de
honestidad: documenta con fidelidad qué se probó y qué se descartó en su
momento, y sigue siendo la referencia correcta para no repetir intentos ya
fallidos de arte plano por celda/orillas por pieza). Pero **para el estado
ACTUAL de la capa de presentación, la fuente correcta es
`informes/informe_funcionalidades_actuales.docx` (tercera edición,
29-08-2026), sección 16**, no esta sección de CLAUDE.md. Esa misma
auditoría también corrigió cuatro hallazgos críticos ya arreglados en
código (commit `500267d`): la cadena `Necesidades.seguridad`/HUIR estaba
completamente muerta (con un crash latente detrás si se activara), las
formaciones macro de desierto/tundra del visor nunca se estampaban pese a
un test en verde, y había un doble-dibujo visual de liquen/musgo. Quedan
abiertos, como decisión de diseño pendiente de hablar con Diego antes de
tocar código (no bugs mecánicos): recalibrar las proporciones de bioma y
la pendiente transitable contra el generador causal actual (ambas
quedaron desfasadas tras el círculo causal del 27-08, sin que nadie las
revisara después), decidir si el clima diario debe afectar al confort
térmico (el código lo declara pero no lo hace), y dar comportamiento
propio a HUIDA_ERRATICA/CRISIS_VIOLENTA en movimiento (hoy indistinguibles
de CATATONIA).

## Interacción física y social: refugio construido, recolección,
## asentamiento (2026-08-30)

Arco de diseño y ejecución completo en una sola sesión, arrancado tras
cerrar el refugio instintivo (memoria individual + sesgo gregario
reutilizado, ver commit `8bc3411`, sin cambios). Diego conectó en un solo
mensaje refugio construido, recolección para mitigar el hambre, el
"problema de la sed" y dónde se ubica un asentamiento — se separó en
conversación antes de tocar código (principio 2: una fuente de
complejidad por incremento), y cada pieza se implementó como su propio
círculo, verificada contra el motor real (no solo arnés dirigido: en
varios casos con `BOSQUE_AUTO_TICKS` sin ninguna intervención manual)
antes de sumar la siguiente. Commits en orden: `97c7945` (Construccion),
`ed145f6` (CONSTRUIR), `ad44a68` (RECOLECTAR), `67c8ed5` (detección de
asentamiento), `d1cfd19` (almacén + aporte), `db3cfcc` (deterioro),
`6e1d49b` (corrección de pertenencia).

**La sed — resuelta solo a medias, decisión explícita de Diego**: entre
portar agua sin recipiente (ficción peor que llevar una manzana a mano,
descartada) y no tocar el transporte de agua todavía, Diego confirmó la
segunda ("b si"). Un gnomo sigue bebiendo in situ como siempre; el acceso
a agua se resuelve por dónde se ubica el asentamiento (cerca de una
fuente), no por inventario. **Sigue sin resolver de verdad**: portar agua
en un recipiente exige fabricar objetos, que no existe — candidato
natural para cuando exista un sistema de fabricación real (mismo
mecanismo base que refugio/almacén, ver más abajo).

**Refugio y almacén como entidades físicas reales** (antes: "refugio" era
solo una coordenada en memoria, sin nada en el mundo). `Construccion`
(`componentes/construccion.py`): `tipo` (string abierto, "refugio" |
"almacen"), `materiales` (dict material→kg, mismo patrón que
Necromasa.masas/Inventario.contenidos/Celda.recursos), `propietario_id`
(entidad_id del gnomo para refugio, `None` para almacén — un almacén es
del asentamiento, no de un individuo), `progreso` ([0,1], fluctúa),
`completado_alguna_vez` (permanente, ver corrección más abajo). Mismo
molde ECS que Necromasa: `Posicion` + un componente de datos, sin
Identidad ni Intencion propias, sin fila en `entidades` (persistida en su
propia tabla `construccion_estado`, igual que `necromasa_estado`).
`config/materiales.yaml` gana `apto_construccion` por material (piedra,
arcilla, tierra, madera, fibra, hierba_seca, hierro, cobre sí; arena,
hueso, tejido_blando no) y una sección `construccion:` con
`masa_minima_refugio` (15.0 kg) / `masa_minima_almacen` (60.0 kg) — sin
receta fija por material, cualquier combinación de materiales aptos que
sume el umbral sirve (emergente de qué recolectó cada gnomo, no un
guion).

**Accion.CONSTRUIR / Accion.RECOLECTAR**, exclusivas de quien supera
`decision.umbral_consciencia_agencia` (gnomo hoy, mismo umbral que ya
exime del sesgo de territorio — construir es agencia consciente, no
instinto). RECOLECTAR convierte `Celda.tipo_sustrato` de la celda actual
(piedra/arcilla/tierra — propiedad estática, siempre presente, NO
depletable) en material de `Inventario`, topado por la capacidad de carga
(`nucleo/inventario.py`, ligada al peso propio). **Deliberadamente
limitado a sustrato**: madera/fibra/hierba_seca son depósitos que
exigirían un sistema de tala/siega de flora que no existe — hueco
honesto, el propio ejemplo de Diego ("techo de paja") queda fuera hasta
que se construya esa pieza. CONSTRUIR transfiere del `Inventario` a la
`Construccion` objetivo (`sistema_recursos.py:_resolver_construir`) al
llegar a su celda; al cruzar `progreso=1.0` registra memoria "refugio"
(reutiliza `nucleo/memoria.py` sin cambios, la memoria apunta al SITIO no
a la entidad — confirmado explícitamente por Diego) y emite un Evento
(NOTABLE para refugio, HISTÓRICO para almacén).

Utilidades gateadas (`sistema_decision.py`): RECOLECTAR con prioridad
mayor que CONSTRUIR mientras falte material y quede espacio en
Inventario (mejor completar la carga que ir y volver por poco); en
cuanto basta o se llena, cae a 0 y CONSTRUIR toma el relevo. El refugio
propio SIEMPRE tiene prioridad sobre el almacén comunal mientras no esté
terminado (necesidad individual antes que comunal, mismo Maslow que rige
el resto del motor) — `nucleo/construccion.py:objetivo_construccion_actual`
es el punto único que decide el objetivo vigente, usado igual por
decisión, movimiento y recursos.

Dos bugs reales encontrados por el propio arnés de verificación, no al
escribir el código (mismo patrón que el resto del proyecto: "esto parecía
correcto sobre el papel"):
1. El compromiso de CONSTRUIR no comprobaba si quedaba material en
   Inventario — un gnomo que lo vaciaba se quedaba encallado en CONSTRUIR
   para siempre sin volver a RECOLECTAR. Corregido: se libera en cuanto
   no hay nada más que aportar.
2. (Ver más abajo, almacén) el compromiso tampoco re-verificaba
   disposición a aportar en cada tick, solo al elegir la acción.

**Verificado con el motor real sin intervención** (`BOSQUE_AUTO_TICKS`,
sin sembrar ningún inventario a mano): 2000 ticks → 18 refugios
iniciados espontáneamente por la Utility AI, 13 terminados.

**Asentamiento — "el germen de un asentamiento"** (`nucleo/asentamiento.py`,
`sistemas/sistema_asentamiento.py`, cadencia diaria). NO es una entidad
nueva de propiedad compartida — cada refugio sigue siendo del gnomo que
lo construyó; el asentamiento es el CLÚSTER que emerge cuando el sesgo
gregario ya existente agrupa varios refugios cerca (resolución explícita
de Diego: "cada gnomo construye su propio refugio primitivo, el instinto
gregario les lleva a construir unos cerca de otros. ese conjunto de
refugios es el germen de un asentamiento"). `mundo.asentamientos`:
recalculado ÍNTEGRO cada día a partir de Construccion+Temperamento, sin
identidad persistida entre días, NO guardado en SQLite (100% derivable,
mismo criterio que `pendiente_local`). Agrupación por proximidad Manhattan
(`agrupar_por_proximidad`, BFS por distancia — NO el mismo algoritmo que
`_componentes_conexas` de vetas minerales, que es flood-fill de grid
contiguo; aquí los puntos pueden estar varias celdas separados).

**Liderazgo, "no creamos leyes absolutas" (Diego)**: `Temperamento.dominancia`
decide quién es candidato (el propio componente ya documentaba desde hace
tiempo que esperaba justo este cálculo — cero atributo nuevo). Agresividad
y cohesión social (empatía+lealtad) de esos candidatos, moduladas por el
tamaño del grupo, deciden si se impone un líder único o se reparte el
poder en consejo — individuos dominantes y agresivos no ceden autoridad,
individuos con más cohesión social sí. Verificado en el motor real (4000
ticks): 3 asentamientos fundados espontáneamente, uno con líder único,
otro con consejo de 2 sobre 5 miembros.

**Almacén comunal y aporte por carácter**: `Construccion` tipo "almacen"
(propietario_id=None), creada en el CENTRO del asentamiento (hay que
llegar hasta ahí, no donde a cada gnomo le pille). Aportar exige
disposición propia — excedente de saciedad/hidratación por encima de un
umbral de carácter (`nucleo/asentamiento.py:disposicion_a_aportar`):
empatía+lealtad lo bajan, agresividad lo sube. **Dominancia queda fuera a
propósito** — conversación con Diego: "¿un ser dominante y agresivo
aportaría lo mismo que uno que no lo sea?... creo que es la agresividad,
porque puedes ser un líder dominante y empático que aporte". Bug 2 de
arriba: sin re-verificar disposición cada tick, un individuo
fundamentalmente egoísta podía "engancharse" tras un pico momentáneo de
saciedad y terminar el almacén él solo — corregido y verificado con dos
casos de control (población prosocial con excedente real completa el
almacén; población egoísta con excedente clavado por debajo del umbral,
simulando metabolismo real, no completa nada). Motor real (4000 ticks): 2
de 3 asentamientos con su almacén ya terminado.

**Deterioro — dos capas, la tercera aplazada a propósito**. "Nada dura
para siempre" (Diego). Capa 1, decomposición pasiva
(`sistema_descomposicion.py:_descomponer_construcciones`, cadencia
diaria): cada material a su propia `tasa_descomposicion_dia` del
catálogo, SIN el fallback de 0.08 que usa Necromasa — piedra/arcilla/
tierra/hierro/cobre no decaen (geológicamente estables, correcto),
madera/fibra/hierba_seca sí. Capa 2, fuego (`sistema_desastres.py`,
extensión de `procesar_fuego_tick`): consumo proporcional a
`combustibilidad` del material, mismo ritmo que ya usa el daño a
criaturas. Capa 3 (clima normal, uso continuado) deliberadamente fuera —
señalada, no resuelta, para no acumular tres fuentes de degradación sin
poder aislar el efecto de ninguna. Verificado: refugio de madera colapsa
en ~568 días de partida, piedra intacta tras 900; hierba_seca ardiendo
colapsa en ~59 ticks, piedra en la misma llama intacta. Motor real (4000
ticks): 0 colapsos — correcto, la partida real solo ha recolectado
arcilla hasta ahora.

**Corrección de diseño, Diego (30-08, tras ver el hallazgo de
calibración del deterioro)**: "no debería salir del asentamiento a la
mínima degradación, una casa dañada sigue perteneciendo a un pueblo. y
por otro lado la degradación inmediata no tiene mucho sentido". El
diagnóstico correcto no era la velocidad de la degradación (1%/día es
lenta) sino que `SistemaAsentamiento` filtraba pertenencia por
`progreso>=1.0` EXACTO — un umbral que la propia degradación rompía al
segundo día. Pertenencia social ("¿llegó a ser una casa de verdad?") y
estado de mantenimiento ("¿hace falta trabajo aquí ahora?") eran la misma
pregunta sin necesidad. Separadas con `completado_alguna_vez` (permanente
desde la primera vez que `progreso` toca 1.0, solo vuelve a `False` si la
entidad colapsa del todo): `SistemaAsentamiento` usa
`completado_alguna_vez` para pertenencia, `objetivo_construccion_actual`
sigue usando `progreso` (fluctuante) para decidir si hace falta aportar
más. Verificado: un refugio que decae de 1.0 a 0.99 tras un día sigue
contando como miembro en el recálculo siguiente.

**CORRECCIÓN 2026-08-31 -- lo siguiente quedó IMPLEMENTADO el mismo día
31-08 (commit `2640a82`, antes de la auditoría de coherencia de más
abajo) y esta nota de "pendiente" nunca se actualizó para reflejarlo --
hallazgo propio al releer esta sección antes de re-implementar algo que
ya existía. Ver la nueva sección dedicada más abajo, "Conflicto por
refugio ocupado", para el estado real (implementado, verificado dos
veces, config todavía provisional).**

**Pendiente, señalado explícitamente, ninguno implementado todavía**:
- ~~**Conflicto por refugio ocupado / resolutor genérico de disputas**
  (`nucleo/conflicto.py`, no creado). Diseñado en conversación completa
  con Diego pero sin una sola línea de código: `indice_asertividad_social`
  (dominancia+agresividad+valentía+urgencia) comparado bilateralmente
  entre dos individuos — CEDE/COMPARTE/ENFRENTAMIENTO según pertenezcan o
  no al mismo asentamiento. Explícitamente generalizado más allá del
  refugio ("esto debe ser reutilizable a futuro... que un individuo robe
  a otro, un agravio del tipo que sea") — el refugio ocupado sería solo su
  primer consumidor, robo/agravio quedan como consumidores futuros del
  mismo resolutor sin lógica nueva.~~ Memoria de agravios entre individuos
  con nombre propio (rencor persistente) explícitamente fuera de esto —
  conecta con lo que `Temperamento.empatia`/`lealtad` ya señalan como
  pendiente ("esperan vínculos personales con nombre propio").
- **Recolección de madera/fibra/hierba_seca** — bloqueada por la
  ausencia de un sistema de tala/siega de flora que deposite el material
  real en el mundo. Sin esto, ningún refugio puede tener de verdad "un
  techo de paja" (el ejemplo original de Diego).
- **Transporte de agua** — sigue sin resolver, esperando un sistema de
  fabricación de objetos (ver "la sed" arriba).
- **Calibración numérica, todo provisional**: `masa_minima_refugio/
  almacen`, `tasa_aporte_construccion_kg_tick`, `tasa_recoleccion_kg_tick`,
  `utilidad_construir_base`/`utilidad_recolectar_base`,
  `poblacion_minima_asentamiento`, `radio_cluster_celdas`,
  `margen_dominancia_elite`, `umbral_cohesion_consejo`,
  `excedente_base_para_aportar` y sus modificadores — ninguno calibrado
  contra el harness completo (15 semillas × 12000 ticks), solo contra
  arneses dirigidos y partidas de 2000-4000 ticks sin intervención.

## Profundidad geológica — Círculo 1 (mecanismo multi-zona), 2026-08-30

Arranca de un informe externo que Diego trajo para valorar ("Propuesta
Técnica: Expansión de Profundidad y Reforma del Sistema de Visualización"),
diagnosticando que el mapa es "solo una cuadrícula sin opción de
profundidad". Analizado contrastando cada afirmación contra el código real
(no contra la lectura del propio informe) antes de opinar — encontró varios
problemas serios que se le señalaron explícitamente a Diego antes de tocar
nada:

- **La pregunta de fondo ya se había planteado y respondido ESE MISMO DÍA**:
  `nucleo/celda.py:deposito_mineral` (círculo de materiales físicos, más
  arriba en este documento) documenta textualmente la pregunta de Diego
  ("cuál es la profundidad del suelo? ahora es una celda, pero hacia dónde
  va eso?") y la decisión tomada entonces — mantener la abstracción plana
  deliberadamente, aparcando el eje de profundidad como "decisión de
  arquitectura aparte, no resuelta ni asumida aquí". El informe presentaba
  como hallazgo nuevo algo ya detectado y aparcado con el mismo diagnóstico.
- **Afirmaciones factuales desactualizadas o inventadas contra el HEAD
  real**: citaba un umbral de zoom "1.6" cambiado a 1.0 dos días antes
  (`vista_web.py`, comentario propio del código: "(2026-08-28) 1.6 -> 1.0");
  describía "Modo Códice vs Modo Inmersivo" cuando el visor real tiene TRES
  modos (códice/relieve/hidro) más un pivote de estilo tinta/color
  ortogonal a esos modos; describía el y-sort de criaturas como "efecto
  pegatina" y "disonancia estética insalvable" cuando el propio test se
  autodescribe como "oclusión real" (`criaturas_ysort.test.mjs`); proponía
  usar `CapacidadMental.consciencia` como radio de niebla de guerra cuando
  su propio docstring dice explícitamente "sin ninguna lógica de gating
  implementada todavía... nada la consume" y su propósito real y
  documentado es gating de facultades mentales superiores, no percepción
  espacial — reutilizar el nombre de un campo real con una semántica que no
  es la suya.
- **Violaba el principio 2 de fondo**: proponía en un único documento
  refactor de ECS (`Posicion`+`percepcion`+`disposicion`) + generación de
  portales + reforma completa de renderizado (LOD, niebla de guerra, panel
  de rayos X) + migración de esquema SQLite, todo junto, sin secuenciar.
- **Colisión de vocabulario evitable**: `zona_id` para "nivel subterráneo"
  cuando "Zona de bioma" ya significa algo distinto y establecido en la
  jerarquía Mundo → Territorio → Zona de bioma → Celda.

Con esa crítica por delante, Diego confirmó que la necesidad de fondo es
real: "hace falta minería vertical, es parte de la riqueza de nuestro
mundo, animales fantásticos que habitan el subsuelo, grandes ciudades
enanas subterráneas, cuevas con monstruos, minas" — no un simple almacén de
recursos, un marco nuevo de verdad para el mundo.

**Reencuadre importante, en conversación**: frente a las dos opciones ya
sobre la mesa (nodo único tipo Necromasa, o réplica completa del grid
mundial como en el informe original), Diego pidió tratar el subsuelo como
**zona de bioma real** — geografía, físicas, flora y fauna propias.
Verificado contra el código que esto encaja MEJOR con "reutiliza antes de
inventar" que cualquiera de las otras dos: `nucleo/territorio.py` ya
declaraba `self.zonas` como lista desde el 23-08, explícitamente "el día
que un territorio contenga varias zonas, este mismo atributo crece". El
subsuelo es, literalmente, `zonas[1]` — el punto de extensión ya estaba
sembrado, once días antes de que hiciera falta.

Dos decisiones cerradas con Diego (pregunta directa) antes de escribir
código:
1. **Modelo espacial: bolsas dispersas**, no réplica completa del grid — el
   subsuelo nace donde hay algo que simular (anclado a celdas de montaña
   con depósito mineral), no como un segundo plano continuo del tamaño del
   mundo. Evita duplicar la carga de un motor que ya arrastra sobrepoblación
   sin techo investigado en superficie (límite conocido, migración 24-08).
2. **"Ciudades enanas" = el gnomo ya existente**, no una raza nueva —
   reutiliza el sistema de asentamiento/construcción de hoy mismo (ver
   arriba) en vez de diseñar una raza desde cero antes de poder empezar.

### Círculo 1 — implementado y verificado (commit `f79274e`)

Objetivo único, deliberadamente acotado: demostrar que el mecanismo
multi-zona funciona de punta a punta (movimiento, persistencia, aislamiento
de percepción), sin contenido nuevo todavía — ni geometría interior real de
cueva, ni minería, ni fauna/flora subterránea, ni ciudades enanas.

- `componentes/posicion.py`: `Posicion` gana `zona_idx: int = 0` — índice en
  `Territorio.zonas`, reutiliza el contenedor ya existente en vez de
  inventar un término que colisione con "Zona de bioma". Toda entidad
  existente queda en superficie sin tocar nada.
- `nucleo/territorio.py`: genera una segunda zona de PRUEBA (`zonas[1]`,
  12×12, mismo `generar_zona_bioma` que la superficie — sin bioma/flora/
  fauna propios todavía, eso es círculo posterior) anclada bajo
  `acceso_subterraneo`, la celda de montaña con `deposito_mineral` no vacío
  más determinista disponible (sin agua ni fuego — las dos salvaguardas del
  informe original que sí eran correctas por sí mismas). `entrada_cueva` es
  el centro de esa zona.
- **Mecanismo de portal, no una Accion nueva de la Utility AI**
  (`sistema_movimiento.py:_aplicar_movimiento`): pisar la celda de acceso
  cruza de zona, igual que una escalera de Dwarf Fortress — un rasgo físico
  del terreno, no una decisión consciente que ninguna especie necesite
  "elegir" (leyes neutras, principio 5). Evita inventar una curva de
  utilidad nueva sin calibrar solo para esto.
- **Aislamiento**: se auditaron y corrigieron todos los puntos del motor
  que comparaban entidades por `(x,y)` sin noción de zona —
  `nucleo/disposicion.py` (las tres funciones de búsqueda por disposición),
  `nucleo/amenaza.py`, varias búsquedas internas de `sistema_movimiento.py`
  (huida, caza, pareja, conspecífico más cercano, carroñeo),
  `sistema_depredacion.py` (la clave de agrupación por celda),
  `sistema_reproduccion.py` (contacto para concepción), y — encontrado
  durante la verificación, no antes de escribir código —
  `sistema_capacidad_mental.py` ("presenciar una muerte" comparaba
  posiciones de fallecimiento sin zona, así que una muerte en la cueva
  podía traumatizar a un vecino de superficie con el mismo `(x,y)`
  numérico). Las cuatro emisiones de evento `"Muerte"`
  (`sistema_necesidades.py`, `sistema_ciclo_vital.py`,
  `sistema_depredacion.py`, y la de `sistema_desastres.py` que YA carecía
  de `x,y` desde antes — gap preexistente, no corregido aquí, fuera de
  alcance) ahora llevan `zona_idx` en `datos`.
- **Sistemas de ciclo diario multi-zona**: `sistema_clima.py`,
  `sistema_desastres.py` (ignición y propagación) y `sistema_flora.py`
  procesan ahora todas las zonas del territorio, no solo `zonas[0]`.
  `sistema_descomposicion.py` calcula el factor de humedad por zona (cada
  `ZonaBioma` tiene su propio `clima_actual`) y lo aplica según la zona real
  de cada Necromasa.
- **Persistencia**: `celdas_estado`, `componentes_estado`, `plantas_estado`,
  `necromasa_estado` y `construccion_estado` guardan `zona_idx` (esquema
  `0.27-fase0`, DROP-and-recreate según el criterio ya establecido — sin
  migración de datos, fase sin campañas reales que conservar).

**Verificado contra el motor real, no solo contra la lectura del código**:
los 22 tests existentes siguen en verde; arnés dirigido (portal en ambos
sentidos, aislamiento de percepción/disposición con coordenadas
numéricamente coincidentes entre zonas, roundtrip completo de guardado/
carga con entidades y celdas en ambas zonas); **3000 ticks completos de
`BOSQUE_AUTO_TICKS` sin ninguna excepción**, más 300 ticks del pipeline
completo (los nueve sistemas: decisión → movimiento → desastres →
depredación → recursos → necesidades → capacidad física → capacidad mental
→ reproducción) con un gnomo y un lobo viviendo de verdad dentro de
`zona_idx=1`, no solo cruzando el portal una vez.

**Hueco encontrado y señalado, deliberadamente NO corregido en este
círculo** (mismo criterio de honestidad que el resto del proyecto):
`nucleo/asentamiento.py:almacen_cercano`/`agrupar_por_proximidad`
(clustering de asentamiento) siguen sin filtrar por `zona_idx` — un almacén
en la cueva y otro en superficie con coordenadas numéricamente cercanas
podrían confundirse. Inofensivo hoy porque ningún gnomo construye bajo
tierra todavía (nadie llega a recorrer ese camino); es lo primero a
corregir cuando se aborde el Círculo 4 (ciudades enanas), no antes.

### Qué sigue — círculos siguientes, ninguno arrancado todavía

1. **Geometría interior real de la cueva** + acción de extracción minera
   real (`deposito_mineral`/`tipo_sustrato` desde dentro) — hoy la zona de
   prueba es un placeholder sin relación con "cueva" salvo el mecanismo de
   acceso.
2. **Fauna subterránea** ("animales fantásticos", monstruos) como catálogo
   nuevo de especies, reutilizando rango racial + sorteo individual — nada
   de mecanismo nuevo que inventar.
3. **"Ciudad enana"**: extender `SistemaAsentamiento`/`Construccion` (ya
   existen, ya hacen clustering + liderazgo + almacén) para que funcionen
   dentro de una cueva — primer paso real: corregir el hueco de
   `almacen_cercano` señalado arriba.
4. **Presentación** (`presentacion/vista_web.py`) — deliberadamente sin
   tocar todavía, ni un selector de nivel ni ninguna estética de cueva.
   Motor primero.

Ninguna decisión sobre "físicas distintas" (¿sin clima?, ¿modelo de luz/
oscuridad?, ¿temperatura desacoplada?) está tomada — explícitamente abierta
para cuando se llegue al círculo correspondiente, no asumida aquí.

### Círculo 2 — geometría real de la cueva + extracción minera real (2026-08-30)

Dos decisiones cerradas con Diego (pregunta directa) antes de escribir
código, igual que en el Círculo 1:

1. **Vetas finitas**: `deposito_mineral` deja de ser una abstracción
   infinita como `tipo_sustrato` — cada celda de veta nace con
   `masa_mineral_restante` (kg) y se agota de verdad al extraerla.
   Consecuencia directa no anticipada al principio: `deposito_mineral`/
   `masa_mineral_restante` dejan de ser puramente derivables de la
   semilla (como decía el docstring original) y pasan a ser estado
   mutable de la partida — **ahora SÍ se persisten** (`celdas_estado`,
   esquema `0.28-fase0`).
2. **Geometría por autómata celular**, no habitaciones+pasillos: relleno
   aleatorio de pared/hueco + suavizado iterativo por mayoría de vecinos
   (el método estándar de generación procedimental de cavernas orgánicas).

**Implementado**:
- `nucleo/cueva.py` (nuevo): `generar_geometria_cueva` hace el autómata
  celular (parámetros en `config/cueva.yaml`, ninguno calibrado, la
  parametrización estándar documentada del algoritmo) y garantiza que la
  entrada sea caminable y pertenezca a la única componente conexa de
  suelo — se fuerza un radio de hueco alrededor de la entrada ANTES de
  calcular componentes conexas, y cualquier cavidad aislada del resto
  (inevitable con autómata celular puro) se vuelve pared. `generar_zona_cueva`
  construye la `ZonaBioma` completa: suelo caminable con vetas minerales
  sembradas (reutiliza `nucleo/materiales.py:generar_vetas_minerales` tal
  cual, sin cambios), paredes impasables.
- **Paredes sin campo nuevo en `Celda`**: en vez de un booleano
  `transitable` (que habría exigido tocar movimiento, visor y cualquier
  búsqueda de celda vecina), una pared es una celda con `elevacion=1.0`
  frente a `elevacion=0.1` del suelo — reutiliza el mecanismo YA
  existente de `nucleo/relieve.py:pendiente_maxima_transitable` (tope
  real calibrado ~0.21), que ya bloqueaba un paso cuya diferencia de
  elevación superase lo que la fuerza del individuo permite. Ninguna
  criatura, por fuerte que sea, puede escalar una pared.
- **Vetas en el suelo, no en las paredes**: minar la pared en sí (que la
  extracción abra un túnel nuevo, mutando la geometría en plena partida)
  se descartó a propósito por ser una fuente de complejidad aparte
  (recalcular conectividad/pathing cada vez que se agota una veta) — el
  suelo caminable es la única superficie minable, mismo criterio que ya
  usa la superficie (las vetas de montaña ya viven en celdas caminables,
  no en un concepto de "pared" que la superficie ni siquiera tiene).
- `nucleo/materiales.py:_componentes_conexas` promovida a pública
  (`componentes_conexas`) — reutilizada por `nucleo/cueva.py` para el
  mismo flood-fill de 4-vecindad, sin duplicar el algoritmo.
- `sistemas/sistema_recursos.py:_resolver_recolectar` extendida: si la
  celda actual tiene `deposito_mineral` con masa restante, se extrae eso
  en vez de `tipo_sustrato`, decrementando la masa y limpiando
  `deposito_mineral` a `""` al agotarse. **Cero cambios en
  `sistema_decision.py`**: `Accion.RECOLECTAR` ya gateaba genéricamente
  por "masa apta de construcción pendiente" y hierro/cobre ya eran
  `apto_construccion: true` en el catálogo — para la Utility AI, extraer
  mineral o sustrato es indistinguible, solo cambia qué clave del
  Inventario crece. Esto también significa que la minería de superficie
  (vetas de montaña, ya existentes desde el Círculo de materiales
  físicos) queda extraíble por el mismo camino, sin pieza aparte.
- `config/materiales.yaml`: `masa_inicial_por_celda_veta_kg` (PROVISIONAL
  =40.0, sin calibrar) en `generacion_vetas` — una veta típica de 4
  celdas suma ~160kg extraíbles, del mismo orden de magnitud que
  `masa_minima_almacen` (60kg).

**Verificado contra el motor real**: geometría comprobada en 5 semillas
distintas (entrada siempre caminable, suelo siempre una única componente
conexa, proporción pared/suelo en un rango razonable — ni sala vacía ni
bloque sólido); extracción real de una veta hasta agotarla por completo
(40kg en 40 ticks a la tasa configurada, con descargas de inventario
intermedias porque la capacidad de carga es real y menor que una veta
entera — igual que ya pasa con `tipo_sustrato`); roundtrip de persistencia
con una veta parcialmente y totalmente agotada; **500 ticks del pipeline
completo con un gnomo colocado a mano sobre una veta en `zona_idx=1`, sin
ninguna excepción**; 3000 ticks de `BOSQUE_AUTO_TICKS` sin intervención
(verificado que `masa_mineral_restante` se inicializa y persiste
correctamente en ambas zonas); los 22 tests existentes siguen en verde.

**Deliberadamente fuera de este círculo, sin resolver**: "físicas
distintas" bajo tierra sigue exactamente igual de abierto que tras el
Círculo 1 (la cueva no tiene clima propio, hereda el sorteo diario
genérico); excavar un túnel de verdad (mutar una pared a suelo al agotar
su veta) no existe; ningún consumo de tala/siega de madera-fibra-
hierba_seca (hueco ya señalado en el Círculo de interacción física,
sigue igual). **La única zona de prueba de 12×12 y su anclaje exclusivo a
montaña, descritos aquí originalmente, quedaron superados por el Círculo
3 el mismo día — ver más abajo.**

### Círculo 3 — varias cuevas, tamaño variable, sin bioma ni propósito
### asignado (2026-08-30)

Corrección de diseño de Diego, el mismo día, al ver el Círculo 2
funcionando: preguntó "¿las cuevas son todas del mismo tamaño? podría
haber cuevas superficiales que usen los lobos para habitar y grandes
galerías naturales con su propio bioma". Primera respuesta propuesta
(dos categorías discretas — "madriguera" pequeña vs. "galería" grande,
cada una con su propia regla de acceso por bioma/propósito) **rechazada
por Diego, con razón, por violar el principio 5 (leyes neutras)**: "las
cuevas no deberían aparecer solo en un bioma, son formaciones naturales
que no siguen esas normas... para que se use la cueva no es algo que
debamos definir nosotros, si un lobo está buscando refugio y encuentra
un acceso no se tiene que plantear si puede entrar ahí porque es grande
o pequeña". Autoría de guion disfrazada de categoría de generación —
exactamente el patrón que este documento pide vigilar.

**Rediseño aceptado**: cuevas como fenómeno geológico puro, desacoplado
del clima de superficie —

- `nucleo/territorio.py:AccesoSubterraneo` (nuevo dataclass): generaliza
  el par único `acceso_subterraneo`/`entrada_cueva` del Círculo 1-2 (ya
  retirado) a `Territorio.accesos_subterraneos: list[AccesoSubterraneo]`
  — una entrada por cueva generada.
- **Acceso en cualquier bioma**: `_candidatos_acceso_subterraneo` ya no
  filtra por `TipoTerreno.MONTANA` ni prefiere celdas con depósito
  mineral (ese anclaje "hay mina donde hay acceso" era un vestigio del
  diseño de una única cueva — ya no tiene sentido cuando cada cueva
  genera sus propias vetas en su propio interior, con independencia de
  qué haya en superficie). Solo se conservan las dos salvaguardas
  físicas reales: sin agua, sin fuego. Verificado que los accesos caen
  de hecho en los cinco biomas (bosque, pradera, desierto, montaña,
  tundra), no solo montaña.
- **Tamaño continuo, sin categorías**: cada cueva sortea su propio ancho
  y alto (por separado, no forzado a cuadrado) dentro de un rango
  (`ancho_min/max_celdas`, `alto_min/max_celdas`, PROVISIONAL 6–22) —
  mismo patrón de "rango racial + sorteo individual" que el motor ya
  reutiliza para atributos de criatura, aplicado aquí a un rasgo
  geográfico en vez de biológico. Sin bifurcación "pequeña"/"grande" en
  el código: quién acaba usando cada cueva emerge de la Utility AI de
  siempre (memoria instintiva de refugio para fauna, RECOLECTAR donde
  haya veta para el gnomo), no de una etiqueta puesta en generación.
- **Varias cuevas por mundo**: `num_cuevas_min/max` (PROVISIONAL 3–6),
  con `separacion_minima_celdas` (PROVISIONAL 8) entre accesos para que
  el sorteo no las amontone en un rincón del mapa.
- `sistemas/sistema_movimiento.py:_aplicar_movimiento` generalizado:
  busca en la lista de accesos en vez de comparar contra un par fijo —
  búsqueda lineal O(N) sobre un puñado de cuevas, mismo límite de
  escalabilidad ya aceptado en el resto del motor a esta escala.
  `nucleo/cueva.py` no cambió nada de su algoritmo — solo pasó a
  recibir ancho/alto variables en vez de la constante 12.

**Verificado contra el motor real**: 5 semillas — número de cuevas
dentro del rango configurado, separación mínima respetada, cada cueva
caminable y conexa (mismo chequeo del Círculo 2, ahora por cueva), 22
tamaños distintos vistos entre semillas (sin agrupamiento en dos
valores, confirmando que no quedó una categoría discreta oculta),
accesos repartidos en los cinco biomas; el portal generalizado probado
explícitamente con descensos por CADA acceso de una semilla real,
confirmando que cada uno lleva a su propia zona/entrada; aislamiento de
percepción confirmado también entre dos cuevas no-superficie (zona_idx 1
frente a 2, no solo 0 frente a 1 — caso que el Círculo 1 no pudo probar
porque solo existía una cueva); 300 ticks de pipeline completo con
gnomos en cuevas distintas simultáneas sin excepciones; 3000 ticks de
`BOSQUE_AUTO_TICKS`; los 22 tests existentes en verde.

### Corrección — aislamiento de asentamientos por zona (2026-08-30, mismo día)

Diego preguntó, tras cerrar el Círculo 3, "¿hay que afinar algo de aquí?"
— en vez de repetir solo lo ya documentado, se verificó el motor de
verdad en busca de algo concreto. Dos comprobaciones:

- **Vetas en cuevas pequeñas**: la preocupación razonada (una "madriguera"
  de 6×6 podría no generar ninguna veta, dado el redondeo de
  `escala_abundancia_a_fraccion_piedra`) **no se confirmó** al medirla:
  50 semillas, 221 cuevas generadas, 0 sin ninguna veta (mínimo 4 celdas
  de veta incluso en las más pequeñas). Descartada explícitamente en vez
  de "arreglada" sin necesidad — el motor real dijo que no hacía falta.
- **`almacen_cercano`/`agrupar_por_proximidad` sin filtrar por zona**: el
  hueco que el Círculo 1 ya había señalado como "inofensivo hoy" dejó de
  serlo — con varias cuevas por mundo compartiendo rangos de coordenadas
  pequeños (6-22 en vez de los 40×40 de superficie), dos refugios en
  CUEVAS DISTINTAS caen dentro del mismo `radio_cluster_celdas` por pura
  coincidencia numérica con mucha más frecuencia que en superficie.
  Reproducido explícitamente con un arnés dirigido (dos grupos de 3
  gnomos con refugio terminado, mismas coordenadas relativas, en
  `zona_idx=1` y `zona_idx=2`) antes de corregir, no solo razonado.

**Corregido**: `sistema_asentamiento.py` agrupa refugios POR ZONA antes
de llamar a `agrupar_por_proximidad` (que sigue siendo genérica, sin
noción de zona — la partición es responsabilidad de quien la llama, no
de la función geométrica en sí). `Asentamiento` gana `zona_idx` (la de
todos sus miembros, garantizada por esa partición previa). `almacen_cercano`
gana un parámetro `zona_idx` y filtra por él; `nucleo/construccion.py:
objetivo_construccion_actual` lo propaga desde `asen.zona_idx`. Verificado:
el mismo arnés que reproducía la fusión incorrecta ahora detecta dos
asentamientos distintos, uno por zona, sin miembros cruzados; 4000 ticks
de `BOSQUE_AUTO_TICKS` sin excepciones; 22 tests en verde.

**Comprobación adicional, mismo día, tras preguntar Diego otra vez "¿hay
algo más que añadir al tema de las formaciones subterráneas?"**: dos
cosas más verificadas contra el motor real, una confirmada en verde y
otra decidida explícitamente en vez de dejarla en el aire.

- **Roundtrip de persistencia con número de cuevas variable**: no se
  había reprobado explícitamente desde que el Círculo 3 dejó de ser
  "siempre exactamente una cueva" — verificado ahora (mundo con 5
  cuevas, marca de estado distinta en cada una, guardado, mundo
  regenerado desde cero con la misma semilla, cargado): las 5 zonas
  recuperan su estado exacto. Correcto, no hacía falta tocar nada.
- **Desequilibrio de mineral entre superficie y cuevas, medido, NO
  corregido — decisión explícita**: con varias cuevas por mundo, el
  mineral total bajo tierra resultó ser 4-10× el de toda la superficie
  junta (medido en 5 semillas: 240-680kg en superficie frente a
  1400-3840kg repartidos entre las cuevas de ese mismo mundo). Diego,
  consultado, delegó el criterio ("haz lo que consideres que será
  mejor"). Decisión: **dejarlo tal cual, sin ningún parámetro nuevo que
  rebaje la abundancia bajo tierra**. Razonamiento: el número no es un
  accidente sin sentido -- surge de aplicar la MISMA fórmula
  (`escala_abundancia_a_fraccion_piedra`) a más terreno de piedra en
  total (varias cuevas enteras de suelo caminable suman más superficie
  minable que la montaña de la superficie sola), y encaja temáticamente
  con el motivo original de todo este arco ("hace falta minería
  vertical... grandes ciudades enanas... minas" -- concentrar mineral
  bajo tierra es precisamente la razón real por la que se cava).
  Introducir un parámetro nuevo solo para que el número "se sienta más
  equilibrado" sin ningún motivo de diseño detrás habría sido inventar
  una regla para forzar una sensación estética, justo lo que el
  proyecto pide evitar. `masa_inicial_por_celda_veta_kg` y
  `escala_abundancia_a_fraccion_piedra` siguen marcados PROVISIONAL,
  pendientes del harness completo (15 semillas × 12000 ticks) -- este
  hallazgo queda anotado para revisar entonces con datos de partida
  real, no para ajustar a ojo sobre una foto de generación.

### Qué sigue tras el Círculo 3

1. **Fauna subterránea** ("animales fantásticos", monstruos) como
   catálogo nuevo de especies, reutilizando rango racial + sorteo
   individual.
2. **"Ciudad enana"**: extender `SistemaAsentamiento`/`Construccion` para
   que funcionen dentro de una cueva — el aislamiento por zona (arriba)
   ya no es un hueco pendiente, así que este paso puede empezar
   directamente por diseñar cómo es una ciudad enana de verdad, no por
   una corrección previa.
3. **Presentación** (`presentacion/vista_web.py`) — deliberadamente sin
   tocar todavía. Motor primero.

## Auditoría de coherencia tras el merge del sistema de profundidad, y dos
## piezas más del arco de refugio (2026-08-31)

Dos sesiones de Claude Code trabajaron en paralelo el mismo día sobre el
mismo `master` — esta (refugio/recolección/asentamiento/conflicto, arriba)
y otra (profundidad/cuevas, también arriba). Al fusionar de vuelta a la
rama de esta sesión, `git` resolvió solo el conflicto textual; verificar
que la SEMÁNTICA seguía siendo correcta exigió trabajo aparte, ya que
ambas líneas tocaron `nucleo/asentamiento.py`, `nucleo/construccion.py` y
`sistema_movimiento.py`.

**Corrección propia encontrada durante el merge**: `_resolver_posible_intruso`
(conflicto por refugio ocupado) comparaba solo `(x, y)` para decidir "misma
celda" -- con varias zonas ya en el motor, dos entidades en cuevas
DISTINTAS con coordenadas numéricamente coincidentes podían disparar un
conflicto falso. Mismo tipo de hallazgo que el propio Círculo de
profundidad ya se había encontrado a sí mismo con `almacen_cercano`.
Corregido con el mismo patrón (filtrar por `zona_idx`) y verificado
explícitamente el caso negativo (mismas coordenadas, zonas distintas → sin
conflicto) antes de dar el merge por bueno.

**Auditoría de coherencia pedida por Diego** ("¿con qué continuamos?" →
"3", el sistema de profundidad) tras confirmar que la otra sesión ya había
terminado: no solo releer la documentación que dejaron (inusualmente
rigurosa y autocrítica -- capturaron su propia violación del principio 5
cuando Diego les corrigió lo de categorizar cuevas por tamaño/bioma), sino
verificar contra el motor real, mismo criterio de siempre.

**Hallazgo real, no documentado por la otra sesión**: `presentacion/
vista_web.py:construir_instantanea` no filtraba NINGUNA de sus tres
consultas de entidades (criaturas, plantas, necromasa) por `zona_idx`,
pese a que solo dibuja `zonas[0]` (superficie). Esto NO es lo mismo que
"todavía no hay arte de cueva" (omisión ya documentada y aceptada por la
otra sesión) -- es corrupción activa de la vista de superficie en cuanto
algo cruza a una cueva: dos entidades en zonas distintas con las mismas
coordenadas numéricas llegaban al DTO como filas indistinguibles (mismo
`x`, `y`, sin ningún campo que las diferenciara), y una planta de cueva
podía pisar la entrada de una planta de superficie en `plantas_por_celda`
(misma clave `(x,y)`). Reproducido de forma concreta antes de arreglar
(dos gnomos en `(5,5)`, uno en superficie y otro en cueva → el DTO los
devolvía como dos filas idénticas) y verificado a escala real después:
una partida de 800 ticks sin intervención (población fundadora + sistemas
reales, sembrada con una semilla distinta a la de mis propios smoke
tests) terminó con **10 entidades genuinamente bajo tierra** -- confirma
que el fallo se dispara con facilidad en juego normal, no solo en un caso
construido a mano. Arreglado con el filtro mínimo (`pos.zona_idx == 0` en
las tres consultas) -- no una capacidad nueva (selector de zona, arte de
cueva), la corrección para que la vista que YA existe deje de mentir.

Aparte, sin relación con la profundidad, encontrado de paso mientras
comprobaba cifras de población: `entidades.viva` en persistencia nunca se
pone a `False` al morir -- solo se escribe una vez, al crear la entidad
(commit inicial del proyecto, `879f3f7`, nada que ver con esta sesión ni
con la de profundidad). El snapshot en vivo (`componentes_estado`) sí
refleja bien quién sigue vivo; el registro histórico no. Señalado, no
corregido -- fuera de alcance de lo que se estaba auditando.

**Recolección de madera/fibra/hierba_seca, sin tala/siega** (Diego: "los
árboles dejan caer ramas que los gnomos recogen o arrancan hierba
directamente sin mecanismos complejos de tala y siega"). Cierra el hueco
que quedaba señalado desde el Círculo C de RECOLECTAR (limitado a
`tipo_sustrato`) y desde el propio catálogo de materiales ("madera y
fibra... sin consumidor mecánico desde que se escribieron"):

- `sistema_flora.py`: el bucle de producción diaria filtraba
  `categoria != "alimento": continue`, ignorando por completo las
  entradas `categoria: material` ya declaradas bajo manzano/cactus desde
  hacía días. Ampliado a alimento+material -- MISMA fórmula de
  producción (`tasa_regeneracion * eficiencia_total`, mismo
  desbordamiento a mantillo al llenarse) que ya usa la fruta, sin
  ninguna acción de tala/siega que destruya la `Planta`. El chequeo de
  sobreforrajeo (`agotada_hoy`) queda restringido a alimento --
  quedarse sin ramas que recoger no es hambre, no debe hacer retroceder
  la planta a brote.
- `config/flora.yaml`: `madera` (manzano) y `fibra` (cactus) ganan
  `capacidad_maxima`/`tasa_regeneracion` (ya declaradas, sin numérica
  hasta ahora); `hierba_seca` se añade como entrada nueva bajo
  `hierba_silvestre`, categoria material, junto a la ya existente
  "hierba" de alimento. Todo PROVISIONAL, sin calibrar.
- `sistema_recursos.py:_resolver_recolectar`: nueva rama genérica por
  catálogo -- cualquier clave de `Celda.recursos` que sea
  `apto_construccion` en `config/materiales.yaml` cuenta, no una lista
  de nombres fija -- insertada entre `deposito_mineral` (más
  prioritario, finito de verdad) y `tipo_sustrato` (fallback, siempre
  disponible): mineral > material de flora > sustrato. Cero cambios en
  `sistema_decision.py` -- mismo motivo que la minería del Círculo 2 de
  profundidad, RECOLECTAR ya gatea genéricamente por masa apta
  pendiente.

Verificado: un manzano maduro produce madera de verdad en su celda (2.8kg
tras 29 días de partida); un gnomo colocado ahí la recolecta al
Inventario y cae a arcilla (sustrato) en cuanto la madera se agota en esa
celda concreta -- prioridad funcionando; "manzanas"/comida nunca terminan
en el inventario de construcción (no están en el catálogo de materiales,
así que el filtro `apto_construccion` las excluye sin necesidad de una
lista de exclusión). Motor real (4000 ticks) sin intervención:
construcciones reales usaron arcilla + hierba_seca. Con esto, "un
habitáculo de madera con un techo de paja" -- el propio ejemplo original
de Diego para refugio construido -- ya es alcanzable de verdad, no solo
teórico.

Commits de esta pieza: `a2ab5e7`/`164a5e9` (merge del sistema de
profundidad + corrección de `zona_idx` en el conflicto por refugio),
`fe47bb1` (arreglo del visor), `622abe8` (recolección de flora).

**Pendiente real que sigue abierto**, sin una sola línea de código:
~~`entidades.viva` nunca actualizado (señalado arriba, pre-existente)~~
-- CERRADO 2026-09-01/02, ver la sección "Dos pendientes antiguos
cerrados vía pipeline" más abajo; selector de zona real en el visor (el
arreglo de hoy solo evita que la vista de superficie mienta, no añade
forma de ver el subsuelo); liquen (montaña) y musgo (tundra) siguen sin
ganar su propia entrada de material recolectable -- Diego no lo pidió
esta vez, no se ha tocado.

## Sobrepoblación sin techo aparente -- investigado y mitigado con un
## mecanismo natural de fertilidad por nutrición (2026-08-31)

Retomado el límite conocido más antiguo del proyecto (migración
24-08-2026: "varias semillas de referencia terminan con densidades de
hasta 0.45 individuos/celda, referencia 0.05-0.07"). Diego, ante cinco
opciones posibles para seguir ("con que podemos avanzar ahora?"), descartó
"ciudad enana" (no tiene sentido hasta plantear esa raza), el selector de
zona en el visor (va a sufrir bastantes cambios a futuro) y el transporte
de agua (pertenece a la capa de fabricación de objetos, sin empezar), y
eligió explícitamente este: "me pondria con el 4".

**Diagnóstico empírico, no razonado sobre el papel** (mismo criterio que
el resto del proyecto: "verifica contra el motor real"). Arnés nuevo,
`diagnostico_poblacion.py` (no forma parte del repo, vive en el
scratchpad de la sesión -- reutilizable si hace falta retomar esto),
que corre `main.py` real sin persistencia SQLite, muestreando población
por especie/zona y tallando causas de muerte. Primeras 4 semillas (42,
99, 1, 7; 6000-8000 ticks): el problema NO era "crecimiento sin techo" tal
cual estaba documentado -- es un ciclo boom-bust real, que en el peor caso
(semilla 7) alcanzó densidad 0.34 (cerca del histórico 0.45) y en otro
(semilla 42) terminó en extinción total de las cuatro especies hacia
t=6000. Causa raíz identificada leyendo `sistema_reproduccion.py`: la
probabilidad de concepción (`factor_base_concepcion * sociabilidad_media`)
no consultaba `Necesidades` en absoluto -- el único gate de necesidades
físicas existente (`decision.umbral_atencion_pareja`) actuaba solo sobre
la utilidad de `Accion.BUSCAR_PAREJA` (búsqueda consciente de pareja), no
sobre el roll de concepción en sí, así que dos elegibles que coincidían en
la misma celda por cualquier motivo (huyendo, migrando, deambulando)
concebían sin que importara si estaban muriendo de hambre. Hallazgo
secundario, no la causa principal: las cuevas (del arco de profundidad,
mismo día) están 100% desprovistas de comida (`sembrar_flora_inicial`
solo siembra `zonas[0]`, y sin ninguna `Planta` semilla no hay propagación
posible bajo tierra) -- entre 8% y 42% de las muertes por inanición según
la semilla ocurrían en cuevas, un amplificador real pero secundario.

**Decisión de diseño con Diego, no autorada por Claude**: pregunta directa
("¿Cómo quieres encarar esto?") con dos alternativas descartadas
explícitamente antes de plantearlas -- un contador de densidad local
(freno artificial con la forma exacta del síntoma observado en conejo, no
una ley que pudiera producirlo entre otras; violaría el principio 5, leyes
neutras) fue rechazado por Diego con la misma lógica del proyecto: "hay
que encontrar un mecanismo natural no una solucion para conejo". La ley
natural real, confirmada en conversación: desnutrición suprime fertilidad
-- no es que un individuo "cuente" cuántos coespecíficos hay alrededor, es
que un individuo mal alimentado no concibe (y, añadido por Diego en el
mismo intercambio, "un conejo mal alimentado lo normal es que produzca
menos crias" -- también el tamaño de camada, no solo si concibe).

**Implementación** (`sistemas/sistema_reproduccion.py`), misma ley para
las cuatro especies, ninguna rama por especie:
1. Gate de concepción: si hembra o macho tienen saciedad por debajo de
   `decision.umbral_atencion_pareja` (reutilizado, mismo umbral que ya
   protege `BUSCAR_PAREJA`, sin inventar uno nuevo), la concepción ni se
   intenta.
2. Tamaño de camada escalado por la saciedad de la MADRE en el instante
   de concepción (único rasgo usado -- ni el resto de necesidades ni la
   condición del padre; el tamaño de camada en biología real depende de
   capacidad uterina/ovulación materna, no paterna): interpolación lineal
   entre `umbral_atencion_pareja` (ahí el techo efectivo de la tirada cae
   a `camada_min`) y saciedad plena (techo = `camada_max`), con sorteo
   real (`rng.randint`) dentro de ese rango reducido -- la nutrición
   mueve el techo, no elimina el azar.

**RONDA 1 (gate por las 4 necesidades físicas, igual que BUSCAR_PAREJA)
sobrecorregía**: con las mismas 4 semillas, 3 de 4 pasaron de "sin techo"
a colapsar muy por debajo del rango de referencia (semilla 42 estabilizó
en 0.0037 con solo ardilla superviviente; semilla 1 en caída hacia
0.0031). Solo semilla 7 aterrizó bien (pico 0.12 -> 0.065). Diagnosticado:
exigir las 4 necesidades altas EN AMBOS progenitores a la vez, cada tick,
es una condición mucho más estricta que cualquier gate previo, y además
mezclaba "estado físico general" con lo que Diego pidió específicamente
(nutrición). **RONDA 2, mismo día**: gate estrechado a saciedad
únicamente (energía/hidratación/aliviado siguen gateando `BUSCAR_PAREJA`
sin cambios, ya no bloquean la concepción en sí) -- coherente con que el
escalado de camada ya solo miraba saciedad.

**Hallazgo metodológico real, encontrado al re-verificar ronda 2 con las
mismas 4 semillas**: los resultados semilla-a-semilla entre ronda 1 y
ronda 2 fueron incoherentes con causalidad simple (semilla 1 mejoró
mucho, semillas 42 y 7 empeoraron a casi-extinción con un gate MÁS
permisivo que en ronda 1) -- la firma de trayectorias caóticas
divergentes, no de un efecto causal. Causa: `sistema_reproduccion.py` y
el resto de sistemas comparten un único `rng_juego` por partida; cambiar
cuántas veces se llama a `rng.random()`/`rng.randint()` en el gate de
concepción desplaza la secuencia de aleatoriedad que consume TODO lo
demás (movimiento, decisión) en los ticks siguientes -- con una dinámica
tan sensible a condiciones iniciales (retroalimentación depredación/
inanición), "la misma semilla" bajo dos versiones de código son en la
práctica dos partidas distintas. **Lección para cualquier calibración
futura de esta clase**: una comparación semilla-a-semilla entre versiones
de código que cambian el número de tiradas de `rng` no es fiable --
hace falta comparar DISTRIBUCIONES sobre muchas semillas nuevas, no pares
puntuales. `sistema_reproduccion.py` sigue compartiendo `rng_juego` con
el resto del motor -- decidido no separarlo en un rng propio esta vez
(cambio de infraestructura no pedido, fuera de alcance de este círculo),
pero queda anotado aquí como candidato si se retoma calibración fina de
reproducción en el futuro.

**Verificación final, 14 semillas (42, 99, 1, 7 reverificadas + 2, 3, 4,
5, 6, 8, 9, 10, 11, 12 nuevas, hasta 8000 ticks las que mostraban boom o
colapso sin resolver a los primeros 4000)**: 10 de 14 (71%) se comportan
razonablemente -- estables desde el principio o con un ciclo boom-bust
real que se autocorrige hacia el rango de referencia (algunas tardan
hasta t=7000 en aterrizar, ej. semilla 12: pico 0.19, aterriza en
0.065-0.075). Ninguna semilla queda instalada de forma permanente en
crecimiento sin control como antes (0.34 sostenido). Quedan DOS modos de
fallo residuales, señalados explícitamente, NO corregidos:
1. **Colapso/extinción** (semillas 42, 7): el gate sobrecorrige en
   trayectorias concretas y borra la población entera -- efecto
   secundario nuevo que el problema original no tenía.
2. **Overshoot sin resolver o muy lento** (semillas 9, 11): semilla 9
   sigue subiendo sin bust hasta el final de la corrida (0.29 a t=8000,
   cerca del histórico 0.34); semilla 11 se estabiliza en una meseta
   ruidosa 0.10-0.17 sin bajar nunca al rango de referencia. Hipótesis
   razonada, no confirmada con más profundidad: retraso (lag) entre "hay
   demasiada población" y "la saciedad cae lo bastante" -- con
   concepción evaluada cada tick y camadas de hasta `camada_max` mientras
   la comida siga alcanzando, una población bien alimentada puede
   componer muchos ticks antes de que la escasez local golpee lo
   bastante fuerte como para que el gate actúe.

**Decisión de cierre, con Diego**: aceptado como mejora sustancial y
PROVISIONAL (mismo criterio que el resto de constantes del proyecto sin
calibrar contra el harness completo de 15 semillas x 12000 ticks -- esta
verificación de 14 semillas hasta 8000 ticks es la más cercana a ese
estándar que se ha hecho en el proyecto hasta ahora para una sola pieza,
pero sigue sin ser ese harness exacto). No se persigue eliminar el 29% de
casos con overshoot/colapso ahora mismo -- exigiría algo más sofisticado
que mover el mismo umbral (separar el umbral de concepción del de
`BUSCAR_PAREJA`, o una capa adicional), inversión no claramente
justificada frente a seguir con otra pieza del proyecto. Los 22 tests
existentes en verde en todo momento (ninguno cubre reproducción
directamente). Commits: `6eff7cc` (ronda 1, gate de 4 necesidades +
camada por saciedad), `2e11912` (ronda 2, gate estrechado a saciedad
únicamente -- estado final).

**Pendiente real, explícito**: las cuevas siguen sin ninguna fuente de
comida (hallazgo secundario de esta investigación, no corregido -- las
cuevas fueron diseñadas en un círculo previo sin plantearse el hueco de
flora, y esta sesión no lo tocó); los dos modos de fallo residuales
(colapso, overshoot lento) sin resolver, candidatos para cuando se aborde
una calibración más profunda de reproducción; ~~separar `sistema_
reproduccion.py` a su propio `rng` en vez de compartir `rng_juego` con el
resto del motor, si se quiere volver a comparar versiones de código
semilla-a-semilla de forma fiable en el futuro~~ -- CERRADO 2026-09-01,
`rng_reproduccion` propio y persistido, ver "Dos pendientes antiguos
cerrados vía pipeline" más abajo.

## Conflicto por refugio ocupado -- estado real corregido, no una pieza
## nueva (2026-08-31)

Diego pidió empezar a perfilar "sociedad" retomando el resolutor de
conflicto, creyendo (por la nota de "Pendiente" de más arriba, sección de
refugio/asentamiento del 30-08) que seguía sin una sola línea de código.
Antes de implementar nada por segunda vez, la propia disciplina del
proyecto ("verifica contra el código real, no la lectura en abstracto")
obligaba a comprobarlo primero -- y **ya estaba hecho**: commit `2640a82`,
el mismo 31-08 pero ANTES de la auditoría de coherencia documentada más
arriba, implementó `nucleo/conflicto.py` completo
(`indice_asertividad_social`, `resolver_disputa` con CEDE_A/CEDE_B/
COMPARTE/ENFRENTAMIENTO) y su primer consumidor,
`sistema_movimiento.py:_resolver_posible_intruso`, disparado desde
`_calcular_dormir` cuando el propietario llega a su refugio CONSTRUIDO
(`completado_alguna_vez`, no un punto de memoria instintivo) y encuentra
a otra entidad en la misma celda/zona. La nota de "pendiente, sin una
sola línea de código" de la sección de arriba nunca se corrigió tras ese
commit -- documentación desfasada, no un hueco funcional real. Tachada
arriba en vez de borrada, mismo criterio de honestidad que el resto del
documento (registro de qué se creyó en cada momento, no solo el estado
final).

El propio commit ya documentaba verificación real: arnés dirigido de los
cuatro desenlaces, despacho normal a través de `Accion.DORMIR` de
principio a fin (no solo llamando al método directamente), 4000 ticks de
motor real sin fallos, 22/22 tests. Esta sesión añadió una segunda
re-verificación independiente antes de confiar en la primera (arnés en
el scratchpad, `verificar_conflicto.py`, no en el repo): cinco escenarios
construidos a mano llamando a `_resolver_posible_intruso` directamente --
propietario dominante (intruso pierde 0.3 de `Necesidades.seguridad`,
propietario intacto), intruso dominante (al revés), empate agresivo
(ambos pierden 0.2, el drenaje de `ENFRENTAMIENTO`), mismo asentamiento
con alta cohesión (`COMPARTE`, nadie pierde nada), y temperamento
exactamente parejo pero con la seguridad del propietario ya baja --
confirmando que la urgencia (`1.0 - seguridad`) desempata a su favor
incluso sin ventaja de temperamento. Los cinco coinciden exactamente con
el diseño documentado.

**Lo que sí sigue siendo un hueco real, no documentación desfasada**:
1. Robo y "agravio genérico", nombrados explícitamente en el diseño
   original como consumidores futuros del mismo resolutor ("esto debe
   ser reutilizable a futuro... que un individuo robe a otro") --
   `resolver_disputa`/`indice_asertividad_social` no tienen ningún otro
   punto de disparo en el motor todavía, solo refugio ocupado.
2. Memoria de agravios entre individuos con nombre propio (rencor
   persistente tras perder una disputa) -- deliberadamente fuera de
   `nucleo/conflicto.py` desde su diseño original, conecta con lo que
   `Temperamento.empatia`/`lealtad` ya señalan como pendiente.
3. `config/comportamiento.yaml` sección `conflicto` (umbrales de
   cohesión/empate reñido/agresividad, drenajes de seguridad) sigue
   PROVISIONAL, sin calibrar contra el motor en marcha -- ni el commit
   original ni esta sesión lo han hecho.
4. No confirmado si el disparador llega a ocurrir con población real
   corriendo sola (el "4000 ticks sin fallos" del commit original
   confirma ausencia de crash, no que la ruta de conflicto se ejerciera
   de verdad) -- candidato a comprobar si se retoma esta pieza.

No se ha escrito código nuevo en esta sesión para esto -- la corrección
fue de documentación, más la re-verificación. Pendiente de que Diego
decida si el siguiente paso real es extender a robo/agravio (mismo
resolutor, un disparador nuevo en su propio sistema, sin lógica nueva en
`nucleo/conflicto.py`) o calibrar lo ya existente.

## Capacidad de construcción por celda -- "¿una hoguera ocupa lo mismo
## que una casa?" (2026-08-31)

Diego, al plantear perfilar herramientas/fuego/comida elaborada como
próxima área ("la base de la sociedad realmente"), se detuvo en una duda
de fondo que venía arrastrando: "¿qué es una celda?". El mundo se planteó
al principio como una rejilla de 40×40 con `metros_por_celda: 10`
(`config/mundo.yaml`) -- cada celda son 100 m² reales. Verificado contra
el código, no supuesto: hoy la ocupación por celda es una mezcla
inconsistente, no una regla uniforme -- flora tiene un límite duro real
de 1 `Planta` por celda (`sistema_flora.py:_intentar_propagacion`, un
`set` de posiciones ya colonizadas, defendible como abstracción a esta
escala: la mancha/individuo DOMINANTE de esos 100 m², no "la única planta
literal"); depósito mineral igual (campo propio de `Celda`); criaturas
sin ningún límite (ya conviven varias por celda de forma rutinaria);
**construcción no tenía absolutamente ninguna noción de espacio** --
`construccion_propia` busca por `propietario_id`, nunca por celda, así
que nada impedía (ni nada comprobaba) que dos refugios coincidieran en la
misma celda sin distinguir un objeto pequeño de uno grande. De ahí la
pregunta concreta de Diego: "¿una hoguera ocupa lo mismo que una casa?
En el caso de los recursos igual".

**Opción descartada explícitamente, con razonamiento**: encoger el grid
(por ejemplo a 2m/celda) para que los objetos se distingan por
resolución en vez de por atributo. Se descartó porque casi todo el motor
está calibrado contra 40×40@10m -- generación de terreno/agua/cuevas
(`nucleo/orografia.py`, `nucleo/agua.py`, `nucleo/cueva.py`), radios de
percepción, costes de movimiento, y las propias cifras de referencia de
densidad poblacional (0.05-0.07 individuos/celda) que se acababan de
investigar en esta misma sesión. Encoger el grid multiplicaría el número
de celdas por 25x y reabriría media docena de sistemas ya cerrados sin
ninguna necesidad real detrás -- desproporción de coste frente a la otra
vía, no una decisión de diseño en sí.

**Opción elegida**: separar "resolución de movimiento/terreno" (se queda
igual, 100 m²/celda) de "cuánto espacio ocupa un objeto CONSTRUIDO dentro
de esa celda" (nuevo). Mismo patrón que `masa_minima_refugio`/
`masa_minima_almacen` (un umbral acumulado por tipo), aplicado esta vez a
área en vez de a masa -- `config/materiales.yaml` sección `construccion`
gana `huella_m2_refugio` (15.0, PROVISIONAL, una choza primitiva ~4x4m),
`huella_m2_almacen` (40.0, PROVISIONAL, construcción comunal más grande)
y `capacidad_construccion_celda_m2` (80.0 de los 100 m² reales, margen
razonado no medido para paso/terreno natural, sin inventar un parámetro
de margen aparte). `nucleo/construccion.py` gana `huella_m2_para` (mismo
criterio permisivo por `.get()` que `masa_minima_para`) y
`espacio_disponible_para_construir` (capacidad menos la suma de huellas
de toda `Construccion` ya presente en esa celda exacta, filtrado por
`zona_idx` desde el principio -- no hubo que descubrir ese hueco esta vez,
ya se sabía del arco de profundidad). `sistema_movimiento.py:
_calcular_construir` comprueba el espacio disponible contra la huella del
tipo objetivo antes de crear la `Construccion`; si no cabe, no se crea
este tick -- deliberadamente SIN ninguna búsqueda de una celda vecina con
hueco (mismo criterio que "sin lógica de selección de sitio" ya
documentado para refugio): el individuo simplemente lo reintentará en su
próxima posición según el resto de su comportamiento ya lo mueva. Límite
conocido, no resuelto: el almacén se crea en el centro FIJO del
asentamiento, así que si esa celda exacta está llena, el individuo puede
quedarse sin poder construirlo -- no se le buscó una celda vecina de
respaldo, mismo argumento de "no inventar sin necesidad real todavía".

**Estructuras multi-celda (muralla, castillo) -- explícitamente fuera,
apuntado como extensión futura, no construido**: Diego señaló que a
futuro algunas construcciones excederán una sola celda. La unidad m² ya
generaliza a eso sin cambios conceptuales -- una construcción cuya
huella supere la capacidad de una celda necesariamente reclama celdas
vecinas, mismo número, más celdas. Pero el MECANISMO real (qué celdas
vecinas reclama, en qué forma -- una línea para un muro, un bloque para
un castillo -- y qué pasa si se destruye) no se ha construido: no hay
todavía ninguna construcción real que lo necesite, y hacerlo ahora sería
inventar una regla para un caso hipotético (mismo error que ya costó
tiempo con el hueco de materiales de flora). Queda como punto de
extensión natural para cuando exista un caso real (candidato: cuando se
retome "ciudad enana").

**Verificado contra el motor real, tres pasadas**: (1) arnés dirigido
(`verificar_capacidad.py`, scratchpad) confirmando la aritmética exacta
-- celda vacía = 80 m² libres, 5 refugios (75 m²) caben y el 6º queda
bloqueado con 5 m² libres, aislamiento correcto por celda y por zona, un
almacén cabe tras 2 refugios (50 m² libres > 40 requeridos); (2) 3000
ticks de `BOSQUE_AUTO_TICKS` sin ninguna excepción; (3) 4 semillas (42,
1, 7, 99) × 4000 ticks del pipeline completo sin intervención,
inspeccionando construcciones reales al final: **0 celdas exceden los 80
m² de capacidad en las 4 semillas** -- el invariante nunca se viola en
juego normal. El mecanismo se ejerce de verdad, no solo en teoría: 2 de
4 semillas ya tienen celdas con más de una construcción compartiendo
espacio de forma espontánea (hasta 55 m² de huella conjunta en una misma
celda, refugio + almacén). 22/22 tests en verde.

**Pendiente real, explícito**: `huella_m2_refugio`/`huella_m2_almacen`/
`capacidad_construccion_celda_m2` son PROVISIONALES, sin calibrar contra
el harness completo; sin búsqueda de celda vecina de respaldo si la
elegida está llena (refugio: se resuelve solo por el resto del
comportamiento; almacén: puede quedarse bloqueado si el centro exacto del
asentamiento está lleno); estructuras multi-celda sin construir, a la
espera de un caso real.

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

## Pipeline autónomo -- primera prueba real de extremo a extremo, tres
## hallazgos reales sobre el modelo `agente-obrero` (2026-09-02)

Contexto: el pipeline autónomo (`.ai-pipeline/`, centinela +
`run-plan.sh` + `aider` vía proxy LiteLLM local, alias `agente-obrero`)
se configuró y se corrigió de varios fallos de infraestructura en una
sesión anterior (rama `feature/2026-09-01-armas-fabricadas`, PR #1, sin
mergear todavía -- esa rama documenta el incidente original: un primer
intento del pipeline abrió un PR sin ninguna implementación real porque
el proxy nunca llegó a arrancar). Esta sesión, ya en `master`, hizo la
**primera prueba real de punta a punta** con un plan minúsculo y de bajo
riesgo (fix de una línea: `entidades.viva` nunca se actualizaba al
morir, ver más abajo) -- deliberadamente elegido como prueba de humo del
pipeline, no como pieza de diseño.

**Modelo `agente-obrero`**: `openrouter/deepseek/deepseek-v4-flash-0731`
(decisión de Diego, ver commits `dd31a3b`/`67f57af`).

**Hallazgo 1 -- bucle de razonamiento no convergente, causa raíz
verificada, NO era el modelo**. Al primer intento real, el modelo se
quedó atascado repitiendo el mismo párrafo de razonamiento cientos de
veces sin converger nunca a una respuesta. Diego cuestionó con razón que
un modelo con buena puntuación pudiera fallar así ("tiene que ser
problema de nuestro flujo") -- se investigó antes de aceptar "el modelo
es poco fiable" como conclusión, y tenía razón: `aider/models.py`
resuelve la temperatura de la llamada por coincidencia de patrones sobre
el NOMBRE del modelo -- modelos de razonamiento ya conocidos por aider
(QwQ-32b, Qwen3-235b) reciben `use_temperature=0.6/0.7` a propósito,
precisamente para evitar bucles de repetición con muestreo greedy nuestro
alias `openai/agente-obrero` no coincidía con ningún patrón conocido y
caía al default genérico (`use_temperature=True` -> `temperature=0`,
greedy puro) -- la causa real y demostrada del bucle. Corregido con
`.ai-pipeline/aider-model-settings.yml` (`--model-settings-file`),
dándole a nuestro alias el mismo tratamiento que aider ya da a QwQ-32b:
`use_temperature: 0.6`. Verificado: el bucle exacto desaparece por
completo tras el fix (994 tokens de respuesta real en vez de cientos de
párrafos repetidos).

**Hallazgo 2 -- confusión con el ejemplo de demostración integrado en
aider, distinto del anterior**. Con el bucle ya resuelto, el modelo
seguía sin avanzar: confundía el ejemplo fijo que aider inyecta en su
prompt para enseñar el formato SEARCH/REPLACE (el clásico "Change
get_factorial() to use math.factorial" de
`aider/coders/editblock_prompts.py`) con conversación real, llegando a
proponer ediciones contra `mathweb/flask/app.py` -- un fichero que no
existe en este repo, parte literal del ejemplo, no de nuestra tarea.
Causa: por defecto aider inyecta ese ejemplo como turnos
`role=user`/`role=assistant` sueltos, estructuralmente IDÉNTICOS a una
conversación real -- sin ninguna marca textual de "esto es solo un
ejemplo". Corregido en el mismo `model-settings.yml`:
`examples_as_sys_msg: true` mete el ejemplo DENTRO del propio system
prompt bajo un encabezado explícito "# Example conversations:" --
exactamente el tratamiento que aider ya da a QwQ-32b por el mismo
motivo. Verificado: tras el fix, el modelo ya no menciona
`mathweb/flask/app.py` ni el factorial en ningún intento posterior.

**Hallazgo 3 -- el modelo sigue sin usar el contenido real de los
ficheros que aider confirma haber añadido al chat, NO resuelto**. Con
los dos hallazgos anteriores corregidos, en los 3 intentos de una
ejecución completa el modelo siguió razonando "no tenemos el contenido
real de `nucleo/persistencia.py`/`main.py`, tenemos que adivinar" --
pese a que el propio log de aider confirma explícitamente "Added
main.py to the chat" / "Added nucleo/persistencia.py to the chat" en
cada intento. Resultado: adivinó una firma de método plausible pero
incorrecta (`def persistir_eventos(self, eventos):` en vez de la real,
con anotaciones de tipo), la edición no se aplicó, y el test creado
(correcto, palabra por palabra igual al plan) falló con
`AttributeError: 'Persistencia' object has no attribute
'marcar_entidad_muerta'` las tres veces. Se probó una hipótesis
adicional concreta antes de rendirse: el aviso repetido "Unknown context
window size and costs, using sane defaults" sugería que litellm no
conocía el contexto real del modelo -- se declaró explícitamente
`model_info` (max_input_tokens/costes reales, tomados del catálogo de
OpenRouter) en `litellm_config.yaml`. **No resolvió nada**: el aviso
persiste igual (viene del propio `litellm` que `aider` importa como
librería cliente, no de nuestro proxy -- declarar el modelo en la config
del proxy no cambia lo que el cliente aider cree saber de él) y el
modelo siguió sin usar el contenido de los ficheros. Quedó como
**hallazgo abierto, no resuelto**, tras haber agotado las palancas de
configuración razonables sin necesitar cambiar de modelo todavía.

**Reducción de contexto también probada, sin ser la causa raíz por sí
sola**: se detectó de paso que `CLAUDE.md` (150KB / ~2300 líneas en el
momento de la prueba) se pasaba entero como fichero editable en
cualquier plan que lo tocara -- diluyendo el plan real (252 líneas) en
~40.000 tokens mayormente irrelevantes (`Tokens: 67k sent` observado).
Se recortó la tarea de documentación del plan de prueba para no
depender de tocar `CLAUDE.md` desde el pipeline, y aun así el Hallazgo 3
persistió con un contexto mucho más pequeño (~21-22k tokens) -- así que
el tamaño de `CLAUDE.md` agrava el problema si un plan lo toca, pero no
es la causa de fondo del Hallazgo 3. **Lección aparte, con consecuencia
práctica real**: cualquier plan futuro para el pipeline autónomo debería
evitar declarar `CLAUDE.md` como fichero a modificar por el propio
agente -- mejor dejar esa actualización para el cierre manual, como se
hizo aquí.

**Balance honesto**: 2 de 3 hallazgos reales fueron demostrablemente
nuestros (configuración de aider, no calidad del modelo) -- confirma que
cuestionar la primera explicación fue lo correcto. El tercero queda sin
resolver y es el que realmente bloquea el pipeline hoy: sin que el
modelo use de forma fiable el contenido de los ficheros que se le
entregan, no puede completar ni una tarea mínima de una sola línea.
Ninguna prueba llegó a dejar código real mergeado -- todos los intentos
se descartaron limpiamente (branches borradas, sin commits huérfanos en
`master`), el propio `run-plan.sh` (con las correcciones de esta
sesión: verificación de cambios reales, timeout de 480s, extracción
precisa de ficheros por convención `- Modify/Create/Test:`) se comportó
correctamente en todo momento -- el disyuntor de 3 intentos se activó
como se diseñó.

**Pendiente real, decisión de Diego**: (a) seguir intentando con
`deepseek-v4-flash-0731` explorando otras palancas (p.ej. probar sin
`--edit-format diff` forzado, o con `--architect` en vez de edición
directa, o simplificar aún más el plan de prueba); (b) volver a un
modelo con track record probado en esta misma prueba de humo
(`anthropic/claude-sonnet-5` vía OpenRouter, ya confirmado funcionando
de extremo a extremo en una sesión anterior, aunque nunca probado dentro
de una sesión real de `aider`); (c) otra opción. No decidido
unilateralmente por Claude -- el patrón de esta sesión (Diego elige el
modelo, Claude prueba y reporta con evidencia) se mantiene.

## Dos pendientes antiguos cerrados vía pipeline, mismo tramo de trabajo
## (2026-09-01/02) -- entidades.viva y RNG propio de reproducción

Tras el balance del Hallazgo 3 (sección anterior), el pipeline autónomo
(todavía con `aider` en este tramo, antes de la migración a
`mini-swe-agent` documentada más abajo) sí llegó a cerrar limpiamente
dos pendientes reales señalados en secciones previas de este documento
-- ninguno de los dos documentado como cerrado hasta ahora (encontrado
al auditar el `git log` real contra este documento, no al releerlo).

- **`entidades.viva` nunca se actualizaba a `False` al morir** (hueco
  señalado en "Auditoría de coherencia...", 2026-08-31, arriba --
  tachado ahí). Plan `2026-09-02-fix-entidades-viva`: `UPDATE` real al
  emitir el evento de muerte + test de persistencia dedicado
  (`tests/test_persistencia_entidades_viva.py`). Cerrado con `aider`, a
  pesar de que el Hallazgo 3 (modelo sin usar de forma fiable el
  contenido de los ficheros) seguía sin resolución formal -- para una
  tarea de una sola línea con poco contexto, el problema de fondo no
  llegó a manifestarse esta vez; no se investigó por qué, tampoco se
  necesitó.
- **`sistema_reproduccion.py` seguía compartiendo `rng_juego` con el
  resto del motor** (candidato señalado en "Sobrepoblación...",
  2026-08-31, arriba -- tachado ahí, para cuando se quisiera volver a
  comparar semillas de forma fiable). Plan
  `2026-09-02-rng-propio-reproduccion`: `rng_reproduccion` propio,
  sembrado de forma determinista a partir de la semilla del mundo y
  persistido junto al resto del estado de RNG
  (`tests/test_rng_reproduccion.py`). Cierra la lección metodológica de
  aquella sección -- comparar código de reproducción semilla-a-semilla
  vuelve a ser fiable.

De paso, mismo tramo: `tests/test_ciclo_vital_es_adulto.py` añade
cobertura nueva (sin ningún bug encontrado -- cobertura pura) a la ley
de madurez reproductiva (`es_adulto`/`fraccion_madurez` por especie),
que hasta entonces no tenía ningún test dedicado.

## Distribución causal de flora (2026-09-01/02) -- pieza 1 de la cola
## "poblar más el mundo", 5/5 mergeada vía pipeline con `aider`

Primera pieza real de la cola acordada para "poblar más el mundo" (1.
este círculo; 2. tipos de propagación, ver la sección de ese nombre más
abajo; 3. cupo de espacio compartido por celda, sin empezar; 4. catálogo
ampliado de especies, sin empezar) -- **nunca tuvo su propia sección en
este documento hasta ahora**, pese a que secciones posteriores ya la
referencian como "ya cerrada". Spec aprobada por Diego en
`docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`:
sustituye la colocación de flora en generación -- hasta entonces una
norma de config (`proporcion` + `celdas_por_mancha_objetivo` por
especie, sin relación con el terreno real) -- por una ley física real
que lee sustrato, humedad de subsuelo, lluvia y temperatura ya
calculados en generación. Troceada en 5 planes, cada uno soltado al
pipeline autónomo (`aider`, en este arco) y mergeado por su propio PR:

1. **PR #4** -- catálogo de sustrato con `fertilidad_base` (piedra,
   arcilla, arena, tierra + tres materiales nuevos: tierra_negra,
   marga, grava). **Incidente real de corrupción de `aider`, encontrado
   en revisión de código, no por el pipeline**: el commit original
   dejaba `fertilidad_base` triplicada/cuadruplicada en piedra/arcilla
   (una copia con el homoglifo cirílico "misма" en vez de "misma"),
   `tasa_infiltracion` corrompida a la clave inexistente
   `taa_infiltracion` en piedra/tierra (habría roto en silencio la
   infiltración de agua real de esos sustratos), y el fichero de test
   entero duplicado -- la copia corrupta quedaba sombreada por la
   limpia, por lo que "33 passed" no lo detectó. **Fallo de
   verificación propio, reconocido en el commit de corrección**: haber
   confiado en el recuento de pytest en vez de leer el diff completo.
   Corregido con una segunda pasada: diff completo + loader YAML
   estricto (rechaza claves duplicadas) + búsqueda de caracteres
   no-ASCII sospechosos.
2. **PR #5** -- `elegir_sustrato_celda`. Primer plan limpio con
   `--edit-format udiff` en vez de `diff`/SEARCH-REPLACE (0
   duplicación, 0 typos, diff exacto al plan) -- interrumpido a media
   ejecución por una suspensión de la máquina (~6h sin proceso vivo),
   completado a mano el resto del flujo de éxito ya en marcha.
3. **PR #6** -- `idoneidad_colonizacion` + refactor de
   `factor_produccion`. El modelo añadió 7 tests no pedidos por el
   plan, 2 con bugs reales (afirmaban resultados que contradecían la
   propia función documentada, o ignoraban una trampa de saturación de
   humedad que el plan ya evitaba a propósito) -- retirados, quedan
   solo los 7 del plan.
4. **PR #7** -- sustrato variado + fertilidad inicial en generación.
   Dos correcciones manuales: una línea duplicada en
   `nucleo/territorio.py` rompía TODA generación de mundo con un
   `TypeError` (afectaba incluso a un test preexistente sin relación,
   `test_rng_reproduccion`); un test heredado de la pieza 1 que
   afirmaba que `sustrato_por_bioma` no cambiaría de forma quedó sin
   retirar por el propio plan, pese a que la pieza 4 sí lo cambia a
   lista por diseño -- hallazgo de revisión del plan, no de ejecución.
5. **PR #8** -- ley de colonización por idoneidad
   (`colonizar_por_idoneidad`), sustituye del todo el reparto por
   proporción/mancha. Dos correcciones: función duplicada byte a byte
   (inofensiva en ejecución, sucia); un test que exigía observar celdas
   vacías nunca se cumplía contra la calibración PROVISIONAL real (0
   celdas vacías en 5 semillas × 900 celdas) -- corregida la aserción,
   señalado para revisar en calibración futura, sin tocar los números
   a ojo por corregir un test.

**Recalibración post-merge** (`3b427be`, verificación de conjunto tras
las 5 piezas): `umbrales_sustrato_fertil` de montaña (0.6) y bosque
(0.55) estaban por debajo del propio umbral de clasificación de esos
biomas -- grava y arcilla quedaban estructuralmente inalcanzables ahí,
no solo raras (confirmado: fertilidad de montaña siempre 0.0, de bosque
siempre 0.70, en 3 semillas). Un primer intento de corrección (punto
medio hasta 1.0) sobrecorrigió bosque -- medido en 10 semillas, la
lluvia real dentro de bosque nunca supera 0.78. Recalibrado con la
mediana real observada de cada bioma en vez del techo teórico del
campo. Desierto y pradera no tenían este problema, sin tocar.

**Balance**: 5/5 piezas mergeadas, 3 de los 5 PRs con al menos una
corrección manual real tras revisión (corrupción, tests inventados con
bugs, línea duplicada rompiendo la generación completa) -- ninguna
quedó sin detectar antes de mergear, pero ninguna se mergeó limpia al
primer intento tampoco. Contraste directo con las ejecuciones de
`mini-swe-agent` documentadas más abajo, aunque sobre piezas de menor
alcance cada una -- la comparación no es enteramente equivalente. 56/56
tests en verde al cierre del arco, 1000 ticks de `BOSQUE_AUTO_TICKS` sin
excepciones.

## Prueba de control del pipeline (2026-09-02, misma tarde) -- dos fallos
## más, causa raíz real del Hallazgo 3 identificada, `aider` descartado
## como herramienta, pieza 1 de propagación de flora resuelta a mano

Diego, tras revisar el balance de la sección anterior, preguntó
directamente "¿hemos ahorrado? ¿la mejora justifica el flujo?" -- en vez
de responder en abstracto, se hizo la prueba real que faltaba: trocear
la pieza 2 de "poblar más el mundo" (tipos de propagación de flora, ver
más abajo) en 5 planes con el mismo formato que ya había funcionado en
la distribución causal de flora, y soltar el más simple al pipeline ya
endurecido para medir cuánta supervisión hacía falta.

**Primer intento: falló los 3 reintentos** -- dos silenciosos ("el
agente no modificó ningún fichero") y uno por timeout con el mismo
bucle de repetición no convergente que las correcciones de
temperatura/`examples_as_sys_msg` debían haber resuelto. Investigado
antes de aceptarlo como "el modelo es poco fiable, sin más" (mismo
criterio que el resto de esta sección): la causa real, verificada
leyendo `aider/coders/base_coder.py:get_file_mentions`/
`check_for_file_mentions` del paquete instalado, no supuesta -- **cualquier
palabra suelta del mensaje (nuestro plan, O la propia respuesta del
modelo) que coincida con el nombre de un fichero del repo dispara un
auto-añadido al chat, sin ningún flag de CLI para desactivarlo**, y con
`--yes-always` se acepta siempre sin preguntar. El plan de prueba
mencionaba `CLAUDE.md` una sola vez, en prosa, para decir "no lo
toques" -- bastó para arrastrarlo entero al contexto, y el propio
contenido de `CLAUDE.md` menciona decenas de otros ficheros del
proyecto (`componentes/necromasa.py`, `sistema_ciclo_vital.py`,
`sistema_depredacion.py`...), que se auto-añadieron en cascada.
Resultado: 66k tokens enviados para una tarea de 2 ficheros.

**CORRECCIÓN sobre la mitigación de la sección anterior**: "evitar
declarar `CLAUDE.md` como fichero a modificar" (ver arriba, "Lección
aparte") **no basta** -- el disparador no es declararlo modificable, es
nombrarlo en cualquier parte del texto, entre backticks o no. La
mitigación real es no mencionar NINGÚN fichero fuera de los que el
plan declara en `Modify/Create/Test`, en ningún punto de la prosa ni de
los comentarios de código de ejemplo.

**Segundo intento, con esa corrección aplicada**: se reescribió el
mismo plan sin una sola mención de fichero fuera de los dos objetivo,
verificado antes de soltarlo con un script que replica la lógica exacta
de `get_file_mentions` contra la lista real de ficheros del repo (`git
ls-files`) -- 0 menciones inesperadas confirmadas. **Volvió a fallar los
3 intentos** -- mismo patrón de dos fallos silenciosos, pero el tercero
esta vez por un motivo distinto y más revelador: el modelo entró en un
bucle de autoargumentación contando espacios de indentación del formato
`udiff` ("¿son 2 espacios o 3 para una línea de contexto?"), sin
converger nunca, hasta el timeout de 480s.

**Conclusión, con las dos pruebas juntas (6 fallos consecutivos sobre la
tarea más simple posible, dos veces 3/3)**: la contaminación de contexto
era real y se corrigió, pero NO era la única causa. Con contexto
limpio, el modelo sigue bloqueado por la fragilidad mecánica del propio
formato de diff de texto libre (`SEARCH/REPLACE` o `udiff`, probados
ambos en esta sesión y en la anterior) -- un requisito de precisión
sintáctica sin relación con su capacidad real de razonar sobre el
código. Investigación en paralelo (agente de búsqueda, no implementado
nada) sobre alternativas confirma que esto es un problema conocido de
`aider` frente a modelos no-frontier: **`SWE-agent`** (Princeton,
SWE-bench) usa tool-calling estructurado (comandos JSON tipo
`str_replace_editor`) en vez de diffs de texto libre, corre headless
por diseño, acepta cualquier endpoint OpenAI-compatible (nuestro proxy
`litellm` sin cambios), y DeepSeek sí soporta function-calling real vía
OpenRouter -- viable con el modelo actual, sin cambiar de modelo.
`OpenHands` quedó descartado como primera opción: su propia
documentación pide un modelo "potente", lo contrario de la premisa
económica de este pipeline.

**Decisión de Diego sobre el enfoque de fondo**: ante la propuesta
externa de pasar de "Claude escribe el código completo en el plan" a
"Claude escribe solo un blueprint, el modelo investiga el repo y escribe
el código él mismo" (más fiel al ahorro económico real), Diego coincidió
en que el diagnóstico económico es correcto en teoría, pero señaló que
"la herramienta aider no me está gustando nada, arrastra muchos
problemas" -- la solución no es solo replantear el formato del plan,
también hace falta valorar cambiar de herramienta. Confirmado con
evidencia propia: un blueprint exige que el modelo **explore y narre
más ficheros por su cuenta**, justo el mecanismo que dispara la cascada
de auto-mención -- con `aider` como está, más autonomía real empeoraría
el problema, no lo mejoraría. **Pendiente, sin decidir todavía**: si
seguir con `aider` (mínimo, ya no parece razonable tras dos 3/3
consecutivos con causas distintas), probar `SWE-agent` con el mismo
modelo, o replantear el flujo de planes (blueprint vs. código completo)
una vez resuelta la herramienta. Explícitamente aplazado por Diego
("cuando eso esté nos pondremos a plantear el nuevo flujo") hasta cerrar
primero la pieza 1 de propagación de flora, más abajo.

**Pieza 1 de propagación de flora, implementada a mano**: tras el
segundo fallo, Diego pidió implementar directamente el plan que había
fallado (sin pipeline) y documentar el estado de la funcionalidad --
ver la sección siguiente. Los planes 2-5, ya escritos con el mismo
formato completo (código real, no blueprint) por si se retoma el
pipeline más adelante, quedaron aparcados en
`docs/superpowers/plans/pendientes/` (fuera del directorio que vigila
el centinela), sin implementar.

## Tipos de propagación de flora (2026-09-02) -- pieza 2 de la cola
## "poblar más el mundo", 5/5 IMPLEMENTADA Y MERGEADA (ver cierre real
## más abajo, tras la sección de sustitución de aider por mini-swe-agent)

Segunda pieza de la cola acordada en brainstorming el mismo día que la
distribución causal de flora (1. distribución causal, ya cerrada -- ver
más arriba; **2. este círculo**; 3. cupo de espacio compartido por
celda; 4. catálogo ampliado de especies). Spec completa ya escrita y
aprobada por Diego en
`docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`:
sustituye el mecanismo ciego actual (una planta madura intenta
colonizar un vecino contiguo al azar, sin relación con cómo se dispersa
de verdad una semilla) por tres vectores reales -- viento (reutiliza la
dirección global ya sorteada por mundo), caída (el mecanismo de hoy,
refinado) y zoocoria (un animal come el fruto, dispersa la semilla al
`ALIVIARSE` en otro sitio) -- validados todos contra
`idoneidad_colonizacion` (pieza 1 de la distribución causal), no contra
el chequeo tosco de bioma+agua actual.

Troceada en 5 planes con el mismo formato que ya había funcionado en la
distribución causal (código completo, no blueprint):

1. **Catálogo `tipo_propagacion` -- IMPLEMENTADO** (2026-09-02, a mano,
   tras dos fallos consecutivos del pipeline autónomo sobre este mismo
   plan -- ver sección anterior). `config/flora.yaml`: cada especie
   lleva ahora `tipo_propagacion: viento | caida | zoocoria`
   (`hierba_silvestre`/`liquen`/`musgo` -> viento con
   `alcance_viento_celdas` propio; `manzano` -> zoocoria; `cactus` ->
   caida -- asignación PROVISIONAL, razonada, sin calibrar); más
   `probabilidad_recogida_semilla_zoocoria`/
   `probabilidad_plantar_semilla_en_aliviarse` (también PROVISIONALES).
   Sin ningún consumidor todavía -- ningún sistema del motor lee
   `tipo_propagacion` hasta la pieza 3. `tests/test_flora_tipo_propagacion.py`
   (5 tests), 61/61 en verde, `BOSQUE_AUTO_TICKS=800` sin excepciones.

2-5. **CIERRE REAL (2026-09-02, mismo día): las 5 piezas quedaron
   implementadas y mergeadas** -- lo que sigue es el diseño de cada
   plan tal como se escribió originalmente (narrativa histórica,
   conservada), más una nota de cierre real al final de cada una. Ver
   la sección "Sustitución de aider por mini-swe-agent" más abajo para
   2/5 y 3/5, y la sección siguiente a esa para 4/5 y 5/5 (incluye la
   primera prueba real de planes tipo "blueprint" del proyecto):
   - **2/5**: `nucleo.flora.intentar_colonizar_celda` -- helper
     compartido por los tres vectores, sustituye la validación de
     destino que hoy vive solo dentro de `_intentar_propagacion`.
     **Desviación deliberada de la spec original, encontrada al
     diseñar este plan**: la spec no incluía ningún guard de agua en
     el helper; se añadió uno (`if celda_dest.tiene_agua: return
     False`) porque `sistema_flora.py` ya tenía ese guard con un
     comentario documentando que fue un bug real ya corregido una vez
     ("la propagación colonizaba celdas de río/lago/poza"). **Hallazgo
     colateral real, verificado contra el motor** -- en su momento NO
     corregido: la generación inicial (pieza 1 de la distribución
     causal, ya mergeada) tenía exactamente este mismo bug sin el
     guard -- `colonizar_por_idoneidad` nunca excluía celdas sumergidas,
     medido en 3 semillas (40x40): entre el 5% y el 11% de las celdas
     colonizadas con flora en generación estaban también sobre agua.
     **CORREGIDO el mismo día** (`500c05a`, PR #10
     `feature/2026-09-02-fix-flora-sobre-agua`, primera prueba real de
     plan tipo "blueprint" -- ver detalle en la sección "Piezas 4/5 y
     5/5..." más abajo): `colonizar_por_idoneidad` recibe ahora
     `celdas_con_agua` (reutiliza el resultado ya calculado de
     `generar_cuerpos_agua`, sin recorrer el grid otra vez) y excluye
     las celdas sumergidas antes de sortear especie, misma ley física
     que ya aplicaba `intentar_colonizar_celda` a la propagación en
     tiempo real.
   - **3/5**: integra el helper en `_intentar_propagacion` (vector
     caída) y añade `SistemaFlora._propagar_planta`, el punto único de
     dispatch por `tipo_propagacion` que sustituirá la llamada
     incondicional actual -- con las ramas `viento`/`zoocoria` como
     no-op documentado hasta los planes 4 y 5 (regresión temporal
     deliberada dentro del mismo círculo de trabajo).
   - **4/5**: `ZonaBioma` gana `viento_dx`/`viento_dy` (hoy variables
     locales de `generar_zona_bioma` que se pierden al terminar la
     generación) y `SistemaFlora._propagar_viento` -- sortea distancia
     dentro de `alcance_viento_celdas`, prueba una única celda en la
     dirección del viento dominante ya sorteado por el mundo.
   - **5/5**: componente `Semillas.especie_transportada` (mismo molde
     que `Agarre`, añadido a las 4 especies en `crear_criatura` Y
     `nacer_criatura` -- dos fábricas ECS separadas, mismo hallazgo ya
     documentado para `Agarre`); hooks en
     `_resolver_comer`/`_resolver_aliviarse` de `sistema_recursos.py`;
     persistencia (`VERSION_ESQUEMA` a `0.31-fase0`).

**CIERRE REAL (2026-09-02, mismo día): las 5/5 piezas quedaron
implementadas y mergeadas** -- ver "Sustitución de aider por
mini-swe-agent" (2/5, 3/5) y "Piezas 4/5 y 5/5 de propagación de
flora..." (4/5, 5/5, más el fix del bug de flora-sobre-agua) más abajo.
**Pendiente real que queda de verdad**: asignación de vector por
especie y las constantes numéricas nuevas, todas PROVISIONALES sin
calibrar contra el harness completo; piezas 3 (cupo de espacio
compartido por celda) y 4 (catálogo ampliado de especies) de la cola
"poblar más el mundo" sin empezar.

## Sustitución de aider por mini-swe-agent en el pipeline (2026-09-02) --
## validado dos veces de extremo a extremo, piezas 2/5 y 3/5 de
## propagación de flora ya mergeadas por el pipeline nuevo

Diego, con el balance de la sección anterior ("aider arrastra muchos
problemas, la solución no es solo replantear el flujo sino cambiar de
herramienta"), aprobó investigar y probar `SWE-agent`. Verificado antes
de instalar nada: esta máquina (WSL2) tiene Docker solo en el lado
Windows, sin integración WSL activada -- `SWE-agent` clásico lo exige.
Investigación (agente de búsqueda) encontró que el propio equipo del
proyecto recomienda ahora `mini-swe-agent` ("el agente de 100 líneas")
en vez de `SWE-agent` clásico, con un modo `local` sin Docker (ejecuta
comandos vía `subprocess` directo en el host) pensado justo para
desarrollo normal -- instalación aislada (`uv tool install
mini-swe-agent`, mismo patrón que `aider`), reutiliza el proxy
`litellm` existente sin cambios.

**Mecanismo de fondo, la diferencia real frente a aider**: leyendo
`minisweagent/models/litellm_model.py` del paquete instalado --
`litellm.completion(..., tools=[BASH_TOOL], ...)`, tool-calling
estructurado real (el modelo emite comandos bash -- `sed`, heredocs,
`cat`, `git commit` -- ejecutados en un subproceso, la salida vuelve
como observación) en vez de diffs de texto libre que un parser frágil
tiene que interpretar. Sin ningún mecanismo de "auto-mención de
fichero" que vigilar -- el modelo lee/escribe ficheros él mismo con
comandos reales, no hay ninguna inyección automática de contexto que
pueda descontrolarse.

**Setup real** (dos ajustes de configuración, ninguno documentado de
forma obvia): `MSWEA_CONFIGURED=true` en
`~/.config/mini-swe-agent/.env` evita el asistente interactivo de
primer uso (bloquea en modo no interactivo sin esto);
`MSWEA_COST_TRACKING=ignore_errors` evita un `RuntimeError` real --
litellm no tiene en su tabla de costes ningún registro para el alias
custom `openai/agente-obrero`, y sin este flag `mini-swe-agent` aborta
al no poder calcular el coste de una llamada que sí tuvo éxito.

**Spike inicial (manual, fuera del pipeline)**: mismo modelo, mismo
proxy, plan 2/5 de propagación de flora (`intentar_colonizar_celda`,
dificultad comparable a los 6 fallos consecutivos de aider ese mismo
día) -- completado en un único intento, 15 pasos, sin intervención.
Diff idéntico byte a byte al plan, 0 corrupción, 0 duplicados, 66/66
tests, motor real sin excepciones.

**`run-plan.sh` reescrito** para invocar `mini` en vez de `aider`,
manteniendo intacta toda la lógica agnóstica a la herramienta (gestión
de ramas, `PLAN_START_COMMIT`/`CAMBIOS_REALES`, tests, apertura de PR).
Retirado: el parche de `max_reflections`, `--edit-format`/
`aider-model-settings.yml`, el incrustado manual de contenido de
fichero en el mensaje (mini lee ficheros él mismo). Añadido:
**commit de seguridad** -- a diferencia de `aider` (`--auto-commits`
garantizaba que todo cambio aplicado quedaba comiteado), `mini-swe-agent`
solo comitea si el propio modelo ejecuta `git commit` como una de sus
acciones; si se queda sin turnos/presupuesto antes de llegar a ese
paso, los cambios reales podrían perderse sin comitear -- se añade un
`git add -A && git commit` de respaldo tras cada intento si queda algo
sin comitear. Descubierto útil en la práctica: los pasos "Step N:
Commit" del plan (con el mensaje de commit exacto, pie
Co-Authored-By/Claude-Session incluido) SÍ son ejecutables tal cual
para `mini-swe-agent` -- a diferencia de `aider`, que necesitaba un
aviso explícito para ignorarlos.

**Validación real de extremo a extremo, vía el centinela y `run-plan.sh`
tal cual, no invocación manual**: pieza 3/5 (`_intentar_propagacion` vía
el helper compartido + dispatch `_propagar_planta` por
`tipo_propagacion`) soltada al centinela -- recogida sola, completada en
el intento 1/3, diff idéntico al plan (0 corrupción), 70/70 tests, motor
real sin excepciones, PR #9 abierto y mergeado. Único matiz real: el
modelo no llegó a ejecutar su propio `git commit` final antes de
intentar cerrar la tarea (acción `COMPLETE_TASK_AND_SUBMIT_FINAL_OUTPUT`
que falló) -- el commit de seguridad lo capturó correctamente sin
perder nada, confirmando que esa red de seguridad era necesaria de
verdad, no solo teórica.

**Balance, dos intentos reales sobre el pipeline ya reescrito: 2 de 2
éxitos en el primer intento cada vez**, frente a 0 de más de 6 intentos
con `aider` ese mismo día. Cambia la conclusión de la sección anterior
sobre viabilidad económica: con el mecanismo de tool-calling, el
formato de plan actual (código completo, no blueprint) ya no es la
única palanca posible -- pedirle al modelo más autonomía real (explorar
el repo, decidir la implementación) ya no choca con la fragilidad
mecánica que hundía a `aider`. **Pregunta cerrada el mismo día, ver la
sección siguiente**: si retomar la propuesta original de Diego de
planes tipo blueprint ahora que la herramienta lo permite, o seguir con
el formato de código completo ya validado dos veces -- la respuesta
real, probada contra el motor, fue "blueprint funciona, y hasta mejora
sobre el plan escrito a mano".

**Nota técnica sobre el propio proceso de esta migración, sin relación
con el pipeline en sí**: al mergear el PR #9, `origin/master` había
avanzado por el propio squash-merge de GitHub mientras el `master`
local tenía 8 commits propios nunca empujados al remoto -- confirmado
con `git diff` que el remoto era un superset exacto del local (mismo
contenido, historia squasheada), resuelto con `git reset --hard
origin/master` tras verificar que no había pérdida real de trabajo,
solo de granularidad de commits locales.

## Piezas 4/5 y 5/5 de propagación de flora, más el fix de
## flora-sobre-agua -- primeras pruebas reales de planes "blueprint"
## con mini-swe-agent, cierre completo del arco de propagación (2026-09-02)

Con `mini-swe-agent` ya validado 2/2 sobre planes de código completo
(sección anterior), se probó la otra pregunta que había quedado
explícitamente abierta desde el balance del pipeline: si un plan tipo
**blueprint** (solo la sección de spec, sin código pre-escrito por
Claude) también funciona con esta herramienta -- la propuesta
económica original de Diego, descartada antes por chocar con la
fragilidad de `aider` (más autonomía real solo empeoraba la cascada de
auto-mención de ficheros).

**Primer intento de blueprint -- PR #10, fix de flora-sobre-agua**
(mismo bug señalado como "NO corregido" en la pieza 2/5 de arriba):
1/2 intentos. El primero se atascó en un paso por defecto del flujo de
fábrica de `mini-swe-agent` -- "crear un script para reproducir el
issue" -- porque el propio modelo escribió ese script con una comilla
triple mal cerrada (código lleno de docstrings de comilla triple) y
nunca convergió, agotando los 900s. **Causa raíz corregida, no
parcheada a ciegas**: `.ai-pipeline/mini-agente-obrero.yaml`
(`instance_template` propio, `30dbbcd`) sustituye ese paso por "edita
directo, verifica con la suite de tests real del proyecto (ya sirve de
reproducción)", más un aviso explícito contra escribir scripts de
parche/reproducción en este código. El segundo intento, ya con esa
config, completó limpio en 26 pasos con diseño independiente de
calidad -- `500c05a`, PR #10 mergeado. Documentado también, de paso:
`watch-plans.sh` puede quedar vivo entre sesiones sin que se sepa
(hallazgo operativo, no corregido aquí).

**Segundo intento de blueprint -- pieza 4/5, vector viento**
(`8e6351a`): soltado como spec pura, sin ningún plan de código escrito
por Claude -- `mini-swe-agent` exploró el repo, diseñó
`SistemaFlora._propagar_viento` y `ZonaBioma.viento_dx/viento_dy` por
su cuenta. Verificado independientemente contra el diseño ya
documentado (arriba, en "Tipos de propagación de flora"): equivalente,
**con una mejora real que el propio plan escrito no tenía** -- un
guard explícito para zona sin viento. 76/76 tests, motor real sin
excepciones. El plan 4/5 ya redactado a mano quedó retirado de
`docs/superpowers/plans/pendientes/`, sin uso -- superado por la
prueba, no por decisión de descartarlo antes de intentarlo.

**Pieza 5/5, vector zoocoria** (componente `Semillas`, hooks en
`_resolver_comer`/`_resolver_aliviarse`, persistencia a
`VERSION_ESQUEMA=0.31-fase0`): cerrada con PR #11
(`feature/2026-09-02-propagacion-05-zoocoria`), completando las 3
partes ya diseñadas en la pieza 2/5 original (componente en ambas
fábricas ECS, hooks, persistencia). Con esto, **el arco completo de
"tipos de propagación de flora" (pieza 2 de la cola "poblar más el
mundo") queda cerrado, 5/5**, junto con la "distribución causal de
flora" (pieza 1, ver más arriba) -- quedan piezas 3 (cupo de espacio
compartido por celda) y 4 (catálogo ampliado de especies) sin empezar.

**Conclusión sobre blueprint vs. código completo, la pregunta que
quedaba abierta**: con `mini-swe-agent`, un blueprint puro SÍ funciona
-- de hecho, en la única comparación directa disponible (pieza 4/5)
igualó y mejoró el diseño que Claude había escrito a mano. La
limitación real encontrada no es el formato del plan sino el TIPO de
tarea: `dc64f30` documenta que tareas de calibración de
juicio/estilo (como la poda de comentarios narrativos de la sección
siguiente) fallaron 2/2 con `mini-swe-agent` -- confirmado, esa poda
se acabó haciendo a mano, por Claude, en toda la sesión siguiente (ver
más abajo). El patrón que emerge, con evidencia real de ambos lados:
implementación con criterio de éxito objetivo (tests, comportamiento
verificable) funciona bien delegada, sea blueprint o plan completo;
juicio de estilo sin un criterio de éxito objetivo no funciona
delegado todavía.

## Coste real del pipeline -- instrumentación y una causa raíz de
## discrepancia de ~3x, investigada hasta el fondo (2026-09-02)

Con el pipeline ya migrado a `mini-swe-agent` y probado repetidamente,
Diego pidió medir si de verdad compensa económicamente -- pregunta que
exigió investigar en profundidad, no una respuesta de una línea, porque
la primera fuente de coste consultada resultó no ser fiable.

**Instrumentación** (`707d3bb`, el commit más reciente de esta rama de
trabajo): `run-plan.sh` consulta el balance real de la cuenta de
OpenRouter (`/api/v1/credits`) antes del primer intento y al salir de
cada ejecución (éxito o fallo, vía el `trap EXIT` ya existente),
dejando un registro por ejecución en `.ai-pipeline/costes/costes.jsonl`
(gitignored, igual que `trayectorias/`, best-effort -- nunca tumba el
pipeline si la API no responde). Antes de esto, el coste real de cada
pieza (flora, zoocoria) se calculaba a mano, con el campo
`instance_cost` que `mini-swe-agent` reporta por su cuenta.

**Investigación real de una discrepancia de ~3x, con dos hipótesis
descartadas antes de encontrar la causa correcta** (mismo criterio que
el resto del proyecto: verificar contra la fuente real, no conformarse
con la primera explicación plausible):
1. **Hipótesis 1, descartada**: "aterrizó en un proveedor caro
   (DeepSeek/Fireworks/SiliconFlow oficial)". Comprobado contra el
   catálogo real de OpenRouter -- Diego identificó en el panel que el
   proveedor había cambiado a mitad de la ejecución de zoocoria
   (OpenInference → Baidu/Qianfan), real, pero Baidu cuesta
   $0.065/$0.130 por millón, prácticamente lo mismo que OpenInference
   ($0.050/$0.160) -- no explica un salto de 3x.
2. **Hipótesis 2, descartada**: `instance_cost` de `mini-swe-agent` es
   fiable. Falso -- ese campo asume siempre el proveedor MÁS BARATO del
   catálogo de litellm, con independencia de a cuál haya enrutado
   OpenRouter la llamada de verdad (`sort:"price"` es una preferencia,
   no una garantía; los proveedores baratos pueden estar saturados).
   Verificado contra el balance real de la cuenta para la pieza de
   zoocoria: coste real $0.12 frente a $0.03957 calculado -- ~3x, el
   mismo patrón.
3. **Causa raíz real, confirmada (`300b093`)**: `litellm_model_registry.json`
   no declaraba `cache_read_input_token_cost` para el alias custom --
   `mini-swe-agent`/litellm tratan como GRATIS cualquier token de
   prompt marcado `cached` por el proveedor cuando el modelo no tiene
   tarifa de caché registrada. En un bucle agéntico con contexto
   creciente, el 96.8% del prompt de zoocoria (6.73M de 6.95M tokens)
   estaba marcado `cached` -- casi todo el coste real venía de tokens
   que el cálculo daba por gratuitos. Recalculado con la tarifa real
   añadida: $0.127 contra el balance real medido de $0.12 --
   reconciliado. El fix de flora se recalculó con el mismo método:
   $0.03232 (antes $0.01949 con el cálculo viejo, ~1.66x).

**Cuatro ajustes de coste tras el hallazgo** (`50ee3fd`), directos una
vez identificada la causa (más contexto en caché = más coste real, no
gratis): umbral de elisión de salidas largas bajado (4000/1500+1500,
antes 10000/5000+5000 -- toda salida que quede en contexto se
refactura, a precio de caché, en cada paso siguiente); instrucción para
correr solo tests concretos mientras se desarrolla, suite completa una
única vez al terminar; límite de coste por intento (`-l`) bajado de
0.60 a 0.30 USD (la pieza más cara medida hasta ahora costó $0.127
real); miga de pan en blueprints documentada con su peso económico
real en `guia-tareas.md`.

**Otros ajustes de infraestructura del mismo tramo, encontrados de
paso**: `bda0c14` declaró el pricing real del alias en
`litellm_model_registry.json` (litellm ya no necesita
`MSWEA_COST_TRACKING=ignore_errors` para no fallar, y calcula coste
real por llamada); `6780e88` forzó `extra_body.provider.sort="price"`
tras verificar que ir directo a la API oficial de DeepSeek sería 3-4x
más caro que los proveedores de inferencia más baratos del mismo
modelo de pesos abiertos.

**Pendiente real, explícito**: `.ai-pipeline/costes/costes.jsonl` no
tiene todavía ninguna entrada real -- ninguna ejecución del pipeline ha
corrido desde que se conectó la instrumentación; la próxima tarea
soltada al centinela dará el primer dato de coste medido de extremo a
extremo sin cálculo manual. La pregunta de fondo de Diego ("¿compensa
económicamente?") sigue sin una respuesta agregada -- solo hay costes
puntuales de piezas sueltas ($0.03-$0.13), no un balance sobre varias
ejecuciones.

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

## Cupo de espacio compartido por celda -- pieza 3 de "poblar más el
## mundo", cerrada (2026-09-03, misma tarde)

Diseño completo en `docs/superpowers/specs/2026-09-03-cupo-espacio-celda-design.md`
(brainstorming con Diego, resumen: dos pistas de ocupación
independientes en `Celda` -- especies con `compite_espacio_fisico:
true`, hoy `manzano`/`cactus`, compiten por un cupo real en m²
compartido con `Construccion` vía `nucleo/espacio.py`, huella fija por
especie; especies de cobertura de suelo, `hierba_silvestre`/`liquen`/
`musgo`, no compiten con nada, cohabitan libremente con la pista
competidora). Decisiones reales de la conversación, no autoría de
Claude: Diego rechazó dejar que un árbol bloqueara sin más un refugio
en la misma celda ("no tiene sentido, lo lógico es que cohabiten"),
lo que llevó a separar las dos pistas en vez de compartir un único
gate; también preguntó explícitamente si una criatura consciente
consideraría la hierba un obstáculo físico real -- respuesta que
fijó la categoría `compite_espacio_fisico` como distinción binaria
por naturaleza física de la especie, no un número pequeño calibrado a
ojo. Tala (destruir una `Planta` para liberar su hueco) quedó
señalada explícitamente como acción consciente futura, no construida
aquí -- el bloqueo silencioso (sin búsqueda de celda vecina) sigue el
mismo criterio ya aceptado para construcción-vs-construcción.

**Cierre real, no trivial**: el primer intento real del pipeline
implementó la pieza completa (864 líneas, `nucleo/espacio.py` nuevo,
396 líneas de test) pero el commit quedó huérfano por un incidente de
infraestructura (ver sección siguiente) antes de que Claude lo
recuperara y auditara. Verificado antes de mergear: 110/110 tests en
verde (99 previos + 11 nuevos), dos smoke tests reales
(`BOSQUE_AUTO_TICKS` 1000 y 500 ticks) sin ninguna excepción. Cerrado
manualmente por Claude, no por el flujo de éxito automático del
pipeline -- commit `db817bc`/merge `b5406b9`.

## Reenfoque del pipeline + una tarde de incidentes reales de
## infraestructura (2026-09-03)

Mismo día, después de cerrar la pieza 3, Diego pidió reenfocar
partes del pipeline "que cree que están desactualizadas". Diagnóstico
compartido en conversación: el fichero que Claude dejaba en
`docs/superpowers/plans/` ya no contenía ningún plan real desde el
arco de flora -- solo un envoltorio que apuntaba a la spec ("libertad
total para decidir la forma exacta"). Rediseño acordado en
brainstorming (spec:
`docs/superpowers/specs/2026-09-03-reenfoque-pipeline-spec-no-plan-design.md`):

- `docs/superpowers/plans/` → `docs/superpowers/encargos/` (Claude
  deja un ENCARGO mínimo -- ruta a la spec + qué NO tocar, sin
  repetir boilerplate).
- `.ai-pipeline/watch-plans.sh` → `.ai-pipeline/centinela.sh`,
  `.ai-pipeline/run-plan.sh` → `.ai-pipeline/ejecutar-encargo.sh`
  (nombre fiel a lo que hace cada uno, decidido explícitamente con
  Diego, incluida la pregunta directa sobre si renombrar
  `run-plan.sh` también -- sí).
- `instance_template` de `mini-agente-obrero.yaml` gana un paso 0:
  el propio modelo escribe y comitea su plan real de implementación
  (sobrescribiendo el fichero que `ejecutar-encargo.sh` ya movió a
  `docs/plans/in_progress/`) ANTES de tocar código -- el encargo se
  convierte en plan real en ese momento, no antes.

Implementado en worktree aislado (`.claude/worktrees/reenfoque-pipeline`,
skill `using-git-worktrees`) porque el directorio principal tenía
`mini-swe-agent` corriendo en vivo sobre la pieza 3 en ese momento --
comprobado con `ps aux` antes de tocar cualquier rama, evitando
corromper el trabajo en curso. Mergeado a `master` tras 99/99 tests.

**Cuatro incidentes reales de infraestructura, todos encontrados
soltando la propia pieza 3 de nuevo como primera prueba del flujo
nuevo -- ninguno hipotético, los cuatro con coste real medido**:

1. **Límite diario de OpenRouter, tres reintentos consecutivos
   borraron trabajo real**: `mini` chocó contra `"Key limit exceeded
   (daily limit)"`, reintentó con backoff exponencial hasta que el
   proceso se rindió con código de salida no-0/no-124 (camino de
   "error de infraestructura" de `ejecutar-encargo.sh`), que hacía
   `git branch -D` de la rama SIN comprobar si tenía un commit de
   seguridad con trabajo real -- y el centinela, sin pausa, volvía a
   recoger el mismo encargo de la cola (nunca se había retirado de
   `master`) y repetía el ciclo. Pasó 3 veces seguidas antes de
   intervención manual. **Recuperado** un commit huérfano de 864
   líneas vía `git fsck --unreachable` (los objetos seguían vivos,
   sin GC todavía) a una rama de rescate, subida a `origin` antes de
   arreglar nada -- disciplina de "proteger primero, arreglar
   después". Fix real (`2122d17`): `ejecutar-encargo.sh` compara
   `HEAD` contra `PLAN_START_COMMIT` antes de borrar -- solo borra si
   no hay nada que perder.
2. **El fix anterior no bastaba por sí solo -- dos bugs más
   encontrados en la SIGUIENTE prueba real** (un límite DISTINTO de
   OpenRouter, `"total limit"`, no el `"daily limit"` ya levantado):
   `.ai-pipeline/watch.log` estaba en `.gitignore` pero llevaba
   tiempo trackeado desde antes de esa regla -- sus escrituras
   continuas ensuciaban el árbol de trabajo y hacían fallar `git
   checkout master`, y ese fallo abortaba el script vía `set -e`
   ANTES de llegar al `exit 2` que el centinela necesita para
   detenerse -- el disyuntor del punto 1 nunca se disparaba pese a
   ser exactamente el caso para el que se diseñó. Fix (`e56269a`):
   `git rm --cached` sobre `watch.log`, y `|| true` en cada paso de
   limpieza para garantizar que se llegue al `exit 2` pase lo que
   pase. **Confirmado funcionando la vez siguiente**: el centinela se
   detuvo solo con el mensaje `"CENTINELA DETENIDO: fallo de
   infraestructura externa"` -- la causa real esa vez ni siquiera era
   de OpenRouter, era nuestro propio `max_budget: 1.00` USD/día del
   proxy, agotado por la suma de reintentos del propio día.
3. **PR vacío reportado como éxito** (mismo día, tras levantar todos
   los límites externos): el modelo exploró 66 pasos correctamente y
   luego dejó de emitir tool calls 6 veces seguidas (rechazado por
   `mini-swe-agent`: "cada respuesta debe incluir al menos una
   llamada a herramienta"), cerrando la tarea sin tocar ni un fichero
   de código. El pipeline lo marcó como ÉXITO -- tests "en verde"
   trivialmente, PR #12 con diff 0/0 -- porque el chequeo
   `CAMBIOS_REALES` excluía `docs/plans/`/`.ai-pipeline/` pero NO
   `docs/superpowers/encargos/`, así que el simple borrado
   administrativo del propio fichero de encargo (que pasa siempre,
   toque código o no) ya contaba como "1 cambio real". Mismo tipo de
   fallo que ese chequeo se diseñó para evitar en 2026-09-01. Fix
   (`00c7737`): excluir también `docs/superpowers`. PR #12 cerrado,
   rama vacía borrada.
4. **Cuarto intento, ya con los tres fixes aplicados, funcionó de
   punta a punta**: el modelo escribió y comitó su propio plan
   (`plan: cupo de espacio compartido por celda...`, confirmando que
   el paso 0 nuevo funciona), llegó al paso 136 sin atascos, y volvió
   a chocar solo con el tope diario del proxy -- de nuevo con el
   trabajo real preservado (964 líneas) y el centinela deteniéndose
   correctamente. Ver sección anterior para el cierre final (manual,
   por Claude).

**Balance honesto**: el reenfoque del pipeline en sí (renombrado +
paso 0) funcionó a la primera. Los tres bugs de infraestructura
NINGUNO estaba relacionado con el reenfoque -- eran fallos latentes
del código ya existente (`watch.log` trackeado desde antes,
`CAMBIOS_REALES` sin excluir la carpeta correcta) que solo salieron a
la luz porque esta tarde de pruebas generó, por primera vez, la
combinación exacta de circunstancias (límite externo + trabajo real
ya comiteado + un PR completamente vacío) que los exponía. Todos
corregidos y verificados con una repetición real, no solo con
lectura de código.

## Catálogo ampliado de especies de flora -- pieza 4 de "poblar más el
## mundo", cierra el arco (2026-09-03, misma tarde)

10 especies nuevas, 2 por bioma que hasta hoy tenía solo una
(`pradera`: `flor_silvestre`+`arbusto_espinoso`; `desierto`:
`arbusto_desertico`+`hierba_desertica`; `montana`: `pino`+
`arbusto_montano`; `tundra`: `arbusto_artico`+`hierba_artica`) más 2
en `bosque` (`roble`+`helecho`, pese a ya tener 2 -- Diego señaló que
un bosque real es el bioma más biodiverso de todos, así que 2 seguía
siendo poco). Diseño cerrado en conversación, sin spec aparte
(bounded, sin decisión de arquitectura pendiente): mismo patrón de
catálogo exacto que las 5 especies previas, cero mecanismo nuevo.

**Hallazgo real al diseñar, no al implementar**: la primera propuesta
del roble era "solo madera, sin alimento" con `tipo_propagacion:
zoocoria` -- verificado contra `sistema_recursos.py` que zoocoria
exige un recurso de categoría `alimento` de verdad (el enganche de
`Semillas.especie_transportada` solo se dispara al comer), así que
sin bellotas comestibles el roble nunca se habría propagado pese a
tener el vector "correcto" configurado. Corregido antes de escribir
una sola línea de config. De paso, Diego preguntó si "las ardillas
cogen bellotas" necesitaba un mecanismo dedicado -- confirmado que
zoocoria YA es genérica (cualquier criatura que coma el recurso puede
dispersarlo), así que la idea emerge sola sin tocar nada.

**Implementado directamente por Claude, no vía pipeline** -- el proxy
tenía el tope diario agotado tras las pruebas de la pieza 3 ("hazlo
tú", Diego). Verificado: 116/116 tests en verde (6 nuevos), smoke
test real de 3000 ticks, y confirmado contra la base de datos real
(no solo "no lanzó excepción") que las 10 especies nuevas -- incluidas
las 6 competidoras por espacio -- tienen entidades `Planta` reales en
el mundo tras la corrida. Commit `0afe91d`.

Con esto, **la cola completa de "poblar más el mundo" queda cerrada**
(distribución causal de flora, tipos de propagación, cupo de espacio,
catálogo ampliado -- las 4 piezas).

**Pendiente real, explícito**: todos los rangos de
preferencia/tasas/huella_m2 de las 10 especies nuevas son
PROVISIONAL, sin calibrar contra el harness completo, mismo criterio
que el resto del catálogo. Propagación multi-vector simultánea por
especie (p.ej. un roble que se disperse por caída Y por zoocoria a la
vez) señalada como círculo futuro, no construida -- `tipo_propagacion`
sigue siendo un único valor por especie. Evaluar modelos alternativos
de OpenRouter para el pipeline (Diego pidió comparar coste/fiabilidad
real de `deepseek-v4-flash-0731` contra candidatos como
`z-ai/glm-4.7-flash`, posicionado para *"long-horizon task planning y
tool collaboration"* -- justo el punto débil visto hoy) quedó
explícitamente aplazado a una conversación futura, sin decidir nada
todavía.

## Reconstrucción de la biblioteca de sprites + cuatro correcciones reales
## encontradas verificando contra el visor en marcha (2026-09-04)

Sesión arrancada retomando el estado real de `master`: entre la migración
del 24-08 y hoy, `presentacion/assets/` (la biblioteca de sprites del
Códice Cartográfico, ver la Nota de cierre del 29-08-2026 más arriba)
había quedado **borrada por completo** (commit `20999a4`, "borrados
assets antiguos") tras un primer intento parcial de recorte manual desde
`presentacion/nuevosAssets/` (10/12 hojas, commit `f6c3634`) -- ninguno
de los dos commits es de esta sesión, se encontraron ya en `master` al
arrancar. `presentacion/vista_web.py` seguía intacto y esperando esa
carpeta (`RUTA_ASSETS`, `construir_manifiesto_assets()`) sin ningún
cambio de código -- el visor no estaba roto, estaba huérfano: sin
ficheros que servir, caía en silencio al dibujo vectorial de siempre
(diseño ya previsto, "ninguna categoría vacía rompe el visor").

### Extracción de 234 sprites desde `nuevosAssetsDefinitivos/`

Diego pidió reconstruir la biblioteca desde una fuente nueva y más
reducida, `presentacion/nuevosAssetsDefinitivos/` (10 hojas: pares
`<bioma>Macro`(tinta)/`<bioma>Micro`(color) por bosque/desierto/pradera/
tundra, más 4 hojas sueltas de montañas, más 6 hojas de pose por
criatura). Inspeccionadas una a una (no solo por nombre de fichero)
antes de tocar nada -- confirmó que el contenido real encaja con la
convención que el visor ya esperaba (flora/flora_color, relieve/
relieve_color, agua, criaturas_poses) pero con mapeos NO literales por
carpeta: el pino "de verdad" (sin nieve) está dibujado en la hoja de
bosque, no en la de montaña; el liquen está en la hoja de tundra, no en
la de montaña -- la fuente agrupa por tema visual real, no por especie
del catálogo del motor.

**Método de extracción** (`presentacion/arnes/extraer_sprites_definitivos.py`,
nuevo): detección automática de sprites individuales por componentes
conexas (distancia al fondo estimado de las esquinas + dilatación
morfológica para fusionar el hachurado disperso de la tinta en un único
blob por sprite, validada visualmente hoja a hoja con una pasada de
depuración con cajas numeradas antes de confiar en ella) + recorte con
alfa de zona muerta + rampa (mismo criterio que ya documentaba la
biblioteca anterior, evita el halo rectangular que costó un bug real la
primera vez que se intentó esto). El mapeo índice-de-detección → nombre
de fichero es una tabla escrita a mano revisando cada hoja, no
automática.

**Hallazgo real durante la extracción, no anticipado**: el sistema
`FORMACIONES_POR_BIOMA` de `vista_web.py` (formaciones macro -- un
cluster entero de celdas contiguas estampado como una sola silueta
panorámica) ya leía activamente cuatro pools --
`relieve/cordillera_*`, `relieve/masa_desierto_*`,
`relieve/masa_tundra_*`, `flora/masa_bosque_*` -- que llevaban vacíos
desde el borrado (montaña además llegó a estar desconectada de esa
tabla en su día, según el propio comentario del código). Sin
saberlo, el borrado de assets no solo quitó sprites individuales,
dejó inerte un sistema de formación macro entero. Identificadas las
siluetas panorámicas correctas en las hojas fuente (filas anchas de
dunas/colinas/skyline de bosque) y extraídas también.

**Aproximaciones provisionales, aprobadas explícitamente por Diego** (sin
sprite fuente real disponible): `arbusto_montano` y `hierba_artica`
reutilizan sprites de pradera (mismo criterio que ya aceptaba `liquen`/
`musgo` en la biblioteca anterior, "sin gemela en tinta todavía");
`lobo_andar_s` usa un único frame de la pose de carrera frontal en vez de
un ciclo de 4 (la hoja fuente no trae ciclo de paso hacia cámara para
lobo). `criaturas_poses/{especie}_andar_{dir}_f2/f3/f4.png` (frames
extra del ciclo de paso) se extrajeron por decisión explícita de Diego
pese a no tener consumidor todavía (el visor solo dibuja una pose
estática, sin animación) -- listos si se añade animación a futuro.
Documentado completo en `presentacion/assets/README.md` (nuevo,
reconstruye la convención de nombres que el README anterior --
borrado junto con la carpeta -- ya documentaba).

**Verificado en tres niveles, no solo "el script no lanzó excepción"**:
(1) composición de una muestra sobre fondo de color (no blanco) para
confirmar que el alfa no dejaba halo -- limpio en las 234; (2) servidor
real (`BOSQUE_MODO_VISUAL=1`) + petición HTTP real a `/assets_manifest.json`
y a ficheros concretos (`200`, PNG real, dimensiones correctas, guardia
anti path-traversal intacta); (3) **captura real del canvas con
Playwright** (headless Chromium, instalado en el sandbox --
`chrome-headless-shell` necesitaba `libnspr4`/`libnss3` del sistema,
Diego los instaló entre sesiones) -- confirmó visualmente montañas con
variantes de color, árboles/cactus/agua renderizando bien.

Commit `d6e4e5a`. Diego afinó el resultado a mano tras verlo (commit
`2756955`, "ajuste sprites", autor `Prototipo Bosque` -- otra
herramienta/sesión, no esta): retiró el manzano en tinta (débil, sin
marcas de fruto distinguibles) y lo reutilizó como `masa_bosque`;
podó a la mitad las variantes de `formacion_color` y retiró
`masa_tundra_color`/algunos `pico` de nieve; añadió 7 variantes nuevas
de `flor_silvestre_color`. Verificado que sus retiros no rompen nada
(`masa_tundra` siempre lee de `relieve/` con independencia del modo
color, según la propia tabla `FORMACIONES_POR_BIOMA`).

### Cuatro correcciones reales al visor, encontradas verificando la
### captura real (no solo leyendo el código)

Pedido explícito de Diego tras ver las primeras capturas ("el mapa
debería aparecer centrado... el zoom debería ser aún mayor... no veo
que haya hierba por ningún lado, ni flores"):

1. **Centrado automático al cargar**: `centrarCamara()` solo estaba
   enlazada al botón "Centrar mapa", nunca se llamaba al arrancar la
   página -- se dispara ahora una vez, la primera vez que hay datos
   reales, sin pisar el pan/zoom del usuario después.
2. **`ZOOM_MAXIMO` 8.0 → 20.0** -- a 8x un conejo (peso real ~1.5kg,
   `escalaPorPeso` muy bajo contra la referencia de 90kg) medía ~14px de
   alto en pantalla, casi invisible.
3. **Marco perimetral de medio/micro retirado por completo**
   (`dibujarMarco`, función eliminada) -- Diego, viendo una captura real,
   confirmó que bajo la proyección Caballera no se leía como borde de
   mapa reconocible (aparecía como una línea/diagonal suelta). El marco
   de códice a nivel macro (`dibujarMarcoCodice`) no se tocó.
4. **Bug real de datos, no de sprites -- `plantas_por_celda` solo
   guardaba UNA planta por celda `(x,y)`** en el DTO de
   `construir_instantanea` (`presentacion/vista_web.py`): desde "cupo de
   espacio compartido por celda" (2026-09-03, más arriba) una especie de
   cobertura (hierba_silvestre, flor_silvestre, liquen, musgo) puede
   cohabitar la celda con una especie competidora (árbol/arbusto), y la
   última en sobrescribir la clave ganaba en silencio. Confirmado contra
   el motor real (semilla 42): **101 celdas con cobertura oculta**.
   Corregido: pasa a ser una lista; los dos consumidores JS (sello real y
   fallback vectorial) iteran todas las plantas de la celda, con offset
   propio por índice para que no coincidan pixel a pixel.

Verificado con Playwright contra el servidor real en cada paso (captura
sin clicar el botón, flores conviviendo con arbustos, marco ausente) y
116/116 tests en verde. Commit `280fea9`.

**Pendiente real, explícito, NO resuelto en este círculo -- diseño
aplazado a conversación futura**: las criaturas pequeñas quedan tapadas
por árboles/montañas grandes vecinos incluso a zoom alto -- confirmado
invocando `construirElementoCriatura()`+`el.dibujar()` manualmente sobre
fondo sólido (el sprite se ve perfecto aislado) y comparando contra el
render real en contexto (invisible junto a un pico o un manzano grande).
Causa: el Y-sort por punto de anclaje no tiene en cuenta que el lienzo de
un sprite grande se desborda visualmente mucho más allá de ese punto --
la misma limitación que el propio código ya documentaba ("un gnomo tras
un pico al sur queda oculto tras él"), ahora mucho más notoria porque la
flora real puebla el mapa de verdad. Diego pidió explícitamente diseñarlo
en conversación aparte antes de tocar el algoritmo de ordenación.

### Fracción de siembra inicial de flora -- asimetría real entre pista
### competidora y no-competidora, corregida

Diego, viendo el mapa poblado de verdad por primera vez, señaló que
"todo el mapa está lleno de arbustos" y preguntó si el motor siembra
plantas en todas las celdas posibles. Investigado contra el motor real
(semilla 42, `main.py:sembrar_poblacion_inicial`/`sembrar_flora_inicial`
llamadas directamente, no solo lectura de código): **sí, casi** -- pero
solo para la pista COMPETIDORA (árboles/arbustos,
`compite_espacio_fisico: true`):

| Especie | Compite | Cobertura real de su bioma |
|---|---|---|
| arbusto_espinoso | sí | 91.3% |
| roble / manzano | sí | 80.8% c/u |
| cactus / arbusto_desertico | sí | 98.6% c/u |
| arbusto_artico | sí | 100% |
| hierba_silvestre | no | 3.4% |
| flor_silvestre | no | 3.8% |
| liquen | no | 6.7% |

Medido también que la IDONEIDAD de colonización (`idoneidad_colonizacion`)
no es la causa -- hierba_silvestre y arbusto_espinoso superan el umbral
en el 100% de las mismas celdas de pradera. La causa real, encontrada
leyendo `main.py:sembrar_flora_inicial`: la pista no-competidora ya
pasaba por `fraccion_siembra_inicial` (0.08) desde antes; la pista
competidora (añadida en "cupo de espacio compartido por celda",
2026-09-03) sembraba una `Planta` por CADA colocación que
`colonizar_por_idoneidad` le asignaba, sin ningún muestreo -- una
asimetría real entre dos mecanismos que evolucionaron por separado, no
una diferencia de clima.

**Diseño acordado con Diego** (rechazó explícitamente volver al sistema
de manchas pre-causal: "no volver a la estructura anterior que diseñaba
las manchas de flora sin causalidad"): sembrar solo individuos
FUNDADORES dispersos de ambas pistas, y dejar que la propagación diaria
ya causal por especie (`sistema_flora.py`, caída/viento/zoocoria, arco
"tipos de propagación de flora" ya cerrado) genere el agrupamiento en
manchas/bosquecillos de forma emergente -- sin autorar ninguna forma de
mancha, cumpliendo el principio de leyes neutras.

Implementado: `fraccion_siembra_inicial` 0.08 → 0.35 (cobertura, sube);
nueva `fraccion_siembra_inicial_competidora` = 0.15 (pista competidora,
antes sin fracción -- baja). Verificado antes/después: arbusto_espinoso
91.3%→13.7%, hierba_silvestre 3.4%→14.8%, liquen 6.7%→29.9% -- ambas
pistas convergen a un rango mucho más parecido, ninguna satura su
bioma. 116/116 tests en verde, 3000 ticks reales sin excepciones.
Ambos números PROVISIONAL. Commit `4edd1e3`.

### Concordancia de género en el narrador

Diego, leyendo la crónica en vivo del visor, señaló "un ardilla entra en
crisis mental" -- "ardilla" es femenino en español con independencia del
sexo del individuo (igual que "jirafa"), pero las cuatro plantillas de
`presentacion/narrador.py` (Muerte/Herida/CrisisMental/Nacimiento)
tenían el artículo "un" fijo en el texto -- nunca delatado por
gnomo/lobo/conejo, las tres especies restantes, todas masculinas. De
paso, encontrado el mismo problema en el participio de Herida ("resulta
herido" → "resulta herida" para ardilla). `_contexto()` calcula ahora
`articulo`/`terminacion` una vez por evento a partir de un catálogo
cerrado de especies femeninas (`_ESPECIES_FEMENINAS = {"ardilla"}`), sin
tocar la función genérica de disposición por peso. Primer test dedicado
de `narrador.py` (`tests/test_narrador_genero.py`, no tenía ninguno).
122/122 tests en verde, verificado también contra el servidor real
corriendo. Commit `18e7862`.

### Percepción de amenaza ponderada por agresividad, no solo por peso

Diego, tras el fix del narrador, notó que la crónica mostraba muchas
líneas de ardilla en crisis mental/catatonia. Investigado a fondo contra
el motor real (3000 ticks, semilla 42, eventos `CrisisMental` contados
por especie): el total agregado en realidad mostraba a CONEJO por
delante de ardilla (145 vs 78 en 3000 ticks -- 4.8 vs 2.6 crisis por
individuo inicial), pero repetir la ventana exacta de los primeros ~30
ticks (la que Diego había visto en pantalla) sí reproducía el patrón
observado casi exacto (14 de ardilla, 5 de conejo, 1 de gnomo).

**Causa raíz real de la asimetría conejo/ardilla, encontrada en
`nucleo/disposicion.py`**: la detección de amenaza
(`posicion_amenaza_mas_cercana` → `posicion_mas_cercana_por_disposicion`,
`buscar_mayor=True`) es puramente por RATIO DE PESO -- cualquier
candidato suficientemente más pesado cuenta como amenaza, sin mirar en
ningún momento si es un depredador real. Conejo (1.5-3.0kg) supera el
umbral de amenaza frente a ardilla (0.3-0.6kg, magnitud de peso
0.48-0.70 según el individuo), así que el "pool de amenazas" de ardilla
incluye gnomo+lobo+conejo (54 individuos), mientras el de conejo es solo
gnomo+lobo (24) -- ardilla nunca cuenta como amenaza para conejo por ser
más ligera.

**Primera propuesta de Claude, rechazada por Diego con razón** ("¿tiene
sentido que un conejo asuste a una ardilla igual que un depredador?"):
un gate binario "solo depredadores reales" (`medio_alimentacion==
'cazar'`, hoy solo lobo). Diego la corrigió: un caballo (herbívoro
grande, no depredador) SÍ debería asustar a una ardilla solo por tamaño
-- lo que falta no es un filtro binario por especie, es que la
AGRESIVIDAD del candidato (`Temperamento.agresividad`, ya existe, sorteo
individual dentro de rango racial) module cuánta amenaza percibida
genera, además del tamaño. "Una criatura más grande y además agresiva es
motivo para estar muy insegura" -- pero un conejo (algo más grande, poco
agresivo) no debería contar como amenaza plena.

**Diseño cerrado y verificado con rangos reales**
(`config/poblacion.yaml`: agresividad lobo 0.5-0.9, gnomo 0.1-0.4,
conejo/ardilla 0.05-0.2): puntuación combinada `magnitud_por_peso +
peso_agresividad × agresividad_candidato`, comparada contra un umbral
PROPIO de amenaza (antes compartía `depredacion.umbral_disposicion_caza`
con la disposición de caza -- deja de compartirlo, cada uso con su
propia calibración). Umbral subido de 0.5 a 0.65 (conejo, magnitud
0.48-0.70, deja de superarlo en la mayoría de individuos) con
`peso_agresividad=0.3` (gnomo ~0.76 y lobo ~0.84 lo siguen superando
solo por tamaño, sin necesitar agresividad -- así un "caballo"
hipotético seguiría siendo amenaza real). Respeta el principio de
diseño ya declarado en el propio módulo ("cada sistema que consuma la
disposición por peso la combina con sus propios atributos... es lo que
pide el principio de leyes neutras") -- la ponderación por agresividad
vive en un parámetro opcional nuevo (`peso_agresividad_candidato`,
0.0 por defecto) de `posicion_mas_cercana_por_disposicion`, sin tocar
su comportamiento para depredación/pareja/territorio, que no lo pasan.

Los TRES consumidores reales de "amenaza" en el motor (drenaje de
`Necesidades.seguridad` en `sistema_necesidades.py`, dirección de HUIR
en `sistema_movimiento.py`, deseo de empuñar arma en
`sistema_decision.py`) actualizados de forma consistente -- una sola
noción de amenaza en todo el motor, no una versión distinta por sistema.

**Verificado, resultado honesto y matizado**: a 3000 ticks reales, el
desequilibrio agregado conejo/ardilla se corrigió con claridad (conejo
145→84, ardilla 78→86 -- casi a la par). Pero repetida la ventana de los
primeros ~30 ticks, la ardilla SIGUE dominando (18 vs 3) -- el fix
corrige exactamente el mecanismo que Diego señaló (conejo-como-amenaza-
de-ardilla) y mejora el balance agregado, pero no es la explicación
completa del arranque de partida concreto que motivó la pregunta; gnomo
(18 individuos, amenaza real solo por tamaño, correctamente) parece
pesar más en ese arranque específico. Señalado explícitamente a Diego,
quien decidió dejarlo así por ahora -- investigar el porqué del
arranque queda como pendiente real, sin decidir si se retoma.

129/129 tests en verde (7 nuevos, `tests/test_amenaza_agresividad.py`,
primer test dedicado de `nucleo/disposicion.py`/`nucleo/amenaza.py`, no
tenían ninguno). **CORREGIDO 2026-09-04**: la nota anterior de este
párrafo decía "sigue sin comitear a fecha de esta nota" -- quedó
desactualizada sin corregir; el cambio (`nucleo/disposicion.py`,
`nucleo/amenaza.py`, `config/combate.yaml`, tres sistemas consumidores)
en realidad ya se comiteó ese mismo día (`4abf887`), antes incluso de
que se escribiera la actualización de este documento (`ca77a7e`) --
inconsistencia real entre dos commits de la misma sesión, encontrada al
auditar `git log` contra CLAUDE.md antes de añadir la sección siguiente,
no de memoria.

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

## Investigación de causas del colapso reproductivo de gnomo (2026-09-04,
## misma tarde, tras cerrar el arco "hilo individual")

Arranque real: verificado que una hembra gestante NO tiene mayor riesgo
de morir por tick que cualquier otra hembra adulta (ratio 0.59x,
gestar es ligeramente MÁS seguro, no menos) -- el 95-96% de fracaso
reproductivo medido antes es pura matemática de exposición (riesgo de
fondo compuesto sobre 4800-6240 ticks de gestación). Diego pidió
investigar la causa de fondo y proponer soluciones; delegado a un fork
con instrucciones explícitas de no tocar código real, solo medir contra
el motor (arneses en scratchpad, no en el repo:
`diagnostico_riesgo_gestacion.py`, `diagnostico_causas_colapso.py`, 5-7
semillas × 6000-9000 ticks, sin persistencia SQLite para velocidad).

**Hipótesis inicial, refutada por datos reales**: se sospechaba que
gnomo, al ser consciente, queda exento del "sesgo de territorio"
(`sistema_movimiento.py:_calcular_deambular`) y por tanto vaga más lejos
de la comida conocida. Medido: gnomo es la especie MEJOR alimentada de
las 4 (saciedad media 0.736, solo 9.16% del tiempo en crisis <0.2,
distancia media a comida 0.32 celdas) -- muy por delante de lobo
(0.490/27.12%), conejo (0.653/21.93%) y ardilla (0.620/23.63%).
Descartada esta vía por completo.

**Causa real, medida con dos hallazgos que se combinan**:
1. **Depredación real y letal**: 67 encuentros lobo-gnomo detectados
   (radio≤3, 5 semillas × 6000 ticks), **47.76% terminaron en la
   muerte del gnomo** dentro de los 500 ticks siguientes. Mecánicamente
   esperable -- `magnitud_disposicion_por_peso` entre lobo (60-90kg) y
   gnomo (8-15kg) da ~0.65 de disposición de caza solo por la diferencia
   de masa. Muertes totales en la muestra: gnomo 45 depredación + 44
   inanición (90 total) frente a conejo 656 y ardilla 168 -- gnomo muere
   MENOS en términos absolutos que las otras dos especies.
2. **Sin ningún margen reproductivo que compense ni siquiera esa cifra
   menor**: comparando gestación/camada/factor_base_concepción de las 4
   especies (`config/poblacion.yaml`) -- gnomo tiene la PEOR combinación
   posible de los tres a la vez: gestación más larga con diferencia
   (200-260 días, 4-13x más que las otras), camada fija en exactamente 1
   (sin margen), y la tasa de concepción más baja del catálogo (empatada
   con lobo, 0.0033). Lobo comparte esa misma tasa de concepción baja
   pero la compensa con gestación 4x más corta (60-75 días) y camada
   4-6x mayor -- con el riesgo de fondo medido, la supervivencia esperada
   de una gestación de lobo es ~40% frente al 4% de gnomo. **El
   rendimiento reproductivo esperado por intento de gnomo es
   aproximadamente 50 veces menor que el de lobo**, pese a partir de la
   misma probabilidad de concebir.

**Conclusión causal**: gnomo no muere de forma anormal -- muere a un
ritmo razonable para su tamaño y la densidad de depredadores. Lo que no
tiene es NINGÚN margen reproductivo para absorber ese ritmo, porque su
estrategia (gestación larguísima + camada de 1, un patrón k-estratega
puro) parece haberse calibrado sin relación real con el riesgo de fondo
que el resto del motor ya produce -- mientras que conejo/ardilla
(r-estrategas: gestación corta, camadas grandes, concepción más
frecuente) sostienen población pese a sufrir MÁS muertes absolutas,
simplemente porque las reemplazan mucho más rápido.

**Propuestas entregadas por el fork, ninguna implementada, decisión
pendiente de Diego**:
- **A (recomendada primero)**: recalibrar conjuntamente gestación/
  camada/factor_base_concepción de gnomo contra el riesgo de fondo ya
  medido -- mismo criterio implícito que ya sostiene a lobo, calibración
  numérica pura, sin mecánica nueva.
- **B**: reducir el riesgo de fondo general (inanición/depredación) si
  el harness completo confirma que es demasiado agresivo para cualquier
  actividad sostenida de miles de ticks -- palanca más neutral (afecta a
  las 4 especies igual), conecta directamente con "Sobrepoblación..."
  ya documentada arriba.
- **C**: ley física de movilidad reducida en gestación avanzada
  (reencuadre de la idea original de Diego de "pareja que recolecta para
  la embarazada" -- pero SIN depender de que exista pareja/asentamiento,
  ambos frágiles hoy; una hembra grávida se mueve/expone menos por la
  carga física real, ley biológica general aplicable a cualquier
  especie que gestee). Más superficie de diseño nueva que A/B.

**Pendiente real, explícito**: no se midió encuentro/captura real para
lobo-conejo ni lobo-ardilla (solo lobo-gnomo) -- no se puede confirmar
si la letalidad por encuentro de gnomo es anómala frente a otras presas
o refleja el mismo patrón general; las cifras de riesgo de fondo vienen
de 5-7 semillas, no del harness completo de 15×12000 ya pendiente desde
la sección "Sobrepoblación...". ~~Sin decisión tomada sobre cuál de las
3 propuestas seguir -- pendiente de conversación con Diego.~~
**ACTUALIZACIÓN el mismo día, ver la sección siguiente: la Propuesta A
de aquí (recalibrar gnomo hacia el perfil de lobo) queda SUPERADA -- se
descubrió que lobo también fracasa reproductivamente, así que copiar su
perfil no habría arreglado nada.** No se tache el texto de arriba
porque documenta con fidelidad el razonamiento y los datos disponibles
en el momento en que se escribió -- es la investigación siguiente la
que lo corrige, no un error de lectura de esta.

## Sesgo de agrupamiento al construir refugio + hallazgo que reinterpreta
## la causa del colapso: lobo también fracasa, no solo gnomo (2026-09-04,
## misma tarde, implementado directamente por Claude a petición de Diego)

Diego propuso una vía distinta a las tres anteriores, mejor fundamentada
biológicamente: en vez de recalibrar números o depender de mecanismos
sociales (pareja/asentamiento, ambos frágiles), preguntó si la propia
consciencia de gnomo debería traducirse en comportamiento social que
compense su bajo rendimiento reproductivo -- la estrategia real de
especies k-estrategas (primates, elefantes, cetáceos): cooperación,
vigilancia compartida, reparto de comida, en vez de reproducir más
rápido. Antes de diseñar ese mecanismo, se midió si tenía sentido
temporal: **cuando un asentamiento SÍ se forma, lo hace muy rápido
(tick 192-384, 8-16 días) -- mucho antes que cualquier gestación**, así
que la velocidad no es el problema. El problema real es que **solo se
formaba en 4/10 semillas (40%)** -- fiabilidad de formación, no
velocidad.

**Implementado (commit `99a2bff`)**: sesgo de agrupamiento en
`sistema_movimiento.py:_calcular_construir`, dos capas que reutilizan
mecanismos YA existentes (mismo criterio de leyes neutras que
`_calcular_dormir` ya aplicaba) -- (1) si el individuo recuerda un
refugio (memoria `objetivo_recordado(mem, "refugio", ...)`, que YA no
distingue de quién es, se registra al dormir sin amenaza cerca sea o no
el refugio propio), camina hacia él en vez de construir aislado; (2) sin
recuerdo, mismo sesgo gregario que ya usa deambular/dormir -- busca al
conspecífico más cercano según sociabilidad propia. Sin ninguno de los
dos, o ya cerca, construye en su posición actual -- comportamiento
original intacto. 4 tests nuevos (`tests/test_construir_agrupamiento.py`),
199/199 en total.

**Verificación A/B a escala real, 30 semillas nuevas (101-130) x
8000 ticks, un worktree en el commit padre (`92d384f`, sin el fix) y
`master` (`99a2bff`, con el fix) -- mismo criterio metodológico ya
aprendido con el fix de fertilidad (comparar DISTRIBUCIONES sobre
muchas semillas nuevas, no pares puntuales, porque añadir una tirada de
rng desplaza la secuencia de todo lo demás)**:

- Sin el fix: 7/30 (23.3%) formaron asentamiento.
- Con el fix: 8/30 (26.7%).

**Veredicto honesto: mejora dentro del ruido, no significativa a este
tamaño de muestra.** El mecanismo es correcto (verificado con tests
dirigidos) y se mantiene -- ley limpia, coste cero, sin regresión -- pero
**no resuelve el problema de fondo**: los asentamientos siguen sin
formarse en ~73-77% de las partidas con o sin el cambio. La causa real
no estaba en cómo se posicionan los refugios.

### El hallazgo real: inanición domina las 4 especies, y lobo fracasa
### reproductivamente igual o peor que gnomo

Aprovechando la escala de la prueba, Diego pidió auditar más ampliamente
mientras se corría. Datos reales (10 semillas nuevas, 201-210, 8000
ticks -- recortado de 30 semillas/2h de cómputo a petición explícita de
Diego tras medir el ritmo real):

| Especie | Muertes totales | Depredación | Inanición | Vejez | Concepciones → Nacimientos |
|---|---|---|---|---|---|
| gnomo | 180 | 37.8% | 58.3% | 3.9% | 44 → 3 (6.8%) |
| **lobo** | 60 | 0% | **90.0%** | 10.0% | 2 → **0 (0%)** |
| conejo | 4694 | 3.2% | 74.3% | 22.5% | 1882 → 4642 (sostiene de sobra) |
| ardilla | 352 | 21.6% | 65.9% | 12.5% | 32 → 52 (sostiene) |

**Esto invalida la mitad central de la conclusión causal de la sección
anterior.** Se había concluido que gnomo fallaba por tener "la peor
combinación reproductiva" mientras lobo "compensaba con gestación corta
y camadas grandes" -- un argumento calculado sobre el papel a partir de
las cifras de `config/poblacion.yaml`, nunca verificado contra si lobo
REALMENTE llegaba a reproducirse en la práctica. No llega: **0% de
éxito reproductivo, peor que gnomo**, porque el 90% de las muertes de
lobo son por inanición -- el depredador se muere de hambre antes de
tener ocasión de aparearse, con solo 6 lobos fundadores y sin ningún
encuentro de caza medido en esta corrida que sugiera que la presa
disponible (gnomo/conejo/ardilla, los tres existen en la simulación) es
el problema.

**Conclusión causal revisada**: no es "gnomo tiene mala genética
reproductiva frente a lobo" -- **la inanición es letal de forma
sistémica para las 4 especies a la vez** (58-90% de las muertes según
la especie), y gnomo y lobo chocan contra ese mismo muro por caminos
distintos que ninguno comparte con conejo/ardilla: gnomo por ventana de
exposición reproductiva demasiado larga, lobo porque su población de
depredadores no se sostiene cazando lo suficiente para sobrevivir, ni
siquiera para llegar a intentar reproducirse.

**Propuestas actualizadas (sustituyen a la Propuesta A de la sección
anterior, ninguna implementada)**:
- **A' (recomendada primero por ambos forks que investigaron esto)**:
  revisar `probabilidad_muerte_saciedad_critica`/mecánica de inanición
  de forma UNIVERSAL (`config/fisiologia.yaml`), no solo para gnomo --
  palanca más neutral (afecta a las 4 especies por igual), con mucho más
  respaldo de datos que antes porque explica el fracaso de dos especies
  con estrategias reproductivas opuestas. Riesgo real: podría
  desestabilizar el equilibrio que hoy sostiene a conejo/ardilla si se
  sobre-corrige -- medir con una corrida de control antes de fijar un
  valor nuevo, no ajustar a ciegas.
- **B' (en paralelo o inmediatamente después)**: investigar
  específicamente la relación depredador-presa de lobo -- disponibilidad
  real de presa perceptible, tasa de encuentro, eficiencia de caza, o si
  6 lobos fundadores son sencillamente demasiado pocos para sostener una
  tasa de encuentro viable (en cuyo caso subir `lobos_iniciales` sería
  calibración pura, no un guion). No medido con esta corrida --
  requeriría el mismo tipo de arnés de encuentro lobo-presa ya usado una
  vez para lobo-gnomo, repetido para lobo-conejo/lobo-ardilla.
- **C' (aplazada)**: recalibrar gnomo copiando el perfil de lobo -- YA
  NO tiene sentido como objetivo de referencia, dado que lobo también
  está roto. Si se retoma, calibrar contra el riesgo de fondo real (una
  vez A' se aborde), no contra otra especie que resulta estar igual de
  mal.

**Deshidratación resultó prácticamente irrelevante en la práctica**: 1
sola muerte por esa causa en las 4 especies combinadas sobre 10 semillas
× 8000 ticks -- o el agua es efectivamente abundante, o el mecanismo casi
nunca se dispara. Merece una nota, no una calibración a ciegas.

**Decisión de cierre de esta sesión (Diego, "procede como consideres")**:
dado el alcance de este hallazgo (afecta a las 4 especies y al
equilibrio poblacional ya alcanzado por conejo/ardilla), Claude decidió
NO tocar `probabilidad_muerte_saciedad_critica` ni ninguna otra
constante de riesgo de fondo en esta misma sesión -- documentarlo aquí
con el máximo detalle posible y dejarlo como el punto de partida real
para la siguiente sesión de calibración, en vez de cambiar un número de
tanto alcance sin la misma ronda de diseño+verificación que se ha
seguido con todo lo demás hoy.

**Pendiente real, explícito, esta es ahora la investigación prioritaria
del proyecto**: A' (revisar inanición universal) y B' (investigar
depredación lobo-presa específicamente) sin empezar; `fraccion_minima_peso_presa`/
`peso_referencia_deteccion_plena`/tasas de charco efímero/probabilidad
de muerte por vejez siguen totalmente sin iluminar por esta corrida
(instrumentación distinta, no barata de obtener de los mismos eventos
Muerte/Concepcion/Nacimiento ya usados); el harness completo de 15
semillas × 12000 ticks sigue sin correrse nunca para nada de esto,
sigue siendo la referencia de rigor que el proyecto tiene pendiente
desde la sección "Sobrepoblación...".

### Por qué lobo se muere de hambre pese a cazar más que nadie -- hallazgo
### de esa misma noche, verificado directamente contra el motor real

Ante la pregunta directa de Diego ("si la cantidad de conejos es tan
alta, ¿no es la presa principal del lobo?"), se investigó con datos
reales en vez de suponer. Dos hipótesis descartadas por evidencia:

- **Aislamiento geográfico** (lobo nace en bosque, conejo en pradera):
  descartada -- bosque y pradera son biomas CONTIGUOS (distancia mínima
  borde a borde de 1 celda, medido en 4 semillas), no hay barrera real.
- **Lobo no encuentra/no caza conejo**: descartada de forma tajante --
  matriz de depredación real medida (4 semillas × 6000 ticks): **lobo
  caza conejo 40 veces, ardilla 28, gnomo 27** -- conejo es la presa MÁS
  frecuente de lobo, no la menos.

**Causa real**: la fórmula de cuánto alimenta una captura
(`sistema_depredacion.py`: `saciedad_ganada = (peso_presa/peso_cazador) *
eficiencia_biomasa_saciedad(1.5)`) depende del RATIO de masa, no del
número de capturas. Con los pesos reales del catálogo (lobo ~75kg,
gnomo ~11.5kg, conejo ~2.25kg, ardilla ~0.45kg de media): una captura de
gnomo da ~23% de saciedad, conejo ~4.5%, ardilla ~0.9%. Cruzando esto
con la matriz real: **el 75% de toda la nutrición que obtiene un lobo
viene de sus 27 capturas de gnomo, pese a ser la presa menos
frecuente** -- conejo y ardilla, aunque abundantes y fáciles de cazar,
apenas alimentan a un depredador del tamaño de lobo. Coherente con la
biología real: un lobo no puede sostenerse cazando solo conejos y
ardillas, necesita presas grandes -- y hoy gnomo (la única presa grande
del catálogo) es también la más frágil y escasa.

**Primera idea de Diego para esto, evaluada y matizada**: "madrigueras"
de conejo agrupado + memoria de zona de caza para lobo (reutilizando el
mismo patrón de `MemoriaEspacial` ya usado para comida/agua/refugio).
Buena idea de diseño en sí (reutiliza antes de inventar), pero **NO
ataca la causa raíz** según esta medición -- lobo ya encuentra y caza
conejo más que ninguna otra presa; facilitarle encontrar más no cambia
que cada captura solo dé un 4.5% de saciedad. Aparcada por esta razón,
no descartada por mala idea.

**Segunda idea de Diego, la que se retoma**: introducir una especie
NUEVA de herbívoro grande (working name "caballo") como presa de peso
comparable o mayor al de lobo, combinado con un mecanismo de **caza en
manada** (varios lobos coordinándose contra una sola presa, mecanismo
que hoy no existe -- `sistema_depredacion.py` solo resuelve encuentros
1 contra 1) -- exactamente la estrategia real de los lobos para poder
abatir presas mucho más grandes que un individuo solo. **Alcance real:
dos piezas de diseño grandes, del mismo calibre que el arco "hilo
individual" de hoy** -- (1) la especie nueva en sí (catálogo, peso,
bioma de aparición, ciclo reproductivo propio) y (2) el mecanismo de
coordinación de caza en grupo, sin precedente en el motor actual.
**Decisión de Diego: diseñar YA la especie "caballo" como pieza
independiente; la caza en manada queda aparcada para una sesión
dedicada aparte** -- ver la sección siguiente para el diseño real de
"caballo", si llegó a cerrarse esa misma sesión.

## Especie caballo + techo de presa por manada -- cerrado el mismo día,
## implementado directamente por Claude tras un fallo real del pipeline
## (2026-09-05, madrugada)

Spec: `docs/superpowers/specs/2026-09-05-especie-caballo-design.md`.
Caballo: herbívoro grande (400-500kg) en pradera, gestación
deliberadamente corta (60-90 días, no los ~340 reales) por decisión
consciente de sostenibilidad -- evita a propósito la misma trampa
(gestación larga + cría única) que ya causa el colapso de gnomo.
`Especie.CABALLO` nuevo, entrada completa en `rangos_raciales`,
`caballos_iniciales: 9` en `sembrar_poblacion_inicial`.

**El pipeline falló su único intento por una causa externa, no de
contenido**: el proxy `litellm` agotó su presupuesto diario (~$1/día,
mismo tipo de límite ya visto en incidentes anteriores del proyecto) y
el modelo se quedó reintentando contra ese muro hasta agotar el timeout
de 45 min sin tocar una sola línea de código (coste real $0.216,
íntegro en reintentos fallidos). Diego pidió implementarlo
directamente (excepción ya prevista: "Diego lo pide explícitamente").

**Dos hallazgos reales, no anticipados en el spec, que cambiaron el
alcance de la pieza durante la propia implementación**:

1. **El filtro de búsqueda de presa dejaba a caballo completamente
   inerte, no "difícil de cazar"**. `sistema_movimiento.py:_calcular_caza`
   excluía CUALQUIER candidato que pesara igual o más que el propio
   cazador (`dims_p.peso >= peso_cazador`) -- con caballo siempre más
   pesado que lobo, un lobo NUNCA habría llegado siquiera a perseguirlo,
   independientemente de lo difícil o fácil que fuera derribarlo. El
   spec original asumía "difícil pero posible" (aceptable para este
   círculo); la realidad era "imposible, cero interacción".
2. Ante la pregunta directa de Diego ("hay que definir el paradigma de
   depredador solitario frente a un conjunto que trabaja junto"), se
   reencuadró como concepto real en vez de parche puntual: **techo de
   presa por manada**. Un cazador SOLITARIO (sin conespecíficos cazando
   activamente cerca) sigue limitado a su propio peso -- comportamiento
   original, sin cambios, un lobo solo nunca va a por un caballo. Con
   aliados cazando cerca (mismo dato y mismo radio -- `social.
   radio_apoyo_grupal`, `contar_conspecificos_cercanos(...,
   solo_cazando=True)` -- que YA usaba el bono de éxito existente en
   `_resolver_ataque`, descubierto durante esta misma investigación que
   YA había un germen de cooperación de caza en el motor, contradiciendo
   lo que se había dicho antes de "sin precedente en el motor actual"),
   el techo sube proporcionalmente
   (`peso_cazador * (1 + aliados * factor_ampliacion_techo_manada)`,
   factor=1.0 PROVISIONAL -- con eso, un lobo necesita ~5-8 aliados
   cazando cerca para poder perseguir un caballo, del orden real de un
   grupo de caza). Aplicado en los DOS puntos donde el motor decide "es
   presa válida" -- `_calcular_caza` (hacia dónde caminar) y
   `_es_presa_valida` (contacto directo en la misma celda) -- para que
   el mecanismo funcione de punta a punta, no solo a medias.

**Bug real, latente hasta este momento, expuesto y corregido de
paso**: `magnitud_disposicion_por_peso` es SIMÉTRICA por diseño (mide
cuánto pesa la diferencia, no quién tiene ventaja -- documentado así
desde su creación). Hasta ahora esto nunca fue un problema porque el
filtro de arriba garantizaba que el cazador SIEMPRE fuera el más
pesado, así que "disposición alta" siempre coincidía con "ventaja del
cazador". Al permitir perseguir presa más pesada, ese acoplamiento
implícito se rompía: sin corrección, un lobo pequeño "atacando" un
caballo enorme habría obtenido una disposición ALTA (por la gran
diferencia de peso) interpretada como ventaja para el cazador --
exactamente al revés de lo correcto. Corregido en
`sistema_depredacion.py:_resolver_ataque`: se invierte el signo de
`disp` cuando la presa pesa más que el cazador. Verificado que esto NO
cambia nada del comportamiento actual con gnomo/conejo/ardilla (donde
el cazador ya era siempre el más pesado por construcción) -- 209/209
tests en verde, incluidos los existentes, sin ninguna regresión.

**Verificado contra el motor real**: `BOSQUE_AUTO_TICKS=4000` sin
excepciones. Caballo sostiene población de verdad -- 9 fundadores → 14
creados, 9 vivos al final, reproducción funcionando tal como se diseñó
para sostenibilidad. **Ningún caballo murió por depredación en esta
corrida** -- honesto, no ocultado: lobo se extinguió (0/6 vivos) antes
del tick 4000, así que nunca llegó a formarse ningún grupo de caza real
que lo intentara. Mismo patrón que ya se ha visto varias veces hoy
(mecanismo verificado correcto por tests dirigidos, pero su disparo
real en juego libre bloqueado por la fragilidad de lobo, el mismo
problema de fondo que motivó toda esta investigación).

10 tests nuevos (`tests/test_especie_caballo.py`): especie distinta,
fábricas ECS completas, siembra en pradera, techo de presa por manada
(solitario rechaza, manada acepta, en ambos puntos de chequeo),
corrección de signo (probabilidad de éxito baja para un lobo solo
contra un caballo, confirmado estadísticamente sobre 200 intentos), y
ratio de saciedad (una captura de caballo alimenta más del triple que
una de conejo).

**Pendiente real, explícito**: todo el catálogo de caballo y
`factor_ampliacion_techo_manada=1.0` son PROVISIONALES, sin calibrar;
la caza en manada real (varios lobos cazando juntos con éxito contra
caballo) sigue sin observarse en juego libre -- necesita que lobo
sobreviva lo bastante para formar un grupo, lo cual depende de resolver
primero las propuestas A'/B' de la investigación de fragilidad (riesgo
de fondo de inanición, relación depredador-presa de lobo) todavía sin
empezar; sin representación visual, motor primero.

### Intento descartado: subir `lobos_iniciales` no arregla nada
### (2026-09-05, mismo día, medido antes de tocar config real)

Diego propuso, ante la extinción de lobo bloqueando la caza en manada,
simplemente subir `lobos_iniciales` (hoy 6) para que sobrevivieran más
simultáneamente. Probado empíricamente ANTES de tocar
`config/poblacion.yaml` (7 semillas nuevas × 6000 ticks, comparando
6 vs 18 lobos fundadores, arnés en scratchpad
`diagnostico_mas_lobos.py`): **lobo se extinguió (0 vivos al final) en
las 7 semillas con AMBAS configuraciones, sin ninguna excepción** --
triplicar la población fundadora no cambió la trayectoria en ningún
caso. 0 capturas de caballo por depredación en las 14 corridas
combinadas (7 semillas × 2 configuraciones). El único efecto real
medido fue NEGATIVO: con 18 lobos, la población final media de gnomo
bajó de 0.9 a 0.1 -- más depredadores cazando acelera el colapso de una
presa ya frágil, sin producir ningún beneficio a cambio.

**Conclusión, con datos reales, no solo intuición**: el problema de
lobo NO es cuántos individuos empiezan la partida -- es que casi
ningún individuo sobrevive lo bastante (mismo hallazgo ya medido: 90%
de sus muertes son por inanición). Subir la población fundadora solo
multiplica cuántos mueren, no cambia si sobreviven. **Descartado como
vía de solución** -- no se cambió `lobos_iniciales` en el config real.
Refuerza con más fuerza todavía que A'/B' (riesgo de fondo de
inanición, relación depredador-presa de lobo) siguen siendo el único
camino real -- no hay atajo de calibración de población inicial que lo
resuelva.

## Valentía propia también modula la percepción de amenaza -- segundo
## eje del mismo mecanismo, cierra una regresión real introducida por
## caballo (2026-09-05, mismo día)

Diego, tras la investigación de fragilidad de lobo (secciones
anteriores), pidió específicamente investigar por qué lobo muere
siempre y proponer soluciones -- delegado a un fork. Su hallazgo
dominante no fue ninguna de las causas ya conocidas (inanición,
ratio de saciedad por presa), sino un efecto secundario NUEVO
introducido por la propia especie `caballo` esa misma sesión: lobo
(depredador, `Temperamento.valentia` alto por rango racial, 0.5-0.9)
percibía a caballo (herbívoro grande y pacífico, 400-500kg) como
amenaza real solo por la diferencia de peso, disparando
`CRISIS_VIOLENTA` un 18.9% de su tiempo de vida (0% sin caballo,
medido en un arnés dirigido, `diagnostico_caballo_amenaza_lobo.py`,
scratchpad) -- consumiendo estabilidad mental sin que ningún ataque
real estuviera ocurriendo.

Diego generalizó el diagnóstico antes de que se propusiera ningún
parche: "para muchas interacciones el tamaño es consecuente respecto a
que un animal grande sea una amenaza para uno pequeño, pero hay otros
casos que no" -- la fórmula de amenaza de la sección anterior (ronda de
agresividad del candidato, 2026-09-04) seguía siendo una ley
incompleta, no un caso particular de caballo: nunca miraba la
naturaleza de quien PERCIBE, solo la del candidato.

**Diseño cerrado, mismo patrón exacto que `peso_agresividad_candidato`
de la sección anterior**: `Temperamento.valentia` PROPIA (de quien
percibe, no del candidato) eleva el UMBRAL efectivo de amenaza en vez
de sumarse a la magnitud del candidato -- `umbral_efectivo =
umbral_amenaza_percibida + valentia_propia * factor_valentia_amenaza`
(`nucleo/disposicion.py:_candidato_valido`/
`posicion_mas_cercana_por_disposicion`, propagado por
`nucleo/amenaza.py:posicion_amenaza_mas_cercana`). Un individuo
valiente necesita más diferencia de tamaño/agresividad para sentirse
amenazado que uno tímido, ante la MISMA pareja de pesos -- ley general,
sin ninguna excepción de código por especie: `valentia_propia`/
`factor_valentia_amenaza` son parámetros opcionales con default 0.0 en
ambas funciones núcleo, sin cambiar depredación/pareja/territorio, que
no los pasan.

`factor_valentia_amenaza: 0.2` (PROVISIONAL, `config/combate.yaml`),
calculado contra los rangos raciales reales para que lobo (valentia
0.5-0.9) deje de percibir caballo como amenaza en la práctica (umbral
efectivo 0.75-0.83, por encima del score máximo real ~0.74) mientras
ardilla/conejo (valentia 0.2-0.45, presa) solo suben su umbral
levemente (0.686-0.731) -- sin dejar de percibir a gnomo/lobo como
amenaza real (score cercano a 1.0 por la enorme diferencia de peso).
Los TRES consumidores actualizados de forma consistente (mismo
criterio de siempre): drenaje de `Necesidades.seguridad`
(`sistema_necesidades.py`), dirección de HUIR (`sistema_movimiento.py`,
`_calcular_huida` gana un parámetro `temperamento` nuevo), deseo de
empuñar arma (`sistema_decision.py`) -- los tres ya tenían
`Temperamento` de la propia entidad disponible en el mismo scope, sin
necesidad de ninguna consulta ECS adicional.

**Verificado contra el motor real, repitiendo el mismo arnés que había
encontrado el problema** (no uno nuevo): `crisis_violenta` de lobo con
caballo presente vuelve a 0.0% (antes 18.9%), idéntico al baseline sin
caballo, con las mismas muertes de lobo en ambas condiciones (18 vs 18,
3 semillas × 3000 ticks) -- confirma que el fix corrige exactamente el
mecanismo señalado sin ningún efecto colateral sobre la mortalidad real
de lobo (la fragilidad de fondo de lobo, investigada en la sección
anterior, sigue sin resolver -- esto solo cierra la regresión que el
propio caballo había introducido, no el problema de fondo). 216/216
tests en verde (8 nuevos, `tests/test_amenaza_valentia.py`), 3000
ticks de `BOSQUE_AUTO_TICKS` sin excepciones.

**Pendiente real, explícito**: `factor_valentia_amenaza=0.2` sigue
PROVISIONAL, sin calibrar contra el harness completo; la fragilidad de
fondo de lobo (por qué muere siempre, más allá de esta falsa amenaza)
sigue sin solución -- las otras dos propuestas del fork que investigó
esa fragilidad (recalibrar agotamiento/resistencia del perfil cazador;
corregir que `impulso_reproductivo` no se resetea, compartido con el
mismo problema de gnomo) siguen sin abordar, deliberadamente
despriorizadas detrás de esta pieza -- candidatas naturales para
retomar la investigación de fragilidad de lobo.

## Fragilidad de lobo -- mejora real y medida (12/12 → 8/12 extinción),
## NO una solución completa, y un hallazgo nuevo: vejez, no solo inanición
## (2026-09-05, mismo día, tras "pero hay que solucionar eso")

Diego, tras cerrar el fix de valentía de arriba, pidió explícitamente
resolver de una vez la fragilidad de fondo de lobo, no solo seguir
documentándola como pendiente. Se lanzó un fork con instrucciones de
investigar a fondo (presupuesto calórico real, las dos propuestas A'/B'
ya apuntadas, y los dos hallazgos menores sin detalle preservado de la
investigación anterior) e implementar un fix verificado -- **el fork
murió a mitad de camino por un límite de sesión (rate limit)**, dejando
cambios reales pero sin comitear en el árbol de trabajo. Se auditaron y
continuaron directamente en la sesión principal en vez de relanzar el
fork.

**Lo que el fork dejó, verificado y encontrado INSUFICIENTE al
reprobar**: `config/fisiologia.yaml` sección `lobo` con
`tasa_perdida_saciedad_por_tick` 8x más lento (0.012→0.0015) y
`probabilidad_muerte_saciedad_critica` 5x más bajo (0.005→0.001), tras
medir que el presupuesto calórico medio de lobo estaba casi exactamente
en el punto de equilibrio (margen ~1.3%) y que subir
`eficiencia_biomasa_saciedad` un 50% NO cambiaba nada (el problema no es
cuánto alimenta cada captura, es el tiempo a saciedad exactamente 0
entre capturas). El propio fork medía una mejora real (6 semillas × 5000
ticks: extinción 6/6→4/6) -- **pero al reprobar esa misma configuración
contra 12 semillas NUEVAS (501-512, nunca vistas) × 8000 ticks, dio
12/12 EXTINCIÓN** -- la mejora original no generalizaba, muestra clásica
de sobreajuste a un puñado de semillas. Un comentario del fork además
decía "decaimiento a la mitad" cuando el valor real escrito (0.0015) es
un 8x, no un 2x -- inconsistencia de documentación corregida de paso.

**Llevar las mismas dos palancas al extremo tampoco bastaba**: probado
0.0008/0.0004 (15x/12.5x más lento/bajo que el universal) sobre las
mismas 12 semillas -- 9/12 extinción, con los 3 supervivientes en 1-2
individuos (no poblaciones reales sostenidas). Confirma que la
inanición NUNCA fue la única causa de fondo, por agresiva que se hiciera
la mitigación.

**HALLAZGO REAL, no visto en las investigaciones anteriores de este
mismo día**: con la inanición casi neutralizada por esos valores
extremos, un desglose de causas de muerte reales (8 semillas × 8000
ticks) dio **VEJEZ como causa dominante (65.6%)**, inanición en segundo
lugar (32.8%) -- antes quedaba completamente enmascarada bajo el 90% de
muertes por inanición del config original (medido en la investigación
de esa misma tarde, sección "Investigación de causas del colapso
reproductivo de gnomo"). Causa raíz identificada:
`poblacion.techo_fraccion_edad_inicial_longevidad` (0.7) siembra a TODA
la población fundadora con edad inicial de hasta el 70% de su
longevidad individual, aplicado por igual a especies con longevidades
absolutas muy distintas (gnomo 45-65 años, lobo solo 8-14). Para lobo,
la ventana de una corrida de 8000 ticks (~0.91 años) consume una
fracción mucho mayor de vida restante que para gnomo, exponiendo a la
población fundadora entera a la zona final de la curva de vejez
(`nucleo/ciclo_vital.py`, exponente=8) casi desde el principio de la
partida. Conejo/ardilla comparten la MISMA regla de siembra y
longevidades igual de cortas (1-3, 2-5 años) pero la compensan con
reproducción mucho más rápida -- lobo no, pese a tener gestación corta
(60-75 días) y camada grande (4-6), un perfil de r-estratega que nunca
llegó a aprovecharse porque `factor_base_concepcion` (0.0033) seguía
copiado del peor valor del catálogo, compartido con gnomo (que sí
necesita una tasa baja porque cada intento ya es carísimo por sí solo:
gestación larguísima, camada fija en 1) -- probablemente un valor
heredado sin revisar nunca, no una decisión deliberada.

**Fix real, dos piezas combinadas, verificado en las MISMAS 12 semillas
nuevas**: `factor_base_concepcion` de lobo subido a 0.015 (x4.5,
`config/poblacion.yaml`) manteniendo los valores extremos de saciedad de
arriba (0.0008/0.0004, `config/fisiologia.yaml`) -- extinción bajó de
9/12 (solo la mitigación de inanición) a **8/12**, con población final
media de lobo subiendo de ~0.25 a 1.33, y una semilla alcanzando **11
individuos** (población real sostenida, no un superviviente aislado).
Probar x9 (0.03) no mejoró más allá del ruido (también 8/12, media
1.08) -- rendimientos decrecientes, descartado como sobre-ajuste
innecesario frente a x4.5.

**Honestidad explícita sobre el alcance real**: esto es una mejora
sustancial y medida (de colapso total garantizado a 1 de cada 3 semillas
nuevas sosteniendo una población real de lobo), **NO una solución
completa** -- 8 de 12 semillas nuevas siguen terminando en extinción de
lobo. Comparado contra el mismo conjunto de 12 semillas con solo la
mitigación de inanición del fork (sin subir concepción), gnomo/conejo/
caballo muestran algo de variación en sus medias agregadas, pero dentro
del rango ya esperado de ruido por desplazamiento de secuencia de rng
(cambiar la tasa de éxito de concepción cambia cuántas tiradas
`rng.randint` de tamaño de camada ocurren, perturbando la secuencia de
aleatoriedad de todo lo demás en el mismo tick para el resto del motor
-- mismo fenómeno ya documentado en "Sobrepoblación...") -- no se
detectó ninguna regresión clara y sistemática, pero tampoco se puede
descartar con la certeza que daría un harness limpio dedicado.

**Verificado**: 216/216 tests en verde (sin tests nuevos dedicados a
este fix -- es calibración numérica pura sobre parámetros ya cubiertos
por tests existentes de reproducción/necesidades), 3000 ticks de
`BOSQUE_AUTO_TICKS` sin excepciones.

**Pendiente real, explícito, esta es ahora la investigación prioritaria
si se retoma**: 8/12 semillas nuevas siguen extinguiendo lobo -- el
problema de fondo sigue sin resolverse del todo. Candidatos para la
siguiente vuelta, en orden de sospecha: (1) revisar
`techo_fraccion_edad_inicial_longevidad` de forma relativa a la
longevidad absoluta de cada especie en vez de una fracción universal
fija (0.7 para todas) -- palanca más general y mejor justificada que
seguir subiendo la concepción de lobo específicamente; (2) las dos
propuestas A'/B' de la investigación anterior (revisar inanición de
forma universal para las 4 especies; investigar específicamente la
relación depredador-presa de lobo) siguen sin abordarse; (3) los dos
hallazgos menores del fork original (agotamiento/resistencia del perfil
cazador, reseteo de `impulso_reproductivo`) nunca llegaron a
verificarse con datos reales en esta vuelta -- se investigó el gate de
`BUSCAR_PAREJA` en su lugar (ver más abajo) y se descartó como causa
significativa. Todos los valores tocados hoy
(`tasa_perdida_saciedad_por_tick`, `probabilidad_muerte_saciedad_
critica`, `factor_base_concepcion` de lobo) PROVISIONALES, sin calibrar
contra el harness completo.

**Vía descartada explícitamente, con datos**: se sospechó que el gate de
`BUSCAR_PAREJA` (exige las CUATRO necesidades físicas >= `umbral_
atencion_pareja`=0.5 simultáneamente, a diferencia del gate de
concepción en sí, que solo exige saciedad desde la corrección de
"Sobrepoblación..." de 2026-08-31) pudiera ser un cuello de botella
adicional real para una especie que vive con saciedad crónicamente baja.
Medido directamente (3 semillas × 8000 ticks, contando qué necesidad
bloquea el gate en cada muestra): saciedad es responsable del 44-52% de
los bloqueos, energía/hidratación/aliviado apenas 2-5% cada una --
relajar el gate a saciedad-únicamente apenas habría cambiado nada.
Descartado por evidencia real, no se tocó `sistema_decision.py` para
esto.

## Reestructuración de la siembra fundadora: "parejas fundadoras" --
## mejora drástica, verificada, cierra la investigación de estabilidad
## de población del 2026-09-05/06

Diego pidió seguir intentando estabilizar la población general (más
allá del fix específico de lobo de la sección anterior). La
investigación exhaustiva contra el motor real (84 semillas nuevas × 8000
ticks, varios lotes independientes) mostró que el problema era mucho más
general de lo que parecía: **TODAS** las palancas tácticas probadas
fallaron o empeoraron las cosas --

- Ardilla se extinguió en las 84 semillas probadas, sin excepción, bajo
  cualquier combinación de: población base, muerte por hambre universal
  a la mitad, población fundadora x1.5, ambas combinadas, concepción
  propia de ardilla x2.24 (igualando a conejo) o x4.5.
- Reducir la muerte por hambre universal a la mitad EMPEORÓ a gnomo
  (extinción 8/12→11/12) y conejo (4/12→8/12) -- alargar la agonía de
  individuos casi muertos de hambre aumenta la competencia sin
  compensar con más supervivencia (misma lección de "Sobrepoblación...",
  2026-08-31).
- Subir la población fundadora x1.5 tampoco ayudó, empeoró ligeramente a
  conejo.
- Un primer prototipo de "siembra agrupada" (grupos de 4 fundadores
  cerca entre sí, sin garantizar sexo opuesto adyacente) empeoró a
  gnomo y lobo -- concentrar individuos de la misma especie concentra
  también la demanda de comida local.

**Hallazgo real que explicó por qué**: medido directamente en la siembra
fundadora (sin ningún tick transcurrido), la distancia media al
conespecífico de sexo opuesto más cercano es de 5.4-9.9 celdas (gnomo),
11.5-18.8 celdas (lobo), 3.4-4.9 celdas (ardilla) -- casi cero contactos
inmediatos (misma celda, el requisito EXACTO que exige la concepción,
`sistemas/sistema_reproduccion.py:_macho_elegible_en_contacto`). Toda la
población fundadora dependía enteramente del sesgo gregario de deambular
para cerrar esa distancia, compitiendo contra el riesgo combinado desde
el segundo cero -- una carrera entre "tiempo hasta el primer contacto
reproductivo viable" y "tiempo hasta que el riesgo acumulado mate al
fundador" que ninguna palanca de magnitud podía cambiar si la distancia
de partida seguía siendo grande.

**Diego, ante esto**: "esto es un problema general, igual hay que
plantear una reestructuración de algún tipo porque no estamos
encontrando una solución" -- se invocó `superpowers:brainstorming`
(camino arquitectónico) para diseñarlo formalmente en vez de seguir
probando parámetros sueltos. Tres enfoques propuestos: (A) **parejas
fundadoras** -- sembrar la población inicial como parejas macho+hembra
en la misma celda desde tick 0, en vez de individuos independientes; (B)
ventana de resiliencia temprana en el modelo de mortalidad; (C) búsqueda
activa de pareja más fuerte en movimiento. Diego aprobó empezar por A --
el círculo más pequeño y barato de verificar de los tres, sin tocar
ningún sistema del motor en marcha, solo cómo nace la población en tick
0.

**Diseño** (spec:
`docs/superpowers/specs/2026-09-06-parejas-fundadoras-design.md`):
`nucleo/entidad.py:crear_criatura` gana un parámetro opcional
`sexo_forzado: Sexo | None = None` (sin él, comportamiento idéntico bit
a bit -- ningún llamador existente lo pasa). `main.py:
sembrar_poblacion_inicial` reestructura su bucle por especie: en vez de
`cantidad` individuos con celda y sexo sorteados de forma completamente
independiente, forma `cantidad // 2` parejas -- una celda sorteada por
pareja (mismo mecanismo de elección de celda de siempre), un macho y una
hembra creados ahí. El sobrante impar (si lo hay) se siembra como
siempre. Cada miembro sigue sorteando su propia edad inicial por
separado -- pueden acabar con edades muy distintas, variación real, no
un problema. Ley general aplicada por igual a las 5 especies, sin
ninguna excepción de código por especie.

**Implementado por el pipeline en el primer intento** (`mini-swe-agent`,
PR #18, diff idéntico al spec -- 0 corrupción, 0 desviación). Auditoría
manual de Claude antes de fusionar: diff completo revisado línea a
línea, sin bugs; 216/216 tests en verde; `BOSQUE_AUTO_TICKS=3000` sin
excepciones; verificación dirigida independiente (5 semillas nuevas ×
4000 ticks, arnés sin persistencia, tal como pedía el encargo -- Diego
pidió explícitamente no lanzar baterías largas esta vez, ver
`feedback_diagnosticos_rapidos` en memoria persistente).

**Resultado, con solo 5 semillas nunca vistas**:

| Especie | Extinción (de 5) | Media | Antes de este círculo |
|---|---|---|---|
| gnomo | 0/5 | 1.6 | 58-92% extinción |
| lobo | 0/5 | 11.0 | 58-92% extinción |
| conejo | 2/5 | 23.8 | ya razonable |
| ardilla | 4/5 | 0.2 | 100% (84/84) |
| caballo | 0/5 | 4.4 | 58-83% extinción |

**Mejora drástica**: gnomo, lobo y caballo con CERO extinción en esta
muestra (0/5 cada uno), conejo con solo 2/5, y lobo alcanzando una media
de 11 individuos -- igualando el máximo aislado (11) visto en cualquier
intento previo del mismo día, ahora como promedio de la muestra
completa. Ardilla, la especie más obstinada de toda la investigación
(100% de extinción en 84 semillas antes de este cambio),
tuvo su **primera supervivencia real en todo el día** (1 de 5 semillas).
Con n=5 no se puede afirmar una solución completa y cerrada -- pero el
salto de magnitud frente a CUALQUIER otra palanca probada hoy (incluida
la mejora específica de lobo de la sección anterior, que solo llegó al
33% de supervivencia) confirma que el diagnóstico de fondo (distancia de
partida, no magnitud de riesgo) era el correcto.

**Pendiente real, explícito**: ardilla sigue siendo la especie más
frágil (4/5 extinta incluso con parejas fundadoras) -- candidata directa
para el Enfoque B o C si se retoma esta investigación, o para
investigar si su problema estructural (comparte bosque con gnomo Y
lobo, dieta subconjunto de la de gnomo) necesita algo más que resolver
la distancia de partida. Ninguna cifra de esta verificación (n=5) tiene
la resolución del harness completo (15 semillas × 12000 ticks) que el
proyecto tiene pendiente desde "Sobrepoblación..." -- el resultado es
prometedor, no una calibración cerrada. Los Enfoques B (ventana de
resiliencia temprana) y C (búsqueda activa de pareja) quedan aparcados,
no descartados, como candidatos de un segundo círculo si hace falta más
mejora. `techo_fraccion_edad_inicial_longevidad`, todas las tasas de
lobo, y `factor_base_concepcion` de cualquier especie siguen
PROVISIONALES, sin relación con este cambio -- este círculo no tocó
ningún valor numérico, solo la disposición espacial de la siembra.

### CORRECCIÓN el mismo día -- la "mejora drástica" de arriba era real
### pero PARCIAL: a más plazo (6000 ticks), gnomo y ardilla vuelven a
### extinguirse al 100%

Diego pidió confirmar si la mejora se sostenía más allá de los 4000
ticks ya probados -- exactamente el "límite real a vigilar" que el
párrafo de arriba ya señalaba como no confirmado. Medido (5 semillas
nuevas, 1001-1005, × 6000 ticks, mismo criterio de lote pequeño):

| Especie | Extinción (de 5) | Media |
|---|---|---|
| gnomo | **5/5 (100%)** | 0.0 |
| lobo | 0/5 | 3.2 |
| conejo | 2/5 | 28.6 |
| ardilla | **5/5 (100%)** | 0.0 |
| caballo | 0/5 | 3.2 |

**Gnomo y ardilla vuelven exactamente a su tasa de fallo de antes del
fix** -- el buen resultado a 4000 ticks era real pero temporal para
estas dos especies, no una solución duradera. Lobo y caballo, en
cambio, SÍ se sostienen con solidez a 6000 ticks (0/5 extinción en
ambos) -- la mejora para ellos es real y duradera.

**Hipótesis causal, no confirmada con más profundidad todavía**: la
pareja fundadora resuelve el arranque de la PRIMERA generación, pero las
crías siguen dispersándose y buscando pareja por el mismo mecanismo
lento de siempre (sesgo gregario de deambular) -- exactamente el hueco
que el Enfoque C (búsqueda activa de pareja) estaba pensado para cerrar.
Lobo (concepción ya subida x4.5 hoy mismo) y caballo (camada/gestación
ya diseñadas para sostenibilidad) tienen tasa de reproducción suficiente
para construir densidad de población real antes de que la generación
fundadora muera de vieja; gnomo (peor tasa de concepción del catálogo,
camada fija en 1) y ardilla (concepción baja, dieta y bioma compartidos
con dos competidores/depredadores) no llegan a tiempo -- cuando el
impulso inicial se apaga, la población remanente vuelve al mismo
problema de partida disperso, esta vez sin el colchón de una generación
fundadora completa.

**Conclusión honesta**: "parejas fundadoras" NO es una solución completa
para la estabilidad general -- es una mejora real y duradera para
especies con reproducción ya razonablemente rápida (lobo, caballo), pero
solo un aplazamiento temporal para las de reproducción lenta (gnomo,
ardilla). El Enfoque C (búsqueda activa de pareja, ya aparcado arriba)
deja de ser un "candidato futuro" y pasa a ser la pieza que probablemente
hace falta para cerrar esto de verdad -- confirmado con datos, no solo
teorizado. Enfoque B (ventana de resiliencia) sigue como complemento de
menor alcance. Ninguna cifra tiene la resolución del harness completo
-- n=5 por config, misma limitación que arriba.

## Síntesis: investigación de estabilidad de población del 2026-09-05/06
## -- qué se averiguó, qué se corrigió, y qué enfoques quedan para seguir

Cierre consolidado de las cuatro secciones anteriores (valentía/amenaza,
fragilidad de lobo, reestructuración de siembra fundadora), pedido
explícitamente por Diego para tener en un solo sitio qué se sabe hoy y
por dónde seguir -- no repite el detalle ya documentado arriba, apunta a
él.

### Cadena causal completa descubierta hoy

1. **Regresión de amenaza por caballo** (arreglada): lobo percibía a
   caballo como amenaza falsa solo por tamaño, sin mirar la valentía de
   quien percibe -- corregido con umbral de amenaza modulado por
   `Temperamento.valentia` propia. Cierra una regresión, no la
   fragilidad de fondo.
2. **Presupuesto calórico de lobo al límite** (mitigado, no resuelto del
   todo): el ratio de masa presa/cazador hace que conejo/ardilla apenas
   alimenten a un lobo -- mitigado bajando su hambre letal y subiendo su
   concepción, mejora real medida (0%→33% de supervivencia en el momento
   de cerrar esa pieza) pero superada después por el hallazgo de más
   abajo.
3. **Vejez enmascarada por inanición** (descubierto, causa raíz
   identificada): con el hambre casi neutralizada, vejez pasó a ser la
   causa dominante de muerte de lobo (65.6%) -- `techo_fraccion_edad_
   inicial_longevidad` (0.7 universal) expone desproporcionadamente a
   especies de vida corta (lobo 8-14 años) frente a las de vida larga
   (gnomo 45-65).
4. **El problema resultó ser general, no solo de lobo**: ardilla se
   extinguía en el 100% de 84 semillas probadas, insensible a CUALQUIER
   palanca de magnitud (hambre universal, población base, concepción
   propia). Causa raíz real: la reproducción exige contacto exacto en la
   misma celda, y la siembra fundadora colocaba a cada individuo de
   forma completamente independiente -- distancias de partida de 5-19
   celdas al conespecífico de sexo opuesto más cercano, una carrera
   contra el riesgo que la población fundadora no tenía ninguna ventaja
   estructural para ganar.
5. **Reestructuración de la siembra ("parejas fundadoras")**: corrige el
   punto 4 directamente, pero solo PARCIALMENTE -- ver el punto 6.
6. **CORRECCIÓN, mismo día**: a 4000 ticks, salto de magnitud frente a
   todo lo anterior (gnomo/lobo/caballo con 0/5 extinción). Pero
   confirmado a 6000 ticks que gnomo y ardilla vuelven al 100% de
   extinción -- la mejora era real pero temporal para ellas, mientras
   que lobo y caballo (reproducción ya razonablemente rápida) SÍ se
   sostienen con solidez. Causa probable: "parejas fundadoras" arregla
   el arranque de la generación fundadora, pero las crías posteriores
   siguen dependiendo del mismo mecanismo lento de encuentro (sesgo
   gregario) -- especies de reproducción lenta (gnomo, ardilla) no
   construyen suficiente densidad antes de que ese impulso inicial se
   apague.

### Qué queda genuinamente abierto

- **Gnomo Y ardilla, no solo ardilla, siguen siendo las especies
  frágiles a más de 4000 ticks** (100% de extinción a 6000 ticks, pese a
  las parejas fundadoras). Ardilla además comparte bosque con gnomo
  (compite por manzanas/raíces, dieta subconjunto de la suya) y con lobo
  (expuesta a depredación) -- a diferencia de conejo, aislado en
  pradera; gnomo no tiene ese problema de bioma, su fragilidad es pura
  cuestión de tasa de reproducción (peor concepción del catálogo,
  camada fija en 1).
- **Enfoque C ya no es un candidato especulativo -- los datos apuntan
  directamente a él**: búsqueda activa de pareja más fuerte y de mayor
  alcance, con lógica dedicada (como ya tienen CAZAR o HUIR) en vez de
  depender del sesgo gregario genérico de deambular, para que las
  generaciones POSTERIORES a la fundadora (no solo la primera) puedan
  encontrarse a tiempo. Mayor superficie que "parejas fundadoras" (toca
  el motor de movimiento en marcha), pero es el candidato mejor
  respaldado por evidencia real hoy.
- **Enfoque B, aparcado, menor prioridad tras el hallazgo de 6000
  ticks**: ventana de resiliencia temprana en el modelo de mortalidad --
  ataca la carrera desde el lado del riesgo, no del encuentro; sigue
  siendo un complemento válido pero no ataca la causa recién confirmada
  (crías sin mecanismo de encuentro efectivo). Riesgo de diseño ya
  señalado: enmarcarlo como rasgo físico neutral, no atado al estado
  reproductivo, para no rozar ser teleológico.
- **A'/B' de la investigación de fragilidad de lobo, nunca abordadas**:
  revisar la mecánica de inanición de forma universal, e investigar en
  profundidad la relación depredador-presa de lobo con las demás presas
  además de gnomo. Menos urgentes ahora que lobo ya se sostiene con
  solidez a 6000 ticks gracias a la combinación de su propio fix más
  parejas fundadoras.
- **Harness completo (15 semillas × 12000 ticks), pendiente desde
  "Sobrepoblación..." (2026-08-31)**: sigue siendo la referencia de
  rigor real que el proyecto nunca ha corrido para nada de esto. Todas
  las cifras de hoy (incluidas ambas tablas de "parejas fundadoras",
  n=5 cada una) son direccionales, no una calibración cerrada -- aunque
  la de 6000 ticks ya dio una señal binaria clara (100% vs 0%), no un
  resultado ambiguo que necesite más resolución para interpretarse.

### Recomendación de orden si se retoma

1. **Diseñar el Enfoque C** (búsqueda activa de pareja, lógica dedicada
   más allá del sesgo gregario genérico) -- ya no es "si hace falta más
   mejora", es el paso confirmado como necesario por el hallazgo de 6000
   ticks. Mismo proceso de brainstorming que parejas fundadoras.
2. Al verificarlo, comprobar específicamente si soluciona gnomo Y
   ardilla a 6000+ ticks, no solo repetir la mejora ya vista a 4000.
3. Si ardilla sigue rezagada tras eso, investigar su caso específico
   (comparte bioma con dos especies, dieta subconjunto) como una
   segunda capa, no como sustituto de C.
4. Enfoque B (ventana de resiliencia) como complemento de bajo riesgo si
   los anteriores no bastan -- no ataca la causa confirmada hoy, pero
   sigue siendo un margen adicional razonable de bajo coste.

## Cierre real del día: fix directo de ardilla y gnomo (hambre +
## concepción combinadas) -- mejora sustancial confirmada, el objetivo
## del 50% con las 5 especies vivas a la vez SIGUE sin alcanzarse
## (2026-09-06, misma tarde, tras "tenemos que solucionar estos
## problemas para poder seguir desarrollando")

Diego fijó un criterio de éxito concreto y exigente: al menos el 50% de
las semillas deberían terminar con las 5 especies vivas SIMULTÁNEAMENTE,
no solo con alguna sobreviviendo. Medido contra el estado del motor tras
"radio de pareja": 0 de 10 semillas probadas cumplían ese criterio,
bloqueadas siempre por ardilla (100% de extinción, sin excepción, en
más de 90 semillas del día). Ante la insistencia explícita de Diego
("no tiene sentido meter mecánicas nuevas si las poblaciones se
extinguen"), se investigó hasta encontrar una solución real, en vez de
seguir reportando hallazgos negativos.

**Ardilla, resuelto** (commit `f42c5a6`): ninguna de las hipótesis
específicas de ardilla probadas por separado funcionaba (competencia
con gnomo: descartada tras eliminar gnomo del mundo por completo, misma
extinción; concepción sola: cero efecto; mitigación de hambre sola:
inconsistente entre lotes). **El hallazgo real**: la combinación de
ambas -- el mismo recetario que ya había funcionado para lobo, nunca
antes probado junto para ardilla porque cada pieza se había probado por
separado -- sí funciona. `config/fisiologia.yaml:necesidades.ardilla`
gana `tasa_perdida_saciedad_por_tick=0.0008`/
`probabilidad_muerte_saciedad_critica=0.0004` (idéntico a lobo);
`config/poblacion.yaml:rangos_raciales.ardilla.factor_base_concepcion`
sube de 0.0067 a 0.03 (x4.5). Verificado en dos lotes independientes de
semillas nuevas: **6 de 8 semillas con población de ardilla real y
sostenida** (11, 3, 412, 78, 16, 7 individuos), frente al 0 sistemático
de antes -- una de ellas (412 individuos) disparó el tope de seguridad
del propio arnés de diagnóstico.

**Gnomo, mismo recetario aplicado a continuación** (commit `c5697a7`):
con ardilla resuelta, gnomo pasó a ser el bloqueo dominante (80% de
extinción en la verificación más reciente, nunca tocado hasta ese
momento). Mismo par de valores en `necesidades.gnomo`;
`factor_base_concepcion` sube de 0.0033 (el peor del catálogo) a 0.015.
Diferencia real señalada en el propio comentario del config, no
resuelta del todo: la gestación de gnomo (4800-6240 ticks) es del mismo
orden que la ventana de verificación completa (6000-8000 ticks), y su
camada está fija en 1 sin ninguna compensación posible (a diferencia de
lobo 4-6 y ardilla 2-4) -- el efecto podría ser estructuralmente más
limitado aquí. Verificado con 3 semillas nuevas completadas antes de
cortar por tiempo (7001-7003): gnomo sobrevivió con población real en
las 3 (4, 4, 2 individuos) frente al 80% de extinción previo -- mejora
clara y consistente en la muestra parcial disponible.

**Honestidad sobre el objetivo real de Diego, todavía sin alcanzar**:
en las mismas 3 semillas donde gnomo mejoró (7001-7003), **ardilla
estuvo en 0 en las tres** -- su tasa de éxito medida (~75% en 8 semillas
distintas) es alta pero no garantizada semilla a semilla, y no coincidió
con las semillas donde se verificó el fix de gnomo. Ninguna de las
semillas probadas hoy, tras ambos fixes, ha mostrado todavía las 5
especies vivas simultáneamente -- el criterio del 50% de Diego sigue sin
confirmarse. Esto no invalida el progreso real (ambas especies
individualmente pasaron de "extinción sistemática" a "supervivencia
frecuente"), pero es la métrica que de verdad importa y todavía no se ha
medido de forma conjunta con un lote suficientemente grande.

**Pendiente real, inmediato**: correr un lote de verificación conjunto
(gnomo + ardilla + lobo + caballo, todos con sus fixes ya aplicados) el
tiempo suficiente para medir directamente el criterio real de Diego (%
de semillas con las 5 especies vivas a la vez) antes de dar esto por
cerrado. Candidatos si ese lote muestra que sigue sin alcanzarse: (a) el
mismo recetario podría necesitar un tercer ingrediente para gnomo
específicamente, dado el problema estructural de gestación larga/camada
fija ya señalado; (b) revisar si conejo (nunca recibido este recetario,
su extinción parcial en varias de las corridas de hoy -60-100% en
algunos lotes- podría estar convirtiéndose en el nuevo cuello de botella
según mejoran las demás especies); (c) el harness completo (15 semillas
× 12000 ticks) sigue pendiente para cualquier calibración cerrada de
verdad. Todos los valores tocados hoy (`tasa_perdida_saciedad_por_tick`,
`probabilidad_muerte_saciedad_critica`, `factor_base_concepcion` de
lobo/ardilla/gnomo) siguen PROVISIONALES.

### Medición directa del criterio real de Diego, con ambos fixes ya en
### `master` -- 0/4 semillas nuevas, pero cerca, y conejo emerge como el
### siguiente eslabón débil (2026-09-06, mismo cierre de sesión)

Con los fixes de ardilla y gnomo ya en `master` (commits `f42c5a6` y
`c5697a7`), se corrió un lote de semillas nuevas (8001-8008, 6000 ticks,
cortado en 4 completas por tiempo) midiendo directamente el criterio
real que Diego fijó -- no la extinción por especie por separado, sino
cuántas semillas terminan con las 5 especies vivas SIMULTÁNEAMENTE:

| Semilla | gnomo | lobo | conejo | ardilla | caballo | Especies vivas |
|---|---|---|---|---|---|---|
| 8001 | 2 | 3 | 0 | 41 | 0 | 3/5 |
| 8002 | 5 | 1 | 0 | 0 | 0 | 2/5 |
| 8003 | 0 | 7 | 0 | 14 | 5 | 3/5 |
| 8004 | 0 | 6 | 8 | 22 | 11 | 4/5 |

**0 de 4 semillas cumplen el criterio del 50% con las 5 especies vivas a
la vez** -- el objetivo de Diego sigue sin alcanzarse, con la muestra
disponible hasta ahora. Pero hay progreso real y visible: la semilla
8004 le faltó únicamente gnomo, y en ninguna de las 4 semillas fallan
más de 3 especies a la vez (frente al colapso casi total que era la
norma al principio del día).

**Hallazgo nuevo, no anticipado**: **conejo está en 0 en 3 de las 4
semillas** -- antes una de las especies más robustas del catálogo
(nunca recibió ningún ajuste en toda la sesión), podría estar
convirtiéndose en el siguiente eslabón débil precisamente PORQUE las
demás especies mejoraron (más competencia real por el mismo espacio/
comida, o simplemente que conejo nunca tuvo su propio ajuste mientras
lobo/ardilla/gnomo sí). No investigado a fondo -- candidato directo si
se retoma esta investigación.

**Decisión de cierre de la sesión (Diego)**: documentar todo el estado
real y parar aquí, dado el tiempo ya invertido, en vez de seguir
iterando sin límite. Progreso neto del día, medido con honestidad: se
pasó de "ardilla y gnomo se extinguen en el 100% de las semillas,
0/10+ con las 5 especies vivas a la vez" a "ardilla y gnomo sobreviven
la mayoría de las veces individualmente, la combinación conjunta de las
5 especies vivas sigue sin lograrse en la muestra medida, con conejo
como nuevo candidato a investigar". El objetivo del 50% de Diego NO
está cumplido -- se documenta así explícitamente, sin inflar el
resultado.

**Pendiente real, en orden de prioridad si se retoma**:
1. Investigar por qué conejo, nunca tocado, empieza a fallar ahora --
   confirmar si es un efecto real de que las demás especies compitan
   más (más gnomos/ardillas vivos = más presión sobre el mismo espacio
   de pradera/bosque) o una coincidencia de estas 4 semillas concretas.
2. Correr un lote bastante mayor (15-20 semillas) para medir el %
   real del criterio de las 5 especies vivas con más confianza
   estadística que las 4 semillas de esta comprobación.
3. Si conejo se confirma como problema real, aplicar el mismo
   recetario (hambre + concepción combinadas) ya validado tres veces
   hoy (lobo, ardilla, gnomo) -- aunque conejo nunca mostró síntomas de
   este tipo antes, así que convendría diagnosticar primero, no asumir
   la misma causa sin medirla.
4. El PR #19 (radio de pareja ampliado) sigue sin fusionar -- su
   trade-off conocido (ayuda a gnomo, perjudica a caballo) puede haber
   quedado superado por el fix directo de gnomo de hoy; revisar si
   sigue mereciendo la pena antes de decidir su destino.
5. Harness completo (15 semillas × 12000 ticks) sigue siendo la
   referencia de rigor pendiente desde "Sobrepoblación..." para
   cualquier calibración que se quiera dar por cerrada de verdad.

## Medición directa del criterio real de Diego (segunda vuelta, lote más
## grande) + conejo confirmado como nuevo eslabón débil, con un hallazgo
## de sobrecorrección real -- ningún cambio de config aplicado todavía
## (2026-09-06, sesión siguiente al cierre del día anterior)

Continuación directa del pendiente #2 dejado por la sesión anterior
("correr un lote bastante mayor... para medir el % real del criterio de
las 5 especies vivas con más confianza estadística que las 4 semillas de
esta comprobación"). Arnés en scratchpad de sesión (no en el repo, mismo
criterio que arneses anteriores del proyecto), sin persistencia SQLite en
disco salvo un fichero temporal descartable por semilla.

**Medición, 8 semillas nuevas (9001-9008) × 6000 ticks, con los tres
fixes de lobo/ardilla/gnomo (hambre+concepción) más parejas fundadoras ya
en `master`**:

| Semilla | gnomo | lobo | conejo | ardilla | caballo | Especies vivas |
|---|---|---|---|---|---|---|
| 9001 | 2 | 10 | 75 | 39 | 0 | 4/5 |
| 9002 | 6 | 1 | 0 | 19 | 2 | 4/5 |
| 9003 | 0 | 4 | 0 | 24 | 5 | 3/5 |
| 9004 | 4 | 2 | 12 | 26 | 1 | 5/5 |
| 9005 | 2 | 1 | 0 | 4 | 5 | 4/5 |
| 9006 | 1 | 0 | 13 | 280 | 0 | 3/5 |
| 9007 | 1 | 2 | 6 | 0 | 5 | 4/5 |
| 9008 | 2 | 2 | 0 | 0 | 4 | 3/5 |

**1/8 (12%) semillas con las 5 especies vivas a la vez** -- mejor que el
0/4 de la comprobación anterior, pero lejos todavía del 50% que fijó
Diego como criterio. Extinción por especie: gnomo 1/8, lobo 1/8, conejo
**4/8 (50%)**, ardilla 2/8, caballo 2/8 -- confirma con una muestra el
doble de grande el hallazgo de la sesión anterior: conejo, nunca tocado
por ningún ajuste, es ahora el eslabón más frágil del catálogo. Causas de
muerte de conejo agregadas (8 semillas): inanición 1255 (73%), vejez 351
(20.5%), depredación 103 (6%), deshidratación 1 -- mismo patrón
dominado-por-inanición ya visto en lobo/ardilla/gnomo antes de sus fixes
respectivos.

**Causa raíz identificada antes de tocar nada**: `config/fisiologia.yaml`
-- conejo es la ÚNICA de las cuatro especies competidoras sin entrada
propia bajo `necesidades`, sigue con los valores universales de
`defecto` (`tasa_perdida_saciedad_por_tick=0.012`,
`probabilidad_muerte_saciedad_critica=0.005`) mientras lobo/ardilla/gnomo
ya bajaron a `0.0008`/`0.0004`. Su concepción (`factor_base_concepcion:
0.015`, `config/poblacion.yaml`) YA coincide con el valor al que se
subieron lobo y gnomo tras su propio fix -- no parece ser el cuello de
botella, a diferencia de lobo/ardilla/gnomo que necesitaban ambos
ingredientes a la vez. Hipótesis de por qué esto no se había visto antes
(no confirmada con más profundidad, razonamiento, no medición directa de
competencia real): con lobo/ardilla/gnomo colapsando rápido antes de sus
fixes, y caballo (especie nueva del día anterior, comparte pradera con
conejo) recién empezando a sostener población real, conejo nunca tuvo que
competir en serio por el mismo espacio/comida hasta ahora -- el
desequilibrio es indirecto, no un cambio en su propia configuración.

### Prueba A/B real contra el motor -- mismo recetario de hambre aplicado
### solo a conejo (sin tocar su concepción, ya buena): quita la extinción
### pero sobrecorrige con fuerza -- NINGÚN VALOR CAMBIADO EN EL CONFIG REAL

Monkeypatch en memoria (`config["necesidades"]["conejo"]` con los mismos
`0.0008`/`0.0004` de lobo/ardilla/gnomo), 5 semillas nuevas (9101-9105) ×
hasta 6000 ticks, comparando baseline vs. fix:

- **Baseline (sin fix)**: 0/5 con las 5 especies vivas, conejo extinto en
  4/5, media 13.8.
- **Con fix de hambre en conejo**: 5/5 con las 5 especies vivas, conejo
  extinto en 0/5 -- pero **disparado a 517-704 individuos en las cinco
  semillas, todas cortadas antes de completar los 6000 ticks por un tope
  de seguridad del propio arnés (500 individuos de una especie)**, frente
  a gnomo (3-13), lobo (3-17), ardilla (5-92) y caballo (1-9) en las
  mismas corridas. Ninguna semilla se estabilizó por sí sola dentro de la
  ventana medida -- el corte fue del arnés, no del motor.

**Diagnóstico, no solo el dato bruto**: a diferencia de lobo/ardilla/
gnomo (que necesitaban DOS ingredientes -- hambre Y concepción -- porque
partían con la peor reproducción del catálogo), conejo ya tenía la MEJOR
reproducción del catálogo antes de tocar nada (camada 3-7, gestación
15-25 días, concepción ya en 0.015). Aplicarle el mismo alivio de hambre
sin necesitar ningún empujón de concepción quita el freno de mortalidad
sin que haya ningún otro freno natural que lo compense -- sobrecorrección
real, no una mejora limpia. Razonablemente esperable que, dejado correr
la ventana completa, termine en un ciclo boom-bust (mismo patrón ya
documentado en "Sobrepoblación...") o que la explosión de conejo presione
por comida a las demás especies de pradera (caballo).

**ACTUALIZACIÓN, mismo día, tras discutir el hallazgo con Diego -- SÍ
aplicado a `master`**: en vez de dejarlo solo documentado, Diego pidió
subir el mismo alivio de hambre (`0.0008`/`0.0004`,
`fisiologia.yaml:necesidades.conejo`, nueva entrada) combinado con una
mitigación explícita de la sobrecorrección -- rebajar levemente el techo
de camada de conejo (`poblacion.yaml`, `camada: [3, 7]` → `[3, 5]`, solo
el máximo, sin tocar el mínimo), **sin volver a correr el motor tras este
cambio combinado** ("si quieres haz un pequeño ajuste... no hace falta
que lo testees" -- decisión explícita de Diego de aceptar el riesgo de un
valor sin reverificar, a cambio de no gastar otra ronda larga de
diagnóstico el mismo día). 216/216 tests en verde (sanity de que el
config sigue cargando y nada se rompe mecánicamente -- no es una
verificación de que la sobrecorrección quede resuelta).

**Pendiente real, explícito, ahora distinto del párrafo original de
arriba**: el efecto real de la combinación (hambre aliviada + camada
recortada) sobre conejo NO está verificado contra el motor -- candidato
directo a revisar en el próximo círculo de calibración que se retome,
antes de dar el ajuste por bueno; el criterio del 50% de Diego (5
especies vivas a la vez) sigue sin remedirse con este cambio ya aplicado;
el harness completo (15×12000) sigue pendiente para cualquier
calibración que se quiera dar por cerrada; el PR #19 (radio de pareja
ampliado) sigue sin fusionar, su destino sin decidir. Próximo círculo de
desarrollo, distinto de esta investigación de calibración, pendiente de
plantear con Diego.

## Capa de comunicación — arco completo cerrado, 5/5 piezas (2026-09-06)

Diego trajo un informe externo completo de "capa de comunicación"
(sonido físico, memoria espacial compartida, comunicación social/ocio/
conflicto/reputación) pidiendo analizar su viabilidad. Auditado contra
el código real antes de opinar (mismo criterio de siempre): el informe
tenía piezas sólidas pero también un problema serio de fondo —
proponía un componente `MemoriaSocial` nuevo que **ya existía** con
otro nombre (`componentes/relaciones.py:Relaciones`, cerrado el
2026-09-04 en el arco "hilo individual", con cuatro consumidores reales
ya construidos), y describía el visor como cliente **pygame-ce**
cuando en realidad es un servidor web con canvas HTML/JS desde hacía
semanas (mismo patrón de "informe externo con afirmaciones
desactualizadas" ya visto con la "Propuesta de profundidad" de
agosto). Descompuesto en 5 piezas independientes en brainstorming,
cada una su propio spec y su propio círculo de verificación contra el
motor real — **las 5 quedaron cerradas el mismo día**:

1. **Conflicto verbal** (PR #20) — en vez de inventar un disparador
   nuevo de "provocación" (redundante con la condición que ya activa
   `CRISIS_VIOLENTA`), se le dio consecuencia real a ese estado, que el
   propio código documentaba como "gesto de movimiento, sin mecánica de
   daño todavía": al contacto real, resuelve con `resolver_disputa`
   (refactor `_resolver_conflicto_entre`, compartido con el conflicto
   por refugio ocupado ya existente). Segundo disparador, más
   frecuente, pedido explícitamente por Diego tras notar que
   CRISIS_VIOLENTA por sí sola apenas haría fluctuar `Relaciones`: roce
   social probabilístico entre conscientes, modulado por agresividad
   combinada + gradiente de estrés (`1 - PoolMental.estabilidad`).
   Verificado en juego real: 131 roces + 3x más fluctuación de
   `Relaciones` en 1500 ticks frente a antes de la pieza.
2. **Memoria espacial compartida** (PR #21) — dos conscientes que
   coinciden pueden transferirse el sitio de comida/agua/refugio/
   asentamiento más cercano que conocen. Hallazgo de Diego que cambió
   el diseño en marcha: *"¿una memoria compartida tiene el mismo peso
   que un recuerdo propio?"* — resuelto sin campo de "confianza" nuevo,
   degradando la coordenada en el momento de compartir (pasa por
   `objetivo_recordado()` desde la perspectiva del emisor antes de
   registrarse en el receptor) en vez de al recordar. Verificado: 12490
   transferencias reales en 1500 ticks, coordenadas confirmadas en la
   BD que un individuo nunca visitó directamente.
3. **Ocio consciente / `Accion.SOCIALIZAR`** (PR #22) — nueva acción
   que compite con `DEAMBULAR`, primer consumidor real de
   `Temperamento.curiosidad` (sin uso hasta entonces). Se evaluó y
   descartó extender el sesgo gregario ya existente de `DEAMBULAR` (más
   barato pero mezclaba "vagar sin rumbo" con "socializar" en una sola
   acción) a favor de una Accion nueva, más fiel al informe original.
   Incidente de infraestructura real (no de la pieza): el modelo movió
   su propio plan a `done/` por iniciativa propia, rompiendo el `mv`
   hardcoded de `ejecutar-encargo.sh` justo antes de abrir el PR —
   corregido en la raíz (`mv` defensivo) y terminado el resto a mano.
4. **Sonido físico** (PR #23 + #24, partido en 4a/4b por tamaño —
   comparable a "armas primitivas v2", la única pieza que había agotado
   los 3 intentos del pipeline). Hallazgo de diseño clave: el informe
   proponía sonido como `Evento(severidad=RUIDO)`, descartado porque
   `bus_eventos.limpiar()` se ejecuta al cierre de cada tick — necesita
   buffer propio (dos campos efímeros en `Celda`, sin persistir:
   ventana de solo 5 ticks). Se conectó como TERCERA fuente de
   `nucleo/amenaza.py:posicion_amenaza_mas_cercana`, heredando gratis
   los tres consumidores reales ya existentes (seguridad, HUIR, empuñar
   arma) sin cablear nada nuevo. Idea de Diego que amplió el alcance:
   un depredador debería poder USAR el sonido para cazar, no solo huir
   de él — 4b añade un fallback en `_calcular_caza` que reutiliza el
   carroñeo (`_calcular_forrajeo`/`Necromasa`) ya existente sin
   tocarlo. Verificado 4a: 714 sonidos, 2862 amenazas detectadas
   específicamente por sonido en 3000 ticks. 4b: mecanismo correcto por
   9 tests dirigidos, pero 0 usos reales en la misma ventana — mismo
   patrón de "correcto pero invisible" ya visto con asentamiento/
   pareja/parentesco.
5. **Rumor + liderazgo con inercia real** (PR #25 + #26, partido en
   5a/5b). Diego reencuadró la pieza dos veces en conversación: primero
   como cimiento genérico de confianza reutilizable a futuro
   (mercadería, encargos, confiar en alguien), después cuestionando que
   un líder pudiera cambiar de un día para otro sin ningún "proceso" ni
   "adeptos acumulados". **Hallazgo que resolvió el diseño sin inventar
   estado nuevo**: `Asentamiento.id` se reasigna desde 1 cada día (sin
   identidad estable entre recálculos), pero `Relaciones` SÍ persiste
   en cada individuo — "tener seguidores" no necesita un contador de
   días en el poder, es literalmente afinidad acumulada. 5a: un
   consciente comparte su opinión sobre un tercero con quien coincide
   (degradación de segunda mano, mismo espíritu que memoria
   compartida), cero funciones nuevas en `nucleo/relaciones.py`. 5b:
   lealtad diaria miembro→líder (mismo patrón que amistad por
   convivencia) + `calcular_liderazgo` lee reputación para descalificar
   candidatos dominantes mal valorados y desempatar antes de llegar a
   valentía. Verificado: 441 aplicaciones de lealtad real en 3000
   ticks (asentamientos SÍ llegaron a formarse en esta corrida); los
   efectos específicos de reputación (descalificación, cambio de
   desempate) en 0 en la misma ventana — mecanismo correcto por 7 tests
   dirigidos, payoff observable bajo, señalado con honestidad desde el
   propio diseño.

**Patrón operativo de toda la sesión**: cada pieza siguió el flujo fijo
completo (brainstorming → spec escrito y aprobado por Diego → encargo
mínimo al pipeline → auditoría manual del diff + verificación
independiente contra `BOSQUE_AUTO_TICKS` reproduciendo las cifras
exactas del pipeline → merge manual). Ninguna pieza se mergeó sin esa
segunda verificación independiente. Piezas grandes (sonido, rumor+
liderazgo) se partieron en sub-círculos por decisión explícita de
Diego cuando el tamaño se acercaba al de "armas primitivas v2".

**Pendiente real, explícito, tras cerrar el arco completo**:
- Todas las constantes nuevas de las 5 piezas (`probabilidad_base_
  roce_social`, `radio_sonido_base`, `peso_credibilidad_rumor`,
  `delta_lealtad_liderazgo`, `umbral_reputacion_descalificante`, y el
  resto) siguen PROVISIONALES, sin calibrar contra el harness completo.
- ~~El fallback de sonido como pista de caza (4b) y los efectos de
  reputación en liderazgo (5b)... no se ha observado su disparo real en
  juego libre todavía~~ — CORREGIDO el mismo día, ver la sección
  "Auditoría post-cierre" más abajo: con semillas nuevas (no solo la
  42), ambos SÍ se disparan de verdad. Verificar con una sola semilla
  no basta para concluir invisibilidad.
- **Menú de ideas futuras sobre esta base, planteado a Diego el mismo
  día de cerrar el arco, ninguna diseñada todavía** — tres horizontes:
  - **Cerca, círculos pequeños, casi todo ya construido**: (1) robo/
    agravio genérico -- `nucleo/conflicto.py` lo declara como
    consumidor futuro desde su diseño original (30-08), reutilizaría
    `resolver_disputa` tal cual con un disparador nuevo (necesidad
    urgente + tomar recursos ajenos de `Inventario`/`Construccion`).
    (2) Llamada de alarma -- tercer uso real de `nucleo/sonido.py`
    (tras detección de amenaza y pista de caza): un individuo que
    detecta una amenaza REAL emite su propio sonido, más barato que un
    combate, alertando a quien esté cerca -- comportamiento animal
    genuino, infraestructura ya construida.
  - **Medio, las ideas que Diego mencionó explícitamente al diseñar
    rumor social (5a)**: trueque (intercambio de materiales entre
    `Inventario`/`Construccion`, disposición modulada por `Relaciones`
    -- solo intercambias con quien confías) y encargos/cooperación
    dirigida (pedirle a alguien que aporte a TU objetivo en vez del
    suyo) -- esta segunda, más ambiciosa, merece su propio círculo de
    diseño aparte cuando llegue el momento.
  - **Lejos, lo que más conecta con la aspiración Tolkien declarada del
    proyecto**: leyendas/memoria oral -- `cronica_eventos` ya registra
    sucesos NOTABLES/HISTÓRICOS pero nadie en el mundo "sabe" de ellos;
    si el rumor propagara conocimiento de sucesos notables (no solo
    opiniones sobre terceros), la fama de un individuo se extendería
    emergentemente más allá de quien lo conoció en persona -- la pieza
    que más se acerca a "riqueza narrativa por emergencia algorítmica,
    nunca por autoría manual". Y facciones entre asentamientos --con
    liderazgo/reputación ya reales y varias cuevas/asentamientos ya
    posibles desde el arco de profundidad, diplomacia/conflicto entre
    GRUPOS (no solo individuos) sería el siguiente salto de escala,
    civilización en vez de solo pueblo.
- Créditos de licencia de PyxelSpace (pendiente desde la migración del
  24-08, ver arriba) y el harness completo de 15×12000 siguen sin
  abordarse — sin relación con este arco, solo recordatorio de que
  siguen en la lista.

### Auditoría post-cierre: revisión de código independiente + verificación
### multi-semilla, cuatro correcciones aplicadas (2026-09-07)

Diego pidió testear el arco completo y analizarlo "como un agente
externo" para mejorarlo. Dos hallazgos metodológicos reales antes de
las correcciones en sí:

- **Verificar con una sola semilla (42) no basta para concluir
  "invisible en juego libre"**: las piezas 4b (pista de caza) y 5b
  (reputación en liderazgo) se habían cerrado con "0 usos observados"
  en la semilla 42. Con 6 semillas nuevas (601-608) × 3000 ticks sin
  excepciones, **ambos mecanismos se dispararon de verdad** — caza por
  sonido en 3 de 7 corridas, descalificación por reputación en 4 de 7.
  El patrón real no era "nunca ocurre", era "esa semilla concreta no lo
  disparaba". Lección para verificaciones futuras de piezas raras:
  varias semillas nuevas, no una sola, antes de concluir invisibilidad.
- **Una revisión de código independiente (fork sin el contexto de
  diseño de esta sesión) encontró un bug de correctness real cruzando
  dos piezas ya mergeadas** que ninguna verificación por pieza había
  detectado, precisamente porque solo se manifiesta en su interacción.

**Cuatro correcciones aplicadas, todas verificadas (282/282 tests,
motor real sin excepciones)**:

1. **Bug real, corregido** (`b8b8915`): `_procesar_roce_social`
   (probabilístico, corre una vez al principio de `ejecutar()`) y
   `_calcular_crisis_violenta` con contacto (determinista) podían
   resolver el MISMO par dos veces en el mismo tick vía
   `_resolver_conflicto_entre` -- doblando drenaje de seguridad y
   rencor. No era un caso raro: la probabilidad de roce social sube con
   el mismo estrés que dispara CRISIS_VIOLENTA, así que están
   correlacionados. Fix: set de pares ya resueltos por tick, compartido
   por los tres disparadores (refugio ocupado, roce social,
   CRISIS_VIOLENTA), consultado en el único punto de entrada compartido.
2. **Comentario desactualizado, corregido** (`90c47a2`):
   `Accion.CRISIS_VIOLENTA` en `componentes/intencion.py` seguía
   diciendo "sin mecánica de daño todavía" pese a que conflicto verbal
   ya le había dado consecuencia real -- viola el propio principio de
   honestidad del proyecto (comentario como fuente de verdad sobre
   huecos).
3. **División por cero latente, corregida** (`90c47a2`):
   `nucleo/sonido.py:_radio_audible` no protegía contra
   `peso_referencia_sonido` en 0 -- inofensivo hoy (valor fijo 90.0),
   pero esa constante es PROVISIONAL y este proyecto la recalibra a
   menudo; un valor inválido futuro habría tumbado el tick entero.
4. **Capacidad de `Relaciones` insuficiente, corregida** (`23231e2`):
   `min/max_vinculos_por_individuo` (2/6) se fijó cuando solo rencor y
   amistad escribían ahí. Con 7 fuentes compartiendo el mismo cupo
   diminuto -- sobre todo rumor social, que escribe sobre TERCEROS al
   azar en cada encuentro -- medido que de 2391 contactos de
   `SOCIALIZAR` solo 10 vínculos positivos sobrevivían al final. Subido
   a 4/12, sigue PROVISIONAL.

**Hallazgos reales, NO corregidos todavía, señalados para una sesión
futura**:
- Tres copias casi idénticas del escaneo "vecino más cercano"
  (`_entidad_cercana_cualquiera`, `_entidad_cercana_cualquiera_con_id`,
  `_consciente_mas_cercano_con_id`) en `sistema_movimiento.py` en vez de
  una función parametrizada -- mismo patrón de duplicación que ya costó
  tiempo antes en este proyecto (almacén/refugio sin filtrar por zona).
- `_procesar_memoria_compartida` y `_procesar_rumor` repiten el mismo
  bucle O(k²) de pares ordenados sobre `por_celda` (junto a
  `_procesar_roce_social`, tres pasadas casi idénticas) sin cachear los
  componentes del emisor entre iteraciones -- aceptable a la escala
  actual, pero un cuarto consumidor futuro (robo/agravio genérico,
  todavía sin construir) probablemente copiaría un cuarto bucle en vez
  de reutilizar un despachador de pares por celda compartido.
- Comentarios nuevos de las 5 piezas (fechas, "círculo X", rutas
  completas de spec) siguen incrustados en el código en vez de en
  `docs/historial_<módulo>.md` -- viola la convención que el propio
  proyecto cerró el 2026-09-02. Pendiente de una poda dedicada (la
  única clase de tarea que este proyecto ya confirmó que falla
  delegada al pipeline, 2/2, así que tendría que hacerla Claude
  directamente).
- `calcular_liderazgo`: la descalificación por reputación reduce la
  lista de candidatos ANTES de calcular cohesión social para la
  decisión consejo-vs-líder-único -- coincide con lo que el propio spec
  de 5b especificaba literalmente, pero el efecto secundario
  (descalificar a uno puede voltear consejo↔líder único) no se pensó a
  fondo al diseñarlo. Señalado como decisión de diseño a revisar con
  Diego, no como bug.
- `STATS_DESEMPATE_REPUTACION_CAMBIO` no captura el caso de
  descalificación total del ganador presunto (ese caso ya lo cuenta
  `STATS_REPUTACION_DESCALIFICADOS` por separado) -- las dos cifras
  juntas sí capturan el impacto real de la reputación, pero un lector
  de una sola cifra podría subestimarlo. Aclarar en un futuro pase, no
  urgente.

## Manada — estructuras gregarias reales en fauna, cerrada (2026-09-07)

Diego pidió diferenciar el comportamiento gregario por especie (lobo,
caballo, conejo, ardilla) en vez de un único sesgo genérico —
preguntando explícitamente si una manada de lobos debía comportarse
igual que una de conejos. Investigado especie por especie antes de
proponer nada: la mayoría de esa diferenciación YA existía, repartida
en rasgos ya construidos (`medio_alimentacion == "cazar"` ya hace de
lobo la única especie con caza en grupo; `sociabilidad` ya es la más
alta en caballo y la más baja en ardilla). Solo la madriguera excavada
y compartida de conejo exigía algo genuinamente nuevo — un rasgo
racial más, `tipo_refugio_fauna: colonial`, mismo patrón categórico
que `medio_alimentacion` (hecho físico real de la especie, no autoría
de un suceso concreto). Evita repetir el error ya corregido una vez en
este proyecto (categorizar cuevas por tamaño/bioma).

**Diseño**: `Manada` (`nucleo/manada.py`) como objeto real, mismo
molde que `Asentamiento` (sin identidad persistida entre recálculos
diarios, no se guarda en SQLite), formada por pura proximidad
(`agrupar_por_proximidad`, extraída junto a `calcular_centro` a un
módulo neutral nuevo, `nucleo/agrupacion.py`, reutilizado por
asentamiento y manada). Sin gate de sociabilidad para formar el grupo
— la sociabilidad de cada individuo sigue decidiendo, como ya hacía,
cuánto tira hacia el centro, así que una especie poco sociable rara
vez se comporta como manada real aunque la geometría la agrupe por
casualidad. Madriguera compartida (conejo): sincronizada por VOTO DE
MAYORÍA sobre lo que los miembros YA recuerdan individualmente, nunca
una coordenada elegida a dedo — se estabiliza sola con los días porque
la persistencia real vive en `MemoriaEspacial`, ya persistida por
individuo, no en `Manada`. Primer consumidor: `_calcular_deambular`
tira hacia el centro de la manada en vez de solo el conespecífico más
cercano, produciendo grupos más compactos y estables.

**Incidente real de pipeline, sin relación con la calidad de la
spec**: el único intento agotó los 2700s en el paso 177 sin escribir
ni una línea de código ni comitear su propio plan — solo exploración
extensa de `nucleo/asentamiento.py`. Coste bajo ($0.25), sin nada que
rescatar (a diferencia de "armas primitivas v2", aquí no hubo ningún
diff real). Diego pidió implementarlo directamente en vez de
reintentar — **cerrado el mismo día**, 9 tests nuevos, 291/291 en
verde, mergeado a `master` (`f24bd4f`) tras auditoría propia y
verificación contra el motor real.

**Verificado contra el motor real (3000 ticks, semilla por defecto),
resultado inusualmente fuerte para una pieza recién cerrada**: manadas
formadas por especie `{gnomo:1, conejo:2, lobo:1, caballo:1}` (ardilla
0, coherente con su sociabilidad más baja del catálogo, sin necesidad
de excluirla a mano); **14897 sincronizaciones de madriguera, 597
miembros de conejo recibieron un sitio de refugio que no tenían
antes** — a diferencia de varias piezas del arco de comunicación
("correctas pero invisibles" en juego libre), esta se ejerce con
fuerza desde el primer día.

**Pendiente real, explícito**:
- `radio_manada_celdas`/`tipo_refugio_fauna` PROVISIONALES, sin
  calibrar contra el harness completo.
- Sin liderazgo ni "macho alfa" de manada — extensión futura obvia,
  reutilizaría `calcular_liderazgo` tal cual (`dominancia` ya existe
  para las 4 especies fauna).
- "Techo de presa por manada" de lobo (conteo instantáneo de
  conespecíficos cazando cerca) se queda intacto, sin unificar con la
  nueva estructura persistente-por-día — posible unificación futura,
  no hecha aquí para no forzar un refactor no pedido.
- Que una manada de gnomo también se formara (además de su
  `Asentamiento` ya existente, un concepto distinto) no se excluyó a
  propósito (ley neutra, sin excepción por especie) — inofensivo en
  esta corrida, pero señalado por si resulta confuso más adelante.

## Madriguera física — capacidad finita y beneficios reales (círculos A+B),
## cerrada — implementada directamente por Claude tras fallos repetidos
## del pipeline, incidente real de infraestructura (2026-09-07)

Extensión directa de `Manada` (arriba): Diego, viendo la madriguera
compartida funcionando (14897 sincronizaciones, 597 conejos con sitio
nuevo), señaló dos huecos reales -- (1) sin ningún límite, una sola
madriguera podía "contener" a 200 conejos, cuando debería forzar a que
se formen varias comunidades al crecer la población; (2) un refugio
individual no debe tener bonificación (decisión ya tomada,
`_calcular_dormir`: "el beneficio es puramente conductual"), pero una
madriguera colonial SÍ debería dar beneficios reales -- confirmado
explícitamente por Diego que quería ambos beneficios (confort térmico +
seguridad). Diseñado en dos specs (`docs/superpowers/specs/
2026-09-07-madriguera-fisica-a-design.md` y `...-b-design.md`),
partidas desde una única spec combinada tras dos timeouts consecutivos
del pipeline sin ningún progreso (`docs/plans/failed/
2026-09-07-madriguera-fisica.md`).

**Incidente real de infraestructura, no de diseño**: Trozo A también
falló en su primer intento del pipeline con el mismo patrón (exploración
larga, sin converger). Diego, viendo el segundo intento repetir el mismo
patrón ("está tardando mucho... la vez anterior que falló tambn"), pidió
cancelarlo directamente ("cancelalo, algo no está funcionando con el
modelo") en vez de esperar el timeout completo. La cancelación manual
(`kill -TERM` en cascada sobre el árbol de procesos del pipeline) se
clasificó como "fallo de infraestructura externa" (código de salida no
estándar, indistinguible para el script de un fallo real del proxy) --
efecto colateral real: **esto detuvo el centinela por completo**
(`CENTINELA DETENIDO`, diseño intencional del disyuntor para no seguir
recogiendo trabajo a ciegas tras algo que parece un fallo externo). Sin
código perdido (la rama huérfana se autoeliminó, sin progreso real que
proteger). **El centinela sigue parado a fecha de esta nota** -- pendiente
de reinicio manual (`.ai-pipeline/start-pipeline.sh` o `centinela.sh`)
antes de que el pipeline pueda recoger cualquier encargo futuro.

**Decisión de Diego tras esto**: implementar directamente los dos
círculos (A y B) en la sesión, sin reintentar el pipeline -- excepción
ya prevista en la sección "Flujo de implementación" de este documento
("Diego lo pide explícitamente"). Tres fallos consecutivos del pipeline
sobre esta misma pieza (Manada en su día, madriguera-fisica combinada, y
Trozo A dos veces) quedan señalados como una pregunta de fiabilidad
todavía sin resolver -- ver "Pendiente real" más abajo, conecta con la
memoria persistente `project_evaluar_modelos_pipeline.md` (comparar
`deepseek-v4-flash-0731` contra alternativas).

### Círculo A -- entidad física real, capacidad finita

**Hallazgo de diseño clave del propio spec**: para que la capacidad sea
un límite físico real (no solo un número comparado y ya), la madriguera
deja de ser "solo una coordenada en `MemoriaEspacial`" y se convierte en
una entidad física real y persistida -- mismo molde exacto que `Fogata`
(`Posicion` + un componente, sin `Identidad` ni `Intencion`).

- `componentes/madriguera.py` (nuevo): `Madriguera(capacidad: int)`.
- `nucleo/entidad.py:crear_madriguera` -- mismo molde que `crear_fogata`.
- `nucleo/madriguera.py:madriguera_en` -- mismo molde que `fogata_en`.
- `sistemas/sistema_manada.py:_sincronizar_madriguera`, reescrita:
  `SistemaManada` gana `rng` en su constructor (`main.py:
  instanciar_sistemas` le pasa `rng_juego`); localiza o crea la
  `Madriguera` física en el sitio mayoritario (capacidad sorteada
  **una sola vez**, `rng.randint` dentro de `capacidad_madriguera` por
  especie, mismo patrón que el tamaño de una cueva al generarse -- nunca
  se vuelve a sortear); admite con prioridad a quien YA tenía el sitio en
  su memoria (`ya_establecidos`) sobre quien lo recibiría por primera vez
  (`nuevos`), topado a `capacidad`; el resto no se sincroniza ese día, su
  memoria individual queda intacta.
- `config/poblacion.yaml`: `capacidad_madriguera: [10, 25]` (PROVISIONAL,
  solo conejo).
- Persistencia: tabla `madriguera_estado` (mismo molde que
  `fogata_estado`), `VERSION_ESQUEMA` sube a `"0.34-fase0"`
  (DROP-and-recreate, sin migración, criterio ya establecido).

### Círculo B -- beneficios reales de confort y seguridad

Reutiliza `madriguera_en` de A sin tocarlo. Mismo patrón aditivo que
`bono_confort_refugio`/`bono_confort_fogata`/`bono_seguridad_pareja` en
`sistema_necesidades.py`, dos veces más -- `bono_confort_madriguera`
(0.3) suma al objetivo de confort térmico, `bono_seguridad_madriguera`
(0.1, mayor que `bono_seguridad_pareja`=0.05 -- "una madriguera protege
más que la sola compañía de la pareja") suma a la recuperación de
seguridad, topada a 1.0. **Se aplican a CUALQUIERA que esté físicamente
en la celda de la madriguera en ese momento**, sin exigir que la tenga
en su propia memoria ni ser de la especie colonial -- desacopla
deliberadamente "quién la usa de hecho" (bono, círculo B) de "quién está
admitido para que se le sincronice como destino de navegación" (círculo
A). `config/fisiologia.yaml`, sección `necesidades.defecto`, ambos
PROVISIONALES.

### Verificación contra el motor real, no solo tests

300/300 tests en verde (9 nuevos, `tests/test_madriguera_fisica.py`:
creación/búsqueda respetando zona, sorteo de capacidad solo la primera
vez, reutilización sin re-sortear, cupo respetado con prioridad a
ya-establecidos, los dos bonos aplicándose con su tope, refugio
individual sin ningún bono, cualquier especie beneficiándose sin gating).

`BOSQUE_AUTO_TICKS=3000` sin ninguna excepción: **29 madrigueras físicas
creadas** a lo largo de la corrida (capacidades reales 11-24, dentro del
rango configurado), **5763 exclusiones por cupo lleno** (contador directo
nuevo, `SistemaManada._stats_madriguera_excluidos_por_cupo` -- eventos
acumulados, no individuos únicos) confirmando que el cupo actúa de
verdad y con fuerza, no es un límite teórico nunca alcanzado; al cierre
de la corrida, **3 manadas de conejo simultáneas** -- evidencia directa
(no prueba, tal como pedía el spec con honestidad) de que el cupo
finito empuja hacia varias comunidades en vez de una sola. Roundtrip de
persistencia verificado explícitamente (`BOSQUE_CONTINUAR=1`): las 29
madrigueras y sus capacidades exactas se recuperan intactas tras
recargar desde SQLite.

**Pendiente real, explícito**:
- `capacidad_madriguera`/`bono_confort_madriguera`/
  `bono_seguridad_madriguera` PROVISIONALES, sin calibrar contra el
  harness completo.
- **El centinela sigue detenido** -- reiniciar manualmente antes de
  soltar cualquier encargo futuro al pipeline.
- **Fiabilidad del pipeline sobre esta clase de tarea, sin resolver**:
  tres fallos consecutivos (Manada, madriguera-fisica combinada,
  Trozo A ×2) sobre piezas que exigen replicar un molde ECS existente
  (mismo patrón que `Fogata`) -- no investigado a fondo si es un patrón
  de tarea específico que confunde al modelo actual o una racha. Antes
  de la próxima pieza de complejidad similar, decidir con Diego si
  investigar el modelo/pipeline (ver `project_evaluar_modelos_pipeline.md`
  en memoria persistente) o seguir troceando/implementando directamente
  caso a caso.
- Con esto, la extensión completa de "madriguera física" sobre `Manada`
  queda cerrada (círculos A y B).

## Calibración de estabilidad del ecosistema -- caballo y agua, criterio
## maestro cruza el 50% de Diego en la medición, deshidratación como
## hallazgo real sin resolver del todo (2026-09-07)

Diego pidió explícitamente una ronda de pruebas contra el motor real
para calibrar lo marcado PROVISIONAL "para que el ecosistema sea
medianamente estable y los flujos que hemos creado se den de forma
natural". Catalogadas 91 líneas `PROVISIONAL` en `config/*.yaml` -- **sin
barrido ciego**, mismo criterio de siempre: solo se tocó lo que una
medición real contra el motor señaló como bloqueo concreto.

**Metodología**: arnés propio sin SQLite (scratchpad, no en el repo),
reutilizando `main.py` tal cual (`cargar_configuracion`,
`instanciar_sistemas`, `sembrar_poblacion_inicial`, `sembrar_flora_inicial`,
`ejecutar_tick`) con una `Persistencia` de mentira (no-op) para evitar el
coste real de I/O. **Ventana de 4000 ticks, no 6000-8000** -- decisión
explícita por coste real medido: con la población creciendo hacia el
tope de seguridad (varias partes del motor son O(N) o peor por tick,
`_buscar_conspecifico_mas_cercano` ya documentado O(N²)), una sola
semilla a 6000 ticks superó los 520s de una única llamada -- un lote de
6-10 semillas en paralelo a 8000 ticks no cabía en el presupuesto de
tiempo real de esta sesión. **Limitación honesta de esta calibración**:
una ventana de 4000 ticks probablemente infla la tasa de supervivencia
frente a 6000-8000 (especies que acabarían muriendo más tarde siguen
vivas a la mitad de camino) -- los números de aquí no sustituyen al
harness completo de 15×12000 que sigue pendiente desde
"Sobrepoblación...".

### Diagnóstico -- lote base, 6 semillas nuevas (40001-40006) × 4000 ticks, `master` sin tocar

**4/6 (67%) con las 5 especies vivas simultáneamente** -- ya por encima
del 50% que fijó Diego como criterio, aunque con dos hallazgos reales
que exigían corrección antes de dar esto por bueno:

1. **Caballo, único caso de extinción real (2/6 semillas)**, inanición
   como causa dominante en las 6. Causa raíz: caballo -- la especie más
   nueva del catálogo (2026-09-05) -- nunca recibió el recetario de
   hambre/concepción ya aplicado a gnomo/lobo/conejo/ardilla; seguía con
   `necesidades.defecto` (el mismo valor universal que ya había
   resultado insuficiente para las otras cuatro) y la
   `factor_base_concepcion` MÁS BAJA de todo el catálogo (0.005, más
   baja incluso que gnomo antes de su propio fix) pese a tener un perfil
   reproductivo (gestación corta, camada hasta 2) mucho más parecido al
   de lobo/gnomo ya recalibrados que al caso que justificaba un valor
   tan bajo -- probablemente un descuido de cuando se diseñó la especie,
   nunca revisado.
2. **Deshidratación como causa de muerte real y significativa en las 6
   semillas**, en las 5 especies -- contradice lo documentado
   previamente ("deshidratación prácticamente irrelevante, 1 muerte en
   10 semillas × 8000 ticks", sección "Fragilidad de lobo..."). Mismo
   patrón exacto que "vejez enmascarada por inanición": al bajar
   `tasa_perdida_saciedad_por_tick` de 0.012 a 0.0008 para gnomo/lobo/
   conejo/ardilla (15x más lento), la hidratación (`tasa_perdida_
   hidratacion_por_tick=0.004`, sin tocar) pasó a decaer ~5x más rápido
   que el hambre para esas cuatro especies -- un cuello de botella que
   quedaba oculto detrás de la inanición hasta que esta se resolvió.
   Causa raíz confirmada, no solo sospechada: medido contra 4 mundos
   generados reales que solo el **3.3%-11.1% de las celdas tienen agua
   potable** (permanente + charco, sin lluvia todavía), frente al radio
   de búsqueda genérico (0-4 celdas, el mismo que ya usan comida y
   amenaza) -- insuficiente con frecuencia real en semillas de baja
   cobertura hídrica, agravado porque ríos/lagos/pozas son clusters
   contiguos, no dispersos uniformemente.

### Fix aplicado, verificado, mergeado (`e876e18`)

- **Radio de búsqueda propio para `Accion.BEBER`** (2-8 celdas,
  `config/comportamiento.yaml:percepcion.radio_minimo/maximo_agua_celdas`),
  mismo patrón arquitectónico que ya tenía diseñado (sin mergear)
  `Accion.BUSCAR_PAREJA` en el PR #19 -- **PR #19 se cierra sin mergear
  la rama tal cual; su cambio funcional (radio 3-12 celdas para
  búsqueda de pareja) se adapta e integra en este mismo commit**, junto
  al de agua, en vez de mergear una rama de hace un día sin evidencia
  propia comiteada de su efecto real (revisado explícitamente: ni el PR
  ni sus comentarios ni el plan movido a `docs/plans/in_review/`
  contenían ningún número real medido, pese a que CLAUDE.md mencionaba
  un supuesto trade-off "ayuda a gnomo, perjudica a caballo" sin
  evidencia comiteada -- tratado como no verificado y sustituido por
  esta decisión con datos propios).
- **Caballo gana entrada propia en `config/fisiologia.yaml:necesidades`**
  (mismo par `0.0008`/`0.0004` que las otras cuatro) y
  `factor_base_concepcion` sube de 0.005 a 0.015 (igual que gnomo/lobo)
  en `config/poblacion.yaml`.

**Verificado**: 300/300 tests en verde, `BOSQUE_AUTO_TICKS=2500` con la
semilla por defecto sin ninguna excepción. Lote de 6 semillas NUEVAS
(50001-50006, nunca vistas antes -- mismo criterio metodológico de
siempre, nunca semilla-a-semilla) tras el fix:

- **Caballo: 0/6 extinción** (frente a 2/6 antes) -- la especie
  sobrevive con población real en las 6 (7-20 individuos).
- **4/6 (67%) con las 5 especies vivas simultáneamente** -- mismo
  porcentaje que el lote base, pero ahora el fallo residual es ardilla
  (2/6, consistente con su ~25% de fracaso ya documentado desde su
  propio fix, no una regresión nueva) en vez de caballo.
- **Deshidratación sigue siendo una causa de muerte real y en algunos
  casos incluso más alta en términos absolutos** (p.ej. semilla 50005:
  165 muertes de conejo por deshidratación) -- **hallazgo honesto, no
  resuelto del todo**: el radio ampliado mejora el acceso real
  (confirmado por el diagnóstico de cobertura hídrica), pero en
  poblaciones de conejo ya muy densas (300+ individuos por la propia
  explosión reproductiva de la especie, ver más abajo) más población
  compitiendo por la misma agua sigue produciendo muchas muertes
  absolutas por esta causa, con independencia del radio de búsqueda.
  **Hipótesis razonada, no confirmada con más profundidad**: esto podría
  estar funcionando como un freno natural de densidad legítimo (misma
  familia de mecanismo que la fertilidad por nutrición ya aceptada en
  "Sobrepoblación...") en vez de un defecto a eliminar -- no se tocó
  `tasa_perdida_hidratacion_por_tick` en este círculo por no tener
  evidencia de que hacerlo sea una mejora real y no solo desplazar el
  problema, mismo criterio de prudencia que ya se aplicó una vez con
  conejo (alivio de hambre en solitario disparó la población sin
  ningún freno).

### Explosión de conejo -- medida, NO tocada en este círculo, decisión explícita

En **9 de las 12 semillas medidas en total** (ambos lotes, antes y
después del fix), conejo alcanzó el tope de seguridad del propio arnés
de diagnóstico (400 individuos) antes de completar los 4000 ticks --
`abortado_por_explosion: true`. Vejez fue la causa de muerte DOMINANTE
para conejo en las 12 semillas (90-199 por semilla), no inanición ni
deshidratación -- **explicado, no es un bug**: con `TICKS_POR_ANIO=480`
(`Reloj.TICKS_POR_DIA=24 × DIAS_POR_ESTACION=5 × ESTACIONES_POR_ANIO=4`)
y una longevidad racial de 1-3 años (480-1440 ticks), un conejo nacido
en cualquier punto de una corrida de 4000 ticks tiene margen de sobra
para llegar a viejo -- turnover generacional rápido esperable en un
r-estratega, no una anomalía.

**Decisión explícita: no se tocó `camada`/`factor_base_concepcion` de
conejo más allá del recorte ya aplicado el 2026-09-06** (`camada`
`[3,7]`→`[3,5]`, sin re-verificar hasta ahora). Razonamiento: (1) el
propio criterio maestro de Diego (5 especies vivas a la vez) se sigue
cumpliendo en la mayoría de semillas pese a la explosión de conejo --
ninguna otra especie se extinguió POR CAUSA de la competencia de conejo
en los datos medidos; (2) 400 individuos de conejo sobre 1600 celdas
(0.25 ind/celda solo para conejo) es del mismo orden de magnitud que el
pico de 0.34 ind/celda ya aceptado como "boom-bust normal que se
autocorrige" en "Sobrepoblación..." -- no hay evidencia de que esto sea
cualitativamente distinto, solo de que mi propia ventana de
verificación (4000 ticks, tope de seguridad 400) es demasiado corta
para ver si busca solo o no lo hace; (3) seguir apretando el freno de
conejo sin verificar si el boom se autocorregiría con más tiempo
repetiría el error ya cometido una vez con este mismo parámetro
("alivio de hambre en solitario disparó a 500-700 sin estabilizarse" --
la propia investigación de esa sobrecorrección ya es la lección
aplicable aquí, no hace falta repetirla a ciegas). **Pendiente real,
explícito**: confirmar con una ventana más larga (6000-8000 ticks, tope
de seguridad más alto) si conejo realmente busca de forma natural o si
hace falta un tercer ajuste -- no se pudo hacer en esta sesión por el
coste real de cómputo ya señalado arriba.

### "Flujos naturales" -- confirmado que SÍ se disparan con regularidad,
### contraste real con el hallazgo repetido de sesiones anteriores

Las 12 semillas medidas (ambos lotes) traen también datos directos
sobre si los mecanismos sociales/gregarios ya construidos se ejercen de
verdad en juego libre, no solo en tests dirigidos -- la pregunta
explícita de Diego ("que los flujos... se den de forma natural"):

- **Asentamiento (2+ miembros conscientes)**: se formó en **12 de 12
  semillas** (1-3 asentamientos simultáneos por semilla) -- contraste
  directo con el hallazgo repetido de las sesiones de cierre del arco
  "hilo individual" y "capa de comunicación" ("0 asentamientos con 2+
  miembros conscientes... la población se extinguió antes"). Con la
  población ya más estable, este mecanismo deja de ser "correcto pero
  invisible".
- **Pareja estable derivada (gnomo)**: activa en **10 de 12 semillas**
  (0-10 parejas simultáneas) -- mismo contraste, antes documentado como
  "0 casos reales, población extinta antes de acumular afinidad
  suficiente".
- **Manada + madriguera compartida**: las 5 especies formaron manada en
  ambos lotes; `BOSQUE_AUTO_TICKS=2500` (semilla por defecto) confirmó
  29 madrigueras físicas activas y 1274 exclusiones reales por cupo
  lleno en esa sola corrida.
- **Rumor social, lealtad de liderazgo, reputación**: confirmados
  disparándose con fuerza real en la misma corrida de 2500 ticks (15357
  rumores propagados, 154 aplicaciones de lealtad, 4 candidatos
  descalificados por reputación).
- **Único mecanismo que NO se disparó en esta corrida concreta**: el
  fallback de caza por sonido (0 usos en 2500 ticks, semilla por
  defecto) -- ya documentado como "correcto pero raro, necesita varias
  semillas para observarse", no una regresión nueva.
- **No medido en este círculo**: parentesco derivado (madre-hijo ambos
  vivos) -- el arnés no lo instrumentó; dado el volumen real de
  nacimientos medido (cientos por semilla en conejo/ardilla), es
  altamente probable que se esté dando, pero no se confirmó con un
  contador directo. Hueco honesto, no una afirmación sin respaldo.

### Pendiente real, explícito, tras este círculo

- `radio_minimo/maximo_agua_celdas`, `radio_minimo/maximo_pareja_celdas`,
  `factor_base_concepcion`/fisiología de caballo: todos PROVISIONALES,
  sin calibrar contra el harness completo.
- Deshidratación en poblaciones densas de conejo sigue sin resolver del
  todo -- candidato real para una vuelta futura, con la hipótesis de
  "freno de densidad legítimo" señalada explícitamente para no
  sobrecorregir sin verificar primero.
- Explosión de conejo (9/12 semillas tocan el tope de seguridad del
  arnés) medida pero NO tocada -- necesita verificación con ventana más
  larga antes de decidir si hace falta un tercer ajuste.
- Parentesco derivado sin confirmar con contador directo en juego libre
  (probable pero no medido).
- El resto del catálogo de 91 líneas `PROVISIONAL` (combate, materiales,
  fuego, cueva, mundo, flora, nombres, armas, clima -- ver inventario
  completo con `grep -rn PROVISIONAL config/*.yaml`) **no se tocó**,
  deliberadamente -- ninguno mostró relación causal con el criterio
  maestro de Diego ni con los "flujos naturales" en esta investigación;
  tocarlos sin una medición que los señale habría sido un barrido ciego,
  justo lo que este círculo evitó a propósito.
- Harness completo (15 semillas × 12000 ticks) sigue pendiente desde
  "Sobrepoblación..." -- esta calibración (12 semillas × 4000 ticks) es
  direccional, no una calibración cerrada de verdad; la ventana más
  corta que la práctica habitual (6000-8000) es una limitación real de
  esta sesión, no una elección de rigor.

Commit: `e876e18`. PR #19 cerrado sin mergear (funcionalidad adaptada e
integrada en el mismo commit).

## Investigación dedicada de ardilla -- ambas hipótesis de Diego refutadas
## con datos, deshidratación confirmada como el driver real (2026-09-07,
## sesión siguiente, ningún cambio de config aplicado)

Diego, tras la calibración de arriba, pidió investigar específicamente
el ~25-33% de fallo residual de ardilla con dos hipótesis propias a
explorar: (1) darle una "facilidad" tipo refugio en árboles al huir de
un depredador, y (2) ampliar su dieta ahora que el catálogo de flora
creció (pieza 4 de "poblar más el mundo", 2026-09-03 -- 10 especies
nuevas). Investigado con el mismo criterio de siempre: medir contra el
motor real ANTES de diseñar o tocar nada, sin dar ninguna hipótesis por
buena solo por sonar razonable.

**Hallazgo de alcance, confirmado antes de tocar código**: `ardilla`
sigue con `dieta: [manzanas, raices]` -- la dieta original de antes del
catálogo ampliado. Auditado también gnomo/conejo/caballo: **ninguna de
las 4 especies herbívoras** tiene en su dieta ninguno de los ~7 recursos
alimento nuevos (`bellotas`, `brotes_helecho`, `nectar_semillas`,
`bayas_espinosas`, `raices_deserticas`, `bayas_montanas`,
`brotes_articos`) -- toda esa flora nueva crece, ocupa espacio y compite
por él, pero es nutricionalmente INERTE para toda la fauna del motor.
Esto no se tocó para gnomo/conejo/caballo en este círculo (decisión de
alcance que le corresponde a Diego, no autorada aquí) -- señalado
explícitamente como pendiente real de mayor calado que solo ardilla.

**Metodología**: mismo arnés sin SQLite que la calibración anterior (ver
sección de arriba), 6 semillas NUEVAS × 4000 ticks por condición, nunca
semilla-a-semilla entre condiciones.

### Lote base (semillas 70001-70006, `master` sin tocar, lobo presente)

**0/6 extinción de ardilla** -- ya mejor que el ~25-33% documentado
antes de este círculo. Desglose real de causas de muerte de ardilla
agregado (491 muertes): **deshidratación 49.7%**, vejez 31.2%,
depredación 18.9%, inanición 0.2% (1 sola muerte). Hallazgo honesto: la
mejora frente a las cifras históricas probablemente no viene de nada
tocado hoy -- es plausible que el radio de búsqueda de agua ampliado
para `Accion.BEBER` (commit `e876e18`, aplicado a TODAS las especies el
mismo día anterior) ya haya mitigado buena parte de la fragilidad de
ardilla como efecto colateral, sin que nadie lo verificara
específicamente para esta especie hasta ahora. No confirmado con más
profundidad (compararía contra el estado previo a `e876e18`, fuera de
alcance de este círculo).

### Hipótesis 2 (más comida) -- REFUTADA con datos, NO aplicada

Lote con `dieta: [manzanas, raices, bellotas]` (semillas NUEVAS
71001-71006, nunca antes vistas): **1/6 extinción** (peor, no mejor, que
el lote base -- dentro del ruido con n=6, no una regresión real) y
desglose de causas prácticamente idéntico (deshidratación 53.9%, vejez
31.1%, depredación 15.0%). Población total agregada de ardilla: 197
individuos en ambos lotes -- **exactamente la misma suma**. Conclusión:
ampliar la dieta de ardilla no tiene ningún efecto medible, porque
inanición nunca fue el cuello de botella real de esta especie (0.2% de
sus muertes) -- coherente con la biología: no tiene sentido dar más
comida a un animal que casi nunca se muere de hambre. **No se aplicó
ningún cambio a `master`** -- decisión basada en evidencia negativa, no
en falta de tiempo.

### Hipótesis 1 (refugio de depredación) -- REFUTADA con datos, SOLO
### DIAGNÓSTICO, ninguna mecánica implementada

Lote con `lobos_iniciales: 0` (semillas NUEVAS 72001-72006, config de
prueba en memoria, nunca tocado `master`): **0/6 extinción** (igual que
el lote base con lobo presente) y población total agregada de ardilla:
205 individuos -- prácticamente idéntica a los 197 del lote base
CON lobo. Desglose de causas sin depredación (obviamente 0%):
deshidratación 65.6%, vejez 34.2% -- **las muertes que antes eran
depredación se desplazan a deshidratación/vejez en proporción similar,
sin cambiar el resultado neto de supervivencia**. Conclusión: quitar a
lobo por completo del mundo no mejora la supervivencia de ardilla de
forma medible -- la depredación de lobo NO es el driver real de su
fragilidad residual, contra la hipótesis original de Diego.

**Ninguna mecánica de refugio en árboles se diseñó ni se implementó**
-- cumpliendo la regla fija de este proyecto (funcionalidad nueva del
motor exige diseño en conversación con Diego antes de cualquier
implementación). Dado que la depredación no resultó ser el problema
real, esa mecánica -- aunque pueda tener valor narrativo propio a
futuro -- no resolvería el fallo residual de ardilla si se construyera
solo con ese objetivo.

### Conclusión real -- el problema de ardilla ES deshidratación,
### mismo hallazgo ya señalado (y no tocado) para conejo el día anterior

Con ambas hipótesis de Diego refutadas por datos, la causa dominante
real del fallo residual de ardilla es **la misma que ya se había
señalado como pendiente para conejo en la sección anterior**:
deshidratación en poblaciones que ya no mueren tanto de hambre. No se
tocó `tasa_perdida_hidratacion_por_tick` (universal, `config/
fisiologia.yaml`) en este círculo -- mismo criterio de prudencia ya
aplicado antes (sin evidencia de que bajarla sea una mejora real y no
solo desplazar el problema a otra causa, y explícitamente fuera del
alcance que se encargó para esta investigación). **Candidato real y
concreto para la siguiente vuelta de calibración, ahora con evidencia
de que afecta a AL MENOS dos especies (conejo y ardilla), no un caso
aislado**.

**Pendiente real, explícito**:
- `tasa_perdida_hidratacion_por_tick` universal, sin tocar -- candidato
  directo de la próxima calibración, con datos de dos especies
  (conejo, ardilla) ya apuntando en la misma dirección.
- Dieta de gnomo/conejo/caballo también desactualizada frente al
  catálogo de flora ampliado (7 recursos alimento nuevos, ninguno en
  ninguna dieta) -- señalado, no tocado, decisión de alcance pendiente
  de Diego.
- Ninguna mecánica de refugio/huida específica para ardilla (o
  cualquier otra especie) diseñada -- si se retoma, debe partir de un
  problema real que la justifique, y depredación no lo es para ardilla
  según esta medición.
- Mismas limitaciones metodológicas que la sección anterior: 6 semillas
  por condición y 4000 ticks son direccionales, no el harness completo
  pendiente desde "Sobrepoblación...".

Sin commits de código en este círculo -- investigación pura con
resultado negativo en ambas hipótesis, documentada con la misma
honestidad que el resto del proyecto.

## Alimentos huérfanos del catálogo ampliado -- reparto por naturaleza
## real de cada especie (2026-09-07, implementado directamente por Claude)

Tras la investigación de ardilla, Diego pidió repartir los 7 recursos
de categoría alimento del catálogo ampliado de flora (2026-09-03) --
`nectar_semillas`, `bayas_espinosas`, `bellotas`, `brotes_helecho`,
`raices_deserticas`, `bayas_montanas`, `brotes_articos` -- que ninguna
de las 4 especies herbívoras tenía en su `dieta`, y preguntó si hacía
falta algún cambio más en ardilla o si el ecosistema ya podía
considerarse estable.

**Reparto, no uniforme, por naturaleza real de cada especie**
(`config/poblacion.yaml`): gnomo gana los 7 (único forrajero sin bioma
fijo, su dieta original ya cruzaba los 5 biomas); conejo gana
`nectar_semillas`+`bayas_espinosas` (herbívoro generalista de pradera);
ardilla gana solo `bellotas` (la pareja obvia; `brotes_helecho` queda
fuera a propósito -- una ardilla real no come helecho); caballo gana
solo `nectar_semillas` (ramoneo blando de pastoreador; se excluye
`bayas_espinosas` -- un caballo real evita el ramoneo espinoso).
Verificado: 300/300 tests, `BOSQUE_AUTO_TICKS=2500` sin excepciones, los
7 recursos confirmados presentes y regenerando en el mundo real
(`celdas_estado`). Commit `e6a351c`.

**Sobre ardilla**: ningún cambio adicional -- ambas hipótesis de Diego ya
se habían refutado con datos, y el último baseline dio 0/6 extinción.

**Sobre "¿son los mundos ya estables?"**: respuesta crítica, no
complaciente -- NO se declaró cerrado. Tres motivos: (1) la ventana de
medición (4000 ticks) es corta frente a los 6000-8000 usados en
investigaciones anteriores, probablemente infla la supervivencia; (2)
el harness de rigor real (15×12000) nunca se ha corrido para nada de
esto; (3) deshidratación domina las muertes de conejo Y ardilla -- dos
especies distintas señalando lo mismo, sin tocar por prudencia (mismo
riesgo de sobrecorrección ya visto una vez con conejo). Diego decidió
no perseguir una confirmación a ventana larga por ahora ("de momento
no") y pasar a diseñar funcionalidad nueva sobre la base actual.

## Menú de funciones nuevas propuesto + arranque del arco "robo/intercambio
## de recursos" (2026-09-07)

A petición de Diego ("plantéame posibles nuevas funciones que amplíen
el motor"), se presentó un menú curado por horizonte (cerca: robo/
agravio genérico, llamada de alarma, liderazgo de manada, unificar
"techo de presa por manada" con la estructura real, decaimiento de
afinidad; medio: consumidor de `resistencia_enfermedad` -- confirmado
sin ningún consumidor real, mismo patrón que valentía/empatía antes de
su primer uso --, ciudad enana, fabricación de herramientas más allá de
armas, trueque; lejos: leyendas/memoria oral vía rumor, facciones entre
asentamientos, fauna subterránea). Diego eligió **robo + intercambio de
recursos (trueque)**.

**Brainstorming (arquitectural)**: clasificado así porque no hay ningún
flujo existente de "mover un recurso de un individuo a otro" que
extender. Decisión de alcance cerrada con Diego: trocear en círculos
pequeños -- (1) provisiones de alimento (ver más abajo, este mismo
día), (2) primitivo genérico de transferencia entre individuos, (3)
robo vía `nucleo/conflicto.py` (ya lo nombra como consumidor futuro
desde el 30-08), (4) trueque vía `Relaciones` -- cada uno su propio
spec, sin empezar los círculos 2-4 todavía.

### Círculo 1 del arco -- Provisiones de alimento, cerrado (spec, PR
### directo por Claude, 2026-09-07)

Diego, verificando el estado real del motor durante el brainstorming:
"ahora los seres conscientes... no almacenan alimentos para comer
después". Confirmado contra el código antes de diseñar: `RECOLECTAR`
solo mete en `Inventario.contenidos` materiales de construcción, nunca
alimento; `COMER` siempre resuelve in situ. Sin nada que un consciente
guarde de verdad, robo/trueque de comida no tendrían nada sobre lo que
operar.

**Corrección real en brainstorming, no de diseño de Claude sin
cuestionar**: la primera propuesta reutilizaba `Inventario.contenidos`
(la misma bolsa que materiales de construcción) para guardar comida.
Diego la rechazó con una pregunta que expuso el problema de raíz: "si
luego quieren construir que hacen? tiran la comida? o al revés si
tienen el inventario lleno de materiales no pueden guardar comida?" --
compartir capacidad entre reserva de supervivencia y carga de trabajo
de construcción crea un conflicto artificial sin resolución natural.
Corregido: `Inventario.provisiones` (nuevo campo) con su propia
capacidad, pequeña (`fraccion_provisiones_maxima=0.05`, PROVISIONAL) y
TOTALMENTE INDEPENDIENTE de `contenidos`/`objetos` -- nunca compiten.
Diego también cuestionó si esto debía ser "inteligencia variable" --
confirmado que no: ley binaria única (mismo umbral de consciencia que
ya usan `RECOLECTAR`/`CONSTRUIR`), sin atarlo a ningún atributo
individual, un instinto de conservación, no una decisión calculada.

Spec: `docs/superpowers/specs/2026-09-07-provisiones-alimento-design.md`.
**Implementado directamente por Claude, no por el pipeline** -- el
centinela seguía detenido desde el incidente de cancelación de
madriguera-fisica-a (ver sección de esa pieza, más arriba) y Diego
pidió implementarlo directamente en vez de reiniciarlo.

- **Entrada** (`sistema_recursos.py:_resolver_comer`): tras comer del
  forraje de la celda, si el consciente ya tiene `saciedad >= 0.9`
  (PROVISIONAL) y queda cantidad del recurso en la celda, guarda hasta
  `tasa_consumo_comer` kg más (reutilizada, sin constante nueva) en
  `Inventario.provisiones`, topado por el espacio disponible.
- **Salida**: si la celda no tiene nada de la dieta propia, come
  primero de `Inventario.provisiones` (mismo `val_nut`/`val_hid` que el
  forraje normal) ANTES de purgar memoria stale -- sin purgar memoria
  ni disparar zoocoria si tiene éxito (comer de la propia despensa no
  es comer donde crece la planta).
- **Caducidad** (`sistema_descomposicion.py:_descomponer_provisiones`,
  cadencia diaria): tasa única universal
  (`tasa_descomposicion_dia_alimento=0.15`, PROVISIONAL) para toda
  comida guardada -- no una por recurso (13 recursos de alimento en el
  catálogo hoy, diferenciar sin datos reales sería adivinar). Purga por
  debajo de `descomposicion.umbral_purga_masa` (reutilizado, mismo
  umbral que ya usan Necromasa/Construccion). `Inventario.contenidos`
  nunca decae.
- Persistencia: `provisiones` añadido al mismo blob JSON ya usado por
  `contenidos`/`objetos` (`componentes_estado.inventario`), sin columna
  nueva; `VERSION_ESQUEMA` sube a `0.35-fase0` de todos modos, mismo
  criterio de higiene ya aplicado a cada pieza anterior.

**Verificado**: 313/313 tests (13 nuevos,
`tests/test_provisiones_alimento.py` -- capacidad independiente de
carga, entrada/salida con sus cuatro condiciones cada una, caducidad,
persistencia). `BOSQUE_AUTO_TICKS=3000` sin excepciones: **124 veces
guardado excedente, 6 veces comido de la despensa** -- el disparador es
deliberadamente estrecho (solo se evalúa al elegir `COMER`), tal como
avisaba el spec; ambos números son reales y bajos pero no cero,
reportado con honestidad, no inflado. Roundtrip de persistencia
confirmado con la partida real de esa corrida (37 madrigueras físicas
recuperadas exactas, continuación de 5 ticks sin excepciones). Solo 2
entidades con provisiones activas al cierre de los 3000 ticks (0.41 kg
total) -- consistente con la caducidad real actuando, no una despensa
que crece sin límite.

**Pendiente real, explícito**: `fraccion_provisiones_maxima`,
`saciedad_minima_para_guardar_provisiones`, y
`tasa_descomposicion_dia_alimento` PROVISIONALES, sin calibrar contra
el harness completo; si la frecuencia de disparo (sobre todo la salida,
6 en 3000 ticks) resulta demasiado baja para que robo/trueque de
comida tengan algo real que operar, candidato a revisar el umbral o
mover la lógica fuera de `COMER`; fauna con caché instintivo de comida
(ardilla en la vida real acumula frutos secos) aplazado, no descartado;
círculos 2-4 del arco (primitivo de transferencia, robo, trueque)
siguen sin diseñar.

### Círculos 2/3/4 -- Robo + compartir por confianza, cierran el arco
### (implementado directamente por Claude, mismo día)

Diego pidió implementar el resto del arco directamente. Antes de tocar
código, una pregunta de diseño real quedaba abierta desde el
brainstorming inicial: **trueque bidireccional real, descartado**.
Presentado a Diego con dos opciones (trueque real vs. "compartir por
confianza" unidireccional) -- eligió la segunda, más simple, sin
necesidad de modelar utilidad marginal por individuo (algo que el motor
no tiene hoy). Spec:
`docs/superpowers/specs/2026-09-07-robo-compartir-confianza-design.md`.

**Círculo 2 -- primitivo genérico**: `nucleo/intercambio.py:
transferir_recurso(origen, destino, recurso, cantidad_max,
espacio_destino_max) -> float`. Función pura, neutra sobre el motivo --
mismo espíritu que `resolver_disputa` no sabe qué se disputa.

**Círculo 3 -- robo**: hallazgo real al diseñar, no anticipado --
`_resolver_conflicto_entre` (el wrapper compartido de refugio ocupado/
conflicto verbal/CRISIS_VIOLENTA) YA devolvía el `ResultadoDisputa` con
un comentario explícito ("por si un disparador futuro lo necesita")
escrito pensando exactamente en esto. Único cambio real al wrapper:
`urgencia_a`/`urgencia_b` opcionales (semántica libre, como ya
documentaba `indice_asertividad_social` desde su diseño original) --
sin pasarlos, comportamiento IDÉNTICO a los tres consumidores
existentes (regresión verificada por test dedicado). Robo pasa la
urgencia real del ladrón (su propia hambre, `1 - saciedad`) en vez del
déficit de seguridad genérico. `_procesar_robo`/`_intentar_robo`
(`sistema_movimiento.py`): un consciente hambriento
(`saciedad < umbral_saciedad_para_robar=0.3`) sin `Inventario.provisiones`
propias, junto a otro que sí tiene, sortea el intento
(`probabilidad_base_robo=0.05 * (1 - saciedad_ladron)`); si se impone
(vía el mismo resolutor -- mismo_grupo/familia cae en `COMPARTE`
automático, no se roba a los propios, sin lógica nueva), se lleva TODO
lo que la víctima tenga del primer recurso no vacío, topado por su
propio espacio de provisiones. Drenaje de seguridad + rencor en el
perdedor ya vienen gratis del wrapper compartido.

**Círculo 4 -- compartir por confianza** (sustituye al trueque):
`_procesar_compartir_confianza`/`_intentar_compartir_confianza`, mismo
molde de recorrido pero SIN pasar por el resolutor -- no es una disputa.
Un consciente con provisiones y afinidad UNIDIRECCIONAL (`Relaciones.
vinculos[receptor].afinidad`, sin exigir reciprocidad -- "confío en ti"
no requiere que tú confíes en mí) por encima de
`umbral_confianza_compartir=0.3` hacia otro con
`saciedad < saciedad_maxima_para_recibir_compartido=0.5` le da lo que
tenga guardado sin nada a cambio (`probabilidad_base_compartir_confianza=0.05`).
No toca `Necesidades.seguridad` ni escribe `Relaciones` -- lectura, no
consecuencia. De paso, corregido un comentario de cabecera desactualizado
en `config/relaciones.yaml` ("nadie LEE Relaciones todavía" -- falso
desde pareja estable, 2026-09-04).

**Verificado**: 330/330 tests (17 nuevos,
`tests/test_robo_compartir_confianza.py` -- primitivo de transferencia,
regresión de urgencia por defecto vs. override, robo con éxito/fracaso/
mismo grupo/sin condiciones, compartir con sus cuatro condiciones,
confirmación de que compartir no toca seguridad/Relaciones).
`BOSQUE_AUTO_TICKS=3000` sin excepciones.

**Hallazgo honesto, no ocultado**: **0 robos y 0 repartos por confianza
reales en esa corrida** -- exactamente el riesgo que el propio spec ya
señalaba antes de implementar ("si la frecuencia de disparo... resulta
demasiado baja... la causa más probable estaría aguas arriba" en el
círculo 1). Con solo 2 entidades sosteniendo `provisiones` en un
momento dado (medido en el círculo 1), la intersección "consciente
hambriento junto a otro con comida guardada" casi nunca se da en esta
ventana. El mecanismo en sí está verificado correcto por los 17 tests
dirigidos -- lo que falta observar en vivo es, otra vez, consecuencia
de aguas arriba (escasez de provisiones circulando), no un defecto de
estos dos círculos. Mismo patrón ya visto varias veces en este proyecto
(asentamiento, pareja, parentesco) antes de que su causa de fondo se
abordara por separado.

**Con esto, el arco completo "robo/intercambio de recursos" queda
cerrado** -- provisiones de alimento, primitivo de transferencia, robo,
y compartir por confianza, las 4 piezas planteadas el mismo día.

**Pendiente real, explícito**: las 5 constantes nuevas
(`umbral_saciedad_para_robar`, `probabilidad_base_robo`,
`umbral_confianza_compartir`, `probabilidad_base_compartir_confianza`,
`saciedad_maxima_para_recibir_compartido`) PROVISIONALES, sin calibrar;
si se quiere observar robo/compartir en juego libre de verdad, el
candidato real es revisar la frecuencia de entrada de provisiones
(círculo 1), no estos dos mecanismos; trueque bidireccional real,
memoria de agravios por robo, y extender el alcance a materiales de
construcción (`Inventario.contenidos`) quedan como extensiones futuras
explícitamente no perseguidas ahora.

## Salón común -- arranque del arco "dinámicas internas de asentamiento"
## (spec, implementado directamente por Claude, 2026-09-08)

Diego pidió abrir un arco nuevo, distinto del de recursos: "empezar a
definir nuevas dinámicas de asentamientos... un salón común donde
socializar al calor de un fuego, un edificio de liderazgo, unas
cocinas". **Decisión explícita de Diego, importante para sesiones
futuras: "ciudad enana" queda FUERA de este arco por completo** -- "es
algo completamente ajeno que pertenece a la raza enana que aún no
existe, no vuelvas a mencionarlo hasta que la planteemos". No confundir
con las cuevas ya construidas en el arco de profundidad geológica (esas
siguen existiendo, solo el concepto de "ciudad enana" como extensión de
Asentamiento dentro de una cueva queda aparcado sin fecha).

Menú presentado (ciudad enana, facciones entre asentamientos, nombre
propio + crónica de asentamiento, herencia al morir un miembro, defensa
colectiva) -- Diego redirigió hacia las dinámicas INTERNAS concretas que
ya tenía en mente en vez de elegir del menú. Orden acordado: salón
común primero, cocinas después, edificio de liderazgo aplazado hasta
tener claro qué "decisión que afecte al pueblo" debería habilitar
mecánicamente (hoy `calcular_liderazgo` es puro cálculo abstracto, sin
ninguna decisión real que un edificio pudiera condicionar).

Spec: `docs/superpowers/specs/2026-09-08-salon-comun-design.md`.
**Hallazgo de diseño clave**: el cimiento ya existente (`Construccion`
genérica, `CONSTRUIR`/`RECOLECTAR`, cupo de espacio por celda,
deterioro -- todos ya funcionan para cualquier `tipo` nuevo sin tocar
código) bastaba por completo; no hizo falta ningún mecanismo nuevo,
solo encadenar el salón común en la prioridad ya existente y darle su
propio efecto real.

- **Efecto núcleo**: `sistema_movimiento.py:_calcular_socializar`
  camina hacia el salón común completado del propio asentamiento en vez
  de perseguir al consciente más cercano al azar -- amplifica gratis
  todo lo que ya se dispara al compartir celda (roce social, rumor,
  compartir por confianza, memoria compartida) sin tocar ninguno de
  esos sistemas. Sin salón, comportamiento idéntico al de antes; el
  contacto real (ya en la misma celda) sigue resolviendo exactamente
  igual, sin mirar el salón en absoluto.
- **"Al calor de un fuego"**: `bono_confort_salon_comun`/
  `bono_seguridad_salon_comun`, mismo patrón aditivo exacto que
  refugio/fogata/madriguera/pareja, sin necesitar una `Fogata` real
  aparte -- el salón ya implica su propio hogar.
- **Generalización real, no invención**: `nucleo/asentamiento.py:
  almacen_cercano` gana un parámetro `tipo` opcional (segundo
  consumidor real, mismo criterio ya usado para
  `agrupar_por_proximidad`/`calcular_centro` con Manada);
  `nucleo/construccion.py:objetivo_construccion_actual` deja de cortar
  en `None` al completar el almacén -- encadena refugio → almacén →
  salón común, terminal solo cuando TODA la cadena está completa;
  `nucleo/fuego.py:hay_refugio_en` se convierte en un alias de una
  línea de la nueva `hay_construccion_de_tipo_en` (comportamiento
  idéntico, cero consumidores rotos).
- Corrección real durante el auto-repaso del spec (spec self-review):
  la primera redacción de la cadena de prioridad tenía una ambigüedad
  real sobre qué pasa si el almacén no existe todavía -- resuelta
  reestructurando el encadenamiento antes de que Diego llegara a
  leerlo.

**Verificado**: 344/344 tests (14 nuevos, `tests/test_salon_comun.py`
-- generalización de `almacen_cercano`/`hay_refugio_en` con regresión
explícita, cadena de prioridad completa, `SOCIALIZAR` prefiriendo el
salón sobre un vecino deliberadamente más cercano, contacto real
ignorando el salón, los dos bonos con su tope, salón a medias sin dar
ningún bono). `BOSQUE_AUTO_TICKS=3000` sin excepciones.

**Hallazgo honesto, no ocultado**: **0 salones comunes completados** en
esa corrida -- el salón es el tercer y último eslabón de la cadena
(tras refugio Y almacén), y con la semilla por defecto ninguna
comunidad llegó tan lejos en 3000 ticks. El mecanismo está verificado
correcto por los 14 tests dirigidos; su disparo real en juego libre no
se observó en esta ventana concreta -- mismo patrón ya visto varias
veces en este proyecto (asentamiento, pareja, parentesco, y ahora
robo/compartir por confianza) antes de que la causa de fondo (tiempo/
recursos que tarda un asentamiento en completar toda la cadena) se
aborde por separado si hace falta.

**Pendiente real, explícito**: `masa_minima_salon_comun`,
`huella_m2_salon_comun`, `bono_confort_salon_comun`,
`bono_seguridad_salon_comun` PROVISIONALES, sin calibrar; cocinas
(comida elaborada, aparcado desde el arco de fuego) es el siguiente
círculo acordado del mismo arco; edificio de liderazgo sigue aplazado
hasta definir qué decisión mecánica real debería habilitar; **ciudad
enana permanece fuera de alcance hasta que la raza enana se plantee --
no mencionar hasta entonces**.

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
