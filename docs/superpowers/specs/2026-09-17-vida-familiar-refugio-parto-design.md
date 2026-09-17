# Vida familiar: emancipación gateada por adultez + parto dirigido a refugio

Fecha: 2026-09-17. Diseñado en conversación con Diego a partir de la lista
de temas "vida familiar / refugios más grandes para parejas que conviven
con hijos". Alcance de ESTE círculo, cerrado explícitamente en
conversación: dos piezas pequeñas y bien acotadas. La pieza más amplia que
motivó el tema original -- refugios que crecen físicamente según ocupación
("hacinamiento" como señal, ampliación de `huella_m2_refugio`) -- se deja
señalada como pendiente al final de este documento, sin diseñar: no se
concretó ni el umbral de hacinamiento ni el mecanismo de ampliación en la
conversación, y este proyecto no completa huecos de diseño por iniciativa
propia sin avisar.

## Hallazgo que motiva la Pieza A

`sistema_decision.py:747-754` (bloque CONSTRUIR/RECOLECTAR) decide si un
individuo persigue "refugio" como `tipo_objetivo` mirando únicamente
`cap_mental.consciencia >= umbral_consciencia_agencia`. `consciencia`
(`componentes/capacidad_mental.py:26-34`) es un valor sorteado UNA VEZ al
nacer por rango racial, fijo de por vida -- no varía con la edad. Sin
ningún otro gate de por medio, el motor deja hoy que un individuo
consciente compita por construir su propio refugio desde el nacimiento,
sin esperar a nada parecido a una emancipación.

`BUSCAR_PAREJA` (`sistema_decision.py:692-709`), en cambio, ya está
gateada por `adulto = es_adulto(edad, especie, rangos_raciales,
fraccion_madurez)` -- la misma elegibilidad reproductiva
(`nucleo/ciclo_vital.py:95-109`). Diego: la emancipación (buscar pareja,
fundar refugio propio, tener descendencia) debe nacer de la necesidad del
individuo tras el despertar sexual, no de un corte de edad inventado
aparte para "dejar de contar como ocupante" de la vivienda parental.

## Pieza A: gate de adultez en CONSTRUIR-refugio-propio

Extender el mismo `adulto` ya calculado en la línea 700 al bloque de la
738-754: un individuo no adulto nunca elige "refugio" como
`tipo_objetivo`, cae directamente a la rama ya existente para "refugio
propio ya resuelto" (mirar la cadena comunal del asentamiento) -- mismo
comportamiento que ya tiene hoy un adulto con refugio completo. Cambio
quirúrgico: una única línea que fuerza `refugio_pendiente = False` si
`not adulto`, sin tocar el resto de la lógica (mejora de vivienda,
`sistema_decision.py:1066-1170`, no necesita cambio: ya exige
`completado_alguna_vez`, inalcanzable sin haber sido adulto antes).

Consecuencia directa: quién "vive con quién" queda resuelto sin
necesidad de ningún componente ni campo nuevo. `nucleo/construccion.py`
gana `refugio_de_pertenencia(gestor, id_entidad, umbral_pareja)`, función
puramente relacional (mismo criterio que `nucleo/parentesco.py`: sin
estado propio, deriva de lo que ya existe):

1. El refugio propio del individuo (`construccion_propia`), si existe.
2. Si no, el refugio propio de su pareja actual (`son_pareja`, leído
   sobre `Relaciones.vinculos` -- sin imponer monogamia, coherente con
   que `son_pareja()` tampoco la impone; el primero que se encuentre con
   refugio propio entre los vínculos que califican).
3. Si no, el refugio propio de la madre o el padre (parentesco directo,
   `Identidad.id_madre/id_padre`, madre priorizada en empate).
4. `None` si ninguno de los tres tiene refugio propio todavía (basta con
   que exista, aunque `progreso < 1.0`).

No se implementa la función inversa ("ocupantes de un refugio dado") en
este círculo -- sin consumidor real todavía (nada calcula hacinamiento o
capacidad hoy), se deja para cuando esa pieza se diseñe de verdad.

## Pieza B: parto dirigido al refugio de pertenencia

### Motivación

`sistema_reproduccion.py:178-244` resuelve el nacimiento en la posición
EXACTA de la madre en el tick en que se cumple `duracion_gestacion_dias`
-- sin ningún ajuste salvo `celda_nacimiento_segura` (evita que el hijo
nazca sumergido en agua más honda que su propia altura). Diego: lo natural
es que la madre, si tiene un refugio accesible, tienda a dirigirse hacia
él según se acerca el término -- búsqueda de seguridad para parir,
prioritaria en la naturaleza, "dentro de lo posible" (no garantizada: la
duración de gestación sigue siendo fija, si no da tiempo a llegar el parto
ocurre donde esté, comportamiento actual sin cambios).

