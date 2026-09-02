# Propagación 3/5: Caída — integración con el helper + dispatch por tipo — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conectar `nucleo.flora.intentar_colonizar_celda` (plan 2/5) a `sistemas/sistema_flora.py:SistemaFlora._intentar_propagacion` (vector "caída"), y añadir el dispatch por `tipo_propagacion` que sustituye la llamada incondicional a `_intentar_propagacion` para las 5 especies. Pieza 3 de 5 de "tipos de propagación".

**Architecture:** `_intentar_propagacion` conserva su algoritmo de selección de celda vecina (sin cambios) pero delega la validación de destino en el helper compartido. Un método nuevo, `_propagar_planta`, hace de único punto de dispatch por `tipo_propagacion` -- este plan solo implementa la rama `caida`; las ramas `viento` y `zoocoria` quedan como no-op documentado (los planes 4 y 5 las completan).

**Tech Stack:** Python puro, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`, secciones 3 ("Caída") y 5 ("Dispatch por tipo_propagacion").

## Global Constraints

- Depende de los planes 1/5 (`config/flora.yaml` con `tipo_propagacion`) y 2/5 (`nucleo/flora.py:intentar_colonizar_celda`) -- ambos deben estar ya mergeados en `master` antes de ejecutar este plan.
- **Regresión temporal deliberada, documentada aquí para que no se confunda con un bug**: tras este plan, las especies con `tipo_propagacion` distinto de `caida` (`hierba_silvestre`, `manzano`, `liquen`, `musgo`) dejan de propagarse en el ciclo diario hasta que los planes 4 (viento) y 5 (zoocoria) añadan sus ramas al dispatch -- es un estado intermedio esperado dentro del mismo círculo de trabajo, no una pérdida de funcionalidad permanente. Solo `cactus` (única especie `caida`) sigue propagándose exactamente igual que antes de este plan.
- No modificar `sistemas/sistema_recursos.py` ni `componentes/` en este plan -- eso llega en el plan 5 (zoocoria).
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `sistemas/sistema_flora.py` -- import de `intentar_colonizar_celda`; `_intentar_propagacion` delega la validación de destino en el helper; método nuevo `_propagar_planta` como dispatch; `_ejecutar_zona` llama a `_propagar_planta` en vez de `_intentar_propagacion` directamente.
- `tests/test_flora_propagacion_caida.py` -- nuevo.

---

### Task 1: Integración de caída + dispatch

**Files:**
- Modify: `sistemas/sistema_flora.py`
- Test: `tests/test_flora_propagacion_caida.py`

**Interfaces:**
- Consumes: `nucleo.flora.intentar_colonizar_celda(gestor, celda_dest, capacidad_retencion, especie, especie_cfg, umbral_minimo, nx, ny, zona_idx) -> bool` (plan 2/5); `especie_cfg["tipo_propagacion"]` (plan 1/5).
- Produces: `SistemaFlora._propagar_planta(gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg, posiciones_planta, zona_idx) -> None` -- punto único de dispatch, usado por los planes 4 y 5 para añadir sus propias ramas.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_propagacion_caida.py`:

```python
"""Tests de la integración de caída con intentar_colonizar_celda y del
dispatch por tipo_propagacion (2026-09-02, pieza 3/5 de "tipos de
propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).
"""
import random

from componentes.planta import Planta
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_flora import SistemaFlora

CONFIG = {
    "flora": {
        "umbral_minimo_idoneidad_colonizacion": 0.2,
        "especies": {
            "cactus": {
                "biomas": ["desierto"],
                "tipo_propagacion": "caida",
                "preferencia_lluvia": [0.0, 0.3],
                "preferencia_temperatura": [0.5, 1.0],
                "preferencia_fertilidad": [0.0, 0.3],
                "recursos": [
                    {"nombre": "fruto_de_cactus", "categoria": "alimento", "capacidad_maxima": 4.0},
                ],
            },
            "hierba_silvestre": {
                "biomas": ["pradera", "bosque"],
                "tipo_propagacion": "viento",
                "alcance_viento_celdas": [2, 6],
                "preferencia_lluvia": [0.0, 1.0],
                "preferencia_temperatura": [0.0, 1.0],
                "preferencia_fertilidad": [0.0, 1.0],
                "recursos": [],
            },
        },
    },
    "materiales": {},
}


def _zona_desierto(ancho=3, alto=3, **overrides_celda):
    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            base = dict(
                tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.1, temperatura=0.7,
                fertilidad=0.1, humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
            )
            base.update(overrides_celda)
            grid[x][y] = Celda(**base)
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid)


def _sistema():
    s = SistemaFlora(CONFIG, random.Random(1))
    return s


def test_ley_caida_coloniza_celda_vecina_idonea_via_helper():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._intentar_propagacion(
        gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0,
    )

    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    celdas_con_recurso = [
        (x, y) for x, y, c in zona.celdas() if c.tiene_recurso
    ]
    assert len(celdas_con_recurso) == 1
    assert celdas_con_recurso[0] != (1, 1)  # coloniza un vecino, no la propia celda


def test_ley_caida_no_coloniza_celda_sumergida():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto(tiene_agua=True)
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._intentar_propagacion(
        gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0,
    )

    assert gestor.entidades_con(Planta) == set()


def test_ley_dispatch_caida_llama_a_intentar_propagacion():
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()
    cfg_cactus = CONFIG["flora"]["especies"]["cactus"]

    sistema._propagar_planta(gestor, zona, 1, 1, "cactus", cfg_cactus, set(), zona_idx=0)

    assert len(gestor.entidades_con(Planta)) == 1


def test_ley_dispatch_viento_todavia_no_hace_nada_este_plan():
    """Regresión deliberada y temporal -- ver Global Constraints. El
    plan 4 sustituye este test por uno que SÍ espera colonización."""
    sistema = _sistema()
    gestor = GestorEntidades()
    zona = _zona_desierto()  # bioma no coincide con hierba_silvestre a propósito -- no debería importar, viento aún no hace nada
    cfg_hierba = CONFIG["flora"]["especies"]["hierba_silvestre"]

    sistema._propagar_planta(gestor, zona, 1, 1, "hierba_silvestre", cfg_hierba, set(), zona_idx=0)

    assert gestor.entidades_con(Planta) == set()
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_propagacion_caida.py -v`
Expected: FAIL -- `_propagar_planta` no existe todavía, y `_intentar_propagacion` sigue validando bioma+agua inline en vez de vía el helper (el primer test puede pasar por casualidad si el resultado observable coincide; los otros no).

- [ ] **Step 3: Import del helper**

En `sistemas/sistema_flora.py`, cambia la línea de import existente:

```python
from nucleo.flora import factor_humedad_subsuelo, factor_produccion
```

por:

```python
from nucleo.flora import factor_humedad_subsuelo, factor_produccion, intentar_colonizar_celda
```

- [ ] **Step 4: Reescribir `_intentar_propagacion` para delegar en el helper**

Sustituye el cuerpo completo del método `_intentar_propagacion` (desde `def _intentar_propagacion` hasta el final del método, justo antes de la siguiente definición o del final de la clase) por:

```python
    def _intentar_propagacion(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
        posiciones_planta: set[tuple[int, int]],
        zona_idx: int = 0,
    ) -> None:
        """Vector "caída" -- coloniza una celda adyacente compatible.
        Antes tenía su propia validación inline ("bioma compatible + sin
        agua"); ahora delega en nucleo.flora.intentar_colonizar_celda
        (2026-09-02, pieza 3/5 de "tipos de propagación" -- ver
        docs/superpowers/specs/2026-09-01-propagacion-flora-design.md),
        compartido con viento (plan 4) y zoocoria (plan 5). El filtro de
        bioma se mantiene aquí como preselección barata antes de calcular
        idoneidad -- sin él, cualquier celda vecina de bioma incompatible
        pasaría igualmente por el cálculo completo de idoneidad.

        posiciones_planta (2026-08-23, ver comentario en ejecutar()): set
        de posiciones ocupadas por Planta, mantenido por el llamador y
        actualizado aquí mismo tras cada colonización.
        """
        vecinos = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        self.rng.shuffle(vecinos)

        biomas_compatibles = [
            TipoTerreno(b.lower())
            for b in especie_cfg.get("biomas", [])
            if b.lower() in TipoTerreno._value2member_map_
        ]

        umbral_minimo = float(self.cfg_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2))

        for dx, dy in vecinos:
            nx, ny = origen_x + dx, origen_y + dy
            if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
                continue
            if (nx, ny) in posiciones_planta:
                continue

            celda_dest = zona.obtener_celda(nx, ny)
            if celda_dest.tipo_terreno not in biomas_compatibles:
                continue

            capacidad_retencion = float(
                self.catalogo_materiales.get(celda_dest.tipo_sustrato, {}).get(
                    "capacidad_retencion", 0.0
                )
            )
            if intentar_colonizar_celda(
                gestor, celda_dest, capacidad_retencion, especie_nombre,
                especie_cfg, umbral_minimo, nx, ny, zona_idx,
            ):
                posiciones_planta.add((nx, ny))
                break

    def _propagar_planta(
        self,
        gestor: GestorEntidades,
        zona: Any,
        origen_x: int,
        origen_y: int,
        especie_nombre: str,
        especie_cfg: dict[str, Any],
        posiciones_planta: set[tuple[int, int]],
        zona_idx: int,
    ) -> None:
        """Dispatch por tipo_propagacion -- CÍRCULO de "tipos de
        propagación de flora" (2026-09-02, pieza 3/5, ver docs/
        superpowers/specs/2026-09-01-propagacion-flora-design.md).
        Sustituye la llamada incondicional a _intentar_propagacion que
        regía por igual para las 5 especies. Único punto de dispatch --
        los planes 4 (viento) y 5 (zoocoria) añaden sus propias ramas
        aquí, sin tocar el resto de este método.

        viento y zoocoria no hacen nada todavía en este plan (3/5) -- ver
        Global Constraints del plan: regresión temporal esperada,
        corregida por los planes 4 y 5 del mismo círculo."""
        tipo_prop = especie_cfg.get("tipo_propagacion", "caida")
        if tipo_prop == "caida":
            self._intentar_propagacion(
                gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg,
                posiciones_planta, zona_idx,
            )
        elif tipo_prop == "viento":
            pass  # plan 4/5: _propagar_viento
        elif tipo_prop == "zoocoria":
            pass  # plan 5/5: no se dispara desde aquí, ver spec sección 5
```

- [ ] **Step 5: Cambiar el llamador en `_ejecutar_zona`**

En `_ejecutar_zona`, sustituye:

```python
            if planta.etapa >= 1.0:
                prob_prop = float(cfg_esp.get("prob_propagacion_por_dia", 0.02))
                if self.rng.random() < prob_prop:
                    self._intentar_propagacion(
                        gestor, zona, pos.x, pos.y, planta.especie, cfg_esp,
                        posiciones_planta, zona_idx,
                    )
```

por:

```python
            if planta.etapa >= 1.0:
                prob_prop = float(cfg_esp.get("prob_propagacion_por_dia", 0.02))
                if self.rng.random() < prob_prop:
                    self._propagar_planta(
                        gestor, zona, pos.x, pos.y, planta.especie, cfg_esp,
                        posiciones_planta, zona_idx,
                    )
```

- [ ] **Step 6: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_propagacion_caida.py -v`
Expected: 4 tests PASS.

- [ ] **Step 7: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 4 nuevos.

- [ ] **Step 8: Smoke test del motor real**

Run: `cd /home/diego/proyecto-simulacion && BOSQUE_AUTO_TICKS=500 timeout 90 python3 main.py`
Expected: código de salida 0, sin excepciones. `cactus` sigue propagándose con normalidad; el resto de especies simplemente no se propagan durante esta corrida (esperado, ver Global Constraints).

- [ ] **Step 9: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add sistemas/sistema_flora.py tests/test_flora_propagacion_caida.py
git commit -m "$(cat <<'EOF'
feat: caída vía intentar_colonizar_celda + dispatch por tipo (propagación 3/5)

_intentar_propagacion delega la validación de destino en el helper
compartido; nuevo dispatch _propagar_planta por tipo_propagacion,
solo con la rama "caida" implementada -- viento y zoocoria llegan en
los planes 4 y 5 del mismo círculo (docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
