# Plan: Cimiento de relaciones interpersonales (Relaciones) + rencor

Spec de referencia: docs/superpowers/specs/2026-09-04-cimiento-relaciones-design.md
(pieza 2 del arco "hilo individual", segundo círculo).

## Objetivo
Construir el componente universal `Relaciones` (vacío, las 4 especies), su
lógica de capacidad/purga (`nucleo/relaciones.py`), el primer consumidor real
de rencor (afinidad NEGATIVA) en `_resolver_posible_intruso`
(`sistema_movimiento.py`), su persistencia, y la corrección del docstring
desactualizado de `componentes/capacidad_mental.py` campo `memoria`.

## Ficheros a tocar (en orden)

1. **`componentes/relaciones.py`** (nuevo): dataclasses `Vinculo`
   (`afinidad`, `ultima_actualizacion_tick`) y `Relaciones`
   (`vinculos: dict[int, Vinculo]`), dato puro. Rango afinidad [-1.0, 1.0].

2. **`nucleo/relaciones.py`** (nuevo): `capacidad_vinculos()` (interpola
   min/max por `CapacidadMental.memoria`) y `ajustar_afinidad()` (suma y
   clampa a [-1.0,1.0]; si al tope, purga el vínculo con
   `ultima_actualizacion_tick` más antiguo; vínculo existente se actualiza
   sin purgar). Mismo patrón que `nucleo/memoria.py`.

3. **`config/relaciones.yaml`** (nuevo): sección `relaciones` con
   `min_vinculos_por_individuo: 2`, `max_vinculos_por_individuo: 6`,
   `delta_rencor_disputa: -0.25` (PROVISIONALES).

4. **`nucleo/entidad.py`**: añadir `Relaciones()` vacío en `crear_criatura`
   y `nacer_criatura` (4 especies), mismo criterio que Agarre/Semillas.

5. **`sistemas/sistema_movimiento.py`**:
   - `ejecutar` recibe `reloj` opcional → deriva `tick_actual`.
   - `_calcular_dormir` propaga `tick_actual`.
   - `_resolver_posible_intruso` acepta `tick_actual`; tras el drenaje de
     seguridad ya existente en cada desenlace (COMPARTE sin cambio;
     CEDE_A: A hacia B si A consciente; CEDE_B: B hacia A si B consciente;
     ENFRENTAMIENTO: cada parte hacia la otra si ES consciente), aplica
     `ajustar_afinidad` con `delta_rencor_disputa` sobre el `Relaciones`
     del consciente. Fauna (no consciente) nunca escribe.

6. **`nucleo/persistencia.py`**: columna `relaciones TEXT` en
   `componentes_estado`, serialización {entidad_id_str: {"afinidad": ..,
   "ultima_actualizacion_tick": ..}}; carga y guardado. Subir
   `VERSION_ESQUEMA`.

7. **`componentes/capacidad_mental.py`**: corregir docstring de `memoria`
   (documentar sus DOS consumidores reales: MemoriaEspacial y Relaciones).

8. **`tests/test_relaciones.py`** (nuevo): leyes físicas (capacidad,
   ajustar/purga, 4 desenlaces en movimiento, fábricas ECS añaden vacío,
   roundtrip persistencia, verificación motor real via BOSQUE_AUTO_TICKS).

9. **`main.py`**: `sistemas["movimiento"].ejecutar(gestor, mundo, reloj)`.

## Fuera de alcance
- Afinidad positiva (amistad), decaimiento, consumidores que LEAN
  Relaciones, familia/linaje/asentamiento, fauna con nombre/Relaciones
  real. No tocar nombres.yaml/narrador.py/CLAUDE.md/informes/historiales.
