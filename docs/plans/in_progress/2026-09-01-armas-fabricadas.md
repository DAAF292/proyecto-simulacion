# Armas fabricadas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Primer consumidor de `Agarre` distinto de sujetar en crudo: un gnomo consciente e inseguro puede fabricar un arma real (lanza desde madera, hacha_mano desde piedra) que refuerza su defensa frente a depredación, más allá del bono binario ya existente por sujetar cualquier objeto crudo.

**Architecture:** Sigue el patrón exacto ya establecido por `Accion.ENCENDER_FUEGO` (mismo círculo, un día antes): nueva `Accion.FABRICAR_ARMA` gateada por consciencia, con utilidad causal (`1.0 - Necesidades.seguridad`, mismo principio que `confort_termico` para el fuego), resuelta en un solo tick determinista que muta `Agarre.objetos` in situ (sin componente nuevo, sin cambio de esquema de persistencia). El efecto vive en `sistema_depredacion.py`, reforzando la reducción de probabilidad de captura ya existente por Agarre.

**Tech Stack:** Python 3, dataclasses puras para componentes ECS, YAML para configuración (`config/*.yaml`, fusionado por `main.py:cargar_configuracion`), pytest para las leyes puras testables, arneses ad hoc (no committeados) para verificación contra el motor real — mismo criterio que el resto de círculos de este proyecto (ver `CLAUDE.md`).

**Spec:** `docs/superpowers/specs/2026-09-01-armas-fabricadas-design.md`

## Global Constraints

- Alcance de efecto: SOLO defensa reforzada — sin bono ofensivo en caza, sin integración con `nucleo/conflicto.py`, en este círculo.
- Fabricar es exclusivo de especies conscientes (`cap_mental.consciencia >= decision.umbral_consciencia_agencia`) — instintivos (lobo/ardilla) siguen solo con el bono binario existente, sin cambios.
- Sin rama causal nueva en `RECOLECTAR` — el material crudo (madera/piedra) ya se agarra sin causa por el mecanismo genérico existente de Agarre.
- Nombre diferenciado por material (`madera → lanza`, `piedra → hacha_mano`), pero efecto numérico IDÉNTICO para ambas en este círculo.
- Materiales aptos para armas en este círculo: solo `madera` y `piedra`. `hierro`/`cobre` quedan fuera, reservados para un círculo futuro.
- Sin cambios de esquema de persistencia (`Agarre.objetos` ya se persiste como lista de strings).
- `reduccion_prob_captura_por_arma_fabricada` es PROVISIONAL — valor de partida 0.2 (frente al 0.1 ya existente de `reduccion_prob_captura_por_agarre`).

---

## File Structure

- `componentes/intencion.py` — nuevo miembro `Accion.FABRICAR_ARMA` en el enum ya existente.
- `config/materiales.yaml` — nueva propiedad `apto_arma: true` en las entradas `madera` y `piedra`; nueva sección `armas.nombre_arma_por_material`.
- `config/combate.yaml` — nueva constante `depredacion.reduccion_prob_captura_por_arma_fabricada`.
- `sistemas/sistema_decision.py` — nueva función pura `_utilidad_fabricar_arma`, cableada en `actualizar()`.
- `sistemas/sistema_recursos.py` — nuevo método `_resolver_fabricar_arma`, cableado en `ejecutar()`.
- `sistemas/sistema_depredacion.py` — `_resolver_ataque` gana la rama reforzada de reducción por arma fabricada.
- `tests/test_fabricar_arma.py` — nuevo, tests puros de `_utilidad_fabricar_arma` (mismo estilo "ley física" que `test_agua.py`/`test_bioma.py`/`test_orografia.py`).
- `CLAUDE.md` — nueva sección de cierre de círculo, con los números reales observados en la Task 4.

---

### Task 1: `Accion.FABRICAR_ARMA` y su utilidad causal

**Files:**
- Modify: `componentes/intencion.py`
- Modify: `config/materiales.yaml`
- Modify: `sistemas/sistema_decision.py`
- Test: `tests/test_fabricar_arma.py`

**Interfaces:**
- Produces: `Accion.FABRICAR_ARMA` (enum member, valor `"fabricar_arma"`).
- Produces: `_utilidad_fabricar_arma(cap_mental: CapacidadMental, necesidades: Necesidades, agarre: Agarre | None, umbral_consciencia_agencia: float, catalogo_materiales: dict, nombres_arma_fabricada: set[str]) -> float`, función pura de módulo en `sistemas/sistema_decision.py` — consumida por Task 4 indirectamente (verificación de motor real) y por cualquier círculo futuro que quiera razonar sobre esta utilidad sin reimplementarla.
- Consumes: `Agarre` (`componentes/agarre.py`, ya existe — campo `objetos: list[str]`), `CapacidadMental.consciencia`, `Necesidades.seguridad` (ya existen).

- [ ] **Step 1: Escribir el test que falla**

Crea `tests/test_fabricar_arma.py`:

