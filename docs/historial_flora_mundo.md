# Historial — Flora y "poblar más el mundo"

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

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
