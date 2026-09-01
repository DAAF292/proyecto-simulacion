# Flora 2/5: elegir_sustrato_celda — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nueva función pura `elegir_sustrato_celda` en `nucleo/materiales.py`: decide qué sustrato de una lista de candidatos compatibles con un bioma le toca a una celda concreta, según una señal causal ya calculada en generación (elevación para biomas pedregosos, lluvia para biomas vegetados) en vez de un sorteo ciego. Pieza 2 de 5 de la distribución causal de flora — todavía sin conectar a la generación real del mundo (eso es el plan 4).

**Architecture:** Función pura, sin estado, sin `rng` — determinista a partir de sus argumentos, mismo criterio que el resto de campos causales de una celda (elevación/lluvia/temperatura tampoco consumen `rng`). Vive en `nucleo/materiales.py` junto a `generar_vetas_minerales`, ya la incumbencia de "qué material físico hay en una celda" de ese módulo.

**Tech Stack:** Python 3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`, sección 3 ("Elección de sustrato por celda").

## Global Constraints

- Función nueva, sin ningún punto de llamada todavía en `nucleo/zona_bioma.py` — no toca ese fichero. Cero riesgo de romper la generación real, porque nada la invoca aún.
- No tocar `config/materiales.yaml` en este plan (la lista de candidatos y el umbral por bioma se prueban con valores literales en el test, no cargando el YAML real).
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/materiales.py` — nueva función `elegir_sustrato_celda`, nueva constante módulo `_BIOMAS_PEDREGOSOS`.
- `tests/test_materiales_sustrato.py` — nuevo.

---

### Task 1: `elegir_sustrato_celda`

**Files:**
- Modify: `nucleo/materiales.py`
- Test: `tests/test_materiales_sustrato.py`

**Interfaces:**
- Produces: `elegir_sustrato_celda(candidatos: list[str], bioma: TipoTerreno, elevacion_celda: float, lluvia_celda: float, umbral: float) -> str`.
- Consumes: `nucleo.celda.TipoTerreno` (enum ya existente, sin cambios).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_materiales_sustrato.py`:

```python
"""Tests de elegir_sustrato_celda -- ley de qué sustrato le toca a una
celda dentro de la lista de candidatos compatibles con su bioma
(2026-09-01, pieza 2/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Un bioma con dos sustratos candidatos, ordenados de menor a mayor
fertilidad_base, elige entre ellos según una señal causal ya calculada
en generación (elevación para biomas pedregosos -- montaña, desierto;
lluvia para biomas vegetados -- bosque, pradera), nunca un sorteo ciego.
Un bioma con un único candidato (tundra) no consulta ninguna señal.
"""
from nucleo.celda import TipoTerreno
from nucleo.materiales import elegir_sustrato_celda


def test_ley_bioma_con_un_solo_candidato_no_consulta_ninguna_senal():
    assert elegir_sustrato_celda(["tierra"], TipoTerreno.TUNDRA, 0.99, 0.99, 0.5) == "tierra"
    assert elegir_sustrato_celda(["tierra"], TipoTerreno.TUNDRA, 0.01, 0.01, 0.5) == "tierra"


def test_ley_bioma_pedregoso_elevacion_alta_da_el_sustrato_menos_fertil():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.8, 0.5, 0.6) == "piedra"


def test_ley_bioma_pedregoso_elevacion_baja_da_el_sustrato_mas_fertil():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.3, 0.5, 0.6) == "grava"


def test_ley_bioma_vegetado_lluvia_alta_da_el_sustrato_mas_fertil():
    candidatos = ["arcilla", "tierra_negra"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.BOSQUE, 0.5, 0.8, 0.55) == "tierra_negra"


def test_ley_bioma_vegetado_lluvia_baja_da_el_sustrato_menos_fertil():
    candidatos = ["arcilla", "tierra_negra"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.BOSQUE, 0.5, 0.2, 0.55) == "arcilla"


