# Test de la ley de madurez reproductiva (es_adulto) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `nucleo/ciclo_vital.py:es_adulto` decide si un individuo puede reproducirse (usada por `sistemas/sistema_reproduccion.py`) pero no tiene ningún test dedicado en `tests/` — CLAUDE.md señala que "nada de sistemas de comportamiento, reproducción... tiene test dedicado todavía" (esto ya no es del todo cierto tras el commit de `rng_reproduccion`, pero `es_adulto` en sí sigue sin cobertura directa). Es una ley pura y determinista (sin rng, sin estado, sin efectos secundarios) — candidata ideal para un test aislado. Este plan SOLO añade tests, no modifica ningún comportamiento existente.

**Architecture:** `es_adulto(edad_en_ticks, especie, rangos_raciales, fraccion_madurez) -> bool` ya existe y funciona correctamente (verificado manualmente contra el config real antes de escribir este plan) — la ley es: adulto cuando `edad_en_ticks >= fraccion_madurez * rangos_raciales[especie]["longevidad"][0] * TICKS_POR_ANIO`. Se documentan y verifican los umbrales exactos de dos especies reales (gnomo, lobo) usando los valores actuales de `config/poblacion.yaml` y la constante `TICKS_POR_ANIO` ya calculada en el propio módulo.

**Tech Stack:** Python 3, pytest, sin mocks — mismo criterio declarativo ("ley física") que `tests/test_bioma.py`.

**Spec:** Ninguna — pura adición de cobertura de test sobre código ya existente y correcto, sin ambigüedad de diseño.

## Global Constraints

- No modificar `nucleo/ciclo_vital.py` ni ningún otro fichero de código de producción — este plan es exclusivamente de tests.
- No modificar ninguna aserción de los 27 tests ya existentes en `tests/`.
- Los valores numéricos usados en las aserciones deben coincidir EXACTAMENTE con `config/poblacion.yaml` a fecha de este plan: `gnomo.longevidad = [45, 65]`, `gnomo.fraccion_madurez = 0.1`, `lobo.longevidad = [8, 14]`, `lobo.fraccion_madurez = 0.2`. `TICKS_POR_ANIO = 480` (24 ticks/día × 5 días/estación × 4 estaciones/año, ya definido en `nucleo/ciclo_vital.py`).

---

## File Structure

- `tests/test_ciclo_vital_es_adulto.py` — nuevo, tests de "ley física" verificando el umbral exacto de madurez para gnomo y lobo, y que la fracción de madurez se lee POR ESPECIE (no un valor global compartido).

---

### Task 1: Tests de `es_adulto` para gnomo y lobo

**Files:**
- Test: `tests/test_ciclo_vital_es_adulto.py`

**Interfaces:**
- Consumes: `nucleo.ciclo_vital.es_adulto(edad_en_ticks: int, especie: str, rangos_raciales: dict, fraccion_madurez: float) -> bool` (ya existe, sin cambios) y `nucleo.ciclo_vital.TICKS_POR_ANIO` (constante entera ya existente, sin cambios).

- [ ] **Step 1: Escribir los tests**

Crea `tests/test_ciclo_vital_es_adulto.py`:

```python
"""Test de la ley de madurez reproductiva (2026-09-02, ver CLAUDE.md).

nucleo/ciclo_vital.py:es_adulto decide si un individuo puede reproducirse
-- reutiliza el minimo racial de longevidad (rangos_raciales[especie]
["longevidad"][0]) como ancla, escalado por fraccion_madurez, la misma
fraccion que sistemas/sistema_reproduccion.py ya lee por especie desde
config/poblacion.yaml. Estos tests fijan el umbral exacto en ticks para
dos especies reales (gnomo, lobo) y confirman que la fraccion se aplica
POR ESPECIE, no como un valor global compartido."""
from nucleo.ciclo_vital import TICKS_POR_ANIO, es_adulto

RANGOS_RACIALES = {
    "gnomo": {"longevidad": [45, 65]},
    "lobo": {"longevidad": [8, 14]},
}


def test_gnomo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.1 (config real de gnomo) y minimo
    racial de longevidad=45 anios, el umbral de madurez es exactamente
    0.1 * 45 * TICKS_POR_ANIO = 2160 ticks -- un tick antes NO es adulto,
    en el umbral exacto SI lo es."""
    umbral = int(0.1 * 45 * TICKS_POR_ANIO)
    assert umbral == 2160

    assert es_adulto(umbral - 1, "gnomo", RANGOS_RACIALES, 0.1) is False
    assert es_adulto(umbral, "gnomo", RANGOS_RACIALES, 0.1) is True


def test_lobo_es_adulto_justo_en_el_umbral_no_antes():
    """Ley: con fraccion_madurez=0.2 (config real de lobo) y minimo
    racial de longevidad=8 anios, el umbral de madurez es exactamente
    0.2 * 8 * TICKS_POR_ANIO = 768 ticks -- un tick antes NO es adulto,
    en el umbral exacto SI lo es."""
    umbral = int(0.2 * 8 * TICKS_POR_ANIO)
    assert umbral == 768

    assert es_adulto(umbral - 1, "lobo", RANGOS_RACIALES, 0.2) is False
    assert es_adulto(umbral, "lobo", RANGOS_RACIALES, 0.2) is True


def test_fraccion_madurez_se_aplica_por_especie_no_como_valor_global():
    """Ley: la MISMA edad en ticks puede ser adulta para una especie y
    no adulta para otra -- fraccion_madurez y el minimo racial de
    longevidad son propios de cada especie, es_adulto no comparte
    ningun umbral global entre especies."""
    edad = 1000  # adulto para lobo (umbral 768), no adulto para gnomo (umbral 2160)

    assert es_adulto(edad, "lobo", RANGOS_RACIALES, 0.2) is True
    assert es_adulto(edad, "gnomo", RANGOS_RACIALES, 0.1) is False
```

- [ ] **Step 2: Ejecutar los tests y confirmar que pasan**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_ciclo_vital_es_adulto.py -v`
Expected: 3 tests PASS (la función `es_adulto` ya existe y ya es correcta -- este plan documenta su comportamiento con tests, no corrige ningún fallo).

- [ ] **Step 3: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `30 passed` (27 existentes + 3 nuevos).

- [ ] **Step 4: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add tests/test_ciclo_vital_es_adulto.py
git commit -m "$(cat <<'EOF'
Añadir tests de la ley de madurez reproductiva (es_adulto)

nucleo/ciclo_vital.py:es_adulto decide elegibilidad para reproducirse
pero no tenia ningun test dedicado. Ley pura y determinista sin rng ni
estado -- se fija el umbral exacto en ticks para gnomo (2160) y lobo
(768) usando los valores reales de config/poblacion.yaml, y se confirma
que fraccion_madurez se aplica por especie, no como valor global.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01256zvSsQgtHuBBhjD2mz3A
EOF
)"
```
