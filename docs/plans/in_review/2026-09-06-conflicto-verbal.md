# Plan: Conflicto verbal (roce social + contacto por crisis violenta)

Spec fuente de la verdad: `docs/superpowers/specs/2026-09-06-conflicto-verbal-design.md`.

## Objetivo

Dar consecuencia real al estado `Accion.CRISIS_VIOLENTA` (ya existente, hoy
gesto vacío de movimiento) cuando hay contacto a distancia 0, y añadir el
segundo disparador "roce social" entre conscientes en la misma celda. Ambos
usan UN ÚNICO resolutor compartido, extraído por refactor del único
consumidor actual (`_resolver_posible_intruso`, refugio ocupado). Ningún
sistema nuevo LEE `Relaciones` — solo se escribe rencor, igual que ya
escriben refugio ocupado/amistad/concepción.

## Ficheros a tocar

### 1. `sistemas/sistema_movimiento.py` (núcleo del cambio)

- **Imports:** añadir `PoolMental` (componentes/pool_mental.py).
- **`__init__`:** inicializar dos contadores privados de medición
  `_stats_roce_social_resueltos` y `_stats_crisis_violenta_contacto` (0),
  para la verificación explícita contra el motor real y los tests.
- **`_cachear_configuracion`:** cachear de `config["conflicto"]`:
  `probabilidad_base_roce_social` (0.01), `peso_agresividad_roce` (0.05),
  `peso_estres_roce` (0.05).
- **Nueva `_entidad_cercana_cualquiera_con_id`:** igual que
  `_entidad_cercana_cualquiera` pero devolviendo también el id del
  candidato más cercano. `_calcular_huida_erratica` y la variante original
  SIN id quedan intactas.
- **Nueva `_resolver_conflicto_entre(gestor, mundo, a_id, b_id,
  temperamento_a, temperamento_b, tick_actual) -> ResultadoDisputa`:**
  extrae el bloque común de `_resolver_posible_intruso` (urgencias,
  mismo_grupo vía asentamiento_de, bono_arma vía _bono_arma_empunada,
  son_familia vía es_familia_directa, llamada a resolver_disputa, y las
  cuatro ramas de consecuencias CEDE_A/CEDE_B/ENFRENTAMIENTO/COMPARTE con
  drenaje de Necesidades.seguridad + _aplicar_rencor). Simétrico en a/b.
  Devuelve el ResultadoDisputa (hoy ningún llamador lo usa, se expone).
- **`_resolver_posible_intruso` pasa a ser wrapper delgado:** conserva
  TAL CUAL la localización del refugio propio (construcción con
  completado_alguna_vez, misma celda+zona) y del intruso; una vez
  identificado `intruso_id`, delega el resto en
  `_resolver_conflicto_entre`. Comportamiento idéntico → los tests
  existentes de los 4 desenlaces + parentesco siguen en verde.
- **`_calcular_crisis_violenta`:** nueva firma
  `(gestor, mundo, entidad_id, pos_x, pos_y, radio, zona_idx=0,
  temperamento=None, tick_actual=0)`. Usa la variante con id; si no hay
  objetivo → `_paso_aleatorio()`; si el objetivo está a distancia 0
  (contacto real, misma celda) → `_resolver_conflicto_entre` y devuelve
  `(0, 0)`; si está a distancia > 0 → `_acercarse_a` (comportamiento
  actual intacto). Incrementa `_stats_crisis_violenta_contacto` al
  resolver contacto.
- **Rama de despacho en `ejecutar()`** (`elif accion ==
  Accion.CRISIS_VIOLENTA:`): pasar `mundo, temperamento, tick_actual`
  (ya disponibles en ese scope, mismo patrón que otras ramas).
