# Historial — Fauna — nuevas especies, manada, ecología de caza

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

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
## Venado y cabra montés -- primeras dos especies de un arco de
## biodiversidad de fauna, implementadas directamente por Claude
## (2026-09-09, sesión siguiente, mismo día)

Con el ecosistema ya estable, Diego propuso ampliar la biodiversidad --
primero sugirió "cabras y ovejas", descartadas en conversación por
connotación de domesticación real (de los primeros animales
domesticados del mundo real). Reencuadrado hacia mamíferos genuinamente
salvajes: **venado** (cierra directamente el problema nutricional de
lobo, ya documentado desde el 2026-09-04 -- "el 75% de la nutrición de
lobo venía de gnomo") y **cabra montés** (primera fauna del bioma
montaña, vacío de fauna desde que existe flora propia ahí -- también
propuesto por Diego, pero como especie realmente salvaje, nunca
domesticada). Specs escritas por separado a petición explícita de
Diego, para poder soltarlas por separado al pipeline:
`docs/superpowers/specs/2026-09-09-especie-venado-design.md` y
`2026-09-09-especie-cabra-montes-design.md`.

**Diseño clave de venado, distinto de caballo**: peso deliberadamente
por debajo de TODO el rango de lobo (60-90kg), para ser cazable en
SOLITARIO por la vía normal de depredación -- sin pasar por el techo de
presa por manada, que esta misma sesión confirmó (73 corridas) que
prácticamente nunca se dispara en juego libre. Cero código nuevo de
depredación necesario, a diferencia de caballo.

**Bloqueo real de infraestructura, antes de implementar**: Diego pidió
"levanta el centinela" para probar si el modelo barato del pipeline
implementaba las dos specs correctamente. Comprobado antes de intentarlo:
este contenedor cloud no tiene `OPENROUTER_API_KEY` ni `litellm`/
`mini-swe-agent` instalados -- es un entorno efímero distinto de la
máquina histórica del pipeline (WSL2 de Diego). Reportado con honestidad
en vez de fingir un intento, ofrecidas tres vías (instalar aquí con la
clave, correrlo en su máquina, o implementar directamente) -- Diego
eligió la tercera, excepción ya prevista en la sección "Flujo de
implementación" de este documento.

**Hallazgo real durante la implementación, no anticipado en el spec de
venado**: "más ligero que lobo" no bastaba para garantizar caza
solitaria de verdad. `sistema_depredacion.py:_es_presa_valida` exige
además `magnitud_disposicion_por_peso(peso_cazador, peso_presa) >=
depredacion.umbral_disposicion_caza` (0.5) -- una ley LOGARÍTMICA
(`log_ratio/(1+log_ratio)`) que solo supera 0.5 cuando el cazador pesa
más de ~e≈2.72x que la presa. Con el peso original del spec (venado
20-40kg, lobo 60-90kg), el peor caso (lobo 60kg, venado 40kg, ratio
1.5x) quedaba muy por debajo del umbral -- confirmado por un test que
fallaba de forma intermitente según la semilla de sorteo de pesos, no
un fallo aleatorio del arnés. Corregido bajando el peso a `[12, 20]`kg
(corzo real pesa 15-30kg, sigue biológicamente plausible): incluso el
peor caso (lobo 60kg vs venado 20kg, ratio 3.0x) supera el umbral con
margen real (magnitud=0.523 frente a 0.500 exigido).

**Segundo hallazgo real, más serio -- bug de persistencia pre-existente,
sin relación con las especies nuevas, encontrado verificando el
roundtrip**: `BOSQUE_CONTINUAR=1` crasheaba con `TypeError: unhashable
type: list` en `sistema_manada.py:_sincronizar_madriguera`. Causa raíz:
JSON no tiene tupla -- `nucleo/persistencia.py:cargar_snapshot`
deserializaba cada sitio `(x,y)` de `MemoriaEspacial.recuerdos` como
`[x,y]` (lista) sin normalizar de vuelta a tupla. Esto rompía DOS cosas
en silencio para cualquier entidad recargada desde SQLite, no solo la
madriguera: `nucleo/memoria.py:registrar_recuerdo`/
`purgar_recuerdo_invalido` comparan por identidad de tupla (`(x,y) in
lista`), así que la deduplicación/purga de memoria dejaba de funcionar
tras cualquier recarga -- y `_sincronizar_madriguera` usa un sitio como
clave de `dict`, de ahí el crash real, solo visible con una especie
colonial (conejo) que ya tuviera memoria de refugio persistida en el
momento exacto de la carga. Corregido en el único punto de entrada
desde disco (normaliza cada sitio a tupla al cargar), con test de
regresión dedicado (`tests/test_persistencia_memoria_espacial.py`) --
commit separado (`12cc3b3`) del de las especies (`f290a5b`), por ser un
hallazgo independiente.

**Verificado contra el motor real, ambos commits**: 410/410 tests en
verde. `BOSQUE_AUTO_TICKS=3000` sin excepciones: ambas especies forman
manada (`venado: 1, cabra_montes: 1`), y consultando la base de datos
real (no solo "no lanzó excepción") -- venado sufrió depredación real
por lobo (2 de 8 muertes por `depredacion`, de 14 venados creados entre
fundadores y nacidos), confirmando que la caza en solitario se ejerce
de verdad en juego libre; cabra montés no sufrió ninguna depredación (3
de 3 muertes por `vejez`), coherente con la honestidad del spec (sin
depredador real en montaña todavía). Ambas especies se reprodujeron
(venado 10→14, cabra montés 8→11). `BOSQUE_CONTINUAR=1` repetido tras
el fix de persistencia, sin excepciones -- confirma el bug realmente
cerrado, no solo el test unitario en verde.

**Pendiente real, explícito**:
- Todos los valores de ambos catálogos son PROVISIONALES, sin calibrar
  contra el harness completo -- ni siquiera contra el A/B de 6-8
  semillas que sí recibieron gnomo/lobo/conejo/ardilla esta sesión.
- Si lobo empieza a sostener población real gracias a venado, el
  siguiente paso natural (no hecho aquí) es remedir si la caza en
  manada sobre caballo por fin empieza a dispararse -- candidato directo
  de seguimiento.
- ~~Cabra montés sigue sin ningún depredador real en montaña -- si se
  quiere una dinámica presa-depredador ahí, es un círculo de diseño
  aparte (fauna subterránea/de montaña propia, ya mencionada como
  horizonte lejano).~~ -- CORREGIDO el mismo día, ver la sección
  "Lobo caza en montaña -- investigación del mecanismo, confirmado como
  comportamiento correcto, no un bug" más abajo: la prueba extensa
  posterior (15 semillas) sí registró depredación real de cabra_montes
  por lobo (10 muertes) -- esta entrada asumía sin verificar que "sin
  depredador diseñado a propósito" significaba "sin depredador real en
  juego libre", y no era el caso.
- Sin ventaja de escalada/movimiento propio de terreno de montaña para
  cabra montés -- señalado como fuera de alcance en el spec, candidato
  futuro real si se quiere diferenciarla mecánicamente más allá del
  catálogo de atributos.
- Sin representación visual para ninguna de las dos -- motor primero.
- Desierto y tundra siguen siendo los dos biomas sin fauna propia --
  horizonte futuro ya señalado en la conversación de biodiversidad,
  sin empezar.
