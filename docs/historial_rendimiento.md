# Historial — Rendimiento del motor

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

## Índice espacial compartido -- escalabilidad del motor, Círculos 1+2
## cerrados, implementado directamente por Claude (2026-09-08, mismo día)

Diego, tras ver que la explosión de conejo (sección anterior) seguía
dándose, preguntó directamente: "me empieza a preocupar la eficiencia,
¿cómo vamos a hacer cuando existan muchas más funcionalidades
simultáneamente y además más fauna, flora, razas, etc? ¿es viable?".
Tratado como spike (brainstorming): perfilado real con `cProfile` sobre
la misma semilla en dos escalas de población de la misma partida --
población x2.2 → tiempo x3.1, peor que lineal. Causa real localizada,
no supuesta: 60-65% del tiempo de tick en
`nucleo/amenaza.py:posicion_amenaza_mas_cercana` →
`nucleo/disposicion.py:posicion_mas_cercana_por_disposicion`, llamada
una vez por entidad por tick, escaneando `gestor.entidades_con(...)` --
la población mundial entera -- en cada llamada. Mismo patrón repetido a
menor escala en `nucleo/construccion.py`, `nucleo/madriguera.py`,
`nucleo/fuego.py`, `nucleo/asentamiento.py:almacen_cercano` -- el mismo
defecto que `_buscar_conspecifico_mas_cercano` ya documentaba como
O(N²) desde hace semanas, resultó ser un patrón repetido en casi todos
los sistemas de "percepción de algo cercano" añadidos esta semana
(manada, madriguera, salón común, sonido).

**Decisiones cerradas con Diego, brainstorming arquitectónico** (spec:
`docs/superpowers/specs/2026-09-08-indice-espacial-design.md`): (1)
alcance BARRIDO COMPLETO, no solo el mayor contribuyente; (2) índice
"congelado" (se reconstruye una vez por fase relevante, no se mantiene
sincronizado incrementalmente) -- corrige de paso un artefacto de orden
real y nunca diseñado a propósito: dentro del bucle de
`sistema_movimiento.py`, una entidad procesada más tarde podía ver la
posición YA movida de otra procesada antes en el mismo tick (quien
tiene id más bajo se movía "primero"). Centinela del pipeline
confirmado parado (sin reiniciar desde el incidente de madriguera-
física-A) y con 3 fallos consecutivos previos en piezas de tamaño
similar -- Diego eligió explícitamente que Claude implementara
directamente esta pieza, dada su sensibilidad a errores silenciosos de
enhebrado.

**Arquitectura**: `nucleo/indice_espacial.py` (nuevo) -- `IndiceEspacial`
agrupa TODAS las entidades con `Posicion` por `(x, y, zona_idx)` (sin
filtrar por ningún otro componente, cada consumidor sigue filtrando el
suyo después, igual que antes); `en_celda`/`en_radio` (recorre solo las
celdas del rombo Manhattan, nunca la población entera). `main.py:
ejecutar_tick` construye dos índices por tick, no uno por entidad --
Índice A (antes de decisión/movimiento, refleja el cierre del tick
anterior) e Índice B (tras movimiento, para depredación/necesidades/
reproducción). Sistemas de cadencia diaria (`asentamiento`, `manada`)
construyen el suyo propio localmente. Parámetro `indice=None` opcional
en todas partes, con fallback interno (mismo patrón ya usado por
`por_celda: dict | None = None` en `sistema_movimiento.py`) -- **cero
cambios necesarios en la batería de tests existente**.

**Círculo 1** (el 60-65% del coste medido): `nucleo/disposicion.py` (las
3 funciones), `nucleo/amenaza.py` (propaga el índice), y las firmas de
`SistemaDecision`/`SistemaMovimiento`/`SistemaDepredacion`/
`SistemaNecesidades`/`SistemaReproduccion`. **Encontrado durante la
propia implementación, no anticipado en el spec, y migrado también por
ser el mismo patrón exacto con el índice ya a mano**:
`sistema_movimiento.py:_calcular_pareja`,
`_buscar_conspecifico_mas_cercano` (el O(N²) más antiguo y más citado
de todo el proyecto, documentado como límite conocido desde la
migración original del 24-08) y el bucle de detección de presa de
`_calcular_caza` -- ninguno pasaba por `nucleo/disposicion.py`, cada
uno hacía su propio escaneo lineal ad-hoc.

