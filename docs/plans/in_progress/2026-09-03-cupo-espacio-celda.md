# Plan real: Cupo de espacio compartido por celda -- flora vs. construcción

Spec: `docs/superpowers/specs/2026-09-03-cupo-espacio-celda-design.md`
(leída completa). Implemento la pieza 3 "poblar más el mundo": dos
pistas independientes de ocupación de flora (no-competidora en
`Celda.tiene_recurso/tipo_recurso`, competidora SOLO como entidad
`Planta`), y un cupo de espacio físico compartido
(`capacidad_construccion_celda_m2`) entre `Construccion` y flora
competidora (`compite_espacio_fisico=true`: manzano, cactus).

## Ficheros y qué cambia en cada uno (en orden)

1. `config/flora.yaml` — cada especie gana `compite_espacio_fisico: bool`
   (`true`: manzano, cactus; `false`: hierba_silvestre, liquen, musgo).
   Las `true` ganan además `huella_m2` (manzano 4.0, cactus 1.5),
   marcadas PROVISIONAL.

2. `nucleo/espacio.py` (NUEVO) — módulo neutral de cupo compartido,
   generalizando `espacio_disponible_para_construir`:
   - `huella_m2_para(tipo, config_construccion)` (movido de construccion)
   - `huella_m2_flora(especie_cfg)` → `get("huella_m2", 0.0)`
   - `plantas_competidoras_en(gestor, pos_x, pos_y, zona_idx, especies_cfg)`
     → ids de plantas `compite_espacio_fisico=true` en esa celda+zona
   - `espacio_disponible(gestor, pos_x, pos_y, zona_idx, config)` →
     capacidad menos suma de huellas de Construccion y flora competidora,
     aislado por zona_idx.

3. `nucleo/construccion.py` — `espacio_disponible_para_construir` pasa a
   wrapper que delega en `nucleo/espacio.py:espacio_disponible` (recibe
   `config` COMPLETA, no solo `config["construccion"]`). `huella_m2_para`
   se re-exporta igual. Sin cambio de comportamiento para construcciones.

4. `nucleo/flora.py`
   - `intentar_colonizar_celda(...)` gana parámetro `config=None` y se
     bifurca por `compite_espacio_fisico`:
     - `false` → comportamiento histórico exacto (gate `tiene_recurso`,
       escribe la pista no-competidora).
     - `true` → gate por `espacio_disponible` (ignora `tiene_recurso`),
       NO toca `tiene_recurso/tipo_recurso/recursos` de Celda; solo crea
       la entidad `Planta`.
   - `colonizar_por_idoneidad(...)` devuelve `dict[tuple, list[str]]`
     (una celda puede recibir varias competidoras si el cupo lo permite),
     nuevo parámetro `capacidad_construccion_celda_m2=80.0`; sortea
     ponderado sin detenerse tras la primera competidora, y "como mucho
     1 dominante" para la pista no-competidora.

5. `nucleo/zona_bioma.py`
   - `ZonaBioma.__init__` gana `flora_competidora_inicial` (metadata de
     generación, no estado de partida, no se persiste).
   - `generar_zona_bioma` pasa `capacidad_construccion_celda_m2` a
     `colonizar_por_idoneidad`; por celda separa la lista en
     no-competidora (escribe `tipo_recurso/recursos`) y competidora
     (se registra en `flora_competidora_inicial`).

6. `main.py` — `sembrar_flora_inicial` siembra TAMBIÉN las Plantas
   competidoras fundadoras desde `zona.flora_competidora_inicial`
   (etapa=1.0, maduras), para que el motor real tenga varias Plantas
   competidoras coexistiendo en la misma celda.

7. `sistemas/sistema_flora.py` — `posiciones_planta` deja de ser el set
   de TODAS las posiciones ocupadas (que era un veto duro de 1 Planta
   por celda) y pasa a ser el set de colonizaciones del día (vacío al
   arranque). El veto real lo hace `intentar_colonizar_celda` por pista
   (tiene_recurso vs espacio disponible). Pasa `config=self.config` a
   los dos `intentar_colonizar_celda`.

8. `sistemas/sistema_movimiento.py` — `_calcular_construir` pasa
   `self.config` (completa) en vez de `self.config_construccion` a
   `espacio_disponible_para_construir`.

9. `sistemas/sistema_recursos.py`
   - `_cachear_configuracion` arma `self.especie_por_recurso`
     (recurso → especie productora).
   - helper `_hay_recurso_competidor_disponible`: un recurso de especie
     competidora solo es consumible si hay una Planta real de esa especie
     en la celda+zona.
   - `_resolver_comer` filtra `celda.recursos` con ese helper y, para
     competidoras, recupera la especie por `especie_por_recurso` para el
     hook de zoocoria (en vez de `celda.tipo_recurso`).
   - `_resolver_recolectar` gana `gestor/pos_x/pos_y/zona_idx` y filtra
     igual los materiales de especie competidora; `ejecutar` pasa estos
     parámetros.
   - `_resolver_aliviarse` pasa `config=self.config` a
     `intentar_colonizar_celda`.

10. Tests
    - Nuevo `tests/test_cupo_espacio_celda.py` con las leyes de la
      sección Testing de la spec (coexistencia de 2 competidoras y
      rechazo de la 3ª, pistas independientes, espacio_disponible resta
      flora+construcción, aislamiento zona_idx, COMER/RECOLECTAR con
      varias plantas, colonizar_por_idoneidad con varias competidoras y
      respeto del cupo, persistencia roundtrip).
    - `tests/test_flora_colonizacion.py` se adapta al nuevo retorno
      lista de `colonizar_por_idoneidad`.

## Verificación
- `pytest tests/test_cupo_espacio_celda.py tests/test_flora_colonizacion.py
  tests/test_flora_intentar_colonizar.py tests/test_flora_propagacion_caida.py
  tests/test_flora_propagacion_viento.py -v`
- `pytest` completo al final (una vez).