- El menú más amplio de biodiversidad que se discutió el mismo día
  (insectos como capa de recurso forrajeable, no como especie ECS;
  aves terrestres reutilizando el movimiento existente, vuelo real
  aplazado indefinidamente) sigue sin ningún diseño ni línea de código
  -- solo conversación.
## Lobo caza en montaña -- investigación del mecanismo, confirmado como
## comportamiento correcto, no un bug (2026-09-09, mismo día)

La prueba extensa de 15 semillas con venado/cabra_montes ya incluidas
(ver sección anterior) registró **10 muertes reales de cabra_montes por
depredación** -- contradiciendo la propia honestidad del spec de
cabra_montes y la nota de "Pendiente real" de la sección anterior
("sin depredador real en montaña todavía"), escrita a partir de una
única corrida de 3000 ticks donde no se había observado ninguna. Diego
pidió investigar el mecanismo antes de decidir si era un bug o
comportamiento deseado -- lobo es la ÚNICA especie del catálogo con
`medio_alimentacion: cazar`, y lobo nace y vive en bosque, nunca en
montaña.

**Investigación, verificada en tres niveles (código + generación real +
cálculo numérico), no solo leída en abstracto**:

1. **El movimiento no conoce el concepto de bioma, solo elevación y
   agua**. `sistema_movimiento.py:_aplicar_movimiento` (validación de
   cada paso) comprueba exactamente dos restricciones -- profundidad de
   agua frente a la estatura corporal, y diferencia de elevación entre
   celda origen y destino contra `pendiente_maxima_transitable(fuerza)`
   (~0.22, escalado por la fuerza individual). `TipoTerreno`/bioma
   **nunca se consulta** en la función que decide si un paso es válido
   -- el bioma es pura clasificación climática por celda
   (`nucleo/bioma.py:clasificar_bioma`, por elevación+lluvia+
   temperatura), nunca una barrera física para el motor de movimiento.
   Mismo hallazgo que ya existía para bosque/pradera (contiguos,
   documentado en el arco de "Distribución causal de flora"), nunca
   antes verificado para bosque/montaña.

2. **Bosque y montaña son geográficamente contiguos, confirmado
   empíricamente** (arnés dirigido, 4 semillas nuevas, mundo 40×40,
   contando adyacencia real de 4-vecinos):

   | Semilla | Celdas montaña | Celdas bosque | Pares 4-vecinos bosque-montaña | Distancia mínima |
   |---|---|---|---|---|
   | 1 | 52 | 740 | 12 | 1 |
   | 2 | 143 | 589 | 26 | 1 |
   | 3 | 89 | 265 | 7 | 1 |
   | 42 | 194 | 360 | 26 | 1 |

   Frontera real y directa en las 4 semillas, sin excepción -- coherente
   con la generación orográfica causal (campo de elevación continuo,
   sin discontinuidades artificiales entre biomas).

3. **`Accion.CAZAR` está explícitamente exento del sesgo de
   territorio**, por diseño documentado desde antes de esta sesión, no
   un descuido nuevo. El propio docstring de
   `sistema_movimiento.py:_calcular_deambular` lo dice: el sesgo de
   territorio (lo único que mantendría a fauna sin consciencia cerca de
   sitios conocidos) solo aplica "sin objetivo activo (COMER/BEBER/
   CAZAR/HUIR/BUSCAR_PAREJA)". `_calcular_caza` es una función de
   persecución pura -- busca la presa válida más cercana dentro del
   radio sensorial por peso/distancia/detectabilidad, sin ninguna
   noción de bioma, y camina hacia ella con `_acercarse_a`, sujeta
   únicamente al mismo gate de elevación/agua del punto 1.

4. **cabra_montes es presa numéricamente válida para lobo, con margen
   real, no por casualidad rara**: `cabra_montes: [25,45]kg` frente a
   `lobo: [60,90]kg` -- siempre más ligera, nunca choca con el techo
   `peso_maximo_presa` (solitario, sin bono de manada). El filtro
   adicional `magnitud_disposicion_por_peso(peso_cazador, peso_presa)
   >= depredacion.umbral_disposicion_caza` (0.5, logarítmico) exige un
   ratio de peso >= e≈2.72 -- no cualquier combinación individual pasa
   (p.ej. lobo 60kg/cabra 45kg falla, ratio 1.33), pero una fracción
   real del espacio de sorteo sí (p.ej. lobo 90kg/cabra 25kg, ratio 3.6,
   magnitud 0.56) -- coherente con 10 muertes reales en 15 semillas, ni
   una tasa desbocada ni un caso imposible.

**Conclusión, confirmada por Diego como comportamiento correcto, no un
bug**: no hay ningún fallo de código ni ninguna regresión introducida
por venado/cabra_montes -- es el mismo mecanismo de persecución ya
usado deliberadamente para el resto de la caza (nunca antes puesto a
prueba con un depredador y una presa nativos de biomas distintos hasta
hoy). Un lobo cazando cerca del límite bosque/montaña detecta una
cabra_montes dentro de su radio de percepción y camina hacia ella paso
a paso -- cada paso limitado solo por pendiente/agua, nunca por bioma
-- pudiendo terminar cazándola dentro de montaña. Físicamente plausible
además: un lobo real persigue presa a través de fronteras de hábitat
sin ningún problema. La spec de cabra_montes y la nota de "Pendiente
real" de la sección anterior quedaban desactualizadas por una muestra
de una sola corrida corta, no por un error de diseño -- corregidas
arriba (tachadas, no borradas, mismo criterio de honestidad que el
resto de este documento).

**Pendiente real, explícito, distinto de "sin depredador en montaña"**:
- Sin remedir si esta misma vía (persecución sin barrera de bioma)
  también permite a lobo cazar cabra_montes con apoyo de manada (techo
  de presa ampliado) -- no investigado, candidato de seguimiento menor.
- Cabra montés sigue sin ninguna ventaja de terreno propia de montaña
  (escalada, refugio en risco) que compense esta exposición real a
  depredación -- señalado ya en la sección anterior como fuera de
  alcance del spec original, ahora con más motivo real detrás si se
  quisiera equilibrar la dinámica presa-depredador de montaña.
- El mecanismo general (persecución de caza sin gate de bioma, solo
  elevación/agua) aplica igual a CUALQUIER futuro par depredador-presa
  de biomas distintos que sean geográficamente contiguos -- no es
  específico de lobo/cabra_montes, útil recordarlo al diseñar fauna
  futura en desierto/tundra si algún depredador de otro bioma pudiera
  alcanzarlos por el mismo camino.
## Rename cabra_montes -> cabra_montesa + primera verificación real de
## "orillas vadeables" + "tasa de consumo por especie" juntas (2026-09-10,
## misma sesión)

Dos correcciones pedidas por Diego tras cerrar la pieza anterior.

**Rename**: `Especie.CABRA_MONTES` → `Especie.CABRA_MONTESA` (y el
identificador string `cabra_montes` → `cabra_montesa` en todas las claves
de config que lo usan como llave de especie --
`rangos_raciales.cabra_montesa`, `necesidades.cabra_montesa`,
`tasa_consumo_al_comer_por_especie.cabra_montesa`,
`cabras_montesas_iniciales`) -- corrige el identificador técnico,
gramaticalmente incorrecto tal cual estaba (`cabra_montes` quedaba como
adjetivo sin concordar). El nombre legible de la crónica ("cabra montés",
término real en español para *Capra pyrenaica*, invariable en género para
esta especie concreta) no cambia -- solo el identificador interno.
`tests/test_especie_cabra_montes.py` renombrado a
`test_especie_cabra_montesa.py`, contenido actualizado. 425/425 tests en
verde, `BOSQUE_AUTO_TICKS=1500` sin excepciones, confirmado en el propio
log de la corrida que `cabra_montesa` forma manada con su nuevo nombre.

