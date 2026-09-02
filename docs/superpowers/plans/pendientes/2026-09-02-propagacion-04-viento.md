# Propagación 4/5: Viento — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir el vector "viento" -- las especies `hierba_silvestre`, `liquen` y `musgo` propagan una única semilla a distancia en la dirección del viento dominante ya sorteado por el mundo (`viento_dx`/`viento_dy`, hoy variables locales que se pierden al terminar `generar_zona_bioma`). Pieza 4 de 5 de "tipos de propagación".

**Architecture:** `ZonaBioma` gana dos atributos nuevos (`viento_dx`, `viento_dy`) para no perder el sorteo ya hecho en generación. `SistemaFlora` gana `_propagar_viento`, con el mismo patrón que `_intentar_propagacion` (una única celda candidata, un intento por planta por día) pero sorteando distancia y usando dirección fija en vez de vecino aleatorio. La rama `viento` del dispatch (`_propagar_planta`, plan 3/5) pasa de no-op a real.

**Tech Stack:** Python puro, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`, sección 4 ("Viento — nuevo método `_propagar_viento`") y sección 5 (rama `viento` del dispatch).

## Global Constraints

- Depende de los planes 1/5, 2/5 y 3/5 -- deben estar ya mergeados en `master` (en particular, `SistemaFlora._propagar_planta` ya debe existir, del plan 3).
- **Simplificación deliberada frente a la firma literal de la spec**: la spec sugiere pasar `viento_dx`/`viento_dy`/`alcance_min`/`alcance_max` como argumentos explícitos de `_propagar_viento`. Este plan lee `viento_dx`/`viento_dy` directamente de `zona` (ya se le pasa `zona` como argumento, y `ZonaBioma` los lleva ahora como atributos propios -- Task 1 de este plan) en vez de duplicarlos como parámetros aparte; `alcance_min`/`alcance_max` se leen de `especie_cfg["alcance_viento_celdas"]` dentro del propio método, igual que hace `_intentar_propagacion` con `especie_cfg["biomas"]`. Mismo comportamiento, menos argumentos redundantes.
- No modificar `sistemas/sistema_recursos.py` ni `componentes/` en este plan -- eso llega en el plan 5 (zoocoria).
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/zona_bioma.py` -- `ZonaBioma.__init__` gana `viento_dx: int = 0, viento_dy: int = 0`; `generar_zona_bioma` los pasa al construir el `ZonaBioma` final.
- `sistemas/sistema_flora.py` -- nuevo método `_propagar_viento`; la rama `viento` de `_propagar_planta` deja de ser no-op.
- `tests/test_zona_bioma_viento.py` -- nuevo, roundtrip del atributo.
- `tests/test_flora_propagacion_viento.py` -- nuevo.

---

### Task 1: `ZonaBioma.viento_dx`/`viento_dy`

**Files:**
- Modify: `nucleo/zona_bioma.py`
- Test: `tests/test_zona_bioma_viento.py`

**Interfaces:**
- Produces: `ZonaBioma(ancho, alto, grid, clima_actual=..., viento_dx=int, viento_dy=int)` -- `viento_dx`/`viento_dy` accesibles como `zona.viento_dx`/`zona.viento_dy`, uno de los cuatro rumbos cardinales `(1,0)/(-1,0)/(0,1)/(0,-1)` cuando la zona nace de `generar_zona_bioma` (default `0, 0` para cualquier otro llamador que no los pase, p.ej. `generar_zona_cueva`, que no tiene viento propio).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_zona_bioma_viento.py`:

```python
"""Tests de ZonaBioma.viento_dx/viento_dy (2026-09-02, pieza 4/5 de
"tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Antes de esto, viento_dx/viento_dy eran variables locales de
generar_zona_bioma -- se perdían al terminar de generar el mundo. Este
test confirma que ahora sobreviven como atributos de la zona.
"""
from pathlib import Path

from main import cargar_configuracion
from nucleo.zona_bioma import ZonaBioma, generar_zona_bioma
import random


def test_ley_zonabioma_acepta_viento_por_defecto_cero():
    zona = ZonaBioma(ancho=2, alto=2, grid=[[None, None], [None, None]])
    assert zona.viento_dx == 0
    assert zona.viento_dy == 0


def test_ley_zonabioma_acepta_viento_explicito():
    zona = ZonaBioma(ancho=2, alto=2, grid=[[None, None], [None, None]], viento_dx=1, viento_dy=0)
    assert zona.viento_dx == 1
    assert zona.viento_dy == 0


