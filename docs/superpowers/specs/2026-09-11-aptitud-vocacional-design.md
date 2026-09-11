# Aptitud vocacional -- Círculo 1 del arco "fabricación y uso de herramientas"

Fecha: 2026-09-11. Diseñado en conversación con Diego, implementado
directamente por Claude (centinela del pipeline parado desde el
incidente de madriguera-fisica-A, este contenedor cloud tampoco tiene
`OPENROUTER_API_KEY`/`mini-swe-agent` -- mismo escenario ya documentado
repetidas veces en la última semana de trabajo).

## Objetivo, tal como lo planteó Diego

"Entiendo que las herramientas son las bases de las profesiones que se
irán desarrollando, aunque nuestra intención es no tener un catálogo de
profesiones que se asignen con un guion, si no que de las necesidades
de un individuo o grupo junto a las habilidades y temperamento del
individuo nazcan una serie de profesiones."

Tres decisiones cerradas con Diego antes de diseñar (`AskUserQuestion`):
1. **Alcance de este primer círculo**: solo tendencia + observabilidad
   -- aptitud derivada que sesga la Utility AI, más un contador que hace
   la tendencia consultable. Sin mejora por práctica (evitar abrir la
   puerta a "mutación causal de rasgos", ya aplazada una vez en el arco
   de hilo individual) y sin reconocimiento social (necesitaría
   reputación/rumor leyendo vocación -- círculo futuro, no este).
2. **Cubetas vocacionales**: las 4 acciones ya existentes del motor,
   sin ningún verbo nuevo -- forrajero/minero (RECOLECTAR), constructor
   (CONSTRUIR), artesano (FABRICAR), cocinero (COCINAR).
3. **Orden**: aptitud derivada primero (el cimiento, sin efecto visible
   de presentación todavía), herramientas vía FABRICAR queda para un
   círculo posterior -- "el motor primero, la presentación después"
   aplicado aquí como "el cimiento primero, el efecto tangible después".

## Por qué esto no es un catálogo de profesiones (principio 5, leyes neutras)

Nunca se escribe un string de profesión en ningún sitio. Dos piezas
deliberadamente separadas:

1. **Aptitud** (`nucleo/vocacion.py:aptitud_forrajero/aptitud_constructor/
   aptitud_artesano/aptitud_cocinero`): función PURA de atributos que YA
   se sortean al nacer (`DimensionesFisicas`, `Temperamento`,
   `CapacidadMental`) -- nada nuevo que sortear, nada que persistir (se
   recalcula cada vez). Sesga la Utility AI hacia la cubeta para la que
   un individuo está mejor dotado, sin decidir nunca "este individuo ES
   forrajero" -- solo hace que RECOLECTAR le resulte más o menos
   atractivo que a otro individuo, en competencia con el resto de
   necesidades de siempre (hambre, sed, seguridad...).
2. **Vocación practicada** (`componentes/vocacion.py:Vocacion`,
   `nucleo/vocacion.py:vocacion_dominante`): contador de solo-observación
   -- cuántos ticks pasó un individuo despachando cada una de las 4
   acciones. Se deriva la "vocación dominante" leyendo cuál contador es
   mayor, nunca se escribe una etiqueta. Puede DIVERGIR de la aptitud
   (las circunstancias -- necesidad urgente del grupo, escasez de un
   recurso -- pueden empujar a un individuo bien dotado para artesano a
   pasar la mayor parte de su tiempo recolectando) -- esa divergencia es
   la parte genuinamente emergente.

