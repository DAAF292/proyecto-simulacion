# RNG propio para sistema_reproduccion.py — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `sistemas/sistema_reproduccion.py` comparte hoy `rng_juego` con el resto del motor (`main.py:instanciar_sistemas`). CLAUDE.md documenta (sección "Sobrepoblación sin techo aparente") que esto hace poco fiable comparar la misma semilla entre dos versiones de código: cambiar cuántas tiradas de `random()` consume la reproducción desplaza la secuencia de aleatoriedad que consumen TODOS los demás sistemas en los ticks siguientes. Este plan le da a `SistemaReproduccion` su propio generador (`rng_reproduccion`), independiente de `rng_juego`, y persiste/restaura su estado igual que ya se hace con `rng_juego`.

**Architecture:** Mismo patrón que ya existe en el propio `main.py` para `rng_mapa` (una segunda instancia de `random.Random(semilla)`, independiente de `rng_juego` aunque nazca de la misma semilla — no hace falta inventar ningún mecanismo nuevo de generación aleatoria). Se añade una tercera instancia, `rng_reproduccion`, que se inyecta únicamente en `SistemaReproduccion` en vez de `rng_juego`. Su estado se persiste en `configuracion_ejecucion` bajo una clave nueva (`rng_reproduccion_state`), con el mismo mecanismo de pickle que ya usa `rng_juego_state`.

**Tech Stack:** Python 3, módulo `random` estándar, sqlite3 estándar (sin ORM), pytest — mismo criterio que el resto de `tests/`.

**Spec:** Ninguna — fix mecánico de una sola causa ya diagnosticada y documentada en CLAUDE.md, sin ambigüedad de diseño.

## Global Constraints

- No cambiar la fórmula de concepción ni ningún otro comportamiento de `sistema_reproduccion.py` — este plan SOLO cambia qué objeto `random.Random` usa, no cuándo ni cuánto lo usa.
- `rng_reproduccion` se siembra con la MISMA `semilla` que `rng_juego`/`rng_mapa` (`random.Random(semilla)`) — sigue siendo una partida 100% reproducible a partir de una única semilla de configuración, solo se desacopla el ORDEN de consumo entre subsistemas.
- No modificar ninguna aserción de los 24 tests ya existentes en `tests/`.
- No tocar el esquema de la tabla `configuracion_ejecucion` (ya es genérica `clave TEXT, valor BLOB` — solo se añade una fila nueva bajo una clave nueva, igual que ya hace `rng_juego_state`).

---

## File Structure

- `main.py` — nueva variable `rng_reproduccion`, nuevo parámetro en `instanciar_sistemas`, y actualización de las 3 llamadas a `persistencia.guardar_snapshot`/`cargar_snapshot` para pasarle también `rng_reproduccion`.
- `nucleo/persistencia.py` — `guardar_snapshot`/`cargar_snapshot` ganan un parámetro `rng_reproduccion: random.Random` y persisten/restauran su estado bajo la clave `'rng_reproduccion_state'`.
- `tests/test_rng_reproduccion.py` — nuevo, dos tests de "ley física": (1) `SistemaReproduccion` recibe un generador distinto de `rng_juego`; (2) el estado de `rng_reproduccion` sobrevive un roundtrip real de guardar/cargar snapshot, de forma independiente del de `rng_juego`.

---

### Task 1: `rng_reproduccion` propio, inyectado en `SistemaReproduccion`

**Files:**
- Modify: `main.py`
- Test: `tests/test_rng_reproduccion.py`

