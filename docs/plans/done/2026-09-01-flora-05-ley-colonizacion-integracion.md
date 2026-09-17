# Flora 5/5: Ley de colonización sustituye a proporción/mancha — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La colocación de especies de flora en la generación del mundo deja de repartirse por proporción/tamaño de mancha fijados en config (`_generar_manchas`) y pasa a decidirse celda a celda por idoneidad real (`idoneidad_colonizacion`, plan 3), usando el sustrato/fertilidad reales ya conectados (plan 4). Una celda sin ninguna especie por encima del umbral mínimo se queda sin vegetación -- resultado real, no forzado. Última pieza (5/5) de la distribución causal de flora.

**Architecture:** Nueva función `colonizar_por_idoneidad` en `nucleo/flora.py` sustituye, dentro de `generar_zona_bioma`, el bloque que hoy usa `_generar_manchas` para flora. `_generar_manchas` en sí NO se toca ni se borra -- sigue siendo usada por `nucleo/materiales.py:generar_vetas_minerales` para las vetas de mineral, algo completamente distinto de la colocación de flora. Requiere hoistear el cálculo de humedad de subsuelo (hoy inline dentro del bucle final de construcción de `Celda`) a una pasada previa, porque la nueva colonización necesita esa señal ANTES de que exista ninguna `Celda` todavía.

**Tech Stack:** Python 3, YAML, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md`, secciones 4 (reordenación del pipeline) y 6 (sustitución de `_generar_manchas`).

## Global Constraints

- **Prerrequisito: los planes 1, 2, 3 y 4 deben estar ya mergeados en la rama base antes de ejecutar este plan** — usa `idoneidad_colonizacion` (plan 3), `fertilidad_por_celda`/`tipo_sustrato_por_celda` ya conectados (plan 4), y `preferencia_fertilidad`/`fertilidad_base` (planes 1 y 3).
- **No borrar ni modificar `_generar_manchas`** en `nucleo/zona_bioma.py` -- sigue siendo la única implementación de generación de vetas de mineral (`nucleo/materiales.py` la importa en diferido). Solo se elimina su llamada para flora.
- `proporcion`/`celdas_por_mancha_objetivo` se retiran de `config/flora.yaml` en este plan -- confirmado por grep que su único consumidor era el bloque que este plan sustituye (ningún otro fichero `.py` los lee).
- `umbral_minimo_idoneidad_colonizacion` es PROVISIONAL.
- No declarar `CLAUDE.md` como fichero a modificar.
- No modificar ninguna aserción de los tests ya existentes en `tests/`.

---

## File Structure

- `nucleo/flora.py` — nueva función `colonizar_por_idoneidad` (usa `idoneidad_colonizacion` del plan 3); nuevo `import random` al principio del fichero.
- `nucleo/zona_bioma.py` — elimina el bloque de colonización por manchas; añade una pasada previa de humedad de subsuelo; llama a `colonizar_por_idoneidad` en su lugar; simplifica el cálculo inline de humedad dentro del bucle final.
- `config/flora.yaml` — retira `proporcion`/`celdas_por_mancha_objetivo` de las 5 especies; añade `umbral_minimo_idoneidad_colonizacion`.
- `tests/test_flora_colonizacion.py` — nuevo, unitario + integración con configuración real.

---

### Task 1: `colonizar_por_idoneidad` + integración en `generar_zona_bioma`

**Files:**
- Modify: `nucleo/flora.py`
- Modify: `nucleo/zona_bioma.py`
- Modify: `config/flora.yaml`
- Test: `tests/test_flora_colonizacion.py`

**Interfaces:**
- Consumes: `nucleo.flora.idoneidad_colonizacion` (plan 3), `nucleo.celda.Celda`/`TipoTerreno` (ya existentes).
- Produces: `colonizar_por_idoneidad(rng, todas_las_celdas, biomas, campo_lluvia, campo_temperatura, fertilidad_por_celda, humedad_subsuelo_por_celda, capacidad_retencion_por_celda, especies_cfg, umbral_minimo) -> dict[tuple[int, int], str]`.

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_flora_colonizacion.py`:

```python
"""Tests de colonizar_por_idoneidad -- ley de colonización de flora por
celda (2026-09-01, pieza 5/5 de la distribución causal de flora -- ver
docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Sustituye el reparto por proporción/mancha fijo en config: cada celda
decide qué especie (si alguna) la coloniza según su propia idoneidad
física, no según un porcentaje impuesto de antemano.
"""
import random
from pathlib import Path

from main import cargar_configuracion
from nucleo.celda import TipoTerreno
from nucleo.flora import colonizar_por_idoneidad
from nucleo.zona_bioma import generar_zona_bioma

BIOMAS = {(0, 0): TipoTerreno.BOSQUE, (1, 0): TipoTerreno.DESIERTO, (2, 0): TipoTerreno.MONTANA}
TODAS_LAS_CELDAS = set(BIOMAS.keys())
CAMPO_LLUVIA = [[0.6], [0.05], [0.1]]
CAMPO_TEMPERATURA = [[0.5], [0.9], [0.1]]
FERTILIDAD = {(0, 0): 0.6, (1, 0): 0.03, (2, 0): 0.0}
HUMEDAD = {(0, 0): 0.0, (1, 0): 0.0, (2, 0): 0.0}
CAPACIDAD_RETENCION = {(0, 0): 0.8, (1, 0): 0.15, (2, 0): 0.05}

ESPECIES_CFG = {
    "manzano": {
        "biomas": ["bosque"],
        "preferencia_lluvia": [0.5, 1.0], "preferencia_temperatura": [0.3, 0.7],
        "preferencia_fertilidad": [0.4, 0.9],
    },
    "cactus": {
        "biomas": ["desierto"],
        "preferencia_lluvia": [0.0, 0.2], "preferencia_temperatura": [0.5, 1.0],
        "preferencia_fertilidad": [0.0, 0.3],
    },
}


def _colonizar(umbral):
    return colonizar_por_idoneidad(
        random.Random(1), TODAS_LAS_CELDAS, BIOMAS, CAMPO_LLUVIA, CAMPO_TEMPERATURA,
        FERTILIDAD, HUMEDAD, CAPACIDAD_RETENCION, ESPECIES_CFG, umbral,
    )


def test_ley_celda_apta_es_colonizada_por_la_especie_de_su_bioma():
    resultado = _colonizar(umbral=0.2)
    assert resultado[(0, 0)] == "manzano"
    assert resultado[(1, 0)] == "cactus"


def test_ley_celda_sin_ninguna_especie_candidata_de_su_bioma_queda_vacia():
    resultado = _colonizar(umbral=0.2)
    assert (2, 0) not in resultado  # montaña, ninguna especie del catálogo la lista


def test_ley_umbral_alto_deja_vacia_una_celda_con_idoneidad_insuficiente():
    resultado = _colonizar(umbral=0.99)
    assert (0, 0) not in resultado
    assert (1, 0) not in resultado


def test_ley_dos_candidatas_parejas_se_reparten_por_muestreo_ponderado():
    biomas_bosque = {(x, 0): TipoTerreno.BOSQUE for x in range(200)}
    todas = set(biomas_bosque.keys())
    lluvia = [[0.6] for _ in range(200)]
    temperatura = [[0.5] for _ in range(200)]
    fertilidad = {(x, 0): 0.6 for x in range(200)}
    humedad = {(x, 0): 0.0 for x in range(200)}
    capacidad = {(x, 0): 0.8 for x in range(200)}
    especies = {
        "a": {
            "biomas": ["bosque"], "preferencia_lluvia": [0.5, 1.0],
            "preferencia_temperatura": [0.3, 0.7], "preferencia_fertilidad": [0.4, 0.9],
        },
        "b": {
            "biomas": ["bosque"], "preferencia_lluvia": [0.5, 1.0],
            "preferencia_temperatura": [0.3, 0.7], "preferencia_fertilidad": [0.4, 0.9],
        },
    }
    resultado = colonizar_por_idoneidad(
        random.Random(7), todas, biomas_bosque, lluvia, temperatura,
        fertilidad, humedad, capacidad, especies, 0.2,
    )
    especies_vistas = set(resultado.values())
    assert especies_vistas == {"a", "b"}


RUTA_CONFIG = Path(__file__).resolve().parent.parent / "config"


def test_integracion_generacion_real_produce_celdas_vacias_y_pobladas():
    """Verificación contra el motor real, no solo la función aislada:
    genera una zona completa con la configuración real del proyecto y
    confirma que el resultado es físicamente coherente -- especies solo
    en su bioma declarado, y existen celdas legítimamente sin vegetación
    (idoneidad insuficiente en las 5 especies del catálogo actual)."""
    config = cargar_configuracion(RUTA_CONFIG)
    zona = generar_zona_bioma(
        random.Random(1),
        config["generacion_mapa"], config["bioma"], config["flora"], config["agua"],
        config["materiales"], config["sustrato_por_bioma"], config["umbrales_sustrato_fertil"],
        config["generacion_vetas"], 30, 30,
    )
    especies_validas = set(config["flora"]["especies"].keys())
    hay_vacias = False
    hay_pobladas = False
    for x, y, celda in zona.celdas():
        if celda.tiene_recurso:
            hay_pobladas = True
            assert celda.tipo_recurso in especies_validas
            assert celda.tipo_terreno.value in config["flora"]["especies"][celda.tipo_recurso]["biomas"]
        else:
            hay_vacias = True
    assert hay_pobladas
    assert hay_vacias
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_colonizacion.py -v`
Expected: FAIL con `ImportError: cannot import name 'colonizar_por_idoneidad'`.

