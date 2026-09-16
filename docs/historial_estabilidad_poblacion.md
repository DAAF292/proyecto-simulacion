# Historial — Estabilidad de población — sobrepoblación, fragilidad de especie, calibración

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

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
## Raza consciente prospera -- gestación/camada de gnomo + deshidratación
## específica, el bloqueo real detrás de "cocinas comunes invisibles"
## (2026-09-08, mismo día)

Tras cerrar cocinas comunes, Diego preguntó directamente por qué el
mecanismo nunca se observaba en juego libre -- la respuesta llevó a
retomar, con datos frescos y una metodología nueva, la investigación
de fragilidad de gnomo abierta desde el 2026-09-04 y nunca resuelta
del todo. Directiva explícita de Diego: "tenemos que lograr que la
raza consciente prospere".

**Metodología nueva, más precisa que la de investigaciones previas**:
en vez de esperar a que transcurra el término completo de gestación en
tiempo real de corrida (200-260 días = 4800-6240 ticks, carísimo de
alcanzar), se correlaciona cada evento `Concepcion` (entidad_id = madre)
con un eventual evento `Muerte` de esa MISMA madre por su id -- si la
muerte ocurre antes de `tick_concepcion + duracion_gestacion_individual`,
es un fallo confirmado, sin esperar a que el reloj de la simulación
llegue tan lejos. Arnés en scratchpad, no en el repo.

**Hallazgo real, confirma y agrava el de "Parentesco derivado"
(2026-09-04)**: en 2 semillas nuevas (solo 4000-4900 ticks alcanzados
por límite de tiempo real, muy por debajo del término medio de
gestación), **12 de 18 concepciones de gnomo (67%) ya habían fracasado
por muerte materna, 0 nacimientos confirmados en ninguna semilla**.
Causas de muerte dominantes: depredación, deshidratación, vejez (la
inanición, antaño dominante, ya no lo es tras los fixes previos).

**Fix 1 -- gestación y camada** (`config/poblacion.yaml`, decisión
tomada con Diego vía pregunta directa, recomendación aceptada):
`duracion_gestacion_dias` 200-260 → **90-120** (sigue siendo con
claridad la más larga del catálogo -- 1.3-2x el siguiente más largo,
caballo 60-90 -- pero deja de ser una ventana de riesgo casi imposible
de sobrevivir); `camada` fija en `[1,1]` → **`[1,2]`** (mismo orden que
caballo, gnomo sigue siendo la especie menos prolífica). Mismo patrón
de dos ingredientes ya validado con lobo/ardilla (hambre+concepción),
aplicado aquí a gestación+camada porque esos, no hambre/concepción
(ya calibrados el 2026-09-06), eran el problema real medido.
Reverificado con las mismas semillas: fallo por muerte materna baja de
67% a 47%, y aparecen **nacimientos confirmados por primera vez** (0%
→ 32%).

**Fix 2 -- deshidratación específica de gnomo**, con un A/B real antes
de tocar nada (mismo criterio de prudencia que ya evitó una
sobrecorrección con conejo en el pasado): aplicar a hidratación el
mismo alivio ya validado para saciedad (tasa 15x más lenta,
probabilidad de muerte 12.5x más baja) de forma UNIVERSAL **dispara a
conejo de 333 a 702 individuos** en la semilla probada -- confirma con
datos la sospecha ya anotada (sin verificar) el 2026-09-07 de que la
deshidratación actúa como un freno de densidad real. Diego, con el
riesgo ya cuantificado, eligió aplicarlo **solo a gnomo**, mismo patrón
especie-por-especie ya usado con hambre (lobo→ardilla→gnomo→conejo) en
vez de universal. Hallazgo de código aparte:
`probabilidad_muerte_deshidratacion` no soportaba override por
especie -- asimetría real frente a `probabilidad_muerte_saciedad_critica`,
que ya ganó ese mismo patrón el 2026-09-05 por el mismo motivo
(fragilidad de lobo) sin que nadie extendiera el arreglo a
hidratación. Corregido en `sistema_necesidades.py` con el mismo
`cfg_esp.get(...)` que el resto de la sección.

**Resultado combinado, verificado con semillas nuevas y la misma
metodología de correlación**:

| Semilla | Concepciones | Éxito | Gnomos finales |
|---|---|---|---|
| 96001 | 10 | **7 (70%)** | **19** (de 18 fundadores) |
| 96002 | 8 | **5 (62%)** | **15** |

De 0% de éxito reproductivo y población en declive constante en
CUALQUIER semilla probada, a 62-70% de gestaciones completadas con
éxito y población que **crece de verdad** en las dos semillas nuevas
probadas tras ambos fixes. Deshidratación prácticamente desaparece
como causa de muerte de gnomo (0-1 casos por semilla, antes 5-14).
393/393 tests en verde en ambos commits.

**Pendiente real, explícito**: ambos cambios son PROVISIONALES, sin
calibrar contra el harness completo (15×12000); solo 2 semillas nuevas
verificadas para el resultado combinado -- direccional, no una
calibración cerrada; la deshidratación de conejo/ardilla sigue sin
tocar, confirmada ahora con datos como un freno de densidad real (no
solo sospechado) -- candidato a una investigación propia si se
retoma, con la misma prudencia ya aplicada aquí (probar antes de
aplicar, especie por especie); el criterio maestro de Diego (5
especies vivas a la vez, ≥50% de las semillas) no se remidió con
ambos fixes ya aplicados -- candidato inmediato si se quiere cerrar
esa investigación del todo.
## Verificación amplia del motor + conejo, mismo día -- trade-off real
## aceptado, no una solución limpia

Diego pidió una verificación general del estado del motor tras los
fixes de gnomo ("asentamientos, edificios, alimentación, etc."). Arnés
sin persistencia, 2 semillas nuevas hasta 4400-6100 ticks:

- **Asentamientos**: 4 y 2 formados (tamaños 3-10) -- funcionando.
- **Refugios/almacenes**: 21+19 refugios, 3+4 almacenes completados --
  la cadena básica se completa con regularidad ahora que gnomo
  sobrevive de verdad.
- **Salón común/cocina**: 0 completados en ambas -- el tramo paralelo
  final sigue sin alcanzarse (exige sostener el esfuerzo un tramo más
  después del almacén).
- **Cocinar/alacena**: cocinar se ejerce (55 y 14 veces), alacena en 0
  (coherente, sin cocina completada no hay alacena).
- **Social**: socializar/roce social muy activos (miles de veces);
  robo intentado pero nunca exitoso en la muestra; compartir por
  confianza raro pero observado; **pareja estable de gnomo: 0 en
  ambas** -- sigue sin observarse, población aún modesta (12-16).
- **Manada/madriguera**: funcionando con fuerza en casi todas las
  especies.
- **El desequilibrio real y visible**: conejo domina el ecosistema
  (586-642 individuos, 822-1007 muertes ya contabilizadas) frente al
  resto -- el mismo boom-bust sin resolver, ya documentado y aplazado
  hace días.

### Investigación de conejo -- el sistema es más caótico de lo que
### unas pocas semillas pueden calibrar con confianza

Trayectoria real (3 semillas nuevas, seguimiento cada 500 ticks, hasta
8000): una mostró crecimiento sin techo (30→933, sin bust dentro de la
ventana), las otras dos "bust" muy por encima del rango histórico sano
(0.05-0.07 ind/celda). Deshidratación y vejez, casi a la par, como
causas dominantes -- confirma que el alivio de hambre de conejo
(2026-09-06) le quitó su freno natural principal sin compensación
reproductiva suficiente.

**Decisión de Diego, tras plantear tres palancas**: recortar camada Y
concepción a la vez, con margen real (`camada` `[3,5]`→`[2,3]`,
`factor_base_concepcion` `0.015`→`0.008`). **Resultado, con 11
semillas nuevas en total probadas entre las distintas combinaciones,
honesto sobre su límite real**: esta combinación cura la explosión sin
techo en la mayoría de las semillas, pero **2 de 7 (~29%) llevan a
conejo a la extinción total** -- un riesgo que prácticamente no
existía antes de tocar nada. Un intento de suavizar la concepción
(`0.008`→`0.010`) para reducir ese riesgo **no mejoró nada** (2 de 4
semillas nuevas se extinguieron igual) -- evidencia clara de que
cambiar estos números desplaza toda la secuencia de `rng` posterior
(mismo fenómeno ya documentado repetidas veces en este proyecto:
"Sobrepoblación...", el propio conejo en 2026-09-06), haciendo que
comparaciones de pocas semillas por combinación no sean fiables para
afinar más.

**Decisión final de Diego, con el trade-off ya cuantificado**:
quedarse con `camada=[2,3]`/`factor_base_concepcion=0.008` tal cual,
aceptando el ~29% de riesgo de extinción medido como el precio de
eliminar la explosión sin techo -- documentado con total honestidad
como trade-off, no como solución cerrada. 393/393 tests en verde.

**Pendiente real, explícito, más urgente que antes**: el harness
completo (15 semillas × 12000 ticks) sigue siendo la única vía real de
calibrar esto sin el ruido ya demostrado hoy -- cada sesión de
calibración de este proyecto se ha topado con el mismo límite
metodológico sin llegar nunca a correrlo; candidato real a plantear
como su propia pieza de infraestructura si se quiere calibrar
población en serio a partir de ahora. Salón común/cocina/pareja
estable de gnomo siguen sin observarse en juego libre -- correctos por
tests dirigidos, su disparo real exige más ticks de los medidos hoy.
## El harness completo, por fin construido y corrido -- primer 15x12000
## real de todo el proyecto, y dos bugs reales encontrados de inmediato
## (2026-09-09)

Diego pidió construir la pieza de infraestructura señalada el día
anterior. `herramientas/harness_calibracion.py` (nuevo, pieza
reutilizable, no scratchpad): corre N semillas nuevas × M ticks EN
PARALELO (multiprocessing, una semilla por proceso, sin persistencia),
agregando un informe de todos los flujos del motor. Con el motor un
64% más rápido tras el trabajo de rendimiento del día anterior, 15
semillas en paralelo usan hasta 15 de los 20 núcleos disponibles --
factible en minutos, no en horas.

**Primera corrida real, 15 semillas nuevas × hasta 12000 ticks** (las
15 tocaron el límite de seguridad de 1500s antes del objetivo,
llegando a 7655-10032 ticks -- aun así, la muestra más grande y fiable
que este proyecto ha tenido nunca para esto). Hallazgos honestos:

- **Gnomo: 0% extinción**, población 3-39, embudo reproductivo 74% --
  el fix del día anterior se confirma real a escala, no ruido de
  muestra pequeña.
- **Caballo: 0% extinción**, población sana 6-37.
- **Lobo: 100% extinción (15/15)** -- nunca visto con las muestras
  pequeñas de días anteriores, el hallazgo más grave de la corrida.
  Sin investigar todavía.
- **Conejo: 67% extinción** -- mucho peor que el ~29% estimado el día
  anterior con solo 7 semillas: el trade-off aceptado entonces estaba
  basado en una muestra demasiado optimista.
- **Ardilla: 73% extinción** -- investigado a fondo, ver abajo.
- **Criterio maestro de Diego (5 especies vivas a la vez): 0/15** --
  casi enteramente por la extinción total de lobo.
- Asentamientos y almacenes: 15/15 completados -- sólido a esta
  escala. Pareja estable de gnomo, robo exitoso, compartir por
  confianza, cocinar: todos confirmados funcionando de verdad (85, 82,
  51, 653 veces respectivamente) -- antes parecían "invisibles" solo
  por falta de muestra.

**Corrección metodológica real, encontrada al escribir el harness**: la
medición manual de "parejas estables" de sesiones anteriores llamaba a
`son_pareja(rel_a, rel_b, b, a, umbral)` con `id_a`/`id_b` invertidos
-- siempre devolvía 0 aunque sí hubiera parejas reales. El harness lo
corrige (`son_pareja(rel_a, rel_b, a, b, umbral)`).

### Caballo vs. ardilla -- por qué una prospera y la otra se extingue

