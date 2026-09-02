# Propagación 1/5: Catálogo de tipos de propagación — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Declarar `tipo_propagacion` (viento | caida | zoocoria) por especie y las tres constantes numéricas nuevas en `config/flora.yaml` — sin cambiar todavía ningún fichero `.py`. Pieza 1 de 5 de "tipos de propagación de flora".

**Architecture:** Cambio puro de datos de configuración. Ningún consumidor real todavía — piezas futuras lo usan. Cero riesgo de romper nada existente: ningún sistema del motor lee `tipo_propagacion` hoy, así que añadirlo es inerte por construcción.

**Tech Stack:** YAML, pytest + PyYAML (`yaml.safe_load`).

**Spec:** diseño aprobado por Diego para la propagación de flora por vectores (viento, caída, zoocoria), sección de catálogo. Este plan es autocontenido -- todo el código necesario está incluido abajo, no hace falta consultar ningún otro documento para completarlo.

## Global Constraints

- No tocar ningún fichero `.py` en este plan — solo `config/flora.yaml` y un test nuevo.
- No añadas, edites ni menciones ningún fichero que no sea uno de los dos listados en "Files" de la tarea de abajo. Si crees que necesitas leer o tocar otro fichero para completar esta tarea, DETENTE y no lo hagas -- este plan está diseñado para ser autosuficiente con el código ya incluido.
- `alcance_viento_celdas` se declara SOLO en las especies con `tipo_propagacion: viento` — no añadir esa clave a `manzano` (zoocoria) ni `cactus` (caida).
- Todos los valores numéricos nuevos son PROVISIONALES (sin calibrar contra el motor en marcha) — no los justifiques con más precisión de la que ya se da aquí.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `config/flora.yaml` — añade `tipo_propagacion` (y `alcance_viento_celdas` donde aplique) a las 5 especies existentes bajo `flora.especies`; añade `probabilidad_recogida_semilla_zoocoria` y `probabilidad_plantar_semilla_en_aliviarse` como claves sibling de `especies:` dentro de `flora:`.
- `tests/test_flora_tipo_propagacion.py` — nuevo, valida la forma del catálogo cargando el YAML real.

---

### Task 1: `tipo_propagacion` + constantes de zoocoria en el catálogo

**Files:**
- Modify: `config/flora.yaml`
- Test: `tests/test_flora_tipo_propagacion.py`

**Interfaces:**
- Produces: cada entrada de `config["flora"]["especies"]` lleva ahora una clave `tipo_propagacion: str` en `{"viento", "caida", "zoocoria"}`; las especies `viento` llevan además `alcance_viento_celdas: [int, int]`. `config["flora"]["probabilidad_recogida_semilla_zoocoria"]` y `config["flora"]["probabilidad_plantar_semilla_en_aliviarse"]` son floats en `[0.0, 1.0]`.
- Consumes: ninguno (plan aislado, sin dependencias de otros planes).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_tipo_propagacion.py`:

```python
"""Tests del catálogo de tipos de propagación de flora (2026-09-02,
pieza 1 de "tipos de propagación de flora" -- viento, caída, zoocoria).

Valida solo la FORMA del catálogo -- ningún sistema del motor consume
tipo_propagacion todavía. Carga el YAML real, no una config recortada.
"""
import yaml

RUTA_FLORA = "config/flora.yaml"

TIPOS_VALIDOS = {"viento", "caida", "zoocoria"}

ASIGNACION_ESPERADA = {
    "hierba_silvestre": "viento",
    "manzano": "zoocoria",
    "cactus": "caida",
    "liquen": "viento",
    "musgo": "viento",
}