**Interfaces:**
- Produces: `instanciar_sistemas(config: dict[str, Any], rng_juego: random.Random, rng_reproduccion: random.Random) -> dict[str, Any]` — mismo nombre y forma que hoy, con un parámetro posicional nuevo al final.
- Consumes: `SistemaReproduccion.__init__(self, config: dict, rng) -> None` (ya existe, sin cambios — solo cambia qué objeto se le pasa como `rng` en `instanciar_sistemas`).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_rng_reproduccion.py`:

```python
"""Test de independencia del generador aleatorio de reproduccion
(2026-09-02, ver CLAUDE.md, seccion "Sobrepoblacion sin techo aparente").

sistema_reproduccion.py compartia rng_juego con el resto del motor --
cambiar cuantas tiradas de random() consume la reproduccion desplazaba
la secuencia de aleatoriedad que consumen TODOS los demas sistemas en
los ticks siguientes, haciendo que comparar la misma semilla entre dos
versiones de codigo no fuera fiable. Estos tests verifican que
SistemaReproduccion recibe su PROPIO generador, independiente de
rng_juego, aunque ambos nazcan de la misma semilla."""
import random
from pathlib import Path

from main import cargar_configuracion, instanciar_sistemas
from sistemas.sistema_reproduccion import SistemaReproduccion

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_sistema_reproduccion_usa_su_propio_rng_no_el_compartido():
    """Ley: instanciar_sistemas debe pasar a SistemaReproduccion un
    generador DISTINTO de rng_juego -- no la misma instancia, aunque
    ambos se siembren con la misma semilla."""
    config = cargar_configuracion(RUTA_CONFIG)
    rng_juego = random.Random(42)
    rng_reproduccion = random.Random(42)

    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    assert isinstance(sistemas["reproduccion"], SistemaReproduccion)
    assert sistemas["reproduccion"].rng is rng_reproduccion
    assert sistemas["reproduccion"].rng is not rng_juego


def test_consumir_rng_juego_no_desplaza_rng_reproduccion():
    """Ley: avanzar rng_juego (como hacen el resto de sistemas cada tick)
    no debe alterar el estado de rng_reproduccion -- son dos flujos
    independientes, aunque nazcan de la misma semilla."""
    config = cargar_configuracion(RUTA_CONFIG)
    rng_juego = random.Random(42)
    rng_reproduccion = random.Random(42)
    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)

    estado_antes = sistemas["reproduccion"].rng.getstate()

    for _ in range(50):
        rng_juego.random()

    estado_despues = sistemas["reproduccion"].rng.getstate()
    assert estado_antes == estado_despues
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_rng_reproduccion.py -v`
Expected: `TypeError: instanciar_sistemas() takes 2 positional arguments but 3 were given` — el parámetro no existe todavía (verificado literal contra el código real antes de escribir este plan).

- [ ] **Step 3: Añadir el parámetro a `instanciar_sistemas` y usarlo para `SistemaReproduccion`**

En `main.py`, busca este bloque:

```python
def instanciar_sistemas(
    config: dict[str, Any],
    rng_juego: random.Random,
) -> dict[str, Any]:
    """Instancia todos los sistemas del motor inyectando configuración y generador determinista."""
    return {
        "decision": SistemaDecision(config, rng_juego),
        "movimiento": SistemaMovimiento(config, rng_juego),
        "desastres": SistemaDesastres(config, rng_juego),
        "depredacion": SistemaDepredacion(config, rng_juego),
        "recursos": SistemaRecursos(config, rng_juego),
        "necesidades": SistemaNecesidades(config, rng_juego),
        "capacidad_fisica": SistemaCapacidadFisica(config),
        "capacidad_mental": SistemaCapacidadMental(config),
        "reproduccion": SistemaReproduccion(config, rng_juego),
        "clima": SistemaClima(config, rng_juego),
        "descomposicion": SistemaDescomposicion(config, rng_juego),
        "flora": SistemaFlora(config, rng_juego),
        "ciclo_vital": SistemaCicloVital(config, rng_juego),
        "asentamiento": SistemaAsentamiento(config, rng_juego),
    }
