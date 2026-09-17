# Criterio de diversidad sostenida: sustituye a "todas a la vez"

Fecha: 2026-09-17. Origen: tras el harness completo (15×10000 ticks,
criterio maestro original en 0%), Diego señaló dos problemas reales del
criterio de 2026-09-06 (5 especies vivas a la vez, ≥50% de semillas):
es una foto fija del último tick (una especie que prosperó casi toda la
partida y colapsó al final puntúa igual de mal que una que nunca
arrancó), y exigir que TODAS coexistan a la vez es cada vez menos
plausible según crece el catálogo (9 especies hoy, más en camino) --
"es normal que en ecosistemas haya criaturas que prosperen más".

## Decisión: abandonar "todas a la vez", no solo bajar el número

Se consideraron tres opciones (ver conversación): bajar el umbral (K de
N especies vivas a la vez), medir persistencia en el tiempo, o
sustituir la condición conjunta por techos independientes por especie.
Diego eligió combinar las dos últimas -- ninguna exige coexistencia
simultánea.

## Diseño

### B) Diversidad media sostenida en el tiempo

Nuevo campo `diversidad_media_temporal` (por semilla,
`herramientas/harness_calibracion.py::correr_semilla`): promedio del
número de especies con población > 0, muestreado en los mismos puntos
que ya usaba `trayectoria` (cada 1000 ticks) -- no se inventa ningún
muestreo nuevo, `trayectoria` ya existía para otro fin (gráficas de
evolución) y ya tiene exactamente los datos que hacían falta.

Sustituye a la pregunta "¿están todas vivas en el último tick?" por
"¿cuántas especies hay vivas, en promedio, a lo largo de TODA la
partida?" -- una especie que prosperó 9000 de 10000 ticks y colapsó al
final por mala suerte tarde puntúa mucho mejor que una que nunca llegó
a establecerse, justicia real que el criterio anterior no hacía (se
confirmó con zorro/águila en la propia medición que motivó este
círculo: curvas reproductivas sanas, colapso solo al final).

### C) Techo de extinción por especie, independiente

La tabla de "extinción por especie" ya existía en el harness (sin
cambios) -- lo nuevo es una lectura explícita contra un umbral fijo:
`TECHO_EXTINCION_AVISO = 0.5` (PROVISIONAL). Cualquier especie que se
extinga en más de esa fracción de semillas se lista explícitamente en
el resumen como necesitada de calibración, con independencia de qué
les pase a las demás -- desacopla especies entre sí (evita el problema
combinatorio "todas a la vez" que crece con el catálogo) y es
directamente accionable: dice CUÁL especie calibrar primero, en vez de
un aprobado/suspenso agregado que oculta el problema real.

## Qué pasa con el criterio original

Se conserva el cálculo (`especies_vivas_criterio_5`) y su impresión en
el resumen, pero degradado a nota histórica explícita ("[histórico, ya
no es el criterio principal]") -- por comparabilidad con las
mediciones ya citadas en `CLAUDE.md` (2026-09-06, 2026-09-12), no como
objetivo a perseguir. Se retira el "criterio extendido" (7 especies
vivas a la vez) sin reemplazo -- estaba ya hardcodeado a un número fijo
de especies (7) que quedó obsoleto en cuanto el catálogo creció a 9 con
águila, y respondía a la misma lógica de "todas a la vez" que se
abandona aquí.

## Corrección de paso, no parte del diseño original

`ESPECIES` (lista de especies que el harness rastrea) no incluía
`"aguila"` -- gap real descubierto al analizar el harness completo de
hoy (tuve que consultar el JSON crudo para confirmar que águila
aparecía extinta en las 15 semillas, porque el resumen impreso ni
siquiera la mencionaba). Corregido aquí porque el nuevo criterio de
diversidad sostenida sería incorrecto sin ella -- de lo contrario,
águila podría estar viva o extinta sin que ninguna de las dos métricas
nuevas lo reflejara.

## Qué NO se toca

- El propio motor de simulación -- este círculo es enteramente
  infraestructura de medición (`herramientas/harness_calibracion.py`),
  sin ningún cambio de comportamiento del juego.
- `trayectoria` -- se reutiliza tal cual, sin cambiar su cadencia de
  muestreo (cada 1000 ticks) ni su formato.

## Pendiente, no resuelto aquí

- `TECHO_EXTINCION_AVISO=0.5` es PROVISIONAL, elegido por continuidad
  con el umbral que ya se discutía de palabra, no calibrado.
- No se han vuelto a correr las 15 semillas con este nuevo criterio
  todavía -- el harness de 15×10000 de hoy se corrió y analizó ANTES de
  este círculo, con el criterio antiguo. Falta una lectura futura con
  el criterio nuevo para saber si el panorama real (más allá del 0%
  agregado) es mejor de lo que parecía.