```python
"""Tests de la ley de utilidad de FABRICAR_ARMA (primer círculo del arco
herramientas/utensilios/armas, 2026-09-01).

_utilidad_fabricar_arma es una función pura: dado el estado de
consciencia, seguridad y Agarre de un individuo, decide si vale la pena
fabricar un arma. La ley que valida este archivo es CAUSAL, no solo
mecánica: un individuo que nunca ha sentido inseguridad real no debe
desarrollar interés en fabricar un arma aunque tenga material crudo
sujeto -- mismo principio que la corrección de piedra suelta para el
fuego (ver CLAUDE.md).
"""
import pytest

from componentes.agarre import Agarre
from componentes.capacidad_mental import CapacidadMental
from componentes.necesidades import Necesidades
from sistemas.sistema_decision import _utilidad_fabricar_arma

UMBRAL_CONSCIENCIA = 0.3
CATALOGO = {
    "madera": {"apto_arma": True},
    "piedra": {"apto_arma": True},
    "arcilla": {"apto_arma": False},
}
NOMBRES_ARMA = {"lanza", "hacha_mano"}


def _cap_mental(consciencia: float) -> CapacidadMental:
    return CapacidadMental(
        inteligencia=0.5, memoria=0.5, voluntad=0.5,
        resiliencia=0.5, estabilidad_mental_maxima=0.5,
        consciencia=consciencia,
    )


def test_sin_consciencia_nunca_fabrica():
    """Un individuo por debajo del umbral de agencia consciente nunca
    tiene utilidad de fabricar arma, aunque tenga material y esté inseguro."""
    cap = _cap_mental(0.1)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_sin_inseguridad_nunca_desarrolla_interes():
    """LEY CAUSAL: un individuo consciente con material crudo sujeto pero
    que nunca ha sentido inseguridad (seguridad=1.0) tiene utilidad 0 --
    mismo principio que la corrección de piedra suelta para el fuego."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=1.0)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_consciente_inseguro_con_material_fabrica():
    """Consciente + inseguro + material crudo apto -> utilidad real,
    igual a 1.0 - seguridad."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.2)
    agarre = Agarre(objetos=["madera"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == pytest.approx(0.8)


def test_sin_material_apto_no_fabrica():
    """Consciente e inseguro pero sin ningún material apto_arma sujeto
    (solo arcilla, que no es apto_arma) -> utilidad 0."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["arcilla"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_ya_con_arma_fabricada_no_vuelve_a_fabricar():
    """Si ya tiene un arma fabricada sujeta (lanza), la utilidad cae a 0
    aunque siga inseguro -- no fabrica una segunda."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    agarre = Agarre(objetos=["lanza"])
    utilidad = _utilidad_fabricar_arma(
        cap, nec, agarre, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0


def test_sin_agarre_no_fabrica():
    """Una entidad sin componente Agarre (no debería ocurrir en la
    práctica -- las cuatro especies lo tienen -- pero la función debe ser
    robusta) nunca fabrica."""
    cap = _cap_mental(0.9)
    nec = Necesidades(seguridad=0.1)
    utilidad = _utilidad_fabricar_arma(
        cap, nec, None, UMBRAL_CONSCIENCIA, CATALOGO, NOMBRES_ARMA
    )
    assert utilidad == 0.0
```

- [ ] **Step 2: Ejecutar el test y confirmar que falla**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_fabricar_arma.py -v`
Expected: `ImportError` o `ModuleNotFoundError` / `ImportError: cannot import name '_utilidad_fabricar_arma'` — la función no existe todavía.

- [ ] **Step 3: Añadir `Accion.FABRICAR_ARMA` al enum**

En `componentes/intencion.py`, justo después de la línea `ENCENDER_FUEGO = "encender_fuego"` (y antes del comentario `# Bloque F3 (crisis mental...`), inserta:

```python
    # FABRICAR_ARMA (2026-09-01, primer círculo del arco herramientas/
    # utensilios/armas -- ver componentes/agarre.py, config/materiales.yaml
    # sección 'armas' y la conversación de diseño con Diego: "un palo para
    # defenderse, o una roca... hachas utensilios"). Misma compuerta de
    # consciencia que CONSTRUIR/RECOLECTAR/ENCENDER_FUEGO. Utilidad = 1.0 -
    # Necesidades.seguridad, mismo patrón causal que ENCENDER_FUEGO con
    # confort_termico -- responde a una necesidad real (sentirse inseguro),
    # no a un objetivo administrativo. Gateada a 0.0 si ya tiene un arma
    # fabricada en Agarre, o si no tiene ningún material apto_arma
    # (madera/piedra) sujeto todavía. A diferencia de ENCENDER_FUEGO, NO
    # empuja RECOLECTAR -- el material crudo ya se agarra sin causa por el
    # mecanismo genérico de Agarre. Sin desplazamiento (como RECOLECTAR/
    # ENCENDER_FUEGO) -- se resuelve donde ya se esté.
    FABRICAR_ARMA = "fabricar_arma"
```

- [ ] **Step 4: Añadir `apto_arma` y la sección `armas` a `config/materiales.yaml`**

En la entrada `madera:` (dentro de `materiales:`), añade la línea `apto_arma: true` justo después de `apto_construccion: true`:

```yaml
  madera:
    categoria: organico_vegetal
    forma_en_mundo: deposito
    densidad_kg_m3: 700
    dureza: 0.45
    combustibilidad: 0.55
    tasa_descomposicion_dia: 0.01
    apto_construccion: true
    # apto_arma (2026-09-01, primer círculo del arco herramientas/
    # utensilios/armas): una lanza tallada de un palo de madera.
    apto_arma: true
```

En la entrada `piedra:` (arriba del todo, sección "Sustrato de terreno"), añade la misma propiedad después de `apto_construccion: true`:

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
    # apto_arma (2026-09-01, primer círculo del arco herramientas/
    # utensilios/armas): una piedra tallada como hacha de mano.
    apto_arma: true