- [ ] **Step 3: Implementar `colonizar_por_idoneidad` en `nucleo/flora.py`**

Añade `import random` como primera línea de imports del fichero (busca la línea `from __future__ import annotations` y añade justo debajo):

```python
from __future__ import annotations

import random

from typing import Any
```

(La línea `from typing import Any` ya existe tal cual justo después de `from __future__ import annotations` -- solo intercala la línea `import random` entre ambas.)

Añade esta función al final del fichero (después de `idoneidad_colonizacion`, que ya existe desde el plan 3):

```python
def colonizar_por_idoneidad(
    rng: random.Random,
    todas_las_celdas: set[tuple[int, int]],
    biomas: dict[tuple[int, int], Any],
    campo_lluvia: list,
    campo_temperatura: list,
    fertilidad_por_celda: dict[tuple[int, int], float],
    humedad_subsuelo_por_celda: dict[tuple[int, int], float],
    capacidad_retencion_por_celda: dict[tuple[int, int], float],
    especies_cfg: dict[str, Any],
    umbral_minimo: float,
) -> dict[tuple[int, int], str]:
    """Sustituye el reparto por proporción/mancha fijo en config
    (2026-09-01, ver docs/superpowers/specs/
    2026-09-01-distribucion-causal-flora-design.md): por cada celda,
    reúne las especies cuyo bioma declarado coincide con el de la celda
    (mismo filtro grueso de siempre), calcula su idoneidad_colonizacion y
    descarta las que no superan umbral_minimo. Entre las que quedan,
    sortea una ponderada por idoneidad -- no gana siempre la de mayor
    puntuación a rajatabla, ni la primera del catálogo por orden de
    aparición. Si ninguna especie supera el umbral, la celda no aparece
    en el resultado -- suelo desnudo, resultado real, no forzado."""
    especie_por_celda: dict[tuple[int, int], str] = {}
    for x, y in todas_las_celdas:
        bioma_celda = biomas[(x, y)]
        candidatas = [
            (nombre, cfg) for nombre, cfg in especies_cfg.items()
            if bioma_celda.value in cfg.get("biomas", [])
        ]
        if not candidatas:
            continue

        celda_temp = Celda(
            tipo_terreno=bioma_celda,
            lluvia=campo_lluvia[x][y],
            temperatura=campo_temperatura[x][y],
            fertilidad=fertilidad_por_celda[(x, y)],
            humedad_subsuelo=humedad_subsuelo_por_celda[(x, y)],
        )
        capacidad_retencion = capacidad_retencion_por_celda[(x, y)]

        nombres = []
        pesos = []
        for nombre, cfg in candidatas:
            idoneidad = idoneidad_colonizacion(cfg, celda_temp, capacidad_retencion)
            if idoneidad >= umbral_minimo:
                nombres.append(nombre)
                pesos.append(idoneidad)

        if nombres:
            especie_por_celda[(x, y)] = rng.choices(nombres, weights=pesos, k=1)[0]

    return especie_por_celda
```