**Verificación de "un par de semillas"** (2 semillas nuevas, 610001 y
610002, `herramientas/harness_calibracion.py`, hasta 6000 ticks, 480s de
tope por semilla -- 610001 cortada por tiempo a los 4973 ticks, 610002
completó los 6000), pedida explícitamente para medir el efecto conjunto
de "orillas vadeables" y "tasa de consumo al comer por especie" (las dos
piezas cerradas justo antes del rename en esta misma sesión) sobre el
equilibrio del ecosistema:

- **Criterio maestro de Diego (5 especies vivas a la vez): 2/2 (100%)** --
  y de hecho las 7 especies del catálogo completo (incluyendo venado y
  cabra_montesa) quedaron vivas en ambas semillas.
- **Deshidratación, prácticamente desaparecida como causa de muerte**:
  solo 2 muertes de ardilla y 1 de caballo por deshidratación en las
  ~11000 ticks combinadas -- frente a las cifras dominantes que esta
  misma investigación documentó antes de "orillas vadeables" (ardilla
  53.8%, conejo con la deshidratación como causa relevante en varias
  corridas del harness de 15 semillas del 2026-09-09). Dirección
  coherente con el propio objetivo de la pieza: dar acceso real a agua a
  las especies pequeñas.
- Conejo repitió su patrón de explosión ya conocido y sin relación con
  hoy (388 individuos en la semilla 610001, boom-bust ya documentado
  varias veces en este proyecto) -- no es un efecto colateral de los
  cambios de hoy.
- Funnel reproductivo, asentamientos (2/2), almacén (2/2), salón común
  (2/2), cocina (1/2), parejas estables de gnomo (12, presentes en las 2
  semillas) -- todos los mecanismos sociales/de construcción siguen
  disparándose con fuerza real, sin indicio de regresión.

**Honestidad explícita sobre el tamaño de la muestra**: n=2 es
exactamente lo que Diego pidió ("un par de semillas"), no una
calibración -- direccional, no una confirmación estadística. El 100% del
criterio maestro en 2/2 es una señal alentadora, coherente con el efecto
esperado de ambos cambios (más acceso a agua, ritmo de forrajeo más
realista), pero con un tamaño de muestra tan pequeño no se puede
descartar que sea favorable por casualidad -- el harness completo
(15×12000) sigue siendo la referencia de rigor pendiente para dar esto
por cerrado de verdad. `resultados guardados en
/tmp/.../scratchpad/verif_rename.json` (fuera del repo, no comiteado).

Commits: rename del identificador (dos commits, uno del `git mv` del
test y otro del contenido) -- sin cambios de comportamiento del motor,
solo el nombre.
## "No se forma ninguna manada" era un artefacto de medición, no un
## hallazgo real -- bug real corregido en el harness (2026-09-10, misma
## sesión)

Diego, tras ver la corrida de una semilla nueva (999001, hasta 9155
ticks) donde `manadas_por_especie` reportaba `{'gnomo': 4, 'caballo': 1,
'venado': 2}` -- 0 para lobo/conejo/ardilla/cabra_montesa -- preguntó si
hacía falta agrupar a los fundadores de fauna al nacer (mismo patrón que
"parejas fundadoras" para reproducción, 2026-09-06). Antes de evaluar esa
propuesta, se verificó la premisa contra el motor real (mismo criterio de
siempre: nunca aceptar un hallazgo sin comprobarlo).

**La premisa era falsa**: `sistema_manada.py:_stats_manadas_por_especie`
se SOBREESCRIBÍA cada día (`self._stats_manadas_por_especie = stats`) en
vez de acumularse -- el harness/`BOSQUE_AUTO_TICKS` solo leen su valor al
final de la corrida, así que cualquier especie ya extinta (ardilla,
cabra_montesa) o con población dispersa ese día concreto (conejo, a
punto de extinguirse) mostraba 0, indistinguible de "nunca formó
manada". Instrumentado un arnés dedicado que muestrea el stat día a día
en vez de solo al final, misma semilla 999001: **las 7 especies
formaron manada con regularidad durante casi toda su vida** -- lobo en
348 de ~374 días, conejo en 343, ardilla en 251, cabra_montesa en 220,
caballo en 361, venado en 374, gnomo en 374. Coherente además con las
7948 sincronizaciones de madriguera de conejo ya reportadas en la misma
corrida (solo ocurren dentro de una manada de conejo activa) -- un dato
que ya contradecía la lectura de "0 manadas" antes de instrumentar nada,
solo que nadie lo había cruzado hasta ahora.

**Corregido** (`sistemas/sistema_manada.py`, `main.py`): el stat pasa a
ser acumulado (suma de días con al menos 1 manada sobre toda la
corrida), con la etiqueta de impresión aclarando explícitamente que ya
no es un snapshot del último día. Sin cambios de comportamiento del
motor -- `mundo.manadas` (lo que de verdad usan `_calcular_deambular` y
la madriguera) siempre se recalculó correctamente día a día, el bug
estaba solo en el contador de observación. 425/425 tests en verde,
`BOSQUE_AUTO_TICKS=1500` sin excepciones, confirmado el nuevo formato
acumulado en la salida real.

**Conclusión sobre la pregunta original de Diego**: agrupar fundadores
de fauna al nacer NO es el fix que hacía falta -- el mecanismo de manada
ya funciona bien y desde el principio para las 7 especies, el problema
real de conejo/ardilla/cabra_montesa (extinción en esa semilla concreta)
sigue siendo el ya documentado (alta varianza de ardilla, boom-bust de
conejo, margen reproductivo ajustado de cabra_montesa) -- sin relación
con si se agrupan o no al nacer. Ninguna implementación de "fundadores
de fauna agrupados" se hizo, por no estar justificada por el hallazgo
real.

### "Si hay manadas y hay presas, ¿por qué los lobos en manada no cazan
### caballos?" -- dos conceptos distintos del motor, medidos por
### separado sobre la misma semilla, ninguno es un bug (2026-09-10,
### mismo día)

Pregunta de seguimiento directa de Diego, una vez descartado que
"0 manadas" fuera real. Investigado con dos arneses instrumentados
nuevos sobre la MISMA semilla ya en marcha (999001, la que Diego pidió
"lanzar ahora... que se desarrolle lo suficiente") en vez de razonar
solo desde el código -- mismo criterio de siempre.

**Medición 1 -- tamaño real de manada de lobo, día a día** (8136 ticks
reales, 500s de tope): tamaño MÁXIMO observado en cualquier día = 7;
distribución real de tamaños `{2: 53, 3: 22, 4: 82, 5: 72, 6: 49, 7:
38}` -- una manada de lobo alcanza con normalidad 4-7 miembros, **no
"casi siempre 1-2" como decía la documentación anterior de este mismo
arco** (esa cifra se basaba en la lectura de `_stats_manadas_por_especie`,
que en aquel momento SEGUÍA teniendo el bug de snapshot-del-último-día
ya corregido arriba -- una manada de 1-2 lobos en el último día de vida
de la especie no es representativa de su tamaño real durante la partida).
Población total de lobo en esos mismos días: min/max/media 3/13/8.4 --
manadas de 4-7 sobre una población de 3-13 significa que la INMENSA
MAYORÍA de los lobos vivos en un momento dado pertenecen a la manada
grande, no están dispersos.

