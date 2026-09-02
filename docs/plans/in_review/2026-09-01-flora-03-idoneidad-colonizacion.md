# Flora 3/5: idoneidad_colonizacion — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Nueva función `idoneidad_colonizacion` en `nucleo/flora.py` que mide qué tan apta es una celda para que una especie la COLONICE (distinto de `factor_produccion`, que mide cuánto RINDE una planta ya colocada) — combina lluvia, temperatura, fertilidad del sustrato y humedad de subsuelo. Refactoriza `factor_produccion` para compartir la lógica de "idoneidad por rango" en vez de duplicarla. Añade `preferencia_fertilidad` por especie en `config/flora.yaml`. Pieza 3 de 5 — todavía sin conectar a la generación real del mundo (eso es el plan 5).

**Architecture:** Extrae el cálculo de "¿este valor cae dentro del rango preferido, y si no, cuánto se aleja?" (hoy duplicado inline dos veces en `factor_produccion`, para lluvia y temperatura) a un helper `_idoneidad_por_rango`, reutilizado tres veces por `idoneidad_colonizacion` (lluvia, temperatura, fertilidad) y dos por `factor_produccion` (mismo comportamiento exacto que antes, verificado con test de regresión).

**Tech Stack:** Python 3, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`, sección 5 ("Ley de colonización").

## Global Constraints

- El refactor de `factor_produccion` NO debe cambiar ningún resultado existente — el test de regresión de este plan lo comprueba con un valor numérico exacto conocido.
- `idoneidad_colonizacion` es una función nueva, sin ningún punto de llamada todavía en `nucleo/zona_bioma.py` — no toca ese fichero.
- No declarar `CLAUDE.md` como fichero a modificar.
- Los cinco rangos de `preferencia_fertilidad` son PROVISIONALES, mismo criterio que el resto de constantes numéricas del proyecto.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/flora.py` — nuevo helper `_idoneidad_por_rango`, refactor de `factor_produccion` para usarlo, nueva función `idoneidad_colonizacion`.
- `config/flora.yaml` — nuevo campo `preferencia_fertilidad` en las 5 especies existentes (`hierba_silvestre`, `manzano`, `cactus`, `liquen`, `musgo`).
- `tests/test_flora_idoneidad.py` — nuevo.

---

### Task 1: `idoneidad_colonizacion` + refactor de `factor_produccion`

**Files:**
- Modify: `nucleo/flora.py`
- Modify: `config/flora.yaml`
- Test: `tests/test_flora_idoneidad.py`

**Interfaces:**
- Produces: `_idoneidad_por_rango(valor: float, rango: list[float]) -> float`; `idoneidad_colonizacion(especie_cfg: dict, celda: Celda, capacidad_retencion: float) -> float`.
- Consumes: `nucleo.celda.Celda` (ya existente, sin cambios), `nucleo.flora.factor_humedad_subsuelo` (ya existente, sin cambios).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_idoneidad.py`:

```python
"""Tests de idoneidad_colonizacion -- ley de qué tan apta es una celda
para que una especie de flora la COLONICE (2026-09-01, pieza 3/5 de la
distribución causal de flora -- ver docs/superpowers/specs/
2026-09-01-distribucion-causal-flora-design.md).

Distinta de factor_produccion (cuánto rinde una planta YA colocada):
esta se evalúa ANTES de que exista ninguna planta, para decidir si debe
existir. Combina lluvia, temperatura, fertilidad del sustrato y humedad
de subsuelo -- cuatro señales físicas reales de la celda, ninguna
proporción impuesta en config.
"""
from nucleo.celda import Celda, TipoTerreno
from nucleo.clima import Clima, Estacion
from nucleo.flora import _idoneidad_por_rango, factor_produccion, idoneidad_colonizacion

ESPECIE_CFG = {
    "preferencia_lluvia": [0.4, 0.8],
    "preferencia_temperatura": [0.3, 0.7],
    "preferencia_fertilidad": [0.4, 0.9],
}


def test_idoneidad_por_rango_dentro_del_rango_es_maxima():
    assert _idoneidad_por_rango(0.5, [0.4, 0.8]) == 1.0


def test_idoneidad_por_rango_fuera_del_rango_cae_con_la_distancia():
    idoneidad_cerca = _idoneidad_por_rango(0.35, [0.4, 0.8])
    idoneidad_lejos = _idoneidad_por_rango(0.0, [0.4, 0.8])
    assert 0.1 <= idoneidad_lejos < idoneidad_cerca < 1.0


def test_idoneidad_por_rango_nunca_baja_de_0_1():
    assert _idoneidad_por_rango(-5.0, [0.4, 0.8]) == 0.1


def test_celda_dentro_de_todos_los_rangos_preferidos_da_idoneidad_alta():
    """capacidad_retencion=0.5 con humedad_subsuelo=0.5 (saturación
    completa) para que f_humedad alcance su máximo normalizado de 1.0 --
    con capacidad_retencion=0.0, factor_humedad_subsuelo devuelve 1.0 sin
    el bono (material sin capacidad de retención conocida), que
    normalizado da 1.0/1.2=0.833, no >0.9."""
    celda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.5,
    )
    idoneidad = idoneidad_colonizacion(ESPECIE_CFG, celda, capacidad_retencion=0.5)
    assert idoneidad > 0.9