- **Nueva `_procesar_roce_social(gestor, mundo, tick_actual)`:** llamada
  UNA VEZ al principio de `ejecutar()` (antes del bucle por entidad, sobre
  posiciones del cierre del tick anterior). Agrupa conscientes
  (consciencia >= umbral_consciencia_agencia) por `(x, y, zona_idx)`; para
  cada par que comparte celda sortea `probabilidad_base_roce_social +
  peso_agresividad_roce * ((agr_a + agr_b)/2) + peso_estres_roce *
  max(1-estab_a, 1-estab_b)`; si `rng.random() < prob` →
  `_resolver_conflicto_entre`. Cada par se procesa una sola vez
  (bucles i<j). Incrementa `_stats_roce_social_resueltos` por resolución.

### 2. `config/comportamiento.yaml`

En la sección `conflicto` (sin tocar nada existente), añadir las tres
claves PROVISIONAL sin calibrar:
`probabilidad_base_roce_social: 0.01`, `peso_agresividad_roce: 0.05`,
`peso_estres_roce: 0.05`.

### 3. `tests/test_conflicto_verbal.py` (nuevo)

Estilo "ley física" del proyecto.

- Refactor: no hace falta test nuevo — los existentes de los 4 desenlaces
  (test_relaciones.py) + parentesco (test_parentesco.py) deben seguir en
  verde SIN cambios.
- CRISIS_VIOLENTA + contacto: dos entidades en la misma celda, una
  despachada en `_calcular_crisis_violenta` → se resuelve (se escribe
  rencor / se drena seguridad), devuelve `(0, 0)`, y
  `_stats_crisis_violenta_contacto == 1`. Con distancia > 0 → se acerca
  (dx/dy != 0) sin resolver nada (sin rencor, contador 0).
- Roce social: con `rng.random` fijado a un valor entre las dos
  probabilidades, el par de alta agresividad/estrés se resuelve y el de
  baja no (mismo rng semillado → la probabilidad efectiva sube con
  agresividad/estrés combinados). Un par con un solo consciente queda
  fuera del filtro (no se resuelve). Un mismo par no se procesa dos veces
  en el mismo tick (a lo sumo un vinculo nuevo entre ellos).

### 4. Verificación obligatoria contra el motor real (BOSQUE_AUTO_TICKS)

- Harness temporal FUERA del repo (`/tmp/medir_conflicto_verbal.py`) que
  replica la inicialización de `main.py` (config, reloj, gestor, mundo,
  sistemas, sembrar_poblacion_inicial) y corre ~3000 ticks de
  `ejecutar_tick`, midiendo explícitamente al final:
  - `sistemas["movimiento"]._stats_roce_social_resueltos`
  - `sistemas["movimiento"]._stats_crisis_violenta_contacto`
  - `Relaciones` de la población: nº de individuos con vinculos != {},
    nº total de vinculos negativos, y nº de pares (autor, otro) NUEVOS
    con rencor creados durante la tanda (fluctuación real).
- Mismo harness sobre el código ANTERIOR a esta pieza como baseline
  (git stash) para comparar la fluctuación de `Relaciones` antes/después.
- Cifras reales reportadas en el mensaje del commit final, aunque sean
  bajas o nulas.

## Orden

1. Plan + commit `plan:`.
2. Baseline de medición sobre el código actual (git stash limpio).
3. Implementar cambios (sistema_movimiento.py → comportamiento.yaml).
4. Tests nuevos + suite dirigida (test_conflicto_verbal,
   test_relaciones, test_parentesco, test_armas_primitivas_v2).
5. Suite completa UNA vez.
6. Medición BOSQUE_AUTO_TICKS con el código nuevo.
7. Commit final con cifras de medición en el mensaje.

## Fuera de alcance (recordatorio)

- Nada de robo/agravio por recurso escaso, `Accion.SOCIALIZAR`, sonido,
  memoria espacial compartida, `_tipo_crisis` ni umbrales de crisis.
- Ningún sistema LEE `Relaciones` para modular comportamiento.
- No se tocan `componentes/relaciones.py`, `nucleo/relaciones.py`,
  `config/nombres.yaml`, CLAUDE.md, informes/, docs/historial_*.md,
  esquemas SQLite, ni `_calcular_huida_erratica`.
