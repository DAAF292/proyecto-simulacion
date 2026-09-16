# Servidor de control remoto: lanzar/pausar/acelerar/finalizar una partida desde el navegador

Fecha: 2026-09-16. Origen: Diego preguntó si sería posible alojar el
programa en algún sitio y lanzar una partida remota por web. Tras aclarar
que de momento es para uso propio (una sola partida, un solo espectador,
sin necesidad de aislar sesiones), su queja concreta sobre el estado
actual fue: "lo que no me convence es la forma de lanzarlo, debería haber
un comando... el front nos tiene que permitir controlar la velocidad,
parar, reanudar y finalizar la simulación". Arquitectura ya confirmada
con Diego antes de escribir este documento (proceso único siempre
encendido + hilo por partida + barra de control en el mismo visor, sin
página de arranque separada, sin múltiples partidas simultáneas).

**Nota sobre el flujo de implementación**: esto NO es una regla/mecanismo
nuevo del motor de simulación (no cambia ninguna ley de comportamiento
del mundo) -- es infraestructura de control/presentación, la misma
categoría que ya cubre `presentacion/vista_web.py` y
`presentacion/terminal_prototipo/terminal.html`, ambos editados
directamente por Claude durante toda esta sesión sin pasar por el
pipeline autónomo. Por ese motivo, y porque el centinela del pipeline
sigue parado en este entorno (ver CLAUDE.md), esta spec se implementa
directamente en la sesión, no se suelta como encargo.

## Estado actual (verificado contra el código real antes de diseñar)

- `main.py:main()` lee `SIMULACION_MODO_VISUAL`/`SIMULACION_AUTO_TICKS`/
  `SIMULACION_CONTINUAR` **una sola vez al arrancar** el proceso. No existe
  ningún mecanismo para pausar, acelerar ni finalizar sin matar el
  proceso (Ctrl+C, que además solo funciona en local).
- La semilla es siempre `config.get("semilla_por_defecto", 42)` -- fija,
  nunca aleatoria, nunca elegida en caliente.
- `presentacion/vista_web.py:ServidorWeb` ya es un `ThreadingHTTPServer`
  en un hilo daemon -- correcto punto de apoyo, no hace falta un
  framework nuevo. Solo expone `GET` (`do_GET`); no existe `do_POST`.
- `construir_instantanea()` lee `mundo.config.get("semilla_por_defecto")`
  directamente para el campo `"semilla"` del DTO -- funcionaba porque
  hasta ahora la semilla nunca cambiaba en caliente.
- El bucle de tick (`main.py:562-604`) hace TODO en la misma función:
  ejecutar tick, procesar eventos para persistencia/narrador, actualizar
  `servidor_web`, dormir `segundos_por_tick`, autoguardado periódico.
  Tras el `while`, si `auto_ticks > 0`, imprime ~25 bloques de
  estadísticas de verificación de circuitos ya cerrados -- utilidad
  exclusiva del modo CLI de testing/calibración, no aplica al modo
  controlado por web.

## Diseño

### Pieza 1: `nucleo/control_partida.py` (nuevo, pequeño)

```python
class ControlPartida:
    def __init__(self) -> None:
        self.pausado = threading.Event()          # set() == en pausa
        self.detener = threading.Event()          # set() == debe terminar
        self._velocidad_lock = threading.Lock()
        self._velocidad = 1.0

    @property
    def velocidad(self) -> float: ...
    @velocidad.setter
    def velocidad(self, factor: float) -> None: ...  # clamp [0.25, 8.0]
```

Sin lock para `pausado`/`detener` (los `threading.Event` ya son
thread-safe por diseño de la librería estándar); lock solo para
`_velocidad` porque es un float mutable simple, para evitar un
read-modify-write no atómico si en el futuro se le suma más lógica al
setter. Límites `[0.25, 8.0]` PROVISIONAL, sin calibrar contra el coste
real de tick a distintas velocidades -- una `segundos_por_tick=0.4`
config con factor 8.0 deja 0.05s de sleep real por tick, suficiente
margen para no saturar CPU en una máquina modesta, pero no medido.

