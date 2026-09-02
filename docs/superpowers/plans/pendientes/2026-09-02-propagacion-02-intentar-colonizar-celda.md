# Propagación 2/5: Helper compartido `intentar_colonizar_celda` — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir `intentar_colonizar_celda` a `nucleo/flora.py` -- función pura que decide si una especie coloniza una celda destino ya existente (a diferencia de `idoneidad_colonizacion`, usada en generación, donde la `Celda` todavía no existe). Será reutilizada por los tres vectores de propagación (caída, viento, zoocoria) en los planes 3-5. Este plan NO conecta el helper a ningún sistema todavía -- función aislada, con sus propios tests.

**Architecture:** Función pura en `nucleo/flora.py`, junto a `idoneidad_colonizacion` (mismo fichero, misma familia de responsabilidad: ecología vegetal). Reutiliza `idoneidad_colonizacion` para la nota de idoneidad, sin duplicar esa fórmula. Import de `crear_planta` DIFERIDO (dentro de la función, no en el top del módulo) -- `nucleo/entidad.py` no importa `nucleo/flora.py`, así que no hay ciclo real, pero mantener el import a nivel de módulo en `nucleo/flora.py` sí crearía uno futuro si `nucleo/entidad.py` alguna vez necesitara algo de `nucleo/flora.py`; el import diferido es la práctica ya usada en el resto del proyecto para este caso.

**Tech Stack:** Python puro, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`, sección 2 ("Helper compartido de colonización — `nucleo/flora.py`").

## Global Constraints

- No modificar `sistemas/sistema_flora.py`, `sistemas/sistema_recursos.py`, ni ningún otro fichero fuera de `nucleo/flora.py` y su test -- la conexión a los sistemas reales llega en los planes 3-5.
- **Desviación deliberada de la spec, confirmada por Diego antes de escribir este plan**: la spec original NO incluye ninguna comprobación de agua dentro de este helper. Se añade aquí de todas formas -- `sistema_flora.py:_intentar_propagacion` ya tenía un guard explícito `not celda_dest.tiene_agua` con un comentario que documenta que fue un BUG REAL ya corregido una vez ("la propagación colonizaba celdas de río/lago/poza de su mismo bioma"). Si el helper nuevo sustituye esa validación sin heredar el guard, el bug se reintroduce. La ley física "la flora no crece sumergida" pertenece al helper compartido (afecta a los tres vectores por igual), no a cada llamador por separado -- confirmado además que este mismo problema existe hoy en la generación inicial (pieza 1, `colonizar_por_idoneidad`, sin guard de agua, 5-11% de las celdas colonizadas resultaron estar sobre agua en 3 semillas de verificación) -- **eso NO se toca en este plan** (círculo ya cerrado, fuera de alcance), pero el helper nuevo de aquí no debe repetir el mismo error en tiempo real.
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/flora.py` -- añade `intentar_colonizar_celda`, junto a `idoneidad_colonizacion`.
- `tests/test_flora_intentar_colonizar.py` -- nuevo, arnés directo sobre la función con un `GestorEntidades` real.

---

### Task 1: `intentar_colonizar_celda`

**Files:**
- Modify: `nucleo/flora.py`
- Test: `tests/test_flora_intentar_colonizar.py`

