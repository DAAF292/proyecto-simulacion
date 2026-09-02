# Historial de diseño — `nucleo/` (módulos pequeños)

Extraído de los comentarios en línea el 2026-09-02 (ver CLAUDE.md,
sección "Comentarios técnicos vs narrativa histórica"). Catálogo de los
módulos pequeños de `nucleo/` que no tienen su propio historial
dedicado (flora, celda y construcción sí lo tienen aparte).

## `reloj.py` — `DIAS_POR_ESTACION`

Calibración 2026-08-19, investigación "qué queremos: vidas largas o
ciclos cortos": comprimido de 20 a 5. Con este valor: TICKS_POR_ANIO =
24×5×4 = 480 (antes 1920). Madurez de gnomo (fracción_madurez=0.2 sobre
el mínimo racial de 45 años) pasa de 17280 a 4320 ticks; madurez de
lobo (mínimo racial 8 años) de 3072 a 768. Sigue siendo una ventana
grande frente a una corrida de calibración típica (600-800 ticks) pero
ya es alcanzable en corridas largas (10000-20000 ticks), que es lo que
esta calibración necesitaba.

## `bioma.py`

Fase terreno 3 del informe técnico, referencia Dwarf Fortress. Desde el
círculo 1 de generación causal (2026-08-27), la regla "temperatura muy
baja → Tundra" pasó a evaluarse ANTES que "elevación alta → Montaña":
con relieve orográfico real la temperatura de las cumbres cae por el
gradiente térmico, así que una cumbre fría es una cumbre nevada
(tundra de altura) -- la ley vieja asumía elevación-ruido sin
estructura y enterraba esta física. Corrección posterior, discutida y
confirmada con Diego (ver nucleo/celda.py): esta función solo decidía
el bioma; qué especies de flora viven dentro de cada uno es una
decisión completamente distinta.

## `fuego.py` / `componentes/fogata.py`

FUNDAMENTO (2026-08-31, ver componentes/agarre.py y conversación de
diseño con Diego: "usar dos rocas para hacer un fuego").

## `amenaza.py`

Surgió al conectar la huida del fuego (sistemas/sistema_desastres.py) y
detectar que implementarlo directamente en sistema_movimiento.py/
sistema_necesidades.py habría duplicado, con otro nombre, el mismo
patrón que nucleo/disposicion.py ya centralizó una vez.

## `campo_continuo.py`

Fase terreno 2 (elevación), reutilizado en fase terreno 3 (lluvia y
temperatura). Los algoritmos que ya existían en zona_bioma.py
(_generar_rio: paseo aleatorio; _generar_manchas: flood-fill
probabilístico) son ambos DISCRETOS, no sirven para una magnitud
continua. Value noise elegido sobre Perlin/Simplex/diamond-square por
ser la opción más simple que sigue dando resultados reales, coherente
con "no optimices por anticipación" y con que esto es una
implementación propia con fines de aprendizaje.

## `clima.py`