```

Al final del fichero (después de la sección `construccion:`), añade una nueva sección de nivel superior:

```yaml
# --- Armas fabricadas (2026-09-01, primer círculo del arco herramientas/
# utensilios/armas) -----------------------------------------------------
# Qué materiales sirven para fabricar un arma simple (apto_arma, arriba en
# cada entrada del catálogo -- madera y piedra por ahora; hierro/cobre
# quedan fuera, reservados para un círculo futuro de armas metálicas) y
# qué nombre recibe el arma fabricada a partir de cada uno. Efecto
# idéntico para ambas en este círculo (ver config/combate.yaml,
# reduccion_prob_captura_por_arma_fabricada) -- el nombre distinto no
# cambia nada mecánico todavía, solo deja la puerta abierta para un
# círculo futuro que sí diferencie por tipo de arma.
armas:
  nombre_arma_por_material:
    madera: lanza
    piedra: hacha_mano
```

- [ ] **Step 5: Implementar `_utilidad_fabricar_arma` y cablearla en `actualizar()`**

En `sistemas/sistema_decision.py`, añade esta función de módulo justo después de `_tipo_crisis` y antes de `class SistemaDecision:`:

```python
def _utilidad_fabricar_arma(
    cap_mental: CapacidadMental,
    necesidades: Necesidades,
    agarre: Agarre | None,
    umbral_consciencia_agencia: float,
    catalogo_materiales: dict,
    nombres_arma_fabricada: set[str],
) -> float:
    """Utilidad de FABRICAR_ARMA -- 1.0 - seguridad, mismo patrón causal
    que ENCENDER_FUEGO con confort_termico (ver docstring del módulo y
    componentes/intencion.py). Devuelve 0.0 si no es consciente, si ya
    tiene un arma fabricada sujeta, o si no tiene ningún material
    apto_arma en crudo sujeto todavía."""
    if cap_mental.consciencia < umbral_consciencia_agencia:
        return 0.0
    if agarre is None:
        return 0.0
    if any(obj in nombres_arma_fabricada for obj in agarre.objetos):
        return 0.0
    tiene_material_crudo = any(
        catalogo_materiales.get(obj, {}).get("apto_arma", False)
        for obj in agarre.objetos
    )
    if not tiene_material_crudo:
        return 0.0
    return 1.0 - necesidades.seguridad
```

Dentro de `actualizar()`, justo después de la línea:
```python
    piedras_necesarias_fuego = int(config.get("fuego", {}).get("piedras_necesarias", 2))
```
añade:
```python
    # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
    # config/materiales.yaml sección 'armas' y sistema_decision.py:
    # _utilidad_fabricar_arma).
    config_armas = config.get("armas", {})
    nombre_arma_por_material: dict[str, str] = config_armas.get("nombre_arma_por_material", {})
    nombres_arma_fabricada = set(nombre_arma_por_material.values())
```

Dentro del bucle `for id_entidad in gestor.entidades_con(...)`, justo después del bloque completo de `utilidad_encender_fuego` (después de la línea `utilidad_encender_fuego = 1.0 - necesidades.confort_termico` y su cierre de `if`/`else`, antes de la línea `candidatas = (`), añade:

```python
        # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
        # config/materiales.yaml sección 'armas' y el docstring del
        # módulo). Mismo patrón causal que ENCENDER_FUEGO -- ver
        # _utilidad_fabricar_arma arriba.
        agarre = gestor.obtener_componente(id_entidad, Agarre)
        utilidad_fabricar_arma = _utilidad_fabricar_arma(
            cap_mental,
            necesidades,
            agarre,
            umbral_consciencia_agencia,
            catalogo_materiales,
            nombres_arma_fabricada,
        )
```

Y en la tupla `candidatas`, añade `(utilidad_fabricar_arma, Accion.FABRICAR_ARMA),` justo después de `(utilidad_encender_fuego, Accion.ENCENDER_FUEGO),` y antes de `(base_deambular, Accion.DEAMBULAR),`.

- [ ] **Step 6: Ejecutar el test y confirmar que pasa**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/test_fabricar_arma.py -v`
Expected: 6 tests PASS.

- [ ] **Step 7: Ejecutar toda la suite para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `28 passed` (22 existentes + 6 nuevos).

- [ ] **Step 8: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add componentes/intencion.py config/materiales.yaml sistemas/sistema_decision.py tests/test_fabricar_arma.py
git commit -m "$(cat <<'EOF'
Armas fabricadas: Accion.FABRICAR_ARMA y su utilidad causal

Primer círculo del arco herramientas/utensilios/armas. Mismo patrón
causal que ENCENDER_FUEGO -- utilidad = 1.0 - Necesidades.seguridad, un
individuo que nunca ha sentido inseguridad real no desarrolla interés en
fabricar un arma. Sin rama causal nueva en RECOLECTAR: el material crudo
(madera/piedra) ya se agarra sin causa por el mecanismo genérico
existente de Agarre.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LxmziiZgNCXSFcf1311t4M
EOF
)"
```

---

### Task 2: Resolución — `_resolver_fabricar_arma`

**Files:**
- Modify: `sistemas/sistema_recursos.py`

**Interfaces:**
- Consumes: `Accion.FABRICAR_ARMA` (Task 1), `Agarre` (`componentes/agarre.py`), `config["armas"]["nombre_arma_por_material"]` (Task 1), `self.catalogo_materiales` (ya existe en `_cachear_configuracion`).
- Produces: `SistemaRecursos._resolver_fabricar_arma(self, agarre: Agarre | None, entidad_id: int, pos_x: int, pos_y: int, zona_idx: int, bus_eventos: BusEventos, tick_actual: int) -> None` — muta `agarre.objetos` in situ; emite Evento `"ArmaFabricada"`.

- [ ] **Step 1: Cachear `nombre_arma_por_material`**

En `sistemas/sistema_recursos.py`, dentro de `_cachear_configuracion`, justo después de la línea:
```python
        self.piedras_necesarias_fuego: int = int(cfg_fuego.get("piedras_necesarias", 2))
