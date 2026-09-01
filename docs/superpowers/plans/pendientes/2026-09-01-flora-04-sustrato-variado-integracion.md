# Flora 4/5: Sustrato variado + fertilidad inicial en generación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Conectar `elegir_sustrato_celda` (plan 2) a la generación real del mundo (`nucleo/zona_bioma.py`) y hacer que `Celda.fertilidad` nazca del `fertilidad_base` de su sustrato en vez de 0.0 fijo. `sustrato_por_bioma` cambia de `{bioma: material}` a `{bioma: [candidatos]}`. La colocación de FLORA (qué especie coloniza qué celda) sigue exactamente igual que hoy en este plan — eso es el plan 5. Pieza 4 de 5.

**Architecture:** Este plan cambia la forma de `sustrato_por_bioma` en `config/materiales.yaml` Y su único punto de lectura real (`nucleo/zona_bioma.py`) en el MISMO plan/commit, para que el repositorio nunca quede en un estado donde el dato tenga una forma que el código no sepa leer. Requiere pre-requisitos: **este plan depende de que los planes 1 y 2 ya estén mergeados** (usa `fertilidad_base` del plan 1 y `elegir_sustrato_celda` del plan 2).

**Tech Stack:** Python 3, YAML, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`, secciones 2 ("sustrato_por_bioma") y 3 (elección de sustrato, ya implementada en el plan 2).

## Global Constraints

- **Prerrequisito: los planes 1 (`flora-01-catalogo-sustrato-fertilidad`) y 2 (`flora-02-elegir-sustrato-celda`) deben estar ya mergeados en la rama base antes de ejecutar este plan** — usa `fertilidad_base` y `elegir_sustrato_celda`, que no existen sin ellos.
- No tocar la colocación de flora (`especie_por_celda`, el bucle que hoy usa `_generar_manchas` para especies) — sigue exactamente igual que hoy. Eso es el plan 5.
- No tocar `_generar_manchas` en absoluto — sigue siendo usada por `nucleo/materiales.py:generar_vetas_minerales` para vetas de mineral, sin relación con este plan.
- Los 4 umbrales de `umbrales_sustrato_fertil` son PROVISIONALES.
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `config/materiales.yaml` — `sustrato_por_bioma` pasa de escalar a lista por bioma; nueva sección `umbrales_sustrato_fertil`.
- `nucleo/zona_bioma.py` — `generar_zona_bioma` gana un parámetro `config_umbrales_sustrato_fertil`; el bloque que calculaba `tipo_sustrato_por_celda` con un lookup fijo pasa a llamar a `elegir_sustrato_celda` por celda y a calcular `fertilidad_por_celda`; el constructor de `Celda` recibe `fertilidad=`.
- `nucleo/territorio.py` — el único punto de llamada a `generar_zona_bioma` pasa el nuevo argumento.
- `tests/test_zona_bioma_fertilidad.py` — nuevo, integración con la configuración real del proyecto.

---

### Task 1: sustrato variado + fertilidad inicial en `generar_zona_bioma`

**Files:**
- Modify: `config/materiales.yaml`
- Modify: `nucleo/zona_bioma.py`
- Modify: `nucleo/territorio.py`
- Test: `tests/test_zona_bioma_fertilidad.py`

**Interfaces:**
- Consumes: `nucleo.materiales.elegir_sustrato_celda` (plan 2), `fertilidad_base` en `config["materiales"]` (plan 1).
- Produces: `generar_zona_bioma(rng, config_generacion, config_bioma, config_flora, config_agua, config_materiales, config_sustrato_por_bioma, config_umbrales_sustrato_fertil, config_generacion_vetas, ancho, alto, probabilidad_piedra_suelta=0.0) -> ZonaBioma` — mismo nombre, un parámetro nuevo insertado en la posición 8 (justo después de `config_sustrato_por_bioma`, antes de `config_generacion_vetas`). Toda `Celda` de la zona generada lleva `fertilidad` real, no 0.0.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_zona_bioma_fertilidad.py`:

```python
"""Tests de integración: sustrato variado + fertilidad de partida en la
generación de una zona de bioma real (2026-09-01, pieza 4/5 de la
distribución causal de flora -- ver docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md).

Usa la configuración REAL del proyecto (config/*.yaml) en vez de una
config de prueba recortada -- esta pieza depende de que
sustrato_por_bioma/umbrales_sustrato_fertil/fertilidad_base tengan
exactamente la forma que el motor real usa, no una forma simplificada
inventada para el test.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.celda import TipoTerreno
from nucleo.zona_bioma import generar_zona_bioma

RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"
ANCHO = ALTO = 24


def _generar(semilla: int):
    config = cargar_configuracion(RUTA_CONFIG)
    rng = random.Random(semilla)
    zona = generar_zona_bioma(
        rng,
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"], ANCHO, ALTO,
    )
    return config, zona


def test_ley_fertilidad_de_celda_nace_del_fertilidad_base_de_su_sustrato():
    config, zona = _generar(semilla=1)
    catalogo = config["materiales"]
    for x, y, celda in zona.celdas():
        esperado = float(catalogo[celda.tipo_sustrato]["fertilidad_base"])
        assert celda.fertilidad == esperado


def test_ley_tundra_siempre_tiene_el_unico_sustrato_candidato():
    config, zona = _generar(semilla=2)
    for x, y, celda in zona.celdas():
        if celda.tipo_terreno is TipoTerreno.TUNDRA:
            assert celda.tipo_sustrato == "tierra"


def test_ley_montana_solo_usa_sustratos_de_su_lista_de_candidatos():
    config, zona = _generar(semilla=3)
    candidatos_montana = set(config["sustrato_por_bioma"]["montana"])
    for x, y, celda in zona.celdas():
        if celda.tipo_terreno is TipoTerreno.MONTANA:
            assert celda.tipo_sustrato in candidatos_montana


def test_regresion_vetas_de_mineral_siguen_solo_sobre_piedra():
    """Regresión: el círculo de minería exige que las vetas de mineral
    sigan restringidas a celdas de sustrato piedra tras el cambio de
    sustrato_por_bioma a lista -- ninguna veta debe aparecer sobre grava
    ni sobre ningún otro sustrato."""
    config, zona = _generar(semilla=4)
    for x, y, celda in zona.celdas():
        if celda.deposito_mineral:
            assert celda.tipo_sustrato == "piedra"


def test_regresion_humedad_subsuelo_saturada_donde_hay_agua_permanente():
    """Regresión: una celda con agua permanente sigue naciendo con
    humedad_subsuelo al tope de la capacidad_retencion de su propio
    sustrato -- mismo comportamiento de siempre."""
    config, zona = _generar(semilla=5)
    catalogo = config["materiales"]
    for x, y, celda in zona.celdas():
        if celda.tiene_agua:
            capacidad = float(catalogo[celda.tipo_sustrato]["capacidad_retencion"])
            assert celda.humedad_subsuelo == capacidad
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_zona_bioma_fertilidad.py -v`
Expected: FAIL — bien con `TypeError` (número de argumentos posicionales no coincide con la firma actual de `generar_zona_bioma`), bien con `KeyError: 'umbrales_sustrato_fertil'` (la clave no existe todavía en `config/materiales.yaml`).

- [ ] **Step 3: `sustrato_por_bioma` a lista + `umbrales_sustrato_fertil` en `config/materiales.yaml`**

Busca este bloque exacto en `config/materiales.yaml`:

```yaml
sustrato_por_bioma:
  montana: piedra
  bosque: arcilla
  pradera: arcilla
  desierto: arena
  tundra: tierra
```

Sustitúyelo por:

```yaml
sustrato_por_bioma:
  montana: [piedra, grava]
  bosque: [arcilla, tierra_negra]
  pradera: [marga, tierra_negra]
  desierto: [arena, grava]
  tundra: [tierra]

# umbrales_sustrato_fertil (2026-09-01, ver docs/superpowers/specs/
# 2026-09-01-distribucion-causal-flora-design.md): qué sustrato de la
# lista de sustrato_por_bioma le toca a una celda concreta ya no es un
# sorteo -- se deriva de una señal causal ya calculada en generación
# (elevación para biomas pedregosos, lluvia para biomas vegetados, ver
# nucleo/materiales.py:elegir_sustrato_celda). Un único float por
# bioma, en la misma escala [0,1] que campo_elevacion/campo_lluvia.
# Tundra no aparece -- un único candidato no consulta ningún umbral.
# PROVISIONAL, sin calibrar contra el motor en marcha.
umbrales_sustrato_fertil:
  montana: 0.6
  desierto: 0.5
  bosque: 0.55
  pradera: 0.45
```

- [ ] **Step 4: Añadir el import y el parámetro nuevo en `nucleo/zona_bioma.py`**

Busca esta línea de import:

```python
from nucleo.materiales import generar_vetas_minerales
```

Sustitúyela por:

```python
from nucleo.materiales import elegir_sustrato_celda, generar_vetas_minerales
```

Busca la firma de la función:

```python
def generar_zona_bioma(
    rng: random.Random,
    config_generacion: dict,
    config_bioma: dict,
    config_flora: dict,
    config_agua: dict,
    config_materiales: dict,
    config_sustrato_por_bioma: dict,
    config_generacion_vetas: dict,
    ancho: int,
    alto: int,
    probabilidad_piedra_suelta: float = 0.0,
) -> ZonaBioma:
```

Sustitúyela por (añade `config_umbrales_sustrato_fertil: dict,` justo después de `config_sustrato_por_bioma: dict,`):

```python
def generar_zona_bioma(
    rng: random.Random,
    config_generacion: dict,
    config_bioma: dict,
    config_flora: dict,
    config_agua: dict,
    config_materiales: dict,
    config_sustrato_por_bioma: dict,
    config_umbrales_sustrato_fertil: dict,
    config_generacion_vetas: dict,
    ancho: int,
    alto: int,
    probabilidad_piedra_suelta: float = 0.0,
) -> ZonaBioma:
```

- [ ] **Step 5: Calcular sustrato y fertilidad por celda con la nueva ley**

Busca este bloque exacto en `nucleo/zona_bioma.py` (dentro de `generar_zona_bioma`, justo antes de la generación de vetas de mineral):

```python
    sustrato_por_bioma = config_sustrato_por_bioma
    catalogo_materiales = config_materiales
    tipo_sustrato_por_celda = {
        (x, y): sustrato_por_bioma.get(biomas[(x, y)].value, "")
        for x in range(ancho) for y in range(alto)
    }
```

Sustitúyelo por:

```python
    sustrato_por_bioma = config_sustrato_por_bioma
    catalogo_materiales = config_materiales
    umbrales_sustrato_fertil = config_umbrales_sustrato_fertil
    # Sustrato variado por celda (2026-09-01, ver docs/superpowers/specs/
    # 2026-09-01-distribucion-causal-flora-design.md): antes de esto,
    # cada bioma tenía un único material fijo (sustrato_por_bioma.get(...)
    # directo) -- ahora cada bioma trae una LISTA de candidatos y
    # elegir_sustrato_celda decide cuál le toca a cada celda según
    # elevación/lluvia ya calculadas, causal en vez de fijo. fertilidad_
    # por_celda nace del fertilidad_base del sustrato elegido, no de 0.0.
    tipo_sustrato_por_celda = {}
    fertilidad_por_celda = {}
    for x in range(ancho):
        for y in range(alto):
            bioma_celda = biomas[(x, y)]
            candidatos = sustrato_por_bioma.get(bioma_celda.value, [])
            umbral = umbrales_sustrato_fertil.get(bioma_celda.value, 0.5)
            sustrato = elegir_sustrato_celda(
                candidatos, bioma_celda, campo_elevacion[x][y], campo_lluvia[x][y], umbral,
            )
            tipo_sustrato_por_celda[(x, y)] = sustrato
            fertilidad_por_celda[(x, y)] = float(
                catalogo_materiales.get(sustrato, {}).get("fertilidad_base", 0.0)
            )
```