Informe técnico, secciones 7.1 y 7.2 -- diseñadas desde el principio
del proyecto, nunca implementadas hasta la sesión en que se escribió
este módulo. El efecto mecánico (estación+clima como modificador de
regeneración y objetivo de confort_termico) fue una decisión tomada en
esa misma pasada, no estaba en el informe técnico con este detalle --
le da a confort_termico su primer consumidor real (componentes/
necesidades.py lo declaraba desde su introducción explícitamente "sin
mecánica... depende del futuro sistema de clima y estaciones").

## `mundo.py` — `asentamientos`

2026-08-30, "el germen de un asentamiento" (ver nucleo/asentamiento.py
y sistemas/sistema_asentamiento.py).

## `inventario.py`

FUNDAMENTO de la fase de interacción física (2026-08-30, ver
componentes/inventario.py y conversación de diseño con Diego): "creo
que lo que importa es el peso, da igual cuantos materiales sean,
depende de tu capacidad física de portarlos".

## `relieve.py`

Diego señaló directamente: "la altitud no afecta en absoluto a las
criaturas" -- hasta esta corrección, elevación determinaba el bioma y
modulaba producción de flora pero no tenía ningún efecto sobre el
movimiento.

**RECALIBRADO 2026-08-29** (auditoría de funcionalidades, tercera
edición): la medición original de las pendientes (mediana ~0.032, p90
~0.10, p99 ~0.16, máximo ~0.21, 10 semillas) era anterior al círculo de
generación causal -- cordilleras, escorrentía, clima orográfico
(nucleo/orografia.py, 2026-08-27) -- que sustituyó el terreno de ruido
puro por uno estructurado. El relieve que se genera hoy es más suave de
lo que esa medición asumía: verificado que con la calibración antigua
un lobo (fuerza máxima) NUNCA se bloqueaba por pendiente (0% de los
pasos cuesta arriba), muy por debajo del ~p99 pretendido. Remedido
contra 15 semillas con el generador causal actual (mapa 40×40, 23177
subidas positivas muestreadas): mediana 0.0111, p87 0.0517, p99 0.1426,
máximo 0.2084 -- aproximadamente un tercio de la mediana anterior.
Recalibrado con el MISMO criterio de anclaje (resolviendo el sistema
lineal para que fuerza=0.2 caiga en p87 y fuerza=0.9 en p99 de la
distribución real de hoy), no un criterio nuevo. Sigue sin validarse
contra el harness completo -- el mismo hueco de antes, ahora sobre
números frescos en vez de desfasados.

`pendiente_maxima_transitable` (2026-08-23): firma corregida -- recibía
un dict `config_relieve`, pero su único consumidor
(sistema_movimiento.py) ya la llamaba con pendiente_minima/maxima_
transitable sueltos, mismo desfase función/llamador que
radio_individual() en nucleo/percepcion.py, mismo criterio de arreglo
(ajustar la función al único sitio que la usa).

## `ciclo_vital.py` — `probabilidad_muerte_vejez`

**HUECO DETECTADO Y RELLENADO el 2026-08-23**, no recuperado de commit
anterior: a diferencia de nacer_criatura (que sí existió y se pudo
reconstruir desde el historial de git), esta función se referenciaba
desde sistemas/sistema_ciclo_vital.py (import roto) sin que existiera
en NINGÚN commit de todo el historial del proyecto -- confirmado
buscando en `git log --all -p`. No es una pérdida por colisión de
ediciones concurrentes como nacer_criatura: sencillamente nunca se
escribió.

**RECALIBRADA EL MISMO DÍA, más tarde**: la primera versión (techo=0.3,
exponente=2 fijo) se probó contra el motor en marcha por primera vez al
validar el cambio de tamaño de grid y resultó catastrófica -- 55-76% de
TODAS las muertes en un barrido de 5 semillas × 6000 ticks,
extinguiendo la población entera en 1000-2000 ticks, muy por delante de
cualquier dinámica de densidad o depredación. La causa: con ratio al
cuadrado, un individuo a mitad de su longevidad individual (ratio=0.5)
ya cargaba una probabilidad diaria de 0.3×0.25=7.5% -- una esperanza de
vida restante de apenas ~13 días útiles, para un individuo que en
teoría llevaba solo la mitad de su vida. Corregido en dos frentes: el
techo baja a un valor muy inferior (sigue PROVISIONAL) y el exponente
sube de 2 a un valor configurable (por defecto 8) para que la curva se
aplane mucho más tiempo y solo se dispare cerca del verdadero final de
vida -- criterio de realismo señalado por Diego para este tipo de
decisión. Sigue sin ser una calibración cerrada: ajustada contra un
barrido ligero de 5 semillas, no el harness completo de 15 semillas ×
12000 ticks.

## `conflicto.py`

FUNDAMENTO (2026-08-30, ver conversación de diseño con Diego: "esto
debe ser reutilizable a futuro... que un individuo robe a otro, un
agravio del tipo que sea").

## `percepcion.py`

Hasta este cambio, un único entero uniforme entre especies
(config.percepcion.radio_celdas), consultado directamente por tres
sistemas. componentes/dimensiones_fisicas.py ya declaraba
agudeza_sensorial con este enganche identificado con precisión,
deliberadamente sin conectar -- "sustituir un radio global por uno
individual tocaría tres sistemas a la vez". Diego pidió afrontar esa
deuda ahora en vez de dejarla acumular más tiempo.

Calibración de los bordes [radio_minimo_celdas, radio_maximo_celdas]:
un primer intento ([1, 4], punto medio 2.5, cerca del único valor ya
calibrado antes de este cambio, 2) resultó tener un fallo real: el
rango entero de lobo caía siempre en el mismo entero redondeado, es
decir CERO variación individual dentro de esa especie -- justo lo que
se quería evitar al conectar el enganche. Los bordes finales, [0, 4],
preservan la asimetría esperada entre especies Y variación individual
real dentro de cada una, con el promedio global todavía cerca del viejo
valor único (2).

`radio_individual` (2026-08-23): firma corregida -- recibía un dict
`config_percepcion`, pero AMBOS consumidores (sistema_movimiento.py,
sistema_capacidad_mental.py) la llamaban ya con radio_min/radio_max
sueltos, mismo criterio de arreglo que pendiente_maxima_transitable.

`radio_efectivo_por_peso` (2026-08-23, pregunta de Diego: "no debería
ser igual de fácil detectar a una mosca que a un gnomo"). Verificado
con el mismo barrido de calibración ligera que el resto de piezas de
esa sesión.

## `disposicion.py`

Informe técnico, secciones 8.1 y 8.2 -- capa racial fija del modelo de
disposición en tres capas. El campo se llamaba `tamano` en el
prototipo original; renombrado a DimensionesFisicas.peso en el Bloque B
del plan de migración a criatura.docx, sin cambiar la fórmula ni los
rangos numéricos.

`contar_conspecificos_cercanos` -- GREGARISMO, Pieza 1 (2026-08-30,
confirmado por Diego: "me parece bien si", tras plantear la
preocupación de que el lobo necesitaba comportamiento de manada real).
Diego fue explícito en que cualquier especie con sociabilidad
suficiente debería beneficiarse igual -- restringir esto a lobo habría
sido autoría de guion, no ley (principios 1 y 5 de CLAUDE.md).

## `territorio.py`

RECONSTRUIDO (2026-08-23): esta clase se quedó congelada en su forma de
Fase 0 (`__init__(nombre, zonas_bioma)`, recibiendo una lista de zonas
ya construidas por quien la llamaba) mientras nucleo/mundo.py
evolucionó para llamarla con `Territorio(ancho, alto, config, rng)`,
esperando que fuera ELLA quien generase su propia zona -- ningún commit
del historial actualizó territorio.py para seguirle el paso a mundo.py.
Todos los sistemas consumidores ya esperaban un atributo `zonas`
(lista), no el `zonas_bioma` original -- se corrigió ahí también.

`AccesoSubterraneo` -- Círculo 3 de profundidad (2026-08-30, ver
CLAUDE.md): generaliza el par único acceso_subterraneo/entrada_cueva
del Círculo 1/2 a una lista, para soportar varias cuevas por mundo.

Varias cuevas por mundo -- corrección de diseño de Diego sobre el
diseño original de Círculo 1-2 (una única zona subterránea anclada bajo
montaña con depósito mineral): "las cuevas no deberían aparecer solo en
un bioma, son formaciones naturales que no siguen esas normas...
deberían generarse por todo el mapa" y "para que se use la cueva no es
algo que debamos definir nosotros" -- leyes neutras, principio 5, nunca
un guion de "esta cueva es para lobos, esta para gnomos".

## `orografia.py`

Círculo 1, acordado con Diego tras el diagnóstico visual del
2026-08-27. Antes: tres campos de value noise independientes
(elevación, lluvia, temperatura) sin relación causal -- ríos nacían en
bultos de ruido, el clima ignoraba el relieve y los biomas salían en
mosaico sin fundamento.

## `asentamiento.py`

FUNDAMENTO de "el germen de un asentamiento" (2026-08-30, ver
conversación de diseño con Diego y CLAUDE.md).

`Asentamiento.zona_idx` -- Círculo 3 de profundidad (2026-08-30,
hallazgo propio al revisar el motor tras varias cuevas): un asentamiento
no puede tener miembros en zonas distintas.

`calcular_liderazgo`: conversación de diseño con Diego -- "no creamos
leyes absolutas". Reutiliza Temperamento.dominancia, el mismo atributo
que su propio docstring ya señalaba desde hace tiempo como "espera el
cálculo de liderazgo de un asentamiento".

`almacen_cercano` -- Círculo 3 de profundidad, hallazgo propio: sin el
filtro por zona_idx, un almacén en una cueva y otro en superficie (o en
otra cueva) con coordenadas numéricamente cercanas se confundían entre
sí -- ya no es un caso hipotético con varias cuevas por mundo
compartiendo rangos de coordenadas pequeños.

`disposicion_a_aportar`: conversación de diseño con Diego -- "¿un ser
dominante y agresivo aportaría lo mismo que uno que no lo sea?... creo
que es la agresividad, porque puedes ser un líder dominante y empático
que aporte" -- de ahí que dominancia quede deliberadamente fuera de
esta fórmula (decide quién lidera, no si acapara o comparte).

## `cueva.py`

Círculo 2 de profundidad (2026-08-30, ver CLAUDE.md y conversación de
diseño con Diego). El Círculo 1 probó el mecanismo multi-zona con una
zona de PRUEBA que reutilizaba tal cual el generador orográfico causal
de la superficie -- sustituido aquí porque una cueva no tiene sentido
físico bajo tierra con viento dominante o lluvia propia.

Algoritmo (autómata celular) confirmado con Diego sobre la alternativa
de habitaciones+pasillos.

Vetas en el suelo, no en las paredes: Diego confirmó vetas finitas
(masa_mineral_restante).

## `materiales.py`

Círculo de vetas de mineral (2026-08-30, ver config/materiales.yaml y
conversación de diseño con Diego).

Dos formas de veta, elegidas al azar por veta individual -- Diego: "por
qué tenemos que utilizar un solo sistema? no podemos usar ambos
indistintamente? eso le dará más variedad".

`componentes_conexas` promovida a nombre público el 2026-08-30 (Círculo
2 de profundidad) cuando nucleo/cueva.py empezó a reutilizarla.

Bug real, encontrado antes de ejecutar nada: catalogo_materiales y
config_generacion_vetas se recibían en un único dict con ambos
anidados, cuando config/materiales.yaml los declara como dos claves de
nivel superior distintas.

"FORMA POR ENCIMA DE EXACTITUD NUMÉRICA": hallazgo real de Diego --
"esas no leen como veta de ninguna forma... es precisamente lo
contrario de lo que buscabas". Un primer intento del filtro de tamaño
mínimo por veta medía solo el total agregado y dejaba pasar celdas
sueltas de 1×1 escondidas dentro de un resultado que sí sumaba lo
suficiente en conjunto -- corregido a filtrar por componente conexa
real, fragmento a fragmento.

`elegir_sustrato_celda` -- 2026-09-01, ver docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md: antes de esto,
sustrato_por_bioma era 1 material fijo por bioma entero, sin ninguna
variación interna.

## `entidad.py`

`_sortear_edad_inicial_ticks`: diagnóstico que motivó esto (2026-08-21,
investigación "cero adultos coexistiendo" en gnomo) -- con
techo_fraccion=0.0 (comportamiento previo, implícito), TODOS los
fundadores de una especie nacían en tick=0 como recién nacidos
simultáneos. Para una especie de maduración lenta (gnomo,
fraccion_madurez=0.1 sobre ~45 años de longevidad mínima ≈ 4.5 años ≈
2160 ticks) eso significaba que, hasta ese primer umbral de madurez, la
población entera era infantil a la vez -- cero parejas fértiles
posibles durante miles de ticks, y para cuando maduraban, las pérdidas
por depredación/inanición ya podían haber diezmado la cohorte. No era
un fallo de la regla de madurez (es neutra, correcta); era que la
generación de la población fundadora no reflejaba una demografía real.

`componer_necromasa`: Círculo 2 de materiales físicos (2026-08-30).
Consolida lo que antes eran CUATRO copias del mismo cálculo "peso *
0.35 / peso * 0.65" repetidas sin config detrás en
sistema_necesidades.py, sistema_ciclo_vital.py, sistema_depredacion.py
y (con sus propias fracciones) sistema_desastres.py.

`_heredar_valor`: recuperada de commit `249793e` ("commit 2",
2026-08-20), perdida en el refactor posterior de necromasa/pipeline
trifásico (`2140243`) sin que mediara ningún commit intermedio que la
protegiera. Informe técnico, 6.3, literal: "herencia de atributos,
promedio de progenitores + mutación, acotado al rango racial".

`nacer_criatura`: RECONSTRUIDA (2026-08-23) -- existió con este mismo
propósito en el commit `249793e`, se perdió en el mismo refactor de
necromasa/pipeline trifásico (`2140243`) que reescribió
nucleo/entidad.py desde una base anterior sin que hubiera un commit
intermedio con este trabajo. Esta versión NO es una copia literal de
aquella: se adapta a las convenciones que crear_criatura ya usa hoy
(config con 'rangos_raciales' en vez de rangos_raciales suelto donde
aplica, Identidad con nombre/id_madre/id_padre, PoolFisico/PoolMental
inicializados a los escalares del propio individuo en vez de a sus
valores por defecto, Intencion con accion=DEAMBULAR explícito) para no
reintroducir una fábrica que diverja en estilo de la que ya existe.

## `agua.py`

CORRECCIÓN de diseño (discutida y confirmada con Diego, posterior a la
corrección biomas/especies): el generador anterior (`_generar_rio`,
retirado de nucleo/zona_bioma.py) trazaba un único camino de una celda
de ancho, de un borde del grid al opuesto, por PASEO ALEATORIO -- ciego
por completo al terreno, no consultaba elevación/lluvia/temperatura/
bioma en ningún momento. Un río podía cruzar una Montaña en línea recta
con la misma probabilidad que cruzar una Pradera. Tampoco existían
lagos ni pozas -- un único tipo de cuerpo de agua, siempre exactamente
uno por mundo.

CORRECCIÓN DE DISEÑO 2026-08-21 (Diego, tras el hueco señalado con
`profundidad_maxima_metros_poza` -- "estás creando normas específicas
para las razas creadas, y si añadimos animales más pequeños aún?"): la
versión anterior de este módulo tenía un techo de metros DISTINTO por
tipo de cuerpo de agua (profundidad_maxima_metros_lago=3.0,
profundidad_maxima_metros_poza=0.5), cada uno "elegido por magnitud
relativa frente a los rangos raciales de altura" de las especies que
existían en ese momento -- una ley teleológica disfrazada de dato de
terreno: el mapa "sabía" a quién quería ahogar. Rompió en cuanto
aparecieron conejo/ardilla (altura por debajo del techo de poza que
prometía "nunca ahoga a nadie"), y habría vuelto a romper con la
próxima especie más pequeña que la anterior, sea cual sea.

Río -- ANTES la excepción deliberada (profundidad_metros_rio, un único
valor fijo para todo el cauce, sin gradiente de orilla ni variación a
lo largo del río -- "un río no es una cuenca"). CORRECCIÓN 2026-08-21
(Diego: "lo que hay que hacer respecto a los ríos es darles un
gradiente a las orillas, igual que a los lagos y a las pozas, la
profundidad deberá variar dependiendo del terreno"). No hay ninguna
banda_elevacion_rio en la config, porque no hace falta inventar una: el
propio camino de descenso ya la da.

`_trazar_rio`, coste_giro (2026-08-28): corrige un meandro sinusoidal
artificial ("codorniz", capturas de Diego contra el visor real) que un
descenso por mínimo puro sin memoria producía en valles anchos y casi
planos.

`_flood_fill_banda`: corrección de docstring 2026-08-29 -- decía "BFS"
y usaba frontera.pop(); en realidad es LIFO (expansión en profundidad).
Sin el tope de tamaño, una cuenca poco profunda sobre un campo de value
noise podría devorar fácilmente cualquier ondulación cercana (mismo
riesgo señalado antes de implementar: "podríamos acabar con charcos
por todo el mapa").

`pendiente_local` -- deliberadamente NO es un campo de Celda (Diego,
2026-08-30: "¿pendiente local no es necesario? ¿ese dato no es ya
determinista?").

## `celda_percibida` (ahora en `percepcion.py`)

Promovida desde sistema_movimiento.py (donde nació como
`_celda_percibida`, privada, para comida y agua) a este módulo: fase
terreno-huida-de-amenazas, cuando nucleo/amenaza.py necesitó el mismo
patrón de búsqueda para "celda peligrosa más cercana" y duplicarlo
habría sido exactamente el riesgo que nucleo/disposicion.py ya señaló
en su propio docstring -- que las distintas nociones de "qué cuenta
como cerca" diverjan con el tiempo.
