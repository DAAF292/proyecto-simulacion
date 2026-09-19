# Desastres naturales: rayo, sequía, inundación, y por qué el incendio no mataba fauna

Fecha: 2026-09-18. Origen: siguiendo el tema de clima de la misma
sesión, Diego pidió "darle una vuelta al tema de desastres naturales"
-- hoy `sistema_desastres.py` solo modela incendio, pese a que la
sección de config se llama `desastres:` en plural. Al plantear tres
candidatos (rayo, sequía, inundación), Diego señaló un hueco real:
"una cosa, el incendio ahora no mata fauna, esto hay que
solucionarlo" -- y pidió después también daño a estructuras por
inundación, y verificar que la flora sí muere en incendio.

## Diagnóstico real del incendio, verificado contra el motor, no supuesto

Antes de tocar nada se confirmó la afirmación de Diego con un
experimento real (no solo lectura de código): 40 individuos de fauna
(lobo/conejo/ardilla/venado) sembrados DIRECTAMENTE en celdas de
bosque, 6000 ticks (250 días) de simulación real. Resultado: 48
incendios reales iniciados, **1 sola "Herida" por fuego, 0 muertes**.

**Primer intento de medición, con un bug real en el propio arnés de
verificación**: la primera pasada del experimento reportó 34727
"IncendioIniciado" -- un número imposible dado el número de celdas de
bosque y la cadencia diaria de ignición (máximo teórico ~18500 en 250
días). Causa: el script de verificación llamaba a `ejecutar_tick()`
directamente sin llamar a `bus_eventos.limpiar()` entre ticks (a
diferencia del bucle real de `main.py`, que sí lo hace) -- los eventos
se acumulaban y se recontaban en cada iteración. Corregido antes de
sacar ninguna conclusión: con el bug arreglado, 48 incendios reales,
cifra coherente con el cálculo teórico.

**Causa raíz real del incendio "manso"**: no hay ningún filtro que
excluya fauna del daño (`_procesar_fuego_tick_zona` itera todas las
criaturas con los mismos 4 componentes, sin distinguir especie) --
es un problema de calibración, dos factores combinados:
1. `prob_extincion_por_tick=0.35` / `prob_propagacion_por_tick=0.08`:
   un foco se apaga solo en ~3 ticks de media y apenas se propaga.
2. `celda.en_llamas` ya es amenaza ambiental con prioridad alta de
   HUIR (`nucleo/amenaza.py`, radio de percepción hasta 4 celdas) --
   la fauna casi siempre tiene tiempo de escapar antes de que el fuego
   llegue a su celda.

**Flora, verificado aparte, mecanismo YA funcional sin cambios**: se
sembró la flora inicial real (`main.py:sembrar_flora_inicial`, sin la
cual el mapa no tiene ninguna Planta) y se forzó ignición en TODAS las
celdas de bosque -- 26 plantas en esas celdas bajaron a 4 en 100 ticks
(~85% destruidas). La flora es estática (no puede huir) -- en cuanto
su celda arde, se quema con certeza. No se tocó nada de este mecanismo.

## Recalibración de incendio (para que mate fauna de verdad)

`prob_propagacion_por_tick: 0.08 → 0.15`, `prob_extincion_por_tick:
0.35 → 0.20`. PROVISIONAL, sin una segunda ronda de calibración tras
este cambio.

**Resultado real tras el cambio (smoke test de 8000 ticks, 333 días,
mismos 40 individuos)**: 36 incendios, **32 muertes por incendio** --
el fix funciona, la fauna ahora sí muere. Pero **observación honesta,
posible sobrecorrección, no ajustada por iniciativa propia**: incendio
pasó a ser la causa de muerte DOMINANTE en esa corrida (32 de 61
muertes totales, 52%) -- de "nunca mata" a "mata más que cualquier
otra causa junta". No hay base para saber si 0.15/0.20 es el punto
correcto o si hace falta un valor intermedio -- necesita el harness
completo para decidir con datos, no esta única corrida.

## Rayo

Cadencia de TICK (no diaria como la ignición espontánea), solo en
zonas con `Clima.TORMENTA` activo. Celda al azar de la zona entera
(`rng.randrange`), sin restringir a bosque. Daño INSTANTÁNEO (no tick
a tick como el fuego) a quien esté en la celda exacta -- reutiliza
`nucleo/entidad.py:procesar_deceso` si mata, con las fracciones de
descomposición NORMALES (no las de "calcinada" del incendio, un rayo
no calcina). Si la celda es bosque, probabilidad adicional de iniciar
un foco de incendio ahí -- segunda vía de ignición, independiente de
la espontánea por sequedad, con su propio dato `causa: "rayo"` en el
evento `IncendioIniciado`.

Config: `probabilidad_impacto_rayo_por_tick=0.02`, `dano_rayo=0.6`
(fracción de `vitalidad_maxima`), `probabilidad_rayo_inicia_incendio=0.3`.
Todas PROVISIONAL.

