# Historial — Construcción, asentamiento y dinámicas sociales

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

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
## Cocinas comunes -- tercera pieza del arco "dinámicas internas de
## asentamiento", cierra la cola de piezas ya planteadas salvo edificio
## de liderazgo (spec, implementado directamente por Claude, 2026-09-08)

Spec: `docs/superpowers/specs/2026-09-08-cocinas-comunes-design.md`.
Arranque con una pregunta de fondo, no asumida: dado que "cómo
cocinar" (mismo día) ya deja a cualquier consciente cocinar en
cualquier Fogata individual, ¿qué hace distinta a una cocina COMÚN?
Diego eligió mezclar las tres ideas de partida en vez de una sola:
bono mecánico (cocinar más rápido), imán social (mismo patrón de
confort/seguridad que salón común, como respaldo si no hay salón),
y alacena comunal real.

**Dos correcciones reales de diseño, cerradas con Diego antes de
escribir código**:
1. **Cadena de construcción, de lineal a PARALELA**: Diego rechazó
   explícitamente encadenar cocina detrás de salón común ("en paralelo
   al salón común") -- `objetivo_construccion_actual` generaliza su
   tramo final a evaluar `["salon_comun", "cocina"]` en paralelo,
   eligiendo el que ya lleve MÁS progreso (ley física: el esfuerzo de
   la población converge en uno sin que nadie lo planifique), empate
   exacto resuelto por orden fijo. `None` terminal solo con AMBOS
   completos. Generaliza limpio a un tercer paralelo futuro.
2. **La alacena es un destino real, no un beneficio pasivo** -- Diego
   corrigió mi primera propuesta ("cualquiera que esté físicamente en
   la cocina come de ahí") señalando que un hambriento en su refugio
   debería IR a la cocina, no beneficiarse solo por casualidad.
   `sistema_movimiento.py:_calcular_forrajeo` gana una tercera fuente
   de candidato (la alacena de la cocina del propio asentamiento, sin
   acotar por radio de percepción -- se sabe dónde está, igual que el
   salón común) que compite por distancia en igualdad de condiciones
   con necromasa y forraje local.

**Arquitectura**: `Construccion` gana `provisiones: dict[str, float]`
(mismo molde exacto que `Inventario.provisiones`, universal en el
componente, vacío salvo en cocinas). `nucleo/construccion.py` gana
`construccion_completada_de_asentamiento` (generaliza el patrón que
antes solo vivía duplicado en `sistema_movimiento.py:_salon_comun_de`)
y `construccion_de_tipo_en` (`hay_construccion_de_tipo_en` pasa a ser
su alias booleano, mismo patrón `hay_X`/`X_en` que ya separan
`fogata_en`/`hay_refugio_en`). `nucleo/comida.py:elaborar_recurso` gana
`destino` opcional (por defecto el mismo dict de origen, comportamiento
idéntico a antes) para poder depositar en la alacena de la cocina en
vez del inventario personal de quien cocina. La cocina "implica su
propio fuego" -- mismo criterio que el salón común -- así que
`Accion.COCINAR` se habilita sin Fogata real si hay una cocina
completada en la celda. `_resolver_cocinar` usa
`factor_bono_tasa_cocina_comun` (2.0, PROVISIONAL) cuando cocina ahí.
`_resolver_comer` gana una tercera fuente (celda → despensa personal →
alacena, en ese orden) sin chequeo de toxicidad (la alacena solo
contiene claves `_elaborada`, cocinar ya la elimina por completo) y
sin filtro de dieta propia (simplificación aceptada mientras solo
exista una especie consciente). `_calcular_socializar` usa la cocina
como respaldo SOLO si no hay salón común. `Construccion.provisiones`
se persiste (a diferencia de los registros de sonido/fuego, es comida
real acumulada por la comunidad) -- `VERSION_ESQUEMA` sube a
`"0.36-fase0"`.

**Verificado**: 393/393 tests (13 nuevos,
`tests/test_cocinas_comunes.py`, más 1 actualizado en
`test_salon_comun.py` para reflejar el nuevo eslabón paralelo).
`BOSQUE_AUTO_TICKS=3000` con la semilla por defecto: contadores
idénticos a los de antes de esta pieza (0 salones/cocinas completados
en esa corrida concreta, no llega tan lejos). **Diagnóstico honesto
aparte** (4 semillas nuevas × hasta 8000 ticks, scratchpad, sin
persistencia): tampoco se completó ninguna cocina ni salón común en
ninguna -- el mecanismo está verificado correcto por los tests
dirigidos (que sí construyen cocinas reales y confirman cada pieza:
alacena, bono de velocidad, imán social, bonos de confort/seguridad),
pero su disparo en juego libre sigue bloqueado por la misma causa de
fondo ya conocida y documentada varias veces en este proyecto (la
cadena refugio→almacén→comunal tarda más ticks de los que dura una
población real con la calibración actual) -- mismo patrón "correcto
pero invisible" ya visto con asentamiento, pareja, parentesco y salón
común.

**Pendiente real, explícito**: `masa_minima_cocina`, `huella_m2_cocina`,
`bono_confort_cocina_comun`, `bono_seguridad_cocina_comun`,
`factor_bono_tasa_cocina_comun` PROVISIONALES, sin calibrar; edificio
de liderazgo sigue aplazado hasta definir qué decisión mecánica real
debería habilitar -- **con esto, de las 3 piezas originalmente
planteadas por Diego para este arco (salón común, edificio de
liderazgo, cocinas), quedan 2 de 3 cerradas**; ciudad enana sigue fuera
de alcance hasta que se plantee la raza enana.
## Deuda técnica + tres círculos pequeños + rediseño de Agarre (manos
## libres) + extensión de robo + rename FABRICAR -- sesión completa
## (2026-09-11)

Sesión arrancada con "vamos a entrar en añadir mejoras en los sistemas
actuales" -- Diego pidió enfocarse primero en deuda técnica ("Bloque
A": consolidar funciones duplicadas, quitar comentarios innecesarios
-- esto último aplazado explícitamente, "dejamos los comentarios de
lado de momento" -- y optimizar sonido) antes de tocar funcionalidad
nueva. El harness completo se descartó de entrada para esta sesión:
este contenedor solo tiene 4 núcleos, la calibración de 15×12000 sigue
reservada para la máquina de Diego con 15.

### Bloque A -- auditoría de código + consolidación, cuatro commits

**Auditoría con el skill `code-review`** sobre `nucleo/` y `sistemas/`
completo (`de8255a`): 6 hallazgos, 5 confirmados contra el código real
(1 descartado explícitamente por ser una recomendación incorrecta --
cambiar `compartir_confianza` a `_pares_ordenados` habría alterado el
orden de tiradas de `rng`, mismo tipo de riesgo ya documentado
repetidas veces en este proyecto). Los 4 aprobados por Diego, cada uno
verificado con un arnés dedicado que reproduce el bug ANTES del fix,
no solo razonado sobre el papel:

1. **Índice espacial congelado ocultaba construcciones/madrigueras
   recién creadas por otro miembro en el mismo tick**:
   `sistema_movimiento.py:_calcular_construir` y
   `sistema_manada.py:_sincronizar_madriguera` consultaban
   `almacen_cercano`/`madriguera_en` a través del índice espacial
   congelado al principio del tick (optimización del 2026-09-08) --
   dos gnomos podían crear cada uno su propio almacén/salón/cocina
   duplicado en la misma celda, y dos manadas coloniales podían
   duplicar una `Madriguera`. Corregido volviendo a búsqueda EN VIVO
   (`indice=None`) solo en estos dos puntos de CREACIÓN -- el resto de
   usos del índice (navegación, no creación, donde un tick de retraso
   es inofensivo) queda intacto. El propio docstring de
   `almacen_cercano` ya prometía "búsqueda EN VIVO... para no perder
   una construcción arrancada por otro miembro este mismo día" --
   contradicho en la práctica desde que el índice se introdujo.
2. **Desempate "menor id" no determinista**:
   `nucleo/disposicion.py:id_en_contacto_por_disposicion` y
   `sistema_reproduccion.py:_macho_elegible_en_contacto` prometían
   desde su creación un desempate por id más bajo, pero dependían en
   la práctica del orden de iteración de un `set` de Python sin
   ordenar -- añadido `sorted()` explícito en ambos.
3. **Fuego en la propia celda nunca se percibía como amenaza**:
   `celda_percibida` excluye por diseño la celda propia (correcto para
   buscar comida/agua en OTRO sitio), así que un individuo de pie
   sobre fuego nunca lo detectaba por el camino de amenaza -- solo
   sufría el daño directo, sin ningún impulso de huir. Corregido en
   `nucleo/amenaza.py:posicion_amenaza_mas_cercana` (chequeo de la
   celda propia primero) y `sistema_movimiento.py:_calcular_huida`
   (caso especial para amenaza en la posición propia -- huir de uno
   mismo daría dirección (0,0), reemplazado por un paso aleatorio).
4. **Docstring falso**: `nucleo/percepcion.py:celda_percibida` decía
   que `sistema_movimiento.py` la reutiliza para buscar comida/agua --
   falso, esos escaneos siguen sin consolidar con ella. Corregido el
   texto.

**Consolidación de deuda técnica real, dos commits, ambos verificados
como refactors puros (comportamiento byte-idéntico)**:
- `0bcb230`: `_entidad_cercana_cualquiera`/
  `_entidad_cercana_cualquiera_con_id`/`_consciente_mas_cercano_con_id`
  (el mismo bucle de búsqueda por índice espacial repetido tres veces
  para HUIDA_ERRATICA/CRISIS_VIOLENTA/SOCIALIZAR, señalado como smell
  ya en la auditoría post-cierre del arco de comunicación del
  2026-09-07) fusionadas en `_buscar_entidad_cercana(...,
  solo_conscientes)`.
- `a723244`: los cinco bucles triple-anidados de `_procesar_roce_social`/
  `_procesar_robo`/`_procesar_compartir_confianza`/
  `_procesar_memoria_compartida`/`_procesar_rumor` sobre `por_celda`
  (crecido de 3 a 5 copias con el arco de robo/intercambio, mismo
  hallazgo del 2026-09-07) extraídos a `_pares_no_ordenados` (i<j, una
  vez por par) y `_pares_ordenados` (las dos direcciones). Verificado
  con el máximo rigor que exige este proyecto para un refactor: salida
  de `BOSQUE_AUTO_TICKS=2000` byte a byte idéntica antes/después con la
  misma semilla (mismos 52031 transferencias de memoria, 14950
  rumores, 2 robos, 2 comparticiones -- cero desplazamiento de la
  secuencia de `rng`).

Sonido: investigado como candidato de optimización del Bloque A,
descartado de inmediato -- `nucleo/sonido.py:sonido_mas_cercano` YA
estaba optimizado desde el Círculo 4 del 2026-09-08
(`ZonaBioma.sonidos_activos`), la cita original en mi propio plan era
un error de lectura mío, corregido antes de proponer nada.

### Tres círculos pequeños de mejora (`6459b7a`)

Diseñados e implementados directamente (pipeline sin disponibilidad en
este contenedor -- sin `OPENROUTER_API_KEY`/`mini-swe-agent`, mismo
patrón ya establecido varias veces en el proyecto).

**Decaimiento de afinidad**: `Relaciones` (rencor/amistad/pareja) solo
se acumulaba desde su diseño (2026-09-04) -- nunca se diluía con el
tiempo, hueco señalado en 3+ piezas distintas del arco de relaciones
sin cerrar nunca. `sistema_descomposicion.py:_decaer_relaciones` aplica
la misma ley "nada dura para siempre" que ya rige Necromasa/
Construccion/provisiones -- decaimiento multiplicativo SIMÉTRICO (mismo
ritmo para rencor y amistad, sin razón física para que un agravio dure
más que un afecto), purga por debajo de umbral, cadencia diaria,
universal (las 4 especies fauna, no solo consciente -- fauna también
escribe `Relaciones` vía afinidad por concepción).

**Piedras de percusión del fuego, se descartan en vez de acumularse**:
al diseñar "soltar objeto de Agarre" se encontró que ya estaba resuelto
para armas desde armas primitivas v2 (2026-09-03) -- el problema real,
más grave de lo que el pendiente de esa sesión documentaba, era que las
piedras gastadas se movían a `Inventario.objetos` con un tope de
transferencia que, verificado con un arnés dedicado contra el código
real, dejaba las piedras de CUALQUIER fuego posterior al primero
atascadas en `Agarre` para siempre -- ocupando el 100% de los puntos de
agarre de un gnomo, bloqueando cualquier arma futura de por vida.
Corregido descartándolas sin más al gastarse -- no son arma ni material
de construcción, no tienen uso futuro real.

**Llamada de alarma, tercer uso real de `nucleo/sonido.py`**: un
individuo que percibe una amenaza real (cualquiera de las tres fuentes
ya combinadas -- disposición por peso, valentía propia, sonido) puede
emitir su propio sonido en su posición -- reutiliza `sonido_mas_cercano`,
YA una fuente de amenaza para cualquier otro individuo cercano, sin
ningún consumidor nuevo que escribir. Calibración corregida tras un
primer smoke test real: `probabilidad_alarma_por_tick=0.3` disparó el
sonido total de ~1500 a ~47000 en 3000 ticks -- demasiado agresivo para
un grito ocasional, bajado a 0.05 ANTES de comitear, reverificado en
~6416.

Verificado los tres círculos juntos: 448/448 tests (17 nuevos),
`BOSQUE_AUTO_TICKS=3000` sin excepciones. Todos los valores nuevos
PROVISIONALES, sin calibrar contra el harness completo.

### Agarre pasa de reflejo de miedo a recurso físico compartido --
### "requisito de manos libres" (`83ad591`)

Diego cuestionó el diseño original de `Agarre` (armas primitivas v2,
2026-09-03) al verlo en la práctica: "debería ser un comportamiento
meramente físico, como lo es andar... ¿en qué momento necesitamos tener
puntos de agarre libres? Pues cuando nuestra intención es agarrar algo
-- quiero comer, pues tendré que tener al menos 1 mano libre, o si voy
a recolectar, o las dos manos libres si estoy cocinando". Hallazgo real
que confirmó el problema: ninguna Acción del motor comprobaba nunca si
tenía manos libres para ejecutarse -- `Agarre` solo existía como
depósito pasivo de armas.

Diseñado en conversación (`AskUserQuestion`, cinco decisiones cerradas
antes de escribir código):
- **Solo aplica a consciente** (gnomo hoy, mismo
  `umbral_consciencia_agencia`) -- fauna come/recolecta con boca o
  patas, sin mano que gatear (conejo tiene `puntos_agarre=0` fijo; un
  gate literal universal lo habría extinguido al instante).
- **Sin manos suficientes, la utilidad de esa Acción cae a 0.0 ese
  tick** -- sin mecanismo de "soltar forzado" (descartado el mismo día
  por sobreingeniería, con el hallazgo de piedras de fuego fresco en la
  memoria: un individuo ya tiene motivos reales para soltar cuando
  hacen falta -- CONSTRUIR/FABRICAR compiten por prioridad como
  siempre).
- **Manos requeridas**: COMER=1, RECOLECTAR=1, COCINAR=2, CONSTRUIR=1,
  FABRICAR_ARMA=2 (hoy `manos_requeridas_fabricar_arma`, sin renombrar
  en el rename posterior -- ver más abajo). CONSTRUIR=1 es
  deliberadamente el mismo para todo tipo de construcción hoy (todos
  primitivos, trabajo manual sin herramienta específica) -- un futuro
  "templo" que exigiera herramientas reales queda documentado como
  sistema pendiente, no construido (necesitaría fabricación de
  herramientas más allá de armas, que no existía en este momento de la
  sesión -- ver el círculo siguiente para cuándo se convirtió en el
  próximo real). ENCENDER_FUEGO ya tenía su propio requisito INVERSO
  (manos OCUPADAS con `piedra_suelta`), sin tocar.
- El reflejo de empuñar arma (`_ajustar_empunadura`) se queda como
  ajuste paralelo, sin tocar -- el nuevo gate ya lo hace competir de
  forma indirecta (si el arma ocupa manos, COMER/RECOLECTAR/COCINAR
  dejan de estar disponibles mientras siga empuñada).

`nucleo/armas.py:manos_libres(puntos_agarre, objetos_agarre) -> int` --
función pura nueva. Gate aplicado una sola vez al valor FINAL de cada
utilidad (tras cualquier eslabón heredado de RECOLECTAR), justo antes
de construir `candidatas`, en vez de repetir el chequeo en cada rama.
De paso: `puntos_agarre`/`Agarre` pasan a leerse una sola vez por
entidad al principio del bucle de `sistema_decision.py` (antes se
recalculaban en tres puntos distintos de la misma función).

**Verificado**: 461/461 tests (13 nuevos, incluidos los dos casos
límite de cada acción), `BOSQUE_AUTO_TICKS=3000` sin excepciones, y un
contador de observación nuevo confirma que el gate se dispara **16638
veces** en esa misma corrida -- se ejerce con fuerza real desde el
primer día, no "correcto pero invisible", sin disparar ninguna
mortalidad anómala por inanición. Todos los valores nuevos
PROVISIONALES, sin calibrar contra el harness completo.

### Robo extendido más allá de comida -- materiales de construcción y
### armas (`15a7aa1`)

Diego, tras cerrar manos libres, retomó robo: "el tema del robo es
interesante, no sé si sería muy factible que le puedas quitar algo de
la mano a alguien así sin más, pero de sus inventarios sí. Por otro
lado, ¿qué motiva el robo?". Dos decisiones cerradas antes de
implementar:

- **Agarre nunca es robable -- solo `Inventario`** (contenidos/
  objetos/provisiones). Lo activamente empuñado exigiría un mecanismo
  de desarme, distinto de un hurto discreto; Diego lo descartó de
  entrada con criterio físico simple.
- **Motivación, sin inventar una "necesidad de robar" nueva**: cada
  tipo de robo reutiliza la MISMA señal de déficit que el motor ya usa
  para decidir si RECOLECTAR/CONSTRUIR/FABRICAR_ARMA -- mismo patrón de
  herencia causal que el proyecto ya usa dos veces (RECOLECTAR hereda
  la utilidad de ENCENDER_FUEGO/FABRICAR_ARMA cuando faltan piedras/
  material). Comida: hambre (ya existía, círculo previo del
  2026-09-07). Materiales: falta de masa apta para el
  `objetivo_construccion_actual` del ladrón (mismo chequeo que ya usa
  RECOLECTAR/CONSTRUIR). Armas: inseguridad real (1 - seguridad, mismo
  driver que FABRICAR_ARMA), solo si el ladrón no porta ya ningún
  objeto `apto_arma` (ni empuñado ni guardado).

`_intentar_robo_material`/`_intentar_robo_arma`, mismo molde exacto que
`_intentar_robo` (mismo resolutor `resolver_disputa`, mismo_grupo/
familia → COMPARTE automático) llamados desde `_procesar_robo` junto al
ya existente. Robo de material transfiere vía `transferir_recurso`
(mismo primitivo dict-based, 2026-09-07); robo de arma manipula
`Inventario.objetos` directamente (lista de objetos discretos, mecánica
distinta de un dict de kg) con su propio chequeo de capacidad de carga.

**Verificado**: 471/471 tests (10 nuevos), `BOSQUE_AUTO_TICKS=3000` sin
excepciones. Robo de materiales se dispara con fuerza real en juego
libre (**1115 intentos, 24 exitosos** en esa corrida). Robo de armas en
0 en esta semilla concreta -- exige la combinación más rara de
inseguridad real + cero armas propias + víctima con algo guardado (no
empuñado); mismo patrón "correcto pero raro en esta semilla" ya visto
varias veces en este proyecto, necesita más semillas para observarse.
Todos los valores nuevos PROVISIONALES, sin calibrar.

### Rename Accion.FABRICAR_ARMA -> Accion.FABRICAR, genérico por
### categoría (`ec03777`)

Diego trajo una propuesta completa ya redactada (de una sesión/
instancia de Claude distinta, sin rastro visible en esta conversación
-- se le pidió explícitamente que la pegara entera antes de opinar,
mismo criterio de honestidad de siempre: nunca fingir memoria de algo
que no está en el contexto visible). Propuesta: renombrar
`Accion.FABRICAR_ARMA` → `Accion.FABRICAR`, con "arma" como única
categoría real implementada hoy (sin inventar "herramienta" todavía,
sin tocar COCINAR), pero con la mecánica ya preparada para que sumar
una segunda categoría el día que haga falta sea añadir un candidato al
resolutor interno, no crear `Accion.FABRICAR_HERRAMIENTA` desde cero.
`CREAR` (acción genérica de construir-cualquier-cosa) quedó fuera por
completo -- sin caso de uso real todavía, sería autoría de una acción
sin ley que la sostenga.

Objeción real planteada antes de aceptar sin más: construir
"infraestructura de resolutor" para un único candidato es sobre-
ingeniería si "herramienta" es solo hipotética. Diego la corrigió con
información nueva y concreta: **"el segundo círculo con el que nos
vamos a meter directamente es el tema de la fabricación de
herramientas"** -- herramienta no es hipotética, es el próximo círculo
real. Retirada la objeción, confirmado el diseño.

`Intencion` gana `fabricar_categoria: str = ""` (transitorio, no
persistido, mismo criterio que `recolectar_motivo_arma`).
`sistema_decision.py` resuelve la categoría ganadora con un resolutor
interno mínimo (`candidatos_fabricar: list[tuple[str, float]]` + `max()`,
mismo molde que `objetivo_construccion_actual:tipos_paralelos` del
2026-09-08), hoy con un único candidato ("arma"). `sistema_recursos.py:
_resolver_fabricar_arma` → `_resolver_fabricar`, gana el parámetro
`categoria: str` y un guard temprano (`if categoria != "arma": return`).
`recolectar_motivo_arma` se deja INTACTO a propósito -- confirmado en
la conversación de diseño que es un mecanismo independiente (RECOLECTAR
heredando utilidad del eslabón de FABRICAR), no parte de esta
generalización.

**Verificado**: 471/471 tests (actualizados los que referenciaban el
nombre anterior en `tests/test_armas_primitivas_v2.py` y
`tests/test_manos_libres.py`, incluidas 2 llamadas reales al método
renombrado, no solo texto), `BOSQUE_AUTO_TICKS=3000` sin excepciones.
Las menciones "renombrada desde FABRICAR_ARMA" que quedan en comentarios
(`sistema_decision.py`, `sistema_recursos.py`, `componentes/intencion.py`)
son históricas, intencionales -- mismo criterio de honestidad del resto
del proyecto.

### Pendiente real, explícito, tras esta sesión

- Los 4 bugs de la auditoría de código y los tres círculos pequeños
  (decaimiento, piedras de fuego, alarma) se verificaron con arneses
  dirigidos y `BOSQUE_AUTO_TICKS`, pero ninguno se midió contra el
  harness completo (15×12000) -- todos sus valores numéricos nuevos
  siguen PROVISIONALES.
- **El siguiente círculo real, ya confirmado por Diego, es fabricación
  de herramientas** -- `manos_requeridas_fabricar_arma` y el resolutor
  `candidatos_fabricar` de FABRICAR quedan ya preparados para ese
  círculo (un candidato "herramienta" más, sin Acción nueva que crear).
- `Accion.CREAR` (verbo genérico de construir-cualquier-cosa) queda
  explícitamente fuera de alcance hasta que exista un caso de uso real
  que lo justifique -- no autorar una acción sin ley que la sostenga.
- Si se retoma COCINAR bajo el mismo paraguas de FABRICAR (pregunta que
  quedó abierta en la propuesta original de Diego, nunca cerrada): el
  precedente en contra (COCINAR ya tiene su propia Acción con su propio
  gate de Fogata, sin ningún resolutor de categorías) sigue siendo
  válido -- no se ha decidido nada al respecto en esta sesión.
- Robo de armas sigue sin observarse en juego libre en ninguna semilla
  probada hasta ahora -- candidato a revisar con más semillas si se
  quiere confirmar que se dispara de verdad, no solo que es correcto
  por los tests dirigidos.
- Centinela del pipeline sigue parado en la máquina histórica; este
  contenedor sigue sin `OPENROUTER_API_KEY`/`mini-swe-agent` -- las 7
  piezas de esta sesión (4 fixes + 2 consolidaciones + 3 círculos +
  manos libres + robo + rename, en 7 commits) se implementaron todas
  directamente por Claude, sin pasar por el pipeline, mismo patrón ya
  establecido en sesiones recientes en este entorno concreto.
## Comodidad -- diseño del arco completo, Piezas A+B cerradas (piedra
## exige pico + catálogo de calidad_construccion), Piezas C/D pendientes
## (2026-09-14, mismo día)

Diego, tras cerrar tala real, cuestionó el propio diseño de "reutiliza
antes de inventar" desde otro ángulo, sin esperar a que se le preguntara:
*"hay que darle una vuelta a esto, porque no todo sirve, para empezar, lo
lógico es que los minerales no se puedan recoger sin intrumentos de
mineria, como un pico. y por otro lado, no todos los materiales deben
poder servir para construir, o quizas si pero no de igual manera, hay que
encontrar la forma de fomentar el desarrollo y la evolucion, quizas un
consciente en un punto inicial prioriza un refugio de arcilla, pero
cuando sus necesidades están medianamente cubiertas lo normal es que
busquen mejorar. quizas deberiamos empezar a plantear una nueva necesidad
de confort o comodidad, y que esa necesidad empuje al individuo y
sociedad a mejorar?"* -- tres hilos entrelazados: (1) gatear minerales
tras herramienta (la veta YA lo tenía desde Círculo 1, faltaba
extenderlo a piedra-como-sustrato), (2) diferenciar calidad de material
para construcción en vez de tratar todo `apto_construccion` como
fungible, (3) una necesidad nueva de comodidad que empuje a mejorar una
vez cubierta la supervivencia.

**Diagnóstico real que motivó la pregunta, encontrado ANTES de diseñar
nada** (pregunta directa de Diego: *"si las construciones básicas
precisan de madera por que no se da la tala de forma natural?"*):
`nucleo/construccion.py:masa_apta_construccion(materiales, catalogo)`
suma CUALQUIER material `apto_construccion` sin distinguir cuál -- la
demanda de construcción es puramente de masa agregada, nunca específica
de material. Como arcilla siempre está disponible y sin gate, satisface
la demanda de refugio/almacén antes de que madera (tala, exige hacha) o
piedra-vía-pico lleguen nunca a ser necesarios. Esto explica con
precisión por qué tala/minería, aunque mecánicamente correctas, resultan
casi invisibles en juego libre -- no falta motivo ni herramienta, falta
DEMANDA real de un material mejor que arcilla.

**Decisiones cerradas con Diego, `AskUserQuestion`, antes de escribir
código**: piedra como `tipo_sustrato` (cantera a granel) TAMBIÉN exige
pico -- *"hombre para coger piedra lo lógico es que tengas que picar
tambn, no? otra cosa son las piedras sueltas del suelo"* (piedra_suelta,
la de percusión de fuego, sigue libre a propósito -- una piedra
encontrada no es una cantera); calidad de material intrínseca y FIJA por
material (no por nivel de procesado -- más simple, y "roca tallada" ya
es intrínsecamente mejor que "tierra suelta" sin necesidad de ningún
paso de elaboración intermedio); la nueva necesidad va en un campo
GENUINAMENTE NUEVO de `Necesidades` (no reutilizar
`CapacidadMental.voluntad`, que ya tiene su propio consumidor real desde
aptitud vocacional -- mezclar ambos habría sido acoplar dos leyes
distintas sin necesidad).

**Reencuadre de alcance, pedido por Diego**: *"el problema es que la
comodidad de la que hablamos tiene que ser un motor general, desarrollo
de 'tecnologias', mejoras para vivir, etc. y luego quizas enlazarlo con
el ocio para que nazca el 'arte'. entiendes por donde voy?"* -- comodidad
como necesidad de nivel superior genuinamente genérica (no solo
vivienda), con una conexión futura a ocio (`Accion.SOCIALIZAR`, ya
existe) para dar pie a "arte" en un horizonte lejano. Acordado
explícitamente reducir el ALCANCE del círculo actual a solo vivienda
(el consumidor más simple y ya cableado) sin cerrar la puerta al resto
-- Diego lo aceptó ("me parece bien") pero pidió que la integración con
los flujos ya existentes quedara planteada de forma concreta, no solo
abstracta.

**Corrección semántica real, encontrada al diseñar la integración**:
`decision.umbral_atencion_pareja` (el gate Maslow genérico -- "ninguna
necesidad de nivel superior compite mientras alguna de las 4
necesidades físicas esté baja") YA tenía tres consumidores reales antes
de comodidad (`BUSCAR_PAREJA`, su origen; `SOCIALIZAR`, desde
2026-09-06; el gate de concepción de `sistema_reproduccion.py`, desde
2026-08-31) -- su nombre ya estaba desfasado, no por comodidad sino por
uso previo nunca corregido. Diego: *"usemos el mismo, pero habrá que
hacer que semanticamente deje de estar relacionado con pareja, porque
ahora lo consumiran otros flujos, no?"* -- renombrado a
`decision.umbral_necesidades_superiores` (commit `4faf293`, puro rename,
comportamiento byte-idéntico verificado con `BOSQUE_AUTO_TICKS=3000`
contra el run de tala real inmediatamente anterior -- mismos contadores
exactos).

**Roadmap de 4 piezas acordado, D es la pieza grande, ninguna de las dos
últimas empezada todavía**:
- **Pieza A** (este círculo): piedra-sustrato exige pico.
- **Pieza B** (este círculo): catálogo `calidad_construccion` [0,1] por
  material, sin consumidor mecánico todavía -- mismo patrón "catálogo
  antes que mecanismo" ya usado con `toxico_crudo` antes de "cómo
  cocinar".
- **Pieza C** (siguiente, sin empezar): `Necesidades.comodidad` como
  campo nuevo, con mecanismo de deriva hacia un objetivo derivado de la
  calidad media ponderada de los materiales del refugio propio ya
  completado (`Construccion.materiales`, sin campo nuevo en
  `Construccion` -- se deriva, no se persiste aparte).
- **Pieza D** (la grande, sin empezar): `necesidad_trabajo` en
  `sistema_decision.py` (hoy `max(utilidad_recolectar,
  utilidad_construir)`) gana un tercer input -- el déficit de comodidad,
  SOLO activo tras `completado_alguna_vez=True` y gateado por
  `umbral_necesidades_superiores` sobre las 4 necesidades físicas (mismo
  patrón exacto que `BUSCAR_PAREJA`). `CONSTRUIR` necesita un modo
  "mejora" nuevo para seguir vivo más allá de `completado_alguna_vez`
  (añadir material de mejor calidad al MISMO refugio sin crecer
  `huella_m2`), autolimitado sin techo autorado -- se satura solo cuando
  `calidad_media` alcanza el mejor material realmente disponible en la
  zona.
- Parked, contingente: una pieza 5 de sesgo de movimiento hacia veta/
  árbol conocido (mismo patrón que refugio/manada/agua en
  `MemoriaEspacial`), solo si tras la Pieza D minería/tala siguen
  invisibles en juego libre.
- Explícitamente FUERA de alcance de este arco por ahora (decisión de
  Diego, "me parece bien" a la reducción de alcance propuesta):
  generalizar comodidad a dominios no habitacionales (calidad de
  herramienta, calidad de comida), y la conexión ocio→arte -- ambas
  quedan como visión declarada, sin una sola línea de diseño todavía.

### Piezas A+B -- implementadas y verificadas (2026-09-14, mismo día)

**Pieza A**: `sistemas/sistema_recursos.py:_resolver_recolectar`, el
fallback terminal de `tipo_sustrato` gana un gate específico -- si
`material == "piedra"`, exige `tiene_herramienta(objetos_para_bono,
self.recetas_mineria)` (mismo catálogo de pico ya usado por la
extracción de veta, Círculo 1) antes de producir nada; sin pico, el tick
simplemente no produce (no hay ningún nivel más abajo al que caer, a
diferencia de veta/tala que sí caen a algo más). arcilla/tierra/
tierra_negra/marga/grava siguen sin gate ("se cavan a mano, no se
pican"). Contador de observación
`_stats_piedra_sustrato_bloqueada_sin_pico` nuevo. Verificado sin
dependencia circular: el material crudo "piedra" que alimenta la receta
de `pico` viene de `piedra_suelta` (`nucleo/armas.py`, solo mira
`celda.recursos`, nunca `tipo_sustrato`) -- un gnomo siempre puede
fabricar su primer pico sin haber cavado cantera nunca.

**Pieza B**: `config/materiales.yaml` gana `calidad_construccion` [0,1]
en los 11 materiales `apto_construccion: true` (PROVISIONAL, razonado a
mano contra `dureza`/naturaleza real del material, sin calibrar contra
el motor): tierra=0.15, hierba_seca=0.15, tierra_negra=0.15, fibra=0.2,
marga=0.22, arcilla=0.3, grava=0.35, madera=0.55, cobre=0.75,
piedra=0.85, hierro=0.95 -- eje DISTINTO de `dureza` (cuánto cuesta
trabajarlo, no el resultado), correlacionado a grandes rasgos pero no
idéntico. Sin ningún consumidor mecánico todavía -- solo catálogo, la
Pieza C es quien lo leerá.

**Verificado**: 541/541 tests en verde (8 nuevos,
`tests/test_piedra_sustrato_pico.py` -- gate con/sin pico, fallback
terminal no cae a nada más sin pico, hacha_primitiva no gatea (cada
herramienta abre solo su propio catálogo), arcilla/tierra siguen sin
gate, piedra_suelta sigue gratuita, catálogo de calidad_construccion
completo/ausente donde corresponde, orden cualitativo metal/piedra >
tierra/barro). Un test preexistente de minería (`test_mineria_real.py:
test_ley_sin_pico_cae_a_sustrato_en_vez_de_bloquearse`) usaba una celda
con `tipo_sustrato="piedra"` como fallback -- ahora también gateada,
corregido a `tipo_sustrato="arcilla"` para aislar el comportamiento que
ese test valida (fallback de veta) del gate nuevo de piedra.
`BOSQUE_AUTO_TICKS=3000` con la semilla por defecto, sin ninguna
excepción: **398 bloqueos reales de piedra-sustrato sin pico** -- se
ejerce con fuerza real desde el primer día, muy por encima de veta (2) y
tala (149) en la misma corrida (piedra es, con diferencia, el
`tipo_sustrato` más común del catálogo de montaña). `BOSQUE_CONTINUAR=1`
(200 ticks más) sin excepciones -- roundtrip limpio, sin campos nuevos
persistidos por esta pieza.

**Pendiente real, explícito**: `calidad_construccion` sigue sin ningún
efecto sobre el motor -- catálogo puro hasta la Pieza C; los 11 valores
y el propio gate de piedra son PROVISIONALES, sin calibrar contra el
harness completo; Piezas C y D (comodidad de verdad, el driver de
mejora) son el siguiente trabajo real de este arco, sin empezar
todavía.

### Pieza C -- `Necesidades.comodidad`, cerrada (2026-09-14, mismo día)

`componentes/necesidades.py` gana `comodidad: float = 0.0`, mismo
molde de deriva-hacia-objetivo que `confort_termico` (a diferencia de
ese campo, sigue la convención estándar del resto del fichero --
1.0=satisfecho, 0.0=nada, no 0.5 como ideal). `nucleo/construccion.py:
calidad_media_construccion(materiales, catalogo)` (nueva, pura): media
de `calidad_construccion` (Pieza B) ponderada por masa, 0.0 si no hay
ninguna masa con calidad declarada -- reutiliza el mismo patrón
permisivo por `.get()` que `masa_apta_construccion`.
`sistema_necesidades.py` calcula el objetivo cada tick (bloque 4b, justo
tras confort térmico): 0.0 sin refugio propio, 0.0 mientras el refugio
propio no esté `completado_alguna_vez`, si no
`calidad_media_construccion` del `Construccion.materiales` del refugio
propio -- SOLO para CONSCIENTE (mismo umbral que ya gatea CONSTRUIR/
RECOLECTAR; fauna nunca construye refugio propio, así que gatear
explícitamente evita un escaneo O(N) de construcciones por individuo
sin necesidad real, no solo un atajo semántico).
`tasa_deriva_comodidad=0.02` nueva (PROVISIONAL, algo más lenta que la
térmica 0.03 a propósito -- la comodidad de un hogar no debería
sentirse de golpe en un tick). Persistido: `comodidad` añadida como
ÚLTIMA columna de `componentes_estado` (deliberadamente al final, no
intercalada -- evita renumerar las docenas de índices posicionales
`fila[N]` ya usados por el resto de `nucleo/persistencia.py` al
cargar), `VERSION_ESQUEMA` sube a `0.39-fase0`. Sin ningún consumidor
todavía -- ni utilidad en la Utility AI, ni mortalidad, ni drenaje de
otro pool depende de su valor; la Pieza D es quien lo leerá.

**Verificado**: 551/551 tests en verde (10 nuevos,
`tests/test_comodidad.py` -- `calidad_media_construccion` en sus cuatro
casos (ponderada por masa, no por conteo; vacía; ignora material no
apto), objetivo 0.0 sin refugio, objetivo 0.0 mientras no está
completado, deriva hacia la calidad real con refugio completado, baja
si el objetivo cae por debajo del valor actual (refugio que se degrada
por decomposición), gate de consciencia, tope exacto sin pasarse del
objetivo). `BOSQUE_AUTO_TICKS=3000` con la semilla por defecto: mismos
contadores exactos que antes de esta pieza (398 bloqueos de piedra, 149
de tala, etc.) -- confirma que Pieza C es puramente aditiva, sin ningún
efecto en decisión todavía, ninguna excepción. `BOSQUE_CONTINUAR=1`
(200 ticks más) sin excepciones -- roundtrip limpio, y consultada la
base de datos real (no solo "no lanzó excepción"): **9 gnomos con
`comodidad > 0` tras la corrida**, valores reales entre 0.15 y 0.285 --
coherente con refugios de arcilla (calidad_construccion=0.3, techo real
que la deriva todavía no había alcanzado) -- el mecanismo se ejerce de
verdad en juego libre desde el primer día, no "correcto pero
invisible".

**Pendiente real, explícito**: `tasa_deriva_comodidad=0.02` sigue
PROVISIONAL, sin calibrar; `Necesidades.comodidad` sigue sin ningún
consumidor -- Pieza D (`necesidad_trabajo` gana el déficit de comodidad
como tercer input, gateado tras `completado_alguna_vez` por
`umbral_necesidades_superiores`, más un modo "mejora" nuevo de
CONSTRUIR para poder seguir aportando material de mejor calidad al
refugio ya completado sin crecer `huella_m2`) es el siguiente trabajo
real de este arco, sin empezar todavía -- es la pieza que de verdad da
propósito a `calidad_construccion` y `comodidad` juntos.

### Pieza D -- mejora de vivienda, cierra el arco de comodidad (2026-09-14,
### mismo día)

La pieza "grande" del arco -- diseñada en conversación con Diego
(`AskUserQuestion`) antes de tocar código, dado su impacto de
comportamiento real (reactiva RECOLECTAR/CONSTRUIR tras completar el
refugio, algo que ningún círculo anterior hacía). Dos decisiones
cerradas: **autolimitación por comparación local real** (no un déficit
puro como fuego/arma -- Diego rechazó explícitamente esa vía por no
autolimitarse); **prioridad comunal-vs-personal por temperamento**, idea
de Diego: *"un individuo más empático y sociable aportaría antes a los
edificios comunes... el que busque su comodidad primero"*.

**Hallazgo real al diseñar, antes de escribir código**: `_resolver_construir`
corta en cuanto `construccion.progreso >= 1.0`, y
`objetivo_construccion_actual` ya no vuelve a señalar el refugio una vez
completo -- "mejorar sin crecer `huella_m2`" no puede reutilizar el
mecanismo de acumulación tal cual. Se necesita un mecanismo de
**sustitución**: cambiar material de peor calidad por uno mejor,
manteniendo la masa total constante.

**Arquitectura, mismo patrón `recolectar_motivo_X` ya usado 4 veces en
este arco (fuego/arma/herramienta/mineria)**, ahora retrofitado a
CONSTRUIR: `Intencion.construir_motivo_mejora: bool` (transitorio, no
persistido) -- cuando `sistema_decision.py` marca CONSTRUIR como
motivado por mejora, `sistema_movimiento.py`/`sistema_recursos.py`
ignoran por completo `objetivo_construccion_actual` y resuelven contra
el refugio propio directamente.

- `nucleo/construccion.py:material_mejora_disponible_en` (nueva, pura):
  peek de solo lectura -- qué material recolectaría RECOLECTAR aquí
  mismo ahora (mineral>tala>flora a granel>sustrato, mismo orden que la
  resolución real), sin mutar nada. Simplificación deliberada y
  documentada: no aplica el filtro de "recurso competidor disponible"
  (una imprecisión aquí es inofensiva, el gate real sigue viviendo en
  `_resolver_recolectar` -- esto solo genera un atractor de interés).
- `sistema_decision.py`, nuevo bloque tras "FABRICAR categoria mineria":
  gateado a consciente + `not fisica_bajo_umbral` (mismo gate Maslow que
  BUSCAR_PAREJA/SOCIALIZAR) + refugio propio `completado_alguna_vez`.
  `sesgo_prosocial = (empatía+sociabilidad)/2` decide, cuando la cadena
  comunal (almacén/salón/cocina) sigue pendiente, si se prioriza lo
  comunal (sin tocar nada, la utilidad ya calculada arriba se queda) o
  la comodidad propia (por debajo de `umbral_prosocial_comunal=0.5`,
  PROVISIONAL). RECOLECTAR-mejora eleva `utilidad_recolectar` a
  `1.0-comodidad` SOLO si `material_mejora_disponible_en` devuelve algo
  con más calidad que la ya invertida; CONSTRUIR-mejora eleva
  `utilidad_construir` SOLO si el Inventario YA porta algo mejor que el
  peor material ya invertido en el refugio -- sin techo autorado en
  ningún sitio, ambas se saturan solas.
- **RECOLECTAR-mejora no necesita ningún código nuevo en
  `sistema_recursos.py`**: ninguno de los cuatro flags
  `recolectar_motivo_X` se activa (mejora no es ninguno de los cuatro
  eslabones existentes), así que la resolución cae directamente al
  bulk cascade YA incondicional (mineral/tala/flora/sustrato) --
  exactamente lo que hace falta, reutilización perfecta sin tocar nada.
- `sistema_recursos.py:_resolver_mejora_refugio` (nueva): retira hasta
  `tasa_mejora_refugio_kg_tick` (PROVISIONAL, `config/materiales.yaml`)
  del material de PEOR `calidad_construccion` ya invertido y lo
  sustituye por el de MEJOR calidad ya portado -- masa total constante.
- `sistema_movimiento.py:_calcular_construir` gana la rama
  `construir_motivo_mejora`: camina directamente hacia el refugio propio
  ya existente (mismo `_acercarse_a` de siempre, sin ningún sesgo de
  agrupamiento nuevo -- el refugio ya tiene posición fija).

**Verificado**: 569/569 tests en verde (18 nuevos,
`tests/test_mejora_vivienda.py` -- las 6 leyes del peek de solo
lectura, las 4 leyes de `_resolver_mejora_refugio` (sustitución, no-op
sin nada mejor portado, tope por masa disponible, no-op sin materiales
en el refugio), 3 de navegación en `_calcular_construir`, y 5 de
integración completa en `sistema_decision.py` incluidas las dos leyes
de prioridad de carácter -- prosocial sigue con lo comunal, egoísta
antepone su comodidad). Una corrección real encontrada al escribir el
test de prioridad prosocial: el primer intento comparaba `cid_objetivo
is not None` para decidir si la cadena comunal seguía pendiente, pero
`cid_objetivo` es `None` tanto si no hay nada pendiente COMO si el
almacén está pendiente pero su `Construccion` todavía no se ha creado
-- corregido a comparar la tupla `objetivo` completa (`is not None`),
la señal correcta. Tres tests preexistentes de `test_ocio_consciente_socializar.py`
rompieron al introducir esta pieza -- su fixture `_refugio_terminado`
creaba un refugio con `materiales={}` (calidad 0.0, un refugio "vacío"
sin sentido físico para este nuevo sistema) y `Necesidades.comodidad`
quedaba en su default 0.0, dando un déficit artificial de 1.0 que
disparaba RECOLECTAR-mejora sin motivo real -- corregido dándole al
refugio de prueba materiales reales (arcilla, `masa_minima_refugio`) y
sincronizando `comodidad` con esa calidad real, mismo estado que
tendría un gnomo genuinamente asentado.

`BOSQUE_AUTO_TICKS=3000` con la semilla por defecto, sin ninguna
excepción: **CONSTRUIR elegido por mejora 3 veces, 2 sustituciones
reales** -- el mecanismo se ejerce de verdad en juego libre desde el
primer día, no "correcto pero invisible" como varias piezas anteriores
de este proyecto. `BOSQUE_CONTINUAR=1` (200 ticks más) sin
excepciones -- roundtrip limpio (ningún campo nuevo persistido por
esta pieza, `construir_motivo_mejora` es transitorio).

**Con esto, las 4 piezas del arco de comodidad quedan cerradas**
(A: piedra exige pico: B: catálogo de calidad; C: `Necesidades.comodidad`;
D: mejora de vivienda) -- el arco completo que arrancó de la pregunta
de Diego *"¿cómo fomentar el desarrollo y la evolución... quizás una
necesidad de confort?"*.

**Pendiente real, explícito**: `umbral_prosocial_comunal=0.5` y
`tasa_mejora_refugio_kg_tick=1.0` PROVISIONALES, sin calibrar contra el
harness completo; ningún criterio maestro de Diego (5 especies vivas a
la vez) remedido con esta pieza ya aplicada -- el cambio afecta solo a
gnomo consciente, riesgo de desplazamiento de secuencia de `rng` bajo
pero no nulo, no medido; visión más amplia de Diego (comodidad como
motor GENERAL de "tecnologías" más allá de vivienda, conexión con ocio
para dar pie a "arte") deliberadamente fuera de alcance de este arco,
sin ningún diseño todavía -- horizonte futuro, no descartado.

## Asentamiento como entidad propia -- arco nuevo, Pieza 1 (identidad
## persistente) cerrada (2026-09-15)

Diego, con el núcleo social ya medianamente construido (relaciones,
manada, salón común, cocinas, comodidad -- todo lo de arriba), planteó
la pregunta de fondo: *"quizás es momento de empezar a pensar como
vamos a estructurar un asentamiento como entidad propia, con sus
propias necesidades, interacciones, etc. porque es algo base de una
sociedad."* Clasificada explícitamente como diseño conceptual (no
calibración, no implementación directa) -- Diego pidió primero un
**informe de alternativas**, mismo patrón ya usado para "hilo
individual" (2026-09-04): investigar el código real, presentar piezas
distinguibles con sus dependencias, sin comprometerse a ninguna hasta
que Diego decida el orden.

**Hallazgo real durante la investigación, no anticipado**: `Asentamiento`
(`nucleo/asentamiento.py`) es un dataclass 100% derivado -- se
recalcula ÍNTEGRO cada día desde cero por proximidad de refugios
(`agrupar_por_proximidad`), sin ninguna identidad persistida entre
recálculos, mismo criterio que `pendiente_local`. Verificando por qué
esto podía ser un problema real (no solo teórico) para cualquier pieza
que quisiera dar "necesidades propias" a un asentamiento, se encontró
un **bug real, nunca detectado por los tests existentes** (todos
probaban escenarios estáticos, no evolución día a día):
`SistemaAsentamiento.ejecutar()` decidía si emitir el evento
`AsentamientoFundado` comparando el conjunto EXACTO de miembros de hoy
contra `self._miembros_vistos_ayer` -- cualquier fluctuación de
población (un miembro muere, nace, o su refugio queda fuera del radio
de clúster ese día concreto) hacía que el conjunto ya no coincidiera
byte a byte, y el sistema volvía a tratarlo como un pueblo NUEVO,
reemitiendo el evento HISTÓRICO para lo que en realidad es el mismo
asentamiento con composición cambiante.

**Informe entregado, 6 piezas distinguibles** (identidad persistente
como prerrequisito; necesidades colectivas agregadas; efecto de vuelta
hacia los miembros; interacción entre asentamientos; nombre propio +
crónica; posible unificación con el roadmap ya vivo de
"asentamientos/profesiones", ver `docs/historial_profesiones.md`),
recomendando empezar por identidad persistente -- sin ella, cualquier
"necesidad colectiva" que se fuera a diseñar después no tendría un
sujeto estable al que atribuírsela (una necesidad que se resetea cada
vez que el id cambia no es una necesidad real). Diego aprobó ("adelante
si"), pidiendo primero `git pull` de master (se recogió de paso un pull
grande y no relacionado de otra sesión: la poda de este mismo CLAUDE.md
a los ficheros `docs/historial_*.md`, commit `cac1b25`/merge `4872988`).

### Diseño e implementación (spec, implementado directamente por Claude)

Spec: `docs/superpowers/specs/2026-09-15-identidad-persistente-asentamiento-design.md`.
Implementado directamente -- mismo escenario ya documentado
repetidamente en las últimas sesiones: este contenedor cloud no tiene
`OPENROUTER_API_KEY` ni `mini-swe-agent`/centinela, y Diego lo pidió
explícitamente.

- `nucleo/asentamiento.py:resolver_identidades_persistentes(grupos_hoy,
  registro_anterior, umbral_continuidad) -> dict[int, frozenset[int]]`
  (nueva, pura): continuidad por **coeficiente de Jaccard**
  (`|intersección|/|unión|`) en vez de igualdad exacta de conjunto --
  cada clúster de hoy hereda el id de ayer con mayor solape si supera
  `umbral_continuidad` (0.5, PROVISIONAL, `config/comportamiento.yaml`);
  si no, recibe el siguiente id consecutivo al mayor ya visto.
  Simplificación deliberada y documentada: si dos clústeres de hoy
  compiten por el mismo id anterior, gana el de mayor solape -- el otro
  recibe id nuevo; sin tracking real de fusión/escisión (fuera de
  alcance, principio 2).
- `Asentamiento` gana `tick_fundacion: int = 0` -- momento real de
  fundación, no el día del recálculo actual.
- El registro de continuidad (qué id corresponde a qué miembros ayer, y
  cuándo se fundó cada uno) vive en `Mundo`, no en `Asentamiento`
  (que sigue siendo 100% derivado): `mundo.asentamiento_registro_
  identidad: dict[int, frozenset[int]]` y `mundo.asentamiento_tick_
  fundacion: dict[int, int]`, ambos SÍ persistidos -- reutilizando la
  tabla genérica `configuracion_ejecucion` (la misma que ya guarda
  `rng_juego_state`/`rng_reproduccion_state`), sin tabla nueva y sin
  subir `VERSION_ESQUEMA` (sigue en `0.39-fase0`).
- `SistemaAsentamiento.ejecutar()`: retira `_miembros_vistos_ayer`,
  construye los clústeres válidos del día (filtrados por
  `poblacion_minima_asentamiento`), resuelve sus ids vía la función
  nueva, y emite `AsentamientoFundado` únicamente cuando el id es
  genuinamente nuevo (no estaba en el registro anterior) -- cierra el
  bug de reemisión de raíz.

**Verificado**: 10 tests nuevos
(`tests/test_identidad_persistente_asentamiento.py` -- 7 leyes de la
función pura: churn en ambas direcciones, sin solape suficiente,
registro vacío, no-doble-reclamo del mismo id anterior, id consecutivo;
2 de integración real con `SistemaAsentamiento.ejecutar()` de punta a
punta -- pierde un miembro y conserva el id sin reemitir el evento,
`tick_fundacion` se conserva entre días; 1 de roundtrip de
persistencia). Dos tests fallaron al primer intento por usar solo 3
fundadores (al quitar 1 quedaban 2, por debajo de
`poblacion_minima_asentamiento=3`) -- corregidos a 4 fundadores.
`BOSQUE_AUTO_TICKS=3000` y `BOSQUE_CONTINUAR=1` (roundtrip) sin
ninguna excepción. Commit `ad7b28b`.

**Corrección honesta sobre el propio commit**: el mensaje de `ad7b28b`
dice "598/598 tests en verde" -- es incorrecto, un error de conteo al
escribirlo. El número real, verificado con `pytest -q` antes y después
del commit, es **590 passed**. No se ha amendado el commit ya empujado
(regla del proyecto: nunca reescribir historia ya pusheada sin que
Diego lo pida explícitamente) -- se corrige aquí, con la misma
disciplina de honestidad que el resto de este documento.

**Diagnóstico de juego libre** (scratchpad, 4 semillas nuevas
401001-401004 × 5000 ticks, sin ningún escenario dirigido a mano):
confirma la ley en condiciones no escritas para la ocasión --

- Semilla 401002: un asentamiento nace con 3 miembros en el tick 2663 y
  **conserva el mismo id=1** mientras crece a 5 y luego a 6 miembros a
  lo largo de ~2200 ticks -- exactamente el caso que antes habría
  reemitido el evento en cada cambio de tamaño.
- Semilla 401004: **tres asentamientos distintos** nacen en momentos
  distintos (tick 191, 3071, 4031) con ids 1, 2 y 3 -- nunca se
  confunden entre sí; el primero (id=1) crece de 3→4→5 miembros sin
  perder su identidad, mientras los otros dos permanecen estables en 3.
- En las 4 semillas, el número de eventos `AsentamientoFundado` coincide
  exactamente con el número de ids genuinamente nuevos -- ninguna
  reemisión espuria.

**Pendiente real, explícito**: `umbral_continuidad_identidad=0.5`
PROVISIONAL, sin calibrar contra el harness completo; con esto la
Pieza 1 queda cerrada -- las Piezas 2-6 del informe (necesidades
colectivas agregadas, efecto de vuelta hacia miembros, interacción
entre asentamientos, nombre propio + crónica, unificación con el
roadmap de profesiones) siguen sin empezar, a la espera de que Diego
decida el orden.

## Conocimiento colectivo transmisible -- fusión del roadmap
## "asentamientos/profesiones" con el informe "asentamiento como
## entidad propia", cerrado el mismo día (2026-09-15)

Diego, con la Pieza 1 ya cerrada, eligió explícitamente "unificar con
roadmap de profesiones" en vez de seguir con cualquiera de las otras
piezas sueltas del informe -- decisión tomada vía pregunta directa
(`AskUserQuestion`), no autorada. Antes de diseñar nada, se recuperó el
roadmap real ya aprobado el 2026-09-12 para "asentamientos/profesiones"
(`docs/historial_profesiones.md`) para no diseñar dos veces la misma
idea: 4 pasos -- (1) calidad de materiales, CERRADO (comodidad Pieza
B); (2) niveles de construcción, parcialmente resuelto por comodidad
Pieza D (mejora CONTINUA, sin categorías nombradas -- pregunta abierta
sin cerrar sobre si eso ya basta); (3) conocimiento como componente
propio, transmisible, aparcado sin spec en su momento porque
`Asentamiento` no tenía identidad estable; (4) tipos de construcción
nuevos, sin empezar.

**El punto de fusión real**: la Pieza 3 del roadmap de profesiones
("conocimiento... transmisible, no solo un stat que muere con el
individuo") y las Piezas 2-3 del informe de hoy ("necesidades/
capacidades colectivas agregadas" + "efecto de vuelta hacia miembros")
son la misma pregunta de diseño -- algo que se acumula a nivel de
pueblo y repercute hacia atrás en sus miembros. La razón por la que
"conocimiento" quedó aparcado el 12-09 sin spec es que `Asentamiento`
no tenía sujeto estable al que atribuírselo -- la Pieza 1 de esta misma
sesión (identidad persistente) es exactamente el prerrequisito que
faltaba, cerrado sin saber en su momento que serviría para esto.

Roadmap unificado propuesto y aprobado ("adelante"): tras calidad de
materiales/mejora continua (ya cerradas), conocimiento colectivo es el
siguiente círculo real; tipos de construcción nuevos y interacción
entre asentamientos vienen después (consumidores de este); nombre
propio + crónica queda como pieza acotada y de bajo riesgo, intercalable
en cualquier momento.

### Diseño e implementación

Spec: `docs/superpowers/specs/2026-09-15-conocimiento-colectivo-design.md`.
Implementado directamente por Claude (mismo escenario de toda la
sesión: sin `OPENROUTER_API_KEY`/`mini-swe-agent`/centinela en este
contenedor).

- `nucleo/conocimiento.py` (nuevo): funciones puras sobre las 4 cubetas
  ya existentes de `nucleo/vocacion.py:CUBETAS` (forrajero/constructor/
  artesano/cocinero) -- `registrar_contribucion` (suma topada),
  `erosionar` (decaimiento multiplicativo diario, mismo patrón que
  `Relaciones` pero 4x más lento -- `tasa_erosion_conocimiento_dia=0.005`
  frente a `relaciones.tasa_decaimiento_dia_afinidad=0.02`, porque el
  oficio de un pueblo no se olvida a la misma velocidad que un vínculo
  emocional individual), `nivel_conocimiento` (saturación lineal [0,1],
  `escala_saturacion_conocimiento=2000.0`), `factor_conocimiento_colectivo`
  (multiplicador de TASA `1.0 + peso*nivel`, **sin penalización por
  debajo de 1.0** -- decisión deliberada distinta de `factor_aptitud`:
  un asentamiento recién fundado no es peor que un individuo disperso,
  solo carece todavía del bonus).
- `Mundo.asentamiento_conocimiento: dict[int, dict[str, float]]` (llave
  = `Asentamiento.id`, la identidad estable de Pieza 1) -- persistido
  igual que el registro de identidad, reutilizando
  `configuracion_ejecucion`, sin bump de esquema. A diferencia de
  `Vocacion` (contador por individuo, se pierde con él), este valor
  sobrevive a la muerte de cualquier miembro -- "transmisible" en el
  sentido más simple posible, nunca fue propiedad de una persona.
- Acumulación: el mismo punto donde ya se incrementa `Vocacion`
  (`SistemaRecursos._incrementar_vocacion`, en el despacho de
  RECOLECTAR/CONSTRUIR/FABRICAR/COCINAR) suma +1.0 a la cuenta bruta del
  asentamiento del individuo, si pertenece a uno
  (`nucleo.asentamiento.asentamiento_de`, ya existente desde Pieza 1) --
  reutiliza exactamente el disparador ya existente, sin ningún evento
  nuevo. `asen` se resuelve UNA vez por entidad consciente en
  `ejecutar()`, reutilizado tanto para el bono de tasa (antes de
  resolver) como para la acumulación (después).
- Erosión diaria: `SistemaAsentamiento._erosionar_conocimiento_diario`,
  aplicada con independencia de si hoy existe algún asentamiento vivo
  (entradas de un id ya retirado del registro simplemente quedan
  inertes, nunca purgadas -- mismo criterio de laissez-faire que
  `Relaciones.vinculos` apuntando a un id ya muerto).
- Efecto de vuelta: multiplicador de tasa en los tres puntos donde ya
  existía un bono equivalente por herramienta -- RECOLECTAR
  (`tasa_recoleccion_efectiva`, cubeta "forrajero"), CONSTRUIR
  (`tasa_aporte_efectiva` Y `tasa_mejora_refugio` de la Pieza D de
  comodidad, cubeta "constructor"), COCINAR (`tasa_cocinar_kg_tick`,
  cubeta "cocinero"). **Deliberadamente sin efecto para "artesano"**:
  FABRICAR es determinista/instantáneo (sin ninguna tasa continua que
  acelerar), así que esa cubeta acumula y se puede consultar igual que
  las otras tres, pero sin ningún consumidor de comportamiento todavía
  -- hueco honesto, no un error, candidato real para cuando exista
  "tipos de construcción nuevos" (podría gatear recetas por nivel de
  conocimiento artesano del pueblo).

**Verificado**: 608/608 tests en verde (18 nuevos,
`tests/test_conocimiento_colectivo.py` -- las funciones puras en sus
leyes (suma topada, decaimiento con purga, saturación, factor sin
penalización), acumulación real vía `_incrementar_vocacion` con y sin
asentamiento, conocimiento sobreviviendo a `gestor.eliminar_entidad`
del individuo que lo aportó, comparación directa de
`_resolver_recolectar` con/sin bono confirmando que la cantidad
recolectada escala EXACTAMENTE con el factor, erosión diaria real vía
`SistemaAsentamiento.ejecutar()`, roundtrip de persistencia).
`BOSQUE_AUTO_TICKS=3000` y `BOSQUE_CONTINUAR=1` (roundtrip) sin ninguna
excepción -- con la semilla por defecto, 0 asentamientos llegaron a
formarse en esa corrida concreta (mismo patrón ya visto varias veces en
este proyecto: la formación de asentamiento con la semilla por defecto
es poco fiable en ventanas cortas), así que el propio smoke test no
tuvo nada que acumular -- esperado, no un fallo.

**Diagnóstico de juego libre, resultado mucho más fuerte de lo
habitual**: reutilizando las mismas 4 semillas nuevas
(401001-401004 × 5000 ticks) que ya habían confirmado formar
asentamiento real en la verificación de la Pieza 1 (mismo día) --
**las 4 acumularon conocimiento colectivo real, con niveles
significativos, no solo trazas**:

- Semilla 401001: forrajero 0.454, constructor 0.786.
- Semilla 401002: forrajero **saturado a 1.0**, constructor 0.311,
  artesano 0.001 (trazas, coherente con FABRICAR siendo raro).
- Semilla 401003: forrajero 0.04, constructor 0.221.
- Semilla 401004 (2 asentamientos simultáneos, sin mezclarse entre
  sí -- confirma aislamiento correcto por id): asentamiento 1 con
  forrajero saturado a 1.0 y artesano 0.002; asentamiento 2 con
  forrajero 0.481, constructor 0.208.

A diferencia de varias piezas anteriores de este proyecto que quedaron
"correctas pero invisibles" en juego libre durante semanas (asentamiento
mismo en su día, pareja estable, parentesco, salón común, minería,
tala...), esta se ejerce con fuerza real desde el primer momento en que
existe un asentamiento -- probablemente porque RECOLECTAR/CONSTRUIR son,
con diferencia, las acciones más frecuentes del repertorio consciente,
así que su cubeta de conocimiento acumula rápido en cuanto hay pueblo.

**Pendiente real, explícito**: `tasa_erosion_conocimiento_dia`,
`escala_saturacion_conocimiento` y `peso_conocimiento_colectivo`
PROVISIONALES, sin calibrar contra el harness completo; la cubeta
"artesano" sigue sin ningún efecto de comportamiento (solo se
acumula); ningún criterio maestro de Diego remedido con esta pieza ya
aplicada -- riesgo de desplazamiento de secuencia de `rng` bajo pero no
nulo, no medido; **con esto, "tipos de construcción nuevos" pasa a ser
el siguiente círculo real del roadmap unificado** (consumidor directo
de conocimiento colectivo + calidad de materiales), junto con
"interacción entre asentamientos" y "nombre propio + crónica" (piezas
4-5 del informe original), ninguna decidida todavía -- a la espera de
que Diego elija.

## Nombre propio + crónica de asentamiento, con mix geográfico -- cerrado
## el mismo día (2026-09-15)

Elegida por Diego, vía `AskUserQuestion`, como la más acotada y de menor
riesgo de las piezas restantes del informe "asentamiento como entidad
propia" (Piezas 4-5) -- pura identidad narrativa + consulta de solo
lectura, sin tocar ningún mecanismo de comportamiento, mismo alcance que
"biografía consultable" (Círculo 6 del arco "hilo individual",
2026-09-04). Spec:
`docs/superpowers/specs/2026-09-15-nombre-cronica-asentamiento-design.md`.
Implementado directamente por Claude (sin pipeline en este contenedor).

### Diseño e implementación, primera versión

- `config/nombres.yaml` gana `nombres_asentamiento` (prefijos/sufijos
  planos, catálogo NUEVO de topónimos, nunca nombres de persona).
- `nucleo/asentamiento.py:generar_nombre(rng, catalogo) -> str | None`
  (nueva, pura): mismo patrón `rng.choice(prefijos) + rng.choice(sufijos)`
  que `nucleo/entidad.py:_generar_nombre`, sin generalizar esa función
  -- pequeña duplicación deliberada.
- Sorteado UNA vez, exactamente cuando `SistemaAsentamiento.ejecutar()`
  determina que un id es genuinamente nuevo (mismo punto donde ya se
  emite `AsentamientoFundado`) -- nunca se resortea mientras el id
  persista. Persistido en `Mundo.asentamiento_nombre: dict[int, str]`,
  reutilizando `configuracion_ejecucion` (sin bump de esquema).
- Crónica: sin columna nueva en `cronica_eventos` -- se añade
  `datos["asentamiento_id"]`/`datos["nombre_asentamiento"]` a
  `AsentamientoFundado` y `RefugioConstruido`/`AlmacenConstruido` (estos
  últimos resolviendo `asentamiento_de` en el momento de emitir, mismo
  helper que ya usa conocimiento colectivo).
  `Persistencia.cronica_de_asentamiento(id) -> list[Evento]` (nueva,
  mismo molde que `biografia_de`): filtra `cronica_eventos` en Python,
  no vía SQL/json1 -- consulta bajo demanda, no hot path.
- `presentacion/narrador.py` gana plantillas para `AsentamientoFundado`
  y `AlmacenConstruido` (hueco preexistente en `_PLANTILLA_GENERICA`,
  cerrado de paso).

### Corrección tras feedback crítico de Diego (mismo día)

Viendo el resultado real ("Barost", "Karom", "Stenost"), Diego señaló
con razón que un catálogo de sílabas puro "no se diferencia mucho de
una generación de nombres común" -- pidió mezclarlo con la zona o un
accidente geográfico, dando el ejemplo de una pradera con nombre
construido frente a un valle que se nombra a sí mismo por el accidente.

Verificado contra el código real qué rasgos geográficos existen hoy
(sin inventar "valle", que el motor no modela): `Celda.tipo_terreno` (5
biomas) y `Celda.tipo_agua`. Vía `AskUserQuestion`, Diego escogió
acotar el mix a **solo los dos rasgos "fuertes" (agua y montaña)**, no
dar temática a los 5 biomas -- más fiel a su propio ejemplo (una
pradera sigue siendo genérica).

- `nucleo/asentamiento.py:rasgo_geografico_notable(celda)` (nueva):
  `'agua'` si `celda.tipo_agua != ""` (prioridad sobre montaña),
  `'montana'` si bioma MONTANA sin agua, `None` en cualquier otro caso.
  **Corrección real durante el desarrollo**: la primera versión miraba
  `celda.tiene_agua`, que NO se deriva automáticamente de `tipo_agua` al
  construir una `Celda` a mano (solo lo sincroniza el generador de
  mundo real) -- 2 tests fallaron hasta cambiar la comprobación a
  `celda.tipo_agua != ""` directamente, la fuente de verdad real según
  el propio docstring del campo.
- `generar_nombre` gana dos parámetros opcionales (`rasgo`,
  `probabilidad_tematico`, ambos con default que reproduce el
  comportamiento anterior): con rasgo presente y la tirada de
  `asentamiento.probabilidad_nombre_tematico` (0.6, PROVISIONAL)
  favorable, sustituye `catalogo["prefijos"]` por
  `catalogo[f"prefijos_{rasgo}"]` -- los SUFIJOS siguen siendo siempre
  los mismos. Deliberadamente no determinista, coherente con el
  "quizás" de Diego.
- `config/nombres.yaml:nombres_asentamiento` gana `prefijos_agua` (Vad,
  Rib, Font, Reman) y `prefijos_montana` (Alt, Cim, Peñ, Risc).
- **Hallazgo real, corregido de paso**: `RefugioConstruido` (evento
  individual) ya quedaba etiquetado con `asentamiento_id` desde la
  primera versión (mismo bloque de `_resolver_construir` que
  `AlmacenConstruido`), pero sin plantilla dedicada caía en el genérico
  feo ("evento refugio (entidad 2016)") -- añadida una plantilla mínima.

**Verificado**: 628/628 tests en verde (creció de 11 a 20 en
`tests/test_nombre_cronica_asentamiento.py` entre las dos rondas).
`BOSQUE_AUTO_TICKS`/`BOSQUE_CONTINUAR` sin excepciones.

**Diagnóstico de juego libre, reutilizando las mismas 4 semillas
(401001-401004) que ya confirmaron formar asentamiento**: el mecanismo
base funciona -- las 4 corridas generan nombre al fundarse y la crónica
reconstruida es coherente (aislada correctamente entre los 2
asentamientos simultáneos de la semilla 401004: "Karom" con sus 4
refugios propios, "Stenost" con sus almacenes/salón común propios, sin
mezclarse). **Pero el mix geográfico no llegó a observarse en esta
muestra**: los 5 asentamientos resultantes (4 semillas, 2 en la 401004)
salieron con nombre puramente silábico -- Thornom, Barost, Dunom,
Karom, Stenost, ninguno con prefijo `_agua`/`_montana`. Con
`probabilidad_nombre_tematico=0.6`, 0/5 temáticos es estadísticamente
posible pero low-probability SI el centro cae en agua/montaña con
frecuencia -- lectura más honesta: los centros de asentamiento de esta
muestra concreta simplemente no cayeron sobre esos dos biomas
concretos, no que el mecanismo falle (verificado aparte por tests
dirigidos que sí ejercen la sustitución). **Pendiente real**: el mix
geográfico sigue sin confirmarse en juego libre con una muestra mayor;
`probabilidad_nombre_tematico` PROVISIONAL, sin calibrar.

## Tipos de construcción nuevos: taller de artesano, mobiliario y
## almacén personal en refugio -- cerrado, resultado dividido en juego
## libre (2026-09-16)

Siguiente círculo natural del roadmap unificado (arco "asentamiento
como entidad propia" + "asentamientos/profesiones"), primer consumidor
real de conocimiento colectivo con efecto de comportamiento (la cubeta
"artesano" venía acumulando desde la pieza anterior sin ningún
consumidor). Ante la pregunta abierta "qué más podemos añadir", Diego
eligió esta pieza y, al detallar qué objeto concreto debía desbloquear
el taller, respondió con una idea EXPANDIDA en vez de elegir una de las
opciones ofrecidas: objetos que suban la comodidad de un individuo
(mobiliario) Y que un refugio propio tenga su propio almacén para
guardar pertenencias. Vía `AskUserQuestion`, Diego eligió explícitamente
implementar **ambas piezas en el mismo círculo**, contra la
recomendación de mantenerlas separadas por el principio habitual de
"una complejidad a la vez". Spec:
`docs/superpowers/specs/2026-09-16-taller-mobiliario-almacen-refugio-design.md`.
Implementado directamente por Claude (sin pipeline en este contenedor).

### Pieza A -- taller de artesano -> mobiliario -> comodidad

- `nucleo/construccion.py:tipos_paralelos` gana un tercer elemento,
  `"taller"` (junto a `salon_comun`/`cocina`, ya generalizado para esto
  desde su comentario original) -- `objetivo_construccion_actual` solo
  devuelve `None` cuando los TRES paralelos están completos.
- `config/materiales.yaml` gana `masa_minima_taller`/`huella_m2_taller`,
  y dos materiales nuevos: `utensilios_domesticos` (calidad 0.65) y
  `mueble_tallado` (calidad 0.9, deliberadamente por debajo del hierro
  0.95). **Conflicto de capacidad real, documentado sin resolver**: la
  suma de `huella_m2` de los 4 edificios comunales (almacén+salón
  común+cocina+taller) da 125, por encima de
  `capacidad_construccion_celda_m2=80` -- ni retocado el valor ni
  añadida búsqueda en celda vecina, honestamente señalado en el propio
  fichero de config.
- `config/herramientas.yaml:recetas_mobiliario` (catálogo separado,
  mismo criterio que `recetas_mineria`): `utensilios_domesticos` (nivel
  1, madera) y `mueble_tallado` (nivel 2, madera+piedra).
- **Reutilización arquitectónica real**: FABRICAR es determinista/
  instantáneo, sin ninguna tasa continua que un bono pudiera acelerar --
  en vez de inventar un mecanismo nuevo, el mueble se trata como un
  MATERIAL más (kg añadidos a `Inventario.contenidos`, no un objeto
  discreto en `.objetos`), con `calidad_construccion` alta en el
  catálogo. Esto hace que el mecanismo YA CONSTRUIDO de mejora de
  vivienda por sustitución (`_resolver_mejora_refugio`, Pieza D del arco
  comodidad) lo reconozca **sin ningún cambio de código** -- verificado
  con una regresión dedicada.
- `sistemas/sistema_decision.py`: tercera vía de mejora de vivienda,
  junto a RECOLECTAR-mejora y CONSTRUIR-mejora, heredando el mismo
  `deficit_comodidad` -- gateada por estar en un `taller` completado del
  propio asentamiento Y que `nivel_conocimiento(..., "artesano", ...)`
  supere `umbral_conocimiento_taller` (0.3, PROVISIONAL) -- primer
  efecto de comportamiento real de esa cubeta, hasta ahora solo
  acumulada.

### Pieza B -- almacén personal en refugio

- `componentes/construccion.py:Construccion.almacen` (nuevo,
  `dict[str, float]`, mismo molde que `provisiones`/`materiales`) --
  universal en el componente pero solo poblado hoy en tipo "refugio".
- `sistemas/sistema_recursos.py:_resolver_deposito_almacen_refugio`:
  disparado por `Accion.DORMIR` (elegido deliberadamente frente a
  cualquier otra acción para no vaciar el inventario de alguien
  meramente de paso hacia el almacén comunal) -- si el individuo duerme
  exactamente en la celda de su propio refugio ya
  `completado_alguna_vez`, todo `Inventario.contenidos` se mueve a
  `Construccion.almacen` (sumando sobre lo ya guardado), liberando
  capacidad de carga real. Solo depósito -- sin mecanismo de retirada
  todavía, pendiente honesto señalado en el spec.
- `nucleo/persistencia.py`: `VERSION_ESQUEMA` 0.39 -> 0.40-fase0,
  columna `almacen TEXT` nueva en `construccion_estado` (bump de
  esquema, a diferencia de nombre+crónica -- aquí sí hace falta porque
  `construccion_estado` es tabla de esquema fijo, no
  `configuracion_ejecucion`).

### Regresión corregida de paso

Añadir `"taller"` como tercer paralelo rompió 2 tests preexistentes
(`test_cocinas_comunes.py::test_objetivo_none_solo_cuando_ambos_
paralelos_completos`, `test_salon_comun.py::test_objetivo_none_cuando_
salon_comun_tambien_esta_completo`) que asumían solo 2 paralelos --
corregidos construyendo también un `"taller"` completado antes de
esperar `None`, preservando el invariante real bajo prueba (ahora son 3
paralelos, no 2), no debilitando la aserción.

**Verificado**: 644/644 tests en verde (16 nuevos,
`tests/test_taller_mobiliario_almacen.py`): fabricación de mobiliario
como kg en `contenidos` no objeto discreto, preferencia por receta de
mayor nivel completable, no-op sin receta; depósito automático (deposita,
suma sin sobrescribir, y sus 4 no-op reales: sin refugio propio, refugio
no completado, fuera de la celda del refugio, inventario vacío); el gate
completo de la utilidad de mobiliario en `sistema_decision.py` (6
escenarios: gana con todo presente, y falla sin taller/sin asentamiento/
con conocimiento insuficiente/sin receta/sin mejora de calidad real); y
la regresión de `_resolver_mejora_refugio` reconociendo `mueble_tallado`
sin ningún cambio de código. `BOSQUE_AUTO_TICKS=3000` y
`BOSQUE_CONTINUAR=1` (roundtrip con la columna `almacen` nueva) sin
ninguna excepción.

**Diagnóstico de juego libre, 4 semillas × 10000 ticks (401001 +
402001-402003 -- ticks más largos que el resto de diagnósticos de esta
sesión a propósito, porque esta pieza depende de una cadena comunal de
4 pasos, la más profunda probada hasta ahora), resultado DIVIDIDO y
honesto**:

- **Pieza B (almacén de refugio): se ejerce con fuerza real en las 4
  semillas** -- 143, 198, 4 y 122 depósitos automáticos respectivamente
  (variación entre semillas coherente con cuánta población consciente
  con refugio propio llegó a sobrevivir lo bastante en cada corrida).
- **Pieza A (taller/mobiliario): 0 muebles fabricados en las 4
  semillas**, sin ninguna excepción. Solo la semilla 402001 llegó a
  completar tanto salón común como cocina (los dos paralelos previos al
  taller) dentro de los 10000 ticks -- ni siquiera en ese caso llegó a
  completarse el taller mismo (tercer paralelo) en el resto de la
  ventana. Las otras 3 semillas ni siquiera completaron salón común,
  así que el taller nunca entró en juego -- conocimiento colectivo
  "artesano" alcanzó niveles muy por encima del umbral (0.947, 1.000,
  0.380, 0.960 según semilla) en todas, así que el umbral de
  conocimiento NO es el cuello de botella real: lo es la profundidad de
  la cadena comunal (4 construcciones paralelas en secuencia) combinada
  con el conflicto de capacidad ya documentado (125m² > 80m²).

**Lectura honesta**: Pieza A queda en el mismo patrón que salón
común/minería/tala sufrieron en su día -- "correcta pero invisible" en
juego libre, verificada solo por los 16 tests dirigidos. No es un bug:
el mecanismo dispara exactamente como se diseñó en cuanto sus 3
precondiciones (taller completo + asentamiento + conocimiento sobre
umbral) se cumplen a la vez, pero la primera de esas tres es
estructuralmente rara a esta escala de ticks. **Pendiente real,
explícito**: el conflicto de capacidad (125m² > 80m²) sigue sin
resolverse -- ni retocada la huella de ningún edificio comunal, ni
añadida búsqueda en celda vecina; sin esa resolución, es dudoso que el
taller llegue a completarse nunca en juego libre a esta escala de
población, por mucho conocimiento colectivo que se acumule. Candidato
real para la próxima calibración numérica de este arco, no para más
diseño sobre el papel.