```

Sustitúyelo por (solo cambia la firma y la línea de `"reproduccion"`, el resto de claves se quedan exactamente igual):

```python
def instanciar_sistemas(
    config: dict[str, Any],
    rng_juego: random.Random,
    rng_reproduccion: random.Random,
) -> dict[str, Any]:
    """Instancia todos los sistemas del motor inyectando configuración y generador determinista.

    rng_reproduccion (2026-09-02, ver CLAUDE.md): generador PROPIO e
    independiente de rng_juego para SistemaReproduccion -- mismo patrón
    que rng_mapa ya usa para separar la generación de terreno del resto
    del motor. Evita que cambiar cuántas tiradas de random() consume la
    reproducción desplace la secuencia que consumen los demás sistemas.
    """
    return {
        "decision": SistemaDecision(config, rng_juego),
        "movimiento": SistemaMovimiento(config, rng_juego),
        "desastres": SistemaDesastres(config, rng_juego),
        "depredacion": SistemaDepredacion(config, rng_juego),
        "recursos": SistemaRecursos(config, rng_juego),
        "necesidades": SistemaNecesidades(config, rng_juego),
        "capacidad_fisica": SistemaCapacidadFisica(config),
        "capacidad_mental": SistemaCapacidadMental(config),
        "reproduccion": SistemaReproduccion(config, rng_reproduccion),
        "clima": SistemaClima(config, rng_juego),
        "descomposicion": SistemaDescomposicion(config, rng_juego),
        "flora": SistemaFlora(config, rng_juego),
        "ciclo_vital": SistemaCicloVital(config, rng_juego),
        "asentamiento": SistemaAsentamiento(config, rng_juego),
    }
```

- [ ] **Step 4: Crear `rng_reproduccion` en `main()` y actualizar la llamada a `instanciar_sistemas`**

En `main.py`, busca este bloque (dentro de `main()`, justo después de crear `rng_juego`):

```python
    semilla = config.get("semilla_por_defecto", 42)
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
```

Sustitúyelo por:

```python
    semilla = config.get("semilla_por_defecto", 42)
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
    # rng_reproduccion (2026-09-02, ver CLAUDE.md): mismo patrón que
    # rng_mapa -- generador independiente sembrado con la misma semilla,
    # para que sistema_reproduccion.py no comparta flujo con rng_juego.
    rng_reproduccion = random.Random(semilla)
```

Después, busca esta línea (más abajo, tras `sembrar_flora_inicial`):

```python
    sistemas = instanciar_sistemas(config, rng_juego)
```

Sustitúyela por:

```python
    sistemas = instanciar_sistemas(config, rng_juego, rng_reproduccion)
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_rng_reproduccion.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `26 passed` (24 existentes + 2 nuevos). NOTA: en este punto `main.py` todavía no compila del todo en su bucle principal para una ejecución real completa (`rng_reproduccion` aún no se pasa a `persistencia.guardar_snapshot`/`cargar_snapshot`, eso es el Task 2) -- pero los tests de `tests/` no ejercitan el bucle principal de `main()`, así que deben pasar igualmente.

- [ ] **Step 7: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add main.py tests/test_rng_reproduccion.py
git commit -m "$(cat <<'EOF'
Añadir rng_reproduccion propio para sistema_reproduccion.py

sistema_reproduccion.py compartía rng_juego con el resto del motor --
cambiar cuántas tiradas de random() consume la reproducción desplazaba
la secuencia de aleatoriedad que consumen TODOS los demás sistemas en
los ticks siguientes (ver CLAUDE.md, "Sobrepoblación sin techo
aparente"). Mismo patrón que ya usa rng_mapa: una instancia
independiente de random.Random(semilla), inyectada solo en
SistemaReproduccion.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01256zvSsQgtHuBBhjD2mz3A
EOF
)"
```

---

### Task 2: Persistir y restaurar el estado de `rng_reproduccion`

**Files:**
- Modify: `nucleo/persistencia.py`
- Modify: `main.py`
- Test: `tests/test_rng_reproduccion.py`

**Interfaces:**
- Produces: `Persistencia.guardar_snapshot(self, gestor, mundo, reloj, rng_juego: random.Random, semilla: int, rng_reproduccion: random.Random) -> None` y `Persistencia.cargar_snapshot(self, gestor, mundo, reloj, rng_juego: random.Random, semilla: int, rng_reproduccion: random.Random) -> bool` — mismas firmas de hoy, con `rng_reproduccion` añadido como último parámetro.
- Consumes: `rng_reproduccion` creado en Task 1 (`main.py`, `random.Random(semilla)`); `instanciar_sistemas` de Task 1 (sin cambios en este Task).

- [ ] **Step 1: Escribir el test que falla**

Añade esto al final de `tests/test_rng_reproduccion.py` (mismo fichero del Task 1, sin tocar los dos tests ya escritos):

```python
import random as random_module
import tempfile
from pathlib import Path as PathlibPath

