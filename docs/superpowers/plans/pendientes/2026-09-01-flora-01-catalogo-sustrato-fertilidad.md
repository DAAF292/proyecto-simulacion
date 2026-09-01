# Flora 1/5: Catálogo de sustrato con fertilidad base — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Añadir un campo `fertilidad_base` a cada material de sustrato del catálogo (`config/materiales.yaml`) y ampliar el catálogo con tres materiales nuevos (`tierra_negra`, `marga`, `grava`) — sin cambiar todavía cómo se usa el sustrato en ningún sitio del motor. Pieza 1 de 5 de la distribución causal de flora.

**Architecture:** Cambio puro de datos de configuración. Ningún fichero `.py` se modifica en este plan — `fertilidad_base` y los tres materiales nuevos quedan declarados pero sin ningún consumidor todavía (los planes 2-5 los usan). Cero riesgo de romper nada existente: `config_materiales` ya se lee hoy vía `.get(clave, {})` en todo el motor, así que un campo nuevo o una entrada nueva sin consumidor es inerte por construcción.

**Tech Stack:** YAML, pytest + PyYAML (`yaml.safe_load`, mismo cargador que usa `main.py:cargar_configuracion`).

**Spec:** `docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`, sección 1 ("Catálogo de sustrato — `config/materiales.yaml`").

## Global Constraints

- No tocar `sustrato_por_bioma` en este plan (sigue siendo `{bioma: material_unico}`, sin cambiar de forma) — ese cambio va atado a su único consumidor real en el plan 4, para no dejar nunca el repositorio en un estado donde el dato tenga una forma que ningún código sabe leer todavía.
- No tocar ningún fichero `.py` — solo `config/materiales.yaml` y un test nuevo.
- No declarar `CLAUDE.md` como fichero a modificar.
- Todos los valores de `fertilidad_base` son PROVISIONALES (orden de magnitud razonado, sin calibrar contra el motor en marcha) — no se justifican con más precisión que la ya dada en la spec.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `config/materiales.yaml` — añade `fertilidad_base` a `piedra`/`arcilla`/`arena`/`tierra`; añade `tierra_negra`/`marga`/`grava` como entradas nuevas completas (mismo esquema que las existentes).
- `tests/test_sustrato_fertilidad.py` — nuevo, valida la forma del catálogo cargando el YAML real.

---

### Task 1: `fertilidad_base` en el catálogo de sustrato

**Files:**
- Modify: `config/materiales.yaml`
- Test: `tests/test_sustrato_fertilidad.py`

**Interfaces:**
- Produces: cada entrada de `config["materiales"]` cuyo `forma_en_mundo == "sustrato"` lleva ahora una clave `fertilidad_base: float` en `[0.0, 1.0]`. Nuevas claves de material: `tierra_negra`, `marga`, `grava`.
- Consumes: ninguno (plan aislado, sin dependencias de otros planes).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_sustrato_fertilidad.py`:

```python
"""Tests del catálogo de sustrato con fertilidad base (2026-09-01, pieza
1/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Valida solo la FORMA del catálogo -- ningún sistema del motor consume
todavía fertilidad_base (eso llega en los planes 2-5). Carga el YAML
real, no una config de prueba recortada: es la única forma de detectar
un typo de indentación o una clave mal escrita antes de que otro plan
dependa de ella.
"""
import yaml

RUTA_MATERIALES = "config/materiales.yaml"

SUSTRATOS_EXISTENTES = {"piedra", "arcilla", "arena", "tierra"}
SUSTRATOS_NUEVOS = {"tierra_negra", "marga", "grava"}