**Círculo 2** (extender el mismo índice): `nucleo/construccion.py`
(`construccion_propia`, `hay_construccion_de_tipo_en`),
`nucleo/madriguera.py`, `nucleo/fuego.py`, `nucleo/asentamiento.py:
almacen_cercano`, propagado a través de `objetivo_construccion_actual`
(la cadena refugio→almacén→salón común) y de los cuatro bonos de
confort/seguridad en `SistemaNecesidades`.

**Verificado, con cifras reales, no solo "los tests pasan"**: 375/375
tests (7 nuevos, `tests/test_indice_espacial.py`), `BOSQUE_AUTO_TICKS=3000`
sin excepciones. Perfilado repetido con el mismo arnés, misma semilla
60004, antes/después:

| | Población | ms/tick |
|---|---|---|
| Antes | 93 → 208 (x2.2) | 102 → 319 (x3.1) |
| Después | 92 → 185 (x2.0) | 69 → 173 (x2.5) |

Mejora real en dos ejes distintos: velocidad absoluta (32-45% más
rápido según la escala) Y el propio EXPONENTE de escalado (factor
tiempo baja de x3.1 a x2.5 -- más cerca de lineal, no solo una
constante más rápida). `hay_construccion_de_tipo_en`, `madriguera_en` y
`posicion_mas_cercana_por_disposicion` dejan de aparecer entre los
costes dominantes del perfil tras el fix.

**Honestidad explícita sobre lo que queda fuera de estos dos círculos,
encontrado durante la propia implementación (perfilado repetido tras
el Círculo 2)**: `nucleo/sonido.py:sonido_mas_cercano` sigue siendo un
coste real y ahora más visible relativamente (su límite es O(radio²)
celdas por llamada, no O(N) entidades -- explícitamente fuera de
alcance del spec, un índice de entidades no lo resuelve).
`sistema_movimiento.py` conserva más funciones con el MISMO patrón de
escaneo ad-hoc sin pasar por `nucleo/disposicion.py` que no se
migraron en este círculo por no formar parte del alcance acordado con
Diego (barrido de los consumidores YA identificados, no de cualquier
`entidades_con(...)` del fichero): `_entidad_cercana_cualquiera`/
`_entidad_cercana_cualquiera_con_id`/`_consciente_mas_cercano_con_id`
(ya señaladas como código casi duplicado en la auditoría post-cierre
del arco de comunicación, 2026-09-07), la búsqueda de carroñeo por
Necromasa, "presenciar una muerte" (trauma), y el intruso de
`_resolver_posible_intruso`. Confirmado en el perfil final:
`_entidad_cercana_cualquiera` ya es visible (0.50→1.17s entre las dos
escalas) -- candidato real y concreto para un **Círculo 3**, mismo
patrón exacto, mismo índice ya construido, sin decisión de diseño
nueva que tomar.

**Pendiente real, explícito**: Círculo 3 (arriba) sin decidir si se
aborda; el propio harness completo (15×12000) seguiría siendo la
referencia de rigor para cualquier calibración numérica, sin relación
con esta pieza (esta es una corrección de rendimiento, no de
comportamiento -- ningún valor de config se tocó). El índice se
reconstruye completo dos veces por tick (O(N) cada vez) -- suficiente
para la escala actual; si el número de entidades sube en órdenes de
magnitud en el futuro, la siguiente palanca sería mantenerlo
incremental en vez de reconstruirlo, no evaluada aquí por no hacer
falta todavía.

### Círculo 3 -- el resto del motor, mismo día, a petición explícita de
### Diego ("yo lo arreglaría ahora para dejar el motor lo más eficiente
### posible y sin deuda técnica")