**Interfaces:**
- Consumes: `idoneidad_colonizacion(especie_cfg, celda, capacidad_retencion) -> float` (ya existe en `nucleo/flora.py`); `nucleo.entidad.crear_planta(gestor, especie, pos_x, pos_y, etapa=1.0, zona_idx=0) -> int` (ya existe, import diferido); `nucleo.entidad.GestorEntidades` (ya existe).
- Produces: `intentar_colonizar_celda(gestor, celda_dest, capacidad_retencion, especie, especie_cfg, umbral_minimo, nx, ny, zona_idx) -> bool` -- usado por los planes 3 (caída), 4 (viento) y 5 (zoocoria).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_intentar_colonizar.py`:

```python
"""Tests de intentar_colonizar_celda -- helper compartido de colonización
en tiempo real (2026-09-02, pieza 2/5 de "tipos de propagación" -- ver
docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).

A diferencia de idoneidad_colonizacion (usada en generación, donde la
Celda todavía no existe), aquí la Celda destino ya existe de verdad --
este helper decide si colonizarla y, si procede, crea la entidad Planta
y dejar la celda coherente (tiene_recurso/tipo_recurso/recursos).
"""
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.flora import intentar_colonizar_celda
from componentes.planta import Planta
from componentes.posicion import Posicion

ESPECIE_CFG = {
    "biomas": ["bosque"],
    "preferencia_lluvia": [0.5, 1.0],
    "preferencia_temperatura": [0.3, 0.7],
    "preferencia_fertilidad": [0.4, 0.9],
    "recursos": [
        {"nombre": "manzanas", "categoria": "alimento", "capacidad_maxima": 5.0},
        {"nombre": "madera", "categoria": "material", "capacidad_maxima": 6.0},
    ],
}

UMBRAL = 0.2


def _celda_idonea(**overrides):
    base = dict(
        tipo_terreno=TipoTerreno.BOSQUE,
        lluvia=0.7,
        temperatura=0.5,
        fertilidad=0.6,
        humedad_subsuelo=0.0,
        tiene_recurso=False,
        tiene_agua=False,
    )
    base.update(overrides)
    return Celda(**base)


def test_ley_celda_ya_ocupada_no_se_toca():
    gestor = GestorEntidades()
    celda = _celda_idonea(tiene_recurso=True, tipo_recurso="manzano")
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tipo_recurso == "manzano"
    assert gestor.entidades_con(Planta) == set()


def test_ley_celda_sumergida_nunca_se_coloniza_aunque_la_idoneidad_sea_alta():
    """Ver Global Constraints -- ley física común a los tres vectores,
    corrige un bug ya documentado que la spec original no heredaba."""
    gestor = GestorEntidades()
    celda = _celda_idonea(tiene_agua=True)
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_idoneidad_insuficiente_no_coloniza():
    gestor = GestorEntidades()
    celda = _celda_idonea(lluvia=0.0, temperatura=0.0, fertilidad=0.0)
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert resultado is False
    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_exito_crea_planta_y_deja_la_celda_coherente():
    gestor = GestorEntidades()
    celda = _celda_idonea()
    resultado = intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=1,
    )
    assert resultado is True
    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "manzano"
    assert celda.recursos == {"manzanas": 0.0, "madera": 0.0}

    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    planta_id = next(iter(plantas))
    planta = gestor.obtener_componente(planta_id, Planta)
    pos = gestor.obtener_componente(planta_id, Posicion)
    assert planta.especie == "manzano"
    assert planta.etapa == 0.1
    assert pos.x == 3 and pos.y == 4 and pos.zona_idx == 1


