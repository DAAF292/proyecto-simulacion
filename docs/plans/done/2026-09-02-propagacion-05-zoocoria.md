# Propagación 5/5: Zoocoria — componente Semillas + hooks + persistencia — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cierra el círculo de "tipos de propagación de flora" -- `manzano` (única especie `zoocoria`) se dispersa cuando un individuo come su fruto y, más tarde, en otro sitio, hace `Accion.ALIVIARSE`. Componente `Semillas` nuevo, dos hooks en `sistemas/sistema_recursos.py`, persistencia. Pieza 5 de 5.

**Architecture:** `Semillas.especie_transportada: str` (componente de dato puro, mismo molde que `Agarre`). Se llena en `_resolver_comer` (COMER fruto de especie zoocora), se consume en `_resolver_aliviarse` (ALIVIARSE con semilla ya recogida). Desacoplado del ciclo diario de `SistemaFlora` -- lo dispara el comportamiento del animal, no la planta; la rama `zoocoria` del dispatch (`_propagar_planta`, plan 3/5) se queda en no-op para siempre, a propósito.

**Tech Stack:** Python puro, pytest, SQLite (vía `nucleo/persistencia.py`).

**Spec:** `docs/superpowers/specs/2026-09-01-propagacion-flora-design.md`, secciones 6 ("Zoocoria — componente Semillas + hooks") y 7 ("Persistencia").

## Global Constraints

- Depende de los planes 1/5, 2/5, 3/5 y 4/5 -- deben estar ya mergeados en `master`.
- `VERSION_ESQUEMA` sube de `"0.30-fase0"` a `"0.31-fase0"` -- DROP-and-recreate del esquema al cargar una base de datos antigua (criterio ya establecido en todo el proyecto, sin migración de datos).
- `Semillas` se añade a las CUATRO especies por igual en `crear_criatura` Y `nacer_criatura` (dos fábricas ECS separadas, ver el hallazgo ya documentado sobre `Agarre` en `CLAUDE.md`: un descuido aquí deja a toda cría nacida en partida sin el componente).
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `componentes/semillas.py` -- nuevo, componente `Semillas`.
- `nucleo/entidad.py` -- `Semillas()` añadida en `crear_criatura` y `nacer_criatura`.
- `sistemas/sistema_recursos.py` -- caché de config nueva; hook en `_resolver_comer`; `_resolver_aliviarse` extendida (gana `gestor`, `entidad_id`, `pos_x`, `pos_y`, `zona_idx`); llamador actualizado.
- `nucleo/persistencia.py` -- columna `semillas` en `componentes_estado`; `VERSION_ESQUEMA` a `"0.31-fase0"`.
- `tests/test_semillas_zoocoria.py` -- nuevo, arnés de los dos hooks.
- `tests/test_persistencia_semillas.py` -- nuevo, roundtrip.

---

### Task 1: Componente `Semillas` + fábricas ECS

**Files:**
- Create: `componentes/semillas.py`
- Modify: `nucleo/entidad.py`
- Test: `tests/test_semillas_fabricas.py`

**Interfaces:**
- Produces: `componentes.semillas.Semillas(especie_transportada: str = "")`; toda entidad creada por `crear_criatura`/`nacer_criatura` lleva el componente, vacío.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_semillas_fabricas.py`:

```python
"""Tests de que Semillas se añade en ambas fábricas ECS (2026-09-02,
pieza 5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Mismo hallazgo ya documentado para Agarre en CLAUDE.md: crear_criatura
(población fundadora) y nacer_criatura (nacimientos en partida) son dos
fábricas ECS separadas -- un descuido en cualquiera de las dos deja a
esas entidades sin el componente, un AttributeError la primera vez que
algo intente leerlo.
"""
import random
from pathlib import Path

from componentes.identidad import Especie
from componentes.semillas import Semillas
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura, nacer_criatura

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_ley_crear_criatura_anade_semillas_vacio():
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng = random.Random(1)
    eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas is not None
    assert semillas.especie_transportada == ""