**Medición 2 -- "aliados cazando activamente cerca", la condición REAL
que exige el techo de presa por manada** (7464 ticks reales, 400s de
tope, muestreo cada 10 ticks de la función de producción real
`nucleo/disposicion.py:contar_conspecificos_cercanos(..., solo_cazando=
True)` dentro de `social.radio_apoyo_grupal=3`, no `manada.
radio_manada_celdas=8`): máximo observado = **4** aliados cazando a la
vez; distribución sobre 6457 muestras `{0: 4284, 1: 692, 2: 629, 3: 728,
4: 124}` -- solo el **1.92%** de los momentos alcanza 4 o más aliados
cazando simultáneamente, y 4 nunca llegó a superarse en ninguna muestra.

**La respuesta real a la pregunta de Diego**: `Manada` (agrupamiento
social/espacial diario, radio 8, sin exigir que nadie esté cazando) y
"aliados cazando cerca" (el chequeo momentáneo que de verdad activa el
techo de presa por manada, radio 3, exige `Accion.CAZAR` LITERAL y
SIMULTÁNEA en cada aliado) son dos conceptos completamente distintos del
motor -- pertenecer a una manada grande de 4-7 lobos NO significa que
esos 4-7 estén cazando al mismo tiempo ni cerca unos de otros en el
instante exacto en que uno de ellos se plantea perseguir un caballo. La
fórmula (`peso_cazador * (1 + aliados_cazando_cerca) >=
peso_presa`, `config/combate.yaml:factor_ampliacion_techo_manada=1.0`)
necesita típicamente 4-6 aliados cazando a la vez para que un lobo medio
pueda plantearse un caballo medio -- el máximo real medido (4) está justo
en el borde inferior de ese rango, y se da en menos de 1 de cada 50
momentos observados. No es un bug: el mecanismo está verificado correcto
por sus propios tests dirigidos y por esta medición en juego libre --
es, sencillamente, una condición demasiado exigente para que la
dispersión natural de "quién está cazando en este preciso instante"
dentro de una manada ya grande la cumpla con frecuencia real.

**Ningún cambio de código en este círculo** -- diagnóstico puro, sin
decisión de diseño de Diego todavía sobre si tocarlo. Candidatos ya
señalados el 2026-09-09 siguen siendo los mismos, ahora con datos
mucho más precisos que entonces: bajar `factor_ampliacion_techo_manada`
(exigiría menos aliados, palanca numérica directa) o ampliar
`radio_apoyo_grupal` (más candidatos entran en el chequeo de
"cazando cerca" en un instante dado) -- ninguno probado todavía.
Descartado explícitamente por esta misma medición: el problema NUNCA
fue que las manadas fueran pequeñas (no lo son, llegan a 7) ni que
faltara presa viable (venado y caballo ya están ahí) -- es la
coincidencia temporal exacta de varios cazadores activos a la vez,
un umbral mucho más fino que "cuántos lobos hay cerca".

### Aullido de caza en manada -- cierra el hallazgo de arriba,
### implementado directamente por Claude a petición explícita de Diego
### (2026-09-10, mismo día)

Diego generalizó el diagnóstico: "la función de una manada de lobos es
cazar, protegerse, aparearse -- si no hay forma de que esos ciclos se
sincronicen como en la naturaleza, no sirve de nada". Corroborado
contra el código antes de aceptarlo sin más: `protección` y
`apareamiento` YA cobran su beneficio real solo de la cohesión espacial
que `Manada` construye bien (`bono_defensa_por_aliado` en
`sistema_necesidades.py` usa `solo_cazando=False`, cualquier
conespecífico cerca cuenta, sin exigir sincronía de ninguna acción; la
concepción exige contacto en la misma celda, que la cohesión ya
favorece) -- **caza es la única de las tres que necesita coincidencia
temporal exacta y la única para la que el motor no tenía ningún
mecanismo que la produjera**. Diego propuso el mecanismo concreto: un
lobo que detecta una presa que no puede intentar solo, aúlla, y eso
hace que la manada converja sobre ella.

Spec:
`docs/superpowers/specs/2026-09-10-aullido-caza-manada-design.md`.
**Un único círculo, más pequeño de lo que parecía al proponerlo**: la
mitad "convergencia real hacia el mismo objetivo" (que se había
planteado como posible círculo B aparte en la conversación previa)
resultó gratuita reutilizando el fallback de sonido ya existente
(2026-09-06, círculo 4b) -- un cazador sin presa válida propia YA
camina hacia el sonido audible más cercano, así que basta con que el
aullido exista como fuente de sonido real para que la convergencia
ocurra sin ningún código nuevo de movimiento.

**Implementado directamente por Claude** (pipeline sin disponibilidad
en este contenedor, mismo escenario ya documentado varias veces esta
sesión; "Diego lo pide explícitamente").

- `sistema_movimiento.py:_calcular_caza`: dentro del bucle de
  candidatos, un candidato que falla EXCLUSIVAMENTE por el techo de
  manada (`dims_p.peso >= peso_maximo_presa`, con los aliados que el
  cazador YA tiene cazando cerca en este instante -- el caso real de
  "esto no puedo yo solo/con lo que tengo ahora", no cualquier presa
  vista) dispara un aullido: `emitir_sonido` en la posición PROPIA del
  cazador (no la de la presa -- el sonido nace de quien lo emite, la
  física de `nucleo/sonido.py` no tiene forma de "teletransportar" la
  ubicación de un tercero, y no hace falta: una vez que compañeros
  llegan cerca, `aliados_cazando` sube en la siguiente evaluación y
  desbloquea la presa vía el mismo mecanismo de techo de manada ya
  existente). Magnitud `peso_cazador + peso_presa`, mismo convenio ya
  usado por las otras dos emisiones de sonido existentes -- ninguna
  constante nueva que calibrar. Como máximo un aullido por cazador y
  tick (`aullido_emitido`).
- **Bug real encontrado y corregido durante la propia implementación,
  antes de comitear** (no al fallar en caliente): la primera versión
  no acotaba el aullido por distancia -- cuando `self._indice_actual`
  es `None` (llamadas directas sin índice, como los propios tests),
  `candidatos` recorre TODAS las entidades del gestor sin filtrar por
  `radio`, y el chequeo del techo de manada se evaluaba antes de
  calcular ninguna distancia. Un lobo habría podido "detectar" y aullar
  por un caballo al otro lado del mapa. Corregido moviendo el cálculo
  de `dist` antes del chequeo de techo y descartando cualquier
  candidato con `dist > radio` antes de considerar el aullido -- mismo
  alcance que `radio_efectivo_por_peso` ya garantiza para presas
  válidas (siempre `<= radio`).

**Limitación real, señalada con honestidad en el propio spec, no
resuelta aquí**: solo responden al aullido los compañeros que YA
estaban ejecutando `Accion.CAZAR` este tick (por su propio hambre) pero
sin presa válida propia que perseguir -- `_calcular_caza` es la única
función que consulta el sonido de caza, y solo se llama cuando el
individuo ya eligió cazar por su cuenta. El aullido NO recluta a un
lobo que este tick prefiere beber, dormir o socializar, por hambriento
que esté en términos generales -- más estrecho que "cualquier miembro
de la manada se anima a cazar", aunque defendible (un lobo no abandona
lo que esté haciendo por cualquier aullido lejano).