def _cargar_flora():
    with open(RUTA_FLORA, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_ley_toda_especie_tiene_tipo_propagacion_valido():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        assert "tipo_propagacion" in cfg, f"{nombre} sin tipo_propagacion"
        assert cfg["tipo_propagacion"] in TIPOS_VALIDOS


def test_ley_asignacion_por_especie_es_la_acordada_con_diego():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, tipo_esperado in ASIGNACION_ESPERADA.items():
        assert especies[nombre]["tipo_propagacion"] == tipo_esperado, (
            f"{nombre} debía ser {tipo_esperado}"
        )


def test_ley_especies_viento_declaran_alcance_valido():
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        if cfg["tipo_propagacion"] != "viento":
            continue
        alcance = cfg.get("alcance_viento_celdas")
        assert alcance is not None, f"{nombre} es viento pero no declara alcance_viento_celdas"
        assert len(alcance) == 2
        assert alcance[0] >= 1
        assert alcance[0] <= alcance[1]


def test_ley_especies_no_viento_no_declaran_alcance():
    """caida y zoocoria no usan alcance_viento_celdas -- si aparece ahí
    es un descuido de copiar/pegar entre especies, no un valor real."""
    datos = _cargar_flora()
    especies = datos["flora"]["especies"]
    for nombre, cfg in especies.items():
        if cfg["tipo_propagacion"] != "viento":
            assert "alcance_viento_celdas" not in cfg, (
                f"{nombre} no es viento pero declara alcance_viento_celdas"
            )


def test_ley_constantes_zoocoria_son_probabilidades_validas():
    datos = _cargar_flora()
    flora_cfg = datos["flora"]
    assert "probabilidad_recogida_semilla_zoocoria" in flora_cfg
    assert "probabilidad_plantar_semilla_en_aliviarse" in flora_cfg
    assert 0.0 <= flora_cfg["probabilidad_recogida_semilla_zoocoria"] <= 1.0
    assert 0.0 <= flora_cfg["probabilidad_plantar_semilla_en_aliviarse"] <= 1.0
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_flora_tipo_propagacion.py -v`
Expected: FAIL — `tipo_propagacion` no existe todavía en ninguna especie.

- [ ] **Step 3: Añadir `tipo_propagacion` a las 5 especies**

En `config/flora.yaml`, dentro de `flora.especies`, añade la clave `tipo_propagacion` (y `alcance_viento_celdas` donde aplique) como última propiedad de cada bloque de especie, justo antes de su clave `recursos:`. No reescribas el resto de cada bloque — solo inserta estas líneas.

En `hierba_silvestre` (antes de `recursos:`):
```yaml
      # tipo_propagacion (2026-09-02): semilla ligera dispersada por el
      # viento del mundo (zona.viento_dx/viento_dy) -- PROVISIONAL, sin
      # calibrar. Pradera abierta: alcance mayor que liquen/musgo.
      tipo_propagacion: viento
      alcance_viento_celdas: [2, 6]
```

En `manzano` (antes de `recursos:`):
```yaml
      # tipo_propagacion: fruto comestible -- lo dispersa un animal que
      # se lo come (zoocoria), no el viento ni la caída directa.
      tipo_propagacion: zoocoria
```

En `cactus` (antes de `recursos:`):
```yaml
      # tipo_propagacion: fruto pesado, cae cerca de la base de la planta
      # madre -- mismo mecanismo que ya tenía la propagación de hoy,
      # solo formalizado como catálogo.
      tipo_propagacion: caida
```

En `liquen` (antes de `recursos:`):
```yaml
      # tipo_propagacion: reproducción por esporas ligeras -- viento,
      # alcance corto (superficie resguardada de montaña).
      tipo_propagacion: viento
      alcance_viento_celdas: [1, 3]
```

En `musgo` (antes de `recursos:`):
```yaml
      # tipo_propagacion: igual que liquen -- esporas, viento de corto
      # alcance.
      tipo_propagacion: viento
      alcance_viento_celdas: [1, 3]
```

- [ ] **Step 4: Añadir las dos constantes de zoocoria**

En `config/flora.yaml`, dentro de la sección `flora:`, justo antes de la clave `especies:`, añade:

```yaml
  # probabilidad_recogida_semilla_zoocoria / probabilidad_plantar_semilla_
  # en_aliviarse (2026-09-02): modelado por probabilidad, sin simular
  # tránsito digestivo real. La primera: comer fruto de una especie
  # zoocora deja una semilla "recogida" con esta probabilidad. La
  # segunda: un ALIVIARSE con semilla ya recogida es el evento que la
  # deposita con esta probabilidad (no cada ALIVIARSE disemina
  # necesariamente la semilla concreta que se transporta). Ambas
  # PROVISIONALES, sin calibrar.
  probabilidad_recogida_semilla_zoocoria: 0.3
  probabilidad_plantar_semilla_en_aliviarse: 0.5
```

- [ ] **Step 5: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_flora_tipo_propagacion.py -v`
Expected: 5 tests PASS.

- [ ] **Step 6: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde, más los 5 nuevos.

- [ ] **Step 7: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add config/flora.yaml tests/test_flora_tipo_propagacion.py
git commit -m "feat: catalogo de tipos de propagacion de flora (propagacion 1/5)"
```