def test_ley_nacer_criatura_anade_semillas_vacio():
    config = cargar_configuracion(RUTA_CONFIG)
    gestor = GestorEntidades()
    rng = random.Random(1)
    madre_id = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    padre_id = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
    cria_id = nacer_criatura(gestor, madre_id, padre_id, config, rng, tick_actual=0)
    semillas = gestor.obtener_componente(cria_id, Semillas)
    assert semillas is not None
    assert semillas.especie_transportada == ""
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_semillas_fabricas.py -v`
Expected: FAIL -- `ModuleNotFoundError: No module named 'componentes.semillas'`. Si `nacer_criatura` exige argumentos distintos a los usados arriba, revisa su firma real en `nucleo/entidad.py` (línea ~406) y ajusta la llamada del test -- no cambies el fichero de producción para acomodar el test.

- [ ] **Step 3: Crear `componentes/semillas.py`**

```python
"""Componente Semillas: dato puro, sin logica.

Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación de flora" --
ver docs/superpowers/specs/2026-09-01-propagacion-flora-design.md): un
individuo que come el fruto de una especie zoocora (config/flora.yaml,
tipo_propagacion: zoocoria) lleva la semilla consigo hasta su próximo
ALIVIARSE, donde puede depositarla en otra celda -- desacoplado del
ciclo diario de SistemaFlora, lo dispara el comportamiento del animal
(COMER, luego ALIVIARSE en otro momento y lugar), no la planta.

especie_transportada: str, no list -- a diferencia de Agarre.objetos
(que admite varios objetos a la vez según puntos_agarre por especie),
aquí solo se modela una semilla transportada cada vez, sin distinción
de qué especie animal la lleva: cualquier individuo con Accion.COMER
puede recogerla. "" si no lleva ninguna.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Semillas:
    especie_transportada: str = ""
```

- [ ] **Step 4: Añadir `Semillas()` a `crear_criatura` y `nacer_criatura`**

En `nucleo/entidad.py`, añade el import junto al resto de imports de `componentes.*`:

```python
from componentes.semillas import Semillas
```

Localiza la línea `gestor.anadir_componente(entidad_id, Agarre())` dentro de `crear_criatura` (hay un comentario justo antes explicando el criterio de Agarre) y añade justo después:

```python
    # Semillas (2026-09-02, ver componentes/semillas.py) -- mismo
    # criterio que Agarre: componente universal, vacío al nacer, cuánto
    # se usa de verdad depende de con qué especies de flora zoocora
    # coincida el individuo en su vida.
    gestor.anadir_componente(entidad_id, Semillas())
```

Repite exactamente el mismo bloque justo después de la línea equivalente `gestor.anadir_componente(entidad_id, Agarre())` dentro de `nacer_criatura` (hay una segunda ocurrencia, con su propio comentario sobre Agarre, más abajo en el fichero).

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_semillas_fabricas.py -v`
Expected: 2 tests PASS.

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 2 nuevos.

- [ ] **Step 7: Commit parcial**

```bash
cd /home/diego/proyecto-simulacion
git add componentes/semillas.py nucleo/entidad.py tests/test_semillas_fabricas.py
git commit -m "$(cat <<'EOF'
feat: componente Semillas en ambas fábricas ECS (propagación 5/5, parte 1)

Semillas.especie_transportada, mismo molde que Agarre -- añadido a
crear_criatura y nacer_criatura por separado (dos fábricas ECS, mismo
hallazgo ya documentado para Agarre). Cimiento de zoocoria, pieza 5
de 5 (docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```

---

### Task 2: Hooks en `_resolver_comer` / `_resolver_aliviarse`

**Files:**
- Modify: `sistemas/sistema_recursos.py`
- Test: `tests/test_semillas_zoocoria.py`

**Interfaces:**
- Consumes: `componentes.semillas.Semillas` (Task 1); `nucleo.flora.intentar_colonizar_celda` (plan 2/5); `config["flora"]["probabilidad_recogida_semilla_zoocoria"]`/`["probabilidad_plantar_semilla_en_aliviarse"]` (plan 1/5).
- Produces: `SistemaRecursos._resolver_aliviarse(gestor, entidad_id, nec, celda, pos_x, pos_y, zona_idx) -> None` -- firma AMPLIADA (antes solo `(self, nec, celda)`); todo llamador debe actualizarse.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_semillas_zoocoria.py`:

```python
"""Tests de los hooks de zoocoria en SistemaRecursos (2026-09-02, pieza
5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).
"""
import random

from componentes.identidad import Especie, Identidad
from componentes.necesidades import Necesidades
from componentes.planta import Planta
from componentes.semillas import Semillas
from nucleo.celda import Celda, TipoTerreno
from nucleo.entidad import GestorEntidades
from sistemas.sistema_recursos import SistemaRecursos

CFG_MANZANO = {
    "biomas": ["bosque"],
    "tipo_propagacion": "zoocoria",
    "preferencia_lluvia": [0.0, 1.0],
    "preferencia_temperatura": [0.0, 1.0],
    "preferencia_fertilidad": [0.0, 1.0],
    "recursos": [
        {"nombre": "manzanas", "categoria": "alimento", "capacidad_maxima": 5.0,
         "valor_nutricional": 0.4, "valor_hidratacion": 0.15},
    ],
}

CONFIG = {
    "flora": {
        "umbral_minimo_idoneidad_colonizacion": 0.2,
        "probabilidad_recogida_semilla_zoocoria": 1.0,  # determinista para el test
        "probabilidad_plantar_semilla_en_aliviarse": 1.0,
        "especies": {"manzano": CFG_MANZANO},
    },
    "materiales": {},
    "rangos_raciales": {"gnomo": {"dieta": []}},
    "consumo": {},
    "abono": {"incremento_fertilidad_por_aliviarse": 0.2, "techo_fertilidad": 1.0},
    "necesidades": {"defecto": {"tasa_alivio_al_aliviarse": 0.5}},
}


def _celda_manzano(**overrides):
    base = dict(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.7, temperatura=0.5, fertilidad=0.6,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=True, tipo_recurso="manzano",
        recursos={"manzanas": 3.0},
    )
    base.update(overrides)
    return Celda(**base)


def _entidad_gnomo(gestor):
    eid = gestor.crear_entidad()
    gestor.anadir_componente(eid, Identidad(especie=Especie.GNOMO, nombre="Test", tick_nacimiento=0))
    gestor.anadir_componente(eid, Necesidades())
    gestor.anadir_componente(eid, Semillas())
    return eid


def test_ley_comer_fruto_zoocoro_recoge_semilla():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano()

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas.especie_transportada == "manzano"


def test_ley_comer_fruto_no_zoocoro_no_recoge_nada():
    """cactus (caida) no debe dejar semilla -- el hook solo dispara para
    tipo_propagacion == zoocoria."""
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano(tipo_recurso="cactus", recursos={"manzanas": 3.0})
    # celda.tipo_recurso="cactus" no está en CONFIG["flora"]["especies"],
    # así que especies_flora.get("cactus", {}) devuelve {} -- tipo_propagacion ausente.

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    semillas = gestor.obtener_componente(eid, Semillas)
    assert semillas.especie_transportada == ""


def test_ley_no_recoge_una_segunda_semilla_si_ya_lleva_una():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    identidad = gestor.obtener_componente(eid, Identidad)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = _celda_manzano()

    sistema._resolver_comer(gestor, eid, identidad, nec, None, None, celda, 0, 0, zona_idx=0)

    # sigue llevando la misma semilla, no se sobreescribe ni se pierde
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == "manzano"


def test_ley_aliviarse_con_semilla_coloniza_la_celda_actual_y_la_limpia():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.7, temperatura=0.5, fertilidad=0.6,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
    )

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=2)

    assert celda.tiene_recurso is True
    assert celda.tipo_recurso == "manzano"
    plantas = gestor.entidades_con(Planta)
    assert len(plantas) == 1
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == ""


def test_ley_aliviarse_sin_semilla_no_intenta_colonizar():
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    nec = gestor.obtener_componente(eid, Necesidades)
    celda = Celda(tipo_terreno=TipoTerreno.BOSQUE, tiene_recurso=False)

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=0)

    assert celda.tiene_recurso is False
    assert gestor.entidades_con(Planta) == set()


def test_ley_aliviarse_con_semilla_limpia_aunque_la_idoneidad_falle():
    """La semilla se deposita igual, prenda o no -- se limpia en
    cualquier caso (éxito o fallo de idoneidad)."""
    sistema = SistemaRecursos(CONFIG, random.Random(1))
    gestor = GestorEntidades()
    eid = _entidad_gnomo(gestor)
    gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"
    nec = gestor.obtener_componente(eid, Necesidades)
    # Idoneidad nula a propósito: fuera de todo rango de preferencia de manzano.
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.0, temperatura=0.0, fertilidad=0.0,
        humedad_subsuelo=0.0, tiene_agua=False, tiene_recurso=False,
    )

    sistema._resolver_aliviarse(gestor, eid, nec, celda, 5, 5, zona_idx=0)

    assert celda.tiene_recurso is False
    assert gestor.obtener_componente(eid, Semillas).especie_transportada == ""
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_semillas_zoocoria.py -v`
Expected: FAIL -- `_resolver_aliviarse` no acepta todavía `gestor`/`entidad_id`/`zona_idx`, y `_resolver_comer` no toca `Semillas`.

- [ ] **Step 3: Imports + caché de config**

En `sistemas/sistema_recursos.py`, añade a los imports existentes:

```python
from componentes.semillas import Semillas
from nucleo.flora import intentar_colonizar_celda
```

En `_cachear_configuracion`, sustituye el bloque:

```python
        # Mapa de valores nutricionales e hídricos por recurso vegetal
        self.nutricion_flora: dict[str, float] = {}
        self.hidratacion_flora: dict[str, float] = {}
        for esp_data in self.config.get("flora", {}).get("especies", {}).values():
            for rec in esp_data.get("recursos", []):
                nom = rec.get("nombre")
                if nom:
                    self.nutricion_flora[nom] = float(rec.get("valor_nutricional", 0.2))
                    self.hidratacion_flora[nom] = float(rec.get("valor_hidratacion", 0.05))
```

por:

```python
        # Mapa de valores nutricionales e hídricos por recurso vegetal
        self.especies_flora: dict[str, Any] = self.config.get("flora", {}).get("especies", {})
        self.nutricion_flora: dict[str, float] = {}
        self.hidratacion_flora: dict[str, float] = {}
        for esp_data in self.especies_flora.values():
            for rec in esp_data.get("recursos", []):
                nom = rec.get("nombre")
                if nom:
                    self.nutricion_flora[nom] = float(rec.get("valor_nutricional", 0.2))
                    self.hidratacion_flora[nom] = float(rec.get("valor_hidratacion", 0.05))

        # Zoocoria (2026-09-02, ver componentes/semillas.py y
        # docs/superpowers/specs/2026-09-01-propagacion-flora-design.md).
        self.umbral_minimo_idoneidad_colonizacion: float = float(
            self.config.get("flora", {}).get("umbral_minimo_idoneidad_colonizacion", 0.2)
        )
        self.probabilidad_recogida_semilla_zoocoria: float = float(
            self.config.get("flora", {}).get("probabilidad_recogida_semilla_zoocoria", 0.3)
        )
        self.probabilidad_plantar_semilla_en_aliviarse: float = float(
            self.config.get("flora", {}).get("probabilidad_plantar_semilla_en_aliviarse", 0.5)
        )
```

- [ ] **Step 4: Hook en `_resolver_comer`**

En `_resolver_comer`, dentro del bloque `if recursos_disponibles:` (Evaluación de Forrajeo Vegetal), justo después de la línea `self._registrar_recuerdo_si_procede(mem, cap_mental, "comida", pos_x, pos_y)` y antes del `else:` que le sigue, añade:

```python

            # Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación"
            # -- ver docs/superpowers/specs/
            # 2026-09-01-propagacion-flora-design.md): comer fruto de una
            # especie zoocora puede dejar una semilla "recogida" -- se
            # planta más tarde, en otro sitio, al ALIVIARSE (ver
            # _resolver_aliviarse). celda.tipo_recurso ya ES la especie
            # que produce este recurso (nucleo/celda.py), no hace falta
            # buscarla por nombre_rec.
            especie_cfg_comida = self.especies_flora.get(celda.tipo_recurso, {})
            if especie_cfg_comida.get("tipo_propagacion") == "zoocoria":
                semillas = gestor.obtener_componente(entidad_id, Semillas)
                if (
                    semillas is not None
                    and semillas.especie_transportada == ""
                    and self.rng.random() < self.probabilidad_recogida_semilla_zoocoria
                ):
                    semillas.especie_transportada = celda.tipo_recurso
```

- [ ] **Step 5: Ampliar `_resolver_aliviarse`**

Sustituye el método completo:

```python
    def _resolver_aliviarse(self, nec: Necesidades, celda: Celda) -> None:
        """Evacua residuos orgánicos corporales incrementando la fertilidad del suelo."""
        tasa_alivio = float(self.config.get("necesidades", {}).get("defecto", {}).get("tasa_alivio_al_aliviarse", 0.5))
        nec.aliviado = min(1.0, nec.aliviado + tasa_alivio)
        celda.fertilidad = min(self.techo_fertilidad, celda.fertilidad + self.incremento_fertilidad)
```

por:

```python
    def _resolver_aliviarse(
        self,
        gestor: GestorEntidades,
        entidad_id: int,
        nec: Necesidades,
        celda: Celda,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
    ) -> None:
        """Evacua residuos orgánicos corporales incrementando la fertilidad del suelo.

        Zoocoria (2026-09-02, pieza 5/5 de "tipos de propagación" -- ver
        docs/superpowers/specs/2026-09-01-propagacion-flora-design.md):
        si el individuo lleva una semilla recogida (Semillas.especie_
        transportada, ver _resolver_comer), este es también el evento
        que puede depositarla -- desacoplado del ciclo diario de
        SistemaFlora, lo dispara el comportamiento del animal (COMER,
        luego ALIVIARSE en otro momento y lugar), no la planta. La
        semilla se limpia SIEMPRE (éxito o fallo de idoneidad) -- se
        deposita igual, prenda o no.
        """
        tasa_alivio = float(self.config.get("necesidades", {}).get("defecto", {}).get("tasa_alivio_al_aliviarse", 0.5))
        nec.aliviado = min(1.0, nec.aliviado + tasa_alivio)
        celda.fertilidad = min(self.techo_fertilidad, celda.fertilidad + self.incremento_fertilidad)

        semillas = gestor.obtener_componente(entidad_id, Semillas)
        if semillas is not None and semillas.especie_transportada != "":
            especie = semillas.especie_transportada
            if self.rng.random() < self.probabilidad_plantar_semilla_en_aliviarse:
                especie_cfg = self.especies_flora.get(especie, {})
                capacidad_retencion = float(
                    self.catalogo_materiales.get(celda.tipo_sustrato, {}).get("capacidad_retencion", 0.0)
                )
                intentar_colonizar_celda(
                    gestor, celda, capacidad_retencion, especie, especie_cfg,
                    self.umbral_minimo_idoneidad_colonizacion, pos_x, pos_y, zona_idx,
                )
            semillas.especie_transportada = ""
```

- [ ] **Step 6: Actualizar el llamador en `ejecutar`**

En el método `ejecutar` de `SistemaRecursos`, cambia:

```python
            elif intencion.accion == Accion.ALIVIARSE:
                self._resolver_aliviarse(nec, celda)
```

por:

```python
            elif intencion.accion == Accion.ALIVIARSE:
                self._resolver_aliviarse(gestor, eid, nec, celda, pos.x, pos.y, pos.zona_idx)
```

- [ ] **Step 7: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_semillas_zoocoria.py -v`
Expected: 6 tests PASS.

- [ ] **Step 8: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 6 nuevos.

- [ ] **Step 9: Commit parcial**

```bash
cd /home/diego/proyecto-simulacion
git add sistemas/sistema_recursos.py tests/test_semillas_zoocoria.py
git commit -m "$(cat <<'EOF'
feat: hooks de zoocoria en _resolver_comer/_resolver_aliviarse (propagación 5/5, parte 2)

Comer fruto de una especie zoocora recoge una semilla; ALIVIARSE con
semilla ya recogida intenta plantarla en la celda actual, vía el
mismo intentar_colonizar_celda que ya usan caída y viento.
_resolver_aliviarse amplía su firma (gestor, entidad_id, zona_idx).
Pieza 5 de 5 (docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```

---

### Task 3: Persistencia de `Semillas.especie_transportada`

**Files:**
- Modify: `nucleo/persistencia.py`
- Test: `tests/test_persistencia_semillas.py`

**Interfaces:**
- Consumes: `componentes.semillas.Semillas` (Task 1).
- Produces: `Semillas.especie_transportada` sobrevive a un roundtrip completo de `guardar_snapshot`/`cargar_snapshot`.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_persistencia_semillas.py`:

```python
"""Test de roundtrip de Semillas.especie_transportada (2026-09-02,
pieza 5/5 de "tipos de propagación" -- ver docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md).

