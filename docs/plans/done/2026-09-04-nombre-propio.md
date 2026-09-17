# Plan de implementacion: nombre propio real para criaturas conscientes

Fuente de verdad: docs/superpowers/specs/2026-09-04-nombre-propio-design.md.

## Objetivo

Que los gnomos (unica especie consciente hoy) reciban un nombre propio real
(prefijo+sufijo desde `config/nombres.yaml`) en las dos fabricas ECS
(`crear_criatura` y `nacer_criatura`), y que el narrador lo use como sujeto
(`{sujeto}`) en Muerte/Herida/CrisisMental/Nacimiento, concordando el
participio herido/herida por sexo REAL cuando hay nombre propio y por
genero gramatical de especie (fallback) cuando no.

## Ficheros a tocar y que cambia en cada uno

1. `nucleo/entidad.py`
   - Helper `_generar_nombre(rng, catalogo_especie, sexo)` -> str | None
     (prefijo+sufijo, None si el catalogo del sexo esta vacio).
   - `crear_criatura`: sortear `sexo` y `consciencia` ANTES de crear
     `Identidad`; calcular nombre (param `nombre` explicito, si no nombre
     propio por consciencia>=umbral y catalogo no vacio, si no fallback
     `{especie}_{id}`); pasarlo a `Identidad`. Reusar variables para la
     `CapacidadMental` y `Reproduccion` posteriores.
   - `nacer_criatura`: nuevos parametros opcionales `nombres=None` y
     `umbral_consciencia_agencia=0.3`. Sortear `sexo` y calcular
     `consciencia_heredada` ANTES de `Identidad`; mismo criterio de nombre.
2. `sistemas/sistema_reproduccion.py` (`_resolver_nacimientos`): pasar
   `config.get("nombres", {})` y el umbral a `nacer_criatura`.
3. `presentacion/narrador.py`
   - `_contexto()`: anadir `tiene_nombre_propio`, `sujeto`, y `terminacion`
     por sexo real (macho->"o", hembra->"a") cuando hay nombre propio; si no,
     comportamiento de fallback EXACTO actual (`{articulo} {especie}` con
     terminacion por `_es_femenino`).
   - Plantillas Muerte/Herida/CrisisMental/Nacimiento: `{articulo} {especie}`
     -> `{sujeto}`. Concepcion no se toca.
4. Sistemas que emiten eventos: anadir `"sexo": reproduccion.sexo.value` a
   `datos` (junto a `especie`/`nombre` ya presentes):
   - `sistema_necesidades.py` (Muerte)
   - `sistema_ciclo_vital.py` (Muerte)
   - `sistema_depredacion.py` (Muerte + Herida; Herida ademas gana
     `especie` y `nombre`, que hoy no lleva)
   - `sistema_decision.py` (CrisisMental)
   - `sistema_reproduccion.py` (Nacimiento)
   Necesita importar `Reproduccion` en necesidades/ciclo_vital/depredacion.
   `sistema_desastres.py` queda FUERA (spec lo excluye).

## No tocar

- `config/nombres.yaml` (dato entrada cerrado)
- `sistema_desastres.py` / evento Muerte por incendio
- Evento `Concepcion` y su plantilla
- Chequeo de unicidad de nombres
- `CLAUDE.md`, `informes/`, `docs/historial_*.md`
- Esquema SQLite

## Orden

1. Plan (este fichero) y commit `plan: ...`.
2. nucleo/entidad.py (helper + 2 fabricas).
3. sistema_reproduccion.py (pasar catalogo/umbral).
4. Sistemas emisores (sexo/nombre/especie en datos).
5. presentacion/narrador.py (_contexto + plantillas).
6. Tests: ampliar test_narrador_genero.py + nuevo test entidad/nombre.
7. Suite completa una vez al final.
