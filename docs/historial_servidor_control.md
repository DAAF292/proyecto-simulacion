# Historial — Renombrado BOSQUE_*→SIMULACION_* y servidor de control remoto

> **Archivado de `CLAUDE.md` el 2026-09-17**, dentro de la poda de la
> sección "Estado actual y pendientes reales" (había crecido a ~465
> líneas mezclando pendientes genuinos con crónica detallada de piezas ya
> cerradas — mismo patrón que ya obligó a la poda de la Bitácora completa
> el 2026-09-15). Este fichero es historial puro — registro tal cual se
> escribió en su momento, sin reescribir ni resumir. Para la orientación
> rápida vigente del proyecto, ver `CLAUDE.md`.

## Renombrado `BOSQUE_* -> SIMULACION_*` (2026-09-16)

Diego, sobre la spec de abajo: "lo de que aparezca bosque en todos los
comandos de test... deberíamos cambiarlo por simulación, que es lo que
es, ya no es un solo bosque". `SIMULACION_MODO_VISUAL`/
`SIMULACION_AUTO_TICKS`/`SIMULACION_CONTINUAR` (las 3 únicas lecturas
reales de `os.environ` del proyecto) y `datos/bosque.db` →
`datos/simulacion.db`. Alcance acotado a código y documentación VIVA
(`main.py`, comentarios en `sistemas/`/`nucleo/` que citan el nombre,
`COMANDOS.md`, README del visor) — la bitácora histórica ya cerrada
(`docs/historial_*.md`, `docs/plans/*`, las specs de sesiones anteriores)
conserva el nombre real usado en su momento a propósito, no se reescribió.

## Servidor de control remoto (2026-09-16)

Ver `docs/superpowers/specs/2026-09-16-servidor-control-remoto-design.md`,
implementado directamente por Claude el mismo día — infraestructura de
control/presentación, no una regla nueva del motor. Diego preguntó si
podía alojarse el programa y lanzar/controlar una partida remota por web,
con la queja explícita de que el arranque actual por env vars "debería
ser un comando". `python3 servidor.py` (nuevo, raíz) arranca
`ServidorWeb`+`GestorPartidas` sin lanzar ninguna partida; desde el
navegador (barra de control nueva en `terminal.html`): NUEVA PARTIDA
(semilla aleatoria u opcional), PAUSAR/REANUDAR, velocidad (0.25x-8x,
límites sin calibrar), FINALIZAR — 5 endpoints `POST /partida/*` nuevos
en `vista_web.py`, 501 si el servidor no tiene `GestorPartidas`
inyectado (modo CLI de `main.py` de siempre, sin cambios de
comportamiento, condición de aceptación verificada con los 658 tests
previos intactos). `main.py` se refactorizó en
`preparar_partida()`/`avanzar_un_tick()` reutilizables entre el modo CLI
y el nuevo `ejecutar_partida_controlada()` (hilo de fondo,
`nucleo/control_partida.py:ControlPartida` con pausado/detener/velocidad
thread-safe). **Bug real encontrado en verificación manual contra el
servidor real, no en tests**: `pausada` quedaba hardcodeada a `False` en
el payload, y aunque se leyera bien de `control`, el hilo se queda
bloqueado dentro de la espera de pausa y NUNCA vuelve a publicar mientras
dura — `GestorPartidas.pausar()/reanudar()` parchean ahora directamente
el último JSON servido. Verificado con Playwright contra el servidor real
(no solo tests): ciclo completo pantalla de espera → nueva partida →
mapa real → pausa (tick congelado, confirmado con dos lecturas) →
reanudar → velocidad → finalizar → vuelta a pantalla de espera. Sin
autenticación ni TLS (aceptado por ahora, "solo quiero verlo yo"; hueco
real si se comparte la URL); una partida nueva sobreescribe
`datos/simulacion.db` sin histórico de partidas anteriores. **Pendiente
real**: Diego no ha desplegado esto en ninguna máquina remota todavía,
solo verificado en local dentro de esta sesión — sigue sin probarse el
caso de uso real que lo motivó.