- [ ] **Step 4: Ejecutar solo los tests unitarios (sin el de integración) y confirmar que pasan**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_colonizacion.py -v -k "not integracion"`
Expected: 4 tests PASS. El test de integración (`test_integracion_generacion_real_produce_celdas_vacias_y_pobladas`) seguirá fallando hasta el Step 7 -- todavía no hemos conectado `colonizar_por_idoneidad` a `generar_zona_bioma`.

- [ ] **Step 5: Eliminar el bloque de colonización por manchas en `nucleo/zona_bioma.py`**

Busca este bloque exacto (empieza justo después de `cuerpos_agua = generar_cuerpos_agua(...)`, termina justo antes de `sustrato_por_bioma = config_sustrato_por_bioma`):

```python
    cuerpos_agua = generar_cuerpos_agua(campo_elevacion, rng, config_agua, ancho, alto)

    # Flora (correccion posterior a fase terreno 4, discutida y
    # confirmada con Diego): cada especie del catalogo (config/
    # constantes.yaml, seccion flora.especies) coloniza una mancha DENTRO
    # de los biomas donde puede crecer -- mismo _generar_manchas de
    # siempre, ahora por especie en vez de por terreno fijo Claro/
    # Espesura. celdas_ya_asignadas se acumula entre especies para que
    # dos especies del MISMO bioma (hierba silvestre y manzano, ambas en
    # Bosque) no compitan por la misma celda -- el orden del catalogo
    # decide quien tiene primera opcion, sin ninguna razon ecologica
    # detras del orden, solo el orden de config/constantes.yaml.
    # CORRECCION 2026-08-20 (pedida por Diego: hierba tiene que ser "la
    # gran mayoria de la pradera" -- ver config/constantes.yaml,
    # flora.especies.hierba_silvestre.proporcion): antes se combinaban
    # TODOS los biomas compatibles de una especie en un unico conjunto de
    # candidatas y se aplicaba una sola proporcion escalar sobre ese
    # conjunto -- con una especie en dos biomas (hierba_silvestre en
    # pradera Y bosque), no habia forma de subir su abundancia en un
    # bioma sin subirla tambien en el otro (hierba va primera en el
    # catalogo, con primera opcion de celda sobre manzano en bosque).
    # Ahora se itera especie x bioma por separado, cada bioma con su
    # propio conjunto de candidatas y su propia proporcion -- proporcion
    # puede seguir siendo un escalar (aplicado igual a todos los biomas
    # de esa especie, comportamiento identico al de antes para cualquier
    # especie de un solo bioma) o un diccionario {bioma: proporcion} para
    # el caso -- hoy solo hierba_silvestre -- que necesita valores
    # distintos por bioma. celdas_por_mancha_objetivo se aplica tambien
    # POR bioma ahora, con el mismo escalar-o-diccionario que proporcion.
    #
    # CORRECCION 2026-08-23 (pedida por Diego, ver diagnostico de
    # inanicion del mismo dia): num_manchas era un CONTEO fijo por
    # especie, independiente del area del grid -- el mismo antipatron que
    # ya se sospecho (equivocadamente, esa vez) como causa de la
    # inanicion. Con num_manchas fijo, `objetivo` (que si escala con el
    # area, via candidatas) se repartia entre un numero constante de
    # manchas -- un mapa mas grande no generaba mas manchas, generaba
    # manchas mas grandes, degenerando en un unico "supercontinente"
    # dominante por especie (confirmado empiricamente: 500-975 de 1600
    # celdas en una sola mancha de hierba silvestre en el mapa 40x40
    # actual). Ahora el parametro fijo es celdas_por_mancha_objetivo (un
    # TAMANO de mancha, no un conteo), y num_manchas se DERIVA:
    # objetivo // celdas_por_mancha_objetivo. Es el numero de manchas el
    # que crece con el area del mapa, no su tamano individual -- un
    # prado mas grande tiene mas parches de hierba de tamano parecido, no
    # un parche unico cada vez mas grande. Valores de
    # celdas_por_mancha_objetivo calibrados para reproducir
    # aproximadamente el num_manchas de hoy en el mapa 40x40 actual (ver
    # config/constantes.yaml, seccion flora) -- ancla de continuidad, no
    # una recalibracion desde cero.
    especie_por_celda = {}
    celdas_ya_asignadas = set()
    for especie_key, especie_cfg in config_flora["especies"].items():
        proporcion_cfg = especie_cfg["proporcion"]
        celdas_por_mancha_cfg = especie_cfg["celdas_por_mancha_objetivo"]
        for bioma_nombre in especie_cfg["biomas"]:
            bioma = TipoTerreno(bioma_nombre)
            candidatas = {
                p for p in todas_las_celdas
                if biomas[p] == bioma and p not in celdas_ya_asignadas
            }
            proporcion = (
                proporcion_cfg[bioma_nombre] if isinstance(proporcion_cfg, dict) else proporcion_cfg
            )
            celdas_por_mancha = (
                celdas_por_mancha_cfg[bioma_nombre]
                if isinstance(celdas_por_mancha_cfg, dict)
                else celdas_por_mancha_cfg
            )
            objetivo = int(len(candidatas) * proporcion)
            num_manchas = max(1, round(objetivo / max(celdas_por_mancha, 1)))
            mancha = _generar_manchas(
                ancho, alto, rng,
                celdas_candidatas=candidatas,
                num_manchas=num_manchas,
                objetivo_absoluto=objetivo,
                prob_expansion=config_generacion["recurso_prob_expansion"],
            )
            for p in mancha:
                especie_por_celda[p] = especie_key
            celdas_ya_asignadas |= mancha

    sustrato_por_bioma = config_sustrato_por_bioma