Sin decisión de diseño nueva -- mismo índice ya construido, mismo
patrón exacto, aplicado al resto de funciones de
`sistema_movimiento.py` que hacían su propio escaneo O(N) ad-hoc sin
pasar nunca por `nucleo/disposicion.py`: `_entidad_cercana_cualquiera`,
`_entidad_cercana_cualquiera_con_id`, `_consciente_mas_cercano_con_id`
(HUIDA_ERRATICA, CRISIS_VIOLENTA, SOCIALIZAR), `_clasificar_destino_sonido`
(presa y necromasa, solo observación), `_calcular_forrajeo` (necromasa),
`_resolver_posible_intruso` (conflicto por refugio ocupado). También
`sistema_recursos.py:_resolver_comer` (carroñeo de Necromasa) -- este
sí necesitó enhebrar el parámetro por primera vez en `SistemaRecursos`
(no lo tenía desde el Círculo 1/2 por no hacer falta hasta ahora),
recibiendo el Índice B desde `main.py`.

**Barrido de verificación explícito, no solo "arreglé lo que ya sabía"**:
un `grep` de todos los `entidades_con(...)` restantes en `sistemas/`
confirmó que el resto son bucles de despacho por entidad o por día
(necesariamente O(N) -- un sistema tiene que visitar cada entidad una
vez para procesarla, eso no es el defecto) o mantenimiento completo
(`sistema_recursos.py:_consumir_fogatas`, decae TODA fogata cada tick
con independencia de dónde esté nadie) -- ninguno es una búsqueda de
"más cercano" sin resolver. `sistema_capacidad_mental.py` (penalización
por presenciar muerte) se revisó y se descartó explícitamente: compara
cada entidad contra la lista de muertes DE ESTE TICK (típicamente 0-3),
no contra la población -- O(N × muertes_del_tick), no el mismo defecto.

**Verificado**: 375/375 tests en verde (sin tests nuevos -- refactor de
rendimiento puro sobre funciones ya cubiertas), `BOSQUE_AUTO_TICKS=3000`
sin excepciones. Perfilado repetido una vez más, mismo arnés: a la
población de referencia estable (~92, escala 1 en las tres rondas),
ms/tick sigue bajando -- 102 (antes de tocar nada) → 76 (Círculo 1) →
69 (Círculo 1+2) → 65 (Círculo 1+2+3). **Limitación honesta de la
escala 2 de este arnés**: al avanzar un número fijo de ticks con un
límite de tiempo real, un motor más rápido recorre más ticks (y por
tanto llega a una población MAYOR) en la misma ventana de 150s -- la
población de la escala 2 no es la misma entre rondas (208 → 237 → 185 →
279), así que comparar el "factor tiempo" de una ronda a otra no es
una medición limpia. La comparación que SÍ es limpia y favorable:
contra el baseline original sin ningún fix (208 población → 319
ms/tick), esta ronda final procesa MÁS población (279) en MENOS tiempo
por tick (247 ms) -- más entidades, más rápido, sin ambigüedad.

Con esto, la investigación de eficiencia iniciada por la pregunta de
Diego ("¿es viable?") queda cerrada del todo por ahora -- los tres
círculos cubren todo patrón de escaneo O(N) por entidad identificado
en el motor, dejando solo `nucleo/sonido.py:sonido_mas_cercano`
(O(radio²) por celda, un defecto de naturaleza distinta, no resuelto
por un índice de entidades) como coste real conocido y sin tocar,
documentado explícitamente en el spec como fuera de alcance.

### Círculo 4 -- registro de sonidos activos, mismo día, a petición
### explícita de Diego ("como solucionamos eso")

`nucleo/sonido.py:sonido_mas_cercano` escaneaba un cuadrado de
`radio_busqueda_maxima²` celdas por llamada preguntando "¿hay sonido
aquí?" -- la inmensa mayoría vacías, dado que un sonido dura solo
`duracion_sonido_ticks` (5 por defecto). No era el mismo defecto que
los Círculos 1-3 (no escala con la población, escala con el radio de
búsqueda, constante), pero seguía siendo trabajo desperdiciado real.
Bounded (per la skill de brainstorming), sin spec aparte -- mismo
espíritu del índice espacial: sustituir "recorrer todo el espacio de
búsqueda" por "recorrer solo lo que puede tener respuesta".