### Pieza 2: refactor de `main.py` (sin cambiar el comportamiento del modo CLI)

Extraer, SIN cambiar una sola línea de lo que ya hacen (solo mover código
a funciones nombradas):

- `preparar_partida(semilla: int, config: dict, ruta_base: Path) ->
  EstadoPartida` -- todo el bloque `main.py:503-539` (RNGs, reloj, bus de
  eventos, gestor, persistencia, mundo, siembra inicial o restauración,
  sistemas). `EstadoPartida` es un `dataclass` simple que agrupa esos
  objetos (gestor, mundo, reloj, bus_eventos, sistemas, persistencia,
  rng_juego, rng_reproduccion, semilla) -- ningún comportamiento nuevo,
  solo nombrar lo que hoy son variables locales sueltas de `main()` para
  poder pasarlas como una unidad a la nueva función controlada.
- `avanzar_un_tick(estado: EstadoPartida, cola_cronica, modo_visual: bool,
  auto_ticks: int) -> None` -- el cuerpo del `while` (`main.py:575-604`,
  sin el `time.sleep` de la rama visual, que se queda fuera porque el
  bucle controlado necesita dormir según `control.velocidad`, no según
  una constante).

`main()` sigue exactamente igual en comportamiento observable: llama a
estas dos funciones donde antes tenía el código inline, conserva su
propio `while True` con `auto_ticks`/`SIMULACION_MODO_VISUAL` y todo el
bloque de estadísticas de cierre intacto. **Los 658 tests actuales y
cualquier harness de calibración (`SIMULACION_AUTO_TICKS`) deben seguir
pasando sin cambios** -- es la condición de aceptación de este paso.

Nueva función, exclusiva del modo controlado:

```python
def ejecutar_partida_controlada(
    semilla: int,
    control: ControlPartida,
    servidor_web: ServidorWeb,
    config: dict,
    ruta_base: Path,
) -> None:
    estado = preparar_partida(semilla, config, ruta_base)
    cola_cronica = collections.deque(maxlen=...)
    segundos_por_tick = float(config.get("visual", {}).get("segundos_por_tick", 0.4))
    try:
        while not control.detener.is_set():
            # Pausa: espera cooperativa, no busy-wait puro. wait(timeout)
            # en vez de wait() a secas para poder reaccionar a `detener`
            # si llega mientras está en pausa.
            while control.pausado.is_set() and not control.detener.is_set():
                control.pausado_event_interno.wait(timeout=0.2)  # o control.detener.wait(timeout=0.2)
            if control.detener.is_set():
                break

            avanzar_un_tick(estado, cola_cronica, modo_visual=True, auto_ticks=0)

            payload = construir_instantanea(estado.mundo, estado.gestor, estado.reloj, list(cola_cronica), estado.semilla)
            payload["partida"] = {
                "activa": True,
                "pausada": False,
                "semilla": estado.semilla,
                "velocidad": control.velocidad,
            }
            servidor_web.actualizar_instantanea(payload)
            time.sleep(segundos_por_tick / control.velocidad)
    finally:
        estado.persistencia.guardar_snapshot(
            estado.gestor, estado.mundo, estado.reloj,
            estado.rng_juego, estado.semilla, estado.rng_reproduccion,
        )
```

(Pseudocódigo simplificado -- el `wait` sobre pausa exacto se resuelve al
implementar, ver nota "espera de pausa" más abajo.)

**Nota "espera de pausa"**: un `threading.Event` no tiene un `wait()` que
reaccione a OTRO Event distinto de forma nativa. La forma simple: la
pausa se implementa como un `while control.pausado.is_set() and not
control.detener.is_set(): control.detener.wait(timeout=0.2)` -- reutiliza
`detener.wait()` como temporizador (siempre devuelve tras 0.2s si
`detener` no se activa), consultando `pausado` de nuevo en cada vuelta.
Encender `detener` mientras está en pausa la despierta de inmediato
(pausado Y detenido a la vez -> sale del `while` interior por la
condición `not control.detener.is_set()`).