### Diseño

Nueva `Accion.BUSCAR_REFUGIO_PARTO` (`componentes/intencion.py`), resuelta
con el mismo patrón de dos sistemas que el resto (`sistema_decision.py`
decide SI aplica y su utilidad, `sistema_movimiento.py` resuelve HACIA
DÓNDE moverse, sin desplazamiento cacheado -- reresuelve
`refugio_de_pertenencia` en vivo, mismo criterio que `tipo_objetivo` ya
documentado en `objetivo_construccion_actual`).

Utilidad en `sistema_decision.py`, nueva candidata en la tupla
`candidatas` (`sistema_decision.py:1285-1323`), colocada justo después de
`Accion.HUIR` y antes de `accion_alimentarse`:

- Se activa cuando la `Gestacion` de la madre lleva transcurrida una
  fracción >= `reproduccion.fraccion_gestacion_buscar_refugio`
  (PROVISIONAL 0.75, el último cuarto de la gestación) de
  `Reproduccion.duracion_gestacion_dias * Reloj.TICKS_POR_DIA` -- mismo
  cálculo que ya usa `_resolver_nacimientos`.
- Y `refugio_de_pertenencia(...)` devuelve un cid cuya `Posicion` no
  coincide con la posición actual de la madre (si ya está ahí, o no
  tiene ninguno, utilidad 0.0 -- no hay a dónde ir).
- Utilidad = constante `decision.utilidad_buscar_refugio_parto`
  (PROVISIONAL 0.9), NO graduada por ningún déficit -- se activa ya
  alta de golpe, como un instinto, no una necesidad que se acumula.
- Sin el gate `fisica_bajo_umbral` que sí aplica a `BUSCAR_PAREJA`/
  `SOCIALIZAR`: buscar refugio para parir es justo lo contrario de una
  "necesidad superior" que debe esperar a que las básicas estén
  cubiertas.
- Resultado práctico de la posición en la tupla + el valor alto: gana a
  recolectar/construir/socializar/buscar pareja en la inmensa mayoría de
  casos; pierde ante `Accion.HUIR` (amenaza real) siempre, y ante
  comer/beber/dormir solo cuando esas necesidades ya están en un nivel
  tan crítico que su propia utilidad (`1.0 - necesidad`) supera 0.9 --
  sin necesitar ninguna regla de prioridad especial adicional, pura
  competencia numérica.

Resolución del movimiento en `sistema_movimiento.py`: nueva rama
`elif accion == Accion.BUSCAR_REFUGIO_PARTO`, nuevo método
`_calcular_ir_a_refugio_parto` que reobtiene `refugio_de_pertenencia` y
usa `self._acercarse_a(pos_x, pos_y, destino.x, destino.y)` -- mismo
mecanismo ya usado por `_calcular_construir` para caminar hacia el
refugio ya existente.

Nada cambia en `sistema_reproduccion.py`: el parto se sigue resolviendo
en la posición donde la madre esté en ese tick, sea o no su refugio --
solo que ahora, con esta utilidad activa, es mucho más probable que esa
posición ya sea el refugio.

## Config nueva (ambas PROVISIONALES, sin calibrar contra el harness)

- `config/fisiologia.yaml`, sección `decision`:
  `utilidad_buscar_refugio_parto: 0.9`
- `config/fisiologia.yaml`, sección `reproduccion`:
  `fraccion_gestacion_buscar_refugio: 0.75`

## Fuera de alcance de este círculo (pendiente real, no diseñado)

- **Refugio que crece con la familia**: `huella_m2_refugio` sigue siendo
  una constante fija por tipo (`config/materiales.yaml`), sin relación
  con cuántos ocupantes tenga. Ni el umbral de "hacinamiento" ni el
  mecanismo de ampliación física (¿nuevo tipo de construcción?, ¿masa
  extra sobre la misma `Construccion`?) se concretaron en conversación
  -- pendiente de un círculo propio.
- **Función inversa `ocupantes_de`** (contar cuántos dependen de un
  refugio dado): sin consumidor real todavía, no se escribe hasta que
  la pieza de hacinamiento la necesite.
- **Orden pareja → refugio → descendencia**: deliberadamente NO se
  impone como secuencia obligatoria -- las utilidades de
  `BUSCAR_PAREJA`, `CONSTRUIR`-refugio y la reproducción (gateada solo
  por `es_adulto`, sin exigir refugio propio) siguen compitiendo en
  paralelo, coherente con que el motor no fuerza guiones.