**Diseño**: `ZonaBioma.sonidos_activos: set[tuple[int,int]]` (nuevo) --
registro de coordenadas que tuvieron un sonido emitido y podrían seguir
activas. `Celda.sonido_tick_emitido`/`sonido_magnitud` siguen siendo la
fuente real del dato (sin duplicar tick/magnitud en dos sitios); el set
solo dice DÓNDE mirar. `emitir_sonido` cambia de firma
(`celda`) → (`zona, pos_x, pos_y`) para poder registrar la coordenada
-- dos call sites reales (`sistema_movimiento.py`,
`sistema_depredacion.py`) y varios tests con la firma vieja
actualizados. `sonido_mas_cercano` recorre `zona.sonidos_activos` en
vez del cuadrado de celdas, **auto-podándose**: una entrada expirada se
descarta la primera vez que se encuentra en cualquier consulta, sin
necesitar un barrido de limpieza aparte -- el registro se mantiene
pequeño solo. Mismo techo de escaneo (`radio_busqueda_maxima`) que
antes, comportamiento idéntico verificado con los contadores exactos
de `BOSQUE_AUTO_TICKS` (147 sonidos, 1702 amenazas por sonido, 1
fallback de caza -- mismos números que antes del fix).

**Verificado**: 375/375 tests, perfilado repetido con el mismo arnés --
a población 92 (escala estable de las cuatro rondas), ms/tick sigue
bajando: 65 → **37**. A población 279 (coincide exactamente con la
medición anterior, comparación limpia sin el sesgo de muestreo ya
señalado): 247 → **149** ms/tick. `sonido_mas_cercano`/`_sonido_activo`
dejan de aparecer entre los costes dominantes del perfil.

**Balance acumulado del día completo** (Círculos 1-4, misma población
de referencia ~92-93): 102 → 76 → 69 → 65 → **37 ms/tick** -- una
reducción del 64% desde el punto de partida, sin cambiar ningún
comportamiento del motor (solo rendimiento). Con esto, no queda ningún
coste de escaneo conocido y sin abordar en el motor.

### Círculo 5 -- registro de celdas en llamas, mismo día, y un bug real
### de orden encontrado y corregido antes de comitear

Mismo patrón exacto que sonidos_activos, aplicado esta vez a
`sistema_desastres.py:procesar_fuego_tick`, que escaneaba TODA la
cuadrícula de CADA zona, CADA tick, solo para encontrar qué celda
seguía ardiendo -- trabajo desperdiciado casi siempre (el fuego es un
evento raro). `ZonaBioma.celdas_en_llamas` (set de coordenadas)
sustituye el escaneo, sincronizado en los tres puntos donde
`en_llamas` muta (ignición diaria, propagación y extinción por tick).
A diferencia de sonido, **esto SÍ se persiste** (`en_llamas` sobrevive
a guardar/cargar) -- `nucleo/persistencia.py` repuebla el registro al
cargar una partida.

**Hallazgo real, encontrado por el propio proceso de verificación de
este proyecto, no después de comitear**: la primera versión iteraba
`zona.celdas_en_llamas` (un `set`, sin orden de iteración garantizado)
directamente. `BOSQUE_AUTO_TICKS=3000` con la misma semilla dio
contadores DISTINTOS al run anterior (552 sonidos frente a 147,
distintas muertes de gnomo) -- señal inmediata de que algo divergía.
Causa: el orden en que se procesan los focos de fuego determina el
orden en que se consumen tiradas de `rng.random()` (extinción/
propagación); con un orden distinto al escaneo (y, x) que sustituía,
toda la secuencia de aleatoriedad posterior del tick se desviaba --
mismo fenómeno de "cambiar cuántas/en qué orden se llama a rng
desplaza todo lo demás" ya documentado varias veces en este proyecto
(Sobrepoblación..., rng_reproduccion). Corregido ordenando el registro
`sorted(..., key=lambda c: (c[1], c[0]))` antes de procesarlo --
reverificado con **los mismos contadores exactos** que antes del
cambio (147 sonidos, 1702 amenaza por sonido, 5+5 muertes de gnomo).