def test_ley_desierto_es_pedregoso_no_vegetado():
    """Desierto usa elevación, no lluvia, igual que montaña -- pese a ser
    un bioma 'seco' no es la categoría 'vegetado' de esta ley."""
    candidatos = ["arena", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.DESIERTO, 0.7, 0.9, 0.5) == "arena"
    assert elegir_sustrato_celda(candidatos, TipoTerreno.DESIERTO, 0.2, 0.9, 0.5) == "grava"


def test_ley_valor_justo_en_el_umbral_cuenta_como_alto():
    candidatos = ["piedra", "grava"]
    assert elegir_sustrato_celda(candidatos, TipoTerreno.MONTANA, 0.6, 0.5, 0.6) == "piedra"
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_materiales_sustrato.py -v`
Expected: FAIL con `ImportError: cannot import name 'elegir_sustrato_celda'`.

- [ ] **Step 3: Implementar `elegir_sustrato_celda`**

En `nucleo/materiales.py`, añade este import junto a los ya existentes al principio del fichero (`import math` / `import random`):

```python
from nucleo.celda import TipoTerreno
```

Y añade esta función al final del fichero (después de todo lo demás):

```python
# elegir_sustrato_celda (2026-09-01, ver docs/superpowers/specs/
# 2026-09-01-distribucion-causal-flora-design.md): qué sustrato de una
# lista de candidatos compatibles con un bioma le toca a una celda
# concreta -- antes de esto, sustrato_por_bioma era 1 material fijo por
# bioma entero, sin ninguna variación interna. Determinista, sin
# consumir rng -- mismo criterio que elevación/lluvia/temperatura, que
# tampoco lo consumen: son funciones puras del ruido ya generado.
_BIOMAS_PEDREGOSOS = {TipoTerreno.MONTANA, TipoTerreno.DESIERTO}


def elegir_sustrato_celda(
    candidatos: list[str],
    bioma: TipoTerreno,
    elevacion_celda: float,
    lluvia_celda: float,
    umbral: float,
) -> str:
    """Candidatos ordenados de menor a mayor fertilidad_base (convención
    de config/materiales.yaml:sustrato_por_bioma). Con un único
    candidato, se devuelve directo -- ningún bioma necesita más de una
    señal para decidir lo que ya está decidido (tundra hoy). Con dos,
    biomas 'pedregosos' (montaña, desierto) comparan elevación_celda
    contra el umbral -- más alta empuja hacia el candidato MENOS fértil
    (roca desnuda en las cumbres); biomas 'vegetados' (bosque, pradera)
    comparan lluvia_celda -- más alta empuja hacia el candidato MÁS
    fértil (mantillo donde llueve más)."""
    if len(candidatos) == 1:
        return candidatos[0]
    if bioma in _BIOMAS_PEDREGOSOS:
        return candidatos[0] if elevacion_celda >= umbral else candidatos[-1]
    return candidatos[-1] if lluvia_celda >= umbral else candidatos[0]
```

- [ ] **Step 4: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_materiales_sustrato.py -v`
Expected: 7 tests PASS.

- [ ] **Step 5: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 7 nuevos. Presta atención especial a que ningún test de `nucleo/materiales.py` existente (vetas de mineral) se haya visto afectado por el nuevo import de `TipoTerreno` -- no debería, es un import adicional sin efecto sobre el código ya presente.

- [ ] **Step 6: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/materiales.py tests/test_materiales_sustrato.py
git commit -m "$(cat <<'EOF'
feat: elegir_sustrato_celda (flora 2/5)

Nueva función pura en nucleo/materiales.py que decide qué sustrato de
una lista de candidatos le toca a una celda según elevación (biomas
pedregosos) o lluvia (biomas vegetados) -- sin conectar todavía a la
generación real del mundo, pieza 2 de 5 de la distribución causal de
flora (docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