def test_ley_exito_no_pisa_recurso_ya_inicializado_en_la_celda():
    """Si la celda ya trae algo de recurso a granel (poco realista pero
    posible tras el arreglo del plan 5, si una zoocoria falla dos veces
    en la misma celda), la colonización no debe resetearlo a 0.0."""
    gestor = GestorEntidades()
    celda = _celda_idonea()
    celda.recursos["manzanas"] = 2.5
    intentar_colonizar_celda(
        gestor, celda, capacidad_retencion=0.8, especie="manzano",
        especie_cfg=ESPECIE_CFG, umbral_minimo=UMBRAL, nx=3, ny=4, zona_idx=0,
    )
    assert celda.recursos["manzanas"] == 2.5
    assert celda.recursos["madera"] == 0.0
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_intentar_colonizar.py -v`
Expected: FAIL -- `ImportError: cannot import name 'intentar_colonizar_celda' from 'nucleo.flora'`.

- [ ] **Step 3: Implementar `intentar_colonizar_celda`**

En `nucleo/flora.py`, añade esta función justo después de `idoneidad_colonizacion` (antes de `colonizar_por_idoneidad`):

```python
def intentar_colonizar_celda(
    gestor: "GestorEntidades",
    celda_dest: Celda,
    capacidad_retencion: float,
    especie: str,
    especie_cfg: dict[str, Any],
    umbral_minimo: float,
    nx: int,
    ny: int,
    zona_idx: int,
) -> bool:
    """Intenta colonizar una celda DESTINO YA EXISTENTE con una especie --
    distinto de idoneidad_colonizacion (generación inicial, donde la Celda
    todavía no existe y hay que construir una parcial). Círculo de
    "tipos de propagación de flora" (2026-09-02, ver docs/superpowers/
    specs/2026-09-01-propagacion-flora-design.md): sustituye la
    validación tosca "¿bioma compatible + sin agua?" que usaba
    _intentar_propagacion, compartida ahora por los tres vectores
    (caída, viento, zoocoria).

    Ley física común a los tres vectores, no solo caída: una celda ya
    ocupada (tiene_recurso) o sumergida (tiene_agua) nunca se coloniza,
    con independencia de cuánta idoneidad tenga -- el guard de agua
    corrige un bug ya documentado en sistema_flora.py (una versión previa
    sin él dejaba que la propagación colonizara río/lago/poza), no está
    en la redacción original de la spec pero es la misma ley física que
    ya regía antes de esta pieza. Devuelve False sin tocar nada en
    cualquiera de los dos casos, y también si la idoneidad no alcanza
    umbral_minimo.

    Import de crear_planta diferido (no a nivel de módulo): nucleo/
    entidad.py no importa nucleo/flora.py hoy, así que no hay ciclo real,
    pero mantener el import aquí evita crear uno si eso cambia."""
    if celda_dest.tiene_recurso or celda_dest.tiene_agua:
        return False

    idoneidad = idoneidad_colonizacion(especie_cfg, celda_dest, capacidad_retencion)
    if idoneidad < umbral_minimo:
        return False

    from nucleo.entidad import crear_planta

    crear_planta(gestor, especie, nx, ny, etapa=0.1, zona_idx=zona_idx)
    celda_dest.tiene_recurso = True
    celda_dest.tipo_recurso = especie
    for r_cfg in especie_cfg.get("recursos", []):
        nombre_rec = r_cfg.get("nombre")
        if nombre_rec and nombre_rec not in celda_dest.recursos:
            celda_dest.recursos[nombre_rec] = 0.0

    return True
```

Añade también `from nucleo.entidad import GestorEntidades` al bloque `if TYPE_CHECKING:` si el fichero ya usa ese patrón para anotaciones diferidas; si `nucleo/flora.py` no tiene ningún bloque `TYPE_CHECKING` todavía, usa la anotación como string literal tal cual aparece arriba (`"GestorEntidades"`) sin añadir ningún import nuevo a nivel de módulo -- ya es válido en Python con `from __future__ import annotations` (primera línea del fichero, ya presente).

- [ ] **Step 4: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_intentar_colonizar.py -v`
Expected: 5 tests PASS.

- [ ] **Step 5: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 5 nuevos.

- [ ] **Step 6: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/flora.py tests/test_flora_intentar_colonizar.py
git commit -m "$(cat <<'EOF'
feat: helper intentar_colonizar_celda (propagación 2/5)

Función pura compartida por los tres vectores de propagación (caída,
viento, zoocoria) -- sustituye la validación tosca de bioma+agua que
usaba _intentar_propagacion. Incluye guard de agua no presente en la
redacción original de la spec, corrigiendo un bug ya documentado en
sistema_flora.py. Sin conectar a ningún sistema todavía, pieza 2 de 5
(docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