```

Sustitúyelo por (conserva la primera y la última línea tal cual, elimina todo el bloque de flora que había entre medias):

```python
    cuerpos_agua = generar_cuerpos_agua(campo_elevacion, rng, config_agua, ancho, alto)

    sustrato_por_bioma = config_sustrato_por_bioma
```

- [ ] **Step 6: Añadir la pasada de humedad de subsuelo y la llamada a `colonizar_por_idoneidad`**

Busca este bloque exacto (justo después de la pasada de sustrato/fertilidad que el plan 4 ya dejó en su sitio):

```python
    celdas_piedra = {
        pos for pos, sustrato in tipo_sustrato_por_celda.items() if sustrato == "piedra"
    }
```

Sustitúyelo por (añade la pasada de humedad y la llamada a colonización ANTES de esta línea, sin tocar el resto):

```python
    # Humedad de subsuelo por celda (2026-09-01, ver docs/superpowers/
    # specs/2026-09-01-distribucion-causal-flora-design.md): antes se
    # calculaba inline dentro del bucle final de construcción de Celda --
    # se adelanta a una pasada propia porque la colonización de flora de
    # aquí abajo necesita esta señal ANTES de que exista ninguna Celda
    # todavía. Mismo cálculo exacto de siempre, solo cambia el momento.
    humedad_subsuelo_por_celda = {}
    capacidad_retencion_por_celda = {}
    for x in range(ancho):
        for y in range(alto):
            info_agua = cuerpos_agua.get((x, y))
            tiene_agua_celda = (info_agua.tipo if info_agua else "") != ""
            capacidad_retencion = float(
                catalogo_materiales.get(tipo_sustrato_por_celda[(x, y)], {}).get(
                    "capacidad_retencion", 0.0
                )
            )
            capacidad_retencion_por_celda[(x, y)] = capacidad_retencion
            humedad_subsuelo_por_celda[(x, y)] = capacidad_retencion if tiene_agua_celda else 0.0

    # Colonización de flora por idoneidad (2026-09-01): sustituye al
    # antiguo reparto por proporción/mancha -- cada celda decide qué
    # especie (si alguna) la coloniza según sustrato/fertilidad/lluvia/
    # temperatura reales, ya calculados arriba.
    especie_por_celda = colonizar_por_idoneidad(
        rng, todas_las_celdas, biomas, campo_lluvia, campo_temperatura,
        fertilidad_por_celda, humedad_subsuelo_por_celda, capacidad_retencion_por_celda,
        config_flora["especies"],
        float(config_flora.get("umbral_minimo_idoneidad_colonizacion", 0.2)),
    )

    celdas_piedra = {
        pos for pos, sustrato in tipo_sustrato_por_celda.items() if sustrato == "piedra"
    }