Mismo criterio que Agarre.objetos: perder esto al recargar sería una
regresión silenciosa, no un campo transitorio inofensivo -- ya tiene un
efecto real conectado (zoocoria).
"""
import random
import tempfile
from pathlib import Path

from componentes.identidad import Especie
from componentes.semillas import Semillas
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades, crear_criatura
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj

RUTA_CONFIG = Path(__file__).parent.parent / "config"


def test_ley_semillas_sobrevive_roundtrip_de_guardar_y_cargar():
    config = cargar_configuracion(RUTA_CONFIG)
    semilla = 3

    with tempfile.TemporaryDirectory() as directorio_tmp:
        ruta_db = Path(directorio_tmp) / "test_semillas.db"
        persistencia = Persistencia(ruta_db)
        mundo = Mundo(6, 6, config, random.Random(semilla))
        gestor = GestorEntidades()
        reloj = Reloj()
        rng = random.Random(semilla)

        eid = crear_criatura(gestor, Especie.GNOMO, 0, 0, config, rng)
        gestor.obtener_componente(eid, Semillas).especie_transportada = "manzano"

        eid_sin_semilla = crear_criatura(gestor, Especie.LOBO, 1, 1, config, rng)

        persistencia.guardar_snapshot(gestor, mundo, reloj, rng, semilla, random.Random(semilla))

        gestor_cargado = GestorEntidades()
        ok = persistencia.cargar_snapshot(
            gestor_cargado, mundo, reloj, random.Random(semilla), semilla, random.Random(semilla)
        )
        assert ok is True

        semillas_restauradas = gestor_cargado.obtener_componente(eid, Semillas)
        assert semillas_restauradas is not None
        assert semillas_restauradas.especie_transportada == "manzano"

        semillas_vacia_restaurada = gestor_cargado.obtener_componente(eid_sin_semilla, Semillas)
        assert semillas_vacia_restaurada is not None
        assert semillas_vacia_restaurada.especie_transportada == ""
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_persistencia_semillas.py -v`
Expected: FAIL -- `componentes_estado` no tiene columna `semillas` todavía.

- [ ] **Step 3: `VERSION_ESQUEMA` + columna nueva**

En `nucleo/persistencia.py`, cambia:

```python
VERSION_ESQUEMA = "0.30-fase0"
```

por:

```python
VERSION_ESQUEMA = "0.31-fase0"
```

En el `CREATE TABLE IF NOT EXISTS componentes_estado`, cambia la última línea de columnas:

```python
                    zona_idx INTEGER NOT NULL DEFAULT 0,
                    agarre TEXT
                )
```

por:

```python
                    zona_idx INTEGER NOT NULL DEFAULT 0,
                    agarre TEXT,
                    -- semillas (2026-09-02, ver componentes/semillas.py):
                    -- Semillas.especie_transportada, mismo criterio que
                    -- agarre -- perderla al recargar sería una regresión
                    -- silenciosa en un mecanismo con efecto real conectado.
                    semillas TEXT
                )
```

- [ ] **Step 4: Guardar -- añadir `semillas` a la fila y al INSERT**

En `guardar_snapshot`, dentro del bucle que construye `filas_criaturas`, localiza la línea:

```python
                agarre = gestor.obtener_componente(eid, Agarre)
```

y añade justo después:

```python
                semillas = gestor.obtener_componente(eid, Semillas)
```

Añade el import correspondiente junto al resto de imports de `componentes.*` al principio del fichero:

```python
from componentes.semillas import Semillas
```

Localiza, dentro de la tupla que se añade a `filas_criaturas`, la última línea:

```python
                            json.dumps(agarre.objetos) if agarre else None,
```

y añade justo después (como último elemento de la tupla, antes del paréntesis de cierre):

```python
                            semillas.especie_transportada if semillas else None,
```

En el `INSERT INTO componentes_estado VALUES (...)`, la última línea de placeholders tiene 9 signos `?`:

```python
                    ?, ?, ?, ?, ?, ?, ?, ?, ?
```

Cámbiala por 10:

```python
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
```

- [ ] **Step 5: Cargar -- leer `semillas` y desplazar los índices de `Identidad`**

`semillas` es la columna 50 de `componentes_estado` (después de `agarre`, que es la 49) -- en el `SELECT c.*, e.especie, e.nombre, e.tick_nacimiento, e.id_madre, e.id_padre`, esto desplaza en +1 los índices de `Identidad` (antes `fila[49]`..`fila[53]`, ahora `fila[50]`..`fila[54]`).

Localiza:

```python
                agarre_lista = json.loads(fila[48]) if fila[48] else []
                gestor.anadir_componente(eid, Agarre(objetos=agarre_lista))
```

y añade justo después:

```python
                semillas_valor = fila[49] if fila[49] else ""
                gestor.anadir_componente(eid, Semillas(especie_transportada=str(semillas_valor)))
```

Localiza el bloque de `Identidad`:

```python
                    Identidad(
                        especie=Especie(fila[49]),
                        nombre=fila[50],
                        tick_nacimiento=fila[51],
                        id_madre=fila[52],
                        id_padre=fila[53],
                    ),
```

y cambia los índices a:

```python
                    Identidad(
                        especie=Especie(fila[50]),
                        nombre=fila[51],
                        tick_nacimiento=fila[52],
                        id_madre=fila[53],
                        id_padre=fila[54],
                    ),
```

- [ ] **Step 6: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_persistencia_semillas.py -v`
Expected: 1 test PASS.

- [ ] **Step 7: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más el nuevo.

- [ ] **Step 8: Smoke test del motor real**

Run: `cd /home/diego/proyecto-simulacion && BOSQUE_AUTO_TICKS=800 timeout 150 python3 main.py`
Expected: código de salida 0, sin excepciones. Las 5 especies vuelven a propagarse (caída, viento y zoocoria, las tres piezas del círculo ya completas).

- [ ] **Step 9: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/persistencia.py tests/test_persistencia_semillas.py
git commit -m "$(cat <<'EOF'
feat: persistencia de Semillas.especie_transportada (propagación 5/5, parte 3)

Columna semillas en componentes_estado, VERSION_ESQUEMA 0.31-fase0
(DROP-and-recreate). Cierra la pieza 5 de 5 de "tipos de propagación
de flora" (docs/superpowers/specs/
2026-09-01-propagacion-flora-design.md) -- caída, viento y zoocoria
completos.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