```
añade:
```python
        # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
        # config/materiales.yaml sección 'armas' y
        # sistema_decision.py:_utilidad_fabricar_arma).
        self.nombre_arma_por_material: dict[str, str] = self.config.get("armas", {}).get(
            "nombre_arma_por_material", {}
        )
```

- [ ] **Step 2: Implementar `_resolver_fabricar_arma`**

Añade este método a la clase `SistemaRecursos`, justo después de `_resolver_encender_fuego` (antes de `_consumir_fogatas`):

```python
    def _resolver_fabricar_arma(
        self,
        agarre: Agarre | None,
        entidad_id: int,
        pos_x: int,
        pos_y: int,
        zona_idx: int,
        bus_eventos: BusEventos,
        tick_actual: int,
    ) -> None:
        """
        FABRICAR_ARMA -- primer círculo del arco herramientas/utensilios/
        armas (2026-09-01, ver componentes/agarre.py, config/materiales.yaml
        sección 'armas' y sistema_decision.py:_utilidad_fabricar_arma). Un
        solo tick, determinista -- a diferencia de ENCENDER_FUEGO, tallar
        un palo o afilar una piedra no es un evento de azar equivalente a
        que prenda una chispa. Busca el primer objeto en Agarre.objetos
        cuyo material sea apto_arma y lo sustituye IN SITU por su nombre
        de arma (nombre_arma_por_material) -- mismo slot de la lista, no
        toca Inventario ni capacidad de carga. sistema_decision.py ya
        comprobó las precondiciones (consciente, material crudo presente,
        sin arma ya fabricada) antes de elegir esta Accion.
        """
        if agarre is None:
            return
        for indice, objeto in enumerate(agarre.objetos):
            info = self.catalogo_materiales.get(objeto, {})
            if not info.get("apto_arma", False):
                continue
            nombre_arma = self.nombre_arma_por_material.get(objeto)
            if not nombre_arma:
                continue
            agarre.objetos[indice] = nombre_arma
            bus_eventos.emitir(
                Evento(
                    tipo="ArmaFabricada",
                    severidad=Severidad.NOTABLE,
                    tick=tick_actual,
                    entidad_id=entidad_id,
                    datos={"x": pos_x, "y": pos_y, "zona_idx": zona_idx, "arma": nombre_arma},
                )
            )
            return
```

- [ ] **Step 3: Cablear el despacho en `ejecutar()`**

En `sistemas/sistema_recursos.py`, dentro de `ejecutar()`, justo después del bloque:
```python
            elif intencion.accion == Accion.ENCENDER_FUEGO:
                self._resolver_encender_fuego(
                    gestor, celda, pos.x, pos.y, pos.zona_idx, bus_eventos, reloj.tick_actual
                )
```
añade:
```python
            elif intencion.accion == Accion.FABRICAR_ARMA:
                agarre = gestor.obtener_componente(eid, Agarre)
                self._resolver_fabricar_arma(
                    agarre, eid, pos.x, pos.y, pos.zona_idx, bus_eventos, reloj.tick_actual
                )
```

- [ ] **Step 4: Escribir y ejecutar el arnés de verificación (no se commitea)**

Crea `/tmp/verificar_fabricar_arma.py`:

```python
"""Arnes de verificacion manual, NO forma parte del repositorio -- mismo
criterio que verificar_agarre.py y el resto de arneses de este proyecto
(ver CLAUDE.md). Se ejecuta una vez y se descarta."""
import random
import sys
from pathlib import Path

sys.path.insert(0, "/home/diego/proyecto-simulacion")

from componentes.agarre import Agarre
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from sistemas.sistema_recursos import SistemaRecursos

config = cargar_configuracion(Path("/home/diego/proyecto-simulacion/config"))
sr = SistemaRecursos(config, random.Random(1))
bus = BusEventos()

gestor = GestorEntidades()
eid = gestor.crear_entidad()
agarre = Agarre(objetos=["arcilla", "madera"])
gestor.anadir_componente(eid, agarre)

sr._resolver_fabricar_arma(agarre, eid, 5, 5, 0, bus, 100)
assert agarre.objetos == ["arcilla", "lanza"], agarre.objetos
assert len(bus.eventos_del_tick) == 1
ev = bus.eventos_del_tick[0]
assert ev.tipo == "ArmaFabricada"
assert ev.datos["arma"] == "lanza"
print("OK: madera -> lanza, resto intacto, evento emitido")

agarre2 = Agarre(objetos=["piedra"])
bus.limpiar()
sr._resolver_fabricar_arma(agarre2, eid, 5, 5, 0, bus, 101)
assert agarre2.objetos == ["hacha_mano"], agarre2.objetos
print("OK: piedra -> hacha_mano")