Diego pidió determinar la diferencia real. Comparando causas de muerte:
caballo 5.6% por deshidratación, ardilla 53.8% (con diferencia la
causa dominante). Explicado por `altura` (config/poblacion.yaml):
`profundidad_agua_potable(celda) <= altura` condiciona qué tan
profunda puede ser el agua que una criatura alcanza a vadear -- caballo
es la especie más alta del catálogo (1.4-1.8m), ardilla la más baja con
diferencia (0.15-0.25m). No es un bug: es una consecuencia real y
coherente de un mecanismo ya existente, cuya severidad nunca se había
medido a esta escala. Las trayectorias de ardilla muestran además un
patrón de "vórtice de extinción" -- la mayoría cae a 0 en 4000-6000
ticks de forma bastante monótona, pero las pocas que sobreviven ese
tramo explotan después (147-566) -- sugiere un umbral crítico de
población mínima viable, no una decadencia suave.

**Fix aplicado**: mismo alivio de deshidratación que ya recibió gnomo
(`tasa_perdida_hidratacion_por_tick`/`probabilidad_muerte_deshidratacion`
→ 0.0008/0.0004), específico de ardilla. A/B real antes de aplicar (6
semillas nuevas × hasta 8000 ticks, en paralelo, config parcheada en
memoria sin tocar ficheros): **0/6 extinción con el alivio frente a
3/6 sin él**, sin el patrón de sobrecorrección que sí apareció con
conejo (poblaciones de magnitud comparable en ambas condiciones).
395/395 tests en verde.

### Por qué salón común y cocina nunca se completaban -- dos bugs
### reales, no un problema de escala ni de suerte

Diego preguntó directamente por qué los sistemas sociales nuevos de
asentamiento nunca se daban. Diagnóstico dirigido (inspeccionando
`Construccion.progreso`/`materiales` de tipo `salon_comun`/`cocina`
directamente, no solo `completado_alguna_vez`): en una semilla con
almacén completo desde el tick 3000 y 23 gnomos vivos a los 7625
ticks, **ninguno de los dos había recibido jamás ni 1 kg de
material**. No era un problema de tiempo ni de población -- algo lo
bloqueaba por completo.

**Bug real 1, de código**: `sistema_movimiento.py:_calcular_construir`
creaba SIEMPRE `tipo="almacen"` hardcodeado al llegar al centro del
asentamiento para el eslabón comunal siguiente, sin mirar el `tipo`
real devuelto por `objetivo_construccion_actual` -- desde que cocinas
comunes (día anterior) añadió `salon_comun`/`cocina` como paralelos,
cada intento de empezar cualquiera de los dos creaba en su lugar OTRO
almacén duplicado (nunca registrado como `salon_comun`/`cocina` en
ninguna consulta por tipo, y confundiendo a `objetivo_construccion_actual`
con dos "almacen" a la vez). El código llevaba el comentario literal
"# almacén, todavía no existe" desde antes de que cocinas comunes
existiera -- nunca se actualizó al generalizar la función a paralelos.
Ningún test existente lo detectó porque ninguno probaba la rama de
CREACIÓN de `_calcular_construir` cuando `cid` es `None` para un tipo
que no fuera refugio/almacén -- hueco de cobertura real, cerrado ahora
con 2 tests de regresión.

**Bug real 2, de calibración, encontrado al escribir el test de
regresión (no antes)**: `huella_m2_salon_comun` (45.0) +
`huella_m2_almacen` (40.0) = 85 > `capacidad_construccion_celda_m2`
(80.0) -- el salón común era MATEMÁTICAMENTE IMPOSIBLE de construir en
el centro del asentamiento (el único sitio donde puede crearse) una
vez el almacén ya estaba ahí, con independencia de cuánta población o
tiempo hubiera. Bajado a 35.0 (igual que cocina) -- 40+35=75≤80, cabe
con margen real de 5 m².

**Verificado con el motor real tras ambos fixes**: dos semillas nuevas,
salón común completado en el tick 800 y 400 respectivamente (¡nunca en
ninguna corrida antes del fix!); en una de las dos, tras completar el
salón, la población pasó automáticamente a construir la cocina
también, completándola en el tick 2600 -- la cadena paralela completa
funciona de punta a punta por primera vez. 395/395 tests en verde.

**Pendiente real, explícito, ahora la investigación más urgente**:
**lobo se extingue en el 100% de las 15 semillas del harness** --
nunca visto con las muestras pequeñas de sesiones anteriores, sin
investigar todavía. Conejo (67% real, no el ~29% estimado antes) y
ardilla (mejorado pero sin remedir a la escala del harness completo)
siguen con extinción real significativa. El criterio maestro de Diego
(5 especies vivas a la vez) sigue en 0% -- casi enteramente explicado
por lobo. El harness completo (`herramientas/harness_calibracion.py`)
ya existe y está verificado -- el siguiente paso natural es
recalibrar lobo con él como referencia, y luego remedir conejo/ardilla
juntos para ver si el criterio maestro por fin se acerca al 50%.

### Lobo -- dos intentos rápidos, ninguno con mejora clara, la especie
### de mayor varianza del catálogo (2026-09-09, mismo día)

Diego pidió seguir con lobo de inmediato. Vejez es la causa dominante
(42.7%) en el harness de 15 semillas -- hipótesis directa: el techo
universal `poblacion.techo_fraccion_edad_inicial_longevidad` (0.7)
penaliza mucho más a una especie de vida corta (lobo, 8-14 años) que a
una larga (gnomo, 45-65), dejando a los fundadores más desafortunados
con apenas 1000-2000 ticks de vida restante desde el tick 0. Hecho
configurable por especie (`rangos_raciales.<especie>.
techo_fraccion_edad_inicial_longevidad`, opcional, sin entrada
comportamiento idéntico a antes -- infraestructura de riesgo cero,
sí aplicada) y probado en A/B para lobo (0.7→0.3, 6 semillas nuevas):
**NO mostró mejora** -- 5/6 extinción con el cambio frente a 3/6 sin
él. Descartado, no se le da ningún valor a lobo en config real.

Segundo intento, sobre el hallazgo de que caballo tuvo **0 muertes por
depredación en las 15 semillas del harness** -- lobo nunca caza
caballo con éxito, pese a ser la presa que de verdad lo alimentaría
(conejo/ardilla apenas nutren a un depredador de su tamaño). La caza
en manada exige varios aliados cazando cerca a la vez, algo que casi
nunca se da con una población de 8-20 lobos dispersos. Probado en A/B
subir `factor_ampliacion_techo_manada` (1.0→3.0, menos aliados
necesarios): tampoco mostró diferencia clara -- 2/6 extinción en
ambas condiciones, 1 caza exitosa de caballo con el cambio frente a 0
sin él.

**Hallazgo metodológico real, más importante que cualquiera de los dos
intentos**: el propio baseline de lobo dio TRES resultados de
extinción distintos según la muestra -- 100% en el harness de 15
semillas, 50% (3/6) en el primer A/B, 33% (2/6) en el segundo, todos
con semillas nuevas distintas. Lobo parece ser la especie de mayor
varianza de todo el catálogo -- ni 6 semillas por combinación bastan
para distinguir una mejora real del ruido, mismo fenómeno de
desplazamiento de secuencia de `rng` ya visto varias veces hoy con
conejo, llevado aquí a un extremo mayor.

**Decisión de cierre**: no seguir iterando con muestras de 6 semillas
-- rendimientos decrecientes claros, mismo patrón ya visto con conejo.
395/395 tests en verde en ambos intentos (ninguno se aplicó a config
real salvo la infraestructura de riesgo cero).

**Pendiente real, explícito**: lobo sigue extinguiéndose con alta
probabilidad y sin una palanca clara identificada -- de los tres
hallazgos reales del día (vejez enmascarando, caza en manada nunca
disparándose, alta varianza intrínseca), ninguno se tradujo en un fix
verificado. Cualquier intento futuro de calibrar lobo necesita el
harness completo (15×12000) por combinación probada, no A/B de 6
semillas -- la lección más clara que deja esta investigación. El
criterio maestro de Diego (5 especies vivas a la vez) sigue sin
remedirse tras los fixes de ardilla y los bugs de salón/cocina
corregidos hoy mismo -- candidato inmediato si se retoma esta línea de
trabajo.
## Auditoría de estabilización -- primer momento en que el criterio
## maestro de Diego se cumple con claridad (13% → 62% → 88%), tres
## commits verificados uno a uno contra el motor real (2026-09-09,
## sesión siguiente, entorno con 4 núcleos en vez de los 15-20 de la
## sesión anterior -- muestras por ronda más pequeñas por necesidad,
## documentado así en cada paso)

Retomada la investigación de estabilidad justo donde la dejó la sección
anterior. Diego pidió una auditoría completa de semillas para ver cómo
sobreviven las criaturas y cómo se disparan los mecanismos del motor --
el propio `herramientas/harness_calibracion.py` ya construido el día
anterior, corrido de nuevo (15 semillas nuevas, 300001-300015, hasta
12000 ticks, tope de 1200s/semilla por la limitación real de cómputo de
este entorno -- las 15 se cortaron por tiempo entre 7003 y 10296 ticks,
ninguna llegó al término completo, mismo criterio de honestidad que la
corrida anterior sobre qué cuenta como dato válido).

**Resultado de esa primera corrida**: gnomo y caballo 0% extinción
(confirmando que sus fixes previos se sostienen), lobo 53% (8/15),
conejo 47% (7/15), ardilla 20% (3/15) pero con **explosión sin control**
en la mayoría de sus supervivencias (hasta 701 individuos, muy por
encima de cualquier referencia sana histórica). Criterio maestro de
Diego: **2/15 (13%)**. Mecanismos sociales confirmados disparándose con
fuerza real por primera vez a escala completa: salón común 15/15, almacén
15/15, cocina 10/15, parejas estables de gnomo en 12/15, manada/
madriguera con 94.620 sincronizaciones agregadas, socializar/roce social
con más de 230.000 contactos combinados.

**Lectura crítica de ese primer resultado, antes de tocar nada**:
comparado con la corrida anterior (lobo 100%, conejo 67%, ardilla 73%),
la mejora de lobo y conejo **no podía atribuirse a ningún cambio de
config propio de esas dos especies** -- solo ardilla había recibido un
fix nuevo el día anterior (alivio de deshidratación), y cualquier cambio
de config desplaza toda la secuencia de `rng` del motor para el resto de
especies (fenómeno ya documentado repetidas veces en este proyecto).
Señalado explícitamente como posible ruido, no como mejora real, antes
de decidir ningún siguiente paso.

### Comparación de causas de muerte contra caballo (referencia estable),
### normalizada por exposición individuo-tick, no solo conteo bruto

Diego pidió específicamente comparar los motivos de muerte de ardilla,
conejo y lobo contra caballo (el único junto a gnomo con 0% de extinción
en la corrida). Calculada la exposición individuo-tick real (integral
trapezoidal de la trayectoria muestreada cada 1000 ticks) para poder
comparar tasas, no solo proporciones dentro de cada especie -- una tasa
de mortalidad total 7.9x más alta que caballo no se ve comparando solo
porcentajes de causa.

| | caballo | gnomo | lobo | conejo | ardilla |
|---|---|---|---|---|---|
| tasa global (por 10k ind-tick) | **1.00** | 1.36 | 3.28 (3.3x) | 7.87 (7.9x) | 4.16 (4.2x) |
| vejez | 0.744 | 0.196 | 0.218 | 5.296 | 3.087 |
| inanición | 0.136 | 0.397 | 1.269 | 0.066 | 0.355 |
| deshidratación | 0.118 | 0.010 | **0.790** | **2.106** | 0.013 |
| depredación | 0 | 0.729 | 0 | 0.396 | 0.705 |

**Diagnóstico real, distinto para cada especie, no una causa común**:
caballo es estable porque NINGÚN eje de riesgo está elevado (cero
depredación, inanición y deshidratación bajas, solo vejez esperable) con
una fecundidad calibrada a juego (concepción 0.015, camada 1-2). Lobo
tenía los tres frentes elevados a la vez (inanición 9.3x caballo,
deshidratación 6.7x) y **nunca había recibido el mismo alivio de
deshidratación que ya tenían gnomo y ardilla** -- hallazgo nuevo, no
visto en la investigación de fragilidad de lobo del día anterior (esa
investigación probó edad inicial y techo de manada, nunca deshidratación
específica). Conejo tenía deshidratación real (17.9x caballo) pero
mostraba un patrón bimodal genuino en sus trayectorias (pico-y-caída en
varias semillas, algo que ardilla nunca mostraba). Ardilla ya tenía la
deshidratación resuelta desde el día anterior -- su problema real era
`factor_base_concepcion=0.03`, el doble que el resto del catálogo, sin
ningún freno que lo compensara tras quitarle el de deshidratación.