**Verificado**: 380/380 tests (5 nuevos,
`tests/test_incendio_registro.py` -- sincronización en ignición/
extinción/propagación, no-op sin fuego, roundtrip de persistencia).
Ganancia de rendimiento marginal a la escala del mundo por defecto
(pocos incendios reales), pero corrige una fuente de coste FIJO por
tick que no dependía de población y que crecería con más zonas/cuevas.

### Análisis final -- perfilado del juego real (con persistencia SQLite
### incluida, no solo el arnés aislado), tres hallazgos más, ninguno
### perseguido por decisión de Diego

Pedido explícito de Diego: "analiza si hay algo más que podamos hacer
para agilizar o mejorar el motor". Perfilado con `cProfile` sobre
`main.main()` real (800 ticks, semilla por defecto, persistencia
real) en vez del arnés sin persistir -- reveló tres costes reales de
naturaleza distinta a los ya corregidos, ninguno un "defecto" limpio:

1. **`sistema_recursos.py:_actualizar_charcos`** (~16% del tiempo del
   tick): escanea la cuadrícula entera de cada zona cada tick para
   charcos/humedad de subsuelo. A diferencia de sonido/fuego, la
   lluvia afecta potencialmente a TODO el mapa -- en los ticks con
   lluvia el escaneo completo es necesario de verdad, no desperdiciado.
   Una optimización parcial (registro de celdas con agua residual para
   saltar el escaneo en ticks SIN lluvia) es posible pero de beneficio
   parcial y con el mismo riesgo de bug de orden ya visto en el
   Círculo 5.
2. **`sqlite3.Connection.commit`** (~8.5% del tiempo total): un commit
   real a disco por tick. Reducirlo (agrupar varios ticks por commit)
   ahorraría tiempo real a cambio de aceptar perder más progreso si el
   proceso muere a mitad de partida -- decisión de diseño de
   durabilidad, no un bug de rendimiento a corregir sin más.
3. **`sistema_movimiento.py:_calcular_pareja`** sigue siendo caro, pero
   ya usa el índice espacial -- el coste restante es proporcional a la
   densidad LOCAL dentro del radio de búsqueda de pareja (recalibrado
   hace poco a 3-12 celdas), no a la población global. Esperable, no
   un defecto.