agarre3 = Agarre(objetos=["arcilla"])
bus.limpiar()
sr._resolver_fabricar_arma(agarre3, eid, 5, 5, 0, bus, 102)
assert agarre3.objetos == ["arcilla"]
assert len(bus.eventos_del_tick) == 0
print("OK: sin material apto, sin cambios")

print("VERIFICACION TASK 2: TODO OK")
```

Run: `python3 /tmp/verificar_fabricar_arma.py`
Expected: las tres líneas `OK:` y `VERIFICACION TASK 2: TODO OK`, sin `AssertionError`.

- [ ] **Step 5: Ejecutar la suite completa para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `28 passed`.

- [ ] **Step 6: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add sistemas/sistema_recursos.py
git commit -m "$(cat <<'EOF'
Armas fabricadas: resolución de FABRICAR_ARMA

_resolver_fabricar_arma sustituye in situ el primer material apto_arma
sujeto en Agarre.objetos por su nombre de arma (madera -> lanza, piedra
-> hacha_mano), un solo tick, determinista. Emite Evento ArmaFabricada.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LxmziiZgNCXSFcf1311t4M
EOF
)"
```

---

### Task 3: Efecto reforzado en combate

**Files:**
- Modify: `config/combate.yaml`
- Modify: `sistemas/sistema_depredacion.py`

**Interfaces:**
- Consumes: `Agarre.objetos` conteniendo `"lanza"` o `"hacha_mano"` (Task 2), `config["armas"]["nombre_arma_por_material"]` (Task 1).
- Produces: `SistemaDepredacion.reduccion_prob_captura_por_arma_fabricada: float` (nuevo atributo cacheado); lógica reforzada en `_resolver_ataque` — sin cambio de firma pública.

- [ ] **Step 1: Añadir la constante a `config/combate.yaml`**

Justo después de la línea `reduccion_prob_captura_por_agarre: 0.1` (y su bloque de comentario ya existente), añade:

```yaml
  # reduccion_prob_captura_por_arma_fabricada (2026-09-01, primer círculo
  # del arco herramientas/utensilios/armas -- ver componentes/agarre.py,
  # sistema_decision.py:_utilidad_fabricar_arma y sistema_recursos.py:
  # _resolver_fabricar_arma). Reducción REFORZADA cuando la presa tiene
  # un arma FABRICADA ("lanza" o "hacha_mano") en vez de un objeto crudo
  # cualquiera -- sustituye a reduccion_prob_captura_por_agarre en ese
  # caso, no se suma a ella. Mismo efecto numérico para ambos tipos de
  # arma en este círculo, pese al nombre distinto (deliberado, ver spec).
  # PROVISIONAL, sin calibrar contra el motor en marcha.
  reduccion_prob_captura_por_arma_fabricada: 0.2
```

- [ ] **Step 2: Cachear la constante y el conjunto de nombres de arma**

En `sistemas/sistema_depredacion.py`, dentro de `_cachear_configuracion`, justo después de:
```python
        self.reduccion_prob_captura_por_agarre: float = float(
            cfg_dep.get("reduccion_prob_captura_por_agarre", 0.1)
        )
```
añade:
```python
        # FABRICAR_ARMA (2026-09-01, ver componentes/agarre.py,
        # sistema_decision.py:_utilidad_fabricar_arma y
        # sistema_recursos.py:_resolver_fabricar_arma).
        self.reduccion_prob_captura_por_arma_fabricada: float = float(
            cfg_dep.get("reduccion_prob_captura_por_arma_fabricada", 0.2)
        )
        self.nombres_arma_fabricada: set[str] = set(
            self.config.get("armas", {}).get("nombre_arma_por_material", {}).values()
        )
```

- [ ] **Step 3: Reforzar la reducción en `_resolver_ataque`**

Sustituye el bloque:
```python
        # AGARRE -- primer efecto real (2026-08-31, ver componentes/agarre.py
        # y conversación de diseño con Diego: "un palo para defenderse, o
        # una roca"). Binario por ahora: tener algo sujeto reduce la
        # probabilidad de captura, sin escalar por cuántos puntos de
        # agarre estén llenos ni por qué material sea -- primera pasada
        # deliberadamente simple.
        if agarre_presa is not None and len(agarre_presa.objetos) > 0:
            prob_exito -= self.reduccion_prob_captura_por_agarre
```
por:
```python
        # AGARRE -- primer efecto real (2026-08-31, ver componentes/agarre.py
        # y conversación de diseño con Diego: "un palo para defenderse, o
        # una roca"). REFORZADO (2026-09-01, ver componentes/agarre.py y
        # sistema_recursos.py:_resolver_fabricar_arma): un arma FABRICADA
        # ("lanza"/"hacha_mano") reduce la probabilidad de captura más que
        # un objeto crudo cualquiera -- sustituye la reducción binaria, no
        # se suma a ella. Efecto todavía binario dentro de cada categoría
        # (crudo vs. fabricada), sin escalar por cantidad ni diferenciar
        # lanza de hacha_mano -- primera pasada deliberadamente simple.
        if agarre_presa is not None and any(
            obj in self.nombres_arma_fabricada for obj in agarre_presa.objetos
        ):
            prob_exito -= self.reduccion_prob_captura_por_arma_fabricada
        elif agarre_presa is not None and len(agarre_presa.objetos) > 0:
            prob_exito -= self.reduccion_prob_captura_por_agarre
```

- [ ] **Step 4: Escribir y ejecutar el arnés estadístico de verificación (no se commitea)**

