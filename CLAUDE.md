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
   (hoy, terminal + vista web con formas geométricas y glifos emoji, sin arte
   dibujado) es una capa desacoplada y sustituible. No acoples la lógica de
   simulación a cómo se presenta.
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
- Sin tests automatizados todavía (pytest está en requirements.txt pero no
  hay ni un solo archivo de test) ni CI/linting configurados — estado
  conocido, no un descuido a corregir por iniciativa propia.

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
- **Tono**: español, extenso/detallado/explicativo por defecto salvo que se
  pida lo contrario, nunca adulador ni condescendiente, crítico y
  contrastado en vez de solo confirmatorio. Diego es desarrollador
  profesional fullstack — usa terminología técnica sin explicarla de más,
  salvo en documentos explícitamente no técnicos (como el informe de
  visión), donde el registro se mantiene accesible.

## Límites conocidos y pendientes abiertos a fecha de esta migración (24-08-2026)

- **Sobrepoblación sin techo aparente** (informe técnico, sección 20; informe
  de implementación, 7.52): tras corregir el bug de regeneración de flora y
  la purga de memoria agotada, varias semillas de referencia terminan con
  densidades de hasta 0.45 individuos/celda (referencia: 0.05-0.07). No
  investigado todavía — es el límite conocido real más urgente a día de hoy.
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
- **Capa visual con arte real**: explorada por completo el 24-08-2026
  (sprites propios de Diego para gnomo/lobo/conejo/ardilla/manzano/hierba,
  integrados y verificados) y revertida el mismo día por decisión de Diego
  al migrar de Cowork a Claude Code — no por ningún problema técnico. Los
  ficheros (`.ase` originales y `.png` exportados) siguen en disco sin usar.
  Si se retoma, ver informe de implementación 7.53 para el estado exacto en
  que quedó y las preguntas de diseño que quedaron sin cerrar (tamaño de
  lienzo 16×16 vs. la convención 16×24 para bípedos, ausencia de
  diferenciación de forma por sexo en los sprites infantiles, y si las
  variantes 1/2/3 por categoría deben ser un catálogo cerrado o un sorteo de
  tono continuo siguiendo el patrón de atributo racial + sorteo individual).