def test_ley_generar_zona_bioma_conserva_el_viento_sorteado():
    config = cargar_configuracion(Path("config"))
    rng = random.Random(7)
    zona = generar_zona_bioma(
        rng, config["generacion_mapa"], config["bioma"], config["flora"],
        config["agua"], config["materiales"], config["sustrato_por_bioma"],
        config["umbrales_sustrato_fertil"], config["generacion_vetas"], 10, 10,
    )
    rumbos_validos = {(1, 0), (-1, 0), (0, 1), (0, -1)}
    assert (zona.viento_dx, zona.viento_dy) in rumbos_validos
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_zona_bioma_viento.py -v`
Expected: FAIL -- `ZonaBioma.__init__()` no acepta `viento_dx`/`viento_dy`, y la zona real no expone esos atributos.

- [ ] **Step 3: `ZonaBioma.__init__` gana `viento_dx`/`viento_dy`**

En `nucleo/zona_bioma.py`, en `class ZonaBioma`, cambia la firma de `__init__`:

```python
    def __init__(self, ancho: int, alto: int, grid: list, clima_actual: Clima = Clima.DESPEJADO):
        self.ancho = ancho
        self.alto = alto
        self.grid = grid  # grid[x][y] -> Celda
        self.clima_actual = clima_actual
```

por:

```python
    def __init__(
        self,
        ancho: int,
        alto: int,
        grid: list,
        clima_actual: Clima = Clima.DESPEJADO,
        viento_dx: int = 0,
        viento_dy: int = 0,
    ):
        self.ancho = ancho
        self.alto = alto
        self.grid = grid  # grid[x][y] -> Celda
        self.clima_actual = clima_actual
        self.viento_dx = viento_dx
        self.viento_dy = viento_dy
        """Viento dominante de la zona -- uno de los cuatro rumbos
        cardinales sorteados en generación (nucleo/orografia.py:
        sortear_viento_dominante), 0,0 por defecto para cualquier zona
        sin viento propio (p.ej. nucleo/cueva.py:generar_zona_cueva, que
        no genera ninguno -- las cuevas no tienen clima propio). Antes
        de este círculo (2026-09-02, ver docs/superpowers/specs/
        2026-09-01-propagacion-flora-design.md) el sorteo de generar_
        zona_bioma se perdía al terminar la generación -- se conserva
        aquí para que el vector de propagación "viento" pueda usar la
        MISMA dirección con la que ya se calculó la lluvia orográfica de
        esta zona, en vez de sortear una dirección nueva sin relación
        con el clima ya generado."""
```

- [ ] **Step 4: `generar_zona_bioma` pasa el viento ya sorteado**

En `nucleo/zona_bioma.py`, al final de `generar_zona_bioma`, cambia:

```python
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid)
```

por:

```python
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid, viento_dx=viento_dx, viento_dy=viento_dy)
```

(`viento_dx`/`viento_dy` ya existen como variables locales, sorteadas más arriba en la misma función vía `sortear_viento_dominante(rng)` -- no hay que sortear nada de nuevo.)

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_zona_bioma_viento.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Commit parcial**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/zona_bioma.py tests/test_zona_bioma_viento.py
git commit -m "$(cat <<'EOF'
feat: ZonaBioma conserva el viento dominante sorteado (propagación 4/5, parte 1)

viento_dx/viento_dy pasan de variables locales de generar_zona_bioma
(se perdían al terminar la generación) a atributos de ZonaBioma --
necesario para que el vector de propagación "viento" use la misma
dirección con la que ya se calculó la lluvia orográfica de esa zona.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```

---

### Task 2: `_propagar_viento` + dispatch real

**Files:**
- Modify: `sistemas/sistema_flora.py`
- Test: `tests/test_flora_propagacion_viento.py`

**Interfaces:**
- Consumes: `zona.viento_dx`/`zona.viento_dy` (Task 1); `nucleo.flora.intentar_colonizar_celda` (plan 2/5); `SistemaFlora._propagar_planta` (plan 3/5, la rama `viento` ya existe como no-op, se completa aquí).
- Produces: `SistemaFlora._propagar_viento(gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg, posiciones_planta, zona_idx) -> None`.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_propagacion_viento.py`:

```python
"""Tests del vector de propagación "viento" (2026-09-02, pieza 4/5 de
"tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).
"""
import random

from componentes.planta import Planta
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from nucleo.zona_bioma import ZonaBioma
from sistemas.sistema_flora import SistemaFlora

CFG_HIERBA = {
    "biomas": ["pradera"],
    "tipo_propagacion": "viento",
    "alcance_viento_celdas": [2, 2],  # rango fijo -- distancia determinista para el test
    "preferencia_lluvia": [0.0, 1.0],
    "preferencia_temperatura": [0.0, 1.0],
    "preferencia_fertilidad": [0.0, 1.0],
    "recursos": [],
}

CONFIG = {
    "flora": {"umbral_minimo_idoneidad_colonizacion": 0.2, "especies": {"hierba_silvestre": CFG_HIERBA}},
    "materiales": {},
}


def _zona_pradera(ancho=8, alto=8, viento_dx=1, viento_dy=0, **overrides_celda):
    grid = [[None] * alto for _ in range(ancho)]
    for x in range(ancho):
        for y in range(alto):
            base = dict(
                tipo_terreno=TipoTerreno.PRADERA, lluvia=0.5, temperatura=0.5,
                fertilidad=0.5, humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
            )
            base.update(overrides_celda)
            grid[x][y] = Celda(**base)
    return ZonaBioma(ancho=ancho, alto=alto, grid=grid, viento_dx=viento_dx, viento_dy=viento_dy)