```

- [ ] **Step 7: Simplificar el cálculo inline de humedad en el bucle final**

Busca este bloque exacto (dentro del bucle final de construcción de `Celda`):

```python
            tipo_sustrato = tipo_sustrato_por_celda[(x, y)]
            deposito_mineral = vetas_minerales.get((x, y), "")
            masa_mineral_restante = masa_inicial_veta if deposito_mineral else 0.0
            capacidad_retencion = float(
                catalogo_materiales.get(tipo_sustrato, {}).get("capacidad_retencion", 0.0)
            )
            humedad_subsuelo = capacidad_retencion if tiene_agua else 0.0
```

Sustitúyelo por (la humedad ya se calculó en la pasada previa del Step 6, se reutiliza en vez de recalcularla):

```python
            tipo_sustrato = tipo_sustrato_por_celda[(x, y)]
            deposito_mineral = vetas_minerales.get((x, y), "")
            masa_mineral_restante = masa_inicial_veta if deposito_mineral else 0.0
            humedad_subsuelo = humedad_subsuelo_por_celda[(x, y)]
```

- [ ] **Step 8: Actualizar el import de `nucleo.flora` en `nucleo/zona_bioma.py`**

Busca:

```python
from nucleo.flora import recursos_alimento
```

Sustitúyela por:

```python
from nucleo.flora import colonizar_por_idoneidad, recursos_alimento
```

- [ ] **Step 9: Retirar `proporcion`/`celdas_por_mancha_objetivo` de `config/flora.yaml` y añadir el umbral mínimo**

Busca este bloque exacto (dentro de `flora.especies.hierba_silvestre`, incluye el comentario que documentaba estos dos campos -- se retira entero porque ya no describiría ningún campo presente):

```yaml
      # celdas_por_mancha_objetivo (2026-08-23, sustituye a num_manchas
      # fijo): tamaño de mancha objetivo en celdas, del que se DERIVA el
      # número de manchas (num_manchas_calculado = max(1, round(objetivo /
      # celdas_por_mancha_objetivo)), ver nucleo/zona_bioma.py) en vez de
      # al revés. Con num_manchas fijo, un mapa más grande no producía más
      # manchas -- producía manchas más grandes (objetivo crece con el
      # área, num_manchas no), degenerando en un único "supercontinente"
      # dominante por especie (confirmado empíricamente: 500-975 de 1600
      # celdas en una sola mancha de hierba en el mapa 40x40 actual). Con
      # el tamaño de mancha como parámetro fijo en su lugar, es el NÚMERO
      # de manchas el que crece con el área -- más parches de tamaño
      # similar en un mapa más grande, no menos parches gigantescos.
      # Valores calibrados para reproducir aproximadamente el num_manchas
      # de hoy en el mapa 40x40 actual (script de 5 semillas, ver
      # diagnóstico de inanición 2026-08-23) -- ancla de continuidad, no
      # una cifra recalibrada desde cero.
      celdas_por_mancha_objetivo:
        pradera: 180
        bosque: 12
      proporcion:
        pradera: 0.75
        bosque: 0.2
      tasa_crecimiento_por_dia: 0.25