### Pieza 3: `presentacion/gestor_partidas.py` (nuevo)

```python
class GestorPartidas:
    def __init__(self, servidor_web: ServidorWeb, config: dict, ruta_base: Path) -> None:
        self._servidor_web = servidor_web
        self._config = config
        self._ruta_base = ruta_base
        self._control: ControlPartida | None = None
        self._hilo: threading.Thread | None = None
        self._semilla_actual: int | None = None
        self._servidor_web.instantanea_json = json.dumps({"partida": {"activa": False, "pausada": False, "semilla": None, "velocidad": 1.0}})

    def nueva(self, semilla: int | None = None) -> int:
        self._detener_hilo_actual()
        semilla_real = semilla if semilla is not None else random.randint(0, 2**31 - 1)
        self._control = ControlPartida()
        self._semilla_actual = semilla_real
        self._hilo = threading.Thread(
            target=ejecutar_partida_controlada,
            args=(semilla_real, self._control, self._servidor_web, self._config, self._ruta_base),
            daemon=True,
        )
        self._hilo.start()
        return semilla_real

    def pausar(self) -> bool:
        if self._control is None: return False
        self._control.pausado.set(); return True

    def reanudar(self) -> bool: ...  # simétrico, .clear()

    def velocidad(self, factor: float) -> float | None:
        if self._control is None: return None
        self._control.velocidad = factor  # el setter clampa
        return self._control.velocidad

    def finalizar(self) -> bool:
        return self._detener_hilo_actual()

    def _detener_hilo_actual(self) -> bool:
        if self._hilo is None: return False
        self._control.detener.set()
        self._hilo.join()
        self._hilo = None
        self._control = None
        self._servidor_web.instantanea_json = json.dumps({"partida": {"activa": False, "pausada": False, "semilla": None, "velocidad": 1.0}})
        return True
```

`GestorPartidas` importa de `presentacion.vista_web` (`ServidorWeb`,
`construir_instantanea`) y de `main` (`ejecutar_partida_controlada`) --
vive en `presentacion/` porque es control de PRESENTACIÓN (arrancar/
parar lo que se muestra), no una regla del motor. Import circular
evitado: `main.py` seguirá importando de `presentacion.vista_web`
(como ya hace hoy), nunca de `presentacion.gestor_partidas` -- la
dependencia va en un solo sentido (`gestor_partidas` -> `main` +
`vista_web`, nunca al revés).

### Pieza 4: endpoints en `presentacion/vista_web.py`

`ManejadorWeb` gana `do_POST`, y `ServidorWeb` gana un atributo
`gestor_partidas: GestorPartidas | None = None` (inyectado DESPUÉS de
construir ambos objetos, para no invertir la dependencia).

| Método | Ruta | Body | Respuesta | Notas |
|---|---|---|---|---|
| POST | `/partida/nueva` | `{}` o `{"semilla": N}` | `{"ok": true, "semilla": N}` | Detiene la partida activa si la había (sin confirmación en el backend -- la confirmación es cosa del frontend) |
| POST | `/partida/pausar` | (vacío) | `{"ok": true}` / 409 si no hay partida | |
| POST | `/partida/reanudar` | (vacío) | `{"ok": true}` / 409 | |
| POST | `/partida/velocidad` | `{"factor": F}` | `{"ok": true, "velocidad": F_clampado}` / 409 | |
| POST | `/partida/finalizar` | (vacío) | `{"ok": true}` | Idempotente: finalizar sin partida activa responde `{"ok": true}` igualmente (no es un error querer asegurarse de que no hay nada corriendo) |