from nucleo.entidad import GestorEntidades
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj


def test_rng_reproduccion_sobrevive_roundtrip_de_guardar_y_cargar():
    """Ley: el estado de rng_reproduccion se persiste y se restaura de
    forma independiente del de rng_juego -- tras cargar una partida
    guardada, ambos flujos deben continuar exactamente donde se
    quedaron, no reiniciarse desde la semilla."""
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 7

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = PathlibPath(directorio_tmp) / "test_rng_reproduccion.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random_module.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()

        rng_juego = random_module.Random(semilla)
        rng_reproduccion = random_module.Random(semilla)
        # Avanzar cada flujo un número DISTINTO de tiradas antes de
        # guardar, para confirmar que cada uno restaura su propio
        # estado y no el del otro.
        for _ in range(10):
            rng_juego.random()
        for _ in range(30):
            rng_reproduccion.random()

        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)

        estado_juego_esperado = rng_juego.getstate()
        estado_reproduccion_esperado = rng_reproduccion.getstate()

        rng_juego_restaurado = random_module.Random(999)
        rng_reproduccion_restaurado = random_module.Random(999)
        ok = persistencia.cargar_snapshot(
            gestor, mundo, reloj, rng_juego_restaurado, semilla, rng_reproduccion_restaurado
        )

        assert ok is True
        assert rng_juego_restaurado.getstate() == estado_juego_esperado
        assert rng_reproduccion_restaurado.getstate() == estado_reproduccion_esperado
        assert rng_juego_restaurado.getstate() != rng_reproduccion_restaurado.getstate()
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_rng_reproduccion.py::test_rng_reproduccion_sobrevive_roundtrip_de_guardar_y_cargar -v`
Expected: `TypeError: Persistencia.guardar_snapshot() takes 6 positional arguments but 7 were given` — el parámetro no existe todavía (verificado literal contra el código real antes de escribir este plan).

- [ ] **Step 3: Añadir `rng_reproduccion` a `guardar_snapshot`**

En `nucleo/persistencia.py`, busca este bloque:

```python
    def guardar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
    ) -> None:
```

Sustitúyelo por:

```python
    def guardar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
        rng_reproduccion: random.Random,
    ) -> None:
```

Después, busca este bloque (sección "E. Metadatos de ejecución y RNG", dentro del mismo método):

```python
            # E. Metadatos de ejecución y RNG
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('tick_actual', ?)", (reloj.tick_actual,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('semilla', ?)", (semilla,))
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_juego_state', ?)",
                (pickle.dumps(rng_juego.getstate()),),
            )

            con.commit()
```

Sustitúyelo por:

```python
            # E. Metadatos de ejecución y RNG
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('tick_actual', ?)", (reloj.tick_actual,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('version_esquema', ?)", (VERSION_ESQUEMA,))
            cur.execute("REPLACE INTO configuracion_ejecucion VALUES ('semilla', ?)", (semilla,))
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_juego_state', ?)",
                (pickle.dumps(rng_juego.getstate()),),
            )
            cur.execute(
                "REPLACE INTO configuracion_ejecucion VALUES ('rng_reproduccion_state', ?)",
                (pickle.dumps(rng_reproduccion.getstate()),),
            )

            con.commit()