**Verificado**: 432/432 tests (7 nuevos,
`tests/test_aullido_caza_manada.py` -- gate exacto por techo de manada,
posición correcta del sonido, magnitud, regresión sin zona/sin presa,
como máximo un aullido por tick, y un test de integración con dos
lobos confirmando que el segundo -- sin presa propia y fuera de su
propio radio de detección del caballo -- converge hacia la posición
del primero vía el fallback 4b sin tocarlo). `BOSQUE_AUTO_TICKS=3000`
con la semilla por defecto, sin ninguna excepción: **130 aullidos** en
la corrida -- el mecanismo se dispara con fuerza real en juego libre
desde el primer día, a diferencia de varias piezas anteriores de este
proyecto que quedaron "correctas pero invisibles" durante semanas.

**Pendiente real, explícito**: no se ha medido todavía si esto sube de
verdad la tasa de caza exitosa de lobo contra caballo/venado en manada
(el propio objetivo que motivó todo el arco) -- 130 aullidos confirma
que el mecanismo se EJERCE, no que cierre el hallazgo de fondo
(1.92% de coincidencia de aliados cazando a la vez); candidato directo
para una medición A/B similar a las ya hechas en este proyecto (varias
semillas nuevas, comparar capturas de caballo/venado por lobo antes/
después) si se quiere confirmar el efecto real, no solo que el
mecanismo dispara. La limitación de "solo responde quien ya iba a
cazar" tampoco se ha medido cuánto la acota en la práctica.
## Aullido de caza en manada -- REVERTIDO el mismo día, sustituido por
## cohesión de manada como fallback de caza, más fiel a como coordina
## una manada real (2026-09-10, mismo día)

Diego, tras ver el aullido implementado y funcionando (130 disparos en
3000 ticks, 432/432 tests), cuestionó el diseño en vez de aceptarlo sin
más: "es que no me convence, en la naturaleza como funcionaria?".
Investigado antes de defender el diseño ya hecho -- mismo criterio de
autocrítica que el resto del proyecto:

**Por qué el aullido no era fiel**: un lobo real no aúlla a mitad de
acecho para "convocar ayuda" contra una presa ya detectada -- eso
alertaría a la presa, rompiendo el sigilo que la caza real exige. La
coordinación real de una manada es ESTRUCTURAL, no reactiva: el grupo
ya viaja, descansa y busca junto ANTES de encontrar presa -- la
cohesión precede la caza, no se convoca durante ella.

**Causa raíz, sin cambios desde el diagnóstico original**:
`_calcular_deambular` ya tira hacia el centro de la `Manada` propia
como sesgo gregario (2026-09-07), pero queda desactivado mientras haya
CUALQUIER objetivo activo, `Accion.CAZAR` incluido -- correcto cuando
hay presa real, pero deja sin ningún sesgo de cohesión el caso "elegí
cazar, no encontré nada", que es justo el que importa para que varios
cazadores terminen cerca a la vez.

**Rediseño, spec `docs/superpowers/specs/
2026-09-10-cohesion-manada-fallback-caza-design.md`** (supersede a la
del aullido, conservada como registro histórico -- mismo criterio de
honestidad de siempre, no se borra el intento fallido): revertido por
completo el aullido (`emitir_sonido` en `_calcular_caza`,
`_stats_aullido_caza_manada`, sus 7 tests) y sustituido por el MISMO
mecanismo que `_calcular_deambular` ya usa -- `nucleo.manada.manada_de`
+ tirar hacia `manada.centro` si está a más de
`distancia_deseada_conspecifico` -- aplicado ahora también dentro de
`_calcular_caza`, solo en la rama `if not presas:`. Orden de fallback:
presa real > sonido audible (2026-09-06, círculo 4b, sin cambios) >
cohesión de manada (nuevo) > paso aleatorio. `_calcular_caza` gana un
parámetro opcional `mundo: Any | None = None` (mismo criterio que
`zona`: sin él, llamadas legacy quedan exactamente como antes). Ninguna
constante numérica nueva -- reutiliza estructuras y umbrales ya
existentes por completo.

**Verificado**: 431/431 tests (6 nuevos,
`tests/test_cohesion_manada_fallback_caza.py`, sustituye al fichero de
tests del aullido -- sin presa ni sonido con manada deriva hacia el
centro; con presa válida la manada nunca se consulta; sonido audible
más cerca que el centro de la manada gana; ya cerca del centro no
fuerza movimiento; sin manada cae al comportamiento anterior; sin
`mundo` -- llamadas legacy -- la cohesión queda desactivada igual que
sin `zona`). `BOSQUE_AUTO_TICKS=3000` con la semilla por defecto sin
ninguna excepción -- 0 disparos de cohesión en esa corrida concreta
(mismo tipo de "correcto pero raro en esta semilla" ya visto varias
veces en este proyecto, comparación semilla-a-semilla no fiable tras
cualquier cambio de código). Confirmado que el mecanismo SÍ se ejerce
en juego libre con una semilla nueva (777001, arnés de sesión sin
persistencia, 2789 ticks reales): **10 disparos de cohesión, 0 de
sonido** en esa corrida -- el fallback nuevo se dispara con normalidad
cuando toca.

**Limitación real, misma que ya tenía el aullido, señalada con
honestidad**: solo se beneficia quien YA eligió `CAZAR` este tick por
su propio hambre -- la cohesión no recluta a quien prefiere beber o
dormir. Tampoco garantiza que, al llegar cerca del centro de la manada,
haya de verdad aliados cazando en ese instante exacto
(`aliados_cazando` sigue exigiendo `Accion.CAZAR` literal y
simultánea) -- sube la PROBABILIDAD de coincidencia, no la garantiza.

**Pendiente real, explícito**: no medido todavía si esto sube de
verdad la tasa de caza exitosa de lobo contra caballo/venado en manada
(mismo objetivo de fondo que ya perseguía el aullido, sin confirmar
con ninguno de los dos diseños) -- candidato directo para una medición
A/B (varias semillas nuevas, capturas de caballo/venado por lobo antes/
después) si se quiere cerrar esto de verdad. Lección metodológica
reforzada: verificar contra el motor real, y estar dispuesto a
cuestionar el propio diseño recién implementado en vez de defenderlo,
sigue siendo más valioso que cualquier razonamiento sobre el papel --
mismo patrón ya documentado media docena de veces en este proyecto.

### A/B real contra el objetivo de fondo -- 0 muertes de caballo por
### depredación en AMBAS condiciones, resultado nulo, no una mejora
### confirmada (2026-09-10, mismo día, pedido explícito de Diego "y ha
### funcionado?" / "adelante, pruébalo")

Diego cuestionó con razón que confirmar "el mecanismo se dispara" no
es lo mismo que "ha funcionado" -- el objetivo real de todo este arco
(desde "¿por qué los lobos en manada no cazan caballos?") era que la
caza en manada contra caballo empezara a darse de verdad, no solo que
`_stats_manada_cohesion_fallback_caza` subiera. Medido con el mismo
método ya usado para el radio de caza (worktree en el commit ANTERIOR
a todo este mecanismo -- `0a5c851`, sin aullido ni cohesión -- frente a
`master` con la cohesión ya aplicada, mismas 8 semillas nuevas
850001-850008, hasta 6000 ticks, `herramientas/harness_calibracion.py`).