De las necesidades del GRUPO (mencionadas por Diego) solo se modela hoy
lo que ya existía antes de este círculo: `objetivo_construccion_actual`
(refugio→almacén→salón/cocina en paralelo) ya hace que la utilidad de
CONSTRUIR/RECOLECTAR dependa de qué necesita el asentamiento en cada
momento. Este círculo NO añade ninguna señal de escasez de vocación a
nivel de grupo (p.ej. "nadie está cocinando, sube la utilidad de
COCINAR para todos") -- eso es el alcance de "reconocimiento social"
que Diego declinó explícitamente para este primer círculo. Señalado
como pendiente real, no construido aquí.

## Diseño de la aptitud

Cada cubeta combina dos atributos ya existentes con un reparto fijo
60/40 (atributo "principal" pesa más) -- decisión de diseño sobre QUÉ
importa para cada oficio, vive en código
(`nucleo/vocacion.py:_PESO_PRIMARIO/_PESO_SECUNDARIO`), no en config
(distinto de la magnitud de modulación, que sí es PROVISIONAL/config):

- **Forrajero/minero** (RECOLECTAR): `agudeza_sensorial` (0.6, percibir
  dónde hay recurso) + `fuerza` (0.4, cargar/extraer).
- **Constructor** (CONSTRUIR): `fuerza` (0.6, trabajo físico sostenido)
  + `voluntad` (0.4, persistir en un esfuerzo hacia un objetivo --
  **primer consumidor real de `CapacidadMental.voluntad`**, cuyo propio
  docstring ya esperaba justo esto: "necesidades superiores --
  propósito, trabajo").
- **Artesano** (FABRICAR): `inteligencia` (0.6, resolver cómo combinar
  materiales -- **primer consumidor real de
  `CapacidadMental.inteligencia`**, cuyo docstring literalmente decía
  "espera... profesión emergente") + `curiosidad` (0.4, experimentar).
- **Cocinero** (COCINAR): `inteligencia` (0.6, técnica/tiempos) +
  `agudeza_sensorial` (0.4, detectar el punto correcto por
  olfato/gusto).

`factor_aptitud(aptitud, peso) = 1.0 + peso * (aptitud - 0.5) * 2.0` --
multiplicador centrado en 1.0 (aptitud=0.5 no cambia nada), aplicado al
valor FINAL de cada utilidad (tras cualquier eslabón heredado, ej.
RECOLECTAR por fuego/arma) y SOLO si la utilidad ya es > 0.0 --
multiplicativo, nunca aditivo: nunca crea utilidad donde no la había
(sin objetivo de construcción, sin material -- sigue en 0.0 con
cualquier aptitud), solo modula cuando ya existe un motivo real para
actuar. Misma causalidad que ya exige el resto del motor. Gateado a
consciente (mismo `umbral_consciencia_agencia` de siempre) -- fauna
nunca ejecuta estas 4 acciones hoy.

`vocacion.peso_aptitud_vocacional = 0.3` (PROVISIONAL,
`config/comportamiento.yaml`): a esa magnitud, un individuo en el
extremo superior de aptitud ve la utilidad de esa cubeta multiplicada
por 1.3, uno en el extremo inferior por 0.7 -- sesgo real pero que
nunca por sí solo puede hacer perder a una necesidad más urgente
(hambre/sed/seguridad no pasan por este factor).

## Vocación practicada

`componentes/vocacion.py:Vocacion` -- 4 contadores enteros,
universal en las 4 especies (mismo criterio que `Agarre`/`Semillas`/
`Relaciones`: componente presente en todas, en la práctica solo se
incrementa para consciente). Incrementado en `sistemas/
sistema_recursos.py:ejecutar()`, justo tras despachar cada resolver
(`_resolver_construir`/`_resolver_recolectar`/`_resolver_cocinar`/
`_resolver_fabricar`) -- en el DESPACHO, no tras confirmar éxito
(representa "ticks dedicados a esta labor", mismo criterio que el resto
de contadores de observación de este sistema, no "kg conseguidos").
`nucleo/vocacion.py:vocacion_dominante(voc)` deriva la cubeta con más
práctica acumulada, o `None` si las 4 siguen en cero.

Persistido (`componentes_estado.vocacion`, JSON, mismo molde que
`agarre`/`relaciones`) -- perder la práctica acumulada al recargar
sería una regresión silenciosa en la única observabilidad real de este
círculo. `VERSION_ESQUEMA` sube a `0.37-fase0`.

## Verificación

- Tests dirigidos (`tests/test_vocacion.py`): las 4 fórmulas de
  aptitud, `factor_aptitud` en sus tres zonas (aptitud=0.5 neutro,
  aptitud=1.0/0.0 en los extremos), `vocacion_dominante` con empate/
  vacío/un ganador claro, el gate multiplicativo no crea utilidad desde
  0.0, roundtrip de persistencia.
- `BOSQUE_AUTO_TICKS` sin excepciones, confirmando que el contador se
  incrementa de verdad en juego libre.

## Pendiente real, explícito

- `peso_aptitud_vocacional=0.3` y el reparto 60/40 por cubeta son
  PROVISIONALES, sin calibrar contra el harness completo.
- Reconocimiento social (que el asentamiento "sepa" quién hace qué, vía
  reputación/rumor ya construidos) queda fuera de este círculo,
  declinado explícitamente por Diego para empezar más pequeño.
- Necesidad de GRUPO como señal de escasez de vocación (p.ej. "nadie
  cocina, sube la utilidad de COCINAR para todos") no se modela --
  candidato real de un círculo futuro.
- Mejora por práctica (cuanto más se repite una acción, mejor se
  ejecuta) queda fuera -- abriría la puerta a mutación causal de
  rasgos, decisión ya aplazada una vez en el arco de hilo individual.
- Sin ninguna herramienta física todavía -- el siguiente círculo real
  del arco, ya confirmado por Diego como el próximo tema, es
  fabricación de herramientas vía `Accion.FABRICAR` (categoría
  "herramienta", el resolutor `candidatos_fabricar` ya está preparado
  para un segundo candidato desde el rename `FABRICAR_ARMA -> FABRICAR`
  del 2026-09-11).
- Sin ningún consumidor de `vocacion_dominante` en narrador/vista_web
  todavía -- presentación, deliberadamente sin tocar (motor primero).