**Verificado real**: 69 impactos en 333 días, 0 muertes directas por
rayo en esa corrida concreta (0.6 de daño hiere mucho pero rara vez
mata de un solo golpe) -- coherente con la calibración, no un bug.

## Sequía

Ley emergente por zona, SIN entidad de "evento" propia (a diferencia
de incendio) -- nuevo estado en `ZonaBioma`: `dias_secos_consecutivos`,
`en_sequia`. Clasificación propia de `SistemaDesastres`
(`_CLIMAS_SECOS = {despejado, ola_calor}`, el resto resetea el
contador). Al superar `dias_secos_para_sequia=8` (PROVISIONAL), la
zona entra en sequía (`SequiaIniciada`/`SequiaTerminada`, NOTABLE):
mientras dura, reduce `fertilidad` (`penalizacion_fertilidad_sequia_por_dia=0.02`)
y acelera el drenaje de `profundidad_charco` existente
(`factor_secado_charco_sequia=0.01`) en TODAS las celdas de la zona,
cada día.

**Decisión de diseño deliberada (principio de leyes neutras)**: la
sequía NO mata directamente -- amplifica inanición/deshidratación ya
existentes al reducir comida/agua disponible, en vez de inventar una
"muerte por sequía" nueva. Verificado con un test dedicado que ningún
evento Muerte con esa causa se emite desde este sistema.

**Verificado real**: 8 ciclos completos de sequía (inicia y termina)
en 333 días.

## Inundación

Mismo patrón de contador que sequía, pero de días húmedos consecutivos
(`_CLIMAS_HUMEDOS = {lluvioso, tormenta, ventisca}` -- ventisca cuenta
como húmedo, es precipitación en forma de nieve, aunque enfríe). Al
ENTRAR en inundación (la transición, no cada día que dure -- evita
crecimiento de charco sin límite), desborda UNA VEZ: cualquier celda
con agua real (`nucleo.agua.hay_agua_potable`) sube
`profundidad_charco` de sus vecinas de tierra firme
(`incremento_charco_desborde=0.15`, con el mismo techo
`techo_profundidad_charco` que ya usa el resto del sistema de charcos)
-- reutiliza el ahogamiento YA EXISTENTE
(`profundidad_agua_potable > dims.altura`, `sistema_necesidades.py`)
sin inventar una causa de muerte nueva. Las celdas desbordadas se
registran en `zona.celdas_inundadas` (mismo patrón exacto que
`celdas_en_llamas`).

**Daño a estructuras, pedido explícito de Diego**: nuevo campo
`vulnerabilidad_agua` en `config/materiales.yaml`, contrapunto
SIMÉTRICO de `combustibilidad` -- solo declarado en los tres
materiales orgánicos que tiene sentido que se pudran con agua
estancada (madera 0.3, fibra 0.5, hierba_seca 0.6, PROVISIONAL razonado
por dureza/densidad relativa); los minerales quedan en 0.0 implícito
(mismo `.get(material, {}).get("vulnerabilidad_agua", 0.0)` que ya usa
combustibilidad, sin tocar sus entradas). Mecánica de daño idéntica a
la del fuego sobre construcciones (`sistema_desastres.py`, mismo
bloque replicado con `vulnerabilidad_agua`/`tasa_dano_inundacion_por_tick`
en vez de `combustibilidad`/`dano_por_tick_en_llamas`): consume masa
por material, recalcula `progreso`, colapsa (`ConstruccionColapsada`,
causa `"inundacion"`) si todo el material cae por debajo del umbral de
purga ya existente.

Config: `dias_humedos_para_inundacion=5`, `incremento_charco_desborde=0.15`,
`tasa_dano_inundacion_por_tick=0.1`. PROVISIONAL.

**Verificado real**: 32 ciclos completos de inundación en 333 días
(mucho más frecuente que la sequía, coherente con que lluvioso+tormenta+ventisca
cubren más días que despejado+ola_calor en el catálogo de probabilidades
por estación).

## Estado no persistido, decisión explícita

`dias_secos_consecutivos`/`en_sequia`/`dias_humedos_consecutivos`/
`en_inundacion`/`celdas_inundadas` NO se persisten -- mismo criterio ya
aceptado para `clima_actual`/`estacion_previa` (`nucleo/zona_bioma.py`):
se resembraría en el primer corte de día tras cargar una partida. Una
sequía o inundación en curso se "olvida" al recargar, aceptado como el
resto de estado de clima no persistido.

## Verificación

- 803 tests pasan (789 antes de este círculo + 14 nuevos,
  `tests/test_desastres_naturales.py`).
- Smoke test real de 8000 ticks (333 días) con fauna sembrada en
  bosque: confirma que las tres piezas nuevas se ejercen de verdad
  (69 RayoImpacto, 8 ciclos de sequía, 32 ciclos de inundación) y que
  la recalibración de incendio corrige el hueco original (32 muertes
  por incendio, antes 0) -- con la observación honesta de posible
  sobrecorrección (incendio pasó a ser la causa de muerte dominante),
  señalada como PROVISIONAL sin ajustar más por esta única corrida.