Si `servidor_ref.gestor_partidas is None` (caso: el servidor lo arrancó
`main.py` en modo `SIMULACION_MODO_VISUAL=1` de toda la vida, no el nuevo
`servidor.py`) -> **501 Not Implemented** para cualquier ruta
`/partida/*`. Así el modo CLI de debug local sigue funcionando exactamente
igual que hoy, sin saber nada de control remoto ni verse afectado por
este círculo.

Body JSON inválido -> 400. Ruta desconocida bajo `/partida/` o método no
soportado -> 404/405 (patrón ya usado en el resto del fichero).

### Pieza 5: `construir_instantanea()` -- un solo cambio de firma

```python
def construir_instantanea(mundo, gestor, reloj, cronica, semilla: int) -> dict:
    ...
    return {
        ...
        "semilla": semilla,  # antes: mundo.config.get("semilla_por_defecto")
        ...
    }
```

La clave `"partida": {...}` (activa/pausada/semilla/velocidad) **NO** se
añade dentro de esta función -- se queda fuera de su contrato (que sigue
siendo "serializar el estado del mundo", nada de control-plane) y la
añade quien construye el payload final (`ejecutar_partida_controlada` en
el modo controlado; en el modo CLI de `main.py`, si se quiere mantener el
campo por consistencia del contrato JSON, se añade `{"activa": true,
"pausada": false, "semilla": semilla, "velocidad": 1.0}` fijo -- decisión
menor a resolver al implementar, no cambia nada del motor).

Único call site existente a actualizar: `main.py:597`
(`construir_instantanea(mundo, gestor, reloj, list(cola_cronica))` ->
añadir `semilla`, valor ya disponible como variable local, cero cambio de
comportamiento).

### Pieza 6: `servidor.py` (nuevo, raíz del repo) -- "un comando"

```python
"""Arranca el servidor de control remoto (ServidorWeb + GestorPartidas)
SIN lanzar ninguna partida -- todo lo demás (nueva partida, pausar,
velocidad, finalizar) se controla desde el navegador. Este es el único
comando que hay que ejecutar en la máquina remota; se queda corriendo
hasta Ctrl+C o hasta que el proceso se detenga (systemd/tmux/screen,
decisión de despliegue de Diego, fuera de alcance de este documento)."""

if __name__ == "__main__":
    ruta_base = Path(__file__).parent
    config = cargar_configuracion(ruta_base / "config")
    puerto = int(config.get("visual", {}).get("puerto", 8765))
    servidor_web = ServidorWeb(puerto)
    servidor_web.gestor_partidas = GestorPartidas(servidor_web, config, ruta_base)
    servidor_web.iniciar()
    print(f"Servidor de control en http://0.0.0.0:{puerto} -- Ctrl+C para parar")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        if servidor_web.gestor_partidas is not None:
            servidor_web.gestor_partidas.finalizar()
        servidor_web.detener()
```

`main.py` no cambia su rol de entrypoint CLI (`python3 main.py` con
env vars sigue funcionando para tests/calibración/debug local); `servidor.py`
es el nuevo entrypoint para el caso de uso remoto de Diego.

### Pieza 7: `terminal.html` -- barra de control + pantalla de espera

- Nueva franja de controles (en `.titulo` del panel de mapa, junto al
  reloj/zoom ya existentes): botón **NUEVA PARTIDA**, botón
  **PAUSAR/REANUDAR** (toggle, texto según `partida.pausada`), selector
  de velocidad (0.5x/1x/2x/4x/8x), botón **FINALIZAR**.
- El polling ya existente a `/estado.json` (cada ~1s) se reutiliza sin
  cambios de mecanismo -- ahora también lee `DATA.partida` para
  actualizar el estado de los botones y decidir qué pantalla mostrar.
- Cuando `DATA.partida.activa === false`: el área de mapa se sustituye
  por un panel simple ("SIN PARTIDA ACTIVA -- pulsa NUEVA PARTIDA para
  empezar"), sin intentar leer `celdas`/`entidades` (no existen en ese
  payload).