Crea `/tmp/verificar_efecto_arma.py`:

```python
"""Arnes de verificacion manual, NO forma parte del repositorio -- mismo
criterio que el resto de arneses de este proyecto (ver CLAUDE.md). Se
ejecuta una vez y se descarta. Mismo metodo estadistico que ya se uso
para verificar el efecto original de Agarre (ver CLAUDE.md, circulo
'Agarre', 2026-08-31): peso cazador=30 / presa=3 da una disposicion base
~0.697 (log(10)/(1+log(10))), comodamente lejos de los topes
captura_prob_min=0.15/captura_prob_max=0.85, para que la reduccion no
sature."""
import random
import sys
from pathlib import Path

sys.path.insert(0, "/home/diego/proyecto-simulacion")

from componentes.agarre import Agarre
from componentes.dimensiones_fisicas import DimensionesFisicas
from componentes.identidad import Especie, Identidad
from componentes.necesidades import Necesidades
from componentes.pool_fisico import PoolFisico
from componentes.temperamento import Temperamento
from main import cargar_configuracion
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from sistemas.sistema_depredacion import SistemaDepredacion

config = cargar_configuracion(Path("/home/diego/proyecto-simulacion/config"))


def construir_par(gestor, objetos_presa):
    cazador = gestor.crear_entidad()
    presa = gestor.crear_entidad()
    gestor.anadir_componente(cazador, DimensionesFisicas(
        peso=30.0, fuerza=0.7, agilidad=0.5, vitalidad_maxima=0.6,
        resistencia_maxima=0.6, curacion=0.1, recuperacion=0.1,
        altura=0.6, longevidad=10.0, velocidad=0.5,
        resistencia_enfermedad=0.5, agudeza_sensorial=0.5,
    ))
    gestor.anadir_componente(presa, DimensionesFisicas(
        peso=3.0, fuerza=0.3, agilidad=0.5, vitalidad_maxima=0.4,
        resistencia_maxima=0.4, curacion=0.1, recuperacion=0.1,
        altura=0.3, longevidad=5.0, velocidad=0.5,
        resistencia_enfermedad=0.5, agudeza_sensorial=0.5,
    ))
    gestor.anadir_componente(cazador, Temperamento(
        valentia=0.5, sociabilidad=0.0, agresividad=0.5, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.0, curiosidad=0.5,
    ))
    gestor.anadir_componente(presa, Temperamento(
        valentia=0.5, sociabilidad=0.0, agresividad=0.5, dominancia=0.5,
        empatia=0.5, lealtad=0.5, fe=0.0, curiosidad=0.5,
    ))
    gestor.anadir_componente(presa, PoolFisico(vitalidad=1.0, resistencia=1.0))
    gestor.anadir_componente(presa, Agarre(objetos=list(objetos_presa)))
    gestor.anadir_componente(cazador, Necesidades())
    gestor.anadir_componente(cazador, Identidad(especie=Especie.LOBO, tick_nacimiento=0))
    gestor.anadir_componente(presa, Identidad(especie=Especie.CONEJO, tick_nacimiento=0))
    return cazador, presa


def tasa_exito(objetos_presa, n=1000, semilla_base=1):
    exitos = 0
    for i in range(n):
        gestor = GestorEntidades()
        sd = SistemaDepredacion(config, random.Random(semilla_base * 100000 + i))
        bus = BusEventos()
        cazador, presa = construir_par(gestor, objetos_presa)
        if sd._resolver_ataque(gestor, bus, cazador, presa, 0, 0, 0):
            exitos += 1
    return exitos / n


t_desarmada = tasa_exito([], semilla_base=1)
t_cruda = tasa_exito(["madera"], semilla_base=2)
t_armada = tasa_exito(["lanza"], semilla_base=3)

print(f"desarmada={t_desarmada:.3f} cruda={t_cruda:.3f} armada={t_armada:.3f}")
diff_cruda = t_desarmada - t_cruda
diff_armada = t_desarmada - t_armada
cfg_dep = config["depredacion"]
print(f"reduccion cruda={diff_cruda:.3f} (config={cfg_dep['reduccion_prob_captura_por_agarre']})")
print(f"reduccion armada={diff_armada:.3f} (config={cfg_dep['reduccion_prob_captura_por_arma_fabricada']})")

assert t_cruda < t_desarmada, "objeto crudo deberia reducir exito respecto a desarmada"
assert t_armada < t_cruda, "arma fabricada deberia reducir exito MAS que objeto crudo"
print("VERIFICACION TASK 3: TODO OK")
```

Run: `python3 /tmp/verificar_efecto_arma.py`
Expected: `desarmada > cruda > armada` en las tres tasas impresas, ambos `assert` sin fallar, y `VERIFICACION TASK 3: TODO OK`.

- [ ] **Step 5: Ejecutar la suite completa para confirmar que no hay regresión**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `28 passed`.

- [ ] **Step 6: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add config/combate.yaml sistemas/sistema_depredacion.py
git commit -m "$(cat <<'EOF'
Armas fabricadas: efecto reforzado en defensa