def test_celda_fuera_de_los_rangos_preferidos_da_idoneidad_baja():
    celda = Celda(
        tipo_terreno=TipoTerreno.DESIERTO, lluvia=0.0, temperatura=1.0,
        fertilidad=0.0, humedad_subsuelo=0.0,
    )
    idoneidad = idoneidad_colonizacion(ESPECIE_CFG, celda, capacidad_retencion=0.0)
    assert idoneidad < 0.05


def test_humedad_de_subsuelo_alta_sube_la_idoneidad_frente_a_ninguna():
    celda_seca = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.0,
    )
    celda_humeda = Celda(
        tipo_terreno=TipoTerreno.BOSQUE, lluvia=0.6, temperatura=0.5,
        fertilidad=0.6, humedad_subsuelo=0.8,
    )
    idoneidad_seca = idoneidad_colonizacion(ESPECIE_CFG, celda_seca, capacidad_retencion=0.8)
    idoneidad_humeda = idoneidad_colonizacion(ESPECIE_CFG, celda_humeda, capacidad_retencion=0.8)
    assert idoneidad_humeda > idoneidad_seca


def test_regresion_factor_produccion_da_el_mismo_resultado_de_siempre():
    """Regresión: el refactor a _idoneidad_por_rango no debe cambiar
    ningún resultado existente de factor_produccion. Con lluvia=0.5 y
    temperatura=0.5 dentro de rangos [0.25, 0.85] (ambos con f=1.0) y
    verano/despejado (modificador 1.2 * 1.0), el resultado exacto
    esperado es 1.2 -- mismo cálculo que antes del refactor."""
    especie_cfg = {
        "preferencia_lluvia": [0.25, 0.85], "preferencia_temperatura": [0.25, 0.85],
    }
    config = {
        "estaciones": {"verano": {"modificador_regeneracion": 1.2}},
        "clima": {"efectos": {"despejado": {"modificador_regeneracion": 1.0}}},
    }
    resultado = factor_produccion(
        especie_cfg, lluvia_celda=0.5, temp_celda=0.5,
        estacion=Estacion.VERANO, clima=Clima.DESPEJADO, config=config,
    )
    assert resultado == 1.2
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_flora_idoneidad.py -v`
Expected: FAIL con `ImportError: cannot import name '_idoneidad_por_rango'` (y `idoneidad_colonizacion`).

- [ ] **Step 3: Extraer `_idoneidad_por_rango` y refactorizar `factor_produccion`**

En `nucleo/flora.py`, busca este bloque dentro de `factor_produccion` (el cuerpo completo de la función, secciones "1. Idoneidad de lluvia" y "2. Idoneidad de temperatura"):

```python
    # 1. Idoneidad de lluvia
    rango_lluvia = especie_cfg.get("preferencia_lluvia", [0.0, 1.0])
    if rango_lluvia[0] <= lluvia_celda <= rango_lluvia[1]:
        f_lluvia = 1.0
    else:
        dist = min(
            abs(lluvia_celda - rango_lluvia[0]),
            abs(lluvia_celda - rango_lluvia[1]),
        )
        f_lluvia = max(0.1, 1.0 - (dist * 2.0))

    # 2. Idoneidad de temperatura
    rango_temp = especie_cfg.get("preferencia_temperatura", [0.0, 1.0])
    if rango_temp[0] <= temp_celda <= rango_temp[1]:
        f_temp = 1.0
    else:
        # (2026-08-23) corregido: referenciaba una variable inexistente
        # `temp_temp` dentro de una condición que siempre era verdadera
        # (`"rango_temp" in locals()`, definida justo arriba sin condición)
        # -- habría lanzado NameError la primera vez que una celda cayera
        # fuera del rango de temperatura preferido de cualquier especie.
        # Misma forma que el cálculo de lluvia de arriba.
        dist = min(
            abs(temp_celda - rango_temp[0]),
            abs(temp_celda - rango_temp[1]),
        )
        f_temp = max(0.1, 1.0 - (dist * 2.0))
```

Sustitúyelo por:

```python
    # 1-2. Idoneidad de lluvia y temperatura -- ambas comparten la misma
    # ley (dentro del rango preferido -> 1.0, fuera -> cae linealmente
    # con la distancia, suelo 0.1), extraída a _idoneidad_por_rango
    # (2026-09-01, ver docs/superpowers/specs/
    # 2026-09-01-distribucion-causal-flora-design.md) para reutilizarla
    # también en idoneidad_colonizacion sin triplicar la fórmula.
    f_lluvia = _idoneidad_por_rango(lluvia_celda, especie_cfg.get("preferencia_lluvia", [0.0, 1.0]))
    f_temp = _idoneidad_por_rango(temp_celda, especie_cfg.get("preferencia_temperatura", [0.0, 1.0]))