```

Sustitúyelo por:

```yaml
      tasa_crecimiento_por_dia: 0.25
```

Busca en `manzano`:

```yaml
      celdas_por_mancha_objetivo: 10
      proporcion: 0.15
      tasa_crecimiento_por_dia: 0.08
```

Sustitúyelo por:

```yaml
      tasa_crecimiento_por_dia: 0.08
```

Busca en `cactus`:

```yaml
      celdas_por_mancha_objetivo: 3
      proporcion: 0.15
      tasa_crecimiento_por_dia: 0.05
```

Sustitúyelo por:

```yaml
      tasa_crecimiento_por_dia: 0.05
```

Busca en `liquen`:

```yaml
      celdas_por_mancha_objetivo: 12
      proporcion: 0.1
      tasa_crecimiento_por_dia: 0.03
```

Sustitúyelo por:

```yaml
      tasa_crecimiento_por_dia: 0.03
```

Busca en `musgo`:

```yaml
      celdas_por_mancha_objetivo: 4
      proporcion: 0.1
      tasa_crecimiento_por_dia: 0.03
```

Sustitúyelo por:

```yaml
      tasa_crecimiento_por_dia: 0.03
```

Por último, busca la línea `fraccion_siembra_inicial: 0.08` (dentro de la sección `flora:`, justo antes de `especies:`) y añade el umbral mínimo justo debajo:

```yaml
  fraccion_siembra_inicial: 0.08
  especies:
```

Sustitúyelo por:

```yaml
  fraccion_siembra_inicial: 0.08
  # umbral_minimo_idoneidad_colonizacion (2026-09-01, ver docs/superpowers/
  # specs/2026-09-01-distribucion-causal-flora-design.md): idoneidad
  # mínima (nucleo/flora.py:idoneidad_colonizacion) que una especie debe
  # superar para colonizar una celda -- por debajo, la celda se queda sin
  # vegetación en vez de forzar una especie que no encaja. PROVISIONAL,
  # sin calibrar contra el harness completo.
  umbral_minimo_idoneidad_colonizacion: 0.2
  especies:
```

- [ ] **Step 10: Ejecutar el test de este plan y confirmar que pasa por completo**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/test_flora_colonizacion.py -v`
Expected: 5 tests PASS (los 4 del Step 4 más el de integración).

- [ ] **Step 11: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && PYTHONPATH=. python3 -m pytest tests/ -q`
Expected: todos los tests existentes siguen en verde -- prestar atención especial a `tests/test_zona_bioma_fertilidad.py` (plan 4), que sigue pasando porque no depende de CÓMO se elige la especie, solo del sustrato/fertilidad, que este plan no toca.

- [ ] **Step 12: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add nucleo/flora.py nucleo/zona_bioma.py config/flora.yaml tests/test_flora_colonizacion.py
git commit -m "$(cat <<'EOF'
feat: ley de colonización de flora sustituye a proporción/mancha (flora 5/5)

colonizar_por_idoneidad decide qué especie (si alguna) coloniza cada
celda según sustrato/fertilidad/lluvia/temperatura reales -- sustituye
el reparto por proporción y tamaño de mancha fijados en config
(_generar_manchas sigue intacta, sigue siendo usada por vetas de
mineral). Una celda sin ninguna especie por encima del umbral queda sin
vegetación, resultado real. Cierra la distribución causal de flora
(docs/superpowers/specs/2026-09-01-distribucion-causal-flora-design.md).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01SqktCmrHLwNtu317aMKy29
EOF
)"
```