Un arma fabricada (lanza/hacha_mano) reduce la probabilidad de captura
más que un objeto crudo cualquiera -- sustituye la reducción binaria
existente, no se suma a ella. Verificado estadísticamente (1000 ataques
por escenario): desarmada > objeto crudo > arma fabricada.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LxmziiZgNCXSFcf1311t4M
EOF
)"
```

---

### Task 4: Verificación contra el motor real y cierre de círculo

**Files:**
- Test: arnés de motor real (no se commitea)
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: todo lo producido en Tasks 1-3 — ninguna interfaz nueva.

- [ ] **Step 1: Escribir y ejecutar el arnés de motor real (no se commitea)**

Crea `/tmp/verificar_armas_motor_real.py`:

```python
"""Arnes de verificacion de motor real, NO forma parte del repositorio --
mismo patron que diagnostico_poblacion.py (ver CLAUDE.md, circulo de
sobrepoblacion): corre main.py real sin persistencia SQLite persistente
(usa un fichero temporal descartable por semilla), sembrando poblacion y
flora reales, ejecutando el pipeline completo tick a tick, sin ninguna
intervencion manual sobre Agarre/Necesidades. Se ejecuta una vez y se
descarta."""
import random
import sys
from pathlib import Path

sys.path.insert(0, "/home/diego/proyecto-simulacion")

from componentes.agarre import Agarre
from main import (
    cargar_configuracion,
    ejecutar_tick,
    instanciar_sistemas,
    sembrar_flora_inicial,
    sembrar_poblacion_inicial,
)
from nucleo.entidad import GestorEntidades
from nucleo.eventos import BusEventos
from nucleo.mundo import Mundo
from nucleo.persistencia import Persistencia
from nucleo.reloj import Reloj

BASE = Path("/home/diego/proyecto-simulacion")
config = cargar_configuracion(BASE / "config")


def correr(semilla: int, ticks: int) -> dict:
    rng_mapa = random.Random(semilla)
    rng_juego = random.Random(semilla)
    reloj = Reloj()
    bus = BusEventos()
    gestor = GestorEntidades()
    persistencia = Persistencia(Path(f"/tmp/verificar_armas_{semilla}.db"))
    ancho = int(config.get("mundo", {}).get("grid_ancho", 40))
    alto = int(config.get("mundo", {}).get("grid_alto", 40))
    mundo = Mundo(ancho, alto, config, rng_mapa)
    sembrar_poblacion_inicial(gestor, mundo, config, rng_juego, persistencia)
    sembrar_flora_inicial(gestor, mundo, config, rng_juego)
    sistemas = instanciar_sistemas(config, rng_juego)

    armas_fabricadas = 0
    for _ in range(ticks):
        ejecutar_tick(gestor, mundo, reloj, bus, sistemas)
        for ev in bus.eventos_del_tick:
            if ev.tipo == "ArmaFabricada":
                armas_fabricadas += 1
        bus.limpiar()

    con_arma = 0
    for eid in gestor.entidades_con(Agarre):
        agarre = gestor.obtener_componente(eid, Agarre)
        if any(o in ("lanza", "hacha_mano") for o in agarre.objetos):
            con_arma += 1

    return {"semilla": semilla, "eventos_arma": armas_fabricadas, "individuos_con_arma": con_arma}


for semilla in (42, 1, 7, 99):
    print(correr(semilla, 3000))

print("VERIFICACION TASK 4: motor real completada")
```

Run: `python3 /tmp/verificar_armas_motor_real.py`
Expected: cuatro líneas de resultado (una por semilla) sin ninguna excepción, y `VERIFICACION TASK 4: motor real completada`. Anota los números reales de `eventos_arma` e `individuos_con_arma` por semilla — se usan en el Step 3.

Si las cuatro semillas dan `eventos_arma == 0`, NO continúes al Step 3 dando el círculo por cerrado: investiga primero (mismo patrón que el hallazgo real de "piedra suelta" en el círculo de fuego, donde la precondición resultó casi inalcanzable en juego normal) y decide si hace falta un ajuste antes de documentar.

- [ ] **Step 2: Confirmar que la suite completa de tests sigue en verde**

Run: `cd /home/diego/proyecto-simulacion && python3 -m pytest tests/ -q`
Expected: `28 passed`.

- [ ] **Step 3: Documentar el cierre del círculo en `CLAUDE.md`**

Añade una nueva sección al final de `CLAUDE.md` (después de la última sección existente, "Fuego controlado (Fogata)..." / "Piedra suelta..."), siguiendo el mismo estilo narrativo que el resto del documento (título con fecha, decisiones de diseño, implementación, verificación con números REALES de Step 1, pendiente explícito). Usa esta plantilla, sustituyendo `<N>` por los números reales observados:

```markdown
## Armas fabricadas -- primer círculo del arco herramientas/utensilios/
## armas, sobre el cimiento de Agarre y el patrón causal de fuego (2026-09-01)

Retomado el arco que Diego planteó al cerrar el círculo de fuego
("herramientas básicas, hachas utensilios"). Brainstorming con Diego
(spec completa en `docs/superpowers/specs/2026-09-01-armas-fabricadas-design.md`)
decidió: "herramientas, utensilios y armas" son 2-3 subsistemas
independientes, no uno -- este círculo cubre solo armas simples
fabricadas, por no depender de nada que falte todavía y por tener ya un
punto de enganche real (`reduccion_prob_captura_por_agarre`).