```

Justo ANTES de la definición de `factor_produccion` (antes de la línea `def factor_produccion(`), añade el nuevo helper:

```python
def _idoneidad_por_rango(valor: float, rango: list[float]) -> float:
    """Nota de idoneidad [0.1, 1.0] de un valor continuo frente a un rango
    preferido -- 1.0 dentro del rango, cae linealmente por distancia fuera
    de él, con un suelo de 0.1 (ningún valor es una imposibilidad
    absoluta, solo una idoneidad baja). Extraída de factor_produccion
    (2026-09-01), que la calculaba dos veces inline -- reutilizada también
    por idoneidad_colonizacion (fertilidad) sin triplicar la fórmula."""
    if rango[0] <= valor <= rango[1]:
        return 1.0
    dist = min(abs(valor - rango[0]), abs(valor - rango[1]))
    return max(0.1, 1.0 - (dist * 2.0))


```

- [ ] **Step 4: Implementar `idoneidad_colonizacion`**

En `nucleo/flora.py`, añade esta función al final del fichero (después de `factor_humedad_subsuelo` y su alias `calcular_factor_produccion`):

```python
def idoneidad_colonizacion(
    especie_cfg: dict[str, Any], celda: Celda, capacidad_retencion: float,
) -> float:
    """Idoneidad de una especie para COLONIZAR una celda -- distinto de
    factor_produccion (que mide cuánto RINDE una planta ya colocada).
    Círculo de distribución causal de flora (2026-09-01, ver
    docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md):
    sustituye el reparto por proporción/mancha fijo en config -- una
    especie coloniza donde su idoneidad real (lluvia, temperatura,
    fertilidad del sustrato, humedad de subsuelo) lo permite, no donde un
    porcentaje impuesto de antemano dice que debe haber tanta hierba.

    factor_humedad_subsuelo devuelve un multiplicador en [1.0, 1+bono] --
    pensado para producción, no como nota de idoneidad en [0,1] como los
    demás factores de aquí -- se normaliza dividiendo por (1+bono) para
    que se comporte igual que f_lluvia/f_temp/f_fertilidad."""
    f_lluvia = _idoneidad_por_rango(celda.lluvia, especie_cfg.get("preferencia_lluvia", [0.0, 1.0]))
    f_temp = _idoneidad_por_rango(celda.temperatura, especie_cfg.get("preferencia_temperatura", [0.0, 1.0]))
    f_fertilidad = _idoneidad_por_rango(celda.fertilidad, especie_cfg.get("preferencia_fertilidad", [0.0, 1.0]))
    bono_maximo = 0.2
    f_humedad = factor_humedad_subsuelo(celda, capacidad_retencion, bono_maximo) / (1.0 + bono_maximo)
    return f_lluvia * f_temp * f_fertilidad * f_humedad
```

- [ ] **Step 5: Añadir `preferencia_fertilidad` a las 5 especies de `config/flora.yaml`**

En `config/flora.yaml`, dentro de `flora.especies`, añade la línea `preferencia_fertilidad` justo después de `preferencia_temperatura` en cada especie (busca cada línea `preferencia_temperatura` por su valor exacto, que es único por especie):

```yaml
      preferencia_temperatura: [0.25, 0.85]
      preferencia_fertilidad: [0.2, 0.8]
```
(en `hierba_silvestre`)

```yaml
      preferencia_temperatura: [0.3, 0.75]
      preferencia_fertilidad: [0.4, 0.9]
```
(en `manzano`)

```yaml
      preferencia_temperatura: [0.5, 1.0]
      preferencia_fertilidad: [0.0, 0.3]
```
(en `cactus`)

```yaml
      preferencia_temperatura: [0.0, 0.4]
      preferencia_fertilidad: [0.0, 0.2]
```
(en `liquen`)

```yaml
      preferencia_temperatura: [0.0, 0.15]
      preferencia_fertilidad: [0.0, 0.3]
```
(en `musgo`)

En cada caso, la línea `preferencia_temperatura: [...]` ya existe tal cual en el fichero (con esos valores exactos, cada uno aparece una sola vez) -- solo añade la línea `preferencia_fertilidad` justo debajo, sin tocar nada más de esa especie.

- [ ] **Step 6: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_flora_idoneidad.py -v`
Expected: 7 tests PASS.

- [ ] **Step 7: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 7 nuevos.

- [ ] **Step 8: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/flora.py config/flora.yaml tests/test_flora_idoneidad.py
git commit -m "$(cat <<'EOF'
feat: idoneidad_colonizacion (flora 3/5)

Extrae _idoneidad_por_rango de factor_produccion (comportamiento
idéntico, verificado con test de regresión) y la reutiliza en la nueva
idoneidad_colonizacion -- combina lluvia, temperatura, fertilidad del
sustrato y humedad de subsuelo para decidir si una especie PUEDE
colonizar una celda, distinto de cuánto RINDE una planta ya colocada.
Añade preferencia_fertilidad por especie. Sin conectar todavía a la
generación real del mundo, pieza 3 de 5 de la distribución causal de
flora (docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