def _cargar_materiales():
    with open(RUTA_MATERIALES, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ley_todo_sustrato_tiene_fertilidad_base_en_0_1():
    datos = _cargar_materiales()
    catalogo = datos["materiales"]
    for nombre, propiedades in catalogo.items():
        if propiedades.get("forma_en_mundo") == "sustrato":
            assert "fertilidad_base" in propiedades, f"{nombre} sin fertilidad_base"
            assert 0.0 <= propiedades["fertilidad_base"] <= 1.0


def test_ley_los_tres_sustratos_nuevos_existen_con_esquema_completo():
    datos = _cargar_materiales()
    catalogo = datos["materiales"]
    campos_obligatorios = {
        "categoria", "forma_en_mundo", "densidad_kg_m3", "dureza",
        "tasa_infiltracion", "capacidad_retencion", "combustibilidad",
        "apto_construccion", "fertilidad_base",
    }
    for nombre in SUSTRATOS_NUEVOS:
        assert nombre in catalogo, f"falta el material nuevo {nombre}"
        assert campos_obligatorios.issubset(catalogo[nombre].keys()), (
            f"{nombre} no tiene el esquema completo de un sustrato"
        )
        assert catalogo[nombre]["forma_en_mundo"] == "sustrato"


def test_ley_sustrato_por_bioma_no_cambia_de_forma_todavia():
    """Este plan NO toca sustrato_por_bioma -- sigue siendo un mapeo
    escalar bioma->material, exactamente como antes. El cambio a lista
    llega en el plan 4, junto con su único consumidor real."""
    datos = _cargar_materiales()
    mapeo = datos["sustrato_por_bioma"]
    for bioma, material in mapeo.items():
        assert isinstance(material, str), (
            f"sustrato_por_bioma[{bioma}] ya no es un string -- este plan no debía tocar esto"
        )
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_sustrato_fertilidad.py -v`
Expected: FAIL — `fertilidad_base` no existe todavía en ninguna entrada, y `tierra_negra`/`marga`/`grava` no existen.

- [ ] **Step 3: Añadir `fertilidad_base` a los 4 sustratos existentes**

En `config/materiales.yaml`, dentro de la sección `materiales:`, añade la clave `fertilidad_base` como última propiedad de cada una de estas cuatro entradas (busca cada bloque por su nombre y añade la línea justo después de `apto_construccion`):

```yaml
  piedra:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 2700
    dureza: 0.9
    tasa_infiltracion: 0.05
    capacidad_retencion: 0.05
    combustibilidad: 0.0
    apto_construccion: true
    # fertilidad_base (2026-09-01, ver docs/superpowers/specs/
    # 2026-09-01-distribucion-causal-flora-design.md): roca desnuda, sin
    # ninguna capacidad de sostener vegetación por sí misma.
    fertilidad_base: 0.0
  arcilla:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1800
    dureza: 0.2
    tasa_infiltracion: 0.15
    capacidad_retencion: 0.8
    combustibilidad: 0.0
    apto_construccion: true
    # fertilidad_base: vega fértil de bosque/pradera -- ya lo era
    # conceptualmente antes de este campo, ahora es un número real.
    fertilidad_base: 0.5
  arena:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1600
    dureza: 0.05
    tasa_infiltracion: 0.85
    capacidad_retencion: 0.15
    combustibilidad: 0.0
    apto_construccion: false
    # fertilidad_base: casi estéril, drena demasiado rápido para retener
    # nutrientes.
    fertilidad_base: 0.03
  tierra:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1300
    dureza: 0.15
    tasa_infiltracion: 0.4
    capacidad_retencion: 0.35
    combustibilidad: 0.0
    apto_construccion: true
    # fertilidad_base: suelo pobre y suelto de tundra -- por encima de
    # arena, muy por debajo de una vega real.
    fertilidad_base: 0.15
```

(El resto de cada bloque -- `categoria` hasta `apto_construccion` -- ya existe tal cual en el fichero; solo añades la línea `fertilidad_base` y su comentario al final de cada uno, sin reescribir el resto.)

- [ ] **Step 4: Añadir los tres sustratos nuevos**

En `config/materiales.yaml`, dentro de la sección `materiales:`, justo después del bloque de `tierra` (antes de la sección `# --- Depósitos orgánicos`), añade:

```yaml
  # tierra_negra / marga / grava (2026-09-01, ver docs/superpowers/specs/
  # 2026-09-01-distribucion-causal-flora-design.md): amplían la variedad
  # de sustrato dentro de un mismo bioma -- antes de esto,
  # sustrato_por_bioma mapeaba 1 material fijo por bioma entero (toda
  # celda de bosque era arcilla, sin variación). El plan 4 de esta pieza
  # los conecta de verdad a sustrato_por_bioma; aquí solo se declaran.
  tierra_negra:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1400
    dureza: 0.12
    tasa_infiltracion: 0.3
    capacidad_retencion: 0.6
    combustibilidad: 0.0
    apto_construccion: true
    # Mantillo acumulado -- el sustrato más fértil del catálogo,
    # candidato de bosque/pradera en celdas de mucha lluvia.
    fertilidad_base: 0.7
  marga:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1600
    dureza: 0.18
    tasa_infiltracion: 0.25
    capacidad_retencion: 0.5
    combustibilidad: 0.0
    apto_construccion: true
    # Intermedia entre arcilla y tierra_negra -- candidata de pradera en
    # celdas de lluvia moderada.
    fertilidad_base: 0.35
  grava:
    categoria: mineral
    forma_en_mundo: sustrato
    densidad_kg_m3: 1900
    dureza: 0.5
    tasa_infiltracion: 0.6
    capacidad_retencion: 0.1
    combustibilidad: 0.0
    apto_construccion: true
    # Transición piedra-tierra -- casi tan estéril como piedra pero
    # suelta, candidata de montaña/desierto en celdas menos extremas que
    # el resto del bioma.
    fertilidad_base: 0.05
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_sustrato_fertilidad.py -v`
Expected: 3 tests PASS.

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 3 nuevos.

- [ ] **Step 7: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add config/materiales.yaml tests/test_sustrato_fertilidad.py
git commit -m "$(cat <<'EOF'
feat: catálogo de sustrato con fertilidad base (flora 1/5)

Añade fertilidad_base a los 4 sustratos existentes y tres materiales
nuevos (tierra_negra, marga, grava) -- sin consumidor todavía, pieza 1
de 5 de la distribución causal de flora
(docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