**Decisiones cerradas con Diego**: fabricar un arma es un acto consciente
distinto de sujetar un objeto en crudo (mismo umbral
`umbral_consciencia_agencia` que CONSTRUIR/RECOLECTAR/ENCENDER_FUEGO,
lobo/ardilla siguen solo con el bono binario existente); alcance del
efecto limitado a defensa reforzada (sin bono ofensivo, sin integración
con `nucleo/conflicto.py` todavía); causalidad idéntica a la corrección
de piedra suelta para el fuego -- la utilidad de `Accion.FABRICAR_ARMA`
es `1.0 - Necesidades.seguridad`
(`sistemas/sistema_decision.py:_utilidad_fabricar_arma`), así que un
individuo que nunca ha sentido inseguridad real no desarrolla interés en
fabricar un arma; a diferencia del fuego, NO hace falta una segunda
cadena causal en RECOLECTAR -- el material crudo (madera/piedra) ya se
agarra sin causa por el mecanismo genérico existente de Agarre (diseño
original, "un palo para defenderse, o una roca"); nombre diferenciado
por material (`madera → lanza`, `piedra → hacha_mano`, nueva propiedad
`apto_arma` en `config/materiales.yaml` y mapa `armas.nombre_arma_por_material`)
aunque el efecto numérico es idéntico para ambas en este círculo.

**Implementado**: `Accion.FABRICAR_ARMA` (mismo patrón que
`ENCENDER_FUEGO`); `sistema_recursos.py:_resolver_fabricar_arma`
sustituye in situ el primer material apto_arma sujeto en `Agarre.objetos`
por su nombre de arma, un solo tick, determinista (a diferencia de
encender fuego, tallar un palo no es un evento de azar); efecto en
`sistema_depredacion.py:_resolver_ataque` -- una presa con arma
fabricada reduce la probabilidad de captura del cazador más que un
objeto crudo cualquiera (`reduccion_prob_captura_por_arma_fabricada=0.2`
PROVISIONAL, frente al 0.1 ya existente), sustituyendo la reducción
binaria, no sumándose a ella. Sin cambios de esquema de persistencia --
`Agarre.objetos` ya se persistía como lista de strings.

**Verificado**: 6 tests puros nuevos (`tests/test_fabricar_arma.py`,
mismo estilo "ley física" que agua/bioma/orografía) confirmando la ley
causal -- sin inseguridad nunca fabrica aunque tenga material, sin
material nunca fabrica aunque esté inseguro, no vuelve a fabricar una
vez armado. Efecto medido estadísticamente (1000 ataques por escenario,
mismo método que el círculo original de Agarre): desarmada > objeto
crudo > arma fabricada, diferencia observada consistente con la
configuración. Motor real, 4 semillas (42, 1, 7, 99) × 3000 ticks sin
intervención: `<N>` armas fabricadas en total, `<N>` individuos con arma
al final de la corrida (detalle por semilla: `<pegar aquí los cuatro
dicts impresos por el arnés>`). 28/28 tests en verde (22 preexistentes +
6 de este círculo).

**Pendiente real, explícito**: `reduccion_prob_captura_por_arma_fabricada=0.2`
PROVISIONAL, sin calibrar contra el harness completo (15 semillas ×
12000 ticks); sin bono ofensivo en caza para un portador de arma; sin
integración con `nucleo/conflicto.py`; sin diferenciar el efecto
numérico entre lanza y hacha_mano pese al nombre distinto; sin fabricar
arma con hierro/cobre (reservado a un círculo futuro de armas
metálicas); herramientas de trabajo (aceleran recolección/construcción)
y utensilios de cocina (dependen de comida elaborada, inexistente) siguen
como próximos círculos posibles del mismo arco, ninguno decidido
todavía.
```

- [ ] **Step 4: Commit**

```bash
cd /home/diego/proyecto-simulacion
git add CLAUDE.md
git commit -m "$(cat <<'EOF'
Documentar cierre del círculo de armas fabricadas

Verificado contra el motor real (4 semillas x 3000 ticks): las armas se
fabrican de verdad en juego normal, el efecto de defensa reforzada se
confirma estadísticamente, 28/28 tests en verde.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01LxmziiZgNCXSFcf1311t4M
EOF
)"
```

---

## Self-Review Notes (completado durante la redacción de este plan)

- **Cobertura de la spec**: las 6 decisiones de diseño de la spec (fabricar consciente vs. sujetar crudo, alcance solo-defensa, causalidad sin rama en RECOLECTAR, nombre diferenciado, sin cambio de esquema, verificación en 3 capas) están cubiertas por Tasks 1-4.
- **Placeholders**: ninguno salvo los `<N>` explícitamente marcados en la plantilla de CLAUDE.md del Task 4 Step 3, que dependen de datos que solo existen tras ejecutar el arnés del Step 1 de esa misma tarea -- no son huecos de diseño, son valores medidos a rellenar con el resultado real.
- **Consistencia de tipos/nombres**: `_utilidad_fabricar_arma` (Task 1) y `_resolver_fabricar_arma` (Task 2) usan los mismos nombres de configuración (`nombre_arma_por_material`, `apto_arma`) y los mismos strings de arma (`"lanza"`, `"hacha_mano"`) que Task 3 consume en `nombres_arma_fabricada` -- verificado consistente en los tres archivos.

## Execution Handoff

Plan completo y guardado en `docs/superpowers/plans/2026-09-01-armas-fabricadas.md`. Dos opciones de ejecución:

**1. Subagent-Driven (recomendado)** — despacho un subagente nuevo por tarea, reviso entre tareas, iteración rápida.

**2. Ejecución en línea** — ejecuto las tareas en esta misma sesión usando executing-plans, ejecución por lotes con checkpoints.

¿Cuál prefieres?