**Decisión de Diego, dado el riesgo/beneficio de cada uno**: no
perseguir ninguno de los tres ahora ("los tres cambios grandes de hoy
ya cubrieron los defectos claros -- estos son trade-offs o mejoras
marginales con riesgo real, no defectos obvios"). Quedan documentados
aquí como candidatos reales para una sesión futura de rendimiento, no
como pendientes urgentes.
## Informe de calibracion -- primer harness completo de 7 especies, y
## arco de rendimiento -- tres paquetes verificados byte a byte (2026-09-12,
## misma tarde, con 20 nucleos reales por primera vez desde el 09-09)

Diego pidio lanzar la prueba de referencia ("ver que todos los mecanismos
salten en el mundo real y el estado real de las criaturas") y luego, con el
informe en mano, attackar el rendimiento primero.

### Harness desactualizado -- corrigido antes de lanzar

`herramientas/harness_calibracion.py` seguia en el estado de 5 especies
(sin venado/cabra_montesa, commit `c7f0504`): ESPECIES a 7; criterio
maestro en DOBLE version (5 originales para comparar contra toda la
historia de CLAUDE.md, y 7 del catalogo completo); contadores nuevos de
armas/herramientas fabricadas (eventos `ArmaFabricada`/`HerramientaFabricada`),
robo de material y de arma, cohesive de manada fallback caza, sonido caza
fallback, gate de manos libres, lealtad, vocaciones dominantes
(nucleo.vocacion:vocacion_dominante leida al cierre), decaimiento de
vinculos, material descartado, cupo de madriguera, reputacion (globals de
nucleo/asentamiento) y sonidos (nucleo/sonido:SONIDOS_EMITIDOS_TOTALES,
reset por semilla en cada worker).

**Resultado, 15 semillas nuevas (1000001-1000015), todas cortadas por la
salvaguarda de 3600s a 7202-10704 ticks** (12000 sigue sin completarse
nunca): gnomo 0/15 y caballo 0/15 de extincion (resueltas de verdad),
venado/cabra_montesa 27% c/u (nuevas, tooltip sano 89-91%), **lobo 60%,
conejo 60%, ardilla 53%**, criterio maestro 5 especies 7% y 7 especies 0%.
El total social se ejerce con fuerza real por primera vez a esta escala:
135 parejas estables en 14/15 semillas (masivamente forrajero 231 vs
constructor 12, sin artesanos/cocineros), salon comun 9/15 (antes 0),
armas 299, herramientas 20, robos 535+636+37, cocinar 199. Conejo boom-bust
sincronico (283->0; 3.321 muertes por vejez) y lobo con embudo reproductivo
ACTIVO (2-6 concepciones -> 6-19 nacimientos) pero columnut a 0 por
desgaste de adultos (130 por vejez + 117 por vejez... inanicion 130 y
vejez 117 agregadas): el hueco es ecologico, no calibracion -- no hay
ninguna ley natural que regule presa pequena (lobo no vive de conejo por
ratio de saciedad). Caballo sigue en 0 depredaciones en las 15; sonido
emitido reporta 0 (global de nucleo/sonido.py al parecer no se incrementa
en alguna via real -- credibilidad sospechosa, no verificado, candidato a
revisar). Informe completo entregado a Diego en conversacion con
soluciones priorizadas; Decision de Diego: atacar rendimiento primero
(calibrar contra ventanas truncadas es la leccion repetida del proyecto).

### Rendimiento -- perfilado real y tres paquetes

Perfilado con cProfile sobre main.py real (700 ticks, 108 entidades,
persistencia real, con el contenedor sin 20 procesos compitiendo): **el
cuadro del 08-09 habia caducado**. Mayor coste individual: obtener_
componente ~30% (23.8M llamadas; el 29% de todas ellas de UNA funcion,
_calcular_pareja), _actualizar_charcos ~18% (la mayor parte es pendiente_
local recalculada cada tick), _calcular_pareja ~15%. SQLite: ya no aparece
en el top-25 (el dato del 8.5% del 08-09 quedo obsoleto con el motor
crescido). `nucleo/agua.py:pendiente_local` tenia el docstring que previa
exactamente este momento ("se cachea cuando el perfilado lo pida, no
antes") -- lo pido. Precondicion verificada antes de tocar: elevacion solo
se escribe en generacion (grep de asignaciones), celda estatica.

Paquete 1 (charcos): (a) cache de pendiente_local por zona (lazy, muere
con la zona, NO persiste); (b) `ZonaBioma.celdas_humedas` (registro de
celdas con charco>0 o humedad_subsuelo>0) + drenaje seco via
_drenar_celdas_humedas: el LLENADO sigue escaneando completo en lluvia
(cualquier celda puede empezar a guardar agua -- necesario de verdad, sino
el registro se quedaria vacio y perdian incubas), el drenaje seco solo
toca las registradas. profundidad_charco SI se persiste y se repuebla al
cargar; humedad_subsuelo no se persiste (arranca 0.0 en tierra).
**Bug real encontrado por el propio arnes de bisect tick a tick
(PRIMER DIF: tick 169, zona 0, gota de 6.08e-06): la lisis hidrica de
sistema_descomposicion.py TAMBIEN escribe profundidad_charco** (agua
tisular de tejido blando sobre tierra seca) y mi registro no la conocia --
con el drenaje por registro, la gota quedaba encharcada PARA SIEMPRE
(drenaba solo las registradas). Fix real (no bypass): la lisis registra su
celda en celdas_humedas. Regla fija para sesiones futuras: **TODO escritor
de profundidad_charco/humedad_subsuelo debe entrar en el registro** --
hoy: _actualizar_charcos (lluvia, barrido completo), lisis (descomposicion),
repuebla al cargar. Un escritor nuevo que se olvide deja gotas encharcadas
eternas sin crash. Idiam exacto ya usado por celdas_en_llamas (08-09):
con lluvia/el fuego el escaneo completo es necesario de verdad al momento
de IGNICION, el registro solo ahorra el barrido seco.

Paquete 2 (pareja): (a) `nucleo/relaciones.py:pareja_presente` gana
`indice=None` (mismo resultado booleano, no consume rng; el fallback sin
indice intacto) -- sistema_necesidades pasa `indice=self._indice_actual`
en sus dos llamadas; (b) `_calcular_pareja` usa un catalogo POR TICK
(`self._catalogo_pareja`, poblada con la primera llamada del tick):
especie/sexo/gestacion no mutan durante la fase de movimiento/decision
(nacimientos/muertes ocurren en fases posteriores del tick, ver
main.py:ejecutar_tick) -- la foto es exacta; **la POSICION sigue leyendose
EN VIVO** (muta dentro del tick con el propio movimiento -- un snapshot de
posicion habria desempatado distinto). El 29% de las llamadas a
obtener_componente desaparece; _calcular_pareja cae de 5.6s a 2.4s en el
perfil de 700 ticks.

Paquete 3: `nucleo/entidad.py:obtener_componente` sin el literal {}.get()
que asignaba un dict vacio en cada falla de tipo (23.8M veces).

**Verificacion de los tres paquetes (el mas rigor que ha tenido cualquier
piezas de rendimiento del proyecto)**: suite 508/508 siempre verde; (
BOSQUE_AUTO_TICKS=2000 con persistencia real: salida byte a byte IDENTICA
al baseline master en los tres paquetes, por separado; bisect tick a tick
(semilla 42, 2000 ticks, poblacion + sumas de charco/humedad por tick y
por zona) idéntico; roundtrip BOSQUE_CONTINUAR sin excepciones. Medicion
final no-proxy (1400 ticks +50 de calentamiento, semilla 1000004): master
22.8 -> 17.3 ms/tick a pop ~107 (-24%); a 6000 ticks (poblacion crecida)
33.2 -> 25.6 ms/tick (-23%). Perfil de 700 ticks tras los paquetes:
obtener_componente 23.8M -> 14.7M llamadas, _actualizar_charcos 6.7->6.0s,
_calcular_pareja 5.6->2.4s, pendiente_local fuera del top.

**Nota honesta sobre el coste residual**: `_actualizar_charcos` sigue aun
6s en el perfil -- los ~2000 ticks de lluvia en la ventana siguen necesitando
el barrido completo (el resto del año seco ahora es casi gratis). Los
22.8 -> 17.3 reflejan el motor real completo, no solo lo que el perfil
pmuestra. Commits: `c7f0504` (harness) y `9a03a94` (los tres paquetes de
rendimiento juntos -- son un mismo arco de refactor, mismos tests de
integridad).

### Pendiente real tras esta sesion

- Con el motor ~24% mas rapido, 12000 tick completos quedan a ~1.1x de
  tiempo por semilla: un redine de 15 semillas SIN salvaguarda corta
  (p.ej. limite 5400s) ya deberia llegar. Es EL siguiente paso natural
  para calibrar con la ventana completa pendiente desde "Sobrepoblacion...".
- El informe ecoloico del dia queda abierto con su recomendacion firmada:
  (1) especie depredadora pequena nueva (disenar con Diego en brainstorming),
  (2) densidad de venado para el valle de lobo, (3) factor de manada hacia
  abajo (error de signo del 09-09 marcado), (4) vocacion a menos sesgo de
  forrajero, (5) reputacion de 5a/5b en 0 usos. Ninguna implementada.
- `sonidos_emitidos` del harness reporta 0 pese a sonidos reales (hay
  amenaza por sonido con volumen positivo): sospecha de instrumentacion,
  verificar global, no concluido.
