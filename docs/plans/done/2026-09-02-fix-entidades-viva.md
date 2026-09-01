# Fix: entidades.viva nunca se pone a False al morir — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir un bug real y aislado de persistencia: la columna `viva` de la tabla histórica `entidades` se escribe a `True` al nacer una entidad, pero ningún código la pone a `False` cuando la entidad muere — el snapshot en vivo (`componentes_estado`) sí sabe quién sigue vivo, pero el registro histórico permanente miente para siempre sobre cualquier entidad que ya ha muerto.

**Architecture:** Reutiliza el mecanismo ya existente, sin inventar nada nuevo: los cuatro puntos del motor donde una entidad muere (`sistema_ciclo_vital.py`, `sistema_depredacion.py`, `sistema_necesidades.py`, `sistema_desastres.py`) ya emiten un `Evento(tipo="Muerte", entidad_id=...)` justo antes de purgarla del ECS con `gestor.eliminar_entidad(...)`. `main.py` ya escucha eventos del bus cada tick para alimentar la persistencia (`if ev.tipo == "Nacimiento": persistencia.registrar_entidad_nueva(...)`) — el fix añade la rama simétrica para `"Muerte"`, más el método de `Persistencia` que le da soporte.

**Tech Stack:** Python 3, sqlite3 estándar (sin ORM), pytest con `tmp_path` para una base de datos real y descartable — mismo criterio que el resto de `tests/`.

**Spec:** Ninguna — fix mecánico de una sola causa, clasificado "Bounded" en la conversación de diseño con Diego (diseño de un párrafo en chat, sin ceremonia de spec arquitectónica).

## Global Constraints

- No tocar el esquema de la tabla `entidades` (ya tiene la columna `viva BOOLEAN NOT NULL` desde su creación) — solo falta el UPDATE que la mantenga sincronizada.
- No tocar ninguno de los cuatro puntos de emisión del evento `"Muerte"` — ya llevan `entidad_id` en el propio `Evento`, que es todo lo que hace falta.
- Sin arnés de motor real ni verificación estadística — es un fix determinista de una línea de causalidad, el test unitario de persistencia (base de datos real, sin mocks) es el criterio de aceptación completo.
- No modificar ninguna aserción de los 22 tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/persistencia.py` — nuevo método `Persistencia.marcar_entidad_muerta`.
- `main.py` — nueva rama en el bucle de procesamiento de eventos de `ejecutar_tick`/bucle principal.
- `tests/test_persistencia_entidades_viva.py` — nuevo, test de "ley física" (mismo estilo que el resto de `tests/`) verificando el ciclo completo nace-vivo → muere-no-vivo contra una base de datos SQLite real.

---

### Task 1: `Persistencia.marcar_entidad_muerta` + cableado en `main.py`

**Files:**
- Modify: `nucleo/persistencia.py`
- Modify: `main.py`
- Test: `tests/test_persistencia_entidades_viva.py`

**Interfaces:**
- Produces: `Persistencia.marcar_entidad_muerta(self, entidad_id: int) -> None` — método de instancia, ejecuta `UPDATE entidades SET viva = 0 WHERE id = ?` y comitea.
- Consumes: `Persistencia.__init__(self, ruta_db: Path)` (ya existe), `Persistencia.registrar_entidad_nueva(self, entidad_id: int, datos: dict) -> None` (ya existe, sin cambios — el test lo usa para sembrar la fila antes de marcarla muerta), `Persistencia._conectar(self) -> sqlite3.Connection` (ya existe, método privado reutilizado igual que el resto de métodos de la clase).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_persistencia_entidades_viva.py`:

```python
"""Test de la ley de persistencia histórica de entidades (2026-09-02,
fix aislado -- ver CLAUDE.md).

La tabla `entidades` es el registro histórico PERMANENTE de toda
entidad que ha existido en la partida (vivo o muerto), distinto del
snapshot en vivo `componentes_estado` (que sí se sobrescribe en cada
guardado y solo contiene quién sigue vivo ahora). La columna `viva` de
`entidades` debía reflejar el estado real -- este test verifica el
ciclo completo: nace viva, muere y deja de estarlo, sin que la fila se
borre ni se duplique.
"""
import sqlite3
from pathlib import Path

from nucleo.persistencia import Persistencia


def _leer_viva(ruta_db: Path, entidad_id: int) -> bool:
    con = sqlite3.connect(ruta_db)
    try:
        cur = con.cursor()
        cur.execute("SELECT viva FROM entidades WHERE id = ?", (entidad_id,))
        fila = cur.fetchone()
        assert fila is not None, f"no existe fila para entidad_id={entidad_id}"
        return bool(fila[0])
    finally:
        con.close()


def test_entidad_nace_viva_y_muere_no_viva(tmp_path):
    """Ley: registrar_entidad_nueva dege viva=True; marcar_entidad_muerta
    la pasa a viva=False sobre la MISMA fila, sin crear una fila nueva
    ni borrar la existente."""
    ruta_db = tmp_path / "test_entidades_viva.db"
    persistencia = Persistencia(ruta_db)

    persistencia.registrar_entidad_nueva(
        entidad_id=7,
        datos={"especie": "gnomo", "nombre": "Test", "tick_nacimiento": 0},
    )
    assert _leer_viva(ruta_db, 7) is True

    persistencia.marcar_entidad_muerta(7)
    assert _leer_viva(ruta_db, 7) is False


def test_marcar_muerta_no_afecta_a_otras_entidades(tmp_path):
    """Ley: marcar_entidad_muerta solo toca la fila de su propio
    entidad_id -- una entidad distinta que sigue viva no se ve afectada."""
    ruta_db = tmp_path / "test_entidades_viva_multi.db"
    persistencia = Persistencia(ruta_db)

    persistencia.registrar_entidad_nueva(
        entidad_id=1, datos={"especie": "gnomo", "tick_nacimiento": 0}
    )
    persistencia.registrar_entidad_nueva(
        entidad_id=2, datos={"especie": "lobo", "tick_nacimiento": 0}
    )

    persistencia.marcar_entidad_muerta(1)

    assert _leer_viva(ruta_db, 1) is False
    assert _leer_viva(ruta_db, 2) is True
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_persistencia_entidades_viva.py -v`
Expected: `AttributeError: 'Persistencia' object has no attribute 'marcar_entidad_muerta'` — el método no existe todavía.

- [ ] **Step 3: Implementar `Persistencia.marcar_entidad_muerta`**

En `nucleo/persistencia.py`, añade este método a la clase `Persistencia`, justo después de `registrar_entidad_nueva` (antes de `persistir_eventos`):

```python
    def marcar_entidad_muerta(self, entidad_id: int) -> None:
        """Actualiza el registro histórico de una entidad para reflejar
        que ha muerto (2026-09-02, fix aislado -- ver CLAUDE.md,
        'entidades.viva nunca se actualizaba'). Antes de este fix, toda
        entidad quedaba marcada viva=True para siempre en la tabla
        histórica una vez creada -- el snapshot en vivo
        (componentes_estado) sí reflejaba correctamente quién seguía
        vivo, pero el registro histórico permanente mentía. Se llama
        desde main.py al procesar cualquier Evento con tipo == "Muerte",
        el mismo patrón que ya usa registrar_entidad_nueva para
        "Nacimiento"."""
        with self._conectar() as con:
            cur = con.cursor()
            cur.execute(
                "UPDATE entidades SET viva = 0 WHERE id = ?",
                (entidad_id,),
            )
            con.commit()
```

- [ ] **Step 4: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_persistencia_entidades_viva.py -v`
Expected: 2 tests PASS.

- [ ] **Step 5: Cablear el evento "Muerte" en `main.py`**

En `main.py`, busca este bloque (dentro del bucle principal, sección "Procesamiento de eventos en presentación y persistencia"):

```python
            # Procesamiento de eventos en presentación y persistencia
            eventos_tick = bus_eventos.eventos_del_tick
            for ev in eventos_tick:
                if ev.tipo == "Nacimiento":
                    persistencia.registrar_entidad_nueva(ev.entidad_id, ev.datos)
            persistencia.persistir_eventos(eventos_tick)
```

Sustitúyelo por (añade la rama `elif` para `"Muerte"`, sin tocar nada más de este bloque):

```python
            # Procesamiento de eventos en presentación y persistencia
            eventos_tick = bus_eventos.eventos_del_tick
            for ev in eventos_tick:
                if ev.tipo == "Nacimiento":
                    persistencia.registrar_entidad_nueva(ev.entidad_id, ev.datos)
                elif ev.tipo == "Muerte":
                    persistencia.marcar_entidad_muerta(ev.entidad_id)
            persistencia.persistir_eventos(eventos_tick)
```

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `24 passed` (22 existentes + 2 nuevos).

- [ ] **Step 7: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/persistencia.py main.py tests/test_persistencia_entidades_viva.py
git commit -m "$(cat <<'EOF'
Fix: entidades.viva se actualiza a False al morir

nucleo/persistencia.py:registrar_entidad_nueva escribía viva=True al
nacer una entidad, pero ningún código la ponía a False al morir -- el
registro histórico permanente mentía para siempre sobre cualquier
entidad ya fallecida (el snapshot en vivo componentes_estado sí lo
reflejaba bien). Nuevo método marcar_entidad_muerta, cableado en
main.py desde el evento "Muerte" que los cuatro puntos de muerte del
motor ya emitían -- mismo patrón que ya usa "Nacimiento".

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01EWJmuU1xt1BX91Kg4Eb2Qp
EOF
)"
```