- [ ] **Step 6: Pasar `fertilidad` al construir cada `Celda`**

Busca este bloque exacto (el final de la construcción de `Celda`, dentro del bucle principal de `grid`):

```python
            grid[x][y] = Celda(
                tipo_terreno=tipo, elevacion=campo_elevacion[x][y],
                lluvia=campo_lluvia[x][y], temperatura=campo_temperatura[x][y],
                recursos=recursos_iniciales, tiene_recurso=tiene_recurso,
                tipo_recurso=especie_key, tiene_agua=tiene_agua, tipo_agua=tipo_agua,
                profundidad_agua=profundidad_agua, tipo_sustrato=tipo_sustrato,
                humedad_subsuelo=humedad_subsuelo, deposito_mineral=deposito_mineral,
                masa_mineral_restante=masa_mineral_restante,
            )
```

Sustitúyelo por (añade `fertilidad=fertilidad_por_celda[(x, y)],` como último argumento):

```python
            grid[x][y] = Celda(
                tipo_terreno=tipo, elevacion=campo_elevacion[x][y],
                lluvia=campo_lluvia[x][y], temperatura=campo_temperatura[x][y],
                recursos=recursos_iniciales, tiene_recurso=tiene_recurso,
                tipo_recurso=especie_key, tiene_agua=tiene_agua, tipo_agua=tipo_agua,
                profundidad_agua=profundidad_agua, tipo_sustrato=tipo_sustrato,
                humedad_subsuelo=humedad_subsuelo, deposito_mineral=deposito_mineral,
                masa_mineral_restante=masa_mineral_restante,
                fertilidad=fertilidad_por_celda[(x, y)],
            )
```

- [ ] **Step 7: Pasar el nuevo argumento en `nucleo/territorio.py`**

Busca este bloque exacto en `nucleo/territorio.py`:

```python
        zona = generar_zona_bioma(
            rng,
            config["generacion_mapa"],
            config["bioma"],
            config["flora"],
            config["agua"],
            config["materiales"],
            config["sustrato_por_bioma"],
            config["generacion_vetas"],
            ancho,
            alto,
            probabilidad_piedra_suelta=float(
                config.get("fuego", {}).get("probabilidad_piedra_suelta_por_celda", 0.0)
            ),
        )
```

Sustitúyelo por (añade `config["umbrales_sustrato_fertil"],` justo después de `config["sustrato_por_bioma"],`):

```python
        zona = generar_zona_bioma(
            rng,
            config["generacion_mapa"],
            config["bioma"],
            config["flora"],
            config["agua"],
            config["materiales"],
            config["sustrato_por_bioma"],
            config["umbrales_sustrato_fertil"],
            config["generacion_vetas"],
            ancho,
            alto,
            probabilidad_piedra_suelta=float(
                config.get("fuego", {}).get("probabilidad_piedra_suelta_por_celda", 0.0)
            ),
        )
```

- [ ] **Step 8: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_zona_bioma_fertilidad.py -v`
Expected: 5 tests PASS.

- [ ] **Step 9: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde (incluidos los de `test_agua.py`/`test_bioma.py`/`test_orografia.py`, que no llaman a `generar_zona_bioma` directamente pero sí ejercitan piezas que este plan reordena indirectamente), más los 5 nuevos.

- [ ] **Step 10: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add config/materiales.yaml nucleo/zona_bioma.py nucleo/territorio.py tests/test_zona_bioma_fertilidad.py
git commit -m "$(cat <<'EOF'
feat: sustrato variado + fertilidad inicial en generación (flora 4/5)

sustrato_por_bioma pasa de un material fijo por bioma a una lista de
candidatos, elegidos por celda vía elegir_sustrato_celda (elevación/
lluvia ya causales). Celda.fertilidad nace del fertilidad_base real de
su sustrato en vez de 0.0 fijo. La colocación de flora sigue exactamente
igual que antes -- pieza 4 de 5 de la distribución causal de flora
(docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
