# Plan: Rumor social (5a) — propagación de opiniones sobre terceros

Fuente de verdad: `docs/superpowers/specs/2026-09-06-rumor-social-design.md`
(pseudocódigo literal de `_procesar_rumor`/`_compartir_rumor` en las líneas
90-134). No se toca 5b, `nucleo/relaciones.py` no gana funciones, ni
`nucleo/asentamiento.py`/`sistemas/sistema_asentamiento.py`.

## Ficheros a tocar (orden)

1. **`config/relaciones.yaml`** — añadir clave PROVISIONAL
   `peso_credibilidad_rumor: 0.15` (fracción del camino que recorre el
   receptor hacia la opinión reportada, no sustitución).

2. **`sistemas/sistema_movimiento.py`**
   - `__init__`: añadir contadores de observación tipo memoria/socializar:
     `_stats_rumores_propagados: int = 0` y
     `_stats_rumor_terceros_nuevos: set[tuple[int, int]]` (pares
     (receptor, tercero) donde el rumor creó una opinión que el receptor
     no tenía antes — evidencia de "nunca formó directamente").
   - `_cachear_configuracion`: cachear `self.peso_credibilidad_rumor`
     desde `config_relaciones` (default 0.15).
   - `ejecutar()`: tercera pasada `_procesar_rumor(gestor, por_celda,
     tick_actual)` sobre el mismo `por_celda`, sin tocar las otras dos.
   - Nuevos métodos `_procesar_rumor` y `_compartir_rumor` copiando el
     pseudocódigo de la spec + comprobación defensiva
     `emisor_id == tercero_id` (spec líneas 141-144). `_compartir_rumor`
     cuenta `_stats_rumores_propagados` y registra en
     `_stats_rumor_terceros_nuevos` cuando el tercero no estaba en
     `rel_receptor.vinculos` antes de `ajustar_afinidad`.

3. **`main.py`** — bloque `BOSQUE_AUTO_TICKS`: reportar rumores
   propagados y cuántos pares (receptor, tercero) tienen hoy una opinión
   que el rumor creó (verificando en el gestor vivo que esos vinculos
   siguen existiendo).

4. **`tests/test_rumor_social.py`** (nuevo) — leyes físicas dirigidas:
   - `_compartir_rumor` dispara → transfiere y desplaza; sin efecto si
     falla la tirada; sin efecto si el emisor no conoce a nadie más que
     al receptor; el tercero nunca es el receptor; receptor sin opinión
     previa parte de 0.0 (valor exacto); receptor con opinión previa
     contraria se desplaza fracción, no sobrescribe (valor exacto).
   - `_procesar_rumor`: direcciones independientes (A→B sí, B→A no).
   - `ejecutar()` invoca la pasada una vez por tick.

## Verificación obligatoria (no opcional)

- `pytest tests/test_rumor_social.py -v`
- Suite completa una vez al final: `pytest -q`
- `BOSQUE_AUTO_TICKS=2000 python main.py` (población real) midiendo
  rumores propagados de verdad y si algún consciente terminó con opinión
  sobre un tercero que nunca formó directamente (via
  `_stats_rumor_terceros_nuevos` + gestor vivo / BD). Reportar la cifra
  en el mensaje de commit final aunque sea baja o nula.
