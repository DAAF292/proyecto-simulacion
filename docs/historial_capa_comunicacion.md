# Historial — Capa de comunicación — sonido, rumor, liderazgo, ocio

> **Archivado de `CLAUDE.md` el 2026-09-15**, por tamaño (CLAUDE.md había
> superado las 600KB / ~9944 líneas mezclando orientación rápida con
> bitácora cronológica completa). Este fichero es historial puro —
> registro sesión a sesión, tal cual se escribió en su momento, sin
> reescribir ni resumir. Para la orientación rápida vigente del proyecto
> (los 5 principios, mecanismos reutilizables, estado y pendientes reales
> a día de hoy), ver `CLAUDE.md`.

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