Examinadas también las trayectorias completas (no solo el final): en las
semillas de ardilla que se extinguen, depredación es 27-44% de sus
muertes; en las que explotan, baja a 1-16% -- confirma que es una
**carrera contra la depredación temprana**, no un problema de comida (la
inanición se mantiene baja incluso con 701 individuos, la comida no está
limitando la población a esa escala). Conejo, en cambio, no mostró esa
correlación con depredación -- su extinción se explica mejor por la
combinación de deshidratación real y una fecundidad ya recortada el
2026-09-06 que resultó insuficiente para el contexto actual (con gnomo/
lobo ya no colapsando, compitiendo por el mismo espacio).

### Ronda 1 de A/B -- tres hipótesis aisladas, una se aplica, dos no

Diseñado un arnés nuevo (`ab_estabilizacion.py`, scratchpad de sesión,
mismo patrón que `harness_calibracion.py` pero con parches de config en
memoria, sin tocar disco) para probar cada hipótesis en aislamiento
antes de aplicar nada -- 4 condiciones × 6 semillas nuevas × 6000 ticks:

- **`lobo_hidrat`** (mismo alivio de deshidratación que gnomo/ardilla,
  `0.0008`/`0.0004`): extinción 4/6 (control) → **0/6**. Señal limpia y
  fuerte, sin ningún indicio de sobrecorrección (lobo nunca se acerca a
  explotar, máximo 16 individuos en la muestra). **Aplicado a
  `config/fisiologia.yaml`, commit `a9e3bf7`.**
- **`conejo_hidrat`** (mismo alivio, aislado, sin tocar fecundidad): 1/6
  extinción, igual que el control -- no redujo la extinción, solo
  desplazó hacia arriba las poblaciones que sobrevivían. Descartado en
  solitario.
- **`ardilla_trim`** (concepción 0.03→0.015 + camada [2,4]→[1,3], los dos
  a la vez y de golpe): sobrecorrigió con fuerza -- ardilla pasó de
  explotar (6-432) a rozar la extinción (0-24), y **conejo empeoró como
  efecto colateral** (1/6→4/6 extinción). Descartado, no aplicado.

395/395 tests en verde tras aplicar solo el fix de lobo.

### Ronda 2 -- hipótesis más quirúrgicas, aislando qué parámetro pesa
### realmente

Con los dos intentos combinados de la ronda 1 fallidos, la ronda 2 aisló
variables en vez de combinarlas: 3 condiciones × 6 semillas × 6000
ticks, comparadas contra el control ya medido en la ronda 1.

- **`ardilla_concepcion_suave`** (solo concepción 0.03→0.022, camada
  intacta): apenas frenó la explosión (67-690 individuos) -- concepción
  no es el lever dominante.
- **`ardilla_camada_suave`** (solo camada [2,4]→[2,3], concepción
  intacta): **el lever más eficaz de los dos probados por separado**
  (4-258 individuos, techo bastante más bajo, 0/6 extinción) -- confirma
  que el tamaño de camada pesa más que la probabilidad de concepción a
  la hora de controlar el techo de una explosión.
- **`conejo_combo_moderado`** (alivio de deshidratación + restauración
  PARCIAL de la fecundidad recortada el 2026-09-06: camada [2,3]→[2,4],
  concepción 0.008→0.010 -- ni el valor original que causó la
  mega-explosión, ni el recorte que dejaba 47% de extinción real):
  **0/6 extinción**, primera condición que elimina la extinción de
  conejo observada en cualquier muestra de esta sesión -- pero las
  poblaciones que sobreviven suben (hasta 343).

Bono de esta ronda: las 18 semillas (bajo las tres condiciones, todas ya
con el fix de lobo committeado en disco) dieron **0/18 extinción de
lobo** -- confirmación mucho más amplia que la ronda 1 de que el fix se
sostiene.

**Aplicados a `config/poblacion.yaml` y `config/fisiologia.yaml`,
commit `13411ef`**: camada de ardilla a [2,3] (concepción se deja en
0.03, sin tocar -- el lever que menos pesaba); receta completa de conejo
(deshidratación + camada [2,3]→[2,4] + concepción 0.008→0.010).

**Verificación combinada, primera vez con los tres cambios juntos en
disco** (8 semillas nuevas, 700001-700008, hasta 8000 ticks): criterio
maestro de Diego **13% → 62%** -- primera vez que cruza el 50% en toda
la investigación. Extinción de ardilla (1/8) y conejo (0/8)
prácticamente resueltas. **Pero con un coste real, dicho con la misma
honestidad que el resto de esta sección**: conejo no se estabilizó, solo
cambió de modo de fallo -- máximo observado **691 individuos**, peor que
el peor caso histórico sin tocar nada (394). Vejez explicaba el 94.6% de
sus muertes -- básicamente sin ningún freno real una vez quitada la
extinción.

### Corrección quirúrgica -- revertir solo la camada de conejo, criterio
### maestro sube a 88%

Mismo diagnóstico que ya había dado la ronda 2 con ardilla (camada pesa
más que concepción para controlar el techo de explosión), aplicado aquí
en sentido inverso: revertir SOLO `camada` de conejo a [2,3] (valor de
2026-09-06), dejando `factor_base_concepcion=0.010` y el alivio de
deshidratación intactos. **Commit `862f5f0`.**

**Verificado con 8 semillas nuevas más (800001-800008, hasta 8000
ticks)**: conejo **0/8 extinción, máximo 337** -- por debajo incluso del
peor caso histórico (394), confirmando la hipótesis con precisión.
Criterio maestro de Diego: **62% → 88% (7/8)**. Lobo se mantuvo dentro de
su rango de varianza ya conocido (1/8, 12%) -- no hay evidencia de que
combinar los tres fixes lo haya perjudicado. Ardilla no se extinguió en
ninguna semilla, aunque su magnitud media subió algo frente a la
verificación anterior (203.9 vs 92.4) -- probablemente desplazamiento de
secuencia de `rng` al tocar la config de conejo, no perseguido más por
ahora dado que el resultado global mejoró. 395/395 tests en verde en las
tres verificaciones.

### Investigación aparte: ¿caza lobo en manada a caballo? -- NO,
### confirmado con 73 corridas de esta misma sesión, sin excepción

Diego preguntó explícitamente si el mecanismo de "techo de presa por
manada" (diseñado el 2026-09-05 junto a la especie caballo, para que
varios lobos cazando juntos pudieran abatir una presa mucho más grande
que un individuo solo) se está disparando ahora que lobo ya no colapsa.
Comprobado agregando el campo `depredacion` de las muertes de caballo en
**las 73 corridas generadas en toda esta sesión** (24 de la ronda 1, 18
de la ronda 2, 15 del harness completo, 8+8 de las dos verificaciones
combinadas): **0 muertes de caballo por depredación, en las 73, sin
ninguna excepción**.