**Resultado, contando `muertes_por_especie["caballo"]["depredacion"]`
en las 16 corridas totales (8 por condición)**: **0 en ambas
condiciones, sin ninguna excepción**. Venado (cazable en solitario,
sin depender de la manada) sí muestra depredación real en las dos
(30 antes, 34 después -- diferencia dentro del ruido esperado por
desplazamiento de secuencia de `rng`, no una señal). Lobo tampoco
mostró ninguna extinción en ninguna condición (0/8 ambas), población
final 1-16 en rangos similares.

**Conclusión honesta, sin inflar el resultado**: la cohesión de manada
NO mostró ningún efecto medible sobre el objetivo real que motivó todo
el arco -- con 0 eventos en las dos condiciones, no hay señal que
comparar, ni a favor ni en contra. Coherente con el propio hallazgo
del mismo día ("aliados cazando cerca" alcanza el umbral necesario en
solo 1.92% de los momentos observados): una ventana de hasta 6000
ticks con una población de lobo de 1-16 individuos parece
estructuralmente demasiado corta/pequeña para que el evento ocurra ni
una sola vez, con o sin el empujón de cohesión hacia el centro de la
manada. Esto NO invalida la corrección biológica del diseño (el
aullido seguía siendo peor, por las razones ya documentadas), pero sí
cierra con honestidad la pregunta de Diego: **no, no se ha confirmado
que haya funcionado para el objetivo real** -- solo que el mecanismo
se ejerce (ver arriba, 10/0/3/16 disparos en la verificación previa).

**Pendiente real, explícito, más concreto que antes**: para medir esto
de verdad haría falta o (a) una ventana mucho más larga (el harness
completo de referencia, 12000 ticks, nunca corrido hasta el final por
límite de tiempo del entorno), o (b) una población de lobo
artificialmente mayor solo para esta medición (riesgo ya señalado:
"subir lobos_iniciales no arregla nada" para supervivencia, pero no se
ha probado específicamente para frecuencia de eventos de manada), o
(c) aceptar que la caza en manada contra caballo es, en la práctica,
un evento tan raro que ninguna mejora de coordinación por sí sola
(aullido, cohesión, ni ninguna futura) lo hará observable sin tocar
también `factor_ampliacion_techo_manada` o `radio_apoyo_grupal` --
ambas palancas numéricas ya señaladas como candidatas el mismo día y
sin probar todavía. Worktree temporal (`0a5c851`) retirado tras la
comparación, no forma parte del repositorio.
## Especie zorro -- mesodepredador de conejo/ardilla, cerrado con un
## hallazgo real de fragilidad ya corregido (2026-09-14)