```

- [ ] **Step 4: Añadir `rng_reproduccion` a `cargar_snapshot`**

En `nucleo/persistencia.py`, busca este bloque:

```python
    def cargar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
    ) -> bool:
```

Sustitúyelo por:

```python
    def cargar_snapshot(
        self,
        gestor: GestorEntidades,
        mundo: Mundo,
        reloj: Reloj,
        rng_juego: random.Random,
        semilla: int,
        rng_reproduccion: random.Random,
    ) -> bool:
```

Después, busca este bloque (justo después de restaurar `rng_juego`):

```python
            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_juego_state'")
            fila_rng = cur.fetchone()
            if fila_rng:
                rng_juego.setstate(pickle.loads(fila_rng[0]))

            # Limpiar gestor en memoria
```

Sustitúyelo por:

```python
            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_juego_state'")
            fila_rng = cur.fetchone()
            if fila_rng:
                rng_juego.setstate(pickle.loads(fila_rng[0]))

            cur.execute("SELECT valor FROM configuracion_ejecucion WHERE clave = 'rng_reproduccion_state'")
            fila_rng_reproduccion = cur.fetchone()
            if fila_rng_reproduccion:
                rng_reproduccion.setstate(pickle.loads(fila_rng_reproduccion[0]))

            # Limpiar gestor en memoria
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_rng_reproduccion.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Actualizar las 3 llamadas a `guardar_snapshot`/`cargar_snapshot` en `main.py`**

En `main.py`, busca esta línea:

```python
        partida_restaurada = persistencia.cargar_snapshot(gestor, mundo, reloj, rng_juego, semilla)
```

Sustitúyela por:

```python
        partida_restaurada = persistencia.cargar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)
```

Después, busca este bloque (autoguardado periódico dentro del bucle principal):

```python
            if guardar_cada_ticks > 0 and reloj.tick_actual % guardar_cada_ticks == 0:
                persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla)

    except KeyboardInterrupt:
        pass
```

Sustitúyelo por:

```python
            if guardar_cada_ticks > 0 and reloj.tick_actual % guardar_cada_ticks == 0:
                persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)

    except KeyboardInterrupt:
        pass
```

Después, busca este bloque (guardado final incondicional, dentro del `finally`):

```python
        # Guardado final incondicional: cubre tanto la interrupción manual
        # (Ctrl+C) como el fin de una tanda BOSQUE_AUTO_TICKS -- sin este
        # guardado, un autoguardado periódico que aún no llegó a su
        # cadencia dejaría la BD desactualizada respecto al último estado
        # real simulado.
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla)
```

Sustitúyelo por:

```python
        # Guardado final incondicional: cubre tanto la interrupción manual
        # (Ctrl+C) como el fin de una tanda BOSQUE_AUTO_TICKS -- sin este
        # guardado, un autoguardado periódico que aún no llegó a su
        # cadencia dejaría la BD desactualizada respecto al último estado
        # real simulado.
        persistencia.guardar_snapshot(gestor, mundo, reloj, rng_juego, semilla, rng_reproduccion)
```

- [ ] **Step 7: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `27 passed` (24 existentes + 3 nuevos).

- [ ] **Step 8: Verificación de humo del motor real**

Run: `cd /home/diego/proyecto-simulacion && BOSQUE_AUTO_TICKS=50 PYTHONPATH=. python3 main.py`
Expected: termina sin ninguna excepción (confirma que `main()` sigue arrancando y guardando con la firma nueva de `guardar_snapshot`/`cargar_snapshot`).

- [ ] **Step 9: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/persistencia.py main.py tests/test_rng_reproduccion.py
git commit -m "$(cat <<'EOF'
Persistir y restaurar el estado de rng_reproduccion

Tras darle a sistema_reproduccion.py su propio generador (commit
anterior), su estado también debe sobrevivir a guardar/cargar una
partida -- mismo mecanismo que ya usa rng_juego_state en
configuracion_ejecucion, bajo una clave nueva independiente.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01256zvSsQgtHuBBhjD2mz3A
EOF
)"
```