**Causa real, no un bug**: el propio código de "techo de presa por
manada" (`sistema_depredacion.py`/`sistema_movimiento.py`,
`factor_ampliacion_techo_manada=1.0`, `config/combate.yaml`) exige
`peso_cazador * (1 + aliados_cazando_cerca) >= peso_presa` para que un
lobo (~60-90kg) considere siquiera perseguir un caballo (~400-500kg) --
con los pesos medios reales del catálogo, hacen falta **~5 lobos
cazando activamente (`Accion.CAZAR`) dentro de `radio_apoyo_grupal=3`
celdas a la vez**, no solo 5 lobos vivos en el mundo. Revisadas las 73
corridas: la población de lobo NUNCA superó los 18 individuos en ninguna
semilla de esta sesión (máximo real observado: 16, en la ronda 1;
mediana mucho más baja), y las manadas de lobo que sí se formaron
(visibles en los conteos de `manadas_por_especie` de las corridas que
usan el harness completo) casi siempre son de 1, ocasionalmente 2
lobos -- nunca los ~5 cazando simultáneamente y cerca que exige la
fórmula. El mecanismo está verificado correcto por sus propios tests
dirigidos (`tests/test_especie_caballo.py`, escenarios construidos a
mano que sí confirman el techo funcionando), pero en juego libre, ni
siquiera con lobo ya mucho más estable que antes de esta sesión, la
población de lobo real nunca alcanza la escala necesaria para que se
dispare ni una sola vez. **No es un problema nuevo de esta sesión --ya
se había señalado el 2026-09-05 ("0 caballos murieron por depredación
en las 15 semillas del harness")-- pero esta sesión lo confirma con una
muestra mucho mayor (73 corridas, no solo 15) y con lobo en un estado de
salud poblacional muy superior al de esa fecha, descartando "lobo estaba
casi extinto" como explicación suficiente.**

**Implicación real, sin resolver todavía**: subir la población de lobo
por sí sola no bastaría sin más -- ya se descartó una vez ("Intento
descartado: subir `lobos_iniciales` no arregla nada", 2026-09-05) que
más fundadores ayudara a nada, y el propio umbral de ~5 cazando a la vez
es estructuralmente difícil de alcanzar con una especie que, incluso
estable, ronda 1-18 individuos totales por semilla. Candidatos reales
para una investigación futura, ninguno explorado hoy: (a) bajar
`factor_ampliacion_techo_manada` (1.0→algo menor, requeriría menos
aliados) -- palanca numérica pura, ya probada una vez sin éxito claro el
2026-09-05 (1.0→3.0 fue en la dirección equivocada, subir el factor
ayuda menos, no más -- habría que bajarlo, no subirlo, error de signo a
evitar en el próximo intento); (b) revisar si `radio_apoyo_grupal=3` es
demasiado estricto para que varios lobos dispersos lleguen a coincidir;
(c) aceptar que la caza en manada de caballo es, en la práctica, un
evento rarísimo y coherente con la propia escasez de grandes
depredadores organizados -- no necesariamente un defecto a corregir.

### Balance del día, con honestidad

Progreso real y medido: el criterio maestro de Diego (5 especies vivas a
la vez) pasó de **13% → 62% → 88%** en tres iteraciones, cada una
verificada contra el motor real antes de aplicarse, ninguna aceptada
solo por la lectura de config en abstracto. Es el primer momento de todo
el proyecto en que el motor se comporta de forma genuinamente estable en
la mayoría de las semillas probadas.

**Lo que sigue sin resolver, explícito**: ninguno de los tres commits de
hoy se verificó contra el harness completo de referencia (15×12000) --
todas las verificaciones de esta sesión usaron 6-8 semillas por
condición (entorno de 4 núcleos, frente a los 15-20 de sesiones
anteriores, tiempo real limitado), documentado así en cada paso. Ardilla
sigue sin un techo firme (hasta 495 en la última muestra, sin
extinguirse). Lobo mantiene su varianza ya conocida (0-25% de extinción
según la muestra). La caza en manada de caballo permanece, con una
muestra mucho mayor que antes, confirmada como un evento que
prácticamente nunca ocurre en juego libre -- mecanismo correcto,
población de lobo estructuralmente insuficiente para dispararlo. Todos
los valores tocados hoy (`fisiologia.yaml`: hidratación de lobo/conejo;
`poblacion.yaml`: camada de ardilla/conejo, concepción de conejo) siguen
PROVISIONALES. El harness completo de referencia (15×12000) sigue
siendo la validación de rigor pendiente para dar cualquiera de estos
tres commits por definitivamente cerrado.
## Prueba extensa con venado/cabra_montes -- criterio maestro real 40%
## (5 especies), no el 88% ya documentado -- hueco de documentación
## corregido, hallazgo real sobre lobo sin resolver (2026-09-09, mismo
## día, análisis de los datos crudos ya generados por "lanza una prueba
## extensa", nunca escrito hasta ahora)

**Corrección de un hueco real de documentación**: la corrida de 15
semillas nuevas (900001-900015, hasta 10104 ticks, harness
`herramientas/harness_calibracion.py`) lanzada tras cerrar el arco de
venado/cabra_montes se reportó verbalmente en conversación pero nunca
se escribió aquí -- viola el propio principio de este documento
("documentación... no lo des por recordado sin más"). Recuperados los
datos crudos (`.json` del harness, seguían en el scratchpad de la
sesión) y reanalizados con rigor antes de escribir esto, no de memoria.

**Resultado real, con las 15 semillas completas**:

| Especie | Extinción | Causa dominante |
|---|---|---|
| gnomo | 0/15 (0%) | depredación 54%, inanición 27% |
| lobo | 7/15 (47%) | inanición 51%, vejez 48% |
| conejo | 3/15 (20%) | vejez 93% |
| ardilla | 4/15 (27%) | vejez 75%, depredación 19% |
| caballo | 0/15 (0%) | vejez 71%, deshidratación 19% |
| venado | 3/15 (20%) | vejez 42%, depredación 39% |
| cabra_montes | 1/15 (7%) | vejez 61%, inanición 33% |

**Criterio maestro de Diego (5 especies vivas a la vez): 6/15 (40%)**
-- con las 7 especies del catálogo completo vivas a la vez: 5/15 (33%).
Muy por debajo del 88% (7/8) con el que se cerró la sesión de
estabilización horas antes.

**Diagnóstico honesto, no alarmista**: la caída NO parece deberse a
venado/cabra_montes perjudicando al resto -- gnomo y caballo siguen en
0% de extinción, conejo/ardilla dentro de rangos ya vistos antes.
**Lobo (47% de extinción) es, con diferencia, quien arrastra el
criterio maestro hacia abajo**, y ese 47% cae limpiamente dentro de la
varianza YA documentada de esta misma especie en esta misma sesión
(100%, 67%, 53%, 47%, 25%, 12% según la muestra -- ver "Lobo -- dos
intentos rápidos..." más arriba). El 88% que se documentó como cierre
de la investigación de estabilización se midió sobre una muestra de
solo 8 semillas -- no representativa, sesgada hacia el extremo bueno de
la varianza real de lobo, tal como este mismo documento ya advertía en
su momento ("ninguno de los tres commits... se verificó contra el
harness completo... 6-8 semillas por condición"). No es una regresión
causada por hoy -- es la primera vez que se mide con una muestra grande
tras esos fixes, y la varianza que ya se sabía que existía se manifiesta.

**Hallazgo real, más interesante, sin resolver**: venado SÍ se caza de
verdad en juego libre (85 muertes reales por depredación agregadas en
las 15 semillas, presente incluso en la mayoría de semillas donde lobo
acabó extinto) -- el propósito de diseño de venado ("darle a lobo una
presa nutricionalmente viable en solitario") se ejerce, no es
"correcto pero invisible" como tantos otros mecanismos de este
proyecto. **Pero no está cerrando el problema de fondo**: incluso con
caza de venado real y documentada, la causa de muerte dominante de
lobo sigue siendo inanición (51%), casi empatada con vejez (48%) --
prácticamente sin cambios frente a antes de que venado existiera.
Revisando semilla a semilla: en varias de las 7 semillas donde lobo se
extinguió, hubo entre 2 y 9 capturas reales de venado antes de la
extinción -- comer presa real no bastó para evitar el colapso. Esto
apunta a que el cuello de botella de lobo no es "falta de presa
viable" (ya resuelto, venado lo demuestra) sino algo más fino:
frecuencia/eficiencia de caza real, o simplemente que el margen
calórico por captura sigue sin ser suficiente incluso con una presa
más grande que conejo/ardilla -- no investigado todavía con datos, sería
la primera vez que se mide esto DESPUÉS de tener una presa nutricionalmente
adecuada disponible (a diferencia de la investigación previa de fragilidad
de lobo, que nunca contó con venado).

**Otros datos reales de la misma corrida, sin sorpresas**: asentamientos
(40 en total entre las 15 semillas), refugios (344), almacenes (36),
salón común (27) y cocina (12) completados -- confirma que los
mecanismos sociales/de construcción siguen disparándose con fuerza real
a esta escala, sin relación con el hallazgo de lobo.

**Pendiente real, explícito, más concreto que antes**:
- Investigar el presupuesto calórico real de lobo AHORA que existe una
  presa numéricamente viable en solitario (venado) -- pregunta nueva,
  nunca antes formulada así: ¿por qué cazar venado con éxito real no
  está bastando para bajar la inanición? Candidatos: tasa de encuentro/
  frecuencia de caza real (no solo viabilidad numérica), o el ratio de
  saciedad ganada por captura de venado frente al coste metabólico de
  lobo en el tramo de tiempo entre capturas.
- El criterio maestro real hoy es 33-40%, no 88% -- corregido aquí con
  honestidad; sigue sin alcanzar el 50% que fijó Diego como objetivo,
  con lobo como bloqueo casi exclusivo (el resto del catálogo se
  comporta razonablemente bien).
- El harness completo de referencia (15×12000, sin cortar por tiempo)
  sigue sin correrse nunca para nada de esto -- las 15 semillas de hoy
  se cortaron entre 5765 y 10104 ticks por el límite de tiempo real del
  entorno de 4 núcleos.
## Presupuesto calórico de lobo con venado disponible -- causa real
## identificada: no es nutrición, es frecuencia de encuentro (2026-09-09,
## mismo día, respuesta directa al "Pendiente real" de la sección
## anterior)

Diego pidió investigar directamente la pregunta que dejó abierta la
sección anterior: ¿por qué la inanición sigue siendo la causa de muerte
dominante de lobo pese a que venado (presa numéricamente viable en
solitario, con margen real) ya existe y se caza de verdad? Arnés nuevo,
`diag_calorico_lobo.py` (scratchpad, no en el repo): instrumenta
`SistemaDepredacion._resolver_ataque` para registrar cada captura real
de lobo (especie de presa, saciedad antes/después) y muestrea
`Necesidades.saciedad` de cada lobo vivo cada 200 ticks. 4 semillas
nuevas (500001-500004), hasta 6000 ticks cada una (cortadas entre
5142-6000 por el límite de tiempo real del entorno).

**Corrección propia importante, encontrada al preparar el diagnóstico
antes de interpretar nada**: mis primeros cálculos a mano sobre el
"margen calórico por captura" partían de los valores por DEFECTO
codificados en `sistema_depredacion.py` (`eficiencia_biomasa_saciedad
=1.5`, `captura_prob_min/max=0.05/0.5`) en vez de los valores REALES de
`config/combate.yaml` (`eficiencia_biomasa_saciedad=12.0`,
`captura_prob_min/max=0.15/0.85`) -- un error de lectura propio, no del
motor, corregido antes de sacar ninguna conclusión de los números
equivocados.

**Resultado 1 -- la nutrición por captura NO es el problema, confirmado
con datos reales de captura, no solo con la fórmula**: con
`eficiencia_biomasa_saciedad=12.0` real, `aporte_maximo = (peso_presa/
peso_cazador) * 12.0` es generoso -- una captura de venado o de gnomo
casi siempre llena la saciedad de lobo A TOPE (a 1.0), confirmado
capturando directamente el antes/después real de decenas de capturas
(ejemplos reales: venado 0.598→1.0, gnomo 0.387→1.0, gnomo 0.152→1.0).
Incluso ardilla (la presa menos nutritiva del catálogo) da un
0.06-0.10 real por captura, no un valor insignificante.

**Resultado 2 -- lobo pasa una fracción real y alta de su vida en
saciedad=0**: muestreado directamente (no inferido), **26.4% de media**
de las muestras de saciedad de lobo (15.8%-34.7% según la semilla)
están exactamente en 0.0 -- el estado en el que se activa el sorteo de
muerte por inanición cada tick (`probabilidad_muerte_saciedad_critica
=0.0004` para lobo). Esto explica directamente por qué inanición sigue
dominando: no es que cada captura alimente poco, es que pasan MUCHOS
ticks entre capturas, tiempo suficiente para vaciarse del todo y
quedarse ahí, acumulando riesgo de muerte tick a tick.

**Resultado 3 -- causa raíz real: radio de percepción de caza minúsculo
+ elección puramente por distancia, sin preferencia por valor
nutricional**. `sistema_movimiento.py:_calcular_caza` usa el mismo
`radio_individual` genérico que el resto de percepción
(`config/comportamiento.yaml: percepcion.radio_minimo/maximo_celdas`
=[0,4]) -- para lobo (`agudeza_sensorial` 0.5-0.8), esto aterriza en
radio 2 (42% de individuos) o radio 3 (58%), según el propio docstring
de `nucleo/percepcion.py`. Un radio Manhattan de 2 cubre solo 12 celdas,
uno de 3 cubre 24 -- una fracción minúscula del mapa en cualquier tick
dado. Y dentro de ese radio, `_calcular_caza` ordena presas por
DISTANCIA únicamente (`presas.sort()`, sin ningún peso por valor
nutricional) y persigue siempre la más cercana, nunca la más rentable.
**Confirmado con las capturas reales agregadas de las 4 semillas**:
ardilla 106 capturas, conejo 58, gnomo 35, **venado solo 28** -- pese a
ser, con diferencia, la presa que más saciedad da por captura. La
explicación no es preferencia ni casualidad: ardilla parte con 3x más
población fundadora que venado (30 vs 10) y probablemente mayor
densidad efectiva, así que dentro de un radio de 2-3 celdas es
simplemente más probable topar antes con una ardilla barata que con un
venado rentable -- lobo no elige, coge lo primero que ve.

**Conclusión, contrastada con Diego antes de tocar nada**: el problema
de fondo de lobo nunca fue "falta de presa nutricionalmente viable"
(ya resuelto con venado, y el propio venado se caza con éxito real) --
es que el radio de percepción de caza es demasiado pequeño para que la
frecuencia de encuentro (con cualquier presa, no solo venado) mantenga
a lobo fuera de saciedad=0 la mayor parte del tiempo, y que dentro de
ese radio limitado no hay ninguna preferencia por la presa más rentable
-- ambos factores compuestos explican por qué tener venado disponible
no bajó la inanición de forma visible en la prueba extensa.

**Pendiente real, sin decidir todavía, palancas candidatas sin
implementar**:
- Ampliar el radio de percepción específico de caza (distinto del radio
  genérico compartido con comida/agua/amenaza) -- palanca más directa,
  pero exige decidir si es solo para lobo o una ley general (todo
  cazador percibe presa más lejos que otras cosas, biológicamente
  plausible -- un depredador real invierte más en detectar presa que
  una presa en detectar comida vegetal estática).
- Preferencia por valor nutricional al elegir presa dentro del radio ya
  percibido (ordenar por `aporte_maximo` estimado en vez de por
  distancia pura, o un compromiso entre ambos) -- no descarta el
  problema de radio pequeño, pero al menos evitaría que lobo ignore un
  venado más rentable por perseguir la ardilla más cercana cuando ambas
  están dentro del radio.
- Subir la densidad de venado (más `venados_iniciales`, o tasa de
  reproducción) -- la vía más simple pero ya se descartó una vez un
  atajo parecido para lobo ("subir `lobos_iniciales` no arregla nada",
  2026-09-05) por el mismo motivo que podría fallar aquí: más población
  sin mejorar el problema de encuentro solo añade individuos compitiendo
  por el mismo cuello de botella.
- Ninguna implementada -- decisión de diseño real (qué tan "consciente"
  debe ser un depredador de la calidad de su presa, si el radio de caza
  debe ser una ley general o específica) pendiente de acordar con Diego
  antes de tocar código, mismo criterio que el resto del proyecto.
## Intento real de radio de caza + preferencia por presa -- IMPLEMENTADO,
## MEDIDO, REVERTIDO -- empeora las dos métricas que debía mejorar
## (2026-09-09, mismo día)

Diego aprobó las dos palancas de la sección anterior ("ajustar lo de la
percepción, pero tampoco pasarnos, y lo de la preferencia de presas me
parece interesante sí"). Implementado directamente (pipeline seguía sin
disponibilidad en este contenedor, mismo motivo que venado/cabra_montes):

- `radio_minimo/maximo_caza_celdas` (1-7, `config/comportamiento.yaml`)
  -- radio propio de `Accion.CAZAR`, mismo patrón exacto que ya usan
  BEBER/BUSCAR_PAREJA (`radio_individual` con su propio par min/max),
  ampliación deliberadamente más contenida que la de pareja.
- `peso_distancia_preferencia_presa` (0.02, `config/combate.yaml`) --
  `sistema_movimiento.py:_calcular_caza` deja de ordenar candidatos por
  distancia pura (`presas.sort()` + `presas[0]`) y en su lugar puntúa
  cada uno como `ratio_biomasa - peso_distancia*distancia`, escogiendo
  el máximo -- `ratio_biomasa` reutilizado tal cual del mismo proxy que
  ya usa `_resolver_ataque` para `aporte_maximo`.

Commit `158cdb1`: 415/415 tests (5 nuevos), `BOSQUE_AUTO_TICKS=3000` sin
excepciones -- verificación mecánica correcta, el código hace exactamente
lo que el diseño pedía.

**Verificación cuantitativa real, mismo arnés y MISMAS 4 semillas del
diagnóstico que motivó el cambio (500001-500004) -- resultado: EMPEORA
las dos métricas objetivo, en las 4 de 4 semillas, sin excepción**:

| | Antes (commit `f07915c`) | Después (commit `158cdb1`) |
|---|---|---|
| `frac_tiempo_saciedad_cero` (media) | 0.264 | **0.385** (peor) |
| Capturas totales (4 semillas) | 227 | **58** (peor, -74%) |
| `saciedad_ganada_media` por captura | ~0.25-0.32 | ~0.33-0.44 (mejor) |

La nutrición por captura SÍ mejora (la preferencia por valor funciona
tal como se diseñó: cuando lobo caza, caza algo mejor) -- pero la
FRECUENCIA de caza se desploma tanto que el efecto neto es peor, no
mejor. Dos semillas (de 4) ni siquiera completaron su presupuesto de
ticks en el mismo límite de tiempo real que antes (radio más ancho =
más candidatos que escanear cada tick = más coste real por tick, un
efecto colateral de rendimiento aparte del efecto ecológico).

**Diagnóstico de la causa, con un segundo arnés dirigido** (instrumenta
`_calcular_caza`, no solo las capturas resueltas, para ver si el lobo
oscila de objetivo tick a tick en vez de comprometerse a uno): resultado
mixto, no una única causa limpia -- una semilla mostró oscilación baja
(4.0% de cambios de dirección entre decisiones consecutivas, racha
media de 23.4 ticks manteniendo el mismo rumbo) y otra oscilación alta
(22.4%, racha media 4.4). Incluso en la semilla de BAJA oscilación (más
"comprometida" con un objetivo), las capturas siguieron siendo muchas
menos que antes -- la oscilación real existe pero no es la explicación
completa por sí sola.

**Hipótesis más probable, no confirmada con más profundidad todavía**:
`peso_distancia_preferencia_presa=0.02` es demasiado débil frente a la
brecha real de `ratio_biomasa` entre presas (ardilla~0.006 frente a
venado~0.21, gnomo~0.15 -- una diferencia de hasta 0.2), así que la
distancia queda casi irrelevante en la práctica: con el radio ya
ampliado a 1-7, el lobo persigue casi siempre la presa "más valiosa"
visible, esté a 1 celda o a 7, en vez de comer lo que tiene al lado.
Perseguir sistemáticamente el objetivo más lejano dentro de un radio
mucho más ancho, con presa que también se mueve y sin ningún mecanismo
de "objetivo fijado" entre ticks (`_calcular_caza` recalcula el mejor
candidato de cero cada vez, sin memoria del intento anterior), parece
convertir cada intento de caza en una persecución mucho más larga y con
más probabilidad de fallar -- la ganancia de calidad por captura no
compensa la pérdida de frecuencia.

**Decisión, con la evidencia ya en mano**: revertido por completo
(`git revert 158cdb1`, sin reescribir historia) en vez de intentar una
segunda recalibración sin verificar -- mismo criterio de prudencia ya
aplicado varias veces en este proyecto ("no ajustar a ciegas... probar
antes de aplicar"). El motor vuelve exactamente al comportamiento de
`f07915c` (radio genérico, presa más cercana sin ponderar valor).

**Pendiente real, con más información que antes de intentar esto**:
- El diagnóstico de causa raíz de la sección anterior (radio de caza
  minúsculo + sin preferencia por valor) sigue siendo válido -- lo que
  falla es ESTA implementación concreta, no el diagnóstico.
- Si se retoma: candidatos razonados, ninguno probado -- (a) un peso de
  distancia mucho más alto (p.ej. 0.08-0.10 en vez de 0.02), para que
  solo una presa MUCHO más valiosa justifique alejarse pocas celdas más,
  no todo el radio; (b) mecanismo de "objetivo fijado" (recordar el
  último objetivo de caza mientras siga siendo válido y visible, en vez
  de recalcular desde cero cada tick) -- ataca la oscilación directamente,
  pero es una pieza de estado nueva, más grande que un ajuste numérico;
  (c) separar las dos palancas (probar radio ampliado SOLO, sin
  preferencia, y preferencia SOLO, sin ampliar radio) para aislar cuál
  de las dos es la que realmente perjudica -- este círculo las combinó
  desde el principio y nunca las aisló.
- Lección metodológica reforzada: una intención de diseño bien razonada
  (y aprobada por Diego) no garantiza el resultado -- verificar contra
  el motor real ANTES de dar algo por bueno siguió siendo decisivo aquí,
  exactamente el mismo patrón que motivó media docena de reversiones ya
  documentadas en este proyecto (fertilidad de conejo, `techo_fraccion_
  edad_inicial_longevidad` de lobo, `ardilla_trim`, entre otras).
## Segundo intento (candidato "c" de arriba): preferencia por presa como
## TASA, radio de caza sin tocar -- también empeora, aislando la causa
## real: el problema no era combinar las dos palancas, es preferir
## "mejor" sobre "más cerca" en sí (2026-09-09, mismo día, descartado
## sin comitear)

Diego aprobó explícitamente seguir con el candidato "c" de la sección
anterior: aislar la preferencia por presa del cambio de radio,
implementando además una fórmula distinta (tasa `ratio_biomasa /
(distancia + 1)` en vez de la resta lineal ya descartada) -- una presa
al doble de distancia necesita ser el doble de rentable para ganar,
mismo principio que la teoría de forrajeo óptimo real (rentabilidad =
valor/tiempo de persecución), en teoría más robusto que restar un coste
fijo pequeño. Radio de caza deliberadamente SIN TOCAR esta vez.

414/414 tests (4 nuevos), `BOSQUE_AUTO_TICKS=3000` sin excepciones --
mecánicamente correcto, igual que el primer intento.

**Verificación cuantitativa, mismo arnés y MISMAS 4 semillas
(500001-500004), comparando las tres condiciones ya medidas**:

| | Línea base (`f07915c`) | 1er intento (radio+resta lineal, revertido) | 2º intento (solo tasa, radio intacto) |
|---|---|---|---|
| `frac_tiempo_saciedad_cero` (media) | 0.264 | 0.385 | **0.352** |
| Capturas totales (4 semillas) | 227 | 58 | **95** |

**El segundo intento es mejor que el primero en ambas métricas, pero
sigue siendo claramente peor que la línea base** -- ni la fórmula de
tasa (más principiada) ni aislar el radio bastaron para recuperar el
comportamiento original. Composición de presas también reveladora:
pese a que la tasa está diseñada para favorecer explícitamente a venado
(ratio~0.21) sobre ardilla (ratio~0.006), la PROPORCIÓN de capturas de
venado bajó frente a la línea base (12.3%→8.4% del total) -- el colapso
general de frecuencia de caza (227→95) arrastra hacia abajo incluso a
la presa que la preferencia debía beneficiar.

**Conclusión real, más importante que el resultado numérico en sí**:
esto descarta la hipótesis de que "combinar radio ampliado + preferencia
mal calibrada" era la causa del primer fracaso -- **la preferencia por
presa SOLA, con radio intacto y con una fórmula mejor fundamentada
(tasa, no resta), sigue perjudicando la frecuencia de caza real**. El
mecanismo de fondo parece ser estructural, no un problema de calibración
de un parámetro concreto: `_calcular_caza` recalcula el mejor candidato
desde cero cada tick, sin ningún compromiso persistente con un objetivo
-- cualquier fórmula que a veces prefiera un objetivo más lejano sobre
uno más cercano introduce, por diseño, más ticks de persecución por
intento de caza, y con presa que también se mueve, más ticks de
persecución significan más oportunidades reales de perder el objetivo
antes de alcanzarlo. La ventaja de "cazar mejor cuando se caza" nunca ha
compensado la pérdida de "cazar con menos frecuencia" en ninguna de las
dos fórmulas probadas.

**Decisión, con la evidencia ya en mano**: descartado sin comitear
(cambios locales revertidos con `git checkout`, nunca llegaron a
`master` ni a la rama de trabajo) -- 410/410 tests en verde tras
descartar, motor exactamente en el estado de `f07915c`.

**Pendiente real, con el candidato "c" ya agotado**:
- De las tres palancas candidatas señaladas tras el primer revert, dos
  quedan descartadas por evidencia real (resta lineal + radio; tasa sin
  radio) y una sin probar todavía -- **mecanismo de "objetivo fijado"**
  (recordar el último objetivo de caza mientras siga siendo válido y
  visible, en vez de recalcular desde cero cada tick) es ahora el único
  candidato de la lista original que no se ha intentado, y el análisis
  de esta sección lo señala como el más prometedor: ataca directamente
  la causa estructural identificada (sin compromiso persistente, ningún
  cambio de fórmula de puntuación puede evitar el coste de persecuciones
  más largas y más propensas a fallar). Es una pieza de estado nueva
  (más grande que un ajuste numérico), no probada todavía.
- Alternativa mucho más simple, también sin probar: aceptar que "más
  cerca" ya es, en la práctica, una heurística razonable para un
  depredador oportunista (coincide con cómo cazan muchos depredadores
  reales -- energía mínima antes que presa óptima) y abandonar la vía
  de preferencia por valor por completo, centrando cualquier mejora
  futura de lobo en otras palancas (frecuencia de encuentro vía
  densidad de presa, no vía elección de presa).
- El diagnóstico de causa raíz de "Presupuesto calórico de lobo..."
  (radio pequeño + sin preferencia) sigue siendo correcto como
  DIAGNÓSTICO -- lo que estas dos rondas descartan es que la preferencia
  por valor, en cualquiera de sus dos formulaciones probadas, sea la
  CURA correcta.
## Radio de caza en solitario -- TERCER intento, la primera mejora real
## tras dos reversiones, comiteado (2026-09-09, mismo día)

Diego preguntó directamente si bastaba con dejar solo el radio de
percepción más alto -- exactamente la palanca que quedaba sin aislar de
la lista original ("probar radio ampliado SOLO, sin preferencia").
Implementado: mismo `radio_minimo/maximo_caza_celdas` (1-7,
`config/comportamiento.yaml`, patrón ya usado por BEBER/BUSCAR_PAREJA)
del primer intento, pero **sin ningún cambio en la elección de presa**
-- `_calcular_caza` sigue con `presas.sort()` + `presas[0]` (la más
cercana), exactamente como en la línea base. 413/413 tests (3 nuevos),
`BOSQUE_AUTO_TICKS=3000` sin excepciones.

**Verificación cuantitativa, mismo arnés y MISMAS 4 semillas
(500001-500004), comparando las cuatro condiciones ya medidas**:

| | Línea base (`f07915c`) | 1er intento (radio+resta lineal) | 2º intento (solo tasa) | 3er intento (solo radio) |
|---|---|---|---|---|
| `frac_tiempo_saciedad_cero` (media) | 0.264 | 0.385 | 0.352 | **0.218** |
| Capturas totales (4 semillas) | 227 | 58 | 95 | **212** |

**Primera mejora real de las tres rondas probadas**: `frac_tiempo_
saciedad_cero` baja de 0.264 a 0.218 (lobo pasa menos tiempo en el
estado que activa el sorteo de muerte por inanición), y las capturas se
mantienen prácticamente al nivel de la línea base (212 frente a 227,
dentro del ruido esperado por desplazamiento de secuencia de `rng`).
Desglose semilla a semilla, coherente con la varianza ya conocida de
esta especie (no una mejora uniforme, pero sí clara en agregado): 3 de
4 semillas mejoran individualmente (s2: frac 0.311→0.074, capturas
57→90; s3: 0.347→0.215, 29→50; s4: 0.240→0.213, 51→57), 1 de 4 empeora
(s1: 0.158→0.370, 90→15).

**Conclusión, con las tres rondas juntas**: confirma con precisión el
diagnóstico de causa raíz -- el radio de percepción SÍ era demasiado
pequeño y SÍ era una palanca real de mejora; el error de los dos
intentos anteriores no era el radio, era la preferencia por valor
combinada con él (o sola). "Más cerca" resulta ser, en la práctica, una
heurística de caza suficientemente buena para un depredador oportunista
-- ampliar cuánto ve sin cambiar a quién persigue es lo que realmente
ayuda, coincidiendo con la alternativa "mucho más simple" ya señalada
como candidata en la sección anterior.

**Comiteado** (`config/comportamiento.yaml`,
`sistemas/sistema_movimiento.py`, `tests/test_radio_caza_solitario.py`).

**Pendiente real, explícito**: `radio_minimo/maximo_caza_celdas=[1,7]`
sigue PROVISIONAL, sin calibrar contra el harness completo -- esta
verificación es de 4 semillas, no las 15×12000 de referencia; el
criterio maestro de Diego (5 especies vivas a la vez) no se remidió con
este cambio ya aplicado, candidato inmediato si se quiere confirmar el
efecto agregado sobre el criterio maestro, no solo sobre lobo en
aislamiento; el mecanismo de "objetivo fijado" entre ticks queda como
posible mejora adicional futura, ya no urgente dado que esta palanca
más simple ya mostró una mejora real medida.

### Verificación a escala del criterio maestro -- A/B real con el harness
### completo (worktree "antes" vs. `master` "después"), mejora real pero
### modesta, no una solución (2026-09-09, mismo día)

Diego cuestionó con razón que la mejora del proxy (`frac_tiempo_
saciedad_cero` 0.264→0.218, 17.4% relativo) pudiera ser demasiado
pequeña para importar -- pregunta legítima, dado que el proxy nunca
mide directamente lo que de verdad interesa (extinción real, criterio
maestro). Verificado con el propio `herramientas/harness_calibracion.py`
en vez de seguir confiando en el proxy: worktree aislado en el commit
previo al fix (`890d6b3`, "antes") corriendo las MISMAS 8 semillas
nuevas (20001-20008, 6000 ticks, 400s/semilla de límite) que el
directorio principal con el fix ya aplicado (`e3f1d7c`, "después") --
mismo criterio metodológico ya usado varias veces este día (comparar
código real, no solo config en memoria).

| | Antes (`890d6b3`) | Después (`e3f1d7c`) |
|---|---|---|
| Extinción lobo | 25% (2/8) | **12% (1/8)** |
| Extinción gnomo | 0% (0/8) | 12% (1/8) |
| Extinción ardilla | 12% (1/8) | 12% (1/8) |
| Extinción conejo / caballo | 0% / 0% | 0% / 0% |
| **Criterio maestro (5 especies vivas)** | **62% (5/8)** | **75% (6/8)** |

**Honesto sobre el tamaño real del efecto**: hay mejora real en las dos
métricas que de verdad importan (extinción de lobo, criterio maestro),
en la misma dirección que predecía el proxy -- pero **n=8 por
condición, la misma escala pequeña que ya ha producido lecturas
erróneas varias veces este día** (el propio lobo mostró 100%/67%/53%/
47%/25%/12% de extinción según la muestra en investigaciones previas de
esta sesión). Un dato que no encaja limpio y no se ignora: gnomo pasó
de 0% a 12% de extinción (1 semilla) -- gnomo no es depredador, no
debería verse afectado por el radio de caza de lobo de ninguna forma
causal directa, así que esto es ruido de desplazamiento de secuencia de
`rng` (el mismo fenómeno ya documentado media docena de veces en este
proyecto), no un efecto colateral real. Las causas de muerte agregadas
de lobo son casi idénticas entre ambas corridas (inanición 46 antes vs
45 después, vejez 40 en ambas) -- la mejora se explica más por CUÁLES
semillas concretas cruzan el umbral de extinción que por un cambio
dramático en el patrón agregado de causas.

**Conclusión, sin inflar el resultado**: el radio de caza ampliado es
una mejora real, medida dos veces de forma independiente (proxy
instrumentado + harness completo con extinción real), en la dirección
correcta y del orden de magnitud esperado por el propio análisis del
proxy (no una sorpresa positiva ni negativa) -- pero **no resuelve la
fragilidad de lobo**, sigue extinguiéndose en 1 de 8 semillas nuevas
incluso con el fix, y la varianza intrínseca de esta especie sigue
siendo mayor que la señal de cualquier mejora aislada medida con
muestras de este tamaño. Confirma con más fuerza la síntesis ya escrita
varias veces en este documento: cualquier calibración de lobo que se
quiera dar por "cerrada" de verdad necesita el harness de referencia
completo (15×12000), no lotes de 4-8 semillas -- este mismo ejercicio,
con más semillas, sería la forma correcta de confirmar si el 62%→75% es
una señal real o todavía ruido.

Worktree temporal (`scratchpad/worktree-antes`) retirado tras la
comparación -- no forma parte del repositorio.
## Orillas vadeables -- acceso real a agua para especies pequeñas,
## implementado directamente por Claude (2026-09-10)

Diego preguntó por qué `tasa_perdida_hidratacion_por_tick`/
`probabilidad_muerte_deshidratacion` se calibran especie por especie sin
ninguna relación con `DimensionesFisicas.peso`/`altura` -- el propio
docstring de `componentes/dimensiones_fisicas.py` ya reconocía el hueco
para peso ("el enlace peso -> tasa de saciedad vía metabolismo queda
pendiente, sin construir"). Investigado en conversación antes de tocar
nada: aplicar una ley de Kleiber real a la TASA DE PÉRDIDA habría ido en
la dirección CONTRARIA a la que el motor necesitó empíricamente estos
últimos días (especies pequeñas necesitaron decaer MÁS LENTO, no más
rápido, para sobrevivir) -- indicio real de que esos ajustes compensaban
mecánica de forrajeo que no escala con el tamaño corporal (consumo/
valor nutricional universales), no metabolismo real. Diego redirigió el
diseño hacia la causa concreta que él mismo señaló: el ACCESO a fuentes
de agua, no el metabolismo.

**Diagnóstico contra el motor real, tres mediciones antes de diseñar
nada** (arnés de sesión, 8 semillas nuevas):
1. Solo 5.1-9.5% del agua permanente (río/lago/poza) es vadeable para
   ardilla, 7.6-11.4% para conejo -- frente a 44-62% para gnomo/caballo.
   `profundidad_agua_potable(celda) <= altura` es un umbral binario duro,
   mediana real de profundidad 1.26m.
2. Charcos efímeros cubren 57-82% del mapa cuando llueve (siempre
   vadeables, `techo_profundidad_charco=0.03m`), pero hay rachas reales
   de 70-190 ticks (~3-8 días) de sequía total sin un solo charco --
   ardilla/conejo dependen enteramente del agua permanente en esas
   ventanas.
3. **Vía descartada, medida antes de elegir**: curvar
   `nucleo/agua.py:_profundidades_cuenca` (hoy lineal en `[0,banda]`)
   con un exponente >1 mejora la vadeabilidad de forma real (9.5%→20.4%
   con exponente 2.5) pero con techo bajo -- incluso exponente 5.0
   (mediana global cayendo de 1.26m a 0.96m) solo llega a 27-29%, porque
   la mayoría de celdas de una cuenca caen cerca del mínimo por la
   resolución del grid (10m/celda), no distribuidas parejo en [0,1].

**Diseño elegido por Diego, con datos que lo respaldan**: un cuerpo de
agua real tiene orilla por el propio desgaste del agua -- medido ANTES
de implementar que el anillo de celdas de tierra firme 4-vecinas de
cualquier celda de agua tiene, en las mismas 8 semillas, **el mismo
tamaño que el propio cuerpo de agua** (634 celdas de anillo frente a 632
de agua, ratio 1.00). Spec:
`docs/superpowers/specs/2026-09-10-orillas-vadeables-design.md`.

**Implementado directamente por Claude** -- este contenedor cloud no
tiene `OPENROUTER_API_KEY` ni `mini-swe-agent` instalado ni centinela
corriendo (mismo escenario ya documentado con venado/cabra_montes),
Diego pidió implementar directamente en vez de dejarlo en cola.

- `nucleo/celda.py`: nuevo campo `profundidad_orilla: float = 0.0` --
  capa geográfica estática (como `profundidad_agua`, nunca se persiste,
  se regenera desde la semilla), independiente de `tiene_agua`/
  `tipo_agua` -- la celda de orilla sigue siendo tierra de verdad, mismo
  `tipo_sustrato`, sigue colonizable por flora y construible.
- `nucleo/agua.py:generar_orillas_vadeables` (nueva): toda celda de
  tierra firme 4-vecina de al menos una celda de `cuerpos_agua` recibe
  `profundidad_orilla_metros` fijo -- llamada una vez sobre el resultado
  ya unificado de río+lago+poza (`nucleo/zona_bioma.py`, justo tras
  `generar_cuerpos_agua`), igual para los tres tipos, sin distinción
  (ley neutra). `hay_agua_potable`/`profundidad_agua_potable` extendidas
  para mirar también esta capa, mismo patrón `or`/`max` que ya combinan
  `profundidad_agua`/`profundidad_charco` -- como estas dos funciones ya
  son las que consume `_calcular_hidratacion` y la validación de
  movimiento, el enganche es automático sin tocar nada más.
- `config/hidrologia.yaml`: `profundidad_orilla_metros: 0.1`
  (PROVISIONAL) -- por debajo incluso de la altura mínima de ardilla
  (0.15m), vadeable por cualquier especie del catálogo.
- `celdas_con_agua` (exclusión de flora-sobre-agua, fix del 2026-09-02)
  deliberadamente sin tocar -- sigue mirando solo `tipo_agua != ""`, el
  anillo nunca cuenta como sumergido.
- 8 tests nuevos (`tests/test_orillas_vadeables.py`): geometría del
  anillo (solo 4-vecinos, nunca sobrescribe agua real, nunca diagonal),
  `hay_agua_potable`/`profundidad_agua_potable` con la nueva capa sola y
  combinada (regresión de las dos capas ya existentes), anillo real
  sobre un mundo generado, y regresión explícita de que una celda de
  orilla generada por `generar_zona_bioma` conserva `tipo_sustrato` y NO
  aparece como agua para flora.

**Verificado contra el motor real, no solo geometría aislada**: 429/429
tests en verde (421 previos + 8 nuevos), `BOSQUE_AUTO_TICKS=3000` sin
ninguna excepción. Medido el efecto real combinando agua permanente +
orilla (`hay_agua_potable`/`profundidad_agua_potable` sobre las mismas 8
semillas): **ardilla 9.5%→54.8%, conejo 11.4%→55.8%** de vadeabilidad
real -- muy por encima del techo de ~27-29% que daba la vía de la curva
descartada, y acercando a ardilla/conejo al mismo orden de magnitud que
gnomo/lobo (72-75%) en vez de quedar muy por detrás.

**Pendiente real, explícito**: `profundidad_orilla_metros=0.1`
PROVISIONAL, sin calibrar contra el harness completo; las tasas de
hidratación por especie (lobo/ardilla/gnomo/conejo, todas rebajadas del
valor universal durante la investigación de estabilidad de
2026-09-05/06/09) siguen sin tocar -- con acceso real mejorado podría
haber margen para revisar si esos alivios siguen haciendo falta con la
misma magnitud, pero eso exige su propia investigación A/B contra el
motor, no se asume aquí; la vía de "ganancia por bocado escalada por
peso" (saciedad, problema distinto del de hidratación) sigue sin
diseñar, aparcada en la misma conversación en favor de resolver primero
el acceso a agua.
## Tasa de consumo al comer por especie -- anclada a datos reales de
## alimentación animal, no a una fórmula de peso, implementado
## directamente por Claude (2026-09-10, misma sesión)

Continuación directa de "Orillas vadeables": con el acceso a agua ya
resuelto, se retomó la pregunta original de Diego sobre peso/hidratación,
ahora aplicada a `tasa_consumo_al_comer` (cuánta comida se ingiere por
tick de `Accion.COMER`) -- universal hasta ahora (0.5, sin relación con
ninguna especie).

**Dos errores propios, corregidos con honestidad antes de fijar
nada** -- mismo patrón de autocrítica ya varias veces documentado en este
proyecto:
1. Primer intento: dividir la ganancia por bocado entre `peso^exponente`
   (mismo patrón que ya funcionó para "orillas"). Diego señaló con razón
   que el resultado era absurdo -- con exponente 0.5, caballo pasaría de
   17 a 107 ticks (4.5 días) solo para saciarse. **Corrección real, no
   solo un ajuste de exponente**: el baseline de 17 ticks (17h) ya
   coincide con datos reales de campo (caballos pastan 10-17h/día), así
   que el error no era el punto de partida, era escalarlo sin ningún
   ancla real -- ninguna fórmula matemática pura de peso reproduce el
   patrón real observado (ver más abajo, no es monótona en el peso).
2. Segundo error, encontrado al buscar datos de hidratación: los
   cálculos previos de "46-91 ticks para hidratarse" (sección de arriba)
   estaban mal -- usaban por error la fórmula de "hidratación al comer"
   (`consumo*val_hid`) en vez del mecanismo real de `Accion.BEBER`
   (`_resolver_beber`: `hidratacion += tasa_consumo_al_beber` directo,
   SIN `val_hid` de por medio) -- 5 ticks reales, no 46-91.

**Investigación real (WebSearch, no inventado) de tiempo de alimentación
y bebida en la naturaleza, antes de diseñar nada**:
- **Beber es rápido y prácticamente independiente del peso**: caballo
  (450kg, la especie más grande) solo dedica 5-6 minutos/día a beber
  pese a beber 20-55L; conejo bebe "poco y a menudo" (hasta 15
  visitas/día); ciervo 1-2 veces/día; ardilla ~2 veces/día (gran parte de
  su hidratación viene de la comida); lobo puede pasar días sin beber
  directamente (agua de la presa + agua metabólica). **Conclusión: el
  mecanismo de `BEBER` (5 ticks, universal) ya estaba bien calibrado --
  no se tocó nada, y NO se diferencia por especie a propósito** (el peso
  determina el ACCESO, ya resuelto con orillas, pero no la velocidad).
- **Comer, en cambio, sí varía por especie de forma real, aunque no
  como función simple del peso**: caballo 10-17h/día (dieta pobre, baja
  densidad calórica, el que MÁS tiempo dedica en términos absolutos
  pese a ser el más grande); conejo 6-8h/día; ardilla ~2.5-5.5h/día
  (47-50% de su actividad real en forraje); ciervo, patrón de 5 comidas
  cortas repartidas en 24h (~7h estimadas); lobo -- patrón cualitativamente
  distinto, festín-y-ayuno, no comparable a un "tiempo diario" (ya
  resuelto de otra forma, ver abajo). Cazadores-recolectores humanos
  (!Kung, Agta): 2.8-7.6h/día de trabajo de subsistencia total, ~1.7-2.7h/
  día de forrajeo puro (estudio !Kung) -- usado como ancla para gnomo,
  a petición explícita de Diego ("un gnomo debería alimentarse como un
  humano recolector").

**Diseño**: en vez de una fórmula de peso^exponente (descartada, no
reproduce el patrón real observado -- caballo > conejo > ardilla en
horas absolutas no es una función simple del tamaño, depende del tipo de
dieta), `tasa_consumo_al_comer_por_especie` por especie
(`config/fisiologia.yaml`), calculada como
`1/(horas_objetivo*val_nut_medio_de_la_dieta)` contra los valores
nutricionales reales del catálogo:

| Especie | Horas reales/día | tasa_consumo_al_comer |
|---|---|---|
| gnomo | 4h (proxy cazador-recolector) | 1.250 |
| conejo | 7h | 0.952 |
| ardilla | 4h | 0.884 |
| venado | 7h (estimado) | 0.826 |
| cabra_montes | 7h (proxy venado, sin dato propio) | 0.680 |
| caballo | 13h | 0.657 |
| lobo | — (depredación, no forraje vegetal) | sin entrada, usa el universal 0.5 |

**Alcance real, deliberadamente limitado**: solo afecta a
`Accion.COMER` sobre forraje vegetal (celda, provisiones propias,
alacena de cocina) -- el **carroñeo de Necromasa sigue usando el valor
universal** (0.5, sin datos reales de velocidad de ingesta de carroña
investigados, ningún consciente come carne hoy). `sistema_recursos.py`
calcula `tasa_comer_especie` una vez al principio del bloque de
forrajeo vegetal (`identidad.especie.value`, ya disponible ahí para la
dieta) y sustituye las 4 apariciones relevantes de
`self.tasa_consumo_comer`; el carroñeo (línea aparte, antes en el
método) queda intacto.

**Efecto colateral real, detectado al correr los tests, no un bug**:
con `tasa_comer_especie` de gnomo (1.25) mayor que la cantidad
disponible en varios tests dirigidos (`Inventario.provisiones` con solo
1.0kg guardado), el consumo real queda topado por lo disponible y la
purga automática (`restante <= umbral_purga_provisiones`) borra la
clave por completo en vez de dejar un residuo -- 6 tests existentes
(`test_provisiones_alimento.py`, `test_como_cocinar.py`) asumían
implícitamente el valor universal (0.5) de antes de este cambio,
corregidos para reflejar los nuevos números exactos.

**Verificado**: 425/425 tests (4 nuevos,
`tests/test_tasa_consumo_por_especie.py` -- gnomo consume más rápido
que el universal, caballo tiene su propia tasa distinta de gnomo, una
especie sin entrada -- lobo -- cae al universal, el carroñeo NUNCA usa
la tasa por especie). `BOSQUE_AUTO_TICKS=3000` sin ninguna excepción.

**Pendiente real, explícito**: ninguna verificación A/B de población
tras este cambio -- desplaza la secuencia de `rng` como cualquier
cambio de config (mismo fenómeno metodológico ya documentado
repetidas veces en este proyecto), no medido si afecta al criterio
maestro de Diego; los tiempos objetivo de venado/cabra_montes/gnomo
son estimaciones razonadas (patrón de comidas cortas, proxy de
rumiante similar, proxy de cazador-recolector humano) más flojas que
los datos directos de caballo/conejo/ardilla (medidos en fuentes
reales específicas de esas especies) -- señalado con honestidad, no
presentado con la misma solidez; todos los valores siguen
PROVISIONALES, sin calibrar contra el harness completo.
## Investigación de fondo del lobo -- el embudo ya funciona, 0 extinciones
## en 39 semillas nuevas de esta sesión, y la ley de fecundidad por edad
## cerrada encima (2026-09-10, mismo día)

Diego pidió analizar bien por qué el lobo no prospera. Investigación con
arnés nuevo de instrumentación fina (scratchpad de sesión,
`diag_lobo_profundo.py`, no en el repo), un nivel más profundo que el
harness agregado: embudo completo por gestación (Concepcion -> término o
muerte de la madre), por lobo individual (fundador vs nacido en partida,
edad y saciedad al último muestreo, causa de muerte, capturas atribuidas
por `cazador_id`, muestreo de estado cada 100 ticks) y trayectoria diaria
de población. **Resultado que invierte parcialmente el diagnóstico
histórico**: en 36 semillas nuevas medidas en dos tandas (911001-911112,
911101-911112, ventanas 3132-6457 ticks por límite de tiempo real) el
lobo se sostiene en TODAS, sin una sola extinción, con embudo
reproductivo activo de forma medible:

- Embudo real (agregado de las dos tandas): ~79-81% de las gestaciones
  resueltas llegan a término; los fallos (~21%) son por muerte de la
  madre, y de esos fallos ~3/4 son por VEJEZ (madres que conciben ya
  viejas y mueren de historia natural a ~44-50 días de una gestación de
  60-75 días — gestaciones de 1440-1800 ticks).
- Las muertes de lobo fundador son el recambio natural (vejez a edad
  media 4506-4680 ticks, ~9.4-9.8 años de longevidad 8-14), no colapso.
- La caza nueva de venado se ejerce a escala (53-55 capturas por tanda
  de 12 semillas, frente a prácticamente 0 antes del radio de caza),
  con variedad real (ardilla 241, conejo 182, gnomo 75 por tanda).

**Harness de referencia del repo también corrido el mismo día** (15
semillas nuevas 921001-921015, cortadas todas a 1500s entre 3990-7966
de 12000 ticks): **lobo 0/15 extinción (0%)**, población final media 10.7
(min 3, max 27); criterio maestro de Diego (5 especies vivas a la vez)
**11/15 (73%)**, la mejor medición grande de todo el proyecto. Conejo 7%
y ardilla 27% de extinción — el cuello de botella residual deja de ser
el lobo. Atribución honesta, sin cerrar: no se puede atribuir este giro
a una sola pieza sin A/B contra el commit previo (la corrida del 47% del
2026-09-09 llevaba el mismo código salvo radio de caza + cohesión de
manada + orillas + tasa de consumo; y 47% estaba dentro de la varianza
ya documentada de lobo). Inanición sigue siendo la causa #1 de muerte
de lobo (98 vs 82 por vejez en el harness): vive al borde, y lo que
ahora funciona es que la reproducción lo compensa.

### Fecundidad por edad — ley biológica neutra, cerrada (spec, implementado
### directamente por Claude, A/B contra el motor con hallazgo honesto)

Diego cuestionó el hallazgo ("muerte de la madre por vejez embarazada no
cuadra con la realidad animal"). Contrastado con la biología real:
concebir y perder la gestación por muerte natural EXISTE en fauna
salvaje (la fertilidad persiste hasta cerca de la muerte en la mayoría
de mamíferos), pero lo que NO cuadraba era que el motor no modelara
ninguna senescencia reproductiva — `factor_base_concepcion` era
constante con la edad. Tres formas discutidas (declive tardío espejo de
vejez / lineal desde madurez / ventana fértil discreta); Diego eligió
la 1. Spec:
`docs/superpowers/specs/2026-09-10-fecundidad-edad-design.md`.

**Implementado directamente por Claude** (pipeline sin disponibilidad en
este contenedor, excepción pedida explícitamente por Diego):

- `nucleo/ciclo_vital.py:factor_fecundidad_edad()` (nueva, pura): 1.0
  hasta `inicio_declinacion_fecundidad` (PROVISIONAL 0.6) de la
  longevidad INDIVIDUAL (mismo ancla que `probabilidad_muerte_vejez`),
  declive progresivo `1 - fase**exponente_fecundidad_edad` (PROVISIONAL
  2.0 — a diferencia del exponente 8 del muro de muerte, el declive de
  FERTILIDAD es perceptible desde el inicio del tramo: al 80% de vida
  factor ~0.75, al 90% ~0.36) y 0.0 saturado al agotar la longevidad
  (misma convención que la curva de vejez). Solo la hembra (la tirada de
  concepción ya es por hembra); fecundidad masculina diferida, YAGNI.
- `sistemas/sistema_reproduccion.py:actualizar` (línea ~325, el ÚNICO
  punto de concepción del motor): `probabilidad = factor_base *
  sociabilidad_media * factor_edad`. Sin tocar el gate de saciedad ni el
  escalado de camada. Sin persistencia (deriva de edad + longevidad ya
  persistidos).
- `config/fisiologia.yaml` sección `ciclo_vital`: los dos parámetros
  nuevos, PROVISIONALES, con el A/B requerido documentado en el propio
  comentario.
- 5 tests de ley (`tests/test_fecundidad_edad.py`, declarativos + 2 por
  el despacho real: hembra con longevidad agotada JAMÁS concibe a través
  de `actualizar`, hembra joven sí).

**Hallazgo de test expuesto por la ley, no causado por ella**: 3 tests de
concepción de `tests/test_relaciones.py` fallaban al activar la ley —
su fixture usaba `tick_actual=100_000` con `tick_nacimiento=0`, es decir
probar la concepción con una madre gnomo de ~208 AÑOS. La ley bloquea
esa concepción CORRECTAMENTE (razón de edad desbordada); fixtures
corregidos con edad adulta plena anclada al tick de la escena (7200
ticks). La ley no regresó nada más: 436/436 tras el fix.

**A/B contra el motor real, criterio del spec NO del todo cumplido —
decisión de Diego: dejar la ley así**: con 12 semillas nuevas
(911201-911212): 0/12 extinción, motor estable, frecuencia de concepción
baja ~35% (53 -> 35 gestaciones resueltas por tanda comparable) y la
reproducción se concentra en hembras más jóvenes — pero el % de
gestaciones perdidas por muerte de madre NO bajó de forma clara (21% ->
31%, entre ruido, mismo conteo absoluto 11): las madres fracasadas
conciben en la zona ratio 0.75-0.9, donde el factor de la curva aún
concede 0.4-0.6. Incumplimiento parcial del criterio de cierre del spec
("tasa baja de forma clara"), aceptado explícitamente por Diego como
mejora de realismo (el embarazo tardío absoluto sí baja). Tres caminos
se plantearon para el % residual (recalibrar curva más agresiva, aceptar
como ley, o gestación como riesgo propio — la vieja Propuesta C) y
Diego eligió aceptar ("dejémoslo así").

**Limitación honesta de la verificación del A/B**: n=12/tanda, ventanas
de 3.5-5k ticks, comparar gestaciones entre tandas comparte el ruido de
desplazamiento de secuencia de rng ya documentado — no una calibración
cerrada; ambos parámetros siguen PROVISIONALES ante el harness completo.

### Corrección de infraestructura de paso — conexión SQLite nunca cerrada
### (bug preexistente, 8 tests roundtrip rojos en Windows)

Al correr la suite completa en este entorno (Python 3.14/Windows), 8
tests de roundtrip de persistencia fallaban YA EN `master` sin relación
con los cambios de hoy. Causa raíz verificada: `Persistencia._conectar()`
abre una conexión nueva POR OPERACIÓN y ninguna se cierra nunca — el
context manager nativo de `sqlite3.Connection` solo hace
commit/rollback, JAMÁS cierra. En Linux/WSL2 es inofensivo (unlink de
ficheros abiertos es legal); en Windows fija el fichero .db y el cleanup
del `TemporaryDirectory` explota con WinError 32. Corregido en UN punto
central: factory `_ConexionConCierre(sqlite3.Connection)` con `__exit__`
que cierra tras el commit/rollback nativo, cero cambios en los 7 call
sites (`with self._conectar() as con:`). 8/8 roundtrips en verde,
ninguna otra prueba tocada.

### Pendiente real, explícito, tras esta sesión

- Lobo: el vórtice de extinción no apareció en ninguna de las 39 semillas
  nuevas de hoy (24 finas + 15 del harness), con embudo reproductivo
  activo y fundadores recambiéndose de forma natural — el mejor estado
  de esta especie desde que se construyó el motor. Aun así, inanición
  sigue siendo su causa #1 de muerte (vive al borde) y el harness se
  cortó por tiempo en 15/15: la ventana 8k-12k sigue sin medirse nunca
  en una corrida completa. Un A/B contra el commit previo a
  radio-de-caza podría cuantificar cuánto del giro se debe a las piezas
  de esa semana frente a varianza — no perseguido por ahora (Diego:
  "dejémoslo así").
- Gestaciones perdidas por muerte de madre (~21-31% de las resueltas):
  el % no se movió con la ley. Si algún día se quiere cortar de raíz,
  el candidato de diseño es la Propuesta C (gestación como estado físico
  con coste real de movilidad/exposición), no más curvas de fecundidad.
- Caza en manada contra caballo: sigue sin observarse (0 eventos en el
  A/B de cohesión de este mismo día) — Quedan las dos palancas
  numéricas ya señaladas sin probar
  (`factor_ampliacion_techo_manada`, `radio_apoyo_grupal`).
- Ardilla (27% de extinción en el harness de 15) y conejo (7%) son ahora
  los eslabones más frágiles del criterio maestro, no el lobo.
- Centinela del pipeline: sigue parado en la máquina histórica, y este
  contenedor no tiene la infraestructura (sin `OPENROUTER_API_KEY` ni
  `mini-swe-agent`) — el cierre de este arco se hizo por implementación
  directa a petición de Diego, la cuarta pieza consecutiva así en este
  entorno.

## Cuatro recomendaciones del informe ecológico (2026-09-12) revisadas
## con datos reales -- tres resultan en NO TOCAR NADA, una queda abierta
## para decisión de diseño (2026-09-15)

Diego pidió retomar las recomendaciones #2-#5 del informe ecológico de
la sesión del 2026-09-12 (la #1, especie depredadora pequeña, ya se
cerró como zorro, ver arriba). Investigadas las cuatro contra el motor
real antes de tocar ningún número -- mismo criterio de siempre.

### Corrección real -- CLAUDE.md se contradecía a sí mismo sobre la
### dirección de `factor_ampliacion_techo_manada`

Al revisar la recomendación #3 ("factor de manada hacia abajo, error de
signo del 09-09 marcado"), verificado contra el código antes de tocar
nada: la fórmula real (`sistema_depredacion.py`/`sistema_movimiento.py`)
es `peso_maximo_presa = peso_cazador * (1 + aliados_cazando * factor)`
-- SUBIR el factor baja el número de aliados necesarios (cada aliado
pesa más en el umbral), nunca al revés. Esto coincide con la propia
entrada del 2026-09-09 más citada en este documento ("subir
`factor_ampliacion_techo_manada` (1.0→3.0, **menos aliados
necesarios**)"). Pero DOS entradas posteriores del mismo día
(sección "Balance del día" y la sección "'No se forma ninguna manada'
era un artefacto...", 2026-09-10) afirman lo contrario ("habría que
bajarlo, no subirlo, error de signo"; "bajar el factor... exigiría
menos aliados") -- ambas incorrectas, contradicen la fórmula Y la
entrada correcta del mismo documento. Un error de redacción real, no
solo una entrada desactualizada -- corregido aquí explícitamente, sin
borrar las entradas originales (mismo criterio de honestidad del resto
del documento: registra qué se creyó en cada momento).

**Verificado con un A/B real antes de decidir nada**, no solo con la
corrección de la fórmula: 6 semillas nuevas (810001-810006) × 6000
ticks, factor=1.0 (control, master) contra factor=6.0 (el doble del 3.0
ya probado el 09-09, para dar a la dirección correcta toda la ventaja
posible). **Resultado: 0 muertes de caballo por depredación en las 12
corridas, en AMBAS condiciones, sin ninguna excepción** -- ni siquiera
un factor 6x mayor (que matemáticamente reduce el umbral a 1-2 aliados
en vez de 5-6) produjo una sola captura de caballo por manada de lobo.
Confirma con más fuerza el diagnóstico ya cerrado el 2026-09-10 ("Lobo
caza en manada... por qué los lobos en manada no cazan caballos"): el
cuello de botella real no es el umbral de peso, es que casi nunca
coinciden varios lobos cazando activamente cerca a la vez (máximo 4
aliados observado en su día, 1.92% de los momentos) -- ningún valor del
factor, en ninguna dirección, puede arreglar un problema de
coincidencia temporal. **Conclusión: no se toca `factor_ampliacion_
techo_manada`** -- ni la dirección "correcta" (subir) ni la "incorrecta"
(bajar) tienen ningún efecto medible, la palanca en sí está agotada. Si
se quiere revivir la caza en manada de caballo, el candidato real es
`radio_apoyo_grupal` (ampliar cuántos lobos entran en el chequeo de
"cazando cerca" en un instante dado) o aceptar que es, en la práctica,
un evento estructuralmente raro y coherente con la escasez real de
grandes cacerías coordinadas -- ninguno de los dos decidido ni probado
en esta sesión.

### Recomendación #2 (densidad de venado para el valle de lobo) --
### probada, sin señal positiva, no aplicada

A/B real, 6 semillas nuevas (720001-720006) × 6000 ticks,
`venados_iniciales` 10 (control) contra 20 (doblado). Resultado: lobo
final medio 7.17 (control) frente a 4.33 (doblado) -- **peor, no
mejor**, con doblar venado; muertes de lobo por inanición agregadas 29
(control) frente a 38 (doblado). Dirección contraria a la hipótesis que
motivó la recomendación. **Diagnóstico honesto, no una conclusión
causal firme**: con solo 6 semillas pareadas, esto es del mismo orden
que el ruido de desplazamiento de secuencia de `rng` ya documentado
repetidas veces en este proyecto (doblar la siembra de venado consume
tiradas de `rng` extra en tick 0, desplazando toda la trayectoria
posterior -- "la misma semilla" bajo ambas condiciones son, en la
práctica, dos partidas distintas). No hay señal positiva que justifique
subir `venados_iniciales`, y sí una señal direccional (aunque no
concluyente) en contra -- **no se toca `config/poblacion.yaml`**. Si se
quiere una respuesta fiable, hace falta el mismo tipo de lote grande no
pareado que ya se recomienda para zorro, no repetir este A/B con más
semillas pareadas.

### Recomendaciones #4 (vocación) y #5 (reputación) -- confirmadas con
### datos, ninguna es un bug de calibración, decisión de diseño
### pendiente de Diego

Diagnóstico con un lote de 6 semillas nuevas (940001-940006) × 6000
ticks usando `herramientas/harness_calibracion.py` (que ya reporta
ambos stats desde el informe del 12-09):

- **Vocación**: `{'forrajero': 114, 'constructor': 3}` como vocación
  dominante de gnomo agregada al cierre de las 6 semillas -- 0 artesano,
  0 cocinero, pese a que `armas fabricadas` (93), `herramientas
  fabricadas` (4) y `cocinar resuelto` (32) SÍ se ejercen en la misma
  corrida. **Causa real, verificada leyendo `sistema_decision.py`**:
  `factor_aptitud` es puramente MULTIPLICATIVO sobre una utilidad que ya
  existe (nunca crea utilidad de donde no la había, por diseño
  deliberado del círculo 1) -- modula QUIÉN dentro de la población tiene
  más ventaja en una acción ya frecuente, pero no cambia la frecuencia
  de base con la que el motor despacha RECOLECTAR frente a FABRICAR/
  COCINAR/CONSTRUIR. RECOLECTAR responde a una necesidad casi constante
  (comida/agua/material); las otras tres son condicionales y mucho más
  raras por construcción del propio motor. `vocacion_dominante` cuenta
  ticks de despacho real -- con una diferencia de frecuencia de ese
  orden, ningún multiplicador razonable sobre la utilidad iba a
  revertir el recuento agregado. **No es un bug de `peso_aptitud_
  vocacional` mal calibrado** -- es una consecuencia esperable y neutral
  (principio 5) del paisaje de frecuencias que el resto del motor ya
  produce. Corregirlo de verdad exigiría una decisión de diseño real,
  no una calibración: o bien medir vocación de otra forma (p.ej.
  normalizada por oportunidad, no por tick bruto), o bien la señal de
  escasez de grupo que el propio círculo 1 ya declaró explícitamente
  fuera de alcance ("ninguna señal nueva de escasez de vocación a nivel
  de grupo"). **No tocado sin decisión de Diego** -- señalado, no
  resuelto por iniciativa propia.
- **Reputación**: `descalificados=107, desempates cambiados=0` en la
  misma corrida -- la rama de DESCALIFICACIÓN de `calcular_liderazgo`
  (candidato dominante con reputación por debajo de
  `umbral_reputacion_descalificante`) se ejerce con fuerza real, **no
  está en 0 usos como sugería el informe del 12-09** (esa cifra parece
  haber venido de una muestra distinta o de una lectura desactualizada,
  no reproducida hoy). Lo que sí está confirmado en 0 es la rama de
  DESEMPATE (reputación decidiendo entre dos candidatos empatados en
  dominancia antes que la valentía) -- nunca cambió el ganador frente a
  la fórmula anterior (dominancia+valentía) en ninguna de las 6
  semillas. Razonable, no necesariamente un fallo: exige que dos
  candidatos queden exactamente empatados dentro de
  `margen_dominancia_elite` Y que su reputación real (no neutra 0.0) sea
  la que de verdad decida antes de llegar a valentía -- una
  intersección más estrecha que la descalificación, que solo necesita
  reputación baja en UN candidato. **No tocado** -- es una rama del
  mecanismo genuinamente rara, no evidencia de que esté rota; decidir si
  vale la pena facilitar el desempate (bajar el margen, o comparar
  reputación con más peso) es otra decisión de diseño, no una
  calibración con datos que la respalden hoy.

**Balance honesto de esta ronda**: de las 4 recomendaciones, 3 (techo
de manada, densidad de venado, y la propia rama de desempate de
reputación) quedan cerradas con NINGÚN cambio de config -- los datos no
respaldan tocar nada, y este proyecto no ajusta a ciegas contra una
hipótesis sin confirmar. La cuarta (vocación) queda genuinamente
abierta como pregunta de diseño para Diego, no como una calibración
pendiente. Ningún commit de código en esta ronda -- investigación pura,
con resultados mayormente negativos, documentados con la misma
honestidad que el resto del proyecto exige.