Diego pidió una criatura nueva que actúe como depredador intermedio de
presas pequeñas y controle el crecimiento de conejo/ardilla --
directamente conectado con la recomendación #1 del informe ecológico de
la sesión anterior ("especie depredadora pequeña nueva, diseñar con
Diego en brainstorming"). Motivación real, no solo narrativa: lobo
(60-90kg) está mal ajustado a presas tan pequeñas -- `aporte_maximo =
(peso_presa/peso_cazador) * eficiencia_biomasa_saciedad` hace que una
captura de conejo o ardilla apenas alimente a un animal de ese tamaño
(hallazgo ya documentado, "Por qué lobo se muere de hambre pese a cazar
más que nadie", 2026-09-04/05).

Spec: `docs/superpowers/specs/2026-09-14-especie-zorro-design.md`.
Reutiliza el 100% del mecanismo genérico ya existente -- fábricas ECS
(`crear_criatura`/`nacer_criatura`) parametrizadas por `especie.value`
sobre `rangos_raciales`, `_es_presa_valida`/`_resolver_ataque` ya
agnósticos a especie -- ninguna línea de código nueva en depredación,
solo catálogo + siembra.

**Dos decisiones cerradas con Diego antes de escribir un solo número**:
1. **Peso [5,9]kg por FIDELIDAD REAL, no por control garantizado.** La
   disposición de caza es logarítmica y exige ratio de peso `>= e≈2.72`
   (`combate.umbral_disposicion_caza=0.5`). Con este peso: contra
   ardilla (0.3-0.6kg) el ratio siempre supera el umbral -- **caza
   garantizada en el 100% de los individuos**; contra conejo
   (1.5-3.0kg) el ratio va de 1.67 (no cazable) a 6.0 (cazable) --
   **control real pero PARCIAL**, depende del individuo. Diego lo
   eligió explícitamente frente a subir el peso mínimo a ~8.2kg (que
   habría garantizado caza de cualquier conejo al precio de alejarse
   del zorro real, rozando tamaño de coyote) -- mismo patrón ya
   aceptado en el proyecto con lobo/cabra_montesa.
2. **Bioma: bosque y pradera a la vez (generalista real).** Ambos
   biomas ya son contiguos en el motor (frontera confirmada, la
   persecución de caza no filtra por bioma -- ver "Lobo caza en
   montaña" más arriba), así que sembrar sobre un pool COMBINADO
   (`candidatas_bosque + celdas_pradera`, sin forzar reparto 50/50) le
   da territorio propio en ambos desde el arranque, no solo acceso por
   persecución incidental.

Resto del catálogo calibrado por analogía razonada con el resto del
catálogo (gestación corta [45,60]d + camada [2,4] + concepción 0.015,
mismo perfil "sostenible" ya validado en lobo/venado; sociabilidad baja
[0.2,0.45] -- territorial/solitario, caza en SOLITARIO por diseño, sin
depender de aliados; agudeza_sensorial alta [0.6,0.9] -- rasgo real
distintivo del zorro; longevidad corta [4,8] años -- evita el error ya
cometido con gnomo, gestación/vida desproporcionada). `zorros_iniciales:
8`, comparable a `lobos_iniciales`. Deliberadamente SIN entrada propia
en `fisiologia.yaml:necesidades` en la spec original -- mismo criterio
que caballo en su día, "no calibrar a ciegas".

**Hallazgo real, corregido el mismo día, no dejado como "correcto pero
frágil" sin más**: `BOSQUE_AUTO_TICKS=3000` con la semilla por defecto
mostró **8/8 zorros muertos, el 100% por inanición**. Un diagnóstico
multi-semilla dedicado (`herramientas/harness_calibracion.py`, 4
semillas nuevas 550001-550004 × 5000 ticks) confirmó el patrón: **4/4
extinción, 100% de las muertes por inanición, 0 concepciones** -- ni una
sola hembra llegó a acumular saciedad suficiente para intentar concebir.
Mismo patrón exacto ya visto en lobo/ardilla/gnomo/conejo/caballo antes
de sus propios fixes de fisiología. Corregido aplicando directamente el
mismo par ya validado repetidas veces en el catálogo
(`tasa_perdida_saciedad_por_tick`/`probabilidad_muerte_saciedad_critica`
= 0.0008/0.0004, más el mismo par de hidratación) -- mismo criterio que
venado/cabra_montesa ("arrancar ya con el par" en vez de repetir el
ciclo completo de caballo, que nació con el valor universal y se corrigió
días después).

**Reverificado con las MISMAS 4 semillas** (mismo criterio metodológico
del proyecto: nunca comparar semilla-a-semilla entre config distinta sin
repetir la semilla exacta, dado que cualquier cambio desplaza la
secuencia de `rng`): extinción de zorro baja de 4/4 (100%) a **2/4
(50%)**, con embudo reproductivo activo (11 concepciones → 18
nacimientos, 164%) y una causa de muerte nueva real: **depredación (5
casos)**. Mejora real, medida, **NO una solución completa** -- mismo
patrón honesto que casi todas las demás especies de este catálogo.

**Hallazgo colateral, no bug, cadena trófica de tres niveles emergiendo
sola**: con zorro (5-9kg) muy por debajo del peso mínimo de lobo
(60kg), el ratio de peso supera el umbral de caza con margen amplio
(magnitud muy por encima de 0.5) -- lobo YA puede cazar zorro, sin
ningún código nuevo, pura consecuencia de la ley de pesos ya existente.
No estaba en la spec original ni se había anticipado, pero es
exactamente el tipo de emergencia que el proyecto busca (leyes
neutras, principio 5) -- un depredador intermedio real, presa de uno
más grande y presa a la vez de conejo/ardilla, sin una sola línea de
código dedicada a esa relación.

**Verificado**: 580/580 tests en verde (11 nuevos,
`tests/test_especie_zorro.py` -- existencia/distinción de la especie,
fábricas ECS completas, siembra real con el pool COMO unión de ambos
biomas (verificado con una población de prueba ampliada para que el
azar de una sola semilla no pueda ocultar que el pool es solo uno de
los dos), las dos leyes de peso frente a ardilla/conejo con los
extremos exactos del rango (no solo el promedio), caza en solitario, y
el ratio de saciedad por captura de ardilla frente a lobo).
`BOSQUE_AUTO_TICKS=3000` y `BOSQUE_CONTINUAR=200` sin ninguna excepción
en ninguna de las dos verificaciones (antes y después del fix de
fisiología).

**Pendiente real, explícito**: 2/4 semillas nuevas siguen extinguiendo
zorro tras el fix -- no se persiguió más calibración con esta muestra
tan pequeña (mismo criterio de prudencia ya aplicado repetidas veces en
el proyecto, "rendimientos decrecientes" frente a seguir ajustando a
ciegas con n=4); si se retoma, candidato más probable es revisar
`factor_base_concepcion`/`camada` de zorro con el mismo criterio de dos
ingredientes ya usado en lobo/ardilla/gnomo, pero solo con evidencia de
un lote mayor, no a ciegas. `zorros_iniciales=8` y todo el catálogo de
temperamento siguen PROVISIONALES, sin calibrar contra el harness
completo. Sin representación visual -- motor primero. Sin ninguna
ventaja de terreno específica de bosque/pradera.

### A/B real: ¿zorro controla de verdad a conejo/ardilla? -- mecanismo
### confirmado, efecto poblacional NO concluyente, mismo artefacto de
### rng ya documentado repetidas veces en el proyecto (2026-09-14, mismo
### día)

Diego pidió confirmar el objetivo de fondo que motivó toda la pieza, no
solo que zorro cace y sobreviva. Arnés dedicado (`ab_zorro.py`,
scratchpad, no en el repo): 8 semillas nuevas (630001-630008) × hasta
5000 ticks, cada una corrida DOS veces -- una con `zorros_iniciales`
parcheado a 0 (control, sin zorro) y otra tal cual está en `master`
(con zorro) -- mismo criterio metodológico ya usado en el proyecto para
A/B en memoria sin tocar disco. Las 16 corridas se cortaron por tiempo
(3222-4555 ticks, ninguna llegó a 5000).

**Resultado, normalizado por cada 1000 ticks reales (necesario porque
cada corrida se cortó en un punto distinto)**:

| | conejo (media) | ardilla (media) | depredación total sobre ardilla (suma 8 semillas) |
|---|---|---|---|
| Sin zorro | 8.82 | 2.36 | 90 |
| Con zorro | 20.39 | 2.51 | 107 |

**Zorro sí caza de verdad, confirmado con el propio desglose de
muertes**: la depredación total sobre ardilla sube ~19% con zorro
presente (90→107), y zorro mismo murió por depredación (presa de lobo)
en 5 de 8 semillas -- el mecanismo se ejerce, no es "correcto pero
invisible".

**Pero el efecto neto sobre la población de conejo va en la dirección
CONTRARIA a la que motivó la pieza**: con zorro presente, la densidad
de conejo normalizada es más del doble (20.4 vs 8.8) que sin él.
Ardilla se mantiene prácticamente igual (2.51 vs 2.36). **Diagnóstico
honesto, no una conclusión causal**: esto es casi con certeza el mismo
artefacto de "desplazamiento de secuencia de `rng`" ya documentado
media docena de veces en este proyecto (Sobrepoblación..., radio de
caza de lobo, el propio ajuste de conejo del 2026-09-06) -- sembrar 8
zorros más consume tiradas de `rng` extra en tick 0, desplazando toda
la secuencia de aleatoriedad posterior para el resto del motor: "la
misma semilla" con y sin zorro son, en la práctica, dos partidas
distintas desde el principio. Con n=8 y trayectorias tan divergentes
entre semillas individuales (conejo sube x1.4 con zorro en unas,
cae a 1/7 en otras), la varianza de ese ruido metodológico es mayor
que cualquier señal causal real que pudiera existir en la muestra.

**Conclusión, sin inflar el resultado**: este experimento NO permite
afirmar ni descartar que zorro controle la población de conejo/ardilla
-- confirma el mecanismo (caza real, depredación real sobre ambas
presas), pero la pregunta de fondo de Diego ("¿reduce de verdad su
crecimiento?") sigue sin respuesta fiable. Para una respuesta limpia
hace falta lo que el propio proyecto ya sabe que hace falta desde hace
semanas: muchas más semillas nuevas por condición (no comparación
pareada semilla-a-semilla, que hereda el ruido de rng) para comparar
DISTRIBUCIONES agregadas, no trayectorias individuales -- el harness
completo (15×12000) sigue siendo la referencia de rigor pendiente,
ahora también para esta pregunta concreta.

**Pendiente real, explícito**: el objetivo de control poblacional de
zorro sigue sin confirmar ni refutar; si se retoma, un lote mucho mayor
(15-20 semillas nuevas por condición, no pareadas) sería el candidato
metodológicamente correcto, mismo criterio que el resto del proyecto ya
aprendió a aplicar tras la investigación de "Sobrepoblación...".

## Círculo 2026-09-17: evasión por vuelo, nivel trófico, segunda ronda
## de bugs de águila, y colonización espontánea

Origen: en la misma conversación en la que se cerró el círculo de
vuelo/águila (aguila como primera especie voladora, entrada anterior de
este historial), Diego cuestionó dos supuestos concretos del propio
mecanismo de depredación -- "no me parece muy factible que un lobo cace
un águila" y "no sé si los zorros son presas reales de lobos" -- y una
tercera pregunta más estructural, con el catálogo de fauna ya en 9
especies: "cada vez hay más razas de fauna, lo de que todas coexistan
en todas las semillas quizás empieza a ser algo inalcanzable... es
normal que en ecosistemas haya criaturas que prosperen más". Decisión
explícita de Diego sobre el orden: "vamos de menos complejidad a más"
-- evasión por vuelo primero, nivel trófico después (ambas en este
historial), criterio de diversidad y colonización espontánea después
(en `docs/historial_estabilidad_poblacion.md` y aquí respectivamente).

### Evasión por vuelo frente a depredador terrestre

Spec: `docs/superpowers/specs/2026-09-17-evasion-vuelo-depredacion-design.md`.
Reutiliza el rasgo racial `vuela` ya introducido en el círculo anterior
-- sin mecanismo nuevo, solo una nueva consecuencia de un rasgo
existente, siguiendo el principio de "reutiliza antes de inventar".
Regla: cuando la presa vuela y el cazador no, `prob_exito` se fija al
suelo ya existente `captura_prob_min` en vez de calcularse
normalmente -- modela captura "rara pero posible" (un lobo que
sorprende un águila posada o herida) sin inventar una probabilidad
nueva ni un mecanismo de "presa inmune". Implementado en
`sistemas/sistema_depredacion.py` (`_vuela()` helper +
bloque en `_resolver_ataque`). Tests: `test_evasion_vuelo_depredacion.py`
(4 tests). Aprobado por Diego ("adelante si") y subido a máster el
mismo día.

### Nivel trófico

Spec: `docs/superpowers/specs/2026-09-17-nivel-trofico-design.md`. Tres
opciones planteadas a Diego para resolver la tensión zorro-como-presa;
eligió la categórica ("la dos es la más útil realmente... esto es un
mundo de fantasía, tener esa categorización nos facilita, imagina que
introducimos un monstruo que sí caza lobos" -- razonamiento propio de
Diego, no sugerido). Nuevo rasgo racial `nivel_trofico` (entero fijo
por especie, no sorteado por individuo, mismo patrón de declaración que
`vuela`/`medio_alimentacion`): lobo, zorro y águila declarados nivel 1
(pares ecológicos entre sí, explícitamente NO una jerarquía interna);
herbívoros sin declarar, nivel 0 por defecto. Regla de tres casos, ley
general y neutra (principio 5), no un carve-out por especie:
- presa de nivel MENOR que el cazador → caza normal, sin cambios.
- presa del MISMO nivel → penalización de probabilidad
  (`penalizacion_disposicion_mismo_nivel_trofico=0.35`, PROVISIONAL en
  `config/combate.yaml`), no un suelo -- la depredación intragremial
  (zorro cazando zorro, lobo cazando zorro) es rara pero real en la
  naturaleza, así que se penaliza sin prohibirse.
- presa de nivel MAYOR → nunca válida como presa, gate duro en
  `_es_presa_valida`.

Diseñado explícitamente pensando en especies futuras de nivel 2+ (un
"super-depredador" que sí cace lobo/zorro/águila) sin necesitar ningún
mecanismo nuevo cuando llegue ese momento -- razón por la que Diego
prefirió esta opción sobre las otras dos más simples. Tests:
`test_nivel_trofico.py` (5 tests). Subido a máster el mismo día.

### Segunda ronda de bugs de águila -- encontrados durante
### instrumentación y verificación, no por queja de Diego

Dos bugs reales encontrados al auditar águila en profundidad tras su
introducción, ninguno reportado antes porque nadie había corrido el
motor con águila viva el tiempo suficiente para verlos:

- **Tasa de hambre 15x más rápida de lo previsto**: diagnosticado
  corriendo el motor real (`ejecutar_tick` invocado directamente en un
  script, no solo leyendo código) y siguiendo una única entidad águila
  tick a tick -- murió de inanición en el tick 138 pese a cazar el 53%
  del tiempo. Causa real: `config/fisiologia.yaml` no tenía ninguna
  entrada `aguila:` bajo `necesidades:`, cayendo al valor por defecto
  del sistema -- **repetición exacta de un bug ya corregido en zorro el
  2026-09-14**, documentado en el mismo fichero de config y no
  replicado a la siguiente especie voladora nueva. Fix: bloque
  `aguila:` añadido con las tasas estándar del resto de fauna
  (`tasa_perdida_saciedad_por_tick: 0.0008`,
  `probabilidad_muerte_saciedad_critica: 0.0004`, mismos valores para
  hidratación).
- **Ahogamiento pese a volar**: el propio diseño original del rasgo
  `vuela` ("volar sobre agua profunda no ahoga") solo se había
  implementado en el bloqueo de movimiento (`sistema_movimiento.py`);
  el drenaje de asfixia por inmersión de `sistema_necesidades.py` es un
  camino completamente independiente y nunca recibió la misma
  excepción -- un águila podía ahogarse en agua profunda igual que un
  gnomo. Fix: condición `and not especie_vuela` añadida al gate de
  ahogamiento (~línea 425).

Ambos verificados con `tests/test_correcciones_aguila_post_harness.py`
(4 tests, incluida una regresión explícita de que especies NO voladoras
deben seguir ahogándose igual que antes). Subido a máster junto con el
resto de fixes de esta ronda.

**Resultado real tras corregir ambos bugs, medido en el harness
completo de 15×10000 (ver desglose completo en
`docs/historial_estabilidad_poblacion.md`)**: águila sigue
extinguiéndose en el 87% de las semillas (13/15) -- los dos fixes eran
reales y necesarios (sin ellos, águila no sobrevivía ni el tiempo
mínimo para que cualquier otro mecanismo la afectara), pero no
resuelven por sí solos la viabilidad de la especie. Con solo 20
concepciones → 18 nacimientos agregados en las 15 semillas, la muestra
es demasiado pequeña para diagnosticar la causa siguiente con
confianza -- pendiente real, no cerrado.

### Colonización espontánea

Spec: `docs/superpowers/specs/2026-09-17-colonizacion-espontanea-design.md`.
Origen: idea propia de Diego, no una respuesta a un bug -- dar a cada
especie más de una oportunidad real de arraigar en el mundo, en vez de
depender enteramente de la siembra inicial de partida. Ley genérica
(principio 1, "reglas no guiones"), deliberadamente restringida a
especies ya en apuros para no convertirse en una válvula de
reaparición disfrazada que enmascare extinciones reales: cualquier
especie con población viva por debajo de `umbral_poblacion_critica=2`
sortea una probabilidad diaria baja
(`probabilidad_colonizacion_diaria=0.005`) de que aparezca una pareja
reproductora nueva (`tamano_pareja_colonizadora=2`) en una celda de
bioma compatible con la especie (`BIOMAS_POR_ESPECIE` en el propio
sistema). Implementado en `sistemas/sistema_colonizacion.py` (nuevo
fichero), integrado en `main.py` en el corte de día, emite
`Evento("ColonizacionEspontanea", Severidad.HISTORICO, ...)`. Tests:
`tests/test_colonizacion_espontanea.py` (5 tests).

**Resultado real medido en el harness completo de 15×10000**: el
mecanismo se ejerce con fuerza real, no es papel mojado -- 82 eventos
en total, en 15/15 semillas, repartidos precisamente hacia las especies
que más lo necesitaban (zorro 21, águila 14, conejo 12, ardilla 12,
lobo 9, cabra montesa 8). **Pero no es suficiente por sí sola para
evitar la extinción final** de esas mismas especies en la misma
corrida (ver `docs/historial_estabilidad_poblacion.md` para el análisis
completo) -- las parejas colonizadoras nuevas siguen sujetas a la misma
dinámica de fondo (incluido, en esa misma corrida, el bug de madurez
sincronizada que se diagnosticó a continuación). Colonización
espontánea da más oportunidades de arraigo, no inmunidad a una causa
estructural no resuelta todavía.