def test_ley_viento_coloniza_en_la_direccion_del_viento_a_la_distancia_sorteada():
    sistema = SistemaFlora(CONFIG, random.Random(3))
    gestor = GestorEntidades()
    zona = _zona_pradera(viento_dx=1, viento_dy=0)

    sistema._propagar_viento(gestor, zona, 2, 2, "hierba_silvestre", CFG_HIERBA, set(), zona_idx=0)

    celdas_con_recurso = [(x, y) for x, y, c in zona.celdas() if c.tiene_recurso]
    assert celdas_con_recurso == [(4, 2)]  # origen (2,2) + viento (1,0) * distancia 2


def test_ley_viento_fuera_del_grid_no_hace_nada():
    sistema = SistemaFlora(CONFIG, random.Random(3))
    gestor = GestorEntidades()
    zona = _zona_pradera(ancho=3, alto=3, viento_dx=1, viento_dy=0)  # origen (2,2) + (2,0) = (4,2), fuera de 3x3

    sistema._propagar_viento(gestor, zona, 2, 2, "hierba_silvestre", CFG_HIERBA, set(), zona_idx=0)

    assert gestor.entidades_con(Planta) == set()


def test_ley_dispatch_viento_ya_coloniza_de_verdad():
    sistema = SistemaFlora(CONFIG, random.Random(3))
    gestor = GestorEntidades()
    zona = _zona_pradera(viento_dx=0, viento_dy=1)

    sistema._propagar_planta(gestor, zona, 2, 2, "hierba_silvestre", CFG_HIERBA, set(), zona_idx=0)

    assert len(gestor.entidades_con(Planta)) == 1
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_propagacion_viento.py -v`
Expected: FAIL -- `_propagar_viento` no existe todavía.

- [ ] **Step 3: Implementar `_propagar_viento`**

En `sistemas/sistema_flora.py`, añade este método justo después de `_intentar_propagacion`:

```python
    def _propagar_viento(
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
        """Vector "viento" -- sortea una distancia dentro de
        alcance_viento_celdas y prueba UNA única celda candidata en la
        dirección del viento dominante de la zona (zona.viento_dx/
        viento_dy, ver Task 1 de este plan). Sin reintento si la
        candidata falla -- mismo criterio de "un intento por planta por
        día" que ya rige _intentar_propagacion. 2026-09-02, pieza 4/5 de
        "tipos de propagación" (ver docs/superpowers/specs/
        2026-09-01-propagacion-flora-design.md)."""
        alcance_min, alcance_max = especie_cfg.get("alcance_viento_celdas", [1, 1])
        distancia = self.rng.randint(int(alcance_min), int(alcance_max))

        nx = origen_x + zona.viento_dx * distancia
        ny = origen_y + zona.viento_dy * distancia
        if not (0 <= nx < zona.ancho and 0 <= ny < zona.alto):
            return
        if (nx, ny) in posiciones_planta:
            return

        biomas_compatibles = [
            TipoTerreno(b.lower())
            for b in especie_cfg.get("biomas", [])
            if b.lower() in TipoTerreno._value2member_map_
        ]
        celda_dest = zona.obtener_celda(nx, ny)
        if celda_dest.tipo_terreno not in biomas_compatibles:
            return

        umbral_minimo = float(self.cfg_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2))
        capacidad_retencion = float(
            self.catalogo_materiales.get(celda_dest.tipo_sustrato, {}).get("capacidad_retencion", 0.0)
        )
        if intentar_colonizar_celda(
            gestor, celda_dest, capacidad_retencion, especie_nombre,
            especie_cfg, umbral_minimo, nx, ny, zona_idx,
        ):
            posiciones_planta.add((nx, ny))
```

- [ ] **Step 4: Completar la rama `viento` del dispatch**

En `_propagar_planta` (creado en el plan 3/5), sustituye:

```python
        elif tipo_prop == "viento":
            pass  # plan 4/5: _propagar_viento
```

por:

```python
        elif tipo_prop == "viento":
            self._propagar_viento(
                gestor, zona, origen_x, origen_y, especie_nombre, especie_cfg,
                posiciones_planta, zona_idx,
            )
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_propagacion_viento.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los nuevos de este plan.

- [ ] **Step 7: Smoke test del motor real**

Run: `cd /home/diego/proyecto-simulacion && BOSQUE_AUTO_TICKS=500 timeout 90 python3 main.py`
Expected: código de salida 0, sin excepciones. `hierba_silvestre`, `liquen`, `musgo` y `cactus` se propagan; `manzano` (zoocoria) sigue sin propagarse hasta el plan 5.

- [ ] **Step 8: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add sistemas/sistema_flora.py tests/test_flora_propagacion_viento.py
git commit -m "$(cat <<'EOF'
feat: vector de propagación viento (propagación 4/5, parte 2)

_propagar_viento sortea distancia dentro de alcance_viento_celdas y
prueba una única celda en la dirección del viento dominante de la
zona. Completa la rama "viento" del dispatch (plan 3/5) -- hierba_
silvestre, liquen y musgo vuelven a propagarse. Pieza 4 de 5 (docs/
superpowers/specs/2026-09-01-propagacion-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