- Los botones llaman a los endpoints nuevos vía `fetch(..., {method:
  'POST', body: JSON.stringify(...)})`; no se implementa optimistic UI
  más allá de deshabilitar el botón mientras la petición está en vuelo
  (evita doble-clic disparando dos partidas nuevas seguidas).
- `NUEVA PARTIDA` y `FINALIZAR` piden confirmación nativa del navegador
  (`confirm()`) cuando ya hay una partida activa -- sin construir un
  modal propio para esto, no lo pidió Diego y `confirm()` cubre el caso
  real (evitar perder una partida en curso sin querer).

## Fuera de alcance, explícito (Principio 4, honestidad)

- **Sin autenticación ni autorización.** Cualquiera con la URL puede
  arrancar/pausar/finalizar la partida. Diego dijo "de momento solo
  quiero verlo yo" -- aceptable para un servidor personal no anunciado
  públicamente, pero es un hueco real, no resuelto aquí. Si en algún
  momento se comparte la URL con más gente, esto necesita revisarse
  antes.
- **Sin TLS.** `http.server` sigue sirviendo en claro. Si se expone
  directo a internet (no solo a una red privada/VPN), un proxy inverso
  (nginx/Caddy) con certificado delante es responsabilidad de despliegue
  de Diego, no de este código.
- **Una única partida a la vez, un único espectador implícito.** No hay
  aislamiento de sesiones ni multi-usuario -- exactamente lo que Diego
  pidió para "de momento".
- **Sin histórico de partidas anteriores.** Cada "nueva partida" corre
  sobre `datos/simulacion.db` sin archivar la anterior -- mismo
  comportamiento que ya tiene `main()` sin `SIMULACION_CONTINUAR` hoy (mundo
  fresco cada vez, la BD se sobreescribe en el primer autoguardado). No
  se resuelve un mecanismo de guardado múltiple en este círculo.
- **Sin reanudar una partida finalizada.** "Finalizar" siempre implica
  que la siguiente partida es nueva (semilla nueva o indicada), nunca
  una continuación de snapshot -- si se quiere retomar la última partida
  guardada, seguiría siendo `SIMULACION_CONTINUAR=1` por el camino CLI
  (`main.py`), no por el camino web (fuera de alcance salvo que Diego lo
  pida explícitamente después).
- **Límites de velocidad (`[0.25, 8.0]`) sin calibrar** contra coste real
  de tick a distintas velocidades -- hipótesis de partida razonada, no
  medida.

## Plan de verificación

- Tests dirigidos nuevos para `ControlPartida`/`GestorPartidas`: pausar
  detiene el avance real de `reloj.tick_actual` (verificado esperando y
  comprobando que no sube), reanudar lo retoma, velocidad cambia el
  intervalo de sleep real (mockeable), `nueva()` con una partida ya
  corriendo deja el hilo anterior realmente muerto (`Thread.is_alive() ==
  False`) antes de arrancar el siguiente.
- Test de `construir_instantanea()` con la nueva firma (`semilla`
  explícita) -- confirmar que el campo `"semilla"` del DTO refleja el
  valor pasado, no `config["semilla_por_defecto"]`.
- Suite completa (`pytest tests/`) debe seguir en 658/658 -- ninguna
  pieza de este círculo toca comportamiento del motor de simulación en
  sí, solo su orquestación externa.
- Verificación manual contra el servidor real (Playwright, mismo patrón
  ya usado en esta sesión para el visor): arrancar `servidor.py`,
  confirmar pantalla de espera, pulsar "nueva partida", ver el mapa
  aparecer con una semilla real distinta de la de config, pausar y
  confirmar que el tick deja de avanzar, cambiar velocidad y confirmar
  que el ritmo de refresco cambia, finalizar y confirmar el retorno a la
  pantalla de espera.
